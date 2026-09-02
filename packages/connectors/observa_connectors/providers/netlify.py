from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from observa_connectors.base import BaseConnector, MetricSignal, PullResult, ResourceSignal, TestResult
from observa_connectors.http import request_json

BASE_URL = "https://api.netlify.com/api/v1"


class NetlifyConnector(BaseConnector):
    id = "netlify"
    name = "Netlify"
    description = "Site inventory and build minutes usage."
    capabilities = ["inventory", "metrics"]
    category = "cloud"
    icon = "netlify"
    docs_url = "https://docs.netlify.com/api/get-started/#authentication"

    def config_schema(self) -> dict[str, Any]:
        return {"type": "object", "properties": {}}

    def secrets_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {"token": {"type": "string", "title": "Personal access token (PAT)"}},
            "required": ["token"],
        }

    def _headers(self, secrets: dict[str, Any]) -> dict[str, str]:
        return {"Authorization": f"Bearer {secrets.get('token', '')}"}

    def test_connection(self, config: dict[str, Any], secrets: dict[str, Any]) -> TestResult:
        status, body = request_json("GET", f"{BASE_URL}/sites", headers=self._headers(secrets), params={"per_page": 1})
        if status == 200:
            return TestResult(ok=True, message="Token is valid.")
        return TestResult(ok=False, message=f"HTTP {status}: {str(body)[:300]}")

    def pull(self, config: dict[str, Any], secrets: dict[str, Any], *, since=None) -> PullResult:
        headers = self._headers(secrets)

        resources: list[ResourceSignal] = []
        status, body = request_json("GET", f"{BASE_URL}/sites", headers=headers, params={"per_page": 100})
        if status == 200 and isinstance(body, list):
            for site in body:
                resources.append(
                    ResourceSignal(
                        provider="netlify",
                        type="site",
                        id=site.get("site_id") or site.get("id", ""),
                        name=site.get("name"),
                        status=site.get("state"),
                        labels={"url": site.get("url") or ""},
                    )
                )

        metrics: list[MetricSignal] = []
        status, body = request_json("GET", f"{BASE_URL}/accounts", headers=headers)
        if status == 200 and isinstance(body, list):
            now = datetime.now(timezone.utc)
            for account in body:
                capabilities = account.get("capabilities") or {}
                build_minutes = capabilities.get("build_minutes") or {}
                used = build_minutes.get("used")
                if used is not None:
                    metrics.append(
                        MetricSignal(
                            name="netlify.build_minutes.used", value=float(used), ts=now,
                            unit="minutes", labels={"account": account.get("slug") or ""},
                        )
                    )

        return PullResult(resources=resources, metrics=metrics, message=f"{len(resources)} sites")
