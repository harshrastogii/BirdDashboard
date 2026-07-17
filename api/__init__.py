"""
NT Environmental Intelligence Platform — HTTP API (FastAPI).

The API is the stable, versioned interface every client uses (Next.js, mobile,
government dashboards, research tools, sensor networks, third-party
integrations). It is a thin *transport + orchestration* layer:

    routers  ->  services  ->  repositories  ->  Postgres (metadata)
                          ->   birddash (scientific core)   filesystem (artifacts)

Design principles:
  * Pydantic schemas are the contract — the API never exposes birddash's
    internal shapes (DataFrames) or filesystem paths.
  * Resources have stable opaque UUIDs, decoupled from storage, so URLs survive
    the Phase-6 filesystem -> Postgres/object-storage migration.
  * Repositories abstract storage; swapping filesystem for the database later
    does not change the contract.
"""

__version__ = "0.1.0"       # API package version (distinct from the /v1 URL major)
