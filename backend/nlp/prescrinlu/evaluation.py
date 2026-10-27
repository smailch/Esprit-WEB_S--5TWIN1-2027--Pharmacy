"""Évaluation reproductible : précision de l'intention et des entités sur un jeu de questions annotées à la main.

Le jeu (`data/questions_eval.json`) contient des formulations variées, avec fautes de frappe et questions hors sujet.
Lancement en ligne de commande depuis backend/ : python -m nlp.prescrinlu.evaluation
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from .pipeline import ask

DATA = Path(__file__).resolve().parent / "data" / "questions_eval.json"


def evaluate() -> dict:
    cases = json.loads(DATA.read_text(encoding="utf-8"))
    ok_intent = ok_entities = 0
    per_intent, errors = Counter(), []
    totals = Counter(c["intent"] or "non_comprise" for c in cases)
    for c in cases:
        out = ask(c["question"])
        got = out["intent"] or "non_comprise"
        expected = c["intent"] or "non_comprise"
        ids = {e["id"] for e in out["entities"]}
        ent_ok = set(c.get("entites", [])) <= ids
        ok_intent += got == expected
        ok_entities += ent_ok
        if got == expected:
            per_intent[expected] += 1
        else:
            errors.append({"question": c["question"], "attendu": expected, "obtenu": got})
    n = len(cases)
    return {
        "questions": n, "precisionIntention": round(ok_intent / n, 3), "precisionEntites": round(ok_entities / n, 3),
        "parIntention": {k: round(per_intent[k] / v, 3) for k, v in sorted(totals.items())}, "erreurs": errors,
    }


if __name__ == "__main__":
    print(json.dumps(evaluate(), ensure_ascii=False, indent=2))
