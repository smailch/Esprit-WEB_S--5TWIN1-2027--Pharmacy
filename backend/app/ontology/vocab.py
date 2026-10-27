"""Vocabulaire réel de pharma.ttl — ne pas inventer de classes ni de propriétés."""

from __future__ import annotations

PHARMA_NS = "http://example.org/pharma#"

PREFIXES = """
PREFIX : <http://example.org/pharma#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
""".strip()

EFFECT_TYPES = (
    "EffetSecondaire",
    "EffetLeger",
    "EffetGrave",
    "EffetLegerDigestif",
    "EffetLegerCutane",
    "EffetGraveDigestif",
    "EffetGraveNeurologique",
)

CI_TYPES = (
    "ContreIndication",
    "ContreIndicationAbsolue",
    "ContreIndicationRelative",
    "ContreIndicationAllergique",
    "ContreIndicationDigestive",
    "ContreIndicationRenale",
    "ContreIndicationHepatique",
)

# Propriétés autorisées en écriture pour le module B.
# peutProvoquer et aContreIndication sont écrites sur la molécule (domain réel),
# pas comme un triplet Médicament → Effet, qui n'existe pas dans l'ontologie.
EFFECT_DATATYPE_PROPERTIES = ("niveauGravite", "frequence")
CI_DATATYPE_PROPERTIES = ("niveauRisque",)
COMMON_DATATYPE_PROPERTIES = ("label",)

GRAVITE_VALUES = {"léger", "grave"}
RISQUE_VALUES = {"absolu", "relatif"}

EFFECT_CATEGORY_CLASSES = {
    "digestif": ("EffetLegerDigestif", "EffetGraveDigestif"),
    "cutane": ("EffetLegerCutane",),
    "neurologique": ("EffetGraveNeurologique",),
}

CI_CATEGORY_CLASSES = {
    "allergique": "ContreIndicationAllergique",
    "digestive": "ContreIndicationDigestive",
    "renale": "ContreIndicationRenale",
    "hepatique": "ContreIndicationHepatique",
    "absolue": "ContreIndicationAbsolue",
    "relative": "ContreIndicationRelative",
}

GRAVITE_BY_TYPE = {
    "EffetLeger": "léger",
    "EffetLegerDigestif": "léger",
    "EffetLegerCutane": "léger",
    "EffetGrave": "grave",
    "EffetGraveDigestif": "grave",
    "EffetGraveNeurologique": "grave",
}

RISQUE_BY_TYPE = {
    "ContreIndicationAbsolue": "absolu",
    "ContreIndicationAllergique": "absolu",
    "ContreIndicationDigestive": "absolu",
    "ContreIndicationRelative": "relatif",
    "ContreIndicationRenale": "relatif",
    "ContreIndicationHepatique": "relatif",
}

LOCAL_NAME = r"[A-Za-z][A-Za-z0-9_]*"

REASONING_LIMIT = (
    "RDFLib exécute SPARQL sur les triplets assertés, y compris les chemins "
    "rdfs:subClassOf. Les équivalences OWL, restrictions (hasValue, cardinalité) "
    "et la chaîne estContreIndiquePour ne sont pas matérialisées."
)
