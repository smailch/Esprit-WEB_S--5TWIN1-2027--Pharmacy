"""Génère docs/SPARQL.md à partir de backend/sparql/*.rq (objectif, requête, exemple de résultat réel).

Chaque requête est exécutée sur un graphe rdflib neuf avec les paramètres « exemple » de son en-tête.
Usage (depuis backend/) : python tools/gen_sparql_doc.py
"""
from pathlib import Path

import _common  # noqa: F401  (chemins + runtime temporaire)

from app.graph_store import store
from app.modules.pathologie_personne.client import StoreClient
from app.modules.pathologie_personne.templates import QUERIES, render

ORDER = ["Create", "Read", "Update", "Delete", "ASK", "Filtre", "Recherche", "Hierarchie",
         "Agregat", "Chemin", "Alerte"]
OUT = Path(__file__).resolve().parents[2] / "docs" / "sante" / "SPARQL.md"

client = StoreClient(store)


def table(res, n=5):
    if not res.rows:
        return "_(aucun résultat)_"
    lines = ["| " + " | ".join(res.vars) + " |", "|" + "---|" * len(res.vars)]
    for r in res.rows[:n]:
        lines.append("| " + " | ".join(str(r.get(v, "")).replace("|", "\\|") for v in res.vars) + " |")
    if len(res.rows) > n:
        lines.append(f"\n… {len(res.rows)} lignes au total")
    return "\n".join(lines)


out = ["# Requêtes SPARQL — modules Pathologie et Personne (Ahmed Allaya)", "",
       "Fichier généré par `scripts/gen_sparql_doc.py` : chaque exemple de résultat est **réellement exécuté**",
       "sur `pharma.ttl` + `ontologie/extensions/*.ttl` (graphe commun de l'application, remis à zéro).", "",
       "Les requêtes de référence Q1–Q8 de l'équipe sont dans `ontologie/requetes.sparql` ; ici,",
       "uniquement les requêtes nommées de mes modules (`backend/app/modules/pathologie_personne/sparql/*.rq`), utilisées par l'API.", "",
       "**Sécurité** : paramètres typés (`iri` validé par regex, `lit` échappé, `int` converti) ;",
       "aucune concaténation brute de texte utilisateur (test d'injection dans `tests/test_sparql.py`).", "",
       f"**{len(QUERIES)} requêtes nommées.**", ""]

for cat in ORDER:
    names = [n for n, q in QUERIES.items() if q.categorie == cat]
    if not names:
        continue
    out += [f"## {cat}", ""]
    for name in names:
        q = QUERIES[name]
        client.reset()
        text = render(name, **q.exemple)
        out += [f"### `{name}`", "", f"**Objectif** : {q.objectif}", ""]
        if q.params:
            out += ["Paramètres : " + ", ".join(f"`{k}` ({t})" for k, t in q.params.items())
                    + f" — exemple `{q.exemple}`", ""]
        out += ["```sparql", text.split("\n", 5)[-1].strip(), "```", ""]
        if cat in ("Create", "Update", "Delete"):
            client.update(text)
            out += ["Résultat : mise à jour appliquée (vérifiée dans les tests).", ""]
        else:
            kind, res = client.run(text)
            if kind == "ASK":
                out += [f"Résultat : `{str(res).lower()}`", ""]
            elif kind == "SELECT":
                out += ["Résultat :", "", table(res), ""]
            else:
                out += ["Résultat (Turtle, extrait) :", "", "```turtle",
                        "\n".join(res.strip().splitlines()[:14]), "```", ""]

OUT.parent.mkdir(exist_ok=True)
OUT.write_text("\n".join(out), encoding="utf-8")
print("écrit :", OUT)
