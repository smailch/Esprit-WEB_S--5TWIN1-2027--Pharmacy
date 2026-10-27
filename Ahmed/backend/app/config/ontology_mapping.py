"""Seul fichier qui connaît les noms de l'ontologie partagée.

Si l'équipe renomme une classe ou une propriété, on ne modifie que ce fichier.
"""

NS = "http://example.org/pharma#"

PREFIXES = f"""PREFIX :     <{NS}>
PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl:  <http://www.w3.org/2002/07/owl#>
PREFIX xsd:  <http://www.w3.org/2001/XMLSchema#>
"""

# Classes (nom local dans l'ontologie)
C = {
    "Pathologie": "Pathologie",
    "MaladieAigue": "MaladieAigue",
    "MaladieChronique": "MaladieChronique",
    "InfectionAigue": "InfectionAigue",
    "DouleurAigue": "DouleurAigue",
    "MaladieMetabolique": "MaladieMetabolique",
    "InsuffisanceOrgane": "InsuffisanceOrgane",
    "Personne": "Personne",
    "Patient": "Patient",
    "PatientEnfant": "PatientEnfant",
    "PatientAdulte": "PatientAdulte",
    "ProfessionnelSante": "ProfessionnelSante",
    "Medecin": "Medecin",
    "Pharmacien": "Pharmacien",
    # Classes des autres membres (lecture seule, pour les jointures)
    "Medicament": "Medicament",
    "Molecule": "Molecule",
    "ContreIndication": "ContreIndication",
    "Prescription": "Prescription",
    "Allergie": "Allergie",
    "Antecedent": "Antecedent",
}

# Propriétés
P = {
    "codeCIM10": "codeCIM10",
    "nom": "nom",
    "age": "age",
    "sexe": "sexe",
    "specialite": "specialite",
    "souffreDe": "souffreDe",
    "concernePathologie": "concernePathologie",
    "estIndiquePour": "estIndiquePour",
    "contientMolecule": "contientMolecule",
    "aContreIndication": "aContreIndication",
    "concernePatient": "concernePatient",
    "prescritPar": "prescritPar",
    "prescritMedicament": "prescritMedicament",
    "estDelivreePar": "estDelivreePar",
    "estDonneeDe": "estDonneeDe",
    "allergiqueA": "allergiqueA",
    "porteSur": "porteSur",
    "nomCommercial": "nomCommercial",
}

# Sous-types de pathologie autorisés à la création (niveau 3 + MaladieChronique,
# utilisé dans pharma.ttl pour l'ulcère).
PATHOLOGY_TYPES = [
    "InfectionAigue", "DouleurAigue", "MaladieMetabolique", "InsuffisanceOrgane",
    "MaladieAigue", "MaladieChronique",
]
PATHOLOGY_FAMILY = {
    "InfectionAigue": "MaladieAigue", "DouleurAigue": "MaladieAigue", "MaladieAigue": "MaladieAigue",
    "MaladieMetabolique": "MaladieChronique", "InsuffisanceOrgane": "MaladieChronique",
    "MaladieChronique": "MaladieChronique",
}

# Préfixes d'URI des individus créés par l'application
URI_PREFIX = {"Patient": "Patient_", "Medecin": "Dr_", "Pharmacien": "Ph_"}

AGE_ADULTE = 18


def iri(local: str) -> str:
    """IRI complet entre chevrons pour un nom local déjà validé."""
    return f"<{NS}{local}>"


def cls(key: str) -> str:
    return iri(C[key])


def prop(key: str) -> str:
    return iri(P[key])
