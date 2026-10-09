"""Génère les pages statiques du guide d'achat dans static/guide/ (HTML pur, lisible par Google et les IA).

    python guides/generer.py

Les adresses sont « propres » : /guide/, /guide/peugeot-208, /guide/voiture-jeune-permis
(le serveur ajoute .html tout seul). Le plan du site (sitemap.xml) les liste automatiquement.
"""
from __future__ import annotations

import html
import json
import sys
from pathlib import Path
from urllib.parse import urlencode

sys.path.insert(0, str(Path(__file__).parent))
from donnees import CLASSEMENTS, MAJ, MAJ_TEXTE, MODELES  # noqa: E402
from entete import ENTETE_CSS, entete  # noqa: E402

DOMAINE = "https://labonneoccaz.fr"
# Photos libres de droits (Wikimedia Commons), servies par le site : /guide/photo/<cle>.webp
PHOTOS = json.loads((Path(__file__).with_name("photos.json")).read_text(encoding="utf-8"))
SORTIE = Path(__file__).resolve().parent.parent / "static" / "guide"
PAR_SLUG = {m["slug"]: m for m in MODELES}
e = html.escape

# --------------------------------------------------------------------------- silhouettes (dessins originaux)
CARROSSERIES = {
    "citadine": ("M20 74 L20 60 Q20 54 26 52 L40 50 L66 28 Q70 25 76 25 L140 25 Q148 25 154 30 L180 50 L210 55 Q222 57 222 66 L222 74 Q222 80 216 80 L26 80 Q20 80 20 74 Z",
                 ["M48 48 L68 31 Q71 29 75 29 L104 29 L104 48 Z", "M110 29 L139 29 Q145 29 149 33 L168 48 L110 48 Z"], (62, 180), 15),
    "compacte": ("M14 74 L14 60 Q14 54 20 52 L38 49 L68 27 Q72 24 78 24 L150 24 Q158 24 164 29 L192 49 L224 54 Q236 56 236 66 L236 74 Q236 80 230 80 L20 80 Q14 80 14 74 Z",
                 ["M46 47 L70 30 Q73 28 78 28 L112 28 L112 47 Z", "M118 28 L150 28 Q155 28 159 32 L181 47 L118 47 Z"], (60, 194), 16),
    "suv": ("M14 76 L14 50 Q14 44 20 42 L36 40 L56 20 Q60 16 68 16 L158 16 Q166 16 172 22 L192 40 L222 46 Q234 48 234 58 L234 76 Q234 82 228 82 L20 82 Q14 82 14 76 Z",
            ["M42 39 L60 22 Q62 20 66 20 L110 20 L110 39 Z", "M116 20 L158 20 Q163 20 167 24 L184 39 L116 39 Z"], (60, 192), 18),
    "berline": ("M12 74 L12 62 Q12 56 18 55 L44 52 L74 30 Q78 27 84 27 L146 27 Q154 27 160 32 L184 50 L222 55 Q234 57 234 66 L234 74 Q234 80 228 80 L18 80 Q12 80 12 74 Z",
                ["M58 50 L77 32 Q80 30 84 30 L116 30 L116 50 Z", "M122 30 L146 30 Q151 30 155 34 L173 50 L122 50 Z"], (58, 192), 16),
}


def silhouette(carrosserie: str, couleur: str, uid: str, classe: str = "car") -> str:
    corps, vitres, roues, r = CARROSSERIES[carrosserie]
    rails = '<path d="M62 12 L160 12" stroke="rgba(255,255,255,.35)" stroke-width="3" stroke-linecap="round"/>' if carrosserie == "suv" else ""
    v = "".join(f'<path d="{p}" fill="url(#v{uid})"/>' for p in vitres)
    w = "".join(f'<circle cx="{x}" cy="{80 if carrosserie != "suv" else 82}" r="{r}" fill="#0b0b0e"/>'
                f'<circle cx="{x}" cy="{80 if carrosserie != "suv" else 82}" r="{r * .5:.0f}" fill="#3f3f46"/>'
                f'<circle cx="{x}" cy="{80 if carrosserie != "suv" else 82}" r="{r * .18:.0f}" fill="#a1a1aa"/>' for x in roues)
    return (f'<svg class="{classe}" viewBox="0 0 250 104" role="img" aria-hidden="true">'
            f'<defs><linearGradient id="c{uid}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{couleur}"/>'
            f'<stop offset="1" stop-color="{couleur}" stop-opacity=".55"/></linearGradient>'
            f'<linearGradient id="v{uid}" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#1c2533"/><stop offset="1" stop-color="#0b0f16"/></linearGradient></defs>'
            f'<ellipse cx="125" cy="{94 if carrosserie == "suv" else 92}" rx="112" ry="6" fill="rgba(0,0,0,.45)"/>'
            f'{rails}<path d="{corps}" fill="url(#c{uid})"/>{v}'
            f'<path d="M24 64 L230 64" stroke="rgba(255,255,255,.18)" stroke-width="1.5"/>{w}</svg>')


TAILLES = {   # largeur d'affichage de chaque type d'image (le navigateur choisit le bon fichier, écrans Retina compris)
    "ph": "(max-width: 600px) 92vw, 300px", "ph-hero": "(max-width: 900px) 92vw, 540px", "ph-rang": "(max-width: 900px) 92vw, 230px",
    "ph-gen": "150px", "ph-cred": "120px", "ph v0": "380px", "ph v1": "380px", "ph v2": "380px",
}


def srcset(cle: str) -> str:
    return f"/guide/photo/480/{cle}.webp 480w, /guide/photo/800/{cle}.webp 800w, /guide/photo/{cle}.webp 1280w"


def photo(cle: str, alt: str, classe: str = "ph", credit: bool = False, prioritaire: bool = False) -> str:
    """Photo d'une génération précise, avec crédit (licences Creative Commons : auteur + licence + lien)."""
    p = PHOTOS.get(cle)
    if not p:
        return ""
    charge = 'fetchpriority="high"' if prioritaire else 'loading="lazy"'
    leg = (f'<p class="credit">Photo : <a href="{e(p["page"])}" rel="noopener nofollow" target="_blank">{e(p["auteur"])}</a>, '
           f'<a href="{e(p["licence_url"])}" rel="noopener nofollow license" target="_blank">{e(p["licence"])}</a> · Wikimedia Commons</p>') if credit else ""
    return (f'<figure class="{classe}"><img src="/guide/photo/800/{cle}.webp" srcset="{srcset(cle)}" sizes="{TAILLES.get(classe, "100vw")}"'
            f' alt="{e(alt)}" width="1280" height="740" {charge} decoding="async"'
            f' title="Photo : {e(p["auteur"])} ({e(p["licence"])}, Wikimedia Commons)"></figure>{leg}')


# --------------------------------------------------------------------------- briques communes
def url_recherche(m: dict, prix_max=None, options=None) -> str:
    p = {"marque": m["marque_id"], "marque_label": m["marque"], "modele": m["modele_cle"], "modele_label": m["modele"]}
    if prix_max:
        p["prix_max"] = prix_max
    if options:
        p["options"] = ",".join(options)
    return "/?" + urlencode(p)


def fiabilite(n: int) -> str:
    pts = "".join(f'<i class="{"on" if k < n else ""}"></i>' for k in range(5))
    return f'<span class="fiab" title="Fiabilité : {n}/5" aria-label="Fiabilité {n} sur 5">{pts}</span>'


UMAMI = ('<script defer src="https://cloud.umami.is/script.js" data-website-id="d5a85375-aefc-4f50-9d56-38882c7c00f2" '
         'data-domains="labonneoccaz.fr,www.labonneoccaz.fr"></script>')


def page(chemin: str, titre: str, description: str, corps: str, jsonld: list, image: str = "/icone-512.png") -> str:
    url = DOMAINE + chemin
    ld = "".join(f'<script type="application/ld+json">{json.dumps(x, ensure_ascii=False)}</script>' for x in jsonld)
    ENTETE = entete("guide")
    return f"""<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{e(titre)}</title>
  <meta name="description" content="{e(description)}" />
  <link rel="canonical" href="{url}" />
  <meta name="theme-color" content="#08080a" />
  <meta property="og:type" content="article" />
  <meta property="og:site_name" content="La Bonne Occaz" />
  <meta property="og:locale" content="fr_FR" />
  <meta property="og:title" content="{e(titre)}" />
  <meta property="og:description" content="{e(description)}" />
  <meta property="og:url" content="{url}" />
  <meta property="og:image" content="{DOMAINE}{image}" />
  <link rel="icon" href="/icone-192.png" />
  <link rel="apple-touch-icon" href="/icone-180.png" />
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@62..125,300..900&display=swap" rel="stylesheet" />
  <link rel="stylesheet" href="/guide/guide.css" />
  {UMAMI}
  {ld}
</head>
<body>
  <div class="halo" aria-hidden="true"></div>
  {ENTETE}
  <main>
{corps}
  </main>
  <footer class="pied">
    <div>
      <p class="brand-pied">La Bonne <b>Occaz</b></p>
      <p>Moteur de recherche de voitures d'occasion : Leboncoin, La Centrale, AutoScout24, L'argus, ParuVendu et d'autres sites en une seule recherche.</p>
    </div>
    <nav aria-label="Guides">
      <p class="titre-pied">Guides</p>
      {"".join(f'<a href="/guide/{c["slug"]}">{e(c["court"])}</a>' for c in CLASSEMENTS)}
      <a href="/guide/">Toutes les fiches modèles</a>
      <a href="/guide/credits-photos">Crédits photos</a>
    </nav>
    <nav aria-label="Informations">
      <p class="titre-pied">Informations</p>
      <a href="/faq.html">Aide &amp; FAQ</a><a href="/mentions-legales.html">Mentions légales</a>
      <a href="/confidentialite.html">Confidentialité</a><a href="/conditions.html">Conditions d'utilisation</a>
    </nav>
  </footer>
</body>
</html>
"""


def fil(*etapes) -> tuple[str, dict]:
    """Fil d'Ariane visible + données structurées BreadcrumbList."""
    items = [("Accueil", "/")] + list(etapes)
    visible = " <span>/</span> ".join(f'<a href="{u}">{e(n)}</a>' if u else f'<span aria-current="page">{e(n)}</span>' for n, u in items)
    ld = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": n, **({"item": DOMAINE + u} if u else {})} for i, (n, u) in enumerate(items)]}
    return f'<nav class="fil" aria-label="Fil d\'Ariane">{visible}</nav>', ld


def article_ld(titre: str, description: str, chemin: str, cle_photo: str = None) -> dict:
    org = {"@type": "Organization", "name": "La Bonne Occaz", "url": DOMAINE + "/",
           "logo": {"@type": "ImageObject", "url": DOMAINE + "/icone-512.png"}}
    return {"@context": "https://schema.org", "@type": "Article", "headline": titre, "description": description,
            "inLanguage": "fr-FR", "datePublished": MAJ, "dateModified": MAJ, "mainEntityOfPage": DOMAINE + chemin,
            "image": DOMAINE + (f"/guide/photo/{cle_photo}.webp" if cle_photo else "/icone-512.png"), "author": org, "publisher": org}


def faq_ld(faq: list) -> dict:
    return {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": r}} for q, r in faq]}


def carte_modele(m: dict, uid: str) -> str:
    return f"""<a class="carte-mod" href="/guide/{m['slug']}" style="--c:{m['couleur']}">
        <div class="carte-vis">{photo(m['photo'], f"{m['marque']} {m['modele']} d'occasion") or silhouette(m['carrosserie'], m['couleur'], uid)}</div>
        <div class="carte-txt"><p class="cat">{e(m['categorie'])}</p><h3>{e(m['marque'])} {e(m['modele'])}</h3>
        <p class="ligne">{fiabilite(m['fiabilite'])}<span>{e(m['budget'])}</span></p></div></a>"""


ICONES = {
    "voiture-jeune-permis": '<path d="M4 18h16M6 18V9l6-4 6 4v9"/><path d="M10 18v-5h4v5"/>',
    "voiture-occasion-moins-10000-euros": '<circle cx="12" cy="12" r="8"/><path d="M15 9.5a3.5 3.5 0 1 0 0 5M8 11h5M8 13h5"/>',
    "voiture-occasion-moins-20000-euros": '<path d="M5 16l1.5-5A2 2 0 0 1 8.4 9.5h7.2a2 2 0 0 1 1.9 1.5L19 16"/><path d="M4 16h16v3H4zM7 19v1.5M17 19v1.5"/>',
    "voiture-occasion-moins-30000-euros": '<path d="M12 3l2.6 5.6 6 .7-4.5 4.1 1.2 6L12 16.5 6.7 19.4l1.2-6L3.4 9.3l6-.7z"/>',
    "voitures-occasion-les-plus-fiables": '<path d="M12 3l8 3v6c0 4.5-3.4 8.3-8 9-4.6-.7-8-4.5-8-9V6z"/><path d="m8.5 12 2.5 2.5 4.5-5"/>',
}


def carte_classement(c: dict) -> str:
    return f"""<a class="carte-cl" href="/guide/{c['slug']}" style="--c:{c['couleur']}">
        <span class="ico"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">{ICONES[c['slug']]}</svg></span>
        <span class="cl-txt"><b>{e(c['court'])}</b><small>{len(c['liste'])} modèles sélectionnés</small></span>
        <svg class="fl" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M5 12h14M13 6l6 6-6 6"/></svg></a>"""


# --------------------------------------------------------------------------- pages
def page_modele(m: dict) -> str:
    nom = f"{m['marque']} {m['modele']}"
    chemin = f"/guide/{m['slug']}"
    titre = f"{nom} d'occasion : moteurs fiables et à éviter"
    desc = f"{nom} d'occasion : quels moteurs choisir, pannes connues et points à vérifier avant d'acheter. Guide {MAJ_TEXTE[-4:]}."
    fil_html, fil_ld = fil(("Guide d'achat", "/guide/"), (nom, None))
    def gen(x):
        vignette = photo(x[2], f"{m['marque']} {x[0]}", "ph-gen") if len(x) > 2 else ""
        return f'<li class="{"avec-ph" if vignette else ""}">{vignette}<div><b>{e(x[0])}</b><span>{e(x[1])}</span></div></li>'
    gens = "".join(gen(x) for x in m["generations"])
    ok = "".join(f'<li><svg viewBox="0 0 24 24"><path d="m5 12 4.5 4.5L19 7"/></svg><div><b>{e(a)}</b><p>{e(b)}</p></div></li>' for a, b in m["conseilles"])
    ko = "".join(f'<li><svg viewBox="0 0 24 24"><path d="M12 8v5M12 16.5v.5"/><path d="M10.3 3.9 2.6 17.5A2 2 0 0 0 4.3 20.5h15.4a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/></svg><div><b>{e(a)}</b><p>{e(b)}</p></div></li>' for a, b in m["surveiller"])
    chk = "".join(f'<li>{e(v)}</li>' for v in m["verifier"])
    opts = "".join(f'<a class="puce" href="{e(url_recherche(m, options=[o]))}">{e(nom)} avec {e(o)}</a>' for o in m["options"])
    faq = "".join(f'<details><summary>{e(q)}</summary><p>{e(r)}</p></details>' for q, r in m["faq"])
    dans = [c for c in CLASSEMENTS if any(x[0] == m["slug"] for x in c["liste"])]
    dans_html = "".join(carte_classement(c) for c in dans)
    proches = [x for x in MODELES if x["slug"] != m["slug"] and x["carrosserie"] == m["carrosserie"]][:4] or MODELES[:4]
    proches_html = "".join(carte_modele(x, f"p{i}") for i, x in enumerate(proches))
    corps = f"""
    {fil_html}
    <section class="hero-mod" style="--c:{m['couleur']}">
      <div class="hero-txt">
        <p class="kicker">{e(m['categorie'])} · Guide d'achat</p>
        <h1>{e(nom)} d'occasion : <span>quels moteurs choisir ?</span></h1>
        <p class="lead">{e(m['resume'])}</p>
        <div class="tuiles">
          <div><small>Fiabilité (notre avis)</small>{fiabilite(m['fiabilite'])}</div>
          <div><small>Budget courant</small><b>{e(m['budget'])}</b></div>
          <div class="large"><small>Moteur conseillé</small><b>{e(m['conseilles'][0][0])}</b></div>
        </div>
        <div class="actions">
          <a class="btn" href="{e(url_recherche(m))}">Voir les annonces {e(nom)} <svg viewBox="0 0 24 24"><path d="M5 12h14M13 6l6 6-6 6"/></svg></a>
          <span class="note">Leboncoin, La Centrale, AutoScout24… en une recherche</span>
        </div>
      </div>
      <div class="hero-vis">{photo(m['photo'], f"{nom} d'occasion", "ph-hero", credit=True, prioritaire=True) or silhouette(m['carrosserie'], m['couleur'], 'h', 'car big')}</div>
    </section>

    <div class="grille-art">
      <article class="contenu">
        <h2>Les générations de {e(nom)}</h2>
        <ul class="gens">{gens}</ul>

        <h2>Les moteurs à privilégier</h2>
        <ul class="avis ok">{ok}</ul>

        <h2>Les points faibles à surveiller</h2>
        <ul class="avis ko">{ko}</ul>

        <h2>Que vérifier avant d'acheter une {e(nom)} ?</h2>
        <ul class="check">{chk}</ul>

        <h2>Trouver une {e(nom)} bien équipée</h2>
        <p>La Bonne Occaz lit la description de chaque annonce pour repérer les options. Un clic lance la recherche :</p>
        <div class="puces">{opts}</div>

        <h2>Questions fréquentes</h2>
        <div class="faq">{faq}</div>

        <p class="avert">Ces conseils résument des tendances connues et des pannes fréquemment signalées : ils ne remplacent pas
        l'inspection du véhicule. Demandez toujours les factures d'entretien et, au moindre doute, faites contrôler la voiture
        par un professionnel. Mise à jour : {MAJ_TEXTE}.</p>
      </article>
      <aside class="cote">
        <div class="box cta-box" style="--c:{m['couleur']}">
          <p class="kicker">Annonces en direct</p>
          <p class="cta-titre">{e(nom)} d'occasion</p>
          <a class="btn plein" href="{e(url_recherche(m))}">Toutes les annonces</a>
          <a class="lien" href="{e(url_recherche(m, prix_max=10000))}">Moins de 10 000 €</a>
          <a class="lien" href="{e(url_recherche(m, prix_max=15000))}">Moins de 15 000 €</a>
          <a class="lien" href="{e(url_recherche(m, prix_max=20000))}">Moins de 20 000 €</a>
        </div>
        {f'<div class="box"><p class="kicker">Dans nos classements</p><div class="pile">{dans_html}</div></div>' if dans else ''}
      </aside>
    </div>

    <section class="bloc">
      <h2 class="h-sec">Modèles similaires</h2>
      <div class="grille-mod">{proches_html}</div>
    </section>
"""
    return page(chemin, titre, desc, corps, [article_ld(titre, desc, chemin, m["photo"]), fil_ld, faq_ld(m["faq"])],
                image=f"/guide/photo/{m['photo']}.webp")


def page_classement(c: dict) -> str:
    chemin = f"/guide/{c['slug']}"
    titre = f"{c['titre']} ({MAJ_TEXTE[-4:]})"
    fil_html, fil_ld = fil(("Guide d'achat", "/guide/"), (c["court"], None))
    lignes = []
    for i, (slug, version, pourquoi, cle_ph) in enumerate(c["liste"], 1):
        m = PAR_SLUG[slug]
        nom = f"{m['marque']} {m['modele']}"
        lignes.append(f"""<li class="rang" style="--c:{m['couleur']}">
          <span class="num">{i}</span>
          <div class="rang-vis">{photo(cle_ph, f"{nom} – {version}", "ph-rang", prioritaire=i == 1) or silhouette(m['carrosserie'], m['couleur'], f'r{i}')}</div>
          <div class="rang-txt">
            <h2><a href="/guide/{slug}">{e(nom)}</a></h2>
            <p class="version">Version conseillée : <b>{e(version)}</b></p>
            <p>{e(pourquoi)}</p>
            <p class="ligne">{fiabilite(m['fiabilite'])}<span>{e(m['budget'])}</span></p>
          </div>
          <div class="rang-act">
            <a class="btn petit" href="{e(url_recherche(m, prix_max=c['prix_max']))}">Voir les annonces{f" &lt; {c['prix_max'] // 1000} k€" if c['prix_max'] else ''}</a>
            <a class="lien" href="/guide/{slug}">Lire la fiche</a>
          </div>
        </li>""")
    criteres = "".join(f"<li>{e(x)}</li>" for x in c["criteres"])
    autres = "".join(carte_classement(x) for x in CLASSEMENTS if x["slug"] != c["slug"])
    corps = f"""
    {fil_html}
    <section class="hero-cl" style="--c:{c['couleur']}">
      <p class="kicker">Classement · mis à jour en {MAJ_TEXTE}</p>
      <h1>{e(c['titre'])}</h1>
      <p class="lead">{e(c['intro'])}</p>
      <div class="box crit"><p class="kicker">Nos critères</p><ul class="check">{criteres}</ul></div>
    </section>
    <ol class="classement">{''.join(lignes)}</ol>
    <p class="avert">Classement indicatif établi à partir de la réputation des modèles et de leurs moteurs. Les prix varient selon
    l'année, le kilométrage et l'état : les boutons « Voir les annonces » affichent les offres réelles du moment.
    Photos : Wikimedia Commons, licences libres (<a href="/guide/credits-photos">crédits</a>).</p>
    <section class="bloc"><h2 class="h-sec">Autres classements</h2><div class="grille-cl">{autres}</div></section>
"""
    item_list = {"@context": "https://schema.org", "@type": "ItemList", "name": c["titre"], "itemListOrder": "https://schema.org/ItemListOrderAscending",
                 "numberOfItems": len(c["liste"]), "itemListElement": [
                     {"@type": "ListItem", "position": i, "name": f"{PAR_SLUG[s]['marque']} {PAR_SLUG[s]['modele']} – {v}",
                      "url": f"{DOMAINE}/guide/{s}", "image": f"{DOMAINE}/guide/photo/{ph}.webp"} for i, (s, v, _, ph) in enumerate(c["liste"], 1)]}
    return page(chemin, titre, c["description"], corps, [article_ld(titre, c["description"], chemin, c["liste"][0][3]), fil_ld, item_list],
                image=f"/guide/photo/{c['liste'][0][3]}.webp")


FAQ_GUIDE = [
    ("Quelle est la voiture d'occasion la plus fiable ?", "Les hybrides Toyota (Yaris, Corolla, C-HR) sont régulièrement citées parmi les plus fiables. En diesel, les moteurs éprouvés comme le 1.5 dCi Renault/Dacia ou le 2.0 TDI Volkswagen ont aussi très bonne réputation."),
    ("Quel kilométrage maximum pour une voiture d'occasion ?", "Il n'y a pas de limite absolue : un moteur bien entretenu à 150 000 km vaut mieux qu'un moteur négligé à 80 000 km. Exigez le carnet et les factures."),
    ("Diesel ou essence en occasion ?", "Le diesel reste intéressant au-delà de 20 000 km par an et sur route. En ville et pour de petits trajets, préférez l'essence ou l'hybride, et vérifiez les restrictions des zones à faibles émissions (ZFE)."),
    ("Comment éviter une voiture avec une panne cachée ?", "Lisez toute la description : La Bonne Occaz repère automatiquement les mentions comme « moteur HS », « turbo à changer » ou « pour pièces » et peut masquer ces véhicules."),
]


def page_index() -> str:
    chemin = "/guide/"
    titre = f"Guide d'achat voiture d'occasion {MAJ_TEXTE[-4:]} : modèles fiables"
    desc = "Quelle voiture d'occasion acheter ? Moteurs fiables, pannes connues et classements : jeune permis, moins de 10 000 €, 20 000 €, 30 000 €."
    fil_html, fil_ld = fil(("Guide d'achat", None))
    cats = {}
    for m in MODELES:
        cats.setdefault({"citadine": "Citadines", "compacte": "Compactes", "suv": "SUV", "berline": "Familiales & électriques"}[m["carrosserie"]], []).append(m)
    grilles = "".join(f'<h3 class="h-cat"><span>{e(k)}</span><small>{len(v)} modèle{"s" if len(v) > 1 else ""}</small></h3>'
                      f'<div class="grille-mod">{"".join(carte_modele(m, f"{k[:2]}{i}") for i, m in enumerate(v))}</div>'
                      for k, v in cats.items())
    regles = [("Le moteur compte plus que le modèle", "Une même voiture peut être excellente ou à éviter selon sa motorisation : lisez la fiche avant d'acheter."),
              ("Exigez les factures", "Carnet tamponné, factures de distribution, de vidange : sans historique, négociez fort ou passez votre chemin."),
              ("Lisez toute l'annonce", "Les pannes se cachent souvent en bas de la description. La Bonne Occaz les repère pour vous."),
              ("Comparez sur tous les sites", "Le même modèle peut coûter 2 000 € de moins sur un autre site : une seule recherche suffit ici."),
              ("Essayez à froid", "Un démarrage moteur froid révèle bruits de chaîne, fumées et voyants.")]
    regles_html = "".join(f'<li><span>{i}</span><div><b>{e(t)}</b><p>{e(d)}</p></div></li>' for i, (t, d) in enumerate(regles, 1))
    faq = "".join(f'<details><summary>{e(q)}</summary><p>{e(r)}</p></details>' for q, r in FAQ_GUIDE)
    vitrine = "".join(photo(k, alt, f"ph v{i}", prioritaire=True) for i, (k, alt) in
                      enumerate([("yaris-4", "Toyota Yaris hybride"), ("3008-2", "Peugeot 3008"), ("golf-7", "Volkswagen Golf 7")]))
    corps = f"""
    {fil_html}
    <section class="hero-guide">
      <div>
        <p class="kicker">Guide d'achat · {MAJ_TEXTE}</p>
        <h1>Quelle voiture d'occasion <span>acheter ?</span></h1>
        <p class="lead">Les bons modèles, les moteurs fiables, ceux qui posent problème et ce qu'il faut vérifier avant de signer.
        Puis un clic pour voir toutes les annonces du moment, sur tous les sites.</p>
        <div class="grille-cl">{''.join(carte_classement(c) for c in CLASSEMENTS)}</div>
      </div>
      <div class="vitrine">{vitrine}</div>
    </section>

    <section class="bloc">
      <h2 class="h-sec">Fiches modèles</h2>
      <p class="sous">Générations, moteurs à privilégier, pannes connues : l'essentiel pour acheter sereinement.</p>
      {grilles}
      <p class="avert">Photos : Wikimedia Commons, licences libres Creative Commons (<a href="/guide/credits-photos">crédits photos</a>).</p>
    </section>

    <section class="bloc deux">
      <div>
        <h2 class="h-sec">Les 5 règles d'or</h2>
        <ol class="regles">{regles_html}</ol>
      </div>
      <div>
        <h2 class="h-sec">Questions fréquentes</h2>
        <div class="faq">{faq}</div>
      </div>
    </section>
"""
    coll = {"@context": "https://schema.org", "@type": "CollectionPage", "name": titre, "description": desc, "url": DOMAINE + chemin,
            "inLanguage": "fr-FR", "dateModified": MAJ,
            "hasPart": [{"@type": "Article", "name": f"{m['marque']} {m['modele']} d'occasion", "url": f"{DOMAINE}/guide/{m['slug']}"} for m in MODELES]
                       + [{"@type": "Article", "name": c["titre"], "url": f"{DOMAINE}/guide/{c['slug']}"} for c in CLASSEMENTS]}
    return page(chemin, titre, desc, corps, [coll, fil_ld, faq_ld(FAQ_GUIDE)])


CSS = r"""
:root{color-scheme:dark;--bg:#08080a;--fg:#e4e4e7;--mut:#a1a1aa;--dim:#71717a;--line:rgba(255,255,255,.08);--card:rgba(255,255,255,.03);--acc:#ff5b1f}
*{box-sizing:border-box}html{-webkit-text-size-adjust:100%;overflow-x:clip}
body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.65 Archivo,ui-sans-serif,system-ui,sans-serif;-webkit-font-smoothing:antialiased;overflow-x:clip}
a{color:inherit}
.halo{position:fixed;inset:0;pointer-events:none;z-index:0;background:radial-gradient(60vmax 40vmax at 90% -10%,rgba(255,106,43,.14),transparent 60%),radial-gradient(50vmax 40vmax at -10% 10%,rgba(109,74,255,.10),transparent 60%)}
main,footer.pied{position:relative;z-index:1;max-width:1280px;margin:0 auto;padding-left:16px;padding-right:16px}
@media (min-width:640px){main,footer.pied{padding-left:32px;padding-right:32px}}
.brand{display:inline-flex;align-items:center;gap:10px;white-space:nowrap;text-decoration:none;font-weight:600;letter-spacing:-.02em;font-size:17px;color:#fff}
.brand b,.brand-pied b{color:#ff5b1f;font-weight:600}
.fil{font-size:13px;color:var(--dim);margin:18px 0 8px}.fil a{color:var(--mut);text-decoration:none}.fil a:hover{color:#fff}.fil span{margin:0 4px}
.kicker{font-family:Archivo,ui-monospace,monospace;font-size:11px;letter-spacing:.2em;text-transform:uppercase;color:var(--acc);margin:0 0 10px}
h1{font-size:clamp(2rem,5vw,3.4rem);line-height:1;letter-spacing:-.03em;margin:0 0 16px;color:#fff;font-weight:800;font-stretch:118%}
h1 span{color:#ff5b1f}
h2{color:#fff;letter-spacing:-.02em;line-height:1.15;font-stretch:112%;font-weight:750}
.lead{font-size:1.1rem;color:var(--mut);max-width:62ch;margin:0 0 22px}
.btn{display:inline-flex;align-items:center;gap:8px;text-decoration:none;font-weight:600;color:#fff;padding:12px 18px;border-radius:14px;
  background:#ff5b1f;box-shadow:0 12px 30px -12px rgba(255,80,60,.7);transition:transform .2s}
.btn:hover{transform:translateY(-1px)}.btn svg{width:18px;height:18px;fill:none;stroke:currentColor;stroke-width:2.2;stroke-linecap:round;stroke-linejoin:round}
.btn.petit{padding:9px 14px;font-size:14px;border-radius:12px}.btn.plein{width:100%;justify-content:center}
.lien{display:block;color:var(--mut);text-decoration:none;font-size:14px;padding:6px 0}.lien:hover{color:#fff}
.note{font-size:13px;color:var(--dim)}
.actions{display:flex;flex-wrap:wrap;align-items:center;gap:14px}
.fiab{display:inline-flex;gap:4px;vertical-align:middle}.fiab i{width:9px;height:9px;border-radius:50%;background:rgba(255,255,255,.14)}
.fiab i.on{background:linear-gradient(135deg,#7ae38a,#2fbf71);box-shadow:0 0 8px rgba(80,220,130,.45)}
.car{width:100%;height:auto;display:block}
/* Photos */
figure.ph,figure.ph-hero,figure.ph-gen,figure.ph-rang,figure.ph-cred{margin:0;position:relative;overflow:hidden;background:#141418}
figure img{display:block;width:100%;height:100%;object-fit:cover}
.credit{margin:8px 4px 0;font-size:11.5px;color:var(--dim);text-align:right}.credit a{color:inherit;text-decoration:none}.credit a:hover{color:#fff;text-decoration:underline}
.avert a{color:var(--mut)}
.carte-vis figure.ph{aspect-ratio:16/10;border-radius:0}
.carte-mod .carte-vis{padding:0;background:none}
.carte-mod figure img{transition:transform .5s cubic-bezier(.16,1,.3,1)}.carte-mod:hover figure img{transform:scale(1.04)}
figure.ph-hero{aspect-ratio:16/10;border-radius:26px;box-shadow:0 30px 60px -25px rgba(0,0,0,.8),0 0 0 1px rgba(255,255,255,.06)}
figure.ph-rang{aspect-ratio:16/10;border-radius:14px}
.gens li.avec-ph{display:flex;gap:14px;align-items:flex-start}
figure.ph-gen{flex:none;width:150px;aspect-ratio:16/10;border-radius:12px}
.credits{list-style:none;padding:0;margin:24px 0;display:grid;gap:10px}
.credits li{display:flex;gap:14px;align-items:center;padding:10px;border-radius:14px;background:var(--card);border:1px solid var(--line)}
figure.ph-cred{flex:none;width:120px;aspect-ratio:16/10;border-radius:10px}.credits b{color:#fff;font-size:14px;word-break:break-word}.credits p{margin:2px 0 0;color:var(--mut);font-size:13px}
/* Accueil du guide */
.hero-guide{display:grid;grid-template-columns:1.25fr .75fr;gap:32px;align-items:center;padding:12px 0 24px}
.vitrine{position:relative;min-height:360px}
.vitrine figure{position:absolute;width:70%;aspect-ratio:16/10;border-radius:20px;box-shadow:0 24px 50px -20px rgba(0,0,0,.85),0 0 0 1px rgba(255,255,255,.08)}
.vitrine .v0{top:0;right:0}.vitrine .v1{top:28%;left:0;z-index:2}.vitrine .v2{top:56%;right:2%}
.grille-cl{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:10px}
.carte-cl{display:flex;align-items:center;gap:12px;padding:12px 14px;border-radius:16px;text-decoration:none;background:var(--card);border:1px solid var(--line);transition:border-color .2s,background .2s}
.carte-cl:hover{border-color:color-mix(in srgb,var(--c) 55%,transparent);background:color-mix(in srgb,var(--c) 8%,transparent)}
.carte-cl .ico{flex:none;width:38px;height:38px;border-radius:12px;display:grid;place-items:center;color:var(--c);background:color-mix(in srgb,var(--c) 14%,transparent)}
.carte-cl .ico svg{width:20px;height:20px}.cl-txt{display:flex;flex-direction:column;line-height:1.25;flex:1}.cl-txt b{color:#fff;font-weight:600}.cl-txt small{color:var(--dim);font-size:12px}
.carte-cl .fl{width:16px;height:16px;color:var(--dim)}
.bloc{margin:56px 0}.h-sec{font-size:clamp(1.4rem,3vw,1.9rem);margin:0 0 6px}.sous{color:var(--mut);margin:0 0 18px}
.h-cat{display:flex;align-items:center;gap:14px;margin:40px 0 14px;font-size:clamp(1.25rem,2.4vw,1.6rem);font-weight:650;letter-spacing:-.02em;color:#fff}
.h-cat span{display:inline-flex;align-items:center;gap:10px}
.h-cat span::before{content:"";width:6px;height:1.1em;border-radius:3px;background:#ff5b1f}
.h-cat small{font-size:12px;font-weight:500;letter-spacing:.02em;color:var(--mut);padding:3px 10px;border-radius:999px;background:rgba(255,255,255,.06);border:1px solid var(--line)}
.h-cat::after{content:"";flex:1;height:1px;background:linear-gradient(90deg,var(--line),transparent)}
.grille-mod{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:12px}
.carte-mod{display:block;text-decoration:none;border-radius:20px;overflow:hidden;background:var(--card);border:1px solid var(--line);transition:transform .25s,border-color .25s}
.carte-mod:hover{transform:translateY(-3px);border-color:color-mix(in srgb,var(--c) 50%,transparent)}
.carte-vis{padding:22px 18px 6px;background:radial-gradient(80% 90% at 50% 100%,color-mix(in srgb,var(--c) 22%,transparent),transparent 70%)}
.carte-txt{padding:6px 16px 16px}.carte-txt h3{margin:0 0 6px;color:#fff;font-size:18px;letter-spacing:-.02em}
.cat{font-family:Archivo,monospace;font-size:10.5px;letter-spacing:.16em;text-transform:uppercase;color:var(--c);margin:0 0 2px}
.ligne{display:flex;align-items:center;gap:10px;margin:0;font-size:13px;color:var(--mut)}
.deux{display:grid;grid-template-columns:1fr 1fr;gap:40px}
.regles{list-style:none;padding:0;margin:14px 0 0;display:grid;gap:10px}
.regles li{display:flex;gap:14px;padding:14px;border-radius:16px;background:var(--card);border:1px solid var(--line)}
.regles span{flex:none;width:30px;height:30px;border-radius:10px;display:grid;place-items:center;font-weight:700;color:#fff;background:#ff5b1f}
.regles b{color:#fff}.regles p{margin:2px 0 0;color:var(--mut);font-size:14.5px}
.faq details{border-bottom:1px solid var(--line);padding:12px 0}.faq summary{cursor:pointer;color:#fff;font-weight:600;list-style:none}
.faq summary::-webkit-details-marker{display:none}.faq summary::after{content:"+";float:right;color:var(--dim)}.faq details[open] summary::after{content:"–"}
.faq p{color:var(--mut);margin:8px 0 0}
/* Fiche modèle */
.hero-mod{display:grid;grid-template-columns:1.1fr .9fr;gap:28px;align-items:center;padding:8px 0 10px}
.hero-vis{position:relative;padding:20px}
.hero-vis::before{content:"";position:absolute;inset:-6%;border-radius:40%;background:radial-gradient(closest-side,color-mix(in srgb,var(--c) 30%,transparent),transparent);filter:blur(24px)}
.hero-vis figure{position:relative}
.hero-vis .car{position:relative;filter:drop-shadow(0 24px 30px rgba(0,0,0,.55))}
.tuiles{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin:0 0 22px}
.tuiles div{padding:12px 14px;border-radius:16px;background:var(--card);border:1px solid var(--line);display:flex;flex-direction:column;gap:6px}
.tuiles small{font-family:Archivo,monospace;font-size:10px;letter-spacing:.14em;text-transform:uppercase;color:var(--dim)}
.tuiles b{color:#fff;font-size:14.5px;line-height:1.3}
.grille-art{display:grid;grid-template-columns:minmax(0,1fr) 300px;gap:36px;margin-top:34px;align-items:start}
.contenu h2{font-size:1.45rem;margin:38px 0 14px}.contenu h2:first-child{margin-top:0}
.gens{list-style:none;padding:0;margin:0;border-left:2px solid var(--line)}
.gens li{position:relative;padding:4px 0 14px 20px}.gens li::before{content:"";position:absolute;left:-7px;top:10px;width:12px;height:12px;border-radius:50%;background:var(--acc);box-shadow:0 0 0 4px rgba(255,106,43,.18)}
.gens b{display:block;color:#fff}.gens span{color:var(--mut)}
.avis{list-style:none;padding:0;margin:0;display:grid;gap:10px}
.avis li{display:flex;gap:12px;padding:14px;border-radius:16px;border:1px solid var(--line)}
.avis svg{flex:none;width:22px;height:22px;fill:none;stroke-width:2.2;stroke-linecap:round;stroke-linejoin:round;margin-top:2px}
.avis b{color:#fff}.avis p{margin:3px 0 0;color:var(--mut);font-size:15px}
.avis.ok li{background:rgba(52,199,120,.06);border-color:rgba(52,199,120,.22)}.avis.ok svg{stroke:#4ade80}
.avis.ko li{background:rgba(255,170,40,.06);border-color:rgba(255,170,40,.22)}.avis.ko svg{stroke:#fbbf24}
.check{list-style:none;padding:0;margin:0;display:grid;gap:8px}
.check li{position:relative;padding-left:30px;color:var(--fg)}
.check li::before{content:"";position:absolute;left:0;top:3px;width:18px;height:18px;border-radius:6px;border:1.5px solid rgba(255,255,255,.25)}
.check li::after{content:"";position:absolute;left:6px;top:7px;width:6px;height:9px;border:solid var(--acc);border-width:0 2px 2px 0;transform:rotate(45deg)}
.puces{display:flex;flex-wrap:wrap;gap:8px}
.puce{text-decoration:none;font-size:13.5px;padding:7px 12px;border-radius:999px;background:var(--card);border:1px solid var(--line);color:var(--fg)}
.puce:hover{border-color:rgba(255,106,43,.5);color:#fff}
.avert{margin-top:34px;padding:14px 16px;border-radius:14px;background:rgba(255,255,255,.025);border:1px dashed var(--line);color:var(--dim);font-size:13.5px}
.cote{position:sticky;top:16px;display:grid;gap:14px}
.box{padding:18px;border-radius:20px;background:var(--card);border:1px solid var(--line)}
.cta-box{background:linear-gradient(160deg,color-mix(in srgb,var(--c) 18%,transparent),rgba(255,255,255,.02) 60%)}
.cta-titre{color:#fff;font-weight:650;font-size:20px;letter-spacing:-.02em;margin:0 0 14px}
.pile{display:grid;gap:8px}
/* Classements */
.hero-cl{padding:8px 0 10px;max-width:860px}.crit{margin-top:4px}
.classement{list-style:none;padding:0;margin:30px 0 0;display:grid;gap:14px}
.rang{display:grid;grid-template-columns:54px 230px minmax(0,1fr) auto;gap:20px;align-items:center;padding:16px 20px;border-radius:22px;background:var(--card);border:1px solid var(--line)}
.rang:hover{border-color:color-mix(in srgb,var(--c) 45%,transparent)}
.num{font-size:34px;font-weight:700;letter-spacing:-.04em;background:linear-gradient(180deg,#fff,#71717a);-webkit-background-clip:text;background-clip:text;color:transparent;text-align:center}
.rang-vis{border-radius:14px}
.rang-txt h2{margin:0 0 4px;font-size:1.3rem}.rang-txt h2 a{text-decoration:none}.rang-txt h2 a:hover{color:var(--acc)}
.rang-txt p{margin:2px 0;color:var(--mut);font-size:15px}.version b{color:#fff;font-weight:600}
.rang-act{display:flex;flex-direction:column;align-items:flex-end;gap:2px}
.pied{display:grid;grid-template-columns:1.4fr 1fr 1fr;gap:28px;padding-top:36px!important;padding-bottom:40px!important;margin-top:40px!important;border-top:1px solid var(--line);color:var(--dim);font-size:14px}
.pied a{display:block;color:var(--mut);text-decoration:none;padding:3px 0}.pied a:hover{color:#fff}
.brand-pied{color:#fff;font-weight:600;font-size:16px;margin:0 0 6px}.titre-pied{color:#fff;font-weight:600;margin:0 0 6px}
@media (max-width:900px){
  .hero-guide,.hero-mod,.grille-art,.deux{grid-template-columns:1fr}
  .vitrine{display:none}.hero-vis{order:-1;width:100%;max-width:560px;margin:0 auto;padding:0}.hero-vis::before{inset:0}
  .cote{position:static}.pied{grid-template-columns:1fr}
  .rang{grid-template-columns:40px minmax(0,1fr);gap:12px;padding:14px}
  .rang-vis{grid-column:2;max-width:100%}.rang-txt{grid-column:1/-1}.rang-act{grid-column:1/-1;align-items:flex-start;flex-direction:row;gap:14px}
  .num{font-size:26px}
}
@media (max-width:560px){.tuiles{grid-template-columns:1fr 1fr}.tuiles .large{grid-column:1/-1}.hide-sm{display:none}}
"""


def page_credits() -> str:
    chemin = "/guide/credits-photos"
    titre = "Crédits photos du guide d'achat"
    desc = "Auteurs et licences des photos de voitures utilisées dans le guide d'achat La Bonne Occaz (Wikimedia Commons)."
    fil_html, fil_ld = fil(("Guide d'achat", "/guide/"), ("Crédits photos", None))
    lignes = "".join(f'<li>{photo(k, p["titre"], "ph-cred")}<div><b>{e(p["titre"].rsplit(".", 1)[0])}</b>'
                     f'<p>Auteur : {e(p["auteur"])} · Licence : <a href="{e(p["licence_url"])}" rel="noopener license">{e(p["licence"])}</a> · '
                     f'<a href="{e(p["page"])}" rel="noopener">Voir sur Wikimedia Commons</a></p></div></li>' for k, p in PHOTOS.items())
    corps = f"""
    {fil_html}
    <section class="hero-cl"><p class="kicker">Crédits</p><h1>Crédits photos</h1>
      <p class="lead">Les photos du guide proviennent de Wikimedia Commons et sont publiées sous licence libre Creative Commons
      par leurs auteurs, que nous remercions. Elles sont affichées sans modification. Les marques et modèles cités appartiennent
      à leurs constructeurs ; La Bonne Occaz n'est affilié à aucun d'eux.</p></section>
    <ul class="credits">{lignes}</ul>
"""
    return page(chemin, titre, desc, corps, [fil_ld]).replace('<meta name="viewport"', '<meta name="robots" content="noindex, follow" />\n  <meta name="viewport"')


def main() -> None:
    SORTIE.mkdir(parents=True, exist_ok=True)
    (SORTIE / "guide.css").write_text(CSS.strip() + "\n" + ENTETE_CSS.strip() + "\n", encoding="utf-8")
    (SORTIE / "index.html").write_text(page_index(), encoding="utf-8")
    for m in MODELES:
        (SORTIE / f"{m['slug']}.html").write_text(page_modele(m), encoding="utf-8")
    for c in CLASSEMENTS:
        (SORTIE / f"{c['slug']}.html").write_text(page_classement(c), encoding="utf-8")
    (SORTIE / "credits-photos.html").write_text(page_credits(), encoding="utf-8")
    print(f"{len(MODELES) + len(CLASSEMENTS) + 2} pages écrites dans {SORTIE}")


if __name__ == "__main__":
    main()
