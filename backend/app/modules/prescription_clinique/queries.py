"""Catalogue des requêtes SPARQL nommées du module D (Prescription + Donnée clinique).

Classes et propriétés utilisées telles qu'elles existent dans ontologie/pharma.ttl (v2), sans ajout.
Les individus des autres modules (patients, médecins, médicaments, molécules, pathologies) sont seulement lus,
car les relations de Prescription et de DonneeClinique pointent vers eux.
"""
from .common import date_lit, lit, render

# Sous-classes de :Prescription (3 niveaux) — estRenouvelable est déduit du type choisi.
PRESCRIPTION_TYPES = {
    "PrescriptionSimple": False,
    "PrescriptionNormale": False,
    "PrescriptionUrgente": False,
    "PrescriptionRenouvelable": True,
    "RenouvellementCourt": True,
    "RenouvellementLong": True,
}
# Sous-classes de :DonneeClinique (3 niveaux) ; les feuilles sont les seules créables.
DONNEE_TYPES = ["DonneeClinique", "ExamenClinique", "HistoriqueMedical", "SigneVital", "AnalyseBiologique", "Allergie", "Antecedent"]
DONNEE_LEAVES = {"SigneVital": "ExamenClinique", "AnalyseBiologique": "ExamenClinique",
                 "Allergie": "HistoriqueMedical", "Antecedent": "HistoriqueMedical"}

CATALOGUE = {
    "D01_prescriptions_par_type": {
        "titre": "Prescriptions d'un type (hiérarchie à 3 niveaux)",
        "notion": "rdf:type/rdfs:subClassOf* + classe définie (estRenouvelable = true ⇒ PrescriptionRenouvelable)",
        "params": {"type": ":PrescriptionRenouvelable"},
        "sparql": """
SELECT DISTINCT ?prescription ?label ?typeDeclare ?date WHERE {
  GRAPH <urn:pharma:base> { ?prescription rdf:type ?typeDeclare . ?typeDeclare rdfs:subClassOf* {{type}} . }
  ?prescription rdfs:label ?label ; :datePrescription ?date .
} ORDER BY ?date""",
    },
    "D02_prescriptions_periode": {
        "titre": "Prescriptions émises sur une période",
        "notion": "FILTER sur des littéraux xsd:date (>= / <=), ORDER BY DESC",
        "params": {"debut": date_lit("2026-10-01"), "fin": date_lit("2026-10-31")},
        "sparql": """
SELECT ?prescription ?label ?date ?patient WHERE {
  ?prescription a :Prescription ; rdfs:label ?label ; :datePrescription ?date ; :concernePatient ?p .
  ?p rdfs:label ?patient .
  FILTER(?date >= {{debut}} && ?date <= {{fin}})
} ORDER BY DESC(?date)""",
    },
    "D03_ordonnance_complete": {
        "titre": "Ordonnance complète (patient, médecin, pharmacien, médicaments)",
        "notion": "Jointures + chemins de propriétés + OPTIONAL + GROUP_CONCAT",
        "params": {"prescription": ":Presc_003"},
        "sparql": """
SELECT ?patient ?medecin ?pharmacien ?date ?duree ?posologie (GROUP_CONCAT(?med; separator=", ") AS ?medicaments) WHERE {
  {{prescription}} :concernePatient/rdfs:label ?patient ; :prescritPar/rdfs:label ?medecin ;
                   :datePrescription ?date ; :prescritMedicament/rdfs:label ?med .
  OPTIONAL { {{prescription}} :dureeJours ?duree }
  OPTIONAL { {{prescription}} :posologie ?posologie }
  OPTIONAL { {{prescription}} :estDelivreePar/rdfs:label ?pharmacien }
} GROUP BY ?patient ?medecin ?pharmacien ?date ?duree ?posologie""",
    },
    "D04_prescriptions_medecin": {
        "titre": "Prescriptions d'un médecin",
        "notion": "Propriété inverse owl:inverseOf (aPrescrit, inférée depuis prescritPar)",
        "params": {"medecin": ":Dr_Benali"},
        "sparql": """
SELECT ?prescription ?label ?date WHERE {
  {{medecin}} :aPrescrit ?prescription .
  ?prescription rdfs:label ?label ; :datePrescription ?date .
} ORDER BY ?date""",
    },
    "D05_medicaments_patient": {
        "titre": "Médicaments prescrits à un patient",
        "notion": "Chemin de propriétés :aPrescription/:prescritMedicament (inverse inféré)",
        "params": {"patient": ":Patient_Youssef"},
        "sparql": """
SELECT DISTINCT ?medicament ?label ?prescription WHERE {
  {{patient}} :aPrescription ?prescription .
  ?prescription :prescritMedicament ?medicament .
  ?medicament rdfs:label ?label .
} ORDER BY ?label""",
    },
    "D06_alertes_prescriptions": {
        "titre": "Alertes : prescriptions dangereuses au vu du dossier clinique",
        "notion": "UNION de 4 raisonnements : pathologie, allergie, antécédent, analyse biologique (extension de Q6 de requetes.sparql)",
        # Restriction facultative appliquée APRÈS l'UNION : un VALUES placé avant fait exploser l'évaluateur de rdflib.
        "params": {"restriction": ""},
        "sparql": """
SELECT ?presc ?ordonnance ?pat ?patient ?med ?medicament ?mol ?molecule ?type ?source ?motif WHERE {
  {
    ?presc :concernePatient ?pat ; :prescritMedicament ?med .
    ?med :contientMolecule ?mol . ?mol :aContreIndication ?ci .
    ?ci :concernePathologie ?patho . ?pat :souffreDe ?patho .
    ?ci rdfs:label ?ciLabel . ?patho rdfs:label ?pathoLabel .
    BIND("contre-indication" AS ?type) BIND(?patho AS ?source)
    BIND(CONCAT(STR(?ciLabel), " (pathologie actuelle : ", STR(?pathoLabel), ")") AS ?motif)
  } UNION {
    ?d a :Allergie ; :estDonneeDe ?pat ; :allergiqueA ?mol .
    ?presc :concernePatient ?pat ; :prescritMedicament ?med .
    ?med :contientMolecule ?mol . ?d rdfs:label ?dLabel .
    BIND("allergie" AS ?type) BIND(?d AS ?source)
    BIND(CONCAT("Allergie connue : ", STR(?dLabel)) AS ?motif)
  } UNION {
    ?d a :Antecedent ; :estDonneeDe ?pat ; :porteSur ?patho .
    ?presc :concernePatient ?pat ; :prescritMedicament ?med .
    ?med :contientMolecule ?mol . ?mol :aContreIndication ?ci . ?ci :concernePathologie ?patho .
    ?d rdfs:label ?dLabel . ?ci rdfs:label ?ciLabel .
    BIND("antécédent" AS ?type) BIND(?d AS ?source)
    BIND(CONCAT(STR(?ciLabel), " (", STR(?dLabel), ")") AS ?motif)
  } UNION {
    ?d a :AnalyseBiologique ; :estDonneeDe ?pat ; rdfs:label "Clairance de la créatinine"@fr ; :valeur ?v ; :unite ?u .
    FILTER(?v < 60)
    ?presc :concernePatient ?pat ; :prescritMedicament ?med .
    ?med :contientMolecule ?mol . ?mol :aContreIndication :CI_InsuffisanceRenale .
    BIND("analyse" AS ?type) BIND(?d AS ?source)
    BIND(CONCAT("Clairance de la créatinine à ", STR(?v), " ", STR(?u), " (< 60) : molécule contre-indiquée en insuffisance rénale") AS ?motif)
  }
  ?presc rdfs:label ?ordonnance . ?pat rdfs:label ?patient . ?med rdfs:label ?medicament . ?mol rdfs:label ?molecule .
  {{restriction}}
} ORDER BY ?presc ?type""",
    },
    "D07_chaine_patient": {
        "titre": "Chaîne Patient → Prescription → Médicament → Molécule → Contre-indication",
        "notion": "Parcours de 5 relations + OPTIONAL + BIND(EXISTS) pour marquer le conflit",
        "params": {"patient": ":Patient_Youssef"},
        "sparql": """
SELECT ?prescription ?prescLabel ?medicament ?medLabel ?molecule ?molLabel ?ci ?ciLabel ?risque ?pathologie ?pathoLabel ?conflit WHERE {
  ?prescription :concernePatient {{patient}} ; rdfs:label ?prescLabel ; :prescritMedicament ?medicament .
  ?medicament rdfs:label ?medLabel ; :contientMolecule ?molecule .
  ?molecule rdfs:label ?molLabel .
  OPTIONAL {
    ?molecule :aContreIndication ?ci . ?ci rdfs:label ?ciLabel .
    OPTIONAL { ?ci :niveauRisque ?risque }
    OPTIONAL { ?ci :concernePathologie ?pathologie . ?pathologie rdfs:label ?pathoLabel }
  }
  BIND(BOUND(?pathologie) && EXISTS { { {{patient}} :souffreDe ?pathologie } UNION
                                       { ?a a :Antecedent ; :estDonneeDe {{patient}} ; :porteSur ?pathologie } } AS ?conflit)
} ORDER BY ?prescription ?medLabel ?ciLabel""",
    },
    "D08_stats_medecins": {
        "titre": "Activité des médecins",
        "notion": "Agrégats COUNT / AVG / MIN / MAX, GROUP BY, HAVING",
        "params": {"minimum": lit(1)},
        "sparql": """
SELECT ?medecin ?nom (COUNT(DISTINCT ?p) AS ?nbPrescriptions) (AVG(?duree) AS ?dureeMoyenne)
       (MIN(?date) AS ?premiere) (MAX(?date) AS ?derniere) WHERE {
  ?medecin a :Medecin ; rdfs:label ?nom .
  ?p :prescritPar ?medecin ; :datePrescription ?date ; :dureeJours ?duree .
} GROUP BY ?medecin ?nom HAVING(COUNT(DISTINCT ?p) >= {{minimum}}) ORDER BY DESC(?nbPrescriptions)""",
    },
    "D09_ordonnances_non_delivrees": {
        "titre": "Ordonnances pas encore délivrées en pharmacie",
        "notion": "Négation : FILTER NOT EXISTS",
        "params": {},
        "sparql": """
SELECT ?prescription ?label ?date WHERE {
  ?prescription a :Prescription ; rdfs:label ?label ; :datePrescription ?date .
  FILTER NOT EXISTS { ?prescription :estDelivreePar ?pharmacien }
} ORDER BY ?date""",
    },
    "D10_prescription_contient": {
        "titre": "Cette ordonnance contient-elle ce médicament ?",
        "notion": "Requête ASK (vérifier une relation)",
        "params": {"prescription": ":Presc_003", "medicament": ":Advil"},
        "sparql": "ASK { {{prescription}} :prescritMedicament {{medicament}} }",
    },
    "D11_patient_en_danger": {
        "titre": "Ce patient a-t-il une prescription contre-indiquée ?",
        "notion": "ASK sur une chaîne de 5 propriétés",
        "params": {"patient": ":Patient_Youssef"},
        "sparql": """
ASK {
  ?presc :concernePatient {{patient}} ; :prescritMedicament/:contientMolecule/:aContreIndication/:concernePathologie ?patho .
  {{patient}} :souffreDe ?patho .
}""",
    },
    "D12_graphe_prescription": {
        "titre": "Sous-graphe d'une ordonnance et du dossier clinique du patient",
        "notion": "Requête CONSTRUCT (nouveau graphe RDF)",
        "params": {"prescription": ":Presc_003"},
        "sparql": """
CONSTRUCT {
  {{prescription}} :concernePatient ?pat ; :prescritPar ?doc ; :prescritMedicament ?med ; :estDelivreePar ?ph .
  ?pat :souffreDe ?patho ; :aDonneeClinique ?d .
  ?d :allergiqueA ?allergene ; :porteSur ?antecedent .
  ?med :contientMolecule ?mol .
  ?mol :aContreIndication ?ci .
  ?ci :concernePathologie ?ciPatho .
} WHERE {
  {{prescription}} :concernePatient ?pat ; :prescritPar ?doc ; :prescritMedicament ?med .
  OPTIONAL { {{prescription}} :estDelivreePar ?ph }
  OPTIONAL { ?pat :souffreDe ?patho }
  OPTIONAL { ?d :estDonneeDe ?pat . OPTIONAL { ?d :allergiqueA ?allergene } OPTIONAL { ?d :porteSur ?antecedent } }
  OPTIONAL { ?med :contientMolecule ?mol . OPTIONAL { ?mol :aContreIndication ?ci . OPTIONAL { ?ci :concernePathologie ?ciPatho } } }
}""",
    },
    "D13_donnees_par_type": {
        "titre": "Données cliniques par type (hiérarchie à 3 niveaux)",
        "notion": "GROUP BY sur le type déclaré + COUNT + rdfs:subClassOf",
        "params": {},
        "sparql": """
SELECT ?type ?label ?parent (COUNT(DISTINCT ?d) AS ?nombre) WHERE {
  VALUES ?type { :SigneVital :AnalyseBiologique :Allergie :Antecedent }
  ?type rdfs:label ?label .
  GRAPH <urn:pharma:base> { ?type rdfs:subClassOf ?parent }
  OPTIONAL { ?d a ?type }
} GROUP BY ?type ?label ?parent ORDER BY ?parent ?type""",
    },
    "D14_clairance_basse": {
        "titre": "Patients dont la clairance de la créatinine est < 60 mL/min",
        "notion": "FILTER numérique sur une donnée clinique (requête Q8 de requetes.sparql)",
        "params": {"seuil": lit(60)},
        "sparql": """
SELECT ?patient ?nom ?valeur ?unite ?date WHERE {
  ?d a :AnalyseBiologique ; rdfs:label "Clairance de la créatinine"@fr ;
     :valeur ?valeur ; :unite ?unite ; :estDonneeDe ?patient .
  OPTIONAL { ?d :dateMesure ?date }
  ?patient rdfs:label ?nom .
  FILTER(?valeur < {{seuil}})
}""",
    },
    "D15_dossier_clinique": {
        "titre": "Dossier clinique d'un patient",
        "notion": "Propriété inverse aDonneeClinique (inférée depuis estDonneeDe) + UNION + OPTIONAL",
        "params": {"patient": ":Patient_Sara"},
        "sparql": """
SELECT ?donnee ?label ?valeur ?unite ?date ?detail WHERE {
  {{patient}} :aDonneeClinique ?donnee .
  ?donnee rdfs:label ?label .
  OPTIONAL { ?donnee :valeur ?valeur } OPTIONAL { ?donnee :unite ?unite } OPTIONAL { ?donnee :dateMesure ?date }
  OPTIONAL { { ?donnee :allergiqueA/rdfs:label ?detail } UNION { ?donnee :porteSur/rdfs:label ?detail } }
} ORDER BY DESC(?date)""",
    },
    "D16_patients_sans_donnee": {
        "titre": "Patients avec ordonnance mais sans aucune donnée clinique",
        "notion": "FILTER NOT EXISTS + DISTINCT",
        "params": {},
        "sparql": """
SELECT DISTINCT ?patient ?nom WHERE {
  ?presc :concernePatient ?patient . ?patient rdfs:label ?nom .
  FILTER NOT EXISTS { ?d :estDonneeDe ?patient }
}""",
    },
    "D17_types_inferes": {
        "titre": "Types déduits par le raisonneur (prescriptions et données cliniques)",
        "notion": "Graphes nommés : inféré (OWL 2 RL) vs déclaré",
        "params": {},
        "sparql": """
SELECT ?individu ?label ?typeInfere WHERE {
  GRAPH <urn:pharma:inferred> { ?individu rdf:type ?typeInfere }
  VALUES ?typeInfere { :Prescription :PrescriptionSimple :PrescriptionRenouvelable :DonneeClinique :ExamenClinique :HistoriqueMedical }
  ?individu rdfs:label ?label .
  FILTER NOT EXISTS { GRAPH <urn:pharma:base> { ?individu rdf:type ?typeInfere } }
} ORDER BY ?individu ?typeInfere""",
    },
    "D18_crud_exemple": {
        "titre": "CRUD — créer, modifier, supprimer (exemple)",
        "notion": "SPARQL Update : INSERT DATA / DELETE-INSERT WHERE / DELETE WHERE",
        "params": {},
        "lecture_seule": False,
        "sparql": """
# CREATE
INSERT DATA { :Glycemie_Youssef a owl:NamedIndividual , :AnalyseBiologique ;
  rdfs:label "Glycémie à jeun"@fr ; :valeur 1.05 ; :unite "g/L" ;
  :dateMesure "2026-10-15"^^xsd:date ; :estDonneeDe :Patient_Youssef } ;
# UPDATE
DELETE { :Glycemie_Youssef :valeur ?ancienne } INSERT { :Glycemie_Youssef :valeur 1.10 }
WHERE  { :Glycemie_Youssef :valeur ?ancienne } ;
# DELETE
DELETE WHERE { :Glycemie_Youssef ?p ?o }""",
    },
}


def catalogue_entry(name: str, **overrides):
    entry = CATALOGUE[name]
    return render(entry["sparql"], **{**entry["params"], **overrides})
