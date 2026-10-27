"""Entraîne le classifieur d'intention de PharmaNLU-A, l'évalue et écrit la carte du modèle.

Usage (depuis backend/) :  python -m nlp.train
Reproductible : graine fixe (42), versions des bibliothèques épinglées dans requirements.txt.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from datetime import date
from importlib.metadata import version
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))
# L'entraînement utilise toujours l'ontologie d'origine, jamais l'état modifié par le CRUD.
os.environ["RUNTIME_PATH"] = str(Path(tempfile.mkdtemp()) / "inutilise.ttl")

from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score  # noqa: E402

from app.graph_store import store  # noqa: E402
from nlp.pharmanlu.entities import EntityRecognizer, build_gazetteer, mask  # noqa: E402
from nlp.pharmanlu.intent_model import build_classifier, save  # noqa: E402
from nlp.pharmanlu.normalizer import spacy_version, tokenize  # noqa: E402
from nlp.pharmanlu.pipeline import CARD_FILE, MODEL_FILE  # noqa: E402
from nlp.pharmanlu.templates import INTENT_LABELS  # noqa: E402

DATA = Path(__file__).resolve().parent / "data"


def known_vocabulary(texts: list[str]) -> set[str]:
    """Mots « ordinaires » des questions d'entraînement : jamais corrigés en entité par RapidFuzz."""
    gaz = build_gazetteer(store)
    entity_words = {w for s in gaz.surfaces for w in s.split()}
    words = {t.text for txt in texts for t in tokenize(txt) if t.is_alpha}
    return words - entity_words


def preprocess(recognizer, texts):
    out, ents = [], []
    for t in texts:
        doc = tokenize(t)
        e, _ = recognizer.recognize(doc)
        out.append(mask(doc, e))
        ents.append(e)
    return out, ents


def evaluate(model, recognizer, test):
    X, ents = preprocess(recognizer, [d["texte"] for d in test])
    y = [d["intention"] for d in test]
    pred = list(model.predict(X))
    ent_ok = sum(1 for d, e in zip(test, ents) if set(d["entites"]) <= {x.id for x in e})
    return {
        "X": X, "y": y, "pred": pred, "ents": ents,
        "precision": accuracy_score(y, pred),
        "f1_macro": f1_score(y, pred, average="macro"),
        "f1_par_intention": dict(zip(sorted(set(y)), f1_score(y, pred, average=None, labels=sorted(set(y))))),
        "entites": ent_ok / len(test),
    }


def main():
    train = json.loads((DATA / "intents_train.json").read_text(encoding="utf-8"))
    test = json.loads((DATA / "intents_test.json").read_text(encoding="utf-8"))
    vocab = known_vocabulary([d["texte"] for d in train])
    recognizer = EntityRecognizer(store, known_words=vocab)

    X, _ = preprocess(recognizer, [d["texte"] for d in train])
    y = [d["intention"] for d in train]
    model = build_classifier()
    model.fit(X, y)

    r = evaluate(model, recognizer, test)
    print(classification_report(r["y"], r["pred"], zero_division=0))
    print(f"Précision (accuracy) sur le test : {r['precision']:.3f} — F1 macro : {r['f1_macro']:.3f} — entités correctes : {r['entites']:.3f}")
    errors = [(d["texte"], d["intention"], p, x) for d, p, x in zip(test, r["pred"], r["X"]) if d["intention"] != p]
    for texte, attendu, predit, masque in errors:
        print(f"  ✗ « {texte} » attendu={attendu} prédit={predit}  [{masque}]")

    MODEL_FILE.parent.mkdir(parents=True, exist_ok=True)
    save(model, MODEL_FILE, vocab)
    labels = sorted(set(y))
    card = {
        "nom": "PharmaNLU-A",
        "version": "1",
        "fichier": MODEL_FILE.name,
        "type": "Hybride : classifieur supervisé (TF-IDF mots + caractères → régression logistique) + règles linguistiques et dictionnaire issu de l'ontologie",
        "date_entrainement": date.today().isoformat(),
        "graine": 42,
        "donnees": {"entrainement": len(train), "test": len(test), "source_test": "questions écrites à la main, jamais vues à l'entraînement (fautes de frappe incluses)"},
        "intentions": [{"id": i, "label": INTENT_LABELS[i]} for i in labels],
        "metriques": {
            "precision_test": round(r["precision"], 3),
            "f1_macro_test": round(r["f1_macro"], 3),
            "reconnaissance_entites_test": round(r["entites"], 3),
            "f1_par_intention": {k: round(v, 3) for k, v in r["f1_par_intention"].items()},
            "matrice_confusion": {"labels": labels, "valeurs": confusion_matrix(r["y"], r["pred"], labels=labels).tolist()},
        },
        "bibliotheques": [
            {"nom": "spaCy", "version": version("spacy"), "role": f"tokenisation, lemmatisation, EntityRuler ({spacy_version()})"},
            {"nom": "scikit-learn", "version": version("scikit-learn"), "role": "TF-IDF + régression logistique (classification d'intention)"},
            {"nom": "RapidFuzz", "version": version("rapidfuzz"), "role": "correction des fautes de frappe (distance de Levenshtein normalisée)"},
            {"nom": "rdflib", "version": version("rdflib"), "role": "exécution de la requête SPARQL générée"},
        ],
        "pipeline": [
            "Normalisation spaCy : minuscules, accents, tokenisation, lemmatisation",
            "Entités : EntityRuler (dictionnaire généré depuis l'ontologie) + RapidFuzz pour les fautes",
            "Délexicalisation : les entités deviennent xmed / xmol / xpatho / xclasse",
            "Intention : TF-IDF (mots 1–2 + caractères 3–5) → régression logistique (probabilité = confiance)",
            "Filtres par règles : prix, ordonnance, type, forme, gravité, attribut",
            "Gabarit SPARQL de l'intention rempli avec les URI → exécution rdflib → réponse en français",
        ],
        "llm_externe": False,
    }
    CARD_FILE.write_text(json.dumps(card, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Modèle enregistré : {MODEL_FILE} ({MODEL_FILE.stat().st_size // 1024} Ko)")


if __name__ == "__main__":
    main()
