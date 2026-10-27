# Contexte — Ahmed Allaya (membre 3) : modules Pathologie + Personne

Consignes d'origine : `PROMPT_CLAUDE_CODE_MEMBRE3.md` (non versionné). Contexte d'équipe : `CLAUDECONTEXT.md` (racine).

## Organisation (projet unifié avec le module A, branche `AhmedAllaya`)
- **Un seul backend** (`backend/`, port 8000, préfixe `/api`) : mon module est `backend/app/modules/pathologie_personne/`,
  branché dans `app/main.py` à côté de `molecule_medicament/`. Routes distinctes de celles du module A ;
  `/api/health`, `/api/admin/reset` et `/api/sparql` sont communs (ceux du module A).
- **Un seul graphe** : `app/graph_store.py` (rdflib + inférence owlrl, sauvegarde `backend/data/runtime.ttl`).
  Mes lectures portent sur le graphe déclaré (`store.base`) ; mes écritures passent par `store.update`.
- **Individus** : `ontologie/extensions/individus-ahmed.ttl`, chargé par `graph_store.load` en plus de `pharma.ttl` (non modifié).
- **Un seul frontend** (React + react-router) : mes pages sont dans `src/pages/sante/` (routes `/sante`, `/pathologies`,
  `/personnes`, `/patients/:id`, `/assistant-sante`), dans le menu d'`AppShell`. Style confiné sous `.sante`.
- spaCy : modèle commun `fr_core_news_sm` (fourni dans `backend/vendor/`).

## Décisions
- Noms de l'ontologie centralisés dans `pathologie_personne/mapping.py`.
- `PatientEnfant`/`PatientAdulte` jamais écrits : on stocke `:Patient` + `:age`, la classe est dérivée.
- HermiT : `xsd:date` non supporté → correctif en mémoire (`xsd:dateTime`) dans `backend/tools/validate_ontology.py`.
  **À remonter à l'équipe** : remplacer `xsd:date` par `xsd:dateTime` dans `pharma.ttl`.
- Fichiers communs modifiés (ajouts uniquement) : `backend/app/main.py`, `config.py`, `graph_store.py`, `tests/conftest.py`,
  `requirements.txt` (owlready2), `src/App.jsx`, `src/app/AppShell.jsx`, `src/app/app.css`, `README.md`, `.gitignore`.

## Avancement
- [x] Ontologie : 19 pathologies, 11 patients, 5 médecins, 3 pharmaciens ; HermiT cohérent
- [x] 36 requêtes SPARQL nommées (`docs/sante/SPARQL.md` généré par `backend/tools/gen_sparql_doc.py`)
- [x] API REST + 64 tests (100 avec le module A)
- [x] Assistant santé : 14 intentions, 100 % sur 78 questions (`backend/tools/eval_nlp_sante.py`)
- [x] Pages React intégrées à l'application commune
- [x] Scénario de démo, questions de l'oral

## Reste à faire (optionnel)
- Captures d'écran de secours dans `docs/sante/captures/` (veille de l'oral).
- Les tests sont lents (~3 min) : chaque remise à zéro relance l'inférence owlrl du graphe commun.
