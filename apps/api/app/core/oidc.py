"""OIDC login flow (authorization code) for GitLab/Google — everything the
settings page already stored (client_id/client_secret/issuer/redirect_uri,
see presentation/api/router.py auth/settings) but never wired to an actual
login. Talks to the provider directly (discovery + JWKS), no third-party
OIDC library — the moving pieces are small enough that a dependency would
buy little.
"""
from __future__ import annotations

import time
from typing import Any
from urllib.parse import urlencode

import httpx
from jose import jwt as jose_jwt
from jose.exceptions import JOSEError

from app.core import db
from app.core.crypto import decrypt_json

_DISCOVERY_CACHE: dict[str, tuple[float, dict]] = {}
_DISCOVERY_TTL_SECONDS = 3600


class OidcError(Exception):
    """Any failure in the login flow — always mapped to a user-safe 400 by
    the router, never leaks provider internals to the browser."""


def client_secret_of(provider_cfg: dict) -> str | None:
    """Decrypt a provider's client_secret for internal use (token exchange).
    Never returned over HTTP — see router.py's get_auth_settings, which
    only ever echoes a has_client_secret boolean."""
    enc = provider_cfg.get("client_secret_enc")
    if not enc:
        return None
    return decrypt_json(enc).get("v")


def get_provider_config(provider: str) -> dict[str, Any]:
    auth = db.get_setting("auth") or {}
    cfg = (auth.get("providers") or {}).get(provider)
    if not cfg or not cfg.get("enabled"):
        raise OidcError(f"Provider '{provider}' is not configured or not enabled.")
    if not cfg.get("client_id") or not cfg.get("issuer"):
        raise OidcError(f"Provider '{provider}' is missing client_id/issuer.")
    return cfg


async def discover(issuer: str) -> dict[str, Any]:
    cached = _DISCOVERY_CACHE.get(issuer)
    if cached and (time.monotonic() - cached[0]) < _DISCOVERY_TTL_SECONDS:
        return cached[1]
    url = issuer.rstrip("/") + "/.well-known/openid-configuration"
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url)
    if resp.status_code != 200:
        raise OidcError(f"OIDC discovery failed for {issuer} ({resp.status_code}).")
    doc = resp.json()
    _DISCOVERY_CACHE[issuer] = (time.monotonic(), doc)
    return doc


async def build_authorize_url(provider: str, *, redirect_uri: str, state: str) -> str:
    cfg = get_provider_config(provider)
    discovery = await discover(cfg["issuer"])
    params = {
        "response_type": "code",
        "client_id": cfg["client_id"],
        "redirect_uri": redirect_uri,
        "scope": "openid email profile",
        "state": state,
    }
    return f"{discovery['authorization_endpoint']}?{urlencode(params)}"


async def complete_login(provider: str, *, code: str, redirect_uri: str) -> dict[str, Any]:
    """Exchanges the code, verifies the id_token, returns the claims to base
    the Observa session on (`sub`, `email`, `name`)."""
    cfg = get_provider_config(provider)
    client_secret = client_secret_of(cfg)
    if not client_secret:
        raise OidcError(f"Provider '{provider}' has no client_secret configured.")
    discovery = await discover(cfg["issuer"])

    async with httpx.AsyncClient(timeout=10) as client:
        token_resp = await client.post(
            discovery["token_endpoint"],
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": cfg["client_id"],
                "client_secret": client_secret,
            },
            headers={"Accept": "application/json"},
        )
        if token_resp.status_code != 200:
            raise OidcError(f"Token exchange failed ({token_resp.status_code}): {token_resp.text[:200]}")
        tokens = token_resp.json()
        id_token = tokens.get("id_token")
        if not id_token:
            raise OidcError("Provider response had no id_token.")

        jwks_resp = await client.get(discovery["jwks_uri"])
        if jwks_resp.status_code != 200:
            raise OidcError("Failed to fetch the provider's signing keys (jwks_uri).")
        jwks = jwks_resp.json()

    try:
        claims = jose_jwt.decode(
            id_token,
            jwks,
            algorithms=["RS256"],
            audience=cfg["client_id"],
            issuer=discovery.get("issuer", cfg["issuer"]),
        )
    except JOSEError as exc:
        raise OidcError(f"id_token failed verification: {exc}") from exc

    if not claims.get("sub"):
        raise OidcError("id_token has no 'sub' claim.")
    return claims
