"""Tests d'intégration de l'API du module Pathologie + Personne (TestClient sur l'application commune)."""


def test_patients_crud_flow(fresh):
    api = fresh
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
    r = api.get("/api/patients/Patient_Yassine")
    assert r.status_code == 404 and r.json()["code"] == "not_found"


def test_validation_errors(fresh):
    r = fresh.post("/api/patients", json={"prenom": "A", "nom": "B", "age": 150, "sexe": "X"})
    assert r.status_code == 422
    assert {e["loc"][-1] for e in r.json()["detail"]} == {"age", "sexe"}
    r = fresh.post("/api/pathologies", json={"label": "Grippe", "type": "InfectionAigue", "code": "grippe"})
    assert r.status_code == 422
    assert fresh.get("/api/patients/Patient_Ali%3E%20%3Fp").status_code == 422


def test_delete_referenced_returns_409_with_reason(fresh):
    r = fresh.delete("/api/patients/Patient_Ali")
    assert r.status_code == 409 and r.json()["code"] == "conflict" and r.json()["details"]
    assert fresh.delete("/api/pathologies/DiabeteType2").status_code == 409
    assert fresh.delete("/api/medecins/Dr_Benali").status_code == 409


def test_live_alert_on_lina(fresh):
    assert len(fresh.get("/api/alertes").json()) == 3
    r = fresh.post("/api/patients/Patient_Lina/pathologies/InsuffisanceHepatique")
    assert r.status_code == 200 and len(r.json()["alertes"]) == 1
    assert len(fresh.get("/api/alertes").json()) == 4
    fresh.delete("/api/patients/Patient_Lina/pathologies/InsuffisanceHepatique")
    assert len(fresh.get("/api/alertes").json()) == 3


def test_pathologies_and_professionals(fresh):
    r = fresh.get("/api/pathologies", params={"famille": "MaladieChronique", "limit": 100})
    assert r.json()["total"] == 10
    r = fresh.post("/api/pathologies", json={"label": "Grippe", "type": "InfectionAigue", "code": "J11"})
    assert r.status_code == 201
    d = fresh.get("/api/pathologies/InsuffisanceRenale").json()
    assert {m["id"] for m in d["contreIndiques"]} == {"Advil", "IbuprofeneMylan", "Glucophage"}
    r = fresh.post("/api/medecins", json={"nom": "Saidi", "specialite": "Dermatologie"})
    assert r.status_code == 201 and r.json()["id"] == "Dr_Saidi"
    assert fresh.get("/api/medecins/Dr_Saidi").json()["label"] == "Dr Saidi"
    assert fresh.get("/api/pharmaciens/Dr_Saidi").status_code == 404  # bonne classe exigée
    assert fresh.get("/api/pharmaciens").json()["total"] == 3


def test_stats_search_graph_rdf(fresh):
    assert fresh.get("/api/sante/stats").json()["alertes"] == 3
    hits = {x["id"] for x in fresh.get("/api/sante/recherche", params={"q": "cardiaque"}).json()}
    assert "InsuffisanceCardiaque" in hits
    g = fresh.get("/api/sante/graphe/Patient_Ali").json()
    assert {"souffreDe", "concernePatient"} <= {e["prop"] for e in g["edges"]}
    r = fresh.get("/api/patients/Patient_Sara/rdf")
    assert r.headers["content-type"].startswith("text/turtle") and "Jlassi" in r.text


def test_shared_graph_with_module_a(fresh):
    """Un seul graphe : un patient créé ici est visible par la console SPARQL commune, et reset vaut pour tous."""
    fresh.post("/api/patients", json={"prenom": "Yassine", "nom": "Kefi", "age": 12, "sexe": "M"})
    r = fresh.post("/api/sparql", json={"requete": "ASK { :Patient_Yassine :age 12 }"})
    assert r.json()["data"]["resultat"] is True
    fresh.post("/api/admin/reset")
    assert fresh.get("/api/patients/Patient_Yassine").status_code == 404
