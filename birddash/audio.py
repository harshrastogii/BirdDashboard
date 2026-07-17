"""Audio loading and spectrogram generation.

Framework-agnostic. Returns plain numpy arrays / bytes; any UI caching is the
caller's concern.
"""

import io

import numpy as np
import librosa
import soundfile as sf

from birddash import config


def generate_spectrogram(audio_path, sr=config.SAMPLE_RATE,
                         duration=config.DISPLAY_SPEC_DURATION,
                         n_mels=config.N_MELS, fmax=config.DISPLAY_SPEC_FMAX):
    """Mel spectrogram (in dB) for the dashboard heatmap.

    Returns (S_db, sr, y). Capped at `duration` seconds for display responsiveness.
    """
    y, sr = librosa.load(audio_path, sr=sr, duration=duration)
    S = librosa.feature.melspectrogram(y=y, sr=sr, n_mels=n_mels, fmax=fmax)
    S_db = librosa.power_to_db(S, ref=np.max)
    return S_db, sr, y


def render_spectrogram_png(audio_path, sr=config.SAMPLE_RATE,
                           duration=config.DISPLAY_SPEC_DURATION,
                           n_mels=config.N_MELS, fmax=config.DISPLAY_SPEC_FMAX) -> bytes:
    """Render a mel spectrogram to PNG bytes (server-side, reliable).

    Replaces client-side FFT so the spectrogram always renders. Styled to sit
    cleanly inside the Observatory design system (dark axis-less panel).
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import librosa.display

    S_db, sr, _ = generate_spectrogram(audio_path, sr=sr, duration=duration, n_mels=n_mels, fmax=fmax)

    fig, ax = plt.subplots(figsize=(10, 3.2))
    librosa.display.specshow(
        S_db, sr=sr, x_axis="time", y_axis="mel", fmax=fmax, ax=ax, cmap="viridis",
    )
    ax.set_xlabel("Time (s)", fontsize=9)
    ax.set_ylabel("Frequency (Hz)", fontsize=9)
    ax.tick_params(labelsize=8)
    fig.tight_layout(pad=0.4)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return buf.getvalue()


def extract_audio_window(audio_path, start_sec: float, end_sec: float):
    """Load a slice of audio and encode it as in-memory WAV bytes.

    Used by the Listen & Label workflow to play a single detection window.
    Returns (samples, sample_rate, wav_bytes).
    """
    duration = max(0.1, end_sec - start_sec)
    y, sr = librosa.load(audio_path, sr=None, offset=start_sec, duration=duration, mono=True)

    buf = io.BytesIO()
    sf.write(buf, y, sr, format="WAV", subtype="PCM_16")
    buf.seek(0)
    return y, sr, buf.read()
