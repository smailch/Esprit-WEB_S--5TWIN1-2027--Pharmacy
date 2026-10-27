"""Chaîne complète : question française → SPARQL RDFLib.

Qwen2.5 3B Instruct (Ollama, local) écrit la requête quand NLP_ENGINE=qwen.
S'il est absent, la chaîne spaCy et les modèles SPARQL répondent à sa place.
"""

from __future__ import annotations

from app.nlp.entity_extractor import extract_entities
from app.nlp.intent_classifier import SUGGESTIONS, classify
from app.nlp.preprocessing import normalize
from app.nlp.qwen import QwenUnavailable, answer_with_qwen
from app.nlp.sparql_generator import describe_entities, execute_intent
from app.ontology.loader import OntologyStore
from app.ontology.queries import DomainError
from app.ontology.sparql_guard import SparqlRejected


def _prefer_rules(ruled: dict, notice: str) -> dict:
    ruled["warnings"] = [notice, *[item for item in ruled.get("warnings") or [] if item]]
    analysis = dict(ruled.get("analysis") or {})
    analysis["translator"] = "rules"
    analysis["qwen"] = "replaced"
    ruled["analysis"] = analysis
    return ruled


def answer_question(store: OntologyStore, question: str) -> dict:
    if store.settings.nlp_engine == "qwen":
        try:
            produced = answer_with_qwen(store, question)
        except (QwenUnavailable, SparqlRejected) as exc:
            notice = str(exc)
            if isinstance(exc, SparqlRejected):
                notice = f"Qwen a proposé une requête refusée ({exc}). Réponse par les règles."
            return _prefer_rules(answer_with_rules(store, question), notice)
        if not produced.get("results") and not produced.get("count"):
            ruled = answer_with_rules(store, question)
            if ruled.get("results") or ruled.get("count"):
                return _prefer_rules(
                    ruled,
                    "La requête de Qwen ne correspond à aucun triplet. "
                    "Réponse par les règles : sous-classes, contientMolecule, peutProvoquer et aContreIndication.",
                )
        return produced
    return answer_with_rules(store, question)


def answer_with_rules(store: OntologyStore, question: str) -> dict:
    cleaned = " ".join((question or "").split())
    normalized = normalize(cleaned)
    entities, notes, analysis = extract_entities(store.graph, cleaned, normalized)
    entity_dicts = [entity.as_dict() for entity in entities]
    intent = classify(normalized, entity_dicts)
    base = {
        "question": cleaned,
        "intent": intent.name,
        "entities": describe_entities(entity_dicts),
        "sparql": None,
        "results": [],
        "count": 0,
        "message": intent.message,
        "suggestions": intent.suggestions,
        "warnings": notes,
        "analysis": analysis,
    }
    if intent.name == "unknown":
        base["suggestions"] = intent.suggestions or SUGGESTIONS
        return base
    try:
        executed = execute_intent(store, intent)
    except DomainError as exc:
        base["message"] = str(exc)
        base["intent"] = "unknown"
        base["suggestions"] = SUGGESTIONS
        return base
    results = executed["results"]
    message = executed.get("message") or intent.message
    if executed.get("warnings"):
        base["warnings"] = notes + [warning for warning in executed["warnings"] if warning]
    if not results:
        message = message + " Aucun triplet asserté ne correspond."
    base.update(
        {
            "sparql": executed["sparql"],
            "results": results,
            "count": executed.get("value", len(results)),
            "message": message,
            "resultShape": executed.get("resultShape"),
        }
    )
    return base
