"""Remet les données dans l'état initial (plan B de la démo), en une commande.

Passe par l'API (fonctionne en mode rdflib comme en mode Fuseki).
Usage : python scripts/reset_data.py [URL_API]
"""
import sys

import httpx

api = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
r = httpx.post(f"{api}/api/admin/reset", timeout=60)
r.raise_for_status()
print("Données réinitialisées :", r.json())
