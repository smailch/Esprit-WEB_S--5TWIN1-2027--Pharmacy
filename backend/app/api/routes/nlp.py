"""Question en français vers une requête SPARQL exécutée localement."""

from __future__ import annotations

from fastapi import APIRouter, Request

from app.api.deps import store_of
from app.nlp.pipeline import answer_question
from app.schemas import AskBody

router = APIRouter(prefix="/nlp", tags=["taln"])


@router.post("/ask")
def ask(body: AskBody, request: Request) -> dict:
    return answer_question(store_of(request), body.question)
