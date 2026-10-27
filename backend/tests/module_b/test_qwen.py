"""Qwen2.5 3B Instruct : extraction SPARQL, garde-fou, exécution et repli."""

from app.nlp.qwen import QwenUnavailable, extract_sparql
from app.ontology.sparql_guard import SparqlRejected, validate_read_query


SEVERE = """
PREFIX : <http://example.org/pharma#>
PREFIX rdfs: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
SELECT ?effet ?label WHERE {
  ?effet a ?type ;
         rdfs:label ?label ;
         :niveauGravite ?gravite .
  ?type rdfs:subClassOf* :EffetSecondaire .
  FILTER(isIRI(?type))
  FILTER(STR(?gravite) = "grave")
}
"""


def test_extract_sparql_from_fence_and_refusal():
    assert "SELECT" in extract_sparql(f"```sparql\n{SEVERE}\n```")
    assert extract_sparql("AUCUNE") is None
    assert extract_sparql("```sparql\nAUCUNE\n```") is None


def test_write_query_is_rejected():
    try:
        validate_read_query("DELETE WHERE { ?s ?p ?o }")
        raise AssertionError("DELETE aurait dû être refusé")
    except SparqlRejected:
        pass


def test_qwen_select_is_executed(client, monkeypatch):
    client.app.state.settings.nlp_engine = "qwen"

    def fake_generate(settings, question, graph):
        return SEVERE

    monkeypatch.setattr("app.nlp.qwen.generate_sparql", fake_generate)
    response = client.post("/api/nlp/ask", json={"question": "Quels sont les effets secondaires graves ?"})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["intent"] == "qwen_sparql"
    assert body["analysis"]["analyzer"] == "qwen2.5:3b"
    assert {item["id"] for item in body["results"]} == {
        "HemorragieDigestive",
        "UlcerePerfore",
        "Convulsion",
        "DepressionRespiratoire",
    }


def test_qwen_delete_falls_back_to_rules(client, monkeypatch):
    client.app.state.settings.nlp_engine = "qwen"
    monkeypatch.setattr(
        "app.nlp.qwen.generate_sparql",
        lambda settings, question, graph: "DELETE WHERE { ?s ?p ?o }",
    )
    response = client.post("/api/nlp/ask", json={"question": "Quels sont les effets secondaires graves ?"})
    body = response.json()
    assert body["intent"] == "list_severe_effects"
    assert "refusée" in body["warnings"][0]
    assert "DELETE" not in (body["sparql"] or "")


def test_missing_ollama_uses_rules(client, monkeypatch):
    client.app.state.settings.nlp_engine = "qwen"

    def missing(settings, question, graph):
        raise QwenUnavailable("Ollama ne répond pas.")

    monkeypatch.setattr("app.nlp.qwen.generate_sparql", missing)
    response = client.post("/api/nlp/ask", json={"question": "Quelle est la météo à Tunis ?"})
    body = response.json()
    assert body["intent"] == "unknown"
    assert body["sparql"] is None
    assert "Ollama" in body["warnings"][0]
