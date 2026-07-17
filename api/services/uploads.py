"""
Upload use-case — restores the original Streamlit "upload a recording" feature.

Saves the audio, analyses it with the global BirdNET model (exactly as the
Streamlit sidebar did), registers a Recording, and returns it. The v5.2
multi-species pipeline runs on demand when the recording is opened.
"""

import os
import shutil
from pathlib import Path

from sqlalchemy.orm import Session

from api.errors import ConflictError, ValidationError
from api.models import Recording
from api.repositories.recordings import get_by_source_path
from api.schemas import RecordingOut
from api.security import Principal
from api.services.recordings import _to_dto
from birddash import birdnet, config

_MEDIA = {".mp3": "audio/mpeg", ".wav": "audio/wav", ".flac": "audio/flac", ".ogg": "audio/ogg"}


def create_from_upload(db: Session, principal: Principal, filename: str, fileobj) -> RecordingOut:
    name = os.path.basename(filename or "")
    ext = Path(name).suffix.lower()
    if ext not in _MEDIA:
        raise ValidationError(f"Unsupported file type '{ext}'. Use MP3, WAV, FLAC, or OGG.")

    os.makedirs(config.SAMPLE_AUDIO_DIR, exist_ok=True)
    save_path = config.SAMPLE_AUDIO_DIR / name
    rel = f"{config.SAMPLE_AUDIO_DIR.name}/{name}"

    if get_by_source_path(db, rel) or save_path.exists():
        raise ConflictError(f"A recording named '{name}' already exists.")

    with open(save_path, "wb") as out:
        shutil.copyfileobj(fileobj, out)

    # Analyse with global BirdNET (as the original upload flow did). If BirdNET
    # fails, keep the recording — analysis can be retried on demand.
    try:
        birdnet.analyze_upload(rel, output_dir=config.BIRDNET_RESULTS_DIR)
    except Exception:  # noqa: BLE001
        pass

    rec = Recording(
        organisation_id=principal.organisation_id, source_path=rel, filename=name,
        media_type=_MEDIA[ext], size_bytes=save_path.stat().st_size,
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return _to_dto(rec)
