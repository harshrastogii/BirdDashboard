"""
Environmental-intelligence boundary — inert scaffold (Phase 7 · C4).

This is the seam DECISIONS.md D-21 requires: environmental context (fire, weather,
vegetation, protected areas, hydrology, …) is a **decoupled** concern that Avian
Observatory *consumes* through a stable service + API boundary, sourced from open
data first and from **TerraIQ** (a separate engine) later — with no frontend change
when the source is swapped.

Today it is deliberately **inert**: no environmental data is fetched or computed.
The `EnvironmentalProvider` protocol defines the contract; `NullProvider` returns
`available=false` so the UI can render a truthful "coming soon" state and toggles
without any backend commitment. A real provider (open-data adapters or a TerraIQ
client) is dropped in later behind `get_provider()` — routers and DTOs stay put.

The catalogue below names the Stage-2 layers (ROADMAP.md) purely as *intended*
scope, each flagged `available=false`; it is metadata, not data.
"""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from api.schemas import (
    EnvironmentalContextOut, EnvironmentalLayer, EnvironmentalLayersOut,
)

# Intended Stage-2 environmental layers (metadata only — none available yet).
PLANNED_LAYERS: list[dict] = [
    {"key": "fire_history", "name": "Fire history", "category": "fire", "planned_source": "NAFI (North Australia & Rangelands Fire Information)"},
    {"key": "land_cover", "name": "Land cover", "category": "vegetation", "planned_source": "DEA Land Cover"},
    {"key": "protected_areas", "name": "Protected areas", "category": "protected", "planned_source": "CAPAD"},
    {"key": "indigenous_protected_areas", "name": "Indigenous Protected Areas", "category": "protected", "planned_source": "NIAA IPA dataset"},
    {"key": "hydrology", "name": "Hydrology", "category": "hydrology", "planned_source": "Geoscience Australia Surface Hydrology"},
    {"key": "elevation", "name": "Elevation", "category": "terrain", "planned_source": "Geoscience Australia DEM"},
    {"key": "weather", "name": "Weather (current + historical)", "category": "weather", "planned_source": "BoM / TerraIQ"},
]


class EnvironmentalProvider(Protocol):
    """Contract a future environmental source (open-data adapter or TerraIQ
    client) implements. Kept minimal so the boundary is easy to satisfy."""

    name: str

    def layers(self) -> EnvironmentalLayersOut: ...

    def context_for_site(self, site_id: UUID) -> EnvironmentalContextOut: ...


class NullProvider:
    """The current provider: advertises the intended layers as unavailable and
    supplies no context. Swapping this out is the whole Stage-2 integration."""

    name = "none"

    def layers(self) -> EnvironmentalLayersOut:
        return EnvironmentalLayersOut(
            available=False,
            provider=self.name,
            note="Environmental layers are not yet available. This boundary exists so "
                 "Stage-2 sources (open data, then TerraIQ) can be added without any "
                 "frontend change (DECISIONS.md D-21).",
            layers=[EnvironmentalLayer(available=False, **layer) for layer in PLANNED_LAYERS],
        )

    def context_for_site(self, site_id: UUID) -> EnvironmentalContextOut:
        return EnvironmentalContextOut(
            available=False,
            provider=self.name,
            note="No environmental provider is wired yet. When one is, this returns "
                 "fire/weather/vegetation/etc. context for the site with no API change.",
            site_id=site_id,
            context={},
        )


def get_provider() -> EnvironmentalProvider:
    """Return the active environmental provider. The single place a real
    provider (open-data or TerraIQ) is introduced later."""
    return NullProvider()


def layers() -> EnvironmentalLayersOut:
    return get_provider().layers()


def context_for_site(site_id: UUID) -> EnvironmentalContextOut:
    return get_provider().context_for_site(site_id)
