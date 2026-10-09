"""
Serveur de La Bonne Occaz (sur votre PC ou en ligne).

    python server.py              -> http://localhost:8000  (requêtes directes, sans navigateur)
    python server.py --navigateur -> ancien mode : Chrome piloté en arrière-plan (Playwright)
    python server.py --visible    -> mode navigateur, fenêtre Chrome affichée
    python server.py --port 8080

En ligne (Render, Docker…), tout se règle par variables d'environnement :
    AUTORADAR_HOTE=0.0.0.0          écouter sur le réseau (par défaut 127.0.0.1 = ce PC seulement)
    PORT / AUTORADAR_PORT           port d'écoute (Render fournit PORT)
    AUTORADAR_MOT_DE_PASSE=...      protège tout le site (identifiant au choix)
    AUTORADAR_PUBLIC=1              site ouvert à tous, sans mot de passe (limite de requêtes par visiteur)
    AUTORADAR_MODE=http|navigateur  http par défaut
    AUTORADAR_DOMAINE=labonneoccaz.fr   nom de domaine officiel (par défaut labonneoccaz.fr) : le site n'est
                                    proposé à Google, Bing et aux IA que lorsqu'il est ouvert à cette adresse
    AUTORADAR_REDIRECTION=1         renvoie les visiteurs de l'adresse onrender.com vers le nom de domaine
                                    (à activer une fois le domaine branché et fonctionnel)

Pages :
    /             recherche en direct (10 sources) + liens Leboncoin, La Centrale, Aramis Auto
    /base.html    annonces enregistrées par scraper_autoscout24.py (base SQLite locale)

API :
    GET  /api/marques, /api/modeles?marque=55, /api/options, /api/statut, /api/annonces
    GET  /api/recherche?source=...&...   une page de résultats d'une source
    POST /api/fiches {source, liens}     lecture différée des fiches (description, options, merguez)
"""
from __future__ import annotations

import argparse
import base64
import hmac
import io
import json
import os
import re
import tempfile
import threading
import urllib.request
import time
import webbrowser
from collections import defaultdict, deque
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from database import list_annonces

STATIC_DIR = Path(__file__).with_name("static")
MOTEUR = None  # initialisé dans main()
MOT_DE_PASSE = os.environ.get("AUTORADAR_MOT_DE_PASSE", "")
PUBLIC = os.environ.get("AUTORADAR_PUBLIC") == "1"
# Limite par visiteur (site public) : évite qu'un robot ou un curieux fasse bloquer le serveur par les sites
LIMITE_MINUTE = int(os.environ.get("AUTORADAR_LIMITE_MINUTE", "90"))
DOMAINE = os.environ.get("AUTORADAR_DOMAINE", "labonneoccaz.fr").strip().lower()
REDIRECTION = os.environ.get("AUTORADAR_REDIRECTION") == "1"
# Photos du guide (Wikimedia Commons, licences libres) : téléchargées une fois, réduites, puis servies par le site
PHOTOS_GUIDE = Path(__file__).with_name("guides") / "photos.json"
CACHE_PHOTOS = Path(tempfile.gettempdir()) / "labonneoccaz-photos"
AGENT_PHOTOS = "LaBonneOccaz/1.0 (https://labonneoccaz.fr; contact@labonneoccaz.fr) python-urllib"
VERSION_PHOTOS = "v3"   # à changer pour forcer le re-téléchargement des photos
_photos_meta: dict = {}


def _meta_photos() -> dict:
    if not _photos_meta:
        try:
            _photos_meta.update(json.loads(PHOTOS_GUIDE.read_text(encoding="utf-8")))
        except Exception:
            pass
    return _photos_meta


LARGEURS_PHOTOS = (240, 480, 800, 1280)       # tailles servies (le navigateur choisit selon l'écran : srcset)


def _source_photo(cle: str, meta: dict) -> bytes:
    """Photo d'origine (1280 px, Wikimedia), téléchargée une seule fois."""
    src = CACHE_PHOTOS / f"{cle}-source.jpg"
    if src.is_file() and src.stat().st_size > 1000:
        return src.read_bytes()
    req = urllib.request.Request(meta["img"], headers={"User-Agent": AGENT_PHOTOS})
    with urllib.request.urlopen(req, timeout=20) as r:
        brut = r.read()
    tmp = CACHE_PHOTOS / f".{cle}.{os.getpid()}.{threading.get_ident()}"
    tmp.write_bytes(brut)
    tmp.replace(src)
    return brut


def photo_en_cache(cle: str, largeur: int = 1280) -> tuple[bytes, str] | None:
    """Renvoie (octets, type) de la photo à la largeur demandée. La réduction est faite ici, avec un filtre
    de haute qualité (Lanczos + légère accentuation) : une grande photo réduite par le navigateur paraît pixélisée."""
    meta = _meta_photos().get(cle)
    if not meta or largeur not in LARGEURS_PHOTOS:
        return None
    CACHE_PHOTOS.mkdir(parents=True, exist_ok=True)
    f = CACHE_PHOTOS / f"{cle}-{largeur}-{VERSION_PHOTOS}.webp"
    if f.is_file() and f.stat().st_size > 1000:
        return f.read_bytes(), "image/webp"
    brut = _source_photo(cle, meta)
    try:
        from PIL import Image, ImageFilter
        im = Image.open(io.BytesIO(brut)).convert("RGB")
        if im.width > largeur:
            im = im.resize((largeur, round(im.height * largeur / im.width)), Image.LANCZOS)
            im = im.filter(ImageFilter.UnsharpMask(radius=0.8, percent=60, threshold=2))
        out = io.BytesIO()
        im.save(out, "WEBP", quality=88, method=6)
        donnees = out.getvalue()
    except Exception:
        return brut, "image/jpeg"              # Pillow absent : photo d'origine
    tmp = CACHE_PHOTOS / f".{cle}-{largeur}.{os.getpid()}.{threading.get_ident()}"
    tmp.write_bytes(donnees)
    tmp.replace(f)
    return donnees, "image/webp"


def prechauffer_photos() -> None:
    """Au démarrage, en arrière-plan : récupère les photos pour que les visiteurs ne les attendent pas."""
    def tache():
        for cle in list(_meta_photos()):
            for largeur in LARGEURS_PHOTOS:
                try:
                    photo_en_cache(cle, largeur)
                except Exception:
                    pass
            time.sleep(1.5)                    # doucement, pour Wikimedia
    threading.Thread(target=tache, daemon=True).start()


PAGES_PUBLIQUES = ["/", "/faq.html"]   # pages à référencer (les pages légales sont en noindex)
_appels: dict[str, deque] = defaultdict(deque)
_verrou = threading.Lock()


def _trop(ip: str) -> bool:
    maintenant = time.time()
    with _verrou:
        d = _appels[ip]
        while d and maintenant - d[0] > 60:
            d.popleft()
        if len(d) >= LIMITE_MINUTE:
            return True
        d.append(maintenant)
        if len(_appels) > 5000:
            _appels.clear()
        return False


def _q(qs: dict, k: str, default=None):
    v = qs.get(k, [default])[0]
    return v if v not in ("", None) else default


_NUMERIQUES = ("marque", "prix_max", "km_max", "annee_min", "annee_max", "puissance_min", "puissance_max", "page")


def _parametres_valides(chemin: str, qs: dict) -> bool:
    """Refuse proprement (400) les valeurs absurdes au lieu de planter (500)."""
    for k in _NUMERIQUES:
        v = _q(qs, k)
        if v is not None and not (str(v).isdigit() and len(str(v)) <= 9):
            return False
    if chemin in ("/api/modeles", "/api/recherche") and _q(qs, "marque") is None:
        return False
    return True


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    # -- protection par mot de passe (Basic Auth) quand AUTORADAR_MOT_DE_PASSE est défini --
    def _autorise(self) -> bool:
        if not MOT_DE_PASSE:
            return True
        entete = self.headers.get("Authorization", "")
        if entete.startswith("Basic "):
            try:
                _, _, mdp = base64.b64decode(entete[6:]).decode("utf-8").partition(":")
                if hmac.compare_digest(mdp, MOT_DE_PASSE):
                    return True
            except Exception:
                pass
        self.send_response(401)
        self.send_header("WWW-Authenticate", 'Basic realm="La Bonne Occaz", charset="UTF-8"')
        self.send_header("Content-Length", "0")
        self.end_headers()
        return False

    def _hote(self) -> str:
        return (self.headers.get("Host") or "").split(":")[0].strip().lower()

    def _officiel(self) -> bool:
        """Référencement seulement sur le vrai nom de domaine (pas sur onrender.com ni en local : pas de doublon)."""
        h = self._hote()
        return bool(DOMAINE) and h in (DOMAINE, "www." + DOMAINE)

    def end_headers(self):
        if not self._officiel() or self.path.startswith(("/api/", "/base.html")):
            self.send_header("X-Robots-Tag", "noindex, nofollow")
        # en-têtes de sécurité (HSTS seulement sur le vrai domaine, servi en HTTPS)
        if self._officiel():
            self.send_header("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
        self.send_header("X-Frame-Options", "SAMEORIGIN")
        self.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=(), interest-cohort=()")
        super().end_headers()

    def _texte(self, body: str, ctype: str) -> None:
        b = body.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", ctype + "; charset=utf-8")
        self.send_header("Cache-Control", "public, max-age=3600")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def _rediriger(self) -> bool:
        """onrender.com ou www. -> https://labonneoccaz.fr (même chemin), en 301."""
        h = self._hote()
        if not DOMAINE or self.path == "/healthz":
            return False
        if h == "www." + DOMAINE or (REDIRECTION and h.endswith(".onrender.com")):
            self.send_response(301)
            self.send_header("Location", f"https://{DOMAINE}{self.path}")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return True
        return False

    def _ip(self) -> str:
        return (self.headers.get("X-Forwarded-For") or self.client_address[0]).split(",")[0].strip()

    def _limite(self) -> bool:
        if PUBLIC and _trop(self._ip()):
            self._json({"erreur": "trop de requêtes", "message": "Patientez une minute."}, 429)
            return True
        return False

    def _json(self, data, status: int = 200) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/healthz":   # contrôle de santé de l'hébergeur (sans mot de passe, ne révèle rien)
            return self._json({"ok": True})
        if self._rediriger():
            return
        if self.path == "/robots.txt":
            if not self._officiel():   # adresse technique (onrender.com, PC) : rien à référencer
                return self._texte("User-agent: *\nDisallow: /\n", "text/plain")
            # Moteurs de recherche ET assistants IA (Googlebot, Bingbot, OAI-SearchBot, GPTBot, PerplexityBot…) bienvenus
            return self._texte("User-agent: *\nAllow: /\nDisallow: /api/\nDisallow: /base.html\n\n"
                               f"Sitemap: https://{DOMAINE}/sitemap.xml\n", "text/plain")
        if self.path == "/sitemap.xml" and self._officiel():
            pages = [(p, STATIC_DIR / (p.strip("/") or "index.html"), "1.0" if p == "/" else "0.5") for p in PAGES_PUBLIQUES]
            for f in sorted((STATIC_DIR / "guide").glob("*.html")):     # guide d'achat (pages statiques)
                if f.stem == "credits-photos":
                    continue
                pages.append(("/guide/" if f.stem == "index" else f"/guide/{f.stem}", f, "0.9" if f.stem == "index" else "0.8"))
            jour = lambda f: time.strftime("%Y-%m-%d", time.gmtime(f.stat().st_mtime))
            urls = "".join(f"  <url><loc>https://{DOMAINE}{p}</loc><lastmod>{jour(f)}</lastmod>"
                           f"<priority>{prio}</priority></url>\n" for p, f, prio in pages)
            return self._texte('<?xml version="1.0" encoding="UTF-8"?>\n'
                               '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + urls + "</urlset>\n",
                               "application/xml")
        if not self._autorise():
            return
        # Guide d'achat : adresses propres (/guide/peugeot-208 -> peugeot-208.html) ; l'ancienne forme .html redirige
        chemin, _, requete = self.path.partition("?")
        m = re.fullmatch(r"/guide/photo/(?:(\d{3,4})/)?([a-z0-9-]{2,40})\.webp", chemin)
        if m:
            return self._photo(m.group(2), int(m.group(1) or 1280))
        if chemin.startswith("/guide/") and chemin.endswith(".html") and not chemin.endswith("/index.html"):
            self.send_response(301)
            self.send_header("Location", chemin[:-5] + (f"?{requete}" if requete else ""))
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if chemin.startswith("/guide/") and "." not in chemin.rsplit("/", 1)[-1] and not chemin.endswith("/") \
                and (STATIC_DIR / (chemin.lstrip("/") + ".html")).is_file():
            self.path = chemin + ".html" + (f"?{requete}" if requete else "")
        if self.path.startswith(("/api/recherche", "/api/modeles")) and self._limite():
            return
        u = urlparse(self.path)
        qs = parse_qs(u.query)
        if u.path.startswith("/api/") and not _parametres_valides(u.path, qs):   # adresse tapée à la main, mal formée
            return self._json({"erreur": "parametre", "message": "Paramètre invalide."}, 400)
        try:
            if u.path == "/api/annonces":
                return self._json(list_annonces())
            if u.path == "/api/statut":
                return self._json({"navigateur": MOTEUR.navigateur, "mode": MOTEUR.mode, "sources": MOTEUR.statut})
            if u.path == "/api/options":
                from detection import OPTIONS_GROUPES
                return self._json({g: list(o) for g, o in OPTIONS_GROUPES.items()})
            if u.path == "/api/marques":
                return self._json(MOTEUR.run(MOTEUR.marques()))
            if u.path == "/api/modeles":
                return self._json(MOTEUR.run(MOTEUR.modeles(int(_q(qs, "marque")))))
            if u.path == "/api/recherche":
                q = {
                    "marque_id": _q(qs, "marque"), "marque_label": _q(qs, "marque_label", ""),
                    "modele": _q(qs, "modele", ""), "modele_label": _q(qs, "modele_label", ""),
                    "prix_max": _q(qs, "prix_max"), "km_max": _q(qs, "km_max"), "annee_min": _q(qs, "annee_min"),
                    "annee_max": _q(qs, "annee_max"), "region": _q(qs, "region"),
                    "puissance_min": _q(qs, "puissance_min"), "puissance_max": _q(qs, "puissance_max"),
                    "options": [o for o in (_q(qs, "options", "") or "").split(",") if o],
                    "carburants": [c for c in (_q(qs, "carburants", "") or "").split(",") if c],
                    "tri": _q(qs, "tri", "pertinence"), "page": _q(qs, "page", "1"),
                    "_repli": _q(qs, "repli") == "1",
                    "_differe": _q(qs, "differe") == "1",
                }
                return self._json(MOTEUR.run(MOTEUR.rechercher(_q(qs, "source", ""), q)))
        except Exception as e:  # erreur lisible côté interface
            return self._json({"erreur": type(e).__name__, "message": str(e)[:300]}, 500)
        return super().do_GET()

    def _photo(self, cle: str, largeur: int = 1280):
        meta = _meta_photos().get(cle)
        if not meta or largeur not in LARGEURS_PHOTOS:
            self.send_response(404)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        try:
            donnees, ctype = photo_en_cache(cle, largeur)
        except Exception:                       # téléchargement impossible : on renvoie vers la photo d'origine
            self.send_response(302)
            self.send_header("Location", meta["img"])
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "public, max-age=2592000, immutable")
        self.send_header("Content-Length", str(len(donnees)))
        self.end_headers()
        self.wfile.write(donnees)

    def do_POST(self):
        if not self._autorise():      # lecture des fiches : non comptée (elle découle d'une recherche déjà comptée)
            return
        u = urlparse(self.path)
        try:
            n = int(self.headers.get("Content-Length") or 0)
            corps = json.loads(self.rfile.read(n) or b"{}") if n else {}
            if u.path == "/api/fiches":
                liens = [l for l in corps.get("liens") or [] if isinstance(l, str)][:12]
                return self._json(MOTEUR.run(MOTEUR.fiches(corps.get("source", ""), liens), timeout=240))
        except Exception as e:
            return self._json({"erreur": type(e).__name__, "message": str(e)[:300]}, 500)
        self.send_response(404)
        self.end_headers()

    def log_message(self, fmt, *args):
        if "/api/recherche" in str(args[0] if args else ""):   # args[0] peut être un code HTTP (erreurs)
            super().log_message(fmt, *args)


def main() -> None:
    global MOTEUR
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=int(os.environ.get("AUTORADAR_PORT") or os.environ.get("PORT") or 8000))
    ap.add_argument("--hote", default=os.environ.get("AUTORADAR_HOTE", "127.0.0.1"))
    ap.add_argument("--visible", action="store_true", help="mode navigateur, fenêtre Chrome affichée")
    ap.add_argument("--navigateur", action="store_true", help="passe par Chrome (Playwright) au lieu de requêtes directes")
    ap.add_argument("--no-browser", action="store_true", help="n'ouvre pas l'interface automatiquement")
    args = ap.parse_args()

    if args.hote not in ("127.0.0.1", "localhost") and not MOT_DE_PASSE and not PUBLIC:
        raise SystemExit("Refus de démarrer : site accessible depuis le réseau sans mot de passe. "
                         "Définissez AUTORADAR_MOT_DE_PASSE, ou AUTORADAR_PUBLIC=1 pour un site ouvert à tous.")

    from recherche_live import Moteur
    mode = "navigateur" if (args.navigateur or args.visible) else None
    MOTEUR = Moteur(visible=args.visible, mode=mode)
    MOTEUR.prechauffer()  # ouvre les onglets des sites en arrière-plan : 1re recherche plus rapide
    prechauffer_photos()  # photos du guide d'achat

    url = f"http://localhost:{args.port}"
    server = ThreadingHTTPServer((args.hote, args.port), Handler)
    print(f"La Bonne Occaz sur {url}  — {MOTEUR.navigateur}  (Ctrl+C pour arrêter)", flush=True)
    if not args.no_browser and args.hote in ("127.0.0.1", "localhost"):
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nArrêt…")
    finally:
        MOTEUR.arreter()


if __name__ == "__main__":
    main()
