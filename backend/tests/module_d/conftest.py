"""Configuration des tests du module D.

Le graphe est chargé depuis une COPIE de ontologie/pharma.ttl : l'ontologie d'équipe n'est jamais lue en écriture
ni modifiée. (Le conftest parent du module A redirige déjà le fichier runtime vers un dossier temporaire.)
"""
import hashlib
import os
import shutil
import sys
import tempfile
from pathlib import Path

ORIGINAL = Path(__file__).resolve().parents[3] / "ontologie" / "pharma.ttl"
os.environ.setdefault("ORIGINAL_ONTOLOGY_SHA256", hashlib.sha256(ORIGINAL.read_bytes()).hexdigest())
if "app.config" not in sys.modules:  # la configuration est lue une seule fois, à l'import de l'application
    copy = Path(tempfile.mkdtemp()) / "pharma.ttl"
    shutil.copy(ORIGINAL, copy)
    os.environ["ONTOLOGY_PATH"] = str(copy)
