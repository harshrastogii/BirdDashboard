"""
birddash — framework-agnostic core for the NT Bird Acoustic Monitoring platform.

This package owns all machine-learning, inference, audio-processing, and
domain logic. It has NO dependency on Streamlit (or any UI framework), so the
same code backs the current Streamlit dashboard, the upcoming FastAPI service,
and offline scripts.

Public surface:
    config      — centralised paths and pipeline constants
    audio       — audio loading & spectrogram generation
    nt_model    — custom NT CNN: load + segment-level prediction
    birdnet     — BirdNET-Analyzer wrappers (upload analysis)
    results     — loading/parsing BirdNET result CSVs
    metrics     — biodiversity indices (Shannon, Simpson)
    detection   — multi-species sound event detection pipeline
"""

__all__ = [
    "config",
    "audio",
    "nt_model",
    "birdnet",
    "results",
    "metrics",
    "detection",
]
