"""Normalisation linguistique sans service externe.

La casse, les accents, la ponctuation et quelques variantes lexicales
sont ramenées à une forme stable avant l'extraction d'entités.
"""

from __future__ import annotations

import re
import unicodedata

_PHRASES = (
    ("effets secondaires", "effet"),
    ("effet secondaire", "effet"),
    ("contre indications", "contre-indication"),
    ("contre indication", "contre-indication"),
    ("contre-indications", "contre-indication"),
    ("contre indiques", "contre-indication"),
    ("contre indiquees", "contre-indication"),
    ("contre indique", "contre-indication"),
    ("effets", "effet"),
    ("medicaments", "medicament"),
    ("molecules", "molecule"),
    ("pathologies", "pathologie"),
    ("nausees", "nausee"),
    ("hemorragies digestives", "hemorragie digestive"),
    ("eruptions cutanees", "eruption cutanee"),
    ("graves", "grave"),
    ("legers", "leger"),
    ("legeres", "leger"),
    ("legere", "leger"),
    ("digestifs", "digestif"),
    ("digestives", "digestif"),
    ("digestive", "digestif"),
    ("cutanes", "cutane"),
    ("cutanee", "cutane"),
    ("neurologiques", "neurologique"),
    ("renales", "renal"),
    ("renaux", "renal"),
    ("hepatiques", "hepatique"),
    ("allergiques", "allergique"),
    ("allergies", "allergique"),
    ("allergie", "allergique"),
    ("absolues", "absolu"),
    ("relatives", "relatif"),
    ("associes", "associe"),
    ("associees", "associe"),
    ("liees", "lie"),
    ("lies", "lie"),
    ("enregistres", "enregistre"),
    ("enregistrees", "enregistre"),
)


def fold(value: str) -> str:
    text = unicodedata.normalize("NFD", value or "")
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")
    return text.lower().replace("’", "'").replace("`", "'")


def normalize(question: str) -> str:
    text = fold(question)
    text = text.replace("-", " ").replace("'", " ")
    text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
    text = re.sub(r"\s+", " ", text).strip()
    for source, target in _PHRASES:
        text = re.sub(rf"\b{re.escape(source)}\b", target, text)
    return re.sub(r"\s+", " ", text).strip()


def camel_fold(name: str) -> str:
    trimmed = name[3:] if name.startswith("CI_") else name
    spaced = re.sub(r"([a-z])([A-Z])", r"\1 \2", trimmed).replace("_", " ")
    return normalize(spaced)
