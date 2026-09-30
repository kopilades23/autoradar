"""
Scraper AutoScout24 — asynchrone (Playwright async + asyncio).

Récupère TOUT dès le premier passage : infos de la liste, description complète du
vendeur, liste complète des équipements, accident déclaré, JSON brut… puis applique
les filtres « merguez » et « options premium » et enregistre dans annonces.db.

    python scraper_autoscout24.py                      # Peugeot 208, 3 pages
    python scraper_autoscout24.py --pages 0            # TOUTES les pages de résultats
    python scraper_autoscout24.py --concurrence 10     # requêtes simultanées (défaut 10)
    python scraper_autoscout24.py --visible            # voir le navigateur (utile si blocage)
    python scraper_autoscout24.py --sans-details       # liste seule (réutilise les fiches déjà en base)
    python scraper_autoscout24.py --marque bmw --modele serie-3 --pages 5 --max 80

Comment c'est rapide (analyse du site faite le 30/09/2026) :
  1. Hydration JSON : chaque page (recherche ET fiche) embarque tout son état dans
     <script id="__NEXT_DATA__">. Le scraper lit ce JSON (+ window.__INITIAL_STATE__ & co,
     + les réponses XHR/fetch JSON interceptées) au lieu de parser le HTML.
     -> Sur AutoScout24, la recherche NE contient PAS la description complète
        (seulement un sous-titre tronqué) : les fiches restent nécessaires.
  2. Fiches en parallèle : le navigateur n'ouvre QUE la 1re page (cookies + anti-bot),
     puis toutes les autres pages et les fiches sont téléchargées par fetch() exécuté
     DANS cet onglet (pile réseau du vrai Chrome, mêmes cookies, sans rendu ni images),
     10 requêtes simultanées, et seul le JSON __NEXT_DATA__ est renvoyé à Python.
     Repli automatique sur un vrai onglet (ressources lourdes bloquées) si une
     requête ne renvoie pas le JSON attendu.
"""
from __future__ import annotations

import argparse
import asyncio
import html
import json
import random
import re
import sys
import time
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urljoin, urlparse

try:  # Playwright n'est nécessaire que pour le scraper local (pas pour le site en ligne)
    from playwright.async_api import BrowserContext, Page, async_playwright
except ImportError:  # pragma: no cover
    BrowserContext = Page = async_playwright = None

from database import DB_PATH, Annonce, get_details_connus, init_db, save_annonces
from detection import analyser

SOURCE = "AutoScout24"
BASE_URL = "https://www.autoscout24.fr"
DEBUG_DIR = Path(__file__).with_name("debug")

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
)

# Masque les marqueurs d'automatisation les plus courants (anti-bot basique).
STEALTH_JS = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
Object.defineProperty(navigator, 'languages', { get: () => ['fr-FR', 'fr', 'en-US', 'en'] });
Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
window.chrome = window.chrome || { runtime: {} };
const origQuery = window.navigator.permissions && window.navigator.permissions.query;
if (origQuery) {
  window.navigator.permissions.query = (p) =>
    p && p.name === 'notifications'
      ? Promise.resolve({ state: Notification.permission })
      : origQuery(p);
}
"""

NEXT_DATA_RE = re.compile(r'<script[^>]+id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.S)
# Autres "states" globaux fréquents (Redux, Nuxt, Apollo…) — lus s'ils existent.
GLOBAL_STATES = ["__INITIAL_STATE__", "__PRELOADED_STATE__", "__NUXT__", "__APOLLO_STATE__", "__REDUX_STATE__"]
# Clés susceptibles de porter une description complète dans un JSON d'annonce.
DESC_KEYS = ("description", "body", "sellerNotes", "sellerComment", "htmlDescription", "descriptionHtml")
# Champs lourds inutiles retirés du JSON brut stocké.
BRUT_EXCLUS = {"images", "ocsImagesA", "headerImage", "threeSixty", "adTargetingString", "trackingParams",
               "searchTrackingParams", "trackingParameters", "tracking", "partnerIntegrations", "rawData"}
BLOQUER_TYPES = {"image", "media", "font", "stylesheet"}


# --------------------------------------------------------------------------- #
# Utilitaires de parsing (fonctions pures, testables sans navigateur)
# --------------------------------------------------------------------------- #
def to_int(value: Any) -> Optional[int]:
    """'15 990 €' -> 15990 ; '45.000 km' -> 45000 ; 15990 -> 15990."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return int(value)
    digits = re.sub(r"[^\d]", "", str(value).split(",")[0])
    return int(digits) if digits else None


def to_year(value: Any) -> Optional[int]:
    """'06/2019', '06-2019', '2019' -> 2019."""
    if value is None:
        return None
    m = re.search(r"(19|20)\d{2}", str(value))
    return int(m.group(0)) if m else None


def bigger_image(url: Optional[str]) -> Optional[str]:
    """Les vignettes AutoScout24 finissent par /250x188.webp : on demande une taille plus grande."""
    if not url:
        return None
    return re.sub(r"([/_])\d{2,4}x\d{2,4}(\.\w+)$", r"\g<1>720x540\2", url)


def html_to_text(value: str) -> str:
    value = re.sub(r"&([a-zA-Z]{2,8}|#\d{2,5})\s*(<br\s*/?>|\n)", r"&\1;", value)  # entités coupées par un saut
    value = re.sub(r"<br\s*/?>|</p>|</li>|</div>", "\n", value, flags=re.I)
    value = re.sub(r"<[^>]+>", " ", value)
    value = html.unescape(html.unescape(value))
    value = re.sub(r"[ \t ]+", " ", value)
    return re.sub(r"\n\s*\n+", "\n", value).strip()


def _first(*values: Any) -> Any:
    for v in values:
        if v not in (None, "", [], {}):
            return v
    return None


def _find_key(node: Any, key: str, want: type | tuple = (dict, list, str)) -> Any:
    """Premier objet trouvé (parcours récursif) dont la clé vaut `key`."""
    if isinstance(node, dict):
        v = node.get(key)
        if v and isinstance(v, want):
            return v
        for child in node.values():
            found = _find_key(child, key, want)
            if found:
                return found
    elif isinstance(node, list):
        for child in node:
            found = _find_key(child, key, want)
            if found:
                return found
    return None


def _slim(obj: dict) -> dict:
    return {k: v for k, v in obj.items() if k not in BRUT_EXCLUS}


def parse_next_data_html(page_html: str) -> Optional[dict]:
    m = NEXT_DATA_RE.search(page_html or "")
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError:
        return None


def description_hydratee(obj: dict) -> Optional[str]:
    """Description complète éventuellement présente directement dans le JSON de la liste."""
    for k in DESC_KEYS:
        v = obj.get(k)
        if isinstance(v, str) and len(v.strip()) >= 80 and not v.rstrip().endswith(("…", "...")):
            return html_to_text(v)
    return None


def annonce_depuis_recherche(it: dict) -> Optional[Annonce]:
    href = it.get("url")
    if not href:
        return None
    vehicle = it.get("vehicle") or {}
    tracking = it.get("tracking") or {}
    price = it.get("price") or {}
    location = it.get("location") or {}
    seller = it.get("seller") or {}

    titre = " ".join(str(p) for p in (
        vehicle.get("make"), vehicle.get("model"),
        _first(vehicle.get("modelVersionInput"), vehicle.get("variant")),
    ) if p) or "Annonce sans titre"

    puissance = None
    for d in it.get("vehicleDetails") or []:
        if isinstance(d, dict) and "puissance" in str(d.get("ariaLabel", "")).lower():
            m = re.search(r"(\d+)\s*ch", str(d.get("data", "")), re.I)
            puissance = int(m.group(1)) if m else None

    images = it.get("images") or []
    image = images[0] if images and isinstance(images[0], str) else (
        images[0].get("url") if images and isinstance(images[0], dict) else None)

    a = Annonce(
        titre=titre.strip(),
        prix=to_int(_first(tracking.get("price"), price.get("priceRaw"), price.get("priceFormatted"))),
        annee=to_year(_first(tracking.get("firstRegistration"), vehicle.get("firstRegistration"))),
        kilometrage=to_int(_first(tracking.get("mileage"), vehicle.get("mileageInKm"))),
        lien=urljoin(BASE_URL, href),
        source=SOURCE,
        image=bigger_image(image),
        carburant=vehicle.get("fuel"),
        boite=vehicle.get("transmission"),
        puissance_ch=puissance,
        ville=(location.get("city") or "").title() or None,
        code_postal=location.get("zip"),
        vendeur=_first(seller.get("companyName"), seller.get("contactName")),
        type_vendeur=seller.get("type"),
        donnees_brutes={"recherche": _slim(it)},
    )
    a["_id"] = it.get("id")                      # type: ignore[typeddict-unknown-key]
    a["_sous_titre"] = vehicle.get("subtitle")   # type: ignore[typeddict-unknown-key]
    desc = description_hydratee(it)
    if desc:
        a["description"] = desc
        a["origine_description"] = "recherche"
    return a


def parse_resultats(etats: list[Any]) -> tuple[list[Annonce], Optional[int]]:
    """JSON d'hydration / XHR d'une page de résultats -> (annonces, nombre de pages)."""
    annonces: list[Annonce] = []
    seen: set[str] = set()
    nb_pages = None
    for etat in etats:
        nb_pages = nb_pages or _find_key(etat, "numberOfPages", int)
        for it in _find_key(etat, "listings", list) or []:
            if isinstance(it, dict):
                a = annonce_depuis_recherche(it)
                if a and a["lien"] not in seen:
                    seen.add(a["lien"])
                    annonces.append(a)
    return annonces, nb_pages


def labels_equipements(eq: Any) -> list[str]:
    """AutoScout24 : {"comfortAndConvenience": [{"id": "Climatisation auto", "categoryName": …}, …], …}
    -> le libellé est dans "id". On accepte aussi name/label et les listes simples."""
    out: list[str] = []

    def add(x: Any) -> None:
        if isinstance(x, str):
            out.append(x)
        elif isinstance(x, dict):
            lab = _first(x.get("name"), x.get("label"), x.get("id"))
            if isinstance(lab, str) and not lab.isdigit():
                out.append(lab)
            for sub in ("items", "equipment", "values"):
                if isinstance(x.get(sub), list):
                    for y in x[sub]:
                        add(y)

    if isinstance(eq, dict):
        for v in eq.values():
            if isinstance(v, list):
                for x in v:
                    add(x)
    elif isinstance(eq, list):
        for x in eq:
            add(x)
    return list(dict.fromkeys(s.strip() for s in out if s and s.strip()))


def parse_fiche(data: dict) -> Optional[dict]:
    """JSON d'une fiche annonce -> infos complètes."""
    ld = _find_key(data, "listingDetails", dict)
    if not ld:
        return None
    v = ld.get("vehicle") or {}
    desc = ld.get("description")
    return {
        "description": html_to_text(desc) if isinstance(desc, str) and desc.strip() else None,
        "equipements": labels_equipements(v.get("equipment")),
        "accident_declare": v.get("hadAccident") if isinstance(v.get("hadAccident"), bool) else None,
        "dommages": v.get("damageConditions") or [],
        "puissance_ch": to_int(_first(v.get("rawPowerInHp"), v.get("powerInHp"))),
        "brut": _slim(ld),
    }


def appliquer_fiche(a: Annonce, fiche: dict, origine: str) -> None:
    a["description"] = fiche["description"] or a.get("description")
    a["equipements"] = fiche["equipements"]
    a["accident_declare"] = fiche["accident_declare"]
    a["origine_description"] = origine
    a["puissance_ch"] = a.get("puissance_ch") or fiche["puissance_ch"]
    a["_dommages"] = fiche["dommages"]  # type: ignore[typeddict-unknown-key]
    brut = a.get("donnees_brutes") or {}
    brut["fiche"] = fiche["brut"]
    a["donnees_brutes"] = brut


# --------------------------------------------------------------------------- #
# Réseau
# --------------------------------------------------------------------------- #
async def pause(a: float = 0.4, b: float = 1.2) -> None:
    await asyncio.sleep(random.uniform(a, b))


FETCH_JS = """async (url) => {
  try {
    const r = await fetch(url, { credentials: 'include', headers: { 'Accept': 'text/html,application/xhtml+xml' } });
    const h = await r.text();
    const m = h.match(/<script[^>]+id="__NEXT_DATA__"[^>]*>([\\s\\S]*?)<\\/script>/);
    return { status: r.status, json: m ? m[1] : null };
  } catch (e) { return { status: 0, json: null }; }
}"""


async def fetch_json(page: Page, url: str, essais: int = 3) -> Optional[dict]:
    """GET exécuté dans l'onglet déjà ouvert : empreinte réseau du vrai navigateur, mêmes
    cookies, aucun rendu. Ne renvoie que le JSON __NEXT_DATA__ (quelques dizaines de Ko)."""
    for i in range(essais):
        try:
            res = await page.evaluate(FETCH_JS, url)
        except Exception:
            res = {"status": 0, "json": None}
        if res["status"] in (0, 403, 429, 503):
            await asyncio.sleep(2 ** i * 2 + random.random() * 2)  # le site freine : on ralentit
            continue
        if res["json"]:
            try:
                return json.loads(res["json"])
            except json.JSONDecodeError:
                return None
        return None
    return None


async def ouvrir_leger(ctx: BrowserContext, url: str) -> Page:
    """Onglet de repli : images, polices, CSS et domaines tiers bloqués."""
    page = await ctx.new_page()
    hote = urlparse(BASE_URL).hostname or ""

    async def filtre(route):
        req = route.request
        if req.resource_type in BLOQUER_TYPES or hote not in (urlparse(req.url).hostname or ""):
            await route.abort()
        else:
            await route.continue_()

    await page.route("**/*", filtre)
    await page.goto(url, wait_until="domcontentloaded", timeout=45_000)
    return page


async def etats_de_la_page(page: Page) -> list[Any]:
    """__NEXT_DATA__ + états globaux window.* de la page courante."""
    etats: list[Any] = []
    nd = page.locator("script#__NEXT_DATA__")
    if await nd.count():
        try:
            etats.append(json.loads(await nd.first.text_content() or ""))
        except json.JSONDecodeError:
            pass
    autres = await page.evaluate(
        """(noms) => { const out = [];
            for (const k of noms) { try { if (window[k]) out.push(JSON.parse(JSON.stringify(window[k]))); } catch (e) {} }
            return out; }""",
        GLOBAL_STATES,
    )
    return etats + autres


async def capturer_json(resp, sink: list) -> None:
    """Intercepte les réponses XHR/fetch JSON (certains sites y mettent les annonces)."""
    try:
        if resp.request.resource_type not in ("xhr", "fetch"):
            return
        if "json" not in (resp.headers.get("content-type") or ""):
            return
        if int(resp.headers.get("content-length") or 0) > 8_000_000:
            return
        sink.append(await resp.json())
    except Exception:
        pass


async def accept_cookies(page: Page) -> None:
    for loc in (
        page.locator('[data-testid="as24-cmp-accept-all-button"]'),
        page.get_by_role("button", name=re.compile(r"(tout accepter|accepter tout|accepter|accept all)", re.I)),
    ):
        try:
            await loc.first.click(timeout=4000)
            print("  ✓ Bandeau cookies accepté")
            await pause()
            return
        except Exception:
            continue
    print("  · Pas de bandeau cookies détecté")


async def extract_from_dom(page: Page) -> list[Annonce]:
    """Dernier repli pour la liste : lit les <article> de la page."""
    raw = await page.evaluate(
        """() => [...document.querySelectorAll('main article, article[data-guid]')].map(a => {
            const link = a.querySelector('a[href*="/offres/"], a[href*="/angebote/"], a[href*="/offers/"]');
            if (!link) return null;
            const img = a.querySelector('picture img, img'), title = a.querySelector('h2, [data-testid*="title"]');
            return { titre: title ? title.innerText.replace(/\\s+/g, ' ').trim() : '',
                     prix: a.dataset.price || '', km: a.dataset.mileage || '', annee: a.dataset.firstRegistration || '',
                     texte: a.innerText, lien: link.href,
                     image: img ? (img.currentSrc || img.src || '') : '' };
          }).filter(Boolean)"""
    )
    out, seen = [], set()
    for r in raw:
        if r["lien"] in seen:
            continue
        seen.add(r["lien"])
        texte = r.get("texte") or ""
        km = r.get("km") or (re.search(r"([\d\s.  ]+)\s?km", texte) or [None, None])[1]
        annee = r.get("annee") or (re.search(r"\b\d{2}/((?:19|20)\d{2})\b", texte) or [None, None])[1]
        img = r.get("image") or ""
        out.append(Annonce(titre=r.get("titre") or "Annonce", prix=to_int(r.get("prix")), annee=to_year(annee),
                           kilometrage=to_int(km), lien=r["lien"], source=SOURCE,
                           image=bigger_image(img) if img and not img.startswith("data:") else None))
    return out


async def fiche_via_dom(page: Page) -> Optional[dict]:
    texte = await page.evaluate(
        """() => {
          const pick = (sels) => { for (const s of sels) { const el = document.querySelector(s);
              if (el && el.innerText.trim()) return el.innerText.trim(); } return ''; };
          return { desc: pick(['[data-cy="seller-notes-section"]', '#sellerNotesSection', '[class*="SellerNotes"]']),
                   equip: pick(['[data-cy="equipment-section"]', '#equipmentSection', '[class*="Equipment"]']) };
        }"""
    )
    if not (texte["desc"] or texte["equip"]):
        return None
    equip = [l.strip() for l in texte["equip"].split("\n") if l.strip()]
    return {"description": texte["desc"] or None, "equipements": equip, "accident_declare": None,
            "dommages": [], "puissance_ch": None, "brut": {}}


async def dump_debug(page: Page, tag: str) -> None:
    DEBUG_DIR.mkdir(exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    try:
        await page.screenshot(path=str(DEBUG_DIR / f"{tag}-{stamp}.png"), full_page=True)
        (DEBUG_DIR / f"{tag}-{stamp}.html").write_text(await page.content(), encoding="utf-8")
        print(f"  ! Capture et HTML enregistrés dans {DEBUG_DIR}/")
    except Exception as e:
        print(f"  ! Impossible d'écrire le debug : {e}")


def search_url(marque: str, modele: str, page_num: int) -> str:
    return (f"{BASE_URL}/lst/{marque.lower()}/{modele.lower()}"
            f"?atype=C&cy=F&sort=standard&desc=0&ustate=N%2CU&page={page_num}")


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #
async def page_resultats(ctx: BrowserContext, base: Page, sem: asyncio.Semaphore, url: str) -> list[Annonce]:
    async with sem:
        await pause(0.1, 0.6)
        data = await fetch_json(base, url)
        if data:
            return parse_resultats([data])[0]
        page = await ouvrir_leger(ctx, url)  # repli navigateur
        try:
            annonces = parse_resultats(await etats_de_la_page(page))[0]
            return annonces or await extract_from_dom(page)
        finally:
            await page.close()


async def lire_fiche(ctx: BrowserContext, base: Page, sem: asyncio.Semaphore, a: Annonce, stats: dict) -> None:
    async with sem:
        await pause(0.05, 0.4)
        data = await fetch_json(base, a["lien"])
        fiche = parse_fiche(data) if data else None
        origine = "fiche-json"
        if not fiche:
            origine = "fiche-navigateur"
            try:
                page = await ouvrir_leger(ctx, a["lien"])
                try:
                    for etat in await etats_de_la_page(page):
                        fiche = parse_fiche(etat)
                        if fiche:
                            break
                    fiche = fiche or await fiche_via_dom(page)
                finally:
                    await page.close()
            except Exception:
                fiche = None
        if fiche:
            appliquer_fiche(a, fiche, origine)
            stats[origine] += 1
        else:
            stats["echecs"] += 1
        stats["faites"] += 1
        if stats["faites"] % 10 == 0 or stats["faites"] == stats["total"]:
            print(f"    {stats['faites']:>4}/{stats['total']}  "
                  f"(json {stats['fiche-json']}, onglet {stats['fiche-navigateur']}, échecs {stats['echecs']})")


async def scrape(marque: str, modele: str, pages: int, limit: Optional[int], visible: bool,
                 details: bool, concurrence: int) -> list[Annonce]:
    t0 = time.perf_counter()
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=not visible,
                                          args=["--disable-blink-features=AutomationControlled"])
        ctx = await browser.new_context(
            user_agent=USER_AGENT, locale="fr-FR", timezone_id="Europe/Paris",
            viewport={"width": 1440, "height": 900},
            extra_http_headers={"Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8"},
        )
        await ctx.add_init_script(STEALTH_JS)
        page = await ctx.new_page()
        sem = asyncio.Semaphore(concurrence)

        try:
            # ---------- 1. Page 1 dans un vrai navigateur (cookies, consentement, anti-bot) ----------
            url1 = search_url(marque, modele, 1)
            print(f"→ {marque.title()} {modele.upper()} — page 1 (navigateur) {url1}")
            captures, en_cours = [], set()

            def on_response(resp):
                t = asyncio.ensure_future(capturer_json(resp, captures))
                en_cours.add(t)
                t.add_done_callback(en_cours.discard)

            page.on("response", on_response)
            await page.goto(url1, wait_until="domcontentloaded", timeout=45_000)
            await pause(1.0, 2.0)
            await accept_cookies(page)
            try:
                await page.wait_for_selector("main article", timeout=15_000)
            except Exception:
                print("  · Aucun <article> visible (anti-bot ? mise en page modifiée ?)")
            if en_cours:
                await asyncio.gather(*list(en_cours), return_exceptions=True)

            etats = await etats_de_la_page(page) + captures
            annonces, nb_pages = parse_resultats(etats)
            source_liste = "JSON d'hydration" + (f" + {len(captures)} XHR" if captures else "")
            if not annonces:
                annonces, source_liste = await extract_from_dom(page), "DOM (repli)"
            if not annonces:
                await dump_debug(page, "echec-page1")
                return []
            print(f"  ✓ {len(annonces)} annonces via {source_liste} — {nb_pages or '?'} page(s) disponibles")
            page.remove_listener("response", on_response)

            # ---------- 2. Autres pages : HTTP direct en parallèle ----------
            total = (nb_pages or pages or 1) if pages == 0 else min(pages, nb_pages or pages)
            if limit:
                total = min(total, -(-limit // max(1, len(annonces))))  # inutile d'aller plus loin
            if total > 1:
                print(f"→ Pages 2 à {total} en parallèle ({concurrence} à la fois)…")
                res = await asyncio.gather(*(page_resultats(ctx, page, sem, search_url(marque, modele, n))
                                             for n in range(2, total + 1)), return_exceptions=True)
                seen = {a["lien"] for a in annonces}
                for n, r in enumerate(res, start=2):
                    if isinstance(r, Exception):
                        print(f"    ✗ page {n} : {type(r).__name__}")
                        continue
                    nouvelles = [a for a in r if a["lien"] not in seen]
                    seen.update(a["lien"] for a in nouvelles)
                    annonces.extend(nouvelles)
                print(f"  ✓ {len(annonces)} annonces uniques sur {total} page(s)")
            if limit:
                annonces = annonces[:limit]

            # ---------- 3. Descriptions complètes ----------
            hydratees = [a for a in annonces if a.get("origine_description") == "recherche"]
            a_lire = [a for a in annonces if a.get("origine_description") != "recherche"]
            if hydratees:
                print(f"  ✓ {len(hydratees)} description(s) complète(s) déjà présentes dans le JSON de recherche")
            if details and a_lire:
                print(f"→ Fiches complètes : {len(a_lire)} en parallèle ({concurrence} à la fois)…")
                stats = {"total": len(a_lire), "faites": 0, "fiche-json": 0, "fiche-navigateur": 0, "echecs": 0}
                await asyncio.gather(*(lire_fiche(ctx, page, sem, a, stats) for a in a_lire))
            print(f"  ⏱ {time.perf_counter() - t0:.1f} s au total")
            return annonces
        except Exception:
            await dump_debug(page, "erreur")
            raise
        finally:
            await ctx.close()
            await browser.close()


def enrichir(annonces: list[Annonce]) -> None:
    """Filtres merguez / options sur titre + description + équipements + infos déclarées."""
    connus = get_details_connus(a["lien"] for a in annonces if not a.get("origine_description"))
    for a in annonces:
        k = connus.get(a["lien"])
        if k and not a.get("origine_description"):  # fiche non relue : on réutilise la base
            a["description"] = k["description"]
            a["equipements"] = k["equipements"]
            a["accident_declare"] = k["accident_declare"]
        motifs, options = analyser(
            a["titre"], a.get("description"), a.get("equipements"), a.get("accident_declare"),
            a.get("_dommages"), [a["_sous_titre"]] if a.get("_sous_titre") else None,  # type: ignore[typeddict-item]
        )
        a["motifs_merguez"], a["merguez"], a["options"] = motifs, bool(motifs), options


def main() -> int:
    ap = argparse.ArgumentParser(description="Scraper AutoScout24 (asynchrone)")
    ap.add_argument("--marque", default="peugeot")
    ap.add_argument("--modele", default="208")
    ap.add_argument("--pages", type=int, default=3, help="pages de résultats (0 = toutes ; défaut 3)")
    ap.add_argument("--max", type=int, default=None, help="plafond d'annonces (défaut : toutes)")
    ap.add_argument("--concurrence", type=int, default=10, help="requêtes simultanées (défaut 10)")
    ap.add_argument("--sans-details", action="store_true", help="ne pas télécharger les fiches")
    ap.add_argument("--visible", action="store_true", help="affiche le navigateur")
    args = ap.parse_args()

    init_db()
    annonces = asyncio.run(scrape(args.marque, args.modele, args.pages, args.max, args.visible,
                                  not args.sans_details, max(1, args.concurrence)))
    if not annonces:
        print("✗ Aucune annonce extraite. Relance avec --visible pour voir ce qui bloque.")
        return 1

    enrichir(annonces)
    for a in annonces:  # nettoie les champs internes
        for k in [k for k in a if k.startswith("_")]:
            a.pop(k)  # type: ignore[misc]

    merguez = [a for a in annonces if a["merguez"]]
    premium = [a for a in annonces if a["options"]]
    sans_desc = sum(1 for a in annonces if not a.get("description"))
    print()
    for a in merguez[:15]:
        print(f"  ⚠ MERGUEZ  {a['titre'][:55]:<55}  ({', '.join(a['motifs_merguez'])})")
    for a in premium[:15]:
        print(f"  ★ PREMIUM  {a['titre'][:55]:<55}  ({', '.join(a['options'])})")

    n = save_annonces(annonces)
    print(f"\n✓ {n} annonce(s) enregistrée(s) dans {DB_PATH.name} — {len(merguez)} merguez, "
          f"{len(premium)} avec options premium, {sans_desc} sans description")
    return 0


if __name__ == "__main__":
    sys.exit(main())
