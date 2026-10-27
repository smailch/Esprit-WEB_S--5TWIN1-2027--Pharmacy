"""Sélection d'un modèle SPARQL et insertion des URI déjà validées."""

from __future__ import annotations

from app.nlp.intent_classifier import Intent
from app.ontology.loader import OntologyStore
from app.ontology.queries import (
    ask_link,
    contraindications_of,
    count_contraindications,
    count_effects,
    drugs_for_ci_category,
    drugs_for_effect,
    drugs_for_effect_category,
    effects_of,
    get_contraindication,
    get_effect,
    list_contraindications,
    list_effects,
    molecules_without_medicament,
)


def _public_entity(entity: dict) -> dict:
    return {key: entity[key] for key in ("kind", "id", "uri", "label", "text") if key in entity}


def execute_intent(store: OntologyStore, intent: Intent) -> dict:
    name = intent.name
    warnings: list[str] = []

    if name == "list_severe_effects":
        payload = list_effects(store, gravite="grave", page_size=100)
        return _from_list(payload, "effect")
    if name == "list_mild_effects":
        payload = list_effects(store, gravite="leger", page_size=100)
        return _from_list(payload, "effect")
    if name == "list_effects_by_category":
        payload = list_effects(store, categorie=intent.effect_category, page_size=100)
        return _from_list(payload, "effect")
    if name == "list_effects":
        payload = list_effects(store, page_size=100)
        return _from_list(payload, "effect")
    if name == "list_effects_of_entity":
        payload = effects_of(store, intent.entity["kind"], intent.entity["id"])
        shaped = _from_list(payload, "effect")
        shaped["warnings"].append(
            "Le médicament n'est pas relié directement à l'effet. Le chemin utilisé est contientMolecule puis peutProvoquer."
            if intent.entity["kind"] == "medicament"
            else "Le chemin utilisé est la propriété peutProvoquer, dont le domaine est Molécule."
        )
        return shaped
    if name == "list_drugs_for_effect_category":
        payload = drugs_for_effect_category(store, intent.effect_category)
        for molecule in molecules_without_medicament(store, intent.effect_category):
            warnings.append(
                f"{molecule['label']} provoque un effet {intent.effect_category}, "
                "mais aucun médicament ne la contient via contientMolecule."
            )
        return {"sparql": payload["sparql"], "results": payload["items"], "warnings": warnings, "resultShape": "medicament"}
    if name == "list_drugs_for_effect":
        payload = drugs_for_effect(store, intent.effect["id"])
        return {"sparql": payload["sparql"], "results": payload["items"], "warnings": warnings, "resultShape": "medicament"}
    if name == "list_contraindications":
        payload = list_contraindications(store, page_size=100)
        return _from_list(payload, "contraindication")
    if name == "list_contraindications_by_category":
        payload = list_contraindications(store, categorie=intent.ci_category, page_size=100)
        return _from_list(payload, "contraindication")
    if name == "list_drugs_for_ci_category":
        payload = drugs_for_ci_category(store, intent.ci_category)
        if intent.ci_category == "allergique":
            warnings.append(
                "Le lien retenu est aContreIndication vers ContreIndicationAllergique. "
                "La classe Allergie (donnée clinique du patient) est un autre module et n'est pas confondue avec cette contre-indication."
            )
        return {"sparql": payload["sparql"], "results": payload["items"], "warnings": warnings, "resultShape": "medicament"}
    if name == "list_drugs_for_ci":
        detail = get_contraindication(store, intent.contraindication["id"])
        return {
            "sparql": detail.get("sparql"),
            "results": detail["medicaments"],
            "warnings": [detail["note"]] if detail.get("note") else [],
            "resultShape": "medicament",
        }
    if name == "list_ci_of_entity":
        payload = contraindications_of(store, intent.entity["kind"], intent.entity["id"])
        shaped = _from_list(payload, "contraindication")
        shaped["warnings"].append("Le chemin utilisé est contientMolecule puis aContreIndication." if intent.entity["kind"] == "medicament" else "Le chemin utilisé est aContreIndication.")
        return shaped
    if name == "show_effect":
        detail = get_effect(store, intent.effect["id"])
        return {"sparql": detail.get("sparql"), "results": [detail], "warnings": [detail["note"]] if detail.get("note") else [], "resultShape": "effect"}
    if name == "show_contraindication":
        detail = get_contraindication(store, intent.contraindication["id"])
        return {"sparql": detail.get("sparql"), "results": [detail], "warnings": [detail["note"]] if detail.get("note") else [], "resultShape": "contraindication"}
    if name == "count_effects":
        payload = count_effects(store, gravite=intent.gravite, categorie=intent.effect_category)
        return {"sparql": payload["sparql"], "results": [{"count": payload["value"]}], "warnings": [], "resultShape": "count", "value": payload["value"]}
    if name == "count_contraindications":
        payload = count_contraindications(store, categorie=intent.ci_category)
        return {"sparql": payload["sparql"], "results": [{"count": payload["value"]}], "warnings": [], "resultShape": "count", "value": payload["value"]}
    if name == "check_relation":
        target = intent.effect or intent.contraindication
        payload = ask_link(store, intent.entity, target)
        verified = payload["verified"]
        return {
            "sparql": payload["sparql"],
            "results": [
                {
                    "verified": verified,
                    "path": payload["path"],
                    "subject": intent.entity["label"],
                    "object": target["label"],
                }
            ],
            "warnings": [],
            "resultShape": "ask",
            "message": (
                f"Oui : un chemin {payload['path']} est asserté."
                if verified
                else f"Non : aucun triplet ne relie ces individus par {payload['path']}."
            ),
        }
    if name == "profile_entity":
        effects = effects_of(store, intent.entity["kind"], intent.entity["id"])
        contraindications = contraindications_of(store, intent.entity["kind"], intent.entity["id"])
        rows = [{**item, "group": "effet"} for item in effects["items"]] + [
            {**item, "group": "contre-indication"} for item in contraindications["items"]
        ]
        return {
            "sparql": effects["sparql"] + "\n\n# --- contre-indications ---\n\n" + contraindications["sparql"],
            "results": rows,
            "warnings": [
                "Deux requêtes de lecture sont exécutées. Aucune relation médicament-effet directe n'est inventée."
            ],
            "resultShape": "profile",
        }
    raise ValueError(f"Intention sans modèle SPARQL : {name}")


def _from_list(payload: dict, shape: str) -> dict:
    warnings = []
    for item in payload["items"]:
        if item.get("note"):
            warnings.append(f"{item.get('label')} : {item['note']}")
    return {"sparql": payload["sparql"], "results": payload["items"], "warnings": warnings[:4], "resultShape": shape}


def describe_entities(entities: list[dict]) -> list[dict]:
    return [_public_entity(entity) for entity in entities]
