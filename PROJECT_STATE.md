# PROJECT_STATE.md — Avian Observatory

> Single source of truth for **current implementation status**. Read this first.
> Companion docs: [ARCHITECTURE.md](ARCHITECTURE.md) · [MODEL_REGISTRY.md](MODEL_REGISTRY.md) · [ROADMAP.md](ROADMAP.md) · [DECISIONS.md](DECISIONS.md) · [TECHNICAL_DEBT.md](TECHNICAL_DEBT.md) · [SCIENTIFIC_METHOD.md](SCIENTIFIC_METHOD.md)

**Last updated:** 2026-07-17

## What this project is

**Avian Observatory** is an environmental-intelligence platform for acoustic bird
monitoring in the Northern Territory (Australia). It began as a single-file
Streamlit thesis dashboard (PRT840, Charles Darwin University) and is being
migrated, phase by phase, into a production-quality platform.

**Vision (see [ROADMAP.md](ROADMAP.md) §Vision):** it is evolving from a
bird-classification dashboard into a **GIS-first environmental-intelligence
platform** for ecological research, biodiversity monitoring, and conservation
decision support — fusing acoustic AI, spatial data, and (over time)
environmental context. The four-stage GIS roadmap culminates in integrating
**TerraIQ**, a *separate* environmental-intelligence engine.

Current layered platform:

```
birddash (Python scientific core)  →  FastAPI (API + services + repositories)  →  Next.js (Avian Observatory web app)
                                       PostgreSQL (metadata)  +  filesystem (audio, detections, spectrograms)
```

The **original Streamlit app still runs** (`app.py`, `multi_species_section.py`)
and is the functional reference for parity. Nothing about it was broken during
the migration — the ML logic was extracted into `birddash`, which both the
Streamlit app and the API import.

## How to run it (local dev)

```bash
# 0. Python env
source birdenv/bin/activate                      # or: pip install -r requirements-api.txt

# 1. Database (PostgreSQL 16 via Homebrew is already installed locally)
createdb birddash_dev                            # first time only
alembic upgrade head
python -m api.seed                               # org, species, sites, models, recordings

# 2. Backend API
uvicorn api.main:app --port 8000                 # http://localhost:8000/docs

# 3. Frontend
cd frontend && npm install && npm run dev        # http://localhost:3000

# 4. (still available) original Streamlit app
streamlit run app.py
```

Config: `frontend/.env.local` holds `NEXT_PUBLIC_API_BASE` and
`NEXT_PUBLIC_MAPTILER_KEY` (gitignored). API config via `BIRDDASH_*` env vars
(see `api/settings.py`, `birddash/config.py`).

## Completed phases (see ROADMAP.md for detail)

- **Phase 1 — Stabilise & prepare.** Fixed the upload bug, centralised config
  (`birddash/config.py`, portable paths), pinned deps, added golden-file tests.
- **Phase 2 — Extract ML core.** Created the framework-agnostic `birddash`
  package (no Streamlit). Golden tests prove identical outputs.
- **Phase 3a — FastAPI + Postgres.** Resource-oriented read API, SQLAlchemy +
  Alembic metadata store, RFC 9457 errors, cursor pagination, auth scheme (dev
  stub), seed from filesystem.
- **Phase 4 — Next.js frontend foundation.** App Router + TS + Tailwind v4 +
  shadcn-style UI + TanStack Query + MapLibre/MapTiler. "Observatory" design
  system. App shell, homepage, dashboard, map, recordings, species.
- **Phase 5 — Feature parity.** Migrated BirdNET detections, multi-species SED,
  Listen & Label, biodiversity, spectrogram, audio, charts, exports.
- **Phase 6 — Refinement & IA redesign.** Consolidated the fragmented UI into a
  Recording Workspace (Overview / Model Comparison / Events & Labelling), trimmed
  navigation, fixed the model-comparison logic (verified-label ground truth),
  server-rendered spectrograms.
- **Model reframe & scientific integrity.** Made the **v5 / v5.2** pipeline the
  primary production model everywhere; the CNN became documented history (kept
  intact, un-deprecated). Built the **model registry** and separated
  *documented* vs *original-evaluation* vs *independent-reproduction* metrics.
  Regenerated CNN evaluation artefacts from saved arrays; built and ran the v5
  reproducible held-out evaluation.

## Current status snapshot

| Area | Status |
|---|---|
| `birddash` core | ✅ Stable, framework-free, golden-tested (4/4) |
| FastAPI backend | ✅ Read + write (uploads) + analysis + registry; 10/10 API tests |
| PostgreSQL metadata | ✅ `birddash_dev`, Alembic-migrated, seeded |
| Next.js frontend | ✅ Builds; dashboard, map, recordings workspace, species, model performance, biodiversity |
| Feature parity w/ Streamlit | ✅ Believed 100% (re-verify against §"Known gaps") |
| Model registry | ✅ `evaluation/registry.json` + `/api/v1/models/registry` |
| CNN evaluation | ✅ Verified/traceable (`evaluation/original/cnn_{v2,v4}`); now with Clopper–Pearson + bootstrap CIs |
| v5 independent reproduction | ✅ Completed (`evaluation/reproduced/v5`), acc 0.882 [0.84–0.92] / AUROC 0.980 |
| Statistical rigour (Phase 7·B) | ✅ Wilson/Clopper–Pearson/McNemar/bootstrap in `birddash/statistics.py`; synonym-aware matching (`birddash/taxonomy.py`); provenance + CIs on every metric; [docs/METHODOLOGY.md](docs/METHODOLOGY.md). **McNemar: NT-vs-BirdNET lead not significant at n=23** |
| GIS foundation (Phase 7·C) | ✅ Coordinate-provider (`api/services/geospatial.py`, `coordinate_precision`); map species/confidence filters + layer toggles (`/map/sites`); inert environmental seam (`/environmental/*`); PostGIS-ready path documented. Longitude not a blocker |
| Platform polish (Phase 7·E) | ✅ About/onboarding drawer (closes parity G1); placeholder nav behind `FEATURES.roadmapModules` flag; decorative bell/search removed; consistent loading/empty/error states; a11y + chart-legend/caption pass |
| Research foundation (Phase 7·D) | ✅ Publication Asset Registry (`evaluation/asset_registry.json`, 53 assets); publication figures/tables (`evaluation/paper1/`); `verify_metric_provenance.py` 9/9 (app == artefact); registry is the single authoritative source. See [docs/PUBLICATION_ASSETS.md](docs/PUBLICATION_ASSETS.md) |
| Stabilization (parser fix) | ✅ Fixed a name-truncation collision in `parse_birdnet_csv` (Barking Owl→"Masked Owl", Black Kite→"Whistling Kite"); model was correct (>0.99), parser mislabelled. Regenerated 17 artefacts; **NT comparison 21/23 → 23/23**. Regression tests `tests/test_detection_parsing.py` (7/7). Only 2 primaries changed; no correct→wrong regressions |
| Auth / multi-tenancy | ⏸ Designed, dev-stubbed (permissive) |
| Deployment | ⏳ Local only (no Docker/CI yet) |

## Current priorities (set by the project owner, in order)

1. **Finish 100% feature parity** with the original Streamlit app (verify nothing lost).
2. **Improve the GIS experience** and interactive map.
3. **Improve overall UX/UI** — make it feel like a polished environmental-intelligence platform.
4. **Strengthen the annotation workflow** — Listen & Label, reviewer workflow, confidence, provenance, expert verification.
5. **(Deferred, do not resume unless asked)** the independent v5 evaluation pipeline / retraining.

## Known gaps / things to verify for "100% parity"

- **Overarching "About this dashboard" help** — Streamlit had a big explanatory
  expander; the new app has per-section info popovers but no single About/onboarding drawer.
- Re-check the original `app.py` feature list against the workspace tabs (see
  SCIENTIFIC_METHOD.md §comparison and the git history of `app.py`).
- The CNN per-segment "NT predictions" view is available only via the historical
  `/nt-predictions` endpoint; the production per-recording NT view is the v5.2 SED events.

## Current UI/UX issues (summary; full list in TECHNICAL_DEBT.md)

- ✅ **About / onboarding** — resolved (Phase 7·E): accessible drawer, first-run
  auto-open + Help button.
- ✅ **Decorative top-bar bell / search** — removed (Phase 7·E).
- ✅ **Placeholder "Roadmap" nav** — hidden behind a feature flag (Phase 7·E).
- **No command palette (⌘K)** and **no mobile sidebar drawer** — desktop-first (open).
- **Listen & Label persistence is client-side only** (localStorage) — no reviewer
  workflow / expert verification yet (priority #4).
- **Map is site-level, not per-recording** (longitude missing) — now behind the
  coordinate-provider abstraction, labelled *approximate*, and upgrades
  automatically when precise GPS arrives. Species/confidence filters + layer
  toggles are in place (Phase 7·C); deck.gl overlays remain future.
- **"Roadmap" nav modules** (Behaviour, Migration, Pelican, Environmental, Sensors)
  are placeholders.

## Known issues (see TECHNICAL_DEBT.md for the full list)

- **Per-recording longitude missing** — `download_dataset_v2.py` captured only
  latitude from Xeno-canto (`lng` empty). The map therefore uses **seeded NT
  monitoring sites** with **illustrative** recording→site associations (labelled
  as sample data in the UI). Real per-recording GPS needs a Xeno-canto re-fetch.
- **Dead frontend components** not yet removed: `nt-model-panel`, `birdnet-panel`,
  `multi-species-panel`, `species-card`. Removal awaits explicit approval.
- **Legacy endpoint** `/api/v1/models/research-metrics` superseded by
  `/models/registry` (frontend uses registry). Kept for now.
- **Long background jobs get killed** in this environment — the v5 reproduction
  must be run as a persistent process, not inside a single tool call.

## Immediate next tasks (when work resumes)

1. Re-audit parity against original Streamlit `app.py`; close any residual gaps
   (esp. the About/onboarding content).
2. GIS: richer map (layer toggles, species/confidence filters, deck.gl overlays,
   fix per-recording geo once longitude is recovered).
3. UX polish: command palette (⌘K), mobile sidebar drawer, job/notification bell
   wiring, empty/loading states, dark-mode pass.
4. Annotation workflow: persist labels server-side (annotations resource +
   table), reviewer/expert-verification states, inter-annotator agreement,
   provenance on each label.

## Important operating rules for the next Claude

- **Do not commit, push, or delete files/endpoints** unless the owner explicitly asks.
- **Do not fabricate or estimate metrics.** Keep documented vs verified vs reproduced strictly separate (see DECISIONS.md D-12/D-13).
- **Do not resurface the old CNN as the production model.** v5/v5.2 is primary; CNN is historical (kept intact).
- **Do not resume retraining / v5 reproduction** unless explicitly asked.
