from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

from observa_connectors.base import (
    BaseConnector,
    CostSignal,
    MetricSignal,
    PullResult,
    ResourceSignal,
    TestResult,
)

# Full demo catalog (FinOps + observability) — synthetic multi-product marketplace data.
DEMO_PRODUCTS: list[dict[str, Any]] = [
    {
        "slug": "painel",
        "name": "Painel (Geramundo)",
        "squad": "geramundo-backoffice",
        "tribe": "solucoes-digitais",
        "aliases": ["raimundo", "geraldo"],
        "services": ["painel-core", "painel-bff", "painel-queue"],
        "weight": 1.4,
    },
    {
        "slug": "hiperlocal",
        "name": "Hiperlocal",
        "squad": "hiperlocal",
        "tribe": "marketplace",
        "aliases": [],
        "services": ["catalog-api", "checkout-api", "search-api", "order-api"],
        "weight": 1.8,
    },
    {
        "slug": "gertrudes",
        "name": "Gertrudes (Pagamentos)",
        "squad": "experiencia-financeira",
        "tribe": "financeiro",
        "aliases": ["pagamento"],
        "services": ["gertrudes-api", "gertrudes-worker"],
        "weight": 1.1,
    },
    {
        "slug": "delivery",
        "name": "Aiqentrega",
        "squad": "logistica",
        "tribe": "ops",
        "aliases": [],
        "services": ["freight-api", "tracking-api"],
        "weight": 0.9,
    },
    {
        "slug": "platform",
        "name": "Platform / Shared",
        "squad": "dbre",
        "tribe": "engenharia-de-plataforma",
        "aliases": [],
        "services": ["gateway", "argo-cd", "observability"],
        "weight": 0.7,
    },
]


class MockDemoConnector(BaseConnector):
    id = "mock-demo"
    name = "Mock Demo (full platform)"
    description = (
        "Rich synthetic dataset: multi-product catalog, multi-cloud cost, "
        "APM/DB metrics and alerts — for UI demos without real cloud credentials."
    )
    capabilities = ["cost", "inventory", "metrics", "alerts"]
    category = "demo"
    icon = "mock"

    def config_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "days": {
                    "type": "integer",
                    "title": "Lookback days",
                    "default": 30,
                    "minimum": 7,
                    "maximum": 90,
                },
                "profile": {
                    "type": "string",
                    "title": "Dataset profile",
                    "default": "full",
                },
            },
            "required": [],
        }

    def test_connection(self, config: dict[str, Any], secrets: dict[str, Any]) -> TestResult:
        return TestResult(ok=True, message="Mock full platform dataset ready.")

    def pull(
        self,
        config: dict[str, Any],
        secrets: dict[str, Any],
        *,
        since: date | None = None,
    ) -> PullResult:
        days = int(config.get("days") or 30)
        end = date.today()
        start = since or (end - timedelta(days=days - 1))
        now = datetime.now(timezone.utc)

        costs: list[CostSignal] = []
        resources: list[ResourceSignal] = []
        metrics: list[MetricSignal] = []

        providers_cost = (
            ("gcp", 0.52),
            ("aws", 0.18),
            ("datadog", 0.16),
            ("gitlab", 0.14),
        )

        day = start
        while day <= end:
            dow = day.weekday()
            weekend = 0.72 if dow >= 5 else 1.0
            for pi, product in enumerate(DEMO_PRODUCTS):
                base = 85 * float(product["weight"]) * weekend
                for provider, share in providers_cost:
                    jitter = 1 + ((day.toordinal() + pi) % 9) * 0.03
                    amount = round(base * share * jitter, 2)
                    svc = product["services"][pi % len(product["services"])]
                    costs.append(
                        CostSignal(
                            date=day,
                            provider=provider,
                            amount=amount,
                            currency="BRL",
                            account="demo-org",
                            service=svc,
                            product=product["slug"],
                            squad=product["squad"],
                            environment="prd" if day.toordinal() % 5 else "stg",
                            sku=f"{provider}.usage",
                        )
                    )
            day += timedelta(days=1)

        for product in DEMO_PRODUCTS:
            for svc in product["services"]:
                resources.append(
                    ResourceSignal(
                        provider="gcp",
                        type="gke_deployment",
                        id=f"gke/{product['slug']}/{svc}",
                        name=svc,
                        region="us-central1",
                        product=product["slug"],
                        squad=product["squad"],
                        status="running",
                        labels={"env": "prd", "tribe": product["tribe"]},
                    )
                )
            resources.append(
                ResourceSignal(
                    provider="gcp",
                    type="cloudsql",
                    id=f"sql/{product['slug']}-primary",
                    name=f"{product['slug']}-primary",
                    region="us-central1",
                    product=product["slug"],
                    squad=product["squad"],
                    status="running",
                    labels={"tier": "db-custom-4-16384", "env": "prd"},
                )
            )
            resources.append(
                ResourceSignal(
                    provider="gcp",
                    type="cloud_run",
                    id=f"run/{product['slug']}-worker",
                    name=f"{product['slug']}-worker",
                    region="us-central1",
                    product=product["slug"],
                    squad=product["squad"],
                    status="running",
                    labels={"env": "prd"},
                )
            )
            if product["slug"] == "hiperlocal":
                resources.append(
                    ResourceSignal(
                        provider="aws",
                        type="elasticache",
                        id="redis/hiperlocal-cache",
                        name="hiperlocal-cache",
                        region="us-east-1",
                        product="hiperlocal",
                        squad=product["squad"],
                        status="running",
                    )
                )

        # Observability metrics (last 24h hourly samples condensed as latest + series tags)
        for product in DEMO_PRODUCTS:
            w = float(product["weight"])
            for hour in range(24):
                ts = now - timedelta(hours=23 - hour)
                metrics.append(
                    MetricSignal(
                        name="apm.latency_p95_ms",
                        value=round(80 + w * 40 + (hour % 6) * 12, 1),
                        ts=ts,
                        unit="ms",
                        resource_id=f"svc/{product['slug']}",
                        product=product["slug"],
                        labels={"squad": product["squad"]},
                    )
                )
                metrics.append(
                    MetricSignal(
                        name="apm.error_rate_pct",
                        value=round(0.2 + (hour == 14) * 2.5 * w * 0.3, 2),
                        ts=ts,
                        unit="%",
                        resource_id=f"svc/{product['slug']}",
                        product=product["slug"],
                        labels={"squad": product["squad"]},
                    )
                )
                metrics.append(
                    MetricSignal(
                        name="apm.requests_per_min",
                        value=round(120 * w + hour * 8, 0),
                        ts=ts,
                        unit="rpm",
                        resource_id=f"svc/{product['slug']}",
                        product=product["slug"],
                        labels={"squad": product["squad"]},
                    )
                )
                metrics.append(
                    MetricSignal(
                        name="infra.cpu_pct",
                        value=round(35 + w * 10 + (hour % 5) * 4, 1),
                        ts=ts,
                        unit="%",
                        resource_id=f"gke/{product['slug']}",
                        product=product["slug"],
                        labels={"kind": "gke"},
                    )
                )
                metrics.append(
                    MetricSignal(
                        name="infra.memory_pct",
                        value=round(48 + w * 8 + (hour % 4) * 3, 1),
                        ts=ts,
                        unit="%",
                        resource_id=f"gke/{product['slug']}",
                        product=product["slug"],
                        labels={"kind": "gke"},
                    )
                )
                metrics.append(
                    MetricSignal(
                        name="db.connections",
                        value=round(40 + w * 25 + hour * 1.5, 0),
                        ts=ts,
                        unit="conn",
                        resource_id=f"sql/{product['slug']}-primary",
                        product=product["slug"],
                        labels={"engine": "postgres", "max": "200"},
                    )
                )
                metrics.append(
                    MetricSignal(
                        name="db.cpu_pct",
                        value=round(28 + w * 12 + (hour % 7) * 3, 1),
                        ts=ts,
                        unit="%",
                        resource_id=f"sql/{product['slug']}-primary",
                        product=product["slug"],
                        labels={"engine": "postgres"},
                    )
                )
                metrics.append(
                    MetricSignal(
                        name="db.replication_lag_s",
                        value=round(0.1 + (hour == 18) * 4.2, 2),
                        ts=ts,
                        unit="s",
                        resource_id=f"sql/{product['slug']}-primary",
                        product=product["slug"],
                        labels={"engine": "postgres"},
                    )
                )

        return PullResult(
            costs=costs,
            resources=resources,
            metrics=metrics,
            message=(
                f"Full demo: {len(costs)} costs, {len(resources)} resources, "
                f"{len(metrics)} metric samples, {len(DEMO_PRODUCTS)} products"
            ),
        )


def demo_alerts() -> list[dict[str, Any]]:
    """Static alert catalog for the demo UI (not pulled via connector row)."""
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    return [
        {
            "id": "cost-hiperlocal-spike",
            "severity": "high",
            "category": "cost",
            "product": "hiperlocal",
            "title": "Custo semanal hiperlocal +38% vs semana anterior",
            "message": "GCP + Datadog no produto hiperlocal acima do baseline de 7 dias.",
            "status": "open",
            "detected_at": now,
        },
        {
            "id": "cost-unallocated",
            "severity": "medium",
            "category": "cost",
            "product": "platform",
            "title": "18% do custo sem label product/squad",
            "message": "Revisar labels no Terraform/Helm do shared platform.",
            "status": "open",
            "detected_at": now,
        },
        {
            "id": "apm-painel-errors",
            "severity": "high",
            "category": "apm",
            "product": "painel",
            "title": "Error rate painel-core > 2.5%",
            "message": "Pico de 5xx entre 14h–15h (demo). Latência P95 também elevada.",
            "status": "open",
            "detected_at": now,
        },
        {
            "id": "db-hiperlocal-connections",
            "severity": "medium",
            "category": "database",
            "product": "hiperlocal",
            "title": "Cloud SQL connections > 75% do max",
            "message": "hiperlocal-primary em ~150/200 conexões. Estilo alerta GCP/Percona.",
            "status": "open",
            "detected_at": now,
        },
        {
            "id": "db-gertrudes-lag",
            "severity": "low",
            "category": "database",
            "product": "gertrudes",
            "title": "Replication lag 4.2s",
            "message": "Lag pontual no read replica (demo hora 18).",
            "status": "open",
            "detected_at": now,
        },
        {
            "id": "infra-delivery-cpu",
            "severity": "medium",
            "category": "infra",
            "product": "delivery",
            "title": "CPU GKE delivery acima de 70%",
            "message": "freight-api / tracking-api sob carga sustentada.",
            "status": "acknowledged",
            "detected_at": now,
        },
        {
            "id": "rec-staging-ratio",
            "severity": "low",
            "category": "recommendation",
            "product": "platform",
            "title": "Staging representa ~42% do custo de produção",
            "message": "Oportunidade: schedules de shutdown (FinOps).",
            "status": "pending",
            "detected_at": now,
        },
    ]


def demo_product_catalog() -> list[dict[str, Any]]:
    return DEMO_PRODUCTS
