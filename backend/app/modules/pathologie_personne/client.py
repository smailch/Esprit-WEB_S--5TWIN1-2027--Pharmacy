"""Accès SPARQL du module Pathologie + Personne, branché sur le graphe commun de l'application (graph_store.store).

- Lectures : sur le graphe DÉCLARÉ (urn:pharma:base) — les types assertés y sont uniques, ce qui garde
  les listes sans doublons ; la classe Enfant/Adulte est dérivée de l'âge directement en SPARQL.
- Écritures : via store.update (recalcul de l'inférence OWL RL + sauvegarde runtime.ttl), donc visibles
  par tous les modules.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import Decimal

from rdflib import BNode, Graph, Literal
from rdflib.plugins.sparql import prepareQuery
from rdflib.plugins.sparql.parserutils import CompValue

from ...graph_store import PREFIXES, GraphStore, to_python

CONSOLE_KINDS = {"SelectQuery": "select", "AskQuery": "ask", "ConstructQuery": "graphe"}


def _nodes(node):
    if isinstance(node, CompValue):
        yield node
        for value in node.values():
            yield from _nodes(value)
    elif isinstance(node, (list, tuple)):
        for value in node:
            yield from _nodes(value)


def validate_readonly(query: str) -> str:
    """Console : la requête est analysée (parseur rdflib) et son algèbre inspectée.

    Seules SELECT, ASK et CONSTRUCT passent ; toute mise à jour est rejetée par le parseur de requêtes ;
    SERVICE (appel réseau) et FROM / FROM NAMED (graphe externe) sont interdits.
    """
    try:
        parsed = prepareQuery(PREFIXES + query)
    except Exception as e:
        raise SparqlError(f"Requête refusée : seules SELECT, ASK et CONSTRUCT sont acceptées ({e})") from e
    kind = CONSOLE_KINDS.get(parsed.algebra.name)
    if not kind:
        raise SparqlError(f"Forme de requête non autorisée : {parsed.algebra.name}")
    if parsed.algebra.get("datasetClause"):
        raise SparqlError("FROM / FROM NAMED interdits : la requête porte uniquement sur l'ontologie chargée")
    if any(n.name == "ServiceGraphPattern" for n in _nodes(parsed.algebra)):
        raise SparqlError("SERVICE interdit : aucune requête vers un serveur distant")
    return kind


@dataclass
class SelectResult:
    vars: list[str]
    rows: list[dict] = field(default_factory=list)


class SparqlError(Exception):
    pass


def query_kind(query: str) -> str:
    """Type de requête : SELECT, ASK, CONSTRUCT, DESCRIBE ou UPDATE."""
    body = re.sub(r"(?m)^\s*#.*$", "", query)  # lignes de commentaire (pas le # des IRI)
    body = re.sub(r"(?is)^\s*((PREFIX|BASE)\s+\S*\s*<[^>]*>\s*)*", "", body)
    m = re.match(r"\s*(\w+)", body)
    word = m.group(1).upper() if m else ""
    return word if word in {"SELECT", "ASK", "CONSTRUCT", "DESCRIBE"} else "UPDATE"


def _py(term):
    if isinstance(term, Literal):
        v = term.toPython()
        if isinstance(v, Decimal):
            return float(v)
        if isinstance(v, (int, float, bool, str)):
            return v
    return str(term)


class StoreClient:
    def __init__(self, store: GraphStore):
        self.store = store

    @property
    def version(self) -> int:  # change à chaque écriture : invalide le vocabulaire du NLP
        return self.store.version

    def _query(self, query: str):
        try:
            with self.store._lock:
                res = self.store.base.query(query)
                return res, (list(res) if res.type != "ASK" else None)
        except Exception as e:  # erreur de syntaxe, etc.
            raise SparqlError(str(e)) from e

    def select(self, query: str) -> SelectResult:
        res, rows = self._query(query)
        vars_ = [str(v) for v in res.vars]
        return SelectResult(vars_, [{v: _py(r[v]) for v in vars_ if r[v] is not None and not isinstance(r[v], BNode)}
                                    for r in rows])

    def ask(self, query: str) -> bool:
        return bool(self._query(query)[0].askAnswer)

    def graph(self, query: str) -> str:
        _, triples = self._query(query)
        out = Graph()
        out.bind("", "http://example.org/pharma#")
        for t in triples:
            out.add(t)
        return out.serialize(format="turtle")

    def update(self, query: str) -> None:
        try:
            self.store.update(query)
        except Exception as e:
            raise SparqlError(str(e)) from e

    def reset(self) -> None:
        self.store.load(reset=True)

    def console(self, query: str, limite: int = 500) -> dict:
        """Exécution contrôlée (lecture seule) pour la console ; même format que les consoles des autres modules."""
        kind = validate_readonly(query)
        with self.store._lock:
            res = self.store.base.query(PREFIXES + query)
            if kind == "ask":
                return {"type": "ask", "resultat": bool(res.askAnswer)}
            if kind == "graphe":
                g = Graph()
                g.bind("", "http://example.org/pharma#")
                for t in res:
                    g.add(t)
                return {"type": "graphe", "triplets": len(g), "turtle": g.serialize(format="turtle")}
            columns = [str(v) for v in res.vars]
            rows, truncated = [], False
            for i, row in enumerate(res):
                if i >= limite:
                    truncated = True
                    break
                rows.append({c: to_python(row[c]) for c in columns})
        return {"type": "select", "colonnes": columns, "lignes": rows, "tronque": truncated}

    def run(self, query: str):
        kind = query_kind(query)
        if kind == "SELECT":
            return kind, self.select(query)
        if kind == "ASK":
            return kind, self.ask(query)
        if kind in ("CONSTRUCT", "DESCRIBE"):
            return kind, self.graph(query)
        raise SparqlError("Requête de mise à jour non autorisée ici")
