"""Charge pharma.ttl + ontology-extension/*.ttl dans le dataset Fuseki (Graph Store Protocol).

Remplace le graphe par défaut : sert aussi de remise à zéro côté Fuseki.
Usage : python scripts/load_ontology.py
"""
from _common import settings

from app.sparql.client import FusekiClient

client = FusekiClient(settings.fuseki_url, settings.fuseki_dataset, settings.ontology_files(),
                      auth=(settings.fuseki_user, settings.fuseki_password))
client.reset()
n = client.select("SELECT (COUNT(*) AS ?n) WHERE { ?s ?p ?o }").rows[0]["n"]
for f in settings.ontology_files():
    print("chargé :", f.name)
print(f"{n} triplets dans {settings.fuseki_url}/{settings.fuseki_dataset}")
