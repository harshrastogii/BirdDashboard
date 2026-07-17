"""
Analysis use-cases: NT CNN predictions and multi-species sound-event detection.

Both are compute-heavy, so results are cached on the filesystem (keyed by
recording) and reused on subsequent requests — mirroring the Streamlit app's
behaviour. The NT model is loaded lazily once per process.
"""

import json
from pathlib import Path
from uuid import UUID

from sqlalchemy.orm import Session

from api.errors import APIError
from api.schemas import (
    MultiSpeciesEvent, MultiSpeciesOut, NtPredictionRow, NtPredictionsOut,
)
from api.security import Principal
from api.services.recordings import get_recording_entity
from birddash import config, detection, nt_model

# Lazy, process-wide NT model cache (TensorFlow is heavy; load once).
_MODEL = None
_LABELS: dict | None = None


def _model_and_labels():
    global _MODEL, _LABELS
    if _MODEL is None:
        _MODEL = nt_model.load_model()
        _LABELS = nt_model.load_label_map()
    return _MODEL, _LABELS


def nt_predictions(db: Session, principal: Principal, recording_id: UUID) -> NtPredictionsOut:
    rec = get_recording_entity(db, principal, recording_id)
    stem = Path(rec.source_path).stem
    cache = config.DETECTIONS_DIR / f"{stem}_nt_predictions.json"

    if cache.exists():
        rows = json.loads(cache.read_text())
    else:
        model, labels = _model_and_labels()
        if model is None:
            raise APIError("NT CNN model is not available on the server.")
        audio_path = config.BASE_DIR / rec.source_path
        df = nt_model.predict(str(audio_path), model, labels)
        rows = [
            {
                "start_seconds": r["Start (s)"],
                "end_seconds": r["End (s)"],
                "species": r["Species"],
                "confidence": r["Confidence"],
                "rank": r["Rank"],
            }
            for r in df.to_dict("records")
        ]
        config.DETECTIONS_DIR.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(rows))

    return NtPredictionsOut(
        recording_id=rec.id,
        predictions=[NtPredictionRow(**r) for r in rows],
    )


def multi_species(db: Session, principal: Principal, recording_id: UUID, *,
                  force: bool = False, params: dict | None = None) -> MultiSpeciesOut:
    """Run (or read cached) v5.2 multi-species SED. When `params` are supplied
    or `force` is set, the detector is re-run with those parameters instead of
    using the cached default result."""
    rec = get_recording_entity(db, principal, recording_id)
    stem = Path(rec.source_path).stem
    json_path = config.DETECTIONS_DIR / f"{stem}_v5_1_detections.json"

    run_params = {k: v for k, v in (params or {}).items() if v is not None}
    cached = json_path.exists() and not force and not run_params
    if cached:
        data = json.loads(json_path.read_text())
    else:
        audio_path = config.BASE_DIR / rec.source_path
        try:
            data = detection.run_detection(str(audio_path), make_plot=False, **run_params)
        except RuntimeError as e:
            raise APIError(f"Multi-species detection failed: {e}")

    events = data.get("events", [])
    primary = data.get("primary_species")
    dto_events = [
        MultiSpeciesEvent(
            start=e["start"], end=e["end"], species=e["species"],
            confidence=e["confidence"], is_primary=(e["species"] == primary),
        )
        for e in events
    ]
    return MultiSpeciesOut(
        recording_id=rec.id,
        duration_seconds=data.get("duration_seconds", 0.0),
        primary_species=primary,
        num_events=len(events),
        unique_species=len({e["species"] for e in events}),
        events=dto_events,
        parameters=data.get("parameters", {}),
        cached=cached,
    )
