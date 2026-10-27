"""Évalue le modèle PharmaNLU-A enregistré sur le jeu de test (sans ré-entraîner).

Usage (depuis backend/) :  python -m nlp.evaluate
"""
import json

from sklearn.metrics import classification_report

from nlp.train import DATA, evaluate, store  # noqa: F401  (store initialisé sur l'ontologie d'origine)
from nlp.pharmanlu.entities import EntityRecognizer
from nlp.pharmanlu.intent_model import load
from nlp.pharmanlu.pipeline import MODEL_FILE


def main():
    model, vocab = load(MODEL_FILE)
    test = json.loads((DATA / "intents_test.json").read_text(encoding="utf-8"))
    r = evaluate(model, EntityRecognizer(store, known_words=vocab), test)
    print(classification_report(r["y"], r["pred"], zero_division=0))
    print(f"Précision : {r['precision']:.3f} · F1 macro : {r['f1_macro']:.3f} · entités : {r['entites']:.3f}")


if __name__ == "__main__":
    main()
