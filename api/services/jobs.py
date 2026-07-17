"""
Job use-cases and the async-work executor abstraction.

Phase 3a ships the Job *resource* (create/read) and an in-process executor
stub. Phase 3b uses `create_and_run` for uploads/analyses; a later phase swaps
the executor for Celery/RQ + Redis with no change to this interface or the API.
"""

from collections.abc import Callable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from api.db import SessionLocal
from api.errors import NotFoundError
from api.models import Job
from api.pagination import clamp_limit, decode_cursor, encode_cursor
from api.schemas import JobOut, Page
from api.security import Principal


def get_job(db: Session, principal: Principal, job_id: UUID) -> JobOut:
    job = db.scalars(
        select(Job).where(Job.id == job_id, Job.organisation_id == principal.organisation_id)
    ).first()
    if job is None:
        raise NotFoundError(f"Job {job_id} not found")
    return JobOut.model_validate(job)


def list_jobs(db: Session, principal: Principal, *,
              cursor: str | None, limit: int | None) -> Page[JobOut]:
    limit = clamp_limit(limit)
    after_id = decode_cursor(cursor)
    stmt = select(Job).where(Job.organisation_id == principal.organisation_id)
    if after_id is not None:
        stmt = stmt.where(Job.id > after_id)
    rows = list(db.scalars(stmt.order_by(Job.id).limit(limit + 1)))
    has_more = len(rows) > limit
    rows = rows[:limit]
    next_cursor = encode_cursor(rows[-1].id) if has_more and rows else None
    return Page(items=[JobOut.model_validate(j) for j in rows],
                next_cursor=next_cursor, limit=limit)


def create_job(db: Session, principal: Principal, job_type: str) -> Job:
    job = Job(organisation_id=principal.organisation_id, type=job_type,
              status="queued", progress=0)
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


# --- Executor abstraction (swappable for Celery/RQ later) ----------------

JobWork = Callable[[Session, Job], None]


def run_now(job_id: UUID, work: JobWork) -> None:
    """Execute `work` in-process with its own DB session, tracking status.

    Used with FastAPI BackgroundTasks in Phase 3b. A distributed executor will
    implement this same contract (enqueue instead of run inline)."""
    db = SessionLocal()
    try:
        job = db.get(Job, job_id)
        if job is None:
            return
        job.status = "running"
        db.commit()
        work(db, job)
        job.status = "succeeded"
        job.progress = 100
        db.commit()
    except Exception as exc:  # noqa: BLE001 — record failure on the job
        db.rollback()
        job = db.get(Job, job_id)
        if job is not None:
            job.status = "failed"
            job.error = str(exc)[:2048]
            db.commit()
    finally:
        db.close()
