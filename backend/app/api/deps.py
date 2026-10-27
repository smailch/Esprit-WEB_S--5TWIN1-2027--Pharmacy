"""Dépendances FastAPI."""

from __future__ import annotations

import hmac

from fastapi import HTTPException, Request

from app.ontology.loader import OntologyError, OntologyStore
from app.ontology.queries import DomainError


def store_of(request: Request) -> OntologyStore:
    return request.app.state.store


def raise_domain(exc: Exception) -> None:
    if isinstance(exc, DomainError):
        raise HTTPException(exc.status, str(exc)) from exc
    if isinstance(exc, OntologyError):
        raise HTTPException(400, str(exc)) from exc
    raise exc


def require_write(request: Request) -> None:
    expected = (request.app.state.settings.write_token or "").strip()
    if not expected:
        raise HTTPException(403, "Écriture désactivée : WRITE_TOKEN est vide.")
    provided = request.headers.get("X-Write-Token", "")
    if not provided:
        raise HTTPException(401, "Jeton d'écriture requis dans l'en-tête X-Write-Token.")
    if not hmac.compare_digest(provided, expected):
        raise HTTPException(403, "Jeton d'écriture refusé.")
