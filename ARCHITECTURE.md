# ARCHITECTURE.md — Avian Observatory

> Complete technical architecture. Companion: [PROJECT_STATE.md](PROJECT_STATE.md) · [MODEL_REGISTRY.md](MODEL_REGISTRY.md) · [DECISIONS.md](DECISIONS.md)

## 1. Layered overview

```
┌──────────────────────────────────────────────────────────────────────┐
│  Clients                                                               │
│   • Next.js web app (frontend/)  • (future) mobile, gov dashboards     │
└───────────────┬────────────────────────────────────────────────────────┘
                │ REST/JSON over HTTP (contract = Pydantic DTOs)
┌───────────────▼────────────────────────────────────────────────────────┐
│  FastAPI (api/)                                                          │
│   routers → services → repositories                                     │
│   cross-cutting: settings, errors (RFC 9457), pagination, security      │
└───────────────┬───────────────────────────────┬────────────────────────┘
                │                                │
     ┌──────────▼───────────┐        ┌───────────▼─────────────┐
     │ PostgreSQL (metadata) │        │ Filesystem (artefacts)  │
     │ SQLAlchemy + Alembic  │        │ audio, detections, specs│
     └───────────────────────┘        └─────────────────────────┘
                │
┌───────────────▼────────────────────────────────────────────────────────┐
│  birddash (scientific core, framework-agnostic — NO Streamlit/FastAPI)  │
│   config · audio · nt_model · birdnet · results · metrics · detection   │
└─────────────────────────────────────────────────────────────────────────┘
        ▲
        │  (also imported directly by the original Streamlit app: app.py)
```

**Guiding principle:** `birddash` owns all science; the API is a stable
resource contract; the frontend is a thin, modern client. The API never leaks
internal shapes (DataFrames, file paths) — Pydantic DTOs are the contract.

## 2. `birddash/` — scientific core (Python, no framework)

| Module | Responsibility |
|---|---|
| `config.py` | Single source of truth for paths + pipeline constants. `BASE_DIR` derived from the package location (portable); every path env-overridable via `BIRDDASH_*`. |
| `audio.py` | `generate_spectrogram`, `render_spectrogram_png` (server-side mel spectrogram, viridis), `extract_audio_window` (WAV bytes for a detection window). |
| `nt_model.py` | **Historical** NT CNN (v2/v3, `nt_bird_cnn_best.keras`, 24 classes): `load_model`, `load_label_map`, `predict`. Kept intact for reproducibility; NOT the production model. |
| `birdnet.py` | `analyze_upload` — global BirdNET analysis of a single recording. |
| `detection.py` | **Production** multi-species SED (v5.2): dual-threshold, sliding-window detection over the **v5 custom classifier** (`NT_Bird_BirdNET_Classifier.tflite`, 25 classes). `run_detection(...)` orchestrates BirdNET-Analyzer (subprocess, for process isolation) → parse → primary detection → dual threshold → merge → JSON. |
| `results.py` | Load/aggregate BirdNET result CSVs. |
| `metrics.py` | Biodiversity indices: `shannon_index`, `simpson_index`. |
| `statistics.py` | **Small-sample statistics** for honest metric reporting: Wilson & Clopper–Pearson intervals, exact McNemar paired test, percentile bootstrap. Each cited; see [docs/METHODOLOGY.md](docs/METHODOLOGY.md). |
| `taxonomy.py` | **Species-name canonicalisation + sourced synonyms** (e.g. IOC "Bush Thick-knee" = "Bush Stone-curlew"); `same_species` powers synonym-aware matching. Deliberately conservative (cited entries only). |

The CLI `multi_species_detector_v5_1.py` is a thin wrapper over
`birddash.detection`. Golden-file tests (`tests/`) pin NT-model output.

## 3. `api/` — FastAPI (layered: routers → services → repositories)

**App:** `api/main.py` (app factory, CORS for localhost:3000, request-id
middleware, RFC 9457 handlers, OpenAPI security schemes, mounts `/api/v1`).

**Cross-cutting:**
- `settings.py` — pydantic-settings, `BIRDDASH_*` env (DATABASE_URL, auth_mode, CORS, pagination).
- `db.py` — SQLAlchemy 2.0 engine/session + `Base`, `get_db` dependency.
- `errors.py` — RFC 9457 Problem+JSON; typed domain errors (`NotFoundError`, `ValidationError`, `ConflictError`, …); stable machine-readable `code`s + request id.
- `pagination.py` — opaque base64 **keyset** cursor.
- `security.py` — `Principal` (org + roles + scopes); `require_scope(...)`; **dev-stub** auth (permissive; `X-Debug-Role` header) with a real OIDC path designed but not implemented; roles→scopes in `ROLE_SCOPES`.

**ORM models (`api/models.py`, Postgres):** `Organisation`, `Site`, `Sensor`,
`Species`, `Model`, `Recording`, `Analysis`, `Job`. UUID PKs, string status/type
fields (not DB enums), timezone-aware timestamps, `organisation_id` on tenant
resources (multi-tenancy-ready).

**Repositories (`api/repositories/`)** — the storage seam:
- `recordings.py`, `species.py`, `sites.py` → Postgres.
- `detections.py` → **filesystem** (reads BirdNET result CSVs). *This is the adapter that changes in the Phase-6 blob migration.*

**Services (`api/services/`)** — use-cases + DTO translation + authorization:
- `recordings.py`, `species.py`, `sites.py`, `jobs.py` (async job model + `run_now` executor stub).
- `detections.py` (BirdNET detections), `analysis.py` (NT CNN predictions [historical] + v5.2 multi-species [production], both filesystem-cached), `biodiversity.py` (Shannon/Simpson/richness), `uploads.py` (upload → BirdNET analysis → register recording).
- `model_comparison.py` (data-driven NT-v5-vs-BirdNET on the same recordings, verified labels; **synonym-aware matching**, **Wilson 95% intervals** on each rate, **exact McNemar** paired test, and a `provenance` block — see §7a), `research_metrics.py` (legacy), `model_registry.py` (**the registry** — see §7).

**Routers (`api/routers/v1/`):** `meta` (health/version), `recordings`
(list/detail/audio/spectrogram/detections/nt-predictions/multi-species/upload),
`species`, `sites`, `biodiversity`, `models` (list/comparison/research-metrics/registry), `jobs`.

## 4. API contract (selected endpoints, all under `/api/v1`)

| Method | Path | Purpose |
|---|---|---|
| GET | `/recordings` | Cursor-paginated list (`?site=&cursor=&limit=`) |
| GET | `/recordings/{id}` | Recording metadata (+ hypermedia `audio_url`, `detections_url`) |
| GET | `/recordings/{id}/audio` | Streamed audio (Range) |
| GET | `/recordings/{id}/spectrogram` | Server-rendered mel spectrogram PNG (cached) |
| GET | `/recordings/{id}/detections?min_confidence=` | BirdNET (global) detections |
| GET | `/recordings/{id}/multi-species?…params` | **Production v5.2 SED** (cached or re-run with params) |
| GET | `/recordings/{id}/nt-predictions` | **Historical** NT CNN per-segment predictions |
| POST | `/recordings/upload` | Upload + BirdNET analysis + register |
| GET | `/species`, `/species/{id}` | NT species catalog (enriched: scientific name, conservation) |
| GET | `/sites`, `/sites/{id}` | NT monitoring sites (map) |
| GET | `/map/sites?min_confidence=&species=` | Sites as **filterable map points** (species present, `coordinate_precision`, synonym-aware species filter) |
| GET | `/environmental/layers` | Environmental map layers — **inert scaffold** (`available=false`; §11) |
| GET | `/environmental/context?site_id=` | Environmental context for a site — **inert scaffold** |
| GET | `/biodiversity?min_confidence=` | Overall + per-recording indices |
| GET | `/models/comparison` | NT-v5-vs-BirdNET correct-detection rate (same recordings, verified labels); returns `nt_interval`/`birdnet_interval` (Wilson), `mcnemar` (paired test), `provenance` |
| GET | `/models/registry` | **Model registry** (see §7); each `per_species` carries Clopper–Pearson `precision_ci`/`recall_ci` + `reliable`; each `metrics` carries bootstrap `macro_intervals` |
| GET | `/jobs`, `/jobs/{id}` | Async job tracking |

Contract types are hand-authored in `frontend/lib/api/types.ts` (production
approach: generate from `/openapi.json`).

## 5. `frontend/` — Next.js (Avian Observatory web app)

Next.js 16 (App Router) · React 19 · TypeScript · Tailwind CSS v4 · TanStack
Query · MapLibre GL + MapTiler · wavesurfer.js · recharts · next-themes.

```
app/
  page.tsx                     public homepage (marketing)
  layout.tsx                   RootLayout: Inter/JetBrains fonts, Providers (Query + theme)
  (platform)/
    layout.tsx                 AppShell (Sidebar + TopBar)
    dashboard/                 Territory Dashboard (aggregate intelligence — no map)
    map/                       Interactive Map (site drill-down)
    recordings/[id]/           Recording Workspace (tabs: Overview / Model Comparison / Events & Labelling)
    species/                   Species Explorer (catalog + conservation + reference recordings)
    biodiversity/              Biodiversity (indices + cross-file comparison)
    models/                    Model Performance (Comparison / Research Metrics / Model Evolution)
    label/, analysis/multi-species/   → redirect into the Recording Workspace (no duplicate entry points)
    analysis/behaviour, migration, pelican, environment, sensors   → "Roadmap" placeholders
components/  ui/ layout/ map/ audio/ spectrogram/ data/ domain/
lib/  api/(client,types,hooks) config providers utils csv ground-truth hooks/
```

**Design system ("Observatory"):** CSS-variable tokens in `app/globals.css`;
deep teal + slate, NT earth-tone accents; light default + night-observatory dark;
field-notebook cues (`.specimen-label`, specimen metadata cards). Class-based
dark mode via next-themes.

**State:** server state = TanStack Query; ephemeral UI state = component/`useState`
(+ localStorage for Listen & Label); URL/query for filters. No Redux.

## 6. GIS architecture

- **Coordinate provider (the seam):** `api/services/geospatial.py` is the single
  place a recording's location is resolved. `resolve_location(rec, site)` prefers
  **precise** per-recording GPS (`Recording.latitude/longitude`, added nullable in
  Phase 7 · C) and falls back to the **approximate** site location, tagging every
  point with `coordinate_precision` (precise | approximate | unknown) + source.
  Real per-recording GPS "slots in" later (a Xeno-canto re-fetch populates the
  columns) with **no caller/DTO/frontend change**. Nothing fabricates coordinates
  — approximate points are explicitly the site's location, labelled as such (D-25).
- **Data:** `Site` (lat/lon) is the map anchor; `Recording.site_id` associates
  recordings to sites. Longitude is still missing per recording, so points are
  approximate (site-level) and the UI says so.
- **Map endpoint:** `GET /api/v1/map/sites?min_confidence=&species=` returns sites
  as filterable points with the species detected there (synonym-aware), so the map
  filters by species + confidence.
- **Rendering:** `components/map/map-view.tsx` — MapLibre GL + MapTiler basemap
  (`dataviz`/`dataviz-dark`); site markers sized by recording count, non-matching
  sites dimmed under a species filter, click → drill-down. The `/map` page adds a
  species dropdown, confidence slider, and layer toggles (a disabled "Environmental
  layers" toggle wired to the inert environmental boundary — §11).
- **PostGIS-ready path (not activated):** `Site`/`Recording` use plain lat/lon
  columns today. When spatial queries are needed (bbox/temporal joins,
  environmental-layer overlays), these become PostGIS geometry columns **behind the
  same `geospatial` service** — no infra is carried until then. This unlocks GIS
  Stages 2–3.
- **Future:** deck.gl overlays, PostGIS spatial queries, environmental layers;
  precise per-recording GPS after a Xeno-canto re-fetch (upgrades automatically).

## 7. Model registry (future-proof)

`evaluation/registry.json` is the **single source of truth for model versions**.
Each entry: `key, name, version, family, status (production|baseline|historical),
description, documented (or null), evaluations[]`. `api/services/model_registry.py`
resolves each evaluation's metrics from its `artefact_dir`.

Three strictly-separated concepts (never conflated — see DECISIONS.md D-13):
- **documented** — reported values with NO traceable artefact (v5 thesis AUPRC/AUROC).
- **original_evaluation** — metrics reproduced from ORIGINAL saved artefacts (CNN, traceable).
- **independent_reproduction** — a NEW experiment (v5 held-out retrain).

**Adding a future model (v6, v7…) = add a registry entry + drop artefacts under
`evaluation/original/<key>/` or `evaluation/reproduced/<key>/`. No code change.**

## 7a. Statistics & provenance (Phase 7 · Workstream B)

Every reported metric carries its sampling uncertainty and an explicit provenance
tag; the methods live in the framework-free core (`birddash/statistics.py`) so the
API and the offline evaluation scripts share one implementation. Rationale and
citations for each method: [docs/METHODOLOGY.md](docs/METHODOLOGY.md); the driving
decisions: DECISIONS.md **D-23** (uncertainty on every metric) and **D-24**
(synonym-aware matching).

- **Operational comparison** (`live_comparison`): Wilson 95% intervals per rate +
  exact McNemar paired test (the models share recordings, so the rates are paired).
- **Held-out evaluations** (`original_evaluation`, `independent_reproduction`):
  Clopper–Pearson exact CIs per class (with a *derived* reliability flag — CI width
  > 0.5, not a fixed minimum n) + percentile-bootstrap CIs for accuracy/macro-F1,
  resampled at the recording level. Computed from persisted arrays with **no
  retraining** (`regenerate_cnn_evaluation.py`, `evaluate_v5.py --from-saved`).
- **Documented** values (v5 0.98/0.99) carry no interval and are always shown
  behind a "Documented · not verified" badge — no evaluation sample underlies them.

DTOs (`api/schemas.py`): `IntervalOut`, `McNemarOut`, and additive CI/provenance
fields on `ModelComparisonOut`, `PerSpeciesMetric`, and `ModelMetrics`. The
frontend mirrors the synonym table in `lib/ground-truth.ts` (server is source of
truth; keep in sync).

## 8. Evaluation pipeline

- `regenerate_cnn_evaluation.py` — recomputes CNN v2/v3/v4 metrics from the
  original saved test arrays (`models/y_test_{probs,true}{,_v3,_v4}.npy`) →
  `evaluation/original/cnn_<ver>/` (metrics.json, confusion_matrix.csv, roc/pr curves).
- `evaluate_v5.py` — reproducible recording-level held-out evaluation of the v5
  approach: seeded split, retrain on train split (BirdNET-Analyzer, augmentation
  disabled), evaluate held-out recordings → `evaluation/reproduced/v5/` (metrics,
  probabilities/predictions/labels npy, confusion, roc/pr curves, split.json, eval classifier).
  `--from-saved` recomputes metrics + CIs from the persisted arrays **without retraining**.
- **Statistics (Phase 7·B):** `regenerate_cnn_evaluation.py` and `evaluate_v5.py`
  emit Clopper–Pearson per-class CIs + bootstrap macro CIs via `birddash.statistics`.
- **Publication pipeline (Phase 7·D):** `persist_comparison_artifact.py` snapshots
  the live comparison; `generate_publication_assets.py` renders colourblind-safe
  figures (PNG+PDF) + tables (CSV+LaTeX) into `evaluation/paper1/` from the
  persisted artefacts; `build_asset_registry.py` generates the **Publication Asset
  Registry** (`evaluation/asset_registry.json`); `verify_metric_provenance.py`
  asserts every displayed metric traces to a reproducible artefact (app == artefact).
  The hardcoded `generate_charts.py` is deprecated and quarantined. See
  [docs/PUBLICATION_ASSETS.md](docs/PUBLICATION_ASSETS.md).

## 9. Annotation workflow (current)

Listen & Label lives in the Recording Workspace (Events & Labelling tab):
multi-species events → per-event **Listen** (plays the exact 3s window via a
segment player), **Confirm / Reject / Not-sure**, pagination, annotator name,
coverage progress, CSV export. **Persistence is client-side (localStorage)** —
server-side annotations (reviewer workflow, expert verification, provenance,
inter-annotator agreement) are the next major annotation task (priority #4).

## 10. Data & storage locations

- `training_data/` — full Xeno-canto dataset (1303 recordings, 25 species folders) + `dataset_metadata.csv` (verified labels).
- `sample_audio/` — recordings surfaced in the app (seeded into the DB).
- `models/` — `.keras` (CNN), `.tflite` (v5 classifier), `.npy` (CNN test arrays), eval JSONs.
- `birdnet_results2/` — global BirdNET result CSVs (per recording).
- `detections/` — cached v5.2 SED JSON, NT-prediction JSON, spectrogram PNGs (gitignored).
- `evaluation/` — `registry.json`, `original/cnn_*`, `reproduced/v5`, thesis charts (PNGs).
- `spectrograms/label_map.json` — CNN 24-class index→name map.

## 11. Environmental intelligence layer & TerraIQ (future)

Avian Observatory is evolving into a GIS-first environmental-intelligence platform
(see [ROADMAP.md](ROADMAP.md) — the four-stage GIS roadmap). Stages 2–3 add
environmental context (weather, fire, vegetation, protected areas, IPAs, land
cover, elevation, hydrology) and spatial-ecology analytics (habitat suitability,
biodiversity hotspots, fire impact, climate relationships, migration).

**Status (Phase 7 · C4):** the boundary is now **scaffolded but inert**.
`api/services/environmental.py` defines an `EnvironmentalProvider` protocol with a
`NullProvider` (returns `available=false`) behind `get_provider()`; the
`/environmental/*` routers serve the intended Stage-2 layer catalogue as
unavailable metadata. **No environmental data is fetched or computed** — a real
provider (open-data adapters, then TerraIQ) drops in behind `get_provider()` with
no router/DTO/frontend change.

**TerraIQ** is a planned *separate* environmental-intelligence engine that will
supply this environmental context. The architecture should keep it at arm's length:

- **Boundary:** put environmental data/analytics behind a dedicated **service +
  API boundary** in `api/` (e.g. an `environmental` service + `/environmental/*`
  routers) so the frontend consumes environmental context through the stable Avian
  Observatory contract, regardless of whether the data is computed in-house or
  fetched from TerraIQ.
- **Integration model:** TerraIQ is an upstream provider queried by site/recording/
  region (e.g. "environmental context for site X" / "fire history over this bbox+
  time"). Avian Observatory *consumes* it; it does not merge into it. Both remain
  independent projects.
- **PostGIS** underpins the spatial side (site geometry, bbox/temporal queries,
  environmental-layer joins) — required to unlock Stages 2–3.
- **Design rule now:** do not couple the frontend directly to any environmental
  data source; route everything through the API's environmental service so TerraIQ
  can be slotted in later with no frontend change. See DECISIONS.md D-21.
