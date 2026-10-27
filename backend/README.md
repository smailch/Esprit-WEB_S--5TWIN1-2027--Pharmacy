# Backend — module B (effets secondaires et contre-indications)

API FastAPI qui charge l’ontologie `ontologie/pharma.ttl` avec RDFLib, exécute des requêtes SPARQL et traduit une question française en SPARQL **sans API LLM externe**.

Dans l’application commune, ces routes sont montées sous `/api/b` (`/api/b/nlp/ask`, `/api/b/effects`, …) pour laisser `/api/nlp/ask` et `/api/health` aux autres modules. Les tests isolés lancent la même API sous `/api`.

URI de base : `http://example.org/pharma#`.

## Noms réels utilisés

Les classes de niveau 3 des contre-indications ne s’appellent pas `Allergique`, `Digestive`, `Renale` ou `Hepatique`. Dans `pharma.ttl` ce sont :

- `ContreIndicationAllergique`
- `ContreIndicationDigestive`
- `ContreIndicationRenale`
- `ContreIndicationHepatique`

Les effets sont `EffetLegerDigestif`, `EffetLegerCutane`, `EffetGraveDigestif` et `EffetGraveNeurologique`.

Il n’existe pas de propriété directe entre un médicament et un effet. Les chemins assertés sont :

- médicament `contientMolecule` molécule `peutProvoquer` effet ;
- molécule `aContreIndication` contre-indication `concernePathologie` pathologie.

`CI_AllergiePenicilline` n’a pas de triplet `concernePathologie`. `Demangeaison` et `UlcerePerfore` ne sont la cible d’aucun `peutProvoquer`. La codéine provoque des effets, mais aucun médicament ne la contient.

RDFLib n’applique pas HermiT. Les équivalences OWL, les restrictions `hasValue` et la chaîne `estContreIndiquePour` ne sont pas matérialisées. Les résultats affichés viennent des triplets réellement présents.

## Installation (Windows)

Prérequis : Python 3.11 ou plus récent. Les versions ci-dessous sont celles de `requirements.txt` (spaCy 3.8.18, compatible Python 3.13 ; spaCy 3.8.4 ne l’est pas).

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m spacy download fr_core_news_sm
copy .env.example .env
```

`fr_core_news_sm` ajoute la lemmatisation française. Sans ce modèle, l’API démarre quand même : spaCy fournit un pipeline `blank` et un `PhraseMatcher` alimenté par les libellés de l’ontologie. Si le paquet spaCy lui-même est absent, un parcours lexical du même lexique prend le relais. Aucun de ces modes n’appelle un service externe.

Le graphe de travail est créé au premier lancement dans `backend/data/graph.ttl`, à partir de `pharma.ttl` (ou de `pharma.owl` si le Turtle est absent). Les écritures CRUD modifient cette copie, pas le fichier source. Supprimer `graph.ttl` recharge l’ontologie d’origine.

## Lancement

Depuis `backend`, avec l’environnement virtuel activé :

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Documentation interactive : http://127.0.0.1:8000/docs

Le frontend Vite proxifie `/api` vers ce port. Le jeton d’écriture de démonstration est `neocoders-module-b` (en-tête `X-Write-Token`). Ce n’est pas un secret de production.

## Tests

```powershell
cd backend
python -m pytest
```

Les tests copient l’ontologie dans un dossier temporaire. `ontologie/pharma.ttl` n’est pas modifié.

## Traducteur Qwen2.5 3B Instruct

`NLP_ENGINE=qwen` envoie la question à **Qwen2.5 3B Instruct** via Ollama (`http://127.0.0.1:11434`, modèle `qwen2.5:3b`). Le modèle reçoit le lexique réel du graphe et doit répondre par une seule requête SPARQL. Cette requête passe par le garde-fou de lecture avant RDFLib. Les poids ne sont pas dans le dépôt.

```powershell
winget install Ollama.Ollama
ollama pull qwen2.5:3b
```

Ce modèle tient dans les 4 Go de la GTX 1650. Le fichier pèse environ 1,9 Go. Le 7B (environ 4,7 Go) dépasse la mémoire vidéo et la RAM libre de cette machine.

Si Ollama ou le modèle est absent, `app/nlp/pipeline.py` répond avec la chaîne par règles et ajoute un avertissement. `GET /api/health` expose `llm.ready` et `llm.detail`.

## Méthode TALN

La chaîne de repli est locale et expliquable. Chaque étape est un module :

1. `app/nlp/preprocessing.py` — minuscules, suppression des accents, ponctuation, et variantes (`effets secondaires`, pluriels, `rénales` → `renal`).
2. `app/nlp/entity_extractor.py` — lexique construit depuis le graphe (libellés, noms commerciaux, identifiants). spaCy `PhraseMatcher` repère ces expressions. Avec `fr_core_news_sm`, les lemmes sont aussi confrontés au lexique.
3. `app/nlp/intent_classifier.py` — règles ordonnées : compter, vérifier, lister des médicaments, lister des effets ou des contre-indications, filtrer par gravité ou catégorie.
4. `app/nlp/sparql_generator.py` — un modèle SPARQL par intention. Seules des URI déjà présentes dans l’ontologie sont insérées, via leur forme RDFLib, jamais le texte brut de la question.
5. RDFLib exécute la requête. Si l’intention est inconnue, aucune requête n’est fabriquée : la réponse demande une reformulation.
6. `app/nlp/pipeline.py` renvoie l’intention, les entités, la requête, les résultats et les avertissements (relation absente, molécule sans médicament, homonyme).

Bibliothèques réellement utilisées : **FastAPI**, **RDFLib**, **Pydantic**, **Uvicorn**, **spaCy**, **httpx**, **pytest**. Le modèle de traduction est Qwen2.5 3B Instruct, exécuté par Ollama sur la machine. Aucune API OpenAI ou Gemini n’est appelée.

### Exemples

| Question | Intention | Repère |
|---|---|---|
| Quels sont les effets secondaires graves ? | `list_severe_effects` | `niveauGravite` = `grave` |
| Quels médicaments sont associés à des effets digestifs ? | `list_drugs_for_effect_category` | `contientMolecule` / `peutProvoquer`, classes digestives |
| Quelles sont les contre-indications rénales ? | `list_contraindications_by_category` | `ContreIndicationRenale` |
| Quels médicaments sont liés aux allergies ? | `list_drugs_for_ci_category` | `ContreIndicationAllergique`, pas la classe `Allergie` |
| Quels effets secondaires sont associés à Doliprane ? | `list_effects_of_entity` | Doliprane → paracétamol → éruption cutanée |
| Combien d’effets secondaires sont enregistrés ? | `count_effects` | 8 individus |
| Affiche les contre-indications hépatiques. | `list_contraindications_by_category` | `ContreIndicationHepatique` |
| L’ibuprofène peut-il provoquer une hémorragie digestive ? | `check_relation` | `ASK` vrai |

## Endpoints

Les listes acceptent `q`, `page`, `page_size` (1–100) et `sort` (`label`, `gravite`, `frequence`, `type`, préfixe `-` pour l’ordre inverse).

### `GET /api/health`

```json
{"status": "ok", "triples": 850, "spacy": "blank", "module": "B"}
```

### `GET /api/ontology/stats`

Nombre de triplets et d’individus par module, plus la limite de raisonnement.

### `GET /api/effects?gravite=grave&categorie=digestif&medicament=Advil`

```json
{"items": [{"id": "HemorragieDigestive", "label": "Hémorragie digestive", "gravite": "grave", "type": "EffetGraveDigestif"}], "total": 1, "page": 1, "pageSize": 20}
```

`categorie` vaut `digestif`, `cutane` ou `neurologique`. `gravite` vaut `léger` ou `grave`.

### `GET /api/effects/Nausee`

Fiche avec molécules (`peutProvoquer`) et médicaments (`contientMolecule`). `note` explique l’absence de lien quand c’est le cas.

### `GET /api/contraindications?categorie=renale`

`categorie` : `allergique`, `digestive`, `renale`, `hepatique`, `absolue`, `relative`. Filtres additionnels : `niveau`, `medicament`, `molecule`, `pathologie`.

### `POST /api/nlp/ask`

```json
{"question": "Quels sont les effets secondaires graves ?"}
```

```json
{
  "question": "Quels sont les effets secondaires graves ?",
  "intent": "list_severe_effects",
  "entities": [],
  "sparql": "PREFIX : <http://example.org/pharma#> ...",
  "results": [],
  "count": 4,
  "message": "Effets dont niveauGravite vaut « grave »."
}
```

Une question incomprise renvoie `intent: "unknown"`, `sparql: null` et un message de reformulation. Ce n’est pas une erreur HTTP.

### `POST /api/sparql/query`

Lecture seule. `SELECT`, `ASK`, `CONSTRUCT` et `DESCRIBE` sont acceptés. `INSERT`, `DELETE`, `UPDATE`, `LOAD`, `CLEAR`, `DROP`, `SERVICE` sont rejetés, y compris lorsque le mot n’est pas dans un littéral. Un littéral qui contient le mot `DELETE` reste autorisé.

```json
{"query": "PREFIX : <http://example.org/pharma#> ASK { :Doliprane :contientMolecule :Paracetamol }"}
```

### Écriture

`POST`, `PUT` et `DELETE` sur `/api/effects` et `/api/contraindications`. En-tête obligatoire : `X-Write-Token`.

Corps de création d’un effet :

```json
{
  "id": "Cephalee",
  "label": "Céphalée",
  "type": "EffetGraveNeurologique",
  "gravite": "grave",
  "frequence": "rare",
  "molecules": ["Tramadol"]
}
```

La classe doit appartenir à la liste blanche. `niveauGravite` doit être cohérent avec la classe (`léger` pour `EffetLeger*`, `grave` pour `EffetGrave*`). Les molécules et pathologies doivent déjà exister. Le lien est écrit sur la molécule (`peutProvoquer` ou `aContreIndication`), conformément au domaine OWL. Un individu cité par `owl:hasValue` (comme `CI_AllergiePenicilline`) ne peut pas être supprimé.

`GET /api/ontology/resources` fournit les classes, molécules, médicaments et pathologies pour les formulaires.
