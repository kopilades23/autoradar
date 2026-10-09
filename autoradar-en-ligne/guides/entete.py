"""Barre de navigation commune (guide, aide, pages légales) : copie exacte de celle de l'accueil."""

LOGO_SVG = ('<svg viewBox="0 0 64 64" fill="none"><g transform="translate(-2 3)"><path d="M8 41.5 v-6.5 c0-2.6 1.7-4.5 4.2-5 l5.8-9.6 c1.1-1.7 2.6-2.5 4.6-2.5 h18.8 c2 0 3.5.8 4.6 2.5 l5.8 9.6 c2.5.5 4.2 2.4 4.2 5 v6.5 c0 1.6-1.1 2.7-2.7 2.7 h-42.6 c-1.6 0-2.7-1.1-2.7-2.7z" fill="white"/>'
            '<path d="M19.5 30 l4.6-7.6 c.5-.8 1.2-1.2 2.1-1.2 h11.6 c.9 0 1.6.4 2.1 1.2 l4.6 7.6z" fill="#ff5f50"/><rect x="11.5" y="43" width="9" height="6.5" rx="2.2" fill="white"/>'
            '<rect x="43.5" y="43" width="9" height="6.5" rx="2.2" fill="white"/><circle cx="16.3" cy="36" r="2.6" fill="#ff5f50"/><circle cx="47.7" cy="36" r="2.6" fill="#ff5f50"/></g>'
            '<g class="logo-badge"><circle cx="50" cy="15" r="9.5" fill="white"/><path class="logo-check" d="M45.6 15.2 l3.1 3.1 l5.8-6" fill="none" stroke="#ff4d5a" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/></g></svg>')

COEUR = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"><path d="M12 20.5s-7.5-4.6-9.3-9.2C1.4 8 3.4 4.5 7 4.5c2 0 3.6 1.1 5 2.9 1.4-1.8 3-2.9 5-2.9 3.6 0 5.6 3.5 4.3 6.8-1.8 4.6-9.3 9.2-9.3 9.2z"/></svg>')


def entete(actif: str = "") -> str:
    """actif : "guide" ou "faq" pour surligner la page en cours."""
    cur = lambda k: ' aria-current="page"' if k == actif else ""
    return f'''<div class="lbo-cont">
    <header class="lbo-entete">
      <a href="/" class="lbo-brand" aria-label="La Bonne Occaz — accueil">
        <span class="logo-mark" aria-hidden="true"><span class="logo-sweep"></span>{LOGO_SVG}</span>
        <span class="lbo-txt"><span class="lbo-nom"><span class="wordmark">La Bonne</span> <span class="wordmark-accent">Occaz</span></span><span class="lbo-sous">Moteur de recherche d'occasions</span></span>
      </a>
      <nav class="lbo-nav" aria-label="Navigation principale">
        <a href="/guide/"{cur("guide")}>Guide<span class="lbo-sm"> d'achat</span></a>
        <a href="/faq.html" class="lbo-md"{cur("faq")}>Aide &amp; FAQ</a>
        <a href="/#favoris" class="lbo-fav" aria-label="Mes favoris">{COEUR}<span class="lbo-sm">Favoris</span><span class="lbo-nb" id="nbFavoris" hidden></span></a>
        <a href="/" class="lbo-btn">Nouvelle recherche</a>
      </nav>
    </header>
  </div>
  <script>try{{var n=Object.keys(JSON.parse(localStorage.getItem("autoradar.favoris")||"{{}}")||{{}}).length,e=document.getElementById("nbFavoris");if(n){{e.textContent=n;e.hidden=false}}}}catch(_){{}}</script>'''


# mêmes mesures que la barre Tailwind de l'accueil (max-w-7xl, px-4 / sm:px-8, rounded-2xl, py-2.5…)
ENTETE_CSS = r"""
html{scroll-padding-top:96px}
.lbo-cont{z-index:30;max-width:1280px;margin:0 auto;padding:0 16px;position:sticky;top:16px}
.lbo-entete{margin-top:16px;display:flex;align-items:center;justify-content:space-between;border-radius:16px;border:1px solid rgba(255,255,255,.08);
  background:rgba(11,11,14,.85);padding:10px 12px;box-shadow:0 10px 40px -20px rgba(0,0,0,.9);-webkit-backdrop-filter:blur(24px);backdrop-filter:blur(24px);
  font-family:"Geist",ui-sans-serif,system-ui,sans-serif;line-height:1.5}
.lbo-brand{display:flex;align-items:center;gap:12px;text-decoration:none;color:#fff}
.lbo-txt{display:flex;flex-direction:column;line-height:1}
.lbo-nom{font-size:17px;font-weight:600;letter-spacing:-.03em}
.lbo-sous{display:none;margin-top:4px;font-family:"Geist Mono",ui-monospace,monospace;font-size:9.5px;text-transform:uppercase;letter-spacing:.22em;color:#71717a}
.lbo-nav{display:flex;align-items:center;gap:4px;white-space:nowrap;font-size:13px;color:#a1a1aa}
.lbo-nav a{color:inherit;text-decoration:none;border-radius:8px;padding:6px 12px;transition:background-color .15s,color .15s,border-color .15s}
.lbo-nav a:hover,.lbo-nav a[aria-current]{background:rgba(255,255,255,.06);color:#fff}
.lbo-fav{display:inline-flex;align-items:center;gap:6px}.lbo-fav svg{width:16px;height:16px}
.lbo-nb{min-width:20px;border-radius:999px;background:#ff3d6e;padding:0 6px;text-align:center;font-size:11px;font-weight:600;line-height:20px;color:#fff}
.lbo-nb[hidden]{display:none}
.lbo-md{display:none}.lbo-sm{display:none}
.lbo-nav a.lbo-btn{display:none;margin-left:4px;border:1px solid rgba(255,255,255,.1);background:rgba(255,255,255,.04);color:#e4e4e7}
.lbo-nav a.lbo-btn:hover{border-color:rgba(255,255,255,.2);background:rgba(255,255,255,.1)}
@media (min-width:640px){.lbo-cont{padding:0 32px}.lbo-entete{padding:10px 16px}.lbo-sous{display:block}.lbo-sm{display:inline}.lbo-nav a.lbo-btn{display:inline-block}}
@media (min-width:768px){.lbo-md{display:inline}}
.logo-mark{position:relative;width:38px;height:38px;border-radius:12px;overflow:hidden;flex:none;
  background:linear-gradient(145deg,#ff7a3d,#ff3d6e);box-shadow:0 10px 30px -10px rgba(255,90,60,.8),inset 0 1px 0 rgba(255,255,255,.35)}
.logo-mark svg{position:absolute;inset:0;width:100%;height:100%}
.logo-sweep{position:absolute;inset:0;transform:translateX(-130%);background:linear-gradient(115deg,transparent 30%,rgba(255,255,255,.5) 50%,transparent 70%);
  animation:reflet 1.6s cubic-bezier(.45,.05,.55,.95) .5s 1}
@keyframes reflet{to{transform:translateX(130%)}}
.logo-check{stroke-dasharray:16;animation:coche .6s cubic-bezier(.65,0,.35,1) .35s both}
@keyframes coche{from{stroke-dashoffset:16}to{stroke-dashoffset:0}}
.wordmark{background:linear-gradient(180deg,#fff 0%,#d4d4d8 100%);-webkit-background-clip:text;background-clip:text;color:transparent}
.wordmark-accent{background:linear-gradient(120deg,#ff8a4c 0%,#ff4d6d 100%);-webkit-background-clip:text;background-clip:text;color:transparent}
@media (prefers-reduced-motion:reduce){.logo-sweep,.logo-check{animation:none!important}}
"""
