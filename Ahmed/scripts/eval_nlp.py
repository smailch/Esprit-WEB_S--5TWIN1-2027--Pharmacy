"""Évaluation du module NLP : précision par intention et globale (cible ≥ 90 % dans le périmètre).

Une question compte comme réussie si l'intention, les entités attendues et le résultat SPARQL sont bons.
Usage : python scripts/eval_nlp.py   (code de sortie 1 si la cible n'est pas atteinte)
"""
from _common import settings

from app.nlp.evaluation import evaluate
from app.nlp.pipeline import NlpPipeline
from app.sparql.client import RdflibClient

report = evaluate(NlpPipeline(RdflibClient(settings.ontology_files())))

print(f"{'intention':<30} {'ok':>4} / total   précision")
for name, r in report["par_intention"].items():
    print(f"{name:<30} {r['ok']:>4} / {r['total']:<5}   {r['precision']:.0%}")
print(f"\nPrécision dans le périmètre : {report['precision_perimetre']:.1%}")
print(f"Précision globale ({report['total']} questions) : {report['precision_globale']:.1%}")
for f in report["echecs"]:
    print(f"  ✗ {f['question']} → {'; '.join(f['erreurs'])}")
raise SystemExit(0 if report["precision_perimetre"] >= 0.9 else 1)
