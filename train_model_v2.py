"""
Avian Observatory — CNN Model Training v2
PRT840 IT Thesis | Charles Darwin University
Custom CNN designed for mel spectrogram classification.
No transfer learning — trained from scratch on bird audio data.
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
EPOCHS = 100
LEARNING_RATE = 0.001
EARLY_STOP_PATIENCE = 12
REDUCE_LR_PATIENCE = 5
INPUT_SHAPE = (128, 130, 1)  # Single channel mel spectrogram


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
    Build a custom CNN for mel spectrogram classification.
    Architecture inspired by bioacoustics literature:
    - Conv blocks with increasing filters (32 -> 64 -> 128 -> 256)
    - Batch normalisation after each conv layer
    - Max pooling to reduce spatial dimensions
    - Dropout for regularisation
    - Global average pooling instead of flatten (fewer parameters)
    """
    print("\nBuilding custom CNN for spectrograms...")

    inputs = keras.Input(shape=INPUT_SHAPE)

    # --- Data Augmentation ---
    x = layers.GaussianNoise(0.02)(inputs)

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
    """Training callbacks."""
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
            os.path.join(MODEL_DIR, "nt_bird_cnn_best.keras"),
            monitor="val_accuracy",
            save_best_only=True,
            verbose=1
        ),
        callbacks.CSVLogger(
            os.path.join(MODEL_DIR, "training_log_v2.csv"),
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
    np.save(os.path.join(MODEL_DIR, "y_test_true.npy"), y_test)
    np.save(os.path.join(MODEL_DIR, "y_test_pred.npy"), y_pred_classes)
    np.save(os.path.join(MODEL_DIR, "y_test_probs.npy"), y_pred)

    results = {
        "test_loss": float(loss),
        "test_accuracy": float(accuracy),
        "per_species": species_results
    }
    with open(os.path.join(MODEL_DIR, "evaluation_results.json"), "w") as f:
        json.dump(results, f, indent=2)

    return accuracy


def main():
    print("=" * 60)
    print("  Avian Observatory — Model Training v2")
    print("  Custom CNN for Mel Spectrograms")
    print("  PRT840 IT Thesis | Charles Darwin University")
    print("=" * 60)

    start_time = time.time()

    # Step 1: Load data
    X_train, X_val, X_test, y_train, y_val, y_test, label_map, num_classes = load_data()

    # Step 2: Compute class weights
    class_weights = compute_weights(y_train)

    # Step 3: Build model
    model = build_model(num_classes)

    # Step 4: Train
    print("\n" + "=" * 60)
    print("  TRAINING")
    print("=" * 60)

    history = model.fit(
        X_train, y_train,
        validation_data=(X_val, y_val),
        epochs=EPOCHS,
        batch_size=BATCH_SIZE,
        class_weight=class_weights,
        callbacks=get_callbacks(),
        verbose=1
    )

    best_val_acc = max(history.history["val_accuracy"])
    print(f"\n  Best validation accuracy: {best_val_acc*100:.1f}%")

    # Step 5: Load best model and evaluate
    best_path = os.path.join(MODEL_DIR, "nt_bird_cnn_best.keras")
    if os.path.exists(best_path):
        model = keras.models.load_model(best_path)
        print(f"  Loaded best model from {best_path}")

    test_accuracy = evaluate_model(model, X_test, y_test, label_map)

    # Step 6: Save final model
    final_path = os.path.join(MODEL_DIR, "nt_bird_cnn_final.keras")
    model.save(final_path)

    elapsed = time.time() - start_time

    print("\n" + "=" * 60)
    print("  TRAINING COMPLETE")
    print("=" * 60)
    print(f"\n  Best validation accuracy: {best_val_acc*100:.1f}%")
    print(f"  Test accuracy: {test_accuracy*100:.1f}%")
    print(f"  Total training time: {elapsed/60:.1f} minutes")
    print(f"\n  Files saved to: {MODEL_DIR}")
    print(f"    nt_bird_cnn_final.keras     — Final model")
    print(f"    nt_bird_cnn_best.keras      — Best checkpoint")
    print(f"    training_log_v2.csv         — Epoch-by-epoch log")
    print(f"    evaluation_results.json     — Per-species results")
    print(f"    y_test_true/pred/probs.npy  — For confusion matrix")


if __name__ == "__main__":
    main()
