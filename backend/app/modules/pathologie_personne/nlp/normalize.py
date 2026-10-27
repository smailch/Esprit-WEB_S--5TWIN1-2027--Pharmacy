"""Étape 1 — Normalisation.

Minuscules, accents retirés, ponctuation et apostrophes → espaces.
La transformation est caractère par caractère (même longueur) : les positions trouvées
dans le texte normalisé sont valables dans la question d'origine (surlignage des entités).
"""
import unicodedata


def _char(c: str) -> str:
    base = unicodedata.normalize("NFKD", c)[:1].lower()[:1] or c
    return base if base.isalnum() else " "


def normalize(text: str) -> str:
    return "".join(_char(c) for c in text)


def stem(token: str) -> str:
    """Pluriel simple : « maladies » → « maladie », « chroniques » → « chronique »."""
    if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def stem_phrase(text: str) -> str:
    return " ".join(stem(t) for t in normalize(text).split())
