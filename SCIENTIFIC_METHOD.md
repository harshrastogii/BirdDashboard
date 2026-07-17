# SCIENTIFIC_METHOD.md — Avian Observatory

> Dataset provenance, annotation & evaluation methodology, comparison method,
> model evolution, limitations, and future research.
> Companion: [MODEL_REGISTRY.md](MODEL_REGISTRY.md) · [DECISIONS.md](DECISIONS.md)

## 1. Motivation

BirdNET (Kahl et al., 2021) is the global gold-standard for acoustic bird ID, but
its training skews to the Northern Hemisphere; on Northern Territory species it
routinely misidentifies (e.g. Azure Kingfisher → "Eurasian Treecreeper", Diamond
Dove → "New Zealand Bellbird"), often with high confidence. The project builds
NT-specific classifiers that materially outperform BirdNET on NT species, and a
platform to demonstrate and operationalise this.

Context: PRT840 IT Thesis, Master of Data Science, Charles Darwin University;
supervisor Dr. Md Rafiqul Islam.

## 2. Dataset provenance

- **Source:** Xeno-canto (community recordings), downloaded via `download_dataset*.py`.
- **Scope:** `training_data/` — **1303 recordings across 25 species folders**
  (24 core NT species + **Red_Goshawk**). Per-species counts vary (e.g. Azure
  Kingfisher 24, Black Kite 80).
- **Verified labels & metadata:** `training_data/dataset_metadata.csv` — common
  name, scientific name, conservation status, Xeno-canto id, quality, recordist,
  country, **latitude** (longitude MISSING — download bug), date, time, **call
  `type`** (call/song/flight call/alarm/begging/duet/…), length, filename.
  *(The metadata CSV currently covers **1215 rows / 24 named species**; the
  `training_data/` folders span the 25 v5 classes incl. Red_Goshawk. The CSV md5 +
  counts are recorded in the Publication Asset Registry for reproducibility.)*
- **Known data issue:** longitude was not captured (only latitude), so
  per-recording GPS is unavailable (see limitations).

## 3. Preprocessing

- **CNN (v2/v3):** 3-second non-overlapping segments, 22050 Hz mono, 128-mel
  spectrograms (`n_fft=2048, hop=512, fmin=150, fmax=15000`), per-segment [0,1]
  normalisation, RMS silence gate (`< 0.001`). (`preprocess.py`, `birddash.nt_model`.)
- **v5 classifier:** raw 48 kHz 3-second audio (144000 samples) → BirdNET v2.4
  feature extractor (baked into the tflite) → 25-class head.

## 4. Model evolution (scientific narrative)

| Version | Method | Key result | Lesson |
|---|---|---|---|
| v2 | CNN on mel-spectrograms, segment-level split | 92.7% (segment) | Looked great — but... |
| v3 | v2 + augmentation | 92.7% (segment) | Augmentation didn't move it; capacity wasn't the limit |
| **v4** | Same CNN, **recording-level** split | **66.6%** | **Exposed segment-level data leakage** — the honest number is far lower |
| v5 | BirdNET embeddings + custom head (transfer learning) | AUPRC 0.98 / AUROC 0.99 (documented) | Bypasses leakage at the representational level |
| v5.2 | v5 + sliding-window dual-threshold SED | multi-species + timestamps | Operational multi-species detection |

The **leakage lesson (v4)** is the pivotal scientific result: evaluating on
segments that share a recording with training segments inflates accuracy. All
honest evaluation must split at the **recording** level.

## 5. Evaluation methodology & provenance

Three strictly-separated classes (see DECISIONS.md D-13):

1. **Documented (not verified).** v5 AUPRC 0.98 / AUROC 0.99 — reported in
   thesis/README, but an exhaustive repo + git search found **no** original v5
   evaluation artefacts. They originate from BirdNET-Analyzer's **internal
   validation** during training (a leaky, non-persisted segment-level split).
   Shown labelled *"Documented · not verified"*.

2. **Original evaluation (verified/traceable).** CNN v2/v3/v4 metrics recomputed
   from the ORIGINAL saved test arrays (`models/y_test_{probs,true}{,_v3,_v4}.npy`)
   by `regenerate_cnn_evaluation.py` → `evaluation/original/cnn_*`. Recomputed
   values match the original `classification_report.json` exactly. Includes
   accuracy, precision/recall/F1 (per-class + macro/weighted), AUROC, AUPRC,
   confusion matrix, ROC & PR curves.
   - v2: acc **0.9267**, macro F1 0.9169, AUROC 0.997, AUPRC 0.9643.
   - v4: acc **0.6661** (honest recording-level).

3. **Independent reproduction (verified, separate experiment).** `evaluate_v5.py`
   performs a **recording-level held-out** evaluation of the v5 approach: seeded
   80/20 recording split (seed 42; 1041 train / 262 test), **retrain** the head on
   the train split (BirdNET-Analyzer; mixup/upsampling disabled), evaluate the 262
   **unseen** recordings (raw-audio → tflite → 25 scores, recording-level mean).
   Result (`evaluation/reproduced/v5/`): accuracy **0.8817**, macro AUROC
   **0.9797**, macro AUPRC **0.9207**, full per-class + confusion + ROC/PR + npy
   arrays + `split.json`. **This is a new experiment — never presented as the
   original thesis evaluation.**

## 6. Comparison methodology (operational, live)

`GET /api/v1/models/comparison`. On the recordings where **both** the production
NT model (v5.2 SED) and global BirdNET produced output **and** a verified label
exists (currently **23**), score each by *does it detect the true species?*
(synonym-aware matching, see below):

- **NT Custom Classifier (v5): 23/23 (100%)** — Wilson 95% CI ≈ [85.7%, 100%]
- **BirdNET v2.4 (global): 18/23 (78.3%)** — Wilson 95% CI ≈ [58%, 90%]

**Statistical significance:** an **exact McNemar paired test** (the models are
scored on the *same* recordings, so the rates are paired) currently returns
**p ≈ 0.063 — not significant** at α=0.05: only 5 discordant recordings (all
favouring NT), and with 5 one-sided discordances p cannot fall below 0.0625, so
significance is unreachable until more labelled recordings exist. The point
estimates favour the NT model; the *direction* and the *significance* are reported
separately. Rates carry Wilson 95% intervals; see
[docs/METHODOLOGY.md](docs/METHODOLOGY.md) §1–2 for method + citations.

*(NT rose from 21/23 to 23/23 after a name-truncation parsing bug — mislabelling
Barking Owl → "Masked Owl" and Black Kite → "Whistling Kite" — was fixed in the SED
pipeline; the model had detected both correctly at >0.99. See TECHNICAL_DEBT.md and
`tests/test_detection_parsing.py`.)*

**Synonym-aware matching:** BirdNET emits the IOC common name "Bush Thick-knee"
for "Bush Stone-curlew"; counting that correctly (not a miss) moved BirdNET from
17/23 to 18/23 — an honest correction that *reduces* the NT model's apparent lead.
The synonym table is sourced and conservative; genuine misidentifications
(Azure Kingfisher → "Eurasian Treecreeper") remain misses (METHODOLOGY.md §5).

Ground truth = verified labels from `dataset_metadata.csv`. The predicted species
is displayed per recording so every success/failure is transparent. This is a
per-recording detection test, distinct from the classifier evaluations in §5.

## 7. Annotation methodology

- **Listen & Label** (Recording Workspace → Events & Labelling): the v5.2 SED
  produces species events with timestamps + confidence; annotators play the exact
  3-second window, then mark **Confirm / Reject / Not-sure**. Annotator name is
  captured; labels export as ground-truth CSV (recording id, event, times,
  predicted species/confidence, is_primary, annotator, label, timestamp).
- **Confidence tiers** and **coverage** are surfaced; dual-threshold detection
  separates dominant vs background species.
- **Current limitation:** persistence is client-side (localStorage). A rigorous
  workflow (reviewer roles, expert verification, provenance per label,
  inter-annotator agreement) is the next annotation task (priority #4).

## 8. Limitations

- **v5 production metrics are not independently verified** (documented only). The
  independent reproduction is a *different* classifier instance (retrained,
  augmentation-off) → a conservative proxy, not the deployed model's numbers.
- **Leakage risk in production v5 training** (trained on all data with an internal
  segment-level split) — mitigated conceptually by embeddings, but the exact
  production held-out performance is not persisted.
- **No per-recording GPS** (longitude missing) — spatial analysis uses seeded NT
  sites with illustrative associations.
- **Small evaluation sets** for the operational comparison (23 recordings) and
  several held-out species with support of 1–2. This is now made explicit rather
  than hidden: all reported metrics carry confidence intervals (Wilson /
  Clopper–Pearson / bootstrap) and small-support per-class estimates are flagged
  unreliable; the comparison difference is tested with exact McNemar and is
  **not currently statistically significant** (see [docs/METHODOLOGY.md](docs/METHODOLOGY.md)).
  The remaining mitigation is more labelled data, not more statistics.
- **Xeno-canto provenance ≠ NT field deployment** — recordings come from where
  recordists were (mostly Australia, some Indonesia/PNG/etc.), so this is not a
  longitudinal monitoring dataset; migration analysis needs real field data.

## 9. Future research directions

The scientific trajectory follows the GIS-first, four-stage vision (see
[ROADMAP.md](ROADMAP.md)): from **Recording Intelligence** (acoustic + spatial) to
**Environmental Intelligence** (environmental context layers) to **Spatial
Ecology** (fusing them into ecological insight). Environmental context will
ultimately be provided by **TerraIQ**, a separate environmental-intelligence
engine (Stage 4) — the research questions below increasingly depend on that fused
acoustic + environmental data.

- **Reproducible, persisted v5 evaluation** — retrain v5 with a saved
  recording-level split so production metrics are verifiable (`evaluate_v5.py` is
  the basis). Re-enable mixup/upsampling (install `keras_tuner`).
- **Behaviour classification** — the `type` field (feeding/mating/alarm/
  territorial/flight/duet/…) is labelled raw material for call-type models.
- **Spatial ecology** — habitat suitability, biodiversity hotspots, species-richness
  mapping, environmental change, **fire impact** on species presence, and
  **climate/species relationships** — all require environmental layers (Stage 2)
  joined to detections via PostGIS.
- **Migration & movement analysis** — requires field-deployment data across sites
  and seasons (and recovered geo).
- **Pelican–barramundi conflict monitoring** — spatial + temporal alerting once
  geo + sensor ingest exist.
- **Environmental overlays** — weather/rainfall/wetlands/fire/vegetation/protected
  areas/IPAs/land cover/elevation/hydrology via PostGIS (Stage 2), sourced in-house
  first and from TerraIQ later.
