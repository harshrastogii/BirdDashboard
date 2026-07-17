"""
Error handling — RFC 9457 Problem Details (application/problem+json).

Domain code raises the typed exceptions here; the service/router layers never
build HTTP responses by hand. `register_exception_handlers` maps everything —
domain errors, validation errors, unhandled exceptions — to a consistent
Problem envelope with a stable machine-readable `code` and a request id.
"""

import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

PROBLEM_MEDIA_TYPE = "application/problem+json"
_ERROR_BASE = "https://api.ntbirds.example/errors/"


class APIError(Exception):
    """Base domain error carrying an HTTP status and a stable code."""
    status = 500
    code = "INTERNAL_ERROR"
    title = "Internal Server Error"

    def __init__(self, detail: str | None = None):
        self.detail = detail
        super().__init__(detail or self.title)


class NotFoundError(APIError):
    status = 404
    code = "NOT_FOUND"
    title = "Resource Not Found"


class ValidationError(APIError):
    status = 422
    code = "VALIDATION_ERROR"
    title = "Validation Error"


class ConflictError(APIError):
    status = 409
    code = "CONFLICT"
    title = "Conflict"


class UnauthorizedError(APIError):
    status = 401
    code = "UNAUTHORIZED"
    title = "Unauthorized"


class ForbiddenError(APIError):
    status = 403
    code = "FORBIDDEN"
    title = "Forbidden"


def _problem(request: Request, *, status: int, title: str, code: str,
             detail: str | None = None, errors=None) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None) or str(uuid.uuid4())
    body = {
        "type": _ERROR_BASE + code.lower(),
        "title": title,
        "status": status,
        "detail": detail,
        "instance": str(request.url.path),
        "code": code,
        "request_id": request_id,
    }
    if errors:
        body["errors"] = errors
    return JSONResponse(status_code=status, content=body, media_type=PROBLEM_MEDIA_TYPE)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(APIError)
    async def _handle_api_error(request: Request, exc: APIError):
        return _problem(request, status=exc.status, title=exc.title,
                        code=exc.code, detail=exc.detail)

    @app.exception_handler(RequestValidationError)
    async def _handle_validation(request: Request, exc: RequestValidationError):
        errors = [{"field": ".".join(str(p) for p in e["loc"][1:]) or e["loc"][0],
                   "message": e["msg"]} for e in exc.errors()]
        return _problem(request, status=422, title="Validation Error",
                        code="VALIDATION_ERROR", detail="Request validation failed",
                        errors=errors)

    @app.exception_handler(StarletteHTTPException)
    async def _handle_http(request: Request, exc: StarletteHTTPException):
        return _problem(request, status=exc.status_code,
                        title=str(exc.detail) if exc.detail else "HTTP Error",
                        code=f"HTTP_{exc.status_code}", detail=str(exc.detail))

    @app.exception_handler(Exception)
    async def _handle_unexpected(request: Request, exc: Exception):
        return _problem(request, status=500, title="Internal Server Error",
                        code="INTERNAL_ERROR",
                        detail="An unexpected error occurred.")
