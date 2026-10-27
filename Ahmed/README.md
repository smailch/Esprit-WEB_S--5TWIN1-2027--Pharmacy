# PharmaSémantique — modules Pathologie & Personne (Ahmed Allaya)

Projet Web sémantique, ESPRIT 5 TWIN 2026/2027, équipe NeoCoders.
Ontologie partagée : `../ontologie/pharma.ttl` (non modifiée) + mes individus `ontology-extension/individus-ahmed.ttl`.
**Données fictives — aucun conseil médical.**

| Partie | Technologie | Où |
|---|---|---|
| Triplestore | rdflib en mémoire (défaut) ou Apache Jena Fuseki | `backend/app/sparql/client.py` |
| SPARQL | 36 requêtes nommées | `backend/sparql/*.rq`, doc : `docs/SPARQL.md` |
| API | Python 3.11, FastAPI, Pydantic | `backend/app/` → http://localhost:8000/docs |
| NLP → SPARQL | spaCy, RapidFuzz, scikit-learn (aucune API de LLM) | `backend/app/nlp/`, doc : `docs/NLP.md` |
| Interface | React 18 + Vite | `frontend/` → http://localhost:5174 |
| Raisonneur | HermiT (owlready2) | `scripts/validate_ontology.py` |

## Prérequis
- **Python 3.11**, **Node.js 18+** (testé avec 22), **Java 17+** (seulement pour HermiT et Fuseki sans Docker).
- Aucune clé API. Connexion Internet uniquement pour l'installation (pip, npm, modèle spaCy).

## Installation et lancement (sans Docker — recommandé)
Windows (PowerShell), depuis le dossier `Ahmed/` :
```powershell
.\scripts\setup.ps1      # venv, dépendances épinglées, modèle spaCy, classifieur, npm ci
.\scripts\start.ps1      # backend (nouvelle fenêtre) + frontend
```
Linux / macOS : `sh scripts/setup.sh` puis `sh scripts/start.sh`.

À la main :
```powershell
cd backend
py -3.11 -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
.venv/Scripts/python scripts/setup_models.py
.venv/Scripts/python -m uvicorn app.main:app --reload     # API : http://localhost:8000/docs
cd ../frontend
npm ci
npm run dev                                                # Appli : http://localhost:5174
```

## Avec Docker
```bash
cd Ahmed
docker compose up --build
```
Lance Fuseki (http://localhost:3030, dataset `pharma`, chargé automatiquement au démarrage du backend), l'API et l'application.
⚠ Le fichier n'a pas pu être testé sur le PC de développement (Docker absent).

## Avec Fuseki sans Docker
1. Télécharger Apache Jena Fuseki (https://jena.apache.org/download/), puis lancer `fuseki-server --mem --update /pharma`.
2. Dans `.env` : `SPARQL_BACKEND=fuseki` (voir `.env.example`).
3. Lancer le backend : il charge l'ontologie si le dataset est vide. Rechargement forcé : `.\scripts\load_ontology.ps1`.

## Scripts utiles (`scripts/`, chacun en `.ps1` et `.sh`)
| Script | Rôle |
|---|---|
| `validate_ontology` | HermiT : cohérence, classes inférées (Lina → PatientAdulte…), individus par classe |
| `eval_nlp` | Précision du NLP par intention (cible ≥ 90 %) |
| `reset_data` | Remet les données dans l'état initial (backend lancé) — aussi dans le pied de page de l'appli |
| `load_ontology` | Charge l'ontologie dans Fuseki |
| `check_clean_install` | Clone neuf dans un dossier temporaire, installation, tests, démarrage, appel `/api/health` |
| `gen_sparql_doc.py` | Régénère `docs/SPARQL.md` (résultats réels) |

## Tests
```powershell
cd backend; .venv/Scripts/python -m pytest -q     # 65 tests : SPARQL, API, NLP (rdflib, sans Fuseki)
cd ../frontend; npm run lint
```

## Jeu de données
19 pathologies (5 infections aiguës, 4 douleurs aiguës, 4 maladies métaboliques, 4 insuffisances d'organe, 2 autres chroniques),
11 patients (3 enfants, 8 adultes, 5 dont la classe est seulement inférée, 1 sans pathologie), 5 médecins, 3 pharmaciens.
Les prescriptions, médicaments et molécules viennent des modules des autres membres (lecture seule).

## Documentation
`docs/SCENARIO_DEMO.md` (démo de 7 min) · `docs/ORAL_QA.md` (20 questions du jury) · `docs/SPARQL.md` · `docs/NLP.md` · `CLAUDECONTEXT.md` (décisions, avancement).

## Dépannage
| Problème | Solution |
|---|---|
| Bandeau « Backend injoignable » | Lancer l'API (`uvicorn`) dans `backend/` ; vérifier http://localhost:8000/api/health |
| Port 5174 ou 8000 occupé | Changer `--port` (backend) ou `server.port` dans `frontend/vite.config.js` et `VITE_API_TARGET` dans `.env` |
| `fr_core_news_md` introuvable | `.venv/Scripts/python scripts/setup_models.py` |
| Premier appel NLP lent (~4 s) | Normal : chargement de spaCy, les suivants prennent environ 20 ms |
| `validate_ontology` échoue sur Java | Installer Java 17+ et vérifier `java -version` |
| `py -3.11` introuvable | Installer Python 3.11 (python.org) ou remplacer par le chemin de votre Python 3.11 |
