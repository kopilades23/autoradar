"""Barre de navigation commune (guide, aide, pages légales) : copie exacte de celle de l'accueil."""

LOGO_SVG = ('<svg viewBox="0 0 38 38" fill="none"><g transform="translate(7 7)"><path d="M1.6 16.7v-3.6c0-1 .7-1.9 1.7-2.1l2.1-3.5c.4-.7 1.1-1.1 1.9-1.1h7.4c.8 0 1.5.4 1.9 1.1l2.1 3.5c1 .2 1.7 1.1 1.7 2.1v3.6c0 .6-.4 1-1 1H2.6c-.6 0-1-.4-1-1z" fill="#fff"/>'
            '<path d="M6.6 10.9l1.7-2.9h7.4l1.7 2.9z" fill="#ff5b1f"/><rect x="3.4" y="17" width="3.4" height="3" rx="1.1" fill="#fff"/><rect x="17.2" y="17" width="3.4" height="3" rx="1.1" fill="#fff"/></g></svg>')

COEUR = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"><path d="M12 20.5s-7.5-4.6-9.3-9.2C1.4 8 3.4 4.5 7 4.5c2 0 3.6 1.1 5 2.9 1.4-1.8 3-2.9 5-2.9 3.6 0 5.6 3.5 4.3 6.8-1.8 4.6-9.3 9.2-9.3 9.2z"/></svg>')


def entete(actif: str = "") -> str:
    """actif : "guide" ou "faq" pour surligner la page en cours."""
    cur = lambda k: ' aria-current="page"' if k == actif else ""
    return f'''<div class="lbo-cont">
    <header class="lbo-entete">
      <a href="/" class="lbo-brand" aria-label="La Bonne Occaz — accueil">
        <span class="logo-mark" aria-hidden="true"><span class="logo-sweep"></span>{LOGO_SVG}</span>
        <span class="lbo-nom"><span class="wordmark">La Bonne</span> <span class="wordmark-accent">Occaz</span></span>
      </a>
      <nav class="lbo-nav" aria-label="Navigation principale">
        <a href="/guide/"{cur("guide")}>Guide<span class="lbo-sm"> d'achat</span></a>
        <a href="/faq.html"{cur("faq")}>Aide<span class="lbo-md"> &amp; FAQ</span></a>
        <a href="/#favoris" class="lbo-fav" aria-label="Mes favoris">{COEUR}<span class="lbo-sm">Favoris</span><span class="lbo-nb" id="nbFavoris" hidden></span></a>
        <a href="/" class="lbo-btn">Nouvelle recherche</a>
      </nav>
    </header>
  </div>
  <script>try{{var n=Object.keys(JSON.parse(localStorage.getItem("autoradar.favoris")||"{{}}")||{{}}).length,e=document.getElementById("nbFavoris");if(n){{e.textContent=n;e.hidden=false}}}}catch(_){{}}</script>
  <div class="lbo-spot" aria-hidden="true"></div>
  <script>(function(){{if(!matchMedia("(hover: hover) and (pointer: fine)").matches)return;
    var spot=document.querySelector(".lbo-spot"),raf=0,ev=null,SEL=".carte-mod,.carte-cl,.tuiles>*,.pile>*,.regles li,.cote>*,.lueur";
    document.addEventListener("DOMContentLoaded",function(){{document.querySelectorAll(SEL).forEach(function(b){{b.classList.add("lueur")}})}});
    addEventListener("pointermove",function(e){{ev=e;if(raf)return;raf=requestAnimationFrame(function(){{raf=0;
      spot.style.setProperty("--sx",ev.clientX+"px");spot.style.setProperty("--sy",ev.clientY+"px");
      var b=ev.target.closest&&ev.target.closest(".lueur");if(b){{var r=b.getBoundingClientRect();b.style.setProperty("--x",(ev.clientX-r.left)+"px");b.style.setProperty("--y",(ev.clientY-r.top)+"px")}}}})}},{{passive:true}});}})();</script>'''


# mêmes mesures que la barre Tailwind de l'accueil (max-w-7xl, px-4 / sm:px-8, rounded-2xl, py-2.5…)
ENTETE_CSS = r"""
.lbo-spot{position:fixed;inset:0;z-index:0;pointer-events:none;background:radial-gradient(640px circle at var(--sx,78%) var(--sy,8%),rgba(255,91,31,.12),transparent 62%)}
.lueur{position:relative}
.lueur::after{content:"";position:absolute;inset:0;border-radius:inherit;padding:1px;pointer-events:none;
  background:radial-gradient(260px circle at var(--x,50%) var(--y,50%),rgba(255,91,31,.85),transparent 55%);
  -webkit-mask:linear-gradient(#000 0 0) content-box,linear-gradient(#000 0 0);-webkit-mask-composite:xor;mask-composite:exclude;opacity:0;transition:opacity .35s}
.lueur:hover::after{opacity:1}
html{scroll-padding-top:96px}
.lbo-cont{z-index:30;max-width:1280px;margin:0 auto;padding:0 16px;position:sticky;top:16px}
.lbo-entete{margin-top:16px;display:flex;align-items:center;justify-content:space-between;border-radius:16px;border:1px solid rgba(255,255,255,.08);
  background:rgba(11,11,14,.85);padding:10px 12px;box-shadow:0 10px 40px -20px rgba(0,0,0,.9);-webkit-backdrop-filter:blur(24px);backdrop-filter:blur(24px);
  font-family:Archivo,ui-sans-serif,system-ui,sans-serif;line-height:1.5}
.lbo-brand{display:flex;align-items:center;gap:12px;text-decoration:none;color:#fff}
.lbo-txt{display:flex;flex-direction:column;line-height:1}
.lbo-nom{font-stretch:125%;font-weight:800;font-size:15.5px;letter-spacing:-.01em;text-transform:uppercase;line-height:1}
.lbo-sous{display:none;margin-top:4px;font-family:Archivo,ui-monospace,monospace;font-size:9.5px;text-transform:uppercase;letter-spacing:.22em;color:#71717a}
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
@media (max-width:639px){.lbo-cont{top:8px}.lbo-entete{margin-top:8px;padding:6px 8px;border-radius:14px}.lbo-brand{gap:10px}.lbo-brand .logo-mark{width:30px;height:30px;border-radius:9px}.lbo-nom{font-size:12.5px;white-space:nowrap}.lbo-nav{font-size:12.5px}.lbo-nav a{padding:4px 8px}}
.logo-mark{position:relative;width:38px;height:38px;border-radius:12px;overflow:hidden;flex:none;
  background:#ff5b1f;box-shadow:0 10px 30px -12px rgba(255,91,31,.9),inset 0 1px 0 rgba(255,255,255,.3)}
.logo-mark svg{position:absolute;inset:0;width:100%;height:100%}
.logo-sweep{position:absolute;inset:0;transform:translateX(-130%);background:linear-gradient(115deg,transparent 30%,rgba(255,255,255,.5) 50%,transparent 70%);
  animation:reflet 1.6s cubic-bezier(.45,.05,.55,.95) .5s 1}
@keyframes reflet{to{transform:translateX(130%)}}
.logo-check{stroke-dasharray:16;animation:coche .6s cubic-bezier(.65,0,.35,1) .35s both}
@keyframes coche{from{stroke-dashoffset:16}to{stroke-dashoffset:0}}
.wordmark{color:#fff}
.wordmark-accent{color:#ff5b1f}
@media (prefers-reduced-motion:reduce){.logo-sweep,.logo-check{animation:none!important}}
"""
