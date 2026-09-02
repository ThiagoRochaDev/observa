from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from observa_connectors.base import BaseConnector, MetricSignal, PullResult, ResourceSignal, TestResult
from observa_connectors.http import request_json


class OpsgenieConnector(BaseConnector):
    id = "opsgenie"
    name = "Opsgenie"
    description = "Alerts and on-call schedules as inventory."
    capabilities = ["inventory", "metrics"]
    category = "incident"
    icon = "opsgenie"
    docs_url = "https://support.atlassian.com/opsgenie/docs/api-key-management/"

    def config_schema(self) -> dict[str, Any]:
        return {"type": "object", "properties": {}}

    def secrets_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {"api_key": {"type": "string", "title": "API key"}},
            "required": ["api_key"],
        }

    def _headers(self, secrets: dict[str, Any]) -> dict[str, str]:
        return {"Authorization": f"GenieKey {secrets.get('api_key', '')}"}

    def test_connection(self, config: dict[str, Any], secrets: dict[str, Any]) -> TestResult:
        status, body = request_json(
            "GET", "https://api.opsgenie.com/v2/account", headers=self._headers(secrets)
        )
        if status == 200:
            return TestResult(ok=True, message="API key is valid.")
        return TestResult(ok=False, message=f"HTTP {status}: {str(body)[:300]}")

    def pull(self, config: dict[str, Any], secrets: dict[str, Any], *, since=None) -> PullResult:
        headers = self._headers(secrets)
        resources: list[ResourceSignal] = []
        open_count = 0

        status, body = request_json(
            "GET", "https://api.opsgenie.com/v2/alerts",
            headers=headers, params={"limit": 100, "query": "status: open"},
        )
        if status == 200 and isinstance(body, dict):
            for alert in body.get("data", []):
                open_count += 1
                resources.append(
                    ResourceSignal(
                        provider="opsgenie",
                        type="alert",
                        id=alert.get("id", ""),
                        name=alert.get("message"),
                        status=alert.get("status"),
                        labels={"priority": alert.get("priority") or ""},
                    )
                )

        status, body = request_json("GET", "https://api.opsgenie.com/v2/schedules", headers=headers)
        if status == 200 and isinstance(body, dict):
            for sched in body.get("data", []):
                resources.append(
                    ResourceSignal(
                        provider="opsgenie",
                        type="schedule",
                        id=sched.get("id", ""),
                        name=sched.get("name"),
                        status="enabled" if sched.get("enabled") else "disabled",
                    )
                )

        metrics = [
            MetricSignal(
                name="opsgenie.alerts.open", value=float(open_count),
                ts=datetime.now(timezone.utc), unit="count",
            )
        ]
        return PullResult(resources=resources, metrics=metrics, message=f"{len(resources)} items, {open_count} open alerts")
