"""Étape 3 — Extraction d'entités.

- spaCy `PhraseMatcher` (attribut LOWER, texte sans accents) : alias issus de l'ontologie, plus longue correspondance gardée ;
- règles (expressions régulières) : identifiants d'ordonnance (« Presc_002 », « ordonnance 3 »), dates et périodes ;
- règles : seuils numériques (« clairance inférieure à 60 », « tension > 140 ») ;
- RapidFuzz : correction des fautes de frappe (« dolipran » → Doliprane) sur les mots restés inconnus ;
- identifiants qui ressemblent à un individu mais absents de l'ontologie (« Patient_F001 ») → entité INCONNUE.
"""
from __future__ import annotations

import calendar
import re
from dataclasses import asdict, dataclass
from datetime import date, timedelta

from spacy.matcher import PhraseMatcher
from spacy.util import filter_spans

from .lexicon import Entry, Lexicon
from .preprocessing import Analysis, load_nlp

try:
    from rapidfuzz import fuzz, process
except ImportError:  # pragma: no cover - RapidFuzz est dans requirements.txt
    process = None

MONTHS = {m: i for i, m in enumerate(
    ["janvier", "fevrier", "mars", "avril", "mai", "juin", "juillet", "aout", "septembre", "octobre", "novembre", "decembre"], 1)}
MONTH_RE = "|".join(MONTHS)
DAY_RE = r"(?:1er|[0-3]?\d)"

# Mots du domaine qui ne doivent jamais être « corrigés » en nom propre par la recherche approximative.
VOCABULARY = set("""
quel quels quelle quelles qui quoi combien comment pourquoi liste lister affiche afficher montre montrer donne donner
prescription prescriptions ordonnance ordonnances prescrit prescrits prescrite prescrites prescrire medicament medicaments
patient patients medecin medecins pharmacien pharmaciens delivre delivree delivrees delivrer forme formes galenique
galeniques disponible disponibles existe existent sous contient contiennent contenir renouvelable
renouvelables simple simples urgente urgentes normale normales enregistre enregistrees enregistrees toutes tous entre
apres avant depuis pendant janvier fevrier mars avril juin juillet aout septembre octobre novembre decembre contre
indique indiquee danger dangereuse dangereuses risque alerte alertes allergie allergies allergique posologie duree date
details detail chaine parcours scenario traitement traitements prend prennent prendre ayant avoir cette celle ceux leur
leurs donnee donnees clinique cliniques dossier examen examens mesure mesures analyse analyses valeur valeurs resultat
resultats inferieur inferieure superieur superieure moins plus dessus dessous antecedent antecedents historique bilan
""".split())

COMPARATORS = [
    (r"inferieure?s? ou egale?s? a|au plus|<=|≤", "<="), (r"superieure?s? ou egale?s? a|au moins|>=|≥", ">="),
    (r"inferieure?s? a|moins de|en dessous de|en-dessous de|sous|<", "<"),
    (r"superieure?s? a|plus de|au dessus de|au-dessus de|depasse|dessus de|>", ">"),
]


@dataclass
class Threshold:
    op: str
    valeur: float
    texte: str

    def as_dict(self):
        return asdict(self)


def extract_threshold(raw: str) -> Threshold | None:
    """Seuil numérique sur le texte brut sans accents (avant suppression de « < », « > » et de la virgule décimale)."""
    for pattern, op in COMPARATORS:
        m = re.search(rf"(?:{pattern})\s*(\d+(?:[.,]\d+)?)(?!\d|/|-)", raw)
        if m:
            return Threshold(op, float(m[1].replace(",", ".")), m[0].strip())
    return None

UNKNOWN_ID_RE = re.compile(r"\b(?:patient|patiente|dr|ph|presc|prescription|ordonnance)_[a-z0-9]+\b")
PRESC_RE = re.compile(r"\b(?:presc|prescription|ordonnance|ord)(?:[\s_#-]*)0*(\d{1,3})\b")


@dataclass
class Entity:
    type: str
    id: str
    label: str
    texte: str
    methode: str          # dictionnaire | regle | approximatif
    score: int = 100

    def as_dict(self):
        return asdict(self)


@dataclass
class Period:
    debut: date | None = None
    fin: date | None = None
    texte: str = ""

    def as_dict(self):
        return {"debut": self.debut and self.debut.isoformat(), "fin": self.fin and self.fin.isoformat(), "texte": self.texte}


def _matcher(lex: Lexicon):
    nlp, _ = load_nlp()
    m = PhraseMatcher(nlp.vocab, attr="LOWER")
    for alias in lex.aliases:
        m.add(alias, [nlp.make_doc(alias)])
    return m


def _parse_day(day: str, month: str, year: str) -> date:
    d = 1 if day == "1er" else int(day)
    return date(int(year), MONTHS[month], d)


def extract_period(text: str) -> Period | None:
    """Dates et périodes : ISO, JJ/MM/AAAA, « 12 octobre 2026 », « octobre 2026 », « en 2026 », avec entre / après / avant."""
    spans = []
    for m in re.finditer(r"\b(\d{4})-(\d{2})-(\d{2})\b", text):
        spans.append((m.start(), m.end(), date(int(m[1]), int(m[2]), int(m[3])), None))
    for m in re.finditer(r"\b([0-3]?\d)[/.]([01]?\d)[/.](\d{4})\b", text):
        spans.append((m.start(), m.end(), date(int(m[3]), int(m[2]), int(m[1])), None))
    for m in re.finditer(rf"\b({DAY_RE}) ({MONTH_RE}) (\d{{4}})\b", text):
        spans.append((m.start(), m.end(), _parse_day(m[1], m[2], m[3]), None))
    taken = [(s, e) for s, e, *_ in spans]
    for m in re.finditer(rf"\b({MONTH_RE})(?: (\d{{4}}))?\b", text):
        if any(s <= m.start() < e for s, e in taken):
            continue
        year = int(m[2]) if m[2] else date.today().year
        month = MONTHS[m[1]]
        spans.append((m.start(), m.end(), date(year, month, 1), date(year, month, calendar.monthrange(year, month)[1])))
    taken = [(s, e) for s, e, *_ in spans]
    for m in re.finditer(r"\b(20\d{2}|19\d{2})\b", text):
        if not any(s <= m.start() < e for s, e in taken):
            y = int(m[1])
            spans.append((m.start(), m.end(), date(y, 1, 1), date(y, 12, 31)))
    if not spans:
        return None
    spans.sort()
    first, last = spans[0], spans[-1]
    before = text[max(0, first[0] - 25):first[0]]
    start_of = lambda s: s[2]  # noqa: E731
    end_of = lambda s: s[3] or s[2]  # noqa: E731
    texte = text[first[0]:last[1]]
    if len(spans) >= 2 and re.search(r"\b(entre|du|de)\b", before):
        return Period(start_of(first), end_of(last), texte)
    if re.search(r"\bapres\b", before):
        return Period(end_of(first) + timedelta(days=1), None, texte)
    if re.search(r"\b(depuis|a partir d[ue]?|a compter d[ue]?)\b", before):
        return Period(start_of(first), None, texte)
    if re.search(r"\bavant\b", before):
        return Period(None, start_of(first) - timedelta(days=1), texte)
    if re.search(r"\bjusqu", before):
        return Period(None, end_of(first), texte)
    return Period(start_of(first), end_of(first), texte)


def extract(analysis: Analysis, lex: Lexicon) -> tuple[list[Entity], Period | None, list[str]]:
    """Renvoie (entités reconnues, période, identifiants inconnus)."""
    text = analysis.normalized
    doc = analysis.doc
    entities: list[Entity] = []
    covered: set[int] = set()

    # 1) Identifiants d'ordonnance par règle (« Presc_002 », « ordonnance 3 », « prescription n° 001 »).
    unknown = []
    for m in PRESC_RE.finditer(text):
        pid = f"Presc_{int(m[1]):03d}"
        e = lex.ids.get(pid.lower())
        if e:
            entities.append(Entity(e.type, e.id, e.label, m[0], "regle"))
        else:
            unknown.append(pid)
        covered.update(range(m.start(), m.end()))

    # 2) Dictionnaire de l'ontologie via spaCy PhraseMatcher (correspondance la plus longue).
    matcher = _matcher(lex)
    spans = filter_spans([doc[s:e] for _, s, e in matcher(doc)])
    for span in spans:
        if any(i in covered for i in range(span.start_char, span.end_char)):
            continue
        for entry in lex.aliases.get(span.text, []):
            entities.append(Entity(entry.type, entry.id, entry.label, span.text, "dictionnaire"))
        covered.update(range(span.start_char, span.end_char))

    # 3) Identifiants de forme « Patient_xxx » absents de l'ontologie → signalés, jamais inventés.
    for m in UNKNOWN_ID_RE.finditer(text):
        if not any(i in covered for i in range(m.start(), m.end())) and m[0] not in lex.ids:
            unknown.append(m[0])
            covered.update(range(m.start(), m.end()))

    # 4) Fautes de frappe : RapidFuzz sur les mots restants (≥ 4 lettres, hors vocabulaire du domaine).
    if process is not None:
        choices = {a: es for a, es in lex.aliases.items()
                   if " " not in a and len(a) >= 4 and es[0].type not in ("TYPE_PRESCRIPTION", "TYPE_DONNEE")}
        for tok in doc:
            word = tok.text.strip("'")
            if (tok.idx in covered or len(word) < 4 or not word.isalpha() or word in VOCABULARY):
                continue
            best = process.extractOne(word, list(choices), scorer=fuzz.ratio, score_cutoff=82)
            if best:
                alias, score, _ = best
                for entry in choices[alias]:
                    entities.append(Entity(entry.type, entry.id, entry.label, word, "approximatif", int(score)))
                covered.update(range(tok.idx, tok.idx + len(tok.text)))

    # Dédoublonnage (un même individu peut être cité deux fois).
    seen, unique = set(), []
    for e in entities:
        if (e.type, e.id) not in seen:
            seen.add((e.type, e.id))
            unique.append(e)
    return unique, extract_period(text), sorted(set(unknown))


def first(entities: list[Entity], kind: str) -> Entity | None:
    return next((e for e in entities if e.type == kind), None)


def of_type(entities: list[Entity], kind: str) -> list[Entity]:
    return [e for e in entities if e.type == kind]


__all__ = ["Entity", "Period", "Entry", "extract", "extract_period", "first", "of_type"]
