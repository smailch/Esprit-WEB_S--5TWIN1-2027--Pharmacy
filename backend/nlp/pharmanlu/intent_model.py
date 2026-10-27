"""Étape 2 — Classifieur d'intention (scikit-learn).

Entrée : question délexicalisée et lemmatisée (ex. « quel medicament contenir xmol »).
Modèle : TF-IDF mots (1–2-grammes) + TF-IDF caractères (3–5-grammes) → régression logistique multinomiale.
"""
from __future__ import annotations

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import FeatureUnion, Pipeline

SEED = 42


def build_classifier() -> Pipeline:
    features = FeatureUnion([
        ("mots", TfidfVectorizer(analyzer="word", ngram_range=(1, 2), sublinear_tf=True, token_pattern=r"(?u)\b\w+\b")),
        ("caracteres", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True)),
    ])
    clf = LogisticRegression(C=8.0, max_iter=3000, class_weight="balanced", random_state=SEED)
    return Pipeline([("features", features), ("classifieur", clf)])


def save(model: Pipeline, path, vocabulary: set[str]):
    joblib.dump({"model": model, "vocabulaire": sorted(vocabulary)}, path)


def load(path):
    bundle = joblib.load(path)
    return bundle["model"], set(bundle["vocabulaire"])
