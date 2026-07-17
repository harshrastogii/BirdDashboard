"""Jobs resource: track asynchronous work (uploads, analyses, ...)."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.db import get_db
from api.schemas import JobOut, Page
from api.security import Principal, require_scope
from api.services import jobs as job_svc

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("", response_model=Page[JobOut], summary="List jobs")
def list_jobs(
    cursor: str | None = Query(default=None),
    limit: int | None = Query(default=None, ge=1, le=200),
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_scope("jobs:read")),
) -> Page[JobOut]:
    return job_svc.list_jobs(db, principal, cursor=cursor, limit=limit)


@router.get("/{job_id}", response_model=JobOut, summary="Get a job")
def get_job(
    job_id: UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_scope("jobs:read")),
) -> JobOut:
    return job_svc.get_job(db, principal, job_id)
