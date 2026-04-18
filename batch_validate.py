"""
Batch validation test for multi-species detector v5.1
Runs the detector on 6 carefully selected recordings covering:
  - Threatened species with few training samples
  - Common species with many training samples
  - Simple acoustic signatures (owl, raptor)
  - Held-out recordings (never seen during training)

Outputs a summary table + individual timeline PNGs + a combined grid chart.
"""

import os
import sys
import json
import subprocess
import shutil
from pathlib import Path

BASE_DIR = os.path.expanduser("~/BirdDashboard")
DETECTIONS_DIR = os.path.join(BASE_DIR, "detections")
VALIDATION_DIR = os.path.join(BASE_DIR, "detections", "validation")
DETECTOR_SCRIPT = os.path.join(BASE_DIR, "multi_species_detector_v5_1.py")

# Test recordings: (label, path, rationale)
TEST_CASES = [
    ("T1_Threatened_Gouldian",
     "sample_audio/Gouldian_Finch_XC125548.mp3",
     "Threatened species, only 7 training recordings"),
    ("T2_Common_Galah",
     "sample_audio/Galah_XC107839.mp3",
     "Common species, well-represented in training"),
    ("T3_Owl_Barking",
     "sample_audio/Barking_Owl_XC1018800.mp3",
     "Simple acoustic signature, likely genuine single-species"),
    ("T4_Raptor_Whistling_Kite",
     "sample_audio/Whistling_Kite_XC104991.mp3",
     "Raptor - sparse calls, long gaps"),
    ("T5_Small_Bird_Willie_Wagtail",
     "sample_audio/Willie_Wagtail_XC1001943.mp3",
     "Small passerine with distinctive chip-chip call"),
    ("T6_Heldout_Laughing_Kookaburra",
     "sample_audio_old/Laughing_Kookaburra_820587.mp3",
     "HELD-OUT - never seen during training"),
]


def run_one(test_label, audio_path, rationale):
    print("\n" + "=" * 85)
    print(f"  {test_label}")
    print(f"  File: {audio_path}")
    print(f"  Purpose: {rationale}")
    print("=" * 85)

    full_audio = os.path.join(BASE_DIR, audio_path)
    if not os.path.exists(full_audio):
        print(f"  SKIP: file not found")
        return None

    cmd = [
        sys.executable, DETECTOR_SCRIPT,
        "--audio", full_audio,
    ]

    result = subprocess.run(cmd, cwd=BASE_DIR, text=True, capture_output=True)
    if result.returncode != 0:
        print(f"  FAIL: {result.stderr[-500:]}")
        return None

    # Print key lines from stdout
    for line in result.stdout.split("\n"):
        if any(k in line for k in [
            "Unique species detected",
            "Primary species:",
            "Final merged events:",
            "Raw BirdNET detections",
        ]):
            print(f"  {line.strip()}")

    # Parse the JSON output
    stem = Path(audio_path).stem
    json_path = os.path.join(DETECTIONS_DIR, f"{stem}_v5_1_detections.json")
    if not os.path.exists(json_path):
        print(f"  WARN: JSON not found at {json_path}")
        return None

    with open(json_path) as f:
        data = json.load(f)

    # Copy timeline PNG to validation folder with test label prefix
    src_png = os.path.join(DETECTIONS_DIR, f"{stem}_v5_1_timeline.png")
    dst_png = os.path.join(VALIDATION_DIR, f"{test_label}_timeline.png")
    if os.path.exists(src_png):
        shutil.copy2(src_png, dst_png)
        print(f"  Saved: {dst_png}")

    events = data.get("events", [])
    primary = data.get("primary_species", "?")
    expected = Path(audio_path).stem.split("_")[:3]  # rough species from filename

    summary = {
        "test": test_label,
        "file": audio_path,
        "rationale": rationale,
        "duration": data.get("duration_seconds", 0),
        "primary_detected": primary,
        "num_events": len(events),
        "unique_species_in_events": len({e["species"] for e in events}),
        "species_list": sorted({e["species"] for e in events}),
    }
    return summary


def main():
    os.makedirs(VALIDATION_DIR, exist_ok=True)

    print("=" * 85)
    print("  MULTI-SPECIES DETECTOR VALIDATION")
    print(f"  Running {len(TEST_CASES)} test cases")
    print("=" * 85)

    results = []
    for test_label, audio_path, rationale in TEST_CASES:
        summary = run_one(test_label, audio_path, rationale)
        if summary:
            results.append(summary)

    # Final summary table
    print("\n\n" + "=" * 100)
    print("  VALIDATION SUMMARY")
    print("=" * 100)
    print(f"{'Test':<35} {'Dur':>6} {'Primary Detected':<30} {'Events':>7} {'Species':>8}")
    print("-" * 100)
    for r in results:
        print(f"{r['test']:<35} {r['duration']:>5.1f}s {r['primary_detected']:<30} "
              f"{r['num_events']:>7} {r['unique_species_in_events']:>8}")
    print("=" * 100)

    # Save summary JSON
    with open(os.path.join(VALIDATION_DIR, "validation_summary.json"), "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n  Charts and summary saved to: {VALIDATION_DIR}")
    print(f"  Open with: open {VALIDATION_DIR}")


if __name__ == "__main__":
    main()
