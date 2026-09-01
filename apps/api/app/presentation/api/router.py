from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field

from app.application import sync_service
from app.core import db
from app.core.crypto import encrypt_json
from app.core.security import require_api_key
from app.core.session import verify_session_token

router = APIRouter(dependencies=[Depends(require_api_key)])


class AuthSettingsUpdate(BaseModel):
    mode: str = Field(description="local | oidc")
    providers: dict[str, Any] = Field(default_factory=dict)


class ConnectionCreate(BaseModel):
    name: str
    connector_id: str
    config: dict[str, Any] = Field(default_factory=dict)
    secrets: dict[str, Any] = Field(default_factory=dict)


class ConnectionUpdate(BaseModel):
    name: str | None = None
    config: dict[str, Any] | None = None
    secrets: dict[str, Any] | None = None
    enabled: bool | None = None


class TestConnectionBody(BaseModel):
    connector_id: str
    config: dict[str, Any] = Field(default_factory=dict)
    secrets: dict[str, Any] = Field(default_factory=dict)


@router.get("/health")
def health():
    summary = db.cost_summary(30)
    obs = db.observability_overview()
    return {
        "status": "ok",
        "app": "observa",
        "connections": len(db.list_connections()),
        "cost_records": summary["records"],
        "open_alerts": summary.get("open_alerts", 0),
        "metric_series": obs.get("metric_count", 0),
        "auth_mode": (db.get_setting("auth") or {}).get("mode", "local"),
        "demo": True,
    }


@router.post("/demo/seed")
def seed_demo():
    return sync_service.ensure_full_demo()


@router.get("/auth/me")
def auth_me(
    x_observa_api_key: str | None = Header(default=None, alias="X-Observa-Api-Key"),
    authorization: str | None = Header(default=None),
):
    """Who the caller is — a real identity if they're on an OIDC session, or
    just 'local' if they're using the shared key (require_api_key already
    accepted whichever it is; this only tells the two apart for the UI)."""
    provided = x_observa_api_key
    if not provided and authorization and authorization.lower().startswith("bearer "):
        provided = authorization[7:]
    claims = verify_session_token(provided) if provided else None
    if claims:
        return {
            "mode": "oidc",
            "provider": claims.get("provider"),
            "email": claims.get("email"),
            "name": claims.get("name"),
        }
    return {"mode": "local"}


@router.get("/auth/settings")
def get_auth_settings():
    auth = db.get_setting("auth") or {"mode": "local", "providers": {}}
    providers = {}
    for key, p in (auth.get("providers") or {}).items():
        p = dict(p)
        has_secret = bool(p.pop("client_secret_enc", None))
        p.pop("client_secret", None)  # legacy plaintext field, never echoed back
        providers[key] = {
            **p,
            "client_secret": "••••••••" if has_secret else "",
            "has_client_secret": has_secret,
        }
    return {"mode": auth.get("mode", "local"), "providers": providers}


@router.put("/auth/settings")
def put_auth_settings(body: AuthSettingsUpdate):
    current = db.get_setting("auth") or {"mode": "local", "providers": {}}
    providers = dict(current.get("providers") or {})
    for key, incoming in (body.providers or {}).items():
        prev = dict(providers.get(key) or {})
        prev.pop("client_secret", None)  # drop any legacy plaintext value on write
        secret = incoming.get("client_secret") or ""
        if secret and secret != "••••••••":
            # Secrets at rest go through the same Fernet key as connection
            # secrets — never stored as plaintext JSON in the settings table.
            prev["client_secret_enc"] = encrypt_json({"v": secret})
        for field in ("enabled", "client_id", "issuer", "redirect_uri"):
            if field in incoming:
                prev[field] = incoming[field]
        providers[key] = prev
    saved = {"mode": body.mode, "providers": providers}
    db.set_setting("auth", saved)
    return {"ok": True, "mode": body.mode}


@router.get("/connectors")
def connectors():
    return sync_service.catalog_connectors()


@router.get("/connections")
def connections():
    return db.list_connections()


@router.post("/connections")
def create_connection(body: ConnectionCreate):
    if not any(c["id"] == body.connector_id for c in sync_service.catalog_connectors()):
        raise HTTPException(400, f"Unknown connector: {body.connector_id}")
    conn_id = sync_service.new_connection_id()
    row = db.create_connection(
        conn_id=conn_id,
        name=body.name,
        connector_id=body.connector_id,
        config=body.config,
        secrets=body.secrets,
    )
    if row and "_secrets" in row:
        del row["_secrets"]
    return row


@router.patch("/connections/{conn_id}")
def patch_connection(conn_id: str, body: ConnectionUpdate):
    row = db.update_connection(
        conn_id,
        name=body.name,
        config=body.config,
        secrets=body.secrets,
        enabled=body.enabled,
    )
    if not row:
        raise HTTPException(404, "Connection not found")
    row.pop("_secrets", None)
    return row


@router.delete("/connections/{conn_id}")
def remove_connection(conn_id: str):
    if not db.delete_connection(conn_id):
        raise HTTPException(404, "Connection not found")
    return {"ok": True}


@router.post("/connections/test")
def test_connection(body: TestConnectionBody):
    return sync_service.test_connection_payload(body.connector_id, body.config, body.secrets)


@router.post("/connections/{conn_id}/sync")
def sync(conn_id: str):
    try:
        return sync_service.sync_connection(conn_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(500, str(exc)[:500]) from exc


@router.get("/costs/summary")
def costs_summary(days: int = 30):
    return db.cost_summary(days)


@router.get("/costs/trend")
def costs_trend(days: int = 30):
    return db.cost_trend(days)


@router.get("/products")
def products():
    return db.list_products()


@router.get("/products/{slug}")
def product_detail(slug: str):
    item = db.get_product(slug)
    if not item:
        raise HTTPException(404, "Product not found")
    return item


@router.get("/resources")
def resources(product: str | None = None):
    return db.list_resources(product)


@router.get("/observability")
def observability():
    return db.observability_overview()


@router.get("/metrics/series")
def metrics_series(name: str, product: str | None = None, hours: int = 24):
    return db.metric_series(name, product=product, hours=hours)


@router.get("/alerts")
def alerts(status: str | None = None):
    return db.list_alerts(status)


@router.get("/ecosystem")
def ecosystem(product: str = "hiperlocal"):
    from app.application.demo_platform import ecosystem as eco

    return eco(product)


@router.get("/dashboards")
def dashboards():
    from app.application.demo_platform import dashboards as dlist

    return dlist()


@router.get("/dashboards/{dash_id}")
def dashboard_detail(dash_id: str):
    from app.application.demo_platform import dashboard_detail as detail

    return detail(dash_id)


@router.get("/monitors")
def monitors():
    from app.application.demo_platform import monitors as mlist

    return mlist()


@router.get("/logs")
def logs(
    limit: int = 100,
    product: str | None = None,
    severity: str | None = None,
    source: str | None = None,
    q: str | None = None,
):
    from app.application.demo_platform import logs as log_list

    return log_list(limit=limit, product=product, severity=severity, source=source, q=q)


@router.get("/traces")
def traces(limit: int = 50):
    from app.application.demo_platform import traces as trace_list

    return trace_list(limit=limit)


@router.get("/gcp/monitoring")
def gcp_monitoring():
    from app.application.demo_platform import gcp_monitoring_metrics

    return gcp_monitoring_metrics()


@router.get("/rum")
def rum():
    from app.application.demo_platform import rum_summary

    return rum_summary()


@router.get("/synthetics")
def synthetics():
    from app.application.demo_platform import synthetics as syn

    return syn()
