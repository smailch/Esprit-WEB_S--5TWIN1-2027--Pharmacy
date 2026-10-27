"""Exécution contrôlée des requêtes SPARQL saisies par l'utilisateur (lecture seule).

La requête est réellement analysée (parseur SPARQL de rdflib) puis son algèbre est inspectée :
- seules les formes SELECT, ASK et CONSTRUCT sont acceptées ;
- toute mise à jour (INSERT, DELETE, LOAD, DROP…) est refusée, car le parseur de requêtes ne l'accepte pas ;
- SERVICE (requête fédérée vers un serveur distant) et FROM / FROM NAMED (chargement d'un graphe externe)
  sont interdits, ce qui empêche tout appel réseau déclenché par le client ;
- le nombre de lignes renvoyées est plafonné.
"""
from __future__ import annotations

from rdflib.plugins.sparql import prepareQuery
from rdflib.plugins.sparql.parserutils import CompValue

from ...graph_store import PREFIXES, store, to_python

ALLOWED = {"SelectQuery": "select", "AskQuery": "ask", "ConstructQuery": "graphe"}
FORBIDDEN_NODES = {"ServiceGraphPattern": "SERVICE (requête vers un serveur distant)"}


class UnsafeQuery(ValueError):
    pass


def _walk(node):
    if isinstance(node, CompValue):
        yield node
        for value in node.values():
            yield from _walk(value)
    elif isinstance(node, (list, tuple)):
        for value in node:
            yield from _walk(value)


def validate(sparql: str) -> str:
    """Renvoie le type de requête ('select', 'ask', 'graphe') ou lève UnsafeQuery."""
    try:
        query = prepareQuery(PREFIXES + sparql)
    except Exception as e:  # le parseur de requêtes rejette aussi toute requête de mise à jour
        raise UnsafeQuery(f"Requête refusée : seules les requêtes SELECT, ASK et CONSTRUCT sont acceptées ({e})") from e
    kind = ALLOWED.get(query.algebra.name)
    if not kind:
        raise UnsafeQuery(f"Forme de requête non autorisée : {query.algebra.name}")
    if query.algebra.get("datasetClause"):
        raise UnsafeQuery("FROM / FROM NAMED interdits : la requête porte uniquement sur l'ontologie chargée")
    for node in _walk(query.algebra):
        if node.name in FORBIDDEN_NODES:
            raise UnsafeQuery(f"Opération interdite : {FORBIDDEN_NODES[node.name]}")
    return kind


def execute(sparql: str, limite: int = 500) -> dict:
    kind = validate(sparql)
    if kind == "ask":
        return {"type": "ask", "resultat": store.ask(sparql)}
    if kind == "graphe":
        g = store.construct(sparql)
        return {"type": "graphe", "triplets": len(g), "turtle": g.serialize(format="turtle")}
    with store._lock:
        result = store.ds.query(PREFIXES + sparql)
        columns = [str(v) for v in result.vars]
        rows, truncated = [], False
        for i, row in enumerate(result):
            if i >= limite:
                truncated = True
                break
            rows.append({str(v): to_python(row[v]) for v in result.vars})
    return {"type": "select", "colonnes": columns, "lignes": rows, "tronque": truncated}
