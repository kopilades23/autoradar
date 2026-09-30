"""
Accès aux sites SANS navigateur (mode « http », utilisé en ligne) : requêtes HTTP avec l'empreinte
TLS/HTTP2 de Chrome (curl_cffi), cookies conservés par site, pages analysées en Python (parseurs.py).
Mêmes réponses que les scripts exécutés dans les onglets Chrome du mode « navigateur ».
"""
from __future__ import annotations

import asyncio
import json
from typing import Any
from urllib.parse import quote

from curl_cffi.requests import AsyncSession

import parseurs

ENTETES = {"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
           "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.6"}


class TransportHttp:
    def __init__(self, leparking: str = "https://www.leparking.fr"):
        self.leparking = leparking
        self._sessions: dict[str, AsyncSession] = {}
        self._visites: set[str] = set()

    def _session(self, source: str) -> AsyncSession:
        s = self._sessions.get(source)
        if s is None:   # une session (cookies) par site, comme un onglet
            s = self._sessions[source] = AsyncSession(impersonate="chrome", timeout=20, headers=ENTETES)
        return s

    async def fermer(self) -> None:
        for s in self._sessions.values():
            try:
                await s.close()
            except Exception:
                pass

    async def _get(self, source: str, url: str, **kw):
        return await self._session(source).get(url, allow_redirects=True, **kw)

    async def appel(self, source: str, genre: str, arg: Any) -> dict:
        try:
            if genre == "leparking":
                return await self._leparking(arg[0])
            url = arg[0] if genre == "liste" else arg
            r = await self._get(source, url)
            h = r.text or ""
            if parseurs.BLOQUE.search(h[:30000]):
                return {"status": 429}
            if genre == "next":
                return {"status": r.status_code, "json": parseurs.next_data(h)}
            if genre == "liste":
                if r.status_code >= 400 and r.status_code != 404:
                    return {"status": r.status_code}
                _, motif, marque = arg
                res = await asyncio.to_thread(parseurs.extraire_liste, h, str(r.url or url), motif, marque)
                return {"status": r.status_code, **res}
            if genre == "fiche":
                if r.status_code >= 400:
                    return {"status": r.status_code}
                return {"status": r.status_code, **await asyncio.to_thread(parseurs.lire_fiche, h, url)}
        except Exception:
            return {"status": 0}
        return {"status": 0}

    async def _leparking(self, ctx: dict) -> dict:
        s = self._session("leparking")
        if "leparking" not in self._visites:   # 1re visite : cookies de session du site
            try:
                await s.get(self.leparking + "/")
            except Exception:
                pass
            self._visites.add("leparking")
        r = await s.post(self.leparking + "/index.php", data="ajax=" + quote(json.dumps(ctx)),
                         headers={"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                                  "X-Requested-With": "XMLHttpRequest", "Accept": "application/json, text/javascript, */*",
                                  "Referer": self.leparking + "/", "Origin": self.leparking})
        if r.status_code >= 400:
            return {"status": r.status_code}
        return await asyncio.to_thread(parseurs.leparking, r.text, self.leparking)
