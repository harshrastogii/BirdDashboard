# NT Bird Acoustic Monitoring Dashboard

**Interactive Visual Analytics System for AI-Powered Biodiversity Acoustic Monitoring**

PRT840 IT Thesis | Charles Darwin University | Supervisor: Dr. Md Rafiqul Islam

## Overview

This project addresses the gap in automated bird species identification for Northern Territory (NT) Australia. Global models like BirdNET (Cornell Lab of Ornithology) fail on Australian species because they were trained primarily on Northern Hemisphere bird sounds. We developed a custom CNN classifier trained specifically on 24 NT bird species, achieving 92.7% test accuracy, and built an interactive Streamlit dashboard for real-time acoustic analysis.

## Key Features

- **Custom CNN Model** — 4-block convolutional neural network (32→64→128→256 filters) trained from scratch on 18,462 mel spectrogram segments across 24 NT bird species
- **BirdNET Comparison** — Side-by-side comparison with BirdNET v2.4, demonstrating why region-specific models are essential
- **Interactive Dashboard** — Streamlit-based interface with audio playback, mel spectrograms, confidence charts, detection timelines, and biodiversity metrics (Shannon & Simpson indices)
- **Data Export** — CSV exports for environmental impact assessments and conservation reports

## Species Covered (24)

Azure Kingfisher, Barking Owl, Black Kite, Blue-winged Kookaburra, Bush Stone-curlew, Channel-billed Cuckoo, Diamond Dove, Galah, Gouldian Finch, Great Bowerbird, Helmeted Friarbird, Hooded Parrot, Laughing Kookaburra, Magpie Goose, Masked Owl, Pheasant Coucal, Rainbow Bee-eater, Red-tailed Black Cockatoo, Sulphur-crested Cockatoo, Tawny Frogmouth, Torresian Crow, Whistling Kite, Willie Wagtail

Including 6 threatened/near-threatened species: Gouldian Finch, Hooded Parrot, Masked Owl, Partridge Pigeon, Red Goshawk, Bush Stone-curlew.

## Project Structure

```
BirdDashboard/
├── app.py                      # Streamlit dashboard (main application)
├── preprocess.py               # Audio → mel spectrogram preprocessing pipeline
├── train_model_v2.py           # Custom CNN training (from scratch)
├── train_model_v3.py           # CNN + spectrogram augmentation
├── train_model_v4.py           # CNN + recording-level split + augmentation
├── train_birdnet_embeddings.py # BirdNET transfer learning (v5)
├── download_dataset_v2.py      # Xeno-canto API v3 dataset acquisition
├── download_additional.py      # Download extra recordings for weak species
├── evaluate_model.py           # Model evaluation and charts
├── requirements.txt            # Python dependencies
├── logo.svg / logo.png         # Dashboard branding
├── spectrograms/
│   ├── label_map.json          # Class index → species name mapping
│   └── species_counts.json     # Per-species segment counts
└── models/                     # Trained models (not in repo — see Setup)
```

## Setup

### 1. Clone and install dependencies

```bash
git clone https://github.com/YOUR_USERNAME/BirdDashboard.git
cd BirdDashboard
python3 -m venv birdenv
source birdenv/bin/activate
pip install -r requirements.txt
```

### 2. Download training data

Audio recordings are sourced from Xeno-canto (xeno-canto.org) via API v3. You need a registered API key.

```bash
python3 download_dataset_v2.py
```

### 3. Preprocess audio

Converts MP3 recordings into 128×130 mel spectrogram segments (3-sec, 22050Hz).

```bash
python3 preprocess.py
```

### 4. Train the model

```bash
python3 train_model_v3.py
```

### 5. Run the dashboard

```bash
python3 -m streamlit run app.py
```

## Model Versions

| Version | Approach | Test Accuracy | Notes |
|---------|----------|--------------|-------|
| v2 | Custom CNN | 92.7% | Segment-level split (inflated) |
| v3 | CNN + Augmentation | 92.7% | Time/freq masking, noise, volume scaling |
| v4 | CNN + Recording-level split | 65.6% | Honest generalisation metric |
| v5 | BirdNET Embeddings | AUPRC 0.98 | Transfer learning approach |

## Data Source

All bird audio recordings are from [Xeno-canto](https://xeno-canto.org/) — a community database of bird sounds. Recordings are used under the terms of the Xeno-canto sharing policy for academic research purposes. We acknowledge all recordists whose contributions made this research possible.

## Team

- **Harsh Rastogi** (Lead)
- Jisan
- Rafel
- Tahmid

## Citation

If you use this work, please cite:

```
Rastogi, H., et al. (2026). Designing an Interactive Visual Analytics System for
AI-Powered Biodiversity Acoustic Monitoring. PRT840 IT Thesis, Charles Darwin University.
```

## License

This project is developed for academic purposes as part of PRT840 IT Thesis at Charles Darwin University.
