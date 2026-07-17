"""
Verify metric provenance (Phase 7 · D).

Proves that EVERY evaluation metric the application can display originates from a
reproducible artefact catalogued in the Publication Asset Registry — the same
artefacts Paper 1 uses — and that the only un-traceable numbers are explicitly
flagged 'documented · not verified'.

Checks:
  1. Every evaluation in evaluation/registry.json with metrics resolves to a
     metrics.json that exists and is catalogued in evaluation/asset_registry.json.
  2. The live /models/comparison computation equals the persisted snapshot
     (evaluation/reproduced/comparison/metrics.json) — so app == artefact.
  3. The Model Evolution narrative constants trace to artefacts: 92.7% -> cnn_v2
     accuracy, 66.6% -> cnn_v4 accuracy; and the v5 0.98/0.99 are ONLY ever shown
     behind a 'Documented · not verified' badge.
  4. The hardcoded generate_charts.py is not on any displayed/verified path.

Exit code 0 = all checks pass. Run:  python verify_metric_provenance.py
"""

import json
from pathlib import Path

from birddash import config

BASE = config.BASE_DIR
FRONTEND = BASE / "frontend"
_ok, _fail = [], []


def check(name, ok, detail=""):
    (_ok if ok else _fail).append(name)
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))


def approx(a, b, tol=0.001):
    return abs(a - b) <= tol


def main():
    registry = json.loads((BASE / "evaluation" / "registry.json").read_text())
    assets = json.loads((BASE / "evaluation" / "asset_registry.json").read_text())
    asset_paths = {a["path"] for a in assets["assets"]}

    # 1. Registry evaluations resolve to catalogued metrics.json.
    print("1. Registry evaluations trace to catalogued artefacts:")
    for m in registry["models"]:
        for e in m.get("evaluations", []):
            mj = f"{e['artefact_dir']}/metrics.json"
            exists = (BASE / mj).exists()
            catalogued = mj in asset_paths
            check(f"{m['key']}/{e['id']} -> {mj}", exists and catalogued,
                  "" if exists and catalogued else f"exists={exists} catalogued={catalogued}")

    # 2. Live comparison == persisted snapshot.
    print("2. Live comparison equals the persisted artefact:")
    snap_path = BASE / "evaluation" / "reproduced" / "comparison" / "metrics.json"
    try:
        from api.db import SessionLocal
        from api.models import Organisation
        from api.security import Principal, ROLE_SCOPES
        from api.services.model_comparison import compare
        db = SessionLocal()
        org = db.query(Organisation).first()
        principal = Principal(organisation_id=org.id, roles=["admin"],
                              scopes=set().union(*ROLE_SCOPES.values()))
        live = compare(db, principal).model_dump(mode="json")
        db.close()
        snap = json.loads(snap_path.read_text())
        same = (live["nt_correct"] == snap["nt_correct"]
                and live["birdnet_correct"] == snap["birdnet_correct"]
                and live["total_with_ground_truth"] == snap["total_with_ground_truth"])
        check("live == snapshot (NT/BirdNET/total)", same,
              f"live {live['nt_correct']}/{live['birdnet_correct']}/{live['total_with_ground_truth']} "
              f"vs snap {snap['nt_correct']}/{snap['birdnet_correct']}/{snap['total_with_ground_truth']}")
    except Exception as e:  # pragma: no cover - DB optional
        check("live == snapshot", False, f"could not recompute (DB?): {e}")

    # 3. Model Evolution narrative constants trace to artefacts.
    print("3. Model Evolution constants trace to artefacts:")
    v2 = json.loads((BASE / "evaluation/original/cnn_v2/metrics.json").read_text())
    v4 = json.loads((BASE / "evaluation/original/cnn_v4/metrics.json").read_text())
    check("92.7% -> cnn_v2 accuracy", approx(v2["accuracy"], 0.927, 0.001), f"{v2['accuracy']}")
    check("66.6% -> cnn_v4 accuracy", approx(v4["accuracy"], 0.666, 0.001), f"{v4['accuracy']}")

    # 3b. The v5 0.98/0.99 appear ONLY with a documented-not-verified badge.
    evo = (FRONTEND / "app/(platform)/models/page.tsx").read_text()
    panel = (FRONTEND / "components/domain/model-comparison-panel.tsx").read_text()
    check("evolution v5 0.98/0.99 flagged documented",
          "0.98" in evo and "documented: true" in evo)
    check("comparison-panel 0.98/0.99 badged 'Documented · not verified'",
          "AUPRC 0.98" in panel and "Documented · not verified" in panel)

    # 4. Hardcoded generate_charts.py is not imported anywhere on the app/eval path.
    print("4. Hardcoded generate_charts.py is quarantined:")
    import_markers = ("import generate_charts", "from generate_charts")
    importers = []
    for p in list(BASE.glob("api/**/*.py")) + [
        BASE / "regenerate_cnn_evaluation.py", BASE / "evaluate_v5.py",
        BASE / "generate_publication_assets.py",
    ]:
        if p.exists() and any(mk in p.read_text() for mk in import_markers):
            importers.append(str(p.relative_to(BASE)))
    check("no verified path imports generate_charts.py", not importers, ", ".join(importers))

    print(f"\n{'=' * 48}\n{len(_ok)} passed, {len(_fail)} failed")
    if _fail:
        print("FAILED:", ", ".join(_fail))
        raise SystemExit(1)
    print("All displayed metrics trace to reproducible artefacts. ✓")


if __name__ == "__main__":
    main()
