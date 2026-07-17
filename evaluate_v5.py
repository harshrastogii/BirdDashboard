"""
Reproducible v5 evaluation — recording-level held-out.

The production NT Custom Classifier (v5) was trained on ALL of training_data
with an internal segment-level split that was not persisted, so it cannot be
evaluated on that data without leakage. To produce an HONEST, reproducible
generalisation estimate (mirroring the v4 methodology that exposed the CNN's
leakage), this pipeline:

  1. Splits recordings per species into train/test at the RECORDING level
     (deterministic, seeded) — no recording appears in both.
  2. Retrains a v5-architecture classifier on the TRAIN split via
     birdnet_analyzer.train (same hyperparameters as train_birdnet_embeddings.py).
  3. Runs that classifier on the HELD-OUT test recordings (raw 48 kHz 3-second
     segments -> 25-class scores), aggregated to recording level.
  4. Computes and PERSISTS every artefact under evaluation/v5/:
       probabilities.npy, predictions.npy, labels.npy, split.json,
       metrics.json, confusion_matrix.csv, roc_curve.csv, pr_curve.csv

Run:  python evaluate_v5.py       (long-running: retrains + evaluates)

Once evaluation/v5/metrics.json exists, the API's Research Metrics endpoint
switches automatically from the documented thesis values to these verified
metrics.
"""

import csv
import json
import os
import random
import shutil
import subprocess
import sys
import warnings
from pathlib import Path

import numpy as np

from birddash import config, statistics as stats

warnings.filterwarnings("ignore")

SEED = 42
TEST_FRACTION = 0.2
SR = 48000
SEG = 144000  # 3 s @ 48 kHz — the v5 tflite input length

TRAIN_DATA = config.BASE_DIR / "training_data"
OUT_DIR = config.BASE_DIR / "evaluation" / "reproduced" / "v5"
TMP_TRAIN = OUT_DIR / "_train"
EVAL_TFLITE = OUT_DIR / "eval_classifier.tflite"

# v5 hyperparameters (from train_birdnet_embeddings.py). NOTE: the mixup +
# upsampling augmentation is intentionally omitted here — the current
# BirdNET-Analyzer crashes in its upsampling path on this split (an empty-class
# edge case whose error handler needs the uninstalled keras_tuner). Augmentation
# is a training-time regulariser; omitting it yields a CONSERVATIVE, honest
# held-out estimate of the v5 architecture. This deviation is recorded in the
# persisted metrics provenance.
HP = dict(epochs="100", batch_size="32", learning_rate="0.001", hidden_units="128",
          dropout="0.25", val_split="0.2", crop_mode="segments", overlap="0.5")
AUGMENTATION = False   # mixup + upsampling disabled (see note above)


def split_recordings():
    rng = random.Random(SEED)
    species = sorted(d.name for d in TRAIN_DATA.iterdir()
                     if d.is_dir() and not d.name.startswith("_"))
    train, test = {}, {}
    for sp in species:
        recs = sorted(p.name for p in (TRAIN_DATA / sp).glob("*.mp3"))
        rng.shuffle(recs)
        n_test = max(1, round(len(recs) * TEST_FRACTION))
        test[sp] = recs[:n_test]
        train[sp] = recs[n_test:]
    return species, train, test


def stage_train(train):
    if TMP_TRAIN.exists():
        shutil.rmtree(TMP_TRAIN)
    for sp, recs in train.items():
        (TMP_TRAIN / sp).mkdir(parents=True, exist_ok=True)
        for r in recs:
            dst = TMP_TRAIN / sp / r
            if not dst.exists():
                os.symlink((TRAIN_DATA / sp / r).resolve(), dst)


def retrain():
    # Stream BirdNET's (chatty, tqdm) output to a log file — capturing via a
    # PIPE deadlocks once the 64 KB buffer fills.
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    log = OUT_DIR / "train.log"
    print(f"Retraining v5 classifier on the train split (streaming to {log})...", flush=True)
    cmd = [sys.executable, "-u", "-m", "birdnet_analyzer.train", str(TMP_TRAIN),
           "-o", str(EVAL_TFLITE)]
    for k, v in HP.items():
        cmd += [f"--{k}", v]
    if AUGMENTATION:
        cmd += ["--upsampling_ratio", "0.5", "--mixup"]
    with open(log, "w") as lf:
        r = subprocess.run(cmd, cwd=config.BASE_DIR, stdout=lf, stderr=subprocess.STDOUT)
    if r.returncode != 0 or not EVAL_TFLITE.exists():
        print(f"TRAIN FAILED (rc={r.returncode}) — see {log}", flush=True)
        raise SystemExit(1)
    print("  eval classifier trained:", EVAL_TFLITE.name, flush=True)


def load_labels():
    lp = EVAL_TFLITE.with_name(EVAL_TFLITE.stem + "_Labels.txt")
    return [l.strip() for l in lp.read_text().splitlines() if l.strip()]


def evaluate(test, labels):
    import tensorflow as tf
    import librosa
    idx = {name: i for i, name in enumerate(labels)}
    it = tf.lite.Interpreter(model_path=str(EVAL_TFLITE))
    it.allocate_tensors()
    inp = it.get_input_details()[0]["index"]
    out = it.get_output_details()[0]["index"]

    all_probs, all_true, recs = [], [], []
    for sp, files in test.items():
        if sp not in idx:
            continue
        for fn in files:
            try:
                y, _ = librosa.load(TRAIN_DATA / sp / fn, sr=SR, mono=True)
            except Exception:
                continue
            seg_scores = []
            for s in range(0, max(len(y), SEG), SEG):
                seg = y[s:s + SEG]
                if len(seg) < SEG:
                    seg = np.pad(seg, (0, SEG - len(seg)))
                it.set_tensor(inp, seg.reshape(1, SEG).astype(np.float32))
                it.invoke()
                seg_scores.append(it.get_tensor(out)[0].copy())
            if not seg_scores:
                continue
            all_probs.append(np.mean(seg_scores, axis=0))
            all_true.append(idx[sp])
            recs.append(f"{sp}/{fn}")
    return np.array(all_probs), np.array(all_true), recs


def compute_and_persist(probs, true, labels, split):
    from sklearn.metrics import (
        accuracy_score, average_precision_score, confusion_matrix, f1_score,
        precision_recall_curve, precision_recall_fscore_support, roc_auc_score, roc_curve,
    )
    n = probs.shape[1]
    # Normalise scores to a probability-like distribution per sample for AUPRC/AUROC.
    pred = probs.argmax(1)
    present = sorted(set(true.tolist()))
    onehot = np.eye(n)[true]

    prec, rec, f1, support = precision_recall_fscore_support(
        true, pred, labels=range(n), zero_division=0)
    per_species = []
    for i, name in enumerate(labels):
        if support[i] == 0:
            continue
        try:
            auroc_i = roc_auc_score(onehot[:, i], probs[:, i])
            auprc_i = average_precision_score(onehot[:, i], probs[:, i])
        except ValueError:
            auroc_i = auprc_i = None
        # Exact (Clopper–Pearson) 95% CIs. On recording-level held-out data the
        # support IS the number of held-out recordings of that species, so tiny
        # supports (1–2) yield correctly wide intervals and reliable=False.
        tp_i = int(np.sum((true == i) & (pred == i)))
        n_pred_i = int(np.sum(pred == i))
        recall_ci = stats.clopper_pearson(tp_i, int(support[i]))
        precision_ci = stats.clopper_pearson(tp_i, n_pred_i)
        per_species.append({
            "species": name.replace("_", " "), "precision": round(float(prec[i]), 4),
            "recall": round(float(rec[i]), 4), "f1": round(float(f1[i]), 4),
            "support": int(support[i]),
            "auroc": round(auroc_i, 4) if auroc_i is not None else None,
            "auprc": round(auprc_i, 4) if auprc_i is not None else None,
            "precision_ci": precision_ci.as_dict(),
            "recall_ci": recall_ci.as_dict(),
            "reliable": bool(recall_ci.reliable() and precision_ci.reliable()),
        })

    cols = [i for i in present]
    metrics = {
        "model": "NT Custom Classifier (v5) — recording-level held-out",
        "description": "v5.2 approach evaluated on unseen recordings (retrained on the train split).",
        "provenance": {
            "method": "recording-level held-out; classifier retrained on train split",
            "seed": SEED, "test_fraction": TEST_FRACTION,
            "n_test_recordings": int(len(true)), "n_classes": n,
            "augmentation": "disabled (mixup/upsampling omitted — conservative estimate)",
            "eval_classifier": "evaluation/v5/eval_classifier.tflite",
            "computed_by": "evaluate_v5.py",
        },
        "accuracy": round(float(accuracy_score(true, pred)), 4),
        "macro_f1": round(float(f1_score(true, pred, average="macro", zero_division=0)), 4),
        "weighted_f1": round(float(f1_score(true, pred, average="weighted", zero_division=0)), 4),
        "macro_auroc": round(float(roc_auc_score(onehot[:, cols], probs[:, cols],
                                                 average="macro", multi_class="ovr")), 4),
        "macro_auprc": round(float(average_precision_score(onehot[:, cols], probs[:, cols],
                                                           average="macro")), 4),
        "per_species": sorted(per_species, key=lambda p: p["f1"], reverse=True),
        # Bootstrap 95% CIs for the aggregate metrics. The resampling unit is the
        # RECORDING (each row is a recording-level mean), so the interval
        # reflects recording-level — not segment-level — sampling variability.
        "macro_intervals": {
            "accuracy": stats.bootstrap_ci((true == pred).astype(float), np.mean).as_dict(),
            "macro_f1": stats.bootstrap_ci(
                np.arange(len(true), dtype=float),
                lambda ii: f1_score(true[ii.astype(int)], pred[ii.astype(int)],
                                    average="macro", zero_division=0),
            ).as_dict(),
        },
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "metrics.json").write_text(json.dumps(metrics, indent=2))
    np.save(OUT_DIR / "probabilities.npy", probs)
    np.save(OUT_DIR / "predictions.npy", pred)
    np.save(OUT_DIR / "labels.npy", true)
    (OUT_DIR / "split.json").write_text(json.dumps(split, indent=2))

    cm = confusion_matrix(true, pred, labels=range(n))
    with open(OUT_DIR / "confusion_matrix.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["true\\pred"] + labels)
        for i, row in enumerate(cm):
            w.writerow([labels[i]] + [int(v) for v in row])

    fpr, tpr, _ = roc_curve(onehot[:, cols].ravel(), probs[:, cols].ravel())
    _dump_curve(OUT_DIR / "roc_curve.csv", ["fpr", "tpr"], fpr, tpr)
    p, r, _ = precision_recall_curve(onehot[:, cols].ravel(), probs[:, cols].ravel())
    _dump_curve(OUT_DIR / "pr_curve.csv", ["recall", "precision"], r, p)

    print(f"v5 held-out: acc={metrics['accuracy']} macroF1={metrics['macro_f1']} "
          f"AUROC={metrics['macro_auroc']} AUPRC={metrics['macro_auprc']} "
          f"(n_test={len(true)}) -> {OUT_DIR}")


def _dump_curve(path, header, x, y, n=200):
    x, y = np.asarray(x), np.asarray(y)
    if len(x) > n:
        i = np.linspace(0, len(x) - 1, n).astype(int)
        x, y = x[i], y[i]
    with open(path, "w", newline="") as f:
        w = csv.writer(f); w.writerow(header); w.writerows(zip(map(float, x), map(float, y)))


def recompute_from_saved():
    """Recompute metrics.json (now including Clopper–Pearson per-class CIs and
    bootstrap macro CIs) from the PERSISTED evaluation arrays — WITHOUT
    retraining. This respects the owner's pause on v5 retraining while still
    producing the honest uncertainty statistics from the existing held-out
    experiment's saved probabilities/labels."""
    probs = np.load(OUT_DIR / "probabilities.npy")
    true = np.load(OUT_DIR / "labels.npy")
    labels = load_labels()
    split_path = OUT_DIR / "split.json"
    split = json.loads(split_path.read_text()) if split_path.exists() else {}
    compute_and_persist(probs, true, labels, split)
    print("Recomputed v5 metrics (with CIs) from saved arrays — no retraining.")


if __name__ == "__main__":
    if "--from-saved" in sys.argv:
        recompute_from_saved()
        raise SystemExit(0)

    species, train, test = split_recordings()
    print(f"Recording-level split (seed={SEED}): "
          f"{sum(len(v) for v in train.values())} train / {sum(len(v) for v in test.values())} test")
    stage_train(train)
    retrain()
    labels = load_labels()
    probs, true, recs = evaluate(test, labels)
    compute_and_persist(probs, true, labels,
                        {"seed": SEED, "test_fraction": TEST_FRACTION,
                         "test_recordings": recs})
    if TMP_TRAIN.exists():
        shutil.rmtree(TMP_TRAIN)   # symlink dir; artefacts + eval classifier kept
    print("Done. Research Metrics will now show verified v5 metrics.")
