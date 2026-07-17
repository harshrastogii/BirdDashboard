"""
Model-registry use-case — models as versioned scientific artefacts.

Reads evaluation/registry.json (the single source of truth for model versions)
and, for each model, resolves its evaluation records from disk. The two
concepts are kept strictly distinct and never conflated:

  * `documented`             — reported research values with NO traceable
                               artefact (e.g. the v5 thesis AUPRC/AUROC).
  * `original_evaluation`    — metrics reproduced from the ORIGINAL saved
                               artefacts (the original experiment, traceable).
  * `independent_reproduction` — a NEW evaluation (fresh split + retrain), never
                               presented as the original experiment.

Future models (v6, v7, ...) are added by editing registry.json + dropping
artefacts — no code change here.
"""

import csv
import json

from api.schemas import (
    CurvePoint, DocumentedMetrics, ModelEvaluation, ModelMetrics,
    ModelRegistryOut, PerSpeciesMetric, RegistryModel,
)
from birddash import config


def _read_curve(path, x_key, y_key) -> list[CurvePoint]:
    if not path.exists():
        return []
    with open(path) as f:
        return [CurvePoint(x=float(r[x_key]), y=float(r[y_key])) for r in csv.DictReader(f)]


def _load_metrics(artefact_dir: str) -> ModelMetrics | None:
    d = config.BASE_DIR / artefact_dir
    mfile = d / "metrics.json"
    if not mfile.exists():
        return None
    m = json.loads(mfile.read_text())
    return ModelMetrics(
        version=m.get("model", artefact_dir), description=m.get("description", ""),
        accuracy=m["accuracy"], macro_f1=m["macro_f1"], weighted_f1=m["weighted_f1"],
        macro_auroc=m["macro_auroc"], macro_auprc=m["macro_auprc"],
        # PerSpeciesMetric now carries optional Clopper–Pearson CIs + a
        # reliability flag; extra keys in older artefacts are ignored, and the
        # CI keys are picked up automatically once the artefacts include them.
        per_species=[PerSpeciesMetric(**p) for p in m["per_species"]],
        roc_curve=_read_curve(d / "roc_curve.csv", "fpr", "tpr"),
        pr_curve=_read_curve(d / "pr_curve.csv", "recall", "precision"),
        provenance=m.get("provenance", {}),
        macro_intervals=m.get("macro_intervals") or None,
    )


def registry() -> ModelRegistryOut:
    reg = json.loads((config.BASE_DIR / "evaluation" / "registry.json").read_text())
    models = []
    for m in reg["models"]:
        evals = []
        for e in m.get("evaluations", []):
            metrics = _load_metrics(e["artefact_dir"])
            evals.append(ModelEvaluation(
                id=e["id"], type=e["type"], title=e["title"], note=e["note"],
                available=metrics is not None, metrics=metrics,
            ))
        documented = None
        if m.get("documented"):
            documented = DocumentedMetrics(**m["documented"])
        models.append(RegistryModel(
            key=m["key"], name=m["name"], version=m["version"], family=m["family"],
            status=m["status"], description=m["description"],
            documented=documented, evaluations=evals,
        ))
    return ModelRegistryOut(evaluation_types=reg.get("evaluation_types", {}), models=models)
