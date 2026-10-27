"""Tests d'intégration de l'API (TestClient + rdflib en mémoire, sans Fuseki)."""
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def api(repo):
    app.state.repo = repo
    with TestClient(app) as c:
        yield c


def test_health(api):
    r = api.get("/api/health")
    assert r.status_code == 200 and r.json()["status"] == "ok" and r.json()["triples"] > 400


def test_patients_crud_flow(api):
    r = api.get("/api/patients", params={"limit": 5})
    assert r.status_code == 200 and r.json()["total"] == 11 and len(r.json()["items"]) == 5

    r = api.post("/api/patients", json={"prenom": "Yassine", "nom": "Kefi", "age": 12, "sexe": "M",
                                        "pathologies": ["Asthme"]})
    assert r.status_code == 404  # pathologie inexistante → rien n'est créé
    r = api.post("/api/patients", json={"prenom": "Yassine", "nom": "Kefi", "age": 12, "sexe": "M",
                                        "pathologies": ["Otite"]})
    assert r.status_code == 201 and r.json() == {"id": "Patient_Yassine"}
    assert api.post("/api/patients", json={"prenom": "Yassine", "nom": "X", "age": 3, "sexe": "M"}).status_code == 409

    detail = api.get("/api/patients/Patient_Yassine").json()
    assert detail["classe"] == "PatientEnfant" and detail["asserte"] is False

    r = api.patch("/api/patients/Patient_Yassine", json={"age": 19})
    assert r.status_code == 200 and r.json()["classe"] == "PatientAdulte"

    assert api.delete("/api/patients/Patient_Yassine").status_code == 204
    assert api.get("/api/patients/Patient_Yassine").status_code == 404


def test_validation_errors_are_uniform(api):
    r = api.post("/api/patients", json={"prenom": "A", "nom": "B", "age": 150, "sexe": "X"})
    body = r.json()
    assert r.status_code == 422 and body["code"] == "validation_error"
    assert {d["champ"] for d in body["details"]} == {"age", "sexe"}
    r = api.post("/api/pathologies", json={"label": "Grippe", "type": "InfectionAigue", "code": "grippe"})
    assert r.status_code == 422
    assert api.get("/api/patients/Patient_Ali%3E%20%3Fp").status_code == 422


def test_delete_referenced_returns_409_with_reason(api):
    r = api.delete("/api/patients/Patient_Ali")
    assert r.status_code == 409 and r.json()["code"] == "conflict" and r.json()["details"]
    assert api.delete("/api/pathologies/DiabeteType2").status_code == 409
    assert api.delete("/api/medecins/Dr_Benali").status_code == 409


def test_live_alert_on_lina(api):
    assert len(api.get("/api/alertes").json()) == 3
    r = api.post("/api/patients/Patient_Lina/pathologies/InsuffisanceHepatique")
    assert r.status_code == 200 and len(r.json()["alertes"]) == 1
    assert len(api.get("/api/alertes").json()) == 4
    api.delete("/api/patients/Patient_Lina/pathologies/InsuffisanceHepatique")
    assert len(api.get("/api/alertes").json()) == 3


def test_pathologies_and_professionals(api):
    r = api.get("/api/pathologies", params={"famille": "MaladieChronique", "limit": 100})
    assert r.json()["total"] == 10
    r = api.post("/api/pathologies", json={"label": "Grippe", "type": "InfectionAigue", "code": "J11"})
    assert r.status_code == 201
    d = api.get("/api/pathologies/InsuffisanceRenale").json()
    assert {m["id"] for m in d["contreIndiques"]} == {"Advil", "IbuprofeneMylan", "Glucophage"}
    r = api.post("/api/medecins", json={"nom": "Saidi", "specialite": "Dermatologie"})
    assert r.status_code == 201 and r.json()["id"] == "Dr_Saidi"
    assert api.get("/api/medecins/Dr_Saidi").json()["label"] == "Dr Saidi"
    assert api.get("/api/pharmaciens/Dr_Saidi").status_code == 404  # bonne classe exigée
    assert api.get("/api/pharmaciens").json()["total"] == 3


def test_stats_search_graph_rdf(api):
    assert api.get("/api/stats").json()["alertes"] == 3
    assert {x["id"] for x in api.get("/api/search", params={"q": "cardiaque"}).json()} >= {"InsuffisanceCardiaque"}
    g = api.get("/api/graph/Patient_Ali").json()
    assert {"souffreDe", "concernePatient"} <= {e["prop"] for e in g["edges"]}
    r = api.get("/api/patients/Patient_Sara/rdf")
    assert r.headers["content-type"].startswith("text/turtle") and "Jlassi" in r.text


def test_sparql_console_is_read_only(api):
    r = api.post("/api/sparql", json={"query": "PREFIX : <http://example.org/pharma#> "
                                               "SELECT ?p WHERE { ?p a :Medecin }"})
    assert r.status_code == 200 and len(r.json()["rows"]) == 5
    r = api.post("/api/sparql", json={"query": "PREFIX : <http://example.org/pharma#> ASK { :Patient_Sara :age 9 }"})
    assert r.json()["boolean"] is True
    for update in ["DELETE WHERE { ?s ?p ?o }", "INSERT DATA { <a> <b> <c> }", "DROP ALL",
                   "# commentaire\nCLEAR DEFAULT"]:
        r = api.post("/api/sparql", json={"query": update})
        assert r.status_code == 400
    assert api.get("/api/health").json()["triples"] > 400
    assert api.post("/api/sparql", json={"query": "SELEC oops"}).status_code == 400
