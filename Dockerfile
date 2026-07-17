# syntax=docker/dockerfile:1
#
# Production image for the Avian Observatory FastAPI backend.
# Target: Heroku Container Stack (the classic buildpack cannot hold the ~2.3 GB
# TensorFlow stack under its 500 MB slug limit; a Docker image can).
#
# Full TensorFlow + BirdNET-Analyzer inference is retained — no features reduced.
# NOTE: a sane build context depends on .dockerignore (added as the next change);
# do not build until the full production config is in place.

# Python 3.12 (not 3.13): it is the most broadly-supported CPython for this ML
# stack on Linux — TensorFlow 2.21, scikit-learn, librosa, numpy and
# birdnet-analyzer all ship mature manylinux cp312 wheels. The code is 3.10–3.13
# compatible (verified on 3.13 locally); 3.12 reduces wheel-availability risk in
# production without any code change.
FROM python:3.12-slim

# System libraries:
#   ffmpeg + libsndfile1  -> audio decoding for librosa / soundfile
#   libgomp1              -> OpenMP runtime used by TensorFlow / scikit-learn
# Kept minimal; apt lists removed to keep the image small.
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        libsndfile1 \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install Python dependencies first so this layer is cached across code changes.
# requirements-api.txt pulls in requirements.txt (TensorFlow, birdnet-analyzer,
# librosa, soundfile, scikit-learn, ...) plus FastAPI/uvicorn/SQLAlchemy/psycopg.
COPY requirements.txt requirements-api.txt ./
RUN pip install --upgrade pip && pip install -r requirements-api.txt

# Copy the application, scientific core, migrations, and the model + seed
# artefacts. What actually enters the build context is controlled by
# .dockerignore (next change): models/, sample_audio/, birdnet_results2/ and
# detections/ are gitignored but ARE included in the local Docker build context,
# so a `heroku container:push` from a local checkout bakes them into the image.
COPY . .

# Heroku injects $PORT at runtime; bind to it. A SINGLE uvicorn process is
# intentional — TensorFlow's memory footprint makes multiple workers risk OOM
# even on a 1 GB dyno. Shell form so ${PORT} expands.
CMD uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000}
