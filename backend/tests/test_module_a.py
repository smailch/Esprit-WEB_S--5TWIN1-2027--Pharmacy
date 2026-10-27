"""Tests de l'API du module A (Molécule + Médicament) et du catalogue SPARQL."""


def ids(rows):
    return {r["id"] for r in rows}


def test_health(client):
    r = client.get("/api/health").json()
    assert r["statut"] == "ok" and r["triplets_declares"] > 500 and r["triplets_inferes"] > 0


# ---------- Catalogue : chaque requête s'exécute ----------
def test_catalogue_executable(client):
    for q in client.get("/api/requetes").json()["data"]:
        if not q["lectureSeule"]:
            continue
        r = client.post(f"/api/requetes/{q['nom']}/executer")
        assert r.status_code == 200, (q["nom"], r.text)


def test_hierarchie_sans_boucle(client):
    rows = client.post("/api/requetes/Q01_hierarchie_molecules/executer").json()["data"]["lignes"]
    assert all(r["classe"] != r["parent"] for r in rows)
    assert {"Penicilline", "Macrolide", "AntalgiqueOpioide"} <= {r["classe"] for r in rows}


# ---------- Molécules ----------
def test_liste_complete_et_tris(client):
    for tri in ("label", "atc", "dose", "medicaments"):
        rows = client.get("/api/molecules", params={"tri": tri}).json()["data"]
        assert len(rows) == 8, tri
    codeine = next(r for r in rows if r["id"] == "Codeine")
    assert codeine["nbMedicaments"] == 0 and codeine["medicaments"] == []
    for tri in ("label", "prix", "prix_desc"):
        assert len(client.get("/api/medicaments", params={"tri": tri}).json()["data"]) == 9


def test_filtre_classe_via_hierarchie(client):
    rows = client.get("/api/molecules", params={"classe": "Antibiotique"}).json()["data"]
    assert ids(rows) == {"Amoxicilline", "Azithromycine"}


def test_recherche_sans_accent(client):
    rows = client.get("/api/molecules", params={"q": "paracetamol"}).json()["data"]
    assert ids(rows) == {"Paracetamol"}


def test_fiche_molecule_interaction_symetrique(client):
    d = client.get("/api/molecules/Aspirine").json()["data"]
    inter = {i["id"]: i for i in d["interactions"]}
    assert inter["Ibuprofene"]["inferee"] is True  # déclarée seulement dans le sens Ibuprofène → Aspirine
    assert "Aspegic" in ids(d["medicaments"])  # propriété inverse estContenuDans


def test_crud_molecule(fresh):
    c = fresh
    body = {"nom": "Naproxène", "classe": "AntalgiqueNonOpioide", "codeATC": "M01AE02", "doseMaxJourMg": 1100,
            "effets": ["Nausee"], "contreIndications": ["CI_UlcereGastrique"], "interactions": ["Aspirine"]}
    r = c.post("/api/molecules", json=body)
    assert r.status_code == 201, r.text
    assert r.json()["data"]["id"] == "Naproxene"
    assert any(s["requete"].startswith("INSERT DATA") for s in r.json()["sparql"])
    assert c.post("/api/molecules", json=body).status_code == 409

    body["doseMaxJourMg"] = 1000
    d = c.put("/api/molecules/Naproxene", json=body).json()["data"]
    assert d["doseMaxJourMg"] == 1000

    assert c.delete("/api/molecules/Naproxene").status_code == 200
    assert c.get("/api/molecules/Naproxene").status_code == 404


def test_suppression_molecule_utilisee_refusee(client):
    assert client.delete("/api/molecules/Ibuprofene").status_code == 409


def test_validation_molecule(client):
    assert client.post("/api/molecules", json={"nom": "X1", "classe": "Inconnue"}).status_code == 422
    assert client.post("/api/molecules", json={"nom": "Test", "classe": "Molecule", "codeATC": "faux"}).status_code == 422


# ---------- Médicaments ----------
def test_filtres_medicaments(client):
    rows = client.get("/api/medicaments", params={"ordonnance": False, "prixMax": 5}).json()["data"]
    assert ids(rows) == {"Doliprane", "IbuprofeneMylan", "Aspegic"}
    rows = client.get("/api/medicaments", params={"type": "Generique"}).json()["data"]
    assert ids(rows) == {"IbuprofeneMylan", "AmoxicillineBiogaran"}
    rows = client.get("/api/medicaments", params={"molecule": "Amoxicilline"}).json()["data"]
    assert ids(rows) == {"Clamoxyl", "AmoxicillineBiogaran"}


def test_fiche_medicament_contre_indications_deduites(client):
    d = client.get("/api/medicaments/Advil").json()["data"]
    assert {"UlcereGastroduodenal", "InsuffisanceRenale"} <= ids(d["contreIndications"])
    assert d["surOrdonnance"] is False
    assert any(c["id"] == "PrincepsSansOrdonnance" and not c["inferee"] for c in d["classes"])


def test_crud_medicament_et_classement_infere(fresh):
    c = fresh
    body = {"nomCommercial": "Paracétamol Biogaran", "type": "Generique", "dosage": "500 mg", "formeGalenique": "comprimé",
            "surOrdonnance": False, "prixDT": 2.1, "molecules": ["Paracetamol"], "indications": ["Migraine"]}
    r = c.post("/api/medicaments", json=body)
    assert r.status_code == 201, r.text
    d = r.json()["data"]
    classes = {x["id"]: x for x in d["classes"]}
    assert classes["GeneriqueSansOrdonnance"]["inferee"] is True  # classe définie (owl:equivalentClass)

    body["prixDT"] = 1.9
    assert c.put(f"/api/medicaments/{d['id']}", json=body).json()["data"]["prixDT"] == 1.9
    assert c.delete(f"/api/medicaments/{d['id']}").status_code == 200


def test_medicament_sans_molecule_refuse(client):
    body = {"nomCommercial": "Vide", "type": "Generique", "dosage": "1 mg", "formeGalenique": "comprimé",
            "surOrdonnance": False, "prixDT": 1, "molecules": []}
    assert client.post("/api/medicaments", json=body).status_code == 422


def test_suppression_medicament_prescrit_refusee(client):
    assert client.delete("/api/medicaments/Advil").status_code == 409


# ---------- Valeurs ajoutées ----------
def test_alternatives(client):
    d = client.get("/api/medicaments/Advil/alternatives").json()["data"]
    assert d["meilleure"]["id"] == "IbuprofeneMylan" and d["meilleure"]["economiePct"] == 40


def test_interactions(client):
    d = client.post("/api/interactions/verifier", json={"medicaments": ["Advil", "Aspegic", "IbuprofeneMylan"]}).json()["data"]
    niveaux = {a["niveau"] for a in d["alertes"]}
    assert niveaux == {"interaction", "doublon"} and d["sur"] is False
    d = client.post("/api/interactions/verifier", json={"medicaments": ["Doliprane", "Clamoxyl"]}).json()["data"]
    assert d["sur"] is True


def test_graphe(client):
    d = client.get("/api/medicaments/Advil/graphe").json()["data"]
    assert {"Advil", "Ibuprofene", "HemorragieDigestive"} <= {n["id"] for n in d["noeuds"]}


def test_console_lecture_seule(client):
    assert client.post("/api/sparql", json={"requete": "DELETE WHERE { ?s ?p ?o }"}).status_code == 400
    r = client.post("/api/sparql", json={"requete": "SELECT ?m WHERE { ?m a :Molecule }"}).json()["data"]
    assert len(r["lignes"]) == 8


def test_stats_et_hierarchie(client):
    s = client.get("/api/stats").json()["data"]
    assert s["totaux"] == {"molecules": 8, "medicaments": 9}
    roots = client.get("/api/hierarchie").json()["data"]
    assert {r["id"] for r in roots} == {"Molecule", "Medicament"}
