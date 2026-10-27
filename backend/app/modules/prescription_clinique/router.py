"""Routes REST du module D (Prescription + Donnée clinique).

- ressources : /api/prescriptions, /api/donnees-cliniques ;
- tout le reste (dossier patient, référentiels, catalogue SPARQL, requête contrôlée, TALN) sous /api/module-d/
  pour éviter tout doublon avec les routes des autres modules lors de l'intégration.
Réponses REST : {"data": ..., "sparql": [{titre, requete}, ...]} ; le TALN renvoie {question, intent, entities, sparql, results, count, message, ...}.
"""
from datetime import date

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from nlp.prescrinlu import evaluation, pipeline
from nlp.prescrinlu.preprocessing import NlpUnavailable

from . import service as S
from . import sparql_guard
from .common import Conflict, NotFound, Trace
from .queries import CATALOGUE, catalogue_entry
from .schemas import DonneeCliniqueIn, PrescriptionIn, SparqlQueryIn

router = APIRouter(tags=["Module D — Prescription + Donnée clinique"])


def run(fn, *args, **kwargs):
    t = Trace()
    try:
        data = fn(t, *args, **kwargs)
    except NotFound as e:
        raise HTTPException(404, str(e))
    except Conflict as e:
        raise HTTPException(409, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"data": data, "sparql": t.items}


# ---------- Prescriptions (routes fixes avant /{pid}) ----------
@router.get("/prescriptions")
def prescriptions(
    type: str | None = None, patient: str | None = None, medecin: str | None = None,
    pharmacien: str | None = None, medicament: str | None = None,
    dateMin: date | None = Query(None, description="AAAA-MM-JJ (inclus)"),
    dateMax: date | None = Query(None, description="AAAA-MM-JJ (inclus)"),
    q: str | None = Query(None, max_length=80), tri: str = "date",
    page: int = Query(1, ge=1), taille: int = Query(20, ge=1, le=100),
):
    return run(S.list_prescriptions, type=type, patient=patient, medecin=medecin, pharmacien=pharmacien,
               medicament=medicament, dateMin=dateMin, dateMax=dateMax, q=q, tri=tri, page=page, taille=taille)


@router.get("/prescriptions/statistiques")
def prescriptions_stats():
    return run(S.stats)


@router.get("/prescriptions/alertes")
def prescriptions_alertes(patient: str | None = None):
    return run(S.alertes, patient=patient)


@router.get("/prescriptions/{pid}")
def prescription(pid: str):
    return run(S.get_prescription, pid)


@router.get("/prescriptions/{pid}/graphe")
def prescription_graphe(pid: str):
    return run(S.graphe_prescription, pid)


@router.post("/prescriptions", status_code=201)
def prescription_create(body: PrescriptionIn):
    return run(S.create_prescription, body)


@router.put("/prescriptions/{pid}")
def prescription_update(pid: str, body: PrescriptionIn):
    return run(S.update_prescription, pid, body)


@router.delete("/prescriptions/{pid}")
def prescription_delete(pid: str):
    return run(S.delete_prescription, pid)


# ---------- Données cliniques ----------
@router.get("/donnees-cliniques")
def donnees(
    type: str | None = None, patient: str | None = None,
    dateMin: date | None = Query(None), dateMax: date | None = Query(None),
    q: str | None = Query(None, max_length=80), tri: str = "date_desc",
    page: int = Query(1, ge=1), taille: int = Query(20, ge=1, le=100),
):
    return run(S.list_donnees, type=type, patient=patient, dateMin=dateMin, dateMax=dateMax, q=q, tri=tri, page=page, taille=taille)


@router.get("/donnees-cliniques/{did}")
def donnee(did: str):
    return run(S.get_donnee, did)


@router.post("/donnees-cliniques", status_code=201)
def donnee_create(body: DonneeCliniqueIn):
    return run(S.create_donnee, body)


@router.put("/donnees-cliniques/{did}")
def donnee_update(did: str, body: DonneeCliniqueIn):
    return run(S.update_donnee, did, body)


@router.delete("/donnees-cliniques/{did}")
def donnee_delete(did: str):
    return run(S.delete_donnee, did)


# ---------- Dossier patient, référentiels, ontologie ----------
@router.get("/module-d/patients/{pid}/dossier")
def dossier(pid: str):
    """Scénario : Patient → Prescription → Médicament → Molécule → Contre-indication → Pathologie + données cliniques."""
    return run(S.dossier_patient, pid)


@router.get("/module-d/referentiels")
def referentiels():
    return run(S.referentiels)


@router.get("/module-d/ontologie")
def ontologie():
    return run(S.ontology_stats)


# ---------- Catalogue SPARQL et requête contrôlée ----------
@router.get("/module-d/requetes")
def requetes():
    return {"data": [{
        "nom": nom, "titre": e["titre"], "notion": e["notion"], "requete": catalogue_entry(nom),
        "lectureSeule": e.get("lecture_seule", True),
    } for nom, e in CATALOGUE.items()], "sparql": []}


@router.post("/module-d/requetes/{nom}/executer")
def requete_executer(nom: str):
    if nom not in CATALOGUE:
        raise HTTPException(404, "Requête inconnue")
    if not CATALOGUE[nom].get("lecture_seule", True):
        raise HTTPException(400, "Requête de mise à jour : utilisez les formulaires CRUD (exemple affiché à titre pédagogique).")
    sparql = catalogue_entry(nom)
    return {"data": sparql_guard.execute(sparql), "sparql": [{"titre": CATALOGUE[nom]["titre"], "requete": sparql}]}


@router.post("/module-d/sparql")
def sparql_query(body: SparqlQueryIn):
    """SELECT / ASK / CONSTRUCT uniquement : la requête est analysée et son algèbre inspectée avant exécution."""
    try:
        data = sparql_guard.execute(body.requete, body.limite)
    except sparql_guard.UnsafeQuery as e:
        raise HTTPException(400, str(e))
    except Exception as e:  # erreur d'évaluation → message lisible
        raise HTTPException(400, f"Requête invalide : {e}")
    return {"data": data, "sparql": [{"titre": "Requête contrôlée", "requete": body.requete}]}


# ---------- API IA : PrescriNLU-D ----------
class Question(BaseModel):
    question: str = Field(min_length=3, max_length=300)


@router.post("/module-d/nlp/ask")
def nlp_ask(body: Question):
    """Question en français → intention + entités → requête SPARQL → résultats + explication."""
    try:
        return pipeline.ask(body.question.strip())
    except NlpUnavailable as e:
        raise HTTPException(503, str(e))


@router.get("/module-d/nlp/suggestions")
def nlp_suggestions():
    return {"data": pipeline.suggestions(), "sparql": []}


@router.get("/module-d/nlp/modele")
def nlp_modele():
    try:
        return {"data": {**pipeline.model_card(), "evaluation": evaluation.evaluate()}, "sparql": []}
    except NlpUnavailable as e:
        raise HTTPException(503, str(e))
