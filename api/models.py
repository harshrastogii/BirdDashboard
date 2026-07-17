"""
SQLAlchemy ORM models — the Postgres metadata store.

Scope (Phase 3a, "core-first"): Organisation, Species, Model, Recording,
Analysis, Job are fully modelled. Site and Sensor exist as schema-only stubs so
their relationships and IDs are stable from day one (fleshed out in Phase 7).

Detection data and audio artifacts remain on the filesystem in Phase 3; they
migrate into their own tables / object storage in Phase 6. Recording.source_path
is the stable link to those artifacts until then.

Conventions:
  * UUID primary keys (opaque, storage-independent, migration-proof).
  * Status/type fields are strings with documented allowed values (NOT database
    enums) so they can evolve additively without fragile migrations.
  * Timestamps are timezone-aware UTC.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    ForeignKey, String, Integer, Float, DateTime, JSON, Uuid, func, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.db import Base


def _pk() -> Mapped[uuid.UUID]:
    return mapped_column(Uuid, primary_key=True, default=uuid.uuid4)


class Organisation(Base):
    """Tenant boundary. Every resource belongs to an organisation."""
    __tablename__ = "organisations"

    id: Mapped[uuid.UUID] = _pk()
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    sites: Mapped[list["Site"]] = relationship(back_populates="organisation")
    recordings: Mapped[list["Recording"]] = relationship(back_populates="organisation")


class Site(Base):
    """A monitoring location. Geometry is lat/lon now; PostGIS geometry later.

    Schema-only stub in Phase 3a (anchor for all future GIS features)."""
    __tablename__ = "sites"

    id: Mapped[uuid.UUID] = _pk()
    organisation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organisations.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    organisation: Mapped["Organisation"] = relationship(back_populates="sites")
    sensors: Mapped[list["Sensor"]] = relationship(back_populates="site")
    recordings: Mapped[list["Recording"]] = relationship(back_populates="site")


class Sensor(Base):
    """A device deployed at a site (schema-only stub in Phase 3a)."""
    __tablename__ = "sensors"

    id: Mapped[uuid.UUID] = _pk()
    site_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sites.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    site: Mapped["Site"] = relationship(back_populates="sensors")
    recordings: Mapped[list["Recording"]] = relationship(back_populates="sensor")


class Species(Base):
    """Reference taxonomy the platform recognises."""
    __tablename__ = "species"

    id: Mapped[uuid.UUID] = _pk()
    common_name: Mapped[str] = mapped_column(String(255), index=True)
    scientific_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    class_index: Mapped[int | None] = mapped_column(Integer, nullable=True, unique=True)
    conservation_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Model(Base):
    """A versioned classifier available on the platform (reproducibility)."""
    __tablename__ = "models"

    id: Mapped[uuid.UUID] = _pk()
    key: Mapped[str] = mapped_column(String(64), unique=True, index=True)  # e.g. "nt_cnn"
    name: Mapped[str] = mapped_column(String(255))
    version: Mapped[str] = mapped_column(String(32))
    kind: Mapped[str] = mapped_column(String(32))  # segment_classifier | global | sed
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    analyses: Mapped[list["Analysis"]] = relationship(back_populates="model")


class Recording(Base):
    """An audio asset. The media file lives on the filesystem (source_path)
    until Phase 6 moves it to object storage; the DB row is its stable identity."""
    __tablename__ = "recordings"

    id: Mapped[uuid.UUID] = _pk()
    organisation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organisations.id"), index=True)
    site_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("sites.id"), nullable=True, index=True)
    sensor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("sensors.id"), nullable=True, index=True)

    source_path: Mapped[str] = mapped_column(String(1024), unique=True)  # e.g. "sample_audio/Foo.mp3"
    filename: Mapped[str] = mapped_column(String(512), index=True)
    media_type: Mapped[str] = mapped_column(String(64), default="audio/mpeg")
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    captured_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Per-recording GPS. Currently NULL for all rows (the Xeno-canto download
    # captured latitude but not longitude); the coordinate provider
    # (api/services/geospatial.py) falls back to the site location and labels it
    # 'approximate' until a re-fetch populates precise coordinates here. PostGIS
    # geometry can replace these lat/lon columns when spatial queries are needed.
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    organisation: Mapped["Organisation"] = relationship(back_populates="recordings")
    site: Mapped["Site"] = relationship(back_populates="recordings")
    sensor: Mapped["Sensor"] = relationship(back_populates="recordings")
    analyses: Mapped[list["Analysis"]] = relationship(back_populates="recording")


class Analysis(Base):
    """An application of a Model to a Recording with parameters.

    The central platform abstraction: 'running a model' is a durable, queryable,
    reproducible resource rather than an RPC call. Populated in Phase 3b."""
    __tablename__ = "analyses"

    id: Mapped[uuid.UUID] = _pk()
    recording_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("recordings.id"), index=True)
    model_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("models.id"), index=True)
    type: Mapped[str] = mapped_column(String(32))  # birdnet | nt_cnn | multi_species | ...
    params: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending|running|succeeded|failed
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    recording: Mapped["Recording"] = relationship(back_populates="analyses")
    model: Mapped["Model"] = relationship(back_populates="analyses")


class Job(Base):
    """Tracks asynchronous work (uploads, analyses, batch/aggregate compute).

    A generic (result_kind, result_id) pointer links a finished job to the
    resource it produced, without coupling the job table to every result type."""
    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = _pk()
    organisation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organisations.id"), index=True)
    type: Mapped[str] = mapped_column(String(32))  # upload | analysis | ...
    status: Mapped[str] = mapped_column(String(16), default="queued")  # queued|running|succeeded|failed
    progress: Mapped[int] = mapped_column(Integer, default=0)          # 0-100
    result_kind: Mapped[str | None] = mapped_column(String(32), nullable=True)
    result_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    error: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
