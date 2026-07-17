"""Biodiversity diversity indices.

Pure functions over a {species: count} mapping. No I/O, no framework deps.
"""

import math
from typing import Mapping


def shannon_index(species_counts: Mapping[str, int]) -> float:
    """Shannon diversity index H' = -sum(pi * ln(pi))."""
    total = sum(species_counts.values())
    if total == 0:
        return 0
    h = 0
    for count in species_counts.values():
        if count > 0:
            pi = count / total
            h -= pi * math.log(pi)
    return h


def simpson_index(species_counts: Mapping[str, int]) -> float:
    """Simpson's diversity index D = 1 - sum(pi^2)."""
    total = sum(species_counts.values())
    if total == 0:
        return 0
    d = 0
    for count in species_counts.values():
        pi = count / total
        d += pi ** 2
    return 1 - d
