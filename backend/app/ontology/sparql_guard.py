"""Validation des requêtes SPARQL en lecture seule."""

from __future__ import annotations

import re

class SparqlRejected(ValueError):
    pass


_FORBIDDEN = re.compile(
    r"\b(INSERT|DELETE|UPDATE|LOAD|CLEAR|DROP|CREATE|COPY|MOVE|ADD|WITH|SERVICE|SILENT)\b",
    re.IGNORECASE,
)
_READ = re.compile(r"^\s*(SELECT|ASK|CONSTRUCT|DESCRIBE)\b", re.IGNORECASE)
_PREFIX_LINE = re.compile(r"^\s*(PREFIX|BASE)\b", re.IGNORECASE)


def _strip_literals_and_comments(query: str) -> str:
    out: list[str] = []
    i = 0
    n = len(query)
    while i < n:
        char = query[i]
        if char in {'"', "'"}:
            quote = char
            if query.startswith(quote * 3, i):
                end = query.find(quote * 3, i + 3)
                i = n if end < 0 else end + 3
            else:
                i += 1
                while i < n and query[i] != quote:
                    i += 2 if query[i] == "\\" else 1
                i += 1
            out.append(" ")
            continue
        if char == "#":
            while i < n and query[i] not in "\n\r":
                i += 1
            continue
        out.append(char)
        i += 1
    return "".join(out)


def validate_read_query(query: str, max_length: int = 8000) -> str:
    if not query or not query.strip():
        raise SparqlRejected("La requête SPARQL est vide.")
    if len(query) > max_length:
        raise SparqlRejected(f"Requête trop longue (maximum {max_length} caractères).")
    if "\x00" in query:
        raise SparqlRejected("Requête refusée.")

    visible = _strip_literals_and_comments(query)
    if _FORBIDDEN.search(visible):
        raise SparqlRejected(
            "Seules les requêtes de lecture SELECT, ASK, CONSTRUCT et DESCRIBE sont acceptées. "
            "Les mises à jour SPARQL et les clauses SERVICE sont interdites."
        )

    without_prefixes = "\n".join(
        line for line in visible.splitlines() if not _PREFIX_LINE.match(line)
    )
    if not _READ.match(without_prefixes):
        raise SparqlRejected(
            "La requête doit commencer par SELECT, ASK, CONSTRUCT ou DESCRIBE."
        )
    return query.strip()
