import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="librosa")
import streamlit as st
import pandas as pd
import numpy as np
import librosa
import plotly.express as px
import plotly.graph_objects as go
import os

# All ML / inference / domain logic lives in the framework-agnostic birddash
# package (no Streamlit inside). app.py is a thin UI layer over it.
from birddash import config, audio, birdnet, results, metrics
from birddash import nt_model as nt_cnn
from multi_species_section import render_multi_species_section

# Page config
st.set_page_config(
    page_title="NT Bird Acoustic Monitor",
    page_icon="logo.png",
    layout="wide"
)

st.image("logo.svg", width=120)
st.title("NT Bird Acoustic Monitoring Dashboard")
st.caption("Interactive Visual Analytics System for AI-Powered Biodiversity Acoustic Monitoring | PRT840 IT Thesis | Charles Darwin University")

# ========== INFO PANEL: About this Dashboard ==========
with st.expander("ℹ️ About this Dashboard — Click to learn how to use it", expanded=False):
    st.markdown("""
    ### What does this dashboard do?
    
    This dashboard processes bird audio recordings using **two AI models** to identify bird species from sound:
    
    - **BirdNET** — A global pre-trained model developed by the Cornell Lab of Ornithology. Trained primarily 
      on Northern Hemisphere bird sounds, it often misidentifies Australian species.
    - **Custom NT Model** — Our own CNN model trained specifically on **24 Northern Territory bird species** 
      using 18,462 mel spectrogram segments from Xeno-canto recordings. Achieves **92.7% test accuracy** on NT species.
    
    The dashboard lets you compare both models side-by-side, demonstrating why region-specific models 
    are critical for biodiversity monitoring in the Northern Territory.
    
    ### How does the analysis work?
    
    1. **Audio is split into 3-second segments** — Both models analyse each 3-second window independently.
    2. **Each segment gets predictions** — Each model predicts which bird species it thinks it heard, along 
       with a **confidence score** (0-100%) indicating how sure it is.
    3. **Results are compared** — The dashboard shows predictions from both models, highlighting where 
       the custom NT model outperforms BirdNET on local species.
    
    ### Understanding the key columns
    
    | Column | What it means |
    |--------|--------------|
    | **Start (s)** | The timestamp (in seconds) where this 3-second analysis window begins |
    | **End (s)** | The timestamp where this analysis window ends (always Start + 3) |
    | **Common name / Species** | The bird species the model thinks it heard in this window |
    | **Confidence** | How confident the model is in its prediction (0% = guessing, 100% = very sure) |
    
    ### What does the confidence threshold do?
    
    The sidebar slider lets you filter out low-confidence detections. A higher threshold (e.g., 0.50) shows only 
    predictions the model is fairly sure about. A lower threshold (e.g., 0.10) shows more detections but includes 
    more uncertain or potentially incorrect predictions.
    
    ### Why does BirdNET get species wrong?
    
    BirdNET misidentifies Australian birds as European or North American species. **This is expected 
    and is a key finding of this research.** BirdNET was trained primarily on Northern Hemisphere bird sounds. 
    Our custom NT model addresses this gap by training specifically on local species vocalisations.
    
    ### Who is this for?
    
    - **Field ecologists**: Upload recordings from monitoring sites to quickly scan for species presence
    - **Conservation managers**: Track threatened species across sites and seasons
    - **Policy makers**: Use biodiversity metrics and exportable summaries for environmental impact assessments
    - **Researchers**: Compare BirdNET's global model against our custom NT-specific model
    """)

# --- Cached data-access & inference wrappers -----------------------------
# The heavy logic lives in the birddash package; these thin wrappers only add
# Streamlit caching, which is a UI concern and stays out of the core package.

@st.cache_data
def load_all_results(results_dir):
    return results.load_results(results_dir)

@st.cache_data
def generate_spectrogram(audio_path):
    return audio.generate_spectrogram(audio_path)

@st.cache_resource
def load_nt_model():
    return nt_cnn.load_model(config.NT_MODEL_PATH)

@st.cache_data
def load_label_map():
    return nt_cnn.load_label_map(config.NT_LABEL_MAP_PATH)

# Load NT model and label map at startup
nt_model = load_nt_model()
nt_label_map = load_label_map()

# ========== SIDEBAR ==========
st.sidebar.header("Filters")

# --- File upload section ---
st.sidebar.subheader("Upload new audio")
uploaded_files = st.sidebar.file_uploader(
    "Drop audio files here",
    type=["mp3", "wav", "flac", "ogg"],
    accept_multiple_files=True,
    help="Upload bird audio recordings to analyse with BirdNET. Supported formats: MP3, WAV, FLAC, OGG."
)

SELECT_KEY = "selected_recording"

if uploaded_files:
    # Process each uploaded file exactly once (file_id is stable across the
    # reruns that Streamlit triggers while the uploader still holds the file),
    # so later widget interactions don't re-trigger analysis or noise.
    handled_ids = st.session_state.setdefault("_handled_upload_ids", set())
    fresh = [uf for uf in uploaded_files if uf.file_id not in handled_ids]

    if fresh:
        os.makedirs(config.SAMPLE_AUDIO_DIR, exist_ok=True)
        saved_new = []
        skipped_existing = []
        for uf in fresh:
            save_path = config.SAMPLE_AUDIO_DIR / uf.name
            if save_path.exists():
                skipped_existing.append(uf.name)
            else:
                save_path.write_bytes(uf.getbuffer())
                saved_new.append(save_path)
            handled_ids.add(uf.file_id)

        if skipped_existing:
            st.sidebar.info(
                "Already in the library (skipped): " + ", ".join(skipped_existing)
            )

        if saved_new:
            with st.sidebar.status(
                f"Analysing {len(saved_new)} new recording(s) with BirdNET...",
                expanded=True,
            ) as status:
                try:
                    first_ref = None
                    for path in saved_new:
                        st.write(f"Processing `{path.name}`...")
                        # Analyse ONLY the new file (not the whole directory),
                        # so one unrelated bad recording can't abort the batch.
                        # Pass a path relative to BASE_DIR so BirdNET writes the
                        # File column as "sample_audio/<name>", matching every
                        # other recording (required for selection + playback).
                        rel_input = os.path.relpath(path, config.BASE_DIR)
                        birdnet.analyze_upload(rel_input, output_dir=config.BIRDNET_RESULTS_DIR)
                        if first_ref is None:
                            first_ref = rel_input
                    status.update(label="Analysis complete!", state="complete")
                    st.cache_data.clear()
                    # Make the first freshly uploaded recording the active one,
                    # so the user immediately sees their upload instead of the
                    # dashboard staying on the previous selection.
                    if first_ref is not None:
                        st.session_state[SELECT_KEY] = first_ref
                except Exception as e:
                    status.update(label="Analysis failed", state="error")
                    st.exception(e)

st.sidebar.divider()

# Load results
results_dir = config.BIRDNET_RESULTS_DIR
df = load_all_results(results_dir)

if df.empty:
    st.error("No BirdNET results found. Upload audio files or run the analysis first.")
    st.stop()

# File filter
files = sorted(df["File"].unique())
# Honour an auto-selected upload if it produced detections; otherwise fall
# back to the first recording (guards against a silent upload that yielded no
# rows and therefore isn't among the options).
desired = st.session_state.get(SELECT_KEY)
default_index = files.index(desired) if desired in files else 0
selected_file = st.sidebar.selectbox(
    "Select recording",
    options=files,
    index=default_index,
    format_func=lambda x: os.path.basename(x).replace(".mp3", "").replace(".wav", "").replace("_", " ")
)
st.session_state[SELECT_KEY] = selected_file

# Confidence slider
min_confidence = st.sidebar.slider(
    "Minimum confidence",
    0.0, 1.0, 0.25, 0.05,
    help="Filter out detections below this confidence level. Higher = fewer but more reliable detections. Lower = more detections but more noise."
)

# Filter data
filtered = df[(df["File"] == selected_file) & (df["Confidence"] >= min_confidence)]

# Run NT model prediction early so we can use results in top metrics
nt_results = None
nt_top1 = None
nt_top1_filtered = None
if nt_model is not None and os.path.exists(selected_file):
    with st.spinner("Running Custom NT Model analysis..."):
        nt_results = nt_cnn.predict(selected_file, nt_model, nt_label_map)
    if len(nt_results) > 0:
        nt_top1 = nt_results[nt_results["Rank"] == 1].copy()
        nt_top1_filtered = nt_top1[nt_top1["Confidence"] >= min_confidence]

# ========== TOP METRICS — BOTH MODELS ==========
st.markdown("#### 🇦🇺 Custom NT Model")
col_nt1, col_nt2, col_nt3, col_nt4 = st.columns(4)
with col_nt1:
    nt_count = len(nt_top1_filtered) if nt_top1_filtered is not None else 0
    st.metric("Segments analysed", nt_count,
              help="Number of 3-second segments analysed by the custom NT model above your confidence threshold")
with col_nt2:
    nt_species = nt_top1_filtered["Species"].nunique() if nt_top1_filtered is not None and len(nt_top1_filtered) > 0 else 0
    st.metric("Unique species", nt_species,
              help="Number of different NT species identified by the custom model")
with col_nt3:
    nt_avg = nt_top1_filtered["Confidence"].mean() if nt_top1_filtered is not None and len(nt_top1_filtered) > 0 else 0
    st.metric("Avg confidence", f"{nt_avg:.1%}",
              help="Average confidence score from the custom NT model")
with col_nt4:
    if nt_top1 is not None and len(nt_top1) > 0:
        best_nt = nt_top1.loc[nt_top1["Confidence"].idxmax()]
        st.metric("Top species", best_nt["Species"],
                  help="The species predicted with highest confidence by the custom NT model")
    else:
        st.metric("Top species", "N/A")

st.markdown("#### 🌍 BirdNET v2.4")
col_bn1, col_bn2, col_bn3, col_bn4 = st.columns(4)
with col_bn1:
    st.metric("Total detections", len(filtered),
              help="Number of 3-second segments where BirdNET detected a species above your confidence threshold")
with col_bn2:
    st.metric("Unique species", filtered["Common name"].nunique(),
              help="Number of different species BirdNET identified in this recording")
with col_bn3:
    avg_conf = filtered["Confidence"].mean() if len(filtered) > 0 else 0
    st.metric("Avg confidence", f"{avg_conf:.1%}",
              help="Average confidence score across all BirdNET detections")
with col_bn4:
    if len(filtered) > 0:
        top = filtered.loc[filtered["Confidence"].idxmax()]
        st.metric("Top species", top["Common name"],
                  help="The species detected with the highest confidence score by BirdNET")
    else:
        st.metric("Top species", "N/A")

st.divider()

# ========== AUDIO PLAYER AND SPECTROGRAM ==========
col_audio, col_spec = st.columns([1, 2])

with col_audio:
    st.subheader("Audio player")
    if os.path.exists(selected_file):
        st.audio(selected_file)
    else:
        st.warning("Audio file not found")
    
    st.subheader("Recording info")
    basename = os.path.basename(selected_file)
    st.write(f"**File:** {basename}")
    file_size = os.path.getsize(selected_file) if os.path.exists(selected_file) else 0
    st.write(f"**Size:** {file_size / 1024:.0f} KB")
    st.write(f"**Detections:** {len(filtered)} (above {min_confidence:.0%} confidence)")
    
    # Ground truth info
    ground_truth = {
        "Laughing_Kookaburra": "Laughing Kookaburra (*Dacelo novaeguineae*)",
        "Rainbow_Bee-eater": "Rainbow Bee-eater (*Merops ornatus*)",
        "Sulphur-crested_Cockatoo": "Sulphur-crested Cockatoo (*Cacatua galerita*)",
        "Willie_Wagtail": "Willie Wagtail (*Rhipidura leucophrys*)",
    }
    for key, label in ground_truth.items():
        if key in basename:
            st.write(f"**Actual species:** {label}")
            if len(filtered) > 0:
                top_pred = filtered.loc[filtered["Confidence"].idxmax(), "Common name"]
                if key.replace("_", " ").lower() not in top_pred.lower():
                    st.error(f"⚠️ BirdNET misidentified this as **{top_pred}**")
                else:
                    st.success(f"✅ BirdNET correctly identified this species")
            break

with col_spec:
    st.subheader("Mel spectrogram")
    with st.expander("What is a spectrogram?", expanded=False):
        st.markdown("""
        A **mel spectrogram** is a visual representation of sound. The horizontal axis shows **time** (seconds), 
        the vertical axis shows **frequency** (pitch, in Hz — higher = higher pitched sounds), and the colour 
        intensity shows **loudness** (brighter = louder). Each bird species produces a unique pattern — their 
        acoustic "fingerprint." Researchers use spectrograms to visually identify calls, compare species, 
        and spot patterns that AI models might miss.
        """)
    
    if os.path.exists(selected_file):
        with st.spinner("Generating spectrogram..."):
            S_db, sr, y = generate_spectrogram(selected_file)
            
            fig_spec = go.Figure(data=go.Heatmap(
                z=S_db,
                x=np.linspace(0, len(y)/sr, S_db.shape[1]),
                y=librosa.mel_frequencies(n_mels=128, fmax=8000),
                colorscale="Viridis",
                colorbar=dict(title="dB"),
            ))
            fig_spec.update_layout(
                xaxis_title="Time (seconds)",
                yaxis_title="Frequency (Hz)",
                height=300,
                margin=dict(l=0, r=0, t=10, b=0),
                yaxis=dict(type="log", range=[np.log10(200), np.log10(8000)])
            )
            st.plotly_chart(fig_spec, width="stretch")

st.divider()

# ========== NT MODEL vs BIRDNET COMPARISON ==========
st.subheader("🤖 Model comparison: Custom NT Model vs BirdNET")
with st.expander("Why compare two models?", expanded=False):
    st.markdown("""
    **BirdNET** is a global model trained primarily on Northern Hemisphere bird species. While it's excellent 
    for European and North American birds, it consistently misidentifies Australian species because their 
    vocalisations are underrepresented in its training data.
    
    **Our Custom NT Model** was trained specifically on **24 Northern Territory bird species** using 18,462 
    mel spectrogram segments sourced from Xeno-canto. It achieves **92.7% test accuracy** on NT species.
    
    This side-by-side comparison demonstrates the importance of **region-specific acoustic models** for 
    biodiversity monitoring in Australia's Top End.
    
    | Model | Training data | NT species accuracy | Best for |
    |-------|--------------|-------------------|----------|
    | **BirdNET v2.4** | ~6,000 global species | ~0% on NT species | Northern Hemisphere birds |
    | **Custom NT CNN** | 24 NT species, 18,462 segments | 92.7% test accuracy | Northern Territory birds |
    """)

if nt_model is not None and nt_results is not None and len(nt_results) > 0:

    # --- NT Model top-5 predictions for highest-confidence segment ---
    st.markdown("##### NT Model — Top 5 predictions (highest-confidence segment)")
    if len(nt_top1) > 0:
        best_segment_start = nt_top1.loc[nt_top1["Confidence"].idxmax(), "Start (s)"]
        best_segment = nt_results[nt_results["Start (s)"] == best_segment_start].sort_values("Rank")

        fig_top5 = px.bar(
            best_segment,
            x="Confidence",
            y="Species",
            orientation="h",
            color="Confidence",
            color_continuous_scale="Viridis",
            labels={"Confidence": "Confidence score", "Species": ""},
        )
        fig_top5.update_layout(
            height=250,
            margin=dict(l=0, r=0, t=10, b=0),
            coloraxis_showscale=False,
            yaxis=dict(autorange="reversed"),
            xaxis=dict(range=[0, 1])
        )
        st.plotly_chart(fig_top5, width="stretch")

    # --- Confidence comparison across segments ---
    st.markdown("##### Confidence comparison across segments")
    col_ntline, col_bnline = st.columns(2)

    with col_ntline:
        st.caption("Custom NT Model — top prediction per segment")
        if len(nt_top1) > 0:
            fig_nt_conf = px.scatter(
                nt_top1,
                x="Start (s)",
                y="Confidence",
                color="Species",
                size="Confidence",
                hover_data=["Species", "Confidence"],
                labels={"Start (s)": "Time (seconds)", "Confidence": "Confidence"}
            )
            fig_nt_conf.update_layout(
                height=280,
                margin=dict(l=0, r=0, t=10, b=0),
                yaxis=dict(range=[0, 1]),
                legend=dict(orientation="h", yanchor="bottom", y=-0.4, font=dict(size=10))
            )
            st.plotly_chart(fig_nt_conf, width="stretch")

    with col_bnline:
        st.caption("BirdNET — detections per segment")
        if len(filtered) > 0:
            fig_bn_conf = px.scatter(
                filtered,
                x="Start (s)",
                y="Confidence",
                color="Common name",
                size="Confidence",
                hover_data=["Common name", "Confidence"],
                labels={"Start (s)": "Time (seconds)", "Confidence": "Confidence"}
            )
            fig_bn_conf.update_layout(
                height=280,
                margin=dict(l=0, r=0, t=10, b=0),
                yaxis=dict(range=[0, 1]),
                legend=dict(orientation="h", yanchor="bottom", y=-0.4, font=dict(size=10))
            )
            st.plotly_chart(fig_bn_conf, width="stretch")
        else:
            st.info("No BirdNET detections above threshold")

    # --- Full NT Model results table ---
    st.markdown("##### NT Model — All segment predictions (Top-1)")
    if len(nt_top1_filtered) > 0:
        nt_display = nt_top1_filtered[["Start (s)", "End (s)", "Species", "Confidence"]].copy()
        nt_display["Confidence"] = nt_display["Confidence"].apply(lambda x: f"{x:.1%}")
        st.dataframe(nt_display, width="stretch", hide_index=True, height=300)
    else:
        st.info("No NT model predictions above the confidence threshold. Try lowering it in the sidebar.")

elif nt_model is None:
    st.warning(
        "⚠️ Custom NT model not found. Please ensure the model file is at: `models/nt_bird_cnn_best.keras` "
        "and the label map is at: `spectrograms/label_map.json`"
    )

st.divider()

# ========== DETECTION RESULTS AND SPECIES CHART ==========
st.subheader("BirdNET detection results")
col_table, col_chart = st.columns([1, 1])

with col_table:
    with st.expander("Understanding these results", expanded=False):
        st.markdown("""
        Each row represents a **3-second window** of the audio recording. BirdNET analysed that window and 
        predicted which species it sounds like. Multiple species can appear for the same time window because 
        BirdNET reports all predictions above your confidence threshold.
        
        **Important:** The "Common name" column shows what BirdNET *thinks* it heard — not necessarily what's 
        actually in the recording. Compare with the "Actual species" shown in Recording info to see if 
        BirdNET got it right.
        """)
    
    if len(filtered) > 0:
        display_df = filtered[["Start (s)", "End (s)", "Common name", "Scientific name", "Confidence"]].copy()
        display_df["Confidence"] = display_df["Confidence"].apply(lambda x: f"{x:.1%}")
        st.dataframe(display_df, width="stretch", hide_index=True, height=350)
    else:
        st.info("No detections above the confidence threshold. Try lowering it in the sidebar.")

with col_chart:
    st.subheader("Species by confidence")
    if len(filtered) > 0:
        species_conf = filtered.groupby("Common name")["Confidence"].max().sort_values(ascending=True).tail(10)
        fig_bar = px.bar(
            x=species_conf.values,
            y=species_conf.index,
            orientation="h",
            labels={"x": "Max confidence", "y": "Species"},
            color=species_conf.values,
            color_continuous_scale="Viridis"
        )
        fig_bar.update_layout(
            height=350,
            margin=dict(l=0, r=0, t=10, b=0),
            showlegend=False,
            coloraxis_showscale=False
        )
        st.plotly_chart(fig_bar, width="stretch")

st.divider()

# ========== DETECTION TIMELINE ==========
st.subheader("Detection timeline")
with st.expander("How to read this chart", expanded=False):
    st.markdown("""
    This scatter plot shows **when** each species was detected across the recording. Each dot represents 
    a detection, positioned at the time it occurred (x-axis) and grouped by species (y-axis). The size and 
    colour of each dot represent the confidence score. Larger, brighter dots = higher confidence.
    
    **For ecologists:** This helps identify temporal activity patterns — when species are most vocal, 
    whether multiple species overlap, and which time segments have the most acoustic activity.
    """)

if len(filtered) > 0:
    fig_timeline = px.scatter(
        filtered,
        x="Start (s)",
        y="Common name",
        size="Confidence",
        color="Confidence",
        color_continuous_scale="Viridis",
        hover_data=["Scientific name", "Confidence", "Start (s)", "End (s)"],
        labels={"Start (s)": "Time (seconds)", "Common name": "Species"}
    )
    fig_timeline.update_layout(
        height=max(200, filtered["Common name"].nunique() * 40),
        margin=dict(l=0, r=0, t=10, b=0)
    )
    st.plotly_chart(fig_timeline, width="stretch")

st.divider()

# ========== MULTI-SPECIES SOUND EVENT DETECTION ==========
render_multi_species_section(selected_file)

st.divider()

# ========== BIODIVERSITY METRICS (for policy makers) ==========
st.subheader("Biodiversity metrics")
with st.expander("What are biodiversity indices and why do they matter?", expanded=False):
    st.markdown("""
    Biodiversity indices are standardised numerical measures that summarise the diversity of species 
    at a site. They are widely used in **environmental impact assessments**, **conservation planning**, 
    and **policy reports** because they condense complex ecological data into comparable numbers.
    
    | Index | Range | What it measures | Use in policy |
    |-------|-------|-----------------|---------------|
    | **Species Richness** | 0 to ∞ | Raw count of different species detected | Basic measure for site comparison |
    | **Shannon Index (H')** | 0 to ~4.5 | Species diversity accounting for abundance | Higher = more diverse ecosystem; used in environmental impact assessments |
    | **Simpson Index (D)** | 0 to 1 | Probability that two random detections are different species | Higher = more even distribution; used in conservation status reporting |
    
    **For policy makers:** These metrics can be tracked over time to detect ecosystem decline. A site 
    showing decreasing Shannon Index over successive monitoring periods may indicate habitat degradation 
    requiring intervention.
    """)

all_filtered = df[df["Confidence"] >= min_confidence]
if len(all_filtered) > 0:
    col_bio1, col_bio2, col_bio3 = st.columns(3)
    
    # Calculate per-file metrics
    bio_data = []
    for file in all_filtered["File"].unique():
        file_df = all_filtered[all_filtered["File"] == file]
        species_counts = file_df["Common name"].value_counts().to_dict()
        bio_data.append({
            "Recording": os.path.basename(file).replace(".mp3", "").replace(".wav", "").replace("_", " "),
            "Species Richness": len(species_counts),
            "Shannon Index (H')": round(metrics.shannon_index(species_counts), 3),
            "Simpson Index (D)": round(metrics.simpson_index(species_counts), 3),
            "Total Detections": len(file_df)
        })
    
    bio_df = pd.DataFrame(bio_data)
    
    with col_bio1:
        st.metric("Overall species richness",
                  all_filtered["Common name"].nunique(),
                  help="Total number of unique species detected across all recordings")
    
    with col_bio2:
        overall_counts = all_filtered["Common name"].value_counts().to_dict()
        st.metric("Overall Shannon Index",
                  f"{metrics.shannon_index(overall_counts):.3f}",
                  help="Shannon diversity index across all recordings. Higher values (>2.0) indicate rich, diverse ecosystems")
    
    with col_bio3:
        st.metric("Overall Simpson Index",
                  f"{metrics.simpson_index(overall_counts):.3f}",
                  help="Simpson diversity index across all recordings. Values close to 1.0 indicate high evenness across species")
    
    st.dataframe(bio_df, width="stretch", hide_index=True)

st.divider()

# ========== CROSS-FILE COMPARISON ==========
st.subheader("All recordings comparison")
with st.expander("Comparing across monitoring sites", expanded=False):
    st.markdown("""
    These charts compare detection patterns across all uploaded recordings. In a real deployment, 
    each recording would represent a different **monitoring site** or **time period**.
    
    **For conservation managers:** Compare species richness and detection counts across sites to 
    identify biodiversity hotspots, degraded areas, or sites that need more monitoring attention.
    
    **For policy makers:** Site-level comparisons provide evidence for land-use decisions, protected 
    area designation, and environmental offset requirements.
    """)

if len(all_filtered) > 0:
    col_comp1, col_comp2 = st.columns(2)
    
    with col_comp1:
        detections_per_file = all_filtered.groupby("File").size().reset_index(name="Detections")
        detections_per_file["File"] = detections_per_file["File"].apply(
            lambda x: os.path.basename(x).replace(".mp3", "").replace(".wav", "").replace("_", " "))
        fig_files = px.bar(
            detections_per_file, x="File", y="Detections",
            color="Detections", color_continuous_scale="Viridis",
            labels={"File": "Recording", "Detections": "Number of detections"}
        )
        fig_files.update_layout(height=300, margin=dict(l=0, r=0, t=10, b=0), coloraxis_showscale=False)
        st.plotly_chart(fig_files, width="stretch")
    
    with col_comp2:
        species_per_file = all_filtered.groupby("File")["Common name"].nunique().reset_index(name="Species")
        species_per_file["File"] = species_per_file["File"].apply(
            lambda x: os.path.basename(x).replace(".mp3", "").replace(".wav", "").replace("_", " "))
        fig_species = px.bar(
            species_per_file, x="File", y="Species",
            color="Species", color_continuous_scale="Viridis",
            labels={"File": "Recording", "Species": "Unique species detected"}
        )
        fig_species.update_layout(height=300, margin=dict(l=0, r=0, t=10, b=0), coloraxis_showscale=False)
        st.plotly_chart(fig_species, width="stretch")

st.divider()

# ========== EXPORT SECTION (for policy makers) ==========
st.subheader("Export data")
with st.expander("Download results for reports and assessments", expanded=False):
    st.markdown("""
    Export detection data and biodiversity metrics for use in:
    - Environmental Impact Assessments (EIA)
    - Conservation status reports
    - Threatened species monitoring reports
    - Academic publications and presentations
    """)

col_exp1, col_exp2, col_exp3 = st.columns(3)
with col_exp1:
    if len(filtered) > 0:
        csv_detections = filtered.to_csv(index=False)
        st.download_button(
            "📥 BirdNET detections (CSV)",
            csv_detections,
            f"birdnet_detections_{os.path.basename(selected_file).replace('.mp3','')}.csv",
            "text/csv",
            help="Download the filtered BirdNET detection table for this recording"
        )
with col_exp2:
    if nt_model is not None and os.path.exists(selected_file):
        try:
            nt_export = nt_results[nt_results["Rank"] == 1].copy()
            if len(nt_export) > 0:
                csv_nt = nt_export.to_csv(index=False)
                st.download_button(
                    "📥 NT Model predictions (CSV)",
                    csv_nt,
                    f"nt_model_predictions_{os.path.basename(selected_file).replace('.mp3','')}.csv",
                    "text/csv",
                    help="Download the custom NT model predictions for this recording"
                )
        except NameError:
            pass
with col_exp3:
    if len(all_filtered) > 0 and 'bio_df' in dir():
        csv_bio = bio_df.to_csv(index=False)
        st.download_button(
            "📥 Biodiversity metrics (CSV)",
            csv_bio,
            "biodiversity_metrics_summary.csv",
            "text/csv",
            help="Download biodiversity indices for all recordings"
        )

# ========== FOOTER ==========
st.divider()
st.caption(
    "PRT840 IT Thesis | Designing an Interactive Visual Analytics System for AI-Powered Biodiversity "
    "Acoustic Monitoring | Charles Darwin University | Supervisor: Dr. Md Rafiqul Islam"
)
