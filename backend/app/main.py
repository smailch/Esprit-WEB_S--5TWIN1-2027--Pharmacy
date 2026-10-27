"""Point d'entrée FastAPI de l'application PharmaSémantique.

Lancement : uvicorn app.main:app --reload --port 8000  (depuis le dossier backend/)
Documentation interactive : http://localhost:8000/docs
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import config
from .graph_store import store
from .modules.molecule_medicament.nlp_router import router as nlp_router
from .modules.molecule_medicament.router import router as module_a_router
from .modules.prescription_clinique.router import router as module_d_router

app = FastAPI(
    title="PharmaSémantique API",
    description="API de l'ontologie pharmaceutique (NeoCoders, 5 TWIN 2026/2027). Toutes les données passent par SPARQL.",
    version="1.0.0",
)

app.add_middleware(CORSMiddleware, allow_origins=config.CORS_ORIGINS, allow_methods=["*"], allow_headers=["*"])

app.include_router(module_a_router, prefix="/api")
app.include_router(nlp_router, prefix="/api")
app.include_router(module_d_router, prefix="/api")


@app.on_event("startup")
def warm_up():
    """Charge spaCy et le modèle d'intention au démarrage (la première question est ainsi instantanée)."""
    from nlp.pharmanlu.pipeline import get_nlu
    get_nlu(store).ask("liste des antibiotiques")


@app.get("/api/health", tags=["Système"])
def health():
    return {"statut": "ok", **store.stats()}


@app.post("/api/admin/reset", tags=["Système"])
def reset():
    """Recharge l'ontologie d'origine (annule toutes les modifications CRUD)."""
    store.load(reset=True)
    return {"statut": "réinitialisé", **store.stats()}
