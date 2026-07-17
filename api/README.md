# Platform API (FastAPI) — Phase 3a

Stable, versioned HTTP interface over the `birddash` scientific core. Metadata
lives in PostgreSQL; audio and detection artifacts are read from the filesystem
(they move into the database / object storage in Phase 6).

## Layout

```
api/
  main.py            FastAPI app, middleware, error handlers, OpenAPI
  settings.py        env-driven config (BIRDDASH_* vars)
  db.py              SQLAlchemy engine/session + Base
  models.py          ORM: Organisation, Site, Sensor, Species, Model, Recording, Analysis, Job
  schemas.py         Pydantic DTOs (the stable contract)
  errors.py          RFC 9457 Problem+JSON handling
  pagination.py      opaque cursor (keyset) pagination
  security.py        auth principal + scopes (permissive dev stub)
  seed.py            sync filesystem assets -> metadata DB
  repositories/      storage adapters (Postgres metadata; filesystem detections)
  services/          use-cases (orchestration + DTO translation)
  routers/v1/        HTTP endpoints (recordings, species, jobs, meta)
```

## First-time setup

```bash
pip install -r requirements-api.txt          # in the birdenv venv
createdb birddash_dev                         # local PostgreSQL
alembic upgrade head                          # create schema
python -m api.seed                            # load species/models/recordings
```

Override the database with `BIRDDASH_DATABASE_URL` (default:
`postgresql+psycopg://localhost:5432/birddash_dev`, connects as the OS user).

## Run

```bash
uvicorn api.main:app --reload
# docs:    http://localhost:8000/docs
# openapi: http://localhost:8000/openapi.json
```

## Auth (dev stub)

`auth_mode=dev` is permissive. Send `X-Debug-Role: researcher|agency|annotator|
sensor|integration|admin` to exercise scope enforcement. Switching to real OIDC
is a config flip plus a token validator — no endpoint changes.

## Tests

```bash
python tests/test_api.py        # or: pytest tests/test_api.py
```
Requires the dev DB migrated and seeded.
