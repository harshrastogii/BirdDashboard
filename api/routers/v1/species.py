"""Species reference catalog."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.db import get_db
from api.schemas import Page, SpeciesOut
from api.security import Principal, require_scope
from api.services import species as species_svc

router = APIRouter(prefix="/species", tags=["species"])


@router.get("", response_model=Page[SpeciesOut], summary="List species")
def list_species(
    cursor: str | None = Query(default=None),
    limit: int | None = Query(default=None, ge=1, le=200),
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_scope("species:read")),
) -> Page[SpeciesOut]:
    return species_svc.list_species(db, principal, cursor=cursor, limit=limit)


@router.get("/{species_id}", response_model=SpeciesOut, summary="Get a species")
def get_species(
    species_id: UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_scope("species:read")),
) -> SpeciesOut:
    return species_svc.get_species(db, principal, species_id)
