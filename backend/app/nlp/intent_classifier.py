"""Classification d'intentions par règles explicables, après normalisation."""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class Intent:
    name: str
    gravite: str | None = None
    effect_category: str | None = None
    ci_category: str | None = None
    entity: dict | None = None
    effect: dict | None = None
    contraindication: dict | None = None
    message: str = ""
    suggestions: list[str] = field(default_factory=list)


SUGGESTIONS = [
    "Quels sont les effets secondaires graves ?",
    "Quels médicaments sont associés à des effets digestifs ?",
    "Quelles sont les contre-indications rénales ?",
    "Quels médicaments sont liés aux allergies ?",
    "Quels effets secondaires sont associés à Doliprane ?",
    "Combien d'effets secondaires sont enregistrés ?",
    "Affiche les contre-indications hépatiques.",
]


def _unknown(message: str) -> Intent:
    return Intent("unknown", message=message, suggestions=SUGGESTIONS)


def classify(normalized: str, entities: list[dict]) -> Intent:
    if not normalized:
        return _unknown("La question est vide. Reformulez-la en indiquant un effet, une gravité ou une contre-indication.")

    listing = bool(re.search(r"\b(quel|quelle|quels|quelles|liste|afficher|affiche|montre|donner|donne)\b", normalized))
    counting = bool(re.search(r"\b(combien|nombre)\b", normalized))
    checking = (not listing) and bool(
        re.search(r"\b(peut il|peut elle|est ce que|est il|est elle|a t il|a t elle|possede|provoque)\b", normalized)
    )
    has_effect = bool(re.search(r"\beffet\b", normalized))
    has_ci = "contre-indication" in normalized
    has_drug_word = bool(re.search(r"\bmedicament\b", normalized))
    gravite = "grave" if re.search(r"\bgrave\b", normalized) else None
    if gravite is None and re.search(r"\bleger\b", normalized):
        gravite = "leger"
    effect_category = next((name for name in ("digestif", "cutane", "neurologique") if re.search(rf"\b{name}\b", normalized)), None)
    ci_category = None
    if has_ci or "allergique" in normalized:
        if re.search(r"\brenal\b", normalized):
            ci_category = "renale"
        elif re.search(r"\bhepatique\b", normalized):
            ci_category = "hepatique"
        elif re.search(r"\bdigestif\b", normalized) and has_ci:
            ci_category = "digestive"
        elif "allergique" in normalized:
            ci_category = "allergique"
        elif re.search(r"\babsolu\b", normalized):
            ci_category = "absolue"
        elif re.search(r"\brelatif\b", normalized):
            ci_category = "relative"

    subjects = [entity for entity in entities if entity["kind"] in {"medicament", "molecule"}]
    effects = [entity for entity in entities if entity["kind"] == "effet"]
    contraindications = [entity for entity in entities if entity["kind"] == "contre_indication"]
    entity = subjects[0] if subjects else None

    if counting and has_effect and not has_ci:
        return Intent("count_effects", gravite=gravite, effect_category=effect_category, message="Comptage des effets secondaires assertés.")
    if counting and (has_ci or ci_category):
        return Intent("count_contraindications", ci_category=ci_category, message="Comptage des contre-indications assertées.")

    if checking and entity and (effects or contraindications):
        target = effects[0] if effects else contraindications[0]
        return Intent(
            "check_relation",
            entity=entity,
            effect=effects[0] if effects else None,
            contraindication=contraindications[0] if contraindications else None,
            message=f"Vérification d'un chemin réel entre {entity['label']} et {target['label']}.",
        )
    if checking and not (entity and (effects or contraindications)):
        return _unknown(
            "Pour une vérification, citez un médicament ou une molécule de l'ontologie et un effet ou une contre-indication reconnus."
        )

    if has_effect and has_ci and entity:
        return Intent("profile_entity", entity=entity, message=f"Effets et contre-indications reliés à {entity['label']}.")

    if has_ci or contraindications or (ci_category and not has_effect):
        if has_drug_word and ci_category:
            return Intent(
                "list_drugs_for_ci_category",
                ci_category=ci_category,
                message=f"Médicaments dont une molécule a une contre-indication {ci_category}.",
            )
        if has_drug_word and contraindications:
            return Intent(
                "list_drugs_for_ci",
                contraindication=contraindications[0],
                message=f"Médicaments reliés à la contre-indication {contraindications[0]['label']}.",
            )
        if entity:
            return Intent("list_ci_of_entity", entity=entity, message=f"Contre-indications reliées à {entity['label']}.")
        if ci_category:
            return Intent(
                "list_contraindications_by_category",
                ci_category=ci_category,
                message=f"Contre-indications de catégorie {ci_category}.",
            )
        if contraindications and not has_ci:
            return Intent("show_contraindication", contraindication=contraindications[0], message="Fiche de la contre-indication reconnue.")
        if has_ci:
            return Intent("list_contraindications", message="Liste des contre-indications assertées.")

    if has_effect or effects or gravite or effect_category:
        if has_drug_word and not entity and effect_category:
            return Intent(
                "list_drugs_for_effect_category",
                effect_category=effect_category,
                message=f"Médicaments dont une molécule peut provoquer un effet {effect_category}.",
            )
        if has_drug_word and not entity and effects:
            return Intent(
                "list_drugs_for_effect",
                effect=effects[0],
                message=f"Médicaments dont une molécule peut provoquer {effects[0]['label']}.",
            )
        if has_drug_word and not entity and not effects and not effect_category and not gravite:
            return _unknown(
                "Précisez l'effet, sa gravité (léger ou grave), sa catégorie (digestif, cutané, neurologique) ou le nom du médicament."
            )
        if entity:
            return Intent("list_effects_of_entity", entity=entity, message=f"Effets reliés à {entity['label']} par peutProvoquer.")
        if gravite == "grave":
            return Intent("list_severe_effects", gravite="grave", message="Effets dont niveauGravite vaut « grave ».")
        if gravite == "leger":
            return Intent("list_mild_effects", gravite="leger", message="Effets dont niveauGravite vaut « léger ».")
        if effect_category:
            return Intent(
                "list_effects_by_category",
                effect_category=effect_category,
                message=f"Effets de catégorie {effect_category}, d'après la sous-classe assertée.",
            )
        if effects and not has_effect:
            return Intent("show_effect", effect=effects[0], message="Fiche de l'effet reconnu.")
        if has_effect:
            return Intent("list_effects", message="Liste des effets secondaires assertés.")

    if entity:
        return Intent("list_effects_of_entity", entity=entity, message=f"Aucun filtre explicite : effets reliés à {entity['label']}.")

    return _unknown(
        "Question non reconnue. Reformulez-la avec un effet, une gravité, une contre-indication "
        "ou le nom d'un médicament présent dans l'ontologie."
    )
