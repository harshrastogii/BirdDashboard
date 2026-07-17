"""
Seed the metadata database from existing filesystem assets (idempotent).

    python -m api.seed

Creates the default organisation, the species reference catalog (from the NT
label map), the model catalog, and one Recording row per audio file in
sample_audio/. Detection artifacts stay on the filesystem and are read on
demand; only metadata is seeded here.

Safe to re-run: existing rows are left untouched.
"""

import json

from sqlalchemy import select

from api.db import SessionLocal
from api.models import Model, Organisation, Recording, Site, Species
from api.settings import get_settings
from birddash import config

_settings = get_settings()

_MEDIA_TYPES = {".mp3": "audio/mpeg", ".wav": "audio/wav",
                ".flac": "audio/flac", ".ogg": "audio/ogg"}

_MODELS = [
    # Production NT model (primary throughout the platform).
    {"key": "multi_species", "name": "NT Custom Classifier (v5) · Multi-Species SED",
     "version": "5.2", "kind": "production"},
    # Comparison baseline.
    {"key": "birdnet", "name": "BirdNET v2.4 (global baseline)", "version": "2.4", "kind": "baseline"},
    # Historical research milestone — documented in Model Evolution, not operational.
    {"key": "nt_cnn", "name": "NT Custom CNN (v2/v3, superseded)", "version": "3.0",
     "kind": "historical"},
]


def _norm(s: str) -> str:
    return "".join(c for c in s.lower() if c.isalnum())


def _species_metadata() -> dict[str, tuple[str | None, str | None]]:
    """Map normalised common name -> (scientific_name, conservation_status)
    from the training dataset, used to enrich the species catalog."""
    import csv
    meta: dict[str, tuple[str | None, str | None]] = {}
    csv_path = config.BASE_DIR / "training_data" / "dataset_metadata.csv"
    if not csv_path.exists():
        return meta
    with open(csv_path) as f:
        for row in csv.DictReader(f):
            key = _norm(row.get("common_name", ""))
            if key and key not in meta:
                meta[key] = (row.get("scientific_name") or None,
                             row.get("conservation_status") or None)
    return meta

# Real Northern Territory monitoring locations (true coordinates). Recordings
# are associated to these sites as SAMPLE deployment data for the map/dashboard
# demo — the underlying audio is sourced from Xeno-canto, not field-recorded at
# these exact sites. Genuine per-recording GPS lights up once the Xeno-canto
# longitude capture is restored (see the audit notes).
_NT_SITES = [
    {"name": "Darwin — Charles Darwin NP", "latitude": -12.4239, "longitude": 130.8807},
    {"name": "Kakadu National Park", "latitude": -12.8375, "longitude": 132.8380},
    {"name": "Litchfield National Park", "latitude": -13.2333, "longitude": 130.7833},
    {"name": "Mary River National Park", "latitude": -12.9000, "longitude": 131.6500},
    {"name": "Nitmiluk (Katherine Gorge)", "latitude": -14.3167, "longitude": 132.4167},
    {"name": "Katherine", "latitude": -14.4650, "longitude": 132.2635},
    {"name": "Tennant Creek", "latitude": -19.6483, "longitude": 134.1874},
    {"name": "Alice Springs — West MacDonnell", "latitude": -23.6980, "longitude": 133.5000},
]


def seed():
    db = SessionLocal()
    created = {"org": 0, "species": 0, "models": 0, "sites": 0, "recordings": 0, "assigned": 0}
    try:
        # --- Default organisation ---
        org = db.scalars(
            select(Organisation).where(Organisation.slug == _settings.default_org_slug)
        ).first()
        if org is None:
            org = Organisation(slug=_settings.default_org_slug, name="Default Organisation")
            db.add(org)
            db.flush()
            created["org"] = 1

        # --- Species (from the NT label map, enriched from the dataset) ---
        if config.NT_LABEL_MAP_PATH.exists():
            with open(config.NT_LABEL_MAP_PATH) as f:
                label_map = json.load(f)
            meta = _species_metadata()
            by_index = {s.class_index: s for s in db.scalars(select(Species))}
            for idx_str, common in label_map.items():
                idx = int(idx_str)
                sci, status = meta.get(_norm(common), (None, None))
                sp = by_index.get(idx)
                if sp is None:
                    db.add(Species(common_name=common, class_index=idx,
                                   scientific_name=sci, conservation_status=status))
                    created["species"] += 1
                else:
                    # Enrich existing rows (idempotent update).
                    if sci and not sp.scientific_name:
                        sp.scientific_name = sci
                    if status and not sp.conservation_status:
                        sp.conservation_status = status

        # --- Model catalog (upsert so naming stays accurate) ---
        by_key = {m.key: m for m in db.scalars(select(Model))}
        for m in _MODELS:
            existing = by_key.get(m["key"])
            if existing is None:
                db.add(Model(**m))
                created["models"] += 1
            else:
                existing.name, existing.version, existing.kind = m["name"], m["version"], m["kind"]

        # --- NT monitoring sites ---
        existing_site_names = {s.name for s in db.scalars(select(Site))}
        for s in _NT_SITES:
            if s["name"] not in existing_site_names:
                db.add(Site(organisation_id=org.id, **s))
                created["sites"] += 1
        db.flush()

        # --- Recordings (metadata only) ---
        existing_paths = {r.source_path for r in db.scalars(select(Recording))}
        if config.SAMPLE_AUDIO_DIR.exists():
            for path in sorted(config.SAMPLE_AUDIO_DIR.iterdir()):
                if path.suffix.lower() not in _MEDIA_TYPES:
                    continue
                source_path = f"{config.SAMPLE_AUDIO_DIR.name}/{path.name}"
                if source_path in existing_paths:
                    continue
                db.add(Recording(
                    organisation_id=org.id,
                    source_path=source_path,
                    filename=path.name,
                    media_type=_MEDIA_TYPES[path.suffix.lower()],
                    size_bytes=path.stat().st_size,
                ))
                created["recordings"] += 1
        db.flush()

        # --- Associate unassigned recordings to sites (sample deployment data) ---
        all_sites = list(db.scalars(select(Site).order_by(Site.name)))
        if all_sites:
            unassigned = list(db.scalars(select(Recording).where(Recording.site_id.is_(None))))
            for i, rec in enumerate(unassigned):
                rec.site_id = all_sites[i % len(all_sites)].id
                created["assigned"] += 1

        db.commit()
        print("Seed complete:", created)
    finally:
        db.close()


if __name__ == "__main__":
    seed()
