"""Tests du module D (Prescription + Donnée clinique) : ontologie, SPARQL, filtres, CRUD, persistance, sécurité."""
import hashlib
import os
from datetime import date, timedelta
from pathlib import Path

import pytest

ORIGINAL_ONTOLOGY = Path(__file__).resolve().parents[3] / "ontologie" / "pharma.ttl"


def ids(rows):
    return {r["id"] for r in rows}


def get(client, url, **params):
    r = client.get(url, params=params)
    assert r.status_code == 200, r.text
    return r.json()["data"]


# ---------- Chargement de l'ontologie ----------
def test_ontologie_chargee(client):
    d = get(client, "/api/module-d/ontologie")
    assert d["graphe"]["triplets_declares"] >= 965 and d["graphe"]["triplets_inferes"] > 0
    modules = {m["classe"]: m["individus"] for m in d["modules"]}
    assert modules["Prescription"] == 4 and modules["DonneeClinique"] == 6
    assert d["espacesDeNoms"][""] == "http://example.org/pharma#"


def test_tests_sur_copie_et_original_intact():
    from app import config
    assert config.ONTOLOGY_PATH.resolve() != ORIGINAL_ONTOLOGY.resolve()
    assert hashlib.sha256(ORIGINAL_ONTOLOGY.read_bytes()).hexdigest() == os.environ["ORIGINAL_ONTOLOGY_SHA256"]


def test_referentiels(client):
    ref = get(client, "/api/module-d/referentiels")
    assert ids(ref["patients"]) == {"Patient_Ali", "Patient_Sara", "Patient_Youssef", "Patient_Lina"}
    assert ids(ref["medecins"]) == {"Dr_Benali", "Dr_Trabelsi"}
    assert ids(ref["typesPrescription"]) == {"PrescriptionSimple", "PrescriptionRenouvelable", "PrescriptionNormale",
                                             "PrescriptionUrgente", "RenouvellementCourt", "RenouvellementLong"}
    assert ids(ref["typesDonnee"]) == {"ExamenClinique", "HistoriqueMedical", "SigneVital", "AnalyseBiologique", "Allergie", "Antecedent"}


# ---------- Prescriptions : liste, filtres, tri, pagination ----------
def test_liste_pagination_et_tri(client):
    d = get(client, "/api/prescriptions", tri="date")
    assert d["total"] == 4 and [p["id"] for p in d["elements"]] == ["Presc_001", "Presc_002", "Presc_003", "Presc_004"]
    page2 = get(client, "/api/prescriptions", tri="date_desc", taille=3, page=2)
    assert page2["pages"] == 2 and [p["id"] for p in page2["elements"]] == ["Presc_001"]
    assert client.get("/api/prescriptions", params={"tri": "inconnu"}).status_code == 400


def test_filtre_type_utilise_l_inference(client):
    # Presc_001 / Presc_004 sont déclarées RenouvellementLong / RenouvellementCourt : la catégorie est déduite.
    assert ids(get(client, "/api/prescriptions", type="PrescriptionRenouvelable")["elements"]) == {"Presc_001", "Presc_004"}
    assert ids(get(client, "/api/prescriptions", type="PrescriptionSimple")["elements"]) == {"Presc_002", "Presc_003"}
    assert client.get("/api/prescriptions", params={"type": "Inconnu"}).status_code == 400


def test_filtre_periode(client):
    assert ids(get(client, "/api/prescriptions", dateMin="2026-10-01", dateMax="2026-10-15")["elements"]) == {"Presc_002", "Presc_003"}
    assert get(client, "/api/prescriptions", dateMax="2020-01-01")["total"] == 0  # résultat vide, pas une erreur
    assert client.get("/api/prescriptions", params={"dateMin": "12/10/2026"}).status_code == 422
    assert client.get("/api/prescriptions", params={"dateMin": "2026-10-20", "dateMax": "2026-10-01"}).status_code == 400


def test_filtres_relations_et_recherche(client):
    assert ids(get(client, "/api/prescriptions", medecin="Dr_Trabelsi")["elements"]) == {"Presc_004"}
    assert ids(get(client, "/api/prescriptions", patient="Patient_Youssef")["elements"]) == {"Presc_003"}
    assert ids(get(client, "/api/prescriptions", medicament="Advil")["elements"]) == {"Presc_003"}
    assert ids(get(client, "/api/prescriptions", pharmacien="Ph_Mansour")["elements"]) == {"Presc_001", "Presc_003"}
    assert ids(get(client, "/api/prescriptions", q="glucophage")["elements"]) == {"Presc_001"}
    assert get(client, "/api/prescriptions", q='") } ; DROP ALL #')["total"] == 0  # échappé : aucun effet
    assert client.get("/api/prescriptions", params={"patient": "Patient_F001"}).status_code == 404
    assert client.get("/api/prescriptions", params={"patient": "Dr_Benali"}).status_code == 404  # mauvaise classe


# ---------- Prescription : fiche, graphe ----------
def test_fiche_prescription(client):
    d = get(client, "/api/prescriptions/Presc_003")
    assert d["patient"]["id"] == "Patient_Youssef" and d["medecin"]["id"] == "Dr_Benali" and d["pharmacien"]["id"] == "Ph_Mansour"
    assert d["datePrescription"] == "2026-10-15" and ids(d["medicaments"]) == {"Advil", "Doliprane"}
    classes = {c["id"]: c["inferee"] for c in d["classes"]}
    assert classes["PrescriptionNormale"] is False and classes["PrescriptionSimple"] is True
    assert ids(d["patient"]["donneesCliniques"]) == {"Tension_Youssef", "Antecedent_Youssef"}
    assert {a["type"] for a in d["alertes"]} == {"contre-indication", "antécédent"}
    assert client.get("/api/prescriptions/Presc_999").status_code == 404
    assert client.get("/api/prescriptions/Presc_001;DROP").status_code == 400


def test_graphe_construct_avec_dossier_clinique(client):
    d = get(client, "/api/prescriptions/Presc_002/graphe")
    rel = {(e["source"], e["relation"], e["cible"]) for e in d["aretes"]}
    assert ("Presc_002", "concernePatient", "Patient_Sara") in rel
    assert ("Patient_Sara", "aDonneeClinique", "Allergie_Sara") in rel
    assert ("Allergie_Sara", "allergiqueA", "Amoxicilline") in rel and ("Clamoxyl", "contientMolecule", "Amoxicilline") in rel


# ---------- Alertes et scénario ----------
def test_alertes_quatre_raisonnements(client):
    alertes = get(client, "/api/prescriptions/alertes")
    par_presc = {}
    for a in alertes:
        par_presc.setdefault(a["prescription"]["id"], set()).add(a["type"])
    assert par_presc == {"Presc_001": {"contre-indication", "analyse"}, "Presc_002": {"allergie"},
                         "Presc_003": {"contre-indication", "antécédent"}}
    assert get(client, "/api/prescriptions/alertes", patient="Patient_Lina") == []


def test_scenario_youssef_ulcere(client):
    d = get(client, "/api/module-d/patients/Patient_Youssef/dossier")
    assert d["danger"] is True and d["contreIndicationDetectee"] is True
    advil = next(m for p in d["prescriptions"] for m in p["medicaments"] if m["id"] == "Advil")
    ibu = next(m for m in advil["molecules"] if m["id"] == "Ibuprofene")
    conflit = [c for c in ibu["contreIndications"] if c["conflit"]]
    assert conflit and conflit[0]["id"] == "CI_UlcereGastrique" and conflit[0]["pathologie"]["id"] == "UlcereGastroduodenal"
    doliprane = next(m for p in d["prescriptions"] for m in p["medicaments"] if m["id"] == "Doliprane")
    assert doliprane["conflit"] is False
    assert {x["type"] for x in d["donneesCliniques"]} == {"SigneVital", "Antecedent"}


def test_scenario_allergie_analyse_et_patient_sans_risque(client):
    sara = get(client, "/api/module-d/patients/Patient_Sara/dossier")
    assert sara["danger"] is True and sara["contreIndicationDetectee"] is False
    amox = sara["prescriptions"][0]["medicaments"][0]["molecules"][0]
    assert amox["id"] == "Amoxicilline" and amox["allergie"] is True
    ali = get(client, "/api/module-d/patients/Patient_Ali/dossier")
    assert any(a["type"] == "analyse" and "38" in a["motif"] for a in ali["alertes"])
    lina = get(client, "/api/module-d/patients/Patient_Lina/dossier")
    assert lina["danger"] is False and lina["alertes"] == [] and lina["donneesCliniques"] == []
    assert client.get("/api/module-d/patients/Dr_Benali/dossier").status_code == 404


# ---------- CRUD prescriptions + persistance ----------
BODY = {"type": "RenouvellementCourt", "datePrescription": "2026-10-25", "dureeJours": 30, "posologie": "1 comprimé le soir",
        "medecin": "Dr_Trabelsi", "patient": "Patient_Lina", "medicaments": ["Doliprane"], "pharmacien": "Ph_Khelifi"}


def test_crud_prescription_et_persistance(fresh):
    from app import config
    from app.graph_store import store
    c = fresh
    r = c.post("/api/prescriptions", json=BODY)
    assert r.status_code == 201, r.text
    d = r.json()["data"]
    assert d["id"] == "Presc_005" and d["estRenouvelable"] is True and d["categorie"] == "PrescriptionRenouvelable"
    assert any(s["requete"].startswith("INSERT DATA") for s in r.json()["sparql"])
    assert "Presc_005" in config.RUNTIME_PATH.read_text(encoding="utf-8")
    store.load()  # rechargement depuis le fichier runtime : la création a bien été sauvegardée
    assert c.get("/api/prescriptions/Presc_005").status_code == 200

    body = {**BODY, "dureeJours": 60, "medicaments": ["Doliprane", "Zithromax"], "pharmacien": None}
    d = c.put("/api/prescriptions/Presc_005", json=body).json()["data"]
    assert d["dureeJours"] == 60 and ids(d["medicaments"]) == {"Doliprane", "Zithromax"} and d["pharmacien"] is None

    assert c.delete("/api/prescriptions/Presc_005").status_code == 200
    assert c.get("/api/prescriptions/Presc_005").status_code == 404
    assert get(c, "/api/prescriptions")["total"] == 4


@pytest.mark.parametrize("patch, status", [
    ({"type": "RenouvellementCourt", "dureeJours": 120}, 422),
    ({"type": "RenouvellementLong", "dureeJours": 30}, 422),
    ({"type": "Prescription"}, 422),
    ({"datePrescription": (date.today() + timedelta(days=3)).isoformat()}, 422),
    ({"datePrescription": "2026-13-40"}, 422),
    ({"medicaments": []}, 422),
    ({"medicaments": ["Advil", "Advil"]}, 422),
    ({"medecin": "Dr_Inconnu"}, 404),
    ({"medecin": "Patient_Ali"}, 404),
    ({"patient": "Patient_Ali> } ; DROP ALL ; #"}, 422),
    ({"pharmacien": "Dr_Benali"}, 404),
])
def test_validation_prescription(client, patch, status):
    assert client.post("/api/prescriptions", json={**BODY, **patch}).status_code == status


# ---------- Données cliniques ----------
def test_liste_donnees_filtres(client):
    d = get(client, "/api/donnees-cliniques")
    assert d["total"] == 6
    assert ids(get(client, "/api/donnees-cliniques", type="ExamenClinique")["elements"]) == {
        "Glycemie_Ali", "Creatinine_Ali", "Tension_Youssef", "Temperature_Sara"}  # via la hiérarchie
    assert ids(get(client, "/api/donnees-cliniques", type="HistoriqueMedical")["elements"]) == {"Allergie_Sara", "Antecedent_Youssef"}
    assert ids(get(client, "/api/donnees-cliniques", patient="Patient_Ali")["elements"]) == {"Glycemie_Ali", "Creatinine_Ali"}
    assert ids(get(client, "/api/donnees-cliniques", dateMin="2026-10-01")["elements"]) == {"Tension_Youssef", "Temperature_Sara"}
    assert ids(get(client, "/api/donnees-cliniques", q="amoxicilline")["elements"]) == {"Allergie_Sara"}
    assert get(client, "/api/donnees-cliniques", tri="date_desc", taille=2)["pages"] == 3
    assert client.get("/api/donnees-cliniques", params={"type": "Patient"}).status_code == 400


def test_fiche_donnee(client):
    d = get(client, "/api/donnees-cliniques/Creatinine_Ali")
    assert d["valeur"] == 38 and d["unite"] == "mL/min" and d["dateMesure"] == "2026-09-01" and d["patient"]["id"] == "Patient_Ali"
    classes = {c["id"]: c["inferee"] for c in d["classes"]}
    assert classes["AnalyseBiologique"] is False and classes["ExamenClinique"] is True and classes["DonneeClinique"] is True
    a = get(client, "/api/donnees-cliniques/Antecedent_Youssef")
    assert a["pathologie"]["id"] == "UlcereGastroduodenal" and a["valeur"] is None
    assert client.get("/api/donnees-cliniques/Presc_001").status_code == 404


DONNEE = {"type": "AnalyseBiologique", "patient": "Patient_Youssef", "libelle": "Glycémie à jeun",
          "dateMesure": "2026-10-15", "valeur": 1.05, "unite": "g/L"}


def test_crud_donnee_clinique(fresh):
    c = fresh
    r = c.post("/api/donnees-cliniques", json=DONNEE)
    assert r.status_code == 201, r.text
    d = r.json()["data"]
    assert d["id"] == "Glycemie_Youssef" and d["valeur"] == 1.05
    assert c.post("/api/donnees-cliniques", json=DONNEE).json()["data"]["id"] == "Glycemie_Youssef2"
    d = c.put("/api/donnees-cliniques/Glycemie_Youssef", json={**DONNEE, "valeur": 1.2}).json()["data"]
    assert d["valeur"] == 1.2
    assert c.delete("/api/donnees-cliniques/Glycemie_Youssef").status_code == 200
    assert c.get("/api/donnees-cliniques/Glycemie_Youssef").status_code == 404

    # Une allergie créée est immédiatement prise en compte par les alertes (Lina reçoit du Zithromax → azithromycine).
    allergie = {"type": "Allergie", "patient": "Patient_Lina", "libelle": "Allergie à l'azithromycine",
                "dateMesure": "2025-01-10", "molecule": "Azithromycine"}
    a = c.post("/api/donnees-cliniques", json=allergie).json()["data"]
    assert a["id"] == "Allergie_Lina"
    alertes = get(c, "/api/prescriptions/alertes", patient="Patient_Lina")
    assert [(x["prescription"]["id"], x["type"]) for x in alertes] == [("Presc_004", "allergie")]


@pytest.mark.parametrize("patch, status", [
    ({"type": "Allergie"}, 422),                                  # allergie sans molécule, avec valeur
    ({"type": "SigneVital", "valeur": None}, 422),               # examen sans valeur
    ({"molecule": "Amoxicilline"}, 422),                          # allergiqueA hors domaine
    ({"type": "Antecedent", "valeur": None, "unite": None}, 422),  # antécédent sans pathologie
    ({"type": "Patient"}, 422),
    ({"dateMesure": (date.today() + timedelta(days=1)).isoformat()}, 422),
    ({"patient": "Dr_Benali"}, 404),
    ({"type": "Allergie", "valeur": None, "unite": None, "molecule": "Advil"}, 404),  # Advil n'est pas une :Molecule
    ({"type": "Antecedent", "valeur": None, "unite": None, "pathologie": "Inconnue"}, 404),
])
def test_validation_donnee(client, patch, status):
    assert client.post("/api/donnees-cliniques", json={**DONNEE, **patch}).status_code == status


# ---------- Statistiques, catalogue SPARQL, requêtes contrôlées ----------
def test_statistiques(client):
    d = get(client, "/api/prescriptions/statistiques")
    assert d["totaux"]["prescriptions"] == 4 and d["totaux"]["donneesCliniques"] == 6 and d["totaux"]["alertes"] == 3
    assert {r["type"]: r["nombre"] for r in d["donneesParType"]} == {"SigneVital": 2, "AnalyseBiologique": 2, "Allergie": 1, "Antecedent": 1}


def test_catalogue_module_d_executable(client):
    cat = get(client, "/api/module-d/requetes")
    assert len(cat) >= 18
    kinds = set()
    for q in cat:
        r = client.post(f"/api/module-d/requetes/{q['nom']}/executer")
        if not q["lectureSeule"]:
            assert r.status_code == 400
            continue
        assert r.status_code == 200, (q["nom"], r.text)
        kinds.add(r.json()["data"]["type"])
    assert kinds == {"select", "ask", "graphe"}


def test_requetes_cles(client):
    rows = client.post("/api/module-d/requetes/D01_prescriptions_par_type/executer").json()["data"]["lignes"]
    assert {r["prescription"] for r in rows} == {"Presc_001", "Presc_004"}
    rows = client.post("/api/module-d/requetes/D14_clairance_basse/executer").json()["data"]["lignes"]
    assert [(r["patient"], r["valeur"]) for r in rows] == [("Patient_Ali", 38)]


@pytest.mark.parametrize("requete, ok", [
    ("SELECT ?p WHERE { ?p a :Prescription }", True),
    ("ASK { :Allergie_Sara :allergiqueA :Amoxicilline }", True),
    ("CONSTRUCT { ?d :estDonneeDe ?p } WHERE { ?d :estDonneeDe ?p }", True),
    ("INSERT DATA { :X a :Prescription }", False),
    ("DELETE WHERE { ?s ?p ?o }", False),
    ("delete\twhere { ?s ?p ?o }", False),
    ("DROP ALL", False),
    ("LOAD <http://example.com/x.ttl>", False),
    ("SELECT * WHERE { SERVICE\t<http://dbpedia.org/sparql> { ?s ?p ?o } }", False),
    ("SELECT * FROM <http://example.com/g.ttl> WHERE { ?s ?p ?o }", False),
    ("DESCRIBE :Presc_001", False),
    ("SELECT ?x WHERE { ?x", False),
])
def test_sparql_controle(client, requete, ok):
    before = client.get("/api/health").json()["triplets_declares"]
    r = client.post("/api/module-d/sparql", json={"requete": requete})
    assert (r.status_code == 200) is ok, r.text
    assert client.get("/api/health").json()["triplets_declares"] == before


def test_sparql_controle_limite(client):
    d = client.post("/api/module-d/sparql", json={"requete": "SELECT ?s ?p ?o WHERE { ?s ?p ?o }", "limite": 10}).json()["data"]
    assert len(d["lignes"]) == 10 and d["tronque"] is True
