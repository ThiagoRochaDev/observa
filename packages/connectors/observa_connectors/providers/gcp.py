from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from observa_connectors.base import BaseConnector, CostSignal, PullResult, TestResult


class GcpBillingConnector(BaseConnector):
    id = "gcp-billing"
    name = "Google Cloud (Billing export)"
    description = "Daily cost by service, read from a BigQuery billing export table."
    capabilities = ["cost"]
    category = "cloud"
    icon = "gcp"
    docs_url = "https://cloud.google.com/billing/docs/how-to/export-data-bigquery-setup"

    def config_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "project_id": {"type": "string", "title": "GCP project (runs the BQ job)"},
                "billing_table": {
                    "type": "string",
                    "title": "Billing export table (project.dataset.table)",
                },
            },
            "required": ["project_id", "billing_table"],
        }

    def secrets_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "service_account_json": {
                    "type": "string",
                    "title": "Service account JSON (leave empty to use Application Default Credentials)",
                }
            },
        }

    def _client(self, config: dict[str, Any], secrets: dict[str, Any]):
        try:
            from google.cloud import bigquery
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "GCP connector needs google-cloud-bigquery — install with `pip install observa-connectors[gcp]`."
            ) from exc

        sa_json = secrets.get("service_account_json")
        if sa_json:
            import json

            from google.oauth2 import service_account

            creds = service_account.Credentials.from_service_account_info(json.loads(sa_json))
            return bigquery.Client(project=config.get("project_id"), credentials=creds)
        return bigquery.Client(project=config.get("project_id"))

    def test_connection(self, config: dict[str, Any], secrets: dict[str, Any]) -> TestResult:
        try:
            client = self._client(config, secrets)
            list(client.query("SELECT 1").result())
            return TestResult(ok=True, message=f"Connected to project {config.get('project_id')}")
        except Exception as exc:  # noqa: BLE001
            return TestResult(ok=False, message=str(exc)[:400])

    def pull(
        self,
        config: dict[str, Any],
        secrets: dict[str, Any],
        *,
        since: date | None = None,
    ) -> PullResult:
        table = config.get("billing_table")
        start = since or (date.today() - timedelta(days=90))
        query = f"""
            SELECT
              DATE(usage_start_time) AS day,
              service.description AS service,
              project.id AS account,
              sku.description AS sku,
              SUM(cost) AS amount,
              ANY_VALUE(currency) AS currency
            FROM `{table}`
            WHERE DATE(usage_start_time) >= @start
            GROUP BY day, service, account, sku
            HAVING amount != 0
            ORDER BY day
        """
        client = self._client(config, secrets)
        from google.cloud import bigquery as bq

        job = client.query(
            query,
            job_config=bq.QueryJobConfig(
                query_parameters=[bq.ScalarQueryParameter("start", "DATE", start.isoformat())]
            ),
        )
        costs = [
            CostSignal(
                date=row["day"],
                provider="gcp",
                amount=float(row["amount"]),
                currency=row["currency"] or "USD",
                account=row["account"],
                service=row["service"],
                sku=row["sku"],
            )
            for row in job.result()
        ]
        return PullResult(costs=costs)
