"""Session tokens for OIDC mode.

Local mode (default) gates every /api route with the single shared key from
security.py. OIDC mode replaces that with a per-user session: after the
OIDC callback verifies the identity provider's id_token, we issue our own
short-lived HS256 JWT (signed with a secret generated on first boot, same
persist-next-to-data pattern as api_key/secrets.key) and hand it to the
frontend, which stores it in the exact same slot the API key used to live in
(see lib/api.ts) — every existing request already sends that value in the
X-Observa-Api-Key header, so require_api_key() just needs to also accept a
valid session token (see security.py).
"""
from __future__ import annotations

import os
import secrets
import stat
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt

from app.core.config import get_settings

ALGORITHM = "HS256"
SESSION_TTL = timedelta(days=7)
STATE_TTL = timedelta(minutes=10)


def _restrict(path) -> None:
    try:
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    except (OSError, NotImplementedError):
        pass


def get_or_create_session_secret() -> str:
    path = get_settings().session_secret_file
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        key = secrets.token_urlsafe(32)
        path.write_text(key, encoding="utf-8")
        _restrict(path)
        return key
    _restrict(path)
    return path.read_text(encoding="utf-8").strip()


def create_session_token(*, provider: str, subject: str, email: str | None, name: str | None) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "typ": "session",
        "sub": f"{provider}:{subject}",
        "provider": provider,
        "email": email,
        "name": name,
        "iat": int(now.timestamp()),
        "exp": int((now + SESSION_TTL).timestamp()),
    }
    return jwt.encode(payload, get_or_create_session_secret(), algorithm=ALGORITHM)


def verify_session_token(token: str) -> dict[str, Any] | None:
    try:
        claims = jwt.decode(token, get_or_create_session_secret(), algorithms=[ALGORITHM])
    except JWTError:
        return None
    return claims if claims.get("typ") == "session" else None


def create_state_token(*, provider: str) -> str:
    """Signed, short-lived, server-secret-only value passed as OAuth `state`
    — verified on callback so a request forged without ever hitting
    /auth/authorize first (CSRF) is rejected. No server-side storage needed:
    the token IS the state, its own signature+expiry is the check."""
    now = datetime.now(timezone.utc)
    payload = {
        "typ": "oidc_state",
        "provider": provider,
        "iat": int(now.timestamp()),
        "exp": int((now + STATE_TTL).timestamp()),
    }
    return jwt.encode(payload, get_or_create_session_secret(), algorithm=ALGORITHM)


def verify_state_token(token: str, *, provider: str) -> bool:
    try:
        claims = jwt.decode(token, get_or_create_session_secret(), algorithms=[ALGORITHM])
    except JWTError:
        return False
    return claims.get("typ") == "oidc_state" and claims.get("provider") == provider
