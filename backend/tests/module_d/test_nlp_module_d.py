"""Tests du module TALN PrescriNLU-D : prétraitement, entités, intentions, génération SPARQL, endpoint /ask."""
import json
from datetime import date
from pathlib import Path

import pytest

from nlp.prescrinlu import lexicon
from nlp.prescrinlu.entity_extractor import Entity, Threshold, extract, extract_period, extract_threshold
from nlp.prescrinlu.intent_classifier import classify
from nlp.prescrinlu.preprocessing import analyse, normalize, strip_accents
from nlp.prescrinlu.sparql_generator import generate

EVAL = json.loads((Path(__file__).resolve().parents[2] / "nlp" / "prescrinlu" / "data" / "questions_eval.json").read_text(encoding="utf-8"))
ASK_URL = "/api/module-d/nlp/ask"


def ask(client, question):
    r = client.post(ASK_URL, json={"question": question})
    assert r.status_code == 200, r.text
    return r.json()


def entities_of(question):
    ents, period, unknown = extract(analyse(question), lexicon.build())
    return {e.id: e for e in ents}, period, unknown


# ---------- 1. Prétraitement ----------
def test_normalisation():
    assert normalize("Qu’a prescrit le Docteur BENALI à l'ordonnance n° 3 ?") == "qu'a prescrit le dr benali a l'ordonnance 3"
    assert normalize("Ordonnances CONTRE-INDIQUÉES") == "ordonnances contre-indique"


def test_lemmatisation_spacy():
    a = analyse("Quels médicaments sont prescrits à Ali ?")
    assert "prescrire" in a.lemma_text.split() and "medicament" in a.lemma_text.split()


def test_correction_mots_metier():
    a = analyse("quels medicamants sont prescrit")
    assert any(c["correction"] == "medicaments" for c in a.corrections)


# ---------- 2. Entités ----------
def test_entites_dictionnaire_et_regles():
    ents, _, _ = entities_of("L'ordonnance 3 du docteur Benali pour Youssef contient-elle de l'ibuprofène ?")
    assert {"Presc_003", "Dr_Benali", "Patient_Youssef", "Ibuprofene"} <= set(ents)
    assert ents["Presc_003"].methode == "regle" and ents["Dr_Benali"].methode == "dictionnaire"


def test_entites_donnees_cliniques():
    ents, _, _ = entities_of("glycémie et allergies de Sara, antécédent d'ulcère, signes vitaux")
    assert {"Glycémie à jeun", "Allergie", "Patient_Sara", "Antecedent", "UlcereGastroduodenal", "SigneVital"} <= set(ents)
    assert ents["Glycémie à jeun"].type == "MESURE" and ents["UlcereGastroduodenal"].type == "PATHOLOGIE"


def test_entites_types_de_prescription():
    ents, _, _ = entities_of("les ordonnances non renouvelables")
    assert set(ents) == {"PrescriptionSimple"}  # la correspondance la plus longue l'emporte


def test_entites_fautes_de_frappe():
    ents, _, _ = entities_of("qui a prescrit le dolipran a yousef")
    assert ents["Doliprane"].methode == "approximatif" and ents["Doliprane"].score >= 82
    assert "Patient_Youssef" in ents


def test_entite_inconnue():
    ents, _, unknown = entities_of("Le patient Patient_F001 a-t-il une ordonnance Presc_099 ?")
    assert unknown == ["Presc_099", "patient_f001"] and "Patient_F001" not in ents


@pytest.mark.parametrize("texte, debut, fin", [
    ("en octobre 2026", date(2026, 10, 1), date(2026, 10, 31)),
    ("entre le 2026-09-01 et le 2026-10-13", date(2026, 9, 1), date(2026, 10, 13)),
    ("apres le 12/10/2026", date(2026, 10, 13), None),
    ("avant le 15 octobre 2026", None, date(2026, 10, 14)),
    ("depuis le 1er septembre 2026", date(2026, 9, 1), None),
    ("en 2025", date(2025, 1, 1), date(2025, 12, 31)),
])
def test_periodes(texte, debut, fin):
    p = extract_period(normalize(texte))
    assert (p.debut, p.fin) == (debut, fin)


@pytest.mark.parametrize("texte, op, valeur", [
    ("clairance inférieure à 60", "<", 60), ("tension > 140", ">", 140), ("glycémie supérieure à 1,5", ">", 1.5),
    ("température au moins 38.5", ">=", 38.5), ("moins de 50 mL/min", "<", 50),
])
def test_seuils(texte, op, valeur):
    t = extract_threshold(strip_accents(texte.lower()))
    assert (t.op, t.valeur) == (op, valeur)


def test_pas_de_seuil_sur_une_date():
    assert extract_threshold("prescriptions apres le 12/10/2026") is None


# ---------- 3. Intentions (jeu annoté) ----------
@pytest.mark.parametrize("case", EVAL, ids=[c["question"][:40] for c in EVAL])
def test_intentions_jeu_annote(case):
    a = analyse(case["question"])
    ents, period, _ = extract(a, lexicon.build())
    seuil = extract_threshold(strip_accents(case["question"].lower()))
    types = {e.type for e in ents} | ({"DATE"} if period else set()) | ({"SEUIL"} if seuil else set())
    pred = classify(a.normalized, a.lemma_text, types)
    assert pred.intent == case["intent"], (pred.intent, pred.cues, pred.alternatives)
    assert set(case["entites"]) <= {e.id for e in ents}


# ---------- 4. Génération SPARQL sécurisée ----------
def test_generation_refuse_uri_non_valide():
    evil = Entity("PRESCRIPTION", "Presc_001> } ; DROP ALL ; #", "x", "x", "regle")
    with pytest.raises(ValueError):
        generate("prescripteur", "prescripteur", [evil], None)


def test_generation_echappe_les_litteraux_et_operateurs():
    mesure = Entity("MESURE", 'Glycémie") } ; DROP ALL #', "x", "x", "dictionnaire")
    g = generate("valeur_mesure", "valeur_mesure", [mesure], None)
    assert '\\"' in g.sparql  # guillemet échappé par rdflib : reste à l'intérieur du littéral
    with pytest.raises(ValueError):
        generate("seuil_mesure", "seuil_mesure", [mesure], None, Threshold("; DROP", 1, "x"))


def test_injection_dans_la_question(client):
    out = ask(client, 'Qui a prescrit Presc_002 } ; DROP ALL ; INSERT DATA { :x :y :z } #')
    assert out["intent"] == "prescripteur" and out["results"][0]["medecin"] == "Dr_Benali"
    assert "DROP" not in out["sparql"] and "INSERT" not in out["sparql"]


# ---------- 5. Endpoint /api/module-d/nlp/ask ----------
def test_format_reponse(client):
    out = ask(client, "Quelles sont les prescriptions renouvelables ?")
    for key in ("question", "intent", "entities", "sparql", "results", "count", "message"):
        assert key in out
    assert out["intent"] == "prescriptions_par_type" and out["count"] == 2
    assert {r["prescription"] for r in out["results"]} == {"Presc_001", "Presc_004"}
    assert ":PrescriptionRenouvelable" in out["sparql"] and len(out["etapes"]) == 5


@pytest.mark.parametrize("question, intent, attendu", [
    ("Quels médicaments sont prescrits à Patient_Ali ?", "medicaments_patient", {"Glucophage"}),
    ("Qui a prescrit Presc_002 ?", "prescripteur", {"Dr_Benali"}),
    ("Quelles ordonnances ont été émises en octobre 2026 ?", "prescriptions_periode", {"Presc_002", "Presc_003", "Presc_004"}),
    ("Quel patient est concerné par Presc_004 ?", "patient_prescription", {"Patient_Lina"}),
    ("Quelles prescriptions contiennent de l'ibuprofène ?", "prescriptions_molecule", {"Presc_003"}),
    ("Quelles sont les données cliniques de Ali ?", "donnees_patient", {"Glycemie_Ali", "Creatinine_Ali"}),
    ("Quelles allergies sont enregistrées ?", "donnees_par_type", {"Allergie_Sara"}),
    ("Quels patients ont un antécédent d'ulcère ?", "donnees_par_type", {"Antecedent_Youssef"}),
    ("Quels patients ont une clairance de la créatinine inférieure à 60 ?", "seuil_mesure", {"Patient_Ali"}),
    ("Patients avec une tension > 140", "seuil_mesure", {"Patient_Youssef"}),
])
def test_questions_exemples(client, question, intent, attendu):
    out = ask(client, question)
    assert out["intent"] == intent and out["compris"] is True
    first_col = next(iter(out["results"][0]))
    assert {r[first_col] for r in out["results"]} == attendu


def test_valeur_mesure(client):
    out = ask(client, "Quelle est la glycémie d'Ali ?")
    assert out["intent"] == "valeur_mesure" and out["results"][0]["valeur"] == 1.92 and "1.92 g/L" in out["message"]
    assert ask(client, "Patients avec une tension > 150")["count"] == 0  # seuil non atteint : résultat vide


def test_compter(client):
    assert ask(client, "Combien de prescriptions sont enregistrées ?")["results"][0]["nombre"] == 4
    assert ask(client, "Combien d'ordonnances renouvelables ?")["results"][0]["nombre"] == 2
    assert ask(client, "Combien de données cliniques pour Ali ?")["results"][0]["nombre"] == 2


def test_contre_indication_scenario(client):
    out = ask(client, "Le patient Youssef a-t-il une prescription contre-indiquée ?")
    assert out["intent"] == "verifier_contre_indication" and out["message"].startswith("Oui")
    assert {(r["presc"], r["med"], r["mol"]) for r in out["results"]} == {("Presc_003", "Advil", "Ibuprofene")}
    assert {r["type"] for r in out["results"]} == {"contre-indication", "antécédent"}
    assert ask(client, "Lina a-t-elle une ordonnance à risque ?")["message"].startswith("Aucune contre-indication")


def test_ask_oui_non(client):
    assert ask(client, "L'ordonnance 3 contient-elle de l'Advil ?")["answer"] is True
    out = ask(client, "Presc_001 est-elle renouvelable ?")
    assert out["resultType"] == "ask" and out["answer"] is True  # type déduit (RenouvellementLong ⊑ PrescriptionRenouvelable)
    assert ask(client, "Sara est-elle allergique à l'amoxicilline ?")["answer"] is True
    assert ask(client, "Sara est-elle allergique au Clamoxyl ?")["answer"] is True  # via contientMolecule
    assert ask(client, "Ali est-il allergique au Clamoxyl ?")["answer"] is False


def test_question_inconnue_et_entite_inconnue(client):
    out = ask(client, "Quel temps fera-t-il demain ?")
    assert out["intent"] is None and out["compris"] is False and out["sparql"] is None and "Reformulez" in out["message"]
    out = ask(client, "Le patient Patient_F001 a-t-il une prescription contre-indiquée ?")
    # Le message propose des patients connus ; leur liste dépend des extensions de l'ontologie (ontologie/extensions/)
    assert out["sparql"] is None and "Patient_F001" in out["message"]
    assert any(nom in out["message"] for nom in ("Youssef Hamdi", "Ali Ben Salah", "Sara Jlassi", "Lina Gharbi"))


def test_dictionnaire_dynamique_apres_crud(fresh):
    c = fresh
    c.post("/api/donnees-cliniques", json={"type": "AnalyseBiologique", "patient": "Patient_Lina", "libelle": "Hémoglobine",
                                           "dateMesure": "2026-10-20", "valeur": 13.2, "unite": "g/dL"})
    out = ask(c, "Quelle est l'hémoglobine de Lina ?")  # libellé créé par le CRUD, reconnu sans ré-entraînement
    assert out["intent"] == "valeur_mesure" and out["results"][0]["valeur"] == 13.2


def test_erreurs_http(client):
    assert client.post(ASK_URL, json={"question": ""}).status_code == 422
    assert client.post(ASK_URL, json={"question": "x" * 301}).status_code == 422
    assert client.post(ASK_URL, json={}).status_code == 422


def test_carte_du_modele(client):
    d = client.get("/api/module-d/nlp/modele").json()["data"]
    assert d["llm"].startswith("aucun") and {b["nom"] for b in d["bibliotheques"]} >= {"spaCy", "RapidFuzz", "RDFLib"}
    assert d["evaluation"]["precisionIntention"] >= 0.9
    assert len(client.get("/api/module-d/nlp/suggestions").json()["data"]) >= 8
