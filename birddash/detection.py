"""
Multi-Species Sound Event Detection pipeline (v5.2: BirdNET + dual threshold).

PRT840 IT Thesis | Charles Darwin University | Group 33

This module owns the full sound-event-detection logic that previously lived in
the multi_species_detector_v5_1.py CLI script. The CLI is now a thin wrapper
around `run_detection`, and the FastAPI backend (Phase 3) will call
`run_detection` directly.

Pipeline: BirdNET-Analyzer (custom NT classifier, invoked as a subprocess for
process isolation) -> parse CSV & resolve truncated names -> identify primary
species -> dual-threshold filter (+ top-K secondaries) -> merge adjacent
windows into events -> JSON (+ optional timeline plot).

Robust audio loading: if BirdNET-Analyzer's loader rejects a file (common with
certain Xeno-canto MP3 encodings), the pipeline re-encodes via librosa -> WAV
and retries.
"""

import os
import sys
import csv
import json
import shutil
import subprocess
import warnings
from pathlib import Path
from collections import Counter

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from birddash import config

warnings.filterwarnings("ignore", category=UserWarning, module="librosa")

# === Paths (centralised) ===
BASE_DIR = config.BASE_DIR
CLASSIFIER_PATH = config.CLASSIFIER_TFLITE_PATH
LABELS_PATH = config.CLASSIFIER_LABELS_PATH
OUTPUT_DIR = config.DETECTIONS_DIR
TEMP_DIR = config.DETECTIONS_DIR / "_birdnet_temp"

# === Default detection parameters ===
DEFAULT_MIN_CONF = 0.1            # Low floor so BirdNET returns everything
DEFAULT_PRIMARY_CONF = 0.5        # Threshold for primary species
DEFAULT_SECONDARY_CONF = 0.25     # Threshold for secondary species
DEFAULT_OVERLAP = 2.0             # 1s effective hop
DEFAULT_SENSITIVITY = 1.25        # Slightly elevated for multi-species detection
DEFAULT_TOP_K = 3

# Event merging parameters
MERGE_GAP_TOLERANCE = 1.5
MIN_EVENT_DURATION = 1.5


# =============================================================================
# Label handling
# =============================================================================

def load_official_labels():
    """Load the full canonical species labels from the labels file."""
    with open(LABELS_PATH, "r") as f:
        labels = [line.strip() for line in f if line.strip()]
    return labels


def build_name_map(official_labels):
    """Map any truncated BirdNET CSV name back to the full canonical label.

    BirdNET sometimes returns everything after the first underscore; we rebuild
    the mapping so 'winged_Kookaburra' -> 'Blue_winged_Kookaburra'.
    """
    name_map = {}
    for label in official_labels:
        name_map[label] = label
        parts = label.split("_", 1)
        if len(parts) == 2:
            name_map[parts[1]] = label
    return name_map


def resolve_species_name(raw_name, name_map, official_labels):
    """Resolve a potentially truncated species name to its canonical form."""
    if raw_name in name_map:
        return name_map[raw_name]
    matches = [lab for lab in official_labels if raw_name in lab or lab.endswith(raw_name)]
    if len(matches) == 1:
        return matches[0]
    return raw_name


def pretty_species(label):
    """'Blue_winged_Kookaburra' -> 'Blue-winged Kookaburra' for display."""
    return label.replace("_", " ").replace("  ", " ").strip()


# =============================================================================
# Pre-flight checks
# =============================================================================

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


# =============================================================================
# BirdNET invocation
# =============================================================================

def reencode_to_wav(audio_path, wav_path):
    """Re-encode audio to clean 48kHz mono WAV using librosa (fallback loader)."""
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
            str(path),
            "-o", str(output_dir),
            "--classifier", str(CLASSIFIER_PATH),
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
        print("  BirdNET could not read the original file.")
        print("  Falling back: re-encoding to clean WAV via librosa...")
        try:
            reencoded_path = os.path.join(output_dir, "_reencoded.wav")
            duration = reencode_to_wav(audio_path, reencoded_path)
            print(f"  Re-encoded to: {reencoded_path}  ({duration:.1f}s)")
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
    """Parse BirdNET CSV and resolve truncated species names.

    BirdNET-Analyzer writes the custom-classifier label ``<A>_<B...>`` split
    across two CSV columns: ``Scientific name`` = ``<A>`` and ``Common name`` =
    ``<B...>`` (the text after the first underscore). Reading the ``Common name``
    column alone is lossy for species that share a final word — ``Barking_Owl``
    and ``Masked_Owl`` both yield ``"Owl"``, and ``Black_Kite`` / ``Whistling_Kite``
    both yield ``"Kite"`` — so the old suffix-only resolution collapsed them onto
    whichever full label was defined last (a real mislabelling, see
    tests/test_detection_parsing.py).

    Fix: rejoin the two columns to recover the FULL label and use it directly when
    it is a known class; only fall back to the legacy suffix resolution when the
    rejoined string is not a recognised label (e.g. single-word species where
    ``Scientific == Common``, or a BirdNET build that already emits the full name).
    """
    label_set = set(official_labels)
    detections = []
    with open(csv_path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                common = row.get("Common name", row.get("Species Code", "Unknown"))
                scientific = row.get("Scientific name", "")
                rejoined = f"{scientific}_{common}" if scientific else common
                resolved = (rejoined if rejoined in label_set
                            else resolve_species_name(common, name_map, official_labels))
                detections.append({
                    "start": float(row.get("Start (s)", row.get("Start", 0))),
                    "end": float(row.get("End (s)", row.get("End", 0))),
                    "species": pretty_species(resolved),
                    "species_raw": resolved,
                    "scientific_name": scientific,
                    "confidence": float(row.get("Confidence", 0)),
                })
            except (ValueError, KeyError) as e:
                print(f"Skipped malformed row: {row} ({e})")
    return detections


# =============================================================================
# Detection logic
# =============================================================================

def identify_primary_species(detections):
    """The primary species is the one with the most saturated detections."""
    if not detections:
        return None
    high_conf = Counter()
    for det in detections:
        if det["confidence"] >= 0.9:
            high_conf[det["species"]] += 1
    if high_conf:
        return high_conf.most_common(1)[0][0]
    all_counts = Counter(d["species"] for d in detections)
    return all_counts.most_common(1)[0][0]


def apply_dual_threshold(detections, primary_species, primary_conf, secondary_conf, top_k):
    """Keep primary above primary_conf; keep other species above secondary_conf.

    Top-K applies to SECONDARY species only; primary always gets its own slot.
    """
    filtered = []
    for det in detections:
        threshold = primary_conf if det["species"] == primary_species else secondary_conf
        if det["confidence"] >= threshold:
            filtered.append(det)

    by_window = {}
    for det in filtered:
        key = (round(det["start"], 2), round(det["end"], 2))
        by_window.setdefault(key, []).append(det)

    result = []
    for window_dets in by_window.values():
        primary_in_window = [d for d in window_dets if d["species"] == primary_species]
        secondary_in_window = [d for d in window_dets if d["species"] != primary_species]
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


def get_audio_duration(audio_path):
    try:
        import librosa
        return librosa.get_duration(path=audio_path)
    except Exception:
        return 60.0


# =============================================================================
# Plotting
# =============================================================================

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


# =============================================================================
# Orchestration
# =============================================================================

def run_detection(audio_path, *, min_conf=DEFAULT_MIN_CONF,
                  primary_conf=DEFAULT_PRIMARY_CONF,
                  secondary_conf=DEFAULT_SECONDARY_CONF,
                  overlap=DEFAULT_OVERLAP,
                  sensitivity=DEFAULT_SENSITIVITY,
                  top_k=DEFAULT_TOP_K,
                  suppress_primary=False,
                  make_plot=True,
                  keep_temp=False) -> dict:
    """Run the full multi-species SED pipeline for one recording.

    Returns the results dict (also written to detections/<stem>_v5_1_detections.json).
    Raises RuntimeError if pre-flight checks fail or BirdNET produces no output.
    """
    audio_path = os.path.expanduser(audio_path)
    if not os.path.exists(audio_path):
        raise RuntimeError(f"Audio file not found: {audio_path}")

    recording_name = Path(audio_path).stem

    if not check_birdnet_installed():
        raise RuntimeError("birdnet_analyzer is not installed.")
    if not check_classifier_files():
        raise RuntimeError("Classifier or labels file missing.")

    official_labels = load_official_labels()
    name_map = build_name_map(official_labels)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    session_temp = os.path.join(TEMP_DIR, recording_name)
    if os.path.exists(session_temp):
        shutil.rmtree(session_temp)

    csv_path = run_birdnet_analyze(
        audio_path, min_conf=min_conf, overlap=overlap,
        sensitivity=sensitivity, output_dir=session_temp,
    )
    if csv_path is None:
        raise RuntimeError("BirdNET analysis produced no results.")

    detections = parse_birdnet_csv(csv_path, name_map, official_labels)
    print(f"\nRaw BirdNET detections: {len(detections)}")
    if detections:
        unique_species = sorted({d["species"] for d in detections})
        print(f"Unique species detected: {len(unique_species)}")
        for s in unique_species:
            species_dets = [d for d in detections if d["species"] == s]
            max_conf = max(d["confidence"] for d in species_dets)
            print(f"  - {s:<32} {len(species_dets):>3} windows  max conf {max_conf:.3f}")

    primary_species = identify_primary_species(detections)
    print(f"\nPrimary species: {primary_species}")
    print(f"Applying dual threshold: primary={primary_conf}, secondary={secondary_conf}")

    filtered = apply_dual_threshold(
        detections, primary_species=primary_species,
        primary_conf=primary_conf, secondary_conf=secondary_conf, top_k=top_k,
    )
    print(f"After dual threshold + top-{top_k}: {len(filtered)}")

    if suppress_primary:
        filtered = [d for d in filtered if d["species"] != primary_species]
        print(f"After suppressing primary: {len(filtered)}")

    events = merge_detections(filtered)
    print(f"Final merged events: {len(events)}\n")

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
        print("No detections above threshold. Try lowering secondary-conf.")

    duration = get_audio_duration(audio_path)
    results = {
        "recording": recording_name,
        "audio_path": audio_path,
        "duration_seconds": duration,
        "model_version": "v5.1_birdnet_dual_threshold",
        "classifier": str(CLASSIFIER_PATH),
        "primary_species": primary_species,
        "parameters": {
            "min_conf": min_conf,
            "primary_conf": primary_conf,
            "secondary_conf": secondary_conf,
            "overlap_seconds": overlap,
            "effective_hop_seconds": 3.0 - overlap,
            "sensitivity": sensitivity,
            "top_k": top_k,
            "suppress_primary": suppress_primary,
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

    if make_plot:
        plot_path = os.path.join(OUTPUT_DIR, f"{recording_name}_v5_1_timeline.png")
        plot_timeline(events, duration, plot_path, recording_name, primary_species)

    if not keep_temp and os.path.exists(session_temp):
        shutil.rmtree(session_temp)

    return results
