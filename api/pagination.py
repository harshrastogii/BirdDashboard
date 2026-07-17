"""
Cursor pagination helpers.

Keyset pagination on the primary key (UUID) with an opaque base64 cursor.
Chosen over offset pagination so it stays correct and performant as tables
grow (Phase 6+). The cursor is deliberately opaque so its encoding can change
without breaking clients.
"""

import base64
from uuid import UUID

from api.settings import get_settings

_settings = get_settings()


def clamp_limit(limit: int | None) -> int:
    if limit is None:
        return _settings.default_page_size
    return max(1, min(limit, _settings.max_page_size))


def encode_cursor(last_id: UUID) -> str:
    return base64.urlsafe_b64encode(str(last_id).encode()).decode()


def decode_cursor(cursor: str | None) -> UUID | None:
    if not cursor:
        return None
    try:
        return UUID(base64.urlsafe_b64decode(cursor.encode()).decode())
    except Exception:  # noqa: BLE001 — malformed cursor -> treat as no cursor
        return None
