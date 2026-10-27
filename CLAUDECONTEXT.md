# CLAUDECONTEXT — Mémoire du projet (à relire à chaque session)

## Projet
- Module : Web Sémantique — Esprit, 5 TWIN, 2026/2027
- Équipe : NeoCoders — Allaya Ahmed, Gobji Walid, Missaoui Mourad, Chemlali Ismail
- Thème : « Ontologie Pharmaceutique et Santé » (PharmaSémantique)
- Dépôt GitHub : https://github.com/smailch/Esprit-WEB_S--5TWIN1-2027--Pharmacy (branche main)
- Validation finale : mini-projet, semaine du 26 octobre 2026

## Consignes de la prof (mail)
1. Choisir une thématique de la liste de la présentation du projet.
2. Créer une ontologie liée à la thématique.
3. Créer des ObjectProperty, DataProperty, individus et axiomes.
4. Créer des interfaces graphiques (front et back) — technologies libres.
5. Exécuter des requêtes SPARQL (CRUD, filtrage, recherche…).
6. Assurer la communication front-end ↔ back-end.
7. Module NLP/TALN « traducteur intelligent » : question en langage naturel → requête SPARQL exécutable par le serveur.
   - INTERDIT : API LLM clés en main via simple prompt (Gemini, OpenAI…).
   - OBLIGATOIRE : bibliothèques NLP (spaCy, NLTK, Hugging Face Transformers…) et les citer explicitement dans la présentation.

## Grille de notation (/20, par étudiant)
| Critère | Points |
|---|---|
| Requêtes SPARQL | 4 |
| Individus | 2 |
| Scénario | 2 |
| API IA (module NLP → SPARQL) | 4 |
| Interfaces graphiques | 3 |
| Communication BE ↔ FE | 3 |
| Valeur ajoutée | 2 |

Note : la grille est individuelle → chaque membre doit pouvoir présenter sa partie.

## Ontologie (selon la présentation)
- 8 classes : SubstanceActive, Médicament, EffetSecondaire, ContreIndication, Pathologie, Personne, Prescription, ModalitéAdministration
- 5 relations principales : contientPrincipeActif, peutProvoquer, aPourContreIndication, concernePathologie, estIndiquéPour
- 11 datatype properties (dont nomCommercial, codeATC, dosage, gravitéEffet, datePrescription, spécialité)
- Raisonneur : HermiT (Protégé), visualisation OntoGraf
- Détail des classes/individus : `src/data/ontologyData.js`

## État d'avancement
- [x] Site vitrine React + Vite (présentation de l'ontologie) — poussé sur GitHub
- [x] Ontologie v2 corrigée : `ontologie/pharma.ttl` + `pharma.owl` + `requetes.sparql` (8 modules × 3 niveaux, Administration remplacé par DonneeClinique, URI sans accents)
- [ ] Ismail donnera ensuite les deux modules dont il est responsable → à développer
- [ ] Back-end + SPARQL (CRUD, filtres, recherche)
- [ ] Front-end applicatif branché au back-end
- [ ] Module NLP → SPARQL (spaCy / NLTK / Transformers, sans API LLM)

## Objectif personnel d'Ismail (PRIORITÉ)
- Obtenir la note maximale sur chaque critère de la grille pour SA partie (ses deux modules).
- Soigner particulièrement la « Valeur ajoutée » (2 pts) : proposer des fonctionnalités qui vont au-delà du minimum.
- Pour chaque module : couvrir explicitement chaque critère de la grille (SPARQL CRUD + filtres + recherche, individus, scénario de démo, NLP sans API LLM, interface soignée, communication BE↔FE) et préparer une démo claire et défendable à l'oral.
- Idées de valeur ajoutée à proposer le moment venu (à valider selon les modules) : raisonnement/inférence visible (détection d'incohérences, ex. contre-indication), suggestions de questions NLP + affichage de la requête SPARQL générée, visualisation graphe des résultats, export des résultats, historique des requêtes, tolérance aux fautes/synonymes dans le NLP.

## Contrainte : tout dans Git + portable (OBLIGATOIRE)
- Tout le travail doit être versionné et poussé sur le dépôt GitHub (code, ontologie .owl, données, scripts, docs).
- Le projet doit fonctionner sur le PC d'un coéquipier après un simple `git clone` + commandes d'installation documentées dans le README.
- Cela inclut le modèle IA/NLP : pas de dépendance à un fichier local absent du dépôt.
  - Modèles légers → les committer (si < ~50 Mo) ou les télécharger automatiquement via un script d'installation reproductible (ex. `python -m spacy download fr_core_news_sm`, versions épinglées).
  - Modèles lourds → Git LFS ou téléchargement scripté, jamais un chemin absolu propre à ce PC.
- Dépendances épinglées (package-lock.json, requirements.txt avec versions), chemins relatifs uniquement, pas de secrets/clé API, config via fichier `.env.example`.
- Idéalement : un script de démarrage unique (ou docker-compose) qui lance back + front + triplestore.
- Tester une installation « propre » (clone neuf dans un dossier temporaire) avant chaque livraison.

## Prochaine étape
Attendre le fichier de l'ontologie et la description des deux modules d'Ismail. Ne rien coder de ces modules avant.

## Journal
- 2026-10-27 : ontologie v2 réécrite à partir de ontograf.rdf (corrections : classe Voie non déclarée, codeATC/idPatient à la fois Object et Datatype property, Personne à 3 sous-classes, accents dans les URI). Répartition proposée 2 modules/membre dans ontologie/README.md (à confirmer par l'équipe).
- 2026-10-27 : site vitrine créé et poussé ; consignes et grille notées ici.
