"""
Geospatial use-cases — the coordinate-provider abstraction (Phase 7 · C).

The single seam through which the platform resolves *where* a recording is. Today
per-recording GPS is unavailable (the Xeno-canto download captured latitude but
not longitude), so a recording's location falls back to its monitoring site and is
labelled **approximate**. When real per-recording coordinates are recovered (a
Xeno-canto re-fetch populating `Recording.latitude/longitude`), this provider
returns them as **precise** with NO change required in any caller, the map DTOs,
or the frontend — the abstraction is what lets real geo "slot in naturally later".

Nothing here fabricates coordinates: an approximate point is explicitly the site's
location, flagged as such, so the UI can distinguish real from approximate.

PostGIS note: `Site`/`Recording` use plain lat/lon columns today. When spatial
queries (bbox/temporal joins, environmental-layer overlays) are needed, these
become PostGIS geometry columns behind this same service — see ARCHITECTURE.md §6.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from api.models import Recording, Site
from api.schemas import MapSiteOut, MapSitesOut
from api.security import Principal
from birddash import config, taxonomy
from birddash import results as results_repo

# Coordinate precision levels (also the contract value in DTOs).
PRECISE = "precise"          # real per-recording GPS
APPROXIMATE = "approximate"  # falls back to the site location
UNKNOWN = "unknown"          # no location available


@dataclass(frozen=True)
class Location:
    latitude: float | None
    longitude: float | None
    precision: str            # PRECISE | APPROXIMATE | UNKNOWN
    source: str               # recording_gps | site_association | none


def resolve_location(rec: Recording, site: Site | None) -> Location:
    """Resolve a recording's location, preferring precise per-recording GPS and
    falling back to the site (approximate). The ONE place location is decided."""
    if rec.latitude is not None and rec.longitude is not None:
        return Location(rec.latitude, rec.longitude, PRECISE, "recording_gps")
    if site is not None and site.latitude is not None and site.longitude is not None:
        return Location(site.latitude, site.longitude, APPROXIMATE, "site_association")
    return Location(None, None, UNKNOWN, "none")


def _pretty(file_path: str) -> str:
    base = file_path.rsplit("/", 1)[-1]
    return base.replace(".mp3", "").replace(".wav", "").replace("_", " ")


def map_sites(
    db: Session,
    principal: Principal,
    *,
    min_confidence: float,
    species: str | None = None,
) -> MapSitesOut:
    """Sites for the interactive map, each with the species detected there (from
    BirdNET results at `min_confidence`) so the map can be filtered by species and
    by confidence. When `species` is given, sites are flagged `matched` when that
    species (synonym-aware) is present; non-matching sites are still returned so
    the frontend can dim rather than drop them.

    Locations are the site coordinates (precision = approximate) until precise
    per-recording GPS exists; the `coordinate_precision` field says which."""
    # source_path -> set(species) at/above the threshold
    df = results_repo.load_results(config.BIRDNET_RESULTS_DIR)
    species_by_path: dict[str, set[str]] = {}
    if not df.empty:
        df = df[df["Confidence"] >= min_confidence]
        for file_path, group in df.groupby("File"):
            species_by_path[file_path] = set(group["Common name"].astype(str))

    # recordings for this org, grouped by site
    recs = list(db.scalars(
        select(Recording).where(Recording.organisation_id == principal.organisation_id)
    ))
    species_by_site: dict[object, set[str]] = {}
    count_by_site: dict[object, int] = {}
    for r in recs:
        if r.site_id is None:
            continue
        count_by_site[r.site_id] = count_by_site.get(r.site_id, 0) + 1
        found = species_by_path.get(r.source_path)
        if found:
            species_by_site.setdefault(r.site_id, set()).update(found)

    sites = list(db.scalars(
        select(Site).where(Site.organisation_id == principal.organisation_id).order_by(Site.name)
    ))

    out: list[MapSiteOut] = []
    for s in sites:
        sp = sorted(species_by_site.get(s.id, set()))
        matched = species is None or any(taxonomy.same_species(x, species) for x in sp)
        # Site-level location: approximate unless (future) precise site geometry.
        precision = APPROXIMATE if (s.latitude is not None and s.longitude is not None) else UNKNOWN
        out.append(MapSiteOut(
            id=s.id, name=s.name, latitude=s.latitude, longitude=s.longitude,
            coordinate_precision=precision, coordinate_source="site_association",
            recording_count=count_by_site.get(s.id, 0),
            species_present=sp, matched=matched,
        ))

    return MapSitesOut(
        min_confidence=min_confidence,
        species_filter=species,
        coordinate_precision_note=(
            "Site-level approximate locations. Per-recording GPS is unavailable "
            "(longitude missing from the source download); precise points will "
            "appear automatically once recovered."
        ),
        sites=out,
    )
