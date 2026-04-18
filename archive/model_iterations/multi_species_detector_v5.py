"""
Multi-Species Sound Event Detection — v5 (BirdNET Embeddings)
PRT840 IT Thesis | Charles Darwin University | Group 33

Uses the v5 custom BirdNET classifier (NT_Bird_BirdNET_Classifier.tflite)
for multi-species detection with timestamps.

WHY V5 INSTEAD OF V3:
    The v3 CNN was trained on recording-level labels and exhibits segment-level
    leakage: every window of a training recording returns the recording's label
    with saturated confidence (observed empirically: 100% Blue-winged Kookaburra
    across a 55-second recording, 53/53 windows, even at threshold 0.95).

    BirdNET's backbone was trained at Cornell on segment-level labels across
    6000+ species. The embeddings reflect window content, not recording identity.
    Our custom head (trained in train_birdnet_embeddings.py) maps those
    embeddings to our 24 NT species. This gives segment-honest predictions.

PIPELINE:
    Audio file
      -> BirdNET-Analyzer CLI with --classifier NT_Bird_BirdNET_Classifier.tflite
      -> CSV with per-segment predictions (Start, End, Common name, Confidence)
      -> Merge adjacent same-species segments into events
      -> Timeline plot + JSON output

USAGE:
    python3 multi_species_detector_v5.py --audio sample_audio/Blue_winged_Kookaburra_XC1001935.mp3
    python3 multi_species_detector_v5.py --audio <path> --min-conf 0.25 --overlap 2.0
"""

import os
import sys
import csv
import json
import argparse
import shutil
import subprocess
import warnings
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

warnings.filterwarnings("ignore", category=UserWarning, module="librosa")

# === Configuration ===
BASE_DIR = os.path.expanduser("~/BirdDashboard")
CLASSIFIER_PATH = os.path.join(BASE_DIR, "models", "NT_Bird_BirdNET_Classifier.tflite")
LABELS_PATH = os.path.join(BASE_DIR, "models", "NT_Bird_BirdNET_Classifier_Labels.txt")
OUTPUT_DIR = os.path.join(BASE_DIR, "detections")
TEMP_DIR = os.path.join(BASE_DIR, "detections", "_birdnet_temp")

# BirdNET analysis parameters
# BirdNET uses a 3s window natively; --overlap controls how much each window
# overlaps the previous one (seconds). overlap=2.0 means 1s hop between starts.
DEFAULT_MIN_CONF = 0.25
DEFAULT_OVERLAP = 2.0       # 2s overlap on 3s windows = 1s effective hop
DEFAULT_SENSITIVITY = 1.0   # 0.5 - 1.5; higher = more sensitive
DEFAULT_TOP_K = 3

# Event merging parameters
MERGE_GAP_TOLERANCE = 1.5   # seconds - merge if same species within this gap
MIN_EVENT_DURATION = 1.5    # discard events shorter than this


def check_birdnet_installed():
    """Verify birdnet_analyzer is available."""
    try:
        result = subprocess.run(
            [sys.executable, "-c", "import birdnet_analyzer; print(birdnet_analyzer.__version__)"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            print(f"birdnet_analyzer version: {result.stdout.strip()}")
            return True
    except Exception as e:
        print(f"Could not verify birdnet_analyzer: {e}")
    print("ERROR: birdnet_analyzer is not installed. Run: pip install birdnet-analyzer")
    return False


def check_classifier_files():
    """Verify the v5 classifier and labels file exist."""
    if not os.path.exists(CLASSIFIER_PATH):
        print(f"ERROR: Custom classifier not found: {CLASSIFIER_PATH}")
        return False
    if not os.path.exists(LABELS_PATH):
        print(f"ERROR: Labels file not found: {LABELS_PATH}")
        return False

    with open(LABELS_PATH, "r") as f:
        labels = [line.strip() for line in f if line.strip()]
    print(f"Custom classifier: {CLASSIFIER_PATH}")
    print(f"Labels: {len(labels)} classes -> {labels[:3]}...")
    return True


def run_birdnet_analyze(audio_path, min_conf, overlap, sensitivity, output_dir):
    """Invoke BirdNET-Analyzer CLI with our custom classifier.

    BirdNET handles the sliding-window inference internally and writes a CSV
    with columns: Start (s), End (s), Scientific name, Common name, Confidence.
    """
    os.makedirs(output_dir, exist_ok=True)

    # BirdNET-Analyzer expects a directory of audio or a single file.
    # We pass the single-file path directly.
    cmd = [
        sys.executable, "-m", "birdnet_analyzer.analyze",
        audio_path,
        "-o", output_dir,
        "--classifier", CLASSIFIER_PATH,
        "--min_conf", str(min_conf),
        "--overlap", str(overlap),
        "--sensitivity", str(sensitivity),
        "--rtype", "csv",
    ]

    print(f"\nRunning BirdNET analysis...")
    print(f"  min_conf = {min_conf}")
    print(f"  overlap = {overlap}s (effective hop = {3.0 - overlap:.1f}s)")
    print(f"  sensitivity = {sensitivity}")

    result = subprocess.run(cmd, cwd=BASE_DIR, text=True, capture_output=True)

    if result.returncode != 0:
        print(f"ERROR: BirdNET analysis failed (return code {result.returncode})")
        print("STDOUT:", result.stdout[-1000:] if result.stdout else "(empty)")
        print("STDERR:", result.stderr[-1000:] if result.stderr else "(empty)")
        return None

    # Find the generated CSV
    recording_stem = Path(audio_path).stem
    csv_candidates = [
        os.path.join(output_dir, f) for f in os.listdir(output_dir)
        if f.endswith(".csv") and recording_stem in f and "params" not in f.lower()
    ]

    if not csv_candidates:
        print(f"ERROR: No BirdNET result CSV found in {output_dir}")
        print("Files present:", os.listdir(output_dir))
        return None

    return csv_candidates[0]


def parse_birdnet_csv(csv_path):
    """Parse BirdNET output CSV into a list of per-window detections."""
    detections = []
    with open(csv_path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                detections.append({
                    "start": float(row.get("Start (s)", row.get("Start", 0))),
                    "end": float(row.get("End (s)", row.get("End", 0))),
                    "species": row.get("Common name", row.get("Species Code", "Unknown")),
                    "scientific_name": row.get("Scientific name", ""),
                    "confidence": float(row.get("Confidence", 0)),
                })
            except (ValueError, KeyError) as e:
                print(f"Skipped malformed row: {row} ({e})")
    return detections


def apply_top_k_per_window(detections, top_k):
    """For each unique (start, end) window, keep only the top_k species by confidence."""
    # Group by (start, end)
    by_window = {}
    for det in detections:
        key = (round(det["start"], 2), round(det["end"], 2))
        by_window.setdefault(key, []).append(det)

    filtered = []
    for window_dets in by_window.values():
        window_dets.sort(key=lambda d: d["confidence"], reverse=True)
        filtered.extend(window_dets[:top_k])
    return filtered


def merge_detections(window_dets, gap_tolerance=MERGE_GAP_TOLERANCE, min_duration=MIN_EVENT_DURATION):
    """Merge adjacent same-species windows into continuous events."""
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
                current["end"] = max(current["end"], det["end"])
                current["confidence"] = max(current["confidence"], det["confidence"])
            else:
                if current["end"] - current["start"] >= min_duration:
                    events.append(current)
                current = dict(det)
        if current is not None and current["end"] - current["start"] >= min_duration:
            events.append(current)

    events.sort(key=lambda e: e["start"])
    return events


def plot_timeline(events, audio_duration, output_path, recording_name=""):
    """Generate timeline visualisation."""
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
    ax.set_title(f"Multi-Species Detection Timeline (v5 BirdNET embeddings)"
                 f"{' - ' + recording_name if recording_name else ''}")
    ax.grid(axis="x", linestyle="--", alpha=0.4)
    ax.set_axisbelow(True)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Timeline saved: {output_path}")


def get_audio_duration(audio_path):
    """Get audio duration using librosa (lightweight)."""
    try:
        import librosa
        return librosa.get_duration(path=audio_path)
    except Exception as e:
        print(f"Warning: couldn't determine audio duration ({e}) - using 60s fallback")
        return 60.0


def main():
    parser = argparse.ArgumentParser(
        description="Multi-species sound event detection for NT birds (v5: BirdNET embeddings)"
    )
    parser.add_argument("--audio", required=True, help="Path to audio file")
    parser.add_argument("--min-conf", type=float, default=DEFAULT_MIN_CONF,
                        help="Minimum confidence threshold (0-1)")
    parser.add_argument("--overlap", type=float, default=DEFAULT_OVERLAP,
                        help="Window overlap in seconds (max 2.99)")
    parser.add_argument("--sensitivity", type=float, default=DEFAULT_SENSITIVITY,
                        help="BirdNET sensitivity (0.5-1.5)")
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K,
                        help="Max species to keep per window")
    parser.add_argument("--no-plot", action="store_true", help="Skip timeline plot")
    parser.add_argument("--keep-temp", action="store_true", help="Keep BirdNET temp files")
    args = parser.parse_args()

    audio_path = os.path.expanduser(args.audio)
    if not os.path.exists(audio_path):
        print(f"ERROR: Audio file not found: {audio_path}")
        sys.exit(1)

    recording_name = Path(audio_path).stem

    # === Pre-flight checks ===
    if not check_birdnet_installed():
        sys.exit(1)
    if not check_classifier_files():
        sys.exit(1)

    # === Run BirdNET analysis ===
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    session_temp = os.path.join(TEMP_DIR, recording_name)
    if os.path.exists(session_temp):
        shutil.rmtree(session_temp)

    csv_path = run_birdnet_analyze(
        audio_path,
        min_conf=args.min_conf,
        overlap=args.overlap,
        sensitivity=args.sensitivity,
        output_dir=session_temp,
    )
    if csv_path is None:
        sys.exit(1)

    print(f"BirdNET output CSV: {csv_path}")

    # === Parse and filter ===
    detections = parse_birdnet_csv(csv_path)
    print(f"\nRaw BirdNET detections: {len(detections)}")
    if detections:
        unique_species = sorted({d["species"] for d in detections})
        print(f"Unique species detected: {len(unique_species)}")
        for s in unique_species:
            species_dets = [d for d in detections if d["species"] == s]
            max_conf = max(d["confidence"] for d in species_dets)
            print(f"  - {s}: {len(species_dets)} windows, max conf {max_conf:.3f}")

    # === Top-K filter per window ===
    filtered = apply_top_k_per_window(detections, args.top_k)
    print(f"\nAfter top-{args.top_k} per window: {len(filtered)}")

    # === Merge into events ===
    events = merge_detections(filtered)
    print(f"Final merged events: {len(events)}\n")

    # === Print table ===
    if events:
        print("=" * 80)
        print(f"{'Start':>8} {'End':>8} {'Duration':>9} {'Confidence':>11}  Species")
        print("-" * 80)
        for e in events:
            print(f"{e['start']:>7.1f}s {e['end']:>7.1f}s {e['end']-e['start']:>8.1f}s "
                  f"{e['confidence']:>10.3f}  {e['species']}")
        print("=" * 80)
    else:
        print("No detections above threshold. Try lowering --min-conf.")

    # === Save JSON ===
    duration = get_audio_duration(audio_path)
    results = {
        "recording": recording_name,
        "audio_path": audio_path,
        "duration_seconds": duration,
        "model_version": "v5_birdnet_embeddings",
        "classifier": CLASSIFIER_PATH,
        "parameters": {
            "min_conf": args.min_conf,
            "overlap_seconds": args.overlap,
            "effective_hop_seconds": 3.0 - args.overlap,
            "sensitivity": args.sensitivity,
            "top_k": args.top_k,
            "merge_gap_tolerance": MERGE_GAP_TOLERANCE,
            "min_event_duration": MIN_EVENT_DURATION,
        },
        "num_raw_detections": len(detections),
        "num_filtered_detections": len(filtered),
        "num_events": len(events),
        "events": events,
    }
    json_path = os.path.join(OUTPUT_DIR, f"{recording_name}_v5_detections.json")
    with open(json_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nJSON saved: {json_path}")

    # === Plot ===
    if not args.no_plot:
        plot_path = os.path.join(OUTPUT_DIR, f"{recording_name}_v5_timeline.png")
        plot_timeline(events, duration, plot_path, recording_name)

    # === Cleanup ===
    if not args.keep_temp and os.path.exists(session_temp):
        shutil.rmtree(session_temp)


if __name__ == "__main__":
    main()
