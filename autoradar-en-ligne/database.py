"""
Couche d'accès à la base SQLite locale des annonces automobiles.

Usage :
    python database.py            -> crée / met à jour la base (annonces.db)
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterable, Optional, TypedDict

DB_PATH = Path(__file__).with_name("annonces.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS annonces (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    titre               TEXT    NOT NULL,
    prix                INTEGER,              -- en euros
    annee               INTEGER,
    kilometrage         INTEGER,              -- en km
    lien                TEXT    NOT NULL UNIQUE,  -- clé naturelle : évite les doublons
    source              TEXT    NOT NULL,     -- ex. 'AutoScout24'
    image               TEXT,                 -- URL de la photo principale
    carburant           TEXT,
    boite               TEXT,
    puissance_ch        INTEGER,
    ville               TEXT,
    code_postal         TEXT,
    vendeur             TEXT,
    type_vendeur        TEXT,                 -- 'Dealer' / 'Private'…
    description         TEXT,                 -- texte complet du vendeur
    equipements         TEXT    NOT NULL DEFAULT '[]', -- JSON : liste complète des équipements
    accident_declare    INTEGER,              -- 1 / 0 / NULL (inconnu), déclaré par le vendeur
    origine_description TEXT,                 -- 'fiche-json' | 'fiche-navigateur' | 'recherche' | NULL
    donnees_brutes      TEXT,                 -- JSON brut (recherche + fiche) : rien à rescanner plus tard
    merguez             INTEGER NOT NULL DEFAULT 0,    -- 1 = épave / HS / pour pièces…
    motifs_merguez      TEXT    NOT NULL DEFAULT '[]', -- JSON : motifs détectés
    options             TEXT    NOT NULL DEFAULT '[]', -- JSON : options premium détectées
    cree_le             TEXT    NOT NULL DEFAULT (datetime('now')),
    maj_le              TEXT    NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_annonces_source  ON annonces(source);
CREATE INDEX IF NOT EXISTS idx_annonces_prix    ON annonces(prix);
CREATE INDEX IF NOT EXISTS idx_annonces_merguez ON annonces(merguez);
"""

# Colonnes ajoutées depuis la v1 : migrées automatiquement sur une base existante.
MIGRATIONS = {
    "description":         "ALTER TABLE annonces ADD COLUMN description TEXT",
    "merguez":             "ALTER TABLE annonces ADD COLUMN merguez INTEGER NOT NULL DEFAULT 0",
    "motifs_merguez":      "ALTER TABLE annonces ADD COLUMN motifs_merguez TEXT NOT NULL DEFAULT '[]'",
    "options":             "ALTER TABLE annonces ADD COLUMN options TEXT NOT NULL DEFAULT '[]'",
    "carburant":           "ALTER TABLE annonces ADD COLUMN carburant TEXT",
    "boite":               "ALTER TABLE annonces ADD COLUMN boite TEXT",
    "puissance_ch":        "ALTER TABLE annonces ADD COLUMN puissance_ch INTEGER",
    "ville":               "ALTER TABLE annonces ADD COLUMN ville TEXT",
    "code_postal":         "ALTER TABLE annonces ADD COLUMN code_postal TEXT",
    "vendeur":             "ALTER TABLE annonces ADD COLUMN vendeur TEXT",
    "type_vendeur":        "ALTER TABLE annonces ADD COLUMN type_vendeur TEXT",
    "equipements":         "ALTER TABLE annonces ADD COLUMN equipements TEXT NOT NULL DEFAULT '[]'",
    "accident_declare":    "ALTER TABLE annonces ADD COLUMN accident_declare INTEGER",
    "origine_description": "ALTER TABLE annonces ADD COLUMN origine_description TEXT",
    "donnees_brutes":      "ALTER TABLE annonces ADD COLUMN donnees_brutes TEXT",
}

# Champs "simples" : mis à jour à chaque passage (en gardant l'ancienne valeur si la nouvelle manque)
CHAMPS = ["titre", "prix", "annee", "kilometrage", "lien", "source", "image",
          "carburant", "boite", "puissance_ch", "ville", "code_postal", "vendeur", "type_vendeur",
          "description", "equipements", "accident_declare", "origine_description", "donnees_brutes",
          "merguez", "motifs_merguez", "options"]
JSON_CHAMPS = {"equipements", "motifs_merguez", "options", "donnees_brutes"}
TOUJOURS_ECRASER = {"titre", "prix", "annee", "kilometrage", "source", "merguez", "motifs_merguez", "options"}


class Annonce(TypedDict, total=False):
    titre: str
    prix: Optional[int]
    annee: Optional[int]
    kilometrage: Optional[int]
    lien: str
    source: str
    image: Optional[str]
    carburant: Optional[str]
    boite: Optional[str]
    puissance_ch: Optional[int]
    ville: Optional[str]
    code_postal: Optional[str]
    vendeur: Optional[str]
    type_vendeur: Optional[str]
    description: Optional[str]
    equipements: list[str]
    accident_declare: Optional[bool]
    origine_description: Optional[str]
    donnees_brutes: Optional[dict]
    merguez: bool
    motifs_merguez: list[str]
    options: list[str]


@contextmanager
def connect(db_path: Path | str = DB_PATH):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(db_path: Path | str = DB_PATH) -> None:
    with connect(db_path) as conn:
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(annonces)")}
        if cols:  # base existante : on ajoute les colonnes manquantes avant le reste du schéma
            for col, sql in MIGRATIONS.items():
                if col not in cols:
                    conn.execute(sql)
        conn.executescript(SCHEMA)


def _valeur(a: Annonce, champ: str) -> Any:
    v = a.get(champ)
    if champ == "donnees_brutes":
        return json.dumps(v, ensure_ascii=False) if v else None
    if champ in JSON_CHAMPS:  # listes : '[]' si vide
        return json.dumps(v or [], ensure_ascii=False)
    if champ in ("merguez", "accident_declare") and v is not None:
        return 1 if v else 0
    return v


def _regle_maj(c: str) -> str:
    if c in TOUJOURS_ECRASER:
        return f"{c} = excluded.{c}"
    if c == "equipements":  # liste vide = fiche non relue -> on garde l'existant
        return "equipements = CASE WHEN excluded.equipements = '[]' THEN annonces.equipements ELSE excluded.equipements END"
    return f"{c} = COALESCE(excluded.{c}, annonces.{c})"


def save_annonces(annonces: Iterable[Annonce], db_path: Path | str = DB_PATH) -> int:
    """Insère ou met à jour (upsert sur le lien). Retourne le nombre de lignes traitées."""
    rows = [tuple(_valeur(a, c) for c in CHAMPS) for a in annonces]
    if not rows:
        return 0
    init_db(db_path)
    maj = ",\n    ".join(_regle_maj(c) for c in CHAMPS if c != "lien")
    sql = (f"INSERT INTO annonces ({', '.join(CHAMPS)}) VALUES ({', '.join('?' * len(CHAMPS))})\n"
           f"ON CONFLICT(lien) DO UPDATE SET\n    {maj},\n    maj_le = datetime('now')")
    with connect(db_path) as conn:
        conn.executemany(sql, rows)
    return len(rows)


def get_details_connus(liens: Iterable[str], db_path: Path | str = DB_PATH) -> dict[str, dict]:
    """Description / équipements déjà en base (pour ne rien perdre si les fiches ne sont pas relues)."""
    liens = list(liens)
    if not liens:
        return {}
    init_db(db_path)
    out: dict[str, dict] = {}
    with connect(db_path) as conn:
        for i in range(0, len(liens), 500):  # limite de variables SQLite
            lot = liens[i:i + 500]
            cur = conn.execute(
                f"SELECT lien, description, equipements, accident_declare, origine_description FROM annonces "
                f"WHERE lien IN ({','.join('?' * len(lot))})", lot)
            for r in cur:
                out[r["lien"]] = {
                    "description": r["description"],
                    "equipements": json.loads(r["equipements"] or "[]"),
                    "accident_declare": r["accident_declare"],
                    "origine_description": r["origine_description"],
                }
    return out


def list_annonces(db_path: Path | str = DB_PATH) -> list[dict]:
    """Tout sauf les données brutes (trop lourdes pour l'interface)."""
    init_db(db_path)
    with connect(db_path) as conn:
        cur = conn.execute(
            "SELECT id, titre, prix, annee, kilometrage, lien, source, image, carburant, boite, "
            "puissance_ch, ville, code_postal, vendeur, type_vendeur, description, equipements, "
            "accident_declare, origine_description, merguez, motifs_merguez, options, cree_le, maj_le "
            "FROM annonces ORDER BY maj_le DESC, id DESC"
        )
        out = []
        for r in cur.fetchall():
            d = dict(r)
            d["merguez"] = bool(d["merguez"])
            for k in ("motifs_merguez", "options", "equipements"):
                d[k] = json.loads(d[k] or "[]")
            out.append(d)
        return out


def iter_pour_detection(db_path: Path | str = DB_PATH):
    init_db(db_path)
    with connect(db_path) as conn:
        for r in conn.execute("SELECT id, titre, description, equipements, accident_declare, donnees_brutes FROM annonces"):
            yield dict(r)


def maj_detection(maj: list[tuple[int, list[str], list[str]]], db_path: Path | str = DB_PATH) -> None:
    with connect(db_path) as conn:
        conn.executemany(
            "UPDATE annonces SET merguez = ?, motifs_merguez = ?, options = ? WHERE id = ?",
            [(1 if m else 0, json.dumps(m, ensure_ascii=False), json.dumps(o, ensure_ascii=False), i)
             for i, m, o in maj],
        )


if __name__ == "__main__":
    init_db()
    print(f"Base prête : {DB_PATH.resolve()}  ({len(list_annonces())} annonce(s))")
