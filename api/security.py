"""
Authentication & authorization — fully designed, permissively stubbed.

The contract is final: every endpoint declares the scope it needs via
`require_scope(...)`, a `Principal` (org + roles + scopes) is resolved per
request, and OpenAPI advertises the security schemes. Only the *resolution* is
stubbed for now:

  * auth_mode="dev"  -> a permissive principal (all scopes), optionally shaped
    by an `X-Debug-Role` header, always scoped to the default organisation.
  * auth_mode="oidc" -> (future) validate a bearer JWT from the IdP.

Turning auth on later is a config flip + a real token validator — no endpoint
signatures change.
"""

from dataclasses import dataclass, field
from uuid import UUID

from fastapi import Depends, Header, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.db import get_db
from api.errors import ForbiddenError, UnauthorizedError
from api.models import Organisation
from api.settings import get_settings

_settings = get_settings()

# Role -> granted scopes. Extend as the platform grows.
ROLE_SCOPES: dict[str, set[str]] = {
    "admin": {"*"},
    "researcher": {"recordings:read", "detections:read", "species:read", "sites:read",
                   "analyses:read", "analyses:write", "annotations:write", "jobs:read"},
    "agency": {"recordings:read", "detections:read", "species:read", "sites:read",
               "analyses:read", "jobs:read"},
    "annotator": {"recordings:read", "detections:read", "sites:read",
                  "annotations:write", "jobs:read"},
    "sensor": {"recordings:write", "jobs:read"},
    "integration": {"recordings:read", "detections:read", "species:read", "sites:read",
                    "analyses:read"},
}


@dataclass
class Principal:
    organisation_id: UUID | None
    roles: list[str] = field(default_factory=list)
    scopes: set[str] = field(default_factory=set)

    def has_scope(self, scope: str) -> bool:
        return "*" in self.scopes or scope in self.scopes


def get_principal(
    request: Request,
    db: Session = Depends(get_db),
    x_debug_role: str | None = Header(default=None, alias="X-Debug-Role"),
) -> Principal:
    """Resolve the caller. Dev mode is permissive; oidc mode is future work."""
    if _settings.auth_mode == "dev":
        role = x_debug_role or "admin"
        scopes: set[str] = set()
        for r in role.split(","):
            scopes |= ROLE_SCOPES.get(r.strip(), set())
        if not scopes:
            scopes = {"*"}
        # In dev, every caller acts within the default organisation.
        org = db.scalars(
            select(Organisation).where(Organisation.slug == _settings.default_org_slug)
        ).first()
        return Principal(organisation_id=org.id if org else None,
                         roles=[role], scopes=scopes)

    # auth_mode == "oidc": validate bearer JWT (implemented when the IdP is wired).
    raise UnauthorizedError("OIDC authentication is not yet configured.")


def require_scope(scope: str):
    """Dependency factory: enforce that the principal holds `scope`."""
    def _dep(principal: Principal = Depends(get_principal)) -> Principal:
        if not principal.has_scope(scope):
            raise ForbiddenError(f"Missing required scope: {scope}")
        return principal
    return _dep
