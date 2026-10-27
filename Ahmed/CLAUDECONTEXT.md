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
- Docker non installé sur le PC de dev : `docker-compose.yml` fourni mais non testé localement.

## Avancement
- [x] Étape 2 : squelette, client SPARQL (Fuseki/rdflib), scripts, validation HermiT
- [x] Étape 3 : individus (19 pathologies, 11 patients, 5 médecins, 3 pharmaciens), HermiT OK
- [x] Étape 4 : 36 requêtes nommées (`backend/sparql`), services, 50 tests rdflib, `docs/SPARQL.md` généré
- [x] Étape 5 : API FastAPI (`/api/...`, OpenAPI sur `/docs`), erreurs `{code, message, details}`,
  201/204/404/409/422, console SPARQL lecture seule ; 58 tests (dont 8 d'intégration TestClient)
- [x] Étape 6 : NLP spaCy + RapidFuzz + scikit-learn (`app/nlp/`, `POST /api/nlp/ask`), 14 intentions,
  232 exemples, 78 questions de test → 100 % (`scripts/eval_nlp.py`) ; 65 tests au total. Voir `docs/NLP.md`.

## Reste à faire
- Frontend, docs (scénario, Q&A, README), installation propre.
