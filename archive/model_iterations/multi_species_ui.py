"""
Multi-Species Detection UI Component for Streamlit Dashboard
PRT840 IT Thesis | Charles Darwin University | Group 33

Add this as a new tab in app.py. Copy the render_multi_species_tab() function
into your app.py and add a new st.tabs() entry that calls it.

Minimal integration snippet for app.py:

    from multi_species_ui import render_multi_species_tab

    tab1, tab2, tab3, tab4 = st.tabs([
        "Custom NT Model", "BirdNET", "Biodiversity Metrics",
        "Multi-Species Timeline"   # <-- new tab
    ])
    with tab4:
        render_multi_species_tab(audio_path, model, species_names)
"""

import os
import json
import numpy as np
import pandas as pd
import streamlit as st
import librosa
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

# Import core detection logic from sibling module
from multi_species_detector import (
    sliding_window_predict,
    extract_detections,
    merge_detections,
    WINDOW_DURATION,
    SR,
)


def render_multi_species_tab(audio_path, model, species_names):
    """Render the multi-species timeline detection tab."""
    st.header("Multi-Species Sound Event Detection")
    st.markdown(
        "This view extends segment-level classification to identify **multiple species** "
        "within a single recording, with **timestamps** for each detection event. "
        "Adjust the threshold and window hop to balance sensitivity vs. false positives."
    )

    if not audio_path or not os.path.exists(audio_path):
        st.warning("Upload or select an audio file to run multi-species detection.")
        return

    # === Controls ===
    col1, col2, col3 = st.columns(3)
    with col1:
        threshold = st.slider(
            "Confidence threshold",
            min_value=0.10, max_value=0.90, value=0.30, step=0.05,
            help="Only detections above this confidence are reported"
        )
    with col2:
        hop_seconds = st.slider(
            "Window hop (seconds)",
            min_value=0.5, max_value=3.0, value=1.0, step=0.5,
            help="Smaller hop = more windows = finer resolution but slower"
        )
    with col3:
        top_k = st.slider(
            "Max species per window",
            min_value=1, max_value=5, value=3, step=1,
            help="How many simultaneous species to allow per window"
        )

    run_btn = st.button("Run Multi-Species Detection", type="primary")

    if not run_btn:
        st.info("Click the button above to run detection with the selected parameters.")
        return

    # === Load audio ===
    with st.spinner("Loading audio..."):
        audio, sr = librosa.load(audio_path, sr=SR, mono=True)
        duration = len(audio) / SR

    st.caption(f"Recording duration: {duration:.1f}s - Sample rate: {sr}Hz")

    # === Run detection ===
    with st.spinner("Running sliding-window inference..."):
        timestamps, probs = sliding_window_predict(audio, model, hop_seconds=hop_seconds)

    with st.spinner("Extracting detections..."):
        window_dets = extract_detections(
            timestamps, probs, species_names,
            threshold=threshold, top_k=top_k
        )
        events = merge_detections(window_dets)

    # === Summary metrics ===
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Windows analysed", len(timestamps))
    m2.metric("Raw detections", len(window_dets))
    m3.metric("Merged events", len(events))
    m4.metric("Unique species", len({e["species"] for e in events}))

    if not events:
        st.warning("No events detected above the threshold. Try lowering it.")
        return

    # === Timeline plot ===
    st.subheader("Detection Timeline")
    fig = _build_timeline_figure(events, duration)
    st.pyplot(fig, use_container_width=True)

    # === Event table ===
    st.subheader("Detected Events")
    df = pd.DataFrame([
        {
            "Start": f"{e['start']:.1f}s",
            "End": f"{e['end']:.1f}s",
            "Duration": f"{e['end'] - e['start']:.1f}s",
            "Species": e["species"],
            "Confidence": f"{e['confidence']:.3f}",
        }
        for e in events
    ])
    st.dataframe(df, width="stretch", hide_index=True)

    # === CSV export ===
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Download events as CSV",
        data=csv,
        file_name=f"multi_species_detections.csv",
        mime="text/csv",
    )

    # === Per-window probability heatmap (debug/diagnostic view) ===
    with st.expander("Advanced: per-window probability heatmap"):
        st.caption(
            "Heatmap of species probability across all windows. "
            "Useful for diagnosing missed or borderline detections."
        )
        fig2 = _build_probability_heatmap(timestamps, probs, species_names, threshold)
        st.pyplot(fig2, use_container_width=True)


def _build_timeline_figure(events, audio_duration):
    species_list = sorted({e["species"] for e in events})
    colors = plt.cm.tab20(np.linspace(0, 1, max(len(species_list), 1)))
    color_map = dict(zip(species_list, colors))

    fig, ax = plt.subplots(figsize=(12, max(3, 0.5 * len(species_list) + 1.5)))

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
    ax.set_title("Species Detection Timeline")
    ax.grid(axis="x", linestyle="--", alpha=0.4)
    ax.set_axisbelow(True)
    plt.tight_layout()
    return fig


def _build_probability_heatmap(timestamps, probs, species_names, threshold):
    fig, ax = plt.subplots(figsize=(12, max(6, 0.25 * len(species_names))))
    im = ax.imshow(
        probs.T,
        aspect="auto",
        origin="lower",
        cmap="viridis",
        extent=[timestamps[0], timestamps[-1] + WINDOW_DURATION, -0.5, len(species_names) - 0.5],
        vmin=0.0, vmax=1.0,
    )
    ax.set_yticks(range(len(species_names)))
    ax.set_yticklabels(species_names, fontsize=8)
    ax.set_xlabel("Time (seconds)")
    ax.set_title(f"Per-window class probabilities (threshold = {threshold:.2f})")
    plt.colorbar(im, ax=ax, label="Probability")
    plt.tight_layout()
    return fig
