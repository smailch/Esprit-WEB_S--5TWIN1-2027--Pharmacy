# CLAUDECONTEXT — Ahmed Allaya (membre 3) : Pathologie + Personne

Consignes complètes : `../PROMPT_CLAUDE_CODE_MEMBRE3.md`. Contexte d'équipe : `../CLAUDECONTEXT.md`.

## Décisions
- Périmètre : modules **Pathologie** et **Personne** (slide 6 de la présentation), rien d'autre en CRUD.
- Tout dans `Ahmed/`, branche `AhmedAllaya`. `ontologie/*` jamais modifié.
- Noms de l'ontologie centralisés dans `backend/app/config/ontology_mapping.py`.
- `SPARQL_BACKEND=rdflib` par défaut (graphe en mémoire, aucun service) ; `fuseki` via Docker ou Java.
- `PatientEnfant`/`PatientAdulte` jamais écrits : on stocke `:Patient` + `:age`, la classe est dérivée.
- HermiT : `xsd:date` non supporté → correctif en mémoire (`xsd:dateTime`) dans `validate_ontology.py`.
  **À remonter à l'équipe** : remplacer `xsd:date` par `xsd:dateTime` dans `pharma.ttl` (ou retirer le range).
- Frontend sur le port **5174** (5173 = site vitrine de l'équipe).
- Scripts `.ps1` en UTF-8 **avec BOM** et sans `$ErrorActionPreference = "Stop"` (Windows PowerShell 5.1).
- Docker non installé sur le PC de dev : `docker-compose.yml` fourni mais non testé localement.

## Avancement
- [x] Étape 2 : squelette, client SPARQL (Fuseki/rdflib), scripts, validation HermiT
- [x] Étape 3 : individus (19 pathologies, 11 patients, 5 médecins, 3 pharmaciens), HermiT OK
- [x] Étape 4 : 36 requêtes nommées (`backend/sparql`), services, tests rdflib, `docs/SPARQL.md` généré
- [x] Étape 5 : API FastAPI (`/api/...`, OpenAPI sur `/docs`), erreurs `{code, message, details}`,
  201/204/404/409/422, console SPARQL lecture seule, tests d'intégration TestClient
- [x] Étape 6 : NLP spaCy + RapidFuzz + scikit-learn (`app/nlp/`, `POST /api/nlp/ask`), 14 intentions,
  232 exemples, 78 questions de test → 100 % (`scripts/eval_nlp.py`). Voir `docs/NLP.md`.
- [x] Étape 7 : frontend React 18 + Vite : tableau de bord, pathologies, personnes (3 onglets),
  fiche patient + alertes, assistant NLP, graphe SVG, console SPARQL ; lint 0 avertissement.
- [x] Étape 8 : `docs/SCENARIO_DEMO.md` (rejoué via l'API), `docs/ORAL_QA.md`, `README.md`, scripts setup/start
- [x] Étape 9 : `scripts/check_clean_install` (clone neuf → setup → 65 tests → lint/build → /api/health)

## Reste à faire (optionnel)
- Captures d'écran de secours dans `docs/captures/` (veille de l'oral).
- `materialize_inferences.py` (inférences HermiT dans un graphe nommé Fuseki) : non fait, l'appli fonctionne sans.
- Tester `docker compose up` sur une machine avec Docker.
- Intégration avec les modules des autres membres (chargement de leurs extensions TTL) si l'équipe le décide.
