"""Tests du traducteur NLP → SPARQL du module Pathologie + Personne."""
import pytest

from app.graph_store import store
from app.modules.pathologie_personne.client import StoreClient
from app.modules.pathologie_personne.nlp.evaluation import evaluate
from app.modules.pathologie_personne.nlp.intent import load_dataset
from app.modules.pathologie_personne.nlp.pipeline import NlpPipeline
from app.modules.pathologie_personne.service import Repository


@pytest.fixture(scope="module")
def nlp():
    store.load(reset=True)
    yield NlpPipeline(StoreClient(store))
    store.load(reset=True)


def count(nlp):
    return nlp.client.select("SELECT (COUNT(*) AS ?n) WHERE { ?s ?p ?o }").rows[0]["n"]


def test_training_data_has_15_examples_per_intent():
    _, labels = load_dataset()
    counts = {i: labels.count(i) for i in set(labels)}
    assert len(counts) >= 13 and min(counts.values()) >= 15, counts


def test_accuracy_target(nlp):
    nlp.client.reset()
    report = evaluate(nlp)
    assert report["total"] >= 60
    assert report["precision_perimetre"] >= 0.9, report["echecs"]


def test_explanation_and_highlighting(nlp):
    nlp.client.reset()
    out = nlp.ask("Quels patients souffrent de diabète ?")
    assert out["compris"] and out["sparql"].strip().endswith("ORDER BY ?patient")
    e = out["entites"][0]
    assert out["question"][e["start"]:e["end"]] == "diabète"  # positions valables dans la question d'origine
    assert {"text", "lemma", "pos", "dep"} <= set(out["tokens"][0])
    assert any(t["lemma"] == "souffrir" for t in out["tokens"])


def test_out_of_scope_gives_suggestions(nlp):
    out = nlp.ask("Quelle est la météo à Sousse ?")
    assert not out["compris"] and out["resultat"] is None and len(out["suggestions"]) == 3


def test_new_patient_is_recognised_without_restart(nlp):
    nlp.client.reset()
    Repository(nlp.client).create_patient("Yassine", "Kefi", 10, "M", ["Otite"])
    out = nlp.ask("De quoi souffre Yassine Kefi ?")
    assert out["compris"] and out["resultat"]["rows"][0]["pathologie"] == "Otite moyenne aiguë"
    nlp.client.reset()


def test_injection_in_question_is_harmless(nlp):
    nlp.client.reset()
    n = count(nlp)
    nlp.ask('Quels patients souffrent de "} DELETE WHERE { ?s ?p ?o } # diabète')
    nlp.ask("De quoi souffre <http://evil> ; DROP ALL")
    assert count(nlp) == n


def test_api_endpoint(fresh):
    r = fresh.post("/api/sante/nlp/ask", json={"question": "Combien de patients enfants ?"})
    assert r.status_code == 200 and r.json()["message"] == "Réponse : 3."
    assert len(fresh.get("/api/sante/nlp/exemples").json()) >= 10
    assert fresh.post("/api/sante/nlp/ask", json={"question": ""}).status_code == 422
