"""
Golden-file parity tests — the safety net for the incremental migration.

These assert that the ML inference still produces the outputs snapshotted in
tests/golden/. They are the guard that Phase 2 (extracting inference into
shared modules) changes NOTHING about the scientific results.

Runnable two ways:
    python tests/test_inference_parity.py       # plain, no pytest needed
    pytest tests/                               # if pytest is installed

Regenerate goldens only for an *intended* model/pipeline change:
    python tests/generate_golden.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from tests import _reference

GOLDEN_DIR = Path(__file__).resolve().parent / "golden"
CONF_TOL = 1e-4  # float tolerance for model confidence scores


def _load_golden(name):
    with open(GOLDEN_DIR / name) as f:
        return json.load(f)


def test_config_paths_resolve():
    """Config is portable and the core model artifacts are present."""
    assert config.BASE_DIR.exists()
    assert config.NT_MODEL_PATH.exists(), "NT model missing"
    assert config.NT_LABEL_MAP_PATH.exists(), "label map missing"
    assert config.CLASSIFIER_TFLITE_PATH.exists(), "TFLite classifier missing"


def test_nt_model_parity():
    """NT CNN produces outputs identical to the pre-refactor golden."""
    model = _reference.load_nt_model()
    label_map = _reference.load_label_map()
    assert model is not None

    golden = _load_golden("nt_Rainbow_Bee_eater_XC1001917.json")
    path = config.BASE_DIR / golden["fixture"]
    rows = _reference.predict_with_nt_model(str(path), model, label_map)

    expected = golden["rows"]
    assert len(rows) == len(expected), (
        f"Row count changed: {len(rows)} vs golden {len(expected)}"
    )
    for got, exp in zip(rows, expected):
        assert got["Start (s)"] == exp["Start (s)"]
        assert got["End (s)"] == exp["End (s)"]
        assert got["Rank"] == exp["Rank"]
        assert got["Species"] == exp["Species"], (
            f"Species changed at rank {exp['Rank']}: {got['Species']} vs {exp['Species']}"
        )
        assert abs(got["Confidence"] - exp["Confidence"]) < CONF_TOL, (
            f"Confidence drift: {got['Confidence']} vs {exp['Confidence']}"
        )


def test_nt_model_determinism():
    """Same input twice -> byte-identical predictions (no hidden randomness)."""
    model = _reference.load_nt_model()
    label_map = _reference.load_label_map()
    path = config.BASE_DIR / "sample_audio/Rainbow_Bee_eater_XC1001917.mp3"
    a = _reference.predict_with_nt_model(str(path), model, label_map)
    b = _reference.predict_with_nt_model(str(path), model, label_map)
    assert a == b


def _run_all():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failures = 0
    for t in tests:
        try:
            t()
            print(f"PASS  {t.__name__}")
        except AssertionError as e:
            failures += 1
            print(f"FAIL  {t.__name__}: {e}")
        except Exception as e:  # noqa: BLE001
            failures += 1
            print(f"ERROR {t.__name__}: {type(e).__name__}: {e}")
    print(f"\n{len(tests) - failures}/{len(tests)} passed")
    return failures


if __name__ == "__main__":
    sys.exit(1 if _run_all() else 0)
