"""
Moteur de recherche EN DIRECT, multi-sites : rien n'est téléchargé à l'avance ni stocké.

Sources : AutoScout24 (JSON embarqué), LeParking (agrégateur : Leboncoin, La Centrale…), ParuVendu,
L'argus (dont les copies d'annonces Leboncoin, avec leur description), Auto-Sélection,
Renew, Spoticar, Autosphere, Zoomcar (sur PC seulement : le site refuse les hébergeurs).

Principe : pour chaque site on ne lit qu'UNE page de résultats à la fois (filtrée par le site
quand il le permet), puis les fiches de cette page seulement pour détecter merguez et options.

Deux façons d'accéder aux sites (même logique, mêmes résultats) :
  - mode « http » (défaut, et en ligne) : requêtes directes avec l'empreinte de Chrome (curl_cffi),
    pages analysées en Python (parseurs.py). Léger : tient sur un hébergement gratuit.
  - mode « navigateur » (python server.py --navigateur) : un Chrome piloté par Playwright, un onglet
    par site ; les pages sont récupérées par fetch() et analysées dans le navigateur (sites/*.js).
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import random
import re
import threading
import time
import unicodedata
from pathlib import Path
from typing import Any, Callable, Optional
from urllib.parse import quote, urlencode, urljoin, urlparse

try:  # mode « navigateur » (local) uniquement ; le mode « http » (en ligne) s'en passe
    from playwright.async_api import BrowserContext, Page, async_playwright
except ImportError:
    BrowserContext = Page = async_playwright = None

import scraper_autoscout24 as as24
from detection import MOTS_CLES_SITE, OPTIONS_GROUPES, OPTIONS_PREMIUM, analyser

ICI = Path(__file__).parent
PROFIL = Path(os.environ.get("AUTORADAR_PROFIL") or ICI / "profil_navigateur")   # cookies des sites, mémorisés
CACHE_CATALOGUE = ICI / "catalogue_cache.json"
EXTRACTEUR_JS = (ICI / "sites" / "extracteur.js").read_text(encoding="utf-8")
FICHE_JS = (ICI / "sites" / "fiche.js").read_text(encoding="utf-8")
LEPARKING_JS = (ICI / "sites" / "leparking.js").read_text(encoding="utf-8")
LEPARKING = "https://www.leparking.fr"

AS24 = "https://www.autoscout24.fr"
# Pré-filtres AutoScout24 (ids d'équipement de la taxonomie du site, relevés le 30/09/2026)
AS24_EQ = {"Toit panoramique": 50, "Bose": 155, "Harman Kardon": 155, "Burmester": 155, "Focal": 155,
           "JBL": 155, "Bang & Olufsen": 155, "Meridian": 155}
AS24_TRI = {"pertinence": ("standard", 0), "prix": ("price", 0), "prix_desc": ("price", 1), "date": ("age", 0)}

# fetch() + extraction exécutés DANS l'onglet du site ; seul le résultat (petit) revient à Python.
FETCH_NEXT_JS = """async (url) => {
  try {
    const ctl = new AbortController(); setTimeout(() => ctl.abort(), 20000);
    const r = await fetch(url, { signal: ctl.signal, credentials: 'include', headers: { 'Accept': 'text/html,application/xhtml+xml' } });
    const h = await r.text();
    const m = h.match(/<script[^>]+id="__NEXT_DATA__"[^>]*>([\\s\\S]*?)<\\/script>/);
    return { status: r.status, json: m ? m[1] : null };
  } catch (e) { return { status: 0, json: null }; }
}"""
# Signatures des pages anti-robot (ParuVendu « antiaspiration », DataDome, Cloudflare…)
BLOQUE_JS = r"const BLOQUE = /antiaspiration|getCaptcha|captcha-delivery\.com|geo\.captcha|cf-chl-|<title>\s*(Just a moment|Attention Required|Un instant)/i;"
FETCH_LISTE_JS = f"""async ([url, re, marque]) => {{
  {BLOQUE_JS}
  const EX = {EXTRACTEUR_JS};
  try {{
    const ctl = new AbortController(); setTimeout(() => ctl.abort(), 20000);
    const r = await fetch(url, {{ signal: ctl.signal, credentials: 'include', headers: {{ 'Accept': 'text/html,application/xhtml+xml' }} }});
    const h = await r.text();
    if (BLOQUE.test(h.slice(0, 30000))) return {{ status: 429 }};
    if (r.status >= 400 && r.status !== 404) return {{ status: r.status }};
    return {{ status: r.status, ...EX([h, r.url || url, re, marque]) }};
  }} catch (e) {{ return {{ status: 0 }}; }}
}}"""
FETCH_FICHE_JS = f"""async (url) => {{
  {BLOQUE_JS}
  const FI = {FICHE_JS};
  try {{
    const ctl = new AbortController(); setTimeout(() => ctl.abort(), 20000);
    const r = await fetch(url, {{ signal: ctl.signal, credentials: 'include', headers: {{ 'Accept': 'text/html,application/xhtml+xml' }} }});
    const h = await r.text();
    if (BLOQUE.test(h.slice(0, 30000))) return {{ status: 429 }};
    if (r.status >= 400) return {{ status: r.status }};
    return {{ status: r.status, ...FI([h, url]) }};
  }} catch (e) {{ return {{ status: 0 }}; }}
}}"""


PARSE_FICHE_JS = f"""(args) => {{ const FI = {FICHE_JS}; return FI(args); }}"""
JS_PAR_GENRE = {"next": FETCH_NEXT_JS, "liste": FETCH_LISTE_JS, "fiche": FETCH_FICHE_JS, "leparking": LEPARKING_JS}
EXTRA_ONGLETS: dict[str, str] = {}
# Sites qui refusent les connexions venant de serveurs (hébergeurs) : ignorés en mode « http »
HORS_LIGNE_HTTP = {"zoomcar"}


def _marquer_miroirs(cartes: list[dict]) -> list[dict]:
    """Annonce qui n'est qu'une copie d'une autre plateforme (L'argus reprend Leboncoin) : on l'affiche
    comme une annonce Leboncoin (sa fiche L'argus donne description et équipements), lien vers l'original."""
    out = []
    for c in cartes:
        if c.get("_miroir"):
            c["plateforme"] = c["_miroir"]
            if c.get("_miroir_lien"):
                c["lien_origine"] = c["_miroir_lien"]
            out.append(c)
    return out


# Sites capables de chercher « toutes marques » (recherche par critères ou équipements seulement)
SANS_MARQUE = {"autoscout24", "leparking"}

class SiteBloque(Exception):
    """Le site demande une vérification anti-robot."""


def sans_accents(s: Any) -> str:
    s = unicodedata.normalize("NFKD", str(s or ""))
    return "".join(c for c in s if not unicodedata.combining(c))


def norm(s: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", sans_accents(s).lower().replace("(tous)", ""))


def slug(s: Any) -> str:
    s = sans_accents(s).lower().replace("(tous)", "")
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def modele_propre(label: str) -> str:
    return re.sub(r"\s*\(tous\)\s*", "", label or "").strip()


CARBURANTS = ["Essence", "Diesel", "Hybride", "Électrique"]
_INDICES_CARBURANT = [  # déduit du titre quand le site ne l'affiche pas (ordre important)
    ("Hybride", r"hybrid|e-?tech|\bhev\b|\bphev\b|\bmhev\b|plug-?in"),
    ("Électrique", r"electrique|electric|\be-?(208|2008|c4|up|golf|tron)\b|\bkwh\b|\bev\b|zoe|ioniq 5"),
    ("Diesel", r"diesel|gazole|\b(blue)?hdi\b|\bdci\b|\btdi\b|\bcrdi\b|\bcdi\b|\bd-?4d\b|multijet|\bjtd|\btdci\b|\bbluehdi\b|\bd\d{3}\b|\b\d{3}d\b|\bsdi\b|\bbluetec\b"),
    ("Essence", r"essence|puretech|\bvti\b|\btce\b|\btsi\b|\btfsi\b|\bthp\b|\bsce\b|ecoboost|\bmpi\b|\bgti\b|\bt-?gdi\b|\bi\d{3}\b"),
]


def carburant_de(*textes: Optional[str]) -> Optional[str]:
    t = sans_accents(" ".join(x for x in textes if x)).lower()
    for nom, rx in _INDICES_CARBURANT:
        if re.search(rx, t):
            return nom
    return None


def carburant_norm(c: Optional[str]) -> Optional[str]:
    if not c:
        return None
    t = sans_accents(c).lower()
    if "hybr" in t: return "Hybride"
    if "elec" in t: return "Électrique"
    if "diesel" in t or "gazole" in t: return "Diesel"
    if "essence" in t or "petrol" in t or "benzin" in t: return "Essence"
    return c


AUDIO = set(OPTIONS_GROUPES.get("Audio premium", []))


def mot_cle(options: list[str]) -> Optional[str]:
    """Option la plus sélective -> mot-clé pour la recherche texte des sites (ordre = détection).
    Plusieurs marques audio cochées = « n'importe laquelle » : aucune n'est envoyée comme mot-clé."""
    if len(AUDIO.intersection(options)) > 1:
        options = [o for o in options if o not in AUDIO]
    for opt in OPTIONS_PREMIUM:
        if opt in options and opt in MOTS_CLES_SITE:
            return MOTS_CLES_SITE[opt]
    return None


class TTLCache:
    def __init__(self, ttl: float, maxsize: int = 5000):
        self.ttl, self.maxsize, self.d = ttl, maxsize, {}

    def get(self, k):
        v = self.d.get(k)
        return v[1] if v and time.time() - v[0] < self.ttl else None

    def set(self, k, val):
        if len(self.d) >= self.maxsize:
            for key in sorted(self.d, key=lambda x: self.d[x][0])[: self.maxsize // 5]:
                self.d.pop(key, None)
        self.d[k] = (time.time(), val)


def carte(source: str, **kw) -> dict:
    base = dict(source=source, titre="", prix=None, annee=None, kilometrage=None, lien="", image=None, date=None,
                ville=None, carburant=None, boite=None, puissance_ch=None, type_vendeur=None,
                extrait=None, verifiee=False, merguez=False, motifs_merguez=[], options=[], plateforme=None)
    base.update({k: v for k, v in kw.items() if k in base})
    return base


def publique(c: dict) -> dict:
    return {k: v for k, v in c.items() if not k.startswith("_")}


_MOTEURS = (r"puretech|e-?thp|thp|vti|e-?hdi|bluehdi|hdi|tce|blue ?dci|dci|sce|tsi|tdi|tfsi|ecoboost|ecoblue|tdci|"
            r"mpi|t-?gdi|crdi|multijet|jtdm?|skyactiv-?[gdx]|d-?4d|vvt-?i|cdti|ecotec|mhev|e-?tense")


def puissance_de(*textes: Optional[str]) -> Optional[int]:
    """Puissance en chevaux lue dans le titre / la version / la description (« 130 ch », « PureTech 110 »).
    Les « CV » seuls sont souvent des chevaux fiscaux (5 CV) : ignorés sous 40."""
    t = sans_accents(" ".join(x for x in textes if x)).lower()
    m = re.search(r"\b(\d{2,3})\s?(?:ch|hp|chevaux|cv din)\b", t)
    if m and 40 <= int(m.group(1)) <= 800:
        return int(m.group(1))
    m = re.search(r"\b(?:" + _MOTEURS + r")\s?(\d{2,3})\b", t)
    if m and 40 <= int(m.group(1)) <= 800:
        return int(m.group(1))
    m = re.search(r"\b\d[.,]\d\s(\d{2,3})\b(?!\s?(?:km|000|€|eur))", t)   # « 1.2 100 S&S »
    if m and 50 <= int(m.group(1)) <= 400:
        return int(m.group(1))
    m = re.search(r"\b(\d{3})h\b", t)                                    # hybrides Toyota « 116h »
    if m and 70 <= int(m.group(1)) <= 400:
        return int(m.group(1))
    m = re.search(r"\b(\d{2,3})\s?cv\b", t)
    if m and 40 <= int(m.group(1)) <= 800:
        return int(m.group(1))
    return None


def verifier(c: dict, description: Optional[str], equipements=None, accident=None, dommages=None) -> None:
    autres = [x for x in (c.get("_sous_titre"), f"boite {c['boite']}" if c.get("boite") else None) if x]
    motifs, options = analyser(c["titre"], description, equipements, accident, dommages, autres)
    c.update(merguez=bool(motifs), motifs_merguez=motifs, options=options, verifiee=description is not None,
             extrait=(re.sub(r"\s+", " ", description)[:220] if description else None))
    if not c.get("puissance_ch"):
        c["puissance_ch"] = puissance_de(c.get("titre"), c.get("_sous_titre"), (description or "")[:3000])


# --------------------------------------------------------------------------- #
# Description des sites « HTML » (extraction générique par cartes)
# --------------------------------------------------------------------------- #
class Site:
    def __init__(self, cle: str, nom: str, origine: str, accueil: str, lien_re: str,
                 url: Callable[[dict, int, bool], str], par_page: int, pages_max: int = 50,
                 tri_prix_local: bool = False, filtre_modele_local: bool = False,
                 differe: bool = False, concurrence: int = 6, rythme: float = 0.0):
        self.cle, self.nom, self.origine, self.accueil = cle, nom, origine, accueil
        self.lien_re, self.url, self.par_page, self.pages_max = lien_re, url, par_page, pages_max
        self.tri_prix_local, self.filtre_modele_local = tri_prix_local, filtre_modele_local
        # differe : fiches lues après l'affichage, doucement (sites qui bloquent les rafales)
        self.differe, self.concurrence, self.rythme = differe, concurrence, rythme


def _un_carburant(q: dict) -> Optional[str]:
    c = q.get("carburants") or []
    return c[0] if len(c) == 1 else None


def _paruvendu(q: dict, page: int, repli: bool) -> str:
    p = {}
    if q.get("prix_max"): p["px1"] = q["prix_max"]
    if q.get("km_max"): p["km1"] = q["km_max"]
    if q.get("annee_min"): p["a0"] = q["annee_min"]
    if q.get("annee_max"): p["a1"] = q["annee_max"]
    kw = mot_cle(q.get("options") or [])
    if repli:  # modèle non reconnu dans l'URL : recherche texte « marque modèle »
        p.update(r="VO", fulltext=" ".join(x for x in (q["marque_label"], modele_propre(q["modele_label"]), kw) if x))
        base = "https://www.paruvendu.fr/auto-moto/listefo/default/default"
    else:
        if kw: p["fulltext"] = kw
        m = slug(modele_propre(q["modele_label"]))
        # tri côté site (le tri « prix croissant » de ParuVendu met en tête les annonces sans prix : pas utilisé)
        if q.get("tri") == "prix_desc": p.update(tri="prix", ord="desc")
        elif q.get("tri") == "date": p.update(tri="flagTeteListe", ord="desc")
        base = f"https://www.paruvendu.fr/a/voiture-occasion/{slug(q['marque_label'])}/" + (f"{m}/" if m else "")
    if page > 1: p["p"] = page
    return base + ("?" + urlencode(p) if p else "")


def _largus(q: dict, page: int, repli: bool) -> str:
    p = {}
    if q.get("prix_max"): p["price_max"] = int(q["prix_max"]) * 100  # le site attend des centimes
    if q.get("km_max"): p["mileage_max"] = q["km_max"]
    if q.get("annee_min"): p["year_min"] = q["annee_min"]
    if q.get("annee_max"): p["year_max"] = q["annee_max"]
    c = _un_carburant(q)
    if c: p["energy"] = {"Électrique": "electrique"}.get(c, slug(c))
    kw = mot_cle(q.get("options") or [])
    m = slug(modele_propre(q["modele_label"]))
    if repli and m:
        kw = " ".join(x for x in (modele_propre(q["modele_label"]), kw) if x)
        m = ""
    if kw: p["q"] = kw
    t = {"prix": ("price", "asc"), "prix_desc": ("price", "desc"), "date": ("last_activity_at", "desc")}.get(q.get("tri") or "")
    if t: p.update(sort=t[0], order=t[1])
    if page > 1: p["currentpage"] = page
    base = f"https://occasion.largus.fr/auto/{slug(q['marque_label'])}/" + (f"{m}/" if m else "")
    return base + ("?" + urlencode(p) if p else "")


def _autosphere(q: dict, page: int, repli: bool) -> str:
    m = "" if repli else slug(modele_propre(q["modele_label"]))
    return f"https://www.autosphere.fr/voiture-occasion/{slug(q['marque_label'])}" + (f"/{m}" if m else "") + ".html"


def _zoomcar(q: dict, page: int, repli: bool) -> str:  # ex-Ouest-France Auto
    m = "" if repli else slug(modele_propre(q["modele_label"]))
    return f"https://zoomcar.fr/{slug(q['marque_label'])}" + (f"-{m}" if m else "") + ".html" + (f"?ps={page}" if page > 1 else "")


def _autoselection(q: dict, page: int, repli: bool) -> str:
    p = {}
    if q.get("prix_max"): p["price_max"] = q["prix_max"]
    if q.get("km_max"): p["km_max"] = q["km_max"]
    if q.get("annee_min"): p["annee_min"] = q["annee_min"]
    if q.get("annee_max"): p["annee_max"] = q["annee_max"]
    c = _un_carburant(q)
    if c: p["energie"] = {"Électrique": "electrique"}.get(c, slug(c))
    if "Boîte automatique" in (q.get("options") or []): p["boite"] = "automatique"
    t = {"prix": "prix-asc", "prix_desc": "prix-desc"}.get(q.get("tri") or "")   # défaut du site : plus récentes
    if t: p["tri"] = t
    if page > 1: p["page"] = page
    m = "" if repli else slug(modele_propre(q["modele_label"]))
    return f"https://www.auto-selection.com/voiture-occasion/{slug(q['marque_label'])}" + (f"/{m}" if m else "") + ("?" + urlencode(p) if p else "")


def _renew(q: dict, page: int, repli: bool) -> str:
    p = {"brand.label.raw": sans_accents(q["marque_label"]).upper()}
    m = modele_propre(q["modele_label"])
    if m and not repli: p["model.label.raw"] = sans_accents(m).upper()
    if q.get("km_max"): p["mileage"] = f"0-{q['km_max']}"
    c = _un_carburant(q)
    if c: p["energy.groupLabel.raw"] = {"Électrique": "electrique", "Hybride": "hybride "}.get(c, slug(c))
    t = {"prix": ("prices.customerDisplayPrice", "+"), "prix_desc": ("prices.customerDisplayPrice", "-"),
         "date": ("publicationDate", "-")}.get(q.get("tri") or "")
    if t: p.update(sortKey=t[0], sortOrder=t[1])
    if page > 1: p["page"] = page
    return "https://fr.renew.auto/achat-vehicules-occasions.html?" + urlencode(p)


SITES: dict[str, Site] = {
    "paruvendu": Site("paruvendu", "ParuVendu", "https://www.paruvendu.fr", "/",
                      r"/a/voiture-occasion/[^/]+/[^/]+/\d{8,}[A-Z0-9]+$", _paruvendu, 25,
                      differe=True, concurrence=1, rythme=1.6),
    "largus": Site("largus", "L'argus", "https://occasion.largus.fr", "/",
                   r"/auto/annonce-[0-9a-f-]{36}-", _largus, 24),
    "zoomcar": Site("zoomcar", "Zoomcar (Ouest-France Auto)", "https://zoomcar.fr", "/",
                    r"zoomcar\.fr/[a-z0-9-]+-\d{7,9}\.html$", _zoomcar, 20),
    "autoselection": Site("autoselection", "Auto-Sélection", "https://www.auto-selection.com", "/",
                          r"/voiture-occasion/[a-z0-9-]+/[a-z0-9-]+/[a-z0-9-]{6,}$", _autoselection, 20,
                          concurrence=3, rythme=0.3),
    "renew": Site("renew", "Renew", "https://fr.renew.auto", "/",
                  r"details\.html\?productId=", _renew, 23),
    "autosphere": Site("autosphere", "Autosphere", "https://www.autosphere.fr", "/",
                       r"/fiche[^/]*/auto-occasion-[a-z0-9-]+-\d{3,}$", _autosphere, 22, pages_max=1),
}
TOUTES_SOURCES = ["autoscout24", "leparking", *SITES]
PLATEFORMES_EXCLUES = {"autohero.com", "spoticar.fr"}
# Régions : identifiant LeParking (filtre côté site) + départements (filtre local par code postal)
REGIONS = {
    "auvergne-rhone-alpes": ("Auvergne-Rhône-Alpes", [1269], "01 03 07 15 26 38 42 43 63 69 73 74"),
    "bourgogne-franche-comte": ("Bourgogne-Franche-Comté", [1270], "21 25 39 58 70 71 89 90"),
    "bretagne": ("Bretagne", [14], "22 29 35 56"),
    "centre-val-de-loire": ("Centre-Val de Loire", [1271], "18 28 36 37 41 45"),
    "corse": ("Corse", [29], "20"),
    "grand-est": ("Grand Est", [1276], "08 10 51 52 54 55 57 67 68 88"),
    "hauts-de-france": ("Hauts-de-France", [1272], "02 59 60 62 80"),
    "ile-de-france": ("Île-de-France", [47], "75 77 78 91 92 93 94 95"),
    "normandie": ("Normandie", [1274], "14 27 50 61 76"),
    "nouvelle-aquitaine": ("Nouvelle-Aquitaine", [1273], "16 17 19 23 24 33 40 47 64 79 86 87"),
    "occitanie": ("Occitanie", [1268], "09 11 12 30 31 32 34 46 48 65 66 81 82"),
    "pays-de-la-loire": ("Pays de la Loire", [89], "44 49 53 72 85"),
    "provence-alpes-cote-d-azur": ("Provence-Alpes-Côte d'Azur", [92], "04 05 06 13 83 84"),
    "outre-mer": ("Outre-mer", [39, 78, 42, 94, 79], "971 972 973 974 976"),
}
DEPARTEMENTS = dict(x.split(":") for x in (
    "01:Ain 02:Aisne 03:Allier 04:Alpes-de-Haute-Provence 05:Hautes-Alpes 06:Alpes-Maritimes 07:Ardèche 08:Ardennes "
    "09:Ariège 10:Aube 11:Aude 12:Aveyron 13:Bouches-du-Rhône 14:Calvados 15:Cantal 16:Charente 17:Charente-Maritime "
    "18:Cher 19:Corrèze 20:Corse 21:Côte-d'Or 22:Côtes-d'Armor 23:Creuse 24:Dordogne 25:Doubs 26:Drôme 27:Eure "
    "28:Eure-et-Loir 29:Finistère 30:Gard 31:Haute-Garonne 32:Gers 33:Gironde 34:Hérault 35:Ille-et-Vilaine 36:Indre "
    "37:Indre-et-Loire 38:Isère 39:Jura 40:Landes 41:Loir-et-Cher 42:Loire 43:Haute-Loire 44:Loire-Atlantique 45:Loiret "
    "46:Lot 47:Lot-et-Garonne 48:Lozère 49:Maine-et-Loire 50:Manche 51:Marne 52:Haute-Marne 53:Mayenne "
    "54:Meurthe-et-Moselle 55:Meuse 56:Morbihan 57:Moselle 58:Nièvre 59:Nord 60:Oise 61:Orne 62:Pas-de-Calais "
    "63:Puy-de-Dôme 64:Pyrénées-Atlantiques 65:Hautes-Pyrénées 66:Pyrénées-Orientales 67:Bas-Rhin 68:Haut-Rhin "
    "69:Rhône 70:Haute-Saône 71:Saône-et-Loire 72:Sarthe 73:Savoie 74:Haute-Savoie 75:Paris 76:Seine-Maritime "
    "77:Seine-et-Marne 78:Yvelines 79:Deux-Sèvres 80:Somme 81:Tarn 82:Tarn-et-Garonne 83:Var 84:Vaucluse 85:Vendée "
    "86:Vienne 87:Haute-Vienne 88:Vosges 89:Yonne 90:Territoire-de-Belfort 91:Essonne 92:Hauts-de-Seine "
    "93:Seine-Saint-Denis 94:Val-de-Marne 95:Val-d'Oise 971:Guadeloupe 972:Martinique 973:Guyane 974:Réunion "
    "976:Mayotte").split(" "))


def departement(cp) -> Optional[str]:
    cp = re.sub(r"\D", "", str(cp or ""))
    if len(cp) != 5:
        return None
    return cp[:3] if cp.startswith("97") else cp[:2]


def dans_region(cp, region: Optional[str], dep: Optional[str] = None) -> bool:
    """Sans région choisie : tout passe. Avec : seulement les codes postaux de la région (lieu inconnu = exclu)."""
    if not region or region not in REGIONS:
        return True
    d = dep or departement(cp)
    return bool(d) and d in REGIONS[region][2].split()


def _nom_lieu(t: str) -> str:
    t = (t or "").replace("œ", "oe").replace("Œ", "OE").replace("æ", "ae").replace("Æ", "AE")
    t = re.sub(r"[^a-z0-9]+", " ", sans_accents(t).lower()).strip()
    return re.sub(r"\bst\b", "saint", re.sub(r"\bste\b", "sainte", t))


_COMMUNES: Optional[dict] = None
_DEP_PAR_NOM = {_nom_lieu(v): k for k, v in DEPARTEMENTS.items()}
_DEP_PAR_NOM.update({"corse du sud": "20", "haute corse": "20", "reunion": "974", "la reunion": "974"})
_PAS_UNE_VILLE = set("renault dacia peugeot citroen ds opel fiat nissan toyota volkswagen vw audi bmw mercedes ford kia "
                     "hyundai skoda seat cupra mini volvo jeep alfa romeo mazda suzuki honda mg byd tesla groupe garage "
                     "auto autos automobile automobiles occasion occasions centre agence concession sas sarl site "
                     "garantie mois annexe potentiellement voir details les la le des du de sur".split())


def commune_dep(nom: str) -> Optional[str]:
    """Département d'une commune (la plus peuplée de ce nom), d'après la table Etalab embarquée."""
    global _COMMUNES
    if _COMMUNES is None:
        try:
            _COMMUNES = json.loads(Path(__file__).with_name("communes.json").read_text(encoding="utf-8"))
        except Exception:
            _COMMUNES = {}
    return _COMMUNES.get(_nom_lieu(nom))


def ville_dans(texte: str) -> tuple[Optional[str], Optional[str]]:
    """Cherche une commune dans un libellé (« RENAULT ISTRES - GROUPE AUTOSPHERE » -> Istres)."""
    for bout in re.split(r"\s[-–|]\s|,", texte or ""):
        mots = _nom_lieu(bout).split()
        for n in range(min(len(mots), 6), 0, -1):          # suites de mots, les plus longues d'abord
            for i in range(len(mots) - n + 1):
                if mots[i] in _PAS_UNE_VILLE or mots[i + n - 1] in _PAS_UNE_VILLE:
                    continue                               # « RENAULT », « GROUPE »… ne commencent/finissent pas une ville
                cand = " ".join(mots[i:i + n])
                if len(cand) >= 3 and (d := commune_dep(cand)):
                    return cand.title(), d
    return None, None


def localiser(texte: str, site: str) -> tuple[Optional[str], Optional[str]]:
    """(ville, département) depuis le texte d'une carte de liste. Formats rencontrés :
    ParuVendu « Blois (41000) », L'argus « Chassieu (Rhône) », Auto-Sélection « Bethune | ( | 62 | ) » ou
    « 63500 | ( | LE | ) », Autosphere : ville seule après la boîte, Renew : nom de la concession."""
    P = [p.strip() for p in (texte or "").split(" | ")]
    for k, p in enumerate(P):
        m = re.match(r"^(.{2,50}?)\s*\((\d{5})\)$", p)                       # Blois (41000)
        if m and departement(m.group(2)):
            return m.group(1), departement(m.group(2))
        m = re.match(r"^(.{2,50}?)\s*\(\s*(2[AB]|\d{2,3})\s*\)$", p)           # Bethune (62)
        if m and (m.group(2) in DEPARTEMENTS or m.group(2) in ("2A", "2B")):
            return m.group(1), "20" if m.group(2) in ("2A", "2B") else m.group(2)
        m = re.match(r"^(.{2,50}?)\s*\(([^()\d]{3,30})\)$", p)                  # Chassieu (Rhône)
        if m and (d := _DEP_PAR_NOM.get(_nom_lieu(m.group(2)))):
            return m.group(1), d
        if p == "(" and 0 < k and k + 2 < len(P) and P[k + 2] == ")":             # Bethune | ( | 62 | )
            avant, dedans = P[k - 1], P[k + 1]
            if re.match(r"^\d{5}$", avant) and departement(avant):
                return None, departement(avant)
            if dedans in DEPARTEMENTS or dedans in ("2A", "2B"):
                return avant, "20" if dedans in ("2A", "2B") else dedans
    if site == "autosphere":           # ville seule, juste après la boîte de vitesses
        i = next((k for k, p in enumerate(P) if re.match(r"^(manuelle|automatique)$", p, re.I)), -1)
        if 0 <= i < len(P) - 1 and (d := commune_dep(P[i + 1])):
            return P[i + 1], d
    if site == "renew":                # « RENAULT ISTRES - GROUPE AUTOSPHERE » après « voir les détails »
        i = next((k for k, p in enumerate(P) if re.match(r"^voir les d[ée]tails$", p, re.I)), -1)
        if 0 <= i < len(P) - 1:
            return ville_dans(P[i + 1])
    return None, None


def lieu(ville, cp, dep: Optional[str] = None) -> Optional[str]:
    d = dep or departement(cp)
    if not d:
        return ville or None
    return f"{ville} ({d})" if ville else f"{DEPARTEMENTS.get(d, d)} ({d})"


LEPARKING_ENERGIE = {"Essence": "3", "Diesel": "1", "Hybride": "7", "Électrique": "2"}
LEPARKING_TRI = {"prix": "prix_croissant", "prix_desc": "prix_decroissant", "date": "date"}
PLATEFORMES = {"leboncoin.fr": "Leboncoin", "lacentrale.fr": "La Centrale", "autoscout24.fr": "AutoScout24",
               "paruvendu.fr": "ParuVendu", "autohero.com": "Autohero", "spoticar.fr": "Spoticar",
               "aramisauto.com": "Aramis Auto", "autosphere.fr": "Autosphere", "zoomcar.fr": "Zoomcar",
               "gemy.fr": "Gemy", "used-cars.ayvens.com": "Ayvens", "ev-market.fr": "EV Market",
               "renew.auto": "Renew", "auto-selection.com": "Auto-Sélection", "capcar.fr": "Capcar"}


# --------------------------------------------------------------------------- #
# Moteur (thread dédié + boucle asyncio + navigateur persistant)
# --------------------------------------------------------------------------- #
class Moteur:
    def __init__(self, visible: bool = False, concurrence: int = 6, mode: Optional[str] = None):
        """mode « http » (défaut, et en ligne) : requêtes directes, sans navigateur.
        mode « navigateur » : Chrome piloté par Playwright (onglets par site), pour un usage sur PC."""
        self.visible, self.concurrence = visible, concurrence
        self.mode = mode or os.environ.get("AUTORADAR_MODE") or ("navigateur" if visible else "http")
        if self.mode == "navigateur" and async_playwright is None:
            self.mode = "http"
        self.loop = asyncio.new_event_loop()
        threading.Thread(target=self.loop.run_forever, daemon=True, name="moteur").start()
        self.ctx: Optional[BrowserContext] = None
        self.onglets: dict[str, Page] = {}
        self.http = None
        if self.mode == "http":
            from transport_http import TransportHttp
            self.http = TransportHttp(LEPARKING)
        self.sources = [s for s in TOUTES_SOURCES if not (self.mode == "http" and s in HORS_LIGNE_HTTP)]
        self.statut: dict[str, str] = {s: ("ok" if self.http else "inactif") for s in self.sources}
        self.navigateur = "requêtes directes (sans navigateur)" if self.http else "?"
        self._pret = None
        self._page_vide: Optional[Page] = None
        self._verrous: dict[str, asyncio.Lock] = {}
        self._sems: dict[str, asyncio.Semaphore] = {}
        self.cache_pages = TTLCache(600)
        self.cache_fiches = TTLCache(6 * 3600, 20000)   # une fiche lue n'est pas relue avant 6 h
        self.attente: dict[str, tuple[str, dict]] = {}   # lien -> (source, carte) : fiches à lire après affichage
        self.frein: dict[str, float] = {}                 # source -> heure de fin de la pause anti-blocage
        self.statut_extra: dict[str, str] = {}
        try:
            self.catalogue = json.loads(CACHE_CATALOGUE.read_text(encoding="utf-8"))
        except Exception:
            self.catalogue = {"marques": None, "modeles": {}}
        self.catalogue.setdefault("modeles", {})

    # -- API synchrone (appelée depuis les threads du serveur HTTP) --
    def run(self, coro, timeout: float = 120):
        return asyncio.run_coroutine_threadsafe(coro, self.loop).result(timeout)

    def prechauffer(self) -> None:
        if self.http:
            return

        async def tout():
            await asyncio.gather(*(self._onglet(s) for s in TOUTES_SOURCES), return_exceptions=True)
        asyncio.run_coroutine_threadsafe(tout(), self.loop)

    def arreter(self) -> None:
        try:
            self.run(self._arreter(), timeout=10)
        except Exception:
            pass

    async def _arreter(self) -> None:
        if self.http:
            await self.http.fermer()
        if self.ctx:
            await self.ctx.close()

    def _sauver_catalogue(self) -> None:
        try:
            CACHE_CATALOGUE.write_text(json.dumps(self.catalogue, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass

    async def _demarrer(self) -> None:
        if self._pret is None:
            self._pret = asyncio.ensure_future(self._lancer())
        await self._pret

    async def _lancer(self) -> None:
        self._pw = await async_playwright().start()
        # Chrome « avec fenêtre » passe beaucoup mieux Cloudflare & co que le mode sans fenêtre.
        # Par défaut sur un PC : fenêtre placée hors de l'écran (invisible). Sur un serveur sans écran : sans fenêtre.
        ecran = sys.platform in ("win32", "darwin") or bool(os.environ.get("DISPLAY"))
        sans_fenetre = os.environ.get("AUTORADAR_HEADLESS") == "1" or (not self.visible and not ecran)
        args = ["--disable-blink-features=AutomationControlled", "--blink-settings=imagesEnabled=false"]
        if not sans_fenetre and not self.visible:
            args += ["--window-position=-2600,-2600", "--window-size=1280,800"]
        fenetre = "visible" if self.visible else ("sans fenêtre" if sans_fenetre else "fenêtre cachée")
        kw = dict(headless=sans_fenetre, locale="fr-FR", timezone_id="Europe/Paris", bypass_csp=True,
                  viewport={"width": 1366, "height": 850}, args=args)
        PROFIL.mkdir(parents=True, exist_ok=True)
        try:  # le vrai Google Chrome installé passe mieux les anti-robots
            self.ctx = await self._pw.chromium.launch_persistent_context(str(PROFIL), channel="chrome", **kw)
            self.navigateur = f"Google Chrome ({fenetre})"
        except Exception:
            self.ctx = await self._pw.chromium.launch_persistent_context(str(PROFIL), **kw)
            self.navigateur = f"Chromium ({fenetre})"
        await self.ctx.add_init_script(as24.STEALTH_JS)
        p = self.ctx.pages[0] if self.ctx.pages else await self.ctx.new_page()
        ua = await p.evaluate("navigator.userAgent")
        if "Headless" in ua:  # sans fenêtre, Chrome s'annonce « HeadlessChrome » : on corrige
            ua = ua.replace("HeadlessChrome", "Chrome")
            await self.ctx.set_extra_http_headers({"User-Agent": ua, "Accept-Language": "fr-FR,fr;q=0.9"})
            await self.ctx.add_init_script(f"Object.defineProperty(navigator,'userAgent',{{get:()=>{json.dumps(ua)}}});")
        self._page_vide = p

    async def _onglet(self, source: str, forcer: bool = False) -> Page:
        await self._demarrer()
        async with self._verrous.setdefault(source, asyncio.Lock()):
            page = self.onglets.get(source)
            statut = self.statut if source in self.statut else self.statut_extra
            if page and not page.is_closed() and not forcer and statut.get(source) == "ok":
                return page
            statut[source] = "connexion"
            if not page or page.is_closed():
                page, self._page_vide = (self._page_vide, None) if self._page_vide else (await self.ctx.new_page(), None)
                self.onglets[source] = page
            url = (f"{AS24}/lst?atype=C&cy=F" if source == "autoscout24" else f"{LEPARKING}/" if source == "leparking"
                   else EXTRA_ONGLETS[source] if source in EXTRA_ONGLETS else SITES[source].origine + SITES[source].accueil)
            try:
                resp = await page.goto(url, wait_until="domcontentloaded", timeout=45_000)
            except Exception:
                statut[source] = "erreur"
                raise
            # Page de vérification (Cloudflare « Just a moment… », etc.) : on laisse le navigateur la passer
            defi = "/just a moment|un instant|attention required|v[ée]rification|checking your browser/i.test(document.title)"
            resolu = False
            try:
                if await page.evaluate(defi):
                    await page.wait_for_function(f"!({defi})", timeout=25_000)
                    await page.wait_for_load_state("domcontentloaded")
                    resolu = True
            except Exception:
                pass
            await asyncio.sleep(random.uniform(0.5, 1.2))
            try:  # bandeau cookies : on attend au plus 2,5 s qu'il apparaisse
                btn = page.locator('[data-testid="as24-cmp-accept-all-button"], #didomi-notice-agree-button, '
                                   '#onetrust-accept-btn-handler, button:has-text("Tout accepter"), button:has-text("Accepter et fermer")')
                await btn.first.wait_for(state="visible", timeout=2500)
                await btn.first.click(timeout=1500)
            except Exception:
                pass
            ok = resolu or (resp is not None and resp.status < 400)
            try:
                ok = ok and not await page.evaluate(defi)
            except Exception:
                pass
            if source == "autoscout24":
                ok = ok and await page.locator("script#__NEXT_DATA__").count() > 0
            statut[source] = "ok" if ok else "bloque"
            if not ok:
                raise SiteBloque(source)
            return page

    def _sem(self, source: str) -> asyncio.Semaphore:
        n = SITES[source].concurrence if source in SITES else 2 if source in EXTRA_ONGLETS else self.concurrence
        return self._sems.setdefault(source, asyncio.Semaphore(n))

    def freine(self, source: str) -> bool:
        return self.frein.get(source, 0) > time.time()

    async def _eval(self, source: str, genre: str, arg: Any, cle_cache: str) -> Optional[dict]:
        """Récupère + analyse une page (genre : next / liste / fiche / leparking), avec reprises et cache.
        Mode navigateur : fetch() + extraction dans l'onglet du site. Mode http : curl_cffi + parseurs.py."""
        cached = self.cache_pages.get(cle_cache)
        if cached is not None:
            return cached
        if self.freine(source):
            raise SiteBloque(source)
        page = None if self.http else await self._onglet(source)
        rythme = SITES[source].rythme if source in SITES else 0.4 if source in EXTRA_ONGLETS else 0
        async with self._sem(source):
            for essai in range(3):
                if rythme:
                    await asyncio.sleep(rythme * random.uniform(0.8, 1.3))
                if self.http:
                    res = await self.http.appel(source, genre, arg)
                else:
                    try:
                        res = await page.evaluate(JS_PAR_GENRE[genre], arg)
                    except Exception:
                        res = {"status": 0}
                st = res.get("status", 0)
                if st == 429 and rythme:          # le site freine : on arrête de le solliciter 15 min
                    self.frein[source] = time.time() + 900
                    raise SiteBloque(source)
                if st in (403, 429, 503):
                    if essai == 2:
                        (self.statut if source in self.statut else self.statut_extra)[source] = "bloque"
                        raise SiteBloque(source)
                    await asyncio.sleep(1.5 * (essai + 1) + random.random())
                    continue
                if st == 0:
                    await asyncio.sleep(1)
                    if not self.http:
                        page = await self._onglet(source, forcer=True)
                    continue
                if self.http and source in self.statut:
                    self.statut[source] = "ok"
                if genre != "next":       # JSON bruts (centaines de Ko) : on ne garde que ce qui en est extrait
                    self.cache_pages.set(cle_cache, res)
                return res
        return None

    # ------------------------------------------------------------------ catalogue (AutoScout24)
    async def _as24_json(self, url: str) -> Optional[dict]:
        res = await self._eval("autoscout24", "next", url, "json:" + url)
        return json.loads(res["json"]) if res and res.get("json") else None

    async def marques(self) -> list[dict]:
        if self.catalogue.get("marques"):
            return self.catalogue["marques"]
        data = await self._as24_json(f"{AS24}/lst?atype=C&cy=F")
        tx = as24._find_key(data, "taxonomy", dict) or {}
        tops = {str(x.get("value")) for x in tx.get("topMakes") or [] if isinstance(x, dict)}
        out = [{"id": int(v["value"]), "label": v["label"], "top": str(v["value"]) in tops}
               for v in (tx.get("makes") or {}).values() if isinstance(v, dict)]
        out.sort(key=lambda m: norm(m["label"]))
        self.catalogue["marques"] = out
        self._sauver_catalogue()
        return out

    async def modeles(self, marque_id: int) -> list[dict]:
        k = str(marque_id)
        if k in self.catalogue["modeles"]:
            return self.catalogue["modeles"][k]
        data = await self._as24_json(f"{AS24}/lst?atype=C&cy=F&mmmv={marque_id}|||")
        tx = as24._find_key(data, "taxonomy", dict) or {}
        lignes = [{"cle": f"l:{x['id']}", "label": x["label"]} for x in (tx.get("modelLines") or {}).get(k, [])]
        modeles = [{"cle": f"m:{x['value']}", "label": x["label"]} for x in (tx.get("models") or {}).get(k, [])]
        nat = lambda s: [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", s["label"])]
        out = sorted(lignes, key=nat) + sorted(modeles, key=nat)
        self.catalogue["modeles"][k] = out
        self._sauver_catalogue()
        return out

    # ------------------------------------------------------------------ recherche
    async def rechercher(self, source: str, q: dict) -> dict:
        t0 = time.perf_counter()
        if source in TOUTES_SOURCES and source not in self.sources:
            return {"source": source, "erreur": "indisponible", "annonces": []}
        if not q.get("marque_id") and source not in SANS_MARQUE:    # ces sites exigent une marque dans l'adresse
            return {"source": source, "annonces": [], "suite": False, "total_site": 0, "page": 1}
        try:
            if source == "autoscout24":
                res = await self._as24(q)
            elif source == "leparking":
                res = await self._leparking(q)
            elif source in SITES:
                res = await self._html(SITES[source], q)
            else:
                return {"source": source, "erreur": "source inconnue", "annonces": []}
        except SiteBloque:
            return {"source": source, "erreur": "bloque", "annonces": []}
        except Exception as e:
            return {"source": source, "erreur": f"{type(e).__name__}", "annonces": []}
        res["duree"] = round(time.perf_counter() - t0, 2)
        res["source"] = source
        res["annonces"] = [publique(c) for c in res.get("annonces", [])]
        if len(self.attente) > 5000:   # on oublie les plus anciennes cartes en attente
            for k in list(self.attente)[:1000]:
                self.attente.pop(k, None)
        if self.freine(source):
            res["freine"] = True
        return res

    # ------------------------------------------------------------------ fiches différées
    async def fiches(self, source: str, liens: list[str]) -> dict:
        """Lit (doucement) les fiches d'annonces déjà affichées et renvoie les mises à jour."""
        cartes = [self.attente[l][1] for l in liens if l in self.attente and self.attente[l][0] == source]
        if source == "leparking":
            if "largus" not in self.sources:
                return {"maj": []}
            await self._verifier_toutes(cartes, self._via_largus)
            for c in cartes:
                self.attente.pop(c["lien"], None)
            return {"maj": [publique(c) for c in cartes], "freine": self.freine("largus")}
        if source == "autoscout24":
            await self._verifier_toutes(cartes, self._lire_as24)
        elif source in SITES:
            await self._verifier_toutes(cartes, self._lecteur_fiche(SITES[source]))
        else:
            return {"maj": []}
        _marquer_miroirs(cartes)
        freine = self.freine(source)
        for c in cartes:   # une fiche non lue parce que le site freine pourra être relue plus tard
            if c.get("verifiee") or not freine:
                self.attente.pop(c["lien"], None)
        return {"maj": [publique(c) for c in cartes if c.get("verifiee") or not freine], "freine": freine}

    async def _via_largus(self, c: dict) -> Optional[dict]:
        """Annonce Leboncoin / La Centrale vue sur LeParking : L'argus republie une partie de ces annonces avec
        leur description. On la cherche (même prix exact, même année, km proche), puis on lit sa fiche."""
        q, site = c.get("_q") or {}, SITES["largus"]
        prix, km, annee = c.get("prix"), c.get("kilometrage"), c.get("annee")
        if not (q.get("marque_label") and prix and km and annee):
            return None
        m = slug(modele_propre(q.get("modele_label") or ""))
        url = (f"{site.origine}/auto/{slug(q['marque_label'])}/" + (f"{m}/" if m else "") + "?" +
               urlencode({"price_min": prix * 100, "price_max": prix * 100, "year_min": annee, "year_max": annee,
                          "mileage_min": max(0, km - 1500), "mileage_max": km + 1500}))
        res = await self._eval("largus", "liste", [url, site.lien_re, q["marque_label"]], "liste:" + url) or {}
        b = next((b for b in res.get("annonces") or [] if b.get("prix") == prix and b.get("annee") in (None, annee)
                  and (b.get("km") is None or abs(b["km"] - km) <= 1500)), None)
        if not b:
            return None
        f = await self._lecteur_fiche(site)({"lien": b["lien"]})
        if not f or f.get("miroir") != c.get("plateforme"):   # ce n'est pas la même annonce
            return None
        return {"description": f.get("description") or "", "equipements": f.get("equipements") or [],
                "image": f.get("image"), "date": f.get("date"), "lien_origine": f.get("miroir_lien")}

    def _lecteur_fiche(self, site: Site):
        async def lire(c):
            r = await self._eval(site.cle, "fiche", c["lien"], "fiche:" + c["lien"])
            if not r or r.get("status", 0) >= 400:
                return None
            return {"description": r.get("description") or "", "equipements": r.get("equipements") or [],
                    "miroir": r.get("miroir"), "miroir_lien": r.get("miroir_lien"), "image": r.get("image"),
                    "date": r.get("date")}
        return lire

    async def _verifier_toutes(self, cartes: list[dict], lire) -> None:
        async def une(c):
            cached = self.cache_fiches.get(c["lien"])
            if cached is None:
                try:
                    cached = await lire(c)
                except Exception:          # site qui freine, page illisible… : l'annonce reste affichée
                    cached = None
                if cached is not None:
                    self.cache_fiches.set(c["lien"], cached)
            c["_miroir"] = (cached or {}).get("miroir")
            c["_miroir_lien"] = (cached or {}).get("miroir_lien")
            if (cached or {}).get("image") and not c.get("image"):   # photo absente de la liste : celle de la fiche
                c["image"] = cached["image"]
            if (cached or {}).get("date") and not c.get("date"):
                c["date"] = cached["date"]
            if (cached or {}).get("lien_origine"):
                c["lien_origine"] = cached["lien_origine"]
            infos = {k: v for k, v in (cached or {}).items() if k in ("description", "equipements", "accident", "dommages")}
            verifier(c, **infos) if cached and cached.get("description") is not None else verifier(c, None)
        await asyncio.gather(*(une(c) for c in cartes))

    async def _as24(self, q: dict) -> dict:
        page = max(1, int(q.get("page") or 1))
        params = {"atype": "C", "cy": "F", "ustate": "N,U", "page": page}
        tri, desc = AS24_TRI.get(q.get("tri") or "pertinence", ("standard", 0))
        params.update(sort=tri, desc=desc)
        mid, mod = q.get("marque_id"), q.get("modele") or ""
        if mid:
            params["mmmv"] = (f"{mid}||{mod[2:]}|" if mod.startswith("l:") else
                              f"{mid}|{mod[2:]}||" if mod.startswith("m:") else f"{mid}|||")
        if q.get("prix_max"): params["priceto"] = q["prix_max"]
        if q.get("km_max"): params["kmto"] = q["km_max"]
        if q.get("puissance_min"):   # le site attend des kW (1 kW = 1,36 ch)
            params.update(powerfrom=int(int(q["puissance_min"]) / 1.36), powertype="kw")
        if q.get("puissance_max"):
            params.update(powerto=int(int(q["puissance_max"]) / 1.36) + 1, powertype="kw")
        if q.get("annee_min"): params["fregfrom"] = q["annee_min"]
        if q.get("annee_max"): params["fregto"] = q["annee_max"]
        fuels = sorted({v for c in q.get("carburants") or [] for v in {"Essence": ["B"], "Diesel": ["D"],
                        "Hybride": ["2", "3"], "Électrique": ["E"]}.get(c, [])})
        if fuels: params["fuel"] = ",".join(fuels)
        eqs = sorted({AS24_EQ[o] for o in q.get("options", []) if o in AS24_EQ})
        url = f"{AS24}/lst?" + urlencode(params, safe="|,") + "".join(f"&eq={e}" for e in eqs)
        data = await self._as24_json(url)
        if data is None:
            return {"annonces": [], "total_site": 0, "page": page, "suite": False, "lien_site": url}
        pp = as24._find_key(data, "pageProps", dict) or data
        cartes = []
        for it in pp.get("listings") or []:
            a = as24.annonce_depuis_recherche(it) if isinstance(it, dict) else None
            if not a:
                continue
            c = carte("AutoScout24", **{k: a.get(k) for k in ("titre", "prix", "annee", "kilometrage", "lien",
                                                               "image", "ville", "carburant", "boite", "puissance_ch")})
            if not dans_region(a.get("code_postal"), q.get("region")):
                continue
            c["ville"] = lieu(a.get("ville"), a.get("code_postal"))
            c["type_vendeur"] = {"Dealer": "Pro", "Private": "Particulier"}.get(a.get("type_vendeur") or "", a.get("type_vendeur"))
            c["_sous_titre"] = a.get("_sous_titre")
            cartes.append(c)

        a_verifier = []
        if q.get("_differe"):          # liste affichée tout de suite, fiches lues ensuite (/api/fiches)
            for c in cartes:
                verifier(c, None)
                self.attente[c["lien"]] = ("autoscout24", c)
                a_verifier.append(c["lien"])
        else:
            await self._verifier_toutes(cartes, self._lire_as24)
        return {"annonces": cartes, "total_site": pp.get("numberOfResults"), "page": page, "a_verifier": a_verifier,
                "suite": page < (pp.get("numberOfPages") or 1), "lien_site": url}

    async def _lire_as24(self, c: dict) -> Optional[dict]:
        res = await self._eval("autoscout24", "next", c["lien"], "json:" + c["lien"])
        data = json.loads(res["json"]) if res and res.get("json") else None
        f = as24.parse_fiche(data) if data else None
        cree = as24._find_key(data, "createdTimestampWithOffset", str) if data else None
        return None if not f else {"description": f["description"] or "", "equipements": f["equipements"],
                                   "accident": f["accident_declare"], "dommages": f["dommages"],
                                   "date": (cree or "")[:10] or None}

    async def _leparking(self, q: dict) -> dict:
        """Agrégateur : une seule requête renvoie des annonces de Leboncoin, La Centrale, etc.
        Les fiches LeParking ne contiennent pas la description : détection sur titre + version.
        Les liens /tools/… (redirections vers le site d'origine) sont interdits aux robots par
        leparking.fr (robots.txt) : ils ne sont suivis que par un clic de l'utilisateur."""
        page = max(1, int(q.get("page") or 1))
        sl = lambda face, lo, hi, cmin, cmax: {"id": f"#range_{face}", "face": face, "min": str(lo), "max": str(hi),
                                                "cur_min": str(cmin), "cur_max": str(cmax)}
        texte = " ".join(x for x in (q.get("marque_label"), modele_propre(q.get("modele_label") or ""),
                                     mot_cle(q.get("options") or [])) if x)
        critere = {"id_pays": ["18"]}  # France
        if q.get("region") in REGIONS:
            critere["id_region"] = [str(i) for i in REGIONS[q["region"]][1]]
        energies = [LEPARKING_ENERGIE[c] for c in q.get("carburants") or [] if c in LEPARKING_ENERGIE]
        if energies:
            critere["id_energie"] = energies
        ctx = {"tab_id": "t0", "cur_page": page, "cur_trie": LEPARKING_TRI.get(q.get("tri") or "", "date"),
               "query": sans_accents(texte).lower(), "critere": critere, "req_num": page,
               "sliders": {"prix": sl("prix", 1, 400000, 1, q.get("prix_max") or 400000),
                           "km": sl("km", 1, 500000, 1, q.get("km_max") or 500000),
                           "millesime": sl("millesime", 1910, 2027, q.get("annee_min") or 1910, q.get("annee_max") or 2027)}}
        res = await self._eval("leparking", "leparking", [ctx], "lp:" + json.dumps(ctx, sort_keys=True)) or {}
        prix_max, km_max, annee_min, annee_max = (int(q[k]) if q.get(k) else None
                                                  for k in ("prix_max", "km_max", "annee_min", "annee_max"))
        carbus = set(q.get("carburants") or [])
        cartes, a_verifier = [], []
        for b in res.get("annonces") or []:
            if (prix_max and b.get("prix") and b["prix"] > prix_max) or (km_max and b.get("km") and b["km"] > km_max) \
                    or (annee_min and b.get("annee") and b["annee"] < annee_min) \
                    or (annee_max and b.get("annee") and b["annee"] > annee_max):
                continue
            carbu = carburant_norm(b.get("carburant")) or carburant_de(b.get("titre"), b.get("version"))
            if carbus and carbu and carbu not in carbus:
                continue
            if b.get("pays") and b["pays"].upper() != "FRANCE":   # annonces étrangères (Allemagne…)
                continue
            if q.get("region") and not dans_region(b.get("cp"), q["region"]):
                continue
            pf = b.get("plateforme") or ""
            if pf in PLATEFORMES_EXCLUES:   # sites retirés du site, même vus via LeParking
                continue
            c = carte("LeParking", titre=b["titre"], prix=b.get("prix"), annee=b.get("annee"), kilometrage=b.get("km"),
                      lien=b["lien"], image=b.get("image"), carburant=carbu, boite=b.get("boite"),
                      type_vendeur=(b.get("vendeur") or "").capitalize() or None,
                      plateforme=PLATEFORMES.get(pf, pf or None))
            c["_sous_titre"] = b.get("version")
            c["date"] = b.get("date")
            c["ville"] = lieu(None, b.get("cp"))
            verifier(c, None)             # LeParking ne publie ni description ni équipements : titre + version
            if c.get("plateforme") in ("Leboncoin", "La Centrale") and c.get("prix") and c.get("kilometrage") and c.get("annee"):
                # L'argus republie une partie de ces annonces avec leur description : on la cherchera après l'affichage
                c["_q"] = {"marque_label": q.get("marque_label") or "", "modele_label": q.get("modele_label") or ""}
                self.attente[c["lien"]] = ("leparking", c)
                a_verifier.append(c["lien"])
            cartes.append(c)
        total = res.get("total")
        return {"annonces": cartes, "total_site": total, "page": page, "a_verifier": a_verifier,
                "suite": bool(res.get("annonces")) and page * 27 < (total or 0) and page < 40,
                "lien_site": f"{LEPARKING}/voiture-occasion/{slug(q.get('marque_label'))}"
                             + (f"-{slug(modele_propre(q.get('modele_label') or ''))}" if q.get("modele_label") else "") + ".html"}

    async def _html(self, site: Site, q: dict) -> dict:
        page = max(1, int(q.get("page") or 1))
        repli = bool(q.get("_repli"))
        url = site.url(q, page, repli)
        res = await self._eval(site.cle, "liste", [url, site.lien_re, q.get("marque_label") or ""], "liste:" + url) or {}
        brutes = res.get("annonces") or []
        # Modèle introuvable dans l'URL du site (404 ou 0 annonce) : repli sur la marque + filtrage du titre
        if page == 1 and not repli and not brutes and q.get("modele_label"):
            return await self._html(site, {**q, "_repli": True})
        prix_max, km_max, annee_min, annee_max = (int(q[k]) if q.get(k) else None
                                                  for k in ("prix_max", "km_max", "annee_min", "annee_max"))
        cible = norm(modele_propre(q.get("modele_label") or ""))
        carbus = set(q.get("carburants") or [])
        cartes, fin_prix = [], False
        for b in brutes:
            if site.tri_prix_local and prix_max and b.get("prix") and b["prix"] > prix_max:
                fin_prix = True  # résultats triés par prix : inutile d'aller plus loin
                continue
            if (prix_max and b.get("prix") and b["prix"] > prix_max) or (km_max and b.get("km") and b["km"] > km_max) \
                    or (annee_min and b.get("annee") and b["annee"] < annee_min) \
                    or (annee_max and b.get("annee") and b["annee"] > annee_max):
                continue
            if (repli or site.filtre_modele_local) and cible and cible not in norm(b.get("titre")):
                continue
            carbu = carburant_norm(b.get("carburant")) or carburant_de(b.get("titre"), b.get("texte"))
            if carbus and carbu and carbu not in carbus:
                continue
            ville, dep = localiser(b.get("texte") or "", site.cle)
            if q.get("region") and not dans_region(None, q["region"], dep):
                continue
            cartes.append(carte(site.nom, titre=b.get("titre") or "Annonce", prix=b.get("prix"), annee=b.get("annee"),
                                kilometrage=b.get("km"), lien=b["lien"], image=b.get("image"),
                                carburant=carbu, boite=b.get("boite"), ville=lieu((ville or "").title() or None, None, dep)))

        lire = self._lecteur_fiche(site)
        a_verifier = []
        if site.differe or q.get("_differe") or self.freine(site.cle):
            for c in cartes:          # affichées tout de suite ; fiches lues ensuite, au rythme du site
                verifier(c, None)
                self.attente[c["lien"]] = (site.cle, c)
                a_verifier.append(c["lien"])
        else:
            await self._verifier_toutes(cartes, lire)
        miroirs = _marquer_miroirs(cartes)
        suite = bool(brutes) and len(brutes) >= site.par_page * 0.6 and page < site.pages_max and not fin_prix
        return {"annonces": cartes, "total_site": None, "page": page,
                "suite": suite, "lien_site": url, "ecartees_page": len(brutes) - len(cartes),
                "miroirs": len(miroirs), "repli": repli, "a_verifier": a_verifier}
