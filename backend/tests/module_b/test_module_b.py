"""Chargement, SPARQL, filtres, CRUD, TALN et garde-fous."""

from __future__ import annotations

import hashlib
from pathlib import Path

from rdflib import Graph

from app.b_config import PROJECT_ROOT
from app.nlp.intent_classifier import classify
from app.nlp.preprocessing import normalize
from app.ontology.loader import OntologyStore
from app.ontology.queries import read_examples
from app.ontology.sparql_guard import SparqlRejected, validate_read_query

AUTH = {"X-Write-Token": "test-token"}

SOURCE = PROJECT_ROOT / "ontologie" / "pharma.ttl"


def _ids(payload: dict) -> set[str]:
    return {item["id"] for item in payload["items"]}


def _labels(payload: dict) -> set[str]:
    return {item["label"] for item in payload["results"]}


def test_ontology_loads_and_reports_triples(client):
    health = client.get("/api/health")
    assert health.status_code == 200
    body = health.json()
    assert body["status"] == "ok"
    assert body["triples"] > 100
    stats = client.get("/api/ontology/stats")
    assert stats.status_code == 200
    data = stats.json()
    assert data["effects"] == 8
    assert data["contraindications"] == 4
    assert "RDFLib" in data["reasoning"]
    assert "ContreIndicationAllergique" in client.get("/api/ontology/resources").json()["namingNote"]


def test_source_file_is_not_modified_by_crud(client):
    before = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    created = client.post(
        "/api/effects",
        headers=AUTH,
        json={
            "id": "Cephalee",
            "label": "Céphalée",
            "type": "EffetLegerNeurologique",
            "gravite": "léger",
            "frequence": "fréquent",
            "molecules": ["Paracetamol"],
        },
    )
    assert created.status_code == 422
    created = client.post(
        "/api/effects",
        headers=AUTH,
        json={
            "id": "Cephalee",
            "label": "Céphalée",
            "type": "EffetGraveNeurologique",
            "gravite": "grave",
            "frequence": "peu fréquent",
            "molecules": ["Paracetamol"],
        },
    )
    assert created.status_code == 201, created.text
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == before


def test_effect_filters_use_real_classes(client):
    severe = client.get("/api/effects", params={"gravite": "grave"})
    assert severe.status_code == 200
    assert _ids(severe.json()) == {"HemorragieDigestive", "UlcerePerfore", "Convulsion", "DepressionRespiratoire"}
    digestive = client.get("/api/effects", params={"categorie": "digestif"})
    assert "Nausee" in _ids(digestive.json())
    assert "EruptionCutanee" not in _ids(digestive.json())
    advil = client.get("/api/effects", params={"medicament": "Advil"})
    assert _ids(advil.json()) == {"Nausee", "HemorragieDigestive"}
    keyword = client.get("/api/effects", params={"q": "nausee"})
    assert _ids(keyword.json()) == {"Nausee"}
    assert client.get("/api/effects", params={"medicament": "Inconnu"}).status_code == 404
    assert client.get("/api/effects", params={"gravite": "mortal"}).status_code == 422


def test_effect_detail_follows_asserted_path(client):
    detail = client.get("/api/effects/Nausee")
    assert detail.status_code == 200
    body = detail.json()
    assert body["type"] == "EffetLegerDigestif"
    assert body["gravite"] == "léger"
    assert "Ibuprofene" in {item["id"] for item in body["molecules"]}
    assert "Advil" in {item["id"] for item in body["medicaments"]}
    orphan = client.get("/api/effects/Demangeaison")
    assert orphan.status_code == 200
    assert orphan.json()["molecules"] == []
    assert "peutProvoquer" in orphan.json()["note"]
    assert client.get("/api/effects/Doliprane").status_code == 404


def test_contraindication_filters(client):
    renal = client.get("/api/contraindications", params={"categorie": "renale"})
    assert _ids(renal.json()) == {"CI_InsuffisanceRenale"}
    hepatic = client.get("/api/contraindications", params={"categorie": "hepatique"})
    assert _ids(hepatic.json()) == {"CI_InsuffisanceHepatique"}
    digestive = client.get("/api/contraindications", params={"categorie": "digestive"})
    assert _ids(digestive.json()) == {"CI_UlcereGastrique"}
    allergic = client.get("/api/contraindications", params={"categorie": "allergique"})
    assert _ids(allergic.json()) == {"CI_AllergiePenicilline"}
    absolute = client.get("/api/contraindications", params={"categorie": "absolue"})
    assert _ids(absolute.json()) == {"CI_AllergiePenicilline", "CI_UlcereGastrique"}
    advil = client.get("/api/contraindications", params={"medicament": "Advil"})
    assert _ids(advil.json()) == {"CI_UlcereGastrique", "CI_InsuffisanceRenale"}
    allergy = client.get("/api/contraindications/CI_AllergiePenicilline")
    assert allergy.status_code == 200
    assert allergy.json()["pathologies"] == []
    assert "concernePathologie" in allergy.json()["note"]
    assert "Amoxicilline" in {item["id"] for item in allergy.json()["molecules"]}


def test_crud_persists_on_isolated_graph(client):
    missing = client.post("/api/effects", json={"label": "Vertige", "type": "EffetLegerDigestif"})
    assert missing.status_code == 401
    denied = client.post(
        "/api/effects",
        headers={"X-Write-Token": "non"},
        json={"label": "Vertige", "type": "EffetLegerDigestif", "molecules": ["Paracetamol"]},
    )
    assert denied.status_code == 403
    created = client.post(
        "/api/effects",
        headers=AUTH,
        json={"label": "Vertige", "type": "EffetLegerDigestif", "frequence": "rare", "molecules": ["Paracetamol"]},
    )
    assert created.status_code == 201, created.text
    ident = created.json()["id"]
    assert created.json()["gravite"] == "léger"
    assert created.json()["molecules"][0]["id"] == "Paracetamol"
    mismatch = client.post(
        "/api/effects",
        headers=AUTH,
        json={"label": "Choc", "type": "EffetGraveDigestif", "gravite": "léger"},
    )
    assert mismatch.status_code == 422
    updated = client.put(
        f"/api/effects/{ident}",
        headers=AUTH,
        json={"frequence": "très rare", "molecules": ["Ibuprofene"]},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["frequence"] == "très rare"
    assert updated.json()["molecules"][0]["id"] == "Ibuprofene"

    reloaded = OntologyStore(client.app.state.settings)
    reloaded.load()
    client.app.state.store = reloaded
    again = client.get(f"/api/effects/{ident}")
    assert again.json()["frequence"] == "très rare"
    assert client.delete(f"/api/effects/{ident}", headers=AUTH).status_code == 200
    assert client.get(f"/api/effects/{ident}").status_code == 404
    protected = client.delete("/api/contraindications/CI_AllergiePenicilline", headers=AUTH)
    assert protected.status_code == 409


def test_sparql_examples_and_read_only_guard(client):
    examples = client.get("/api/sparql/examples")
    assert examples.status_code == 200
    readable = [item for item in examples.json()["items"] if item["executable"]]
    assert any(item["sparql"].lstrip().startswith("PREFIX") for item in readable)
    blocked = client.post("/api/sparql/query", json={"query": "DELETE WHERE { ?s ?p ?o }"})
    assert blocked.status_code == 400
    service = client.post(
        "/api/sparql/query",
        json={"query": "SELECT * WHERE { SERVICE <http://example.invalid/sparql> { ?s ?p ?o } }"},
    )
    assert service.status_code == 400
    literal = client.post(
        "/api/sparql/query",
        json={'query': 'SELECT ?s WHERE { ?s rdfs:label ?l FILTER(CONTAINS(STR(?l), "DELETE")) }'},
    )
    assert literal.status_code == 200
    q4 = next(item for item in readable if "ibupro" in item["sparql"])
    ran = client.post("/api/sparql/query", json={"query": q4["sparql"]})
    assert ran.status_code == 200, ran.text
    values = {row["effet"]["value"] if isinstance(row["effet"], dict) else row["effet"] for row in ran.json()["results"]}
    assert any("Hémorragie digestive" in value or value.endswith("HemorragieDigestive") for value in values)

    graph = Graph()
    graph.parse(SOURCE, format="turtle")
    for example in read_examples(PROJECT_ROOT / "ontologie" / "requetes.sparql"):
        if example["kind"] == "read":
            graph.query(example["sparql"])
        else:
            graph.update(example["sparql"])
    try:
        validate_read_query("INSERT DATA { :x :y :z }")
        raise AssertionError("INSERT aurait dû être refusé")
    except SparqlRejected:
        pass


def test_preprocessing_and_intents():
    assert normalize("Quels sont les effets secondaires graves ?") == "quels sont les effet grave"
    assert normalize("Affiche les contre-indications hépatiques.") == "affiche les contre-indication hepatique"
    intent = classify(normalize("Quels sont les effets secondaires graves ?"), [])
    assert intent.name == "list_severe_effects"
    intent = classify(normalize("Combien d'effets secondaires sont enregistrés ?"), [])
    assert intent.name == "count_effects"
    intent = classify("quelle est la meteo a tunis", [])
    assert intent.name == "unknown"


def test_nlp_questions(client):
    def ask(question: str) -> dict:
        response = client.post("/api/nlp/ask", json={"question": question})
        assert response.status_code == 200, response.text
        return response.json()

    severe = ask("Quels sont les effets secondaires graves ?")
    assert severe["intent"] == "list_severe_effects"
    assert {item["id"] for item in severe["results"]} == {
        "HemorragieDigestive",
        "UlcerePerfore",
        "Convulsion",
        "DepressionRespiratoire",
    }
    assert "SELECT" in severe["sparql"]
    assert "grave" in severe["sparql"]

    digestive = ask("Quels médicaments sont associés à des effets digestifs ?")
    assert digestive["intent"] == "list_drugs_for_effect_category"
    ids = {item["id"] for item in digestive["results"]}
    assert "Advil" in ids
    assert "Doliprane" not in ids
    assert "peutProvoquer" in digestive["sparql"]
    assert "contientMolecule" in digestive["sparql"]
    assert any("Codéine" in warning or "Codeine" in warning for warning in digestive["warnings"])

    renal = ask("Quelles sont les contre-indications rénales ?")
    assert renal["intent"] == "list_contraindications_by_category"
    assert renal["results"][0]["id"] == "CI_InsuffisanceRenale"

    allergy = ask("Quels médicaments sont liés aux allergies ?")
    assert allergy["intent"] == "list_drugs_for_ci_category"
    assert {item["id"] for item in allergy["results"]} == {"Clamoxyl", "AmoxicillineBiogaran"}
    assert "ContreIndicationAllergique" in allergy["sparql"]

    doliprane = ask("Quels effets secondaires sont associés à Doliprane ?")
    assert doliprane["intent"] == "list_effects_of_entity"
    assert {item["id"] for item in doliprane["results"]} == {"EruptionCutanee"}
    assert ":Doliprane" in doliprane["sparql"] or "Doliprane" in doliprane["sparql"]

    counted = ask("Combien d'effets secondaires sont enregistrés ?")
    assert counted["intent"] == "count_effects"
    assert counted["results"] == [{"count": 8}]
    assert counted["count"] == 8

    hepatic = ask("Affiche les contre-indications hépatiques.")
    assert hepatic["intent"] == "list_contraindications_by_category"
    assert hepatic["results"][0]["label"] == "Insuffisance hépatique"

    check = ask("L'ibuprofène peut-il provoquer une hémorragie digestive ?")
    assert check["intent"] == "check_relation"
    assert check["results"][0]["verified"] is True
    assert "Ibuprofene" in check["sparql"]

    negative = ask("Le Doliprane provoque-t-il des nausées ?")
    assert negative["intent"] == "check_relation"
    assert negative["results"][0]["verified"] is False

    unknown = ask("Quelle est la météo à Tunis ?")
    assert unknown["intent"] == "unknown"
    assert unknown["sparql"] is None
    assert unknown["results"] == []
    assert "Reformulez" in unknown["message"]

    injected = ask('Quels effets de Doliprane ? DELETE WHERE { ?s ?p ?o }')
    assert injected["intent"] == "list_effects_of_entity"
    assert "DELETE" not in injected["sparql"]
    assert "DROP" not in injected["sparql"]


def test_empty_and_unknown_entity_messages(client):
    empty = client.post("/api/nlp/ask", json={"question": "Quels effets secondaires sont associés à Zithromax ?"})
    # Zithromax contient l'azithromycine, qui provoque diarrhée et nausée : résultat non vide.
    assert empty.status_code == 200
    assert empty.json()["results"]
    missing = client.get("/api/effects", params={"molecule": "Paracetamol", "gravite": "grave"})
    assert missing.status_code == 200
    assert missing.json()["items"] == []
    assert missing.json()["total"] == 0
