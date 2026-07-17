"""Application settings (12-factor, environment-driven).

All configuration comes from the environment (prefixed BIRDDASH_) with
sensible local-dev defaults. This is the injection point for containerised
deployments and CI.
"""

from functools import lru_cache
from typing import Annotated

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="BIRDDASH_", env_file=".env", extra="ignore")

    # --- API metadata ---
    api_title: str = "Avian Observatory API"
    api_description: str = (
        "Avian Observatory — a scientific platform for acoustic bird monitoring, "
        "biodiversity assessment, and environmental intelligence in the Northern "
        "Territory. Stable, versioned interface: recordings, detections, species, "
        "sites, analyses and jobs."
    )
    environment: str = "development"          # development | staging | production

    # --- CORS (browser clients: the Avian Observatory web app) ---
    # Accepts a JSON list OR a comma-separated string (12-factor / Heroku config
    # vars are plain strings), e.g. BIRDDASH_CORS_ALLOW_ORIGINS=https://app.vercel.app
    cors_allow_origins: Annotated[list[str], NoDecode] = [
        "http://localhost:3000", "http://127.0.0.1:3000",
    ]

    # --- Database (Postgres metadata store) ---
    # Reads BIRDDASH_DATABASE_URL or the platform-standard DATABASE_URL (Heroku,
    # Render, etc.). No credentials hardcoded: libpq uses the OS user on localhost.
    database_url: str = Field(
        default="postgresql+psycopg://localhost:5432/birddash_dev",
        validation_alias=AliasChoices("BIRDDASH_DATABASE_URL", "DATABASE_URL"),
    )
    db_echo: bool = False

    @field_validator("database_url", mode="after")
    @classmethod
    def _normalise_database_url(cls, v: str) -> str:
        """Managed Postgres add-ons inject `postgres://…`; SQLAlchemy 2.0 requires
        an explicit driver. Normalise to the psycopg3 dialect the app uses."""
        if v.startswith("postgres://"):
            return "postgresql+psycopg://" + v[len("postgres://"):]
        if v.startswith("postgresql://"):          # no driver specified
            return "postgresql+psycopg://" + v[len("postgresql://"):]
        return v

    @field_validator("cors_allow_origins", mode="before")
    @classmethod
    def _split_origins(cls, v):
        """Allow a comma-separated string from an env/config var, not just JSON."""
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v

    # --- Auth (designed now, permissively stubbed until a real IdP is wired) ---
    auth_mode: str = "dev"                    # dev | oidc   (dev = permissive stub)
    default_org_slug: str = "default"

    # --- Pagination ---
    default_page_size: int = 50
    max_page_size: int = 200


@lru_cache
def get_settings() -> Settings:
    return Settings()
