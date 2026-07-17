"""
Model-comparison use-case: the platform-level story, scientifically fair.

Compares the PRODUCTION NT model — the NT Custom Classifier (v5), deployed via
the v5.2 multi-species SED pipeline — against the global BirdNET v2.4 baseline.

Fairness guarantees:
  * Both models are scored on EXACTLY the same set of recordings (only those
    with a verified label AND output from both models are counted).
  * Ground truth comes from the verified recording labels in
    training_data/dataset_metadata.csv (falling back to filename matching).
  * Each recording exposes what each model predicted, so successes and failures
    are transparent.

The superseded v2/v3 CNN and its 92.7% figure are NOT used here; they live in
the Research Metrics / Model Evolution history.
"""

import csv
import json
from functools import lru_cache
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from api.models import Recording, Species
from api.schemas import (
    IntervalOut, McNemarOut, ModelComparisonOut, ModelComparisonRecord,
)
from api.security import Principal
from api.services.biodiversity import _pretty
from birddash import config, statistics as stats, taxonomy
from api.repositories import detections as detection_repo


def _norm(s: str) -> str:
    return taxonomy.normalize(s)


@lru_cache(maxsize=1)
def _verified_labels() -> dict[str, str]:
    """filename -> verified common name, from the training dataset metadata."""
    out: dict[str, str] = {}
    path = config.BASE_DIR / "training_data" / "dataset_metadata.csv"
    if path.exists():
        with open(path) as f:
            for row in csv.DictReader(f):
                fn, cn = row.get("filename"), row.get("common_name")
                if fn and cn:
                    out[fn] = cn
    return out


def _v5_species_for(source_path: str) -> tuple[set[str], str | None] | None:
    stem = Path(source_path).stem
    json_path = config.DETECTIONS_DIR / f"{stem}_v5_1_detections.json"
    if not json_path.exists():
        return None
    data = json.loads(json_path.read_text())
    return {e["species"] for e in data.get("events", [])}, data.get("primary_species")


def compare(db: Session, principal: Principal) -> ModelComparisonOut:
    # Canonical catalog (for resolving a verified label to a consistent name).
    catalog = [(s.common_name, _norm(s.common_name)) for s in db.scalars(select(Species))]
    catalog.sort(key=lambda t: len(t[1]), reverse=True)
    verified = _verified_labels()

    def ground_truth_for(rec: Recording) -> str | None:
        # 1) verified label from the dataset; 2) filename match against catalog.
        label = verified.get(rec.filename)
        if label:
            n = _norm(label)
            return next((name for name, cn in catalog if cn == n), label)
        fnorm = _norm(rec.filename)
        return next((name for name, cn in catalog if cn and fnorm.startswith(cn)), None)

    recordings = list(db.scalars(
        select(Recording).where(Recording.organisation_id == principal.organisation_id)
        .order_by(Recording.filename)
    ))

    rows: list[ModelComparisonRecord] = []
    bn_correct = nt_correct = total_eval = 0
    only_nt = only_bn = 0   # discordant-pair counts for the McNemar paired test

    for rec in recordings:
        ground_truth = ground_truth_for(rec)
        dets = detection_repo.list_for_recording(rec.source_path, min_confidence=0.0)
        v5 = _v5_species_for(rec.source_path)

        # Fairness: only score recordings evaluated by BOTH models with a label.
        evaluated_by_both = bool(dets) and v5 is not None
        counts = ground_truth is not None and evaluated_by_both

        bn_top = max(dets, key=lambda d: d["confidence"]) if dets else None
        # Synonym-aware matching: a correct detection under a synonymous common
        # name (e.g. BirdNET's "Bush Thick-knee" for "Bush Stone-curlew") counts
        # as correct, not a miss. See birddash.taxonomy.
        bn_flag = (any(taxonomy.same_species(d["common_name"], ground_truth) for d in dets)
                   if counts else None)

        nt_top = v5[1] if v5 else None
        nt_flag = None
        if counts and v5 is not None:
            event_species, primary = v5
            nt_flag = any(taxonomy.same_species(s, ground_truth) for s in event_species) or (
                taxonomy.same_species(primary, ground_truth))

        if counts:
            total_eval += 1
            if bn_flag:
                bn_correct += 1
            if nt_flag:
                nt_correct += 1
            if nt_flag and not bn_flag:
                only_nt += 1
            elif bn_flag and not nt_flag:
                only_bn += 1

        rows.append(ModelComparisonRecord(
            recording_id=rec.id, name=_pretty(rec.source_path), ground_truth=ground_truth,
            evaluated=counts,
            birdnet_top=bn_top["common_name"] if bn_top else None,
            birdnet_confidence=bn_top["confidence"] if bn_top else None,
            birdnet_correct=bn_flag, nt_top=nt_top, nt_correct=nt_flag,
        ))

    # Uncertainty on each rate (Wilson) + the paired difference (exact McNemar).
    # With n≈23 these intervals are wide; reporting them prevents over-reading a
    # single-number lead. See birddash.statistics + docs/METHODOLOGY.md.
    nt_ci = stats.wilson_interval(nt_correct, total_eval) if total_eval else None
    bn_ci = stats.wilson_interval(bn_correct, total_eval) if total_eval else None
    mcnemar = stats.mcnemar_exact(only_nt, only_bn) if total_eval else None

    return ModelComparisonOut(
        birdnet_correct=bn_correct, nt_correct=nt_correct,
        total_with_ground_truth=total_eval,
        nt_interval=IntervalOut(**nt_ci.as_dict()) if nt_ci else None,
        birdnet_interval=IntervalOut(**bn_ci.as_dict()) if bn_ci else None,
        mcnemar=McNemarOut(**mcnemar.as_dict()) if mcnemar else None,
        provenance={
            "n_recordings": total_eval,
            "ground_truth_source": "verified labels from training_data/dataset_metadata.csv "
                                   "(fallback: catalog filename match)",
            "scoring": "does the model detect the recording's verified species (synonym-aware)?",
            "synonym_handling": taxonomy.synonym_provenance(),
            "rate_interval": "Wilson score 95% (Wilson 1927)",
            "paired_test": "exact McNemar (McNemar 1947; Edwards 1948)",
            "note": "Live per-recording detection test — distinct from the held-out "
                    "classifier evaluations in the model registry.",
        },
        per_recording=rows,
    )
