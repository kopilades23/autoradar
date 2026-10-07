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
import json
import os
import threading
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
            jour = time.strftime("%Y-%m-%d", time.gmtime(max((STATIC_DIR / (p.strip("/") or "index.html")).stat().st_mtime
                                                               for p in PAGES_PUBLIQUES)))
            urls = "".join(f"  <url><loc>https://{DOMAINE}{p}</loc><lastmod>{jour}</lastmod>"
                           f"<priority>{'1.0' if p == '/' else '0.6'}</priority></url>\n"
                           for p in PAGES_PUBLIQUES)
            return self._texte('<?xml version="1.0" encoding="UTF-8"?>\n'
                               '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + urls + "</urlset>\n",
                               "application/xml")
        if not self._autorise():
            return
        if self.path.startswith(("/api/recherche", "/api/modeles")) and self._limite():
            return
        u = urlparse(self.path)
        qs = parse_qs(u.query)
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
