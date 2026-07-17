"""Recording metadata repository (Postgres)."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from api.models import Recording


def list_recordings(db: Session, organisation_id: UUID, *,
                    site_id: UUID | None = None,
                    limit: int = 50,
                    after_id: UUID | None = None) -> list[Recording]:
    """Keyset-paginated list, ordered by id. Fetches limit+1 to detect more."""
    stmt = select(Recording).where(Recording.organisation_id == organisation_id)
    if site_id is not None:
        stmt = stmt.where(Recording.site_id == site_id)
    if after_id is not None:
        stmt = stmt.where(Recording.id > after_id)
    stmt = stmt.order_by(Recording.id).limit(limit + 1)
    return list(db.scalars(stmt))


def get_recording(db: Session, organisation_id: UUID, recording_id: UUID) -> Recording | None:
    stmt = select(Recording).where(
        Recording.id == recording_id,
        Recording.organisation_id == organisation_id,
    )
    return db.scalars(stmt).first()


def get_by_source_path(db: Session, source_path: str) -> Recording | None:
    return db.scalars(select(Recording).where(Recording.source_path == source_path)).first()
