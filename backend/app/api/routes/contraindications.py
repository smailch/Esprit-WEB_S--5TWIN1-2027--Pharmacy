"""Contre-indications : lecture, filtres et CRUD contrôlé."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request

from app.api.deps import raise_domain, require_write, store_of
from app.ontology import crud
from app.ontology.queries import get_contraindication, list_contraindications
from app.schemas import ContraindicationWrite

router = APIRouter(prefix="/contraindications", tags=["contre-indications"])


@router.get("")
def read_contraindications(
    request: Request,
    q: str | None = Query(default=None, max_length=80),
    categorie: str | None = None,
    niveau: str | None = None,
    medicament: str | None = None,
    molecule: str | None = None,
    pathologie: str | None = None,
    page: int = 1,
    page_size: int = 20,
    sort: str = "label",
) -> dict:
    try:
        return list_contraindications(
            store_of(request),
            q=q,
            categorie=categorie,
            niveau=niveau,
            medicament=medicament,
            molecule=molecule,
            pathologie=pathologie,
            page=page,
            page_size=page_size,
            sort=sort,
        )
    except Exception as exc:
        raise_domain(exc)


@router.get("/{ci_id}")
def read_contraindication(ci_id: str, request: Request) -> dict:
    try:
        return get_contraindication(store_of(request), ci_id)
    except Exception as exc:
        raise_domain(exc)


@router.post("", status_code=201)
def post_contraindication(body: ContraindicationWrite, request: Request) -> dict:
    require_write(request)
    if not body.label or not body.type:
        raise HTTPException(422, "Les champs label et type sont obligatoires.")
    try:
        return crud.create_contraindication(store_of(request), body.model_dump())
    except Exception as exc:
        raise_domain(exc)


@router.put("/{ci_id}")
def put_contraindication(ci_id: str, body: ContraindicationWrite, request: Request) -> dict:
    require_write(request)
    try:
        return crud.update_contraindication(store_of(request), ci_id, body.model_dump(exclude_unset=True))
    except Exception as exc:
        raise_domain(exc)


@router.delete("/{ci_id}")
def remove_contraindication(ci_id: str, request: Request) -> dict:
    require_write(request)
    try:
        return crud.delete_contraindication(store_of(request), ci_id)
    except Exception as exc:
        raise_domain(exc)
