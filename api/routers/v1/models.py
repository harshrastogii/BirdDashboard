"""Models resource: catalog + the aggregate BirdNET-vs-NT comparison."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.db import get_db
from api.models import Model
from api.schemas import ModelComparisonOut, ModelOut, ModelRegistryOut, ResearchMetricsOut
from api.security import Principal, require_scope
from api.services import model_comparison as cmp_svc
from api.services import model_registry as registry_svc
from api.services import research_metrics as research_svc

router = APIRouter(prefix="/models", tags=["models"])


@router.get("", response_model=list[ModelOut], summary="List models")
def list_models(
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_scope("species:read")),
) -> list[ModelOut]:
    return [ModelOut.model_validate(m) for m in db.scalars(select(Model).order_by(Model.key))]


@router.get("/comparison", response_model=ModelComparisonOut,
            summary="Aggregate NT-vs-BirdNET accuracy across the library")
def comparison(
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_scope("detections:read")),
) -> ModelComparisonOut:
    return cmp_svc.compare(db, principal)


@router.get("/research-metrics", response_model=ResearchMetricsOut,
            summary="(legacy) Research metrics — see /models/registry")
def research_metrics(
    principal: Principal = Depends(require_scope("species:read")),
) -> ResearchMetricsOut:
    return research_svc.research_metrics()


@router.get("/registry", response_model=ModelRegistryOut,
            summary="Model registry: versions, documented values, evaluation history")
def registry(
    principal: Principal = Depends(require_scope("species:read")),
) -> ModelRegistryOut:
    return registry_svc.registry()
