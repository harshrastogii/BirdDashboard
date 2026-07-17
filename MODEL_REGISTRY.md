# MODEL_REGISTRY.md — Avian Observatory

> Full history of every model, its purpose, scientific rationale, and metric
> provenance. The machine-readable source is `evaluation/registry.json` (served
> at `GET /api/v1/models/registry`); this document is the human narrative.
> Companion: [SCIENTIFIC_METHOD.md](SCIENTIFIC_METHOD.md) · [DECISIONS.md](DECISIONS.md)

## Metric provenance taxonomy (critical — never conflate)

| Kind | Meaning | Example |
|---|---|---|
| **Documented** | Reported in the thesis/README, **no** traceable evaluation artefact exists. Shown as *"Documented · not verified"*. **Never presented as experimentally verified.** | v5 AUPRC 0.98 / AUROC 0.99 |
| **Original evaluation (verified/traceable)** | Recomputed from the **original** saved evaluation artefacts (the original experiment, reproduced for traceability). | CNN v2/v3/v4 from `models/y_test_*.npy` |
| **Independent reproduction** | A **new** experiment (fresh split + retrain). Provided for reproducibility; **not** the original experiment. | v5 recording-level held-out eval |

An **exhaustive** repository + git-history search (2026-07-17) found **no
original v5 evaluation artefacts** (predictions, probabilities, labels, ROC/PR
data, notebooks, TensorBoard logs, caches). The v5 0.98/0.99 exist only in
`README.md` and as hardcoded literals in `generate_charts.py`. Therefore the v5
documented values remain *documented, not verified*, and the reproduction below
is a separate experiment.

## Model timeline

### v2 — Custom CNN (mel-spectrograms) · HISTORICAL
- **What:** 4-conv-block CNN trained on 18,462 mel-spectrogram 3s segments, 24 NT species (`models/nt_bird_cnn_best.keras`).
- **Rationale:** first attempt — learn NT species from spectrograms directly.
- **Metrics (original evaluation, verified from `models/y_test_probs.npy` + `y_test_true.npy`, 2770 test segments):**
  accuracy **0.9267**, macro F1 **0.9169**, macro AUROC **0.997**, macro AUPRC **0.9643**.
- **Why superseded:** the 92.7% is a **segment-level** split — segments from one
  recording appear in both train and test → **data leakage** → inflated.
- **Artefacts:** `evaluation/original/cnn_v2/` (metrics.json, confusion_matrix.csv, roc_curve.csv, pr_curve.csv).

### v3 — CNN + augmentation · HISTORICAL
- **What:** v2 + SpecAugment/noise/volume/shift augmentation.
- **Metrics (verified):** accuracy **0.9274**, macro AUROC 0.997, macro AUPRC 0.9693 (`evaluation/original/cnn_v3/`).
- **Finding:** augmentation didn't materially change segment-level accuracy — the leakage, not capacity, was the ceiling.

### v4 — CNN, recording-level split · HISTORICAL (the honesty check)
- **What:** same architecture, but train/test split at the **recording** level (no segment leakage).
- **Metrics (verified):** accuracy **0.6661**, macro F1 0.5346, macro AUROC 0.9436, macro AUPRC 0.6621 (`evaluation/original/cnn_v4/`).
- **Significance:** **exposed the leakage** — honest generalisation was far below 92.7%. This is the pivotal scientific result that motivated v5.

### v5 — NT Custom Classifier (BirdNET embeddings + custom head) · PRODUCTION
- **What:** transfer learning — freeze BirdNET v2.4's feature extractor, train a
  shallow head (128 hidden units, dropout 0.25) on 1024-d embeddings. 25 classes
  (adds **Red_Goshawk**). `models/NT_Bird_BirdNET_Classifier.tflite` (raw 48 kHz
  3s audio → 25 scores; feature extractor baked into the tflite).
- **Rationale:** bypass leakage at the representational level — BirdNET embeddings
  already encode acoustic structure, so the NT head needs little data and
  generalises better than a from-scratch CNN.
- **Trained via:** `train_birdnet_embeddings.py` → `birdnet_analyzer.train` on all
  of `training_data/` with an internal (segment-level, **not persisted**) val split.
- **Documented metrics (NOT verified):** AUPRC 0.98, AUROC 0.99 (thesis/README).
  These came from BirdNET's **internal validation** during training (a leaky,
  segment-level split) — confirmed by observing `birdnet_analyzer.train` printing
  ~0.998 val AUPRC/AUROC. No original held-out artefacts exist.
- **Independent reproduction (verified, `evaluation/reproduced/v5/`):** recording-level
  held-out — a classifier **retrained on an 80% recording-level train split** (1041
  recordings, seed 42, mixup/upsampling disabled) and **evaluated on 262 unseen
  recordings**. Result: accuracy **0.8817**, macro AUROC **0.9797**, macro AUPRC
  **0.9207**, 25-species per-class metrics + confusion + ROC/PR curves. **This is a
  separate experiment — not the original thesis evaluation.** (Augmentation was
  disabled because the current BirdNET-Analyzer crashes in its upsampling path on
  this split; recorded in the metrics provenance. It yields a conservative estimate.)

### v5.2 — Multi-Species Sound Event Detection · PRODUCTION (operational pipeline)
- **What:** sliding-window, dual-threshold SED over the v5 classifier
  (`birddash/detection.py`). Higher threshold for the dominant species, lower for
  background species; merges adjacent windows into events with timestamps.
- **This is the operational NT inference throughout Avian Observatory** — the
  Recording Workspace, dashboard, and comparison all use it.

### BirdNET v2.4 (global) · BASELINE
- **What:** the global pretrained BirdNET model (~6,000 species).
- **Role:** comparison baseline. Routinely misidentifies NT species (e.g. Azure
  Kingfisher → "Eurasian Treecreeper"), which is the platform's core finding.

## Operational comparison (live, data-driven — `GET /models/comparison`)

On the **same 23** recordings (those with a verified label AND output from both
models), scored by *does the model detect the recording's true species?*
(synonym-aware):
- **NT Custom Classifier (v5): 23/23 (100%)** — Wilson 95% CI ≈ [85.7%, 100%]
- **BirdNET v2.4 (global): 18/23 (78.3%)** — Wilson 95% CI ≈ [58%, 90%]
- **Exact McNemar paired test: p ≈ 0.063 — not statistically significant** at α=0.05
  (5 discordant recordings, all favouring NT). Direction favours the NT model; with
  only 5 one-sided discordances p cannot fall below 0.0625, so significance is
  unreachable at this sample size — more labelled recordings are needed.

Ground truth = **verified labels** from `training_data/dataset_metadata.csv`
(filename → common name), matched **synonym-aware** (BirdNET's "Bush Thick-knee" =
"Bush Stone-curlew"; genuine misidentifications remain misses). Enabling synonym
handling moved BirdNET from 17/23 to 18/23 — an honest correction that *narrows*
the NT lead. **NT rose from 21/23 to 23/23** after fixing a name-truncation bug in
the SED pipeline that had mislabelled Barking Owl → "Masked Owl" and Black Kite →
"Whistling Kite" (the model actually detected both correctly at >0.99; fix +
regression tests: `birddash/detection.py`, `tests/test_detection_parsing.py`). Each recording shows what each model predicted, so every
success/failure is transparent. Rates carry Wilson intervals and the difference an
exact McNemar test — see [docs/METHODOLOGY.md](docs/METHODOLOGY.md). This is
distinct from the research metrics above (a live per-recording detection test, not
a held-out classifier eval).

## Adding a future model (v6, v7, …)

1. Add the model artefact (e.g. a new `.tflite`) and, if it becomes production,
   wire it into `birddash`.
2. Produce evaluation artefacts into `evaluation/original/<key>/` (if from
   original saved outputs) or `evaluation/reproduced/<key>/` (independent).
3. Append an entry to `evaluation/registry.json` with metadata + `documented`
   (if applicable) + `evaluations[]` pointing at the artefact dirs.
4. Nothing else — the API and UI render the registry generically.
