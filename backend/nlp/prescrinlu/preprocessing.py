"""Étape 1 — Prétraitement : normalisation du texte et analyse spaCy (tokens, lemmes).

Le modèle `fr_core_news_sm` est chargé une seule fois. S'il est absent, on bascule en « mode lexical »
(`spacy.blank("fr")` : tokenisation seule, lemme = forme normalisée) et l'API le signale.
Si spaCy lui-même n'est pas installé, `NlpUnavailable` donne la commande d'installation.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache

MODEL_NAME = "fr_core_news_sm"
INSTALL_HINT = ("Installez les dépendances du back-end : pip install -r requirements.txt "
                "(le modèle français s'installe aussi seul : python -m spacy download fr_core_news_sm)")

# Variantes lexicales ramenées à une forme canonique (appliquées après suppression des accents).
VARIANTS = [
    (r"\bdr\.?(?=\s)", "dr"),
    (r"\bdocteur\b", "dr"),
    (r"\bn\s*°\s*", " "),
    (r"\bnumero\b", " "),
    (r"\bmedocs?\b", "medicaments"),
    (r"\bcontre[\s-]+indique(e|es|s)?\b", "contre-indique"),
    (r"\bcontre[\s-]+indications?\b", "contre-indication"),
]


# Mots métier corrigés en cas de faute de frappe (« medicamants » → « medicaments »), via RapidFuzz.
DOMAIN_WORDS = sorted(set("""
medicament medicaments prescription prescriptions ordonnance ordonnances renouvelable renouvelables
prescrit prescrits prescrite prescrites prescrire patient patients patiente patientes medecin medecins
pharmacien pharmaciens pharmacienne pharmaciennes renouvellement renouvellements
galenique galeniques posologie delivree delivrees delivre combien urgente urgentes normale normales
contre-indique contre-indication dangereuse dangereuses traitement traitements enregistrees disponibles
clinique cliniques donnees allergie allergies allergique antecedent antecedents analyse analyses examens
glycemie temperature tension clairance creatinine inferieure superieure
""".split()))


class NlpUnavailable(RuntimeError):
    pass


def correct_domain_words(text: str) -> tuple[str, list[dict]]:
    """Corrige les mots métier mal orthographiés (score ≥ 85) ; renvoie le texte et la liste des corrections."""
    try:
        from rapidfuzz import fuzz, process
    except ImportError:  # pragma: no cover
        return text, []
    words, corrections = text.split(" "), []
    for i, w in enumerate(words):
        if len(w) < 6 or w in DOMAIN_WORDS or not w.replace("-", "").isalpha():
            continue
        best = process.extractOne(w, DOMAIN_WORDS, scorer=fuzz.ratio, score_cutoff=85)
        if best:
            corrections.append({"mot": w, "correction": best[0], "score": round(best[1])})
            words[i] = best[0]
    return " ".join(words), corrections


def strip_accents(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")


def normalize(text: str) -> str:
    """Minuscules, apostrophes unifiées, accents retirés, ponctuation neutralisée, variantes canoniques."""
    t = text.lower().replace("’", "'").replace("`", "'").replace("«", " ").replace("»", " ")
    t = strip_accents(t)
    t = re.sub(r"[?!;,:()\[\]{}\"<>|*=+~^$\\]", " ", t)
    t = re.sub(r"(?<!\d)\.(?!\d)", " ", t)  # garde les points des dates « 12.10.2026 »
    for pattern, repl in VARIANTS:
        t = re.sub(pattern, repl, t)
    return re.sub(r"\s+", " ", t).strip()


@dataclass
class Token:
    text: str   # forme dans la question (minuscules, accents conservés)
    norm: str   # forme normalisée (sans accent)
    lemma: str  # lemme spaCy normalisé (ou forme normalisée en mode lexical)
    pos: str


@dataclass
class Analysis:
    original: str
    normalized: str
    tokens: list[Token]
    lemma_text: str
    doc: object  # Doc spaCy construit sur le texte normalisé (pour le PhraseMatcher)
    mode: str
    corrections: list


@lru_cache(maxsize=1)
def load_nlp():
    """Renvoie (nlp, mode). Chargé une fois par processus."""
    try:
        import spacy
    except ImportError as e:  # pragma: no cover - dépend de l'installation
        raise NlpUnavailable("spaCy n'est pas installé. " + INSTALL_HINT) from e
    try:
        return spacy.load(MODEL_NAME, disable=["ner"]), f"spaCy {spacy.__version__} + {MODEL_NAME}"
    except OSError:
        return spacy.blank("fr"), f"spaCy {spacy.__version__} (mode lexical : modèle {MODEL_NAME} absent)"


def analyse(question: str) -> Analysis:
    nlp, mode = load_nlp()
    lowered = re.sub(r"\s+", " ", question.lower().replace("’", "'")).strip()
    doc = nlp(lowered)
    tokens = []
    for tok in doc:
        if tok.is_punct or tok.is_space:
            continue
        lemma = tok.lemma_ if tok.lemma_ else tok.text
        tokens.append(Token(tok.text, strip_accents(tok.text), strip_accents(lemma.lower()), tok.pos_ or ""))
    normalized, corrections = correct_domain_words(normalize(question))
    lemma_text, _ = correct_domain_words(" ".join(t.lemma for t in tokens))
    return Analysis(
        original=question, normalized=normalized, tokens=tokens, lemma_text=lemma_text,
        doc=nlp.make_doc(normalized), mode=mode, corrections=corrections,
    )


def make_doc(text: str):
    nlp, _ = load_nlp()
    return nlp.make_doc(normalize(text))
