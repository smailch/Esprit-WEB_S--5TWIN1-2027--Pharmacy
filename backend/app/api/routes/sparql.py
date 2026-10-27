"""Console SPARQL en lecture seule."""

from __future__ import annotations

from rdflib import Literal, URIRef

from fastapi import APIRouter, HTTPException, Request

from app.api.deps import store_of
from app.ontology.loader import OntologyError
from app.ontology.queries import local_name, read_examples
from app.ontology.sparql_guard import SparqlRejected, validate_read_query
from app.schemas import SparqlBody

router = APIRouter(prefix="/sparql", tags=["sparql"])


def _term(value):
    if isinstance(value, URIRef):
        return {"type": "uri", "value": str(value), "id": local_name(value)}
    if isinstance(value, Literal):
        return {"type": "literal", "value": str(value), "lang": value.language, "datatype": str(value.datatype) if value.datatype else None}
    if isinstance(value, tuple) and len(value) == 3:
        return {"s": _term(value[0]), "p": _term(value[1]), "o": _term(value[2])}
    if value is None:
        return None
    return {"type": "literal", "value": str(value)}


@router.get("/examples")
def examples(request: Request) -> dict:
    path = request.app.state.settings.queries_path
    if not path.exists():
        raise HTTPException(404, f"Fichier de requêtes introuvable : {path}")
    items = read_examples(path)
    return {
        "items": [
            {**item, "executable": item["kind"] == "read"}
            for item in items
        ],
        "note": "Les requêtes INSERT et DELETE du fichier pédagogique ne sont pas exécutables par cet endpoint.",
    }


@router.post("/query")
def run_query(body: SparqlBody, request: Request) -> dict:
    try:
        query = validate_read_query(body.query, request.app.state.settings.sparql_max_length)
        result = store_of(request).query(query)
    except SparqlRejected as exc:
        raise HTTPException(400, str(exc)) from exc
    except OntologyError as exc:
        raise HTTPException(400, str(exc)) from exc

    limit = request.app.state.settings.sparql_max_rows
    if result["kind"] == "ASK":
        return {"kind": "ASK", "ask": result["ask"], "results": [{"ask": result["ask"]}], "count": 1, "truncated": False}
    if result["kind"] == "CONSTRUCT":
        rows = result["rows"]
        return {
            "kind": "CONSTRUCT",
            "results": [_term(row) for row in rows[:limit]],
            "count": min(len(rows), limit),
            "truncated": len(rows) > limit,
        }
    rows = result["rows"]
    shaped = []
    for row in rows[:limit]:
        shaped.append({key: _term(value) for key, value in row.items()})
    return {
        "kind": "SELECT",
        "vars": result["vars"],
        "results": shaped,
        "count": min(len(rows), limit),
        "truncated": len(rows) > limit,
    }
