# CLAUDECONTEXT — Membre 3 (Ahmed Allaya) : Pathologie + Personne

Consignes complètes : `../PROMPT_CLAUDE_CODE_MEMBRE3.md`. Contexte d'équipe : `../CLAUDECONTEXT.md`.

## Décisions
- Périmètre : modules **Pathologie** et **Personne** (slide 6 de la présentation), rien d'autre en CRUD.
- Tout dans `membre3/`, branche `AhmedAllaya`. `ontologie/*` jamais modifié.
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

## Reste à faire
- API, NLP, frontend, docs, installation propre.
