# Requêtes SPARQL — modules Pathologie et Personne (membre 3)

Fichier généré par `scripts/gen_sparql_doc.py` : chaque exemple de résultat est **réellement exécuté**
sur `pharma.ttl` + `ontology-extension/*.ttl` (graphe rdflib neuf).

Les requêtes de référence Q1–Q8 de l'équipe sont dans `ontologie/requetes.sparql` ; ici,
uniquement les requêtes nommées de mes modules (`backend/sparql/*.rq`), utilisées par l'API.

**Sécurité** : paramètres typés (`iri` validé par regex, `lit` échappé, `int` converti) ;
aucune concaténation brute de texte utilisateur (test d'injection dans `tests/test_sparql.py`).

**36 requêtes nommées.**

## Create

### `add_souffre_de`

**Objectif** : Rattacher une pathologie à un patient (lien souffreDe).

Paramètres : `s` (iri), `patho` (iri) — exemple `{'s': 'Patient_Lina', 'patho': 'InsuffisanceHepatique'}`

```sparql
INSERT DATA { <http://example.org/pharma#Patient_Lina> :souffreDe <http://example.org/pharma#InsuffisanceHepatique> . }
```

Résultat : mise à jour appliquée (vérifiée dans les tests).

### `create_pathologie`

**Objectif** : Créer une pathologie aiguë ou chronique (sous-type) avec son code CIM-10.

Paramètres : `s` (iri), `classe` (iri), `label` (litfr), `code` (lit) — exemple `{'s': 'Grippe', 'classe': 'InfectionAigue', 'label': 'Grippe', 'code': 'J11'}`

```sparql
INSERT DATA {
  <http://example.org/pharma#Grippe> a owl:NamedIndividual , <http://example.org/pharma#InfectionAigue> ; rdfs:label "Grippe"@fr ; :codeCIM10 "J11" .
}
```

Résultat : mise à jour appliquée (vérifiée dans les tests).

### `create_patient`

**Objectif** : Créer un patient. Seule la classe :Patient est assertée ; Enfant/Adulte est dérivé de l'âge.

Paramètres : `s` (iri), `label` (litfr), `nom` (lit), `age` (int), `sexe` (lit) — exemple `{'s': 'Patient_Test', 'label': 'Test Demo', 'nom': 'Demo', 'age': 30, 'sexe': 'F'}`

```sparql
INSERT DATA {
  <http://example.org/pharma#Patient_Test> a owl:NamedIndividual , :Patient ;
      rdfs:label "Test Demo"@fr ; :nom "Demo" ; :age 30 ; :sexe "F" .
}
```

Résultat : mise à jour appliquée (vérifiée dans les tests).

### `create_professionnel`

**Objectif** : Créer un médecin ou un pharmacien (classe en paramètre, jamais d'âge ni de sexe : domaine Patient).

Paramètres : `s` (iri), `classe` (iri), `label` (litfr), `nom` (lit), `specialite` (lit) — exemple `{'s': 'Dr_Test', 'classe': 'Medecin', 'label': 'Dr Test', 'nom': 'Test', 'specialite': 'Dermatologie'}`

```sparql
INSERT DATA {
  <http://example.org/pharma#Dr_Test> a owl:NamedIndividual , <http://example.org/pharma#Medecin> ;
      rdfs:label "Dr Test"@fr ; :nom "Test" ; :specialite "Dermatologie" .
}
```

Résultat : mise à jour appliquée (vérifiée dans les tests).

## Read

### `describe_patient`

**Objectif** : Fiche patient en RDF (CONSTRUCT) : le patient, ses pathologies et ses prescriptions — export Turtle.

Paramètres : `s` (iri) — exemple `{'s': 'Patient_Sara'}`

```sparql
CONSTRUCT {
  <http://example.org/pharma#Patient_Sara> ?p ?o .
  ?patho rdfs:label ?pl ; :codeCIM10 ?code .
  ?presc :concernePatient <http://example.org/pharma#Patient_Sara> ; rdfs:label ?prl ; :prescritMedicament ?med .
} WHERE {
  { <http://example.org/pharma#Patient_Sara> ?p ?o }
  UNION { <http://example.org/pharma#Patient_Sara> :souffreDe ?patho . ?patho rdfs:label ?pl . OPTIONAL { ?patho :codeCIM10 ?code } }
  UNION { ?presc :concernePatient <http://example.org/pharma#Patient_Sara> ; rdfs:label ?prl ; :prescritMedicament ?med }
}
```

Résultat (Turtle, extrait) :

```turtle
@prefix : <http://example.org/pharma#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

:Presc_002 rdfs:label "Ordonnance 002 (conflit : allergie)"@fr ;
    :concernePatient :Patient_Sara ;
    :prescritMedicament :Clamoxyl .

:Angine rdfs:label "Angine bactérienne"@fr ;
    :codeCIM10 "J03.9" .

:Patient_Sara a :PatientEnfant,
        owl:NamedIndividual ;
```

### `entity_graph`

**Objectif** : Voisinage d'une entité (relations sortantes et entrantes) pour la vue graphe.

Paramètres : `s` (iri) — exemple `{'s': 'Patient_Ali'}`

```sparql
SELECT DISTINCT ?dir ?prop ?id ?label WHERE {
  { <http://example.org/pharma#Patient_Ali> ?p ?o . BIND("out" AS ?dir) } UNION { ?o ?p <http://example.org/pharma#Patient_Ali> . BIND("in" AS ?dir) }
  FILTER(isIRI(?o) && STRSTARTS(STR(?o), "http://example.org/pharma#"))
  OPTIONAL { ?o rdfs:label ?label }
  BIND(IF(?p = rdf:type, "type", STRAFTER(STR(?p), "#")) AS ?prop)
  BIND(STRAFTER(STR(?o), "#") AS ?id)
}
```

Résultat :

| dir | prop | id | label |
|---|---|---|---|
| out | type | PatientAdulte | Patient adulte (≥ 18 ans) |
| out | souffreDe | DiabeteType2 | Diabète de type 2 |
| out | souffreDe | InsuffisanceRenale | Insuffisance rénale chronique |
| in | concernePatient | Presc_001 | Ordonnance 001 (alerte : rénale) |
| in | estDonneeDe | Glycemie_Ali | Glycémie à jeun |

… 6 lignes au total

### `list_pathologies`

**Objectif** : Liste paginée des pathologies : type asserté, famille (aiguë/chronique), CIM-10, nombre de patients.

Paramètres : `filters` (raw), `limit` (int), `offset` (int) — exemple `{'filters': '', 'limit': 5, 'offset': 0}`

```sparql
SELECT ?id ?label ?code ?type ?famille (COUNT(DISTINCT ?pat) AS ?nbPatients) WHERE {
  ?p a ?t . ?t rdfs:subClassOf* :Pathologie .
  ?p rdfs:label ?label .
  OPTIONAL { ?p :codeCIM10 ?code }
  OPTIONAL { ?t rdfs:subClassOf* ?f . FILTER(?f IN (:MaladieAigue, :MaladieChronique)) }
  OPTIONAL { ?pat :souffreDe ?p }
  BIND(STRAFTER(STR(?p), "#") AS ?id)
  BIND(STRAFTER(STR(?t), "#") AS ?type)
  BIND(STRAFTER(STR(?f), "#") AS ?famille)
  
}
GROUP BY ?id ?label ?code ?type ?famille
ORDER BY ?label
LIMIT 5 OFFSET 0
```

Résultat :

| id | label | code | type | famille | nbPatients |
|---|---|---|---|---|---|
| Angine | Angine bactérienne | J03.9 | InfectionAigue | MaladieAigue | 1 |
| Bronchite | Bronchite aiguë | J20.9 | InfectionAigue | MaladieAigue | 1 |
| ColiqueNephretique | Colique néphrétique | N23 | DouleurAigue | MaladieAigue | 0 |
| Cystite | Cystite aiguë | N30.0 | InfectionAigue | MaladieAigue | 1 |
| DiabeteType2 | Diabète de type 2 | E11 | MaladieMetabolique | MaladieChronique | 2 |

### `list_patients`

**Objectif** : Liste paginée des patients, classe dérivée de l'âge (Enfant/Adulte) et indicateur « asserté ».

Paramètres : `filters` (raw), `limit` (int), `offset` (int) — exemple `{'filters': '', 'limit': 5, 'offset': 0}`

```sparql
SELECT ?id ?label ?nom ?age ?sexe ?classe ?asserte (COUNT(DISTINCT ?patho) AS ?nbPathologies) WHERE {
  ?p a/rdfs:subClassOf* :Patient ; rdfs:label ?label ; :age ?age .
  OPTIONAL { ?p :nom ?nom }
  OPTIONAL { ?p :sexe ?sexe }
  OPTIONAL { ?p :souffreDe ?patho }
  BIND(IF(?age < 18, "PatientEnfant", "PatientAdulte") AS ?classe)
  BIND(EXISTS { ?p a ?c . FILTER(?c IN (:PatientEnfant, :PatientAdulte)) } AS ?asserte)
  BIND(STRAFTER(STR(?p), "#") AS ?id)
  
}
GROUP BY ?id ?label ?nom ?age ?sexe ?classe ?asserte
ORDER BY ?label
LIMIT 5 OFFSET 0
```

Résultat :

| id | label | nom | age | sexe | classe | asserte | nbPathologies |
|---|---|---|---|---|---|---|---|
| Patient_Ali | Ali Ben Salah | Ben Salah | 58 | M | PatientAdulte | True | 2 |
| Patient_Amine | Amine Bouazizi | Bouazizi | 6 | M | PatientEnfant | False | 1 |
| Patient_Fatma | Fatma Chaabane | Chaabane | 72 | F | PatientAdulte | True | 3 |
| Patient_Hedi | Hédi Mejri | Mejri | 81 | M | PatientAdulte | True | 3 |
| Patient_Karim | Karim Jaziri | Jaziri | 45 | M | PatientAdulte | True | 2 |

### `list_professionnels`

**Objectif** : Liste paginée des médecins ou pharmaciens avec le nombre d'ordonnances liées.

Paramètres : `classe` (iri), `filters` (raw), `limit` (int), `offset` (int) — exemple `{'classe': 'Medecin', 'filters': '', 'limit': 10, 'offset': 0}`

```sparql
SELECT ?id ?label ?nom ?specialite (COUNT(DISTINCT ?presc) AS ?nbPrescriptions) WHERE {
  ?s a <http://example.org/pharma#Medecin> ; rdfs:label ?label .
  OPTIONAL { ?s :nom ?nom }
  OPTIONAL { ?s :specialite ?specialite }
  OPTIONAL { ?presc :prescritPar|:estDelivreePar ?s }
  BIND(STRAFTER(STR(?s), "#") AS ?id)
  
}
GROUP BY ?id ?label ?nom ?specialite
ORDER BY ?label
LIMIT 10 OFFSET 0
```

Résultat :

| id | label | nom | specialite | nbPrescriptions |
|---|---|---|---|---|
| Dr_Benali | Dr Benali | Benali | Médecine générale | 3 |
| Dr_Gharsallah | Dr Gharsallah | Gharsallah | Cardiologie | 0 |
| Dr_Hammami | Dr Hammami | Hammami | Pédiatrie | 0 |
| Dr_Trabelsi | Dr Trabelsi | Trabelsi | Pneumologie | 1 |
| Dr_Zouari | Dr Zouari | Zouari | Endocrinologie | 0 |

### `pathologie_detail`

**Objectif** : Détail d'une pathologie (type, famille, CIM-10).

Paramètres : `s` (iri) — exemple `{'s': 'InsuffisanceRenale'}`

```sparql
SELECT ?label ?code ?type ?famille WHERE {
  <http://example.org/pharma#InsuffisanceRenale> a ?t ; rdfs:label ?label . ?t rdfs:subClassOf* :Pathologie .
  OPTIONAL { <http://example.org/pharma#InsuffisanceRenale> :codeCIM10 ?code }
  OPTIONAL { ?t rdfs:subClassOf* ?f . FILTER(?f IN (:MaladieAigue, :MaladieChronique)) }
  BIND(STRAFTER(STR(?t), "#") AS ?type)
  BIND(STRAFTER(STR(?f), "#") AS ?famille)
} LIMIT 1
```

Résultat :

| label | code | type | famille |
|---|---|---|---|
| Insuffisance rénale chronique | N18 | InsuffisanceOrgane | MaladieChronique |

### `patient_detail`

**Objectif** : Détail d'un patient (données + classe dérivée de l'âge).

Paramètres : `s` (iri) — exemple `{'s': 'Patient_Lina'}`

```sparql
SELECT ?label ?nom ?age ?sexe ?classe ?asserte WHERE {
  <http://example.org/pharma#Patient_Lina> a/rdfs:subClassOf* :Patient ; rdfs:label ?label ; :age ?age .
  OPTIONAL { <http://example.org/pharma#Patient_Lina> :nom ?nom }
  OPTIONAL { <http://example.org/pharma#Patient_Lina> :sexe ?sexe }
  BIND(IF(?age < 18, "PatientEnfant", "PatientAdulte") AS ?classe)
  BIND(EXISTS { <http://example.org/pharma#Patient_Lina> a ?c . FILTER(?c IN (:PatientEnfant, :PatientAdulte)) } AS ?asserte)
} LIMIT 1
```

Résultat :

| label | nom | age | sexe | classe | asserte |
|---|---|---|---|---|---|
| Lina Gharbi | Gharbi | 31 | F | PatientAdulte | False |

### `patient_pathologies`

**Objectif** : Pathologies d'un patient avec leur type et leur famille (aiguë/chronique).

Paramètres : `s` (iri) — exemple `{'s': 'Patient_Ali'}`

```sparql
SELECT DISTINCT ?id ?label ?code ?type ?famille WHERE {
  <http://example.org/pharma#Patient_Ali> :souffreDe ?p .
  ?p rdfs:label ?label ; a ?t . ?t rdfs:subClassOf* :Pathologie .
  OPTIONAL { ?p :codeCIM10 ?code }
  OPTIONAL { ?t rdfs:subClassOf* ?f . FILTER(?f IN (:MaladieAigue, :MaladieChronique)) }
  BIND(STRAFTER(STR(?p), "#") AS ?id)
  BIND(STRAFTER(STR(?t), "#") AS ?type)
  BIND(STRAFTER(STR(?f), "#") AS ?famille)
} ORDER BY ?label
```

Résultat :

| id | label | code | type | famille |
|---|---|---|---|---|
| DiabeteType2 | Diabète de type 2 | E11 | MaladieMetabolique | MaladieChronique |
| InsuffisanceRenale | Insuffisance rénale chronique | N18 | InsuffisanceOrgane | MaladieChronique |

### `patient_prescriptions`

**Objectif** : Prescriptions d'un patient (lecture seule, module d'un autre membre) avec médecin et pharmacien.

Paramètres : `s` (iri) — exemple `{'s': 'Patient_Youssef'}`

```sparql
SELECT ?id ?label ?date ?posologie ?medecin ?medecinId ?pharmacien ?pharmacienId
       (GROUP_CONCAT(DISTINCT ?medLabel; separator=", ") AS ?medicaments) WHERE {
  ?presc :concernePatient <http://example.org/pharma#Patient_Youssef> ; rdfs:label ?label .
  OPTIONAL { ?presc :datePrescription ?d }
  OPTIONAL { ?presc :posologie ?posologie }
  OPTIONAL { ?presc :prescritMedicament/rdfs:label ?medLabel }
  OPTIONAL { ?presc :prescritPar ?m . ?m rdfs:label ?medecin }
  OPTIONAL { ?presc :estDelivreePar ?ph . ?ph rdfs:label ?pharmacien }
  BIND(STR(?d) AS ?date)
  BIND(STRAFTER(STR(?presc), "#") AS ?id)
  BIND(STRAFTER(STR(?m), "#") AS ?medecinId)
  BIND(STRAFTER(STR(?ph), "#") AS ?pharmacienId)
} GROUP BY ?id ?label ?date ?posologie ?medecin ?medecinId ?pharmacien ?pharmacienId ORDER BY ?id
```

Résultat :

| id | label | date | posologie | medecin | medecinId | pharmacien | pharmacienId | medicaments |
|---|---|---|---|---|---|---|---|---|
| Presc_003 | Ordonnance 003 (conflit : ulcère) | 2026-10-15 | 1 comprimé si douleur | Dr Benali | Dr_Benali | Pharmacien Mansour | Ph_Mansour | Advil 400 mg, Doliprane 1000 mg |

### `professionnel_detail`

**Objectif** : Détail d'un professionnel de santé et de ses ordonnances (prescrites ou délivrées).

Paramètres : `s` (iri) — exemple `{'s': 'Dr_Benali'}`

```sparql
SELECT ?label ?nom ?specialite ?classe ?prescId ?prescLabel ?patient ?patientId ?role WHERE {
  <http://example.org/pharma#Dr_Benali> a ?c ; rdfs:label ?label . ?c rdfs:subClassOf :ProfessionnelSante .
  OPTIONAL { <http://example.org/pharma#Dr_Benali> :nom ?nom }
  OPTIONAL { <http://example.org/pharma#Dr_Benali> :specialite ?specialite }
  OPTIONAL {
    { ?presc :prescritPar <http://example.org/pharma#Dr_Benali> . BIND("prescrit" AS ?role) }
    UNION { ?presc :estDelivreePar <http://example.org/pharma#Dr_Benali> . BIND("délivre" AS ?role) }
    ?presc rdfs:label ?prescLabel ; :concernePatient ?pat . ?pat rdfs:label ?patient .
  }
  BIND(STRAFTER(STR(?c), "#") AS ?classe)
  BIND(STRAFTER(STR(?presc), "#") AS ?prescId)
  BIND(STRAFTER(STR(?pat), "#") AS ?patientId)
} ORDER BY ?prescId
```

Résultat :

| label | nom | specialite | classe | prescId | prescLabel | patient | patientId | role |
|---|---|---|---|---|---|---|---|---|
| Dr Benali | Benali | Médecine générale | Medecin | Presc_001 | Ordonnance 001 (alerte : rénale) | Ali Ben Salah | Patient_Ali | prescrit |
| Dr Benali | Benali | Médecine générale | Medecin | Presc_002 | Ordonnance 002 (conflit : allergie) | Sara Jlassi | Patient_Sara | prescrit |
| Dr Benali | Benali | Médecine générale | Medecin | Presc_003 | Ordonnance 003 (conflit : ulcère) | Youssef Hamdi | Patient_Youssef | prescrit |

## Update

### `remove_souffre_de`

**Objectif** : Retirer une pathologie d'un patient.

Paramètres : `s` (iri), `patho` (iri) — exemple `{'s': 'Patient_Lina', 'patho': 'InsuffisanceHepatique'}`

```sparql
DELETE DATA { <http://example.org/pharma#Patient_Lina> :souffreDe <http://example.org/pharma#InsuffisanceHepatique> . }
```

Résultat : mise à jour appliquée (vérifiée dans les tests).

### `update_label`

**Objectif** : Modifier le libellé affiché (rdfs:label) d'une entité.

Paramètres : `s` (iri), `label` (litfr) — exemple `{'s': 'Obesite', 'label': 'Obésité (IMC ≥ 30)'}`

```sparql
DELETE { <http://example.org/pharma#Obesite> rdfs:label ?old }
INSERT { <http://example.org/pharma#Obesite> rdfs:label "Obésité (IMC ≥ 30)"@fr }
WHERE  { OPTIONAL { <http://example.org/pharma#Obesite> rdfs:label ?old } }
```

Résultat : mise à jour appliquée (vérifiée dans les tests).

### `update_value`

**Objectif** : Remplacer la valeur d'une propriété de données (age, sexe, specialite, nom, codeCIM10).

Paramètres : `s` (iri), `p` (iri), `value` (raw) — exemple `{'s': 'Patient_Lina', 'p': 'age', 'value': '32'}`

```sparql
DELETE { <http://example.org/pharma#Patient_Lina> <http://example.org/pharma#age> ?old }
INSERT { <http://example.org/pharma#Patient_Lina> <http://example.org/pharma#age> 32 }
WHERE  { OPTIONAL { <http://example.org/pharma#Patient_Lina> <http://example.org/pharma#age> ?old } }
```

Résultat : mise à jour appliquée (vérifiée dans les tests).

## Delete

### `delete_entity`

**Objectif** : Supprimer une entité (après contrôle ASK des références).

Paramètres : `s` (iri) — exemple `{'s': 'Patient_Test'}`

```sparql
DELETE WHERE { <http://example.org/pharma#Patient_Test> ?p ?o }
```

Résultat : mise à jour appliquée (vérifiée dans les tests).

## ASK

### `ask_exists`

**Objectif** : L'IRI existe-t-il déjà ? (404, ou collision 409 à la création)

Paramètres : `s` (iri) — exemple `{'s': 'Patient_Ali'}`

```sparql
ASK { <http://example.org/pharma#Patient_Ali> ?p ?o }
```

Résultat : `true`

### `ask_pathologie_references`

**Objectif** : La pathologie est-elle référencée (patient, contre-indication, médicament, antécédent) ? Si oui, 409.

Paramètres : `s` (iri) — exemple `{'s': 'DiabeteType2'}`

```sparql
ASK {
  { ?x :souffreDe <http://example.org/pharma#DiabeteType2> } UNION { ?x :concernePathologie <http://example.org/pharma#DiabeteType2> }
  UNION { ?x :estIndiquePour <http://example.org/pharma#DiabeteType2> } UNION { ?x :porteSur <http://example.org/pharma#DiabeteType2> }
}
```

Résultat : `true`

### `ask_patient_enfant`

**Objectif** : Question oui/non : ce patient est-il un enfant (âge < 18, classe définie PatientEnfant) ?

Paramètres : `s` (iri) — exemple `{'s': 'Patient_Sara'}`

```sparql
ASK { <http://example.org/pharma#Patient_Sara> a/rdfs:subClassOf* :Patient ; :age ?age . FILTER(?age < 18) }
```

Résultat : `true`

### `ask_patient_references`

**Objectif** : Le patient est-il référencé (prescription ou donnée clinique) ? Si oui, suppression refusée (409).

Paramètres : `s` (iri) — exemple `{'s': 'Patient_Ali'}`

```sparql
ASK { { ?x :concernePatient <http://example.org/pharma#Patient_Ali> } UNION { ?x :estDonneeDe <http://example.org/pharma#Patient_Ali> } }
```

Résultat : `true`

### `ask_professionnel_references`

**Objectif** : Le professionnel a-t-il prescrit ou délivré une ordonnance ? Si oui, suppression refusée (409).

Paramètres : `s` (iri) — exemple `{'s': 'Dr_Benali'}`

```sparql
ASK { { ?x :prescritPar <http://example.org/pharma#Dr_Benali> } UNION { ?x :estDelivreePar <http://example.org/pharma#Dr_Benali> } }
```

Résultat : `true`

## Filtre

### `pathologie_patients`

**Objectif** : Patients atteints d'une pathologie donnée.

Paramètres : `s` (iri) — exemple `{'s': 'HypertensionArterielle'}`

```sparql
SELECT ?id ?label ?age WHERE {
  ?p :souffreDe <http://example.org/pharma#HypertensionArterielle> ; rdfs:label ?label . OPTIONAL { ?p :age ?age }
  BIND(STRAFTER(STR(?p), "#") AS ?id)
} ORDER BY ?label
```

Résultat :

| id | label | age |
|---|---|---|
| Patient_Fatma | Fatma Chaabane | 72 |
| Patient_Hedi | Hédi Mejri | 81 |

## Recherche

### `search`

**Objectif** : Recherche texte insensible à la casse et aux accents (label, nom, CIM-10, spécialité) dans Pathologie et Personne.

Paramètres : `q` (lit) — exemple `{'q': 'insuffisance'}`

```sparql
SELECT DISTINCT ?id ?label ?classe ?module WHERE {
  ?s a ?c . ?c rdfs:subClassOf* ?root . FILTER(?root IN (:Pathologie, :Personne))
  ?s rdfs:label ?label .
  OPTIONAL { ?s :nom ?nom }
  OPTIONAL { ?s :codeCIM10 ?code }
  OPTIONAL { ?s :specialite ?spec }
  BIND(CONCAT(STR(?label), " ", COALESCE(?nom, ""), " ", COALESCE(?code, ""), " ", COALESCE(?spec, "")) AS ?txt)
  BIND(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(LCASE(?txt),
       "[éèêë]", "e"), "[àâä]", "a"), "[îï]", "i"), "[ôö]", "o"), "[ùûü]", "u"), "ç", "c") AS ?norm)
  FILTER(CONTAINS(?norm, "insuffisance"))
  BIND(STRAFTER(STR(?s), "#") AS ?id)
  BIND(STRAFTER(STR(?c), "#") AS ?classe)
  BIND(STRAFTER(STR(?root), "#") AS ?module)
} ORDER BY ?module ?label LIMIT 50
```

Résultat :

| id | label | classe | module |
|---|---|---|---|
| InsuffisanceCardiaque | Insuffisance cardiaque | InsuffisanceOrgane | Pathologie |
| InsuffisanceHepatique | Insuffisance hépatique | InsuffisanceOrgane | Pathologie |
| InsuffisanceRespiratoire | Insuffisance respiratoire chronique | InsuffisanceOrgane | Pathologie |
| InsuffisanceRenale | Insuffisance rénale chronique | InsuffisanceOrgane | Pathologie |

## Hierarchie

### `patients_by_pathology_type`

**Objectif** : Hiérarchie — patients atteints d'une pathologie d'un type donné, sous-types compris (rdf:type/rdfs:subClassOf*).

Paramètres : `type` (iri) — exemple `{'type': 'MaladieChronique'}`

```sparql
SELECT DISTINCT ?id ?patient ?pathologie ?typePathologie WHERE {
  ?pat :souffreDe ?p ; rdfs:label ?patient .
  ?p a ?t ; rdfs:label ?pathologie . ?t rdfs:subClassOf* <http://example.org/pharma#MaladieChronique> ; rdfs:label ?typePathologie .
  BIND(STRAFTER(STR(?pat), "#") AS ?id)
} ORDER BY ?patient
```

Résultat :

| id | patient | pathologie | typePathologie |
|---|---|---|---|
| Patient_Ali | Ali Ben Salah | Diabète de type 2 | Maladie métabolique |
| Patient_Ali | Ali Ben Salah | Insuffisance rénale chronique | Insuffisance d'organe |
| Patient_Fatma | Fatma Chaabane | Hypertension artérielle | Maladie chronique |
| Patient_Fatma | Fatma Chaabane | Diabète de type 2 | Maladie métabolique |
| Patient_Fatma | Fatma Chaabane | Insuffisance cardiaque | Insuffisance d'organe |

… 11 lignes au total

## Agregat

### `count_pathologies`

**Objectif** : Nombre total de pathologies correspondant aux filtres (pagination).

Paramètres : `filters` (raw) — exemple `{'filters': 'FILTER EXISTS { ?p a/rdfs:subClassOf* :MaladieChronique }'}`

```sparql
SELECT (COUNT(DISTINCT ?p) AS ?total) WHERE {
  ?p a ?t . ?t rdfs:subClassOf* :Pathologie .
  ?p rdfs:label ?label .
  OPTIONAL { ?p :codeCIM10 ?code }
  FILTER EXISTS { ?p a/rdfs:subClassOf* :MaladieChronique }
}
```

Résultat :

| total |
|---|
| 10 |

### `count_patients`

**Objectif** : Nombre total de patients correspondant aux filtres (pagination).

Paramètres : `filters` (raw) — exemple `{'filters': 'FILTER(?age >= 60)'}`

```sparql
SELECT (COUNT(DISTINCT ?p) AS ?total) WHERE {
  ?p a/rdfs:subClassOf* :Patient ; rdfs:label ?label ; :age ?age .
  OPTIONAL { ?p :nom ?nom }
  OPTIONAL { ?p :sexe ?sexe }
  FILTER(?age >= 60)
}
```

Résultat :

| total |
|---|
| 3 |

### `count_professionnels`

**Objectif** : Nombre de médecins ou pharmaciens correspondant aux filtres (pagination).

Paramètres : `classe` (iri), `filters` (raw) — exemple `{'classe': 'Pharmacien', 'filters': ''}`

```sparql
SELECT (COUNT(DISTINCT ?s) AS ?total) WHERE {
  ?s a <http://example.org/pharma#Pharmacien> ; rdfs:label ?label .
  OPTIONAL { ?s :nom ?nom }
  OPTIONAL { ?s :specialite ?specialite }
  
}
```

Résultat :

| total |
|---|
| 3 |

### `stats_compteurs`

**Objectif** : Compteurs du tableau de bord (enfants/adultes dérivés de l'âge, aiguës/chroniques via la hiérarchie, médecins, pharmaciens).

```sparql
SELECT ?enfants ?adultes ?aigues ?chroniques ?medecins ?pharmaciens WHERE {
  { SELECT (COUNT(DISTINCT ?p) AS ?enfants) WHERE { ?p a/rdfs:subClassOf* :Patient ; :age ?a . FILTER(?a < 18) } }
  { SELECT (COUNT(DISTINCT ?p) AS ?adultes) WHERE { ?p a/rdfs:subClassOf* :Patient ; :age ?a . FILTER(?a >= 18) } }
  { SELECT (COUNT(DISTINCT ?x) AS ?aigues) WHERE { ?x a/rdfs:subClassOf* :MaladieAigue } }
  { SELECT (COUNT(DISTINCT ?x) AS ?chroniques) WHERE { ?x a/rdfs:subClassOf* :MaladieChronique } }
  { SELECT (COUNT(DISTINCT ?m) AS ?medecins) WHERE { ?m a :Medecin } }
  { SELECT (COUNT(DISTINCT ?m) AS ?pharmaciens) WHERE { ?m a :Pharmacien } }
}
```

Résultat :

| enfants | adultes | aigues | chroniques | medecins | pharmaciens |
|---|---|---|---|---|---|
| 3 | 8 | 9 | 10 | 5 | 3 |

### `stats_patients_par_pathologie`

**Objectif** : Nombre de patients par pathologie (GROUP BY + HAVING sur un minimum).

Paramètres : `min` (int) — exemple `{'min': 2}`

```sparql
SELECT ?id ?pathologie (COUNT(DISTINCT ?pat) AS ?nbPatients) WHERE {
  ?pat :souffreDe ?p . ?p rdfs:label ?pathologie .
  BIND(STRAFTER(STR(?p), "#") AS ?id)
} GROUP BY ?id ?pathologie HAVING (COUNT(DISTINCT ?pat) >= 2) ORDER BY DESC(?nbPatients) ?pathologie
```

Résultat :

| id | pathologie | nbPatients |
|---|---|---|
| DiabeteType2 | Diabète de type 2 | 2 |
| HypertensionArterielle | Hypertension artérielle | 2 |
| Migraine | Migraine | 2 |

### `stats_specialites`

**Objectif** : Professionnels de santé par classe et spécialité (GROUP BY).

```sparql
SELECT ?classe ?specialite (COUNT(?s) AS ?nb) WHERE {
  ?s a ?c ; :specialite ?specialite . ?c rdfs:subClassOf :ProfessionnelSante .
  BIND(STRAFTER(STR(?c), "#") AS ?classe)
} GROUP BY ?classe ?specialite ORDER BY ?classe DESC(?nb)
```

Résultat :

| classe | specialite | nb |
|---|---|---|
| Medecin | Médecine générale | 1 |
| Medecin | Pneumologie | 1 |
| Medecin | Pédiatrie | 1 |
| Medecin | Cardiologie | 1 |
| Medecin | Endocrinologie | 1 |

… 7 lignes au total

### `stats_tranches_age`

**Objectif** : Patients par tranche d'âge (BIND/IF + GROUP BY).

```sparql
SELECT ?tranche (COUNT(DISTINCT ?p) AS ?nb) WHERE {
  ?p a/rdfs:subClassOf* :Patient ; :age ?a .
  BIND(IF(?a < 18, "0-17", IF(?a < 40, "18-39", IF(?a < 65, "40-64", "65+"))) AS ?tranche)
} GROUP BY ?tranche ORDER BY ?tranche
```

Résultat :

| tranche | nb |
|---|---|
| 0-17 | 3 |
| 18-39 | 3 |
| 40-64 | 2 |
| 65+ | 3 |

## Chemin

### `pathologie_medicaments`

**Objectif** : Médicaments indiqués et contre-indiqués pour une pathologie (chaîne estContreIndiquePour écrite en property path).

Paramètres : `s` (iri) — exemple `{'s': 'InsuffisanceRenale'}`

```sparql
SELECT DISTINCT ?id ?label ?relation ?via WHERE {
  {
    ?med :estIndiquePour <http://example.org/pharma#InsuffisanceRenale> . BIND("indiqué" AS ?relation)
  } UNION {
    ?med :contientMolecule ?mol . ?mol :aContreIndication/:concernePathologie <http://example.org/pharma#InsuffisanceRenale> .
    ?mol rdfs:label ?via . BIND("contre-indiqué" AS ?relation)
  }
  ?med rdfs:label ?label .
  BIND(STRAFTER(STR(?med), "#") AS ?id)
} ORDER BY ?relation ?label
```

Résultat :

| id | label | relation | via |
|---|---|---|---|
| Advil | Advil 400 mg | contre-indiqué | Ibuprofène |
| Glucophage | Glucophage 850 mg | contre-indiqué | Metformine (antidiabétique) |
| IbuprofeneMylan | Ibuprofène Mylan 400 mg | contre-indiqué | Ibuprofène |

### `patient_risk_paths`

**Objectif** : Property path complet Patient → Prescription → Médicament → Molécule → ContreIndication → Pathologie ; « atteint » si le patient a la pathologie.

Paramètres : `filters` (raw) — exemple `{'filters': ''}`

```sparql
SELECT DISTINCT ?patient ?medicament ?molecule ?pathologie ?atteint WHERE {
  ?pat ^:concernePatient/:prescritMedicament ?med .
  ?med :contientMolecule ?mol .
  ?mol :aContreIndication/:concernePathologie ?p .
  BIND(EXISTS { ?pat :souffreDe ?p } AS ?atteint)
  ?pat rdfs:label ?patient . ?med rdfs:label ?medicament . ?mol rdfs:label ?molecule . ?p rdfs:label ?pathologie .
  
} ORDER BY DESC(?atteint) ?patient
```

Résultat :

| patient | medicament | molecule | pathologie | atteint |
|---|---|---|---|---|
| Ali Ben Salah | Glucophage 850 mg | Metformine (antidiabétique) | Insuffisance rénale chronique | True |
| Youssef Hamdi | Advil 400 mg | Ibuprofène | Ulcère gastro-duodénal | True |
| Lina Gharbi | Zithromax 250 mg | Azithromycine | Insuffisance hépatique | False |
| Youssef Hamdi | Doliprane 1000 mg | Paracétamol | Insuffisance hépatique | False |
| Youssef Hamdi | Advil 400 mg | Ibuprofène | Insuffisance rénale chronique | False |

## Alerte

### `alertes`

**Objectif** : Alertes sécurité (Q6 enrichie) : contre-indication liée à une pathologie du patient OU allergie connue, avec médecin et pharmacien.

Paramètres : `filters` (raw) — exemple `{'filters': ''}`

```sparql
SELECT DISTINCT ?prescId ?ordonnance ?patId ?patient ?medicament ?type ?raison ?medecin ?pharmacien WHERE {
  {
    ?presc :concernePatient ?pat ; :prescritMedicament ?med .
    ?med :contientMolecule/:aContreIndication ?ci .
    ?ci :concernePathologie ?patho .
    ?pat :souffreDe ?patho .
    ?patho rdfs:label ?pl .
    BIND("contre-indication" AS ?type)
    BIND(CONCAT("Contre-indiqué : ", STR(?pl)) AS ?raison)
  } UNION {
    ?al a :Allergie ; :estDonneeDe ?pat ; :allergiqueA ?mol .
    ?presc :concernePatient ?pat ; :prescritMedicament ?med .
    ?med :contientMolecule ?mol .
    ?mol rdfs:label ?ml .
    BIND("allergie" AS ?type)
    BIND(CONCAT("Allergie connue : ", STR(?ml)) AS ?raison)
  }
  ?presc rdfs:label ?ordonnance . ?pat rdfs:label ?patient . ?med rdfs:label ?medicament .
  OPTIONAL { ?presc :prescritPar/rdfs:label ?medecin }
  OPTIONAL { ?presc :estDelivreePar/rdfs:label ?pharmacien }
  BIND(STRAFTER(STR(?pat), "#") AS ?patId)
  BIND(STRAFTER(STR(?presc), "#") AS ?prescId)
  
} ORDER BY ?prescId
```

Résultat :

| prescId | ordonnance | patId | patient | medicament | type | raison | medecin | pharmacien |
|---|---|---|---|---|---|---|---|---|
| Presc_001 | Ordonnance 001 (alerte : rénale) | Patient_Ali | Ali Ben Salah | Glucophage 850 mg | contre-indication | Contre-indiqué : Insuffisance rénale chronique | Dr Benali | Pharmacien Mansour |
| Presc_002 | Ordonnance 002 (conflit : allergie) | Patient_Sara | Sara Jlassi | Clamoxyl 1 g | allergie | Allergie connue : Amoxicilline | Dr Benali |  |
| Presc_003 | Ordonnance 003 (conflit : ulcère) | Patient_Youssef | Youssef Hamdi | Advil 400 mg | contre-indication | Contre-indiqué : Ulcère gastro-duodénal | Dr Benali | Pharmacien Mansour |
