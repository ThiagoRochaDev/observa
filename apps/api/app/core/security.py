"""Auth gate for the whole /api surface.

Two modes (see settings/auth, app/presentation/api/router.py):
  - local (default): a single shared token generated on first boot,
    persisted next to secrets.key, required on every request via the
    X-Observa-Api-Key header (or `Authorization: Bearer <key>`). Good
    enough for one operator on their own laptop.
  - oidc: real per-user login (Google/GitLab) — see core/oidc.py and
    presentation/api/auth_flow_router.py for the login flow. The frontend
    stores the resulting session token in the SAME header slot the shared
    key used to occupy, so this gate accepts either value: a match against
    the static key, OR a validly-signed, unexpired session token. Mode
    doesn't have to be all-or-nothing at the gate level — this just means
    an operator mid-migration (key still valid, users starting to log in
    via OIDC) doesn't get locked out either way.
"""

from __future__ import annotations

import os
import secrets
import stat

from fastapi import Header, HTTPException

from app.core.config import get_settings
from app.core.session import verify_session_token


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
    provided = x_observa_api_key
    if not provided and authorization and authorization.lower().startswith("bearer "):
        provided = authorization[7:]
    if not provided:
        raise HTTPException(status_code=401, detail="Missing or invalid API key")

    expected = get_or_create_api_key()
    if secrets.compare_digest(provided, expected):
        return
    if verify_session_token(provided) is not None:
        return
    raise HTTPException(status_code=401, detail="Missing or invalid API key")
