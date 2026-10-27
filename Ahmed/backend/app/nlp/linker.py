"""Étape 3 — Entity linking sur l'ontologie : spaCy PhraseMatcher (exact) + RapidFuzz (fautes de frappe)."""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass

from rapidfuzz import fuzz, process
from spacy.matcher import PhraseMatcher
from spacy.util import filter_spans

from app.nlp.normalize import stem
from app.nlp.vocabulary import Concept, Vocabulary

# Mots qui ne doivent jamais être rapprochés par similarité
STOP = set("""quel quelle quels quelle qui que quoi de du des la le les un une est sont a ont pour avec en
dans sur par et ou il elle t y combien liste patient patiente medecin pharmacien maladie pathologie
medicament ordonnance prescription plus moins entre an ans age sexe tous toute toutes the sont-il
code cim souffre souffrent atteint atteinte contre indique traitement suit sans pas ne aucun""".split())

PRESC = re.compile(r"\b(?:ordonnance|ordo|prescription|presc)\s+(?:n\s+|no\s+|numero\s+)?0*(\d{1,3})\b")
FUZZY_CUTOFF = 85


@dataclass
class Entity:
    text: str
    start: int
    end: int
    type: str
    id: str
    label: str
    method: str          # exact | similarité | motif
    score: float
    candidates: list | None = None

    def dict(self):
        return asdict(self)


class Linker:
    def __init__(self, nlp, vocab: Vocabulary):
        self.nlp = nlp
        self.vocab = vocab
        self.matcher = PhraseMatcher(nlp.vocab, attr="NORM")
        self.keys = list(vocab.phrases)
        for i, phrase in enumerate(self.keys):
            self.matcher.add(str(i), [self._doc(phrase)])

    def _doc(self, text: str):
        doc = self.nlp.make_doc(text)
        for t in doc:
            t.norm_ = stem(t.text)
        return doc

    def _entity(self, span_text, start, end, key, method, score):
        concepts = sorted(self.vocab.phrases[key], key=lambda c: (c.type, c.id))
        c: Concept = concepts[0]
        ent = Entity(span_text, start, end, c.type, c.id, c.label, method, round(score, 2))
        if len({(x.type, x.id) for x in concepts}) > 1:
            ent.candidates = [{"type": x.type, "id": x.id, "label": x.label} for x in concepts]
        return ent

    def link(self, original: str, normalized: str) -> list[Entity]:
        doc = self._doc(normalized)
        entities: list[Entity] = []

        # Prescriptions : motif « ordonnance 3 », « presc 003 »…
        for m in PRESC.finditer(normalized):
            pid = f"Presc_{int(m.group(1)):03d}"
            if pid in self.vocab.prescriptions:
                entities.append(Entity(original[m.start():m.end()], m.start(), m.end(), "PRESCRIPTION",
                                       pid, f"Ordonnance {pid[-3:]}", "motif", 1.0))
        taken = {i for e in entities for i in range(e.start, e.end)}

        spans = [doc[s:e] for _, s, e in self.matcher(doc)]
        spans = [s for s in filter_spans(spans)
                 if not any(i in taken for i in range(s.start_char, s.end_char))]
        covered = set()
        for s in spans:
            key = " ".join(t.norm_ for t in s)
            entities.append(self._entity(original[s.start_char:s.end_char], s.start_char, s.end_char,
                                         key, "exact", 1.0))
            covered.update(range(s.start, s.end))

        # Tolérance aux fautes : n-grammes non couverts comparés au vocabulaire
        best = []
        for n in (3, 2, 1):
            for i in range(len(doc) - n + 1):
                toks = doc[i:i + n]
                if any(j in covered for j in range(i, i + n)) or toks[0].norm_ in STOP or toks[-1].norm_ in STOP:
                    continue
                if any(t.is_digit for t in toks):
                    continue
                q = " ".join(t.norm_ for t in toks)
                if len(q) < 4:
                    continue
                hit = process.extractOne(q, self.keys, scorer=fuzz.ratio, score_cutoff=FUZZY_CUTOFF)
                if hit:
                    best.append((hit[1], n, i, hit[0]))
        for score, n, i, key in sorted(best, key=lambda x: (-x[0], -x[1])):
            if any(j in covered for j in range(i, i + n)):
                continue
            span = doc[i:i + n]
            entities.append(self._entity(original[span.start_char:span.end_char], span.start_char,
                                         span.end_char, key, "similarité", score / 100))
            covered.update(range(i, i + n))
        return sorted(entities, key=lambda e: e.start)
