from fastapi import APIRouter, Depends, Query, Request, Response

from app.config.ontology_mapping import C
from app.schemas.models import (AskRequest, Created, Page, PathologieCreate, PathologieItem, PathologieUpdate,
                                PatientCreate, PatientDetail, PatientItem, PatientUpdate, ProCreate,
                                ProItem, ProUpdate, SparqlRequest)
from app.services.repository import Repository
from app.sparql.client import SparqlError, query_kind
from app.sparql.templates import QUERIES

router = APIRouter(prefix="/api")

Limit = Query(20, ge=1, le=100)
Offset = Query(0, ge=0)


def repo(request: Request) -> Repository:
    return request.app.state.repo


def page(items, total, limit, offset):
    return {"items": items, "total": total, "limit": limit, "offset": offset}


# ---------- Santé / administration ----------
@router.get("/health", tags=["système"])
def health(request: Request, r: Repository = Depends(repo)):
    n = r.sparql.select("SELECT (COUNT(*) AS ?n) WHERE { ?s ?p ?o }").rows[0]["n"]
    return {"status": "ok", "backend": request.app.state.settings.sparql_backend, "triples": n}


@router.post("/admin/reset", tags=["système"])
def reset(r: Repository = Depends(repo)):
    r.sparql.reset()
    return {"status": "reset", "alertes": len(r.alertes())}


# ---------- Pathologies ----------
@router.get("/pathologies", response_model=Page[PathologieItem], tags=["pathologies"])
def list_pathologies(q: str | None = None, famille: str | None = None, type: str | None = None,
                     limit: int = Limit, offset: int = Offset, r: Repository = Depends(repo)):
    items, total = r.list_pathologies(limit=limit, offset=offset, q=q, famille=famille, type=type)
    return page(items, total, limit, offset)


@router.post("/pathologies", status_code=201, response_model=Created, tags=["pathologies"])
def create_pathologie(body: PathologieCreate, r: Repository = Depends(repo)):
    return {"id": r.create_pathologie(body.label, body.type, body.code)}


@router.get("/pathologies/{pid}", tags=["pathologies"])
def get_pathologie(pid: str, r: Repository = Depends(repo)):
    return r.get_pathologie(pid)


@router.patch("/pathologies/{pid}", tags=["pathologies"])
def update_pathologie(pid: str, body: PathologieUpdate, r: Repository = Depends(repo)):
    r.update_pathologie(pid, **body.model_dump(exclude_none=True))
    return r.get_pathologie(pid)


@router.delete("/pathologies/{pid}", status_code=204, tags=["pathologies"])
def delete_pathologie(pid: str, r: Repository = Depends(repo)):
    r.delete_pathologie(pid)
    return Response(status_code=204)


# ---------- Patients ----------
@router.get("/patients", response_model=Page[PatientItem], tags=["patients"])
def list_patients(q: str | None = None, sexe: str | None = Query(None, pattern="^[MF]$"),
                  age_min: int | None = Query(None, ge=0, le=120), age_max: int | None = Query(None, ge=0, le=120),
                  pathologie: str | None = None,
                  classe: str | None = Query(None, pattern="^(PatientEnfant|PatientAdulte)$"),
                  limit: int = Limit, offset: int = Offset, r: Repository = Depends(repo)):
    items, total = r.list_patients(limit=limit, offset=offset, q=q, sexe=sexe, age_min=age_min,
                                   age_max=age_max, pathologie=pathologie, classe=classe)
    return page(items, total, limit, offset)


@router.post("/patients", status_code=201, response_model=Created, tags=["patients"])
def create_patient(body: PatientCreate, r: Repository = Depends(repo)):
    return {"id": r.create_patient(body.prenom, body.nom, body.age, body.sexe, body.pathologies)}


@router.get("/patients/{pid}", response_model=PatientDetail, tags=["patients"])
def get_patient(pid: str, r: Repository = Depends(repo)):
    return r.get_patient(pid)


@router.get("/patients/{pid}/rdf", tags=["patients"], response_class=Response)
def patient_rdf(pid: str, r: Repository = Depends(repo)):
    return Response(r.describe_patient(pid), media_type="text/turtle")


@router.patch("/patients/{pid}", response_model=PatientDetail, tags=["patients"])
def update_patient(pid: str, body: PatientUpdate, r: Repository = Depends(repo)):
    r.update_patient(pid, **body.model_dump(exclude_none=True))
    return r.get_patient(pid)


@router.delete("/patients/{pid}", status_code=204, tags=["patients"])
def delete_patient(pid: str, r: Repository = Depends(repo)):
    r.delete_patient(pid)
    return Response(status_code=204)


@router.post("/patients/{pid}/pathologies/{patho}", response_model=PatientDetail, tags=["patients"])
def add_pathology(pid: str, patho: str, r: Repository = Depends(repo)):
    r.add_patient_pathology(pid, patho)
    return r.get_patient(pid)


@router.delete("/patients/{pid}/pathologies/{patho}", response_model=PatientDetail, tags=["patients"])
def remove_pathology(pid: str, patho: str, r: Repository = Depends(repo)):
    r.remove_patient_pathology(pid, patho)
    return r.get_patient(pid)


# ---------- Médecins / pharmaciens (même CRUD, classe différente) ----------
def pro_routes(path: str, classe: str):
    tag = [path]

    @router.get(f"/{path}", response_model=Page[ProItem], tags=tag)
    def list_(q: str | None = None, specialite: str | None = None, limit: int = Limit, offset: int = Offset,
              r: Repository = Depends(repo)):
        items, total = r.list_professionnels(classe, limit=limit, offset=offset, q=q, specialite=specialite)
        return page(items, total, limit, offset)

    @router.post(f"/{path}", status_code=201, response_model=Created, tags=tag)
    def create(body: ProCreate, r: Repository = Depends(repo)):
        return {"id": r.create_professionnel(classe, body.nom, body.specialite, body.label)}

    @router.get(f"/{path}/{{pid}}", tags=tag)
    def get(pid: str, r: Repository = Depends(repo)):
        return r.get_professionnel(classe, pid)

    @router.patch(f"/{path}/{{pid}}", tags=tag)
    def update(pid: str, body: ProUpdate, r: Repository = Depends(repo)):
        r.update_professionnel(classe, pid, **body.model_dump(exclude_none=True))
        return r.get_professionnel(classe, pid)

    @router.delete(f"/{path}/{{pid}}", status_code=204, tags=tag)
    def delete(pid: str, r: Repository = Depends(repo)):
        r.delete_professionnel(classe, pid)
        return Response(status_code=204)


pro_routes("medecins", C["Medecin"])
pro_routes("pharmaciens", C["Pharmacien"])


# ---------- Transversal ----------
@router.get("/alertes", tags=["alertes"])
def alertes(patient: str | None = None, r: Repository = Depends(repo)):
    return r.alertes(patient=patient)


@router.get("/stats", tags=["stats"])
def stats(r: Repository = Depends(repo)):
    return r.stats()


@router.get("/search", tags=["recherche"])
def search(q: str = Query(min_length=1, max_length=100), r: Repository = Depends(repo)):
    return r.search(q)


@router.get("/graph/{eid}", tags=["graphe"])
def graph(eid: str, r: Repository = Depends(repo)):
    return r.graph(eid)


# ---------- NLP : question en français → SPARQL ----------
def nlp_pipeline(request: Request, r: Repository = Depends(repo)):
    from app.nlp.pipeline import NlpPipeline  # import tardif : spaCy n'est chargé qu'au premier appel

    state = request.app.state
    if getattr(state, "nlp", None) is None or state.nlp.client is not r.sparql:
        state.nlp = NlpPipeline(r.sparql)
    return state.nlp


@router.post("/nlp/ask", tags=["nlp"])
def nlp_ask(body: AskRequest, nlp=Depends(nlp_pipeline)):
    return nlp.ask(body.question)


@router.get("/nlp/exemples", tags=["nlp"])
def nlp_examples(nlp=Depends(nlp_pipeline)):
    return nlp.examples


# ---------- Console SPARQL (lecture seule) ----------
@router.get("/sparql/queries", tags=["sparql"])
def named_queries():
    return [{"name": q.name, "objectif": q.objectif, "categorie": q.categorie, "params": q.params,
             "exemple": q.exemple} for q in QUERIES.values()]


@router.post("/sparql", tags=["sparql"])
def sparql_console(body: SparqlRequest, r: Repository = Depends(repo)):
    kind = query_kind(body.query)
    if kind == "UPDATE":
        raise SparqlError("Console en lecture seule : seules SELECT, ASK, DESCRIBE et CONSTRUCT sont autorisées")
    kind, res = r.sparql.run(body.query)
    if kind == "SELECT":
        return {"kind": kind, "vars": res.vars, "rows": res.rows}
    if kind == "ASK":
        return {"kind": kind, "boolean": res}
    return {"kind": kind, "turtle": res}
