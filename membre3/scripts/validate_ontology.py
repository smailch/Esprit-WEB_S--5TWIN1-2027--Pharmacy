"""Validation OWL avec HermiT (owlready2, nécessite Java).

1. Charge pharma.ttl + ontology-extension/*.ttl avec rdflib.
2. Correctif EN MÉMOIRE : xsd:date → xsd:dateTime (HermiT ne supporte pas xsd:date,
   absent de la table des datatypes OWL 2 → UnsupportedDatatypeException).
   pharma.ttl n'est pas modifié ; le problème est à remonter à l'équipe.
3. Lance HermiT : cohérence + classes inférées des patients + comptage par classe.
"""
import tempfile
from collections import Counter
from pathlib import Path

from _common import settings
from rdflib import XSD, Graph, Literal

import owlready2

NS = "http://example.org/pharma#"

g = Graph()
for f in settings.ontology_files():
    g.parse(f, format="turtle")
    print("chargé :", f.name)

patched = 0
for s, p, o in list(g):
    if o == XSD.date:
        g.remove((s, p, o)); g.add((s, p, XSD.dateTime)); patched += 1
    elif isinstance(o, Literal) and o.datatype == XSD.date:
        g.remove((s, p, o)); g.add((s, p, Literal(f"{o}T00:00:00", datatype=XSD.dateTime))); patched += 1
print(f"correctif xsd:date → xsd:dateTime appliqué en mémoire sur {patched} triplets")

tmp = Path(tempfile.mkdtemp()) / "pharma_patched.nt"
g.serialize(tmp, format="nt", encoding="utf-8")

world = owlready2.World()
with open(tmp, "rb") as fh:
    onto = world.get_ontology("http://example.org/pharma").load(fileobj=fh, format="ntriples")
pharma = world.get_namespace(NS)

patients = list(pharma.Patient.instances())
asserted = {p.name: {c.name for c in p.is_a if hasattr(c, "name")} for p in patients}

try:
    with onto:
        owlready2.sync_reasoner_hermit([onto], infer_property_values=False, debug=0)
except owlready2.OwlReadyInconsistentOntologyError:
    print("\n✗ INCOHÉRENCE détectée par HermiT")
    raise SystemExit(1)

inconsistent = list(world.inconsistent_classes())
print(f"\n✓ HermiT : ontologie cohérente, {len(inconsistent)} classe(s) insatisfiable(s)")

print("\nPatients — classe assertée → classe inférée")
for p in sorted(pharma.Patient.instances(), key=lambda x: x.name):
    now = {c.name for c in p.INDIRECT_is_a if hasattr(c, "name")}
    kind = "PatientEnfant" if "PatientEnfant" in now else "PatientAdulte" if "PatientAdulte" in now else "?"
    tag = "(inféré)" if kind not in asserted.get(p.name, set()) else "(asserté)"
    print(f"  {p.name:<22} âge {p.age!s:>4}  {', '.join(sorted(asserted.get(p.name, [])))} → {kind} {tag}")

counts = Counter()
for cname in ["Pathologie", "MaladieAigue", "MaladieChronique", "InfectionAigue", "DouleurAigue",
              "MaladieMetabolique", "InsuffisanceOrgane", "Patient", "PatientEnfant", "PatientAdulte",
              "Medecin", "Pharmacien"]:
    counts[cname] = len(list(getattr(pharma, cname).instances()))
print("\nIndividus par classe (après raisonnement)")
for k, v in counts.items():
    print(f"  {k:<20} {v}")

print("\nRemarque : HermiT ne détecte pas les contre-indications patient/médicament ;"
      " la chaîne estContreIndiquePour relie médicament → pathologie, l'alerte patient est faite en SPARQL.")
