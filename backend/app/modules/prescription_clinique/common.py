"""Utilitaires propres au module D (aucune dépendance au code des autres modules).

Les gabarits SPARQL utilisent des paramètres {{nom}} remplacés uniquement par des termes RDF
déjà validés et sérialisés (`uri`, `lit`, `date_lit`), jamais par du texte brut venant du client.
"""
from __future__ import annotations

import re
import unicodedata
from datetime import date

from rdflib import Literal
from rdflib.namespace import XSD

from ...graph_store import store

ID_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")


class NotFound(Exception):
    pass


class Conflict(Exception):
    pass


def uri(local_id: str) -> str:
    if not ID_PATTERN.match(local_id or ""):
        raise ValueError(f"Identifiant invalide : {local_id!r}")
    return f":{local_id}"


def lit(value, datatype=None, lang=None) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)) and datatype is None:
        return Literal(value, datatype=XSD.decimal if isinstance(value, float) else XSD.integer).n3()
    return Literal(value, datatype=datatype, lang=lang).n3()


def date_lit(value) -> str:
    """Littéral xsd:date validé (refuse tout ce qui n'est pas une date ISO AAAA-MM-JJ)."""
    d = value if isinstance(value, date) else date.fromisoformat(str(value))
    return lit(d.isoformat(), datatype=XSD.date)


def render(sparql: str, **params) -> str:
    def sub(m):
        key = m.group(1)
        if key not in params:
            raise KeyError(f"Paramètre manquant : {key}")
        return str(params[key])
    return re.sub(r"\{\{(\w+)\}\}", sub, sparql).strip()


def strip_accents(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")


def make_id(text: str) -> str:
    words = re.findall(r"[A-Za-z0-9]+", strip_accents(text))
    ident = "".join(w[:1].upper() + w[1:] for w in words)
    return ident if ident and ident[0].isalpha() else "X" + ident


class Trace:
    """Enregistre les requêtes exécutées : l'API les renvoie au front-end (transparence, démonstration)."""

    def __init__(self):
        self.items: list[dict] = []

    def _log(self, titre, sparql):
        self.items.append({"titre": titre, "requete": sparql})

    def select(self, titre, sparql):
        self._log(titre, sparql)
        return store.select(sparql)

    def ask(self, titre, sparql):
        self._log(titre, sparql)
        return store.ask(sparql)

    def construct(self, titre, sparql):
        self._log(titre, sparql)
        return store.construct(sparql)

    def update(self, titre, sparql):
        self._log(titre, sparql)
        store.update(sparql)
