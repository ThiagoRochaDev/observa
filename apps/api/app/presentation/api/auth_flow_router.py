"""OIDC login flow — deliberately OUTSIDE the api-key-gated router (a
browser hits these before it has any credential at all: the whole point is
to hand it one). CSRF is covered by the signed `state` token (see
core/session.py), not by requiring the caller to already be authenticated.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse

from app.core import db, oidc, session
from app.core.config import get_settings

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/mode")
def auth_mode():
    """Public: lets the frontend's login gate decide what to render (paste-a-key
    form vs "Continue with Google/GitLab" buttons) before it has any credential."""
    auth = db.get_setting("auth") or {"mode": "local", "providers": {}}
    enabled = [
        key for key, cfg in (auth.get("providers") or {}).items()
        if cfg.get("enabled") and cfg.get("client_id")
    ]
    return {"mode": auth.get("mode", "local"), "providers": enabled}


@router.get("/authorize/{provider}")
async def authorize(provider: str):
    auth = db.get_setting("auth") or {}
    cfg = (auth.get("providers") or {}).get(provider) or {}
    redirect_uri = cfg.get("redirect_uri") or f"http://localhost:8080/auth/callback/{provider}"
    try:
        state = session.create_state_token(provider=provider)
        url = await oidc.build_authorize_url(provider, redirect_uri=redirect_uri, state=state)
    except oidc.OidcError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return RedirectResponse(url)


@router.get("/callback/{provider}")
async def callback(
    provider: str,
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
):
    frontend = get_settings().frontend_url.rstrip("/")
    if error:
        return RedirectResponse(f"{frontend}/auth/callback?error={error}")
    if not code or not state or not session.verify_state_token(state, provider=provider):
        return RedirectResponse(f"{frontend}/auth/callback?error=invalid_state")

    auth = db.get_setting("auth") or {}
    cfg = (auth.get("providers") or {}).get(provider) or {}
    redirect_uri = cfg.get("redirect_uri") or f"http://localhost:8080/auth/callback/{provider}"

    try:
        claims = await oidc.complete_login(provider, code=code, redirect_uri=redirect_uri)
    except oidc.OidcError:
        # Provider/network detail stays server-side (logs) — the browser only
        # learns that login failed, not why (avoids leaking config internals).
        return RedirectResponse(f"{frontend}/auth/callback?error=login_failed")

    token = session.create_session_token(
        provider=provider,
        subject=claims["sub"],
        email=claims.get("email"),
        name=claims.get("name"),
    )
    return RedirectResponse(f"{frontend}/auth/callback#token={token}")
