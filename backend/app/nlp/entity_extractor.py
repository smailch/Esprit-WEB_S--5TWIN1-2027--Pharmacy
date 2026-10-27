"""Extraction d'entités par le lexique de l'ontologie.

spaCy fournit le PhraseMatcher (et la lemmatisation si fr_core_news_sm
est installé). Sans spaCy, le même lexique est parcouru par expressions régulières.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from rdflib import URIRef
from rdflib.namespace import RDF, RDFS

from app.nlp.preprocessing import camel_fold, fold, normalize
from app.ontology.vocab import PHARMA_NS

_MODE: str | None = None
_NLP = None

_KIND_BY_ROOT = (
    ("effet", "EffetSecondaire"),
    ("contre_indication", "ContreIndication"),
    ("medicament", "Medicament"),
    ("molecule", "Molecule"),
    ("pathologie", "Pathologie"),
)


@dataclass
class Alias:
    text: str
    kind: str
    ident: str
    uri: str
    label: str


@dataclass
class Entity:
    kind: str
    ident: str
    uri: str
    label: str
    text: str
    start: int
    end: int

    def as_dict(self) -> dict:
        return {
            "kind": self.kind,
            "id": self.ident,
            "uri": self.uri,
            "label": self.label,
            "text": self.text,
        }


def analyzer_mode() -> str:
    _engine()
    return _MODE or "lexical"


def _engine():
    global _MODE, _NLP
    if _MODE is not None:
        return _NLP
    try:
        import spacy
    except ImportError:
        _MODE = "lexical"
        _NLP = None
        return None
    for model_name in ("fr_core_news_sm", "fr_core_news_md"):
        try:
            _NLP = spacy.load(model_name)
            _MODE = model_name
            return _NLP
        except Exception:
            continue
    _NLP = spacy.blank("fr")
    _MODE = "blank"
    return _NLP


def _ancestors(graph, type_uri: URIRef) -> set[URIRef]:
    seen: set[URIRef] = set()
    stack = [type_uri]
    while stack:
        current = stack.pop()
        if current in seen:
            continue
        seen.add(current)
        for parent in graph.objects(current, RDFS.subClassOf):
            if isinstance(parent, URIRef):
                stack.append(parent)
    return seen


def _kind_of(graph, type_uri: URIRef) -> str | None:
    ancestors = _ancestors(graph, type_uri)
    for kind, root in _KIND_BY_ROOT:
        if URIRef(PHARMA_NS + root) in ancestors:
            return kind
    return None


def build_aliases(graph) -> list[Alias]:
    aliases: list[Alias] = []
    seen = set()
    for subject, type_uri in graph.subject_objects(RDF.type):
        if not isinstance(subject, URIRef) or not isinstance(type_uri, URIRef):
            continue
        if not str(subject).startswith(PHARMA_NS):
            continue
        kind = _kind_of(graph, type_uri)
        if kind is None:
            continue
        ident = str(subject)[len(PHARMA_NS) :]
        labels = [str(value) for value in graph.objects(subject, RDFS.label)]
        commercial = [str(value) for value in graph.objects(subject, URIRef(PHARMA_NS + "nomCommercial"))]
        surfaces = labels + commercial + [ident.replace("_", " "), camel_fold(ident)]
        for surface in surfaces:
            text = normalize(surface)
            if len(text) < 3:
                continue
            key = (text, kind, ident)
            if key in seen:
                continue
            seen.add(key)
            label = labels[0] if labels else ident
            aliases.append(Alias(text, kind, ident, str(subject), label))
    aliases.sort(key=lambda alias: len(alias.text), reverse=True)
    return aliases


def _blocks(spans: list[tuple[int, int]], start: int, end: int) -> bool:
    """Un span identique est conservé (homonymes). Un chevauchement partiel est écarté."""
    for left, right in spans:
        if start == left and end == right:
            continue
        if not (end <= left or start >= right):
            return True
    return False


def _lexical_spans(text: str, aliases: list[Alias]) -> list[Entity]:
    spans: list[tuple[int, int]] = []
    found: list[Entity] = []
    for alias in aliases:
        for match in re.finditer(rf"(?<!\w){re.escape(alias.text)}(?!\w)", text):
            if _blocks(spans, match.start(), match.end()):
                continue
            span = (match.start(), match.end())
            if span not in spans:
                spans.append(span)
            found.append(Entity(alias.kind, alias.ident, alias.uri, alias.label, alias.text, match.start(), match.end()))
    return found


def _spacy_spans(text: str, aliases: list[Alias]) -> list[Entity]:
    nlp = _engine()
    if nlp is None:
        return _lexical_spans(text, aliases)
    from spacy.matcher import PhraseMatcher

    matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
    lookup = {}
    for index, alias in enumerate(aliases):
        key = f"E{index}"
        matcher.add(key, [nlp.make_doc(alias.text)])
        lookup[key] = alias
    doc = nlp.make_doc(text)
    raw = []
    for match_id, start, end in matcher(doc):
        key = nlp.vocab.strings[match_id]
        alias = lookup[key]
        span = doc[start:end]
        raw.append((span.start_char, span.end_char, alias))
    raw.sort(key=lambda item: (item[1] - item[0], -item[0]), reverse=True)
    spans: list[tuple[int, int]] = []
    found: list[Entity] = []
    occupied_keys = set()
    for start, end, alias in raw:
        if _blocks(spans, start, end):
            continue
        identity = (alias.kind, alias.ident, start, end)
        if identity in occupied_keys:
            continue
        occupied_keys.add(identity)
        span = (start, end)
        if span not in spans:
            spans.append(span)
        found.append(Entity(alias.kind, alias.ident, alias.uri, alias.label, alias.text, start, end))
    return found


def _same_span(entities: list[Entity]) -> list[list[Entity]]:
    groups: dict[tuple[int, int], list[Entity]] = {}
    for entity in entities:
        groups.setdefault((entity.start, entity.end), []).append(entity)
    return list(groups.values())


def disambiguate(entities: list[Entity], normalized: str) -> tuple[list[Entity], list[str]]:
    notes = []
    chosen = []
    priority = {
        "effet": "effet" in normalized,
        "contre_indication": "contre-indication" in normalized,
        "medicament": bool(re.search(r"\bmedicament\b", normalized)),
        "molecule": bool(re.search(r"\bmolecule\b", normalized)),
        "pathologie": bool(re.search(r"\b(pathologie|maladie)\b", normalized)),
    }
    fallback = ("medicament", "molecule", "effet", "contre_indication", "pathologie")
    if priority["medicament"] and not priority["effet"] and not priority["contre_indication"]:
        fallback = ("medicament", "contre_indication", "molecule", "pathologie", "effet")
    for group in _same_span(entities):
        if len(group) == 1:
            chosen.append(group[0])
            continue
        preferred = next((entity for entity in group if priority.get(entity.kind)), None)
        if preferred is None:
            preferred = min(group, key=lambda entity: fallback.index(entity.kind))
        chosen.append(preferred)
        ignored = [entity.label for entity in group if entity.ident != preferred.ident or entity.kind != preferred.kind]
        if ignored:
            notes.append(
                f"« {preferred.text} » correspond à plusieurs individus. "
                f"Retenu : {preferred.kind} {preferred.label}. Écartés : {', '.join(ignored)}."
            )
    chosen.sort(key=lambda entity: entity.start)
    return chosen, notes


def extract_entities(graph, question: str, normalized: str) -> tuple[list[Entity], list[str], dict]:
    aliases = build_aliases(graph)
    nlp = _engine()
    texts = [normalized]
    lemmas: list[str] = []
    tokens: list[str] = []
    if nlp is not None and analyzer_mode() not in {"lexical", "blank"}:
        doc = nlp(question)
        tokens = [token.text for token in doc if not token.is_space]
        lemmas = [token.lemma_ for token in doc if not token.is_punct and not token.is_space]
        lemma_text = normalize(" ".join(lemmas))
        if lemma_text and lemma_text != normalized:
            texts.append(lemma_text)
    else:
        tokens = normalized.split()
    found: list[Entity] = []
    for text in texts:
        found.extend(_spacy_spans(text, aliases) if nlp is not None else _lexical_spans(text, aliases))
    # Les spans de la deuxième passe ne sont pas comparables. On dédoublonne par individu.
    unique = {}
    for entity in found:
        unique.setdefault((entity.kind, entity.ident), entity)
    chosen, notes = disambiguate(list(unique.values()), normalized)
    analysis = {
        "analyzer": "lexical-fallback" if nlp is None else f"spacy:{analyzer_mode()}",
        "normalized": normalized,
        "tokens": tokens[:40],
        "lemmas": lemmas[:40],
    }
    return chosen, notes, analysis
