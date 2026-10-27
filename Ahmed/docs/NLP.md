# Module NLP — traducteur « question en français → SPARQL »

**Aucune API de LLM** (ni OpenAI, ni Gemini, ni Anthropic). Tout tourne en local avec des
bibliothèques NLP, et la requête SPARQL est construite par des gabarits, jamais générée par un modèle.

## Outils utilisés (à citer dans la présentation)

| Bibliothèque | Version | Rôle |
|---|---|---|
| **spaCy** + modèle `fr_core_news_md` | 3.8.18 / 3.8.0 | Tokenisation, lemmatisation, étiquetage morpho-syntaxique (POS), analyse en dépendances ; `PhraseMatcher` (reconnaissance des entités de l'ontologie) ; `Matcher` (règles d'intention) |
| **RapidFuzz** | 3.14.6 | Tolérance aux fautes de frappe (« diabte » → diabète) ; suggestions de questions proches |
| **scikit-learn** | 1.9.1 | Classifieur d'intention : TF-IDF (mots 1-2 + caractères 2-5) → régression logistique |
| rdflib / Apache Jena Fuseki | 7.6.0 | Exécution de la requête SPARQL générée |

## Pipeline (`backend/app/nlp/`, une étape = un fichier)

| # | Étape | Fichier | Exemple : « Quels patients souffrent de diabte ? » |
|---|---|---|---|
| 1 | Normalisation (minuscules, accents, ponctuation) | `normalize.py` | `quels patients souffrent de diabte` |
| 2 | Analyse spaCy : tokens, lemmes, POS, dépendances | `pipeline.py` | `souffrent` → lemme `souffrir`, VERB, ROOT |
| 3 | Reconnaissance des entités de l'ontologie (vocabulaire lu **dans le triplestore** + synonymes) | `vocabulary.py`, `linker.py` | `diabte` → `:DiabeteType2` (similarité 0,91) |
| 4 | Contraintes : âge, sexe, négation, cible d'un comptage | `constraints.py` | — |
| 5 | Intention : règles spaCy puis classifieur scikit-learn sur la question **masquée** | `intent.py` | `quels patients souffrent de ent_pathologie` → `patients_par_pathologie` (0,9) |
| 6 | Génération SPARQL par gabarit + slots sûrs | `generator.py` | `?p :souffreDe ?m . FILTER(?m = :DiabeteType2)` |
| 7 | Exécution et explication (entités, intention, confiance, requête) | `pipeline.py` | 5 patients |
| 8 | Question non comprise ou ambiguë → réponse honnête + 3 suggestions | `pipeline.py` | — |

Points clés à défendre à l'oral :
- **Vocabulaire dynamique** : il est reconstruit dès que les données changent. Un patient créé dans l'interface est reconnu à la question suivante.
- **Masquage des entités** : le classifieur apprend la *forme* de la question (« de quoi souffre ent_patient »), pas les noms. Il marche donc pour des patients qu'il n'a jamais vus.
- **Sécurité** : les IRI insérés viennent du vocabulaire de l'ontologie (validés par regex) et les nombres sont convertis en entiers. Le texte libre n'entre jamais dans la requête (test d'injection dans `tests/test_nlp.py`).

## Intentions (14)

`patients_par_pathologie`, `pathologies_patient`, `patients_filtre` (âge, sexe, enfant/adulte, sans pathologie),
`compter`, `pathologies_par_type` (sous-types compris), `code_cim10`, `medicaments_indiques`,
`medicaments_contre_indiques` (chaîne molécule → contre-indication → pathologie), `medecins_par_specialite`,
`patients_medecin`, `intervenants_prescription`, `alertes`, `ask_patient_classe` (ASK oui/non), `hors_perimetre`.

## Données et reproductibilité

- `backend/nlp/data/intents.jsonl` : 232 exemples d'entraînement (≥ 15 par intention).
- `backend/nlp/data/synonymes.json` : « sucre » → diabète, « mal de tête » → migraine, « gamin » → enfant, « généraliste » → Médecine générale…
- `backend/nlp/data/test_questions.jsonl` : 78 questions de test, **distinctes** des exemples d'entraînement (variantes, fautes de frappe, synonymes, 5 hors périmètre).
- `backend/scripts/setup_models.py` : installe le modèle spaCy (version épinglée) et entraîne le classifieur (< 1 Mo, `random_state` fixé). Le classifieur est aussi réentraîné automatiquement s'il manque.

## Évaluation

```
python scripts/eval_nlp.py
```
Une question n'est comptée juste que si l'intention, les entités **et** le résultat SPARQL sont corrects.
Résultat actuel : **100 % sur 78 questions** (cible : ≥ 90 %). Limite à reconnaître : ce jeu de test a été écrit
par nous. Sur des formulations très différentes, le système se trompe parfois. Dans ce cas, il répond qu'il n'a pas compris et propose des suggestions, plutôt qu'un résultat inventé.
