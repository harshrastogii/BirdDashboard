"""Environmental-layer resource — the decoupled boundary (Phase 7 · C4).

Inert today (returns `available=false`); exists so Stage-2 sources (open data,
then TerraIQ) plug in behind the provider with no frontend change (D-21)."""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.db import get_db
from api.schemas import EnvironmentalContextOut, EnvironmentalLayersOut
from api.security import Principal, require_scope
from api.services import environmental

router = APIRouter(prefix="/environmental", tags=["environmental"])


@router.get("/layers", response_model=EnvironmentalLayersOut,
            summary="Available environmental map layers (inert scaffold)")
def layers(
    principal: Principal = Depends(require_scope("sites:read")),
) -> EnvironmentalLayersOut:
    return environmental.layers()


@router.get("/context", response_model=EnvironmentalContextOut,
            summary="Environmental context for a site (inert scaffold)")
def context(
    site_id: UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_scope("sites:read")),
) -> EnvironmentalContextOut:
    return environmental.context_for_site(site_id)
