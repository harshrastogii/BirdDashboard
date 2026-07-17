"""
Species-name canonicalisation and synonym handling — framework-free core.

Two recordings, two models, and two label sources can refer to the *same*
species by different strings. There are two distinct causes, handled here:

1. **Orthographic variants** — hyphenation, spacing, and case
   ("Blue-winged Kookaburra" vs "Blue winged Kookaburra",
   "Red-tailed Black-Cockatoo" vs "Red tailed Black Cockatoo"). These are the
   same name written differently and are collapsed by `normalize`.

2. **True nomenclatural synonyms** — different accepted common names for one
   biological species across checklists. The one that affects this dataset is
   the global/IOC name **"Bush Thick-knee"** for the Australian
   **"Bush Stone-curlew"** (*Burhinus grallarius*). BirdNET emits the IOC name,
   so a naive string match scored a correct BirdNET detection as a miss (noted
   in TECHNICAL_DEBT.md). `canonical`/`same_species` resolve these via a small,
   **sourced** synonym table.

**Deliberately conservative.** Only genuine cross-checklist synonyms for species
in this study are included, each with a citation. BirdNET's *misidentifications*
of NT species (e.g. Azure Kingfisher → "Eurasian Treecreeper", Diamond Dove →
"New Zealand Bellbird") are NOT synonyms — they are wrong answers and must remain
misses. Adding an unsourced entry here would silently inflate a model's measured
accuracy, so entries require a checklist source. See docs/METHODOLOGY.md
§"Synonym handling".

Sources
-------
- Gill, F., Donsker, D., & Rasmussen, P. (Eds). *IOC World Bird List* (v14.x).
  https://www.worldbirdnames.org/ — uses "Bush Thick-knee" for *Burhinus
  grallarius*.
- BirdLife Australia, *Working List of Australian Birds* (v4). — uses
  "Bush Stone-curlew" as the Australian common name for the same species.
- Kahl, S. et al. (2021). BirdNET. *Ecological Informatics*, 61, 101236. —
  BirdNET's label set follows the eBird/Clements & IOC nomenclature.
"""

from __future__ import annotations

from dataclasses import dataclass


def normalize(name: str) -> str:
    """Lower-case and strip all non-alphanumerics, collapsing orthographic
    variants (hyphen/space/case) to a single comparison key. This alone resolves
    the label-map-vs-metadata spelling differences in this dataset."""
    return "".join(c for c in name.lower() if c.isalnum())


@dataclass(frozen=True)
class SynonymEntry:
    canonical: str          # the name used in this study (BirdLife Australia)
    synonyms: tuple[str, ...]
    source: str             # citation for the equivalence


# Curated, sourced synonym groups. Keep additions cross-checklist synonyms only,
# each with a source — never a BirdNET misidentification.
SYNONYM_GROUPS: tuple[SynonymEntry, ...] = (
    SynonymEntry(
        canonical="Bush Stone-curlew",
        synonyms=("Bush Thick-knee", "Bush Thicknee", "Southern Stone-curlew"),
        source="IOC World Bird List v14 ('Bush Thick-knee') = BirdLife Australia "
               "'Bush Stone-curlew' (Burhinus grallarius).",
    ),
)

# Build the normalized synonym → canonical lookup once.
_SYNONYM_TO_CANONICAL: dict[str, str] = {}
for _entry in SYNONYM_GROUPS:
    _SYNONYM_TO_CANONICAL[normalize(_entry.canonical)] = _entry.canonical
    for _syn in _entry.synonyms:
        _SYNONYM_TO_CANONICAL[normalize(_syn)] = _entry.canonical


def canonical(name: str | None) -> str | None:
    """Return the study-canonical common name for `name`, resolving both
    orthographic variants (via normalisation) and sourced synonyms. Names with
    no synonym entry are returned unchanged (title/spacing preserved)."""
    if not name:
        return None
    return _SYNONYM_TO_CANONICAL.get(normalize(name), name)


def same_species(a: str | None, b: str | None) -> bool:
    """True when two names refer to the same species, tolerant of orthographic
    variants and sourced synonyms. Replaces bare normalized string equality in
    the model comparison so a correct detection under a synonymous name counts
    as correct."""
    if not a or not b:
        return False
    ca, cb = canonical(a), canonical(b)
    return normalize(ca or a) == normalize(cb or b)


def synonym_provenance() -> list[dict]:
    """The synonym table as sourced records, for display/provenance and for the
    publication asset registry (D6)."""
    return [
        {"canonical": e.canonical, "synonyms": list(e.synonyms), "source": e.source}
        for e in SYNONYM_GROUPS
    ]
