"""Étape 6 — Orchestration : question → analyse → entités → intention → SPARQL → exécution RDFLib → réponse expliquée."""
from __future__ import annotations

import re
import time

from app.graph_store import store

from . import lexicon
from .entity_extractor import extract, extract_threshold, first
from .intent_classifier import BY_NAME, INTENTS, classify
from .preprocessing import analyse, load_nlp, strip_accents
from .sparql_generator import generate

MODEL_NAME = "PrescriNLU-D"

TYPE_NEEDED = {"PATIENT": "patients", "MEDECIN": "médecins", "PHARMACIEN": "pharmaciens", "PRESCRIPTION": "ordonnances"}


def _plural(n: int, word: str) -> str:
    return f"{n} " + (" ".join(w + "s" for w in word.split()) if n > 1 else word)


def _known(lex, kind: str, limit: int = 8) -> str:
    return ", ".join(e.label if kind != "PRESCRIPTION" else e.id for e in lex.by_type.get(kind, [])[:limit])


def _message(intent: str, family: str, entities, rows, answer, filters, lex) -> str:
    P, PAT, MED = first(entities, "PRESCRIPTION"), first(entities, "PATIENT"), first(entities, "MEDICAMENT")
    n = len(rows)
    if family == "compter_prescriptions":
        return f"{_plural(rows[0]['nombre'], 'prescription')} correspond{'ent' if rows[0]['nombre'] > 1 else ''} à la question."
    if family == "compter_donnees":
        return f"{_plural(rows[0]['nombre'], 'donnée clinique')} correspond{'ent' if rows[0]['nombre'] > 1 else ''} à la question."
    if answer is not None:
        return "Oui." if answer else "Non."
    if n == 0:
        if family == "pharmacien_prescription":
            return f"{P.label} n'a pas encore été délivrée en pharmacie (aucun triplet :estDelivreePar)."
        if family == "verifier_contre_indication":
            who = PAT.label if PAT else (P.label if P else "les ordonnances enregistrées")
            return f"Aucune contre-indication, allergie, antécédent ou analyse à risque détecté pour {who}."
        if family in ("lister_donnees", "valeur_mesure", "seuil_mesure"):
            return "La requête est valide mais aucune donnée clinique ne correspond dans l'ontologie."
        return "La requête est valide mais ne renvoie aucun résultat dans l'ontologie."
    if family == "lister_prescriptions":
        return f"{_plural(n, 'prescription')} trouvée{'s' if n > 1 else ''} : " + ", ".join(r["prescription"] for r in rows) + "."
    if family == "prescripteur":
        return "Prescrit par " + ", ".join(sorted({r["nom"] + (f" ({r['specialite']})" if r.get("specialite") else "") for r in rows})) + "."
    if family == "patient_prescription":
        r = rows[0]
        return f"{P.label} concerne {r['nom']}" + (f", {r['age']} ans" if r.get("age") is not None else "") + (
            f" (pathologies : {r['pathologies']})" if r.get("pathologies") else "") + "."
    if family == "patients_medicament":
        return f"{MED.label} a été prescrit à : " + ", ".join(sorted({r["nom"] for r in rows})) + "."
    if family == "pharmacien_prescription":
        return f"{P.label} a été délivrée par {rows[0]['nom']}."
    if family in ("medicaments_prescription", "medicaments_patient"):
        labels = sorted({r["label"] for r in rows})
        return f"{_plural(len(labels), 'médicament')} : " + ", ".join(labels) + "."
    if family == "details_prescription":
        r = rows[0]
        return (f"{r['label']} du {r['date']} : {r['medicaments']} pour {r['patient']}, prescrit par {r['medecin']} ; "
                f"posologie « {r['posologie']} » pendant {r['duree']} jours" + (", renouvelable" if r.get("renouvelable") else "") + ".")
    if family == "lister_donnees":
        items = [f"{r['label']}" + (f" = {r['valeur']:g} {r['unite'] or ''}".rstrip() if r.get("valeur") is not None else "")
                 + (f" ({r['detail']})" if r.get("detail") else "") + f" — {r['patient']}" for r in rows]
        return f"{_plural(n, 'donnée clinique')} : " + " ; ".join(items) + "."
    if family in ("valeur_mesure", "seuil_mesure"):
        items = [f"{r['nom']} : {r['valeur']:g} {r['unite'] or ''}".rstrip() + (f" (mesure du {r['date']})" if r.get("date") else "") for r in rows]
        return f"{rows[0]['examen']} — " + " ; ".join(items) + "."
    if family == "verifier_contre_indication":
        presc = sorted({r["ordonnance"] for r in rows})
        detail = " ; ".join(sorted({f"{r['medicament']} ({r['molecule']}) : {r['motif']}" for r in rows}))
        who = f"{PAT.label} a" if PAT else ("Il y a" if not P else f"{P.label} présente")
        return f"Oui — {who} {_plural(len(presc), 'prescription')} à risque ({', '.join(presc)}). {detail}."
    if family == "chaine_patient":
        conflits = sorted({f"{r['prescLabel']} → {r['medLabel']} → {r['molLabel']} → {r['ciLabel']}" for r in rows if r.get("conflit")})
        if conflits:
            return f"Chaîne de {PAT.label} : contre-indication détectée — " + " ; ".join(conflits) + "."
        return f"Chaîne de {PAT.label} : {n} lien(s) parcouru(s), aucun conflit avec ses pathologies ni ses antécédents."
    return f"{n} résultat(s)."


def ask(question: str) -> dict:
    timings = {}
    t0 = time.perf_counter()
    a = analyse(question)
    timings["pretraitement"] = time.perf_counter() - t0

    t1 = time.perf_counter()
    lex = lexicon.build()
    entities, period, unknown = extract(a, lex)
    # Identifiants inconnus affichés tels qu'écrits dans la question (casse d'origine).
    unknown = [m.group(0) if (m := re.search(re.escape(u), question, re.I)) else u for u in unknown]
    threshold = extract_threshold(strip_accents(question.lower()))
    types = {e.type for e in entities} | ({"DATE"} if period else set()) | ({"SEUIL"} if threshold else set())
    timings["entites"] = time.perf_counter() - t1

    t2 = time.perf_counter()
    pred = classify(a.normalized, a.lemma_text, types)
    timings["intention"] = time.perf_counter() - t2

    out = {
        "question": question, "intent": pred.intent, "intentLabel": None, "confidence": pred.confidence,
        "entities": [e.as_dict() for e in entities], "periode": period.as_dict() if period else None,
        "seuil": threshold.as_dict() if threshold else None,
        "entitesInconnues": unknown, "sparql": None, "resultType": None, "results": [], "count": 0,
        "answer": None, "message": "", "compris": False, "filters": {}, "explication": [],
        "indices": pred.cues, "alternatives": pred.alternatives, "mode": a.mode,
        "pretraitement": {"normalise": a.normalized, "lemmes": a.lemma_text, "corrections": a.corrections,
                          "tokens": [{"texte": t.text, "lemme": t.lemma, "pos": t.pos} for t in a.tokens]},
    }

    if unknown:
        kinds = {"PRESCRIPTION" if u.lower().startswith(("presc", "prescription", "ordonnance")) else
                 "MEDECIN" if u.lower().startswith("dr") else "PHARMACIEN" if u.lower().startswith("ph_") else "PATIENT" for u in unknown}
        known = " ; ".join(f"{TYPE_NEEDED[k]} connus : {_known(lex, k)}" for k in sorted(kinds))
        out["message"] = (f"Entité inconnue dans l'ontologie : {', '.join(unknown)}. Aucune requête n'a été générée "
                          f"pour ne pas inventer de données. {known}.")
        out["intentLabel"] = BY_NAME[pred.family].label if pred.family else None
        return _finish(out, timings, t0)

    if pred.intent is None:
        out["message"] = ("Je n'ai pas compris la question. Reformulez-la en citant une ordonnance (Presc_001…), un patient, "
                          "un médecin, un médicament, une donnée clinique (allergie, glycémie…) ou une période. Exemples : "
                          + " · ".join(i.example for i in (INTENTS[0], INTENTS[2], INTENTS[14], INTENTS[16])))
        return _finish(out, timings, t0)

    t3 = time.perf_counter()
    gen = generate(pred.intent, pred.family, entities, period, threshold)
    timings["generation"] = time.perf_counter() - t3
    out.update({"intentLabel": BY_NAME[pred.family].label, "sparql": gen.sparql, "resultType": gen.kind,
                "explication": gen.explanation, "filters": gen.filters, "compris": True})

    t4 = time.perf_counter()
    rows, answer = [], None
    if gen.kind == "ask":
        answer = store.ask(gen.sparql)
        rows = [{"reponse": answer}]
    elif gen.kind == "select":
        rows = store.select(gen.sparql)
    timings["execution"] = time.perf_counter() - t4
    out.update({"results": rows, "count": (1 if answer else 0) if gen.kind == "ask" else len(rows), "answer": answer,
                "message": _message(pred.intent, pred.family, entities, rows, answer, gen.filters, lex)})
    return _finish(out, timings, t0)


def _finish(out: dict, timings: dict, t0: float) -> dict:
    labels = {"pretraitement": "Prétraitement spaCy (tokens, lemmes, normalisation)",
              "entites": "Entités (PhraseMatcher + règles + RapidFuzz)", "intention": "Classification d'intention (règles pondérées)",
              "generation": "Génération SPARQL (gabarit + URI validées)", "execution": "Exécution RDFLib"}
    out["etapes"] = [{"nom": labels[k], "ms": round(v * 1000, 1)} for k, v in timings.items()]
    out["dureeMs"] = round((time.perf_counter() - t0) * 1000, 1)
    return out


def model_card() -> dict:
    import importlib.metadata as md

    def v(pkg):
        try:
            return md.version(pkg)
        except md.PackageNotFoundError:
            return "absent"
    _, mode = load_nlp()
    return {
        "nom": MODEL_NAME, "mode": mode,
        "type": "Pipeline TALN hybride local : analyse spaCy + dictionnaires issus de l'ontologie + règles pondérées + gabarits SPARQL",
        "bibliotheques": [
            {"nom": "spaCy", "version": v("spacy"), "role": "tokenisation, lemmatisation (fr_core_news_sm), PhraseMatcher"},
            {"nom": "fr_core_news_sm", "version": v("fr_core_news_sm"), "role": "modèle français (morphologie, lemmes)"},
            {"nom": "RapidFuzz", "version": v("rapidfuzz"), "role": "tolérance aux fautes de frappe (distance de Levenshtein)"},
            {"nom": "RDFLib", "version": v("rdflib"), "role": "exécution des requêtes SPARQL générées"},
            {"nom": "owlrl", "version": v("owlrl"), "role": "inférence OWL 2 RL (types et propriétés inverses utilisés par les requêtes)"},
        ],
        "pipeline": [
            "Prétraitement : minuscules, apostrophes, accents, ponctuation, variantes (« docteur » → « dr »), lemmes spaCy",
            "Entités : spaCy PhraseMatcher sur les libellés de l'ontologie, règles pour Presc_NNN / dates / périodes / seuils, RapidFuzz pour les fautes",
            "Intention : règles pondérées sur lemmes et entités → score → probabilité (softmax) ; seuil de rejet",
            "Génération : gabarit SPARQL de l'intention, URI vérifiées et littéraux échappés par rdflib",
            "Exécution RDFLib sur le graphe (déclaré + inféré) et réponse en français expliquée",
        ],
        "intentions": [{"nom": i.name, "label": i.label, "exemple": i.example} for i in INTENTS],
        "llm": "aucun — pas d'appel réseau, pas d'API externe",
    }


def suggestions() -> list[str]:
    return [
        "Quelles sont les prescriptions renouvelables ?",
        "Quels médicaments sont prescrits à Patient_Ali ?",
        "Qui a prescrit Presc_002 ?",
        "Le patient Youssef a-t-il une prescription contre-indiquée ?",
        "Combien de prescriptions sont enregistrées ?",
        "Quelles ordonnances ont été émises en octobre 2026 ?",
        "Presc_001 est-elle renouvelable ?",
        "Quelles sont les données cliniques de Ali ?",
        "Sara est-elle allergique à l'amoxicilline ?",
        "Quelle est la glycémie d'Ali ?",
        "Quels patients ont une clairance de la créatinine inférieure à 60 ?",
        "Quels patients ont un antécédent d'ulcère ?",
    ]
