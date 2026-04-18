# NT Bird Acoustic Monitor

**Interactive Visual Analytics System for AI-Powered Biodiversity Acoustic Monitoring**

*PRT840 IT Thesis | Charles Darwin University | Supervisor: Dr. Md Rafiqul Islam*

An AI-powered bioacoustic monitoring system for Northern Territory bird species.
Combines region-specific deep learning classifiers with multi-species sound event
detection and an interactive dashboard for field ecologists, conservation managers,
and policy makers.

## Why this project exists

BirdNET (Kahl et al., 2021) is the current gold-standard tool for AI-based
bioacoustic monitoring globally. Its training data skews toward Northern
Hemisphere species. On Northern Territory birds, BirdNET v2.4 routinely
misidentifies local species as European or North American birds — a Laughing
Kookaburra gets classified as a European Wren; a Willie Wagtail as a North
American owl — often with 99% confidence.

This project builds NT-specific classifiers that outperform BirdNET on
Northern Territory species, and integrates them into an interactive dashboard
for real-world biodiversity monitoring use cases.

## What's been built

### Models (five iterations)

| Version | Approach | Result | Purpose |
|---------|----------|--------|---------|
| v2 | Custom CNN (4 conv blocks, 32→64→128→256) trained on 18,462 mel spectrogram segments | 92.7% segment-level test accuracy | Baseline NT classifier |
| v3 | v2 + five data augmentations (time/freq mask, noise, volume, shift) | 92.7% | Tested augmentation hypothesis |
| v4 | Same architecture, recording-level train/test split | 66.6% | Exposed segment-level label leakage |
| v5 | BirdNET v2.4 embeddings + custom 25-class head (transfer learning) | AUPRC 0.98, AUROC 0.99 | Bypasses v3/v4 leakage issue |
| v5.1 (SED) | v5 + sliding-window sound event detection + dual threshold | Multi-species detection with timestamps | Addresses multi-class classification on single recordings |

### Dashboard

A Streamlit-based interactive dashboard (`app.py`) supporting:

- Side-by-side comparison of BirdNET v2.4 vs the custom NT model
- Per-recording confidence timelines and top-5 species predictions
- Biodiversity metrics (Shannon diversity, Simpson diversity, species richness)
- Multi-species sound event detection with timestamped event tables and CSV export
- Audio file upload with automatic BirdNET analysis integration

### Validated findings

- BirdNET v2.4 achieves ~0% accuracy on NT species
- Custom CNN (v3) achieves 92.7% on segment-level splits but 66.6% on
  recording-level splits, revealing segment-level label leakage in training data
- v5 transfer learning addresses the leakage issue architecturally
- Multi-species detection works well on long, acoustically complex recordings
  (e.g. 139-second Willie Wagtail recording → 8 species detected at varied
  timestamps with confidences 0.27 – 0.94). Short single-species recordings
  remain fundamentally limited by the information available in the signal.

## Repository structure

```
BirdDashboard/
├── app.py                              Streamlit dashboard entry point
├── multi_species_detector_v5_1.py      Active multi-species SED detector (v5-based)
├── multi_species_section.py            Streamlit UI component for multi-species tab
├── batch_validate.py                   Batch validation across multiple recordings
├── generate_charts.py                  Evaluation chart generation (v2/v3/v4/v5 comparison)
├── evaluate_model.py                   Per-species evaluation against held-out test set
├── preprocess.py                       Audio → mel spectrogram preprocessing
├── train_model_v2.py                   v2 training (custom CNN, no augmentation)
├── train_model_v3.py                   v3 training (CNN + 5 augmentations)
├── train_model_v4.py                   v4 training (recording-level split)
├── train_birdnet_embeddings.py         v5 training (BirdNET embeddings + custom head)
├── download_dataset.py                 Xeno-canto bulk downloader
├── download_dataset_v2.py              Xeno-canto downloader with pagination fix
├── download_additional.py              Supplementary species recording fetcher
├── archive/
│   └── model_iterations/               Superseded detector scripts (research history)
├── docs/
│   └── week7_demo/                     Curated charts for Week 7 supervisor demo
├── detections/
│   └── validation/                     6-recording validation set (committed)
│   └── (per-recording outputs)         Ad-hoc experimental results (gitignored)
├── models/                             Trained model weights (gitignored — too large)
├── training_data/                      Xeno-canto audio (gitignored — too large)
├── sample_audio/                       Demo recordings (gitignored)
└── evaluation/                         Evaluation charts
```

## How to run

### Prerequisites

```bash
python3 -m venv birdenv
source birdenv/bin/activate
pip install -r requirements.txt
```

### Regenerate data pipeline (optional, only if reproducing from scratch)

```bash
python3 download_dataset_v2.py       # Download Xeno-canto recordings (~90 min)
python3 preprocess.py                # Generate mel spectrograms (~15 min)
python3 train_model_v3.py            # Train v3 custom CNN (~16 hrs on MacBook Air)
python3 train_birdnet_embeddings.py  # Train v5 BirdNET classifier (~7 min)
```

### Run the dashboard

```bash
source birdenv/bin/activate
python3 -m streamlit run app.py
```

### Run multi-species detection from the command line

```bash
python3 multi_species_detector_v5_1.py \
    --audio sample_audio/Willie_Wagtail_XC1001943.mp3
```

With parameters:

```bash
python3 multi_species_detector_v5_1.py \
    --audio <path_to_mp3> \
    --primary-conf 0.5 \
    --secondary-conf 0.25 \
    --sensitivity 1.25 \
    --overlap 2.0 \
    --top-k 3
```

### Run batch validation

```bash
python3 batch_validate.py
```

## Species coverage

Currently supports 25 Northern Territory bird species, including the
threatened Gouldian Finch, Partridge Pigeon, Red Goshawk, Bush Stone-curlew,
Masked Owl, and Hooded Parrot.

## Data

All training audio is sourced from Xeno-canto (xeno-canto.org) under their
sharing policy for academic research. We acknowledge all recordists whose
contributions made this research possible.

## References

Key references for the project approach:

- Kahl, S., Wood, C. M., Eibl, M., & Klinck, H. (2021). BirdNET: A deep
  learning solution for avian diversity monitoring. *Ecological Informatics, 61.*
- Ghani, B., Denton, T., Kahl, S., & Klinck, H. (2023). Global birdsong
  embeddings enable superior transfer learning for bioacoustic classification.
  *Scientific Reports.*
- Stowell, D. (2022). Computational bioacoustics with deep learning: a review
  and roadmap. *PeerJ.*

Full reference list in the Assessment 2 interim report.

## License

Academic research project. Code contributions welcome via pull request.
Contact: Harsh Rastogi (S386401) via CDU student email.
