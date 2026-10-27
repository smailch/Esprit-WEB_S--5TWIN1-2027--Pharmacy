import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.nlp.evaluation import evaluate
from app.nlp.intent import load_dataset
from app.nlp.pipeline import NlpPipeline


@pytest.fixture(scope="module")
def nlp(base_client):
    base_client.reset()
    return NlpPipeline(base_client)


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
    from app.services.repository import Repository
    nlp.client.reset()
    Repository(nlp.client).create_patient("Yassine", "Kefi", 10, "M", ["Otite"])
    out = nlp.ask("De quoi souffre Yassine Kefi ?")
    assert out["compris"] and out["resultat"]["rows"][0]["pathologie"] == "Otite moyenne aiguë"


def test_injection_in_question_is_harmless(nlp):
    nlp.client.reset()
    n = nlp.client.select("SELECT (COUNT(*) AS ?n) WHERE { ?s ?p ?o }").rows[0]["n"]
    nlp.ask('Quels patients souffrent de "} DELETE WHERE { ?s ?p ?o } # diabète')
    nlp.ask("De quoi souffre <http://evil> ; DROP ALL")
    assert nlp.client.select("SELECT (COUNT(*) AS ?n) WHERE { ?s ?p ?o }").rows[0]["n"] == n


def test_api_endpoint(repo, nlp):
    app.state.repo = repo
    with TestClient(app) as c:
        r = c.post("/api/nlp/ask", json={"question": "Combien de patients enfants ?"})
        assert r.status_code == 200 and r.json()["message"] == "Réponse : 3."
        assert len(c.get("/api/nlp/exemples").json()) >= 10
        assert c.post("/api/nlp/ask", json={"question": ""}).status_code == 422
