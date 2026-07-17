# Avian Observatory

![release](https://img.shields.io/badge/release-v1.0.0-2e7d63)
![python](https://img.shields.io/badge/python-3.13-3776AB)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688)
![Next.js](https://img.shields.io/badge/Next.js-16-000000)
![tests](https://img.shields.io/badge/tests-21%20passing-2e7d63)
![license](https://img.shields.io/badge/license-academic%20research-lightgrey)

**An environmental-intelligence platform for AI-powered acoustic bird monitoring in the Northern Territory, Australia.**

*Originating from PRT840 IT Thesis · Master of Data Science · Charles Darwin University · Supervisor: Dr. Md Rafiqul Islam.*

Avian Observatory identifies Northern Territory bird species from audio using
**region-specific AI**, then fuses those detections with spatial and biodiversity
context — moving beyond *"what species is this?"* toward *"where, when, and what
does it mean for conservation?"* It began as a single-file Streamlit thesis
dashboard and was migrated, phase by phase, into a layered platform with a
framework-free scientific core, a FastAPI service, and a Next.js web app.

---

## Why this project exists

BirdNET (Kahl et al., 2021) is the global gold standard for acoustic bird ID, but
its training skews to the Northern Hemisphere. On Northern Territory species it
routinely **misidentifies** local birds — e.g. Azure Kingfisher → "Eurasian
Treecreeper", Diamond Dove → "New Zealand Bellbird" — often with high confidence.
This project builds NT-specific classifiers that outperform BirdNET on NT species,
and a platform to demonstrate, evaluate, and operationalise that finding
**reproducibly and honestly**.

---

## Architecture

```
Next.js web app (frontend/)                         ← dashboard · map · workspace · species · biodiversity · models
        │  REST/JSON (Pydantic DTOs are the contract)
FastAPI service (api/)   routers → services → repositories
        │                          │
PostgreSQL (metadata)     Filesystem (audio · detections · spectrograms)
        │
birddash (scientific core, framework-free — no Streamlit/FastAPI)
   config · audio · nt_model · birdnet · detection · results · metrics · statistics · taxonomy
        ▲
        └─ also imported by the original Streamlit app (app.py) — kept runnable as the parity reference
```

`birddash` owns all science; the API is a stable resource contract; the frontend
is a thin modern client. Full detail: **[ARCHITECTURE.md](ARCHITECTURE.md)**.

---

## Key features

- **Region-specific detection** — the **NT Custom Classifier (v5)** (BirdNET v2.4
  embeddings + a custom NT head) deployed via the **v5.2 multi-species
  sound-event-detection** pipeline; per-recording species + timestamps.
- **Honest model comparison** — NT model vs global BirdNET on identical recordings,
  synonym-aware, with confidence intervals and a paired significance test.
- **Interactive map** — monitoring sites with species/confidence filters (GIS-first;
  coordinate-provider abstraction ready for precise per-recording GPS).
- **Recording workspace** — audio, server-rendered mel spectrogram, model
  comparison, and a **Listen & Label** annotation workflow.
- **Biodiversity metrics** — Shannon, Simpson, species richness across the library.
- **Reproducible evaluation + Publication Asset Registry** — every figure, table,
  and metric traceable to a persisted artefact (for Paper 1).
- **Scientific-integrity tooling** — documented-vs-verified-vs-reproduced metric
  provenance, Wilson / Clopper–Pearson / McNemar / bootstrap intervals, sourced
  synonym handling.

---

## Model performance & scientific integrity

Three strictly-separated metric classes (never conflated — see
[MODEL_REGISTRY.md](MODEL_REGISTRY.md)):

| Model | Metric | Provenance |
|---|---|---|
| Custom CNN v2/v3 | 92.7% accuracy (**segment-level — inflated by data leakage**) | *original evaluation (traceable)* |
| Custom CNN v4 | **66.6%** accuracy (recording-level — the honest number) | *original evaluation (traceable)* |
| **NT Custom Classifier v5** | AUPRC 0.98 / AUROC 0.99 | *documented — **not** independently verified* |
| **NT Custom Classifier v5** | accuracy **0.88** [0.84–0.92], macro-F1 0.83, AUROC 0.98 | *independent reproduction (recording-level held-out)* |

**Operational comparison (live, same 23 recordings, synonym-aware):**
**NT v5.2 SED 23/23 (100%)** vs **BirdNET v2.4 18/23 (78%)**. The paired **exact
McNemar** test gives **p ≈ 0.063 — not statistically significant** at this small
sample (direction favours the NT model; more labelled recordings are needed to
confirm it). Methods + citations: **[docs/METHODOLOGY.md](docs/METHODOLOGY.md)**.

> **The leakage lesson (v2→v4)** — evaluating on segments that share a recording
> with training segments inflates accuracy from an honest 66.6% to a misleading
> 92.7%. All honest evaluation splits at the *recording* level. This is the
> project's pivotal scientific result; the leaky 92.7% is **never** headlined.

### Reproducibility

All metrics are recomputed from persisted artefacts — no hand-entered numbers.
`verify_metric_provenance.py` asserts the application and the publication assets
share one source (currently 9/9 checks passing).

```bash
python regenerate_cnn_evaluation.py       # CNN metrics + CIs from saved arrays
python evaluate_v5.py --from-saved         # v5 held-out metrics + CIs (no retraining)
python persist_comparison_artifact.py      # snapshot the live NT-vs-BirdNET comparison
python generate_publication_assets.py      # colourblind-safe figures + CSV/LaTeX tables → evaluation/paper1/
python build_asset_registry.py             # Publication Asset Registry (evaluation/asset_registry.json)
python verify_metric_provenance.py         # assert app == artefacts
```

See **[docs/PUBLICATION_ASSETS.md](docs/PUBLICATION_ASSETS.md)**.

---

## Quick start (local development)

**Prerequisites:** Python 3.13, Node 18+, PostgreSQL 16, `ffmpeg`. Model artefacts
(`.tflite`/`.keras`) and datasets are gitignored (too large / not redistributable)
— retrain via the scripts or obtain from the project owner.

```bash
# 1. Python core + API
python3 -m venv birdenv && source birdenv/bin/activate
pip install -r requirements-api.txt        # pulls in requirements.txt (birddash core)

# 2. Database
createdb birddash_dev                       # first time (PostgreSQL 16)
alembic upgrade head && python -m api.seed

# 3. Backend API  →  http://localhost:8000/docs
uvicorn api.main:app --port 8000

# 4. Frontend  →  http://localhost:3000
cd frontend && npm install && npm run dev

# 5. (still runs) the original Streamlit thesis app / parity reference
streamlit run app.py
```

Config: `frontend/.env.local` holds `NEXT_PUBLIC_API_BASE` (default
`http://localhost:8000`) and `NEXT_PUBLIC_MAPTILER_KEY` (both gitignored). API
config via `BIRDDASH_*` env vars (`api/settings.py`). Full run notes:
**[PROJECT_STATE.md](PROJECT_STATE.md)**.

### API (selected endpoints, under `/api/v1`)

`GET /recordings`, `/recordings/{id}` (+ `/audio`, `/spectrogram`, `/detections`,
`/multi-species`), `POST /recordings/upload`, `GET /species`, `/sites`,
`/map/sites`, `/biodiversity`, `/models/comparison`, `/models/registry`,
`/environmental/*` (inert scaffold). Interactive docs at `/docs`.

---

## Repository structure

```
birddash/        scientific core (config, audio, nt_model, birdnet, detection, results, metrics, statistics, taxonomy)
api/             FastAPI (main, settings, db, models, schemas, security, seed, repositories/, services/, routers/v1/)
frontend/        Next.js app (app/, components/, lib/)
alembic/         database migrations
evaluation/      registry.json, asset_registry.json, original/cnn_*, reproduced/v5, paper1/ (figures + tables), thesis charts
docs/            METHODOLOGY.md, PUBLICATION_ASSETS.md
tests/           golden parity + detection-parsing + API tests
app.py, multi_species_section.py            original Streamlit app (parity reference, still runs)
evaluate_v5.py, regenerate_cnn_evaluation.py, generate_publication_assets.py,
build_asset_registry.py, verify_metric_provenance.py, persist_comparison_artifact.py   reproducible pipeline
models/          .keras/.tflite/.npy model artefacts (gitignored)
training_data/, sample_audio/               Xeno-canto dataset + demo audio (gitignored)
```

## Documentation

| Doc | Purpose |
|---|---|
| [PROJECT_STATE.md](PROJECT_STATE.md) | Current status, how to run, priorities |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Full technical architecture + API contract |
| [MODEL_REGISTRY.md](MODEL_REGISTRY.md) | Every model, rationale, metric provenance |
| [SCIENTIFIC_METHOD.md](SCIENTIFIC_METHOD.md) | Dataset, evaluation & comparison methodology |
| [docs/METHODOLOGY.md](docs/METHODOLOGY.md) | Statistical methods + citations (Paper 1) |
| [docs/PUBLICATION_ASSETS.md](docs/PUBLICATION_ASSETS.md) | Publication Asset Registry |
| [ROADMAP.md](ROADMAP.md) · [DECISIONS.md](DECISIONS.md) · [TECHNICAL_DEBT.md](TECHNICAL_DEBT.md) · [PARITY_AUDIT.md](PARITY_AUDIT.md) | Roadmap, decisions, debt, parity |

---

## Species coverage

25 Northern Territory species (24 core + Red Goshawk): Azure Kingfisher, Barking
Owl, Black Kite, Blue-winged Kookaburra, Bush Stone-curlew, Channel-billed Cuckoo,
Diamond Dove, Galah, Gouldian Finch, Great Bowerbird, Helmeted Friarbird, Hooded
Parrot, Laughing Kookaburra, Magpie Goose, Masked Owl, Partridge Pigeon, Pheasant
Coucal, Rainbow Bee-eater, Red Goshawk, Red-tailed Black-Cockatoo, Sulphur-crested
Cockatoo, Tawny Frogmouth, Torresian Crow, Whistling Kite, Willie Wagtail.
Several are threatened/near-threatened (e.g. Gouldian Finch, Partridge Pigeon, Red
Goshawk, Bush Stone-curlew, Masked Owl, Hooded Parrot).

## Data source

Training audio is sourced from **Xeno-canto** (https://xeno-canto.org) under its
academic/research sharing policy; recordists are attributed in the metadata. The
dataset spans ~1,300 recordings across the 25 species (accessed Feb–Apr 2026).
Note: per-recording longitude was not captured in the download, so spatial views
use approximate site-level locations (labelled as such in the UI).

## Deployment

**Prepared, not yet deployed** (no cloud resources exist). The repository ships
production deployment configuration — `Dockerfile`, `.dockerignore`, `heroku.yml`,
`Procfile`, `app.json`, and env-driven `DATABASE_URL`/CORS handling — for the
topology **Vercel (frontend) + Heroku Container Stack (FastAPI + TensorFlow +
BirdNET) + Heroku Postgres**. The Container Stack is used because the ~2.3 GB
TensorFlow stack exceeds Heroku's 500 MB buildpack slug limit; no functionality is
reduced (a `standard-2x` dyno is recommended for TensorFlow headroom). Full
runbook, cost estimate (~$55/mo), and the models-are-gitignored caveat:
**[DEPLOYMENT.md](DEPLOYMENT.md)**. The frontend reads
`NEXT_PUBLIC_API_BASE` from the environment, so it is Vercel-configurable with no
code change.

---

## Key references

- Kahl, S., et al. (2021). BirdNET: A deep learning solution for avian diversity monitoring. *Ecological Informatics*, 61.
- Ghani, B., et al. (2023). Global birdsong embeddings enable superior transfer learning for bioacoustic classification. *Scientific Reports*, 13.
- Roberts, D. R., et al. (2017). Cross-validation strategies for data with temporal, spatial, hierarchical, or phylogenetic structure. *Ecography*, 40(8).
- Wilson (1927); Clopper & Pearson (1934); McNemar (1947); Efron & Tibshirani (1993) — statistical methods, cited in [docs/METHODOLOGY.md](docs/METHODOLOGY.md).

## License and contact

Academic research project submitted in partial fulfilment of the Master of Data
Science at Charles Darwin University; made available under CDU's academic policy
for student research outputs.

**Author:** Harsh Rastogi · **Group 33:** Jisan, Rafel, Tahmid · **Supervisor:**
Dr. Md Rafiqul Islam · **Institution:** Charles Darwin University.
