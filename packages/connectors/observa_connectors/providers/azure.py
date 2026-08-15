from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from observa_connectors.base import BaseConnector, CostSignal, PullResult, TestResult
from observa_connectors.http import request_json

TOKEN_URL = "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
COST_QUERY_URL = (
    "https://management.azure.com/subscriptions/{sub}/providers/Microsoft.CostManagement"
    "/query?api-version=2023-11-01"
)


class AzureCostConnector(BaseConnector):
    id = "azure-cost"
    name = "Azure (Cost Management)"
    description = "Daily cost by service via the Azure Cost Management Query API."
    capabilities = ["cost"]
    category = "cloud"
    icon = "azure"
    docs_url = (
        "https://learn.microsoft.com/azure/active-directory/develop/howto-create-service-principal-portal"
    )

    def config_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "subscription_id": {"type": "string", "title": "Subscription ID"},
            },
            "required": ["subscription_id"],
        }

    def secrets_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "tenant_id": {"type": "string", "title": "Tenant ID"},
                "client_id": {"type": "string", "title": "App (client) ID"},
                "client_secret": {"type": "string", "title": "Client secret"},
            },
            "required": ["tenant_id", "client_id", "client_secret"],
        }

    def _token(self, secrets: dict[str, Any]) -> str:
        # Azure AD's token endpoint takes form-encoded data, not JSON — use requests directly.
        import requests

        resp = requests.post(
            TOKEN_URL.format(tenant=secrets["tenant_id"]),
            data={
                "grant_type": "client_credentials",
                "client_id": secrets["client_id"],
                "client_secret": secrets["client_secret"],
                "scope": "https://management.azure.com/.default",
            },
            timeout=20,
        )
        resp.raise_for_status()
        return resp.json()["access_token"]

    def test_connection(self, config: dict[str, Any], secrets: dict[str, Any]) -> TestResult:
        try:
            self._token(secrets)
            return TestResult(ok=True, message="Azure AD token acquired.")
        except Exception as exc:  # noqa: BLE001
            return TestResult(ok=False, message=str(exc)[:400])

    def pull(
        self,
        config: dict[str, Any],
        secrets: dict[str, Any],
        *,
        since: date | None = None,
    ) -> PullResult:
        token = self._token(secrets)
        start = since or (date.today() - timedelta(days=90))
        end = date.today()
        body = {
            "type": "ActualCost",
            "timeframe": "Custom",
            "timePeriod": {"from": start.isoformat(), "to": end.isoformat()},
            "dataset": {
                "granularity": "Daily",
                "aggregation": {"totalCost": {"name": "Cost", "function": "Sum"}},
                "grouping": [{"type": "Dimension", "name": "ServiceName"}],
            },
        }
        status, resp = request_json(
            "POST",
            COST_QUERY_URL.format(sub=config["subscription_id"]),
            headers={"Authorization": f"Bearer {token}"},
            json_body=body,
        )
        if status >= 400:
            raise RuntimeError(f"Azure Cost Management error {status}: {str(resp)[:300]}")

        columns = [c["name"] for c in resp.get("properties", {}).get("columns", [])]
        rows = resp.get("properties", {}).get("rows", [])
        idx = {name: i for i, name in enumerate(columns)}
        costs = []
        for row in rows:
            amount = float(row[idx["Cost"]])
            if amount == 0:
                continue
            raw_date = str(row[idx["UsageDate"]])
            day = date(int(raw_date[:4]), int(raw_date[4:6]), int(raw_date[6:8]))
            costs.append(
                CostSignal(
                    date=day,
                    provider="azure",
                    amount=amount,
                    currency=row[idx.get("Currency", -1)] if "Currency" in idx else "USD",
                    account=config.get("subscription_id"),
                    service=row[idx["ServiceName"]] if "ServiceName" in idx else None,
                )
            )
        return PullResult(costs=costs)
