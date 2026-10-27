"""Étape 3 — Reconnaissance des entités : spaCy EntityRuler + RapidFuzz.

Le dictionnaire (gazetteer) est construit AUTOMATIQUEMENT à partir de l'ontologie :
labels, noms commerciaux et identifiants des molécules, médicaments, pathologies et classes.
Une donnée ajoutée par le CRUD est donc reconnue immédiatement, sans ré-entraînement.

1. EntityRuler (correspondance exacte, la plus longue d'abord : « ibuprofene mylan » > « ibuprofene ») ;
2. RapidFuzz sur les mots restants pour corriger les fautes (« ibuprophene » → Ibuprofène).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from rapidfuzz import fuzz, process
from spacy.lang.fr.stop_words import STOP_WORDS
from spacy.language import Language
from spacy.pipeline import EntityRuler

from .normalizer import get_nlp, normalize

# Jeton de remplacement (« délexicalisation ») utilisé par le classifieur d'intention.
PLACEHOLDER = {"Molecule": "xmol", "Medicament": "xmed", "Pathologie": "xpatho", "Classe": "xclasse"}

# Synonymes métier (connaissances du domaine) → identifiant de l'ontologie.
SYNONYMES = {
    "Classe": {
        "Antibiotique": ["antibio", "antibios", "antibiotique", "antibiotiques", "anti biotique"],
        "Antalgique": ["antalgique", "antalgiques", "antidouleur", "antidouleurs", "anti douleur", "anti douleurs", "analgesique", "analgesiques"],
        "AntalgiqueOpioide": ["opioide", "opioides", "antalgique opioide", "antalgiques opioides", "morphinique", "morphiniques"],
        "AntalgiqueNonOpioide": ["non opioide", "non opioides", "antalgique non opioide", "antalgiques non opioides"],
        "Penicilline": ["penicilline", "penicillines"],
        "Macrolide": ["macrolide", "macrolides"],
        "Molecule": ["molecule", "molecules", "principe actif", "principes actifs", "substance active", "substances actives"],
    },
    "Pathologie": {
        "UlcereGastroduodenal": ["ulcere", "ulceres", "ulcere gastrique", "ulcere de l'estomac", "ulcere a l'estomac"],
        "InsuffisanceRenale": ["insuffisance renale", "insuffisant renal", "probleme de rein", "problemes de reins", "maladie renale", "reins"],
        "InsuffisanceHepatique": ["insuffisance hepatique", "probleme de foie", "problemes de foie", "maladie du foie", "foie"],
        "DiabeteType2": ["diabete", "diabetique", "diabete de type 2"],
        "DouleurDentaire": ["mal de dent", "mal aux dents", "rage de dent", "douleur dentaire", "dents"],
        "Migraine": ["migraine", "migraines", "mal de tete", "maux de tete"],
        "Angine": ["angine", "angines", "mal de gorge"],
        "Pneumonie": ["pneumonie", "infection pulmonaire"],
        "Obesite": ["obesite", "surpoids"],
    },
    "Molecule": {
        "Aspirine": ["aspirine", "acide acetylsalicylique"],
        "Metformine": ["metformine"],
    },
}

# Les mots génériques ne doivent pas être pris pour des entités par la recherche floue.
# (« molecule » est volontairement une classe ; le vocabulaire d'entraînement est ajouté au chargement du modèle.)
MOTS_DOMAINE = {
    "medicament", "medicaments", "generique", "generiques", "princeps", "ordonnance", "prix", "contre", "indication",
    "indications", "indique", "effet", "effets", "secondaire", "secondaires", "grave", "graves", "interaction",
    "interactions", "dinars", "dinar", "comprime", "comprimes", "gelule", "gelules", "sachet", "sirop", "combien",
    "liste", "affiche", "montre", "donne", "quels", "quelles", "existe", "alternative", "equivalent", "moins", "cher",
    "chers", "dose", "dosage", "forme", "code", "maximale", "prendre", "eviter", "provoquer", "contient", "contiennent",
}


@dataclass
class Entity:
    id: str
    type: str          # Molecule | Medicament | Pathologie | Classe
    label: str
    texte: str         # texte tel qu'écrit par l'utilisateur
    start: int         # indices de jetons [start, end)
    end: int
    score: int = 100
    corrige: bool = False

    def as_dict(self):
        return {"id": self.id, "type": self.type, "label": self.label, "texte": self.texte, "score": self.score, "corrige": self.corrige}


@dataclass
class Gazetteer:
    surfaces: dict[str, tuple[str, str]] = field(default_factory=dict)   # forme normalisée → (type, id)
    labels: dict[tuple[str, str], str] = field(default_factory=dict)     # (type, id) → label lisible

    def add(self, surface: str, typ: str, ident: str):
        s = normalize(surface)
        if len(s) >= 3 and s not in self.surfaces:
            self.surfaces[s] = (typ, ident)


def _camel_words(ident: str) -> str:
    return " ".join(re.findall(r"[A-Z][a-z0-9]*|[a-z0-9]+", ident))


def build_gazetteer(store) -> Gazetteer:
    """Construit le dictionnaire depuis le graphe RDF (requête SPARQL)."""
    g = Gazetteer()
    rows = store.select("""
SELECT ?s ?type ?label ?nom WHERE {
  VALUES ?type { :Medicament :Molecule :Pathologie }
  ?s a ?type ; rdfs:label ?label .
  OPTIONAL { ?s :nomCommercial ?nom }
}""")
    # Les médicaments d'abord : en cas d'égalité, le nom commercial l'emporte.
    rows.sort(key=lambda r: {"Medicament": 0, "Molecule": 1, "Pathologie": 2}[r["type"]])
    for r in rows:
        typ, ident = r["type"], r["s"]
        g.labels[(typ, ident)] = r["label"]
        label = r["label"]
        g.add(label, typ, ident)
        g.add(re.sub(r"\s*\(.*?\)", "", label), typ, ident)                 # « Aspirine (acide …) » → « Aspirine »
        g.add(re.sub(r"\s+\d+([.,]\d+)?\s*(mg|g|ml)\b.*$", "", label, flags=re.I), typ, ident)  # « Advil 400 mg » → « Advil »
        if r.get("nom"):
            g.add(r["nom"], typ, ident)
        g.add(_camel_words(ident), typ, ident)
    for typ, mapping in SYNONYMES.items():
        for ident, forms in mapping.items():
            if typ == "Classe":
                g.labels[(typ, ident)] = ident
            for f in forms:
                g.add(f, typ, ident)
    return g


class EntityRecognizer:
    def __init__(self, store, known_words: set[str] | None = None):
        self.store = store
        self.known_words = set(STOP_WORDS) | MOTS_DOMAINE | (known_words or set())
        self._version = None
        self._nlp: Language | None = None
        self.gaz: Gazetteer | None = None

    def _refresh(self):
        if self._version == self.store.version and self._nlp is not None:
            return
        self.gaz = build_gazetteer(self.store)
        base = get_nlp()
        # Un pipeline spaCy léger dédié : tokeniseur français + EntityRuler (motifs sur l'attribut LOWER).
        nlp = Language(base.vocab)
        nlp.tokenizer = base.tokenizer
        ruler: EntityRuler = nlp.add_pipe("entity_ruler", config={"phrase_matcher_attr": "LOWER", "overwrite_ents": True})
        ruler.add_patterns([{"label": typ, "pattern": s, "id": ident} for s, (typ, ident) in self.gaz.surfaces.items()])
        self._nlp = nlp
        self._choices = list(self.gaz.surfaces.keys())
        self._version = self.store.version

    def label(self, typ, ident):
        return self.gaz.labels.get((typ, ident), ident)

    def recognize(self, doc) -> list[Entity]:
        """`doc` : Doc spaCy du texte normalisé (voir normalizer.tokenize)."""
        self._refresh()
        ruled = self._nlp(doc.text)
        ents: list[Entity] = []
        for e in ruled.ents:
            ents.append(Entity(id=e.ent_id_, type=e.label_, label=self.label(e.label_, e.ent_id_), texte=e.text, start=e.start, end=e.end))

        # --- Correction des fautes : RapidFuzz sur les fenêtres de 1 à 2 mots non reconnus ---
        covered = {i for e in ents for i in range(e.start, e.end)}
        toks = list(ruled)

        def candidate(i):
            t = toks[i].text
            return i not in covered and t.isalpha() and len(t) >= 4 and t not in self.known_words

        i = 0
        while i < len(toks):
            if not candidate(i):
                i += 1
                continue
            best = None
            for n in (2, 1):
                if i + n > len(toks) or not all(candidate(j) for j in range(i, i + n)):
                    continue
                window = " ".join(toks[j].text for j in range(i, i + n))
                cutoff = 80 if len(window) >= 7 else 86
                m = process.extractOne(window, self._choices, scorer=fuzz.ratio, score_cutoff=cutoff)
                if m and (best is None or m[1] > best[1]):
                    best = (m[0], m[1], n, window)
            if best:
                surface, score, n, window = best
                typ, ident = self.gaz.surfaces[surface]
                ents.append(Entity(id=ident, type=typ, label=self.label(typ, ident), texte=window, start=i, end=i + n, score=round(score), corrige=True))
                covered.update(range(i, i + n))
                i += n
            else:
                i += 1
        ents.sort(key=lambda e: e.start)
        return ents, ruled


def mask(doc, ents: list[Entity]) -> str:
    """Remplace chaque entité par son jeton de type et lemmatise le reste (texte d'entrée du classifieur)."""
    by_start = {e.start: e for e in ents}
    out, i = [], 0
    lemmas = [t.lemma_ or t.text for t in doc]
    while i < len(doc):
        if i in by_start:
            out.append(PLACEHOLDER[by_start[i].type])
            i = by_start[i].end
            continue
        tok = doc[i]
        # Seuls les chiffres comptent comme nombres (spaCy considère aussi « un » comme nombre).
        out.append("xnombre" if any(c.isdigit() for c in tok.text) else lemmas[i].lower())
        i += 1
    return " ".join(out)
