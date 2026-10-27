"""Prépare l'import du backend pour les outils en ligne de commande.

RUNTIME_PATH pointe vers un fichier temporaire : les outils partent toujours de l'ontologie d'origine
(+ extensions) et ne modifient jamais les données de démonstration (backend/data/runtime.ttl).
"""
import os
import sys
import tempfile
from pathlib import Path

os.environ["RUNTIME_PATH"] = str(Path(tempfile.mkdtemp()) / "runtime_outil.ttl")
BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
