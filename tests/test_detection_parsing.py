"""
Regression tests for the BirdNET name-truncation collision bug.

BirdNET-Analyzer splits a custom label "<A>_<B...>" across the CSV's Scientific
(<A>) and Common (<B...>) columns. Reading the Common column alone collapsed
species that share a final word — Barking_Owl / Masked_Owl -> "Owl" and
Black_Kite / Whistling_Kite -> "Kite" — onto whichever full label was defined
last, so Barking Owl was mislabelled "Masked Owl" and Black Kite "Whistling Kite"
(root cause: birddash/detection.py::parse_birdnet_csv). These tests pin the fix
and document the full collision scope.

Runnable:  python tests/test_detection_parsing.py
"""

import csv
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from birddash import detection

_LABELS = detection.load_official_labels()
_NAME_MAP = detection.build_name_map(_LABELS)


def _parse_rows(rows):
    """Write rows (dicts) to a temp BirdNET-format CSV and parse them."""
    fields = ["Start (s)", "End (s)", "Scientific name", "Common name", "Confidence", "File"]
    with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({**{k: "" for k in fields}, **r})
        path = f.name
    return detection.parse_birdnet_csv(path, _NAME_MAP, _LABELS)


def _species(sci, common, conf=0.99):
    return {"Start (s)": 0.0, "End (s)": 3.0, "Scientific name": sci,
            "Common name": common, "Confidence": conf}


def test_barking_owl_not_mislabelled_masked_owl():
    got = _parse_rows([_species("Barking", "Owl")])
    assert got[0]["species"] == "Barking Owl", got[0]["species"]


def test_black_kite_not_mislabelled_whistling_kite():
    got = _parse_rows([_species("Black", "Kite")])
    assert got[0]["species"] == "Black Kite", got[0]["species"]


def test_genuine_masked_owl_preserved():
    """The fix must NOT flip a real Masked Owl detection to Barking Owl."""
    got = _parse_rows([_species("Masked", "Owl")])
    assert got[0]["species"] == "Masked Owl", got[0]["species"]


def test_genuine_whistling_kite_preserved():
    got = _parse_rows([_species("Whistling", "Kite")])
    assert got[0]["species"] == "Whistling Kite", got[0]["species"]


def test_multiword_species_unaffected():
    # pretty_species renders underscores as spaces (matches the stored artefacts).
    got = _parse_rows([_species("Blue", "winged_Kookaburra"), _species("Rainbow", "Bee_eater")])
    assert got[0]["species"] == "Blue winged Kookaburra", got[0]["species"]
    assert got[1]["species"] == "Rainbow Bee eater", got[1]["species"]


def test_single_word_species_unaffected():
    """Galah has Scientific == Common; rejoin ('Galah_Galah') is not a label, so
    the fallback must still resolve it correctly."""
    got = _parse_rows([_species("Galah", "Galah")])
    assert got[0]["species"] == "Galah", got[0]["species"]


def test_collision_scope_is_only_owl_and_kite():
    """Document + guard the full scope: under BirdNET's first-underscore split,
    exactly two Common-name values map to more than one official label. If a
    future label addition introduces a new collision, this test fails loudly."""
    groups = defaultdict(list)
    for label in _LABELS:
        parts = label.split("_", 1)
        common = parts[1] if len(parts) == 2 else label
        groups[common].append(label)
    collisions = {c: labs for c, labs in groups.items() if len(labs) > 1}
    assert set(collisions) == {"Owl", "Kite"}, f"collision scope changed: {collisions}"
    assert sorted(collisions["Owl"]) == ["Barking_Owl", "Masked_Owl"]
    assert sorted(collisions["Kite"]) == ["Black_Kite", "Whistling_Kite"]


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
