"""Graphe RDF de l'application.

Deux graphes nommés dans un même Dataset :
- urn:pharma:base      → triplets déclarés (ontologie + modifications CRUD) ;
- urn:pharma:inferred  → triplets ajoutés par le raisonneur OWL 2 RL (owlrl).
Les requêtes de lecture portent sur l'union des deux ; les mises à jour ne touchent que le graphe de base.
"""
from __future__ import annotations

import threading
from decimal import Decimal

import owlrl
from rdflib import BNode, Dataset, Graph, Literal, Namespace, URIRef
from rdflib.namespace import OWL, RDF, RDFS, XSD

from . import config

PH = Namespace(config.PHARMA_NS)

PREFIXES = """PREFIX :     <http://example.org/pharma#>
PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl:  <http://www.w3.org/2002/07/owl#>
PREFIX xsd:  <http://www.w3.org/2001/XMLSchema#>
"""


def to_python(term):
    """Convertit un terme RDF en valeur JSON simple."""
    if term is None:
        return None
    if isinstance(term, URIRef):
        s = str(term)
        return s[len(config.PHARMA_NS):] if s.startswith(config.PHARMA_NS) else s
    if isinstance(term, BNode):
        return f"_:{term}"
    value = term.toPython()
    if isinstance(value, Decimal):
        return float(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


class GraphStore:
    def __init__(self):
        self._lock = threading.RLock()
        self.ds: Dataset | None = None
        self.version = 0  # incrémenté à chaque changement : le NLP reconstruit alors son dictionnaire d'entités
        self.load()

    # ---------- chargement / inférence ----------
    def load(self, reset: bool = False):
        with self._lock:
            if reset and config.RUNTIME_PATH.exists():
                config.RUNTIME_PATH.unlink()
            source = config.RUNTIME_PATH if config.RUNTIME_PATH.exists() else config.ONTOLOGY_PATH
            self.ds = Dataset(default_union=True)
            self.base = self.ds.graph(URIRef(config.BASE_GRAPH))
            self.inferred = self.ds.graph(URIRef(config.INFERRED_GRAPH))
            self.base.parse(source, format="turtle")
            self.source = source
            self._infer()
            self.version += 1

    def _infer(self):
        closure = Graph()
        for t in self.base:
            closure.add(t)
        owlrl.DeductiveClosure(owlrl.OWLRL_Semantics, axiomatic_triples=False, datatype_axioms=False).expand(closure)
        self.inferred.remove((None, None, None))
        for s, p, o in closure:
            # On ne garde que les nouveautés utiles (pas de sameAs réflexif ni de littéraux en sujet).
            if isinstance(s, Literal) or (s, p, o) in self.base:
                continue
            if p == OWL.sameAs and s == o:
                continue
            self.inferred.add((s, p, o))

    def save(self):
        config.RUNTIME_PATH.parent.mkdir(parents=True, exist_ok=True)
        self.base.serialize(config.RUNTIME_PATH, format="turtle")

    # ---------- requêtes ----------
    def select(self, sparql: str) -> list[dict]:
        with self._lock:
            result = self.ds.query(PREFIXES + sparql)
            return [{str(v): to_python(row[v]) for v in result.vars} for row in result]

    def ask(self, sparql: str) -> bool:
        with self._lock:
            return bool(self.ds.query(PREFIXES + sparql).askAnswer)

    def construct(self, sparql: str) -> Graph:
        with self._lock:
            return self.ds.query(PREFIXES + sparql).graph

    def update(self, sparql: str):
        """Applique une mise à jour au graphe de base, puis recalcule l'inférence et sauvegarde."""
        with self._lock:
            self.base.update(PREFIXES + sparql)
            self._infer()
            self.save()
            self.version += 1

    def exists(self, local_id: str, cls: str | None = None) -> bool:
        uri = PH[local_id]
        with self._lock:
            if cls:
                t = (uri, RDF.type, PH[cls])
                return t in self.base or t in self.inferred
            return any(self.base.triples((uri, None, None)))

    def stats(self) -> dict:
        with self._lock:
            return {"triplets_declares": len(self.base), "triplets_inferes": len(self.inferred), "source": self.source.name}


store = GraphStore()

__all__ = ["store", "PH", "RDF", "RDFS", "OWL", "XSD", "PREFIXES", "to_python"]
