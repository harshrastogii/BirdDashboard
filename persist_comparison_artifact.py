"""
Persist the operational NT-vs-BirdNET comparison as a reproducible artefact.

The comparison (`/api/v1/models/comparison`) is computed live from the seeded
recordings + filesystem detections. For Paper 1 and the Publication Asset
Registry, the SAME computation is snapshotted to disk so the figure/table and the
app both trace to one artefact:

    evaluation/reproduced/comparison/metrics.json

This uses the identical service code the API uses (api.services.model_comparison),
so the persisted numbers are guaranteed to match what the app displays. Provenance
type: `live_comparison` (a per-recording detection test, not a held-out classifier
eval). Re-run after the recording set changes:

    python persist_comparison_artifact.py
"""

import json
from datetime import datetime, timezone

from api.db import SessionLocal
from api.models import Organisation
from api.security import Principal, ROLE_SCOPES
from api.services.model_comparison import compare
from birddash import config


def main() -> None:
    db = SessionLocal()
    try:
        org = db.query(Organisation).first()
        if org is None:
            raise SystemExit("No organisation seeded — run `python -m api.seed` first.")
        principal = Principal(
            organisation_id=org.id, roles=["admin"],
            scopes=set().union(*ROLE_SCOPES.values()),
        )
        out = compare(db, principal)
    finally:
        db.close()

    data = out.model_dump(mode="json")
    data["provenance"] = {
        **data.get("provenance", {}),
        "type": "live_comparison",
        "computed_by": "persist_comparison_artifact.py -> api.services.model_comparison.compare",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "note": "Snapshot of the live per-recording detection test. The app computes "
                "this on demand with the identical service code, so the numbers match.",
    }

    out_dir = config.BASE_DIR / "evaluation" / "reproduced" / "comparison"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "metrics.json").write_text(json.dumps(data, indent=2))

    nt, bn, n = data["nt_correct"], data["birdnet_correct"], data["total_with_ground_truth"]
    mc = data.get("mcnemar") or {}
    print(f"Comparison snapshot: NT {nt}/{n}, BirdNET {bn}/{n}, "
          f"McNemar p={mc.get('p_value')} -> {out_dir/'metrics.json'}")


if __name__ == "__main__":
    main()
