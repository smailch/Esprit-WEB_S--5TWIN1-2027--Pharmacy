"""Tests du module IA PharmaNLU-A : de la question en français jusqu'au résultat SPARQL."""
import pytest


def ask(client, q):
    r = client.post("/api/nlp/ask", json={"question": q})
    assert r.status_code == 200, r.text
    return r.json()["data"]


def ids(rows, key):
    return {r[key] for r in rows}


def test_faute_de_frappe_corrigee(client):
    d = ask(client, "quels médicaments contiennent de l'ibuprophene ?")
    assert d["intention"] == "medicaments_contenant"
    assert any(e["id"] == "Ibuprofene" and e["corrige"] for e in d["entites"])
    assert ids(d["resultats"]["lignes"], "medicament") == {"Advil", "IbuprofeneMylan"}


def test_classe_via_hierarchie(client):
    d = ask(client, "liste des antibiotiques")
    assert ids(d["resultats"]["lignes"], "molecule") == {"Amoxicilline", "Azithromycine"}


def test_filtres_prix_ordonnance(client):
    d = ask(client, "médicaments sans ordonnance à moins de 5 dinars")
    assert d["filtres"]["ordonnance"] is False and d["filtres"]["prixMax"] == 5
    assert ids(d["resultats"]["lignes"], "medicament") == {"Doliprane", "IbuprofeneMylan", "Aspegic"}


def test_alternative_generique(client):
    d = ask(client, "y a-t-il un générique moins cher que l'Advil ?")
    assert d["intention"] == "generique_alternative" and "Ibuprofène Mylan" in d["reponse"]


def test_interaction_symetrique(client):
    d = ask(client, "Aspégic et Advil interagissent-ils ?")
    assert d["intention"] == "interaction" and d["resultats"]["lignes"]


def test_contre_indication_inferee(client):
    d = ask(client, "quels médicaments éviter en cas d'ulcère ?")
    assert "estContreIndiquePour" in d["sparql"]
    assert ids(d["resultats"]["lignes"], "medicament") == {"Advil", "IbuprofeneMylan", "Aspegic"}


def test_ask_ordonnance(client):
    d = ask(client, "le Clamoxyl est-il sur ordonnance ?")
    assert d["resultats"] == {"type": "ask", "resultat": True}


def test_question_hors_sujet(client):
    d = ask(client, "quelle est la météo demain à Tunis")
    assert d["compris"] is False or d["sparql"] is not None  # jamais d'erreur serveur


def test_entite_manquante(client):
    d = ask(client, "quels sont les effets secondaires ?")
    assert d["compris"] is False and "Précisez" in d["reponse"]


def test_nouvelle_donnee_reconnue_sans_reentrainement(fresh):
    body = {"nomCommercial": "Efferalgan", "type": "Generique", "dosage": "500 mg", "formeGalenique": "comprimé",
            "surOrdonnance": False, "prixDT": 2.4, "molecules": ["Paracetamol"], "indications": []}
    assert fresh.post("/api/medicaments", json=body).status_code == 201
    d = ask(fresh, "que contient l'Efferalgan ?")
    assert any(e["id"] == "Efferalgan" for e in d["entites"]) and "Paracétamol" in d["reponse"]


def test_carte_modele(client):
    m = client.get("/api/nlp/modele").json()["data"]
    assert m["nom"] == "PharmaNLU-A" and m["llm_externe"] is False
    assert m["metriques"]["precision_test"] >= 0.9


@pytest.mark.parametrize("q", ["Liste des antibiotiques", "Effets secondaires graves de l'Advil", "Combien de médicaments génériques ?",
                               "Que prendre contre la migraine ?", "Quel est le code ATC du paracétamol ?"])
def test_suggestions_repondent(client, q):
    d = ask(client, q)
    assert d["compris"] and d["resultats"] is not None
