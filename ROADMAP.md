# ROADMAP.md — Avian Observatory

> Completed phases, current phase, and remaining milestones.
> Companion: [PROJECT_STATE.md](PROJECT_STATE.md) · [DECISIONS.md](DECISIONS.md)

## Vision

**Avian Observatory is evolving from a bird-classification dashboard into a
professional environmental-intelligence platform for ecological research,
biodiversity monitoring, and conservation decision support.**

The trajectory is deliberately **GIS-first**. Acoustic AI answers *"what species
is this?"*; the platform's ambition is to answer *"**where**, **when**, in **what
habitat**, under **what environmental conditions**, and **what does it mean for
conservation**?"* To get there we fuse three layers:

1. **Acoustic intelligence** — species detection & multi-species SED (v5/v5.2), confidence, annotation.
2. **Spatial intelligence** — recording locations, monitoring sites, biodiversity metrics across space and time.
3. **Environmental intelligence** — weather, fire, vegetation, protected areas, hydrology, land cover, elevation — supplied over time by a dedicated engine (**TerraIQ**, a *separate* project; see Stage 4).

The GIS roadmap below (four stages) is the spine of this evolution. Avian
Observatory remains the acoustic + biodiversity platform; TerraIQ, when it
exists, is the environmental-intelligence engine it integrates with — never a
replacement for it.

## Migration principle

No big-bang rewrite. Migrate feature-by-feature, keeping the project working at
every stage. Priorities: clean architecture → maintainability → scalability →
scientific correctness → production readiness. The original Streamlit app stays
runnable throughout.

## Completed

### Phase 1 — Stabilise & prepare ✅
Fixed the upload bug (analyse only new files, auto-select upload, collision
handling, surfaced errors). Centralised config (`birddash/config.py`, portable/
env-overridable). Pinned dependencies; added `soundfile`/`matplotlib`. Golden-file
test harness. Removed dead backups.

### Phase 2 — Extract ML core ✅
Created the framework-agnostic `birddash` package (`config, audio, nt_model,
birdnet, results, metrics, detection`). Streamlit files became thin consumers;
the detector CLI a thin wrapper. Golden tests prove byte-identical outputs.

### Phase 3a — FastAPI backend + Postgres metadata ✅
Resource-oriented read API (recordings, species, sites, detections, jobs, meta).
SQLAlchemy 2.0 + Alembic; PostgreSQL `birddash_dev`. RFC 9457 errors, cursor
pagination, auth scheme (dev stub), seed from filesystem. Stable UUID identity.

### Phase 4 — Next.js frontend foundation ✅
Next.js 16 App Router + TS + Tailwind v4 + shadcn-style UI + TanStack Query +
MapLibre/MapTiler. "Observatory" design system (light + night-observatory dark).
App shell, homepage, dashboard, map, recordings, species. Rebrand to Avian Observatory.

### Phase 5 — Feature parity ✅
BirdNET detections, NT multi-species SED, Listen & Label, biodiversity metrics,
spectrogram, audio playback, charts, CSV exports — migrated into the app.

### Phase 6 — Refinement & IA redesign ✅
Consolidated per-recording analysis into the Recording Workspace (Overview /
Model Comparison / Events & Labelling). Trimmed navigation (Overview / Explore /
Analyze / Roadmap). Fixed the model-comparison logic (verified-label ground
truth). Server-rendered spectrograms. Removed duplicate entry points.

### Model reframe & scientific integrity ✅
- v5 / v5.2 made the **primary production model** everywhere; CNN kept intact but
  presented only as historical/research (un-deprecated in the core).
- Data-driven NT-v5-vs-BirdNET comparison (dropped the leaky 92.7% headline).
- **Model registry** + strict separation of documented / original-evaluation /
  independent-reproduction metrics.
- CNN evaluation regenerated from saved arrays (traceable). v5 reproducible
  held-out evaluation built and run (`evaluation/reproduced/v5`).
- Upload (write path) restored.

### Phase 7 · Workstream A — Formal parity audit ✅
Demonstrated (not assumed) feature parity vs the original Streamlit app
(`PARITY_AUDIT.md`); one genuine gap (About/onboarding) routed to Workstream E.

### Phase 7 · Workstream B — Scientific credibility hardening ✅
Framework-free statistics core (`birddash/statistics.py`: Wilson, Clopper–Pearson,
exact McNemar, bootstrap — all cited in `docs/METHODOLOGY.md`); sourced,
conservative synonym handling (`birddash/taxonomy.py`); confidence intervals +
provenance on every reported metric (API + UI); CIs recomputed into CNN & v5
artefacts from saved arrays (no retraining). Key honest finding: the NT-vs-BirdNET
operational lead is **not statistically significant at n=23** (McNemar) — surfaced,
not hidden; it signals a data-collection direction (annotation, priority #4).

### Phase 7 · Workstream C — GIS foundation ✅
Coordinate-provider abstraction (`api/services/geospatial.py`; nullable per-recording
lat/lon columns so precise GPS slots in later); map species/confidence filters +
layer toggles (`/map/sites`, synonym-aware); PostGIS-ready path documented (not
activated); inert environmental service boundary (`/environmental/*`) so Stage-2
sources / TerraIQ plug in with no frontend change. Longitude recovery is **not** a
blocker — approximate (site-level) locations are labelled as such and upgrade
automatically when real GPS arrives.

### Phase 7 · Workstream D — Research foundation & publication assets ✅
Reproducible metrics schema with CIs across all evaluations; **Publication Asset
Registry** (`evaluation/asset_registry.json`, 53 assets catalogued with source
script / dataset version / model version / provenance / intended use / md5);
publication-quality figures (PNG+PDF, colourblind-safe) + tables (CSV+LaTeX) under
`evaluation/paper1/`, rendered from the same artefacts the app displays; the live
comparison snapshotted; `verify_metric_provenance.py` proves **app == artefact**
(9/9 checks). `generate_charts.py` deprecated/quarantined. Registry is the single
authoritative source for all reported evaluation results. See docs/PUBLICATION_ASSETS.md.

### Phase 7 · Workstream E — Platform polish ✅
About/onboarding drawer (closes parity gap G1 — accessible, first-run auto-open +
Help button); placeholder "Roadmap" modules hidden behind `FEATURES.roadmapModules`
(nav reflects what's usable today); removed the decorative bell/search; consistent
loading/empty/error states across the data views; accessibility + chart
legend/caption pass. Goal was to make the platform **feel complete** and reduce
first-time-user friction, not add new functionality.

## Current phase — Platform completion & polish

Priority order set by the owner:
1. **Finish 100% feature parity** with the original Streamlit app.
2. **Improve the GIS experience** and interactive map.
3. **Improve UX/UI** — polished environmental-intelligence platform feel.
4. **Strengthen the annotation workflow** — Listen & Label, reviewer workflow,
   confidence, provenance, expert verification.
5. (Deferred) resume the independent v5 evaluation pipeline only if asked.

## GIS & Environmental Intelligence roadmap — the four stages

The long-term GIS-first vision, staged from what exists today to the full
environmental-intelligence platform. Each stage builds on the previous.

### Stage 1 — Recording Intelligence  *(largely in place; being polished)*
The acoustic-spatial foundation: understand recordings in space.
- **Recording locations** — per-recording geo *(blocked: longitude missing from the
  Xeno-canto download; currently approximated via monitoring sites — see TECHNICAL_DEBT.md)*.
- **Monitoring sites** — seeded real NT sites on the map, drill-down to a site's recordings ✅.
- **Species detections** — BirdNET (baseline) + NT v5/v5.2 (production) per recording ✅.
- **Confidence filtering** — threshold filters across detections/metrics ✅.
- **Recording explorer** — browse, play, spectrogram, analyse ✅.
> Status (updated Phase 7 · C): the **coordinate-provider abstraction**
> (`api/services/geospatial.py`) now resolves precise-or-approximate locations
> with a `coordinate_precision` tag; the map has **species + confidence filters
> and layer toggles** (`/map/sites`). Remaining: real per-recording GPS (slots in
> via the provider), deck.gl overlays, PostGIS.

### Stage 2 — Environmental Intelligence
Overlay the environment onto the acoustic-spatial base — toggleable map layers:
- **Weather** (current + historical) · **Fire history** · **Vegetation** ·
  **Protected areas** · **Indigenous Protected Areas (IPAs)** · **Land cover** ·
  **Elevation** · **Hydrology** · a general **environmental layers** framework.
> Requires PostGIS + a layer-management system in the API/UI. These layers are
> the data TerraIQ will ultimately serve (Stage 4); until then they can be
> integrated from open sources (e.g. NAFI fire, DEA land cover, DEM, hydrology).
> **Boundary scaffolded (Phase 7 · C4):** `api/services/environmental.py` +
> `/environmental/*` exist but are inert (`available=false`); a real source plugs
> in behind `get_provider()` with no frontend change.

### Stage 3 — Spatial Ecology
Analytics fusing acoustic + spatial + environmental data into ecological insight:
- **Habitat suitability** · **Biodiversity hotspots** · **Species richness** (mapped)
  · **Environmental change** · **Fire impact** on species presence · **Climate
  relationships** · **Migration** & movement · **Conservation analytics** (decision support).
> This is where the platform becomes genuinely *intelligent* — correlating species
> activity with environmental context. Needs Stage 2 data + longitudinal /
> field-deployment data for movement and change analysis.

### Stage 4 — TerraIQ Integration
**TerraIQ is a future, *separate* environmental-intelligence engine.** It provides
environmental context (the Stage 2 layers and Stage 3 analytics data) to Avian
Observatory through a clean API/integration boundary.
- **Relationship:** TerraIQ is *not* a replacement for Avian Observatory and Avian
  Observatory is *not* absorbed into TerraIQ. Avian Observatory owns acoustic +
  biodiversity intelligence; TerraIQ owns environmental intelligence. They are
  decoupled projects that integrate.
- **Integration model:** Avian Observatory *consumes* TerraIQ as an environmental
  data/analytics service (query environmental context for a site, recording, or
  region) rather than rebuilding all environmental data pipelines in-house.
- **Design implication (now):** keep the environmental layer behind a service
  boundary in the API so TerraIQ can slot in later without frontend changes (see
  ARCHITECTURE.md §"Environmental intelligence layer & TerraIQ").

## Remaining milestones

### Near-term (current priorities)
- **Parity audit** — re-check original `app.py` vs the workspace; add the
  overarching About/onboarding content; confirm no interaction/chart/export lost.
- **GIS (Stage 1 polish)** — layer toggles, species/confidence map filters, deck.gl
  overlays; recover per-recording longitude (Xeno-canto re-fetch) to make the map per-recording.
- **UX/UI** — ⌘K command palette, mobile sidebar, job/notification bell wiring,
  loading/empty states, accessibility + dark-mode pass.
- **Annotation** — server-side annotations resource (table + endpoints), reviewer/
  expert-verification states, confidence + provenance per label, inter-annotator agreement.

### Mid-term (Phase 3b + Stage 2/3 enablement)
- **Phase 3b** — async job execution for analysis (Celery/RQ + Redis or FastAPI
  BackgroundTasks); move heavy inference out of the request path.
- **PostGIS + data migration (Phase 6 data)** — migrate detections/audio from the
  filesystem into Postgres/object storage; add PostGIS spatial queries. *This
  unlocks GIS Stages 2–3.*
- **New platform modules** (currently "Roadmap" nav placeholders), mapped to the
  GIS stages: **Environmental Layers** → Stage 2; **Behaviour Analysis**
  (call-type classification — the `type` field in `dataset_metadata.csv` is the
  raw material), **Migration Analytics**, **Pelican Intelligence** → Stage 3;
  **Sensor Network** → near-real-time ingest.

### Long-term (production platform + environmental intelligence)
- **Auth & multi-tenancy** — wire real OIDC (scheme already designed/stubbed).
- **Deployment** — Docker Compose → containers; CI (lint + tests); monitoring
  (Sentry/Prometheus); model-artefact storage (Git LFS or object store — models
  are gitignored today).
- **TerraIQ integration (GIS Stage 4)** — integrate the separate TerraIQ
  environmental-intelligence engine as the source of environmental context, behind
  the API's environmental-layer service boundary. TerraIQ stays a distinct project.
- **Reproducible v5 evaluation** — finish/persist as a permanent artefact set
  (pipeline exists: `evaluate_v5.py`); consider retraining v5 with a persisted
  recording-level split so production metrics are verifiable.
- **Behaviour & migration research** — requires labelled call-type data (partly
  present) and longitudinal field-deployment data (not yet available).

## Explicitly out of scope right now
- Retraining / reproducing v5 metrics (owner paused this).
- Deleting deprecated/legacy components or endpoints (awaits explicit approval).
- Committing/pushing (owner controls git).
