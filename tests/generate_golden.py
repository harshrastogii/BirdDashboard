"""
Generate golden-file baselines of the ML inference outputs.

The Phase-1 baselines under tests/golden/ were captured from the original
in-app logic before extraction. Re-run this ONLY when a change to the model or
pipeline is *intended* (and reviewed):

    python tests/generate_golden.py

Uses the extracted birddash.nt_model package (the current source of truth).
"""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from birddash import config, nt_model

GOLDEN_DIR = Path(__file__).resolve().parent / "golden"

# Small, fast, deterministic recordings used as fixtures.
NT_FIXTURES = [
    "sample_audio/Rainbow_Bee_eater_XC1001917.mp3",  # ~3s, single segment
]


def generate_nt_golden():
    model = nt_model.load_model()
    label_map = nt_model.load_label_map()
    assert model is not None, "NT model not found — cannot generate golden."

    for rel in NT_FIXTURES:
        path = config.BASE_DIR / rel
        rows = nt_model.predict(str(path), model, label_map).to_dict("records")
        out = GOLDEN_DIR / f"nt_{Path(rel).stem}.json"
        with open(out, "w") as f:
            json.dump({"fixture": rel, "rows": rows}, f, indent=2)
        print(f"Wrote {out}  ({len(rows)} rows)")


if __name__ == "__main__":
    os.makedirs(GOLDEN_DIR, exist_ok=True)
    generate_nt_golden()
    print("Golden baselines generated.")
