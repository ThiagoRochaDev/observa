from __future__ import annotations

from typing import Any

from observa_connectors.base import BaseConnector, PullResult, ResourceSignal, TestResult
from observa_connectors.http import request_json

BASE_URL = "https://api.elastic-cloud.com/api/v1"


class ElasticCloudConnector(BaseConnector):
    id = "elastic-cloud"
    name = "Elastic Cloud"
    description = "Deployment inventory and cluster health."
    capabilities = ["inventory", "metrics"]
    category = "observability"
    icon = "elastic"
    docs_url = "https://www.elastic.co/guide/en/cloud/current/ec-api-authentication.html"

    def config_schema(self) -> dict[str, Any]:
        return {"type": "object", "properties": {}}

    def secrets_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {"api_key": {"type": "string", "title": "API key"}},
            "required": ["api_key"],
        }

    def _headers(self, secrets: dict[str, Any]) -> dict[str, str]:
        return {"Authorization": f"ApiKey {secrets.get('api_key', '')}"}

    def test_connection(self, config: dict[str, Any], secrets: dict[str, Any]) -> TestResult:
        status, body = request_json("GET", f"{BASE_URL}/deployments", headers=self._headers(secrets))
        if status == 200:
            return TestResult(ok=True, message="API key is valid.")
        return TestResult(ok=False, message=f"HTTP {status}: {str(body)[:300]}")

    def pull(self, config: dict[str, Any], secrets: dict[str, Any], *, since=None) -> PullResult:
        headers = self._headers(secrets)
        resources: list[ResourceSignal] = []

        status, body = request_json("GET", f"{BASE_URL}/deployments", headers=headers)
        if status == 200 and isinstance(body, dict):
            for dep in body.get("deployments", []):
                es_resources = (dep.get("resources") or {}).get("elasticsearch") or []
                info = es_resources[0].get("info", {}) if es_resources else {}
                health = info.get("health") or (dep.get("healthy") and "green")
                resources.append(
                    ResourceSignal(
                        provider="elastic-cloud",
                        type="deployment",
                        id=dep.get("id", ""),
                        name=dep.get("name"),
                        region=info.get("region"),
                        status=health,
                    )
                )

        return PullResult(resources=resources, message=f"{len(resources)} deployments")
