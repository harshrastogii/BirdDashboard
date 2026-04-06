"""
NT Bird Acoustic Monitor — Generate Evaluation Charts
Comparison across v2, v3, v4 model versions
PRT840 IT Thesis | Charles Darwin University
"""

import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
import numpy as np
import json
import os

OUTPUT_DIR = os.path.expanduser("~/BirdDashboard/evaluation")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ============================================================
# DATA
# ============================================================

# v2 (Custom CNN - segment split)
v2_accuracy = 0.9267
v2_species = {
    "Azure Kingfisher": 0.96, "Barking Owl": 0.985, "Black Kite": 0.949,
    "Blue-winged Kookaburra": 0.924, "Bush Stone-curlew": 0.921,
    "Channel-billed Cuckoo": 0.900, "Diamond Dove": 0.739, "Galah": 0.856,
    "Gouldian Finch": 0.833, "Great Bowerbird": 0.946, "Helmeted Friarbird": 0.927,
    "Hooded Parrot": 0.900, "Laughing Kookaburra": 0.920, "Magpie Goose": 0.944,
    "Masked Owl": 0.966, "Partridge Pigeon": 1.000, "Pheasant Coucal": 0.920,
    "Rainbow Bee-eater": 0.873, "Red-tailed Black Cockatoo": 0.941,
    "Sulphur-crested Cockatoo": 0.959, "Tawny Frogmouth": 0.965,
    "Torresian Crow": 0.873, "Whistling Kite": 0.875, "Willie Wagtail": 0.928
}

# v3 (CNN + Augmentation - segment split)
v3_accuracy = 0.9274
v3_species = {
    "Azure Kingfisher": 1.000, "Barking Owl": 0.977, "Black Kite": 0.939,
    "Blue-winged Kookaburra": 0.930, "Bush Stone-curlew": 0.931,
    "Channel-billed Cuckoo": 0.850, "Diamond Dove": 0.870, "Galah": 0.899,
    "Gouldian Finch": 0.833, "Great Bowerbird": 0.957, "Helmeted Friarbird": 0.942,
    "Hooded Parrot": 0.900, "Laughing Kookaburra": 0.928, "Magpie Goose": 0.958,
    "Masked Owl": 0.966, "Partridge Pigeon": 1.000, "Pheasant Coucal": 0.943,
    "Rainbow Bee-eater": 0.873, "Red-tailed Black Cockatoo": 0.929,
    "Sulphur-crested Cockatoo": 0.948, "Tawny Frogmouth": 0.982,
    "Torresian Crow": 0.850, "Whistling Kite": 0.896, "Willie Wagtail": 0.921
}

# v4 (CNN + Augmentation + Recording-level split) — mapped class names
v4_accuracy = 0.6661
v4_species = {
    "Azure Kingfisher": 0.500, "Barking Owl": 0.938, "Black Kite": 0.798,
    "Blue-winged Kookaburra": 0.766, "Bush Stone-curlew": 0.438,
    "Channel-billed Cuckoo": 0.442, "Diamond Dove": 0.939, "Galah": 0.655,
    "Gouldian Finch": 1.000, "Great Bowerbird": 0.471, "Helmeted Friarbird": 0.640,
    "Hooded Parrot": 0.097, "Laughing Kookaburra": 0.705, "Magpie Goose": 0.913,
    "Masked Owl": 0.438, "Pheasant Coucal": 0.378, "Rainbow Bee-eater": 0.627,
    "Red-tailed Black Cockatoo": 0.925, "Sulphur-crested Cockatoo": 0.856,
    "Tawny Frogmouth": 0.265, "Torresian Crow": 0.721, "Whistling Kite": 0.467,
    "Willie Wagtail": 0.294
}

# Consistent species order (all 24 for v2/v3, 23 for v4)
all_species = sorted(v3_species.keys())

# Colors
COLOR_V2 = '#2196F3'  # Blue
COLOR_V3 = '#4CAF50'  # Green
COLOR_V4 = '#FF9800'  # Orange
COLOR_BIRDNET = '#F44336'  # Red

plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.size'] = 11


# ============================================================
# CHART 1: Overall Accuracy Comparison
# ============================================================
def chart_overall_accuracy():
    fig, ax = plt.subplots(figsize=(10, 6))
    
    models = ['BirdNET v2.4\n(Global)', 'Custom CNN v2\n(Segment Split)', 
              'Custom CNN v3\n(+ Augmentation)', 'Custom CNN v4\n(Recording Split)']
    accuracies = [0.0, v2_accuracy * 100, v3_accuracy * 100, v4_accuracy * 100]
    colors = [COLOR_BIRDNET, COLOR_V2, COLOR_V3, COLOR_V4]
    
    bars = ax.bar(models, accuracies, color=colors, width=0.6, edgecolor='white', linewidth=1.5)
    
    for bar, acc in zip(bars, accuracies):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1.5, 
                f'{acc:.1f}%', ha='center', va='bottom', fontweight='bold', fontsize=13)
    
    ax.set_ylabel('Test Accuracy (%)', fontsize=13)
    ax.set_title('Model Performance Comparison on NT Bird Species', fontsize=15, fontweight='bold', pad=15)
    ax.set_ylim(0, 105)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.axhline(y=50, color='gray', linestyle='--', alpha=0.3, label='50% baseline')
    
    # Add annotation
    ax.annotate('Segment-level split\n(inflated)', xy=(1, v2_accuracy*100), 
                xytext=(1.5, 75), fontsize=9, color='gray', style='italic',
                arrowprops=dict(arrowstyle='->', color='gray', lw=0.8))
    ax.annotate('Recording-level split\n(honest generalisation)', xy=(3, v4_accuracy*100), 
                xytext=(2.5, 50), fontsize=9, color='gray', style='italic',
                arrowprops=dict(arrowstyle='->', color='gray', lw=0.8))
    
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, 'model_comparison_overall.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print("  Saved: model_comparison_overall.png")


# ============================================================
# CHART 2: Per-Species Accuracy — v3 vs v4
# ============================================================
def chart_v3_vs_v4_species():
    # Only species present in both
    common_species = [s for s in all_species if s in v4_species]
    
    v3_vals = [v3_species.get(s, 0) * 100 for s in common_species]
    v4_vals = [v4_species.get(s, 0) * 100 for s in common_species]
    
    fig, ax = plt.subplots(figsize=(14, 8))
    
    x = np.arange(len(common_species))
    width = 0.35
    
    bars1 = ax.bar(x - width/2, v3_vals, width, label='v3 (Augmented, Segment Split)', 
                   color=COLOR_V3, alpha=0.85, edgecolor='white')
    bars2 = ax.bar(x + width/2, v4_vals, width, label='v4 (Augmented, Recording Split)', 
                   color=COLOR_V4, alpha=0.85, edgecolor='white')
    
    ax.set_ylabel('Accuracy (%)', fontsize=13)
    ax.set_title('Per-Species Accuracy: v3 (Segment Split) vs v4 (Recording Split)', 
                 fontsize=14, fontweight='bold', pad=15)
    ax.set_xticks(x)
    ax.set_xticklabels(common_species, rotation=45, ha='right', fontsize=9)
    ax.legend(loc='upper right', fontsize=10)
    ax.set_ylim(0, 110)
    ax.axhline(y=50, color='gray', linestyle='--', alpha=0.3)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    # Highlight species with big drops
    for i, (v3, v4) in enumerate(zip(v3_vals, v4_vals)):
        if v3 - v4 > 30:
            ax.annotate(f'↓{v3-v4:.0f}%', xy=(i, v4), xytext=(i+0.3, v4+8),
                       fontsize=8, color='red', fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, 'v3_vs_v4_per_species.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print("  Saved: v3_vs_v4_per_species.png")


# ============================================================
# CHART 3: Generalisation Gap (v3 - v4 difference)
# ============================================================
def chart_generalisation_gap():
    common_species = [s for s in all_species if s in v4_species]
    
    gaps = [(v3_species.get(s, 0) - v4_species.get(s, 0)) * 100 for s in common_species]
    
    # Sort by gap size
    sorted_pairs = sorted(zip(common_species, gaps), key=lambda x: x[1], reverse=True)
    sorted_species = [p[0] for p in sorted_pairs]
    sorted_gaps = [p[1] for p in sorted_pairs]
    
    fig, ax = plt.subplots(figsize=(12, 8))
    
    colors = [COLOR_BIRDNET if g > 30 else (COLOR_V4 if g > 15 else COLOR_V3) for g in sorted_gaps]
    
    bars = ax.barh(range(len(sorted_species)), sorted_gaps, color=colors, edgecolor='white', linewidth=0.5)
    ax.set_yticks(range(len(sorted_species)))
    ax.set_yticklabels(sorted_species, fontsize=10)
    ax.set_xlabel('Accuracy Drop (percentage points)', fontsize=12)
    ax.set_title('Generalisation Gap: How Much Accuracy Drops on Unseen Recordings', 
                 fontsize=14, fontweight='bold', pad=15)
    ax.invert_yaxis()
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    # Add value labels
    for i, (bar, val) in enumerate(zip(bars, sorted_gaps)):
        ax.text(val + 0.5, i, f'{val:.1f}%', va='center', fontsize=9)
    
    # Legend
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor=COLOR_BIRDNET, label='Severe drop (>30%)'),
        Patch(facecolor=COLOR_V4, label='Moderate drop (15-30%)'),
        Patch(facecolor=COLOR_V3, label='Minimal drop (<15%)')
    ]
    ax.legend(handles=legend_elements, loc='lower right', fontsize=10)
    
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, 'generalisation_gap.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print("  Saved: generalisation_gap.png")


# ============================================================
# CHART 4: Training History Comparison (v2, v3, v4)
# ============================================================
def chart_training_history():
    import csv
    
    def load_log(path):
        with open(path) as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        epochs = [int(r.get('epoch', i)) + 1 for i, r in enumerate(rows)]
        train_acc = [float(r['accuracy']) * 100 for r in rows]
        val_acc = [float(r['val_accuracy']) * 100 for r in rows]
        return epochs, train_acc, val_acc
    
    model_dir = os.path.expanduser("~/BirdDashboard/models")
    
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    
    logs = [
        ('training_log_v2.csv', 'v2: Custom CNN', COLOR_V2),
        ('training_log_v3.csv', 'v3: CNN + Augmentation', COLOR_V3),
        ('training_log_v4.csv', 'v4: Recording Split', COLOR_V4),
    ]
    
    for ax, (logfile, title, color) in zip(axes, logs):
        path = os.path.join(model_dir, logfile)
        if os.path.exists(path):
            epochs, train_acc, val_acc = load_log(path)
            ax.plot(epochs, train_acc, color=color, alpha=0.7, label='Train', linewidth=1.5)
            ax.plot(epochs, val_acc, color=color, linestyle='--', label='Validation', linewidth=1.5)
            ax.set_title(title, fontsize=12, fontweight='bold')
            ax.set_xlabel('Epoch')
            ax.set_ylabel('Accuracy (%)')
            ax.legend(fontsize=9)
            ax.set_ylim(0, 100)
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.axhline(y=max(val_acc), color='gray', linestyle=':', alpha=0.5)
            ax.text(len(epochs)*0.7, max(val_acc)+2, f'Best: {max(val_acc):.1f}%', 
                   fontsize=9, color='gray')
    
    plt.suptitle('Training History Across Model Versions', fontsize=15, fontweight='bold', y=1.02)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, 'training_history_comparison.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print("  Saved: training_history_comparison.png")


# ============================================================
# CHART 5: Model Evolution Summary
# ============================================================
def chart_model_evolution():
    fig, ax = plt.subplots(figsize=(12, 6))
    
    versions = ['v2\nCustom CNN', 'v3\n+ Augmentation', 'v4\nRecording Split', 'v5\nBirdNET Embeddings']
    test_acc = [92.7, 92.7, 66.6, None]
    val_acc = [None, 93.0, 62.0, 98.0]  # AUPRC for v5
    
    x = np.arange(len(versions))
    
    # Plot test accuracy
    test_points = [(i, a) for i, a in enumerate(test_acc) if a is not None]
    if test_points:
        ax.plot([p[0] for p in test_points], [p[1] for p in test_points], 
                'o-', color=COLOR_V3, markersize=12, linewidth=2, label='Test Accuracy (%)', zorder=5)
        for i, a in test_points:
            ax.annotate(f'{a:.1f}%', (i, a), textcoords="offset points", 
                       xytext=(0, 15), ha='center', fontweight='bold', fontsize=12)
    
    # Annotations for each version
    annotations = [
        'Segment-level split\n24 species\n95 epochs, ~13hrs',
        'SpecAugment + noise\nSame split as v2\n120 epochs, ~16hrs',
        'No recording leakage\nHonest generalisation\n70 epochs, ~12hrs',
        'Transfer learning\nAUPRC: 0.98\nTraining: 7 minutes'
    ]
    
    for i, note in enumerate(annotations):
        y_pos = 30 if i % 2 == 0 else 20
        ax.text(i, y_pos, note, ha='center', fontsize=9, color='gray',
               bbox=dict(boxstyle='round,pad=0.5', facecolor='lightyellow', alpha=0.8))
    
    ax.set_xticks(x)
    ax.set_xticklabels(versions, fontsize=11)
    ax.set_ylabel('Accuracy / AUPRC (%)', fontsize=12)
    ax.set_title('Model Evolution: From Custom CNN to Transfer Learning', 
                 fontsize=15, fontweight='bold', pad=15)
    ax.set_ylim(0, 110)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.legend(loc='upper left', fontsize=10)
    
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, 'model_evolution.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print("  Saved: model_evolution.png")


# ============================================================
# CHART 6: NT Model vs BirdNET (per species)
# ============================================================
def chart_nt_vs_birdnet():
    fig, ax = plt.subplots(figsize=(14, 7))
    
    species_list = sorted(v3_species.keys())
    v3_vals = [v3_species[s] * 100 for s in species_list]
    birdnet_vals = [0] * len(species_list)  # BirdNET = 0% on NT species
    
    x = np.arange(len(species_list))
    width = 0.35
    
    ax.bar(x - width/2, v3_vals, width, label='Custom NT Model (v3)', color=COLOR_V3, edgecolor='white')
    ax.bar(x + width/2, birdnet_vals, width, label='BirdNET v2.4', color=COLOR_BIRDNET, edgecolor='white')
    
    ax.set_ylabel('Accuracy (%)', fontsize=13)
    ax.set_title('Custom NT Model vs BirdNET v2.4 on Northern Territory Species', 
                 fontsize=14, fontweight='bold', pad=15)
    ax.set_xticks(x)
    ax.set_xticklabels(species_list, rotation=45, ha='right', fontsize=9)
    ax.legend(fontsize=11)
    ax.set_ylim(0, 110)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    # Overall accuracy labels
    ax.text(len(species_list)-1, 100, f'NT Model: {v3_accuracy*100:.1f}%', 
            fontsize=11, fontweight='bold', color=COLOR_V3, ha='right')
    ax.text(len(species_list)-1, 8, f'BirdNET: ~0%', 
            fontsize=11, fontweight='bold', color=COLOR_BIRDNET, ha='right')
    
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, 'nt_model_vs_birdnet.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print("  Saved: nt_model_vs_birdnet.png")


# ============================================================
# MAIN
# ============================================================
def main():
    print("=" * 60)
    print("  Generating Evaluation Charts")
    print("  NT Bird Acoustic Monitor | PRT840 IT Thesis")
    print("=" * 60)
    
    chart_overall_accuracy()
    chart_v3_vs_v4_species()
    chart_generalisation_gap()
    chart_training_history()
    chart_model_evolution()
    chart_nt_vs_birdnet()
    
    print(f"\n  All charts saved to: {OUTPUT_DIR}")
    print("  Charts generated:")
    for f in sorted(os.listdir(OUTPUT_DIR)):
        if f.endswith('.png'):
            size = os.path.getsize(os.path.join(OUTPUT_DIR, f)) / 1024
            print(f"    {f} ({size:.0f} KB)")


if __name__ == "__main__":
    main()
