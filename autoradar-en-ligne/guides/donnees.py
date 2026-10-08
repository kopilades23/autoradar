"""Contenu du guide d'achat (pages /guide/…). Modifier ici puis relancer : python guides/generer.py

Les avis sont volontairement prudents : ils résument des tendances connues (pannes fréquemment signalées,
moteurs réputés), pas une garantie. Chaque page renvoie vers la recherche en direct.
"""

MAJ = "2026-10-07"          # date de mise à jour affichée et envoyée à Google
MAJ_TEXTE = "octobre 2026"

# Identifiants utilisés par le moteur de recherche (catalogue AutoScout24)
# carrosserie : citadine | compacte | suv | berline  (choisit la silhouette dessinée)
MODELES = [
    {
        "slug": "peugeot-208", "photo": "208-2", "marque": "Peugeot", "modele": "208", "marque_id": 55, "modele_cle": "m:20057",
        "carrosserie": "citadine", "couleur": "#ff6a2b", "categorie": "Citadine", "fiabilite": 3,
        "resume": "La citadine la plus vendue en France : agréable, bien équipée, mais un moteur essence à surveiller de près.",
        "budget": "5 000 à 20 000 €",
        "generations": [
            ("208 I (2012-2019)", "Le gros du marché sous 10 000 €. Phase 2 à partir de 2015, plus moderne.", "208-1"),
            ("208 II (2019-…)", "Nouveau style, intérieur i-Cockpit 3D, existe en électrique (e-208).", "208-2"),
        ],
        "conseilles": [
            ("1.5 BlueHDi 100 (208 II) / 1.6 BlueHDi 75-100 (208 I)", "Diesels robustes et sobres, idéaux pour beaucoup de kilomètres."),
            ("1.2 PureTech 75-82 (atmosphérique)", "Moins puissant mais plus simple que les versions turbo ; parfait en ville."),
            ("e-208 électrique", "Silencieux et économique à l'usage ; vérifiez l'état de la batterie."),
        ],
        "surveiller": [
            ("1.2 PureTech turbo 100 / 110 / 130", "Usure prématurée de la courroie de distribution (qui baigne dans l'huile) et consommation d'huile signalées sur de nombreux exemplaires produits jusqu'au début des années 2020. Exigez les factures et vérifiez si la courroie a été remplacée. Stellantis a étendu sa prise en charge sous conditions : renseignez-vous en concession."),
            ("Diesels BlueHDi récents", "Pannes du réservoir ou de la pompe AdBlue (message « démarrage impossible dans … km ») : à faire vérifier."),
        ],
        "verifier": ["Factures d'entretien et date du dernier changement de courroie (PureTech)",
                     "Niveau d'huile au contrôle de la jauge, fumée bleue au démarrage",
                     "Aucun message « anti-pollution » ou « AdBlue » au tableau de bord",
                     "Écran tactile réactif, climatisation qui souffle froid"],
        "options": ["CarPlay / Android Auto", "Toit panoramique", "Boîte automatique"],
        "faq": [("Quelle Peugeot 208 d'occasion choisir ?", "En diesel, les 1.5 et 1.6 BlueHDi sont les plus sereines. En essence, privilégiez un 1.2 PureTech dont la courroie a été changée, factures à l'appui, ou la version atmosphérique 75-82 ch."),
                ("La 208 est-elle fiable ?", "Globalement oui, à l'exception du 1.2 PureTech turbo dont la courroie de distribution s'use trop vite sur de nombreux exemplaires. Un entretien suivi et documenté est indispensable.")],
    },
    {
        "slug": "renault-clio", "photo": "clio-5", "marque": "Renault", "modele": "Clio", "marque_id": 60, "modele_cle": "m:1961",
        "carrosserie": "citadine", "couleur": "#ffcf3d", "categorie": "Citadine", "fiabilite": 3,
        "resume": "Increvable en diesel, pratique et pas chère à entretenir : la référence des citadines d'occasion.",
        "budget": "4 000 à 20 000 €",
        "generations": [
            ("Clio 4 (2012-2019)", "Très répandue, pièces bon marché, phase 2 en 2016.", "clio-4"),
            ("Clio 5 (2019-…)", "Intérieur nettement plus moderne, version hybride E-Tech très sobre.", "clio-5"),
        ],
        "conseilles": [
            ("1.5 dCi 75 / 90 (Clio 4) et 1.5 Blue dCi (Clio 5)", "Le diesel K9K est l'un des moteurs les plus éprouvés du marché."),
            ("0.9 TCe 90 (Clio 4) / 1.0 TCe 90-100 (Clio 5)", "Petits turbos essence corrects si l'entretien est suivi."),
            ("E-Tech hybride 140-145 (Clio 5)", "Très sobre en ville, boîte automatique de série."),
        ],
        "surveiller": [
            ("1.2 TCe 120 (Clio 4, 2013-2016 surtout)", "Cas de surconsommation d'huile pouvant aller jusqu'à la casse moteur ; à éviter sans historique clair."),
            ("Boîte automatique EDC (double embrayage)", "À-coups et pannes de mécatronique signalés : faites un essai long, en ville."),
        ],
        "verifier": ["Écran R-Link qui ne fige pas, GPS fonctionnel",
                     "Démarrage à froid sans fumée ni bruit de cliquetis",
                     "Embrayage : point de patinage pas trop haut",
                     "Carnet d'entretien tamponné"],
        "options": ["CarPlay / Android Auto", "Caméra 360°", "Régulateur adaptatif"],
        "faq": [("Quelle Clio d'occasion est la plus fiable ?", "La Clio 4 1.5 dCi est réputée quasi increvable. En essence, préférez le 0.9 TCe 90 au 1.2 TCe 120 de première génération."),
                ("Clio 4 ou Clio 5 ?", "La Clio 4 est imbattable sous 10 000 €. La Clio 5 apporte un intérieur plus moderne et l'hybride E-Tech, à partir d'environ 12 000 €.")],
    },
    {
        "slug": "volkswagen-polo", "photo": "polo-6", "marque": "Volkswagen", "modele": "Polo", "marque_id": 74, "modele_cle": "m:2090",
        "carrosserie": "citadine", "couleur": "#5aa9ff", "categorie": "Citadine", "fiabilite": 4,
        "resume": "Une petite voiture de qualité allemande, solide et qui garde bien sa valeur.",
        "budget": "5 000 à 20 000 €",
        "generations": [
            ("Polo 5 (2009-2017)", "Restylée en 2014 avec de nouveaux moteurs plus modernes.", "polo-5"),
            ("Polo 6 (2017-…)", "Plus spacieuse, plus technologique, très bonne finition.", "polo-6"),
        ],
        "conseilles": [
            ("1.0 MPI 65 / 75 / 80", "Simple, fiable, parfait pour un jeune conducteur."),
            ("1.0 TSI 95 / 110", "Le bon compromis : souple et sobre."),
            ("1.4 / 1.6 TDI", "Pour les gros rouleurs, robuste."),
        ],
        "surveiller": [
            ("1.2 TSI des premières années (avant 2012)", "Chaîne de distribution qui s'allonge : bruit de claquement à froid à surveiller."),
            ("Boîte DSG7 à sec (DQ200)", "Pannes d'embrayage ou de mécatronique signalées : vérifiez l'historique et l'agrément en ville."),
        ],
        "verifier": ["Claquement au démarrage à froid (chaîne)", "Passages de vitesses fluides sur DSG",
                     "Carnet d'entretien Volkswagen", "Usure des pneus régulière (géométrie)"],
        "options": ["CarPlay / Android Auto", "Boîte automatique", "Régulateur adaptatif"],
        "faq": [("La Polo est-elle fiable ?", "Oui, surtout en 1.0 MPI et 1.0 TSI. Surveillez la boîte DSG7 et les tout premiers 1.2 TSI."),
                ("Quelle Polo pour un jeune permis ?", "Une Polo 1.0 MPI de 65 à 80 ch : assurance raisonnable et mécanique simple.")],
    },
    {
        "slug": "toyota-yaris", "photo": "yaris-4", "marque": "Toyota", "modele": "Yaris", "marque_id": 70, "modele_cle": "m:15663",
        "carrosserie": "citadine", "couleur": "#ff4d6d", "categorie": "Citadine", "fiabilite": 5,
        "resume": "La championne de la fiabilité : l'hybride Toyota est réputé pour durer très longtemps avec peu de frais.",
        "budget": "6 000 à 22 000 €",
        "generations": [
            ("Yaris 3 (2011-2020)", "Hybride 100 ch très répandue, souvent d'anciens taxis ou véhicules de flotte.", "yaris-3"),
            ("Yaris 4 (2020-…)", "Nouvelle hybride 116 ch encore plus sobre, primée voiture de l'année 2021.", "yaris-4"),
        ],
        "conseilles": [
            ("1.5 Hybride 100 (Yaris 3)", "Boîte automatique sans embrayage, très peu d'usure, consommation basse en ville."),
            ("1.5 Hybride 116 (Yaris 4)", "Le meilleur choix récent, très sobre."),
            ("1.0 VVT-i 69-72", "Pour un petit budget : simple et économique."),
        ],
        "surveiller": [
            ("Kilométrages très élevés (anciennes flottes)", "La mécanique tient, mais vérifiez l'usure intérieure et l'entretien régulier."),
            ("Coffre et places arrière", "Plus petits que la moyenne : à essayer si vous avez des enfants."),
        ],
        "verifier": ["Historique d'entretien (même chez un garage indépendant)", "Voyant hybride éteint, passage silencieux en électrique",
                     "Ventilateur de la batterie hybride (sous la banquette) propre", "Freins : disques non voilés"],
        "options": ["Caméra 360°", "CarPlay / Android Auto", "Boîte automatique"],
        "faq": [("La Yaris hybride est-elle fiable ?", "C'est l'une des voitures les plus fiables du marché : la batterie hybride dure en général toute la vie du véhicule."),
                ("La Yaris convient-elle à un jeune conducteur ?", "Oui : faible puissance, assurance raisonnable et boîte automatique facile.")],
    },
    {
        "slug": "dacia-sandero", "photo": "sandero-3", "marque": "Dacia", "modele": "Sandero", "marque_id": 16360, "modele_cle": "m:19129",
        "carrosserie": "citadine", "couleur": "#7ad37a", "categorie": "Citadine", "fiabilite": 4,
        "resume": "La voiture neuve la moins chère de France, et une occasion simple, fiable et peu coûteuse.",
        "budget": "4 000 à 15 000 €",
        "generations": [
            ("Sandero 2 (2012-2020)", "Mécanique Renault éprouvée, très bon rapport prix/place.", "sandero-2"),
            ("Sandero 3 (2020-…)", "Plus moderne et mieux équipée, version GPL ECO-G économique.", "sandero-3"),
        ],
        "conseilles": [
            ("1.5 dCi 75 / 90", "Le diesel Renault, robuste et sobre."),
            ("0.9 TCe 90 / 1.0 TCe 90", "Petit turbo essence agréable."),
            ("ECO-G 100 (GPL + essence)", "Plein moins cher : idéal pour beaucoup de kilomètres."),
        ],
        "surveiller": [
            ("Boîte robotisée Easy-R", "Changements de rapports lents et à-coups : préférez la boîte manuelle."),
            ("Finition et insonorisation", "Simples : normal pour le prix, mais vérifiez les bruits de mobilier."),
        ],
        "verifier": ["Traces de corrosion sous la caisse (anciennes Sandero)", "Bruits de trains roulants",
                     "Système GPL : contrôle du réservoir et passage essence/GPL", "Carnet d'entretien"],
        "options": ["Attelage", "CarPlay / Android Auto"],
        "faq": [("La Dacia Sandero est-elle fiable ?", "Oui : elle reprend des moteurs Renault simples et éprouvés, avec peu d'électronique."),
                ("Sandero GPL : bonne idée ?", "Oui si vous roulez beaucoup : le GPL coûte environ deux fois moins cher que l'essence au litre.")],
    },
    {
        "slug": "citroen-c3", "photo": "c3-3", "marque": "Citroën", "modele": "C3", "marque_id": 21, "modele_cle": "m:18264",
        "carrosserie": "citadine", "couleur": "#c58bff", "categorie": "Citadine", "fiabilite": 3,
        "resume": "Confortable et originale, mais qui partage les moteurs 1.2 PureTech de Peugeot.",
        "budget": "4 000 à 18 000 €",
        "generations": [
            ("C3 II (2009-2016)", "Pare-brise panoramique « Zénith », 1.4 HDi robuste."),
            ("C3 III (2016-2024)", "Style original avec Airbump, suspension confortable.", "c3-3"),
        ],
        "conseilles": [
            ("1.6 / 1.5 BlueHDi", "Diesels sobres et durables."),
            ("1.2 PureTech 68-82 (atmosphérique)", "Plus simple que les versions turbo."),
        ],
        "surveiller": [
            ("1.2 PureTech 110 turbo", "Même problème de courroie de distribution que la Peugeot 208 : historique d'entretien indispensable."),
            ("Boîte automatique ETG / BMP", "Robotisée, lente et sujette aux à-coups sur les anciennes."),
        ],
        "verifier": ["Factures de courroie (PureTech)", "Message AdBlue sur les diesels récents",
                     "Fonctionnement des équipements électroniques", "État des Airbump"],
        "options": ["CarPlay / Android Auto", "Toit panoramique"],
        "faq": [("La Citroën C3 est-elle fiable ?", "Correcte en diesel et en 1.2 atmosphérique ; prudence avec le 1.2 PureTech turbo sans historique."),]
    },
    {
        "slug": "volkswagen-golf", "photo": "golf-7", "marque": "Volkswagen", "modele": "Golf", "marque_id": 74, "modele_cle": "m:2084",
        "carrosserie": "compacte", "couleur": "#5aa9ff", "categorie": "Compacte", "fiabilite": 4,
        "resume": "La compacte de référence : polyvalente, bien finie et très demandée à la revente.",
        "budget": "7 000 à 30 000 €",
        "generations": [
            ("Golf 7 (2012-2020)", "Considérée comme l'une des meilleures Golf ; restylage « 7.5 » en 2017.", "golf-7"),
            ("Golf 8 (2020-…)", "Plus connectée, mais quelques bugs logiciels signalés au lancement.", "golf-8"),
        ],
        "conseilles": [
            ("1.6 TDI 110-115 / 2.0 TDI 150", "Diesels endurants, parfaits pour les gros rouleurs."),
            ("1.4 TSI 125-150 / 1.5 TSI 130-150", "Essences souples et sobres."),
            ("Boîte DSG6 (avec 2.0 TDI)", "Boîte automatique robuste à embrayages humides."),
        ],
        "surveiller": [
            ("Boîte DSG7 à sec (moteurs jusqu'à 150 ch)", "Embrayage et mécatronique parfois défaillants : vérifiez l'historique."),
            ("Golf 8 premières années", "Écran et systèmes d'aide qui bugguent : vérifiez les mises à jour logicielles."),
        ],
        "verifier": ["Passages DSG sans à-coups à basse vitesse", "Mises à jour logicielles faites (Golf 8)",
                     "Courroie de distribution du TDI selon le kilométrage", "Historique Volkswagen"],
        "options": ["Régulateur adaptatif", "Affichage tête haute", "Matrix LED", "Boîte automatique"],
        "faq": [("Golf 7 ou Golf 8 d'occasion ?", "La Golf 7 (surtout 7.5) offre le meilleur rapport fiabilité/prix. La Golf 8 est plus moderne mais plus chère et a connu des bugs logiciels."),
                ("Quel moteur choisir sur une Golf 7 ?", "Le 1.6 TDI ou le 2.0 TDI pour rouler beaucoup, le 1.4 TSI ou 1.5 TSI en essence.")],
    },
    {
        "slug": "peugeot-308", "photo": "308-2", "marque": "Peugeot", "modele": "308", "marque_id": 55, "modele_cle": "m:19055",
        "carrosserie": "compacte", "couleur": "#ff6a2b", "categorie": "Compacte", "fiabilite": 3,
        "resume": "Une compacte élégante et confortable, à choisir de préférence en diesel.",
        "budget": "6 000 à 28 000 €",
        "generations": [
            ("308 II (2013-2021)", "Élue voiture de l'année 2014, i-Cockpit et grand coffre.", "308-2"),
            ("308 III (2021-…)", "Plus haut de gamme, versions hybrides rechargeables."),
        ],
        "conseilles": [
            ("1.5 BlueHDi 130 (boîte EAT8)", "L'association la plus réussie : sobre et agréable."),
            ("1.6 BlueHDi 120 / 2.0 BlueHDi 150-180", "Diesels éprouvés."),
        ],
        "surveiller": [
            ("1.2 PureTech 110 / 130", "Courroie de distribution qui s'use prématurément : historique indispensable."),
            ("Système AdBlue (diesels)", "Pannes de réservoir/pompe signalées : vérifiez qu'aucun message n'apparaît."),
        ],
        "verifier": ["Factures de courroie (PureTech) ou de réservoir AdBlue", "Écran central réactif",
                     "Boîte EAT8 sans à-coups", "Usure du volant et du siège conducteur (kilométrage réel)"],
        "options": ["Toit panoramique", "Régulateur adaptatif", "Boîte automatique"],
        "faq": [("Quelle 308 d'occasion choisir ?", "Une 308 II 1.5 BlueHDi 130 EAT8 : sobre, confortable et sans le souci de courroie du PureTech."),]
    },
    {
        "slug": "renault-captur", "photo": "captur-2", "marque": "Renault", "modele": "Captur", "marque_id": 60, "modele_cle": "m:20235",
        "carrosserie": "suv", "couleur": "#ffcf3d", "categorie": "SUV urbain", "fiabilite": 3,
        "resume": "Le SUV urbain qui a lancé la mode : pratique, avec sa banquette coulissante.",
        "budget": "6 000 à 24 000 €",
        "generations": [
            ("Captur I (2013-2019)", "Base de Clio 4, très répandu.", "captur-1"),
            ("Captur II (2019-…)", "Plus grand et mieux fini, hybride E-Tech.", "captur-2"),
        ],
        "conseilles": [
            ("1.5 dCi 90 / 110", "Diesel fiable et sobre."),
            ("0.9 TCe 90 / 1.0 TCe 90-100", "Essences correctes pour un usage mixte."),
            ("1.3 TCe 140 / E-Tech (Captur II)", "Plus récents, agréables."),
        ],
        "surveiller": [
            ("1.2 TCe 120 EDC (2013-2016)", "Surconsommation d'huile et boîte EDC capricieuse."),
            ("Écran R-Link", "Bugs fréquents sur le Captur I."),
        ],
        "verifier": ["Niveau d'huile (TCe)", "Boîte EDC : essai en ville", "Banquette coulissante fonctionnelle", "Carnet d'entretien"],
        "options": ["Caméra 360°", "CarPlay / Android Auto", "Boîte automatique"],
        "faq": [("Le Renault Captur est-il fiable ?", "Oui en 1.5 dCi et en 0.9 TCe ; évitez le 1.2 TCe 120 EDC des premières années.")],
    },
    {
        "slug": "peugeot-2008", "photo": "2008-2", "marque": "Peugeot", "modele": "2008", "marque_id": 55, "modele_cle": "m:20237",
        "carrosserie": "suv", "couleur": "#ff6a2b", "categorie": "SUV urbain", "fiabilite": 3,
        "resume": "Le SUV de la 208 : mêmes qualités, mêmes moteurs, donc mêmes précautions.",
        "budget": "7 000 à 26 000 €",
        "generations": [
            ("2008 I (2013-2019)", "Plus proche d'un break surélevé, Grip Control sur certaines versions."),
            ("2008 II (2019-…)", "Vrai SUV au style affirmé, existe en électrique.", "2008-2"),
        ],
        "conseilles": [
            ("1.5 BlueHDi 100 / 130", "Le choix serein."),
            ("e-2008 électrique", "Pour un usage surtout urbain et périurbain."),
        ],
        "surveiller": [
            ("1.2 PureTech turbo 100 / 110 / 130", "Courroie de distribution et consommation d'huile : exigez l'historique."),
            ("AdBlue (diesels)", "Pannes de réservoir signalées."),
        ],
        "verifier": ["Factures de courroie", "Messages d'alerte au tableau de bord", "État de la batterie (e-2008)"],
        "options": ["Toit panoramique", "Caméra 360°", "Boîte automatique"],
        "faq": [("Peugeot 2008 : quel moteur choisir ?", "Le 1.5 BlueHDi en diesel, ou un 1.2 PureTech avec courroie récemment changée et factures.")],
    },
    {
        "slug": "peugeot-3008", "photo": "3008-2", "marque": "Peugeot", "modele": "3008", "marque_id": 55, "modele_cle": "m:19217",
        "carrosserie": "suv", "couleur": "#ff6a2b", "categorie": "SUV familial", "fiabilite": 3,
        "resume": "Un SUV familial très réussi en design et en présentation, à choisir en diesel de préférence.",
        "budget": "12 000 à 35 000 €",
        "generations": [
            ("3008 II (2016-2023)", "Élu voiture de l'année 2017, énorme succès.", "3008-2"),
            ("3008 III (2024-…)", "Nouvelle génération, encore rare en occasion."),
        ],
        "conseilles": [
            ("1.5 BlueHDi 130 EAT8", "Sobre, agréable, très bonne boîte automatique."),
            ("2.0 BlueHDi 150 / 180", "Pour tracter ou rouler beaucoup."),
        ],
        "surveiller": [
            ("1.2 PureTech 130", "Courroie de distribution : historique indispensable."),
            ("Hybride rechargeable (Hybrid / Hybrid4)", "Plus complexe : vérifiez la recharge et l'état de la batterie."),
            ("AdBlue", "Réservoir et pompe à surveiller sur les diesels."),
        ],
        "verifier": ["Factures d'entretien complètes", "Écrans (compteur et central) sans bug", "Hayon électrique", "Aucun message d'alerte moteur ou AdBlue"],
        "options": ["Hayon électrique", "Toit panoramique", "Sièges chauffants", "Régulateur adaptatif"],
        "faq": [("Le Peugeot 3008 est-il fiable ?", "En 1.5 et 2.0 BlueHDi, globalement oui. Le 1.2 PureTech demande un historique d'entretien irréprochable.")],
    },
    {
        "slug": "dacia-duster", "photo": "duster-2", "marque": "Dacia", "modele": "Duster", "marque_id": 16360, "modele_cle": "m:19264",
        "carrosserie": "suv", "couleur": "#7ad37a", "categorie": "SUV", "fiabilite": 4,
        "resume": "Le SUV le plus malin du marché : spacieux, simple, et disponible en 4x4 à petit prix.",
        "budget": "7 000 à 22 000 €",
        "generations": [
            ("Duster I (2010-2017)", "Rustique mais très costaud."),
            ("Duster II (2018-2024)", "Mieux fini et mieux équipé.", "duster-2"),
        ],
        "conseilles": [
            ("1.5 dCi / Blue dCi 110-115 (4x2 ou 4x4)", "Robuste, idéal pour la campagne et le remorquage."),
            ("1.3 TCe 130 / 150", "Essence moderne et agréable."),
        ],
        "surveiller": [
            ("1.6 SCe 115", "Fiable mais gourmand et un peu poussif."),
            ("Corrosion (Duster I)", "Inspectez le dessous de caisse, surtout en région côtière ou montagneuse."),
        ],
        "verifier": ["Dessous de caisse et rouille", "Transmission 4x4 : essai en courbe serrée", "Attelage et usage en remorquage", "Embrayage"],
        "options": ["4x4 / intégrale", "Attelage", "Caméra 360°"],
        "faq": [("Le Dacia Duster est-il fiable ?", "Oui, surtout en 1.5 dCi : mécanique Renault simple et éprouvée.")],
    },
    {
        "slug": "toyota-c-hr", "photo": "chr-1", "marque": "Toyota", "modele": "C-HR", "marque_id": 70, "modele_cle": "m:74374",
        "carrosserie": "suv", "couleur": "#ff4d6d", "categorie": "SUV hybride", "fiabilite": 5,
        "resume": "Un SUV au look audacieux avec la fiabilité hybride Toyota.",
        "budget": "14 000 à 30 000 €",
        "generations": [
            ("C-HR I (2016-2023)", "Hybride 122 ch puis 184 ch à partir de 2019.", "chr-1"),
            ("C-HR II (2023-…)", "Nouvelle génération, encore chère en occasion."),
        ],
        "conseilles": [
            ("1.8 Hybride 122", "Très sobre en ville, fiabilité exemplaire."),
            ("2.0 Hybride 184", "Plus de punch pour la route."),
        ],
        "surveiller": [
            ("Places arrière et visibilité", "Le style se paie : arrière sombre, coffre moyen."),
        ],
        "verifier": ["Historique d'entretien Toyota (extension de garantie hybride possible)", "Caméra de recul (visibilité arrière limitée)", "Pneus et freins"],
        "options": ["Caméra 360°", "Sièges chauffants", "Régulateur adaptatif"],
        "faq": [("Le Toyota C-HR hybride est-il fiable ?", "Oui, c'est l'un des SUV les plus fiables du marché.")],
    },
    {
        "slug": "toyota-corolla", "photo": "corolla-12", "marque": "Toyota", "modele": "Corolla", "marque_id": 70, "modele_cle": "m:2052",
        "carrosserie": "compacte", "couleur": "#ff4d6d", "categorie": "Compacte hybride", "fiabilite": 5,
        "resume": "La compacte hybride la plus fiable, en berline 5 portes ou en break Touring Sports.",
        "budget": "15 000 à 30 000 €",
        "generations": [
            ("Corolla 12 (2019-…)", "Remplace l'Auris ; hybride 122-140 ch ou 180-196 ch.", "corolla-12"),
        ],
        "conseilles": [
            ("1.8 Hybride 122 / 140", "Très sobre, parfaite au quotidien."),
            ("2.0 Hybride 180 / 196", "Dynamique et toujours sobre."),
        ],
        "surveiller": [
            ("Coffre de la berline 5 portes", "Moyen : préférez le break Touring Sports pour une famille."),
        ],
        "verifier": ["Entretien Toyota régulier", "Écran multimédia (lent sur les premiers modèles)", "Pneus et freins"],
        "options": ["CarPlay / Android Auto", "Régulateur adaptatif", "Sièges chauffants"],
        "faq": [("Toyota Corolla hybride : bon achat d'occasion ?", "Oui : c'est l'une des compactes les plus fiables et économiques, avec une boîte automatique sans entretien particulier.")],
    },
    {
        "slug": "skoda-octavia", "photo": "octavia-3", "marque": "Skoda", "modele": "Octavia", "marque_id": 65, "modele_cle": "m:15222",
        "carrosserie": "berline", "couleur": "#41d1b4", "categorie": "Familiale", "fiabilite": 4,
        "resume": "La familiale la plus rationnelle : un coffre géant et la mécanique Volkswagen.",
        "budget": "8 000 à 30 000 €",
        "generations": [
            ("Octavia III (2013-2020)", "Très répandue, souvent en break Combi.", "octavia-3"),
            ("Octavia IV (2020-…)", "Plus moderne, très bien équipée.", "octavia-4"),
        ],
        "conseilles": [
            ("2.0 TDI 150 / 1.6 TDI 115", "Diesels endurants, parfaits pour les longs trajets."),
            ("1.0 TSI 115 / 1.5 TSI 150", "Essences sobres."),
        ],
        "surveiller": [
            ("Boîte DSG7 à sec", "Comme sur la Golf : historique et essai en ville."),
        ],
        "verifier": ["Courroie de distribution TDI selon le kilométrage", "Passages DSG", "Usure intérieure (souvent d'anciens taxis/VTC)"],
        "options": ["Attelage", "Régulateur adaptatif", "Boîte automatique"],
        "faq": [("La Skoda Octavia est-elle fiable ?", "Oui, elle partage les moteurs éprouvés de la Golf avec plus d'espace et un prix plus bas.")],
    },
    {
        "slug": "kia-sportage", "photo": "sportage-5", "marque": "Kia", "modele": "Sportage", "marque_id": 39, "modele_cle": "m:1812",
        "carrosserie": "suv", "couleur": "#ff8a4c", "categorie": "SUV familial", "fiabilite": 4,
        "resume": "Un SUV familial bien équipé, avec une garantie constructeur de 7 ans transmissible.",
        "budget": "12 000 à 32 000 €",
        "generations": [
            ("Sportage IV (2016-2021)", "Spacieux et bien équipé.", "sportage-4"),
            ("Sportage V (2022-…)", "Hybride et hybride rechargeable, intérieur très moderne.", "sportage-5"),
        ],
        "conseilles": [
            ("1.6 CRDi 115 / 136", "Diesel sobre, souvent en hybridation légère."),
            ("1.6 T-GDi hybride (Sportage V)", "Sobre et agréable."),
        ],
        "surveiller": [
            ("Garantie restante", "La garantie de 7 ans (ou 150 000 km) se transmet aux propriétaires suivants si l'entretien a été suivi : demandez la date de première immatriculation et le carnet."),
        ],
        "verifier": ["Carnet d'entretien (condition de la garantie)", "Date de première mise en circulation", "Équipements électroniques"],
        "options": ["Caméra 360°", "Sièges chauffants", "Hayon électrique"],
        "faq": [("La garantie Kia est-elle transmissible ?", "Oui, la garantie constructeur de 7 ans se transmet en cas de revente, sous réserve d'un entretien conforme.")],
    },
    {
        "slug": "tesla-model-3", "photo": "model3", "marque": "Tesla", "modele": "Model 3", "marque_id": 51520, "modele_cle": "m:74665",
        "carrosserie": "berline", "couleur": "#e4e4e7", "categorie": "Électrique", "fiabilite": 4,
        "resume": "La berline électrique la plus vendue : grande autonomie, recharge rapide et coûts d'usage très bas.",
        "budget": "18 000 à 35 000 €",
        "generations": [
            ("Model 3 (2019-2023)", "Versions Propulsion, Grande Autonomie et Performance.", "model3"),
            ("Model 3 « Highland » (2023-…)", "Restylée, plus silencieuse et mieux finie."),
        ],
        "conseilles": [
            ("Grande Autonomie", "La plus polyvalente pour les longs trajets."),
            ("Propulsion", "Moins chère, suffisante pour un usage quotidien."),
        ],
        "surveiller": [
            ("État de la batterie", "Demandez un relevé de l'autonomie réelle à 100 % ; la batterie reste couverte 8 ans par Tesla sous conditions de kilométrage."),
            ("Finition des premiers modèles", "Ajustements de carrosserie et bruits de suspension avant parfois signalés."),
        ],
        "verifier": ["Autonomie affichée à 100 %", "Écarts de carrosserie et peinture", "Bruits de bras de suspension avant", "Usure des pneus (couple élevé)"],
        "options": ["Toit panoramique", "Sièges chauffants", "Régulateur adaptatif"],
        "faq": [("Une Tesla Model 3 d'occasion est-elle un bon achat ?", "Oui si la batterie est en bon état : l'entretien est très limité et la recharge à domicile coûte peu.")],
    },
]

# Classements thématiques : (slug du modèle, version conseillée, pourquoi)
CLASSEMENTS = [
    {
        "slug": "voiture-jeune-permis", "titre": "Les meilleures voitures d'occasion pour un jeune permis",
        "court": "Jeune permis", "emoji_label": "🎓", "couleur": "#5aa9ff",
        "description": "Quelle voiture acheter avec un permis tout neuf ? Notre sélection de citadines d'occasion sûres, fiables et pas chères à assurer.",
        "intro": "Avec un permis probatoire, la voiture idéale est simple, sûre et peu puissante : l'assurance d'un jeune conducteur coûte vite très cher au-delà de 100 ch environ. Voici les modèles qui cochent toutes les cases.",
        "criteres": ["Puissance modérée (65 à 100 ch) pour une assurance raisonnable", "Bon niveau de sécurité (ESP, airbags, aides au freinage)", "Entretien simple et pièces bon marché", "Gabarit facile à garer"],
        "prix_max": 12000,
        "liste": [
            ("toyota-yaris", "Yaris 3 Hybride 100 (2012-2020)", "Automatique, ultra fiable et sobre : la plus facile à vivre.", "yaris-3"),
            ("renault-clio", "Clio 4 0.9 TCe 75-90 ou 1.5 dCi 75 (2012-2019)", "Économique à l'achat, à l'entretien et à l'assurance.", "clio-4"),
            ("volkswagen-polo", "Polo 5 1.0 MPI 60-75 (2014-2017)", "Solide, bien finie, mécanique très simple.", "polo-5"),
            ("dacia-sandero", "Sandero 2 1.0 SCe 75 ou 0.9 TCe 90 (2016-2020)", "Le meilleur rapport place/prix.", "sandero-2"),
            ("peugeot-208", "208 I 1.2 PureTech 82 atmosphérique (2015-2019)", "Agréable et bien équipée, sans le souci du moteur turbo.", "208-1"),
            ("citroen-c3", "C3 III 1.2 PureTech 82 (2016-2020)", "Confortable et rassurante sur la route.", "c3-3"),
        ],
    },
    {
        "slug": "voiture-occasion-moins-10000-euros", "titre": "Les meilleures voitures d'occasion à moins de 10 000 €",
        "court": "Moins de 10 000 €", "emoji_label": "💶", "couleur": "#7ad37a",
        "description": "Quelle voiture d'occasion acheter avec 10 000 € ? Notre sélection de modèles fiables, avec les versions à privilégier.",
        "intro": "Sous 10 000 €, on trouve surtout des citadines et des compactes de 6 à 10 ans. Le bon choix tient davantage à la motorisation et à l'entretien qu'au modèle lui-même.",
        "criteres": ["Historique d'entretien complet", "Moteur réputé fiable (voir chaque fiche)", "Kilométrage cohérent avec l'âge (environ 15 000 km par an)", "Contrôle technique récent sans défaut majeur"],
        "prix_max": 10000,
        "liste": [
            ("toyota-yaris", "Yaris 3 Hybride 100 (2013-2017)", "La plus fiable de la sélection.", "yaris-3"),
            ("renault-clio", "Clio 4 1.5 dCi 75-90 (2014-2018)", "Increvable et économique.", "clio-4"),
            ("volkswagen-polo", "Polo 5 1.0 MPI / 1.2 TSI (2014-2017)", "Qualité allemande à petit prix.", "polo-5"),
            ("dacia-sandero", "Sandero 2 0.9 TCe 90 / 1.5 dCi (2016-2020)", "Spacieuse et quasi neuve pour le prix.", "sandero-2"),
            ("peugeot-208", "208 I 1.6 BlueHDi 75-100 (2015-2018)", "Le diesel évite le souci du PureTech.", "208-1"),
            ("volkswagen-golf", "Golf 7 1.6 TDI 105-110 (2013-2016, kilométrage élevé)", "Une compacte de qualité si l'entretien suit.", "golf-7"),
            ("renault-captur", "Captur I 1.5 dCi 90 (2014-2017)", "Un SUV urbain à prix de citadine.", "captur-1"),
        ],
    },
    {
        "slug": "voiture-occasion-moins-20000-euros", "titre": "Les meilleures voitures d'occasion à moins de 20 000 €",
        "court": "Moins de 20 000 €", "emoji_label": "🚗", "couleur": "#ffcf3d",
        "description": "Avec 20 000 €, quelle voiture d'occasion choisir ? Compactes, SUV et hybrides récents : notre sélection et les versions à privilégier.",
        "intro": "Avec 20 000 €, on accède à des modèles récents (3 à 6 ans), souvent encore sous garantie, et à l'hybride Toyota.",
        "criteres": ["Garantie constructeur restante", "Équipements récents (aides à la conduite, CarPlay)", "Motorisation adaptée à votre kilométrage annuel"],
        "prix_max": 20000,
        "liste": [
            ("toyota-c-hr", "C-HR I 1.8 Hybride 122 (2017-2020)", "SUV hybride ultra fiable.", "chr-1"),
            ("toyota-corolla", "Corolla 1.8 Hybride 122 (2019-2021)", "La compacte la plus sereine.", "corolla-12"),
            ("volkswagen-golf", "Golf 7 1.4 TSI / 2.0 TDI (2015-2019)", "La valeur sûre.", "golf-7"),
            ("skoda-octavia", "Octavia III Combi 2.0 TDI 150 (2017-2020)", "La familiale la plus spacieuse.", "octavia-3"),
            ("peugeot-3008", "3008 II 1.5 BlueHDi 130 (2018-2020)", "Le SUV familial le plus séduisant.", "3008-2"),
            ("dacia-duster", "Duster II 1.5 Blue dCi 115 (2018-2022)", "Rustique, malin, 4x4 possible.", "duster-2"),
            ("renault-clio", "Clio 5 E-Tech hybride 140 (2020-2022)", "Citadine hybride récente et sobre.", "clio-5"),
        ],
    },
    {
        "slug": "voiture-occasion-moins-30000-euros", "titre": "Les meilleures voitures d'occasion à moins de 30 000 €",
        "court": "Moins de 30 000 €", "emoji_label": "✨", "couleur": "#c58bff",
        "description": "Quelle voiture d'occasion acheter avec 30 000 € ? Électriques, SUV familiaux et hybrides récents : notre sélection.",
        "intro": "Avec 30 000 €, on peut viser une voiture de moins de 3 ans, une électrique performante ou un SUV familial très bien équipé.",
        "criteres": ["Garantie restante (constructeur ou batterie)", "Coût d'usage : électrique et hybride font de grosses économies", "Équipements de confort et de sécurité récents"],
        "prix_max": 30000,
        "liste": [
            ("tesla-model-3", "Model 3 Grande Autonomie (2019-2022)", "Électrique de référence, coût d'usage très bas.", "model3"),
            ("kia-sportage", "Sportage V 1.6 T-GDi Hybride (2022-…)", "SUV familial avec garantie 7 ans transmissible.", "sportage-5"),
            ("toyota-corolla", "Corolla 2.0 Hybride 180-196 (2020-…)", "Fiabilité et sobriété.", "corolla-12"),
            ("peugeot-3008", "3008 II 1.5 BlueHDi 130 EAT8 (2018-2020)", "Très bien équipé.", "3008-2"),
            ("skoda-octavia", "Octavia IV Combi 1.5 TSI / 2.0 TDI (2020-…)", "Espace et technologie.", "octavia-4"),
            ("volkswagen-golf", "Golf 8 1.5 TSI / 2.0 TDI (2020-…)", "La compacte la plus aboutie.", "golf-8"),
        ],
    },
    {
        "slug": "voitures-occasion-les-plus-fiables", "titre": "Les voitures d'occasion les plus fiables",
        "court": "Les plus fiables", "emoji_label": "🛡️", "couleur": "#41d1b4",
        "description": "Quelles sont les voitures d'occasion les plus fiables ? Hybrides Toyota, diesels éprouvés : les modèles et moteurs qui durent.",
        "intro": "La fiabilité dépend surtout du couple modèle + moteur, et de l'entretien. Voici les combinaisons réputées les plus durables.",
        "criteres": ["Moteurs simples et éprouvés", "Peu de pannes connues", "Entretien régulier et documenté"],
        "prix_max": None,
        "liste": [
            ("toyota-yaris", "Yaris 4 Hybride 116 (2020-…)", "Une référence absolue de fiabilité.", "yaris-4"),
            ("toyota-corolla", "Corolla 12 Hybride (2019-…)", "Même technologie, en compacte.", "corolla-12"),
            ("toyota-c-hr", "C-HR I Hybride (2016-2023)", "La fiabilité Toyota en SUV.", "chr-1"),
            ("dacia-duster", "Duster II 1.5 Blue dCi (2018-2024)", "Mécanique simple et robuste.", "duster-2"),
            ("volkswagen-polo", "Polo 6 1.0 MPI / 1.0 TSI (2017-…)", "Petite, solide, durable.", "polo-6"),
            ("skoda-octavia", "Octavia III 2.0 TDI (2013-2020)", "Endurante, idéale gros rouleurs.", "octavia-3"),
            ("renault-clio", "Clio 4 1.5 dCi (2012-2019)", "Le diesel K9K est quasi increvable.", "clio-4"),
        ],
    },
]
