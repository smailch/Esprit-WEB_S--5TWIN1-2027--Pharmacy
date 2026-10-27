"""Étape 1 — Normalisation du texte avec spaCy (fr_core_news_sm).

- minuscules, suppression des accents, apostrophes et nombres harmonisés ;
- tokenisation + lemmatisation spaCy (le modèle français gère « l'ibuprofène » → « l' » + « ibuprofene »).
"""
import re
import unicodedata
from functools import lru_cache

import spacy

SPACY_MODEL = "fr_core_news_sm"


@lru_cache(maxsize=1)
def get_nlp():
    # On garde tokeniseur, morphologie et lemmatiseur ; l'analyse syntaxique et les entités spaCy sont inutiles ici.
    return spacy.load(SPACY_MODEL, exclude=["parser", "ner", "senter"])


def strip_accents(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")


def normalize(text: str) -> str:
    t = text.lower().replace("’", "'").replace("`", "'")
    t = strip_accents(t)
    t = re.sub(r"(\d),(\d)", r"\1.\2", t)               # 4,5 → 4.5
    t = re.sub(r"(\d)([a-z])", r"\1 \2", t)              # 5dt → 5 dt
    t = re.sub(r"[^a-z0-9.'\- <>]", " ", t)              # ponctuation → espace
    t = re.sub(r"-", " ", t)                             # contre-indication → contre indication
    return re.sub(r"\s+", " ", t).strip()


def tokenize(text: str):
    """Renvoie le Doc spaCy du texte normalisé."""
    return get_nlp()(normalize(text))


def spacy_version() -> str:
    nlp = get_nlp()
    return f"spaCy {spacy.__version__} / {nlp.meta.get('name')} {nlp.meta.get('version')}"
