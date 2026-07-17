"""Operational + metadata endpoints: health, readiness, version."""

from fastapi import APIRouter, Depends
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from api import __version__
from api.db import get_db
from api.models import Model
from api.schemas import ModelOut, VersionOut
from api.settings import get_settings

router = APIRouter(tags=["meta"])
_settings = get_settings()


@router.get("/healthz", summary="Liveness probe")
def healthz() -> dict:
    return {"status": "ok"}


@router.get("/readyz", summary="Readiness probe (checks the database)")
def readyz(db: Session = Depends(get_db)) -> dict:
    db.execute(text("SELECT 1"))
    return {"status": "ready"}


@router.get("/version", response_model=VersionOut, summary="API and model versions")
def version(db: Session = Depends(get_db)) -> VersionOut:
    models = list(db.scalars(select(Model).order_by(Model.key)))
    return VersionOut(
        api_version=__version__,
        api_major="v1",
        environment=_settings.environment,
        models=[ModelOut.model_validate(m) for m in models],
    )
