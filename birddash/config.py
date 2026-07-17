"""
Centralised configuration for the Avian Observatory platform.

Single source of truth for all filesystem paths, model locations, and shared
pipeline constants. BASE_DIR is derived from this file's location (the repo
root is the package's parent), so the project runs correctly regardless of the
current working directory or the user's home folder. Every path may be
overridden via an environment variable, giving the FastAPI backend and
containerised deployments a clean injection point without code changes.

Usage:
    from birddash import config
    model = load_model(config.NT_MODEL_PATH)
"""

import os
from pathlib import Path

# Repository root = the parent of the birddash package directory. Portable and
# independent of CWD / username.
_PACKAGE_DIR = Path(__file__).resolve().parent
BASE_DIR = Path(os.environ.get("BIRDDASH_BASE_DIR", _PACKAGE_DIR.parent))


def _path(env_var: str, *default_parts: str) -> Path:
    """Resolve a path, allowing an environment-variable override.

    Relative overrides are resolved against BASE_DIR; absolute overrides are
    honoured as-is.
    """
    override = os.environ.get(env_var)
    if override:
        p = Path(override)
        return p if p.is_absolute() else (BASE_DIR / p)
    return BASE_DIR.joinpath(*default_parts)


# --- Directories ---------------------------------------------------------
MODELS_DIR = _path("BIRDDASH_MODELS_DIR", "models")
SPECTROGRAMS_DIR = _path("BIRDDASH_SPECTROGRAMS_DIR", "spectrograms")
SAMPLE_AUDIO_DIR = _path("BIRDDASH_SAMPLE_AUDIO_DIR", "sample_audio")
SAMPLE_AUDIO_OLD_DIR = _path("BIRDDASH_SAMPLE_AUDIO_OLD_DIR", "sample_audio_old")
DETECTIONS_DIR = _path("BIRDDASH_DETECTIONS_DIR", "detections")

# Active BirdNET results directory consumed by the dashboard. (Named
# "birdnet_results2" historically; kept as-is to avoid data churn. The older
# "birdnet_results" directory was stale and has been removed.)
BIRDNET_RESULTS_DIR = _path("BIRDDASH_BIRDNET_RESULTS_DIR", "birdnet_results2")

# Ground-truth labels captured via the Listen & Label workflow.
LABELS_DIR = _path("BIRDDASH_LABELS_DIR", "detections", "labels")

# --- Model + label artifacts --------------------------------------------
# Custom NT CNN (24-class segment classifier) used by the main dashboard.
NT_MODEL_PATH = _path("BIRDDASH_NT_MODEL_PATH", "models", "nt_bird_cnn_best.keras")
NT_LABEL_MAP_PATH = _path("BIRDDASH_NT_LABEL_MAP_PATH", "spectrograms", "label_map.json")

# BirdNET-embeddings TFLite classifier used by the multi-species detector.
CLASSIFIER_TFLITE_PATH = _path(
    "BIRDDASH_CLASSIFIER_TFLITE_PATH", "models", "NT_Bird_BirdNET_Classifier.tflite"
)
CLASSIFIER_LABELS_PATH = _path(
    "BIRDDASH_CLASSIFIER_LABELS_PATH", "models", "NT_Bird_BirdNET_Classifier_Labels.txt"
)

# --- Scripts -------------------------------------------------------------
DETECTOR_SCRIPT = _path("BIRDDASH_DETECTOR_SCRIPT", "multi_species_detector_v5_1.py")

# --- Audio / inference parameters (shared, must match training pipeline) --
SAMPLE_RATE = 22050
SEGMENT_DURATION = 3.0
N_MELS = 128

# Mel-spectrogram parameters for NT CNN inference (MUST match preprocess.py).
NT_N_FFT = 2048
NT_HOP_LENGTH = 512
NT_FMIN = 150
NT_FMAX = 15000

# Silent-segment gate (RMS below this is skipped, same as training).
SILENCE_RMS_THRESHOLD = 0.001

# Mel-spectrogram parameters for the display spectrogram (dashboard heatmap).
DISPLAY_SPEC_DURATION = 60
DISPLAY_SPEC_FMAX = 8000
