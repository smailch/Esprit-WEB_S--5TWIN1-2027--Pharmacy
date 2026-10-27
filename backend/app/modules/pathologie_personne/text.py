import re
import unicodedata


def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def normalize(s: str) -> str:
    """Minuscules, sans accents, espaces compactés (même normalisation que le SPARQL de search.rq)."""
    return re.sub(r"\s+", " ", strip_accents(s).lower()).strip()


def pascal_case(s: str) -> str:
    """« grippe saisonnière » → « GrippeSaisonniere » (nom local d'URI)."""
    words = re.findall(r"[A-Za-z0-9]+", strip_accents(s))
    return "".join(w[:1].upper() + w[1:] for w in words)


# Expression SPARQL équivalente à normalize() (accents français courants)
def sparql_norm(expr: str) -> str:
    return ('REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(LCASE(' + expr + '),'
            ' "[éèêë]", "e"), "[àâä]", "a"), "[îï]", "i"), "[ôö]", "o"), "[ùûü]", "u"), "ç", "c")')
