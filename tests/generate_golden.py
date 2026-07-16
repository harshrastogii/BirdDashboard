"""
Generate golden-file baselines of the current ML inference outputs.

Run once (now, before any refactoring) to snapshot behaviour:

    python tests/generate_golden.py

The snapshots under tests/golden/ become the contract that Phase 2's extracted
inference modules must reproduce exactly. Re-run only when a change to the
model or pipeline is *intended* (and reviewed).
"""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from tests import _reference

GOLDEN_DIR = Path(__file__).resolve().parent / "golden"

# Small, fast, deterministic recordings used as fixtures.
NT_FIXTURES = [
    "sample_audio/Rainbow_Bee_eater_XC1001917.mp3",  # ~3s, single segment
]


def generate_nt_golden():
    model = _reference.load_nt_model()
    label_map = _reference.load_label_map()
    assert model is not None, "NT model not found — cannot generate golden."

    for rel in NT_FIXTURES:
        path = config.BASE_DIR / rel
        rows = _reference.predict_with_nt_model(str(path), model, label_map)
        out = GOLDEN_DIR / f"nt_{Path(rel).stem}.json"
        with open(out, "w") as f:
            json.dump({"fixture": rel, "rows": rows}, f, indent=2)
        print(f"Wrote {out}  ({len(rows)} rows)")


if __name__ == "__main__":
    os.makedirs(GOLDEN_DIR, exist_ok=True)
    generate_nt_golden()
    print("Golden baselines generated.")
