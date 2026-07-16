"""
Multi-Species Detection Section for app.py — v2 with Listen & Label
PRT840 IT Thesis | Group 33

CHANGES FROM v1:
    - Added per-row "Listen" button that plays exactly the 3-second detection window.
    - Added inline labelling controls (Confirm / Reject / Uncertain) for each event,
      so the dashboard doubles as a hand-labelling tool for ground-truth validation.
    - Pagination (10 events per page) for long recordings (T5/T6 had 23-27 events).
    - "Export labels as CSV" button — generates ground-truth file in the format
      expected by the Assessment 3 validation methodology.
    - Toggle between "Interactive labelling mode" (new) and "Compact view" (original
      st.dataframe behaviour preserved for quick glances).
    - Annotator name input for multi-annotator workflows (Jisan/Rafel cross-labelling).

HOW TO INTEGRATE:
    1. Place this file at ~/BirdDashboard/multi_species_section.py
       (overwriting the previous version)
    2. The import in app.py is unchanged:

        from multi_species_section import render_multi_species_section

    3. Find a good insertion point in app.py - recommend just before the
       final `st.divider()` or at the end of the main flow. Add:

        render_multi_species_section(selected_file)

       where `selected_file` is your current audio filename variable.

    4. Restart Streamlit. The new section will replace the previous one.

DEPENDENCIES:
    Adds `librosa` (already installed in birdenv from preprocessing).
"""

import os
import json
import subprocess
import sys
import io
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import librosa
import soundfile as sf

# Paths are centralised in config.py (portable, env-overridable).
import config

BASE_DIR = config.BASE_DIR
DETECTOR_SCRIPT = config.DETECTOR_SCRIPT
DETECTIONS_DIR = config.DETECTIONS_DIR
SAMPLE_AUDIO_DIR = config.SAMPLE_AUDIO_DIR
SAMPLE_AUDIO_OLD_DIR = config.SAMPLE_AUDIO_OLD_DIR

EVENTS_PER_PAGE = 10


# =============================================================================
# Helpers
# =============================================================================

def _resolve_audio_path(selected_file):
    """Find the full path of an audio file from the sidebar selection."""
    if not selected_file:
        return None

    if os.path.exists(selected_file):
        return selected_file

    for folder in [SAMPLE_AUDIO_DIR, SAMPLE_AUDIO_OLD_DIR]:
        candidate = os.path.join(folder, os.path.basename(selected_file))
        if os.path.exists(candidate):
            return candidate

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
        "--no-plot",
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


@st.cache_data(show_spinner=False, max_entries=8)
def _load_audio_window(audio_path: str, start_sec: float, end_sec: float):
    """Load just a slice of audio. Cached so repeated clicks on the same window
    don't reload from disk. Returns (samples, sample_rate, wav_bytes)."""
    duration = max(0.1, end_sec - start_sec)
    y, sr = librosa.load(audio_path, sr=None, offset=start_sec, duration=duration, mono=True)

    # Encode to in-memory WAV bytes for st.audio
    buf = io.BytesIO()
    sf.write(buf, y, sr, format="WAV", subtype="PCM_16")
    buf.seek(0)
    return y, sr, buf.read()


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


# =============================================================================
# Session state helpers (per-recording label storage)
# =============================================================================

def _label_key(audio_path: str) -> str:
    """Per-recording session-state namespace."""
    return f"labels__{Path(audio_path).stem}"


def _get_labels(audio_path: str) -> dict:
    """Return dict of {event_index: 'confirm'|'reject'|'uncertain'}."""
    key = _label_key(audio_path)
    if key not in st.session_state:
        st.session_state[key] = {}
    return st.session_state[key]


def _set_label(audio_path: str, event_idx: int, label: str):
    labels = _get_labels(audio_path)
    if label is None or label == "":
        labels.pop(event_idx, None)
    else:
        labels[event_idx] = label


def _active_player_key(audio_path: str) -> str:
    return f"active_player__{Path(audio_path).stem}"


def _page_key(audio_path: str) -> str:
    return f"page__{Path(audio_path).stem}"


# =============================================================================
# Row rendering
# =============================================================================

def _render_event_row(audio_path: str, event_idx: int, event: dict, primary_species: str):
    """Render a single event row with Listen button and labelling controls."""
    is_primary = (event["species"] == primary_species)
    star = "⭐ " if is_primary else ""
    duration = event["end"] - event["start"]

    # Layout: time | species | conf | listen | label | (audio when active)
    cols = st.columns([1.2, 2.4, 0.9, 0.9, 2.2])

    with cols[0]:
        st.markdown(f"**{event['start']:.1f}s – {event['end']:.1f}s**")
        st.caption(f"{duration:.1f}s")

    with cols[1]:
        st.markdown(f"{star}{event['species']}")

    with cols[2]:
        conf = event["confidence"]
        # Colour the confidence text based on tier
        if conf >= 0.5:
            st.markdown(f"<span style='color:#2e7d32'><b>{conf:.2f}</b></span>", unsafe_allow_html=True)
        elif conf >= 0.25:
            st.markdown(f"<span style='color:#ef6c00'><b>{conf:.2f}</b></span>", unsafe_allow_html=True)
        else:
            st.markdown(f"<span style='color:#999'>{conf:.2f}</span>", unsafe_allow_html=True)

    with cols[3]:
        listen_clicked = st.button("▶ Listen", key=f"listen_{event_idx}", use_container_width=True)
        if listen_clicked:
            st.session_state[_active_player_key(audio_path)] = event_idx

    with cols[4]:
        current_label = _get_labels(audio_path).get(event_idx, "")
        options = ["", "✓ Confirm", "✗ Reject", "? Uncertain"]
        index = options.index(current_label) if current_label in options else 0
        choice = st.radio(
            "Label",
            options=options,
            index=index,
            key=f"label_{event_idx}",
            label_visibility="collapsed",
            horizontal=True,
        )
        _set_label(audio_path, event_idx, choice)

    # Audio player appears only for the active row
    if st.session_state.get(_active_player_key(audio_path)) == event_idx:
        try:
            _, sr, wav_bytes = _load_audio_window(audio_path, event["start"], event["end"])
            st.audio(wav_bytes, format="audio/wav")
        except Exception as e:
            st.error(f"Could not load audio window: {e}")


# =============================================================================
# Main entry point
# =============================================================================

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

        **New: Listen & Label workflow.** Each detection row has a *Listen* button that
        plays just the 3-second window. Use the radio buttons to mark each event as
        Confirm, Reject, or Uncertain — these labels can be exported as a CSV ground-truth
        file for validation analysis.
        """)

    audio_path = _resolve_audio_path(selected_file)
    if audio_path is None:
        st.warning(f"Could not locate audio file for: `{selected_file}`")
        return

    st.caption(f"Current file: `{os.path.basename(audio_path)}`")

    # === Annotator name (for multi-person labelling) ===
    annotator = st.text_input(
        "Annotator name",
        value=st.session_state.get("annotator_name", ""),
        placeholder="e.g. Jisan, Rafel — used for label CSV export",
        key="annotator_name",
        help="Your name will be saved with each label so multi-annotator agreement can be measured.",
    )

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

    # If we have prior detection results for this file, allow viewing them
    # without forcing a re-run
    cached_data, cached_path = _load_detection_results(audio_path)
    has_cached = cached_data is not None

    if not run and not has_cached:
        st.info("Click the button above to analyse the selected recording.")
        return

    # === Execute (or use cached) ===
    if run:
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

        data, json_path = _load_detection_results(audio_path)
        if data is None:
            st.error("Detection completed but JSON results not found.")
            st.code(result.stdout[-1500:])
            return
        stdout_text = result.stdout
    else:
        st.caption("Showing cached detection results. Click *Run* to refresh.")
        data, json_path = cached_data, cached_path
        stdout_text = ""

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

    # === Mode toggle ===
    st.markdown("#### Detected Events")
    view_mode = st.radio(
        "View mode",
        options=["Interactive (Listen & Label)", "Compact (read-only table)"],
        index=0,
        horizontal=True,
        label_visibility="collapsed",
    )

    if view_mode == "Compact (read-only table)":
        # Original behaviour preserved
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
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Download events as CSV",
            data=csv,
            file_name=f"{Path(audio_path).stem}_multi_species_events.csv",
            mime="text/csv",
        )
    else:
        # === Interactive view: paginated list with Listen + Label ===
        labels = _get_labels(audio_path)
        n_labelled = len(labels)
        n_confirmed = sum(1 for v in labels.values() if v.startswith("✓"))
        n_rejected = sum(1 for v in labels.values() if v.startswith("✗"))
        n_uncertain = sum(1 for v in labels.values() if v.startswith("?"))

        # Progress strip
        prog_cols = st.columns(5)
        prog_cols[0].metric("Labelled", f"{n_labelled} / {len(events)}")
        prog_cols[1].metric("Confirmed", n_confirmed)
        prog_cols[2].metric("Rejected", n_rejected)
        prog_cols[3].metric("Uncertain", n_uncertain)
        prog_cols[4].progress(n_labelled / len(events) if events else 0, text="Coverage")

        # Pagination
        n_pages = (len(events) + EVENTS_PER_PAGE - 1) // EVENTS_PER_PAGE
        page_state_key = _page_key(audio_path)
        if page_state_key not in st.session_state:
            st.session_state[page_state_key] = 0

        if n_pages > 1:
            pcol1, pcol2, pcol3 = st.columns([1, 2, 1])
            with pcol1:
                if st.button("◀ Previous", disabled=st.session_state[page_state_key] == 0,
                             key="prev_page", use_container_width=True):
                    st.session_state[page_state_key] -= 1
                    st.rerun()
            with pcol2:
                current_page = st.session_state[page_state_key]
                st.markdown(
                    f"<div style='text-align:center;padding-top:0.4em'>Page <b>{current_page + 1}</b> of {n_pages}</div>",
                    unsafe_allow_html=True,
                )
            with pcol3:
                if st.button("Next ▶", disabled=st.session_state[page_state_key] == n_pages - 1,
                             key="next_page", use_container_width=True):
                    st.session_state[page_state_key] += 1
                    st.rerun()

        # Header row
        hdr = st.columns([1.2, 2.4, 0.9, 0.9, 2.2])
        hdr[0].markdown("**Time**")
        hdr[1].markdown("**Species**")
        hdr[2].markdown("**Conf.**")
        hdr[3].markdown("**Audio**")
        hdr[4].markdown("**Label**")
        st.divider()

        # Render the current page
        page = st.session_state[page_state_key]
        start_idx = page * EVENTS_PER_PAGE
        end_idx = min(start_idx + EVENTS_PER_PAGE, len(events))

        for i in range(start_idx, end_idx):
            _render_event_row(audio_path, i, events[i], primary)
            st.divider()

        # === Export labels as CSV ===
        st.markdown("#### Export ground-truth labels")
        if not annotator:
            st.info("Enter your annotator name above to enable CSV export.")
        elif n_labelled == 0:
            st.info("Mark at least one event as Confirm / Reject / Uncertain to enable export.")
        else:
            label_rows = []
            for i, event in enumerate(events):
                lbl = labels.get(i, "")
                if not lbl:
                    continue
                # Strip the icon prefix
                clean_lbl = lbl.split(" ", 1)[-1].strip().lower() if " " in lbl else lbl.strip().lower()
                label_rows.append({
                    "recording_id": Path(audio_path).stem,
                    "event_index": i,
                    "start_sec": round(event["start"], 2),
                    "end_sec": round(event["end"], 2),
                    "predicted_species": event["species"],
                    "predicted_confidence": round(event["confidence"], 3),
                    "is_primary_prediction": event["species"] == primary,
                    "annotator": annotator,
                    "annotator_label": clean_lbl,
                    "labelled_at": datetime.now().isoformat(timespec="seconds"),
                })
            label_df = pd.DataFrame(label_rows)
            csv_bytes = label_df.to_csv(index=False).encode("utf-8")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            fname = f"{Path(audio_path).stem}_labels_{annotator.replace(' ', '_')}_{timestamp}.csv"
            st.download_button(
                label=f"⬇ Download {n_labelled} labels as CSV",
                data=csv_bytes,
                file_name=fname,
                mime="text/csv",
                type="primary",
            )

            with st.expander("Preview label CSV", expanded=False):
                st.dataframe(label_df, width="stretch", hide_index=True)

        # Reset button
        if n_labelled > 0:
            if st.button("⟲ Reset all labels for this recording", type="secondary"):
                st.session_state[_label_key(audio_path)] = {}
                st.rerun()

    # === Advanced/diagnostic info ===
    with st.expander("Advanced: raw detector output", expanded=False):
        if stdout_text:
            st.caption("Complete stdout from the detector subprocess, for debugging and verification.")
            st.code(stdout_text[-3500:], language="text")
        st.caption(f"Full JSON output saved at: `{json_path}`")
