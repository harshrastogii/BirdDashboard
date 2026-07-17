"""Biodiversity use-cases: Shannon / Simpson / richness across the library.

Mirrors the Streamlit biodiversity + cross-file comparison sections, computed
from BirdNET detections via the birddash.metrics core.
"""

import os

from sqlalchemy import select
from sqlalchemy.orm import Session

from api.models import Recording
from api.schemas import BiodiversityOut, BiodiversityRecord
from api.security import Principal
from birddash import config, metrics
from birddash import results as results_repo


def _pretty(file_path: str) -> str:
    base = os.path.basename(file_path)
    return base.replace(".mp3", "").replace(".wav", "").replace("_", " ")


def biodiversity(db: Session, principal: Principal, *, min_confidence: float) -> BiodiversityOut:
    df = results_repo.load_results(config.BIRDNET_RESULTS_DIR)
    if df.empty:
        return BiodiversityOut(min_confidence=min_confidence, overall_richness=0,
                               overall_shannon=0.0, overall_simpson=0.0, per_recording=[])

    df = df[df["Confidence"] >= min_confidence]

    # Map recording source_path -> id for the caller's organisation.
    id_by_path = {
        r.source_path: r.id
        for r in db.scalars(
            select(Recording).where(Recording.organisation_id == principal.organisation_id)
        )
    }

    per: list[BiodiversityRecord] = []
    for file_path, group in df.groupby("File"):
        counts = group["Common name"].value_counts().to_dict()
        per.append(BiodiversityRecord(
            recording_id=id_by_path.get(file_path),
            name=_pretty(file_path),
            species_richness=len(counts),
            shannon_index=round(metrics.shannon_index(counts), 3),
            simpson_index=round(metrics.simpson_index(counts), 3),
            total_detections=int(len(group)),
        ))
    per.sort(key=lambda r: r.name)

    overall_counts = df["Common name"].value_counts().to_dict()
    return BiodiversityOut(
        min_confidence=min_confidence,
        overall_richness=len(overall_counts),
        overall_shannon=round(metrics.shannon_index(overall_counts), 3),
        overall_simpson=round(metrics.simpson_index(overall_counts), 3),
        per_recording=per,
    )
