"""
Phase-1 golden-file scaffolding.

This module is a DELIBERATE, VERBATIM copy of the inference logic currently
living in app.py (`predict_with_nt_model` and the model/label loaders), with
the Streamlit `@st.cache_*` decorators removed so it can run headless.

Purpose: capture the *current* behaviour of the NT CNN pipeline as golden
files BEFORE any refactoring, so Phase 2's extraction can be proven to produce
identical outputs.

DO NOT edit the algorithm here. When Phase 2 extracts the real shared
inference module, the parity tests will be repointed at that module and this
scaffolding file will be deleted — the golden files under tests/golden/ are the
lasting contract.
"""

import json
import os

import numpy as np
import librosa
import tensorflow as tf

import config

MODEL_PATH = config.NT_MODEL_PATH
LABEL_MAP_PATH = config.NT_LABEL_MAP_PATH


def load_nt_model():
    if os.path.exists(MODEL_PATH):
        return tf.keras.models.load_model(MODEL_PATH)
    return None


def load_label_map():
    if os.path.exists(LABEL_MAP_PATH):
        with open(LABEL_MAP_PATH, "r") as f:
            return json.load(f)
    return {}


def predict_with_nt_model(audio_path, model, label_map, segment_duration=3.0, sr=22050, n_mels=128):
    """VERBATIM copy of app.py::predict_with_nt_model (returns a DataFrame-less
    list of dict rows here to keep the reference dependency-light)."""
    y, _ = librosa.load(audio_path, sr=sr, mono=True)
    segment_samples = int(segment_duration * sr)
    results = []

    for start in range(0, len(y) - segment_samples + 1, segment_samples):
        segment = y[start:start + segment_samples]

        rms = np.sqrt(np.mean(segment ** 2))
        if rms < 0.001:
            continue

        S = librosa.feature.melspectrogram(
            y=segment,
            sr=sr,
            n_mels=n_mels,
            n_fft=2048,
            hop_length=512,
            fmin=150,
            fmax=15000,
        )
        S_db = librosa.power_to_db(S, ref=np.max)

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

    return results
