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
from observa_connectors.http import request_json


class DatadogConnector(BaseConnector):
    id = "datadog"
    name = "Datadog"
    description = "Estimated usage cost, active monitors, and host inventory."
    capabilities = ["cost", "inventory", "metrics"]
    category = "observability"
    icon = "datadog"
    docs_url = "https://docs.datadoghq.com/account_management/api-app-keys/"

    def config_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "site": {
                    "type": "string",
                    "title": "Datadog site",
                    "default": "datadoghq.com",
                },
            },
        }

    def secrets_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "api_key": {"type": "string", "title": "API key"},
                "app_key": {"type": "string", "title": "Application key"},
            },
            "required": ["api_key", "app_key"],
        }

    def _headers(self, secrets: dict[str, Any]) -> dict[str, str]:
        return {
            "DD-API-KEY": secrets.get("api_key", ""),
            "DD-APPLICATION-KEY": secrets.get("app_key", ""),
        }

    def _base(self, config: dict[str, Any]) -> str:
        return f"https://api.{config.get('site') or 'datadoghq.com'}"

    def test_connection(self, config: dict[str, Any], secrets: dict[str, Any]) -> TestResult:
        status, body = request_json(
            "GET", f"{self._base(config)}/api/v1/validate", headers=self._headers(secrets)
        )
        if status == 200 and isinstance(body, dict) and body.get("valid"):
            return TestResult(ok=True, message="API key is valid.")
        return TestResult(ok=False, message=f"HTTP {status}: {str(body)[:300]}")

    def pull(
        self,
        config: dict[str, Any],
        secrets: dict[str, Any],
        *,
        since: date | None = None,
    ) -> PullResult:
        base = self._base(config)
        headers = self._headers(secrets)
        start = since or (date.today() - timedelta(days=30))

        costs: list[CostSignal] = []
        status, body = request_json(
            "GET",
            f"{base}/api/v2/usage/estimated_cost",
            headers=headers,
            params={"view": "summary", "start_month": start.strftime("%Y-%m")},
        )
        if status == 200 and isinstance(body, dict):
            for row in body.get("data", []):
                attrs = row.get("attributes", {})
                day_str = attrs.get("date")
                if not day_str:
                    continue
                costs.append(
                    CostSignal(
                        date=date.fromisoformat(day_str[:10]),
                        provider="datadog",
                        amount=float(attrs.get("total_cost") or 0),
                        currency="USD",
                        account=attrs.get("org_name"),
                        service="observability",
                    )
                )

        resources: list[ResourceSignal] = []
        status, body = request_json("GET", f"{base}/api/v1/hosts", headers=headers)
        if status == 200 and isinstance(body, dict):
            for h in body.get("host_list", []):
                resources.append(
                    ResourceSignal(
                        provider="datadog",
                        type="host",
                        id=h.get("id") and str(h["id"]) or h.get("name", ""),
                        name=h.get("name"),
                        status="up" if h.get("up") else "down",
                        labels={t.split(":", 1)[0]: t.split(":", 1)[1] for t in h.get("tags_by_source", {}).get("Datadog", []) if ":" in t},
                    )
                )

        metrics: list[MetricSignal] = []
        status, body = request_json("GET", f"{base}/api/v1/monitor", headers=headers)
        if status == 200 and isinstance(body, list):
            now = datetime.now(timezone.utc)
            triggered = sum(1 for m in body if m.get("overall_state") == "Alert")
            metrics.append(
                MetricSignal(name="datadog.monitors.alerting", value=float(triggered), ts=now, unit="count")
            )

        return PullResult(
            costs=costs,
            resources=resources,
            metrics=metrics,
            message=f"{len(costs)} cost rows, {len(resources)} hosts",
        )
