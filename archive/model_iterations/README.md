# Archive — Superseded Model Iterations

This folder preserves earlier iterations of the multi-species detection pipeline.
The scripts here are **not maintained** and are kept for research traceability —
so we can always point to "this is what v3 looked like before we diagnosed
segment-level leakage" or "this is the pre-dual-threshold v5 detector."

For the current, active detector, see `multi_species_detector_v5_1.py` in the
repo root.

## Contents

### `multi_species_detector.py` (original v3-based detector, 18 April 2026 15:12)

First attempt at multi-species sound event detection. Used the custom v3 CNN
(`nt_bird_cnn_best.keras`) directly as the per-window classifier with a simple
sliding-window approach.

**Why superseded:** On a training-pool recording (Blue-winged Kookaburra
XC1001935), the model returned saturated single-species predictions (100%
Blue-winged Kookaburra) across all 53 windows even at confidence threshold 0.95.
This empirically confirmed segment-level label leakage in the v3 CNN —
segments from any Blue-winged Kookaburra training recording were labelled
"Blue-winged Kookaburra" regardless of what was acoustically present in that
specific segment, so the model had learned to memorise recording identity
rather than per-window content.

This diagnostic finding motivated the switch to v5 (BirdNET embeddings), whose
backbone was trained at Cornell on segment-level supervision and does not
exhibit the same recording-level bias.

### `multi_species_detector_v5.py` (first v5-based detector, 18 April 2026 15:29)

Second iteration. Replaced the v3 classifier with the v5 BirdNET-embeddings
classifier (`NT_Bird_BirdNET_Classifier.tflite`). Produced varied multi-species
output on held-out recordings, confirming that v5 does not exhibit segment
leakage.

**Why superseded:** On training-pool recordings, the primary species still
saturated at 1.000 confidence while legitimate secondary species (e.g. Willie
Wagtail at 0.757) were hidden below the default detection threshold. The script
used a single global threshold, so raising sensitivity to surface secondaries
also produced noise from low-confidence primary-species leakage.

Replaced by v5.1 which introduced a dual-threshold scheme: separate thresholds
for primary (0.5) and secondary (0.25) species, with top-K applied only to
secondaries so strong background detections aren't crowded out by the
saturated primary.

### `multi_species_ui.py` (first Streamlit UI component, 18 April 2026 15:12)

Initial design for a Streamlit tab that would import the detector functions
directly into `app.py`.

**Why superseded:** Direct-import integration risked tangling with the existing
`app.py` module load order (TensorFlow + BirdNET + Streamlit caching).
Replaced by `multi_species_section.py` which calls the detector as a subprocess —
cleaner separation, no import conflicts, and the subprocess model aligns with
how BirdNET-Analyzer is designed to be used.

## Timeline of iterations

```
15:12  multi_species_detector.py          (v3-based, revealed leakage)
15:29  multi_species_detector_v5.py       (v5-based, single threshold)
15:40  multi_species_detector_v5.1.py     (v5 + dual threshold)
17:00  + top-K fix (primary doesn't consume secondary slot)
19:00  + MP3 fallback re-encoding via librosa
```

The currently active `multi_species_detector_v5_1.py` in the repo root contains
all the fixes above, despite the `_v5_1` filename suffix.
