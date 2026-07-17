"""Database engine, session management, and the declarative Base.

SQLAlchemy 2.0 style. The session is provided to routers via FastAPI
dependency injection (`get_db`).
"""

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from api.settings import get_settings

_settings = get_settings()

engine = create_engine(
    _settings.database_url,
    echo=_settings.db_echo,
    pool_pre_ping=True,          # survive dropped connections in long-lived deployments
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


def get_db() -> Iterator[Session]:
    """FastAPI dependency yielding a request-scoped session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
