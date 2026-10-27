"""Application FastAPI du module B."""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import contraindications, effects, nlp, ontology, sparql
from app.b_config import Settings, get_settings
from app.ontology.loader import OntologyStore

logger = logging.getLogger("pharma")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    store = OntologyStore(settings)
    store.load()
    logger.warning("Graphe chargé : %s triplets depuis %s", store.triple_count, store.loaded_from)

    app = FastAPI(
        title="PharmaSémantique — module B",
        version="1.0.0",
        summary="Effets secondaires et contre-indications, SPARQL et TALN local.",
        description=(
            "API FastAPI + RDFLib pour les classes EffetSecondaire et ContreIndication. "
            "Le traducteur par défaut est Qwen2.5 3B Instruct, exécuté en local par Ollama. "
            "S'il est absent, spaCy et des modèles SPARQL répondent. "
            "Aucune API cloud n'est appelée. RDFLib n'exécute pas un raisonneur OWL complet."
        ),
    )
    app.state.settings = settings
    app.state.store = store
    origins = [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(ontology.router, prefix="/api")
    app.include_router(effects.router, prefix="/api")
    app.include_router(contraindications.router, prefix="/api")
    app.include_router(nlp.router, prefix="/api")
    app.include_router(sparql.router, prefix="/api")
    return app


def mount(app: FastAPI) -> None:
    """Branche le module B sur l'application commune, sous /api/b."""
    settings = get_settings()
    store = OntologyStore(settings)
    store.load()
    app.state.settings = settings
    app.state.store = store
    app.include_router(ontology.router, prefix="/api/b")
    app.include_router(effects.router, prefix="/api/b")
    app.include_router(contraindications.router, prefix="/api/b")
    app.include_router(nlp.router, prefix="/api/b")
    app.include_router(sparql.router, prefix="/api/b")
