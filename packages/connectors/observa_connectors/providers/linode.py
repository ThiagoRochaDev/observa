from __future__ import annotations

from datetime import date
from typing import Any

from observa_connectors.base import BaseConnector, CostSignal, PullResult, ResourceSignal, TestResult
from observa_connectors.http import request_json

BASE_URL = "https://api.linode.com/v4"


class LinodeConnector(BaseConnector):
    id = "linode"
    name = "Linode (Akamai Cloud)"
    description = "Linode instance inventory and account balance."
    capabilities = ["cost", "inventory"]
    category = "cloud"
    icon = "linode"
    docs_url = "https://www.linode.com/docs/products/tools/api/get-started/"

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
        status, body = request_json("GET", f"{BASE_URL}/account", headers=self._headers(secrets))
        if status == 200:
            return TestResult(ok=True, message="Token is valid.")
        return TestResult(ok=False, message=f"HTTP {status}: {str(body)[:300]}")

    def pull(self, config: dict[str, Any], secrets: dict[str, Any], *, since=None) -> PullResult:
        headers = self._headers(secrets)

        resources: list[ResourceSignal] = []
        status, body = request_json("GET", f"{BASE_URL}/linode/instances", headers=headers, params={"page_size": 100})
        if status == 200 and isinstance(body, dict):
            for inst in body.get("data", []):
                resources.append(
                    ResourceSignal(
                        provider="linode",
                        type="instance",
                        id=str(inst.get("id", "")),
                        name=inst.get("label"),
                        region=inst.get("region"),
                        status=inst.get("status"),
                        labels={"type": inst.get("type") or ""},
                    )
                )

        costs: list[CostSignal] = []
        status, body = request_json("GET", f"{BASE_URL}/account", headers=headers)
        if status == 200 and isinstance(body, dict):
            balance = body.get("balance_uninvoiced")
            if balance is not None:
                costs.append(
                    CostSignal(
                        date=date.today(), provider="linode", amount=float(balance),
                        currency="USD", account=body.get("company") or body.get("email"),
                        service="account_balance_uninvoiced",
                    )
                )

        return PullResult(costs=costs, resources=resources, message=f"{len(resources)} instances")
