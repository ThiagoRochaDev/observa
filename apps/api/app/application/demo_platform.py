"""Rich demo payloads for Observa showcase (Datadog-like + GCP Logging/Monitoring + maps)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

PRODUCTS = ["painel", "hiperlocal", "gertrudes", "delivery", "platform"]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _series(hours: int = 24, base: float = 40, amp: float = 8) -> list[dict[str, Any]]:
    now = _now()
    return [
        {
            "ts": (now - timedelta(hours=hours - 1 - i)).isoformat().replace("+00:00", "Z"),
            "value": round(base + (i % 7) * amp * 0.35 + (i % 3), 2),
        }
        for i in range(hours)
    ]


def ecosystem(product: str) -> dict[str, Any]:
    """Service/resource graph for the ecosystem map view."""
    layouts: dict[str, dict[str, Any]] = {
        "painel": {
            "nodes": [
                {"id": "web", "label": "painel-web", "kind": "frontend", "tier": 0},
                {"id": "bff", "label": "painel-bff", "kind": "api", "tier": 1},
                {"id": "core", "label": "painel-core", "kind": "api", "tier": 1},
                {"id": "queue", "label": "painel-queue", "kind": "worker", "tier": 2},
                {"id": "sql", "label": "painel-primary", "kind": "resource", "tier": 3, "type": "cloudsql"},
                {"id": "redis", "label": "painel-cache", "kind": "resource", "tier": 3, "type": "redis"},
                {"id": "ext", "label": "identity-api", "kind": "external", "tier": 1},
            ],
            "edges": [
                {"source": "web", "target": "bff", "label": "HTTPS"},
                {"source": "bff", "target": "core", "label": "gRPC"},
                {"source": "core", "target": "queue", "label": "Pub/Sub"},
                {"source": "core", "target": "sql", "label": "SQL"},
                {"source": "core", "target": "redis", "label": "cache"},
                {"source": "bff", "target": "ext", "label": "OIDC"},
            ],
        },
        "hiperlocal": {
            "nodes": [
                {"id": "fe", "label": "hiperlocal-frontend", "kind": "frontend", "tier": 0},
                {"id": "checkout", "label": "checkout-api", "kind": "api", "tier": 1},
                {"id": "catalog", "label": "catalog-api", "kind": "api", "tier": 1},
                {"id": "search", "label": "search-api", "kind": "api", "tier": 1},
                {"id": "order", "label": "order-api", "kind": "api", "tier": 2},
                {"id": "sql", "label": "hiperlocal-primary", "kind": "resource", "tier": 3, "type": "cloudsql"},
                {"id": "redis", "label": "hiperlocal-cache", "kind": "resource", "tier": 3, "type": "elasticache"},
                {"id": "pay", "label": "gertrudes-api", "kind": "external", "tier": 2},
            ],
            "edges": [
                {"source": "fe", "target": "checkout", "label": "HTTPS"},
                {"source": "fe", "target": "catalog", "label": "HTTPS"},
                {"source": "fe", "target": "search", "label": "HTTPS"},
                {"source": "checkout", "target": "order", "label": "events"},
                {"source": "checkout", "target": "pay", "label": "payments"},
                {"source": "catalog", "target": "sql", "label": "SQL"},
                {"source": "search", "target": "redis", "label": "cache"},
                {"source": "order", "target": "sql", "label": "SQL"},
            ],
        },
        "gertrudes": {
            "nodes": [
                {"id": "api", "label": "gertrudes-api", "kind": "api", "tier": 1},
                {"id": "ledger", "label": "ledger-worker", "kind": "worker", "tier": 2},
                {"id": "webhook", "label": "webhook-worker", "kind": "worker", "tier": 2},
                {"id": "sql", "label": "gertrudes-primary", "kind": "resource", "tier": 3, "type": "cloudsql"},
                {"id": "spanner", "label": "payments-spanner", "kind": "resource", "tier": 3, "type": "spanner"},
                {"id": "psp", "label": "acquirer-psp", "kind": "external", "tier": 1},
            ],
            "edges": [
                {"source": "api", "target": "ledger", "label": "queue"},
                {"source": "api", "target": "webhook", "label": "queue"},
                {"source": "api", "target": "sql", "label": "SQL"},
                {"source": "ledger", "target": "spanner", "label": "ledger"},
                {"source": "api", "target": "psp", "label": "HTTPS"},
            ],
        },
        "delivery": {
            "nodes": [
                {"id": "fe", "label": "delivery-app", "kind": "frontend", "tier": 0},
                {"id": "api", "label": "delivery-api", "kind": "api", "tier": 1},
                {"id": "routing", "label": "routing-api", "kind": "api", "tier": 1},
                {"id": "dispatch", "label": "dispatch-worker", "kind": "worker", "tier": 2},
                {"id": "sql", "label": "delivery-primary", "kind": "resource", "tier": 3, "type": "cloudsql"},
                {"id": "maps", "label": "maps-provider", "kind": "external", "tier": 1},
            ],
            "edges": [
                {"source": "fe", "target": "api", "label": "HTTPS"},
                {"source": "api", "target": "routing", "label": "gRPC"},
                {"source": "api", "target": "dispatch", "label": "Pub/Sub"},
                {"source": "routing", "target": "maps", "label": "HTTPS"},
                {"source": "api", "target": "sql", "label": "SQL"},
                {"source": "dispatch", "target": "sql", "label": "SQL"},
            ],
        },
        "platform": {
            "nodes": [
                {"id": "portal", "label": "platform-portal", "kind": "frontend", "tier": 0},
                {"id": "gateway", "label": "api-gateway", "kind": "api", "tier": 1},
                {"id": "auth", "label": "auth-service", "kind": "api", "tier": 1},
                {"id": "ci", "label": "ci-runner", "kind": "worker", "tier": 2},
                {"id": "gke", "label": "shared-gke", "kind": "resource", "tier": 3, "type": "gke"},
                {"id": "gitlab", "label": "GitLab", "kind": "external", "tier": 2},
            ],
            "edges": [
                {"source": "portal", "target": "gateway", "label": "HTTPS"},
                {"source": "gateway", "target": "auth", "label": "OIDC"},
                {"source": "ci", "target": "gitlab", "label": "webhooks"},
                {"source": "gateway", "target": "gke", "label": "k8s"},
                {"source": "auth", "target": "gke", "label": "k8s"},
            ],
        },
    }
    base = layouts.get(
        product,
        {
            "nodes": [
                {"id": "api", "label": f"{product}-api", "kind": "api", "tier": 1},
                {"id": "worker", "label": f"{product}-worker", "kind": "worker", "tier": 2},
                {"id": "sql", "label": f"{product}-db", "kind": "resource", "tier": 3, "type": "cloudsql"},
            ],
            "edges": [
                {"source": "api", "target": "worker", "label": "queue"},
                {"source": "api", "target": "sql", "label": "SQL"},
            ],
        },
    )
    return {"product": product, **base}


def dashboards() -> list[dict[str, Any]]:
    return [
        {
            "id": "overview-exec",
            "title": "Executive Overview",
            "source": "observa",
            "description": "Cost + reliability KPIs across products",
            "widgets": 8,
            "tags": ["finops", "exec"],
        },
        {
            "id": "apm-services",
            "title": "APM Services Health",
            "source": "datadog-like",
            "description": "Latency, errors, throughput by service",
            "widgets": 12,
            "tags": ["apm", "slo"],
        },
        {
            "id": "infra-gke",
            "title": "GKE Infrastructure",
            "source": "gcp-monitoring",
            "description": "CPU, memory, restarts, HPA",
            "widgets": 10,
            "tags": ["gke", "infra"],
        },
        {
            "id": "db-cloudsql",
            "title": "Cloud SQL / Databases",
            "source": "gcp-monitoring",
            "description": "Connections, CPU, lag, disk — Percona/GCP style",
            "widgets": 9,
            "tags": ["database"],
        },
        {
            "id": "logs-errors",
            "title": "Error Logs Pipeline",
            "source": "cloud-logging",
            "description": "Error rate by service from Cloud Logging",
            "widgets": 6,
            "tags": ["logs"],
        },
        {
            "id": "rum-web",
            "title": "RUM Web Performance",
            "source": "datadog-like",
            "description": "Core web vitals and session errors",
            "widgets": 7,
            "tags": ["rum"],
        },
    ]


def dashboard_detail(dash_id: str) -> dict[str, Any]:
    title = next((d["title"] for d in dashboards() if d["id"] == dash_id), dash_id)
    rpm = _series(24, 420, 40)
    err = [{"ts": p["ts"], "value": round(0.2 + (i % 5) * 0.35, 2)} for i, p in enumerate(rpm)]
    p95 = [{"ts": p["ts"], "value": 85 + (i % 6) * 18} for i, p in enumerate(rpm)]
    cpu = _series(24, 48, 10)

    panels: list[dict[str, Any]] = [
        {"id": "q1", "title": "Requests / min", "type": "query_value", "value": 4210, "unit": "rpm", "status": "ok"},
        {"id": "q2", "title": "Error rate", "type": "query_value", "value": 0.8, "unit": "%", "status": "warn"},
        {"id": "q3", "title": "P95 latency", "type": "query_value", "value": 142, "unit": "ms", "status": "ok"},
        {"id": "q4", "title": "Open monitors", "type": "query_value", "value": 2, "unit": "alerts", "status": "alert"},
        {"id": "p1", "title": "Requests / min", "type": "timeseries", "series": rpm},
        {"id": "p2", "title": "Error rate %", "type": "timeseries", "series": err},
        {"id": "p3", "title": "P95 latency ms", "type": "timeseries", "series": p95},
        {"id": "p4", "title": "CPU utilization %", "type": "timeseries", "series": cpu},
        {
            "id": "p5",
            "title": "Top services by RPM",
            "type": "toplist",
            "items": [
                {"name": "checkout-api", "value": 4210},
                {"name": "catalog-api", "value": 3880},
                {"name": "painel-core", "value": 2910},
                {"name": "search-api", "value": 2440},
                {"name": "gertrudes-api", "value": 1810},
            ],
        },
        {
            "id": "p6",
            "title": "Errors by service",
            "type": "toplist",
            "items": [
                {"name": "checkout-api", "value": 42},
                {"name": "search-api", "value": 18},
                {"name": "painel-bff", "value": 11},
                {"name": "delivery-api", "value": 7},
            ],
        },
    ]

    if dash_id == "db-cloudsql":
        panels = [
            {"id": "q1", "title": "Connections", "type": "query_value", "value": 138, "unit": "conn", "status": "warn"},
            {"id": "q2", "title": "DB CPU", "type": "query_value", "value": 62, "unit": "%", "status": "ok"},
            {"id": "q3", "title": "Replication lag", "type": "query_value", "value": 120, "unit": "ms", "status": "ok"},
            {"id": "q4", "title": "Disk used", "type": "query_value", "value": 71, "unit": "%", "status": "warn"},
            {"id": "p1", "title": "Connections", "type": "timeseries", "series": _series(24, 110, 18)},
            {"id": "p2", "title": "CPU %", "type": "timeseries", "series": _series(24, 55, 12)},
            {
                "id": "p3",
                "title": "Top DBs by connections",
                "type": "toplist",
                "items": [
                    {"name": "hiperlocal-primary", "value": 148},
                    {"name": "painel-primary", "value": 96},
                    {"name": "gertrudes-primary", "value": 72},
                ],
            },
        ]
    elif dash_id == "rum-web":
        panels = [
            {"id": "q1", "title": "Avg LCP", "type": "query_value", "value": 2100, "unit": "ms", "status": "warn"},
            {"id": "q2", "title": "Crash-free", "type": "query_value", "value": 99.2, "unit": "%", "status": "ok"},
            {"id": "q3", "title": "JS errors", "type": "query_value", "value": 842, "unit": "30d", "status": "warn"},
            {"id": "q4", "title": "Sessions", "type": "query_value", "value": 184200, "unit": "30d", "status": "ok"},
            {"id": "p1", "title": "LCP ms", "type": "timeseries", "series": _series(24, 1900, 80)},
            {"id": "p2", "title": "JS errors / h", "type": "timeseries", "series": _series(24, 12, 4)},
            {
                "id": "p3",
                "title": "Top views",
                "type": "toplist",
                "items": [
                    {"name": "/painel/home", "value": 42000},
                    {"name": "/checkout", "value": 31000},
                    {"name": "/search", "value": 29000},
                ],
            },
        ]

    return {"id": dash_id, "title": title, "panels": panels}


def monitors() -> list[dict[str, Any]]:
    return [
        {
            "id": "mon-apm-err",
            "name": "APM error rate > 2%",
            "type": "metric alert",
            "status": "Alert",
            "product": "painel",
            "query": "avg(last_5m):sum:trace.servlet.request.errors{product:painel} > 2",
            "source": "datadog-like",
        },
        {
            "id": "mon-p95",
            "name": "Checkout P95 > 500ms",
            "type": "metric alert",
            "status": "Warn",
            "product": "hiperlocal",
            "query": "avg(last_10m):p95:trace.express.request{service:checkout-api} > 500",
            "source": "datadog-like",
        },
        {
            "id": "mon-sql-conn",
            "name": "Cloud SQL connections > 75%",
            "type": "gcp monitoring",
            "status": "Alert",
            "product": "hiperlocal",
            "query": "cloudsql.googleapis.com/database/network/connections > 150",
            "source": "gcp-monitoring",
        },
        {
            "id": "mon-log-panic",
            "name": "Panic / FATAL logs",
            "type": "log alert",
            "status": "OK",
            "product": "gertrudes",
            "query": "severity>=ERROR service:gertrudes-api",
            "source": "cloud-logging",
        },
        {
            "id": "mon-cost",
            "name": "Daily cost anomaly",
            "type": "finops",
            "status": "Warn",
            "product": "platform",
            "query": "cost_change_pct > 25 over 1d",
            "source": "observa",
        },
        {
            "id": "mon-rum",
            "name": "RUM JS errors spike",
            "type": "rum alert",
            "status": "OK",
            "product": "painel",
            "query": "rum.error.count{view:painel} > 100",
            "source": "datadog-like",
        },
    ]


def logs(
    limit: int = 80,
    product: str | None = None,
    severity: str | None = None,
    source: str | None = None,
    q: str | None = None,
) -> list[dict[str, Any]]:
    now = _now()
    severities = ["INFO", "INFO", "WARN", "ERROR", "DEBUG", "INFO", "ERROR"]
    messages = [
        "request completed",
        "cache miss key=user:*",
        "slow query detected duration_ms=420",
        "upstream timeout calling payments",
        "auth token refreshed",
        "pubsub message acked",
        "panic recovered in middleware",
        "Cloud Run cold start",
        "HPA scaled replicas=4",
        "connection pool nearly exhausted",
    ]
    rows = []
    for i in range(max(limit * 3, 120)):
        p = PRODUCTS[i % len(PRODUCTS)]
        if product and p != product:
            continue
        sev = severities[i % len(severities)]
        if severity and sev != severity:
            continue
        src = "cloud-logging" if i % 2 == 0 else "datadog-agent"
        if source and src != source:
            continue
        msg = messages[i % len(messages)]
        if q and q.lower() not in msg.lower() and q.lower() not in p and q.lower() not in src:
            continue
        rows.append(
            {
                "ts": (now - timedelta(minutes=i * 3)).isoformat().replace("+00:00", "Z"),
                "severity": sev,
                "product": p,
                "service": f"{p}-api",
                "source": src,
                "message": msg,
                "trace_id": f"trace-{1000 + i}",
                "labels": {"env": "prd", "region": "us-central1"},
            }
        )
        if len(rows) >= limit:
            break
    return rows


def traces(limit: int = 40) -> list[dict[str, Any]]:
    now = _now()
    rows = []
    for i in range(limit):
        p = PRODUCTS[i % len(PRODUCTS)]
        duration = 40 + (i * 17) % 480
        status = "error" if i % 11 == 0 else "ok"
        spans = [
            {"service": f"{p}-api", "name": "http.request", "start_ms": 0, "duration_ms": duration, "status": status},
            {
                "service": f"{p}-api",
                "name": "db.query",
                "start_ms": int(duration * 0.15),
                "duration_ms": int(duration * 0.35),
                "status": "ok",
            },
            {
                "service": "redis",
                "name": "cache.get",
                "start_ms": int(duration * 0.2),
                "duration_ms": int(duration * 0.08),
                "status": "ok",
            },
            {
                "service": "downstream",
                "name": "http.client",
                "start_ms": int(duration * 0.55),
                "duration_ms": int(duration * 0.3),
                "status": status if status == "error" else "ok",
            },
        ]
        rows.append(
            {
                "trace_id": f"trace-{2000 + i}",
                "product": p,
                "service": f"{p}-api",
                "resource": ["GET /api/v1/items", "POST /checkout", "GET /search", "gRPC Pay"][i % 4],
                "duration_ms": duration,
                "status": status,
                "spans": len(spans),
                "span_details": spans,
                "ts": (now - timedelta(minutes=i * 5)).isoformat().replace("+00:00", "Z"),
            }
        )
    return rows


def gcp_monitoring_metrics() -> dict[str, Any]:
    return {
        "project": "demo-gcp-project",
        "metrics": [
            {
                "type": "kubernetes.io/container/cpu/limit_utilization",
                "display": "GKE CPU utilization",
                "series": _series(24, 45, 12),
            },
            {
                "type": "kubernetes.io/container/memory/limit_utilization",
                "display": "GKE Memory utilization",
                "series": _series(24, 62, 8),
            },
            {
                "type": "cloudsql.googleapis.com/database/cpu/utilization",
                "display": "Cloud SQL CPU",
                "series": _series(24, 38, 15),
            },
            {
                "type": "cloudsql.googleapis.com/database/network/connections",
                "display": "Cloud SQL connections",
                "series": _series(24, 110, 20),
            },
            {
                "type": "run.googleapis.com/request_count",
                "display": "Cloud Run requests",
                "series": _series(24, 800, 40),
            },
            {
                "type": "logging.googleapis.com/user/error_count",
                "display": "Cloud Logging errors",
                "series": _series(24, 12, 5),
            },
        ],
    }


def rum_summary() -> dict[str, Any]:
    return {
        "sessions_30d": 184200,
        "avg_lcp_ms": 2100,
        "js_errors": 842,
        "crash_free_pct": 99.2,
        "top_views": [
            {"view": "/painel/home", "sessions": 42000, "errors": 120},
            {"view": "/checkout", "sessions": 31000, "errors": 280},
            {"view": "/search", "sessions": 29000, "errors": 95},
        ],
    }


def synthetics() -> list[dict[str, Any]]:
    return [
        {"id": "syn-1", "name": "Checkout API health", "type": "API", "status": "OK", "locations": 3, "uptime_pct": 99.95},
        {"id": "syn-2", "name": "Painel login flow", "type": "Browser", "status": "OK", "locations": 2, "uptime_pct": 99.8},
        {"id": "syn-3", "name": "Search latency probe", "type": "API", "status": "Alert", "locations": 4, "uptime_pct": 98.1},
    ]
