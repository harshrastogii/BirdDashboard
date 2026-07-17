"""Biodiversity metrics across the recording library."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.db import get_db
from api.schemas import BiodiversityOut
from api.security import Principal, require_scope
from api.services import biodiversity as bio_svc

router = APIRouter(prefix="/biodiversity", tags=["biodiversity"])


@router.get("", response_model=BiodiversityOut, summary="Biodiversity indices")
def get_biodiversity(
    min_confidence: float = Query(default=0.25, ge=0.0, le=1.0),
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_scope("detections:read")),
) -> BiodiversityOut:
    return bio_svc.biodiversity(db, principal, min_confidence=min_confidence)
