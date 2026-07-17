"""Species reference-catalog repository (Postgres)."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from api.models import Species


def list_species(db: Session, *, limit: int = 50, after_id: UUID | None = None) -> list[Species]:
    # Ordered alphabetically by common name (the whole 24-species catalog fits
    # in a single page, so keyset pagination is a formality here).
    stmt = select(Species)
    if after_id is not None:
        stmt = stmt.where(Species.id > after_id)
    stmt = stmt.order_by(Species.common_name).limit(limit + 1)
    return list(db.scalars(stmt))


def get_species(db: Session, species_id: UUID) -> Species | None:
    return db.scalars(select(Species).where(Species.id == species_id)).first()
