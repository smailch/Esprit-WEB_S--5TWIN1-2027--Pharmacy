"""Étape 5 — Classification d'intention hybride.

1. Règles spaCy (Matcher sur la question normalisée) : très précises, prioritaires.
2. Classifieur scikit-learn (TF-IDF mots + caractères → régression logistique), entraîné sur
   nlp/data/intents.jsonl où les entités sont masquées (ent_pathologie, ent_patient…).
"""
from __future__ import annotations

import json
from pathlib import Path

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import FeatureUnion, Pipeline
from spacy.matcher import Matcher

ROOT = Path(__file__).resolve().parents[2] / "nlp"
DATA = ROOT / "data" / "intents.jsonl"
MODEL = ROOT / "model" / "intent.joblib"


def load_dataset(path: Path = DATA):
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return [r["text"] for r in rows], [r["intent"] for r in rows]


def train(path: Path = DATA) -> Pipeline:
    texts, labels = load_dataset(path)
    model = Pipeline([
        ("features", FeatureUnion([
            ("mots", TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True)),
            ("caracteres", TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), sublinear_tf=True)),
        ])),
        ("clf", LogisticRegression(C=20, max_iter=5000, random_state=0)),
    ])
    model.fit(texts, labels)
    return model


def load_or_train() -> Pipeline:
    if MODEL.exists() and MODEL.stat().st_mtime >= DATA.stat().st_mtime:
        try:
            return joblib.load(MODEL)
        except Exception:
            pass
    model = train()
    MODEL.parent.mkdir(exist_ok=True)
    joblib.dump(model, MODEL)
    return model


def _in(*words):
    return {"LOWER": {"IN": list(words)}}


RULES = {
    "COMBIEN": [[_in("combien")], [{"LOWER": "nombre"}, {"LOWER": {"IN": ["de", "d", "total"]}}]],
    "CODE": [[_in("code", "codes", "cim", "cim10")]],
    "CONTRE": [[{"LOWER": "contre"}, _in("indique", "indiques", "indiquee", "indiquees", "indication",
                                         "indications")],
               [_in("eviter", "deconseille", "deconseilles", "interdit", "interdits", "incompatibles")]],
    "ALERTE": [[_in("alerte", "alertes", "dangereuse", "dangereuses", "danger", "risque", "risques",
                    "conflit", "conflits")]],
    "QUI_PRESC": [[_in("qui", "delivre", "delivree", "prescrit", "prescrite", "signe", "prescripteur",
                       "medecin", "pharmacien", "contient", "contenu", "details")]],
    "OUI_NON": [[{"LOWER": "est"}, {"LOWER": "ce"}, {"LOWER": "que"}],
                [{"LOWER": "est"}, _in("il", "elle")], [{"LOWER": "oui"}, {"LOWER": "ou"}, {"LOWER": "non"}]],
    "CIBLE_COMPTE": [[_in("patients", "patient", "patientes", "medecins", "pharmaciens", "pathologies",
                          "maladies", "femmes", "hommes", "enfants", "adultes", "docteurs")]],
}


class IntentClassifier:
    def __init__(self, nlp):
        self.model = load_or_train()
        self.matcher = Matcher(nlp.vocab)
        for name, patterns in RULES.items():
            self.matcher.add(name, patterns)
        self.nlp = nlp

    def rules(self, norm_doc, types: set[str]) -> tuple[str | None, str | None]:
        hits = {self.nlp.vocab.strings[m] for m, _, _ in self.matcher(norm_doc)}
        if "PRESCRIPTION" in types and "QUI_PRESC" in hits:
            return "intervenants_prescription", "règle : ordonnance + qui/délivre/prescrit"
        if "ALERTE" in hits:
            return "alertes", "règle : alerte/danger/risque"
        if "OUI_NON" in hits and "PATIENT" in types and "CLASSE" in types:
            return "ask_patient_classe", "règle : question oui/non sur un patient"
        if "COMBIEN" in hits and ("CIBLE_COMPTE" in hits or types & {"CLASSE", "TYPE", "PATHOLOGIE", "SPECIALITE"}):
            return "compter", "règle : combien / nombre de"
        if "CODE" in hits and types & {"PATHOLOGIE", "TYPE"}:
            return "code_cim10", "règle : code CIM-10"
        if "CONTRE" in hits and types & {"PATHOLOGIE", "TYPE"}:
            return "medicaments_contre_indiques", "règle : contre-indiqué / à éviter"
        return None, None

    def classify(self, masked: str) -> list[tuple[str, float]]:
        proba = self.model.predict_proba([masked])[0]
        ranked = sorted(zip(self.model.classes_, proba), key=lambda x: -x[1])
        return [(c, round(float(p), 3)) for c, p in ranked[:3]]
