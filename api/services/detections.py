"""Detection use-cases (read from the filesystem artifact repo in Phase 3a)."""

from uuid import UUID

from sqlalchemy.orm import Session

from api.repositories import detections as repo
from api.schemas import DetectionOut
from api.security import Principal
from api.services.recordings import get_recording_entity


def list_for_recording(db: Session, principal: Principal, recording_id: UUID, *,
                       min_confidence: float = 0.0) -> list[DetectionOut]:
    rec = get_recording_entity(db, principal, recording_id)   # 404s if absent / wrong org
    raw = repo.list_for_recording(rec.source_path, min_confidence=min_confidence)
    return [
        DetectionOut(
            recording_id=rec.id,
            start_seconds=d["start_seconds"],
            end_seconds=d["end_seconds"],
            common_name=d["common_name"],
            scientific_name=d["scientific_name"],
            confidence=d["confidence"],
            source="birdnet",
        )
        for d in raw
    ]
