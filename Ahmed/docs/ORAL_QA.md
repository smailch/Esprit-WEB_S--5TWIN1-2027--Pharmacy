# Questions probables du jury — réponses courtes

### Web sémantique : bases

**1. Qu'est-ce qu'une URI et comment nommez-vous vos ressources ?**
Un identifiant global d'une ressource. Base `http://example.org/pharma#`, noms sans accents (`:Patient_Sara`, `:InsuffisanceRenale`). Le texte accentué est dans `rdfs:label`. À la création, l'URI est générée (`Patient_<Prénom>`, `Dr_<Nom>`, nom de pathologie en PascalCase) et une collision renvoie 409.

**2. Qu'est-ce que RDF ?**
Un modèle de données en triplets sujet–prédicat–objet. Ex. `:Patient_Sara :souffreDe :Angine`. Les littéraux sont typés : `:age 9` est un `xsd:integer`.

**3. Que vous apporte RDFS ?**
La hiérarchie (`rdfs:subClassOf` : `InfectionAigue ⊑ MaladieAigue ⊑ Pathologie`), les `rdfs:domain`/`rdfs:range` (domaine de `souffreDe` = Patient, range = Pathologie) et les libellés. En SPARQL, `rdf:type/rdfs:subClassOf*` retrouve les sous-types : « maladies chroniques » renvoie 10 pathologies, dont des maladies métaboliques.

**4. Attention au `domain` : quel piège avez-vous évité ?**
`age` et `sexe` ont pour domaine `Patient`. Donner un âge à un médecin ferait déduire qu'il est Patient, or `Patient` et `ProfessionnelSante` sont disjoints : l'ontologie deviendrait incohérente. Les professionnels n'ont donc ni âge ni sexe.

**5. Quels axiomes OWL utilisez-vous dans vos modules ?**
Classes définies (`PatientEnfant ≡ Patient ⊓ ∃age.[< 18]`), disjonctions (`MaladieAigue`/`MaladieChronique`, `Patient`/`ProfessionnelSante`, `Medecin`/`Pharmacien`), `age` fonctionnelle, inverses (`prescritPar`/`aPrescrit`), `owl:AllDifferent` sur mes individus, et la chaîne de propriétés `estContreIndiquePour`.

**6. Pourquoi `PatientEnfant` n'est-il jamais écrit à la main ?**
Parce que c'est une classe **définie** par l'âge : l'écrire serait redondant et risquerait de devenir faux quand l'âge change. On stocke `:Patient` + `:age` ; HermiT infère la classe, et l'appli fait la même déduction en SPARQL (`FILTER(?age < 18)`), ce qui marche même sans raisonneur. Démo : passer Yassine de 12 à 19 ans fait changer le badge.

**7. Qu'est-ce qu'une chaîne de propriétés ?**
`contientMolecule ∘ aContreIndication ∘ concernePathologie ⇒ estContreIndiquePour` : si un médicament contient une molécule contre-indiquée pour une pathologie, le raisonneur déduit que le médicament est contre-indiqué pour cette pathologie. En SPARQL, j'écris le même chemin avec un property path.

**8. HermiT ou SPARQL pour détecter une contre-indication chez un patient ?**
SPARQL. La chaîne OWL donne médicament → pathologie, mais rien en OWL ne relie « ce patient a cette pathologie ET a reçu ce médicament » à une alerte (il faudrait une règle SWRL). Ma requête `alertes.rq` fait la jointure patient → prescription → médicament → molécule → contre-indication → pathologie du patient, plus les allergies. HermiT sert à la cohérence et aux classes inférées.

**9. Pourquoi `xsd:date` pose-t-il problème à HermiT ?**
`xsd:date` ne fait pas partie de la table des datatypes OWL 2 : HermiT lève `UnsupportedDatatypeException`. Je ne modifie pas l'ontologie de l'équipe : `validate_ontology.py` remplace `xsd:date` par `xsd:dateTime` **en mémoire** avant d'appeler HermiT, ce qui donne 0 incohérence. Le problème a été signalé à l'équipe (correctif proposé : `xsd:dateTime`).

**10. Hypothèse du monde ouvert : quel impact ?**
OWL ne conclut pas qu'une chose est fausse parce qu'elle n'est pas écrite, et ne suppose pas que deux noms différents désignent deux individus différents : d'où l'`owl:AllDifferent`. Les contrôles « métier » comme « refuser la suppression si référencé » sont donc faits côté API, par un `ASK`.

### SPARQL

**11. Montrez un CRUD complet.**
Create `INSERT DATA`, Read `SELECT` paginé (`ORDER BY`/`LIMIT`/`OFFSET`) et `CONSTRUCT` pour la fiche RDF, Update `DELETE { } INSERT { } WHERE { }`, Delete `DELETE WHERE` après un `ASK` de contrôle. 36 requêtes nommées documentées avec leur résultat réel dans `docs/SPARQL.md`.

**12. Comment empêchez-vous l'injection SPARQL ?**
Aucune concaténation de texte utilisateur : paramètres typés. Les IRI sont validés par regex (`^[A-Za-z][A-Za-z0-9_]*$`), les littéraux échappés (`"` et `\`), les entiers convertis. Un test tente `" } ; DELETE WHERE { ?s ?p ?o }` : c'est stocké comme texte et le graphe reste intact. La console est en lecture seule (endpoint `/query`, les mises à jour sont refusées).

**13. Comment faites-vous une recherche insensible aux accents ?**
La saisie est normalisée côté serveur (minuscules, sans accents), et dans la requête `REPLACE(LCASE(?txt), "[éèêë]", "e")…` puis `CONTAINS` : « hedi » trouve « Hédi ».

**14. Un exemple d'agrégat ?**
Patients par pathologie (`COUNT` + `GROUP BY` + `HAVING`), médecins par spécialité, patients par tranche d'âge (`BIND(IF(...))`).

**15. Fuseki ou rdflib ?**
Le même code tourne sur les deux, derrière l'interface `SparqlClient`. Fuseki (Docker ou Java) est le vrai triplestore ; rdflib en mémoire sert aux tests et à une démo sans service. Changement par `SPARQL_BACKEND` dans `.env`.

### NLP / IA

**16. Pourquoi pas un LLM ?**
C'est interdit par le sujet (API clé en main), et ce n'est pas souhaitable ici : un LLM peut inventer une requête ou un résultat. Mon système est déterministe, explicable étape par étape, il fonctionne hors ligne, et il dit « je ne sais pas » au lieu d'inventer.

**17. Comment marche votre NLP ?**
(1) normalisation ; (2) spaCy `fr_core_news_md` : tokens, lemmes, POS, dépendances ; (3) reconnaissance des entités avec `PhraseMatcher`, vocabulaire construit depuis le triplestore + synonymes, et RapidFuzz pour les fautes ; (4) contraintes (âge, sexe, négation) ; (5) intention : règles spaCy `Matcher`, puis classifieur scikit-learn TF-IDF + régression logistique sur la question masquée ; (6) gabarit SPARQL rempli avec les entités ; (7) exécution et explication.

**18. Pourquoi masquer les entités avant la classification ?**
Le classifieur apprend la forme de la question (« de quoi souffre ent_patient ») et non les noms : il marche pour un patient créé à l'instant, sans réentraînement.

**19. Comment l'avez-vous évalué ?**
`scripts/eval_nlp.py` sur 78 questions distinctes des exemples d'entraînement (fautes, synonymes, 5 hors sujet). Une question n'est juste que si l'intention, les entités **et** le résultat sont corrects : 100 % (cible 90 %). Limite assumée : c'est nous qui avons écrit ce jeu de test. Sur une formulation imprévue, le système répond qu'il n'a pas compris et propose des questions proches.

### Architecture

**20. Comment front et back communiquent-ils ?**
API REST FastAPI documentée (OpenAPI sur `/docs`), schémas Pydantic en entrée et en sortie, codes 201/204/404/409/422, erreurs uniformes `{code, message, details}`, pagination. Côté React : un seul module `api/client.js`, proxy Vite, annulation des requêtes (`AbortController`), bandeau si le backend est éteint. Tests d'intégration avec `TestClient`.

**Bonus — Pourquoi un dossier `Ahmed/` séparé ?**
La note est individuelle et cela évite les conflits Git. L'ontologie reste partagée : je charge `ontologie/pharma.ttl` sans le modifier et j'ajoute mes individus dans `ontology-extension/`. Les noms de l'ontologie sont centralisés dans un seul fichier (`ontology_mapping.py`).
