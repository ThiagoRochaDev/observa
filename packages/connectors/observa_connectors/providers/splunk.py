from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from observa_connectors.base import BaseConnector, MetricSignal, PullResult, ResourceSignal, TestResult
from observa_connectors.http import request_json


class SplunkConnector(BaseConnector):
    id = "splunk"
    name = "Splunk (on-premise / Cloud)"
    description = "Index volume and license usage via the Splunk REST API."
    capabilities = ["metrics", "inventory"]
    category = "on_prem"
    icon = "splunk"
    docs_url = "https://docs.splunk.com/Documentation/Splunk/latest/Security/Setuptokenauthentication"

    def config_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {"base_url": {"type": "string", "title": "Splunk management URL"}},
            "required": ["base_url"],
        }

    def secrets_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {"token": {"type": "string", "title": "Auth token"}},
            "required": ["token"],
        }

    def _headers(self, secrets: dict[str, Any]) -> dict[str, str]:
        return {"Authorization": f"Bearer {secrets.get('token', '')}"}

    def _base(self, config: dict[str, Any]) -> str:
        return (config.get("base_url") or "").rstrip("/")

    def test_connection(self, config: dict[str, Any], secrets: dict[str, Any]) -> TestResult:
        status, body = request_json(
            "GET", f"{self._base(config)}/services/server/info",
            headers=self._headers(secrets), params={"output_mode": "json"},
        )
        if status == 200:
            return TestResult(ok=True, message="Token is valid.")
        return TestResult(ok=False, message=f"HTTP {status}: {str(body)[:300]}")

    def pull(self, config: dict[str, Any], secrets: dict[str, Any], *, since=None) -> PullResult:
        base = self._base(config)
        headers = self._headers(secrets)

        resources: list[ResourceSignal] = []
        total_size_mb = 0.0
        status, body = request_json(
            "GET", f"{base}/services/data/indexes", headers=headers, params={"output_mode": "json", "count": 0}
        )
        if status == 200 and isinstance(body, dict):
            for entry in body.get("entry", []):
                content = entry.get("content", {})
                size_mb = float(content.get("currentDBSizeMB") or 0)
                total_size_mb += size_mb
                resources.append(
                    ResourceSignal(
                        provider="splunk",
                        type="index",
                        id=entry.get("name", ""),
                        name=entry.get("name"),
                        status="disabled" if content.get("disabled") else "enabled",
                        labels={"size_mb": str(size_mb)},
                    )
                )

        now = datetime.now(timezone.utc)
        metrics = [MetricSignal(name="splunk.index.total_size_mb", value=total_size_mb, ts=now, unit="MB")]

        status, body = request_json(
            "GET", f"{base}/services/licenser/pools", headers=headers, params={"output_mode": "json"}
        )
        if status == 200 and isinstance(body, dict):
            for entry in body.get("entry", []):
                content = entry.get("content", {})
                used = content.get("used_bytes")
                if used is not None:
                    metrics.append(
                        MetricSignal(
                            name="splunk.license.used_bytes", value=float(used), ts=now,
                            unit="bytes", labels={"pool": entry.get("name") or ""},
                        )
                    )

        return PullResult(resources=resources, metrics=metrics, message=f"{len(resources)} indexes, {total_size_mb:.1f}MB")
