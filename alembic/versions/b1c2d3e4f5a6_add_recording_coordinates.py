"""add recording coordinates (per-recording geo, nullable)

Phase 7 · Workstream C (GIS foundation). Adds nullable per-recording latitude /
longitude columns so the coordinate-provider abstraction (api/services/geospatial.py)
can return PRECISE per-recording locations when they are recovered (the Xeno-canto
re-fetch for the missing longitude). Until then these stay NULL and the provider
falls back to the recording's site location (labelled 'approximate'). No data is
fabricated by this migration — the columns are simply an empty home for real GPS.

Revision ID: b1c2d3e4f5a6
Revises: 148afca23aa2
Create Date: 2026-07-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b1c2d3e4f5a6'
down_revision: Union[str, None] = '148afca23aa2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('recordings', sa.Column('latitude', sa.Float(), nullable=True))
    op.add_column('recordings', sa.Column('longitude', sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column('recordings', 'longitude')
    op.drop_column('recordings', 'latitude')
