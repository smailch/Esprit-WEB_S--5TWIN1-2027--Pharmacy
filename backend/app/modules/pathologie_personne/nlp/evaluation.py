"""Évaluation du traducteur sur nlp/data/test_questions.jsonl (utilisé par scripts/eval_nlp.py et les tests)."""
import json
from collections import defaultdict
from pathlib import Path

TESTS = Path(__file__).resolve().parent / "data" / "test_questions.jsonl"


def load_tests():
    return [json.loads(line) for line in TESTS.read_text(encoding="utf-8").splitlines() if line.strip()]


def check(case: dict, out: dict) -> list[str]:
    """Liste des erreurs (vide = question correctement traitée)."""
    errors = []
    expected = case["intent"]
    got = out["intention"] if (out["compris"] or expected == "hors_perimetre") else f"non compris ({out['intention']})"
    if expected == "hors_perimetre":
        if out["compris"]:
            errors.append(f"aurait dû être hors périmètre, compris comme {out['intention']}")
        return errors
    if got != expected:
        errors.append(f"intention {got} au lieu de {expected} — {out['message']}")
        return errors
    ids = {e["id"] for e in out["entites"]}
    for e in case.get("entites", []):
        if e not in ids:
            errors.append(f"entité {e} non reconnue (trouvé {sorted(ids)})")
    res = out["resultat"] or {}
    if "bool" in case and res.get("boolean") != case["bool"]:
        errors.append(f"réponse {res.get('boolean')} au lieu de {case['bool']}")
    if "min" in case and len(res.get("rows", [])) < case["min"]:
        errors.append(f"{len(res.get('rows', []))} résultats, au moins {case['min']} attendus")
    return errors


def evaluate(pipeline) -> dict:
    per = defaultdict(lambda: [0, 0])
    failures = []
    for case in load_tests():
        out = pipeline.ask(case["q"])
        errs = check(case, out)
        per[case["intent"]][1] += 1
        if errs:
            failures.append({"question": case["q"], "erreurs": errs})
        else:
            per[case["intent"]][0] += 1
    in_scope = [v for k, v in per.items() if k != "hors_perimetre"]
    ok_in = sum(v[0] for v in in_scope)
    tot_in = sum(v[1] for v in in_scope)
    ok = sum(v[0] for v in per.values())
    tot = sum(v[1] for v in per.values())
    return {"par_intention": {k: {"ok": v[0], "total": v[1], "precision": round(v[0] / v[1], 3)}
                              for k, v in sorted(per.items())},
            "precision_perimetre": round(ok_in / tot_in, 3), "precision_globale": round(ok / tot, 3),
            "total": tot, "echecs": failures}
