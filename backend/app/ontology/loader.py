"""Chargement RDFLib de pharma.ttl, avec repli sur pharma.owl."""

from __future__ import annotations

import threading
from pathlib import Path

from rdflib import Graph

from app.b_config import Settings


class OntologyError(RuntimeError):
    pass


class OntologyStore:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.graph = Graph()
        self.loaded_from: Path | None = None
        self.using_working_copy = False
        self._lock = threading.RLock()

    def load(self) -> None:
        with self._lock:
            self.graph = Graph()
            working = self.settings.graph_path
            if working.exists() and working.stat().st_size > 0:
                self.graph.parse(working, format="turtle")
                self.loaded_from = working
                self.using_working_copy = True
            else:
                source, fmt = self._source()
                self.graph.parse(source, format=fmt)
                self.loaded_from = source
                self.using_working_copy = False
                self._write()
                self.using_working_copy = True
            if len(self.graph) == 0:
                raise OntologyError(f"Le graphe chargé depuis {self.loaded_from} ne contient aucun triplet.")

    def _source(self) -> tuple[Path, str]:
        ttl = self.settings.ontology_ttl
        owl = self.settings.ontology_owl
        if ttl.exists():
            return ttl, "turtle"
        if owl.exists():
            return owl, "xml"
        raise OntologyError(
            "Ontologie introuvable. Attendu : "
            f"{ttl} ou, à défaut, {owl}."
        )

    def _write(self) -> None:
        path = self.settings.graph_path
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        self.graph.serialize(destination=temporary, format="turtle", encoding="utf-8")
        temporary.replace(path)

    def save(self) -> None:
        with self._lock:
            self._write()

    def update_graph(self, mutator):
        with self._lock:
            snapshot = Graph()
            for triple in self.graph:
                snapshot.add(triple)
            try:
                result = mutator(self.graph)
                self._write()
                return result
            except Exception:
                self.graph = snapshot
                raise

    def query(self, sparql: str):
        with self._lock:
            try:
                result = self.graph.query(sparql)
            except Exception as exc:
                raise OntologyError(f"SPARQL invalide : {exc}") from exc
            kind = result.type
            if kind == "ASK":
                return {"kind": "ASK", "ask": bool(result.askAnswer), "vars": [], "rows": []}
            if kind == "CONSTRUCT":
                triples = [(s, p, o) for s, p, o in result]
                return {"kind": "CONSTRUCT", "ask": None, "vars": ["s", "p", "o"], "rows": triples}
            variables = [str(variable) for variable in result.vars]
            rows = []
            for row in result:
                rows.append({str(variable): row[variable] for variable in result.vars})
            return {"kind": "SELECT", "ask": None, "vars": variables, "rows": rows}

    @property
    def triple_count(self) -> int:
        with self._lock:
            return len(self.graph)
