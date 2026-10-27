# PharmaSémantique — Ontologie Pharmaceutique et Santé

Mini-projet de Web Sémantique — **NeoCoders**, Esprit 5 TWIN, 2026/2027.
Ontologie OWL (Protégé / HermiT) + back-end SPARQL + application React + assistant en langage naturel.

> Projet académique : données fictives, aucune recommandation médicale.

---

## Installation sur un nouveau PC (5 minutes)

Prérequis : **Python 3.11 ou plus récent** (testé avec 3.13) et **Node.js 18+**. Aucune clé API, aucun serveur à installer.

```bash
git clone https://github.com/smailch/Esprit-WEB_S--5TWIN1-2027--Pharmacy.git
cd Esprit-WEB_S--5TWIN1-2027--Pharmacy
```

| | Windows | macOS / Linux |
|---|---|---|
| Installer (une seule fois) | `scripts\setup.bat` | `./scripts/setup.sh` |
| Lancer | `scripts\start.bat` | `./scripts/start.sh` |

Puis ouvrir **http://localhost:5173** (site vitrine) → bouton « Ouvrir l'application ».
Documentation interactive de l'API : **http://localhost:8000/docs**.

L'installation télécharge automatiquement le modèle spaCy `fr_core_news_sm` (version épinglée).
Le modèle d'intention entraîné (`backend/nlp/models/pharmanlu_intent_v1.joblib`) est déjà dans le dépôt.

> **Windows** : clonez dans un dossier au chemin court (ex. `C:\projets\pharma`). Les chemins de plus de 260 caractères
> empêchent spaCy de charger ses bibliothèques (« DLL load failed… Nom de fichier ou extension trop long »).

### Lancement manuel (si besoin)
```bash
# Terminal 1 — API
backend/.venv/Scripts/python -m uvicorn app.main:app --app-dir backend --port 8000   # Windows
backend/.venv/bin/python     -m uvicorn app.main:app --app-dir backend --port 8000   # macOS/Linux
# Terminal 2 — front
npm run dev
```

---

## Architecture

```
ontologie/        pharma.ttl (source), pharma.owl (Protégé), requetes.sparql
  extensions/                        individus ajoutés par les membres (chargés en plus de pharma.ttl)
backend/          FastAPI + rdflib + owlrl (inférence OWL 2 RL)
  app/modules/molecule_medicament/   module A : routes, 16 requêtes SPARQL nommées, CRUD
  app/modules/pathologie_personne/   module Pathologie + Personne : routes, 36 requêtes .rq, CRUD, NLP
  tools/                             validation HermiT, évaluation NLP, génération de docs/sante/SPARQL.md
  nlp/pharmanlu/                     modèle IA PharmaNLU-A (question → SPARQL)
  nlp/data/  nlp/models/             jeux de données et modèle entraîné
  tests/                             100 tests pytest (36 module A + 64 Pathologie + Personne)
src/              React + Vite : site vitrine (/) + application (/molecules, /medicaments, /sante, /pathologies…)
scripts/          setup / start (Windows et macOS/Linux)
```

- Le graphe est chargé depuis `ontologie/pharma.ttl`, puis enrichi par le raisonneur **OWL 2 RL** (owlrl) dans un graphe nommé séparé : l'interface distingue les faits **déclarés** et **inférés**.
- Le CRUD modifie `backend/data/runtime.ttl` (ignoré par Git) ; `pharma.ttl` n'est jamais écrasé. Bouton « Réinitialiser les données » ou `POST /api/admin/reset` pour revenir à l'état d'origine.
- Chaque réponse de l'API contient les requêtes SPARQL exécutées, affichées dans l'interface.

## Module A — Molécule + Médicament (Chemlali Ismail)

| Page | Contenu |
|---|---|
| Molécules | liste filtrable (classe via la hiérarchie, ATC, recherche sans accents), arbre 3 niveaux, fiche, CRUD |
| Médicaments | cartes filtrables (type, ordonnance, forme, prix), statistiques, fiche, graphe CONSTRUCT, CRUD |
| Comparateur | princeps ↔ génériques de même composition, économie en DT et en % |
| Interactions | interactions (propriété symétrique) et doublons de principe actif entre plusieurs médicaments |
| Assistant IA | question en français → SPARQL → réponse (modèle PharmaNLU-A) |
| Console SPARQL | 16 requêtes du catalogue en un clic + éditeur (lecture seule) |

### Assistant IA — modèle PharmaNLU-A (aucune API de LLM)

| Étape | Outil |
|---|---|
| Normalisation, tokenisation, lemmatisation | **spaCy 3.8** + `fr_core_news_sm` |
| Reconnaissance des entités (dictionnaire généré depuis l'ontologie) | **spaCy EntityRuler** |
| Correction des fautes de frappe | **RapidFuzz** (distance de Levenshtein) |
| Classification de l'intention (12 intentions) | **scikit-learn** : TF-IDF mots + caractères → régression logistique |
| Génération et exécution de la requête | gabarits SPARQL + **rdflib** |

Résultats sur 96 questions de test écrites à la main (jamais vues à l'entraînement) : **96,9 % d'intentions correctes, 100 % d'entités reconnues**.

```bash
cd backend
.venv/Scripts/python nlp/data/generer_donnees.py   # régénère le jeu d'entraînement
.venv/Scripts/python -m nlp.train                  # ré-entraîne + évalue + écrit la carte du modèle
.venv/Scripts/python -m nlp.evaluate               # évalue le modèle enregistré
.venv/Scripts/python -m pytest -q                  # 36 tests
```

## Module Pathologie + Personne (Allaya Ahmed)

Section **Pathologie + Personne** du menu de l'application. Individus : `ontologie/extensions/individus-ahmed.ttl`
(19 pathologies, 11 patients, 5 médecins, 3 pharmaciens ; `pharma.ttl` n'est pas modifié).

| Page | Contenu |
|---|---|
| Tableau santé (`/sante`) | compteurs enfants/adultes, aiguës/chroniques (sous-types compris), répartitions, alertes en cours |
| Pathologies | recherche sans accents, filtre aiguë/chronique/sous-type, CRUD, médicaments indiqués et contre-indiqués, patients |
| Personnes | onglets Patients / Médecins / Pharmaciens, filtres (âge, sexe, pathologie, spécialité), CRUD ; classe Enfant/Adulte **dérivée de l'âge** (badge « inféré ») |
| Fiche patient | pathologies (ajout/retrait), prescriptions, **alerte de sécurité en direct** (contre-indication ou allergie), export Turtle |
| Assistant santé | question en français → SPARQL → résultats, avec entités surlignées, confiance et étapes du pipeline |
| Graphe | relations entrantes et sortantes d'une entité |

- **API** : `/api/pathologies`, `/api/patients`, `/api/medecins`, `/api/pharmaciens` (CRUD, 201/204/404/409/422),
  `/api/alertes`, `/api/sante/stats`, `/api/sante/recherche`, `/api/sante/graphe/{id}`, `/api/sante/nlp/ask`.
- **SPARQL** : 36 requêtes nommées et paramétrées (aucune concaténation de texte utilisateur), documentées avec leurs vrais résultats dans `docs/sante/SPARQL.md`.
- **Assistant santé (aucune API de LLM)** : spaCy (`fr_core_news_sm`, PhraseMatcher, Matcher), RapidFuzz, scikit-learn
  (TF-IDF → régression logistique, 14 intentions) ; **100 % sur 78 questions de test**. Détails : `docs/sante/NLP.md`.
- Démo et oral : `docs/sante/SCENARIO_DEMO.md`, `docs/sante/ORAL_QA.md`.

```bash
cd backend
.venv/Scripts/python -m pytest -q tests/test_sante_sparql.py tests/test_sante_api.py tests/test_sante_nlp.py   # 64 tests
.venv/Scripts/python tools/eval_nlp_sante.py      # précision de l'assistant santé
.venv/Scripts/python tools/validate_ontology.py   # HermiT (Java requis) : cohérence + classes inférées
```

## Équipe NeoCoders

Allaya Ahmed · Gobji Walid · Missaoui Mourad · Chemlali Ismail
