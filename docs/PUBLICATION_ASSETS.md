# PUBLICATION_ASSETS.md — Publication Asset Registry (Phase 7 · D6)

> The single authoritative index of every figure, table, statistical result, and
> evaluation artefact behind the platform's reported results — each traceable and
> reproducible for **Paper 1**.
> Machine-readable source: [`evaluation/asset_registry.json`](../evaluation/asset_registry.json)
> (generated). Companion: [METHODOLOGY.md](METHODOLOGY.md) ·
> [../MODEL_REGISTRY.md](../MODEL_REGISTRY.md) · [../SCIENTIFIC_METHOD.md](../SCIENTIFIC_METHOD.md)

## Purpose

Nothing reported by Avian Observatory — in the app or in Paper 1 — is hand-entered.
Every number and figure originates from a persisted artefact, and this registry
catalogues each one with its **source script, dataset version, model version,
provenance, intended use, and an md5** so the manifest is verifiable. The registry
is *generated* (`build_asset_registry.py`), so it cannot drift from disk.

## Provenance types (never conflated — see DECISIONS.md D-12/D-13)

| Type | Meaning |
|---|---|
| `documented` | Reported (thesis/README), **no** traceable artefact. Shown badged "Documented · not verified"; **never** used in Paper 1 as verified (e.g. v5 AUPRC 0.98 / AUROC 0.99). |
| `original_evaluation` | Recomputed from the **original** saved arrays — the original experiment (CNN v2/v4). |
| `independent_reproduction` | A **new** held-out experiment (v5), not the original thesis eval. |
| `live_comparison` | A live per-recording detection test (NT vs BirdNET), snapshotted to disk. |
| `mixed` | Aggregates/sources spanning classes (summary table, registry, methodology). |

## Intended use

- **both** — consumed by the app *and* Paper 1 (e.g. each model's `metrics.json`,
  the ROC/PR/confusion CSVs, the comparison snapshot, the model registry).
- **paper1** — manuscript assets (PNG+PDF figures, CSV+LaTeX tables, captions,
  the persisted probability/label arrays).
- **dashboard** — app-only (the documented, badged v5 0.98/0.99).

Current inventory: **53 assets** (paper1 36 · both 16 · dashboard 1), 0 missing.

## The reproducible pipeline

```
# 1. Recompute classifier metrics + CIs from PERSISTED arrays (no retraining):
python regenerate_cnn_evaluation.py            # CNN v2/v3/v4 -> evaluation/original/cnn_*
python evaluate_v5.py --from-saved             # v5 held-out  -> evaluation/reproduced/v5

# 2. Snapshot the live NT-vs-BirdNET comparison (identical service code as the app):
python persist_comparison_artifact.py          # -> evaluation/reproduced/comparison

# 3. Render publication figures + tables (colourblind-safe, PNG+PDF, CSV+LaTeX):
python generate_publication_assets.py          # -> evaluation/paper1/{figures,tables,captions}

# 4. Rebuild this registry (adds md5s + metadata) and verify provenance:
python build_asset_registry.py                 # -> evaluation/asset_registry.json
python verify_metric_provenance.py             # asserts app metrics == artefacts
```

Every step reads only persisted inputs — **no retraining**, honouring the paused
v5 retrain. `generate_charts.py` (hardcoded thesis PNGs) is **deprecated and
quarantined**: `verify_metric_provenance.py` asserts nothing on the app/eval path
imports it. Use `generate_publication_assets.py` instead.

## What's in `evaluation/paper1/`

- `figures/` — per model: `<key>_confusion.{png,pdf}`, `<key>_roc.{png,pdf}`,
  `<key>_pr.{png,pdf}`; plus `comparison_nt_vs_birdnet.{png,pdf}` (Wilson CIs +
  McNemar). 300 dpi raster + vector; Okabe–Ito colourblind-safe.
- `tables/` — per model `<key>_per_class.{csv,tex}` (with exact CIs + reliability
  flag); `summary_metrics.{csv,tex}` (all models, provenance, n, CIs).
- `captions/` — standalone manuscript captions.

## Verification guarantee

`verify_metric_provenance.py` (9 checks, all passing) asserts:
1. every registry evaluation resolves to a catalogued `metrics.json`;
2. the **live** `/models/comparison` equals the persisted snapshot (app == artefact);
3. the Model-Evolution narrative constants trace to artefacts (92.7% → cnn_v2,
   66.6% → cnn_v4) and the v5 0.98/0.99 appear only behind a documented badge;
4. no verified/displayed path imports the hardcoded `generate_charts.py`.

**Result: every metric displayed in the application originates from the same
reproducible evaluation artefacts used for publication.**

## Dataset version

`training_data/dataset_metadata.csv` (md5 recorded in the registry; 1215 rows, 24
named species). v5 uses 25 classes (adds Red_Goshawk) over `training_data/`
folders. Longitude is missing (latitude-only), so spatial artefacts are
site-approximate (see ARCHITECTURE.md §6).
