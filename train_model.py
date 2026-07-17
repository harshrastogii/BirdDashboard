"""
Avian Observatory — CNN Model Training
PRT840 IT Thesis | Charles Darwin University
Trains an EfficientNetB0-based classifier on mel spectrogram segments.
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
BATCH_SIZE = 32
EPOCHS = 50
LEARNING_RATE = 0.001
EARLY_STOP_PATIENCE = 8
REDUCE_LR_PATIENCE = 4
INPUT_SHAPE = (128, 130, 3)  # EfficientNet expects 3 channels


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
    
    print(f"  X_train: {X_train.shape}, y_train: {y_train.shape}")
    print(f"  X_val:   {X_val.shape}, y_val:   {y_val.shape}")
    print(f"  X_test:  {X_test.shape}, y_test:  {y_test.shape}")
    
    # Get actual number of unique classes in training data
    num_classes = len(np.unique(y_train))
    print(f"  Classes: {num_classes}")
    
    return X_train, X_val, X_test, y_train, y_val, y_test, label_map, num_classes


def convert_to_3channel(X):
    """Convert single-channel spectrograms to 3-channel for EfficientNet."""
    if X.shape[-1] == 1:
        X = np.repeat(X, 3, axis=-1)
    return X


def build_model(num_classes):
    """Build EfficientNetB0-based transfer learning model."""
    print("\nBuilding model...")
    
    # Base model: EfficientNetB0 pretrained on ImageNet
    base_model = keras.applications.EfficientNetB0(
        weights="imagenet",
        include_top=False,
        input_shape=INPUT_SHAPE
    )
    
    # Freeze base model initially
    base_model.trainable = False
    
    # Build classification head
    inputs = keras.Input(shape=INPUT_SHAPE)
    
    # Data augmentation layers
    x = layers.RandomFlip("horizontal")(inputs)
    x = layers.GaussianNoise(0.01)(x)
    
    # Base model
    x = base_model(x, training=False)
    
    # Classification head
    x = layers.GlobalAveragePooling2D()(x)
    x = layers.BatchNormalization()(x)
    x = layers.Dropout(0.4)(x)
    x = layers.Dense(256, activation="relu")(x)
    x = layers.BatchNormalization()(x)
    x = layers.Dropout(0.3)(x)
    outputs = layers.Dense(num_classes, activation="softmax")(x)
    
    model = keras.Model(inputs, outputs)
    
    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=LEARNING_RATE),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"]
    )
    
    total_params = model.count_params()
    trainable_params = sum([tf.size(w).numpy() for w in model.trainable_weights])
    print(f"  Total parameters: {total_params:,}")
    print(f"  Trainable parameters: {trainable_params:,}")
    
    return model, base_model


def compute_weights(y_train):
    """Compute class weights to handle imbalanced species counts."""
    classes = np.unique(y_train)
    weights = compute_class_weight("balanced", classes=classes, y=y_train)
    class_weights = dict(zip(classes, weights))
    
    # Print top 5 most weighted (rarest) species
    sorted_weights = sorted(class_weights.items(), key=lambda x: -x[1])
    print("\nClass weights (top 5 rarest):")
    for cls, w in sorted_weights[:5]:
        print(f"  Class {cls}: weight {w:.2f}")
    
    return class_weights


def get_callbacks():
    """Set up training callbacks."""
    return [
        # Early stopping
        callbacks.EarlyStopping(
            monitor="val_accuracy",
            patience=EARLY_STOP_PATIENCE,
            restore_best_weights=True,
            verbose=1
        ),
        # Reduce learning rate on plateau
        callbacks.ReduceLROnPlateau(
            monitor="val_loss",
            factor=0.5,
            patience=REDUCE_LR_PATIENCE,
            min_lr=1e-6,
            verbose=1
        ),
        # Save best model
        callbacks.ModelCheckpoint(
            os.path.join(MODEL_DIR, "nt_bird_best.keras"),
            monitor="val_accuracy",
            save_best_only=True,
            verbose=1
        ),
        # CSV logger
        callbacks.CSVLogger(
            os.path.join(MODEL_DIR, "training_log.csv"),
            append=False
        )
    ]


def fine_tune(model, base_model, X_train, y_train, X_val, y_val, class_weights):
    """Fine-tune the last layers of the base model."""
    print("\n" + "=" * 60)
    print("  PHASE 2: Fine-tuning last 30 layers of EfficientNetB0")
    print("=" * 60)
    
    # Unfreeze last 30 layers
    base_model.trainable = True
    for layer in base_model.layers[:-30]:
        layer.trainable = False
    
    # Recompile with lower learning rate
    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=LEARNING_RATE * 0.1),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"]
    )
    
    trainable_params = sum([tf.size(w).numpy() for w in model.trainable_weights])
    print(f"  Trainable parameters after unfreeze: {trainable_params:,}")
    
    ft_callbacks = [
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
            min_lr=1e-7,
            verbose=1
        ),
        callbacks.ModelCheckpoint(
            os.path.join(MODEL_DIR, "nt_bird_finetuned.keras"),
            monitor="val_accuracy",
            save_best_only=True,
            verbose=1
        ),
        callbacks.CSVLogger(
            os.path.join(MODEL_DIR, "finetuning_log.csv"),
            append=False
        )
    ]
    
    history_ft = model.fit(
        X_train, y_train,
        validation_data=(X_val, y_val),
        epochs=30,
        batch_size=BATCH_SIZE,
        class_weight=class_weights,
        callbacks=ft_callbacks,
        verbose=1
    )
    
    return history_ft


def evaluate_model(model, X_test, y_test, label_map):
    """Evaluate model and print per-species results."""
    print("\n" + "=" * 60)
    print("  EVALUATION ON TEST SET")
    print("=" * 60)
    
    # Overall accuracy
    loss, accuracy = model.evaluate(X_test, y_test, verbose=0)
    print(f"\n  Test Loss: {loss:.4f}")
    print(f"  Test Accuracy: {accuracy:.4f} ({accuracy*100:.1f}%)")
    
    # Per-species predictions
    y_pred = model.predict(X_test, verbose=0)
    y_pred_classes = np.argmax(y_pred, axis=1)
    
    # Per-species accuracy
    print(f"\n  Per-species accuracy:")
    species_results = {}
    for label_idx in np.unique(y_test):
        mask = y_test == label_idx
        species_name = label_map.get(str(label_idx), f"Class {label_idx}")
        species_acc = np.mean(y_pred_classes[mask] == y_test[mask])
        species_count = np.sum(mask)
        species_results[species_name] = {"accuracy": species_acc, "count": int(species_count)}
        print(f"    {species_name:.<45} {species_acc*100:5.1f}% ({species_count} samples)")
    
    # Save predictions for confusion matrix later
    np.save(os.path.join(MODEL_DIR, "y_test_true.npy"), y_test)
    np.save(os.path.join(MODEL_DIR, "y_test_pred.npy"), y_pred_classes)
    np.save(os.path.join(MODEL_DIR, "y_test_probs.npy"), y_pred)
    
    # Save results summary
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
    print("  Avian Observatory — Model Training")
    print("  PRT840 IT Thesis | Charles Darwin University")
    print("=" * 60)
    
    start_time = time.time()
    
    # Step 1: Load data
    X_train, X_val, X_test, y_train, y_val, y_test, label_map, num_classes = load_data()
    
    # Step 2: Convert to 3-channel
    print("\nConverting to 3-channel for EfficientNet...")
    X_train = convert_to_3channel(X_train)
    X_val = convert_to_3channel(X_val)
    X_test = convert_to_3channel(X_test)
    print(f"  New shape: {X_train.shape}")
    
    # Step 3: Compute class weights
    class_weights = compute_weights(y_train)
    
    # Step 4: Build model
    model, base_model = build_model(num_classes)
    model.summary(print_fn=lambda x: None)  # suppress verbose summary
    
    # Step 5: Phase 1 — Train classification head
    print("\n" + "=" * 60)
    print("  PHASE 1: Training classification head (base frozen)")
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
    
    phase1_acc = max(history.history["val_accuracy"])
    print(f"\n  Phase 1 best val accuracy: {phase1_acc*100:.1f}%")
    
    # Step 6: Phase 2 — Fine-tune
    history_ft = fine_tune(model, base_model, X_train, y_train, X_val, y_val, class_weights)
    
    phase2_acc = max(history_ft.history["val_accuracy"])
    print(f"\n  Phase 2 best val accuracy: {phase2_acc*100:.1f}%")
    
    # Step 7: Evaluate
    # Load best model
    best_model_path = os.path.join(MODEL_DIR, "nt_bird_finetuned.keras")
    if os.path.exists(best_model_path):
        model = keras.models.load_model(best_model_path)
        print(f"\n  Loaded best fine-tuned model from {best_model_path}")
    
    test_accuracy = evaluate_model(model, X_test, y_test, label_map)
    
    # Step 8: Save final model
    final_path = os.path.join(MODEL_DIR, "nt_bird_final.keras")
    model.save(final_path)
    print(f"\n  Final model saved to: {final_path}")
    
    elapsed = time.time() - start_time
    print(f"\n  Total training time: {elapsed/60:.1f} minutes")
    
    print("\n" + "=" * 60)
    print("  TRAINING COMPLETE")
    print("=" * 60)
    print(f"\n  Best validation accuracy: {max(phase1_acc, phase2_acc)*100:.1f}%")
    print(f"  Test accuracy: {test_accuracy*100:.1f}%")
    print(f"  Model saved to: {MODEL_DIR}")
    print(f"\n  Files created:")
    print(f"    nt_bird_final.keras    — Final trained model")
    print(f"    nt_bird_best.keras     — Best Phase 1 model")
    print(f"    nt_bird_finetuned.keras — Best fine-tuned model")
    print(f"    training_log.csv       — Phase 1 epoch-by-epoch log")
    print(f"    finetuning_log.csv     — Phase 2 epoch-by-epoch log")
    print(f"    evaluation_results.json — Per-species test results")
    print(f"    y_test_true/pred.npy   — For confusion matrix")


if __name__ == "__main__":
    main()
