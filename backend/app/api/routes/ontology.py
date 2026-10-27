"""Santé du service, statistiques et ressources de formulaires."""

from __future__ import annotations

from fastapi import APIRouter, Query, Request

from app.api.deps import raise_domain, store_of
from app.nlp.entity_extractor import analyzer_mode
from app.nlp.qwen import probe_qwen
from app.ontology.queries import resources, search, stats
from app.ontology.vocab import REASONING_LIMIT

router = APIRouter(tags=["ontologie"])


@router.get("/health")
def health(request: Request) -> dict:
    store = store_of(request)
    return {
        "status": "ok",
        "triples": store.triple_count,
        "spacy": analyzer_mode(),
        "llm": probe_qwen(request.app.state.settings),
        "module": "B",
        "base": "http://example.org/pharma#",
        "reasoning": REASONING_LIMIT,
    }


@router.get("/ontology/stats")
def ontology_stats(request: Request) -> dict:
    try:
        return stats(store_of(request))
    except Exception as exc:
        raise_domain(exc)


@router.get("/ontology/resources")
def ontology_resources(request: Request) -> dict:
    try:
        return resources(store_of(request))
    except Exception as exc:
        raise_domain(exc)


@router.get("/search")
def search_terms(request: Request, q: str = Query(min_length=2, max_length=80)) -> dict:
    try:
        return search(store_of(request), q)
    except Exception as exc:
        raise_domain(exc)
