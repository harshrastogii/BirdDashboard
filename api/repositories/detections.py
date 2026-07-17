"""
Detection artifact repository (filesystem, Phase 3a).

Reads BirdNET result CSVs produced by the pipeline. This adapter is the thing
that changes in Phase 6: detections move into a Postgres table (and the query
below becomes indexed SQL) with no change to the service or API layers.
"""

from pathlib import Path

import pandas as pd

from birddash import config


def list_for_recording(source_path: str, *, min_confidence: float = 0.0) -> list[dict]:
    """Return BirdNET detections for one recording, filtered by confidence.

    `source_path` is the recording's stored path, e.g. "sample_audio/Foo.mp3";
    the matching results file is "<stem>.BirdNET.results.csv".
    """
    stem = Path(source_path).stem
    csv_path = config.BIRDNET_RESULTS_DIR / f"{stem}.BirdNET.results.csv"
    if not csv_path.exists():
        return []

    df = pd.read_csv(csv_path)
    if df.empty:
        return []
    df = df[df["Confidence"] >= min_confidence]

    detections = []
    for _, row in df.iterrows():
        detections.append({
            "start_seconds": float(row["Start (s)"]),
            "end_seconds": float(row["End (s)"]),
            "common_name": str(row["Common name"]),
            "scientific_name": (str(row["Scientific name"])
                                if "Scientific name" in row and pd.notna(row["Scientific name"])
                                else None),
            "confidence": float(row["Confidence"]),
        })
    return detections
