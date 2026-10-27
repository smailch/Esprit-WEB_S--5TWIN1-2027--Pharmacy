"""API PharmaSémantique — modules Pathologie et Personne (membre 3).

Lancement : uvicorn app.main:app --reload   (documentation OpenAPI : /docs)
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from app.api.routes import router
from app.config.settings import get_settings
from app.services.repository import Conflict, NotFound, Repository
from app.sparql.client import SparqlError, build_client
from app.sparql.templates import InvalidParam


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    app.state.settings = settings
    if not hasattr(app.state, "repo"):  # les tests injectent leur propre dépôt
        app.state.repo = Repository(build_client(settings))
    yield


app = FastAPI(title="PharmaSémantique — Pathologie & Personne", version="1.0.0", lifespan=lifespan,
              description="CRUD, filtres, recherche, alertes et NLP → SPARQL. Données fictives — aucun conseil médical.")

app.add_middleware(CORSMiddleware, allow_origins=get_settings().cors_origins.split(","),
                   allow_methods=["*"], allow_headers=["*"])


def error(status: int, code: str, message: str, details=None):
    return JSONResponse(status_code=status, content={"code": code, "message": message, "details": details})


@app.exception_handler(NotFound)
async def not_found(_: Request, e: NotFound):
    return error(404, "not_found", str(e))


@app.exception_handler(Conflict)
async def conflict(_: Request, e: Conflict):
    return error(409, "conflict", str(e), e.details)


@app.exception_handler(InvalidParam)
async def invalid(_: Request, e: InvalidParam):
    return error(422, "invalid_parameter", str(e))


@app.exception_handler(SparqlError)
async def sparql_error(_: Request, e: SparqlError):
    return error(400, "sparql_error", str(e))


@app.exception_handler(RequestValidationError)
async def validation(_: Request, e: RequestValidationError):
    details = [{"champ": ".".join(str(x) for x in err["loc"][1:]), "message": err["msg"]} for err in e.errors()]
    return error(422, "validation_error", "Données invalides", details)


@app.exception_handler(HTTPException)
async def http_error(_: Request, e: HTTPException):
    return error(e.status_code, "http_error", str(e.detail))


app.include_router(router)
