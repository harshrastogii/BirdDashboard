# Process definitions.
#
# The production deploy uses the Container Stack (see heroku.yml), which defines
# its own `run`/`release`; Heroku ignores this Procfile for container apps. It is
# kept as the process contract and for the classic buildpack path, and mirrors
# heroku.yml exactly:
#   web     — the API bound to Heroku's $PORT (single uvicorn process; see Dockerfile).
#   release — idempotent DB migration + metadata seed on each deploy.
web: uvicorn api.main:app --host 0.0.0.0 --port $PORT
release: alembic upgrade head && python -m api.seed
