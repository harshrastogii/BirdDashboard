"""
Multi-Species Sound Event Detection — CLI wrapper.

PRT840 IT Thesis | Charles Darwin University | Group 33

The detection pipeline now lives in birddash.detection; this script is a thin
command-line front-end preserved for backwards compatibility (the dashboard's
multi-species section invokes it as a subprocess for process isolation).

USAGE:
    python3 multi_species_detector_v5_1.py --audio sample_audio/<file>.mp3
    python3 multi_species_detector_v5_1.py --audio <path> --primary-conf 0.5 --secondary-conf 0.25
    python3 multi_species_detector_v5_1.py --audio <path> --suppress-primary
"""

import argparse
import sys

from birddash import detection


def main():
    parser = argparse.ArgumentParser(
        description="Multi-species SED for NT birds (v5.1: BirdNET + dual-threshold)"
    )
    parser.add_argument("--audio", required=True, help="Path to audio file")
    parser.add_argument("--min-conf", type=float, default=detection.DEFAULT_MIN_CONF,
                        help="BirdNET detection floor (below this is ignored entirely)")
    parser.add_argument("--primary-conf", type=float, default=detection.DEFAULT_PRIMARY_CONF,
                        help="Confidence threshold for the primary species")
    parser.add_argument("--secondary-conf", type=float, default=detection.DEFAULT_SECONDARY_CONF,
                        help="Confidence threshold for secondary species")
    parser.add_argument("--overlap", type=float, default=detection.DEFAULT_OVERLAP,
                        help="Window overlap in seconds (max 2.99)")
    parser.add_argument("--sensitivity", type=float, default=detection.DEFAULT_SENSITIVITY,
                        help="BirdNET sensitivity (0.5-1.5)")
    parser.add_argument("--top-k", type=int, default=detection.DEFAULT_TOP_K,
                        help="Max species to keep per window")
    parser.add_argument("--suppress-primary", action="store_true",
                        help="Hide the primary species in output (shows only secondary)")
    parser.add_argument("--no-plot", action="store_true", help="Skip timeline plot")
    parser.add_argument("--keep-temp", action="store_true", help="Keep BirdNET temp files")
    args = parser.parse_args()

    try:
        detection.run_detection(
            args.audio,
            min_conf=args.min_conf,
            primary_conf=args.primary_conf,
            secondary_conf=args.secondary_conf,
            overlap=args.overlap,
            sensitivity=args.sensitivity,
            top_k=args.top_k,
            suppress_primary=args.suppress_primary,
            make_plot=not args.no_plot,
            keep_temp=args.keep_temp,
        )
    except RuntimeError as e:
        print(f"ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
