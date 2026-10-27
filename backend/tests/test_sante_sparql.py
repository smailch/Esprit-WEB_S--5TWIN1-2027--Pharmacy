import pytest

from app.modules.pathologie_personne.service import Conflict, NotFound
from app.modules.pathologie_personne.templates import QUERIES, InvalidParam, render


def count_triples(sq):
    return sq.select("SELECT (COUNT(*) AS ?n) WHERE { ?s ?p ?o }").rows[0]["n"]


@pytest.mark.parametrize("name", sorted(QUERIES))
def test_every_named_query_runs_with_its_example(sq, name):
    q = QUERIES[name]
    assert q.objectif and q.categorie, f"{name} : en-tête incomplet"
    text = render(name, **q.exemple)
    if q.categorie in ("Create", "Update", "Delete"):
        sq.update(text)
    else:
        sq.run(text)


def test_at_least_15_named_queries():
    assert len(QUERIES) >= 15


def test_three_scenario_alerts(repo):
    pairs = {(a["patId"], a["medicament"].split()[0], a["type"]) for a in repo.alertes()}
    assert pairs == {("Patient_Ali", "Glucophage", "contre-indication"),
                     ("Patient_Sara", "Clamoxyl", "allergie"),
                     ("Patient_Youssef", "Advil", "contre-indication")}
    alert_ali = next(a for a in repo.alertes() if a["patId"] == "Patient_Ali")
    assert alert_ali["medecin"] == "Dr Benali" and alert_ali["pharmacien"] == "Pharmacien Mansour"


def test_adding_pathology_to_lina_triggers_zithromax_alert(repo):
    assert repo.alertes(patient="Patient_Lina") == []
    repo.add_patient_pathology("Patient_Lina", "InsuffisanceHepatique")
    alerts = repo.alertes(patient="Patient_Lina")
    assert len(alerts) == 1 and alerts[0]["prescId"] == "Presc_004" and "Zithromax" in alerts[0]["medicament"]


def test_patient_class_is_derived_from_age(repo):
    lina = repo.get_patient("Patient_Lina")
    assert lina["classe"] == "PatientAdulte" and lina["asserte"] is False
    sara = repo.get_patient("Patient_Sara")
    assert sara["classe"] == "PatientEnfant" and sara["asserte"] is True
    pid = repo.create_patient("Yassine", "Test", 12, "M", ["Angine"])
    assert pid == "Patient_Yassine"
    created = repo.get_patient(pid)
    assert created["classe"] == "PatientEnfant" and created["asserte"] is False
    assert [p["id"] for p in created["pathologies"]] == ["Angine"]


def test_create_collision_is_conflict(repo):
    with pytest.raises(Conflict):
        repo.create_patient("Ali", "Autre", 40, "M")


def test_filters_and_pagination(repo):
    items, total = repo.list_patients(age_min=60)
    assert {p["id"] for p in items} == {"Patient_Youssef", "Patient_Fatma", "Patient_Hedi"} and total == 3
    items, total = repo.list_patients(classe="PatientEnfant")
    assert {p["id"] for p in items} == {"Patient_Sara", "Patient_Amine", "Patient_Nour"}
    items, total = repo.list_patients(sexe="F", pathologie="Migraine")
    assert [p["id"] for p in items] == ["Patient_Nour"]
    page1, total = repo.list_patients(limit=4, offset=0)
    page2, _ = repo.list_patients(limit=4, offset=4)
    assert total == 11 and len(page1) == 4 and not {p["id"] for p in page1} & {p["id"] for p in page2}
    items, _ = repo.list_pathologies(famille="MaladieChronique", limit=100)
    assert len(items) == 10
    items, _ = repo.list_pathologies(type="InfectionAigue")
    assert len(items) == 5
    items, _ = repo.list_professionnels("Medecin", specialite="pneumo")
    assert [m["id"] for m in items] == ["Dr_Trabelsi"]


def test_search_is_case_and_accent_insensitive(repo):
    ids = {r["id"] for r in repo.search("INSUFFISANCE RENALE")}
    assert "InsuffisanceRenale" in ids
    ids = {r["id"] for r in repo.search("hédi")}
    assert ids == {"Patient_Hedi"}
    assert {r["id"] for r in repo.search("pediatrie")} == {"Dr_Hammami"}


def test_hierarchy_subtypes_included(sq):
    rows = sq.select(render("patients_by_pathology_type", type="MaladieChronique")).rows
    patients = {r["id"] for r in rows}
    assert {"Patient_Ali", "Patient_Youssef", "Patient_Fatma"} <= patients
    assert "Patient_Sara" not in patients


def test_ask_patient_enfant(sq):
    assert sq.ask(render("ask_patient_enfant", s="Patient_Sara")) is True
    assert sq.ask(render("ask_patient_enfant", s="Patient_Lina")) is False


def test_update_and_delete(repo):
    repo.update_patient("Patient_Salma", age=17, sexe="F")
    assert repo.get_patient("Patient_Salma")["classe"] == "PatientEnfant"
    repo.update_pathologie("Obesite", code="E66.9")
    assert repo.get_pathologie("Obesite")["code"] == "E66.9"
    repo.delete_patient("Patient_Salma")
    with pytest.raises(NotFound):
        repo.get_patient("Patient_Salma")


def test_delete_refused_when_referenced(repo):
    with pytest.raises(Conflict) as e:
        repo.delete_patient("Patient_Ali")
    assert any(r["relation"] == "concernePatient" for r in e.value.details)
    with pytest.raises(Conflict):
        repo.delete_pathologie("DiabeteType2")
    with pytest.raises(Conflict):
        repo.delete_professionnel("Medecin", "Dr_Benali")
    pid = repo.create_pathologie("Grippe saisonnière", "InfectionAigue", "J11")
    assert pid == "GrippeSaisonniere"
    repo.delete_pathologie(pid)
    repo.delete_professionnel("Medecin", "Dr_Zouari")


def test_stats(repo):
    c = repo.stats()["compteurs"]
    assert c == {"enfants": 3, "adultes": 8, "aigues": 9, "chroniques": 10, "medecins": 5, "pharmaciens": 3}


def test_sparql_injection_is_neutralised(repo, sq):
    before = count_triples(sq)
    evil = 'X" } ; DELETE WHERE { ?s ?p ?o } ; INSERT DATA { <a> <b> "c'
    pid = repo.create_patient("Evil", evil, 30, "M")
    assert repo.get_patient(pid)["nom"] == evil  # stocké comme simple texte
    assert count_triples(sq) == before + 6
    for bad in ["Patient_Ali> ?p ?o } #", "a b", "../x", "Ali;DROP"]:
        with pytest.raises(InvalidParam):
            render("ask_exists", s=bad)
    with pytest.raises(InvalidParam):
        render("create_patient", s="Patient_X", label="x", nom="x", age="1; DROP", sexe="M")
    assert repo.search('" ) } DELETE WHERE { ?s ?p ?o } #') == []
    assert count_triples(sq) == before + 6


def test_console_rejects_updates(sq):
    from app.modules.pathologie_personne.client import SparqlError
    with pytest.raises(SparqlError):
        sq.run("PREFIX : <http://example.org/pharma#> DELETE WHERE { ?s ?p ?o }")
