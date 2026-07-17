"""Site use-cases (powers the interactive map)."""

from uuid import UUID

from sqlalchemy.orm import Session

from api.errors import NotFoundError
from api.models import Site
from api.repositories import sites as repo
from api.schemas import SiteOut
from api.security import Principal


def _to_dto(site: Site, recording_count: int) -> SiteOut:
    return SiteOut(
        id=site.id,
        organisation_id=site.organisation_id,
        name=site.name,
        latitude=site.latitude,
        longitude=site.longitude,
        recording_count=recording_count,
    )


def list_sites(db: Session, principal: Principal) -> list[SiteOut]:
    return [_to_dto(s, c) for s, c in repo.list_sites(db, principal.organisation_id)]


def get_site(db: Session, principal: Principal, site_id: UUID) -> SiteOut:
    row = repo.get_site(db, principal.organisation_id, site_id)
    if row is None:
        raise NotFoundError(f"Site {site_id} not found")
    return _to_dto(*row)
