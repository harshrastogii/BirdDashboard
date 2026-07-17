"""Recording use-cases."""

from uuid import UUID

from sqlalchemy.orm import Session

from api.errors import NotFoundError
from api.models import Recording
from api.pagination import clamp_limit, decode_cursor, encode_cursor
from api.repositories import recordings as repo
from api.schemas import Page, RecordingOut
from api.security import Principal
from api.services import geospatial

API_PREFIX = "/api/v1"


def _to_dto(rec: Recording) -> RecordingOut:
    # Resolve location through the coordinate provider (precise if per-recording
    # GPS exists, else approximate via the site). Single source of location.
    loc = geospatial.resolve_location(rec, rec.site)
    return RecordingOut(
        id=rec.id,
        organisation_id=rec.organisation_id,
        site_id=rec.site_id,
        sensor_id=rec.sensor_id,
        filename=rec.filename,
        media_type=rec.media_type,
        size_bytes=rec.size_bytes,
        duration_seconds=rec.duration_seconds,
        captured_at=rec.captured_at,
        created_at=rec.created_at,
        latitude=loc.latitude,
        longitude=loc.longitude,
        coordinate_precision=loc.precision,
        coordinate_source=loc.source,
        audio_url=f"{API_PREFIX}/recordings/{rec.id}/audio",
        detections_url=f"{API_PREFIX}/recordings/{rec.id}/detections",
    )


def list_recordings(db: Session, principal: Principal, *,
                    site_id: UUID | None, cursor: str | None,
                    limit: int | None) -> Page[RecordingOut]:
    limit = clamp_limit(limit)
    after_id = decode_cursor(cursor)
    rows = repo.list_recordings(db, principal.organisation_id,
                                site_id=site_id, limit=limit, after_id=after_id)
    has_more = len(rows) > limit
    rows = rows[:limit]
    next_cursor = encode_cursor(rows[-1].id) if has_more and rows else None
    return Page(items=[_to_dto(r) for r in rows], next_cursor=next_cursor, limit=limit)


def get_recording(db: Session, principal: Principal, recording_id: UUID) -> RecordingOut:
    rec = repo.get_recording(db, principal.organisation_id, recording_id)
    if rec is None:
        raise NotFoundError(f"Recording {recording_id} not found")
    return _to_dto(rec)


def get_recording_entity(db: Session, principal: Principal, recording_id: UUID) -> Recording:
    """Return the ORM row (for endpoints needing source_path, e.g. audio/detections)."""
    rec = repo.get_recording(db, principal.organisation_id, recording_id)
    if rec is None:
        raise NotFoundError(f"Recording {recording_id} not found")
    return rec
