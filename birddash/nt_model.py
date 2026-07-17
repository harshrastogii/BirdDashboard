"""Custom NT bird CNN (v2/v3): model loading and segment-level prediction.

HISTORICAL model, retained intact for research reproducibility, historical
evaluation, and thesis purposes. It is NOT the production model — the NT Custom
Classifier (v5), deployed via the v5.2 multi-species SED pipeline (see
birddash/detection.py), is the flagship production NT model throughout Avian
Observatory. The CNN is presented only in the Model Evolution / Research
sections of the UI (its 92.7% segment-level accuracy was inflated by
segment-level data leakage; see the v4 recording-level evaluation).

The preprocessing here MUST match the training pipeline exactly (preprocess.py):
3-second non-overlapping segments, 128 mel bands @ 22050 Hz, n_fft=2048,
hop=512, fmin=150, fmax=15000, per-segment [0, 1] normalisation, and an RMS
silence gate. Parity is enforced by the golden-file tests in tests/.
"""

import json
import os

import numpy as np
import pandas as pd
import librosa
import tensorflow as tf

from birddash import config


def load_model(model_path=config.NT_MODEL_PATH):
    """Load the custom NT bird CNN model, or None if the file is absent."""
    if os.path.exists(model_path):
        return tf.keras.models.load_model(model_path)
    return None


def load_label_map(label_map_path=config.NT_LABEL_MAP_PATH) -> dict:
    """Load the class-index -> species-name mapping, or {} if absent."""
    if os.path.exists(label_map_path):
        with open(label_map_path, "r") as f:
            return json.load(f)
    return {}


def predict(audio_path, model, label_map,
            segment_duration=config.SEGMENT_DURATION,
            sr=config.SAMPLE_RATE,
            n_mels=config.N_MELS) -> pd.DataFrame:
    """Run the NT CNN over an audio file.

    Splits into non-overlapping segments, skips silent ones, generates a mel
    spectrogram matching the training pipeline, and returns the top-5
    predictions per segment as a DataFrame with columns:
    Start (s), End (s), Species, Confidence, Rank.
    """
    y, _ = librosa.load(audio_path, sr=sr, mono=True)
    segment_samples = int(segment_duration * sr)
    results = []

    for start in range(0, len(y) - segment_samples + 1, segment_samples):
        segment = y[start:start + segment_samples]

        # Skip silent segments (same RMS threshold as training).
        rms = np.sqrt(np.mean(segment ** 2))
        if rms < config.SILENCE_RMS_THRESHOLD:
            continue

        # Mel spectrogram — EXACT same parameters as preprocess.py.
        S = librosa.feature.melspectrogram(
            y=segment,
            sr=sr,
            n_mels=n_mels,
            n_fft=config.NT_N_FFT,
            hop_length=config.NT_HOP_LENGTH,
            fmin=config.NT_FMIN,
            fmax=config.NT_FMAX,
        )
        S_db = librosa.power_to_db(S, ref=np.max)

        # Normalise to [0, 1] — same method as training.
        S_norm = (S_db - S_db.min())
        if S_norm.max() > 0:
            S_norm = S_norm / S_norm.max()

        input_data = S_norm.reshape(1, n_mels, S_norm.shape[1], 1)

        preds = model.predict(input_data, verbose=0)[0]
        top5_indices = np.argsort(preds)[::-1][:5]

        start_sec = round(start / sr, 1)
        end_sec = round(start_sec + segment_duration, 1)

        for rank, idx in enumerate(top5_indices):
            species = label_map.get(str(idx), f"Unknown ({idx})")
            confidence = float(preds[idx])
            results.append({
                "Start (s)": start_sec,
                "End (s)": end_sec,
                "Species": species,
                "Confidence": confidence,
                "Rank": rank + 1,
            })

    return pd.DataFrame(results)
