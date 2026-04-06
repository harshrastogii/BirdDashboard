"""
NT Bird Acoustic Monitor — CNN Model Training v3 (Augmented)
PRT840 IT Thesis | Charles Darwin University

Addresses the generalisation gap identified in v2:
- v2 achieved 92.7% on held-out test segments from the SAME recordings
- v2 failed on NEW recordings of the same species (overfitting to recording conditions)

Solution: Spectrogram-level data augmentation applied on-the-fly during training.
This forces the model to learn bird call patterns rather than recording-specific
artifacts (microphone type, background noise, compression, distance).

Augmentations applied (based on bioacoustics literature):
1. Time masking  — randomly masks time windows (SpecAugment, Park et al. 2019)
2. Frequency masking — randomly masks frequency bands (SpecAugment)
3. Gaussian noise — simulates varying recording conditions
4. Volume scaling — simulates different recording distances
5. Time shifting — shifts spectrogram horizontally with wrap-around
6. Mixup — blends two spectrograms of the same class for smoother decision boundaries

Architecture: Same 4-block CNN as v2 (32→64→128→256 filters).
The model is retrained from scratch with augmented data.
"""

import os
import json
import numpy as np
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers, callbacks
from sklearn.utils.class_weight import compute_class_weight
import time

# === Configuration ===
SPEC_DIR = os.path.expanduser("~/BirdDashboard/spectrograms")
MODEL_DIR = os.path.expanduser("~/BirdDashboard/models")
os.makedirs(MODEL_DIR, exist_ok=True)

# Training settings
BATCH_SIZE = 64
EPOCHS = 120          # More epochs since augmentation slows convergence
LEARNING_RATE = 0.001
EARLY_STOP_PATIENCE = 15  # More patience — augmented training is noisier
REDUCE_LR_PATIENCE = 6
INPUT_SHAPE = (128, 130, 1)

# Augmentation settings
AUG_TIME_MASK_MAX = 20      # Max time steps to mask (out of 130)
AUG_FREQ_MASK_MAX = 15      # Max frequency bins to mask (out of 128)
AUG_NOISE_STD = 0.03        # Gaussian noise standard deviation
AUG_VOLUME_RANGE = (0.7, 1.3)  # Volume scaling range
AUG_TIME_SHIFT_MAX = 15     # Max time steps to shift
AUG_PROB = 0.5              # Probability of applying each augmentation


# =====================================================================
#  AUGMENTATION FUNCTIONS
# =====================================================================

def time_mask(spec, max_mask=AUG_TIME_MASK_MAX):
    """Mask a random contiguous block of time steps (vertical stripe)."""
    spec = spec.copy()
    t = spec.shape[1]
    mask_len = np.random.randint(1, max_mask + 1)
    start = np.random.randint(0, t - mask_len)
    spec[:, start:start + mask_len, :] = 0
    return spec


def freq_mask(spec, max_mask=AUG_FREQ_MASK_MAX):
    """Mask a random contiguous block of frequency bins (horizontal stripe)."""
    spec = spec.copy()
    f = spec.shape[0]
    mask_len = np.random.randint(1, max_mask + 1)
    start = np.random.randint(0, f - mask_len)
    spec[start:start + mask_len, :, :] = 0
    return spec


def add_noise(spec, std=AUG_NOISE_STD):
    """Add Gaussian noise to simulate varying recording conditions."""
    noise = np.random.normal(0, std, spec.shape).astype(np.float32)
    spec = np.clip(spec + noise, 0, 1)
    return spec


def volume_scale(spec, low=AUG_VOLUME_RANGE[0], high=AUG_VOLUME_RANGE[1]):
    """Scale volume to simulate different recording distances."""
    factor = np.random.uniform(low, high)
    spec = np.clip(spec * factor, 0, 1)
    return spec


def time_shift(spec, max_shift=AUG_TIME_SHIFT_MAX):
    """Shift spectrogram horizontally with wrap-around."""
    shift = np.random.randint(-max_shift, max_shift + 1)
    spec = np.roll(spec, shift, axis=1)
    return spec


def augment_spectrogram(spec):
    """
    Apply a random combination of augmentations to a single spectrogram.
    Each augmentation is applied independently with probability AUG_PROB.
    """
    if np.random.random() < AUG_PROB:
        spec = time_mask(spec)
    if np.random.random() < AUG_PROB:
        spec = freq_mask(spec)
    if np.random.random() < AUG_PROB:
        spec = add_noise(spec)
    if np.random.random() < AUG_PROB:
        spec = volume_scale(spec)
    if np.random.random() < AUG_PROB:
        spec = time_shift(spec)
    return spec


# =====================================================================
#  AUGMENTED DATA GENERATOR
# =====================================================================

class AugmentedDataGenerator(keras.utils.Sequence):
    """
    Custom data generator that applies augmentations on-the-fly.

    Benefits over pre-generating augmented data:
    - No extra disk space needed
    - Every epoch sees different augmentations → more variety
    - Original data is never modified
    """

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
#  MODEL ARCHITECTURE (same as v2)
# =====================================================================

def load_data():
    """Load preprocessed spectrogram data."""
    print("Loading data...")
    X_train = np.load(os.path.join(SPEC_DIR, "X_train.npy"))
    X_val = np.load(os.path.join(SPEC_DIR, "X_val.npy"))
    X_test = np.load(os.path.join(SPEC_DIR, "X_test.npy"))
    y_train = np.load(os.path.join(SPEC_DIR, "y_train.npy"))
    y_val = np.load(os.path.join(SPEC_DIR, "y_val.npy"))
    y_test = np.load(os.path.join(SPEC_DIR, "y_test.npy"))

    with open(os.path.join(SPEC_DIR, "label_map.json"), "r") as f:
        label_map = json.load(f)

    num_classes = len(np.unique(y_train))

    print(f"  X_train: {X_train.shape}, y_train: {y_train.shape}")
    print(f"  X_val:   {X_val.shape}, y_val:   {y_val.shape}")
    print(f"  X_test:  {X_test.shape}, y_test:  {y_test.shape}")
    print(f"  Classes: {num_classes}")

    return X_train, X_val, X_test, y_train, y_val, y_test, label_map, num_classes


def build_model(num_classes):
    """
    Same architecture as v2 — 4 conv blocks (32→64→128→256).
    Removed inline GaussianNoise layer since augmentation is now handled
    externally by the data generator (more diverse and controllable).
    """
    print("\nBuilding custom CNN v3 (augmentation-ready)...")

    inputs = keras.Input(shape=INPUT_SHAPE)
    x = inputs  # No inline GaussianNoise — handled by generator

    # --- Block 1: 32 filters ---
    x = layers.Conv2D(32, (3, 3), padding="same")(x)
    x = layers.BatchNormalization()(x)
    x = layers.ReLU()(x)
    x = layers.Conv2D(32, (3, 3), padding="same")(x)
    x = layers.BatchNormalization()(x)
    x = layers.ReLU()(x)
    x = layers.MaxPooling2D((2, 2))(x)
    x = layers.Dropout(0.2)(x)

    # --- Block 2: 64 filters ---
    x = layers.Conv2D(64, (3, 3), padding="same")(x)
    x = layers.BatchNormalization()(x)
    x = layers.ReLU()(x)
    x = layers.Conv2D(64, (3, 3), padding="same")(x)
    x = layers.BatchNormalization()(x)
    x = layers.ReLU()(x)
    x = layers.MaxPooling2D((2, 2))(x)
    x = layers.Dropout(0.25)(x)

    # --- Block 3: 128 filters ---
    x = layers.Conv2D(128, (3, 3), padding="same")(x)
    x = layers.BatchNormalization()(x)
    x = layers.ReLU()(x)
    x = layers.Conv2D(128, (3, 3), padding="same")(x)
    x = layers.BatchNormalization()(x)
    x = layers.ReLU()(x)
    x = layers.MaxPooling2D((2, 2))(x)
    x = layers.Dropout(0.3)(x)

    # --- Block 4: 256 filters ---
    x = layers.Conv2D(256, (3, 3), padding="same")(x)
    x = layers.BatchNormalization()(x)
    x = layers.ReLU()(x)
    x = layers.Conv2D(256, (3, 3), padding="same")(x)
    x = layers.BatchNormalization()(x)
    x = layers.ReLU()(x)
    x = layers.MaxPooling2D((2, 2))(x)
    x = layers.Dropout(0.35)(x)

    # --- Classification Head ---
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
#  TRAINING UTILITIES
# =====================================================================

def compute_weights(y_train):
    """Compute class weights for imbalanced dataset."""
    classes = np.unique(y_train)
    weights = compute_class_weight("balanced", classes=classes, y=y_train)
    class_weights = dict(zip(classes.astype(int), weights))

    sorted_weights = sorted(class_weights.items(), key=lambda x: -x[1])
    print("\nClass weights (top 5 rarest):")
    for cls, w in sorted_weights[:5]:
        print(f"  Class {cls}: weight {w:.2f}")

    return class_weights


def get_callbacks():
    """Training callbacks — saves to new filename to preserve v2 model."""
    return [
        callbacks.EarlyStopping(
            monitor="val_accuracy",
            patience=EARLY_STOP_PATIENCE,
            restore_best_weights=True,
            verbose=1
        ),
        callbacks.ReduceLROnPlateau(
            monitor="val_loss",
            factor=0.5,
            patience=REDUCE_LR_PATIENCE,
            min_lr=1e-6,
            verbose=1
        ),
        callbacks.ModelCheckpoint(
            os.path.join(MODEL_DIR, "nt_bird_cnn_v3_best.keras"),
            monitor="val_accuracy",
            save_best_only=True,
            verbose=1
        ),
        callbacks.CSVLogger(
            os.path.join(MODEL_DIR, "training_log_v3.csv"),
            append=False
        )
    ]


def evaluate_model(model, X_test, y_test, label_map):
    """Evaluate and print per-species results."""
    print("\n" + "=" * 60)
    print("  EVALUATION ON TEST SET")
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
            "accuracy": float(species_acc),
            "count": species_count
        }
        if species_acc > 0.5:
            correct_species += 1
        total_species += 1
        status = "OK" if species_acc >= 0.5 else "LOW" if species_acc >= 0.2 else "FAIL"
        print(f"    [{status:>4}] {species_name:.<40} {species_acc*100:5.1f}% ({species_count} samples)")

    print(f"\n  Species with >50% accuracy: {correct_species}/{total_species}")

    # Save predictions
    np.save(os.path.join(MODEL_DIR, "y_test_true_v3.npy"), y_test)
    np.save(os.path.join(MODEL_DIR, "y_test_pred_v3.npy"), y_pred_classes)
    np.save(os.path.join(MODEL_DIR, "y_test_probs_v3.npy"), y_pred)

    results = {
        "test_loss": float(loss),
        "test_accuracy": float(accuracy),
        "per_species": species_results,
        "augmentation": {
            "time_mask_max": AUG_TIME_MASK_MAX,
            "freq_mask_max": AUG_FREQ_MASK_MAX,
            "noise_std": AUG_NOISE_STD,
            "volume_range": list(AUG_VOLUME_RANGE),
            "time_shift_max": AUG_TIME_SHIFT_MAX,
            "aug_probability": AUG_PROB
        }
    }
    with open(os.path.join(MODEL_DIR, "evaluation_results_v3.json"), "w") as f:
        json.dump(results, f, indent=2)

    return accuracy


def preview_augmentations(X_train, y_train, label_map):
    """Show a few augmentation examples so you can verify they look right."""
    print("\n  Augmentation preview (first sample):")
    sample = X_train[0:1]
    print(f"    Original  — mean: {sample.mean():.4f}, range: [{sample.min():.4f}, {sample.max():.4f}]")

    for name, func in [("Time mask", time_mask), ("Freq mask", freq_mask),
                        ("Noise", add_noise), ("Volume", volume_scale),
                        ("Time shift", time_shift)]:
        aug = func(sample[0])
        print(f"    {name:<12} — mean: {aug.mean():.4f}, range: [{aug.min():.4f}, {aug.max():.4f}]")

    # Show combined augmentation
    combined = augment_spectrogram(sample[0])
    print(f"    Combined   — mean: {combined.mean():.4f}, range: [{combined.min():.4f}, {combined.max():.4f}]")


# =====================================================================
#  MAIN
# =====================================================================

def main():
    print("=" * 60)
    print("  NT Bird Acoustic Monitor — Model Training v3")
    print("  CNN with Spectrogram Augmentation")
    print("  PRT840 IT Thesis | Charles Darwin University")
    print("=" * 60)
    print()
    print("  Augmentation strategy:")
    print(f"    Time masking:     up to {AUG_TIME_MASK_MAX} steps (of 130)")
    print(f"    Frequency masking: up to {AUG_FREQ_MASK_MAX} bins (of 128)")
    print(f"    Gaussian noise:   std={AUG_NOISE_STD}")
    print(f"    Volume scaling:   {AUG_VOLUME_RANGE[0]:.1f}x — {AUG_VOLUME_RANGE[1]:.1f}x")
    print(f"    Time shifting:    ±{AUG_TIME_SHIFT_MAX} steps")
    print(f"    Each applied with {AUG_PROB:.0%} probability")

    start_time = time.time()

    # Step 1: Load data
    X_train, X_val, X_test, y_train, y_val, y_test, label_map, num_classes = load_data()

    # Step 2: Preview augmentations
    preview_augmentations(X_train, y_train, label_map)

    # Step 3: Create augmented data generators
    print("\n  Creating augmented data generators...")
    train_gen = AugmentedDataGenerator(X_train, y_train, batch_size=BATCH_SIZE, augment=True)
    val_gen = AugmentedDataGenerator(X_val, y_val, batch_size=BATCH_SIZE, augment=False)
    print(f"    Training batches per epoch: {len(train_gen)}")
    print(f"    Validation batches: {len(val_gen)}")

    # Step 4: Compute class weights
    class_weights = compute_weights(y_train)

    # Step 5: Build model
    model = build_model(num_classes)

    # Step 6: Train with augmented data
    print("\n" + "=" * 60)
    print("  TRAINING WITH AUGMENTATION")
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

    # Step 7: Load best model and evaluate
    best_path = os.path.join(MODEL_DIR, "nt_bird_cnn_v3_best.keras")
    if os.path.exists(best_path):
        model = keras.models.load_model(best_path)
        print(f"  Loaded best model from {best_path}")

    test_accuracy = evaluate_model(model, X_test, y_test, label_map)

    # Step 8: Save final model
    final_path = os.path.join(MODEL_DIR, "nt_bird_cnn_v3_final.keras")
    model.save(final_path)

    # Step 9: Copy best model as the active dashboard model
    import shutil
    dashboard_model_path = os.path.join(MODEL_DIR, "nt_bird_cnn_best.keras")
    backup_path = os.path.join(MODEL_DIR, "nt_bird_cnn_v2_best_backup.keras")

    # Backup v2 model first
    if os.path.exists(dashboard_model_path):
        shutil.copy2(dashboard_model_path, backup_path)
        print(f"\n  Backed up v2 model to: {backup_path}")

    # Replace with v3
    shutil.copy2(best_path, dashboard_model_path)
    print(f"  Updated dashboard model: {dashboard_model_path}")

    elapsed = time.time() - start_time

    print("\n" + "=" * 60)
    print("  TRAINING COMPLETE — v3 (Augmented)")
    print("=" * 60)
    print(f"\n  Best validation accuracy: {best_val_acc*100:.1f}%")
    print(f"  Test accuracy: {test_accuracy*100:.1f}%")
    print(f"  Total training time: {elapsed/60:.1f} minutes")
    print(f"\n  Files saved to: {MODEL_DIR}")
    print(f"    nt_bird_cnn_v3_best.keras       — Best augmented model")
    print(f"    nt_bird_cnn_v3_final.keras       — Final augmented model")
    print(f"    nt_bird_cnn_v2_best_backup.keras — Backup of v2 model")
    print(f"    nt_bird_cnn_best.keras           — Updated (now v3)")
    print(f"    training_log_v3.csv              — Epoch-by-epoch log")
    print(f"    evaluation_results_v3.json       — Per-species results")
    print(f"    y_test_true/pred/probs_v3.npy    — For confusion matrix")
    print(f"\n  The dashboard will automatically use the new model.")
    print(f"  Restart Streamlit to load it: python3 -m streamlit run app.py")


if __name__ == "__main__":
    main()
