"""
FastAPI application entry point.

    uvicorn api.main:app --reload

Assembles the app: request-id middleware, RFC 9457 error handlers, the
versioned router, and OpenAPI security-scheme documentation (bearer + API key,
advertised now, enforced when auth_mode flips to "oidc").
"""

import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from api import __version__
from api.errors import register_exception_handlers
from api.routers.v1 import router as v1_router
from api.settings import get_settings

_settings = get_settings()

app = FastAPI(
    title=_settings.api_title,
    description=_settings.api_description,
    version=__version__,
    openapi_tags=[
        {"name": "meta", "description": "Health, readiness, version."},
        {"name": "recordings", "description": "Audio recordings, media, detections."},
        {"name": "species", "description": "Reference species catalog."},
        {"name": "jobs", "description": "Asynchronous work tracking."},
    ],
)

register_exception_handlers(app)

# Allow the Avian Observatory web app (browser) to call the API in dev.
app.add_middleware(
    CORSMiddleware,
    allow_origins=_settings.cors_allow_origins,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Attach a correlation id to every request/response (echoed in errors)."""
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


app.include_router(v1_router)


@app.get("/", include_in_schema=False)
def root() -> dict:
    return {"service": _settings.api_title, "version": __version__, "docs": "/docs"}


# --- OpenAPI security schemes (documented now; enforced later) ------------
def _custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    from fastapi.openapi.utils import get_openapi

    schema = get_openapi(
        title=app.title, version=app.version,
        description=app.description, routes=app.routes, tags=app.openapi_tags,
    )
    schema.setdefault("components", {})["securitySchemes"] = {
        "oidcBearer": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT",
                       "description": "OIDC access token (human users)."},
        "apiKey": {"type": "apiKey", "in": "header", "name": "X-API-Key",
                   "description": "API key for sensors and third-party integrations."},
    }
    app.openapi_schema = schema
    return schema


app.openapi = _custom_openapi
