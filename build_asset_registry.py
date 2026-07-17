"""
Build the Publication Asset Registry (Phase 7 · D6).

Catalogues EVERY figure, table, statistical result, and evaluation artefact so
each is traceable and reproducible for Paper 1. For each asset it records:
    kind · path · md5 · source_script · dataset_version · model_version ·
    provenance · intended_use (dashboard | paper1 | both) · description

The registry is generated (not hand-maintained) so it can never drift from what
is on disk, and each entry carries an md5 so the manifest is verifiable. It is the
single authoritative index of all reported evaluation results.

Output: evaluation/asset_registry.json
Run:    python build_asset_registry.py
(Regenerate the underlying assets first: regenerate_cnn_evaluation.py,
 evaluate_v5.py --from-saved, persist_comparison_artifact.py,
 generate_publication_assets.py.)
"""

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from birddash import config

BASE = config.BASE_DIR


def _md5(path: Path) -> str | None:
    if not path.exists() or path.is_dir():
        return None
    return hashlib.md5(path.read_bytes()).hexdigest()


def _dataset_version() -> dict:
    meta = BASE / "training_data" / "dataset_metadata.csv"
    rows = list(csv.DictReader(open(meta))) if meta.exists() else []
    species = sorted({r["common_name"] for r in rows if r.get("common_name")})
    return {
        "id": "xeno-canto-nt",
        "source": "Xeno-canto community recordings (Northern Territory species)",
        "metadata_file": "training_data/dataset_metadata.csv",
        "metadata_md5": _md5(meta),
        "metadata_rows": len(rows),
        "named_species": len(species),
        "note": "v5 uses 25 classes (adds Red_Goshawk) over training_data/ folders; "
                "the CNN test arrays derive from the same corpus. Longitude is missing "
                "(latitude-only), so spatial artefacts are site-approximate.",
    }


def _asset(kind, path, *, source_script, provenance, intended_use, model, description,
           dataset=True):
    p = BASE / path
    return {
        "kind": kind,
        "path": path,
        "exists": p.exists(),
        "md5": _md5(p),
        "source_script": source_script,
        "dataset_version": "xeno-canto-nt" if dataset else None,
        "model_version": model,
        "provenance": provenance,
        "intended_use": intended_use,
        "description": description,
    }


# Per-model artefact/figure/table descriptors.
MODELS = {
    "cnn_v2": dict(
        title="Custom CNN (v2) — segment-level", version="2", family="Custom CNN",
        model_artifact="models/nt_bird_cnn_best.keras", provenance="original_evaluation",
        eval_dir="evaluation/original/cnn_v2", eval_script="regenerate_cnn_evaluation.py",
        source_arrays=["models/y_test_probs.npy", "models/y_test_true.npy"],
    ),
    "cnn_v4": dict(
        title="Custom CNN (v4) — recording-level", version="4", family="Custom CNN",
        model_artifact="models/nt_bird_cnn_best.keras", provenance="original_evaluation",
        eval_dir="evaluation/original/cnn_v4", eval_script="regenerate_cnn_evaluation.py",
        source_arrays=["models/y_test_probs_v4.npy", "models/y_test_true_v4.npy"],
    ),
    "nt_v5": dict(
        title="NT Custom Classifier (v5) — recording-level held-out", version="5.2",
        family="NT Custom Classifier", model_artifact="models/NT_Bird_BirdNET_Classifier.tflite",
        provenance="independent_reproduction", eval_dir="evaluation/reproduced/v5",
        eval_script="evaluate_v5.py --from-saved",
        source_arrays=["evaluation/reproduced/v5/probabilities.npy",
                       "evaluation/reproduced/v5/labels.npy",
                       "evaluation/reproduced/v5/predictions.npy"],
    ),
}


def build() -> dict:
    assets: list[dict] = []

    for key, m in MODELS.items():
        mv = f"{m['family']} v{m['version']}"
        ed, es, prov = m["eval_dir"], m["eval_script"], m["provenance"]
        # Source arrays (paper1 provenance inputs).
        for arr in m["source_arrays"]:
            assets.append(_asset("array", arr, source_script="(persisted experiment output)",
                                 provenance=prov, intended_use="paper1", model=mv,
                                 description=f"Persisted probabilities/labels for {m['title']} — the reproducible input the metrics recompute from."))
        # Metrics + curve CSVs (consumed by the app AND the paper).
        assets.append(_asset("statistics", f"{ed}/metrics.json", source_script=es, provenance=prov,
                             intended_use="both", model=mv,
                             description=f"Accuracy/F1/AUROC/AUPRC + per-class metrics with CIs for {m['title']}. Served to the app via /models/registry."))
        for fname, desc in [("confusion_matrix.csv", "Confusion matrix"),
                            ("roc_curve.csv", "Micro-average ROC curve points"),
                            ("pr_curve.csv", "Micro-average PR curve points")]:
            assets.append(_asset("data-table", f"{ed}/{fname}", source_script=es, provenance=prov,
                                 intended_use="both", model=mv, description=f"{desc} for {m['title']}."))
        # Publication figures + tables.
        for kind in ("roc", "pr", "confusion"):
            for ext in ("png", "pdf"):
                assets.append(_asset("figure", f"evaluation/paper1/figures/{key}_{kind}.{ext}",
                                     source_script="generate_publication_assets.py", provenance=prov,
                                     intended_use="paper1", model=mv,
                                     description=f"Publication {kind.upper()} figure for {m['title']} ({ext})."))
        for ext, k in (("csv", "data-table"), ("tex", "table")):
            assets.append(_asset(k, f"evaluation/paper1/tables/{key}_per_class.{ext}",
                                 source_script="generate_publication_assets.py", provenance=prov,
                                 intended_use="paper1", model=mv,
                                 description=f"Per-class metrics table (with exact CIs) for {m['title']} ({ext})."))

    # Documented (not verified) v5 values — no artefact, shown badged in the app.
    assets.append(_asset("statistics", "README.md", source_script="(thesis/README)",
                         provenance="documented", intended_use="dashboard",
                         model="NT Custom Classifier v5.2", dataset=False,
                         description="Documented v5 AUPRC 0.98 / AUROC 0.99 — reported, NOT traceable to an artefact; shown behind a 'Documented · not verified' badge, never in Paper 1 as verified."))

    # Operational comparison (live_comparison) + its figure/caption.
    assets.append(_asset("statistics", "evaluation/reproduced/comparison/metrics.json",
                         source_script="persist_comparison_artifact.py", provenance="live_comparison",
                         intended_use="both", model="NT v5.2 vs BirdNET v2.4",
                         description="NT-vs-BirdNET rates (Wilson CIs) + exact McNemar, synonym-aware. Snapshot of the identical service code the app runs."))
    for ext in ("png", "pdf"):
        assets.append(_asset("figure", f"evaluation/paper1/figures/comparison_nt_vs_birdnet.{ext}",
                             source_script="generate_publication_assets.py", provenance="live_comparison",
                             intended_use="paper1", model="NT v5.2 vs BirdNET v2.4",
                             description=f"Publication comparison figure with Wilson CIs + McNemar ({ext})."))
    assets.append(_asset("caption", "evaluation/paper1/captions/comparison_nt_vs_birdnet.txt",
                         source_script="generate_publication_assets.py", provenance="live_comparison",
                         intended_use="paper1", model="NT v5.2 vs BirdNET v2.4",
                         description="Standalone manuscript caption for the comparison figure."))

    # Cross-cutting sources.
    assets.append(_asset("summary-table", "evaluation/paper1/tables/summary_metrics.csv",
                         source_script="generate_publication_assets.py", provenance="mixed",
                         intended_use="both", model="all",
                         description="Aggregate metrics for all models with provenance, n, and CIs (CSV)."))
    assets.append(_asset("table", "evaluation/paper1/tables/summary_metrics.tex",
                         source_script="generate_publication_assets.py", provenance="mixed",
                         intended_use="paper1", model="all",
                         description="LaTeX aggregate-metrics table for Paper 1."))
    assets.append(_asset("registry", "evaluation/registry.json", source_script="(hand-authored + resolved by model_registry.py)",
                         provenance="mixed", intended_use="both", model="all",
                         description="Model registry — the source the app resolves metrics from (documented vs original vs reproduction)."))
    assets.append(_asset("reference", "birddash/taxonomy.py", source_script="(source)",
                         provenance="mixed", intended_use="both", model="all", dataset=False,
                         description="Sourced synonym table underpinning synonym-aware scoring."))
    assets.append(_asset("methodology", "docs/METHODOLOGY.md", source_script="(source)",
                         provenance="mixed", intended_use="paper1", model="all", dataset=False,
                         description="Cited statistical + nomenclatural methods (Wilson/Clopper–Pearson/McNemar/bootstrap/synonyms)."))

    by_use: dict[str, int] = {}
    for a in assets:
        by_use[a["intended_use"]] = by_use.get(a["intended_use"], 0) + 1
    missing = [a["path"] for a in assets if not a["exists"]]

    return {
        "_comment": "Publication Asset Registry (Phase 7 · D6). Generated by "
                    "build_asset_registry.py — do not edit by hand. Every reported "
                    "evaluation result traces to an entry here.",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "dataset": _dataset_version(),
        "provenance_types": {
            "documented": "Reported (thesis/README), no traceable artefact — badged, never in Paper 1 as verified.",
            "original_evaluation": "Recomputed from the original saved arrays (CNN) — the original experiment.",
            "independent_reproduction": "A new held-out experiment (v5) — not the original thesis eval.",
            "live_comparison": "A live per-recording detection test (NT vs BirdNET), snapshotted.",
            "mixed": "Aggregates or sources spanning multiple provenance classes.",
        },
        "summary": {"total_assets": len(assets), "by_intended_use": by_use, "missing": missing},
        "assets": assets,
    }


def main():
    reg = build()
    out = BASE / "evaluation" / "asset_registry.json"
    out.write_text(json.dumps(reg, indent=2))
    s = reg["summary"]
    print(f"Asset registry: {s['total_assets']} assets "
          f"({s['by_intended_use']}) -> {out}")
    if s["missing"]:
        print(f"  WARNING: {len(s['missing'])} missing asset(s): {s['missing'][:5]}")


if __name__ == "__main__":
    main()
