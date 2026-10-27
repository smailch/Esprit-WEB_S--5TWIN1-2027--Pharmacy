"""Requêtes SPARQL de lecture pour le module B, bornées au vocabulaire réel."""

from __future__ import annotations

import re
import unicodedata
from collections import defaultdict

from rdflib import Literal, URIRef
from rdflib.namespace import RDFS

from app.ontology.loader import OntologyStore
from app.ontology.vocab import (
    CI_CATEGORY_CLASSES,
    CI_TYPES,
    EFFECT_CATEGORY_CLASSES,
    EFFECT_TYPES,
    PHARMA_NS,
    PREFIXES,
    REASONING_LIMIT,
)

LOCAL_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")


class DomainError(Exception):
    def __init__(self, message: str, status: int = 422) -> None:
        super().__init__(message)
        self.status = status


def fold(value: str) -> str:
    text = unicodedata.normalize("NFD", value or "")
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")
    text = text.lower().replace("’", "'")
    return re.sub(r"\s+", " ", text).strip()


def local_name(term) -> str:
    value = str(term)
    if "#" in value:
        return value.rsplit("#", 1)[-1]
    return value.rstrip("/").rsplit("/", 1)[-1]


def pharma_uri(name: str) -> URIRef:
    if not LOCAL_NAME.fullmatch(name or ""):
        raise DomainError("Identifiant refusé. Utilisez un nom local sans espace ni accent, par exemple Nausee.")
    return URIRef(PHARMA_NS + name)


def _text(term) -> str | None:
    if term is None:
        return None
    return str(term)


def effect_category(type_id: str) -> str | None:
    if "Digestif" in type_id:
        return "digestif"
    if "Cutane" in type_id:
        return "cutane"
    if "Neurologique" in type_id:
        return "neurologique"
    return None


def ci_category(type_id: str) -> str | None:
    return {
        "ContreIndicationAllergique": "allergique",
        "ContreIndicationDigestive": "digestive",
        "ContreIndicationRenale": "renale",
        "ContreIndicationHepatique": "hepatique",
    }.get(type_id)


def canonical_gravite(value: str | None) -> str | None:
    if value is None or value == "":
        return None
    key = fold(value)
    mapping = {"leger": "léger", "grave": "grave"}
    if key not in mapping:
        raise DomainError("Gravité inconnue. Valeurs autorisées : léger, grave.")
    return mapping[key]


def canonical_risque(value: str | None) -> str | None:
    if value is None or value == "":
        return None
    key = fold(value)
    mapping = {"absolu": "absolu", "absolue": "absolu", "relatif": "relatif", "relative": "relatif"}
    if key not in mapping:
        raise DomainError("Niveau de risque inconnu. Valeurs autorisées : absolu, relatif.")
    return mapping[key]


def canonical_effect_category(value: str | None) -> str | None:
    if value is None or value == "":
        return None
    key = fold(value)
    aliases = {"cutane": "cutane", "cutanee": "cutane", "digestif": "digestif", "digestive": "digestif", "neurologique": "neurologique"}
    key = aliases.get(key, key)
    if key not in EFFECT_CATEGORY_CLASSES:
        raise DomainError("Catégorie d'effet inconnue. Valeurs : digestif, cutane, neurologique.")
    return key


def canonical_ci_category(value: str | None) -> str | None:
    if value is None or value == "":
        return None
    key = fold(value)
    aliases = {
        "allergique": "allergique",
        "allergie": "allergique",
        "digestive": "digestive",
        "digestif": "digestive",
        "renale": "renale",
        "renal": "renale",
        "hepatique": "hepatique",
        "absolue": "absolue",
        "absolu": "absolue",
        "relative": "relative",
        "relatif": "relative",
    }
    key = aliases.get(key, key)
    if key not in CI_CATEGORY_CLASSES:
        raise DomainError(
            "Catégorie de contre-indication inconnue. "
            "Valeurs : allergique, digestive, renale, hepatique, absolue, relative."
        )
    return key


def _run(store: OntologyStore, sparql: str) -> dict:
    return store.query(PREFIXES + "\n" + sparql)


def _exists(store: OntologyStore, sparql_body: str) -> bool:
    result = _run(store, f"ASK {{ {sparql_body} }}")
    return bool(result["ask"])


def individual_kind(store: OntologyStore, uri: URIRef) -> str | None:
    checks = (
        ("effet", "EffetSecondaire"),
        ("contre_indication", "ContreIndication"),
        ("molecule", "Molecule"),
        ("medicament", "Medicament"),
        ("pathologie", "Pathologie"),
    )
    for kind, root in checks:
        if _exists(
            store,
            f"{uri.n3()} a ?type . ?type rdfs:subClassOf* :{root} . FILTER(isIRI(?type))",
        ):
            return kind
    return None


def _class_filter(variable: str, classes: tuple[str, ...] | str) -> str:
    names = (classes,) if isinstance(classes, str) else classes
    parts = [f"EXISTS {{ {variable} rdfs:subClassOf* :{name} }}" for name in names]
    return "FILTER( " + " || ".join(parts) + " )"


def _collapse(rows: list[dict], graph) -> list[dict]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        if row.get("uri") is None:
            continue
        grouped[str(row["uri"])].append(row)
    chosen = []
    for group in grouped.values():
        if len(group) == 1:
            chosen.append(group[0])
            continue
        chosen.append(max(group, key=lambda row: _type_depth(graph, row.get("type"))))
    return chosen


def _type_depth(graph, type_term) -> int:
    if not isinstance(type_term, URIRef):
        return 0
    depth = 0
    seen = set()
    current = type_term
    while isinstance(current, URIRef) and current not in seen:
        seen.add(current)
        parents = [parent for parent in graph.objects(current, RDFS.subClassOf) if isinstance(parent, URIRef)]
        if not parents:
            break
        current = parents[0]
        depth += 1
    return depth


def _effect_from_row(row: dict) -> dict:
    type_id = local_name(row["type"]) if row.get("type") is not None else ""
    return {
        "id": local_name(row["uri"]),
        "uri": str(row["uri"]),
        "label": _text(row.get("label")),
        "type": type_id,
        "typeLabel": _text(row.get("typeLabel")),
        "gravite": _text(row.get("gravite")),
        "frequence": _text(row.get("frequence")),
        "categorie": effect_category(type_id),
    }


def _ci_from_row(row: dict) -> dict:
    type_id = local_name(row["type"]) if row.get("type") is not None else ""
    return {
        "id": local_name(row["uri"]),
        "uri": str(row["uri"]),
        "label": _text(row.get("label")),
        "type": type_id,
        "typeLabel": _text(row.get("typeLabel")),
        "niveauRisque": _text(row.get("niveauRisque")),
        "categorie": ci_category(type_id),
    }


def _sort_key(item: dict, field: str):
    value = item.get(field) or ""
    return fold(str(value))


def _paginate(items: list[dict], page: int, page_size: int, sort: str) -> tuple[list[dict], str]:
    descending = sort.startswith("-")
    field = sort[1:] if descending else sort
    allowed = {"label", "gravite", "frequence", "type", "niveauRisque", "categorie"}
    if field not in allowed:
        raise DomainError("Tri inconnu. Champs : label, gravite, frequence, type, niveauRisque, categorie.")
    ordered = sorted(items, key=lambda item: _sort_key(item, field), reverse=descending)
    start = (page - 1) * page_size
    return ordered[start : start + page_size], sort


def _page_args(page: int, page_size: int) -> None:
    if page < 1:
        raise DomainError("Le numéro de page commence à 1.")
    if page_size < 1 or page_size > 100:
        raise DomainError("La taille de page doit être comprise entre 1 et 100.")


def _keyword(items: list[dict], keyword: str | None) -> list[dict]:
    if not keyword:
        return items
    needle = fold(keyword)
    return [
        item
        for item in items
        if needle in fold(item.get("label") or "") or needle in fold(item.get("id") or "")
    ]


EFFECT_BODY = """
SELECT ?uri ?label ?type ?typeLabel ?gravite ?frequence
WHERE {
  ?uri a ?type ;
       rdfs:label ?label .
  ?type rdfs:subClassOf* :EffetSecondaire .
  FILTER(isIRI(?type))
  OPTIONAL { ?type rdfs:label ?typeLabel }
  OPTIONAL { ?uri :niveauGravite ?gravite }
  OPTIONAL { ?uri :frequence ?frequence }
  FILTER(LANG(?label) = "fr" || LANG(?label) = "")
  /*FILTERS*/
}
"""

CI_BODY = """
SELECT ?uri ?label ?type ?typeLabel ?niveauRisque
WHERE {
  ?uri a ?type ;
       rdfs:label ?label .
  ?type rdfs:subClassOf* :ContreIndication .
  FILTER(isIRI(?type))
  OPTIONAL { ?type rdfs:label ?typeLabel }
  OPTIONAL { ?uri :niveauRisque ?niveauRisque }
  FILTER(LANG(?label) = "fr" || LANG(?label) = "")
  /*FILTERS*/
}
"""


def _resolve(store: OntologyStore, name: str | None, expected: str) -> URIRef | None:
    if name is None or name == "":
        return None
    uri = pharma_uri(name)
    kind = individual_kind(store, uri)
    if kind != expected:
        label = {"medicament": "médicament", "molecule": "molécule", "pathologie": "pathologie"}[expected]
        raise DomainError(f"« {name} » n'est pas une {label} de l'ontologie.", 404)
    return uri


def list_effects(
    store: OntologyStore,
    *,
    q: str | None = None,
    gravite: str | None = None,
    categorie: str | None = None,
    medicament: str | None = None,
    molecule: str | None = None,
    page: int = 1,
    page_size: int = 20,
    sort: str = "label",
) -> dict:
    _page_args(page, page_size)
    gravite = canonical_gravite(gravite)
    categorie = canonical_effect_category(categorie)
    med_uri = _resolve(store, medicament, "medicament")
    mol_uri = _resolve(store, molecule, "molecule")
    filters = []
    if gravite:
        filters.append(f"FILTER(STR(?gravite) = {Literal(gravite).n3()})")
    if categorie:
        filters.append(_class_filter("?type", EFFECT_CATEGORY_CLASSES[categorie]))
    if med_uri is not None:
        filters.append(
            f"FILTER EXISTS {{ {med_uri.n3()} :contientMolecule ?molLien . ?molLien :peutProvoquer ?uri . }}"
        )
    if mol_uri is not None:
        filters.append(f"FILTER EXISTS {{ {mol_uri.n3()} :peutProvoquer ?uri . }}")
    sparql = EFFECT_BODY.replace("/*FILTERS*/", "\n  ".join(filters))
    result = _run(store, sparql)
    items = [_effect_from_row(row) for row in _collapse(result["rows"], store.graph)]
    items = _keyword(items, q)
    total = len(items)
    page_items, sort = _paginate(items, page, page_size, sort)
    return {
        "items": page_items,
        "total": total,
        "page": page,
        "pageSize": page_size,
        "sort": sort,
        "sparql": PREFIXES + "\n" + sparql,
        "filterNote": "Le mot-clé est comparé hors SPARQL, sans accent, sur le libellé et l'identifiant.",
    }


def list_contraindications(
    store: OntologyStore,
    *,
    q: str | None = None,
    categorie: str | None = None,
    niveau: str | None = None,
    medicament: str | None = None,
    molecule: str | None = None,
    pathologie: str | None = None,
    page: int = 1,
    page_size: int = 20,
    sort: str = "label",
) -> dict:
    _page_args(page, page_size)
    categorie = canonical_ci_category(categorie)
    niveau = canonical_risque(niveau)
    med_uri = _resolve(store, medicament, "medicament")
    mol_uri = _resolve(store, molecule, "molecule")
    path_uri = _resolve(store, pathologie, "pathologie")
    filters = []
    if categorie:
        filters.append(_class_filter("?type", CI_CATEGORY_CLASSES[categorie]))
    if niveau:
        filters.append(f"FILTER(STR(?niveauRisque) = {Literal(niveau).n3()})")
    if med_uri is not None:
        filters.append(
            f"FILTER EXISTS {{ {med_uri.n3()} :contientMolecule ?molLien . ?molLien :aContreIndication ?uri . }}"
        )
    if mol_uri is not None:
        filters.append(f"FILTER EXISTS {{ {mol_uri.n3()} :aContreIndication ?uri . }}")
    if path_uri is not None:
        filters.append(f"FILTER EXISTS {{ ?uri :concernePathologie {path_uri.n3()} . }}")
    sparql = CI_BODY.replace("/*FILTERS*/", "\n  ".join(filters))
    result = _run(store, sparql)
    items = [_ci_from_row(row) for row in _collapse(result["rows"], store.graph)]
    items = _keyword(items, q)
    total = len(items)
    page_items, sort = _paginate(items, page, page_size, sort)
    return {
        "items": page_items,
        "total": total,
        "page": page,
        "pageSize": page_size,
        "sort": sort,
        "sparql": PREFIXES + "\n" + sparql,
        "filterNote": "Le mot-clé est comparé hors SPARQL, sans accent, sur le libellé et l'identifiant.",
    }


def _links_for_effect(store: OntologyStore, uri: URIRef) -> dict:
    sparql = f"""
SELECT ?molecule ?moleculeLabel ?medicament ?medicamentLabel ?nomCommercial
WHERE {{
  ?molecule :peutProvoquer {uri.n3()} ;
            rdfs:label ?moleculeLabel .
  OPTIONAL {{
    ?medicament :contientMolecule ?molecule ;
                rdfs:label ?medicamentLabel .
    OPTIONAL {{ ?medicament :nomCommercial ?nomCommercial }}
  }}
}}
"""
    result = _run(store, sparql)
    molecules = {}
    medicaments = {}
    for row in result["rows"]:
        if row.get("molecule") is not None:
            molecules[str(row["molecule"])] = {
                "id": local_name(row["molecule"]),
                "uri": str(row["molecule"]),
                "label": _text(row.get("moleculeLabel")),
            }
        if row.get("medicament") is not None:
            medicaments[str(row["medicament"])] = {
                "id": local_name(row["medicament"]),
                "uri": str(row["medicament"]),
                "label": _text(row.get("medicamentLabel")),
                "nomCommercial": _text(row.get("nomCommercial")),
            }
    note = None
    if not molecules:
        note = (
            "Aucune molécule n'est reliée à cet effet par peutProvoquer. "
            "Il n'existe pas de propriété directe entre Médicament et EffetSecondaire : "
            "le chemin asserté est contientMolecule puis peutProvoquer."
        )
    return {
        "molecules": sorted(molecules.values(), key=lambda item: fold(item["label"] or "")),
        "medicaments": sorted(medicaments.values(), key=lambda item: fold(item["label"] or "")),
        "note": note,
        "sparql": PREFIXES + "\n" + sparql,
    }


def _links_for_ci(store: OntologyStore, uri: URIRef) -> dict:
    sparql = f"""
SELECT ?molecule ?moleculeLabel ?medicament ?medicamentLabel ?nomCommercial ?pathologie ?pathologieLabel
WHERE {{
  OPTIONAL {{
    ?molecule :aContreIndication {uri.n3()} ;
              rdfs:label ?moleculeLabel .
    OPTIONAL {{
      ?medicament :contientMolecule ?molecule ;
                  rdfs:label ?medicamentLabel .
      OPTIONAL {{ ?medicament :nomCommercial ?nomCommercial }}
    }}
  }}
  OPTIONAL {{
    {uri.n3()} :concernePathologie ?pathologie .
    ?pathologie rdfs:label ?pathologieLabel .
  }}
}}
"""
    result = _run(store, sparql)
    molecules = {}
    medicaments = {}
    pathologies = {}
    for row in result["rows"]:
        if row.get("molecule") is not None:
            molecules[str(row["molecule"])] = {
                "id": local_name(row["molecule"]),
                "uri": str(row["molecule"]),
                "label": _text(row.get("moleculeLabel")),
            }
        if row.get("medicament") is not None:
            medicaments[str(row["medicament"])] = {
                "id": local_name(row["medicament"]),
                "uri": str(row["medicament"]),
                "label": _text(row.get("medicamentLabel")),
                "nomCommercial": _text(row.get("nomCommercial")),
            }
        if row.get("pathologie") is not None:
            pathologies[str(row["pathologie"])] = {
                "id": local_name(row["pathologie"]),
                "uri": str(row["pathologie"]),
                "label": _text(row.get("pathologieLabel")),
            }
    notes = []
    if not molecules:
        notes.append("Aucune molécule n'est reliée par aContreIndication.")
    if not pathologies:
        notes.append(
            "Aucun triplet concernePathologie. "
            "Dans l'ontologie fournie, CI_AllergiePenicilline n'est pas reliée à une pathologie."
        )
    return {
        "molecules": sorted(molecules.values(), key=lambda item: fold(item["label"] or "")),
        "medicaments": sorted(medicaments.values(), key=lambda item: fold(item["label"] or "")),
        "pathologies": sorted(pathologies.values(), key=lambda item: fold(item["label"] or "")),
        "note": " ".join(notes) or None,
        "sparql": PREFIXES + "\n" + sparql,
    }


def get_effect(store: OntologyStore, effect_id: str) -> dict:
    uri = pharma_uri(effect_id)
    if individual_kind(store, uri) != "effet":
        raise DomainError(f"Effet secondaire « {effect_id} » introuvable.", 404)
    found = list_effects(store, page_size=100)
    item = next((row for row in found["items"] if row["id"] == effect_id), None)
    if item is None:
        # La pagination peut masquer l'individu si le jeu dépasse 100. Requête directe.
        direct = _run(store, EFFECT_BODY.replace("/*FILTERS*/", f"FILTER(?uri = {uri.n3()})"))
        rows = _collapse(direct["rows"], store.graph)
        if not rows:
            raise DomainError(f"Effet secondaire « {effect_id} » introuvable.", 404)
        item = _effect_from_row(rows[0])
    item.update(_links_for_effect(store, uri))
    return item


def get_contraindication(store: OntologyStore, ci_id: str) -> dict:
    uri = pharma_uri(ci_id)
    if individual_kind(store, uri) != "contre_indication":
        raise DomainError(f"Contre-indication « {ci_id} » introuvable.", 404)
    direct = _run(store, CI_BODY.replace("/*FILTERS*/", f"FILTER(?uri = {uri.n3()})"))
    rows = _collapse(direct["rows"], store.graph)
    if not rows:
        raise DomainError(f"Contre-indication « {ci_id} » introuvable.", 404)
    item = _ci_from_row(rows[0])
    item.update(_links_for_ci(store, uri))
    return item


def list_named(store: OntologyStore, root: str) -> list[dict]:
    sparql = f"""
SELECT ?uri ?label ?type ?extra
WHERE {{
  ?uri a ?type ;
       rdfs:label ?label .
  ?type rdfs:subClassOf* :{root} .
  FILTER(isIRI(?type))
  FILTER(LANG(?label) = "fr" || LANG(?label) = "")
  OPTIONAL {{
    ?uri :nomCommercial ?extra .
  }}
}}
"""
    result = _run(store, sparql)
    items = []
    seen = set()
    for row in _collapse(result["rows"], store.graph):
        ident = local_name(row["uri"])
        if ident in seen:
            continue
        seen.add(ident)
        items.append(
            {
                "id": ident,
                "uri": str(row["uri"]),
                "label": _text(row.get("label")),
                "type": local_name(row["type"]) if row.get("type") is not None else None,
                "nomCommercial": _text(row.get("extra")),
            }
        )
    return sorted(items, key=lambda item: fold(item["label"] or ""))


def resources(store: OntologyStore) -> dict:
    def labels(names: tuple[str, ...]) -> list[dict]:
        found = []
        for name in names:
            uri = pharma_uri(name)
            label = store.graph.value(uri, RDFS.label)
            found.append({"id": name, "uri": str(uri), "label": _text(label)})
        return found

    return {
        "effectTypes": labels(EFFECT_TYPES),
        "contraindicationTypes": labels(CI_TYPES),
        "molecules": list_named(store, "Molecule"),
        "medicaments": list_named(store, "Medicament"),
        "pathologies": list_named(store, "Pathologie"),
        "graviteValues": ["léger", "grave"],
        "risqueValues": ["absolu", "relatif"],
        "effectCategories": list(EFFECT_CATEGORY_CLASSES),
        "contraindicationCategories": list(CI_CATEGORY_CLASSES),
        "namingNote": (
            "Les sous-classes de niveau 3 des contre-indications s'appellent "
            "ContreIndicationAllergique, ContreIndicationDigestive, ContreIndicationRenale "
            "et ContreIndicationHepatique. Les noms courts Allergique, Digestive, Renale et Hepatique "
            "ne sont pas des classes de cette ontologie."
        ),
    }


def stats(store: OntologyStore) -> dict:
    def count(root: str) -> int:
        result = _run(
            store,
            f"""
SELECT (COUNT(DISTINCT ?uri) AS ?n)
WHERE {{
  ?uri a ?type .
  ?type rdfs:subClassOf* :{root} .
  FILTER(isIRI(?type))
}}
""",
        )
        raw = result["rows"][0]["n"] if result["rows"] else 0
        return int(raw)

    return {
        "triples": store.triple_count,
        "effects": count("EffetSecondaire"),
        "contraindications": count("ContreIndication"),
        "molecules": count("Molecule"),
        "medicaments": count("Medicament"),
        "pathologies": count("Pathologie"),
        "base": PHARMA_NS,
        "source": str(store.loaded_from) if store.loaded_from else None,
        "workingCopy": str(store.settings.graph_path),
        "reasoning": REASONING_LIMIT,
    }


def search(store: OntologyStore, q: str) -> dict:
    if not q or len(fold(q)) < 2:
        raise DomainError("Saisissez au moins deux caractères.")
    return {
        "q": q,
        "effects": list_effects(store, q=q, page_size=100)["items"],
        "contraindications": list_contraindications(store, q=q, page_size=100)["items"],
        "molecules": [item for item in list_named(store, "Molecule") if fold(q) in fold(item["label"]) or fold(q) in fold(item["id"])],
        "medicaments": [item for item in list_named(store, "Medicament") if fold(q) in fold(item["label"] or "") or fold(q) in fold(item["id"]) or fold(q) in fold(item.get("nomCommercial") or "")],
    }


def drugs_for_effect_category(store: OntologyStore, categorie: str) -> dict:
    categorie = canonical_effect_category(categorie)
    class_filter = _class_filter("?effetType", EFFECT_CATEGORY_CLASSES[categorie])
    sparql = f"""
SELECT ?uri ?label ?nomCommercial ?molecule ?moleculeLabel ?effet ?effetLabel
WHERE {{
  ?uri a ?type ;
       rdfs:label ?label ;
       :contientMolecule ?molecule .
  ?type rdfs:subClassOf* :Medicament .
  FILTER(isIRI(?type))
  ?molecule rdfs:label ?moleculeLabel ;
            :peutProvoquer ?effet .
  ?effet a ?effetType ;
         rdfs:label ?effetLabel .
  {class_filter}
  OPTIONAL {{ ?uri :nomCommercial ?nomCommercial }}
  FILTER(LANG(?label) = "fr" || LANG(?label) = "")
}}
"""
    return _group_drugs(store, sparql, categorie)


def drugs_for_effect(store: OntologyStore, effect_id: str) -> dict:
    uri = pharma_uri(effect_id)
    if individual_kind(store, uri) != "effet":
        raise DomainError(f"Effet secondaire « {effect_id} » introuvable.", 404)
    sparql = f"""
SELECT ?uri ?label ?nomCommercial ?molecule ?moleculeLabel ?effet ?effetLabel
WHERE {{
  ?uri a ?type ;
       rdfs:label ?label ;
       :contientMolecule ?molecule .
  ?type rdfs:subClassOf* :Medicament .
  ?molecule rdfs:label ?moleculeLabel ;
            :peutProvoquer {uri.n3()} .
  BIND({uri.n3()} AS ?effet)
  ?effet rdfs:label ?effetLabel .
  OPTIONAL {{ ?uri :nomCommercial ?nomCommercial }}
}}
"""
    return _group_drugs(store, sparql, None)


def drugs_for_ci_category(store: OntologyStore, categorie: str) -> dict:
    categorie = canonical_ci_category(categorie)
    class_name = CI_CATEGORY_CLASSES[categorie]
    sparql = f"""
SELECT ?uri ?label ?nomCommercial ?molecule ?moleculeLabel ?effet ?effetLabel
WHERE {{
  ?uri a ?type ;
       rdfs:label ?label ;
       :contientMolecule ?molecule .
  ?type rdfs:subClassOf* :Medicament .
  ?molecule rdfs:label ?moleculeLabel ;
            :aContreIndication ?ci .
  ?ci a ?ciType ;
      rdfs:label ?effetLabel .
  ?ciType rdfs:subClassOf* :{class_name} .
  BIND(?ci AS ?effet)
  OPTIONAL {{ ?uri :nomCommercial ?nomCommercial }}
}}
"""
    grouped = _group_drugs(store, sparql, categorie)
    for item in grouped["items"]:
        item["contraindications"] = list(item["effects"])
    return grouped


def effects_of(store: OntologyStore, kind: str, ident: str) -> dict:
    if kind == "medicament":
        return list_effects(store, medicament=ident, page_size=100)
    if kind == "molecule":
        return list_effects(store, molecule=ident, page_size=100)
    raise DomainError("La recherche d'effets attend un médicament ou une molécule.")


def contraindications_of(store: OntologyStore, kind: str, ident: str) -> dict:
    if kind == "medicament":
        return list_contraindications(store, medicament=ident, page_size=100)
    if kind == "molecule":
        return list_contraindications(store, molecule=ident, page_size=100)
    raise DomainError("La recherche de contre-indications attend un médicament ou une molécule.")


def count_effects(store: OntologyStore, gravite: str | None = None, categorie: str | None = None) -> dict:
    found = list_effects(store, gravite=gravite, categorie=categorie, page_size=100)
    sparql = """
SELECT (COUNT(DISTINCT ?uri) AS ?count)
WHERE {
  ?uri a ?type .
  ?type rdfs:subClassOf* :EffetSecondaire .
  FILTER(isIRI(?type))
  /*FILTERS*/
}
"""
    filters = []
    if gravite:
        filters.append(f"?uri :niveauGravite ?gravite . FILTER(STR(?gravite) = {Literal(canonical_gravite(gravite)).n3()})")
    if categorie:
        filters.append(_class_filter("?type", EFFECT_CATEGORY_CLASSES[canonical_effect_category(categorie)]))
    sparql = sparql.replace("/*FILTERS*/", "\n  ".join(filters))
    result = _run(store, sparql)
    value = int(result["rows"][0]["count"]) if result["rows"] else 0
    return {"value": value, "sparql": PREFIXES + "\n" + sparql, "sample": found["items"]}


def count_contraindications(store: OntologyStore, categorie: str | None = None) -> dict:
    sparql = """
SELECT (COUNT(DISTINCT ?uri) AS ?count)
WHERE {
  ?uri a ?type .
  ?type rdfs:subClassOf* :ContreIndication .
  FILTER(isIRI(?type))
  /*FILTERS*/
}
"""
    filters = []
    if categorie:
        filters.append(_class_filter("?type", CI_CATEGORY_CLASSES[canonical_ci_category(categorie)]))
    sparql = sparql.replace("/*FILTERS*/", "\n  ".join(filters))
    result = _run(store, sparql)
    value = int(result["rows"][0]["count"]) if result["rows"] else 0
    return {"value": value, "sparql": PREFIXES + "\n" + sparql}


def ask_link(store: OntologyStore, subject: dict, target: dict) -> dict:
    subject_uri = pharma_uri(subject["id"]).n3()
    target_uri = pharma_uri(target["id"]).n3()
    if target["kind"] == "effet":
        if subject["kind"] == "medicament":
            body = f"{subject_uri} :contientMolecule ?mol . ?mol :peutProvoquer {target_uri} ."
            path = "contientMolecule / peutProvoquer"
        else:
            body = f"{subject_uri} :peutProvoquer {target_uri} ."
            path = "peutProvoquer"
    elif target["kind"] == "contre_indication":
        if subject["kind"] == "medicament":
            body = f"{subject_uri} :contientMolecule ?mol . ?mol :aContreIndication {target_uri} ."
            path = "contientMolecule / aContreIndication"
        else:
            body = f"{subject_uri} :aContreIndication {target_uri} ."
            path = "aContreIndication"
    else:
        raise DomainError("La vérification attend un effet secondaire ou une contre-indication.")
    sparql = f"ASK {{ {body} }}"
    result = _run(store, sparql)
    return {"verified": bool(result["ask"]), "path": path, "sparql": PREFIXES + "\n" + sparql}


def _group_drugs(store: OntologyStore, sparql: str, categorie: str | None) -> dict:
    result = _run(store, sparql)
    grouped: dict[str, dict] = {}
    for row in result["rows"]:
        if row.get("uri") is None:
            continue
        ident = local_name(row["uri"])
        item = grouped.setdefault(
            ident,
            {
                "id": ident,
                "uri": str(row["uri"]),
                "label": _text(row.get("label")),
                "nomCommercial": _text(row.get("nomCommercial")),
                "molecules": {},
                "effects": {},
            },
        )
        if row.get("molecule") is not None:
            item["molecules"][str(row["molecule"])] = {
                "id": local_name(row["molecule"]),
                "uri": str(row["molecule"]),
                "label": _text(row.get("moleculeLabel")),
            }
        if row.get("effet") is not None:
            item["effects"][str(row["effet"])] = {
                "id": local_name(row["effet"]),
                "uri": str(row["effet"]),
                "label": _text(row.get("effetLabel")),
            }
    items = []
    for item in grouped.values():
        item["molecules"] = sorted(item["molecules"].values(), key=lambda value: fold(value["label"] or ""))
        item["effects"] = sorted(item["effects"].values(), key=lambda value: fold(value["label"] or ""))
        items.append(item)
    items.sort(key=lambda value: fold(value["label"] or ""))
    return {"items": items, "total": len(items), "categorie": categorie, "sparql": PREFIXES + "\n" + sparql}


def molecules_without_medicament(store: OntologyStore, categorie: str) -> list[dict]:
    categorie = canonical_effect_category(categorie)
    class_filter = _class_filter("?effetType", EFFECT_CATEGORY_CLASSES[categorie])
    sparql = f"""
SELECT ?uri ?label
WHERE {{
  ?uri a ?type ;
       rdfs:label ?label ;
       :peutProvoquer ?effet .
  ?type rdfs:subClassOf* :Molecule .
  ?effet a ?effetType .
  {class_filter}
  FILTER NOT EXISTS {{ ?medicament :contientMolecule ?uri }}
}}
"""
    result = _run(store, sparql)
    seen = {}
    for row in result["rows"]:
        seen[str(row["uri"])] = {"id": local_name(row["uri"]), "uri": str(row["uri"]), "label": _text(row.get("label"))}
    return list(seen.values())


def read_examples(path) -> list[dict]:
    text = path.read_text(encoding="utf-8")
    chunks = re.split(r"(?m)^# ===== ", text)
    prefix = chunks[0].strip()
    examples = []
    for chunk in chunks[1:]:
        title, _, body = chunk.partition("\n")
        lines = [line for line in body.splitlines() if not line.strip().startswith("#")]
        sparql = "\n".join(lines).strip()
        if not sparql:
            continue
        full = prefix + "\n" + sparql
        kind = "update" if re.match(r"\s*(INSERT|DELETE|WITH)", sparql, re.I) else "read"
        examples.append({"id": re.sub(r"[^a-z0-9]+", "-", fold(title.split("(")[0])).strip("-"), "title": title.strip(), "kind": kind, "sparql": full})
    return examples
