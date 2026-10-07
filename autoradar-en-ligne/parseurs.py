"""
Lecture des pages des sites EN PYTHON (mode « http », sans navigateur — utilisé en ligne).

Portage fidèle de sites/extracteur.js, sites/fiche.js et sites/leparking.js : mêmes règles,
mêmes résultats. Si vous modifiez l'un, modifiez l'autre.
"""
from __future__ import annotations

import json
import re
import unicodedata
from typing import Any, Optional
from urllib.parse import urljoin, urlparse

from selectolax.lexbor import LexborHTMLParser   # moteur HTML5 (Lexbor) : même découpage que Chrome

BLOQUE = re.compile(r"antiaspiration|getCaptcha|captcha-delivery\.com|geo\.captcha|cf-chl-|"
                    r"<title>\s*(Just a moment|Attention Required|Un instant)", re.I)
NEXT_DATA_RE = re.compile(r'<script[^>]+id="__NEXT_DATA__"[^>]*>([\s\S]*?)</script>')
ESPACES = re.compile(r"[\u00a0\u202f]")


def _low(t: str) -> str:
    t = unicodedata.normalize("NFD", t or "").lower()
    return "".join(c for c in t if not unicodedata.combining(c))


def _doc(h: str) -> LexborHTMLParser:
    return LexborHTMLParser(h or "<html><body></body></html>")


def _retirer(noeud, selecteur: str) -> None:
    for n in noeud.css(selecteur):
        n.decompose()


def _desc(noeud, selecteur: str) -> list:
    """querySelectorAll : descendants seulement (sans le nœud lui-même)."""
    return [n for n in noeud.css(selecteur) if n.mem_id != noeud.mem_id]


def _attr(n, nom: str) -> Optional[str]:
    return (n.attributes or {}).get(nom) if n is not None else None


def _texte(n) -> str:   # textContent
    return n.text(deep=True, separator="", strip=False) or ""


def _classe(el, nom: str) -> bool:
    return nom in (_attr(el, "class") or "").split()


def _parts(el) -> list[str]:
    out = []
    for t in el.traverse(include_text=True):
        if t.tag == "-text":
            v = re.sub(r"\s+", " ", ESPACES.sub(" ", t.text_content or "")).strip()
            if v:
                out.append(v)
    return out


def _num(s: Any) -> int:
    d = re.sub(r"\D", "", str(s or ""))
    return int(d) if d else 0


# --------------------------------------------------------------------------- #
# Page de résultats (extracteur générique) — cf. sites/extracteur.js
# --------------------------------------------------------------------------- #
NB = r"(\d{1,3}(?:[ .]\d{3})+|\d{1,7})"
DATE_COMPLETE = re.compile(r"\b\d{1,2}[/.-]\d{1,2}[/.-](?:19|20)\d{2}\b")
YEAR = re.compile(r"(?:^|ann[ée]e\s*:?\s*|mill[ée]sime\s*:?\s*|mec\s*:?\s*|circulation\s*:?\s*|\b\d{1,2}[/.-])((?:19[89]|20[0-3])\d)\b", re.I)
FUEL = [(re.compile(r"hybride|hybrid|e-tech|\bhev\b|\bphev\b", re.I), "Hybride"),
        (re.compile(r"[ée]lectrique|electric|\bev\b", re.I), "Électrique"),
        (re.compile(r"diesel|gazole", re.I), "Diesel"),
        (re.compile(r"essence|petrol|benzin", re.I), "Essence"),
        (re.compile(r"\bgpl\b|gnv|[ée]thanol", re.I), "GPL / autre")]
NON_PHOTO = re.compile(r"efficiency|logo|icon|picto|badge|label|sprite|flag|\.svg(\?|$)|placeholder|novisu", re.I)
STOP = re.compile(r"€|\bkm\b|kilom|ann[ée]e|bo[iî]te|[ée]nergie|carburant|mois|garantie|^\d{4}$|^\d{1,2}[/.-]\d{4}$|"
                  r"^(essence|diesel|hybride|[ée]lectrique|manuelle|automatique)$", re.I)
PAS_PRIX = re.compile(r"mois|mensualit|loyer|remise|[ée]conom|r[ée]duction|^-|neuf|initial", re.I)
IMG_URL = re.compile(r"https?://[^\"'\s\\<>()]+?\.(?:jpe?g|png|webp|avif)(?:\?[^\"'\s\\<>()]*)?", re.I)


def _abs(h: Optional[str], base: str) -> Optional[str]:
    if not h:
        return None
    try:
        return urljoin(base, h.strip()).split("#")[0]
    except Exception:
        return None


def images_de_page(h: str) -> list[str]:
    """Toutes les URL d'images présentes dans le HTML brut (y compris le JSON échappé des pages React)."""
    brut = (h or "").replace("\\u002F", "/").replace("\\u002f", "/").replace("\\/", "/")
    return [u for u in IMG_URL.findall(brut) if not NON_PHOTO.search(u)]


def image_par_identifiant(lien: str, images: list[str]) -> Optional[str]:
    """Photo chargée par JavaScript (absente de la carte) : on la retrouve grâce à l'identifiant de l'annonce."""
    jetons = [t.lower() for t in re.findall(r"[A-Za-z0-9]+", lien or "") if len(t) >= 6 and re.search(r"\d", t)]
    cands = ([jetons[-2] + jetons[-1]] if len(jetons) >= 2 else []) + [t for t in reversed(jetons) if len(t) >= 8]
    for c in cands:
        for u in images:
            if c in u.lower():
                return re.sub(r"_small\.(jpe?g|webp|png)", r"_medium.\1", u, flags=re.I)
    return None


def _src_image(card):
    img = next((i for i in _desc(card, "img")
                if not NON_PHOTO.search((_attr(i, "data-src") or "") + (_attr(i, "src") or ""))), None)
    src = None
    if img is not None:
        src = (_attr(img, "data-src") or _attr(img, "data-lazy-src") or _attr(img, "src")
               or (_attr(img, "srcset") or "").split(" ")[0])
    if src and src.startswith("data:"):
        src = None
    if not src:   # <picture><source srcset>…</picture> sans <img> exploitable
        for sc in _desc(card, "source"):
            v = (_attr(sc, "srcset") or _attr(sc, "data-srcset") or "").split(",")[0].strip().split(" ")[0]
            if v and not v.startswith("data:") and not NON_PHOTO.search(v):
                src = v
                break
    if not src:   # image de fond
        for el in [card] + _desc(card, "[style]"):
            m = re.search(r"url\(['\"]?([^'\")]+)", _attr(el, "style") or "")
            if m and not m.group(1).startswith("data:") and not NON_PHOTO.search(m.group(1)):
                src = m.group(1)
                break
    return src or None, img


def extraire_liste(h: str, base: str, re_src: str, marque: str = "") -> dict:
    mq = _low(marque)
    rx = re.compile(re_src)
    images = images_de_page(h)
    doc = _doc(h)
    _retirer(doc.root, "script,style,noscript,svg,template")

    def liens_de(el) -> set:
        s = set()
        for a in _desc(el, "a[href]"):
            u = _abs(_attr(a, "href"), base)
            if u and rx.search(u):
                s.add(u)
                if len(s) > 1:
                    break
        return s

    par_lien: dict[str, Any] = {}
    for a in doc.root.css("a[href]"):
        u = _abs(_attr(a, "href"), base)
        if u and rx.search(u) and u not in par_lien:
            par_lien[u] = a
    res = []
    for href, a in par_lien.items():
        card = a
        while True:
            p = card.parent
            if p is None or p.tag in ("body", "html", "-document") or len(liens_de(p)) != 1:
                break
            card = p
        P = _parts(card)
        prix = km = annee = None
        carburant = boite = None
        for i, p in enumerate(P):
            suivant = P[i + 1] if i + 1 < len(P) else ""
            if prix is None and not PAS_PRIX.search(p + " " + suivant[:8]):
                m = re.search(NB + r"\s?(€|EUR)", p)
                if not m and re.match(r"^(€|EUR)$", suivant):
                    m = re.match("^" + NB + "$", p)
                if m and _num(m.group(1)) >= 300:
                    prix = _num(m.group(1))
            if km is None:
                m = re.search(NB + r"\s?km\b", p, re.I)
                if not m and re.match(r"^km\b", suivant, re.I):
                    m = re.match("^" + NB + "$", p)
                if m:
                    km = _num(m.group(1))
            if annee is None and not re.search(r"€|km\b", p, re.I) and not DATE_COMPLETE.search(p):
                m = YEAR.search(p)
                prec = P[i - 1] if i > 0 else ""
                if not m and re.match(r"^(ann[ée]e|mill[ée]sime|mise en circulation)\s*:?$", prec, re.I):
                    m = re.match(r"^((?:19[89]|20[0-3])\d)$", p)
                if m:
                    annee = int(m.group(1))
            if not carburant and len(p) < 40:
                carburant = next((nom for f, nom in FUEL if f.search(p)), None)
            if not boite and len(p) < 40:
                if re.search(r"automatique|\bauto\b|\bbva\b|\beat\s?\d", p, re.I) and not re.search("clim", p, re.I):
                    boite = "Automatique"
                elif re.search(r"manuelle|\bbvm\b", p, re.I):
                    boite = "Manuelle"
        src, img = _src_image(card)
        image = _abs(src, base) if src else image_par_identifiant(href, images)

        def suite(i: int) -> str:
            out = [P[i]]
            for k in range(i + 1, len(P)):
                if len(out) >= 4 or STOP.search(P[k]) or len(P[k]) > 90:
                    break
                if re.match(r"^[•|·\-–]+$", P[k]):
                    continue
                out.append(P[k])
            return " ".join(out)

        hh = _desc(card, "h1,h2,h3,h4")
        titre = re.sub(r"\s+", " ", _texte(hh[0])).strip() if hh else ""
        if not titre or (mq and mq not in _low(titre)):
            i = next((k for k, p in enumerate(P) if mq in _low(p) and len(p) < 120), -1) if mq else -1
            if i >= 0:
                titre = suite(i)
            elif not titre:
                titre = re.sub(r"\s+", " ", _attr(a, "title") or (_attr(img, "alt") if img is not None else "") or "").strip()
            if not titre:
                j = next((k for k, p in enumerate(P) if re.search(r"[a-z]{3}", p, re.I) and len(p) > 5 and not STOP.search(p)), -1)
                titre = suite(j) if j >= 0 else "Annonce"
        elif len(titre) < 22:
            i = next((k for k, p in enumerate(P) if titre in p or p in titre), -1)
            if i >= 0:
                t2 = suite(i)
                if len(titre) < len(t2) < 140:
                    titre = t2 if titre in t2 else titre + " " + t2
                else:   # version placée après le prix (« Peugeot 208 | 11 190 € | 1.2 PureTech Style »)
                    v = next((p for p in P[i + 1:i + 5] if re.search(r"[a-z]{2}", p, re.I) and 3 < len(p) < 90
                              and not STOP.search(p) and p not in titre), None)
                    if v:
                        titre = titre + " " + v
        res.append({"lien": href, "titre": re.sub(r"\s*\|\s*", " ", titre)[:140], "prix": prix, "km": km,
                    "annee": annee, "carburant": carburant, "boite": boite, "image": image,
                    "texte": " | ".join(P)[:600]})
    return {"annonces": res}


# --------------------------------------------------------------------------- #
# Fiche annonce — cf. sites/fiche.js
# --------------------------------------------------------------------------- #
_BLANCS = re.compile(r"[ \t]+")
_LIGNES = re.compile(r"\s*\n\s*")


def _normaliser(t: str) -> str:
    return _LIGNES.sub("\n", _BLANCS.sub(" ", ESPACES.sub(" ", t))).strip()


def _txt(el) -> str:
    return _normaliser(_texte(el))


def equipements_json(h: str, lien: str) -> list[str]:
    """Pages React (ex. Renew) : options et équipements du véhicule dans le JSON embarqué, autour de son
    identifiant (productId=…) : liste « options » juste avant, liste « equipments » juste après."""
    m = re.search(r"[?&]productId=([^&#]+)", lien or "")
    if not m:
        return []
    u = (h or "").replace('\\"', '"').replace("\\u002F", "/")
    cle = '"productId":"' + m.group(1) + '"'
    i = u.find(cle)
    while i >= 0:   # l'identifiant peut apparaître plusieurs fois : on prend la 1re occurrence qui a des données
        avant, apres = u.rfind('"productId":"', 0, i), u.find('"productId":"', i + len(cle))
        zones = [re.findall(r'"options":\[(.*?)\]', u[max(avant, 0, i - 30000):i])[-1:],
                 re.findall(r'"equipments":\[(.*?)\]', u[i:apres if apres > 0 else i + 60000])[:1]]
        out = [d for z in zones for a in z for d in re.findall(r'"description":"([^"]{3,120})"', a)]
        if out:
            return out
        i = u.find(cle, i + 1)
    return []


CLES_DATE = re.compile(r'"(?:publicationDateTime|publicationDate|datePublished|createdTimestampWithOffset|created|createdAt|'
                       r'firstPublicationDate|first_publication_date)"\s*:\s*"(\d{4}-\d{2}-\d{2})')


def date_publication(h: str, lien: str = "") -> Optional[str]:
    """Date de mise en ligne (AAAA-MM-JJ) si la fiche la donne : « Publiée le 08/09/2026 » (L'argus),
    JSON-LD datePublished, ou clé de date dans le JSON embarqué au plus près de l'identifiant de l'annonce."""
    m = re.search(r"publi[ée]e?\s+le(?:\s|&nbsp;|<[^>]{0,200}>)*(\d{1,2})/(\d{1,2})/(\d{4})", h or "", re.I)
    if m:
        return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"
    u = (h or "").replace('\\"', '"').replace("\\u002F", "/")
    m = re.search(r'"datePublished"\s*:\s*"(\d{4}-\d{2}-\d{2})', u)
    if m:
        return m.group(1)
    ident = re.search(r"[?&]productId=([^&#]+)", lien or "") or \
        re.search(r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})", lien or "")
    if not ident:
        return None
    meilleur, dist = None, 5001
    i = u.find(ident.group(1))
    while i >= 0:
        for d in CLES_DATE.finditer(u, max(0, i - 5000), i + 5000):
            if abs(d.start() - i) < dist:
                meilleur, dist = d.group(1), abs(d.start() - i)
        i = u.find(ident.group(1), i + 1)
    return meilleur


def lire_fiche(h: str, lien: str = "") -> dict:
    doc = _doc(h)
    ld, image = "", None
    for sc in doc.css('script[type="application/ld+json"]'):
        try:
            data = json.loads(_texte(sc))
        except Exception:
            continue

        def walk(o):
            nonlocal ld, image
            if isinstance(o, list):
                for x in o:
                    walk(x)
                return
            if not isinstance(o, dict):
                return
            typ = o.get("@type")
            typ = ",".join(map(str, typ)) if isinstance(typ, list) else str(typ) if typ is not None else ""
            if re.search(r"vehicle|car|product|offer", typ, re.I):
                if isinstance(o.get("description"), str) and len(o["description"]) > len(ld):
                    ld = o["description"]
                im = o.get("image")
                im = im[0] if isinstance(im, list) and im else im
                im = im.get("url") if isinstance(im, dict) else im
                if not image and isinstance(im, str) and im.startswith("http"):
                    image = im
            for v in o.values():
                walk(v)
        walk(data)
    og = _attr(doc.css_first('meta[property="og:image"]'), "content") or ""
    if og.startswith("http") and not NON_PHOTO.search(og):
        image = og
    miroir = miroir_lien = None   # annonce « miroir » d'une autre plateforme (L'argus reprend Leboncoin)
    for a in doc.css("a[href]"):
        href = _attr(a, "href") or ""
        if re.search(r"leboncoin\.fr/(ad|voitures)/", href, re.I):
            miroir, miroir_lien = "Leboncoin", href.split("#")[0]
            break
        if re.search(r"lacentrale\.fr/auto-occasion-annonce", href, re.I):
            miroir, miroir_lien = "La Centrale", href.split("#")[0]
            break
    _retirer(doc.root, "script,style,noscript,svg,header,footer,nav,aside,form,iframe,template")
    body = doc.body
    if body is None:
        return {"description": ld[:12000], "equipements": equipements_json(h, lien), "miroir": miroir,
                "miroir_lien": miroir_lien, "image": image, "date": date_publication(h, lien)}
    for e in _desc(body, "p,div,li,br,h1,h2,h3,h4,h5,h6,section,article,tr,dt,dd"):
        e.insert_child("\n")      # sauts de ligne entre blocs, sinon « Description » et le texte se collent
    best, best_score = None, 0.0
    for el in _desc(body, "div,section,article,p"):
        brut = _texte(el)
        if len(brut) < 120 or len(brut) > 40000:   # trop court, ou conteneur de toute la page : inutile de normaliser
            continue
        t = _normaliser(brut)
        if len(t) < 120 or len(t) > 15000:
            continue
        lt = sum(len(_texte(a)) for a in _desc(el, "a"))
        n = len(_desc(el, "div,section"))
        score = len(t) - 4 * lt - 0.5 * n * 10
        if lt / len(t) < 0.25 and score > best_score and not re.search(r"cookie|consentement", t[:200], re.I):
            best, best_score = el, score
    equip = []
    for hd in _desc(body, "h2,h3,h4,h5,dt,strong"):
        tt = _texte(hd)
        if not re.search(r"[ée]quipement|options?\b|[ée]quipé", tt, re.I) or len(tt) > 60:
            continue
        par = hd.parent
        zone = par if par is not None and _desc(par, "li") else (par.parent if par is not None else None)
        if zone is not None:
            for li in _desc(zone, "li"):
                t = _txt(li)
                if 2 < len(t) < 80:
                    equip.append(t)
    corps = ""
    if best is not None:
        c = best.clone()
        _retirer(c, "h1,h2,h3,h4,h5,h6,button")
        corps = _txt(c)
    description = "\n".join(x for x in (ld, corps) if x)[:12000]
    equip += equipements_json(h, lien)
    return {"description": description, "equipements": list(dict.fromkeys(equip))[:300],
            "miroir": miroir, "miroir_lien": miroir_lien, "image": image, "date": date_publication(h, lien)}


# --------------------------------------------------------------------------- #
# LeParking (réponse de /index.php) — cf. sites/leparking.js
# --------------------------------------------------------------------------- #
def leparking(texte: str, origine: str = "https://www.leparking.fr") -> dict:
    j: Any = texte
    for _ in range(3):
        if not isinstance(j, str):
            break
        try:
            j = json.loads(j)
        except Exception:
            break
    if not isinstance(j, dict):
        return {"status": 403}
    doc = _doc(j.get("#lists") or "")
    lieux = {}   # chemin de la fiche -> (code postal, pays), lus dans les blocs schema.org « Vehicle »
    for sc in doc.css('script[type="application/ld+json"]'):
        t = _texte(sc)
        u = re.search(r'"url"\s*:\s*"([^"]+)"', t)
        if u:
            cp = re.search(r'"postalCode"\s*:\s*"\s*([^"]*?)\s*"', t)
            pays = re.search(r'"addressCountry"\s*:\s*\{[^}]*"name"\s*:\s*"([^"]+)"', t)
            lieux[urlparse(u.group(1)).path] = ((cp.group(1) if cp else "") or None, pays.group(1) if pays else None)
    annonces = []
    for li in doc.css("li.li-result"):
        parts = _parts(li)
        if any(re.match(r"^sponsoris", p, re.I) for p in parts):
            continue          # annonces sponsorisées (souvent hors France)
        ext = next(iter(_desc(li, "a.external[name]")), None)
        detail = _attr(next(iter(_desc(li, "[data-url]")), None), "data-url") or ""
        lien = _attr(ext, "href") or detail
        if not lien:
            continue
        blocs = [re.sub(r"\s+", " ", _texte(t)).strip() for t in _desc(li, ".sample-holder h2 .title-block")]
        titre = re.sub(r"\s+4X2$", "", " ".join(blocs), flags=re.I)
        version = (detail.split("/")[-2] if detail.count("/") >= 2 else "").replace("-", " ")
        i_det = next((k for k, p in enumerate(parts) if re.match(r"^d[ée]tail$", p, re.I)), -1)
        specs = parts[i_det + 1:i_det + 8] if i_det >= 0 else parts
        km = annee = carburant = boite = None
        for p in specs:
            if km is None and re.search(r"km$", p, re.I):
                km = _num(p)
            elif annee is None and re.match(r"^(19|20)\d\d$", p):
                annee = int(p)
            elif not carburant and re.match(r"^(essence|diesel|hybride|electrique|électrique|gpl|ethanol)", p, re.I):
                carburant = p[0] + p[1:].lower()
            elif not boite and re.match(r"^(manuelle|automatique)", p, re.I):
                boite = p[0] + p[1:].lower()
        img = _attr(next(iter(_desc(li, "picture img")), None), "src") or ""
        prix_el = next(iter(_desc(li, "p.prix")), None)
        annonces.append({
            "lien": urljoin(origine, lien), "titre": titre or "Annonce", "version": version, "detail": detail,
            "prix": _num(_texte(prix_el)) if prix_el is not None else None, "km": km, "annee": annee,
            "carburant": "Électrique" if carburant == "Electrique" else carburant, "boite": boite,
            "image": urljoin(origine, img) if img and "visuel_generique" not in img else None,
            "plateforme": re.sub(r"^www\.", "", _attr(ext, "name") or "") or None,
            "vendeur": next((p for p in parts if re.match(r"^(particulier|professionnel)$", p, re.I)), None),
            "date": next((f"{m.group(3)}-{m.group(2)}-{m.group(1)}" for p in (parts[:i_det] if i_det >= 0 else parts)
                          for m in [re.match(r"^(\d{2})/(\d{2})/(\d{4})$", p)] if m), None),
        })
        annonces[-1]["cp"], annonces[-1]["pays"] = lieux.get(urlparse(urljoin(origine, detail)).path, (None, None)) if detail else (None, None)
        if annonces[-1]["prix"] == 0:
            annonces[-1]["prix"] = None
    ctx = j.get("context") or {}
    return {"status": 200, "annonces": annonces, "total": _num(ctx.get("nb_results"))}


def next_data(h: str) -> Optional[str]:
    m = NEXT_DATA_RE.search(h or "")
    return m.group(1) if m else None
