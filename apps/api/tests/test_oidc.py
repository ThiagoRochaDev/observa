"""OIDC login flow, end to end, against a MOCKED identity provider (no real
Google/GitLab credentials needed — respx intercepts the discovery/token/jwks
calls). Covers the actual gap this feature closes: settings page could
already store client_id/secret/issuer, but nothing used them to log anyone
in."""
from __future__ import annotations

import base64
import time

import respx
from cryptography.hazmat.primitives.asymmetric import rsa
from httpx import Response
from jose import jwt as jose_jwt

from app.core import db
from app.core.crypto import encrypt_json

ISSUER = "https://idp.example.test"
CLIENT_ID = "observa-test-client"
CLIENT_SECRET = "s3cr3t-client-secret"


def _b64url_uint(n: int) -> str:
    length = (n.bit_length() + 7) // 8
    return base64.urlsafe_b64encode(n.to_bytes(length, "big")).decode().rstrip("=")


def _make_keypair_and_jwks():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pub = key.public_key().public_numbers()
    jwk = {
        "kty": "RSA",
        "use": "sig",
        "alg": "RS256",
        "kid": "test-key-1",
        "n": _b64url_uint(pub.n),
        "e": _b64url_uint(pub.e),
    }
    return key, {"keys": [jwk]}


def _pem(key) -> str:
    from cryptography.hazmat.primitives import serialization

    return key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()


def _configure_provider():
    db.set_setting(
        "auth",
        {
            "mode": "oidc",
            "providers": {
                "mock": {
                    "enabled": True,
                    "client_id": CLIENT_ID,
                    "client_secret_enc": encrypt_json({"v": CLIENT_SECRET}),
                    "issuer": ISSUER,
                    "redirect_uri": "http://localhost:8080/auth/callback/mock",
                }
            },
        },
    )


def _discovery():
    return {
        "issuer": ISSUER,
        "authorization_endpoint": f"{ISSUER}/authorize",
        "token_endpoint": f"{ISSUER}/token",
        "jwks_uri": f"{ISSUER}/jwks",
    }


def test_auth_mode_is_public_and_reflects_settings(client):
    # Deliberately unauthenticated — no X-Observa-Api-Key header.
    from fastapi.testclient import TestClient
    from app.main import app

    anon = TestClient(app)
    r = anon.get("/auth/mode")
    assert r.status_code == 200
    body = r.json()
    assert body["mode"] == "local"  # nothing configured yet

    _configure_provider()
    r = anon.get("/auth/mode")
    assert r.json() == {"mode": "oidc", "providers": ["mock"]}


def test_full_login_flow_against_mocked_idp(client):
    from fastapi.testclient import TestClient
    from app.main import app

    anon = TestClient(app)
    _configure_provider()

    # 1) /auth/authorize redirects straight to the (mocked) provider, with a
    #    signed state token nobody but this server could have produced.
    with respx.mock(assert_all_called=True) as mock:
        mock.get(f"{ISSUER}/.well-known/openid-configuration").mock(
            return_value=Response(200, json=_discovery())
        )
        r = anon.get("/auth/authorize/mock", follow_redirects=False)
    assert r.status_code in (302, 307)
    location = r.headers["location"]
    assert location.startswith(f"{ISSUER}/authorize?")
    assert f"client_id={CLIENT_ID}" in location
    state = location.split("state=")[1].split("&")[0]

    # 2) Provider redirects the browser back to /auth/callback?code=&state=.
    #    Mock the token exchange + jwks fetch it'll make server-side.
    key, jwks = _make_keypair_and_jwks()
    now = int(time.time())
    id_token = jose_jwt.encode(
        {
            "iss": ISSUER,
            "aud": CLIENT_ID,
            "sub": "user-42",
            "email": "dev@example.test",
            "name": "Dev Example",
            "iat": now,
            "exp": now + 300,
        },
        _pem(key),
        algorithm="RS256",
        headers={"kid": "test-key-1"},
    )

    # Discovery isn't re-fetched here — oidc.discover() caches per-issuer for
    # an hour, and step 1 above already warmed it for this ISSUER.
    with respx.mock(assert_all_called=True) as mock:
        mock.post(f"{ISSUER}/token").mock(
            return_value=Response(200, json={"id_token": id_token, "access_token": "irrelevant"})
        )
        mock.get(f"{ISSUER}/jwks").mock(return_value=Response(200, json=jwks))

        r = anon.get(
            f"/auth/callback/mock?code=fake-code&state={state}",
            follow_redirects=False,
        )

    assert r.status_code in (302, 307)
    location = r.headers["location"]
    assert location.startswith("http://localhost:3000/auth/callback#token=")
    token = location.split("#token=")[1]

    # 3) The session token works exactly where the shared API key used to —
    #    same header, same gated routes.
    r = anon.get("/api/health", headers={"X-Observa-Api-Key": token})
    assert r.status_code == 200

    r = anon.get("/api/auth/me", headers={"X-Observa-Api-Key": token})
    assert r.status_code == 200
    assert r.json() == {"mode": "oidc", "provider": "mock", "email": "dev@example.test", "name": "Dev Example"}


def test_callback_rejects_forged_state(client):
    from fastapi.testclient import TestClient
    from app.main import app

    anon = TestClient(app)
    _configure_provider()

    r = anon.get("/auth/callback/mock?code=fake&state=not-a-real-state", follow_redirects=False)
    assert r.status_code in (302, 307)
    assert "error=invalid_state" in r.headers["location"]


def test_gated_routes_still_reject_garbage_token(client):
    from fastapi.testclient import TestClient
    from app.main import app

    anon = TestClient(app)
    r = anon.get("/api/health", headers={"X-Observa-Api-Key": "not-a-real-key-or-token"})
    assert r.status_code == 401
