"""
NT Bird Acoustic Monitor — Audio Preprocessing Pipeline
PRT840 IT Thesis | Charles Darwin University
Converts raw MP3 recordings into mel spectrogram segments for CNN training.
"""

import os
import numpy as np
import librosa
import warnings
import csv
from pathlib import Path
from sklearn.model_selection import train_test_split

warnings.filterwarnings("ignore")

# === Configuration ===
BASE_DIR = os.path.expanduser("~/BirdDashboard/training_data")
OUTPUT_DIR = os.path.expanduser("~/BirdDashboard/spectrograms")
METADATA_FILE = os.path.join(BASE_DIR, "dataset_metadata.csv")

# Audio settings
SAMPLE_RATE = 22050       # Standard for bird audio (matches librosa default)
SEGMENT_DURATION = 3.0    # 3-second segments (matches BirdNET)
N_MELS = 128             # Mel frequency bins
N_FFT = 2048             # FFT window size
HOP_LENGTH = 512         # Hop between FFT windows
FMIN = 150               # Min frequency (Hz) - filters out low rumble
FMAX = 15000             # Max frequency (Hz) - covers bird vocalisations

# Train/val/test split
TRAIN_RATIO = 0.70
VAL_RATIO = 0.15
TEST_RATIO = 0.15
RANDOM_SEED = 42


def audio_to_mel_segments(filepath, sr=SAMPLE_RATE, segment_dur=SEGMENT_DURATION):
    """Load audio file and split into fixed-length mel spectrogram segments."""
    try:
        # Load audio, resample to target rate
        y, _ = librosa.load(filepath, sr=sr, mono=True)
        
        # Skip if too short (less than 1 second)
        if len(y) < sr:
            return []
        
        # Calculate segment length in samples
        segment_samples = int(segment_dur * sr)
        segments = []
        
        # Split into non-overlapping segments
        for start in range(0, len(y) - segment_samples + 1, segment_samples):
            segment = y[start:start + segment_samples]
            
            # Skip silent segments (RMS below threshold)
            rms = np.sqrt(np.mean(segment ** 2))
            if rms < 0.001:
                continue
            
            # Generate mel spectrogram
            mel_spec = librosa.feature.melspectrogram(
                y=segment,
                sr=sr,
                n_mels=N_MELS,
                n_fft=N_FFT,
                hop_length=HOP_LENGTH,
                fmin=FMIN,
                fmax=FMAX
            )
            
            # Convert to log scale (dB)
            mel_spec_db = librosa.power_to_db(mel_spec, ref=np.max)
            
            # Normalise to 0-1 range
            mel_spec_norm = (mel_spec_db - mel_spec_db.min())
            if mel_spec_norm.max() > 0:
                mel_spec_norm = mel_spec_norm / mel_spec_norm.max()
            
            segments.append(mel_spec_norm)
        
        return segments
    
    except Exception as e:
        print(f"    Error processing {filepath}: {e}")
        return []


def get_species_folders(base_dir):
    """Get list of species folders and their labels."""
    species = []
    for folder in sorted(os.listdir(base_dir)):
        folder_path = os.path.join(base_dir, folder)
        if os.path.isdir(folder_path):
            mp3_files = [f for f in os.listdir(folder_path) if f.endswith(".mp3")]
            if mp3_files:
                species.append((folder, folder_path, len(mp3_files)))
    return species


def process_all_species(base_dir):
    """Process all species folders and return spectrograms with labels."""
    species_list = get_species_folders(base_dir)
    
    print(f"\nFound {len(species_list)} species folders")
    print("=" * 60)
    
    all_spectrograms = []
    all_labels = []
    all_label_names = []
    label_map = {}
    species_counts = {}
    
    for idx, (folder_name, folder_path, file_count) in enumerate(species_list):
        species_name = folder_name.replace("_", " ")
        label_map[idx] = species_name
        
        print(f"\n[{idx+1}/{len(species_list)}] {species_name} ({file_count} recordings)")
        
        species_segments = 0
        mp3_files = sorted([f for f in os.listdir(folder_path) if f.endswith(".mp3")])
        
        for fi, fname in enumerate(mp3_files):
            fpath = os.path.join(folder_path, fname)
            segments = audio_to_mel_segments(fpath)
            
            for seg in segments:
                all_spectrograms.append(seg)
                all_labels.append(idx)
                all_label_names.append(species_name)
                species_segments += 1
            
            if (fi + 1) % 20 == 0:
                print(f"    Processed {fi+1}/{len(mp3_files)} files...")
        
        species_counts[species_name] = species_segments
        print(f"    Generated {species_segments} spectrogram segments")
    
    return all_spectrograms, all_labels, label_map, species_counts


def split_dataset(spectrograms, labels, label_map):
    """Split into train/validation/test sets with stratification."""
    X = np.array(spectrograms)
    y = np.array(labels)
    
    print(f"\nTotal spectrograms: {len(X)}")
    print(f"Shape of each: {X[0].shape}")
    print(f"Number of classes: {len(label_map)}")
    
    # First split: train+val vs test
    X_trainval, X_test, y_trainval, y_test = train_test_split(
        X, y, test_size=TEST_RATIO, random_state=RANDOM_SEED, stratify=y
    )
    
    # Second split: train vs val
    val_ratio_adjusted = VAL_RATIO / (TRAIN_RATIO + VAL_RATIO)
    X_train, X_val, y_train, y_val = train_test_split(
        X_trainval, y_trainval, test_size=val_ratio_adjusted, 
        random_state=RANDOM_SEED, stratify=y_trainval
    )
    
    return X_train, X_val, X_test, y_train, y_val, y_test


def save_dataset(X_train, X_val, X_test, y_train, y_val, y_test, label_map, species_counts):
    """Save processed data as numpy arrays."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Add channel dimension for CNN (height, width, channels)
    X_train = X_train[..., np.newaxis]
    X_val = X_val[..., np.newaxis]
    X_test = X_test[..., np.newaxis]
    
    # Save arrays
    np.save(os.path.join(OUTPUT_DIR, "X_train.npy"), X_train)
    np.save(os.path.join(OUTPUT_DIR, "X_val.npy"), X_val)
    np.save(os.path.join(OUTPUT_DIR, "X_test.npy"), X_test)
    np.save(os.path.join(OUTPUT_DIR, "y_train.npy"), y_train)
    np.save(os.path.join(OUTPUT_DIR, "y_val.npy"), y_val)
    np.save(os.path.join(OUTPUT_DIR, "y_test.npy"), y_test)
    
    # Save label map
    import json
    with open(os.path.join(OUTPUT_DIR, "label_map.json"), "w") as f:
        json.dump({str(k): v for k, v in label_map.items()}, f, indent=2)
    
    # Save species counts
    with open(os.path.join(OUTPUT_DIR, "species_counts.json"), "w") as f:
        json.dump(species_counts, f, indent=2)
    
    print(f"\nSaved to: {OUTPUT_DIR}")
    print(f"  X_train: {X_train.shape}")
    print(f"  X_val:   {X_val.shape}")
    print(f"  X_test:  {X_test.shape}")
    
    # Calculate sizes
    total_size = 0
    for f in os.listdir(OUTPUT_DIR):
        total_size += os.path.getsize(os.path.join(OUTPUT_DIR, f))
    print(f"  Total size: {total_size / (1024*1024):.1f} MB")


def main():
    print("=" * 60)
    print("  NT Bird Acoustic Monitor — Preprocessing Pipeline")
    print("  PRT840 IT Thesis | Charles Darwin University")
    print("=" * 60)
    print(f"\nSource: {BASE_DIR}")
    print(f"Output: {OUTPUT_DIR}")
    print(f"Settings: {SAMPLE_RATE}Hz, {SEGMENT_DURATION}s segments, {N_MELS} mel bins")
    print(f"Split: {int(TRAIN_RATIO*100)}% train / {int(VAL_RATIO*100)}% val / {int(TEST_RATIO*100)}% test")
    
    # Step 1: Process all audio files
    print("\n" + "=" * 60)
    print("  STEP 1: Converting audio to mel spectrograms")
    print("=" * 60)
    spectrograms, labels, label_map, species_counts = process_all_species(BASE_DIR)
    
    if len(spectrograms) == 0:
        print("ERROR: No spectrograms generated! Check your audio files.")
        return
    
    # Check for species with too few samples for stratified split
    from collections import Counter
    label_counts = Counter(labels)
    min_samples_needed = 4  # Need at least 4 for stratified 70/15/15
    
    valid_indices = []
    removed_species = []
    for label_idx, count in label_counts.items():
        if count >= min_samples_needed:
            valid_indices.extend([i for i, l in enumerate(labels) if l == label_idx])
        else:
            species_name = label_map[label_idx]
            removed_species.append(f"{species_name} ({count} segments)")
    
    if removed_species:
        print(f"\nWARNING: Removing species with too few segments for splitting:")
        for s in removed_species:
            print(f"  - {s}")
        spectrograms = [spectrograms[i] for i in valid_indices]
        labels = [labels[i] for i in valid_indices]
    
    # Step 2: Split dataset
    print("\n" + "=" * 60)
    print("  STEP 2: Splitting into train/val/test sets")
    print("=" * 60)
    X_train, X_val, X_test, y_train, y_val, y_test = split_dataset(
        spectrograms, labels, label_map
    )
    
    # Step 3: Save
    print("\n" + "=" * 60)
    print("  STEP 3: Saving processed data")
    print("=" * 60)
    save_dataset(X_train, X_val, X_test, y_train, y_val, y_test, label_map, species_counts)
    
    # Summary
    print("\n" + "=" * 60)
    print("  PREPROCESSING COMPLETE")
    print("=" * 60)
    print(f"\n  Species processed: {len(label_map)}")
    print(f"  Total segments: {len(X_train) + len(X_val) + len(X_test)}")
    print(f"  Train: {len(X_train)} | Val: {len(X_val)} | Test: {len(X_test)}")
    
    print(f"\n  Per-species segment counts:")
    for species, count in sorted(species_counts.items(), key=lambda x: -x[1]):
        print(f"    {species:.<45} {count:>5} segments")
    
    print(f"\n  Next step: Run train_model.py to train the CNN classifier")


if __name__ == "__main__":
    main()
