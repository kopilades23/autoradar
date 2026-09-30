# Autoradar — recherche d'occasions en direct

## Mettre le site en ligne gratuitement (Render)

Le site tourne sur un serveur gratuit de [Render](https://render.com) (sans carte bancaire) : votre PC
n'a plus besoin d'être allumé. Le moteur ne lance plus Chrome : il fait des requêtes directes
(empreinte de Chrome, `curl_cffi`) et lit les pages en Python (`parseurs.py`), ce qui tient dans les
512 Mo de l'offre gratuite.

1. **GitHub** (compte gratuit) : créez un dépôt **privé** `autoradar`, puis « Add file » >
   « Upload files » et glissez le contenu du dossier `autoradar-en-ligne` (ou de ce dossier, sans
   `.venv`, `profil_navigateur`, `annonces.db`).
2. **Render** : créez un compte avec « Sign in with GitHub », puis **New > Blueprint**, choisissez le
   dépôt `autoradar`. Render lit `render.yaml` et demande **AUTORADAR_MOT_DE_PASSE** : choisissez
   un mot de passe long (c'est celui du site).
3. Après 2-3 min de construction, le site est à l'adresse `https://autoradar-xxxx.onrender.com`.
   Le navigateur demande identifiant + mot de passe : identifiant au choix, le mot de passe ci-dessus.

Mises à jour : remplacez les fichiers dans GitHub, Render redéploie tout seul.

**Site ouvert à tous** (sans mot de passe) : dans Render > Environment, supprimez
`AUTORADAR_MOT_DE_PASSE` et ajoutez `AUTORADAR_PUBLIC` = `1`. Chaque visiteur est alors limité à
90 requêtes par minute (`AUTORADAR_LIMITE_MINUTE`) et le site demande à Google de ne pas l'indexer.

À savoir sur l'offre gratuite : le serveur **s'endort après 15 min sans visite** ; la première
recherche suivante attend ~1 min qu'il se réveille, ensuite tout est normal.

## Sur votre PC (facultatif)

```powershell
cd $HOME\Documents\auto-agregateur\auto-agregateur
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt   # une fois (curl_cffi, selectolax)
python server.py                  # http://localhost:8000, requêtes directes
python server.py --navigateur     # ancien mode : Chrome piloté en arrière-plan (Playwright)
```

## Sources

| Source | Filtré par le site | Détails lus (options, merguez) |
|---|---|---|
| AutoScout24 | modèle, prix, km, année, carburant, toit pano, hi-fi | fiche complète (JSON) |
| **LeParking** | texte (modèle + option), prix, km, année, carburant, France | titre + version seulement (voir plus bas) |
| ParuVendu | modèle, prix, km, année, mot-clé | fiches lues après l'affichage, une à la fois |
| L'argus Occasion | modèle, prix, km, année, carburant, mot-clé | fiche ; **ses copies d'annonces Leboncoin sont affichées comme « Leboncoin »** avec leur description, lien vers l'annonce Leboncoin |
| Auto-Sélection | modèle, prix, km, année, carburant, boîte auto | fiche |
| Autohero | modèle, prix, km, année, diesel | fiche (1re page seulement) |
| Renew (Renault) | modèle, km, carburant | fiche + équipements du JSON embarqué |
| Spoticar | modèle (tri par prix) | fiche |
| Autosphere | modèle (1re page) | fiche |
| Zoomcar (ex-Ouest-France Auto) | modèle | sur PC seulement (refuse les serveurs) |
| Leboncoin, La Centrale, Aramis Auto | liens « Ouvrir aussi » pré-remplis | — |

- Photos : image de la carte, sinon celle trouvée dans le JSON de la page (sites React comme
  Renew), sinon celle de la fiche.
- Une même voiture publiée sur plusieurs sites (même prix, km, année) n'apparaît qu'une fois
  (« aussi sur … ») ; la version qui a sa description est préférée à celle de LeParking.
- Seules les annonces de la page affichée sont lues ; « Charger plus » va chercher la suite.
- Caches mémoire : 10 min pour les pages de résultats, 6 h pour les fiches.

Fichiers : `recherche_live.py` (moteur + description des sites), `parseurs.py` (lecture des pages
en Python), `transport_http.py` (requêtes directes), `sites/*.js` (mêmes lectures, pour le mode
navigateur), `server.py` (API + mot de passe), `static/index.html` (interface), `render.yaml`.

## LeParking : pourquoi il n'est pas bloqué, et ce qu'on peut en tirer

LeParking ne va pas chercher les annonces au moment où vous cherchez : il a sa propre base
(15 millions d'annonces, ~1 000 sites) remplie en continu par ses robots **et par des flux que les
sites lui envoient** — il leur apporte des visiteurs, ils ont intérêt à se laisser référencer. Nous,
on arrive à chaque recherche avec des dizaines de requêtes d'un coup : c'est ce profil que
ParuVendu, Auto-Sélection (Cloudflare) ou Leboncoin (DataDome) bloquent.

Ce qu'Autoradar en tire : la recherche LeParking (une requête = Leboncoin, La Centrale, Carizy,
concessions…). Par contre les fiches LeParking ne contiennent **ni description ni équipements**
(seulement prix, année, km, énergie, boîte), et ses liens vers le site d'origine (`/tools/…`) sont
**interdits aux robots** dans son robots.txt (ce sont ses clics facturés aux partenaires) : on ne les
suit donc pas automatiquement — seulement quand vous cliquez « Voir l'annonce ». Pour ces annonces,
options et merguez sont repérés sur le titre + la version (petite icône ⓘ). Beaucoup d'entre elles
sont aussi sur une source directe (L'argus pour Leboncoin, AutoScout24, Autohero…) : c'est alors la
version complète qui s'affiche.

## Anti-blocage

- Chaque site a sa cadence : ParuVendu une fiche à la fois (~1,6 s d'écart), lues **après**
  l'affichage des résultats (les cartes se complètent : « fiches 6/25… »).
- Si un site renvoie son captcha (« antiaspiration », Cloudflare, DataDome…), Autoradar arrête de
  le solliciter **15 min** au lieu d'insister.
- Gardez le site **privé** (mot de passe obligatoire en ligne) : republier au public les annonces
  d'autres sites pose des problèmes juridiques (droit des bases de données, conditions d'utilisation).

## Autre hébergement

`Dockerfile` / `docker-compose.yml` (image légère, sans Chrome) pour n'importe quel serveur :
`AUTORADAR_MOT_DE_PASSE='…' docker compose up -d --build`. Variables : `AUTORADAR_HOTE`,
`PORT`/`AUTORADAR_PORT`, `AUTORADAR_MOT_DE_PASSE`, `AUTORADAR_MODE` (`http` par défaut).

---

## Mode « base locale » (optionnel, ancien fonctionnement)

`scraper_autoscout24.py` télécharge des annonces dans `annonces.db`, consultables sur
http://localhost:8000/base.html. Inutile pour la recherche en direct.

```
auto-agregateur/
├── database.py               # schéma SQLite + migration auto + save/list
├── detection.py              # mots-clés « merguez » et options premium (modifiables)
├── scraper_autoscout24.py    # scraper Playwright (3 pages + lecture des fiches)
├── server.py                 # mini-serveur local (stdlib) + API JSON
├── static/index.html         # interface Tailwind (cartes animées)
└── annonces.db               # créée automatiquement
```

## Installation (une fois)

```bash
python -m venv .venv
# Windows : .venv\Scripts\activate    |  macOS/Linux : source .venv/bin/activate
pip install -r requirements-navigateur.txt
python -m playwright install chromium
```

## Utilisation

```bash
python scraper_autoscout24.py                  # Peugeot 208, 3 pages, TOUT est téléchargé
python scraper_autoscout24.py --pages 0        # toutes les pages de résultats
python scraper_autoscout24.py --visible        # voir le navigateur travailler
python scraper_autoscout24.py --concurrence 5  # plus doux si le site freine (défaut 10)
python scraper_autoscout24.py --sans-details   # liste seule (réutilise les fiches déjà en base)
python scraper_autoscout24.py --marque renault --modele clio --pages 5 --max 80
python server.py                               # ouvre http://localhost:8000
python detection.py                            # auto-test des mots-clés
python detection.py --reappliquer              # relance la détection sur la base, sans rescanner
```

## Ce qui est récupéré dès le premier passage

Pour chaque annonce : titre, prix, année, km, lien, image, carburant, boîte, puissance, ville,
vendeur, **description complète**, **liste complète des équipements**, accident déclaré par
le vendeur, et le **JSON brut** de la recherche + de la fiche (colonne `donnees_brutes`).
Rien n'a besoin d'être rescanné plus tard : si vous changez les mots-clés, lancez
`python detection.py --reappliquer`.

## Comment c'est rapide

Analyse d'AutoScout24 (30/09/2026) : chaque page embarque tout son état dans
`<script id="__NEXT_DATA__">`. La page de recherche ne contient **pas** la description complète
(seulement un sous-titre tronqué) et aucun XHR ne la fournit ; la fiche, elle, contient tout.

1. **Hydration JSON d'abord** : le scraper lit `__NEXT_DATA__`, les états `window.__INITIAL_STATE__`
   & co et les réponses XHR/fetch JSON interceptées. Si un site y met la description complète,
   elle est utilisée directement (aucune fiche visitée).
2. **Fiches en parallèle** : le navigateur n'ouvre que la page 1 (cookies, anti-bot). Toutes les
   autres pages et les fiches sont récupérées par `fetch()` exécuté dans cet onglet (vrai Chrome,
   mêmes cookies, sans rendu ni images), **10 à la fois**, et seul le JSON revient à Python.
   Repli automatique sur un onglet allégé si une requête échoue.

Ordre de grandeur : 60 annonces complètes en quelques secondes (contre plusieurs minutes avant).

## Fonctionnalités de l'interface

- **Merguez masquées par défaut** (bouton pour les réafficher, choix mémorisé). Détection sur
  titre + description + accident déclaré ; négations gérées (« jamais accidenté »).
- **Filtres options premium** (Bose, Harman Kardon, Burmester, toit panoramique, Matrix LED) :
  cliquez un ou plusieurs badges (les annonces doivent avoir toutes les options cochées).
- **Recherche plein texte** dans titres, descriptions et équipements (ex. « distribution faite »).
- Rendu progressif (48 cartes, puis la suite au défilement) pour rester fluide avec des centaines d'annonces.

Pour ajouter une option : `detection.py` (motif) + `OPTIONS` dans `static/index.html` (couleur),
puis `python detection.py --reappliquer`.

Une base créée avec une ancienne version est migrée automatiquement (nouvelles colonnes ajoutées).

## Si le scraper ne trouve rien

- Relancer avec `--visible` : un captcha ou un bandeau inattendu est souvent la cause.
- Une capture d'écran + le HTML de la page sont écrits dans `debug/` pour diagnostiquer.
- Le site change régulièrement : l'extraction lit d'abord le JSON embarqué (`__NEXT_DATA__`),
  puis se replie sur le contenu de la page.

Pensez à respecter les conditions d'utilisation des sites et à garder un rythme de requêtes raisonnable (usage personnel).
