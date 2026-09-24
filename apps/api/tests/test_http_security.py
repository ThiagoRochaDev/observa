import pytest

from app.core.config import Settings, get_settings, validate_production_settings
from app.core.http_security import rate_limiter


def test_security_headers_are_present(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["ratelimit-limit"]


def test_rate_limit_rejects_excess_requests(client):
    settings = get_settings()
    previous = settings.rate_limit_requests
    settings.rate_limit_requests = 2
    rate_limiter.reset()
    try:
        assert client.get("/api/health").status_code == 200
        assert client.get("/api/health").status_code == 200
        limited = client.get("/api/health")
        assert limited.status_code == 429
        assert limited.headers["retry-after"]
    finally:
        settings.rate_limit_requests = previous
        rate_limiter.reset()


def test_request_body_limit_rejects_large_payload(client):
    settings = get_settings()
    previous = settings.max_request_body_bytes
    settings.max_request_body_bytes = 8
    try:
        response = client.post("/api/demo/seed", content=b'{"large": true}')
        assert response.status_code == 413
    finally:
        settings.max_request_body_bytes = previous


def test_readiness_checks_databases(client):
    client.headers.pop("X-Observa-Api-Key", None)
    response = client.get("/readyz")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "database": {"control": "ok", "tenant": "ok"},
    }


def test_production_requires_external_secrets():
    settings = Settings(
        environment="production",
        observa_api_key=None,
        observa_secrets_key=None,
        observa_session_secret=None,
    )
    with pytest.raises(RuntimeError, match="externally managed secrets"):
        validate_production_settings(settings)


def test_production_accepts_strong_external_secrets():
    settings = Settings(
        environment="production",
        observa_api_key="a" * 32,
        observa_secrets_key="9fkP6D-M4A3kE-T2I-kHuG6zB7G3RsCM9v8Oya7DjbM=",
        observa_session_secret="b" * 32,
        cors_origins=[],
    )
    validate_production_settings(settings)
