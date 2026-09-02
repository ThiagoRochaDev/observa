from __future__ import annotations

from typing import Any

from observa_connectors.base import BaseConnector, PullResult, ResourceSignal, TestResult
from observa_connectors.http import request_json

BASE_URL = "https://grafana.com/api"


class GrafanaCloudConnector(BaseConnector):
    id = "grafana-cloud"
    name = "Grafana Cloud"
    description = "Stacks, dashboards and active-series usage."
    capabilities = ["inventory", "metrics"]
    category = "observability"
    icon = "grafana"
    docs_url = "https://grafana.com/docs/grafana-cloud/account-management/authentication-and-permissions/access-policies/"

    def config_schema(self) -> dict[str, Any]:
        return {"type": "object", "properties": {"stack_slug": {"type": "string", "title": "Stack slug"}}}

    def secrets_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {"api_token": {"type": "string", "title": "Access policy token"}},
            "required": ["api_token"],
        }

    def _headers(self, secrets: dict[str, Any]) -> dict[str, str]:
        return {"Authorization": f"Bearer {secrets.get('api_token', '')}"}

    def test_connection(self, config: dict[str, Any], secrets: dict[str, Any]) -> TestResult:
        # /api/instances lista todos os stacks (Grafana Cloud) que a access
        # policy token enxerga — não depende do stack_slug estar preenchido.
        status, body = request_json("GET", f"{BASE_URL}/instances", headers=self._headers(secrets))
        if status == 200:
            return TestResult(ok=True, message="Token is valid.")
        return TestResult(ok=False, message=f"HTTP {status}: {str(body)[:300]}")

    def pull(self, config: dict[str, Any], secrets: dict[str, Any], *, since=None) -> PullResult:
        headers = self._headers(secrets)
        stack_filter = (config.get("stack_slug") or "").strip()

        resources: list[ResourceSignal] = []
        status, body = request_json("GET", f"{BASE_URL}/instances", headers=headers)
        if status == 200 and isinstance(body, dict):
            for stack in body.get("items", []):
                slug = stack.get("slug", "")
                if stack_filter and slug != stack_filter:
                    continue
                resources.append(
                    ResourceSignal(
                        provider="grafana-cloud",
                        type="stack",
                        id=str(stack.get("id", slug)),
                        name=stack.get("name") or slug,
                        region=stack.get("clusterSlug"),
                        status=stack.get("status"),
                        labels={"url": stack.get("url") or ""},
                    )
                )

        return PullResult(resources=resources, message=f"{len(resources)} stacks")
