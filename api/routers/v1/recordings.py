"""Recordings resource: metadata, audio streaming, and detections."""

from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, Response, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from api.db import get_db
from api.errors import NotFoundError
from api.schemas import (
    DetectionOut, MultiSpeciesOut, NtPredictionsOut, Page, RecordingOut,
)
from api.security import Principal, require_scope
from api.services import analysis as analysis_svc
from api.services import detections as detection_svc
from api.services import recordings as recording_svc
from api.services import uploads as upload_svc
from birddash import audio, config

router = APIRouter(prefix="/recordings", tags=["recordings"])


@router.get("", response_model=Page[RecordingOut], summary="List recordings")
def list_recordings(
    site: UUID | None = Query(default=None, description="Filter by site id"),
    cursor: str | None = Query(default=None),
    limit: int | None = Query(default=None, ge=1, le=200),
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_scope("recordings:read")),
) -> Page[RecordingOut]:
    return recording_svc.list_recordings(db, principal, site_id=site, cursor=cursor, limit=limit)


@router.post("/upload", response_model=RecordingOut, status_code=201,
             summary="Upload a recording and analyse it with BirdNET")
def upload_recording(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_scope("recordings:write")),
) -> RecordingOut:
    return upload_svc.create_from_upload(db, principal, file.filename, file.file)


@router.get("/{recording_id}", response_model=RecordingOut, summary="Get a recording")
def get_recording(
    recording_id: UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_scope("recordings:read")),
) -> RecordingOut:
    return recording_svc.get_recording(db, principal, recording_id)


@router.get("/{recording_id}/audio", summary="Stream the recording audio")
def get_audio(
    recording_id: UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_scope("recordings:read")),
):
    rec = recording_svc.get_recording_entity(db, principal, recording_id)
    path = config.BASE_DIR / rec.source_path
    if not path.exists():
        raise NotFoundError("Audio file is not available on the server")
    # FileResponse handles HTTP Range requests (seekable audio playback).
    return FileResponse(str(path), media_type=rec.media_type, filename=rec.filename)


@router.get("/{recording_id}/spectrogram", summary="Mel spectrogram (PNG, cached)")
def get_spectrogram(
    recording_id: UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_scope("recordings:read")),
):
    rec = recording_svc.get_recording_entity(db, principal, recording_id)
    stem = Path(rec.source_path).stem
    cache = config.DETECTIONS_DIR / f"{stem}_spectrogram.png"
    if cache.exists():
        png = cache.read_bytes()
    else:
        path = config.BASE_DIR / rec.source_path
        if not path.exists():
            raise NotFoundError("Audio file is not available on the server")
        png = audio.render_spectrogram_png(str(path))
        config.DETECTIONS_DIR.mkdir(parents=True, exist_ok=True)
        cache.write_bytes(png)
    return Response(content=png, media_type="image/png",
                    headers={"Cache-Control": "public, max-age=3600"})


@router.get("/{recording_id}/detections", response_model=list[DetectionOut],
            summary="BirdNET detections for a recording")
def get_detections(
    recording_id: UUID,
    min_confidence: float = Query(default=0.0, ge=0.0, le=1.0),
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_scope("detections:read")),
) -> list[DetectionOut]:
    return detection_svc.list_for_recording(db, principal, recording_id,
                                            min_confidence=min_confidence)


@router.get("/{recording_id}/nt-predictions", response_model=NtPredictionsOut,
            summary="Historical NT CNN (v2/v3) per-segment predictions")
def get_nt_predictions(
    recording_id: UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_scope("detections:read")),
) -> NtPredictionsOut:
    """Historical NT CNN (v2/v3) per-segment predictions. Retained intact for
    research reproducibility and the Model Evolution history; the production NT
    model is the v5 Custom Classifier via the v5.2 SED pipeline."""
    return analysis_svc.nt_predictions(db, principal, recording_id)


@router.get("/{recording_id}/multi-species", response_model=MultiSpeciesOut,
            summary="Multi-species sound-event detection (v5.2, cached or re-run)")
def get_multi_species(
    recording_id: UUID,
    force: bool = Query(default=False, description="Re-run instead of using cache"),
    primary_conf: float | None = Query(default=None, ge=0.3, le=0.95),
    secondary_conf: float | None = Query(default=None, ge=0.1, le=0.7),
    sensitivity: float | None = Query(default=None, ge=0.75, le=1.5),
    overlap: float | None = Query(default=None, ge=0.0, le=2.9),
    top_k: int | None = Query(default=None, ge=1, le=5),
    suppress_primary: bool | None = Query(default=None),
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_scope("detections:read")),
) -> MultiSpeciesOut:
    params = {
        "primary_conf": primary_conf, "secondary_conf": secondary_conf,
        "sensitivity": sensitivity, "overlap": overlap, "top_k": top_k,
        "suppress_primary": suppress_primary,
    }
    return analysis_svc.multi_species(db, principal, recording_id, force=force, params=params)
