"""Requêtes nommées (backend/sparql/*.rq) et rendu paramétré sûr.

En-tête de chaque fichier .rq :
    # objectif: ...
    # categorie: Create | Read | Update | Delete | Filtre | Recherche | Hierarchie | Agregat | Chemin | Alerte | ASK
    # params: nom:type, ...      (types : iri, lit, litfr, int, raw)
    # exemple: {"nom": valeur, ...}

Aucune valeur utilisateur n'est concaténée telle quelle : les IRI sont validés par regex,
les littéraux échappés, les entiers convertis. `raw` est réservé aux fragments construits
par le serveur à partir de valeurs déjà échappées (filtres optionnels).
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from app.config.ontology_mapping import C, P, PREFIXES, iri

SPARQL_DIR = Path(__file__).resolve().parents[2] / "sparql"
LOCAL_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,80}$")


class InvalidParam(ValueError):
    pass


def check_local(name: str) -> str:
    if not isinstance(name, str) or not LOCAL_NAME.match(name):
        raise InvalidParam(f"Identifiant invalide : {name!r}")
    return name


def escape_literal(value: str) -> str:
    s = str(value)
    s = (s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
          .replace("\r", "\\r").replace("\t", "\\t"))
    return f'"{s}"'


def fmt(value, kind: str) -> str:
    if kind == "iri":
        return iri(check_local(value))
    if kind == "lit":
        return escape_literal(value)
    if kind == "litfr":
        return escape_literal(value) + "@fr"
    if kind == "int":
        if isinstance(value, bool):
            raise InvalidParam("entier attendu")
        try:
            return str(int(value))
        except (TypeError, ValueError) as e:
            raise InvalidParam(f"Entier invalide : {value!r}") from e
    if kind == "raw":
        return str(value)
    raise InvalidParam(f"type inconnu {kind}")


@dataclass
class NamedQuery:
    name: str
    objectif: str
    categorie: str
    params: dict[str, str]
    exemple: dict
    body: str

    def render(self, **values) -> str:
        missing = set(self.params) - set(values)
        if missing:
            raise InvalidParam(f"paramètres manquants : {sorted(missing)}")

        def sub(m):
            key = m.group(1)
            return fmt(values[key], self.params[key])

        return PREFIXES + re.sub(r"\{\{(\w+)\}\}", sub, self.body)


def _map_names(text: str) -> str:
    """:Nom → nom défini dans ontology_mapping (renommage centralisé)."""
    return re.sub(r"(?<![\w<]):([A-Za-z]\w*)",
                  lambda m: ":" + C.get(m.group(1), P.get(m.group(1), m.group(1))), text)


def _parse(path: Path) -> NamedQuery:
    header, body = {}, []
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"#\s*(objectif|categorie|params|exemple):\s*(.*)", line)
        if m and not body:
            header[m.group(1)] = m.group(2).strip()
        else:
            body.append(line)
    params = {}
    for item in filter(None, (x.strip() for x in header.get("params", "").split(","))):
        k, t = item.split(":")
        params[k.strip()] = t.strip()
    return NamedQuery(
        name=path.stem,
        objectif=header.get("objectif", ""),
        categorie=header.get("categorie", ""),
        params=params,
        exemple=json.loads(header.get("exemple", "{}")),
        body=_map_names("\n".join(body).strip()),
    )


QUERIES: dict[str, NamedQuery] = {p.stem: _parse(p) for p in sorted(SPARQL_DIR.glob("*.rq"))}


def render(name: str, **values) -> str:
    return QUERIES[name].render(**values)
