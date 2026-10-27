"""Étape 4 — Classification d'intention par règles pondérées (explicable et testable).

Chaque intention déclare :
- des indices lexicaux (expressions régulières sur le texte normalisé ET sur les lemmes spaCy) avec un poids ;
- des contraintes sur les entités : `requires` (toutes), `any_of` (au moins une), `excludes` (aucune) ;
- des indices obligatoires (`needs`, tous requis) et des bonus quand certaines entités sont présentes.
Le score de chaque intention est la somme des poids déclenchés ; les scores sont convertis en probabilités
(softmax) pour afficher une confiance. Sous le seuil, la question est déclarée « non comprise ».
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

PRESC_WORD = r"\b(prescription|ordonnance)s?\b"
PRESCRIRE = r"\bprescri(re|t|ts|te|tes|vent|vait|ent)\b"
MED_WORD = r"\b(medicaments?|traitements?)\b"
LIST = r"\b(quel|quels|quelle|quelles|liste|lister|affiche|afficher|montre|montrer|donne|donner|toutes?|tous|enumerer|voir)\b"
COUNT = r"\b(combien|nombre|total|compter|compte)\b"
YESNO = r"-t-(il|elle|on)\b|\best[- ]ce\b|-(elle|il)\b|\best-(il|elle)\b|\bvrai\b|\boui ou non\b"
DANGER = (r"contre-indique|contre-indication|dangereu|\bdanger|\brisque|\balerte|incompatib|\bconflit"
          r"|deconseill|\bprobleme|\bsecurite|\binterdit|\bincident")
ALLERGIE = r"\ballergi"
DONNEE_WORD = (r"\bdonnees? cliniques?|\bdossier|\bexamens?\b|\banalyses?\b|\bmesures?\b|\bbilans?\b|\bresultats?\b"
               r"|\ballergi|\bantecedents?\b|\bsignes? vita|\bconstantes?\b|\bhistorique")
VALUE_WORD = r"\b(valeur|niveau|taux|resultat|combien|quelle est|quel est|mesure|mesuree)\b"
CHAIN = r"\bchaine|\bparcours|\bscenario|\btrace|\bcheminement|\bgraphe"

THRESHOLD = 2.0


@dataclass
class Intent:
    name: str
    label: str
    cues: list[tuple[str, float, str]]
    requires: list[str] = field(default_factory=list)
    any_of: list[str] = field(default_factory=list)
    excludes: list[str] = field(default_factory=list)
    bonus: dict[str, float] = field(default_factory=dict)
    base: float = 0.0
    example: str = ""
    needs: list[str] = field(default_factory=list)  # indices lexicaux obligatoires (sinon l'intention est écartée)


PRESC_FILTERS = {"TYPE_PRESCRIPTION": 1.5, "DATE": 1.5, "MEDECIN": 1.0, "PATIENT": 1.0, "PHARMACIEN": 1.0,
                 "MEDICAMENT": 0.5, "MOLECULE": 0.5}
DONNEE_FILTERS = {"TYPE_DONNEE": 2.0, "PATIENT": 1.0, "MOLECULE": 0.5, "PATHOLOGIE": 0.5, "DATE": 1.0}

INTENTS = [
    # ---------------- Prescriptions ----------------
    Intent("lister_prescriptions", "Lister / filtrer les prescriptions",
           [(PRESC_WORD, 2, "mot « prescription / ordonnance »"), (LIST, 0.5, "demande de liste"),
            (PRESCRIRE, 0.5, "verbe « prescrire »"), (r"\b(enregistr|existe|disponible)", 0.5, "« enregistrées / existantes »")],
           excludes=["PRESCRIPTION", "TYPE_DONNEE", "MESURE"], bonus=PRESC_FILTERS,
           example="Quelles sont les prescriptions renouvelables ?"),
    Intent("compter_prescriptions", "Compter les prescriptions",
           [(COUNT, 3, "« combien / nombre »"), (PRESC_WORD, 1.5, "mot « prescription / ordonnance »"), (PRESCRIRE, 0.5, "verbe « prescrire »")],
           excludes=["TYPE_DONNEE", "MESURE"], bonus=PRESC_FILTERS, needs=[COUNT, PRESC_WORD + "|" + PRESCRIRE],
           example="Combien de prescriptions sont enregistrées ?"),
    Intent("prescripteur", "Retrouver le prescripteur",
           [(r"\bqui\b.*\bprescri", 4, "« qui a prescrit »"), (r"\b(quel|quels) (medecin|prescripteur|dr)s?\b", 3, "« quel médecin »"),
            (r"\b(medecin|prescripteur)s?\b", 1.5, "mot « médecin »"), (r"\bsigne", 1, "« signée par »")],
           any_of=["PRESCRIPTION", "PATIENT", "MEDICAMENT"], excludes=["MEDECIN"], bonus={"PRESCRIPTION": 1},
           example="Qui a prescrit Presc_002 ?"),
    Intent("patient_prescription", "Retrouver le patient d'une ordonnance",
           [(r"\b(quel|quelle|quels) (patient|patiente|malade)s?\b", 2.5, "« quel patient »"), (r"\b(pour qui|a qui)\b", 2.5, "« pour qui »"),
            (r"\bconcern", 2, "« concerne »"), (r"\b(patient|patiente|malade)\b", 1, "mot « patient »")],
           requires=["PRESCRIPTION"], excludes=["PATIENT"], example="Quel patient est concerné par Presc_004 ?"),
    Intent("patients_medicament", "Patients à qui un médicament a été prescrit",
           [(r"\b(quel|quels|quelle|quelles) (patient|patiente|malade)s?\b", 2.5, "« quels patients »"), (r"\b(a qui|qui)\b", 1.5, "« à qui »"),
            (r"\bprend|\bprendre\b", 1, "« prend »"), (PRESCRIRE, 1, "verbe « prescrire »")],
           requires=["MEDICAMENT"], excludes=["PRESCRIPTION", "PATIENT", "MEDECIN"], example="À quels patients a-t-on prescrit de l'Advil ?"),
    Intent("pharmacien_prescription", "Retrouver le pharmacien qui a délivré une ordonnance",
           [(r"\bdelivr", 2.5, "« délivrée »"), (r"\bpharmaci", 2, "mot « pharmacien »"), (r"\bqui\b", 1, "« qui »")],
           requires=["PRESCRIPTION"], excludes=["PHARMACIEN"], example="Qui a délivré Presc_001 ?"),
    Intent("medicaments_prescription", "Médicaments d'une ordonnance",
           [(MED_WORD, 2, "mot « médicament »"), (r"\bconti?en|\bcontenir\b|\bcompor|\bfigur", 1.5, "« contient »"),
            (r"\b(quoi|que)\b", 0.5, "« quoi / que »"), (PRESCRIRE, 0.5, "verbe « prescrire »")],
           requires=["PRESCRIPTION"], excludes=["MEDICAMENT"], example="Quels médicaments contient l'ordonnance 3 ?"),
    Intent("verifier_medicament_prescription", "Vérifier qu'une ordonnance contient un médicament",
           [(YESNO, 2, "question fermée (oui / non)"), (r"\bconti?en|\bcontenir\b|\bcompor|\bfigur|\binclu", 2, "« contient »"),
            (PRESCRIRE, 1, "verbe « prescrire »")],
           requires=["PRESCRIPTION", "MEDICAMENT"], example="L'ordonnance 3 contient-elle de l'Advil ?"),
    Intent("verifier_type_prescription", "Vérifier le type d'une ordonnance",
           [(YESNO, 2.5, "question fermée (oui / non)"), (r"\b(est|etre)\b", 1, "verbe « être »")],
           requires=["PRESCRIPTION", "TYPE_PRESCRIPTION"], base=1.0, example="Presc_001 est-elle renouvelable ?"),
    Intent("details_prescription", "Détails d'une ordonnance",
           [(r"\bposologie|\bduree|\bdate\b|\bquand\b|\bdetail|\binformation|\bdecri|\bresume|\bfiche|\bjours\b", 2.5,
             "attribut demandé (posologie, durée, date…)")],
           requires=["PRESCRIPTION"], base=1.0, example="Quelle est la posologie de Presc_001 ?"),
    Intent("medicaments_patient", "Médicaments prescrits à un patient",
           [(MED_WORD, 2.5, "mot « médicament »"), (r"\bprend|\bprendre\b", 1.5, "« prend »"), (PRESCRIRE, 1, "verbe « prescrire »")],
           requires=["PATIENT"], excludes=["PRESCRIPTION", "MEDICAMENT", "TYPE_DONNEE", "MESURE"],
           example="Quels médicaments sont prescrits à Ali ?"),
    Intent("verifier_medicament_patient", "Vérifier qu'un patient reçoit un médicament",
           [(YESNO, 2, "question fermée (oui / non)"), (r"\bprend|\bprendre\b|\brecoi|\brecevoir\b", 1.5, "« prend / reçoit »"),
            (PRESCRIRE, 1.5, "verbe « prescrire »")],
           requires=["PATIENT", "MEDICAMENT"], excludes=["PRESCRIPTION", "TYPE_DONNEE"], example="Youssef prend-il de l'Advil ?"),
    Intent("verifier_contre_indication", "Détecter les prescriptions à risque (dossier clinique)",
           [(DANGER, 3, "contre-indication / danger / risque"), (YESNO, 0.5, "question fermée")],
           bonus={"PATIENT": 1, "PRESCRIPTION": 1}, needs=[DANGER + "|" + ALLERGIE + ".*" + PRESC_WORD],
           example="Le patient Youssef a-t-il une prescription contre-indiquée ?"),
    Intent("chaine_patient", "Chaîne Patient → Prescription → Médicament → Molécule → Contre-indication",
           [(CHAIN, 3, "« chaîne / parcours »"), (DANGER, 0.5, "contre-indication")],
           requires=["PATIENT"], needs=[CHAIN], example="Montre la chaîne de Youssef"),
    # ---------------- Données cliniques ----------------
    Intent("lister_donnees", "Lister / filtrer les données cliniques",
           [(DONNEE_WORD, 2.5, "mot « donnée clinique / examen / allergie… »"), (LIST, 0.5, "demande de liste"),
            (r"\b(enregistr|existe|disponible|a-t-il|a-t-elle|ont)\b", 0.5, "« enregistrées / possède »")],
           excludes=["PRESCRIPTION", "MESURE", "SEUIL"], bonus=DONNEE_FILTERS, needs=[DONNEE_WORD],
           example="Quelles sont les données cliniques de Ali ?"),
    Intent("compter_donnees", "Compter les données cliniques",
           [(COUNT, 3, "« combien / nombre »"), (DONNEE_WORD, 1.5, "mot « donnée clinique / examen… »")],
           bonus={"TYPE_DONNEE": 1.5, "PATIENT": 0.5}, needs=[COUNT, DONNEE_WORD], excludes=["MESURE"],
           example="Combien d'allergies sont enregistrées ?"),
    Intent("valeur_mesure", "Valeur d'un examen clinique",
           [(VALUE_WORD, 1.5, "« quelle est / valeur »"), (LIST, 0.5, "demande")],
           requires=["MESURE"], excludes=["SEUIL"], base=1.5, bonus={"PATIENT": 1},
           example="Quelle est la glycémie d'Ali ?"),
    Intent("seuil_mesure", "Patients dont un examen dépasse un seuil",
           [(r"\b(patient|patients|qui)\b", 1, "« quels patients »")],
           requires=["MESURE", "SEUIL"], base=3.0, example="Quels patients ont une clairance inférieure à 60 ?"),
    Intent("verifier_allergie", "Vérifier une allergie du patient",
           [(ALLERGIE, 3, "« allergique »"), (YESNO, 1, "question fermée")],
           requires=["PATIENT"], any_of=["MOLECULE", "MEDICAMENT"], excludes=["PRESCRIPTION"], base=3.0, needs=[ALLERGIE],
           example="Sara est-elle allergique à l'amoxicilline ?"),
]
BY_NAME = {i.name: i for i in INTENTS}

# Raffinement explicatif des intentions « lister » selon le filtre principal reconnu.
REFINEMENTS = {
    "lister_prescriptions": [("TYPE_PRESCRIPTION", "prescriptions_par_type"), ("DATE", "prescriptions_periode"),
                             ("MEDECIN", "prescriptions_medecin"), ("PATIENT", "prescriptions_patient"),
                             ("PHARMACIEN", "prescriptions_pharmacien"), ("MEDICAMENT", "prescriptions_medicament"),
                             ("MOLECULE", "prescriptions_molecule")],
    "lister_donnees": [("PATIENT", "donnees_patient"), ("TYPE_DONNEE", "donnees_par_type"), ("DATE", "donnees_periode")],
}


@dataclass
class Prediction:
    intent: str | None
    family: str | None
    confidence: float
    score: float
    cues: list[str]
    alternatives: list[dict]


def classify(normalized: str, lemma_text: str, entity_types: set[str]) -> Prediction:
    text = f"{normalized} || {lemma_text}"
    scored = []
    for it in INTENTS:
        if any(t not in entity_types for t in it.requires):
            continue
        if it.any_of and not entity_types & set(it.any_of):
            continue
        if entity_types & set(it.excludes):
            continue
        if any(not re.search(n, text) for n in it.needs):
            continue
        score, cues = it.base, []
        for pattern, weight, desc in it.cues:
            if re.search(pattern, text):
                score += weight
                cues.append(f"{desc} ({weight:+g})")
        for t, w in it.bonus.items():
            if t in entity_types:
                score += w
                cues.append(f"entité {t} ({w:+g})")
        scored.append((score, it, cues))
    scored.sort(key=lambda x: -x[0])
    if not scored or scored[0][0] < THRESHOLD:
        alts = [{"intention": it.name, "score": round(s, 2)} for s, it, _ in scored[:3]]
        return Prediction(None, None, 0.0, scored[0][0] if scored else 0.0, [], alts)

    positives = [s for s, *_ in scored if s > 0]
    z = sum(math.exp(s) for s in positives)
    probs = [(math.exp(s) / z if s > 0 else 0.0) for s, *_ in scored]
    best_score, best, cues = scored[0]
    name = next((n for t, n in REFINEMENTS.get(best.name, []) if t in entity_types), best.name)
    alternatives = [{"intention": it.name, "proba": round(p, 3), "score": round(s, 2)}
                    for (s, it, _), p in list(zip(scored, probs))[1:4] if s > 0]
    return Prediction(name, best.name, round(probs[0], 3), round(best_score, 2), cues, alternatives)
