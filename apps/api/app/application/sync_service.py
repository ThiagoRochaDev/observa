from __future__ import annotations

import logging
import uuid
from typing import Any

from observa_connectors import get_connector, list_connectors
from observa_connectors.mock_demo import demo_alerts, demo_product_catalog

from app.application.demo_platform import logs as demo_logs
from app.core import db

logger = logging.getLogger(__name__)

DEMO_CONN_ID = "conn_demo_full"


def catalog_connectors() -> list[dict[str, Any]]:
    out = []
    for c in list_connectors():
        out.append(
            {
                "id": c.id,
                "name": c.name,
                "description": c.description,
                "capabilities": c.capabilities,
                "category": c.category,
                "icon": c.icon,
                "docs_url": c.docs_url,
                "availability": c.availability,
                "config_schema": c.config_schema(),
                "secrets_schema": c.secrets_schema(),
            }
        )
    return out


def sync_connection(conn_id: str) -> dict:
    row = db.get_connection(conn_id)
    if not row:
        raise ValueError("Connection not found")
    connector = get_connector(row["connector_id"])
    if not connector:
        raise ValueError(f"Unknown connector: {row['connector_id']}")

    try:
        result = connector.pull(row["config"], row.get("_secrets") or {})
        cost_rows = [
            {
                "date": c.date.isoformat(),
                "provider": c.provider,
                "amount": c.amount,
                "currency": c.currency,
                "account": c.account,
                "service": c.service,
                "resource_id": c.resource_id,
                "product": c.product,
                "squad": c.squad,
                "environment": c.environment,
                "sku": c.sku,
            }
            for c in result.costs
        ]
        resource_rows = [
            {
                "provider": r.provider,
                "type": r.type,
                "id": r.id,
                "name": r.name,
                "region": r.region,
                "product": r.product,
                "squad": r.squad,
                "status": r.status,
                "labels": r.labels,
            }
            for r in result.resources
        ]
        metric_rows = [
            {
                "name": m.name,
                "value": m.value,
                "unit": m.unit,
                "ts": m.ts.isoformat().replace("+00:00", "Z"),
                "resource_id": m.resource_id,
                "product": m.product,
                "labels": m.labels,
            }
            for m in result.metrics
        ]
        log_rows = [
            {
                "ts": item.ts.isoformat().replace("+00:00", "Z"),
                "severity": item.severity,
                "source": item.source,
                "message": item.message,
                "product": item.product,
                "service": item.service,
                "trace_id": item.trace_id,
                "labels": item.labels,
            }
            for item in result.logs
        ]
        if row["connector_id"] == "mock-demo":
            log_rows = demo_logs(limit=120)
        db.replace_costs(conn_id, cost_rows)
        db.replace_resources(conn_id, resource_rows)
        db.replace_metrics(conn_id, metric_rows)
        db.replace_logs(conn_id, log_rows)
        if row["connector_id"] == "mock-demo":
            db.replace_alerts(demo_alerts())
            db.set_setting("product_catalog", demo_product_catalog())
        msg = result.message or (
            f"Synced {len(cost_rows)} costs, {len(resource_rows)} resources, "
            f"{len(metric_rows)} metrics, {len(log_rows)} logs"
        )
        db.mark_sync(conn_id, "ok", msg)
        return {
            "status": "ok",
            "message": msg,
            "costs": len(cost_rows),
            "resources": len(resource_rows),
            "metrics": len(metric_rows),
            "logs": len(log_rows),
        }
    except NotImplementedError:
        msg = "Connector not implemented yet — configure in UI; use mock-demo for local data."
        db.mark_sync(conn_id, "stub", msg)
        return {"status": "stub", "message": msg, "costs": 0, "resources": 0, "metrics": 0}
    except Exception as exc:
        logger.exception("Sync failed for %s", conn_id)
        db.mark_sync(conn_id, "failed", str(exc)[:500])
        raise


def ensure_full_demo() -> dict:
    """Bootstrap rich demo dataset for local showcase."""
    existing = db.get_connection(DEMO_CONN_ID)
    if not existing:
        # remove older sparse demos
        for c in db.list_connections():
            if c["connector_id"] == "mock-demo":
                db.delete_connection(c["id"])
        db.create_connection(
            conn_id=DEMO_CONN_ID,
            name="Demo Full Platform",
            connector_id="mock-demo",
            config={"days": 30, "profile": "full"},
            secrets={},
        )
    return sync_connection(DEMO_CONN_ID)


def test_connection_payload(connector_id: str, config: dict, secrets: dict) -> dict:
    connector = get_connector(connector_id)
    if not connector:
        return {"ok": False, "message": f"Unknown connector: {connector_id}"}
    result = connector.test_connection(config or {}, secrets or {})
    return {"ok": result.ok, "message": result.message}


def new_connection_id() -> str:
    return f"conn_{uuid.uuid4().hex[:12]}"
