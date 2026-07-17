# CLAUDE.md — Avian Observatory

Orientation for AI assistants working in this repository. **Read the linked
docs before making changes** — they are the single source of truth.

## What this is

**Avian Observatory** — an environmental-intelligence platform for acoustic bird
monitoring in the Northern Territory (Australia), migrated from a Streamlit thesis
dashboard (PRT840, Charles Darwin University) into a layered platform:

```
birddash (Python scientific core) → FastAPI (api/) → Next.js (frontend/)
PostgreSQL (metadata) + filesystem (audio, detections, spectrograms)
```

The original Streamlit app (`app.py`, `multi_species_section.py`) still runs and
is the parity reference; it imports `birddash`, so nothing was forked.

## Vision

Avian Observatory is **evolving from a bird-classification dashboard into a
professional environmental-intelligence platform** for ecological research,
biodiversity monitoring, and conservation decision support. The direction is
**GIS-first**: fuse acoustic AI (species detection), spatial data (recording
locations, monitoring sites), and — over time — environmental context (weather,
fire, vegetation, protected areas, hydrology) to answer not just *"what species
is this?"* but *"where, when, in what habitat, under what conditions, and what
does it mean for conservation?"*

The GIS roadmap runs in four stages (see ROADMAP.md): **1 Recording Intelligence
→ 2 Environmental Intelligence → 3 Spatial Ecology → 4 TerraIQ Integration**.
**TerraIQ** is a *future, separate* environmental-intelligence engine that will
supply environmental context to Avian Observatory via a clean API boundary — an
integration, **not a replacement**. Avian Observatory owns acoustic + biodiversity
intelligence; TerraIQ owns environmental intelligence; they stay decoupled.

## Source-of-truth documents (read these)

| Doc | Use it for |
|---|---|
| **[REPOSITORY_GUIDE.md](REPOSITORY_GUIDE.md)** | Map of every folder & standalone script (runtime/training/evaluation/publication/archive), when to use each, and what's dead/deprecated. Orient here before touching unfamiliar files. |
| **[PROJECT_STATE.md](PROJECT_STATE.md)** | Current status, how to run, priorities, immediate next tasks. **Start here.** |
| **[ARCHITECTURE.md](ARCHITECTURE.md)** | birddash core, FastAPI, Next.js, API contract, repositories, GIS, annotation, evaluation, registry. |
| **[MODEL_REGISTRY.md](MODEL_REGISTRY.md)** | Every model (CNN v2/v3/v4, v5, v5.2, BirdNET), rationale, documented vs verified metrics, provenance. |
| **[ROADMAP.md](ROADMAP.md)** | Completed phases, current phase, remaining milestones. |
| **[DECISIONS.md](DECISIONS.md)** | Every architectural & scientific decision + reasoning (D-1…D-24). |
| **[TECHNICAL_DEBT.md](TECHNICAL_DEBT.md)** | Dead code, legacy components, limitations, cleanup (nothing deleted without approval). |
| **[SCIENTIFIC_METHOD.md](SCIENTIFIC_METHOD.md)** | Dataset, annotation, evaluation & comparison methodology, model evolution, limitations. |
| **[docs/METHODOLOGY.md](docs/METHODOLOGY.md)** | Statistical methods (Wilson, Clopper–Pearson, McNemar, bootstrap) + synonym handling — rationale + citations, for Paper 1. |
| **[docs/PUBLICATION_ASSETS.md](docs/PUBLICATION_ASSETS.md)** | Phase 7 · D6 — the Publication Asset Registry: every figure/table/result catalogued + the reproducible pipeline. |
| **[PARITY_AUDIT.md](PARITY_AUDIT.md)** | Phase 7 · A — demonstrated feature parity vs the original Streamlit app. |
| `README.md` | Original thesis README (historical context). |

## The one thing to get right: model & metric provenance

- **v5 / v5.2 is the primary production model everywhere.** The v5 **NT Custom
  Classifier** (BirdNET embeddings + custom head, `NT_Bird_BirdNET_Classifier.tflite`,
  25 classes) deployed via the **v5.2 multi-species SED** pipeline (`birddash/detection.py`).
- **BirdNET v2.4** is the comparison baseline.
- **The CNN (v2/v3, `nt_bird_cnn_best.keras`) is HISTORICAL** — kept intact for
  reproducibility, shown only in Model Evolution / Research. **Never present it as
  the production model. Never headline its leaky 92.7%.**
- **Three metric classes, never conflated:** *documented* (reported, untraceable —
  v5 0.98/0.99), *original evaluation* (recomputed from original saved artefacts —
  CNN, traceable), *independent reproduction* (a new experiment — v5 held-out
  eval). See MODEL_REGISTRY.md + DECISIONS.md D-12/D-13.
- **Do not fabricate or estimate metrics.**

## Current priorities (owner-set, in order)

1. Finish 100% feature parity with the original Streamlit app.
2. Improve the GIS experience & interactive map.
3. Improve UX/UI (polished environmental-intelligence platform feel).
4. Strengthen the annotation workflow (Listen & Label, reviewer workflow,
   confidence, provenance, expert verification).
5. (Paused) the independent v5 evaluation pipeline / retraining — **do not resume
   unless explicitly asked.**

## Operating rules

- **Do not commit, push, or delete files/endpoints** unless the owner explicitly asks.
- Keep `birddash` framework-free (no Streamlit/FastAPI imports; a test enforces this).
- Keep the API contract stable; DTOs are the contract (don't leak DataFrames/paths).
- No duplicate feature entry points (per-recording analysis lives in the Recording Workspace).
- Long background jobs get killed when a tool call returns — run persistent work
  outside a single invocation (see TECHNICAL_DEBT.md).

## Quick start

```bash
source birdenv/bin/activate
createdb birddash_dev            # first time; PostgreSQL 16 is installed locally
alembic upgrade head && python -m api.seed
uvicorn api.main:app --port 8000                 # API  → :8000/docs
cd frontend && npm install && npm run dev        # web  → :3000
# regenerate CNN eval artefacts:  python regenerate_cnn_evaluation.py
# (paused) v5 reproduction:        python evaluate_v5.py   → evaluation/reproduced/v5
```

## Repo map (detail in ARCHITECTURE.md)

```
birddash/        scientific core (config, audio, nt_model, birdnet, results, metrics, detection)
api/             FastAPI (main, settings, db, models, schemas, errors, security, seed,
                 repositories/, services/, routers/v1/)
frontend/        Next.js app (app/, components/, lib/)
alembic/         DB migrations
evaluation/      registry.json, original/cnn_*, reproduced/v5, thesis charts
models/          .keras (CNN), .tflite (v5), .npy (CNN test arrays), eval JSONs
training_data/   Xeno-canto dataset + dataset_metadata.csv (verified labels)
app.py, multi_species_section.py   original Streamlit app (still runs)
regenerate_cnn_evaluation.py, evaluate_v5.py   evaluation pipelines
```
