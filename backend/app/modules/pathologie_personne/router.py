"""Routes REST du module Pathologie + Personne (Ahmed Allaya).

Montées sous /api par app/main.py. Noms choisis pour ne jamais entrer en collision avec le module A :
/health, /admin/reset, /stats et /sparql restent ceux de l'application commune.
Erreurs de ce module : {code, message, details} avec 404 / 409 / 422.
"""
from fastapi import APIRouter, FastAPI, Query, Request, Response
from fastapi.responses import JSONResponse

from ...graph_store import store
from .client import SparqlError, StoreClient
from .mapping import C
from .schemas import (AskRequest, Created, Page, PathologieCreate, PathologieItem, PathologieUpdate,
                      PatientCreate, PatientDetail, PatientItem, PatientUpdate, ProCreate, ProItem, ProUpdate)
from .service import Conflict, NotFound, Repository
from .templates import InvalidParam

TAG = "Module Pathologie + Personne (Ahmed)"
router = APIRouter(tags=[TAG])
repo = Repository(StoreClient(store))

Limit = Query(20, ge=1, le=100)
Offset = Query(0, ge=0)
_nlp = None


def nlp():
    """Pipeline NLP chargé au premier appel (spaCy)."""
    global _nlp
    if _nlp is None:
        from .nlp.pipeline import NlpPipeline
        _nlp = NlpPipeline(repo.sparql)
    return _nlp


def page(items, total, limit, offset):
    return {"items": items, "total": total, "limit": limit, "offset": offset}


def register_error_handlers(app: FastAPI):
    def handler(status, code):
        async def h(_: Request, e: Exception):
            return JSONResponse(status_code=status, content={"code": code, "message": str(e),
                                                             "details": getattr(e, "details", None)})
        return h

    app.add_exception_handler(NotFound, handler(404, "not_found"))
    app.add_exception_handler(Conflict, handler(409, "conflict"))
    app.add_exception_handler(InvalidParam, handler(422, "invalid_parameter"))
    app.add_exception_handler(SparqlError, handler(400, "sparql_error"))


# ---------- Pathologies ----------
@router.get("/pathologies", response_model=Page[PathologieItem])
def list_pathologies(q: str | None = None, famille: str | None = None, type: str | None = None,
                     limit: int = Limit, offset: int = Offset):
    items, total = repo.list_pathologies(limit=limit, offset=offset, q=q, famille=famille, type=type)
    return page(items, total, limit, offset)


@router.post("/pathologies", status_code=201, response_model=Created)
def create_pathologie(body: PathologieCreate):
    return {"id": repo.create_pathologie(body.label, body.type, body.code)}


@router.get("/pathologies/{pid}")
def get_pathologie(pid: str):
    return repo.get_pathologie(pid)


@router.patch("/pathologies/{pid}")
def update_pathologie(pid: str, body: PathologieUpdate):
    repo.update_pathologie(pid, **body.model_dump(exclude_none=True))
    return repo.get_pathologie(pid)


@router.delete("/pathologies/{pid}", status_code=204)
def delete_pathologie(pid: str):
    repo.delete_pathologie(pid)
    return Response(status_code=204)


# ---------- Patients ----------
@router.get("/patients", response_model=Page[PatientItem])
def list_patients(q: str | None = None, sexe: str | None = Query(None, pattern="^[MF]$"),
                  age_min: int | None = Query(None, ge=0, le=120), age_max: int | None = Query(None, ge=0, le=120),
                  pathologie: str | None = None,
                  classe: str | None = Query(None, pattern="^(PatientEnfant|PatientAdulte)$"),
                  limit: int = Limit, offset: int = Offset):
    items, total = repo.list_patients(limit=limit, offset=offset, q=q, sexe=sexe, age_min=age_min,
                                      age_max=age_max, pathologie=pathologie, classe=classe)
    return page(items, total, limit, offset)


@router.post("/patients", status_code=201, response_model=Created)
def create_patient(body: PatientCreate):
    return {"id": repo.create_patient(body.prenom, body.nom, body.age, body.sexe, body.pathologies)}


@router.get("/patients/{pid}", response_model=PatientDetail)
def get_patient(pid: str):
    return repo.get_patient(pid)


@router.get("/patients/{pid}/rdf", response_class=Response)
def patient_rdf(pid: str):
    return Response(repo.describe_patient(pid), media_type="text/turtle")


@router.patch("/patients/{pid}", response_model=PatientDetail)
def update_patient(pid: str, body: PatientUpdate):
    repo.update_patient(pid, **body.model_dump(exclude_none=True))
    return repo.get_patient(pid)


@router.delete("/patients/{pid}", status_code=204)
def delete_patient(pid: str):
    repo.delete_patient(pid)
    return Response(status_code=204)


@router.post("/patients/{pid}/pathologies/{patho}", response_model=PatientDetail)
def add_pathology(pid: str, patho: str):
    repo.add_patient_pathology(pid, patho)
    return repo.get_patient(pid)


@router.delete("/patients/{pid}/pathologies/{patho}", response_model=PatientDetail)
def remove_pathology(pid: str, patho: str):
    repo.remove_patient_pathology(pid, patho)
    return repo.get_patient(pid)


# ---------- Médecins / pharmaciens (même CRUD, classe différente) ----------
def pro_routes(path: str, classe: str):
    @router.get(f"/{path}", response_model=Page[ProItem])
    def list_(q: str | None = None, specialite: str | None = None, limit: int = Limit, offset: int = Offset):
        items, total = repo.list_professionnels(classe, limit=limit, offset=offset, q=q, specialite=specialite)
        return page(items, total, limit, offset)

    @router.post(f"/{path}", status_code=201, response_model=Created)
    def create(body: ProCreate):
        return {"id": repo.create_professionnel(classe, body.nom, body.specialite, body.label)}

    @router.get(f"/{path}/{{pid}}")
    def get(pid: str):
        return repo.get_professionnel(classe, pid)

    @router.patch(f"/{path}/{{pid}}")
    def update(pid: str, body: ProUpdate):
        repo.update_professionnel(classe, pid, **body.model_dump(exclude_none=True))
        return repo.get_professionnel(classe, pid)

    @router.delete(f"/{path}/{{pid}}", status_code=204)
    def delete(pid: str):
        repo.delete_professionnel(classe, pid)
        return Response(status_code=204)


pro_routes("medecins", C["Medecin"])
pro_routes("pharmaciens", C["Pharmacien"])


# ---------- Transversal ----------
@router.get("/alertes")
def alertes(patient: str | None = None):
    return repo.alertes(patient=patient)


@router.get("/sante/stats")
def stats():
    return repo.stats()


@router.get("/sante/recherche")
def search(q: str = Query(min_length=1, max_length=100)):
    return repo.search(q)


@router.get("/sante/graphe/{eid}")
def graph(eid: str):
    return repo.graph(eid)


# ---------- NLP : question en français → SPARQL ----------
@router.post("/sante/nlp/ask")
def nlp_ask(body: AskRequest):
    return nlp().ask(body.question)


@router.get("/sante/nlp/exemples")
def nlp_examples():
    return nlp().examples
