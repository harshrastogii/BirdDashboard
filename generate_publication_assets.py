"""
Generate publication-quality figures and tables for Paper 1 — from the SAME
reproducible evaluation artefacts the application displays.

Reads only persisted artefacts (metrics.json + confusion/ROC/PR CSVs produced by
regenerate_cnn_evaluation.py / evaluate_v5.py --from-saved, and the comparison
snapshot from persist_comparison_artifact.py) — no retraining, no hardcoded
numbers. This is the clean replacement for generate_charts.py (whose values were
hardcoded and must not be used for publication).

Outputs (all under evaluation/paper1/):
    figures/   <name>.png (300 dpi) + <name>.pdf (vector), colourblind-safe
    tables/    <name>.csv + <name>.tex (LaTeX, booktabs-style)
    captions/  <name>.txt (standalone caption for the manuscript)

Run:  python generate_publication_assets.py
"""

import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from birddash import config

PAPER = config.BASE_DIR / "evaluation" / "paper1"
FIG, TAB, CAP = PAPER / "figures", PAPER / "tables", PAPER / "captions"

# Okabe–Ito colourblind-safe palette.
CB = {
    "blue": "#0072B2", "orange": "#E69F00", "green": "#009E73", "vermillion": "#D55E00",
    "sky": "#56B4E9", "yellow": "#F0E442", "purple": "#CC79A7", "grey": "#5A5A5A",
}

# (key, human title, artefact dir, provenance label)
MODELS = [
    ("cnn_v2", "Custom CNN (v2) — segment-level", "evaluation/original/cnn_v2",
     "Original evaluation (traceable)"),
    ("cnn_v4", "Custom CNN (v4) — recording-level", "evaluation/original/cnn_v4",
     "Original evaluation (traceable)"),
    ("nt_v5", "NT Custom Classifier (v5) — recording-level held-out", "evaluation/reproduced/v5",
     "Independent reproduction"),
]


def _style():
    plt.rcParams.update({
        "figure.dpi": 300, "savefig.dpi": 300, "savefig.bbox": "tight",
        "font.size": 9, "axes.titlesize": 10, "axes.labelsize": 9,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "grid.alpha": 0.25, "grid.linewidth": 0.5,
        "font.family": "sans-serif",
    })


def _load(d):
    return json.loads((config.BASE_DIR / d / "metrics.json").read_text())


def _read_curve(path, xk, yk):
    if not path.exists():
        return None, None
    xs, ys = [], []
    with open(path) as f:
        for r in csv.DictReader(f):
            xs.append(float(r[xk])); ys.append(float(r[yk]))
    return np.array(xs), np.array(ys)


def _save(fig, name):
    fig.savefig(FIG / f"{name}.png")
    fig.savefig(FIG / f"{name}.pdf")
    plt.close(fig)


def _caption(name, text):
    (CAP / f"{name}.txt").write_text(text.strip() + "\n")


# --- Figures -------------------------------------------------------------
def fig_roc_pr(key, title, d):
    for kind, (path, xk, yk, xl, yl, diag) in {
        "roc": ("roc_curve.csv", "fpr", "tpr", "False-positive rate", "True-positive rate", True),
        "pr": ("pr_curve.csv", "recall", "precision", "Recall", "Precision", False),
    }.items():
        x, y = _read_curve(config.BASE_DIR / d / path, xk, yk)
        if x is None:
            continue
        fig, ax = plt.subplots(figsize=(3.4, 3.0))
        ax.plot(x, y, color=CB["blue"], lw=1.8)
        if diag:
            ax.plot([0, 1], [0, 1], ls="--", lw=0.8, color=CB["grey"], label="chance")
            ax.legend(frameon=False, fontsize=8)
        ax.set_xlim(0, 1); ax.set_ylim(0, 1.02)
        ax.set_xlabel(xl); ax.set_ylabel(yl)
        ax.set_title(f"{title}\n{'ROC' if kind == 'roc' else 'Precision–Recall'} (micro-average)", fontsize=8)
        _save(fig, f"{key}_{kind}")


def fig_confusion(key, title, d):
    path = config.BASE_DIR / d / "confusion_matrix.csv"
    if not path.exists():
        return
    with open(path) as f:
        rows = list(csv.reader(f))
    labels = [c.replace("_", " ") for c in rows[0][1:]]
    mat = np.array([[float(v) for v in r[1:]] for r in rows[1:]])
    # Row-normalise (recall-oriented); guard empty rows.
    totals = mat.sum(axis=1, keepdims=True)
    norm = np.divide(mat, totals, out=np.zeros_like(mat), where=totals > 0)

    n = len(labels)
    fig, ax = plt.subplots(figsize=(max(5.5, n * 0.28), max(5.0, n * 0.28)))
    im = ax.imshow(norm, cmap="cividis", vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(range(n)); ax.set_yticks(range(n))
    ax.set_xticklabels(labels, rotation=90, fontsize=6)
    ax.set_yticklabels(labels, fontsize=6)
    ax.set_xlabel("Predicted"); ax.set_ylabel("True")
    ax.set_title(f"{title}\nRow-normalised confusion matrix", fontsize=8)
    ax.grid(False)
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04, label="Proportion of true class")
    _save(fig, f"{key}_confusion")


def fig_comparison():
    path = config.BASE_DIR / "evaluation" / "reproduced" / "comparison" / "metrics.json"
    if not path.exists():
        print("  (comparison artefact missing — run persist_comparison_artifact.py)")
        return
    c = json.loads(path.read_text())
    n = c["total_with_ground_truth"]
    names = ["NT Custom\nClassifier (v5)", "BirdNET v2.4\n(global)"]
    pts = [c["nt_interval"]["point"], c["birdnet_interval"]["point"]]
    los = [c["nt_interval"]["low"], c["birdnet_interval"]["low"]]
    his = [c["nt_interval"]["high"], c["birdnet_interval"]["high"]]
    correct = [c["nt_correct"], c["birdnet_correct"]]
    yerr = np.array([[p - lo for p, lo in zip(pts, los)], [hi - p for p, hi in zip(pts, his)]])

    fig, ax = plt.subplots(figsize=(4.2, 3.4))
    bars = ax.bar(names, pts, color=[CB["green"], CB["grey"]], width=0.6, zorder=2)
    ax.errorbar(names, pts, yerr=yerr, fmt="none", ecolor="black", elinewidth=1.2, capsize=6, zorder=3)
    ax.set_ylim(0, 1.05); ax.set_ylabel("Correct-detection rate")
    ax.set_title(f"NT model vs global BirdNET on {n} shared recordings\n(Wilson 95% CIs)", fontsize=8)
    for b, k in zip(bars, correct):
        ax.text(b.get_x() + b.get_width() / 2, 0.04, f"{k}/{n}", ha="center", color="white", fontsize=8, weight="bold")
    mc = c.get("mcnemar") or {}
    sig = "significant" if mc.get("significant_at_0_05") else "not significant"
    ax.text(0.5, 0.99, f"Exact McNemar: p = {mc.get('p_value'):.3f} ({sig})",
            transform=ax.transAxes, ha="center", va="top", fontsize=7.5,
            bbox=dict(boxstyle="round,pad=0.3", fc=CB["yellow"], ec="none", alpha=0.7))
    _save(fig, "comparison_nt_vs_birdnet")
    _caption("comparison_nt_vs_birdnet",
             f"NT Custom Classifier (v5) vs global BirdNET v2.4 on the {n} recordings scored by "
             f"both models (synonym-aware). Bars show the correct-detection rate with Wilson 95% "
             f"confidence intervals; the exact McNemar paired test gives p = {mc.get('p_value'):.3f} "
             f"({sig} at alpha 0.05). Point estimates favour the NT model; the difference is not yet "
             f"statistically distinguishable at this sample size.")


# --- Tables --------------------------------------------------------------
def _ci(m, key):
    ci = m.get(key)
    return f"[{ci['low']:.2f}, {ci['high']:.2f}]" if ci else ""


def table_per_class(key, title, d):
    m = _load(d)
    header = ["species", "precision", "precision_95ci", "recall", "recall_95ci", "f1", "support", "reliable"]
    rows = []
    for p in m["per_species"]:
        rows.append([
            p["species"], f"{p['precision']:.3f}", _ci(p, "precision_ci"),
            f"{p['recall']:.3f}", _ci(p, "recall_ci"), f"{p['f1']:.3f}",
            str(p["support"]), "yes" if p.get("reliable") else "no",
        ])
    with open(TAB / f"{key}_per_class.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(header); w.writerows(rows)
    _latex_table(
        TAB / f"{key}_per_class.tex",
        caption=f"Per-class metrics for {title}. 95\\% CIs are exact (Clopper–Pearson); "
                f"a class is unreliable when its interval is too wide to interpret (see METHODOLOGY).",
        label=f"tab:{key}_per_class",
        colspec="lrrrrrc",
        header=["Species", "Prec.", "Prec.\\ 95\\% CI", "Recall", "Recall 95\\% CI", "F1", "n"],
        rows=[[r[0], r[1], r[2], r[3], r[4], r[5], r[6] + ("" if r[7] == "yes" else r"\,$\dagger$")]
              for r in rows],
    )


def table_summary():
    header = ["model", "provenance", "n", "accuracy", "accuracy_95ci",
              "macro_f1", "macro_f1_95ci", "macro_auroc", "macro_auprc"]
    rows = []
    tex_rows = []
    for key, title, d, prov in MODELS:
        m = _load(d)
        pr = m.get("provenance", {})
        n = pr.get("n_test_recordings") or pr.get("n_samples") or ""
        mi = m.get("macro_intervals", {})
        acc_ci = _ci(mi, "accuracy") if isinstance(mi.get("accuracy"), dict) else ""
        f1_ci = _ci(mi, "macro_f1") if isinstance(mi.get("macro_f1"), dict) else ""
        rows.append([title, prov, str(n), f"{m['accuracy']:.4f}", acc_ci,
                     f"{m['macro_f1']:.4f}", f1_ci, f"{m['macro_auroc']:.4f}", f"{m['macro_auprc']:.4f}"])
        tex_rows.append([title.split(" — ")[0], prov.split(" (")[0], str(n),
                         f"{m['accuracy']:.3f} {acc_ci}", f"{m['macro_f1']:.3f} {f1_ci}",
                         f"{m['macro_auroc']:.3f}", f"{m['macro_auprc']:.3f}"])
    with open(TAB / "summary_metrics.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(header); w.writerows(rows)
    _latex_table(
        TAB / "summary_metrics.tex",
        caption="Aggregate metrics per model, from persisted evaluation artefacts. Accuracy and macro-F1 "
                "carry bootstrap 95\\% CIs (resampled at the test-unit level).",
        label="tab:summary_metrics", colspec="llrllrr",
        header=["Model", "Provenance", "n", "Accuracy (95\\% CI)", "Macro-F1 (95\\% CI)", "AUROC", "AUPRC"],
        rows=tex_rows,
    )


def _latex_table(path, *, caption, label, colspec, header, rows):
    esc = lambda s: str(s).replace("_", " ").replace("&", "\\&")  # noqa: E731
    lines = [
        "% Auto-generated by generate_publication_assets.py — do not edit by hand.",
        "\\begin{table}[t]", "\\centering", f"\\caption{{{caption}}}", f"\\label{{{label}}}",
        f"\\begin{{tabular}}{{{colspec}}}", "\\hline",
        " & ".join(header) + " \\\\", "\\hline",
    ]
    lines += [" & ".join(esc(c) for c in r) + " \\\\" for r in rows]
    lines += ["\\hline", "\\end{tabular}", "\\end{table}"]
    Path(path).write_text("\n".join(lines) + "\n")


def main():
    for p in (FIG, TAB, CAP):
        p.mkdir(parents=True, exist_ok=True)
    _style()
    for key, title, d, _prov in MODELS:
        if not (config.BASE_DIR / d / "metrics.json").exists():
            print(f"  skip {key}: no metrics.json")
            continue
        fig_roc_pr(key, title, d)
        fig_confusion(key, title, d)
        table_per_class(key, title, d)
        print(f"  {key}: figures + per-class table")
    fig_comparison()
    table_summary()
    print(f"Publication assets written under {PAPER}")


if __name__ == "__main__":
    main()
