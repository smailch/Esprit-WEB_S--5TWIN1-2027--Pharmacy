"""Couche d'accès SPARQL : une interface, deux implémentations.

- FusekiClient : HTTP (SPARQL 1.1 Protocol + Graph Store Protocol)
- RdflibClient : graphe rdflib en mémoire (tests, mode sans service)
"""
from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

import httpx
from rdflib import BNode, Graph, Literal, URIRef

XSD = "http://www.w3.org/2001/XMLSchema#"


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
    if term is None:
        return None
    if isinstance(term, Literal):
        v = term.toPython()
        if isinstance(v, Decimal):
            return float(v)
        if isinstance(v, (int, float, bool, str)):
            return v
        return str(term)
    return str(term)


def _from_json(b: dict):
    if b["type"] != "literal" and b["type"] != "typed-literal":
        return b["value"]
    dt = b.get("datatype", "")
    val = b["value"]
    if dt in (XSD + "integer", XSD + "int", XSD + "long", XSD + "nonNegativeInteger"):
        return int(val)
    if dt in (XSD + "decimal", XSD + "double", XSD + "float"):
        return float(val)
    if dt == XSD + "boolean":
        return val == "true"
    return val


class SparqlClient(ABC):
    @abstractmethod
    def select(self, query: str) -> SelectResult: ...

    @abstractmethod
    def ask(self, query: str) -> bool: ...

    @abstractmethod
    def graph(self, query: str) -> str:
        """CONSTRUCT / DESCRIBE → Turtle."""

    @abstractmethod
    def update(self, query: str) -> None: ...

    @abstractmethod
    def reset(self) -> None:
        """Recharge l'état initial (ontologie + extensions)."""

    def run(self, query: str):
        kind = query_kind(query)
        if kind == "SELECT":
            return kind, self.select(query)
        if kind == "ASK":
            return kind, self.ask(query)
        if kind in ("CONSTRUCT", "DESCRIBE"):
            return kind, self.graph(query)
        raise SparqlError("Requête de mise à jour non autorisée ici")


class RdflibClient(SparqlClient):
    def __init__(self, files: list[Path]):
        self.files = files
        self.g = Graph()
        self.reset()

    def reset(self) -> None:
        g = Graph()
        for f in self.files:
            g.parse(f, format="turtle")
        self.g = g

    def select(self, query):
        try:
            res = self.g.query(query)
        except Exception as e:  # erreur de syntaxe, etc.
            raise SparqlError(str(e)) from e
        vars_ = [str(v) for v in res.vars]
        rows = [{v: _py(row[v]) for v in vars_ if row[v] is not None and not isinstance(row[v], BNode)}
                for row in res]
        return SelectResult(vars_, rows)

    def ask(self, query):
        try:
            return bool(self.g.query(query).askAnswer)
        except Exception as e:
            raise SparqlError(str(e)) from e

    def graph(self, query):
        try:
            res = self.g.query(query)
        except Exception as e:
            raise SparqlError(str(e)) from e
        out = Graph()
        out.bind("", "http://example.org/pharma#")
        for t in res:
            out.add(t)
        return out.serialize(format="turtle")

    def update(self, query):
        try:
            self.g.update(query)
        except Exception as e:
            raise SparqlError(str(e)) from e


class FusekiClient(SparqlClient):
    def __init__(self, url: str, dataset: str, files: list[Path], auth=None):
        self.base = f"{url.rstrip('/')}/{dataset}"
        self.files = files
        self.http = httpx.Client(timeout=30, auth=auth)

    def _query(self, query: str, accept: str) -> httpx.Response:
        try:
            r = self.http.post(f"{self.base}/query", data={"query": query}, headers={"Accept": accept})
        except httpx.HTTPError as e:
            raise SparqlError(f"Fuseki injoignable : {e}") from e
        if r.status_code >= 400:
            raise SparqlError(r.text[:500])
        return r

    def select(self, query):
        data = self._query(query, "application/sparql-results+json").json()
        vars_ = data["head"]["vars"]
        rows = [{k: _from_json(v) for k, v in b.items() if v["type"] != "bnode"}
                for b in data["results"]["bindings"]]
        return SelectResult(vars_, rows)

    def ask(self, query):
        return bool(self._query(query, "application/sparql-results+json").json()["boolean"])

    def graph(self, query):
        return self._query(query, "text/turtle").text

    def update(self, query):
        try:
            r = self.http.post(f"{self.base}/update", data={"update": query})
        except httpx.HTTPError as e:
            raise SparqlError(f"Fuseki injoignable : {e}") from e
        if r.status_code >= 400:
            raise SparqlError(r.text[:500])

    def is_empty(self) -> bool:
        return not self.ask("ASK { ?s ?p ?o }")

    def reset(self) -> None:
        """Graph Store Protocol : PUT du fichier principal, POST des extensions."""
        for i, f in enumerate(self.files):
            method = self.http.put if i == 0 else self.http.post
            r = method(f"{self.base}/data?default", content=f.read_bytes(),
                       headers={"Content-Type": "text/turtle; charset=utf-8"})
            if r.status_code >= 400:
                raise SparqlError(f"Chargement de {f.name} refusé : {r.text[:300]}")


def build_client(settings) -> SparqlClient:
    files = settings.ontology_files()
    if settings.sparql_backend == "fuseki":
        client = FusekiClient(settings.fuseki_url, settings.fuseki_dataset, files,
                              auth=(settings.fuseki_user, settings.fuseki_password))
        if client.is_empty():
            client.reset()
        return client
    return RdflibClient(files)
