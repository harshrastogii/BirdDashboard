"""
Avian Observatory — Model Evaluation & Visualisation
PRT840 IT Thesis | Charles Darwin University
Generates confusion matrix, per-species comparison charts,
and NT model vs BirdNET comparison report.
"""

import os
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from sklearn.metrics import confusion_matrix, classification_report
import seaborn as sns

# === Configuration ===
MODEL_DIR = os.path.expanduser("~/BirdDashboard/models")
SPEC_DIR = os.path.expanduser("~/BirdDashboard/spectrograms")
OUTPUT_DIR = os.path.expanduser("~/BirdDashboard/evaluation")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def load_data():
    """Load predictions and label map."""
    y_true = np.load(os.path.join(MODEL_DIR, "y_test_true.npy"))
    y_pred = np.load(os.path.join(MODEL_DIR, "y_test_pred.npy"))
    y_probs = np.load(os.path.join(MODEL_DIR, "y_test_probs.npy"))

    with open(os.path.join(SPEC_DIR, "label_map.json"), "r") as f:
        label_map = json.load(f)

    # Sort by index
    species_names = [label_map[str(i)] for i in range(len(label_map))]

    print(f"Loaded {len(y_true)} test samples across {len(species_names)} species")
    return y_true, y_pred, y_probs, species_names


def plot_confusion_matrix(y_true, y_pred, species_names):
    """Generate and save confusion matrix heatmap."""
    print("\nGenerating confusion matrix...")

    cm = confusion_matrix(y_true, y_pred)

    # Normalise by row (true label) to show percentages
    cm_norm = cm.astype("float") / cm.sum(axis=1)[:, np.newaxis]
    cm_norm = np.nan_to_num(cm_norm)

    # Short names for readability
    short_names = []
    for name in species_names:
        parts = name.split()
        if len(parts) >= 2:
            short_names.append(parts[0][:3] + " " + parts[1][:3])
        else:
            short_names.append(name[:7])

    # Plot
    fig, ax = plt.subplots(figsize=(20, 16))
    sns.heatmap(
        cm_norm,
        annot=True,
        fmt=".1%",
        cmap="YlOrRd",
        xticklabels=short_names,
        yticklabels=species_names,
        ax=ax,
        vmin=0,
        vmax=1,
        linewidths=0.5,
        linecolor="white",
        cbar_kws={"label": "Classification Rate", "shrink": 0.8}
    )

    ax.set_xlabel("Predicted Species", fontsize=14, fontweight="bold")
    ax.set_ylabel("True Species", fontsize=14, fontweight="bold")
    ax.set_title(
        "NT Bird Classification Model — Confusion Matrix\n"
        "Test Set Accuracy: {:.1f}% | 24 Species | 2,770 Samples".format(
            np.mean(y_true == y_pred) * 100
        ),
        fontsize=16,
        fontweight="bold",
        pad=20
    )

    plt.xticks(rotation=45, ha="right", fontsize=9)
    plt.yticks(fontsize=10)
    plt.tight_layout()

    path = os.path.join(OUTPUT_DIR, "confusion_matrix.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {path}")

    # Also save raw confusion matrix
    path_raw = os.path.join(OUTPUT_DIR, "confusion_matrix_raw.png")
    fig2, ax2 = plt.subplots(figsize=(20, 16))
    sns.heatmap(
        cm,
        annot=True,
        fmt="d",
        cmap="Blues",
        xticklabels=short_names,
        yticklabels=species_names,
        ax=ax2,
        linewidths=0.5,
        linecolor="white",
        cbar_kws={"label": "Sample Count", "shrink": 0.8}
    )
    ax2.set_xlabel("Predicted Species", fontsize=14, fontweight="bold")
    ax2.set_ylabel("True Species", fontsize=14, fontweight="bold")
    ax2.set_title(
        "NT Bird Classification Model — Confusion Matrix (Raw Counts)\n"
        "2,770 Test Samples",
        fontsize=16,
        fontweight="bold",
        pad=20
    )
    plt.xticks(rotation=45, ha="right", fontsize=9)
    plt.yticks(fontsize=10)
    plt.tight_layout()
    fig2.savefig(path_raw, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {path_raw}")

    return cm, cm_norm


def plot_per_species_accuracy(y_true, y_pred, species_names):
    """Bar chart of per-species accuracy."""
    print("\nGenerating per-species accuracy chart...")

    accuracies = []
    counts = []
    for i, name in enumerate(species_names):
        mask = y_true == i
        if np.sum(mask) > 0:
            acc = np.mean(y_pred[mask] == y_true[mask])
            accuracies.append(acc * 100)
            counts.append(int(np.sum(mask)))
        else:
            accuracies.append(0)
            counts.append(0)

    # Sort by accuracy
    sorted_indices = np.argsort(accuracies)
    sorted_names = [species_names[i] for i in sorted_indices]
    sorted_accs = [accuracies[i] for i in sorted_indices]
    sorted_counts = [counts[i] for i in sorted_indices]

    # Colour by conservation status
    threatened = [
        "Gouldian Finch", "Hooded Parrot", "Partridge Pigeon",
        "Red Goshawk", "Masked Owl", "Bush Stone curlew"
    ]
    colors = []
    for name in sorted_names:
        if name in threatened:
            colors.append("#e74c3c")  # Red for threatened
        elif sorted_accs[sorted_names.index(name)] >= 90:
            colors.append("#27ae60")  # Green for >90%
        elif sorted_accs[sorted_names.index(name)] >= 80:
            colors.append("#f39c12")  # Orange for 80-90%
        else:
            colors.append("#e67e22")  # Dark orange for <80%

    fig, ax = plt.subplots(figsize=(14, 10))
    bars = ax.barh(range(len(sorted_names)), sorted_accs, color=colors, edgecolor="white", height=0.7)

    # Add accuracy labels
    for i, (acc, count) in enumerate(zip(sorted_accs, sorted_counts)):
        ax.text(acc + 0.5, i, f"{acc:.1f}% (n={count})", va="center", fontsize=9)

    ax.set_yticks(range(len(sorted_names)))
    ax.set_yticklabels(sorted_names, fontsize=10)
    ax.set_xlabel("Classification Accuracy (%)", fontsize=13, fontweight="bold")
    ax.set_title(
        "NT Bird Classification — Per-Species Test Accuracy\n"
        "Red = Threatened Species | Green = >90% | Orange = 80-90%",
        fontsize=14,
        fontweight="bold",
        pad=15
    )
    ax.set_xlim(0, 108)
    ax.axvline(x=90, color="gray", linestyle="--", alpha=0.5, label="90% threshold")
    ax.axvline(x=50, color="red", linestyle="--", alpha=0.3, label="50% threshold")
    ax.legend(loc="lower right")

    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, "per_species_accuracy.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {path}")


def plot_birdnet_comparison(y_true, y_pred, species_names):
    """
    Generate NT model vs BirdNET comparison chart.
    BirdNET results from our testing: 0% on all NT species.
    """
    print("\nGenerating NT Model vs BirdNET comparison...")

    # BirdNET test results (from our actual testing)
    birdnet_results = {
        "Laughing Kookaburra": {"predicted": "Eurasian Wren", "confidence": 80, "correct": False},
        "Rainbow Bee eater": {"predicted": "Pied Crow", "confidence": 99, "correct": False},
        "Sulphur crested Cockatoo": {"predicted": "Ortolan Bunting", "confidence": 95, "correct": False},
        "Willie Wagtail": {"predicted": "Northern Saw-whet Owl", "confidence": 99, "correct": False},
    }

    # NT model results for the same species
    nt_results = {}
    for i, name in enumerate(species_names):
        mask = y_true == i
        if np.sum(mask) > 0:
            nt_results[name] = np.mean(y_pred[mask] == y_true[mask]) * 100

    # Comparison for tested species
    tested_species = list(birdnet_results.keys())
    nt_accs = [nt_results.get(sp, 0) for sp in tested_species]
    birdnet_accs = [0] * len(tested_species)  # BirdNET got 0% on all

    x = np.arange(len(tested_species))
    width = 0.35

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 8), gridspec_kw={"width_ratios": [1, 1.2]})

    # Left: Bar comparison
    bars1 = ax1.bar(x - width / 2, nt_accs, width, label="NT Model (Ours)", color="#27ae60", edgecolor="white")
    bars2 = ax1.bar(x + width / 2, birdnet_accs, width, label="BirdNET v2.4", color="#e74c3c", edgecolor="white")

    ax1.set_ylabel("Accuracy (%)", fontsize=13, fontweight="bold")
    ax1.set_title("Classification Accuracy on NT Birds", fontsize=14, fontweight="bold")
    ax1.set_xticks(x)
    ax1.set_xticklabels(tested_species, rotation=30, ha="right", fontsize=10)
    ax1.legend(fontsize=11)
    ax1.set_ylim(0, 110)

    for bar, acc in zip(bars1, nt_accs):
        ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1,
                 f"{acc:.1f}%", ha="center", va="bottom", fontsize=10, fontweight="bold")

    for bar in bars2:
        ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1,
                 "0%", ha="center", va="bottom", fontsize=10, color="red", fontweight="bold")

    # Right: BirdNET misidentification table
    ax2.axis("off")
    table_data = [
        ["Species", "BirdNET Prediction", "Confidence", "NT Model"],
    ]
    for sp in tested_species:
        bn = birdnet_results[sp]
        nt_acc = f"{nt_results.get(sp, 0):.1f}%"
        table_data.append([
            sp,
            bn["predicted"],
            f"{bn['confidence']}%",
            nt_acc
        ])

    table = ax2.table(
        cellText=table_data[1:],
        colLabels=table_data[0],
        loc="center",
        cellLoc="center",
        colWidths=[0.28, 0.28, 0.16, 0.16]
    )
    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.scale(1, 2)

    # Style header
    for j in range(4):
        table[0, j].set_facecolor("#34495e")
        table[0, j].set_text_props(color="white", fontweight="bold")

    # Style data rows
    for i in range(1, len(table_data)):
        table[i, 1].set_text_props(color="#e74c3c")  # Red for wrong predictions
        table[i, 2].set_text_props(color="#e74c3c")
        table[i, 3].set_text_props(color="#27ae60", fontweight="bold")

    ax2.set_title(
        "BirdNET Misidentifications on NT Species\n"
        "(All predictions are Northern Hemisphere species)",
        fontsize=14,
        fontweight="bold",
        pad=20
    )

    plt.suptitle(
        "NT-Trained Model vs BirdNET (Global Model) — Performance Comparison\n"
        "RQ2: Regional vs Global Bird Classification",
        fontsize=16,
        fontweight="bold",
        y=1.02
    )
    plt.tight_layout()

    path = os.path.join(OUTPUT_DIR, "nt_vs_birdnet_comparison.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {path}")


def plot_training_history():
    """Plot training curves from CSV log."""
    print("\nGenerating training history plot...")

    import csv
    log_path = os.path.join(MODEL_DIR, "training_log_v2.csv")
    if not os.path.exists(log_path):
        print("  No training log found, skipping.")
        return

    epochs, train_acc, val_acc, train_loss, val_loss, lr = [], [], [], [], [], []
    with open(log_path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            epochs.append(int(row["epoch"]) + 1)
            train_acc.append(float(row["accuracy"]))
            val_acc.append(float(row["val_accuracy"]))
            train_loss.append(float(row["loss"]))
            val_loss.append(float(row["val_loss"]))
            lr.append(float(row["learning_rate"]))

    fig, axes = plt.subplots(1, 3, figsize=(20, 6))

    # Accuracy
    axes[0].plot(epochs, [a * 100 for a in train_acc], "b-", label="Train", linewidth=1.5)
    axes[0].plot(epochs, [a * 100 for a in val_acc], "r-", label="Validation", linewidth=1.5)
    axes[0].set_xlabel("Epoch")
    axes[0].set_ylabel("Accuracy (%)")
    axes[0].set_title("Model Accuracy", fontweight="bold")
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)
    axes[0].set_ylim(0, 100)

    # Loss
    axes[1].plot(epochs, train_loss, "b-", label="Train", linewidth=1.5)
    axes[1].plot(epochs, val_loss, "r-", label="Validation", linewidth=1.5)
    axes[1].set_xlabel("Epoch")
    axes[1].set_ylabel("Loss")
    axes[1].set_title("Model Loss", fontweight="bold")
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)

    # Learning rate
    axes[2].plot(epochs, lr, "g-", linewidth=1.5)
    axes[2].set_xlabel("Epoch")
    axes[2].set_ylabel("Learning Rate")
    axes[2].set_title("Learning Rate Schedule", fontweight="bold")
    axes[2].set_yscale("log")
    axes[2].grid(True, alpha=0.3)

    plt.suptitle(
        "NT Bird CNN — Training History (95 Epochs)",
        fontsize=15,
        fontweight="bold",
        y=1.02
    )
    plt.tight_layout()

    path = os.path.join(OUTPUT_DIR, "training_history.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {path}")


def generate_classification_report(y_true, y_pred, species_names):
    """Generate and save sklearn classification report."""
    print("\nGenerating classification report...")

    report = classification_report(
        y_true, y_pred,
        target_names=species_names,
        digits=3,
        output_dict=True
    )

    # Save as JSON
    path = os.path.join(OUTPUT_DIR, "classification_report.json")
    with open(path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"  Saved: {path}")

    # Print summary
    report_text = classification_report(
        y_true, y_pred,
        target_names=species_names,
        digits=3
    )
    print("\n" + report_text)

    # Save text version
    path_txt = os.path.join(OUTPUT_DIR, "classification_report.txt")
    with open(path_txt, "w") as f:
        f.write("NT Bird Classification Model — Classification Report\n")
        f.write("=" * 70 + "\n\n")
        f.write(report_text)
    print(f"  Saved: {path_txt}")

    return report


def main():
    print("=" * 60)
    print("  Avian Observatory — Model Evaluation")
    print("  PRT840 IT Thesis | Charles Darwin University")
    print("=" * 60)

    # Load data
    y_true, y_pred, y_probs, species_names = load_data()

    overall_acc = np.mean(y_true == y_pred) * 100
    print(f"\n  Overall test accuracy: {overall_acc:.1f}%")

    # Generate all visualisations
    cm, cm_norm = plot_confusion_matrix(y_true, y_pred, species_names)
    plot_per_species_accuracy(y_true, y_pred, species_names)
    plot_birdnet_comparison(y_true, y_pred, species_names)
    plot_training_history()
    report = generate_classification_report(y_true, y_pred, species_names)

    # Summary
    print("\n" + "=" * 60)
    print("  EVALUATION COMPLETE")
    print("=" * 60)
    print(f"\n  All outputs saved to: {OUTPUT_DIR}")
    print(f"  Files generated:")
    print(f"    confusion_matrix.png         — Normalised confusion matrix")
    print(f"    confusion_matrix_raw.png     — Raw count confusion matrix")
    print(f"    per_species_accuracy.png     — Per-species accuracy bar chart")
    print(f"    nt_vs_birdnet_comparison.png — NT Model vs BirdNET comparison")
    print(f"    training_history.png         — Training curves")
    print(f"    classification_report.json   — Full sklearn metrics")
    print(f"    classification_report.txt    — Readable report")

    # Top misconfusions
    print(f"\n  Top misconfusion pairs:")
    np.fill_diagonal(cm, 0)
    for _ in range(5):
        i, j = np.unravel_index(np.argmax(cm), cm.shape)
        if cm[i, j] > 0:
            print(f"    {species_names[i]} -> {species_names[j]}: {cm[i, j]} samples")
            cm[i, j] = 0


if __name__ == "__main__":
    main()
