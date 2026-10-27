"""Traducteur intelligent : question en français → SPARQL → résultats, avec explication de chaque étape.

Outils : spaCy (fr_core_news_md : tokens, lemmes, POS, dépendances, PhraseMatcher, Matcher),
RapidFuzz (tolérance aux fautes, suggestions), scikit-learn (TF-IDF + régression logistique).
Aucun appel à une API de LLM.
"""
from __future__ import annotations

import json
import logging
import threading
from pathlib import Path

import spacy
from rapidfuzz import fuzz, process

from app.nlp import constraints as cons
from app.nlp.generator import MissingSlot, generate
from app.nlp.intent import IntentClassifier
from app.nlp.linker import Linker
from app.nlp.normalize import normalize
from app.nlp.vocabulary import Vocabulary
from app.sparql.client import SparqlClient, SparqlError

log = logging.getLogger(__name__)
SPACY_MODEL = "fr_core_news_md"
EXAMPLES = Path(__file__).resolve().parents[2] / "nlp" / "data" / "exemples.json"
MIN_CONFIDENCE = 0.30


def load_spacy():
    try:
        return spacy.load(SPACY_MODEL, exclude=["ner"])
    except OSError:  # modèle absent : on reste fonctionnel (sans lemmes ni dépendances)
        log.warning("Modèle %s absent : lancez scripts/setup_models.py", SPACY_MODEL)
        return spacy.blank("fr")


class NlpPipeline:
    def __init__(self, client: SparqlClient):
        self.client = client
        self.nlp = load_spacy()
        self.classifier = IntentClassifier(self.nlp)
        self.examples = json.loads(EXAMPLES.read_text(encoding="utf-8"))
        self._linker, self._version = None, None
        self._lock = threading.Lock()

    @property
    def linker(self) -> Linker:
        with self._lock:
            if self._version != self.client.version:  # données modifiées → vocabulaire reconstruit
                self._linker = Linker(self.nlp, Vocabulary(self.client))
                self._version = self.client.version
            return self._linker

    def suggestions(self, question: str, n=3) -> list[str]:
        choices = {normalize(q): q for q in self.examples}
        hits = process.extract(normalize(question), list(choices), scorer=fuzz.token_set_ratio, limit=n)
        return [choices[h[0]] for h in hits]

    @staticmethod
    def mask(norm: str, entities) -> str:
        chars = list(norm)
        for e in sorted(entities, key=lambda e: -e.start):
            chars[e.start:e.end] = list(f" ent_{e.type.lower()} ")
        text = "".join(chars)
        return " ".join("ent_num" if w.isdigit() else w for w in text.split())

    def ask(self, question: str) -> dict:
        question = question.strip()
        norm = normalize(question)
        doc = self.nlp(question)
        tokens = [{"text": t.text, "lemma": t.lemma_, "pos": t.pos_, "dep": t.dep_}
                  for t in doc if not t.is_space]
        entities = self.linker.link(question, norm)
        c = cons.extract(norm)
        masked = self.mask(norm, entities)
        types = {e.type for e in entities}

        rule_intent, rule_reason = self.classifier.rules(self.nlp.make_doc(norm), types)
        ranking = self.classifier.classify(masked)
        if rule_intent:
            intent, confidence, method = rule_intent, 0.95, rule_reason
        else:
            intent, confidence = ranking[0]
            method = "classifieur TF-IDF + régression logistique"

        out = {"question": question, "normalisee": norm, "masquee": masked, "tokens": tokens,
               "entites": [e.dict() for e in entities], "contraintes": c, "intention": intent,
               "confiance": confidence, "methode": method,
               "classement": [{"intention": i, "proba": p} for i, p in ranking],
               "sparql": None, "resultat": None, "compris": False, "message": "", "suggestions": []}

        ambiguous = [e for e in entities if e.candidates]
        if intent == "hors_perimetre" or confidence < MIN_CONFIDENCE:
            out["message"] = ("Je ne peux répondre qu'aux questions sur les pathologies, les patients, "
                              "les médecins, les pharmaciens et leurs ordonnances.")
            out["suggestions"] = self.suggestions(question)
            return out
        if ambiguous:
            e = ambiguous[0]
            out["message"] = f"« {e.text} » est ambigu : " + ", ".join(x["label"] for x in e.candidates)
            out["suggestions"] = self.suggestions(question)
            return out
        try:
            sparql = generate(intent, entities, c)
        except MissingSlot as e:
            out["message"] = f"Question comprise comme « {intent} », mais il manque {e}."
            out["suggestions"] = self.suggestions(question)
            return out

        out["sparql"] = sparql
        try:
            kind, res = self.client.run(sparql)
        except SparqlError as e:
            out["message"] = f"Erreur d'exécution SPARQL : {e}"
            return out
        out["compris"] = True
        if kind == "ASK":
            out["resultat"] = {"kind": kind, "boolean": res}
            out["message"] = "Oui." if res else "Non."
        else:
            out["resultat"] = {"kind": kind, "vars": res.vars, "rows": res.rows}
            if intent == "compter" and res.rows:
                out["message"] = f"Réponse : {res.rows[0].get('nombre', 0)}."
            else:
                n = len(res.rows)
                out["message"] = f"{n} résultat{'s' if n > 1 else ''}." if n else "Aucun résultat dans les données."
        return out
