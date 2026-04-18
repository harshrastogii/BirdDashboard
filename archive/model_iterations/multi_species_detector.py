"""
Multi-Species Sound Event Detection (SED)
PRT840 IT Thesis | Charles Darwin University | Group 33

Extends segment-level classification (v3 model) to multi-species detection
with timestamps using a sliding-window approach.

Pipeline:
    1. Load audio file
    2. Slide a 3-second window across the recording (with overlap)
    3. Predict species probabilities for each window using v3 model
    4. Apply confidence threshold -> keep top-K species per window
    5. Merge adjacent same-species windows into continuous events
    6. Return timestamped detections

Usage:
    python3 multi_species_detector.py --audio sample_audio/Blue_winged_Kookaburra_XC1001935.mp3
    python3 multi_species_detector.py --audio <path> --hop 1.0 --threshold 0.3

Output:
    - Console: list of detected events with start/end times and confidence
    - JSON file: structured detection results for dashboard/report
    - Optional: PNG timeline visualisation
"""

import os
import json
import argparse
import warnings
from pathlib import Path

import numpy as np
import librosa
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from tensorflow import keras

warnings.filterwarnings("ignore", category=UserWarning, module="librosa")

# === Configuration ===
MODEL_PATH = os.path.expanduser("~/BirdDashboard/models/nt_bird_cnn_best.keras")
LABEL_MAP_PATH = os.path.expanduser("~/BirdDashboard/spectrograms/label_map.json")
OUTPUT_DIR = os.path.expanduser("~/BirdDashboard/detections")

# Audio preprocessing parameters (must match training pipeline)
SR = 22050
N_MELS = 128
N_FFT = 2048
HOP_LENGTH = 512
FMIN = 150
FMAX = 15000
WINDOW_DURATION = 3.0   # seconds - matches training segment length
TARGET_FRAMES = 130     # matches model input shape

# Detection parameters
DEFAULT_HOP = 1.0       # seconds between window starts (2s overlap with 3s windows)
DEFAULT_THRESHOLD = 0.3 # minimum confidence to keep a detection
DEFAULT_TOP_K = 3       # max species per window
MIN_EVENT_DURATION = 1.5  # merged events shorter than this are discarded as noise
MERGE_GAP_TOLERANCE = 1.5 # seconds - if same species reappears within this gap, merge


def load_model_and_labels():
    """Load the trained v3 model and 24-class label map."""
    print(f"Loading model from {MODEL_PATH}...")
    model = keras.models.load_model(MODEL_PATH)

    with open(LABEL_MAP_PATH, "r") as f:
        label_map = json.load(f)

    # Ensure label map is indexed 0..N-1 and sorted
    species_names = [label_map[str(i)] for i in range(len(label_map))]

    print(f"Model loaded. Classes: {len(species_names)}")
    print(f"Input shape: {model.input_shape}")
    return model, species_names


def audio_to_melspec(audio_window):
    """Convert a 3-second audio window to a mel spectrogram in the same format as training."""
    mel = librosa.feature.melspectrogram(
        y=audio_window,
        sr=SR,
        n_mels=N_MELS,
        n_fft=N_FFT,
        hop_length=HOP_LENGTH,
        fmin=FMIN,
        fmax=FMAX,
    )
    mel_db = librosa.power_to_db(mel, ref=np.max)

    # Pad or truncate to TARGET_FRAMES
    if mel_db.shape[1] < TARGET_FRAMES:
        pad_width = TARGET_FRAMES - mel_db.shape[1]
        mel_db = np.pad(mel_db, ((0, 0), (0, pad_width)), mode="constant", constant_values=mel_db.min())
    else:
        mel_db = mel_db[:, :TARGET_FRAMES]

    # Normalise to [0, 1] (matches training)
    mel_db = (mel_db - mel_db.min()) / (mel_db.max() - mel_db.min() + 1e-8)

    # Add channel dimension -> (128, 130, 1)
    return mel_db[..., np.newaxis]


def sliding_window_predict(audio, model, hop_seconds=DEFAULT_HOP):
    """Run the model across overlapping windows of the recording.

    Returns:
        timestamps: array of window start times in seconds
        probs: (n_windows, n_classes) array of class probabilities
    """
    window_samples = int(WINDOW_DURATION * SR)
    hop_samples = int(hop_seconds * SR)

    # Generate window start indices
    starts = list(range(0, max(1, len(audio) - window_samples + 1), hop_samples))

    # Include a final window if there's meaningful tail audio
    if starts and starts[-1] + window_samples < len(audio) - hop_samples // 2:
        starts.append(len(audio) - window_samples)

    print(f"Recording length: {len(audio) / SR:.1f}s")
    print(f"Windows: {len(starts)} (3s window, {hop_seconds}s hop)")

    # Build batch of spectrograms
    specs = []
    timestamps = []
    for start in starts:
        end = start + window_samples
        window = audio[start:end]

        # Pad short windows at the tail
        if len(window) < window_samples:
            window = np.pad(window, (0, window_samples - len(window)), mode="constant")

        specs.append(audio_to_melspec(window))
        timestamps.append(start / SR)

    specs = np.array(specs)
    timestamps = np.array(timestamps)

    # Run batch prediction
    print(f"Running inference on {len(specs)} windows...")
    probs = model.predict(specs, verbose=0)

    return timestamps, probs


def extract_detections(timestamps, probs, species_names, threshold=DEFAULT_THRESHOLD, top_k=DEFAULT_TOP_K):
    """Convert per-window probabilities into per-window detections.

    For each window, keep up to top_k species whose probability exceeds threshold.
    """
    window_detections = []  # list of (start_time, end_time, species, confidence)

    for t, p in zip(timestamps, probs):
        # Get top_k class indices by probability
        top_idx = np.argsort(p)[::-1][:top_k]
        for idx in top_idx:
            if p[idx] >= threshold:
                window_detections.append({
                    "start": float(t),
                    "end": float(t + WINDOW_DURATION),
                    "species": species_names[idx],
                    "species_idx": int(idx),
                    "confidence": float(p[idx]),
                })

    return window_detections


def merge_detections(window_dets, gap_tolerance=MERGE_GAP_TOLERANCE, min_duration=MIN_EVENT_DURATION):
    """Merge adjacent detections of the same species into continuous events.

    Strategy:
        - Group by species
        - Within each species, sort by start time
        - Merge if next start <= current end + gap_tolerance
        - Discard merged events shorter than min_duration
    """
    by_species = {}
    for det in window_dets:
        by_species.setdefault(det["species"], []).append(det)

    events = []
    for species, dets in by_species.items():
        dets.sort(key=lambda d: d["start"])
        current = None
        for det in dets:
            if current is None:
                current = dict(det)
            elif det["start"] <= current["end"] + gap_tolerance:
                # Extend the current event
                current["end"] = max(current["end"], det["end"])
                current["confidence"] = max(current["confidence"], det["confidence"])
            else:
                # Finalise current, start new
                if current["end"] - current["start"] >= min_duration:
                    events.append(current)
                current = dict(det)
        if current is not None and current["end"] - current["start"] >= min_duration:
            events.append(current)

    # Sort all events by start time
    events.sort(key=lambda e: e["start"])
    return events


def plot_timeline(events, audio_duration, output_path, recording_name=""):
    """Generate a timeline visualisation of detected species events."""
    if not events:
        print("No events to plot.")
        return

    species_list = sorted({e["species"] for e in events})
    colors = plt.cm.tab20(np.linspace(0, 1, max(len(species_list), 1)))
    color_map = dict(zip(species_list, colors))

    fig, ax = plt.subplots(figsize=(14, max(4, 0.6 * len(species_list) + 2)))

    for i, species in enumerate(species_list):
        for event in events:
            if event["species"] == species:
                ax.barh(
                    y=i,
                    width=event["end"] - event["start"],
                    left=event["start"],
                    height=0.6,
                    color=color_map[species],
                    edgecolor="black",
                    linewidth=0.5,
                    alpha=0.85,
                )
                # Label with confidence
                ax.text(
                    event["start"] + (event["end"] - event["start"]) / 2,
                    i,
                    f"{event['confidence']:.2f}",
                    ha="center", va="center",
                    fontsize=8, color="white", weight="bold",
                )

    ax.set_yticks(range(len(species_list)))
    ax.set_yticklabels(species_list)
    ax.set_xlim(0, audio_duration)
    ax.set_xlabel("Time (seconds)")
    ax.set_title(f"Multi-Species Detection Timeline{' - ' + recording_name if recording_name else ''}")
    ax.grid(axis="x", linestyle="--", alpha=0.4)
    ax.set_axisbelow(True)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Timeline saved: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Multi-species sound event detection for NT birds")
    parser.add_argument("--audio", required=True, help="Path to audio file")
    parser.add_argument("--hop", type=float, default=DEFAULT_HOP, help="Hop size in seconds between windows")
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD, help="Minimum confidence threshold")
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K, help="Max species per window")
    parser.add_argument("--no-plot", action="store_true", help="Skip timeline plot generation")
    args = parser.parse_args()

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    audio_path = os.path.expanduser(args.audio)
    recording_name = Path(audio_path).stem

    # === Load audio ===
    print(f"\nLoading audio: {audio_path}")
    audio, sr = librosa.load(audio_path, sr=SR, mono=True)
    duration = len(audio) / SR
    print(f"Duration: {duration:.1f}s  Sample rate: {sr}Hz")

    # === Load model ===
    model, species_names = load_model_and_labels()

    # === Sliding-window inference ===
    timestamps, probs = sliding_window_predict(audio, model, hop_seconds=args.hop)

    # === Extract per-window detections ===
    window_dets = extract_detections(
        timestamps, probs, species_names,
        threshold=args.threshold, top_k=args.top_k
    )
    print(f"Per-window detections above threshold: {len(window_dets)}")

    # === Merge into events ===
    events = merge_detections(window_dets)
    print(f"\nFinal merged events: {len(events)}\n")

    # === Print results ===
    if events:
        print("=" * 70)
        print(f"{'Start':>8} {'End':>8} {'Duration':>9} {'Confidence':>11}  Species")
        print("-" * 70)
        for e in events:
            print(f"{e['start']:>7.1f}s {e['end']:>7.1f}s {e['end']-e['start']:>8.1f}s "
                  f"{e['confidence']:>10.3f}  {e['species']}")
        print("=" * 70)
    else:
        print("No detections above threshold. Try lowering --threshold.")

    # === Save JSON ===
    results = {
        "recording": recording_name,
        "audio_path": audio_path,
        "duration_seconds": duration,
        "parameters": {
            "window_duration": WINDOW_DURATION,
            "hop_seconds": args.hop,
            "threshold": args.threshold,
            "top_k": args.top_k,
        },
        "num_windows": len(timestamps),
        "num_raw_detections": len(window_dets),
        "num_events": len(events),
        "events": events,
    }
    json_path = os.path.join(OUTPUT_DIR, f"{recording_name}_detections.json")
    with open(json_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nJSON saved: {json_path}")

    # === Plot timeline ===
    if not args.no_plot:
        plot_path = os.path.join(OUTPUT_DIR, f"{recording_name}_timeline.png")
        plot_timeline(events, duration, plot_path, recording_name)


if __name__ == "__main__":
    main()
