"""
Multi-Species Sound Event Detection — v5.2 (BirdNET + Dual Threshold + Robust Loader)
PRT840 IT Thesis | Charles Darwin University | Group 33

IMPROVEMENTS OVER v5.1:
    - Primary species no longer consumes a top-K slot. Top-K is applied ONLY
      to secondary species, so strong secondary detections (e.g. Willie Wagtail
      at 0.75) are not crowded out when the primary saturates at 1.0.
    - Default secondary threshold lowered to 0.25, based on observed legit
      secondary species confidence ranges in NT bird recordings.
    - Robust audio loading: if BirdNET-Analyzer's loader rejects a file
      (common with certain Xeno-canto MP3 encodings), the pipeline automatically
      re-encodes via librosa -> WAV and retries.

IMPROVEMENTS OVER v5.0:
    - Fixed species name parsing (reconstructed from labels file).
    - Dual-threshold detection: separate high/low thresholds for primary/secondary.
    - --suppress-primary mode for clean secondary-species visualisation.

USAGE:
    python3 multi_species_detector_v5_1.py --audio sample_audio/Blue_winged_Kookaburra_XC1001935.mp3
    python3 multi_species_detector_v5_1.py --audio <path> --primary-conf 0.5 --secondary-conf 0.25
    python3 multi_species_detector_v5_1.py --audio <path> --suppress-primary
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
from collections import Counter

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

warnings.filterwarnings("ignore", category=UserWarning, module="librosa")

# === Configuration ===
# Paths are centralised in config.py (portable, env-overridable). config.py
# lives in the repo root, which is on sys.path when this script runs.
import config

BASE_DIR = config.BASE_DIR
CLASSIFIER_PATH = config.CLASSIFIER_TFLITE_PATH
LABELS_PATH = config.CLASSIFIER_LABELS_PATH
OUTPUT_DIR = config.DETECTIONS_DIR
TEMP_DIR = config.DETECTIONS_DIR / "_birdnet_temp"

# BirdNET analysis parameters
DEFAULT_MIN_CONF = 0.1            # Low floor so BirdNET returns everything
DEFAULT_PRIMARY_CONF = 0.5        # Threshold for primary species
DEFAULT_SECONDARY_CONF = 0.25     # Threshold for secondary species (tuned to catch genuine background calls)
DEFAULT_OVERLAP = 2.0             # 1s effective hop
DEFAULT_SENSITIVITY = 1.25        # Slightly elevated for multi-species detection
DEFAULT_TOP_K = 3

# Event merging parameters
MERGE_GAP_TOLERANCE = 1.5
MIN_EVENT_DURATION = 1.5


def load_official_labels():
    """Load the full canonical species labels from the labels file."""
    with open(LABELS_PATH, "r") as f:
        labels = [line.strip() for line in f if line.strip()]
    return labels


def build_name_map(official_labels):
    """Build a fuzzy-match map from any truncated BirdNET CSV name to the full label.

    BirdNET sometimes returns a truncated species name (everything after the first
    underscore) in its CSV output. We rebuild the mapping so 'winged_Kookaburra'
    maps back to 'Blue_winged_Kookaburra'.
    """
    name_map = {}
    for label in official_labels:
        # Exact match
        name_map[label] = label
        # After first underscore: "Blue_winged_Kookaburra" -> "winged_Kookaburra"
        parts = label.split("_", 1)
        if len(parts) == 2:
            name_map[parts[1]] = label
        # Last token alone: "Blue_winged_Kookaburra" -> "Kookaburra"
        # BUT only if unambiguous - skip if multiple species share it
    return name_map


def resolve_species_name(raw_name, name_map, official_labels):
    """Resolve a potentially truncated species name to its full canonical form."""
    if raw_name in name_map:
        return name_map[raw_name]
    # Try substring match against official labels
    matches = [lab for lab in official_labels if raw_name in lab or lab.endswith(raw_name)]
    if len(matches) == 1:
        return matches[0]
    return raw_name  # Fall back to raw if ambiguous


def pretty_species(label):
    """Convert 'Blue_winged_Kookaburra' to 'Blue-winged Kookaburra' for display."""
    return label.replace("_", " ").replace("  ", " ").strip()


def check_birdnet_installed():
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
    print("ERROR: birdnet_analyzer is not installed.")
    return False


def check_classifier_files():
    if not os.path.exists(CLASSIFIER_PATH):
        print(f"ERROR: Custom classifier not found: {CLASSIFIER_PATH}")
        return False
    if not os.path.exists(LABELS_PATH):
        print(f"ERROR: Labels file not found: {LABELS_PATH}")
        return False
    labels = load_official_labels()
    print(f"Custom classifier: {CLASSIFIER_PATH}")
    print(f"Labels: {len(labels)} classes")
    return True


def reencode_to_wav(audio_path, wav_path):
    """Re-encode audio to clean 48kHz mono WAV using librosa.
    Used as a fallback when BirdNET-Analyzer's loader rejects the original file."""
    import librosa
    import soundfile as sf
    audio, _ = librosa.load(audio_path, sr=48000, mono=True)
    sf.write(wav_path, audio, 48000)
    return len(audio) / 48000.0


def run_birdnet_analyze(audio_path, min_conf, overlap, sensitivity, output_dir):
    os.makedirs(output_dir, exist_ok=True)

    def _invoke(path):
        cmd = [
            sys.executable, "-m", "birdnet_analyzer.analyze",
            path,
            "-o", output_dir,
            "--classifier", CLASSIFIER_PATH,
            "--min_conf", str(min_conf),
            "--overlap", str(overlap),
            "--sensitivity", str(sensitivity),
            "--rtype", "csv",
        ]
        return subprocess.run(cmd, cwd=BASE_DIR, text=True, capture_output=True)

    print(f"\nRunning BirdNET analysis...")
    print(f"  min_conf = {min_conf}  (detection floor)")
    print(f"  overlap = {overlap}s  (effective hop = {3.0 - overlap:.1f}s)")
    print(f"  sensitivity = {sensitivity}")

    result = _invoke(audio_path)

    # Detect "Cannot analyze audio file" - BirdNET prints this but may return 0
    combined_output = (result.stdout or "") + (result.stderr or "")
    birdnet_rejected = "Cannot analyze audio file" in combined_output

    if result.returncode != 0 or birdnet_rejected:
        # Fall back to re-encoding via librosa
        print("  BirdNET could not read the original file.")
        print("  Falling back: re-encoding to clean WAV via librosa...")
        try:
            reencoded_path = os.path.join(output_dir, "_reencoded.wav")
            duration = reencode_to_wav(audio_path, reencoded_path)
            print(f"  Re-encoded to: {reencoded_path}  ({duration:.1f}s)")
            # Clear any stale files in the output dir from the failed run
            for f in os.listdir(output_dir):
                if f.endswith(".csv") or f.endswith(".txt"):
                    try:
                        os.remove(os.path.join(output_dir, f))
                    except OSError:
                        pass
            result = _invoke(reencoded_path)
        except Exception as e:
            print(f"  Re-encoding failed: {e}")
            return None

    if result.returncode != 0:
        print(f"ERROR: BirdNET analysis failed (return code {result.returncode})")
        print("STDERR:", result.stderr[-1000:] if result.stderr else "(empty)")
        return None

    recording_stem = Path(audio_path).stem
    # Match either original stem OR '_reencoded' (fallback path)
    csv_candidates = [
        os.path.join(output_dir, f) for f in os.listdir(output_dir)
        if f.endswith(".csv") and "params" not in f.lower()
        and (recording_stem in f or "_reencoded" in f)
    ]

    if not csv_candidates:
        print(f"ERROR: No BirdNET result CSV found in {output_dir}")
        return None

    return csv_candidates[0]


def parse_birdnet_csv(csv_path, name_map, official_labels):
    """Parse BirdNET CSV and resolve truncated species names."""
    detections = []
    with open(csv_path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                raw_name = row.get("Common name", row.get("Species Code", "Unknown"))
                resolved = resolve_species_name(raw_name, name_map, official_labels)
                detections.append({
                    "start": float(row.get("Start (s)", row.get("Start", 0))),
                    "end": float(row.get("End (s)", row.get("End", 0))),
                    "species": pretty_species(resolved),
                    "species_raw": resolved,
                    "scientific_name": row.get("Scientific name", ""),
                    "confidence": float(row.get("Confidence", 0)),
                })
            except (ValueError, KeyError) as e:
                print(f"Skipped malformed row: {row} ({e})")
    return detections


def identify_primary_species(detections):
    """The primary species is the one with the most saturated detections."""
    if not detections:
        return None
    # Count windows where each species is above 0.9
    high_conf = Counter()
    for det in detections:
        if det["confidence"] >= 0.9:
            high_conf[det["species"]] += 1
    if high_conf:
        return high_conf.most_common(1)[0][0]
    # Fallback: just the most common
    all_counts = Counter(d["species"] for d in detections)
    return all_counts.most_common(1)[0][0]


def apply_dual_threshold(detections, primary_species, primary_conf, secondary_conf, top_k):
    """Keep primary-species detections above primary_conf;
    keep all other species above secondary_conf.

    Top-K is applied to SECONDARY species only. Primary always gets its own slot
    (never competes with secondaries) so strong secondary detections aren't
    crowded out when the primary saturates at 1.0."""
    # Filter by dual threshold
    filtered = []
    for det in detections:
        threshold = primary_conf if det["species"] == primary_species else secondary_conf
        if det["confidence"] >= threshold:
            filtered.append(det)

    # Group by (start, end)
    by_window = {}
    for det in filtered:
        key = (round(det["start"], 2), round(det["end"], 2))
        by_window.setdefault(key, []).append(det)

    # For each window: keep primary always + top-K secondaries
    result = []
    for window_dets in by_window.values():
        primary_in_window = [d for d in window_dets if d["species"] == primary_species]
        secondary_in_window = [d for d in window_dets if d["species"] != primary_species]
        # Sort secondaries by confidence descending, take top K
        secondary_in_window.sort(key=lambda d: d["confidence"], reverse=True)
        result.extend(primary_in_window)
        result.extend(secondary_in_window[:top_k])
    return result


def merge_detections(window_dets, gap_tolerance=MERGE_GAP_TOLERANCE, min_duration=MIN_EVENT_DURATION):
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


def plot_timeline(events, audio_duration, output_path, recording_name="", primary_species=None):
    if not events:
        print("No events to plot.")
        return

    species_list = sorted({e["species"] for e in events})
    colors = plt.cm.tab20(np.linspace(0, 1, max(len(species_list), 1)))
    color_map = dict(zip(species_list, colors))

    fig, ax = plt.subplots(figsize=(14, max(4, 0.6 * len(species_list) + 2)))

    for i, species in enumerate(species_list):
        is_primary = (species == primary_species)
        for event in events:
            if event["species"] == species:
                ax.barh(
                    y=i,
                    width=event["end"] - event["start"],
                    left=event["start"],
                    height=0.6,
                    color=color_map[species],
                    edgecolor="black",
                    linewidth=1.5 if is_primary else 0.5,
                    alpha=0.90 if is_primary else 0.75,
                )
                ax.text(
                    event["start"] + (event["end"] - event["start"]) / 2,
                    i,
                    f"{event['confidence']:.2f}",
                    ha="center", va="center",
                    fontsize=8, color="white", weight="bold",
                )

    # Label primary species with a star
    ytick_labels = [f"★ {s}" if s == primary_species else s for s in species_list]
    ax.set_yticks(range(len(species_list)))
    ax.set_yticklabels(ytick_labels)
    ax.set_xlim(0, audio_duration)
    ax.set_xlabel("Time (seconds)")
    title = f"Multi-Species Detection Timeline (v5 BirdNET embeddings, dual-threshold)"
    if recording_name:
        title += f"\n{recording_name}"
    ax.set_title(title, fontsize=11)
    ax.grid(axis="x", linestyle="--", alpha=0.4)
    ax.set_axisbelow(True)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Timeline saved: {output_path}")


def get_audio_duration(audio_path):
    try:
        import librosa
        return librosa.get_duration(path=audio_path)
    except Exception:
        return 60.0


def main():
    parser = argparse.ArgumentParser(
        description="Multi-species SED for NT birds (v5.1: BirdNET + dual-threshold)"
    )
    parser.add_argument("--audio", required=True, help="Path to audio file")
    parser.add_argument("--min-conf", type=float, default=DEFAULT_MIN_CONF,
                        help="BirdNET detection floor (below this is ignored entirely)")
    parser.add_argument("--primary-conf", type=float, default=DEFAULT_PRIMARY_CONF,
                        help="Confidence threshold for the primary species")
    parser.add_argument("--secondary-conf", type=float, default=DEFAULT_SECONDARY_CONF,
                        help="Confidence threshold for secondary species")
    parser.add_argument("--overlap", type=float, default=DEFAULT_OVERLAP,
                        help="Window overlap in seconds (max 2.99)")
    parser.add_argument("--sensitivity", type=float, default=DEFAULT_SENSITIVITY,
                        help="BirdNET sensitivity (0.5-1.5)")
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K,
                        help="Max species to keep per window")
    parser.add_argument("--suppress-primary", action="store_true",
                        help="Hide the primary species in output (shows only secondary)")
    parser.add_argument("--no-plot", action="store_true", help="Skip timeline plot")
    parser.add_argument("--keep-temp", action="store_true", help="Keep BirdNET temp files")
    args = parser.parse_args()

    audio_path = os.path.expanduser(args.audio)
    if not os.path.exists(audio_path):
        print(f"ERROR: Audio file not found: {audio_path}")
        sys.exit(1)

    recording_name = Path(audio_path).stem

    # Pre-flight checks
    if not check_birdnet_installed():
        sys.exit(1)
    if not check_classifier_files():
        sys.exit(1)

    # Load labels for name resolution
    official_labels = load_official_labels()
    name_map = build_name_map(official_labels)

    # Run BirdNET
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

    # Parse with name resolution
    detections = parse_birdnet_csv(csv_path, name_map, official_labels)
    print(f"\nRaw BirdNET detections: {len(detections)}")
    if detections:
        unique_species = sorted({d["species"] for d in detections})
        print(f"Unique species detected: {len(unique_species)}")
        for s in unique_species:
            species_dets = [d for d in detections if d["species"] == s]
            max_conf = max(d["confidence"] for d in species_dets)
            print(f"  - {s:<32} {len(species_dets):>3} windows  max conf {max_conf:.3f}")

    # Identify primary species
    primary_species = identify_primary_species(detections)
    print(f"\nPrimary species: {primary_species}")
    print(f"Applying dual threshold: primary={args.primary_conf}, secondary={args.secondary_conf}")

    # Dual-threshold filter
    filtered = apply_dual_threshold(
        detections,
        primary_species=primary_species,
        primary_conf=args.primary_conf,
        secondary_conf=args.secondary_conf,
        top_k=args.top_k,
    )
    print(f"After dual threshold + top-{args.top_k}: {len(filtered)}")

    # Optional: suppress primary for cleaner secondary view
    if args.suppress_primary:
        filtered = [d for d in filtered if d["species"] != primary_species]
        print(f"After suppressing primary: {len(filtered)}")

    # Merge
    events = merge_detections(filtered)
    print(f"Final merged events: {len(events)}\n")

    # Print table
    if events:
        print("=" * 85)
        print(f"{'Start':>8} {'End':>8} {'Duration':>9} {'Confidence':>11}  Species")
        print("-" * 85)
        for e in events:
            marker = " ★" if e["species"] == primary_species else "  "
            print(f"{e['start']:>7.1f}s {e['end']:>7.1f}s {e['end']-e['start']:>8.1f}s "
                  f"{e['confidence']:>10.3f} {marker} {e['species']}")
        print("=" * 85)
        print("★ = primary species (highest saturation)")
    else:
        print("No detections above threshold. Try lowering --secondary-conf.")

    # Save JSON
    duration = get_audio_duration(audio_path)
    results = {
        "recording": recording_name,
        "audio_path": audio_path,
        "duration_seconds": duration,
        "model_version": "v5.1_birdnet_dual_threshold",
        "classifier": str(CLASSIFIER_PATH),
        "primary_species": primary_species,
        "parameters": {
            "min_conf": args.min_conf,
            "primary_conf": args.primary_conf,
            "secondary_conf": args.secondary_conf,
            "overlap_seconds": args.overlap,
            "effective_hop_seconds": 3.0 - args.overlap,
            "sensitivity": args.sensitivity,
            "top_k": args.top_k,
            "suppress_primary": args.suppress_primary,
        },
        "num_raw_detections": len(detections),
        "num_filtered_detections": len(filtered),
        "num_events": len(events),
        "events": events,
    }
    json_path = os.path.join(OUTPUT_DIR, f"{recording_name}_v5_1_detections.json")
    with open(json_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nJSON saved: {json_path}")

    # Plot
    if not args.no_plot:
        plot_path = os.path.join(OUTPUT_DIR, f"{recording_name}_v5_1_timeline.png")
        plot_timeline(events, duration, plot_path, recording_name, primary_species)

    # Cleanup
    if not args.keep_temp and os.path.exists(session_temp):
        shutil.rmtree(session_temp)


if __name__ == "__main__":
    main()
