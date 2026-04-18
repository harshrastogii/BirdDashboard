"""
Multi-Species Detection Section for app.py
PRT840 IT Thesis | Group 33

HOW TO INTEGRATE:
    1. Place this file at ~/BirdDashboard/multi_species_section.py
    2. Open app.py and add this import near the top (after the other imports):

        from multi_species_section import render_multi_species_section

    3. Find a good insertion point in app.py - recommend just before the
       final `st.divider()` or at the end of the main flow. Add:

        render_multi_species_section(selected_file)

       where `selected_file` is your current audio filename variable.

    4. Restart Streamlit. A new "Multi-Species Sound Event Detection" section
       will appear in the dashboard.

ARCHITECTURE:
    - Calls multi_species_detector_v5_1.py as a subprocess (no import tangle)
    - Loads resulting JSON from detections/ folder
    - Renders summary metrics, timeline chart, event table, CSV export
    - Reuses the same plot style as the CLI detector for consistency
"""

import os
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

BASE_DIR = os.path.expanduser("~/BirdDashboard")
DETECTOR_SCRIPT = os.path.join(BASE_DIR, "multi_species_detector_v5_1.py")
DETECTIONS_DIR = os.path.join(BASE_DIR, "detections")
BIRDNET_RESULTS_DIR = os.path.join(BASE_DIR, "birdnet_results")  # where BirdNET per-file results live
SAMPLE_AUDIO_DIR = os.path.join(BASE_DIR, "sample_audio")
SAMPLE_AUDIO_OLD_DIR = os.path.join(BASE_DIR, "sample_audio_old")


def _resolve_audio_path(selected_file):
    """Find the full path of an audio file from the sidebar selection.

    The sidebar typically stores only the filename; we search known directories."""
    if not selected_file:
        return None

    # If a full path was passed
    if os.path.exists(selected_file):
        return selected_file

    # Search the likely folders
    for folder in [SAMPLE_AUDIO_DIR, SAMPLE_AUDIO_OLD_DIR]:
        candidate = os.path.join(folder, os.path.basename(selected_file))
        if os.path.exists(candidate):
            return candidate

    # Last resort - look in any subfolder of BirdDashboard
    basename = os.path.basename(selected_file)
    for root, _, files in os.walk(BASE_DIR):
        if basename in files:
            return os.path.join(root, basename)

    return None


def _run_detector(audio_path, primary_conf, secondary_conf, overlap, sensitivity, top_k, suppress_primary):
    """Run the multi_species_detector_v5_1.py script as a subprocess."""
    cmd = [
        sys.executable, DETECTOR_SCRIPT,
        "--audio", audio_path,
        "--primary-conf", str(primary_conf),
        "--secondary-conf", str(secondary_conf),
        "--overlap", str(overlap),
        "--sensitivity", str(sensitivity),
        "--top-k", str(top_k),
        "--no-plot",  # Streamlit renders its own plot
    ]
    if suppress_primary:
        cmd.append("--suppress-primary")

    result = subprocess.run(cmd, cwd=BASE_DIR, text=True, capture_output=True, timeout=180)
    return result


def _load_detection_results(audio_path):
    """Locate and parse the JSON output produced by the detector."""
    stem = Path(audio_path).stem
    json_path = os.path.join(DETECTIONS_DIR, f"{stem}_v5_1_detections.json")
    if not os.path.exists(json_path):
        return None, None
    with open(json_path) as f:
        data = json.load(f)
    return data, json_path


def _plot_timeline(events, audio_duration, primary_species):
    """Build matplotlib figure matching the CLI output style."""
    if not events:
        return None

    species_list = sorted({e["species"] for e in events})
    colors = plt.cm.tab20(np.linspace(0, 1, max(len(species_list), 1)))
    color_map = dict(zip(species_list, colors))

    fig, ax = plt.subplots(figsize=(12, max(3.5, 0.5 * len(species_list) + 1.5)))

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
                    alpha=0.90 if is_primary else 0.78,
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
    ax.grid(axis="x", linestyle="--", alpha=0.4)
    ax.set_axisbelow(True)
    plt.tight_layout()
    return fig


def render_multi_species_section(selected_file):
    """Main entry point - renders the multi-species detection section."""
    st.divider()
    st.subheader("🎼 Multi-Species Sound Event Detection")
    with st.expander("What is this?", expanded=False):
        st.markdown("""
        This section extends segment-level classification into **sound event detection** —
        identifying *multiple* species and the *timestamps* at which each one vocalises
        within a single recording. Uses the v5 BirdNET-embeddings classifier with a
        dual-threshold scheme: higher threshold for the dominant species, lower threshold
        for background species.

        **How to use:** Select an audio file from the sidebar (same as for other sections),
        adjust detection parameters if needed, and click *Run Detection*.
        """)

    audio_path = _resolve_audio_path(selected_file)
    if audio_path is None:
        st.warning(f"Could not locate audio file for: `{selected_file}`")
        return

    st.caption(f"Current file: `{os.path.basename(audio_path)}`")

    # === Parameter controls ===
    with st.expander("Detection parameters", expanded=False):
        col1, col2, col3 = st.columns(3)
        with col1:
            primary_conf = st.slider(
                "Primary species threshold",
                min_value=0.30, max_value=0.95, value=0.50, step=0.05,
                help="Confidence threshold for the dominant species",
            )
        with col2:
            secondary_conf = st.slider(
                "Secondary species threshold",
                min_value=0.10, max_value=0.70, value=0.25, step=0.05,
                help="Confidence threshold for background species",
            )
        with col3:
            sensitivity = st.slider(
                "BirdNET sensitivity",
                min_value=0.75, max_value=1.50, value=1.25, step=0.05,
                help="Higher = more sensitive (catches fainter calls)",
            )

        col4, col5, col6 = st.columns(3)
        with col4:
            overlap = st.slider(
                "Window overlap (s)",
                min_value=0.0, max_value=2.9, value=2.0, step=0.5,
                help="Larger overlap = finer time resolution; 2.0 = 1s hop",
            )
        with col5:
            top_k = st.slider(
                "Max secondaries per window",
                min_value=1, max_value=5, value=3, step=1,
                help="How many simultaneous background species per 3s window",
            )
        with col6:
            suppress_primary = st.checkbox(
                "Hide primary species in chart",
                value=False,
                help="Show only secondary species for a clearer background view",
            )

    # === Run button ===
    run = st.button("Run Multi-Species Detection", type="primary", key="run_multi_species")
    if not run:
        st.info("Click the button above to analyse the selected recording.")
        return

    # === Execute ===
    with st.spinner("Running sliding-window inference (3s windows, BirdNET embeddings)..."):
        result = _run_detector(
            audio_path=audio_path,
            primary_conf=primary_conf,
            secondary_conf=secondary_conf,
            overlap=overlap,
            sensitivity=sensitivity,
            top_k=top_k,
            suppress_primary=suppress_primary,
        )

    if result.returncode != 0:
        st.error("Detection failed.")
        st.code(result.stderr[-2000:] if result.stderr else result.stdout[-2000:])
        return

    # === Load results ===
    data, json_path = _load_detection_results(audio_path)
    if data is None:
        st.error("Detection completed but JSON results not found.")
        st.code(result.stdout[-1500:])
        return

    events = data.get("events", [])
    primary = data.get("primary_species", "—")
    duration = data.get("duration_seconds", 0)
    unique_species_in_events = len({e["species"] for e in events}) if events else 0

    # === Summary metrics ===
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Duration", f"{duration:.1f}s")
    m2.metric("Primary species", primary)
    m3.metric("Total events", len(events))
    m4.metric("Unique species", unique_species_in_events)

    if not events:
        st.warning("No detections above threshold. Try lowering the secondary threshold.")
        return

    # === Timeline chart ===
    st.markdown("#### Detection Timeline")
    fig = _plot_timeline(events, duration, primary)
    if fig is not None:
        st.pyplot(fig, width="stretch")

    # === Event table ===
    st.markdown("#### Detected Events")
    df = pd.DataFrame([
        {
            "Start (s)": round(e["start"], 2),
            "End (s)": round(e["end"], 2),
            "Duration (s)": round(e["end"] - e["start"], 2),
            "Species": e["species"],
            "Confidence": round(e["confidence"], 3),
            "Primary": "★" if e["species"] == primary else "",
        }
        for e in events
    ])
    st.dataframe(df, width="stretch", hide_index=True)

    # === CSV export ===
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Download events as CSV",
        data=csv,
        file_name=f"{Path(audio_path).stem}_multi_species_events.csv",
        mime="text/csv",
    )

    # === Advanced/diagnostic info ===
    with st.expander("Advanced: raw detector output", expanded=False):
        st.caption("Complete stdout from the detector subprocess, for debugging and verification.")
        st.code(result.stdout[-3500:], language="text")
        st.caption(f"Full JSON output saved at: `{json_path}`")
