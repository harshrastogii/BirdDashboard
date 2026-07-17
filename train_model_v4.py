"""
Avian Observatory — Preprocessing & Training v4 (Recording-Level Split)
PRT840 IT Thesis | Charles Darwin University

KEY FIX: Splits train/val/test by RECORDING, not by segment.

Previous versions (v2, v3) split randomly by segment, meaning segments from
the same recording could appear in both train and test sets. This caused the
model to learn recording-specific artifacts (microphone, background noise,
compression) rather than actual bird call patterns.

This version ensures that ALL segments from a single recording stay together
in the same split. The model never sees any segment from a test recording
during training, which forces genuine generalisation.

Combined with v3's spectrogram augmentations for maximum robustness.
"""

import os
import json
import numpy as np
import librosa
import warnings
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers, callbacks
from sklearn.utils.class_weight import compute_class_weight
from collections import defaultdict
import time

warnings.filterwarnings("ignore")

# === Configuration ===
BASE_DIR = os.path.expanduser("~/BirdDashboard/training_data")
SPEC_DIR = os.path.expanduser("~/BirdDashboard/spectrograms")
MODEL_DIR = os.path.expanduser("~/BirdDashboard/models")
os.makedirs(SPEC_DIR, exist_ok=True)
os.makedirs(MODEL_DIR, exist_ok=True)

# Audio settings (same as original preprocess.py)
SAMPLE_RATE = 22050
SEGMENT_DURATION = 3.0
N_MELS = 128
N_FFT = 2048
HOP_LENGTH = 512
FMIN = 150
FMAX = 15000

# Split ratios
TRAIN_RATIO = 0.70
VAL_RATIO = 0.15
TEST_RATIO = 0.15
RANDOM_SEED = 42

# Training settings
BATCH_SIZE = 64
EPOCHS = 120
LEARNING_RATE = 0.001
EARLY_STOP_PATIENCE = 15
REDUCE_LR_PATIENCE = 6
INPUT_SHAPE = (128, 130, 1)

# Augmentation settings (same as v3)
AUG_TIME_MASK_MAX = 20
AUG_FREQ_MASK_MAX = 15
AUG_NOISE_STD = 0.03
AUG_VOLUME_RANGE = (0.7, 1.3)
AUG_TIME_SHIFT_MAX = 15
AUG_PROB = 0.5


# =====================================================================
#  STEP 1: PREPROCESSING WITH RECORDING TRACKING
# =====================================================================

def audio_to_mel_segments(filepath, sr=SAMPLE_RATE, segment_dur=SEGMENT_DURATION):
    """Load audio file and split into fixed-length mel spectrogram segments."""
    try:
        y, _ = librosa.load(filepath, sr=sr, mono=True)
        if len(y) < sr:
            return []

        segment_samples = int(segment_dur * sr)
        segments = []

        for start in range(0, len(y) - segment_samples + 1, segment_samples):
            segment = y[start:start + segment_samples]

            rms = np.sqrt(np.mean(segment ** 2))
            if rms < 0.001:
                continue

            mel_spec = librosa.feature.melspectrogram(
                y=segment, sr=sr, n_mels=N_MELS, n_fft=N_FFT,
                hop_length=HOP_LENGTH, fmin=FMIN, fmax=FMAX
            )
            mel_spec_db = librosa.power_to_db(mel_spec, ref=np.max)

            mel_spec_norm = (mel_spec_db - mel_spec_db.min())
            if mel_spec_norm.max() > 0:
                mel_spec_norm = mel_spec_norm / mel_spec_norm.max()

            segments.append(mel_spec_norm)

        return segments
    except Exception as e:
        print(f"    Error processing {filepath}: {e}")
        return []


def process_all_species_with_recording_ids(base_dir):
    """
    Process all species folders.
    Returns spectrograms, labels, AND recording IDs for each segment.
    This is the key difference from the original preprocessing.
    """
    species_list = []
    for folder in sorted(os.listdir(base_dir)):
        folder_path = os.path.join(base_dir, folder)
        if os.path.isdir(folder_path):
            mp3_files = [f for f in os.listdir(folder_path) if f.endswith(".mp3")]
            if mp3_files:
                species_list.append((folder, folder_path, len(mp3_files)))

    print(f"\nFound {len(species_list)} species folders")
    print("=" * 60)

    all_spectrograms = []
    all_labels = []
    all_recording_ids = []  # NEW: track which recording each segment came from
    label_map = {}
    species_counts = {}
    recording_counter = 0

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
                all_recording_ids.append(recording_counter)
                species_segments += 1

            recording_counter += 1

            if (fi + 1) % 20 == 0:
                print(f"    Processed {fi+1}/{len(mp3_files)} files...")

        species_counts[species_name] = species_segments
        print(f"    Generated {species_segments} segments from {file_count} recordings")

    print(f"\n  Total recordings: {recording_counter}")
    print(f"  Total segments: {len(all_spectrograms)}")

    return all_spectrograms, all_labels, all_recording_ids, label_map, species_counts


def split_by_recording(spectrograms, labels, recording_ids, label_map):
    """
    Split into train/val/test by RECORDING, not by segment.

    All segments from a single recording go into the same split.
    This prevents data leakage and forces the model to generalise
    to completely unseen recordings.
    """
    np.random.seed(RANDOM_SEED)

    X = np.array(spectrograms)
    y = np.array(labels)
    rec_ids = np.array(recording_ids)

    print(f"\nSplitting by recording (not by segment)...")
    print(f"  Total segments: {len(X)}")
    print(f"  Total unique recordings: {len(np.unique(rec_ids))}")

    # Group recordings by species
    species_recordings = defaultdict(list)
    for rec_id in np.unique(rec_ids):
        mask = rec_ids == rec_id
        species_label = y[mask][0]  # All segments from same recording have same label
        num_segments = mask.sum()
        species_recordings[species_label].append((rec_id, num_segments))

    train_indices = []
    val_indices = []
    test_indices = []

    print(f"\n  Per-species recording split:")
    for species_label in sorted(species_recordings.keys()):
        recordings = species_recordings[species_label]
        species_name = label_map.get(str(species_label), f"Class {species_label}")
        n_recs = len(recordings)

        # Shuffle recordings for this species
        np.random.shuffle(recordings)

        # Calculate split points
        n_test = max(1, int(n_recs * TEST_RATIO))
        n_val = max(1, int(n_recs * VAL_RATIO))
        n_train = n_recs - n_test - n_val

        # Ensure at least 1 recording in train
        if n_train < 1:
            n_train = 1
            n_val = max(1, (n_recs - 1) // 2)
            n_test = n_recs - n_train - n_val

        test_recs = recordings[:n_test]
        val_recs = recordings[n_test:n_test + n_val]
        train_recs = recordings[n_test + n_val:]

        # Collect segment indices for each split
        train_segs = 0
        for rec_id, _ in train_recs:
            indices = np.where(rec_ids == rec_id)[0]
            train_indices.extend(indices)
            train_segs += len(indices)

        val_segs = 0
        for rec_id, _ in val_recs:
            indices = np.where(rec_ids == rec_id)[0]
            val_indices.extend(indices)
            val_segs += len(indices)

        test_segs = 0
        for rec_id, _ in test_recs:
            indices = np.where(rec_ids == rec_id)[0]
            test_indices.extend(indices)
            test_segs += len(indices)

        print(f"    {species_name:.<40} {n_recs:>3} recs -> "
              f"train: {len(train_recs)} ({train_segs} segs) | "
              f"val: {len(val_recs)} ({val_segs} segs) | "
              f"test: {len(test_recs)} ({test_segs} segs)")

    # Build final arrays
    train_indices = np.array(train_indices)
    val_indices = np.array(val_indices)
    test_indices = np.array(test_indices)

    # Shuffle within each split
    np.random.shuffle(train_indices)
    np.random.shuffle(val_indices)
    np.random.shuffle(test_indices)

    X_train = X[train_indices][..., np.newaxis]
    X_val = X[val_indices][..., np.newaxis]
    X_test = X[test_indices][..., np.newaxis]
    y_train = y[train_indices]
    y_val = y[val_indices]
    y_test = y[test_indices]

    # Verify no recording leakage
    train_rec_ids = set(rec_ids[train_indices])
    val_rec_ids = set(rec_ids[val_indices])
    test_rec_ids = set(rec_ids[test_indices])

    train_val_overlap = train_rec_ids & val_rec_ids
    train_test_overlap = train_rec_ids & test_rec_ids
    val_test_overlap = val_rec_ids & test_rec_ids

    print(f"\n  Recording leakage check:")
    print(f"    Train-Val overlap:  {len(train_val_overlap)} recordings (should be 0)")
    print(f"    Train-Test overlap: {len(train_test_overlap)} recordings (should be 0)")
    print(f"    Val-Test overlap:   {len(val_test_overlap)} recordings (should be 0)")

    if train_val_overlap or train_test_overlap or val_test_overlap:
        print("    WARNING: Recording leakage detected!")
    else:
        print("    ✅ No leakage — splits are clean!")

    return X_train, X_val, X_test, y_train, y_val, y_test


# =====================================================================
#  STEP 2: AUGMENTATION (same as v3)
# =====================================================================

def time_mask(spec, max_mask=AUG_TIME_MASK_MAX):
    spec = spec.copy()
    mask_len = np.random.randint(1, max_mask + 1)
    start = np.random.randint(0, spec.shape[1] - mask_len)
    spec[:, start:start + mask_len, :] = 0
    return spec

def freq_mask(spec, max_mask=AUG_FREQ_MASK_MAX):
    spec = spec.copy()
    mask_len = np.random.randint(1, max_mask + 1)
    start = np.random.randint(0, spec.shape[0] - mask_len)
    spec[start:start + mask_len, :, :] = 0
    return spec

def add_noise(spec, std=AUG_NOISE_STD):
    return np.clip(spec + np.random.normal(0, std, spec.shape).astype(np.float32), 0, 1)

def volume_scale(spec):
    return np.clip(spec * np.random.uniform(AUG_VOLUME_RANGE[0], AUG_VOLUME_RANGE[1]), 0, 1)

def time_shift(spec, max_shift=AUG_TIME_SHIFT_MAX):
    return np.roll(spec, np.random.randint(-max_shift, max_shift + 1), axis=1)

def augment_spectrogram(spec):
    if np.random.random() < AUG_PROB: spec = time_mask(spec)
    if np.random.random() < AUG_PROB: spec = freq_mask(spec)
    if np.random.random() < AUG_PROB: spec = add_noise(spec)
    if np.random.random() < AUG_PROB: spec = volume_scale(spec)
    if np.random.random() < AUG_PROB: spec = time_shift(spec)
    return spec


class AugmentedDataGenerator(keras.utils.Sequence):
    def __init__(self, X, y, batch_size=BATCH_SIZE, augment=True, shuffle=True):
        self.X = X
        self.y = y
        self.batch_size = batch_size
        self.augment = augment
        self.shuffle = shuffle
        self.indices = np.arange(len(X))
        if shuffle:
            np.random.shuffle(self.indices)

    def __len__(self):
        return int(np.ceil(len(self.X) / self.batch_size))

    def __getitem__(self, idx):
        batch_indices = self.indices[idx * self.batch_size:(idx + 1) * self.batch_size]
        batch_X = self.X[batch_indices].copy()
        batch_y = self.y[batch_indices]
        if self.augment:
            for i in range(len(batch_X)):
                batch_X[i] = augment_spectrogram(batch_X[i])
        return batch_X, batch_y

    def on_epoch_end(self):
        if self.shuffle:
            np.random.shuffle(self.indices)


# =====================================================================
#  STEP 3: MODEL (same architecture as v2/v3)
# =====================================================================

def build_model(num_classes):
    print("\nBuilding custom CNN v4 (recording-split + augmentation)...")
    inputs = keras.Input(shape=INPUT_SHAPE)
    x = inputs

    # Block 1: 32 filters
    x = layers.Conv2D(32, (3, 3), padding="same")(x)
    x = layers.BatchNormalization()(x)
    x = layers.ReLU()(x)
    x = layers.Conv2D(32, (3, 3), padding="same")(x)
    x = layers.BatchNormalization()(x)
    x = layers.ReLU()(x)
    x = layers.MaxPooling2D((2, 2))(x)
    x = layers.Dropout(0.2)(x)

    # Block 2: 64 filters
    x = layers.Conv2D(64, (3, 3), padding="same")(x)
    x = layers.BatchNormalization()(x)
    x = layers.ReLU()(x)
    x = layers.Conv2D(64, (3, 3), padding="same")(x)
    x = layers.BatchNormalization()(x)
    x = layers.ReLU()(x)
    x = layers.MaxPooling2D((2, 2))(x)
    x = layers.Dropout(0.25)(x)

    # Block 3: 128 filters
    x = layers.Conv2D(128, (3, 3), padding="same")(x)
    x = layers.BatchNormalization()(x)
    x = layers.ReLU()(x)
    x = layers.Conv2D(128, (3, 3), padding="same")(x)
    x = layers.BatchNormalization()(x)
    x = layers.ReLU()(x)
    x = layers.MaxPooling2D((2, 2))(x)
    x = layers.Dropout(0.3)(x)

    # Block 4: 256 filters
    x = layers.Conv2D(256, (3, 3), padding="same")(x)
    x = layers.BatchNormalization()(x)
    x = layers.ReLU()(x)
    x = layers.Conv2D(256, (3, 3), padding="same")(x)
    x = layers.BatchNormalization()(x)
    x = layers.ReLU()(x)
    x = layers.MaxPooling2D((2, 2))(x)
    x = layers.Dropout(0.35)(x)

    # Classification head
    x = layers.GlobalAveragePooling2D()(x)
    x = layers.Dense(256, activation="relu")(x)
    x = layers.BatchNormalization()(x)
    x = layers.Dropout(0.5)(x)
    x = layers.Dense(128, activation="relu")(x)
    x = layers.Dropout(0.4)(x)
    outputs = layers.Dense(num_classes, activation="softmax")(x)

    model = keras.Model(inputs, outputs)
    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=LEARNING_RATE),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"]
    )
    model.summary()
    return model


# =====================================================================
#  STEP 4: TRAINING & EVALUATION
# =====================================================================

def compute_weights(y_train):
    classes = np.unique(y_train)
    weights = compute_class_weight("balanced", classes=classes, y=y_train)
    class_weights = dict(zip(classes.astype(int), weights))
    sorted_weights = sorted(class_weights.items(), key=lambda x: -x[1])
    print("\nClass weights (top 5 rarest):")
    for cls, w in sorted_weights[:5]:
        print(f"  Class {cls}: weight {w:.2f}")
    return class_weights


def get_callbacks():
    return [
        callbacks.EarlyStopping(
            monitor="val_accuracy", patience=EARLY_STOP_PATIENCE,
            restore_best_weights=True, verbose=1
        ),
        callbacks.ReduceLROnPlateau(
            monitor="val_loss", factor=0.5, patience=REDUCE_LR_PATIENCE,
            min_lr=1e-6, verbose=1
        ),
        callbacks.ModelCheckpoint(
            os.path.join(MODEL_DIR, "nt_bird_cnn_v4_best.keras"),
            monitor="val_accuracy", save_best_only=True, verbose=1
        ),
        callbacks.CSVLogger(
            os.path.join(MODEL_DIR, "training_log_v4.csv"), append=False
        )
    ]


def evaluate_model(model, X_test, y_test, label_map):
    print("\n" + "=" * 60)
    print("  EVALUATION ON TEST SET (unseen recordings)")
    print("=" * 60)

    loss, accuracy = model.evaluate(X_test, y_test, verbose=0)
    print(f"\n  Test Loss: {loss:.4f}")
    print(f"  Test Accuracy: {accuracy:.4f} ({accuracy*100:.1f}%)")

    y_pred = model.predict(X_test, verbose=0)
    y_pred_classes = np.argmax(y_pred, axis=1)

    print(f"\n  Per-species accuracy:")
    species_results = {}
    correct_species = 0
    total_species = 0
    for label_idx in sorted(np.unique(y_test)):
        mask = y_test == label_idx
        species_name = label_map.get(str(label_idx), f"Class {label_idx}")
        species_acc = np.mean(y_pred_classes[mask] == y_test[mask])
        species_count = int(np.sum(mask))
        species_results[species_name] = {
            "accuracy": float(species_acc), "count": species_count
        }
        if species_acc > 0.5:
            correct_species += 1
        total_species += 1
        status = "OK" if species_acc >= 0.5 else "LOW" if species_acc >= 0.2 else "FAIL"
        print(f"    [{status:>4}] {species_name:.<40} {species_acc*100:5.1f}% ({species_count} samples)")

    print(f"\n  Species with >50% accuracy: {correct_species}/{total_species}")

    # Save predictions
    np.save(os.path.join(MODEL_DIR, "y_test_true_v4.npy"), y_test)
    np.save(os.path.join(MODEL_DIR, "y_test_pred_v4.npy"), y_pred_classes)
    np.save(os.path.join(MODEL_DIR, "y_test_probs_v4.npy"), y_pred)

    results = {
        "test_loss": float(loss),
        "test_accuracy": float(accuracy),
        "split_method": "recording-level (no segment leakage)",
        "augmentation": True,
        "per_species": species_results
    }
    with open(os.path.join(MODEL_DIR, "evaluation_results_v4.json"), "w") as f:
        json.dump(results, f, indent=2)

    return accuracy


# =====================================================================
#  MAIN
# =====================================================================

def main():
    print("=" * 60)
    print("  Avian Observatory — v4")
    print("  Recording-Level Split + Augmentation")
    print("  PRT840 IT Thesis | Charles Darwin University")
    print("=" * 60)
    print()
    print("  KEY CHANGE: Train/val/test split by RECORDING, not segment.")
    print("  No recording appears in more than one split.")
    print("  This forces the model to generalise to unseen recordings.")

    start_time = time.time()

    # Step 1: Preprocess with recording tracking
    print("\n" + "=" * 60)
    print("  STEP 1: Converting audio to mel spectrograms")
    print("=" * 60)
    spectrograms, labels, recording_ids, label_map, species_counts = \
        process_all_species_with_recording_ids(BASE_DIR)

    if len(spectrograms) == 0:
        print("ERROR: No spectrograms generated!")
        return

    # Remove species with too few recordings for splitting
    from collections import Counter
    rec_per_species = defaultdict(set)
    for i, label in enumerate(labels):
        rec_per_species[label].add(recording_ids[i])

    min_recordings_needed = 3  # Need at least 3 recordings (1 train, 1 val, 1 test)
    valid_indices = []
    removed_species = []
    for label, recs in rec_per_species.items():
        species_name = label_map.get(label, f"Class {label}")
        if len(recs) >= min_recordings_needed:
            valid_indices.extend([i for i, l in enumerate(labels) if l == label])
        else:
            removed_species.append(f"{species_name} ({len(recs)} recordings)")

    if removed_species:
        print(f"\nWARNING: Removing species with too few recordings for split:")
        for s in removed_species:
            print(f"  - {s}")
        spectrograms = [spectrograms[i] for i in valid_indices]
        labels = [labels[i] for i in valid_indices]
        recording_ids = [recording_ids[i] for i in valid_indices]

    # Remap labels to be contiguous (0, 1, 2, ...) after removing species
    unique_labels = sorted(set(labels))
    old_to_new = {old: new for new, old in enumerate(unique_labels)}
    labels = [old_to_new[l] for l in labels]

    # Rebuild label_map with new contiguous indices
    new_label_map = {}
    for old_idx, new_idx in old_to_new.items():
        new_label_map[new_idx] = label_map[old_idx]
    label_map = new_label_map

    print(f"\n  Remapped {len(unique_labels)} classes to contiguous indices 0-{len(unique_labels)-1}")
    for idx in sorted(label_map.keys()):
        print(f"    {idx}: {label_map[idx]}")

    # Step 2: Split by recording
    print("\n" + "=" * 60)
    print("  STEP 2: Splitting by recording (no leakage)")
    print("=" * 60)
    X_train, X_val, X_test, y_train, y_val, y_test = \
        split_by_recording(spectrograms, labels, recording_ids, label_map)

    print(f"\n  Final split sizes:")
    print(f"    X_train: {X_train.shape}")
    print(f"    X_val:   {X_val.shape}")
    print(f"    X_test:  {X_test.shape}")

    # Save the new splits (overwrite old ones)
    np.save(os.path.join(SPEC_DIR, "X_train.npy"), X_train)
    np.save(os.path.join(SPEC_DIR, "X_val.npy"), X_val)
    np.save(os.path.join(SPEC_DIR, "X_test.npy"), X_test)
    np.save(os.path.join(SPEC_DIR, "y_train.npy"), y_train)
    np.save(os.path.join(SPEC_DIR, "y_val.npy"), y_val)
    np.save(os.path.join(SPEC_DIR, "y_test.npy"), y_test)

    with open(os.path.join(SPEC_DIR, "label_map.json"), "w") as f:
        json.dump({str(k): v for k, v in label_map.items()}, f, indent=2)

    with open(os.path.join(SPEC_DIR, "species_counts.json"), "w") as f:
        json.dump(species_counts, f, indent=2)

    print(f"  Saved new recording-level splits to: {SPEC_DIR}")

    # Step 3: Get number of classes
    num_classes = len(np.unique(y_train))

    # Step 4: Create augmented data generators
    print("\n  Creating augmented data generators...")
    train_gen = AugmentedDataGenerator(X_train, y_train, batch_size=BATCH_SIZE, augment=True)
    val_gen = AugmentedDataGenerator(X_val, y_val, batch_size=BATCH_SIZE, augment=False)
    print(f"    Training batches per epoch: {len(train_gen)}")
    print(f"    Validation batches: {len(val_gen)}")

    # Step 5: Compute class weights
    class_weights = compute_weights(y_train)

    # Step 6: Build model
    model = build_model(num_classes)

    # Step 7: Train
    print("\n" + "=" * 60)
    print("  STEP 3: TRAINING (recording-split + augmentation)")
    print("=" * 60)

    history = model.fit(
        train_gen,
        validation_data=val_gen,
        epochs=EPOCHS,
        class_weight=class_weights,
        callbacks=get_callbacks(),
        verbose=1
    )

    best_val_acc = max(history.history["val_accuracy"])
    print(f"\n  Best validation accuracy: {best_val_acc*100:.1f}%")

    # Step 8: Load best model and evaluate
    best_path = os.path.join(MODEL_DIR, "nt_bird_cnn_v4_best.keras")
    if os.path.exists(best_path):
        model = keras.models.load_model(best_path)
        print(f"  Loaded best model from {best_path}")

    test_accuracy = evaluate_model(model, X_test, y_test, label_map)

    # Step 9: Replace dashboard model
    import shutil
    dashboard_model_path = os.path.join(MODEL_DIR, "nt_bird_cnn_best.keras")
    backup_path = os.path.join(MODEL_DIR, "nt_bird_cnn_v3_best_backup.keras")

    if os.path.exists(dashboard_model_path):
        shutil.copy2(dashboard_model_path, backup_path)
        print(f"\n  Backed up v3 model to: {backup_path}")

    shutil.copy2(best_path, dashboard_model_path)
    print(f"  Updated dashboard model: {dashboard_model_path}")

    # Save final model
    final_path = os.path.join(MODEL_DIR, "nt_bird_cnn_v4_final.keras")
    model.save(final_path)

    elapsed = time.time() - start_time

    print("\n" + "=" * 60)
    print("  TRAINING COMPLETE — v4 (Recording-Level Split)")
    print("=" * 60)
    print(f"\n  Best validation accuracy: {best_val_acc*100:.1f}%")
    print(f"  Test accuracy: {test_accuracy*100:.1f}%")
    print(f"  Total time: {elapsed/60:.1f} minutes")
    print(f"\n  IMPORTANT: Test accuracy is now measured on recordings")
    print(f"  the model has NEVER seen — not even other segments from")
    print(f"  the same file. This is a true generalisation metric.")
    print(f"\n  Files saved to: {MODEL_DIR}")
    print(f"    nt_bird_cnn_v4_best.keras       — Best model")
    print(f"    nt_bird_cnn_best.keras           — Updated dashboard model")
    print(f"    training_log_v4.csv              — Epoch log")
    print(f"    evaluation_results_v4.json       — Results")
    print(f"\n  Restart Streamlit to load: python3 -m streamlit run app.py")


if __name__ == "__main__":
    main()
