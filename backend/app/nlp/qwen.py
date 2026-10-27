"""Traduction français → SPARQL par Qwen2.5 3B Instruct, en local via Ollama.

Les poids ne sont pas dans le dépôt. Ollama les charge avec
``ollama pull qwen2.5:3b`` (variante Instruct, environ 1,9 Go).
La requête produite est refusée si elle n'est pas une lecture SPARQL.
"""

from __future__ import annotations

import re

import httpx
from rdflib import Literal, URIRef

from app.b_config import Settings
from app.nlp.entity_extractor import build_aliases
from app.ontology.loader import OntologyError, OntologyStore
from app.ontology.queries import local_name
from app.ontology.sparql_guard import SparqlRejected, validate_read_query
from app.ontology.vocab import CI_TYPES, EFFECT_TYPES, PREFIXES

# RDFLib n'infère pas rdf:type le long de rdfs:subClassOf.
# Les individus sont typés par une feuille (EffetGraveDigestif, etc.).
_DIRECT_TYPE = re.compile(
    r"(\?[A-Za-z_][\w]*)\s+a\s+:(" + "|".join((*EFFECT_TYPES, *CI_TYPES)) + r")\b"
)

_FENCE = re.compile(r"```(?:sparql|turtle)?\s*(.*?)```", re.IGNORECASE | re.DOTALL)
_START = re.compile(r"(?im)^[ \t]*(PREFIX|BASE|SELECT|ASK|CONSTRUCT|DESCRIBE)\b")

SYSTEM = """Tu traduis une question française en une seule requête SPARQL pour l'ontologie pharmaceutique http://example.org/pharma#.
Réponds uniquement avec un bloc ```sparql. Si la question ne porte pas sur cette ontologie, réponds exactement AUCUNE.

Préfixes obligatoires :
PREFIX : <http://example.org/pharma#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

Chemins réels, à ne pas inventer :
- Un médicament rejoint un effet par :contientMolecule puis :peutProvoquer. Il n'existe pas de propriété directe médicament → effet.
- Une molécule porte :peutProvoquer vers un effet et :aContreIndication vers une contre-indication.
- Une contre-indication peut avoir :concernePathologie.
- :niveauGravite vaut "léger" ou "grave". :niveauRisque vaut "absolu" ou "relatif".
- Les effets graves digestifs sont :EffetGraveDigestif, les effets légers digestifs :EffetLegerDigestif, les cutanés :EffetLegerCutane, les neurologiques graves :EffetGraveNeurologique.
- Les contre-indications s'appellent :ContreIndicationAllergique, :ContreIndicationDigestive, :ContreIndicationRenale, :ContreIndicationHepatique.
- Pour une classe et ses sous-classes : `?individu a ?type . ?type rdfs:subClassOf* :NomDeClasse . FILTER(isIRI(?type))`.
- Filtre les littéraux avec FILTER(STR(?gravite) = "grave") ou FILTER(STR(?gravite) = "léger"), et FILTER(STR(?niveauRisque) = "absolu") ou "relatif".
- SELECT, ASK, CONSTRUCT ou DESCRIBE seulement. Jamais INSERT, DELETE, UPDATE, DROP, CLEAR, LOAD ni SERVICE.
- N'emploie que les individus listés dans le message utilisateur. Les identifiants sont sans accent : Ibuprofene, HemorragieDigestive, Nausee.
- Un effet grave est un individu, pas une classe. Ne mets jamais rdfs:subClassOf sur l'effet lui-même.

Exemple — effets graves :
SELECT ?effet ?label WHERE {
  ?effet a ?type .
  ?effet rdfs:label ?label .
  ?effet :niveauGravite ?gravite .
  ?type rdfs:subClassOf* :EffetSecondaire .
  FILTER(isIRI(?type))
  FILTER(STR(?gravite) = "grave")
}

Exemple — effets d'un médicament :
SELECT ?effet ?label WHERE {
  :Doliprane :contientMolecule ?molecule .
  ?molecule :peutProvoquer ?effet .
  ?effet rdfs:label ?label .
}
"""


class QwenUnavailable(RuntimeError):
    """Ollama ou le modèle Qwen2.5 3B Instruct ne peut pas répondre."""


def _model_ready(names: list[str], model: str) -> bool:
    return any(name == model or name.startswith(model) for name in names)


def probe_qwen(settings: Settings) -> dict:
    model = settings.ollama_model
    if settings.nlp_engine != "qwen":
        return {"engine": settings.nlp_engine, "model": model, "ready": False, "detail": "Chaîne par règles."}
    url = settings.ollama_url.rstrip("/") + "/api/tags"
    try:
        response = httpx.get(url, timeout=1.5)
        response.raise_for_status()
        names = [item.get("name", "") for item in response.json().get("models", [])]
    except Exception:
        return {
            "engine": "qwen",
            "model": model,
            "ready": False,
            "detail": f"Ollama ne répond pas sur {settings.ollama_url}.",
        }
    ready = _model_ready(names, model)
    detail = f"{model} est prêt." if ready else f"Ollama répond. Le modèle {model} n'est pas téléchargé."
    return {"engine": "qwen", "model": model, "ready": ready, "detail": detail}


def lexicon_block(graph) -> str:
    lines = []
    seen = set()
    for alias in build_aliases(graph):
        key = (alias.kind, alias.ident)
        if key in seen:
            continue
        seen.add(key)
        lines.append(f"- {alias.kind} :{alias.ident} « {alias.label} »")
    return "\n".join(lines)


def extract_sparql(text: str) -> str | None:
    cleaned = (text or "").strip()
    if not cleaned or cleaned.upper().startswith("AUCUNE"):
        return None
    fenced = _FENCE.search(cleaned)
    body = fenced.group(1).strip() if fenced else cleaned
    if body.upper().startswith("AUCUNE"):
        return None
    start = _START.search(body)
    if not start:
        return None
    return body[start.start() :].strip()


def generate_sparql(settings: Settings, question: str, graph) -> str:
    """Appelle Ollama et renvoie le texte SPARQL brut, ou lève QwenUnavailable."""
    payload = {
        "model": settings.ollama_model,
        "stream": False,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {
                "role": "user",
                "content": (
                    "Individus présents dans le graphe :\n"
                    f"{lexicon_block(graph)}\n\n"
                    f"Question : {question}"
                ),
            },
        ],
        "options": {"temperature": 0, "num_predict": 700, "num_ctx": 2048},
    }
    url = settings.ollama_url.rstrip("/") + "/api/chat"
    timeout = httpx.Timeout(connect=2.0, read=settings.ollama_timeout, write=30.0, pool=2.0)
    try:
        response = httpx.post(url, json=payload, timeout=timeout)
    except httpx.HTTPError as exc:
        raise QwenUnavailable(
            f"Qwen2.5 3B Instruct est injoignable ({settings.ollama_url}). "
            f"Lancez Ollama puis `ollama pull {settings.ollama_model}`."
        ) from exc
    if response.status_code == 404:
        raise QwenUnavailable(
            f"Le modèle {settings.ollama_model} n'est pas installé dans Ollama. "
            f"Commande : ollama pull {settings.ollama_model}"
        )
    if response.status_code >= 400:
        raise QwenUnavailable(f"Ollama a répondu {response.status_code}.")
    content = response.json().get("message", {}).get("content", "")
    sparql = extract_sparql(content)
    if not sparql:
        raise QwenUnavailable("Qwen n'a pas produit de requête SPARQL pour cette question.")
    return sparql


def _binding_label(row: dict) -> tuple[str, str, int | None]:
    label = None
    ident = None
    count = None
    for key, value in row.items():
        if isinstance(value, Literal):
            if key.lower() == "count":
                try:
                    count = int(value)
                except (TypeError, ValueError):
                    count = None
            elif label is None or key.lower() in {"label", "nom", "libelle"}:
                label = str(value)
        elif isinstance(value, URIRef) and ident is None:
            ident = local_name(value)
    if label is None:
        parts = []
        for key, value in row.items():
            shown = local_name(value) if isinstance(value, URIRef) else str(value)
            parts.append(f"{key}={shown}")
        label = ", ".join(parts) or "résultat"
    return ident or label, label, count


def shape_results(result: dict, limit: int) -> tuple[list[dict], int]:
    if result["kind"] == "ASK":
        verified = bool(result["ask"])
        return [{"id": "ask", "label": "oui" if verified else "non", "verified": verified, "path": "ASK"}], 1
    rows = []
    for row in result["rows"][:limit]:
        if result["kind"] == "CONSTRUCT":
            subject, predicate, obj = row
            rows.append({"id": local_name(subject), "label": f"{local_name(subject)} {local_name(predicate)} {local_name(obj)}"})
            continue
        ident, label, count = _binding_label(row)
        item = {"id": ident, "label": label}
        if count is not None:
            item["count"] = count
        rows.append(item)
    return rows, len(result["rows"])


def widen_direct_types(query: str) -> str:
    """Remplace ``?x a :ClasseParente`` par un chemin de sous-classes.

    ``?effet a :EffetSecondaire`` ne matche personne : Hémorragie digestive
    est ``:EffetGraveDigestif``, sous-classe de ``:EffetGrave``.
    """
    counter = {"n": 0}

    def replace(match: re.Match) -> str:
        counter["n"] += 1
        variable, class_name = match.group(1), match.group(2)
        type_variable = f"?_type{counter['n']}"
        return (
            f"{variable} a {type_variable} . "
            f"{type_variable} rdfs:subClassOf* :{class_name} . "
            f"FILTER(isIRI({type_variable}))"
        )

    return _DIRECT_TYPE.sub(replace, query)


def answer_with_qwen(store: OntologyStore, question: str) -> dict:
    settings = store.settings
    cleaned = " ".join((question or "").split())
    sparql = generate_sparql(settings, cleaned, store.graph)
    query = validate_read_query(sparql, settings.sparql_max_length)
    # Les préfixes officiels remplacent ceux du modèle : un rdfs: mal copié
    # ferait échouer rdfs:label et rdfs:subClassOf.
    body = "\n".join(line for line in query.splitlines() if not re.match(r"(?i)^\s*(PREFIX|BASE)\b", line))
    widened = widen_direct_types(body.strip())
    widened_types = widened != body.strip()
    query = f"{PREFIXES}\n{widened}"
    try:
        executed = store.query(query)
    except OntologyError as exc:
        return _payload(cleaned, query, [], 0, f"Requête Qwen refusée par RDFLib : {exc}", settings.ollama_model)
    rows, total = shape_results(executed, settings.sparql_max_rows)
    count = rows[0]["count"] if len(rows) == 1 and "count" in rows[0] else len(rows)
    message = "Requête écrite par Qwen2.5 3B Instruct et exécutée par RDFLib sur les triplets assertés."
    if widened_types:
        message += (
            " Le type direct a été élargi aux sous-classes : aucun effet n'est typé :EffetSecondaire, "
            "les graves sont :EffetGraveDigestif ou :EffetGraveNeurologique."
        )
    if total == 0:
        message += " Aucun triplet asserté ne correspond."
    if total > len(rows):
        message += f" Affichage limité à {len(rows)} lignes."
    return _payload(cleaned, query, rows, count, message, settings.ollama_model)


def _payload(question: str, sparql: str | None, results: list[dict], count: int, message: str, model: str) -> dict:
    return {
        "question": question,
        "intent": "qwen_sparql",
        "entities": [],
        "sparql": sparql,
        "results": results,
        "count": count,
        "message": message,
        "suggestions": [],
        "warnings": [],
        "analysis": {"analyzer": model, "translator": "ollama"},
    }
