"""
Reproducible historical-CNN evaluation.

Recomputes EVERY metric shown for the historical NT CNN (v2/v3) directly from
the persisted test-set arrays (models/y_test_probs*.npy + y_test_true*.npy) and
writes them as traceable evaluation artefacts under evaluation/cnn_<ver>/:

    metrics.json        overall + per-species (accuracy, precision, recall, F1,
                        AUROC, AUPRC, support) + provenance
    confusion_matrix.csv
    roc_curve.csv       micro-average ROC (fpr, tpr)
    pr_curve.csv        micro-average PR (recall, precision)

Run:  python regenerate_cnn_evaluation.py

This is the reproducibility guarantee: nothing shown in the app's Research
Metrics for the CNN is hand-entered — it is all regenerated here.
"""

import csv
import json
from pathlib import Path

import numpy as np
from sklearn.metrics import (
    accuracy_score, average_precision_score, confusion_matrix, f1_score,
    precision_recall_curve, precision_recall_fscore_support, roc_auc_score, roc_curve,
)

from birddash import config, statistics as stats

# Model versions with saved test arrays -> (probs, true, label description).
VERSIONS = {
    "v2": ("y_test_probs.npy", "y_test_true.npy", "Custom CNN, segment-level split"),
    "v3": ("y_test_probs_v3.npy", "y_test_true_v3.npy", "CNN + augmentation, segment-level split"),
    "v4": ("y_test_probs_v4.npy", "y_test_true_v4.npy", "CNN, recording-level split (no leakage)"),
}


def _labels(n_classes: int) -> list[str]:
    lm = json.loads(config.NT_LABEL_MAP_PATH.read_text())
    return [lm.get(str(i), f"class_{i}") for i in range(n_classes)]


def _downsample(x, y, n=200):
    if len(x) <= n:
        return list(map(float, x)), list(map(float, y))
    idx = np.linspace(0, len(x) - 1, n).astype(int)
    return [float(x[i]) for i in idx], [float(y[i]) for i in idx]


def _macro_intervals(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    """Bootstrap 95% CIs for accuracy and macro-F1, resampling test units with
    replacement (Efron & Tibshirani, 1993). Reuses birddash.statistics by
    bootstrapping over the row index so the paired (y_true, y_pred) structure is
    preserved when recomputing macro-F1."""
    correct = (y_true == y_pred).astype(float)
    acc_ci = stats.bootstrap_ci(correct, np.mean)
    idx = np.arange(len(y_true), dtype=float)
    macro_f1 = lambda ii: f1_score(  # noqa: E731
        y_true[ii.astype(int)], y_pred[ii.astype(int)], average="macro", zero_division=0)
    f1_ci = stats.bootstrap_ci(idx, macro_f1)
    return {"accuracy": acc_ci.as_dict(), "macro_f1": f1_ci.as_dict()}


def evaluate(version: str, probs_file: str, true_file: str, desc: str):
    probs_path = config.MODELS_DIR / probs_file
    true_path = config.MODELS_DIR / true_file
    if not (probs_path.exists() and true_path.exists()):
        print(f"  skip {version}: arrays not found")
        return

    probs = np.load(probs_path)
    true = np.load(true_path)
    y_true = true.argmax(1) if true.ndim > 1 else true
    y_pred = probs.argmax(1)
    n = probs.shape[1]
    labels = _labels(n)
    onehot = np.eye(n)[y_true]

    prec, rec, f1, support = precision_recall_fscore_support(
        y_true, y_pred, labels=range(n), zero_division=0)
    per_species = []
    for i, name in enumerate(labels):
        try:
            auroc_i = roc_auc_score(onehot[:, i], probs[:, i])
            auprc_i = average_precision_score(onehot[:, i], probs[:, i])
        except ValueError:
            auroc_i = auprc_i = None
        # Exact (Clopper–Pearson) 95% CIs for precision & recall. Recall's
        # denominator is the class support; precision's is the number predicted
        # as that class. With small support these intervals are correctly wide,
        # and `reliable` flags when the point estimate should not be read
        # directly. See birddash.statistics.
        tp_i = int(np.sum((y_true == i) & (y_pred == i)))
        n_pred_i = int(np.sum(y_pred == i))
        recall_ci = stats.clopper_pearson(tp_i, int(support[i]))
        precision_ci = stats.clopper_pearson(tp_i, n_pred_i)
        per_species.append({
            "species": name, "precision": round(float(prec[i]), 4),
            "recall": round(float(rec[i]), 4), "f1": round(float(f1[i]), 4),
            "support": int(support[i]),
            "auroc": round(auroc_i, 4) if auroc_i is not None else None,
            "auprc": round(auprc_i, 4) if auprc_i is not None else None,
            "precision_ci": precision_ci.as_dict(),
            "recall_ci": recall_ci.as_dict(),
            "reliable": bool(recall_ci.reliable() and precision_ci.reliable()),
        })

    metrics = {
        "model": f"NT Custom CNN ({version})",
        "description": desc,
        "provenance": {
            "probs_file": f"models/{probs_file}", "true_file": f"models/{true_file}",
            "n_samples": int(probs.shape[0]), "n_classes": n,
            "computed_by": "regenerate_cnn_evaluation.py",
        },
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
        "macro_f1": round(float(f1_score(y_true, y_pred, average="macro")), 4),
        "weighted_f1": round(float(f1_score(y_true, y_pred, average="weighted")), 4),
        "macro_auroc": round(float(roc_auc_score(onehot, probs, average="macro", multi_class="ovr")), 4),
        "macro_auprc": round(float(average_precision_score(onehot, probs, average="macro")), 4),
        "micro_auroc": round(float(roc_auc_score(onehot, probs, average="micro", multi_class="ovr")), 4),
        "micro_auprc": round(float(average_precision_score(onehot, probs, average="micro")), 4),
        "per_species": sorted(per_species, key=lambda p: p["f1"], reverse=True),
        # Bootstrap 95% CIs for the aggregate metrics (resampling the test units
        # — here segments — with replacement). See birddash.statistics.
        "macro_intervals": _macro_intervals(y_true, y_pred),
    }

    out_dir = config.BASE_DIR / "evaluation" / "original" / f"cnn_{version}"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "metrics.json").write_text(json.dumps(metrics, indent=2))

    # Confusion matrix
    cm = confusion_matrix(y_true, y_pred, labels=range(n))
    with open(out_dir / "confusion_matrix.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["true\\pred"] + labels)
        for i, row in enumerate(cm):
            w.writerow([labels[i]] + [int(v) for v in row])

    # Micro-average ROC + PR curves
    fpr, tpr, _ = roc_curve(onehot.ravel(), probs.ravel())
    fpr, tpr = _downsample(fpr, tpr)
    with open(out_dir / "roc_curve.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["fpr", "tpr"])
        w.writerows(zip(fpr, tpr))

    p, r, _ = precision_recall_curve(onehot.ravel(), probs.ravel())
    r, p = _downsample(r, p)
    with open(out_dir / "pr_curve.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["recall", "precision"])
        w.writerows(zip(r, p))

    print(f"  {version}: acc={metrics['accuracy']} macroF1={metrics['macro_f1']} "
          f"AUROC={metrics['macro_auroc']} AUPRC={metrics['macro_auprc']} -> {out_dir}")


if __name__ == "__main__":
    print("Regenerating historical CNN evaluation artefacts...")
    for ver, (pf, tf, desc) in VERSIONS.items():
        evaluate(ver, pf, tf, desc)
    print("Done.")
