"""Installation reproductible des modèles NLP (aucun fichier hors dépôt, aucune clé API).

1. Modèle spaCy fr_core_news_md, version épinglée (téléchargé depuis les releases officielles spaCy).
2. Entraînement du classifieur d'intentions (scikit-learn) → nlp/model/intent.joblib (< 1 Mo).
Usage (depuis Ahmed/backend) : python scripts/setup_models.py
"""
import importlib.util
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

SPACY_MODEL = "fr_core_news_md"
SPACY_VERSION = "3.8.0"
URL = (f"https://github.com/explosion/spacy-models/releases/download/"
       f"{SPACY_MODEL}-{SPACY_VERSION}/{SPACY_MODEL}-{SPACY_VERSION}-py3-none-any.whl")

if importlib.util.find_spec(SPACY_MODEL) is None:
    print(f"Installation de {SPACY_MODEL} {SPACY_VERSION}…")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--no-deps", URL])
else:
    print(f"{SPACY_MODEL} déjà installé")

import joblib  # noqa: E402

from app.nlp.intent import MODEL, load_dataset, train  # noqa: E402

texts, labels = load_dataset()
model = train()
MODEL.parent.mkdir(exist_ok=True)
joblib.dump(model, MODEL)
print(f"Classifieur entraîné sur {len(texts)} exemples / {len(set(labels))} intentions → {MODEL} "
      f"({MODEL.stat().st_size // 1024} Ko)")
