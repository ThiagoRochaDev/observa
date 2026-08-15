from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from observa_connectors.base import BaseConnector, CostSignal, PullResult, ResourceSignal, TestResult


class AwsCostConnector(BaseConnector):
    id = "aws-cost"
    name = "AWS (Cost Explorer)"
    description = "Daily cost by service via AWS Cost Explorer, plus a light EC2/RDS inventory."
    capabilities = ["cost", "inventory"]
    category = "cloud"
    icon = "aws"
    docs_url = "https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_access-keys.html"

    def config_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "region": {"type": "string", "title": "Region", "default": "us-east-1"},
                "account_label": {"type": "string", "title": "Account label (optional)"},
            },
        }

    def secrets_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "access_key_id": {"type": "string", "title": "Access Key ID"},
                "secret_access_key": {"type": "string", "title": "Secret Access Key"},
                "session_token": {"type": "string", "title": "Session token (optional, STS)"},
            },
            "required": ["access_key_id", "secret_access_key"],
        }

    def _client(self, config: dict[str, Any], secrets: dict[str, Any], service: str):
        try:
            import boto3
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "AWS connector needs boto3 — install with `pip install observa-connectors[aws]`."
            ) from exc
        return boto3.client(
            service,
            region_name=config.get("region") or "us-east-1",
            aws_access_key_id=secrets.get("access_key_id"),
            aws_secret_access_key=secrets.get("secret_access_key"),
            aws_session_token=secrets.get("session_token") or None,
        )

    def test_connection(self, config: dict[str, Any], secrets: dict[str, Any]) -> TestResult:
        try:
            sts = self._client(config, secrets, "sts")
            ident = sts.get_caller_identity()
            return TestResult(ok=True, message=f"Connected as {ident.get('Arn', 'unknown')}")
        except Exception as exc:  # noqa: BLE001
            return TestResult(ok=False, message=str(exc)[:400])

    def pull(
        self,
        config: dict[str, Any],
        secrets: dict[str, Any],
        *,
        since: date | None = None,
    ) -> PullResult:
        ce = self._client(config, secrets, "ce")
        start = since or (date.today() - timedelta(days=90))
        end = date.today()
        resp = ce.get_cost_and_usage(
            TimePeriod={"Start": start.isoformat(), "End": end.isoformat()},
            Granularity="DAILY",
            Metrics=["UnblendedCost"],
            GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}],
        )
        costs: list[CostSignal] = []
        for row in resp.get("ResultsByTime", []):
            day = date.fromisoformat(row["TimePeriod"]["Start"])
            for group in row.get("Groups", []):
                amount = float(group["Metrics"]["UnblendedCost"]["Amount"])
                if amount == 0:
                    continue
                costs.append(
                    CostSignal(
                        date=day,
                        provider="aws",
                        amount=amount,
                        currency=group["Metrics"]["UnblendedCost"]["Unit"],
                        account=config.get("account_label"),
                        service=group["Keys"][0] if group["Keys"] else None,
                    )
                )

        resources: list[ResourceSignal] = []
        try:
            ec2 = self._client(config, secrets, "ec2")
            for res in ec2.describe_instances().get("Reservations", []):
                for inst in res.get("Instances", []):
                    resources.append(
                        ResourceSignal(
                            provider="aws",
                            type="ec2_instance",
                            id=inst["InstanceId"],
                            region=config.get("region"),
                            status=inst.get("State", {}).get("Name"),
                            labels={t["Key"]: t["Value"] for t in inst.get("Tags", [])},
                        )
                    )
        except Exception:  # noqa: BLE001
            pass  # inventory is best-effort; cost data above already succeeded

        return PullResult(costs=costs, resources=resources)
