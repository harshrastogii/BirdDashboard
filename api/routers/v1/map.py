"""Map resource: sites as filterable map points (Phase 7 · C GIS foundation)."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.db import get_db
from api.schemas import MapSitesOut
from api.security import Principal, require_scope
from api.services import geospatial

router = APIRouter(prefix="/map", tags=["map"])


@router.get("/sites", response_model=MapSitesOut, summary="Sites as filterable map points")
def map_sites(
    min_confidence: float = Query(0.25, ge=0.0, le=1.0),
    species: str | None = Query(None, description="Filter/flag sites where this species was detected"),
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_scope("sites:read")),
) -> MapSitesOut:
    return geospatial.map_sites(db, principal, min_confidence=min_confidence, species=species)
