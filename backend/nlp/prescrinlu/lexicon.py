"""Étape 2 — Dictionnaires métier générés automatiquement depuis l'ontologie (requêtes SPARQL).

Chaque entrée associe un alias normalisé (« ali », « dr benali », « glycemie »…) à un individu réel
(:Patient_Ali, :Dr_Benali…), à une classe réelle (:Allergie…) ou au libellé réel d'un examen (« Glycémie à jeun »).
Le dictionnaire est reconstruit à chaque question : une donnée créée par le CRUD est reconnue aussitôt.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.graph_store import store

from .preprocessing import normalize


@dataclass
class Entry:
    type: str      # PATIENT, MEDECIN, PHARMACIEN, PRESCRIPTION, MEDICAMENT, MOLECULE, PATHOLOGIE, TYPE_PRESCRIPTION, TYPE_DONNEE, MESURE
    id: str        # identifiant local de l'URI (ou libellé exact pour MESURE)
    label: str


@dataclass
class Lexicon:
    aliases: dict[str, list[Entry]] = field(default_factory=dict)
    by_type: dict[str, list[Entry]] = field(default_factory=dict)
    ids: dict[str, Entry] = field(default_factory=dict)  # identifiant local en minuscules → entrée

    def add(self, entry: Entry, *aliases: str):
        self.by_type.setdefault(entry.type, [])
        if entry not in self.by_type[entry.type]:
            self.by_type[entry.type].append(entry)
        if entry.type not in ("MESURE", "TYPE_PRESCRIPTION", "TYPE_DONNEE"):
            self.ids[entry.id.lower()] = entry
        for a in aliases:
            a = normalize(a or "")
            if len(a) < 2:
                continue
            bucket = self.aliases.setdefault(a, [])
            if entry not in bucket:
                bucket.append(entry)


def _plural(word: str) -> str:
    return " ".join(w if w.endswith(("s", "x")) or len(w) < 3 else w + "s" for w in word.split())


def _clean(label: str) -> str:
    return re.sub(r"\s*\(.*\)", "", label).strip()


# Variantes métier absentes des libellés (vocabulaire du domaine, pas de nouvelles données).
TYPE_SYNONYMS = {
    "PrescriptionSimple": ["simple", "simples", "non renouvelable", "non renouvelables", "ponctuelle", "ponctuelles"],
    "PrescriptionRenouvelable": ["renouvelable", "renouvelables", "a renouveler"],
    "PrescriptionUrgente": ["urgente", "urgentes", "urgence", "en urgence"],
    "PrescriptionNormale": ["normale", "normales"],
    "RenouvellementCourt": ["renouvellement court", "renouvellements courts", "court terme"],
    "RenouvellementLong": ["renouvellement long", "renouvellements longs", "long terme"],
    "DonneeClinique": ["donnee clinique", "donnees cliniques", "dossier clinique", "dossier medical"],
    "ExamenClinique": ["examen", "examens", "mesure", "mesures"],
    "HistoriqueMedical": ["historique", "historique medical", "historiques"],
    "SigneVital": ["signe vital", "signes vitaux", "constante", "constantes"],
    "AnalyseBiologique": ["analyse", "analyses", "bilan", "bilans", "bilan biologique", "analyses biologiques"],
    "Allergie": ["allergie", "allergies", "allergique", "allergiques"],
    "Antecedent": ["antecedent", "antecedents", "antecedent medical", "antecedents medicaux"],
}
STOPWORDS = {"de", "la", "le", "les", "des", "du", "a", "jeun", "et"}


def build() -> Lexicon:
    lex = Lexicon()
    # Personnes (lecture seule) : nécessaires aux relations concernePatient / prescritPar / estDelivreePar / estDonneeDe.
    for r in store.select("""
SELECT ?x ?label ?nom ?role WHERE {
  VALUES ?role { :Patient :Medecin :Pharmacien }
  ?x a ?role ; rdfs:label ?label . OPTIONAL { ?x :nom ?nom }
}"""):
        kind = {"Patient": "PATIENT", "Medecin": "MEDECIN", "Pharmacien": "PHARMACIEN"}[r["role"]]
        label, nom = r["label"], r["nom"] or ""
        local = r["x"].split("_", 1)[-1]
        aliases = [r["x"], r["x"].replace("_", " "), label]
        if kind == "PATIENT":
            first = label.replace(nom, "").strip() if nom and nom in label else label.split(" ")[0]
            aliases += [nom, first, local, f"patient {local}", f"patiente {local}"]
        elif kind == "MEDECIN":
            aliases += [nom, f"dr {nom}", f"medecin {nom}", local]
        else:
            aliases += [nom, f"pharmacien {nom}", f"pharmacienne {nom}", local]
        lex.add(Entry(kind, r["x"], label), *aliases)

    for r in store.select("SELECT ?x ?label WHERE { ?x a :Prescription ; rdfs:label ?label }"):
        lex.add(Entry("PRESCRIPTION", r["x"], r["label"]), r["x"], r["x"].replace("_", " "))

    for r in store.select("SELECT ?x ?label ?nom WHERE { ?x a :Medicament ; rdfs:label ?label . OPTIONAL { ?x :nomCommercial ?nom } }"):
        spaced = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", r["x"])  # IbuprofeneMylan → Ibuprofene Mylan
        lex.add(Entry("MEDICAMENT", r["x"], r["label"]), r["x"], spaced, r["label"], r["nom"])

    for r in store.select("SELECT ?x ?label WHERE { ?x a :Molecule , owl:NamedIndividual ; rdfs:label ?label }"):
        lex.add(Entry("MOLECULE", r["x"], r["label"]), r["x"], r["label"], _clean(r["label"]))

    pathologies = store.select("SELECT ?x ?label WHERE { ?x a :Pathologie , owl:NamedIndividual ; rdfs:label ?label }")
    firsts = [normalize(_clean(r["label"])).split()[0] for r in pathologies]
    for r, first in zip(pathologies, firsts):
        extra = [first] if len(first) >= 5 and firsts.count(first) == 1 else []
        lex.add(Entry("PATHOLOGIE", r["x"], r["label"]), r["x"], r["label"], _clean(r["label"]), *extra)

    for root, kind in (("Prescription", "TYPE_PRESCRIPTION"), ("DonneeClinique", "TYPE_DONNEE")):
        for r in store.select(f"""
SELECT ?x ?label WHERE {{
  GRAPH <urn:pharma:base> {{ ?x rdfs:subClassOf* :{root} }}
  ?x rdfs:label ?label . FILTER(isIRI(?x))
}}"""):
            if r["x"] in ("Prescription", "DonneeClinique"):
                continue  # la classe racine désigne l'objet de la question, pas un filtre de type
            label = _clean(r["label"])
            lex.add(Entry(kind, r["x"], r["label"]), label, _plural(label), *TYPE_SYNONYMS.get(r["x"], []))

    # Examens cliniques : le libellé réel (« Clairance de la créatinine ») et ses mots significatifs.
    for r in store.select("SELECT DISTINCT ?label WHERE { ?d a :ExamenClinique ; rdfs:label ?label }"):
        words = [w for w in normalize(r["label"]).split() if w not in STOPWORDS]
        significant = [w for w in words if len(w) >= 6] + words[:1]
        lex.add(Entry("MESURE", r["label"], r["label"]), r["label"], *significant)
    return lex
