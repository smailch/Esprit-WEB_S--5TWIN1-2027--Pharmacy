"""Effets secondaires : lecture, filtres et CRUD contrôlé."""

from __future__ import annotations

from fastapi import APIRouter, Query, Request

from app.api.deps import raise_domain, require_write, store_of
from app.ontology import crud
from app.ontology.queries import get_effect, list_effects
from app.schemas import EffectWrite

router = APIRouter(prefix="/effects", tags=["effets"])


@router.get("")
def read_effects(
    request: Request,
    q: str | None = Query(default=None, max_length=80),
    gravite: str | None = None,
    categorie: str | None = None,
    medicament: str | None = None,
    molecule: str | None = None,
    page: int = 1,
    page_size: int = 20,
    sort: str = "label",
) -> dict:
    try:
        return list_effects(
            store_of(request),
            q=q,
            gravite=gravite,
            categorie=categorie,
            medicament=medicament,
            molecule=molecule,
            page=page,
            page_size=page_size,
            sort=sort,
        )
    except Exception as exc:
        raise_domain(exc)


@router.get("/{effect_id}")
def read_effect(effect_id: str, request: Request) -> dict:
    try:
        return get_effect(store_of(request), effect_id)
    except Exception as exc:
        raise_domain(exc)


@router.post("", status_code=201)
def post_effect(body: EffectWrite, request: Request) -> dict:
    require_write(request)
    if not body.label or not body.type:
        from fastapi import HTTPException

        raise HTTPException(422, "Les champs label et type sont obligatoires.")
    try:
        return crud.create_effect(store_of(request), body.model_dump())
    except Exception as exc:
        raise_domain(exc)


@router.put("/{effect_id}")
def put_effect(effect_id: str, body: EffectWrite, request: Request) -> dict:
    require_write(request)
    try:
        return crud.update_effect(store_of(request), effect_id, body.model_dump(exclude_unset=True))
    except Exception as exc:
        raise_domain(exc)


@router.delete("/{effect_id}")
def remove_effect(effect_id: str, request: Request) -> dict:
    require_write(request)
    try:
        return crud.delete_effect(store_of(request), effect_id)
    except Exception as exc:
        raise_domain(exc)
