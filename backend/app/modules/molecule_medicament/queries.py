"""Catalogue des requêtes SPARQL nommées du module A (Molécule + Médicament).

Chaque requête est un gabarit : les paramètres {{nom}} sont remplacés par des termes RDF
déjà sérialisés et échappés (voir `render`), jamais par du texte brut venant de l'utilisateur.
"""
import re

from rdflib import Literal, URIRef
from rdflib.namespace import XSD

from ...graph_store import PH

ID_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")


def uri(local_id: str) -> str:
    if not ID_PATTERN.match(local_id or ""):
        raise ValueError(f"Identifiant invalide : {local_id!r}")
    return f":{local_id}"


def lit(value, datatype=None, lang=None) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)) and datatype is None:
        return Literal(value, datatype=XSD.decimal if isinstance(value, float) else XSD.integer).n3()
    return Literal(value, datatype=datatype, lang=lang).n3()


def render(sparql: str, **params) -> str:
    def sub(m):
        key = m.group(1)
        if key not in params:
            raise KeyError(f"Paramètre manquant : {key}")
        return str(params[key])
    return re.sub(r"\{\{(\w+)\}\}", sub, sparql).strip()


MOLECULE_CLASSES = ["Molecule", "Antibiotique", "Penicilline", "Macrolide", "Antalgique", "AntalgiqueNonOpioide", "AntalgiqueOpioide"]
MEDICAMENT_TYPES = ["Princeps", "Generique"]

# ---------------------------------------------------------------------------
# Catalogue : nom → métadonnées + gabarit. `params` = valeurs par défaut (déjà sérialisées).
# ---------------------------------------------------------------------------
CATALOGUE = {
    "Q01_hierarchie_molecules": {
        "titre": "Hiérarchie des molécules",
        "notion": "Chemin de propriété rdfs:subClassOf+ (tous niveaux)",
        "params": {},
        "sparql": """
SELECT ?classe ?label ?parent WHERE {
  GRAPH <urn:pharma:base> {
    ?classe rdfs:subClassOf+ :Molecule ; rdfs:label ?label ; rdfs:subClassOf ?parent .
    ?parent rdfs:subClassOf* :Molecule .
  }
  FILTER(isIRI(?parent) && ?parent != ?classe)
} ORDER BY ?parent ?classe""",
    },
    "Q02_antibiotiques": {
        "titre": "Tous les antibiotiques (via la hiérarchie)",
        "notion": "rdf:type/rdfs:subClassOf* — appartenance indirecte",
        "params": {"classe": ":Antibiotique"},
        "sparql": """
SELECT DISTINCT ?molecule ?label ?classeDeclaree WHERE {
  GRAPH <urn:pharma:base> { ?molecule rdf:type ?classeDeclaree . ?classeDeclaree rdfs:subClassOf* {{classe}} . }
  ?molecule rdfs:label ?label .
} ORDER BY ?label""",
    },
    "Q03_sans_ordonnance_moins_de": {
        "titre": "Médicaments sans ordonnance à moins de X DT",
        "notion": "FILTER numérique + booléen, ORDER BY",
        "params": {"prixMax": lit(5.0)},
        "sparql": """
SELECT ?medicament ?nom ?prix WHERE {
  ?medicament :nomCommercial ?nom ; :surOrdonnance false ; :prixDT ?prix .
  FILTER(?prix < {{prixMax}})
} ORDER BY ?prix""",
    },
    "Q04_recherche_texte": {
        "titre": "Recherche plein texte (molécules et médicaments)",
        "notion": "FILTER REGEX insensible à la casse, UNION",
        "params": {"motif": lit("ibupro")},
        "sparql": """
SELECT DISTINCT ?ressource ?label ?type WHERE {
  { ?ressource a :Molecule . BIND("Molécule" AS ?type) }
  UNION
  { ?ressource a :Medicament . BIND("Médicament" AS ?type) }
  ?ressource rdfs:label ?label .
  FILTER(REGEX(STR(?label), {{motif}}, "i") || REGEX(STRAFTER(STR(?ressource), "#"), {{motif}}, "i"))
} ORDER BY ?type ?label""",
    },
    "Q05_medicaments_par_molecule": {
        "titre": "Médicaments contenant une molécule",
        "notion": "Propriété inverse owl:inverseOf (estContenuDans inférée)",
        "params": {"molecule": ":Ibuprofene"},
        "sparql": """
SELECT ?medicament ?label ?prix WHERE {
  {{molecule}} :estContenuDans ?medicament .
  ?medicament rdfs:label ?label ; :prixDT ?prix .
} ORDER BY ?prix""",
    },
    "Q06_alternatives_generiques": {
        "titre": "Alternatives (même composition) et économie",
        "notion": "Jointure, FILTER NOT EXISTS, BIND arithmétique",
        "params": {"medicament": ":Advil"},
        "sparql": """
SELECT DISTINCT ?alternative ?label ?type ?prix ?prixReference ?economie ?economiePct WHERE {
  {{medicament}} :contientMolecule ?mol ; :prixDT ?prixReference .
  ?alternative :contientMolecule ?mol ; :prixDT ?prix ; rdfs:label ?label .
  FILTER(?alternative != {{medicament}})
  FILTER NOT EXISTS { ?alternative :contientMolecule ?autre . FILTER NOT EXISTS { {{medicament}} :contientMolecule ?autre } }
  OPTIONAL { ?alternative a ?type . VALUES ?type { :Princeps :Generique } }
  BIND(?prixReference - ?prix AS ?economie)
  BIND(ROUND(100 * (?prixReference - ?prix) / ?prixReference) AS ?economiePct)
} ORDER BY ?prix""",
    },
    "Q07_interactions": {
        "titre": "Interactions entre médicaments",
        "notion": "Propriété symétrique owl:SymmetricProperty (interagitAvec), VALUES",
        "params": {"medicaments": ":Advil :Aspegic :Doliprane"},
        "sparql": """
SELECT DISTINCT ?medA ?labelA ?molA ?molALabel ?medB ?labelB ?molB ?molBLabel WHERE {
  VALUES ?medA { {{medicaments}} }
  VALUES ?medB { {{medicaments}} }
  FILTER(STR(?medA) < STR(?medB))
  ?medA :contientMolecule ?molA ; rdfs:label ?labelA .
  ?medB :contientMolecule ?molB ; rdfs:label ?labelB .
  ?molA :interagitAvec ?molB .
  ?molA rdfs:label ?molALabel . ?molB rdfs:label ?molBLabel .
}""",
    },
    "Q07b_doublons_molecule": {
        "titre": "Doublons de principe actif (risque de surdosage)",
        "notion": "Auto-jointure sur la même molécule, VALUES",
        "params": {"medicaments": ":Advil :IbuprofeneMylan :Doliprane"},
        "sparql": """
SELECT DISTINCT ?medA ?labelA ?medB ?labelB ?mol ?molLabel WHERE {
  VALUES ?medA { {{medicaments}} }
  VALUES ?medB { {{medicaments}} }
  FILTER(STR(?medA) < STR(?medB))
  ?medA :contientMolecule ?mol ; rdfs:label ?labelA .
  ?medB :contientMolecule ?mol ; rdfs:label ?labelB .
  ?mol rdfs:label ?molLabel .
}""",
    },
    "Q08_contre_indiques_pour": {
        "titre": "Médicaments contre-indiqués pour une pathologie",
        "notion": "Chaîne de propriétés contientMolecule/aContreIndication/concernePathologie (≡ owl:propertyChainAxiom)",
        "params": {"pathologie": ":UlcereGastroduodenal"},
        "sparql": """
SELECT DISTINCT ?medicament ?label ?molecule ?contreIndication WHERE {
  ?med :contientMolecule ?mol .
  ?mol :aContreIndication ?ci .
  ?ci :concernePathologie {{pathologie}} .
  ?med rdfs:label ?label . ?mol rdfs:label ?molecule . ?ci rdfs:label ?contreIndication .
  BIND(?med AS ?medicament)
} ORDER BY ?label""",
    },
    "Q09_effets_graves_medicament": {
        "titre": "Effets secondaires d'un médicament (graves en premier)",
        "notion": "OPTIONAL + FILTER + ORDER BY sur une chaîne de 2 propriétés",
        "params": {"medicament": ":Advil"},
        "sparql": """
SELECT DISTINCT ?effet ?label ?gravite ?frequence ?molecule WHERE {
  {{medicament}} :contientMolecule ?mol .
  ?mol :peutProvoquer ?effet ; rdfs:label ?molecule .
  ?effet rdfs:label ?label .
  OPTIONAL { ?effet :niveauGravite ?gravite }
  OPTIONAL { ?effet :frequence ?frequence }
} ORDER BY DESC(?gravite = "grave") ?label""",
    },
    "Q10_stats_par_type": {
        "titre": "Statistiques de prix par type de médicament",
        "notion": "Agrégats COUNT / AVG / MIN / MAX, GROUP BY, HAVING",
        "params": {"minimum": lit(1)},
        "sparql": """
SELECT ?type (COUNT(DISTINCT ?med) AS ?nombre) (AVG(?prix) AS ?prixMoyen) (MIN(?prix) AS ?prixMin) (MAX(?prix) AS ?prixMax) WHERE {
  VALUES ?type { :PrincepsSurOrdonnance :PrincepsSansOrdonnance :GeneriqueSurOrdonnance :GeneriqueSansOrdonnance }
  ?med a ?type ; :prixDT ?prix .
} GROUP BY ?type HAVING(COUNT(DISTINCT ?med) >= {{minimum}}) ORDER BY ?type""",
    },
    "Q11_molecules_orphelines": {
        "titre": "Molécules sans médicament commercialisé",
        "notion": "Négation : FILTER NOT EXISTS",
        "params": {},
        "sparql": """
SELECT ?molecule ?label WHERE {
  ?molecule a :Molecule ; rdfs:label ?label .
  FILTER NOT EXISTS { ?medicament :contientMolecule ?molecule }
} ORDER BY ?label""",
    },
    "Q12_est_sur_ordonnance": {
        "titre": "Ce médicament est-il sur ordonnance ?",
        "notion": "Requête ASK (réponse oui / non)",
        "params": {"medicament": ":Clamoxyl"},
        "sparql": """
ASK { {{medicament}} :surOrdonnance true }""",
    },
    "Q13_fiche_graphe": {
        "titre": "Sous-graphe d'un médicament",
        "notion": "Requête CONSTRUCT (produit un nouveau graphe RDF)",
        "params": {"medicament": ":Advil"},
        "sparql": """
CONSTRUCT {
  {{medicament}} :contientMolecule ?mol ; :estIndiquePour ?patho ; :estContreIndiquePour ?ci_patho .
  ?mol :peutProvoquer ?effet ; :aContreIndication ?ci ; :interagitAvec ?autre .
} WHERE {
  {{medicament}} :contientMolecule ?mol .
  OPTIONAL { {{medicament}} :estIndiquePour ?patho }
  OPTIONAL { {{medicament}} :estContreIndiquePour ?ci_patho }
  OPTIONAL { ?mol :peutProvoquer ?effet }
  OPTIONAL { ?mol :aContreIndication ?ci }
  OPTIONAL { ?mol :interagitAvec ?autre }
}""",
    },
    "Q14_crud_exemple": {
        "titre": "CRUD — créer, modifier, supprimer (exemple)",
        "notion": "SPARQL Update : INSERT DATA / DELETE-INSERT WHERE / DELETE WHERE",
        "params": {},
        "lecture_seule": False,
        "sparql": """
# CREATE
INSERT DATA { :ParacetamolBiogaran a owl:NamedIndividual , :Generique ;
  rdfs:label "Paracétamol Biogaran 500 mg"@fr ; :nomCommercial "Paracétamol Biogaran" ;
  :surOrdonnance false ; :prixDT 2.1 ; :contientMolecule :Paracetamol } ;
# UPDATE
DELETE { :ParacetamolBiogaran :prixDT ?ancien } INSERT { :ParacetamolBiogaran :prixDT 1.9 }
WHERE  { :ParacetamolBiogaran :prixDT ?ancien } ;
# DELETE
DELETE WHERE { :ParacetamolBiogaran ?p ?o }""",
    },
    "Q15_types_inferes": {
        "titre": "Types déduits par le raisonneur (non déclarés)",
        "notion": "Graphes nommés (GRAPH) : inférence OWL 2 RL vs déclaré — classes définies owl:equivalentClass",
        "params": {},
        "sparql": """
SELECT ?individu ?label ?typeInfere WHERE {
  GRAPH <urn:pharma:inferred> { ?individu rdf:type ?typeInfere }
  VALUES ?typeInfere { :PrincepsSurOrdonnance :PrincepsSansOrdonnance :GeneriqueSurOrdonnance :GeneriqueSansOrdonnance
                       :Antibiotique :Antalgique :Penicilline }
  ?individu rdfs:label ?label .
  FILTER NOT EXISTS { GRAPH <urn:pharma:base> { ?individu rdf:type ?typeInfere } }
} ORDER BY ?typeInfere ?label""",
    },
}


def catalogue_entry(name: str, **overrides):
    entry = CATALOGUE[name]
    params = {**entry["params"], **overrides}
    return render(entry["sparql"], **params)
