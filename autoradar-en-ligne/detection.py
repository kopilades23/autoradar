"""
Détection par mots-clés dans le titre / la description / les équipements d'une annonce.

  - Filtre « anti-merguez » : épaves, véhicules HS, pour pièces…
  - Options premium : Bose, Harman Kardon, Burmester, toit panoramique, Matrix LED

    python detection.py                 -> auto-test des mots-clés
    python detection.py --reappliquer   -> relance la détection sur toute la base (sans rescanner)

Les listes ci-dessous sont faites pour être modifiées : ajoutez vos propres motifs.
Le texte est normalisé avant recherche (minuscules, sans accents, apostrophes unifiées),
donc écrivez les motifs SANS accents et en minuscules.
"""
from __future__ import annotations

import re
import unicodedata

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #
# libellé affiché -> expression régulière (sur texte normalisé)
MERGUEZ_MOTIFS: dict[str, str] = {
    "HS":            r"\bhs\b",
    "non roulant":   r"\bnon[\s-]+roulante?s?\b",
    "pour pièces":   r"\bpour\s+(les\s+)?pieces?\b",
    "accidenté":     r"\baccidentee?s?\b",
    "dans l'état":   r"\bdans\s+l\s*'?\s*etat\b",
    "moteur cassé":  r"\bmoteur\s+(est\s+)?cassee?\b",
    "problème moteur": r"\b(probleme|souci|defaut|panne)s?\s+(de\s+|du\s+)?moteur\b|\bmoteur\s+(a\s+refaire|a\s+changer|serre|grippe)\b|\bbruit\s+(anormal\s+)?(du\s+)?moteur\b",
    "turbo à changer": r"\bturbo\s+(a\s+changer|a\s+remplacer|defectueux|mort|fuit|a\s+prevoir|siffle)\b",
    "boîte à changer": r"\bboite(\s+de\s+vitesses?)?\s+(a\s+changer|a\s+remplacer|defectueuse|cassee|qui\s+craque)\b",
    "embrayage à changer": r"\bembrayage\s+(a\s+changer|a\s+remplacer|a\s+prevoir|a\s+faire|patine|qui\s+patine|defectueux)\b",
    "joint de culasse": r"\bjoint\s+de\s+culasse\s+(hs|a\s+changer|a\s+faire|a\s+prevoir|defectueux|grille|claque)\b",
    "ne démarre pas": r"\bne\s+demarre\s+(plus|pas)\b",
    "sans contrôle technique": r"\bsans\s+(controle\s+technique|ct)\b|\bct\s+(refuse|a\s+refaire)\b|\bcontre[\s-]+visite\b",
    "épave / VGE":   r"\bepave\b|\bvge\b|\bvei\b|\bsinistree?\b",
}

# Groupe -> {libellé affiché -> expression régulière}. L'ordre compte : le 1er motif coché
# d'un groupe « rare » (audio, etc.) sert aussi de mot-clé aux sites qui savent chercher en texte.
OPTIONS_GROUPES: dict[str, dict[str, str]] = {
    "Audio premium": {
        "Bose":            r"\bbose\b",
        "Harman Kardon":   r"\bharman(\s*[/&-]?\s*kardon)?\b",
        "Burmester":       r"\bburmester\b",
        "Focal":           r"\bfocal\b",
        "JBL":             r"\bjbl\b",
        "Bang & Olufsen":  r"\bbang\s*(&|and|et)?\s*olufsen\b|\bb\s?&\s?o\b",
        "Meridian":        r"\bmeridian\b",
    },
    "Confort & techno": {
        "Toit panoramique":       r"\btoit\b[\w\s/-]{0,25}?\bpano(ramique)?\b|\bpanoramic\s+(glass\s+)?roof\b",
        "Matrix LED":             r"\bmatrix[\s-]*(led|beam)?\b|\bled[\s-]*matrix\b|\bintellilux\b|\bpixel[\s-]*led\b|\bmultibeam\b",
        "Affichage tête haute":   r"\baffichage\s+(en\s+)?tete[\s-]+haute\b|\bhead[\s-]*up\b|\bhud\b",
        "Caméra 360°":            r"\b(camera|vision|cameras)s?\s*(de\s+recul\s*)?(a\s+)?360\b|\b360\s*°?\s*(camera|vision|view|degres)\b|\bsurround\s+view\b|\btop\s*view\b|\barea\s+view\b",
        "CarPlay / Android Auto": r"\bcar\s*play\b|\bandroid\s*auto\b|\bmirror\s*(screen|link)\b",
        "Régulateur adaptatif":   r"\bregulateur\s+(de\s+vitesse\s+)?(adaptatif|actif|intelligent)\b|\badaptive\s+cruise\b|\bacc\b|\bdistronic\b|\bstop\s*(&|and)\s*go\b",
        "Sièges chauffants":      r"\bsieges?\s+(avant\s+|conducteur\s+)?chauffants?\b|\bsieges?\s+(avant\s+)?chauffes?\b",
        "Sièges cuir":            r"\b(sellerie|sieges?|interieur|garnissage)\s+(\w+\s+){0,2}cuir\b|\bcuir\s+(integral|nappa|dakota|vernasca|merino)\b|\b(tout|full)\s+cuir\b",
        "Hayon électrique":       r"\bhayon\s+(de\s+coffre\s+)?(electrique|motorise|mains[\s-]+libres)\b|\bcoffre\s+(electrique|motorise)\b",
    },
    "Mécanique & historique": {
        "Boîte automatique":  r"\bboite\s+(de\s+vitesses?\s+)?(auto|automatique|robotisee)\b|\bbva\d?\b|\beat\s?[68]\b|\bdsg\d?\b|\bedc\b|\be-?dcs\s?\d\b|\bs\s?tronic\b|\bsteptronic\b|\btiptronic\b|\bcvt\b|\bdct\b|\btransmission\s+automatique\b",
        "4x4 / intégrale":    r"\b4x4\b|\b4wd\b|\bawd\b|\bquattro\b|\bx\s?drive\b|\b4\s?motion\b|\b4\s?matic\b|\ball\s*grip\b|\btransmission\s+integrale\b|\b4\s+roues\s+motrices\b",
        "Attelage":           r"\battelage\b",
        "Première main":      r"\b(1\s*(ere|er|re)|premiere)\s+main\b",
    },
}
OPTIONS_PREMIUM: dict[str, str] = {k: v for g in OPTIONS_GROUPES.values() for k, v in g.items()}
# Mot-clé court envoyé aux sites qui savent chercher dans le texte des annonces
MOTS_CLES_SITE: dict[str, str] = {
    "Bose": "bose", "Harman Kardon": "harman", "Burmester": "burmester", "Focal": "focal", "JBL": "jbl",
    "Bang & Olufsen": "olufsen", "Meridian": "meridian", "Toit panoramique": "panoramique", "Matrix LED": "matrix",
    "Affichage tête haute": "tete haute", "Caméra 360°": "360", "CarPlay / Android Auto": "carplay",
    "Régulateur adaptatif": "adaptatif", "Sièges chauffants": "chauffants", "Sièges cuir": "cuir",
    "Hayon électrique": "hayon", "Boîte automatique": "automatique", "4x4 / intégrale": "4x4",
    "Attelage": "attelage", "Première main": "premiere main",
}

# Une négation juste avant le motif annule la détection :
# « jamais accidenté », « non accidenté », « n'a jamais été accidenté », « aucun choc… »
NEGATION_AVANT = re.compile(
    r"\b(non|jamais|pas|aucun|aucune|sans|ni)\b[\w\s']{0,20}$"
)

# --------------------------------------------------------------------------- #
_MERGUEZ_RE = {k: re.compile(v) for k, v in MERGUEZ_MOTIFS.items()}
_OPTIONS_RE = {k: re.compile(v) for k, v in OPTIONS_PREMIUM.items()}


def normaliser(texte: str) -> str:
    texte = unicodedata.normalize("NFKD", texte or "")
    texte = "".join(c for c in texte if not unicodedata.combining(c))
    texte = texte.replace("’", "'").replace("`", "'").replace(" ", " ")
    return re.sub(r"\s+", " ", texte.lower())


def detecter_merguez(*textes: str | None) -> list[str]:
    """Retourne la liste des motifs trouvés (vide = annonce saine)."""
    t = normaliser(" \n ".join(x for x in textes if x))
    trouves: list[str] = []
    for label, rx in _MERGUEZ_RE.items():
        for m in rx.finditer(t):
            avant = t[max(0, m.start() - 30): m.start()]
            if label != "non roulant" and NEGATION_AVANT.search(avant):
                continue  # « jamais accidenté » -> ce n'est pas une merguez
            trouves.append(label)
            break
    return trouves


NEGATION_OPTION = re.compile(r"\b(sans|pas\s+de|pas\s+d|non|aucun|aucune)\b[\s']{0,3}$")


def detecter_options(*textes: str | None) -> list[str]:
    t = normaliser(" \n ".join(x for x in textes if x))
    out = []
    for label, rx in _OPTIONS_RE.items():
        for m in rx.finditer(t):
            if not NEGATION_OPTION.search(t[max(0, m.start() - 12): m.start()]):  # « sans attelage »
                out.append(label)
                break
    return out


def analyser(titre: str | None, description: str | None = None, equipements: list[str] | None = None,
             accident_declare: bool | int | None = None, dommages: list | None = None,
             autres_textes: list[str] | None = None) -> tuple[list[str], list[str]]:
    """Applique les deux filtres à une annonce complète -> (motifs_merguez, options)."""
    motifs = detecter_merguez(titre, description)
    if accident_declare and "accidenté" not in motifs:
        motifs.append("accidenté (déclaré)")
    if dommages:
        motifs.append("dommages déclarés")
    equip = ", ".join(equipements or [])
    options = detecter_options(titre, description, equip, *(autres_textes or []))
    return motifs, options


def reappliquer(db_path=None) -> None:
    """Relance la détection sur toute la base, sans rien retélécharger
    (utile après avoir modifié les mots-clés ci-dessus)."""
    import json
    import database
    kw = {"db_path": db_path} if db_path else {}
    maj, n_m, n_o = [], 0, 0
    for r in database.iter_pour_detection(**kw):
        brut = json.loads(r["donnees_brutes"] or "{}")
        fiche_vehicule = ((brut.get("fiche") or {}).get("vehicle") or {})
        sous_titre = ((brut.get("recherche") or {}).get("vehicle") or {}).get("subtitle")
        motifs, options = analyser(
            r["titre"], r["description"], json.loads(r["equipements"] or "[]"),
            r["accident_declare"], fiche_vehicule.get("damageConditions"), [sous_titre] if sous_titre else None,
        )
        maj.append((r["id"], motifs, options))
        n_m += bool(motifs)
        n_o += bool(options)
    database.maj_detection(maj, **kw)
    print(f"✓ Détection réappliquée sur {len(maj)} annonce(s) : {n_m} merguez, {n_o} avec options premium")


def _auto_test() -> None:
    cas = [
        ("Peugeot 208 moteur HS vendu dans l'état", ["HS", "dans l'état"], []),
        ("Véhicule jamais accidenté, toit panoramique, son Bose", [], ["Bose", "Toit panoramique"]),
        ("Non accidentée. Phares Matrix LED, Harman/Kardon", [], ["Harman Kardon", "Matrix LED"]),
        ("VENDU POUR PIÈCES - non roulante", ["non roulant", "pour pièces"], []),
        ("Accidentée côté gauche, Burmester", ["accidenté"], ["Burmester"]),
        ("Toit ouvrant panoramique", [], ["Toit panoramique"]),
        ("Moteur cassé", ["moteur cassé"], []),
        ("Parfait état, révisée", [], []),
        ("Son Focal, CarPlay, caméra 360, sièges chauffants, 1ère main", [], ["Focal", "Caméra 360°", "CarPlay / Android Auto", "Sièges chauffants", "Première main"]),
        ("Boîte EAT8, attelage, régulateur adaptatif, affichage tête haute", [], ["Affichage tête haute", "Régulateur adaptatif", "Boîte automatique", "Attelage"]),
        ("Climatisation automatique, volant cuir, sans attelage", [], []),
        ("Audi A4 quattro S tronic, sellerie cuir, B&O, hayon électrique", [], ["Bang & Olufsen", "Sièges cuir", "Hayon électrique", "Boîte automatique", "4x4 / intégrale"]),
    ]
    ok = True
    for texte, attendu_m, attendu_o in cas:
        m, o = detecter_merguez(texte), detecter_options(texte)
        bon = m == attendu_m and o == attendu_o
        ok &= bon
        print(("✓" if bon else "✗"), texte, "->", m, o)
    print("OK" if ok else "ÉCHEC")


if __name__ == "__main__":
    import sys
    if "--reappliquer" in sys.argv:
        reappliquer()
    else:
        _auto_test()
        print("\n(astuce : python detection.py --reappliquer  -> relance la détection sur toute la base)")
