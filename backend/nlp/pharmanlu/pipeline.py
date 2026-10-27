"""PharmaNLU-A : question en français → requête SPARQL exécutée → réponse.

Pipeline (100 % local, aucune API de LLM) :
  1. Normalisation         spaCy fr_core_news_sm (tokens, lemmes, accents)
  2. Entités               spaCy EntityRuler (dictionnaire issu de l'ontologie) + RapidFuzz (fautes de frappe)
  3. Filtres               règles (prix, ordonnance, type, forme, gravité, attribut)
  4. Intention             scikit-learn : TF-IDF mots + caractères → régression logistique
  5. Requête SPARQL        gabarit de l'intention rempli avec les URI → exécution sur le graphe RDF
"""
from __future__ import annotations

import json
import threading
from pathlib import Path

from .entities import EntityRecognizer, mask
from .intent_model import load
from .normalizer import normalize, tokenize
from .slots import extract_slots
from .templates import GENERATORS, INTENT_LABELS, MissingEntity

SEUIL_CONFIANCE = 0.40
MODELS_DIR = Path(__file__).resolve().parent.parent / "models"
MODEL_FILE = MODELS_DIR / "pharmanlu_intent_v1.joblib"
CARD_FILE = MODELS_DIR / "pharmanlu_intent_v1.json"


class PharmaNLU:
    def __init__(self, store, model_path: Path = MODEL_FILE):
        self.store = store
        self.model, vocab = load(model_path)
        self.recognizer = EntityRecognizer(store, known_words=vocab)

    # ------------------------------------------------------------------
    def analyse(self, question: str) -> dict:
        """Étapes 1 à 4 : sans exécution (utilisé aussi pour l'évaluation)."""
        doc = tokenize(question)
        ents, _ = self.recognizer.recognize(doc)
        masked = mask(doc, ents)
        slots = extract_slots(doc.text)
        probas = self.model.predict_proba([masked])[0]
        classes = self.model.classes_
        ranked = sorted(zip(classes, probas), key=lambda x: -x[1])
        return {"doc": doc, "entites": ents, "masque": masked, "filtres": slots, "classement": ranked}

    def ask(self, question: str) -> dict:
        a = self.analyse(question)
        intent, conf = a["classement"][0]
        ents, slots = a["entites"], a["filtres"]
        out = {
            "question": question,
            "normalisee": a["doc"].text,
            "intention": intent,
            "intentionLabel": INTENT_LABELS.get(intent, intent),
            "confiance": round(float(conf), 3),
            "alternatives": [{"intention": i, "proba": round(float(p), 3)} for i, p in a["classement"][1:3] if p > 0.08],
            "entites": [e.as_dict() for e in ents],
            "filtres": {k: v for k, v in slots.items()},
            "compris": False, "sparql": None, "explication": [], "resultats": None,
            "etapes": [
                {"nom": "Normalisation (spaCy)", "detail": " · ".join(f"{t.text}→{t.lemma_}" for t in a["doc"] if t.text != t.lemma_)[:160] or a["doc"].text},
                {"nom": "Entités (EntityRuler + RapidFuzz)", "detail": ", ".join(f"{e.texte}→:{e.id}" for e in ents) or "aucune"},
                {"nom": "Délexicalisation", "detail": a["masque"]},
                {"nom": "Intention (scikit-learn)", "detail": f"{intent} ({round(float(conf) * 100)} %)"},
            ],
        }
        if conf < SEUIL_CONFIANCE:
            out["reponse"] = "Je n'ai pas bien compris la question. Essayez de la reformuler ou choisissez un exemple ci-dessous."
            return out
        try:
            sparql, expl, answer = GENERATORS[intent](ents, slots)
        except MissingEntity as e:
            out["reponse"] = f"J'ai compris l'intention « {out['intentionLabel']} », mais il manque une information. {e}"
            return out
        out.update(compris=True, sparql=sparql, explication=expl)
        out["etapes"].append({"nom": "Génération + exécution SPARQL", "detail": f"gabarit « {intent} »"})
        if sparql.lstrip().startswith("ASK"):
            res = self.store.ask(sparql)
            out["resultats"] = {"type": "ask", "resultat": res}
            out["reponse"] = answer(res)
        else:
            rows = self.store.select(sparql)
            out["resultats"] = {"type": "select", "colonnes": list(rows[0].keys()) if rows else [], "lignes": rows}
            out["reponse"] = answer(rows)
        return out


_instance: PharmaNLU | None = None
_lock = threading.Lock()


def get_nlu(store) -> PharmaNLU:
    global _instance
    with _lock:
        if _instance is None:
            _instance = PharmaNLU(store)
        return _instance


def model_card() -> dict:
    return json.loads(CARD_FILE.read_text(encoding="utf-8"))


SUGGESTIONS = [
    "Quels médicaments contiennent de l'ibuprophène ?",
    "Liste des antibiotiques",
    "Médicaments sans ordonnance à moins de 5 dinars",
    "Effets secondaires graves de l'Advil",
    "Y a-t-il un générique moins cher que le Clamoxyl ?",
    "Advil et Aspégic interagissent-ils ?",
    "Quels médicaments éviter en cas d'ulcère ?",
    "Quel est le code ATC du paracétamol ?",
    "Que prendre contre la migraine ?",
    "Combien de médicaments génériques ?",
]

__all__ = ["PharmaNLU", "get_nlu", "model_card", "SUGGESTIONS", "normalize"]
