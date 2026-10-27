"""Création, modification et suppression d'individus du module B.

Les écritures passent par une liste blanche de classes et de propriétés.
Aucune requête SPARQL d'écriture fournie par le client n'est exécutée.
"""

from __future__ import annotations

import re
import unicodedata

from rdflib import Literal, URIRef
from rdflib.namespace import OWL, RDF, RDFS

from app.ontology.loader import OntologyStore
from app.ontology.queries import (
    DomainError,
    get_contraindication,
    get_effect,
    individual_kind,
    pharma_uri,
)
from app.ontology.vocab import (
    CI_DATATYPE_PROPERTIES,
    CI_TYPES,
    EFFECT_DATATYPE_PROPERTIES,
    EFFECT_TYPES,
    GRAVITE_BY_TYPE,
    GRAVITE_VALUES,
    PHARMA_NS,
    RISQUE_BY_TYPE,
    RISQUE_VALUES,
)


def _slug(label: str, prefix: str = "") -> str:
    folded = unicodedata.normalize("NFD", label)
    folded = "".join(char for char in folded if unicodedata.category(char) != "Mn")
    parts = re.findall(r"[A-Za-z0-9]+", folded)
    if not parts:
        raise DomainError("Le libellé ne permet pas de construire un identifiant.")
    body = "".join(part[:1].upper() + part[1:] for part in parts)
    if prefix and not body.startswith(prefix):
        body = prefix + body
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", body):
        raise DomainError("Identifiant généré invalide.")
    return body


def _clean_text(value: str, field: str, max_length: int = 120) -> str:
    text = " ".join((value or "").split())
    if len(text) < 2:
        raise DomainError(f"Le champ {field} est trop court.")
    if len(text) > max_length:
        raise DomainError(f"Le champ {field} dépasse {max_length} caractères.")
    if any(char in text for char in "<>{}\\|"):
        raise DomainError(f"Le champ {field} contient un caractère refusé.")
    return text


def _occupied(graph, name: str) -> bool:
    uri = URIRef(PHARMA_NS + name)
    return (uri, None, None) in graph or (None, None, uri) in graph


def _unique_id(graph, requested: str | None, label: str, prefix: str = "") -> str:
    if requested:
        pharma_uri(requested)
        if _occupied(graph, requested):
            raise DomainError(f"L'identifiant {requested} existe déjà.", 409)
        return requested
    base = _slug(label, prefix)
    candidate = base
    suffix = 2
    while _occupied(graph, candidate):
        candidate = f"{base}_{suffix}"
        suffix += 1
        if suffix > 50:
            raise DomainError("Impossible de trouver un identifiant libre.")
    return candidate


def _require_members(store: OntologyStore, names: list[str], expected: str) -> list[URIRef]:
    uris = []
    for name in names:
        uri = pharma_uri(name)
        if individual_kind(store, uri) != expected:
            raise DomainError(f"« {name} » n'est pas un individu de type {expected}.", 422)
        uris.append(uri)
    return uris


def _replace_type(graph, uri: URIRef, type_name: str, allowed: tuple[str, ...]) -> None:
    if type_name not in allowed:
        raise DomainError(f"Classe « {type_name} » non autorisée pour cette opération.")
    for current in list(graph.objects(uri, RDF.type)):
        if current == OWL.NamedIndividual:
            continue
        if local_ok(current, allowed):
            graph.remove((uri, RDF.type, current))
    graph.add((uri, RDF.type, URIRef(PHARMA_NS + type_name)))
    graph.add((uri, RDF.type, OWL.NamedIndividual))


def local_ok(term, allowed: tuple[str, ...]) -> bool:
    value = str(term)
    if not value.startswith(PHARMA_NS):
        return False
    return value[len(PHARMA_NS) :] in allowed


def _set_literal(graph, uri: URIRef, predicate: URIRef, value: str | None) -> None:
    graph.remove((uri, predicate, None))
    if value is not None and value != "":
        graph.add((uri, predicate, Literal(value)))


def _align_gravite(type_name: str, gravite: str | None) -> str:
    expected = GRAVITE_BY_TYPE.get(type_name)
    if gravite is None:
        if expected is None:
            raise DomainError("Indiquez niveauGravite : « léger » ou « grave ».")
        return expected
    if gravite not in GRAVITE_VALUES:
        raise DomainError("niveauGravite autorise uniquement « léger » ou « grave ».")
    if expected and gravite != expected:
        raise DomainError(f"La classe {type_name} impose niveauGravite « {expected} ».")
    return gravite


def _align_risque(type_name: str, risque: str | None) -> str:
    expected = RISQUE_BY_TYPE.get(type_name)
    if risque is None:
        if expected is None:
            raise DomainError("Indiquez niveauRisque : « absolu » ou « relatif ».")
        return expected
    if risque not in RISQUE_VALUES:
        raise DomainError("niveauRisque autorise uniquement « absolu » ou « relatif ».")
    if expected and risque != expected:
        raise DomainError(f"La classe {type_name} impose niveauRisque « {expected} ».")
    return risque


def _relink_effect(graph, effect: URIRef, molecules: list[URIRef]) -> None:
    predicate = URIRef(PHARMA_NS + "peutProvoquer")
    graph.remove((None, predicate, effect))
    for molecule in molecules:
        graph.add((molecule, predicate, effect))


def _relink_ci(graph, ci: URIRef, molecules: list[URIRef], pathologies: list[URIRef]) -> None:
    indication = URIRef(PHARMA_NS + "aContreIndication")
    concerns = URIRef(PHARMA_NS + "concernePathologie")
    graph.remove((None, indication, ci))
    graph.remove((ci, concerns, None))
    for molecule in molecules:
        graph.add((molecule, indication, ci))
    for pathology in pathologies:
        graph.add((ci, concerns, pathology))


def create_effect(store: OntologyStore, payload: dict) -> dict:
    label = _clean_text(payload.get("label", ""), "label")
    type_name = payload.get("type") or ""
    if type_name not in EFFECT_TYPES:
        raise DomainError("Classe d'effet non autorisée.", 422)
    gravite = _align_gravite(type_name, payload.get("gravite"))
    frequence = payload.get("frequence")
    if frequence:
        frequence = _clean_text(frequence, "frequence", 60)
    molecules = _require_members(store, payload.get("molecules") or [], "molecule")

    def mutate(graph):
        ident = _unique_id(graph, payload.get("id"), label)
        uri = pharma_uri(ident)
        _replace_type(graph, uri, type_name, EFFECT_TYPES)
        graph.add((uri, RDFS.label, Literal(label, lang="fr")))
        graph.add((uri, URIRef(PHARMA_NS + "niveauGravite"), Literal(gravite)))
        if frequence:
            graph.add((uri, URIRef(PHARMA_NS + "frequence"), Literal(frequence)))
        _relink_effect(graph, uri, molecules)
        return ident

    ident = store.update_graph(mutate)
    created = get_effect(store, ident)
    created["writtenProperties"] = ["rdf:type", "rdfs:label", *EFFECT_DATATYPE_PROPERTIES, "peutProvoquer"]
    return created


def update_effect(store: OntologyStore, effect_id: str, payload: dict) -> dict:
    current = get_effect(store, effect_id)
    type_name = payload.get("type") or current["type"]
    if type_name not in EFFECT_TYPES:
        raise DomainError("Classe d'effet non autorisée.")
    label = _clean_text(payload["label"], "label") if payload.get("label") else current["label"]
    gravite_in = payload.get("gravite", current.get("gravite"))
    gravite = _align_gravite(type_name, gravite_in)
    if "frequence" in payload and payload["frequence"] is not None:
        frequence = _clean_text(payload["frequence"], "frequence", 60) if payload["frequence"] != "" else ""
    else:
        frequence = current.get("frequence") or ""
    if "molecules" in payload and payload["molecules"] is not None:
        molecules = _require_members(store, payload["molecules"], "molecule")
    else:
        molecules = [pharma_uri(item["id"]) for item in current["molecules"]]

    def mutate(graph):
        uri = pharma_uri(effect_id)
        _replace_type(graph, uri, type_name, EFFECT_TYPES)
        graph.remove((uri, RDFS.label, None))
        graph.add((uri, RDFS.label, Literal(label, lang="fr")))
        _set_literal(graph, uri, URIRef(PHARMA_NS + "niveauGravite"), gravite)
        _set_literal(graph, uri, URIRef(PHARMA_NS + "frequence"), frequence or None)
        _relink_effect(graph, uri, molecules)

    store.update_graph(mutate)
    return get_effect(store, effect_id)


def _guard_axiom(graph, uri: URIRef) -> None:
    if (None, OWL.hasValue, uri) in graph:
        raise DomainError(
            "Cet individu est cité par un axiome OWL owl:hasValue. Suppression refusée pour ne pas casser l'ontologie.",
            409,
        )


def delete_effect(store: OntologyStore, effect_id: str) -> dict:
    get_effect(store, effect_id)

    def mutate(graph):
        uri = pharma_uri(effect_id)
        _guard_axiom(graph, uri)
        graph.remove((None, None, uri))
        graph.remove((uri, None, None))

    store.update_graph(mutate)
    return {"deleted": effect_id, "uri": PHARMA_NS + effect_id}


def create_contraindication(store: OntologyStore, payload: dict) -> dict:
    label = _clean_text(payload.get("label", ""), "label")
    type_name = payload.get("type") or ""
    if type_name not in CI_TYPES:
        raise DomainError("Classe de contre-indication non autorisée.")
    risque = _align_risque(type_name, payload.get("niveauRisque"))
    molecules = _require_members(store, payload.get("molecules") or [], "molecule")
    pathologies = _require_members(store, payload.get("pathologies") or [], "pathologie")

    def mutate(graph):
        ident = _unique_id(graph, payload.get("id"), label, prefix="CI_")
        uri = pharma_uri(ident)
        _replace_type(graph, uri, type_name, CI_TYPES)
        graph.add((uri, RDFS.label, Literal(label, lang="fr")))
        graph.add((uri, URIRef(PHARMA_NS + "niveauRisque"), Literal(risque)))
        _relink_ci(graph, uri, molecules, pathologies)
        return ident

    ident = store.update_graph(mutate)
    created = get_contraindication(store, ident)
    created["writtenProperties"] = ["rdf:type", "rdfs:label", *CI_DATATYPE_PROPERTIES, "aContreIndication", "concernePathologie"]
    return created


def update_contraindication(store: OntologyStore, ci_id: str, payload: dict) -> dict:
    current = get_contraindication(store, ci_id)
    type_name = payload.get("type") or current["type"]
    if type_name not in CI_TYPES:
        raise DomainError("Classe de contre-indication non autorisée.")
    label = _clean_text(payload["label"], "label") if payload.get("label") else current["label"]
    risque = _align_risque(type_name, payload.get("niveauRisque", current.get("niveauRisque")))
    molecules = (
        _require_members(store, payload["molecules"], "molecule")
        if payload.get("molecules") is not None
        else [pharma_uri(item["id"]) for item in current["molecules"]]
    )
    pathologies = (
        _require_members(store, payload["pathologies"], "pathologie")
        if payload.get("pathologies") is not None
        else [pharma_uri(item["id"]) for item in current["pathologies"]]
    )

    def mutate(graph):
        uri = pharma_uri(ci_id)
        _replace_type(graph, uri, type_name, CI_TYPES)
        graph.remove((uri, RDFS.label, None))
        graph.add((uri, RDFS.label, Literal(label, lang="fr")))
        _set_literal(graph, uri, URIRef(PHARMA_NS + "niveauRisque"), risque)
        _relink_ci(graph, uri, molecules, pathologies)

    store.update_graph(mutate)
    return get_contraindication(store, ci_id)


def delete_contraindication(store: OntologyStore, ci_id: str) -> dict:
    get_contraindication(store, ci_id)

    def mutate(graph):
        uri = pharma_uri(ci_id)
        _guard_axiom(graph, uri)
        graph.remove((None, None, uri))
        graph.remove((uri, None, None))

    store.update_graph(mutate)
    return {"deleted": ci_id, "uri": PHARMA_NS + ci_id}

