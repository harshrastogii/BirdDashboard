# NT Bird Acoustic Monitor

**Interactive Visual Analytics System for AI-Powered Biodiversity Acoustic Monitoring**

*PRT840 Final Thesis Project · Master of Data Science (SDASC3) · Charles Darwin University · Supervisor: Dr. Md Rafiqul Islam*

An AI-powered bioacoustic monitoring system for Northern Territory bird species.
Combines region-specific deep learning classifiers with multi-species sound event
detection and an interactive dashboard designed for field ecologists, conservation
managers, and policy makers.

---

## Why this project exists

BirdNET (Kahl et al., 2021) is the current gold-standard tool for AI-based
bioacoustic monitoring globally. Its training data skews heavily toward Northern
Hemisphere species. On Northern Territory birds, BirdNET v2.4 routinely
misidentifies local species as European or North American birds — a Laughing
Kookaburra gets classified as a European Wren; a Willie Wagtail as a North
American owl — often with 99% confidence.

This project builds NT-specific classifiers that materially outperform BirdNET
on Northern Territory species, and integrates them into an interactive
dashboard for real-world biodiversity monitoring use cases.

---

## What's been built

### Models (five iterations)

| Version | Approach | Result | Purpose |
|---------|----------|--------|---------|
| v2 | Custom CNN (4 conv blocks, 32→64→128→256) trained on 18,462 mel spectrogram segments | 92.7% segment-level test accuracy | Baseline NT classifier |
| v3 | v2 + five data augmentations (time/freq mask, noise, volume, shift) | 92.7% segment-level | Tested augmentation hypothesis |
| v4 | Same architecture, recording-level train/test split | 66.6% recording-level | Exposed segment-level data leakage |
| v5 | BirdNET v2.4 embeddings + custom 25-class head (transfer learning) | AUPRC 0.98, AUROC 0.99 | Bypasses leakage at the representational level |
| v5.1 (SED) | v5 + sliding-window sound event detection + dual threshold | Multi-species detection with timestamps | Multi-species classification on single recordings |

### Dashboard

A Streamlit-based interactive dashboard (`app.py`) supporting:

- Side-by-side comparison of BirdNET v2.4 vs the custom NT model
- Per-recording confidence timelines and top-5 species predictions
- Biodiversity metrics (Shannon diversity, Simpson diversity, species richness)
- Multi-species sound event detection with timestamped event tables and CSV export
- **Listen and Confirm verification interface** — click any detected event to
  audition the exact 3-second window and mark it as confirmed, rejected, or
  uncertain; exports as a ground-truth CSV for hand-labelling workflows
- Audio file upload with automatic BirdNET-Analyzer integration

### Validated findings

- BirdNET v2.4 achieves ≈0% accuracy on NT species under our evaluation.
- Custom CNN (v3) achieves 92.7% on segment-level splits but 66.6% on
  recording-level splits, empirically demonstrating segment-level data leakage.
- v5 transfer learning addresses the leakage at the representational level.
- Multi-species sound event detection achieves 4/6 (66.7%) primary-species
  identification across the six-recording validation set — closely mirroring
  the v4 recording-level baseline of 66.6%.
- The Willie Wagtail recording (139 s) returned the primary species correctly
  plus seven secondary species at distinct timestamps with confidences between
  0.27 and 0.94.

---

## Environment configuration

### System requirements

- **Operating system:** macOS 12+ or Linux (tested on macOS 14, Apple Silicon)
- **Python:** 3.10 – 3.13
- **Disk:** ~3 GB free (training data, models, dependencies)
- **RAM:** 8 GB minimum, 16 GB recommended for training
- **GPU:** Not required; all training runs on CPU (Apple Silicon or Intel)

### External tools

- **ffmpeg** — required by librosa for audio decoding. Install via Homebrew on macOS:
  ```bash
  brew install ffmpeg
  ```
  or via apt on Linux: `sudo apt install ffmpeg`

### Python dependencies

All Python dependencies are listed in `requirements.txt`. Key packages:

| Package | Version | Purpose |
|---------|---------|---------|
| `tensorflow` | 2.x | Custom CNN training and inference (v2-v4) |
| `keras` | 3.x | High-level model API |
| `birdnet-analyzer` | 2.4.0 | BirdNET v2.4 inference and embedding extraction |
| `librosa` | 0.10+ | Audio loading, resampling, mel-spectrogram generation |
| `soundfile` | 0.12+ | Audio I/O |
| `numpy`, `pandas` | latest | Numerical and tabular computation |
| `matplotlib` | 3.7+ | Static visualisations and report figures |
| `streamlit` | 1.30+ | Interactive dashboard |
| `plotly` | 5.15+ | Interactive charts in the dashboard |
| `scikit-learn` | 1.3+ | Evaluation metrics, classification reports |

### Installation

```bash
git clone https://github.com/harshrastogii/BirdDashboard.git
cd BirdDashboard
python3 -m venv birdenv
source birdenv/bin/activate            # On Windows: birdenv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

---

## Model artefacts and data

Trained model files and large datasets are excluded from version control
(`.gitignore`) because of GitHub's file-size limits. To run the system, you
must either retrain from scratch (see the reproduction pipeline below) or
obtain the artefacts via one of the following methods:

| Artefact | Location | Size | How to obtain |
|----------|----------|------|---------------|
| `models/nt_bird_cnn_best.keras` | `models/` | ~15 MB | Re-train via `python3 train_model_v3.py`, or request from the project owner |
| `models/NT_Bird_BirdNET_Classifier.tflite` | `models/` | ~5 MB | Re-train via `python3 train_birdnet_embeddings.py`, or request from the project owner |
| `models/NT_Bird_BirdNET_Classifier_Labels.txt` | `models/` | <1 KB | Generated automatically alongside the .tflite file |
| `spectrograms/X_train.npy`, `X_test.npy`, etc. | `spectrograms/` | ~500 MB total | Generated by `python3 preprocess.py` from raw Xeno-canto audio |
| `training_data/<species>/*.mp3` | `training_data/` | ~2 GB | Downloaded via `python3 download_dataset_v2.py` from Xeno-canto |
| `sample_audio/*.mp3` | `sample_audio/` | ~50 MB | Subset of training_data used for dashboard demos; populate manually from training_data after download |

Examiners requiring direct access to the trained artefacts for assessment
purposes can request them via the contact email at the bottom of this
document.

---

## Parameter settings

### Custom CNN training (v2/v3/v4)

These parameters are set in `train_model_v2.py`, `train_model_v3.py`, and
`train_model_v4.py`:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `BATCH_SIZE` | 64 | Mini-batch size |
| `EPOCHS` | 95 (v2), 120 (v3/v4) | Maximum training epochs |
| `LEARNING_RATE` | 0.001 | Adam optimiser learning rate |
| `EARLY_STOPPING_PATIENCE` | 12 | Epochs without validation improvement before stop |
| `DROPOUT_RATE` | 0.25, 0.3, 0.4, 0.5 | Progressive dropout per conv block |
| `AUGMENTATION_PROBABILITY` | 0.5 | Per-augmentation application probability (v3+) |
| `TIME_MASK_MAX` | 20 | Maximum time-mask width in frames (v3+) |
| `FREQ_MASK_MAX` | 15 | Maximum frequency-mask width in mel bins (v3+) |
| `NOISE_STD` | 0.03 | Gaussian noise standard deviation (v3+) |
| `VOLUME_RANGE` | [0.7, 1.3] | Volume scaling range (v3+) |
| `TIME_SHIFT_MAX` | 15 | Maximum time-shift in frames (v3+) |

### v5 BirdNET embeddings classifier

Set in `train_birdnet_embeddings.py`:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `HIDDEN_UNITS` | 128 | Hidden layer width in the custom head |
| `DROPOUT` | 0.25 | Dropout in the custom head |
| `MIXUP_ALPHA` | 0.4 | Mixup augmentation strength |
| `EPOCHS` | 100 | Maximum training epochs |
| `MINORITY_UPSAMPLE_RATIO` | 0.5 | Upsample minority classes to this fraction of majority class count |

### Multi-species sound event detection (v5.1)

Set in `multi_species_detector_v5_1.py` and exposed via the dashboard sliders:

| Parameter | Default | Range | Description |
|-----------|---------|-------|-------------|
| `--primary-conf` | 0.5 | 0.3 – 0.95 | Confidence threshold for the dominant species in each window |
| `--secondary-conf` | 0.25 | 0.1 – 0.7 | Confidence threshold for background species in each window |
| `--sensitivity` | 1.25 | 0.75 – 1.5 | BirdNET detector sensitivity; higher catches fainter calls |
| `--overlap` | 2.0 | 0.0 – 2.9 | Window overlap in seconds; 2.0 = 1-second hop on 3-second windows |
| `--top-k` | 3 | 1 – 5 | Maximum simultaneous secondary species per window |
| `--suppress-primary` | False | flag | If set, suppresses the primary species in the visualisation for clearer background view |
| `--no-plot` | False | flag | If set, skips matplotlib plot generation (used when the dashboard renders its own) |

### Audio preprocessing

Set in `preprocess.py`:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `SAMPLE_RATE` | 22050 | Resample target in Hz |
| `SEGMENT_DURATION` | 3.0 | Segment length in seconds |
| `N_FFT` | 2048 | FFT window size |
| `HOP_LENGTH` | 512 | STFT hop length in samples |
| `N_MELS` | 128 | Number of mel-frequency bands |
| `FMIN`, `FMAX` | 150, 15000 | Frequency range in Hz |
| `RMS_SILENCE_THRESHOLD` | 0.001 | Segments below this RMS are discarded as silent |

---

## Execution steps

### Quickstart (run the dashboard with existing artefacts)

```bash
git clone https://github.com/harshrastogii/BirdDashboard.git
cd BirdDashboard
python3 -m venv birdenv
source birdenv/bin/activate
pip install -r requirements.txt
# Obtain model artefacts (see Model artefacts and data above)
# Place sample audio files in sample_audio/
python3 -m streamlit run app.py
# Dashboard opens at http://localhost:8501
```

### Full reproduction pipeline (from scratch)

```bash
source birdenv/bin/activate

# 1. Download training audio (~90 min, ~2 GB)
python3 download_dataset_v2.py

# 2. Generate mel spectrograms (~15 min, ~500 MB)
python3 preprocess.py

# 3. Train the custom CNN (v3, with augmentation, ~16 hours on MacBook Air)
python3 train_model_v3.py

# 4. Train the v4 recording-level model (~12 hours)
python3 train_model_v4.py

# 5. Train the v5 BirdNET-embeddings classifier (~7 minutes)
python3 train_birdnet_embeddings.py

# 6. Generate evaluation charts
python3 generate_charts.py

# 7. Run the dashboard
python3 -m streamlit run app.py
```

### Run multi-species detection from the command line

Default parameters:
```bash
python3 multi_species_detector_v5_1.py \
    --audio sample_audio/Willie_Wagtail_XC1001943.mp3
```

With explicit parameters:
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

Output is written to `detections/validation/validation_summary.json` and individual
per-recording JSON files in `detections/`.

---

## Repository structure

```
BirdDashboard/
├── app.py                              Streamlit dashboard entry point
├── multi_species_detector_v5_1.py      Active multi-species SED detector (v5-based)
├── multi_species_section.py            Streamlit UI component with Listen & Confirm
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
├── requirements.txt                    Pinned Python dependencies
├── README.md                           This file
├── archive/
│   └── model_iterations/               Superseded detector scripts (research history)
├── docs/
│   └── week7_demo/                     Curated charts for supervisor demos
├── detections/
│   ├── validation/                     6-recording validation set (committed)
│   └── (per-recording outputs)         Ad-hoc experimental results (gitignored)
├── models/                             Trained model weights (gitignored — see above)
├── spectrograms/                       Preprocessed mel spectrograms (gitignored)
├── training_data/                      Xeno-canto raw audio (gitignored)
├── sample_audio/                       Demo recordings used by the dashboard (gitignored)
└── evaluation/                         Evaluation charts and per-species results
```

---

## Species coverage

The system targets 25 Northern Territory bird species:

**Raptors and kites:** Black Kite, Whistling Kite, Red Goshawk
**Parrots and cockatoos:** Galah, Sulphur-crested Cockatoo, Red-tailed Black
Cockatoo, Hooded Parrot
**Kingfishers and kookaburras:** Azure Kingfisher, Blue-winged Kookaburra,
Laughing Kookaburra
**Owls and nightjars:** Barking Owl, Masked Owl, Tawny Frogmouth
**Pigeons and doves:** Diamond Dove, Partridge Pigeon
**Other:** Magpie Goose, Channel-billed Cuckoo, Pheasant Coucal, Bush
Stone-curlew, Great Bowerbird, Helmeted Friarbird, Rainbow Bee-eater,
Torresian Crow, Willie Wagtail, **Gouldian Finch** (threatened)

Six species are classified as threatened or near-threatened under Australian
federal legislation, including the Gouldian Finch, Partridge Pigeon, Red
Goshawk, Bush Stone-curlew, Masked Owl, and Hooded Parrot.

---

## Data source

All training audio is sourced from Xeno-canto (https://xeno-canto.org) under
their sharing policy for academic and research use. Recordings are
attributed to individual recordists in the Xeno-canto metadata, and we
acknowledge their contributions which made this research possible.

The recordings were accessed via the Xeno-canto API v3 between February and
April 2026. The final dataset comprises 1,303 recordings yielding 18,462
mel-spectrogram segments.

---

## Key references

Full reference list (34 sources) appears in the Assessment 3 final report
References section. Key foundational works:

- Kahl, S., Wood, C. M., Eibl, M., & Klinck, H. (2021). BirdNET: A deep
  learning solution for avian diversity monitoring. *Ecological Informatics*, 61.
- Ghani, B., Denton, T., Kahl, S., & Klinck, H. (2023). Global birdsong
  embeddings enable superior transfer learning for bioacoustic classification.
  *Scientific Reports*, 13.
- Roberts, D. R., et al. (2017). Cross-validation strategies for data with
  temporal, spatial, hierarchical, or phylogenetic structure. *Ecography*, 40(8).
- Stowell, D. (2022). Computational bioacoustics with deep learning: a review
  and roadmap. *PeerJ*, 10.
- Marquez-Rodriguez, J., et al. (2025). A Bird Song Detector for improving
  bird identification through Deep Learning: a case study from Donana.
  *arXiv preprint arXiv:2503.15576*.
- Hendrycks, D., & Gimpel, K. (2017). A baseline for detecting misclassified
  and out-of-distribution examples in neural networks. *ICLR*.

---

## Project status

This repository accompanies the PRT840 Assessment 3 final submission (May 2026).
The system is research-grade and is being developed further beyond the scope
of this assessment, with the secondary-species validation workflow (supported
by the Listen and Confirm interface) as the next primary work item.

---

## License and contact

This is an academic research project submitted in partial fulfilment of the
Master of Data Science (SDASC3) at Charles Darwin University. Code and
documentation are made available under Charles Darwin University's academic
policy for student research outputs.

**Author:** Harsh Rastogi (S386401)
**Team (Group 33):** Jisan (S386804), Rafel (S387949), Tahmid (S391744)
**Supervisor:** Dr. Md Rafiqul Islam
**Institution:** Charles Darwin University, Faculty of Science and Technology
**Contact:** Harsh Rastogi via CDU student email
