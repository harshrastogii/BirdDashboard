# PARITY_AUDIT.md — Avian Observatory

> **Phase 7 · Workstream A deliverable.** A formal, evidence-backed audit of the
> original Streamlit application against the new layered platform, so feature
> parity is **demonstrated, not assumed**.
> Companion: [PROJECT_STATE.md](PROJECT_STATE.md) · [ROADMAP.md](ROADMAP.md) · [ARCHITECTURE.md](ARCHITECTURE.md)

**Audit date:** 2026-07-17
**Reference (source of truth for parity):** `app.py` (675 lines) + `multi_species_section.py` (544 lines) — both still runnable.
**Target:** FastAPI (`api/`) + Next.js (`frontend/`), verified by reading the actual route/component/endpoint code (not the docs' self-description).

## Method

Each user-facing feature in the two Streamlit files was enumerated, then located
in the new app by reading the concrete implementation: the route component, the
domain component it renders, and the backing API endpoint. Every row cites a
real file/endpoint so any reviewer can re-verify.

## Legend

| Mark | Meaning |
|---|---|
| ✅ | Present and functionally equivalent |
| 🟰 | Present via an **intentional** redesign/replacement (function preserved, form/model changed by decision) |
| ⚠️ | Partial — some sub-behaviour not reproduced |
| ❌ | Missing |

---

## 1. `app.py` feature matrix

> **Owner decision (2026-07-17):** for the BirdNET detection timeline (#14 / G3),
> the **comparison temporal scatter is accepted as the modern equivalent** — the
> duplicate BirdNET-only timeline is *not* restored. Both convey per-detection
> timing; the scatter does so within the side-by-side model comparison, which is
> the intended IA. The dead `birdnet-panel.tsx` timeline stays unrestored.
> Likewise, the NT best-segment top-5 (#9 / G2) and footer attribution (#19 / G4)
> are deferred to **Workstream E** (About/UX refinement), not restored now.

| # | Streamlit feature (`app.py`) | New-app home | Status | Evidence / notes |
|---|---|---|---|---|
| 1 | **"About this Dashboard" expander** (`app.py:29`) — what it does, how analysis works, key columns, confidence, why BirdNET errs, who it's for | About/onboarding drawer (`components/layout/about-dialog.tsx`) | ✅ | **Closed in Workstream E.** Accessible drawer (role=dialog, Esc/backdrop close), first-run auto-open + top-bar Help button; content sourced from `app.py:29` and updated for the platform (v5.2 production, provenance, honest significance, how to read outputs). |
| 2 | **Sidebar: upload new audio** (`app.py:107`) — multi-file, analyse-once, collision handling, auto-select | Recordings list upload | ✅ | `frontend/app/(platform)/recordings/page.tsx:39-49` (`useUploadRecording`) → `POST /api/v1/recordings/upload` (`api/routers/v1/recordings.py:36`). Single-file at a time vs multi, but functionally covered. |
| 3 | **Confidence threshold slider** (`app.py:198`) | Per-view min-confidence sliders | ✅ | Workspace `recordings/[id]/page.tsx:51-56`; biodiversity `biodiversity/page.tsx:35`. |
| 4 | **Top metrics — NT model** (`app.py:219`) segments / unique species / avg conf / top species | Comparison tab NT `ModelCard` | 🟰 | `model-comparison-panel.tsx:76-85` (Events/Species/Avg conf). NT source is now v5.2 SED, not the CNN — see note **N1**. |
| 5 | **Top metrics — BirdNET** (`app.py:241`) | Comparison tab BirdNET `ModelCard` | ✅ | `model-comparison-panel.tsx:86-97`. |
| 6 | **Audio player** (`app.py:267`) | Workspace `AudioPlayer` | ✅ | `recordings/[id]/page.tsx:39` → `GET /recordings/{id}/audio`. |
| 7 | **Recording info** (`app.py:273`) file/size/detections + ground-truth "actual species" | Overview "Specimen record" | ✅ | `recording-overview.tsx:38-63` (file, format, duration, size, BirdNET count, ground truth + conservation). Richer than the original. |
| 8 | **Mel spectrogram + "What is a spectrogram?"** (`app.py:299`) | Overview spectrogram card | ✅ | `recording-overview.tsx:26-36` (`SpectrogramViewer` + `InfoPopover`) → server-rendered `GET /recordings/{id}/spectrogram`. |
| 9 | **NT — Top-5 predictions for highest-confidence segment** (`app.py:354`) | Comparison "Top species by confidence" bar | ⚠️ | `model-comparison-panel.tsx:84` shows **top-5 species across the recording**, not the within-segment top-5 rank breakdown of the single best segment. Similar intent, not identical. → candidate polish (E/B). |
| 10 | **Confidence comparison across segments** — NT & BirdNET scatters (`app.py:378`) | Comparison "Confidence across the recording" | ✅ | `model-comparison-panel.tsx:100-115` (`TemporalScatter` ×2). |
| 11 | **NT — All segment predictions (Top-1) table** (`app.py:424`) | Comparison "NT (v5) detections" table | 🟰 | `model-comparison-panel.tsx:119-126`. Now v5.2 events, not CNN per-segment (note **N1**); CSV export included. |
| 12 | **BirdNET detection results table** (`app.py:441`) | Comparison "BirdNET detections" table | ✅ | `model-comparison-panel.tsx:127-135` + CSV. |
| 13 | **Species by confidence chart** (`app.py:464`) | Comparison `SpeciesBarChart` (per model) | ✅ | `model-comparison-panel.tsx:84,95`. |
| 14 | **Detection timeline** (BirdNET, `app.py:486`) | v5 events timeline (Events tab) | ⚠️ | Live timeline is over **v5.2 events** (`events-labelling.tsx:100`). A **BirdNET-detection** timeline exists only in the **dead** `birdnet-panel.tsx` (not rendered). BirdNET timing is still visible via the comparison temporal scatter (#10). → note **N2**. |
| 15 | **Multi-species SED section** (`app.py:517` → `multi_species_section.py`) | Events & Labelling tab | ✅ | See §2. |
| 16 | **Biodiversity metrics** (`app.py:522`) overall + per-file Shannon/Simpson/richness table | Biodiversity page | ✅ | `biodiversity/page.tsx:56-131` → `GET /biodiversity`. |
| 17 | **All-recordings comparison** (`app.py:580`) detections-per-file, species-per-file | Biodiversity page charts | ✅ | `biodiversity/page.tsx:64-96` ("Detections per recording" + "Species richness per recording"). Consolidated here. |
| 18 | **Export data** (`app.py:623`) BirdNET CSV / NT CSV / biodiversity CSV | Per-view CSV buttons | ✅ | `model-comparison-panel.tsx:123,131`; `biodiversity/page.tsx:101`; events `events-labelling.tsx:111`. `lib/csv.ts` (`downloadCsv`/`toCsv`). |
| 19 | **Footer** thesis attribution (`app.py:672`) | *(not reproduced)* | ⚠️ | Minor; provenance/attribution could live in About (E1). |

## 2. `multi_species_section.py` feature matrix

| # | Streamlit feature | New-app home | Status | Evidence / notes |
|---|---|---|---|---|
| 1 | **"What is this?" explainer** (`:267`) | `InfoPopover` (Events tab) | ✅ | `events-labelling.tsx:43-47`. |
| 2 | **Annotator name input** (`:289`) | Listen & Label panel | ✅ | `ListenLabelPanel` (`listen-label-panel.tsx`, rendered `events-labelling.tsx:145`). |
| 3 | **Detection parameters** (primary/secondary/sensitivity/overlap/top-k/suppress-primary) (`:298`) | Parameters card | ✅ | `events-labelling.tsx:54-74` (all six controls, same ranges/defaults). |
| 4 | **Run detection button** (`:340`) | Run button | ✅ | `events-labelling.tsx:40` → `GET /recordings/{id}/multi-species?…` (cached or re-run). |
| 5 | **Summary metrics** duration/primary/events/unique (`:386`) | StatCards | ✅ | `events-labelling.tsx:87-92`. |
| 6 | **Timeline chart** (`:397`) | `DetectionTimeline` | ✅ | `events-labelling.tsx:100`. |
| 7 | **Compact (read-only table) view + CSV** (`:412`) | Compact toggle | ✅ | `events-labelling.tsx:107-141`. |
| 8 | **Interactive Listen & Label** — per-event Listen (3s window), Confirm/Reject/Uncertain, progress, pagination (`:433`) | `ListenLabelPanel` | ✅ | `events-labelling.tsx:142-146`. Persistence is client-side (localStorage) — Workstream priority #4, not a parity gap. |
| 9 | **Export ground-truth labels CSV** (`:493`) | Label export | ✅ | In `ListenLabelPanel`. |
| 10 | **Advanced: raw detector output** (`:540`) | *(not surfaced)* | ⚠️ | Debug-only stdout dump; intentionally omitted from the product UI. Not a user-facing gap. |

---

## 3. Route reconciliation (undocumented routes)

The docs describe the platform routes but omitted several that exist in the tree.
Resolved here:

| Route | Reality | Disposition |
|---|---|---|
| `(platform)/workspace/` | **`ComingSoon` placeholder** ("Research Workspace") — *not* a duplicate of the Recording Workspace | Document as a Roadmap placeholder. Decide (E5): hide behind a flag. |
| `(platform)/admin/` | **`ComingSoon` placeholder** ("Administration") | Document as a Roadmap placeholder; ties to the deferred auth/multi-tenancy work. |
| `(platform)/environment`, `sensors`, `pelican`, `migration`, `analysis/behaviour` | `ComingSoon` placeholders (map to GIS Stages 2–3 / future modules) | Already conceptually in ROADMAP; add to docs' route map. |
| `(platform)/label`, `analysis/multi-species` | **Redirects** to `/recordings` (no duplicate entry point, per D-8) | Correct. Minor nit: they redirect to the recordings **list**, not a specific recording. |

**Conclusion:** the earlier "possible duplication" concern is **resolved** — the
only real Recording Workspace is `recordings/[id]`; `workspace/` and `admin/` are
inert placeholders. No functional duplication exists.

---

## 4. Findings

### Genuine gaps to close (parity)
- **G1 — No "About / onboarding" surface. ✅ CLOSED (Workstream E).** Now an
  accessible About/onboarding drawer (`components/layout/about-dialog.tsx`),
  first-run auto-open + top-bar Help button, sourced from `app.py:29` and extended
  with how-to-read-outputs, provenance, and honest-significance guidance. Verified
  in-browser (opens, renders, Esc-closes).
- **G2 — NT top-5 is recording-level, not best-segment rank (⚠️, #9).** Minor
  fidelity difference; optional to restore.
- **G3 — No BirdNET-specific detection timeline in the live UI (⚠️, #14).**
  BirdNET timing is covered by the comparison temporal scatter; the dedicated
  timeline exists only in dead code. Decide whether to restore or accept the
  equivalent.
- **G4 — Footer/attribution not reproduced (⚠️, #19).** Fold thesis attribution
  into About (E1).

### Intentional divergences (NOT regressions — flagged for transparency)
- **N1 — The "NT model" changed by design.** In `app.py` the NT model was the
  **CNN (v2/v3)**; the new app's production NT view is the **v5.2 SED** (per the
  model reframe, D-11). Function ("per-recording NT predictions") is preserved;
  the model is deliberately different. The CNN per-segment view remains available
  via the historical `GET /recordings/{id}/nt-predictions`. This is correct and
  intended, but should be stated so parity isn't misread as "same output."
- **N2 — Timeline now targets v5 events**, consistent with N1.

### Cross-referenced to later workstreams (not parity issues, logged here)
- **X1 — Unbadged documented metric.** `model-comparison-panel.tsx:159` prints
  **"AUPRC 0.98 / AUROC 0.99"** for the NT model as a plain table cell, with **no
  "Documented · not verified" provenance badge** — the exact integrity rule
  Workstream B (B4) enforces. Not a parity defect; a **scientific-integrity fix
  for Workstream B.**
- **X2 — Dead components confirmed** (already in TECHNICAL_DEBT): `birdnet-panel`,
  `multi-species-panel`, `nt-model-panel`, `species-card` are rendered nowhere
  (`detection-timeline` and `listen-label-panel` **are** live). Removal still
  awaits explicit approval.

---

## 5. Verdict

**Functional parity with the original Streamlit app is substantially
demonstrated.** Every one of the 18 user-facing `app.py` features and all 10
`multi_species_section.py` features is either ✅ present, 🟰 present via an
intentional redesign, or ⚠️ a minor fidelity difference — **except one true gap:
the About/onboarding content (G1, ❌).** All undocumented routes are benign
placeholders. No functional duplication exists.

**Recommended parity closure (for approval):**
1. **G1** (About/onboarding) — execute in **Workstream E**.
2. **G3** (BirdNET timeline) — decide: restore, or accept the temporal-scatter equivalent (recommend: accept + document).
3. **G2, G4** — optional polish in E.
4. **N1/N2** — documentation clarity (add a one-line note to ARCHITECTURE/MODEL_REGISTRY that the NT surface is v5.2 by design).
5. **X1** — hand to **Workstream B** (already scoped, B4).

No code has been changed in this workstream; this document is the deliverable.
