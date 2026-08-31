"""API-key gate for the whole /api surface.

Observa v0.1.0 ships with no OIDC login yet (that flow is tracked
separately, see settings/auth). Until then, every /api route holds
real power over cloud credentials (create/edit/delete connections,
change auth settings) — so it must not be reachable with zero
authentication. This is the interim "local mode" guard: a random
token generated on first boot, persisted next to secrets.key, and
required on every request via the X-Observa-Api-Key header (or
`Authorization: Bearer <key>`).
"""

from __future__ import annotations

import os
import secrets
import stat

from fastapi import Header, HTTPException

from app.core.config import get_settings


def _restrict(path) -> None:
    """Best-effort chmod 0600 — no-op on platforms without POSIX perms (Windows)."""
    try:
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    except (OSError, NotImplementedError):
        pass


def get_or_create_api_key() -> str:
    path = get_settings().api_key_file
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        key = secrets.token_urlsafe(32)
        path.write_text(key, encoding="utf-8")
        _restrict(path)
        print(
            "[observa] Generated API key (required on every /api request):\n"
            f"[observa]   {key}\n"
            f"[observa] Persisted at {path} — also read it any time from there.",
        )
        return key
    _restrict(path)
    return path.read_text(encoding="utf-8").strip()


def require_api_key(
    x_observa_api_key: str | None = Header(default=None, alias="X-Observa-Api-Key"),
    authorization: str | None = Header(default=None),
) -> None:
    expected = get_or_create_api_key()
    provided = x_observa_api_key
    if not provided and authorization and authorization.lower().startswith("bearer "):
        provided = authorization[7:]
    if not provided or not secrets.compare_digest(provided, expected):
        raise HTTPException(status_code=401, detail="Missing or invalid API key")
