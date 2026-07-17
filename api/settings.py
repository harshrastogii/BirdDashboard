"""Application settings (12-factor, environment-driven).

All configuration comes from the environment (prefixed BIRDDASH_) with
sensible local-dev defaults. This is the injection point for containerised
deployments and CI.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


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
    cors_allow_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # --- Database (Postgres metadata store) ---
    # No credentials hardcoded: libpq uses the OS user by default on localhost.
    database_url: str = "postgresql+psycopg://localhost:5432/birddash_dev"
    db_echo: bool = False

    # --- Auth (designed now, permissively stubbed until a real IdP is wired) ---
    auth_mode: str = "dev"                    # dev | oidc   (dev = permissive stub)
    default_org_slug: str = "default"

    # --- Pagination ---
    default_page_size: int = 50
    max_page_size: int = 200


@lru_cache
def get_settings() -> Settings:
    return Settings()
