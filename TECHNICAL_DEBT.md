# TECHNICAL_DEBT.md — Avian Observatory

> Deferred work, cleanup, legacy/deprecated components, known limitations.
> Nothing here is deleted — removal awaits explicit owner approval.
> Companion: [PROJECT_STATE.md](PROJECT_STATE.md) · [ROADMAP.md](ROADMAP.md)

## Dead / orphaned code (safe to remove, pending approval)

- **Frontend components no longer rendered:** `frontend/components/domain/nt-model-panel.tsx`,
  `birdnet-panel.tsx`, `multi-species-panel.tsx`, `species-card.tsx`. Superseded by
  the Recording Workspace tabs + registry UI. (`nt-model-panel` still imports the
  historical `/nt-predictions` hook.)
- **`tests/_reference.py`** — Phase-1 golden-file scaffolding, superseded by
  `birddash.nt_model` (the golden JSON in `tests/golden/` is the lasting contract).
- **Root `config.py`** — a compatibility shim re-exporting `birddash.config`.
  Nothing imports it anymore; kept for safety.

## Legacy / deprecated-but-retained (intentionally kept)

- **`/api/v1/models/research-metrics`** — superseded by `/models/registry`
  (frontend uses the registry). Kept for backward compat.
- **NT CNN (`/recordings/{id}/nt-predictions`, `birddash.nt_model`)** — the
  historical v2/v3 CNN. **Kept intact by explicit decision** (reproducibility,
  thesis). Not deprecated; simply not presented as production.
- **`generate_charts.py`** — **deprecated/quarantined (Phase 7·D).** Produces thesis
  PNGs from **hardcoded** values (incl. the un-traceable v5 0.98/0.99). Superseded by
  `generate_publication_assets.py` (renders from persisted artefacts).
  `verify_metric_provenance.py` asserts nothing on the app/eval path imports it. Kept
  only for historical thesis reference; do not use for publication.

## Resolved defects (kept for the record)

- **Name-truncation collision in the SED parser — FIXED (Phase 7 stabilization).**
  BirdNET-Analyzer writes a custom label `<A>_<B...>` split across the CSV's
  Scientific (`<A>`) and Common (`<B...>`) columns. `parse_birdnet_csv` read only
  the Common column, so labels sharing a final word collided: `Owl`
  {Barking_Owl, Masked_Owl} and `Kite` {Black_Kite, Whistling_Kite} both resolved
  to the last-defined label → Barking Owl was mislabelled "Masked Owl" and Black
  Kite "Whistling Kite" (the model detected both correctly at >0.99). **Fix:**
  rejoin both columns to recover the full label (`birddash/detection.py`).
  Regression tests: `tests/test_detection_parsing.py`. Exactly 2 collision groups
  existed in the 25-label set (test-pinned). 17 affected artefacts regenerated;
  NT comparison rose 21/23 → 23/23. The v5 held-out reproduction was **unaffected**
  (it maps tflite index→label directly, no CSV parsing).

## Data limitations

- **Per-recording longitude missing.** `download_dataset_v2.py` captured
  `rec.get("lat")` but `lng` came back empty for all records → 0 mappable
  recordings. The map uses seeded NT sites + **illustrative** recording
  associations (labelled sample data). Fix: re-fetch Xeno-canto metadata for `lng`.
- **`dataset_metadata.csv`** has a rich `type` field (call/song/flight call/alarm/
  begging/duet…) — raw material for future **behaviour classification** — currently unused.
- **Some species names differ across sources** (e.g. BirdNET "Bush Thick-knee" =
  "Bush Stone-curlew"). **Addressed (Phase 7 · B):** `birddash/taxonomy.py` now
  resolves sourced synonyms so these count correctly (BirdNET 17→18 of 23). The
  table is deliberately minimal/sourced; extend it only with cited cross-checklist
  synonyms (never BirdNET misidentifications). Frontend mirror in
  `frontend/lib/ground-truth.ts` must stay in sync with the core table.

## Architecture / platform debt

- **In-process TensorFlow inference in the API** (NT model loaded lazily in the
  API process). Fine for dev; move to a worker (Phase 3b) before scaling.
- **Detections/audio/spectrograms on the filesystem** (metadata in Postgres).
  Phase 6 migrates blobs to Postgres/object storage; the `detections` repository
  is the single adapter to change.
- **Spectrogram capped at 60 s** (`DISPLAY_SPEC_DURATION`) — mismatched with
  full-file detections for long recordings.
- **Auth stubbed** (dev-permissive). No rate limiting. CORS allows only
  `localhost:3000`. MapTiler client key lives in `frontend/.env.local` (restrict
  by domain before any public deploy).
- **No CI / Docker / deployment config.** Models are gitignored (`.keras`/`.tflite`/
  `.npy` not in git) → a fresh clone has no models; needs Git LFS or object storage
  for deployment. **Corollary:** the Phase 7·D publication assets (`evaluation/paper1/`
  PNG/PDF, and the `.npy` reproduction arrays) are **regenerable** from the pipeline
  (see docs/PUBLICATION_ASSETS.md), so committing them is optional; if committed,
  route binaries through Git LFS. A fresh clone must run the pipeline (needs the
  gitignored source arrays/models) to reproduce them.
- **Tests hit the shared dev DB** (`tests/test_api.py`). For CI, add a dedicated
  test DB + transactional rollback fixtures. `pytest` is in `requirements-dev.txt`
  but tests also run via `python tests/<file>.py`.
- **Frontend API types hand-authored** (`lib/api/types.ts`). Production approach:
  generate from `/openapi.json` (openapi-typescript) in CI.

## UX / feature gaps

- ~~No overarching "About Avian Observatory" / onboarding~~ **Resolved (Phase 7·E):**
  accessible About/onboarding drawer (`components/layout/about-dialog.tsx`),
  first-run auto-open + top-bar Help button.
- ~~Top-bar job/notification bell is decorative~~ **Resolved (Phase 7·E):** the
  decorative bell and non-functional search were removed; the top bar now carries
  the tagline + a working About/Help button + theme toggle (reflects what's real).
- ~~"Roadmap" nav modules are placeholders~~ **Resolved (Phase 7·E):** hidden
  behind the `FEATURES.roadmapModules` flag (default off; `NEXT_PUBLIC_SHOW_ROADMAP`
  reveals them). The routes still exist (ComingSoon), just un-advertised.
- **Command palette (⌘K), mobile sidebar drawer** — still absent (desktop-first).
- **Listen & Label persistence is client-side only** (localStorage) — no
  server-side annotations, reviewer workflow, or expert verification yet (priority #4).

## Evaluation / reproducibility debt (paused by owner)

- **v5 documented metrics unverified.** 0.98/0.99 have no original artefact. An
  independent reproduction exists (`evaluation/reproduced/v5`, acc 0.882 / AUROC
  0.980) but is a *separate* experiment. To make the *production* v5 metrics
  verifiable, retrain v5 with a **persisted** recording-level split.
- **v5 reproduction ran with augmentation disabled** (BirdNET-Analyzer upsampling
  crash needs `keras_tuner`, uninstalled). Installing `keras_tuner` + re-enabling
  would more faithfully reproduce the production recipe.
- **Long background jobs are killed** in this environment when a tool call
  returns; run persistent evaluations outside a single tool invocation.

## Operational notes

- Two dev servers run during work: API `uvicorn api.main:app --port 8000`, web
  `npm run dev` (3000). PIDs were tracked in `/tmp/api_run.pid` / `/tmp/next_run.pid`.
- `birddash_dev` Postgres DB must exist + be migrated + seeded (`PROJECT_STATE.md` §run).
