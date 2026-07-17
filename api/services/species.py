"""Species use-cases."""

from uuid import UUID

from sqlalchemy.orm import Session

from api.errors import NotFoundError
from api.pagination import clamp_limit, decode_cursor, encode_cursor
from api.repositories import species as repo
from api.schemas import Page, SpeciesOut
from api.security import Principal


def list_species(db: Session, principal: Principal, *,
                 cursor: str | None, limit: int | None) -> Page[SpeciesOut]:
    limit = clamp_limit(limit)
    after_id = decode_cursor(cursor)
    rows = repo.list_species(db, limit=limit, after_id=after_id)
    has_more = len(rows) > limit
    rows = rows[:limit]
    next_cursor = encode_cursor(rows[-1].id) if has_more and rows else None
    return Page(items=[SpeciesOut.model_validate(r) for r in rows],
                next_cursor=next_cursor, limit=limit)


def get_species(db: Session, principal: Principal, species_id: UUID) -> SpeciesOut:
    row = repo.get_species(db, species_id)
    if row is None:
        raise NotFoundError(f"Species {species_id} not found")
    return SpeciesOut.model_validate(row)
