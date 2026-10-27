"""Routes de l'assistant en langage naturel (modèle PharmaNLU-A)."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from nlp.pharmanlu.pipeline import SUGGESTIONS, get_nlu, model_card

from ...graph_store import store

router = APIRouter(prefix="/nlp", tags=["Module A — Assistant IA (PharmaNLU-A)"])


class Question(BaseModel):
    question: str = Field(min_length=2, max_length=300)


@router.post("/ask")
def ask(body: Question):
    try:
        data = get_nlu(store).ask(body.question)
    except Exception as e:  # une requête générée qui échoue ne doit jamais faire tomber l'API
        raise HTTPException(500, f"Erreur du module NLP : {e}")
    sparql = [{"titre": f"Requête générée — {data['intentionLabel']}", "requete": data["sparql"]}] if data.get("sparql") else []
    return {"data": data, "sparql": sparql}


@router.get("/suggestions")
def suggestions():
    return {"data": SUGGESTIONS, "sparql": []}


@router.get("/modele")
def modele():
    return {"data": model_card(), "sparql": []}
