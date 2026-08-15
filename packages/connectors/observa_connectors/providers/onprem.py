from __future__ import annotations

from datetime import date, datetime, timezone
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


class PrometheusConnector(BaseConnector):
    """On-premise / self-hosted metrics via the Prometheus HTTP API.

    Works for any Prometheus-compatible endpoint: bare-metal, VMware, on-prem
    Kubernetes, Thanos, Mimir, etc. Auth is optional (bearer token) since many
    internal Prometheus instances sit behind a private network / reverse proxy.
    """

    id = "prometheus"
    name = "Prometheus (on-premise)"
    description = "Pull metrics from a self-hosted Prometheus / Thanos / Mimir endpoint."
    capabilities = ["metrics"]
    category = "on_prem"
    icon = "onprem"
    docs_url = "https://prometheus.io/docs/prometheus/latest/querying/api/"

    def config_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "base_url": {
                    "type": "string",
                    "title": "Prometheus base URL",
                    "default": "http://localhost:9090",
                },
                "queries": {
                    "type": "string",
                    "title": "Instant queries, comma-separated (PromQL)",
                    "default": "up",
                },
            },
            "required": ["base_url"],
        }

    def secrets_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "bearer_token": {"type": "string", "title": "Bearer token (optional)"},
                "basic_user": {"type": "string", "title": "Basic auth user (optional)"},
                "basic_password": {"type": "string", "title": "Basic auth password (optional)"},
            },
        }

    def _headers(self, secrets: dict[str, Any]) -> dict[str, str]:
        h = {}
        if secrets.get("bearer_token"):
            h["Authorization"] = f"Bearer {secrets['bearer_token']}"
        return h

    def _auth(self, secrets: dict[str, Any]):
        if secrets.get("basic_user"):
            return (secrets["basic_user"], secrets.get("basic_password") or "")
        return None

    def test_connection(self, config: dict[str, Any], secrets: dict[str, Any]) -> TestResult:
        status, body = request_json(
            "GET",
            f"{config['base_url'].rstrip('/')}/api/v1/status/buildinfo",
            headers=self._headers(secrets),
            auth=self._auth(secrets),
        )
        if status == 200:
            return TestResult(ok=True, message="Prometheus endpoint reachable.")
        return TestResult(ok=False, message=f"HTTP {status}: {str(body)[:300]}")

    def pull(
        self,
        config: dict[str, Any],
        secrets: dict[str, Any],
        *,
        since: date | None = None,
    ) -> PullResult:
        base = config["base_url"].rstrip("/")
        queries = [q.strip() for q in (config.get("queries") or "up").split(",") if q.strip()]
        metrics: list[MetricSignal] = []
        now = datetime.now(timezone.utc)
        for q in queries:
            status, body = request_json(
                "GET",
                f"{base}/api/v1/query",
                params={"query": q},
                headers=self._headers(secrets),
                auth=self._auth(secrets),
            )
            if status != 200 or not isinstance(body, dict):
                continue
            for result in body.get("data", {}).get("result", []):
                metric_labels = result.get("metric", {})
                _, value = result.get("value", [None, None])
                if value is None:
                    continue
                metrics.append(
                    MetricSignal(
                        name=metric_labels.get("__name__", q),
                        value=float(value),
                        ts=now,
                        labels={k: v for k, v in metric_labels.items() if k != "__name__"},
                    )
                )
        return PullResult(metrics=metrics, message=f"{len(metrics)} series from {len(queries)} queries")


class KubernetesConnector(BaseConnector):
    """Cluster inventory for any Kubernetes cluster — on-prem, EKS/GKE/AKS, k3s.

    Uses a bearer token (ServiceAccount token) against the cluster's API
    server, so it works the same whether the cluster is on-prem or in any cloud.
    """

    id = "kubernetes"
    name = "Kubernetes"
    description = "Node/pod inventory and cluster health via the Kubernetes API server."
    capabilities = ["inventory", "metrics"]
    category = "on_prem"
    icon = "kubernetes"
    docs_url = "https://kubernetes.io/docs/reference/access-authn-authz/service-accounts-admin/"

    def config_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "api_server": {"type": "string", "title": "API server URL"},
                "namespace": {"type": "string", "title": "Namespace filter (optional)"},
                "insecure_skip_tls_verify": {
                    "type": "boolean",
                    "title": "Skip TLS verification (self-signed certs)",
                    "default": False,
                },
            },
            "required": ["api_server"],
        }

    def secrets_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "bearer_token": {"type": "string", "title": "ServiceAccount bearer token"},
            },
            "required": ["bearer_token"],
        }

    def _headers(self, secrets: dict[str, Any]) -> dict[str, str]:
        return {"Authorization": f"Bearer {secrets.get('bearer_token', '')}"}

    def test_connection(self, config: dict[str, Any], secrets: dict[str, Any]) -> TestResult:
        status, body = request_json(
            "GET", f"{config['api_server'].rstrip('/')}/version", headers=self._headers(secrets)
        )
        if status == 200:
            return TestResult(ok=True, message=f"Reached API server: {str(body)[:200]}")
        return TestResult(ok=False, message=f"HTTP {status}: {str(body)[:300]}")

    def pull(
        self,
        config: dict[str, Any],
        secrets: dict[str, Any],
        *,
        since: date | None = None,
    ) -> PullResult:
        base = config["api_server"].rstrip("/")
        headers = self._headers(secrets)
        ns = config.get("namespace")

        resources: list[ResourceSignal] = []
        status, body = request_json("GET", f"{base}/api/v1/nodes", headers=headers)
        if status == 200 and isinstance(body, dict):
            for item in body.get("items", []):
                meta = item.get("metadata", {})
                conditions = {c["type"]: c["status"] for c in item.get("status", {}).get("conditions", [])}
                resources.append(
                    ResourceSignal(
                        provider="kubernetes",
                        type="node",
                        id=meta.get("uid", meta.get("name", "")),
                        name=meta.get("name"),
                        status="Ready" if conditions.get("Ready") == "True" else "NotReady",
                        labels=meta.get("labels", {}) or {},
                    )
                )

        pods_url = f"{base}/api/v1/namespaces/{ns}/pods" if ns else f"{base}/api/v1/pods"
        status, body = request_json("GET", pods_url, headers=headers)
        if status == 200 and isinstance(body, dict):
            for item in body.get("items", []):
                meta = item.get("metadata", {})
                resources.append(
                    ResourceSignal(
                        provider="kubernetes",
                        type="pod",
                        id=meta.get("uid", meta.get("name", "")),
                        name=meta.get("name"),
                        region=meta.get("namespace"),
                        status=item.get("status", {}).get("phase"),
                        labels=meta.get("labels", {}) or {},
                    )
                )

        return PullResult(resources=resources, message=f"{len(resources)} k8s objects")


class OnPremAgentConnector(BaseConnector):
    """Generic escape hatch for internal systems that have no dedicated connector.

    Point it at any internal HTTP endpoint (an in-house exporter, a legacy
    monitoring tool, a custom script exposed over HTTP) that already returns
    JSON shaped like `{"costs": [...], "resources": [...], "metrics": [...]}`
    using the observa.*.v1 field names. This lets a client wire up anything —
    mainframes, private data centers, homegrown tools — without us shipping a
    bespoke connector for every internal system.
    """

    id = "onprem-custom"
    name = "Custom / On-premise (HTTP)"
    description = "Poll any internal HTTP endpoint that returns cost/resource/metric JSON."
    capabilities = ["cost", "inventory", "metrics"]
    category = "on_prem"
    icon = "onprem"
    docs_url = ""

    def config_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "endpoint_url": {"type": "string", "title": "Endpoint URL"},
                "provider_label": {
                    "type": "string",
                    "title": "Label shown in dashboards",
                    "default": "on-prem",
                },
            },
            "required": ["endpoint_url"],
        }

    def secrets_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "bearer_token": {"type": "string", "title": "Bearer token / PAT (optional)"},
                "header_name": {"type": "string", "title": "Custom auth header name (optional)"},
                "header_value": {"type": "string", "title": "Custom auth header value (optional)"},
            },
        }

    def _headers(self, secrets: dict[str, Any]) -> dict[str, str]:
        h = {}
        if secrets.get("bearer_token"):
            h["Authorization"] = f"Bearer {secrets['bearer_token']}"
        if secrets.get("header_name"):
            h[secrets["header_name"]] = secrets.get("header_value", "")
        return h

    def test_connection(self, config: dict[str, Any], secrets: dict[str, Any]) -> TestResult:
        status, body = request_json("GET", config["endpoint_url"], headers=self._headers(secrets))
        if status < 400:
            return TestResult(ok=True, message=f"HTTP {status} from endpoint.")
        return TestResult(ok=False, message=f"HTTP {status}: {str(body)[:300]}")

    def pull(
        self,
        config: dict[str, Any],
        secrets: dict[str, Any],
        *,
        since: date | None = None,
    ) -> PullResult:
        status, body = request_json("GET", config["endpoint_url"], headers=self._headers(secrets))
        if status >= 400 or not isinstance(body, dict):
            raise RuntimeError(f"Endpoint returned HTTP {status}: {str(body)[:300]}")

        label = config.get("provider_label") or "on-prem"
        costs = [
            CostSignal(
                date=date.fromisoformat(str(c["date"])[:10]),
                provider=label,
                amount=float(c["amount"]),
                currency=c.get("currency", "BRL"),
                account=c.get("account"),
                service=c.get("service"),
                product=c.get("product"),
            )
            for c in body.get("costs", [])
        ]
        resources = [
            ResourceSignal(
                provider=label,
                type=r.get("type", "resource"),
                id=str(r.get("id")),
                name=r.get("name"),
                status=r.get("status"),
                labels=r.get("labels", {}) or {},
            )
            for r in body.get("resources", [])
        ]
        metrics = [
            MetricSignal(
                name=m["name"],
                value=float(m["value"]),
                ts=datetime.now(timezone.utc),
                unit=m.get("unit", ""),
                labels=m.get("labels", {}) or {},
            )
            for m in body.get("metrics", [])
        ]
        return PullResult(costs=costs, resources=resources, metrics=metrics)
