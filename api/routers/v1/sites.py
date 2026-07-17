"""Sites resource: monitoring locations (the anchor for GIS features)."""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.db import get_db
from api.schemas import SiteOut
from api.security import Principal, require_scope
from api.services import sites as site_svc

router = APIRouter(prefix="/sites", tags=["sites"])


@router.get("", response_model=list[SiteOut], summary="List monitoring sites")
def list_sites(
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_scope("sites:read")),
) -> list[SiteOut]:
    return site_svc.list_sites(db, principal)


@router.get("/{site_id}", response_model=SiteOut, summary="Get a monitoring site")
def get_site(
    site_id: UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_scope("sites:read")),
) -> SiteOut:
    return site_svc.get_site(db, principal, site_id)
