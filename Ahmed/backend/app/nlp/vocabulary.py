"""Vocabulaire d'entités construit DYNAMIQUEMENT depuis le triplestore (+ synonymes du fichier JSON).

Chaque entrée : phrase normalisée → (type, id, libellé). Un patient créé via l'API est reconnu
par le NLP dès la question suivante (cache invalidé par client.version).
"""
from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from app.config.ontology_mapping import PREFIXES
from app.nlp.normalize import stem_phrase
from app.sparql.client import SparqlClient

DATA = Path(__file__).resolve().parents[2] / "nlp" / "data"


@dataclass(frozen=True)
class Concept:
    type: str      # PATHOLOGIE, TYPE, PATIENT, MEDECIN, PHARMACIEN, MEDICAMENT, MOLECULE, SPECIALITE, CLASSE
    id: str        # nom local (ou valeur pour SPECIALITE)
    label: str


Q = PREFIXES + """
SELECT DISTINCT ?type ?id ?label ?nom ?extra WHERE {
  {
    ?s a/rdfs:subClassOf* :Pathologie ; rdfs:label ?label . BIND("PATHOLOGIE" AS ?type)
  } UNION {
    ?s a/rdfs:subClassOf* :Patient ; rdfs:label ?label . OPTIONAL { ?s :nom ?nom } BIND("PATIENT" AS ?type)
  } UNION {
    ?s a :Medecin ; rdfs:label ?label . OPTIONAL { ?s :nom ?nom } OPTIONAL { ?s :specialite ?extra }
    BIND("MEDECIN" AS ?type)
  } UNION {
    ?s a :Pharmacien ; rdfs:label ?label . OPTIONAL { ?s :nom ?nom } OPTIONAL { ?s :specialite ?extra }
    BIND("PHARMACIEN" AS ?type)
  } UNION {
    ?s a/rdfs:subClassOf* :Medicament ; rdfs:label ?label . OPTIONAL { ?s :nomCommercial ?nom }
    BIND("MEDICAMENT" AS ?type)
  } UNION {
    ?s a/rdfs:subClassOf* :Molecule ; rdfs:label ?label . BIND("MOLECULE" AS ?type)
  } UNION {
    ?s rdfs:subClassOf* :Pathologie ; rdfs:label ?label . FILTER(?s != :Pathologie) BIND("TYPE" AS ?type)
  } UNION {
    ?s a/rdfs:subClassOf* :Prescription ; rdfs:label ?label . BIND("PRESCRIPTION" AS ?type)
  }
  BIND(STRAFTER(STR(?s), "#") AS ?id)
}"""


class Vocabulary:
    def __init__(self, client: SparqlClient):
        self.phrases: dict[str, set[Concept]] = defaultdict(set)
        self.prescriptions: set[str] = set()
        rows = client.select(Q).rows
        for r in rows:
            t, id_, label = r["type"], r["id"], r["label"]
            if t == "PRESCRIPTION":
                self.prescriptions.add(id_)
                continue
            c = Concept(t, id_, label)
            self.add(label, c)
            if t == "PATIENT":
                first = label.split()[0]
                self.add(first, c)
                if r.get("nom"):
                    self.add(r["nom"], c)
            elif t in ("MEDECIN", "PHARMACIEN"):
                if r.get("nom"):
                    self.add(r["nom"], c)
                    prefix = ["dr", "docteur"] if t == "MEDECIN" else ["pharmacien", "pharmacienne"]
                    for p in prefix:
                        self.add(f"{p} {r['nom']}", c)
                if r.get("extra"):
                    self.add(r["extra"], Concept("SPECIALITE", r["extra"], r["extra"]))
            elif t == "MEDICAMENT" and r.get("nom"):
                self.add(r["nom"], c)
            elif t == "MOLECULE":
                self.add(label.split(" (")[0], c)

        labels = {(c.type, c.id): c.label for cs in self.phrases.values() for c in cs}
        syn = json.loads((DATA / "synonymes.json").read_text(encoding="utf-8"))
        for t, mapping in syn.items():
            for phrase, target in mapping.items():
                label = labels.get((t, target), target)
                self.add(phrase, Concept(t, target, label))

    def add(self, phrase: str, concept: Concept):
        key = stem_phrase(phrase)
        if key:
            self.phrases[key].add(concept)
