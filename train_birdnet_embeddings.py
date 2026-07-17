"""
Avian Observatory — v5: BirdNET Embeddings + Custom Classifier
PRT840 IT Thesis | Charles Darwin University

APPROACH: Instead of training a CNN from scratch on raw spectrograms,
we use BirdNET v2.4 as a feature extractor. BirdNET has learned rich
acoustic features from 6,000+ bird species worldwide. We extract its
1024-dimensional embeddings and train a lightweight classifier on top
specifically for our 23 NT species.

WHY THIS WORKS BETTER:
- BirdNET already knows what bird calls generally sound like
- It just maps them to wrong species names for Australian birds
- By replacing its classification head with our NT-specific one,
  we get BirdNET's acoustic understanding + our local species labels
- Research shows this works even with as few as 4 training samples
  (Ghani et al., 2023, Scientific Reports)

USAGE:
  python3 train_birdnet_embeddings.py

REQUIREMENTS:
  pip install birdnet-analyzer
  (already installed if you ran BirdNET analysis)

The script uses BirdNET-Analyzer's built-in training feature which:
1. Extracts 1024-dim embeddings from all training audio
2. Trains a shallow classifier (dense layers) on those embeddings
3. Outputs a .tflite custom classifier file
4. Can be used directly with birdnet_analyzer.analyze()
"""

import os
import subprocess
import sys
import json
import time
import shutil

# === Configuration ===
BASE_DIR = os.path.expanduser("~/BirdDashboard")
TRAINING_DATA = os.path.join(BASE_DIR, "training_data")
MODEL_DIR = os.path.join(BASE_DIR, "models")
OUTPUT_CLASSIFIER = os.path.join(MODEL_DIR, "NT_Bird_BirdNET_Classifier.tflite")

# Training hyperparameters
EPOCHS = 100
BATCH_SIZE = 32
LEARNING_RATE = 0.001
HIDDEN_UNITS = 128       # Hidden layer size (0 = linear probe, >0 = MLP)
DROPOUT = 0.25
VAL_SPLIT = 0.2
CROP_MODE = "segments"   # Process full recordings in 3-sec segments
CROP_OVERLAP = 0.5       # 50% overlap between segments for more training data
UPSAMPLING_RATIO = 0.5   # Upsample minority classes to 50% of majority class

# Cache file for faster re-training
CACHE_FILE = os.path.join(MODEL_DIR, "birdnet_embeddings_cache.pkl")


def check_training_data():
    """Verify training data structure and print summary."""
    print("Checking training data...")
    
    if not os.path.exists(TRAINING_DATA):
        print(f"  ERROR: Training data directory not found: {TRAINING_DATA}")
        return False
    
    species_folders = []
    for folder in sorted(os.listdir(TRAINING_DATA)):
        folder_path = os.path.join(TRAINING_DATA, folder)
        if os.path.isdir(folder_path):
            mp3_files = [f for f in os.listdir(folder_path) if f.endswith((".mp3", ".wav", ".flac", ".ogg"))]
            if mp3_files:
                species_folders.append((folder, len(mp3_files)))
    
    print(f"  Found {len(species_folders)} species folders:")
    total_files = 0
    for folder, count in species_folders:
        total_files += count
        marker = "⚠️" if count < 10 else "✅"
        print(f"    {marker} {folder}: {count} recordings")
    
    print(f"  Total recordings: {total_files}")
    return len(species_folders) > 0


def train_with_birdnet():
    """Train custom classifier using BirdNET-Analyzer's training feature."""
    
    print("\n" + "=" * 60)
    print("  Training BirdNET Custom Classifier")
    print("=" * 60)
    print(f"  Epochs: {EPOCHS}")
    print(f"  Batch size: {BATCH_SIZE}")
    print(f"  Learning rate: {LEARNING_RATE}")
    print(f"  Hidden units: {HIDDEN_UNITS}")
    print(f"  Dropout: {DROPOUT}")
    print(f"  Crop mode: {CROP_MODE}")
    print(f"  Crop overlap: {CROP_OVERLAP}")
    print(f"  Upsampling ratio: {UPSAMPLING_RATIO}")
    print(f"  Output: {OUTPUT_CLASSIFIER}")
    
    # Build the command
    cmd = [
        sys.executable, "-m", "birdnet_analyzer.train",
        TRAINING_DATA,
        "-o", OUTPUT_CLASSIFIER,
        "--epochs", str(EPOCHS),
        "--batch_size", str(BATCH_SIZE),
        "--learning_rate", str(LEARNING_RATE),
        "--hidden_units", str(HIDDEN_UNITS),
        "--dropout", str(DROPOUT),
        "--val_split", str(VAL_SPLIT),
        "--crop_mode", CROP_MODE,
        "--overlap", str(CROP_OVERLAP),
        "--upsampling_ratio", str(UPSAMPLING_RATIO),
        "--mixup",
    ]
    
    print(f"\n  Running: {' '.join(cmd)}")
    print("=" * 60)
    print()
    
    # Run the training
    start_time = time.time()
    
    result = subprocess.run(
        cmd,
        cwd=BASE_DIR,
        text=True
    )
    
    elapsed = time.time() - start_time
    
    if result.returncode != 0:
        print(f"\n  ERROR: Training failed with return code {result.returncode}")
        return False
    
    print(f"\n  Training completed in {elapsed/60:.1f} minutes")
    return True


def verify_classifier():
    """Verify the trained classifier exists and print info."""
    
    # Check for the .tflite file
    if os.path.exists(OUTPUT_CLASSIFIER):
        size = os.path.getsize(OUTPUT_CLASSIFIER) / 1024
        print(f"\n  ✅ Classifier saved: {OUTPUT_CLASSIFIER} ({size:.0f} KB)")
        
        # Check for labels file (should be alongside the classifier)
        labels_file = OUTPUT_CLASSIFIER.replace(".tflite", "_Labels.txt")
        if os.path.exists(labels_file):
            with open(labels_file, "r") as f:
                labels = [l.strip() for l in f.readlines() if l.strip()]
            print(f"  ✅ Labels file: {len(labels)} classes")
            for i, label in enumerate(labels):
                print(f"      {i}: {label}")
        
        return True
    else:
        print(f"\n  ❌ Classifier not found at: {OUTPUT_CLASSIFIER}")
        return False


def test_classifier():
    """Quick test of the trained classifier on sample audio."""
    
    sample_dir = os.path.join(BASE_DIR, "sample_audio")
    if not os.path.exists(sample_dir):
        print("\n  No sample_audio directory found for testing.")
        return
    
    audio_files = [f for f in os.listdir(sample_dir) if f.endswith((".mp3", ".wav", ".flac"))]
    if not audio_files:
        print("\n  No audio files found in sample_audio for testing.")
        return
    
    print(f"\n" + "=" * 60)
    print("  Testing classifier on sample recordings")
    print("=" * 60)
    
    # Run BirdNET analysis with custom classifier
    test_output = os.path.join(BASE_DIR, "birdnet_custom_results")
    os.makedirs(test_output, exist_ok=True)
    
    cmd = [
        sys.executable, "-m", "birdnet_analyzer.analyze",
        sample_dir,
        "-o", test_output,
        "--classifier", OUTPUT_CLASSIFIER,
        "--min_conf", "0.1",
        "--rtype", "csv",
    ]
    
    print(f"  Running analysis on {len(audio_files)} files...")
    result = subprocess.run(cmd, cwd=BASE_DIR, text=True, capture_output=True)
    
    if result.returncode == 0:
        print("  ✅ Analysis complete!")
        
        # Parse results
        import csv
        for f in sorted(os.listdir(test_output)):
            if f.endswith(".csv") and "params" not in f:
                filepath = os.path.join(test_output, f)
                try:
                    with open(filepath, "r") as csvfile:
                        reader = csv.DictReader(csvfile)
                        rows = list(reader)
                        if rows:
                            # Get top prediction
                            best = max(rows, key=lambda r: float(r.get("Confidence", 0)))
                            species = best.get("Common name", "Unknown")
                            conf = float(best.get("Confidence", 0))
                            recording = f.replace(".BirdNET.results.csv", "")
                            print(f"    {recording}: {species} ({conf:.1%})")
                except Exception as e:
                    pass
    else:
        print(f"  ❌ Analysis failed: {result.stderr[:500]}")


def main():
    print("=" * 60)
    print("  Avian Observatory — v5")
    print("  BirdNET Embeddings + Custom Classifier")
    print("  PRT840 IT Thesis | Charles Darwin University")
    print("=" * 60)
    print()
    print("  This approach uses BirdNET v2.4 as a feature extractor.")
    print("  BirdNET's 1024-dim embeddings capture rich acoustic features")
    print("  learned from 6,000+ bird species worldwide.")
    print("  We train a lightweight classifier on these embeddings")
    print("  specifically for our 23 NT species.")
    
    # Step 1: Check training data
    print("\n" + "=" * 60)
    print("  STEP 1: Verifying training data")
    print("=" * 60)
    if not check_training_data():
        return
    
    # Step 2: Train classifier
    print("\n" + "=" * 60)
    print("  STEP 2: Training BirdNET custom classifier")
    print("=" * 60)
    if not train_with_birdnet():
        print("\n  Training failed. Please check the error messages above.")
        return
    
    # Step 3: Verify output
    print("\n" + "=" * 60)
    print("  STEP 3: Verifying trained classifier")
    print("=" * 60)
    if not verify_classifier():
        return
    
    # Step 4: Quick test
    test_classifier()
    
    # Summary
    print("\n" + "=" * 60)
    print("  TRAINING COMPLETE — v5 (BirdNET Embeddings)")
    print("=" * 60)
    print(f"\n  Custom classifier: {OUTPUT_CLASSIFIER}")
    print(f"\n  To use this classifier for analysis:")
    print(f"    python3 -m birdnet_analyzer.analyze sample_audio/")
    print(f"      --classifier {OUTPUT_CLASSIFIER}")
    print(f"      --min_conf 0.25 --rtype csv")
    print(f"\n  To integrate into the dashboard, the app.py needs to be")
    print(f"  updated to use this classifier alongside the existing models.")
    print(f"\n  This classifier leverages BirdNET's understanding of bird")
    print(f"  acoustics (trained on millions of recordings) combined with")
    print(f"  your NT-specific species labels — best of both worlds.")


if __name__ == "__main__":
    main()
