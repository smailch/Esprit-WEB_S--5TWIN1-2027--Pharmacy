"""Configuration : uniquement des chemins relatifs au dépôt, surchargeables par .env."""
import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = BACKEND_DIR.parent

load_dotenv(BACKEND_DIR / ".env")

ONTOLOGY_PATH = Path(os.getenv("ONTOLOGY_PATH", REPO_DIR / "ontologie" / "pharma.ttl"))
# Individus ajoutés par les membres (ex. individus-ahmed.ttl), chargés en plus de pharma.ttl qui reste intact
EXTENSIONS_DIR = Path(os.getenv("EXTENSIONS_DIR", REPO_DIR / "ontologie" / "extensions"))
RUNTIME_PATH = Path(os.getenv("RUNTIME_PATH", BACKEND_DIR / "data" / "runtime.ttl"))
NLP_MODEL_PATH = Path(os.getenv("NLP_MODEL_PATH", BACKEND_DIR / "nlp" / "models" / "pharmanlu_intent_v1.joblib"))
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if o.strip()]

PHARMA_NS = "http://example.org/pharma#"
BASE_GRAPH = "urn:pharma:base"
INFERRED_GRAPH = "urn:pharma:inferred"
