# DECISIONS.md — Avian Observatory

> Every important architectural & scientific decision, with reasoning. Newest
> concepts last. Companion: [ARCHITECTURE.md](ARCHITECTURE.md) · [MODEL_REGISTRY.md](MODEL_REGISTRY.md)

## Architectural

**D-1 · `birddash` is the framework-agnostic scientific core.**
All ML/inference/domain logic lives in `birddash` with no Streamlit/FastAPI
imports. *Why:* the same code backs the original Streamlit app, the FastAPI
service, and offline scripts; enables testing and reuse. Enforced by a test that
asserts no `import streamlit` in the package.

**D-2 · Layered (hexagonal) architecture: routers → services → repositories → (DB | filesystem) + core.**
*Why:* separation of concerns; the repository seam lets storage change (filesystem
→ Postgres/object store) without touching services or the API contract.

**D-3 · Pydantic DTOs are the API contract; never expose internal shapes.**
The API never returns DataFrames or filesystem paths. *Why:* internals can evolve
freely as long as DTOs stay backwards-compatible; makes it a platform, not an RPC wrapper.

**D-4 · Resource-oriented REST with stable opaque UUIDs, decoupled from storage.**
Recordings/species/etc. get UUIDs immediately; `source_path` is an internal link.
*Why:* URLs survive the future filesystem→DB migration; "running a model" is a
durable `Analysis` resource, not a naked function call.

**D-5 · PostgreSQL metadata store introduced early (Phase 3), heavy artefacts on filesystem until later.**
*Why:* real relational IDs/relationships/spatial data need a DB now; avoids a
throwaway filename-ID scheme. Detections/audio/spectrograms stay on the filesystem
(read via the `detections` repository) until the Phase-6 blob migration.

**D-6 · Next.js is the long-term frontend; Streamlit kept running during migration.**
*Why:* Streamlit is the right thesis tool but limiting for GIS/audio/responsiveness;
Next.js is built incrementally behind the working Streamlit app so there's never
a moment without a usable product.

**D-7 · "Observatory" design system; GIS-first, research-focused, modular.**
Deep teal + slate, NT earth-tone accents, field-notebook metadata cues; light +
night-observatory dark. *Why:* should read as a scientific instrument for
researchers/agencies, not a generic SaaS dashboard.

**D-8 · One logical home per feature; no duplication.**
Per-recording analysis (BirdNET, NT v5, multi-species, Listen & Label) lives only
in the Recording Workspace; standalone `/label` and `/analysis/multi-species`
**redirect** there. *Why:* the app had fragmented; users shouldn't jump between
pages to complete one workflow.

**D-9 · Auth fully designed, permissively stubbed.**
Every endpoint declares a scope; roles→scopes defined; OIDC scheme in OpenAPI.
Dev mode is permissive (`X-Debug-Role`). Multi-tenancy in the data model
(`organisation_id`) from day one. *Why:* enforcement becomes a config flip, not a
rewrite; retrofitting tenancy later is painful. (Owner deprioritised implementing real auth.)

**D-10 · Future-proof model registry — models as versioned scientific artefacts.**
`evaluation/registry.json` lists model versions with metadata, status, documented
values, and evaluation history. *Why:* any future model (v6, v7…) is added by
editing the registry + dropping artefacts — no code change. The platform never
assumes a single "current" model.

## Scientific / evaluation

**D-11 · v5 / v5.2 is the primary production model; the CNN is historical (kept intact).**
The old CNN (v2/v3, `nt_bird_cnn_best.keras`) is **not** removed or deprecated in
`birddash` (retained for reproducibility and the thesis), but is never presented
as the production model — only in Model Evolution / Research. *Why:* the CNN's
92.7% was inflated by leakage (exposed by v4); the v5 BirdNET-embeddings classifier
via the v5.2 SED pipeline is the flagship contribution.

**D-12 · Do not fabricate or estimate metrics. Prefer reproducibility over displaying more numbers.**
If a metric can't be traced to an evaluation artefact, it is labelled *documented,
not verified*. *Why:* scientific integrity. The v5 0.98/0.99 are documented (only
in README + hardcoded in `generate_charts.py`); no original v5 artefacts exist
(exhaustive search, 2026-07-17).

**D-13 · Three metric provenance classes, strictly separated, never conflated.**
*documented* (reported, untraceable) vs *original_evaluation* (recomputed from
original saved artefacts — the original experiment) vs *independent_reproduction*
(a new experiment). The app must never present a retrained model's metrics as the
original thesis evaluation, nor silently substitute one for the other. *Why:*
explicit owner requirement; the newly retrained v5 is a different experiment.

**D-14 · Model comparison uses recording-level, data-driven correct-detection rates on identical recordings, with verified labels.**
NOT the leaky 92.7%. Both models scored on the SAME recordings; ground truth from
`dataset_metadata.csv`; predicted species shown for transparency (why each
succeeded/failed). *Why:* an honest, apples-to-apples, transparent comparison.

**D-15 · CNN metrics recomputed from the original saved test arrays (traceable).**
`regenerate_cnn_evaluation.py` recomputes accuracy/P/R/F1/AUROC/AUPRC/confusion/
ROC-PR from `models/y_test_*.npy` → `evaluation/original/cnn_*`. Recomputed values
match the original `classification_report.json` exactly. *Why:* every CNN number
shown is verifiable.

**D-16 · v5 independent reproduction = recording-level held-out, retrained on the train split.**
Because the production v5 was trained on all data with a non-persisted internal
split, an honest generalisation estimate requires a recording-level held-out split
+ a retrained classifier (mirroring the v4 methodology). Result stored in
`evaluation/reproduced/v5` and labelled a separate experiment. Augmentation
(mixup/upsampling) disabled — BirdNET-Analyzer crashes on this split's empty-class
edge case (its handler needs the uninstalled `keras_tuner`); disabling it yields a
conservative estimate, recorded in provenance. *Why:* honesty + reproducibility.

**D-17 · Server-side spectrograms (not client-side FFT).**
`birddash.audio.render_spectrogram_png` (matplotlib, viridis, cached) via
`GET /recordings/{id}/spectrogram`. *Why:* the client-side wavesurfer FFT was
unreliable; the server pipeline mirrors the original Streamlit spectrogram and always renders.

**D-18 · Listen & Label persistence is client-side (localStorage) for now.**
*Why:* exceeds Streamlit's session-only behaviour without new backend; a
server-side annotations resource (reviewer workflow, provenance, verification) is
the next annotation task (priority #4).

**D-19 · Map uses seeded real NT sites + illustrative recording associations (labelled sample data).**
Per-recording longitude is missing (Xeno-canto download captured only latitude).
*Why:* delivers a genuine GIS-first foundation without fabricating per-recording
GPS; real geo lights up after a Xeno-canto re-fetch.

**D-20 · Ground truth for comparison/species = verified labels from `dataset_metadata.csv`.**
Filename → verified common name (fallback: catalog prefix match). *Why:* traceable,
authoritative labels rather than ad-hoc filename parsing.

## Vision & environmental intelligence

**D-21 · Environmental intelligence is a decoupled layer; TerraIQ is a separate integrated project (not a replacement).**
Avian Observatory owns acoustic + biodiversity intelligence; environmental context
(weather, fire, vegetation, protected areas, hydrology, …) is a distinct concern
supplied — eventually — by **TerraIQ**, a separate environmental-intelligence
engine. Avian Observatory *consumes* TerraIQ through a clean API/service boundary
and is never absorbed into it, nor does it rebuild all environmental pipelines
in-house. *Why:* clean separation of concerns; each project evolves independently;
the environmental layer can be sourced in-house first and swapped to TerraIQ later
without frontend changes. Design implication: keep environmental data/analytics
behind an `environmental` service + API boundary. (See ARCHITECTURE.md §11,
ROADMAP.md GIS Stage 4.)

**D-22 · The platform is GIS-first environmental intelligence, not a bird dashboard.**
The product direction is explicitly to evolve from a bird-classification dashboard
into a professional environmental-intelligence platform for ecological research,
biodiversity monitoring, and conservation decision support, staged via the
four-stage GIS roadmap (Recording Intelligence → Environmental Intelligence →
Spatial Ecology → TerraIQ Integration). *Why:* the scientific value is in fusing
acoustic detections with spatial and environmental context ("where/when/what
habitat/what conditions/what conservation meaning"), not just species labels.
Every architectural choice (stable IDs, PostGIS-ready geometry, decoupled layers,
resource-oriented API) is made to support this trajectory.

## Scientific rigour (Phase 7 · Workstream B)

**D-23 · Every reported metric carries an uncertainty statement and a cited
method.** Point estimates on small samples (comparison n≈23; some class supports
of 1–2) are misleading, so: operational detection rates get **Wilson** 95%
intervals and the paired difference an **exact McNemar** test; per-class
precision/recall get **exact Clopper–Pearson** intervals; aggregate accuracy/
macro-F1 get **percentile bootstrap** intervals (resampled at the recording level
for the recording-level held-out eval). Small-sample "reliability" is a **derived**
criterion (95% CI width > 0.5), **not** an arbitrary minimum n. Every method is
cited in [docs/METHODOLOGY.md](docs/METHODOLOGY.md). *Why:* scientific credibility
is the platform's highest priority and the basis of Paper 1; a bare number without
its sampling uncertainty overstates certainty. The statistics live in the
framework-free core (`birddash/statistics.py`); intervals are computed from
persisted arrays with **no retraining** (`--from-saved`), respecting the paused v5
retraining.

**D-25 · Location resolves through a coordinate-provider seam; precise geo slots
in later without rework.** `api/services/geospatial.py` is the single place a
recording's location is decided: precise per-recording GPS when present, else the
site location tagged **approximate** (`coordinate_precision` on the DTOs). Nullable
`Recording.latitude/longitude` columns were added (migration `b1c2d3e4f5a6`) as the
home for real GPS. *Why (owner directive):* longitude recovery must **not** block
GIS — the map, filters, and environmental seam are built now, and when a Xeno-canto
re-fetch fills the columns the map upgrades from approximate to precise with no
caller/DTO/frontend change. No coordinate is fabricated; approximate points are
explicitly the site location and labelled so. PostGIS geometry replaces the lat/lon
columns behind this same service when spatial queries are needed. Supersedes the
data-only framing of D-19 with a real abstraction.

**D-27 · The Publication Asset Registry is the single authoritative index of every
reported result, and it is generated, not hand-maintained.** `build_asset_registry.py`
→ `evaluation/asset_registry.json` catalogues every figure/table/statistic/artefact
with source script, dataset version, model version, provenance, intended use, and an
md5. Publication figures/tables are rendered from the *same* persisted artefacts the
app displays (`generate_publication_assets.py`), the live comparison is snapshotted
(`persist_comparison_artifact.py`), and `verify_metric_provenance.py` asserts app ==
artefact. *Why:* Paper 1 and the app must never diverge, and every number must be
reproducible from the repository. `generate_charts.py` (hardcoded) is deprecated and
quarantined. (See docs/PUBLICATION_ASSETS.md; supersedes the loose "registry-as-data"
framing of D-10 for evaluation *results* specifically.)

**D-26 · The environmental layer is a scaffolded-but-inert boundary now.**
`api/services/environmental.py` (`EnvironmentalProvider` protocol + `NullProvider`)
and `/environmental/*` exist and return `available=false`; **no environmental data
is fetched.** *Why:* realises D-21's decoupling cheaply — a real source (open data,
then TerraIQ) plugs in behind `get_provider()` with no frontend change — while
keeping TerraIQ out of the current focus (owner directive). The frontend shows a
truthful "Environmental layers · soon" toggle driven by this endpoint.

**D-24 · Species-name matching is synonym-aware, via a sourced, conservative
table.** True cross-checklist synonyms (IOC "Bush Thick-knee" = BirdLife Australia
"Bush Stone-curlew") are resolved so a correct detection under a synonymous name is
not scored as a miss (`birddash/taxonomy.py`, mirrored in the frontend). Entries
require a checklist **citation**; BirdNET *misidentifications* are never added.
*Why:* the previous naive string match counted BirdNET's synonymous-but-correct
answer as wrong, biasing the comparison **in our own model's favour**; fixing it
(BirdNET 17→18 of 23) makes the flagship claim defensible. The table is kept
minimal and sourced precisely so it can never silently inflate measured accuracy.
