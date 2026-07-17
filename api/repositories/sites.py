"""Site metadata repository (Postgres), with recording counts for the map."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.models import Recording, Site


def list_sites(db: Session, organisation_id: UUID) -> list[tuple[Site, int]]:
    """Return (site, recording_count) for the organisation, ordered by name."""
    stmt = (
        select(Site, func.count(Recording.id))
        .outerjoin(Recording, Recording.site_id == Site.id)
        .where(Site.organisation_id == organisation_id)
        .group_by(Site.id)
        .order_by(Site.name)
    )
    return [(site, count) for site, count in db.execute(stmt)]


def get_site(db: Session, organisation_id: UUID, site_id: UUID) -> tuple[Site, int] | None:
    stmt = (
        select(Site, func.count(Recording.id))
        .outerjoin(Recording, Recording.site_id == Site.id)
        .where(Site.id == site_id, Site.organisation_id == organisation_id)
        .group_by(Site.id)
    )
    row = db.execute(stmt).first()
    return (row[0], row[1]) if row else None
