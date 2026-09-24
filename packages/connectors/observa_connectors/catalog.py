from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from observa_connectors.base import (
    BaseConnector,
    CostSignal,
    LogSignal,
    MetricSignal,
    PullResult,
    ResourceSignal,
    TestResult,
)
from observa_connectors.http import request_json


class AdapterCatalogConnector(BaseConnector):
    availability = "adapter"

    def __init__(
        self,
        connector_id: str,
        name: str,
        category: str,
        capabilities: list[str],
        description: str,
    ) -> None:
        self.id = connector_id
        self.name = name
        self.category = category
        self.capabilities = capabilities
        self.description = description
        self.icon = connector_id

    def config_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "base_url": {
                    "type": "string",
                    "title": "Observa adapter URL",
                },
                "health_path": {
                    "type": "string",
                    "title": "Health path",
                    "default": "/health",
                },
                "pull_path": {
                    "type": "string",
                    "title": "Canonical data path",
                    "default": "/observa/pull",
                },
            },
            "required": ["base_url"],
        }

    def secrets_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "token": {
                    "type": "string",
                    "title": "Adapter bearer token (optional)",
                }
            },
        }

    @staticmethod
    def _url(config: dict[str, Any], key: str, default: str) -> str:
        base_url = str(config.get("base_url") or "").rstrip("/")
        path = str(config.get(key) or default)
        return f"{base_url}/{path.lstrip('/')}"

    @staticmethod
    def _headers(secrets: dict[str, Any]) -> dict[str, str]:
        token = str(secrets.get("token") or "")
        return {"Authorization": f"Bearer {token}"} if token else {}

    def test_connection(self, config: dict[str, Any], secrets: dict[str, Any]) -> TestResult:
        if not config.get("base_url"):
            return TestResult(ok=False, message="Observa adapter URL is required.")
        status, body = request_json(
            "GET",
            self._url(config, "health_path", "/health"),
            headers=self._headers(secrets),
        )
        if 200 <= status < 300:
            message = body.get("message") if isinstance(body, dict) else None
            return TestResult(ok=True, message=str(message or f"{self.name} adapter is reachable."))
        return TestResult(ok=False, message=f"Adapter health check returned HTTP {status}.")

    def pull(self, config, secrets, *, since=None) -> PullResult:
        params = {"since": since.isoformat()} if since else None
        status, body = request_json(
            "GET",
            self._url(config, "pull_path", "/observa/pull"),
            headers=self._headers(secrets),
            params=params,
        )
        if status < 200 or status >= 300 or not isinstance(body, dict):
            raise RuntimeError(f"{self.name} adapter returned HTTP {status}.")

        costs = [self._cost(row) for row in body.get("costs", []) if isinstance(row, dict)]
        resources = [self._resource(row) for row in body.get("resources", []) if isinstance(row, dict)]
        metrics = [self._metric(row) for row in body.get("metrics", []) if isinstance(row, dict)]
        logs = [self._log(row) for row in body.get("logs", []) if isinstance(row, dict)]
        return PullResult(
            costs=costs,
            resources=resources,
            metrics=metrics,
            logs=logs,
            message=str(body.get("message") or f"{self.name} adapter synchronized."),
        )

    def _cost(self, row: dict[str, Any]) -> CostSignal:
        return CostSignal(
            date=date.fromisoformat(str(row.get("date") or date.today().isoformat())[:10]),
            provider=str(row.get("provider") or self.id),
            amount=float(row.get("amount") or 0),
            currency=str(row.get("currency") or "USD"),
            account=row.get("account"),
            service=row.get("service"),
            resource_id=row.get("resource_id"),
            product=row.get("product"),
            squad=row.get("squad"),
            environment=row.get("environment"),
            sku=row.get("sku"),
        )

    def _resource(self, row: dict[str, Any]) -> ResourceSignal:
        return ResourceSignal(
            provider=str(row.get("provider") or self.id),
            type=str(row.get("type") or "resource"),
            id=str(row.get("id") or row.get("name") or "unknown"),
            name=row.get("name"),
            region=row.get("region"),
            product=row.get("product"),
            squad=row.get("squad"),
            status=row.get("status"),
            labels={str(key): str(value) for key, value in (row.get("labels") or {}).items()},
        )

    def _metric(self, row: dict[str, Any]) -> MetricSignal:
        raw_ts = str(row.get("ts") or datetime.now(timezone.utc).isoformat()).replace("Z", "+00:00")
        return MetricSignal(
            name=str(row.get("name") or "value"),
            value=float(row.get("value") or 0),
            ts=datetime.fromisoformat(raw_ts),
            unit=str(row.get("unit") or ""),
            resource_id=row.get("resource_id"),
            product=row.get("product"),
            labels={str(key): str(value) for key, value in (row.get("labels") or {}).items()},
        )

    def _log(self, row: dict[str, Any]) -> LogSignal:
        raw_ts = str(row.get("ts") or datetime.now(timezone.utc).isoformat()).replace("Z", "+00:00")
        return LogSignal(
            ts=datetime.fromisoformat(raw_ts),
            severity=str(row.get("severity") or "info"),
            source=str(row.get("source") or self.id),
            message=str(row.get("message") or ""),
            product=row.get("product"),
            service=row.get("service"),
            trace_id=row.get("trace_id"),
            labels={str(key): str(value) for key, value in (row.get("labels") or {}).items()},
        )


CATALOG_SPECS = [
    # Cloud, hosting and platform
    ("alibaba-cloud", "Alibaba Cloud", "cloud", ["cost", "inventory"], "Alibaba Cloud billing and resource inventory via an Observa adapter."),
    ("ibm-cloud", "IBM Cloud", "cloud", ["cost", "inventory"], "IBM Cloud accounts, resources and billing via an Observa adapter."),
    ("openstack", "OpenStack", "cloud", ["cost", "inventory", "metrics"], "OpenStack projects, compute, storage and telemetry."),
    ("hetzner", "Hetzner Cloud", "cloud", ["cost", "inventory"], "Hetzner projects, servers and billing."),
    ("ovhcloud", "OVHcloud", "cloud", ["cost", "inventory"], "OVHcloud services, usage and billing."),
    ("scaleway", "Scaleway", "cloud", ["cost", "inventory"], "Scaleway resources and consumption."),
    ("vultr", "Vultr", "cloud", ["cost", "inventory"], "Vultr instances and account billing."),
    ("heroku", "Heroku", "cloud", ["cost", "inventory", "metrics"], "Heroku apps, dynos, add-ons and usage."),
    ("render", "Render", "cloud", ["cost", "inventory", "metrics"], "Render services, deploys and usage."),
    ("fly-io", "Fly.io", "cloud", ["cost", "inventory", "metrics"], "Fly.io applications, machines and billing."),
    ("railway", "Railway", "cloud", ["cost", "inventory", "metrics"], "Railway projects, services and usage."),
    ("vmware-vsphere", "VMware vSphere", "on_prem", ["inventory", "metrics"], "vCenter hosts, clusters and virtual machines."),
    ("proxmox", "Proxmox VE", "on_prem", ["inventory", "metrics", "power:write"], "Proxmox nodes, virtual machines and containers."),
    # Observability and reliability
    ("opentelemetry", "OpenTelemetry", "observability", ["metrics", "logs", "traces"], "OpenTelemetry metrics, logs and traces through a collector adapter."),
    ("dynatrace", "Dynatrace", "observability", ["inventory", "metrics", "logs"], "Dynatrace entities, problems, metrics and logs."),
    ("appdynamics", "AppDynamics", "observability", ["inventory", "metrics"], "AppDynamics applications, tiers, nodes and health."),
    ("honeycomb", "Honeycomb", "observability", ["metrics", "traces"], "Honeycomb datasets, SLOs and trace-derived signals."),
    ("chronosphere", "Chronosphere", "observability", ["metrics", "alerts"], "Chronosphere metrics, monitors and usage."),
    ("splunk-observability", "Splunk Observability Cloud", "observability", ["metrics", "traces", "alerts"], "Splunk Observability detectors, metrics and traces."),
    ("loki", "Grafana Loki", "observability", ["logs"], "Loki log streams and query results."),
    ("tempo", "Grafana Tempo", "observability", ["traces"], "Tempo distributed traces."),
    ("jaeger", "Jaeger", "observability", ["traces", "inventory"], "Jaeger services and distributed traces."),
    ("zipkin", "Zipkin", "observability", ["traces"], "Zipkin services, spans and traces."),
    ("victoriametrics", "VictoriaMetrics", "observability", ["metrics"], "VictoriaMetrics and VictoriaLogs telemetry."),
    ("influxdb", "InfluxDB", "observability", ["metrics"], "InfluxDB buckets and time-series metrics."),
    ("zabbix", "Zabbix", "observability", ["inventory", "metrics", "alerts"], "Zabbix hosts, problems and metrics."),
    ("nagios", "Nagios", "observability", ["inventory", "metrics", "alerts"], "Nagios hosts, services and status."),
    ("uptime-kuma", "Uptime Kuma", "observability", ["metrics", "alerts"], "Uptime Kuma monitors and heartbeat status."),
    # Incidents, work and collaboration
    ("servicenow", "ServiceNow", "incident", ["inventory", "alerts"], "ServiceNow incidents, changes and CMDB records."),
    ("jira-service-management", "Jira Service Management", "incident", ["inventory", "alerts"], "JSM incidents, requests and service projects."),
    ("better-uptime", "Better Stack", "incident", ["metrics", "alerts"], "Better Stack monitors, incidents and on-call data."),
    ("rootly", "Rootly", "incident", ["alerts", "inventory"], "Rootly incidents, services and retrospectives."),
    ("firehydrant", "FireHydrant", "incident", ["alerts", "inventory"], "FireHydrant incidents, services and runbooks."),
    ("xmatters", "xMatters", "incident", ["alerts", "inventory"], "xMatters incidents, services and on-call signals."),
    ("slack", "Slack", "collaboration", ["notifications", "inventory"], "Slack channels and Observa notification delivery."),
    ("microsoft-teams", "Microsoft Teams", "collaboration", ["notifications", "inventory"], "Teams channels and Observa notification delivery."),
    ("discord", "Discord", "collaboration", ["notifications"], "Discord channels and Observa webhook notifications."),
    ("jira", "Jira Software", "collaboration", ["inventory", "alerts"], "Jira projects, issues and operational work."),
    ("confluence", "Confluence", "collaboration", ["inventory"], "Confluence spaces and operational documentation."),
    ("notion", "Notion", "collaboration", ["inventory"], "Notion workspaces, databases and operational pages."),
    # Source control, delivery and automation
    ("azure-devops", "Azure DevOps", "vcs_cicd", ["cost", "inventory", "metrics"], "Azure Repos, Pipelines and Artifacts usage."),
    ("jenkins", "Jenkins", "vcs_cicd", ["inventory", "metrics"], "Jenkins jobs, builds, agents and queue health."),
    ("circleci", "CircleCI", "vcs_cicd", ["cost", "inventory", "metrics"], "CircleCI projects, pipelines and credits."),
    ("travis-ci", "Travis CI", "vcs_cicd", ["inventory", "metrics"], "Travis CI repositories and builds."),
    ("buildkite", "Buildkite", "vcs_cicd", ["cost", "inventory", "metrics"], "Buildkite pipelines, builds and agents."),
    ("teamcity", "TeamCity", "vcs_cicd", ["inventory", "metrics"], "TeamCity projects, builds and agents."),
    ("bamboo", "Bamboo", "vcs_cicd", ["inventory", "metrics"], "Bamboo plans, builds and agents."),
    ("argocd", "Argo CD", "automation", ["inventory", "metrics", "remediation:write"], "Argo CD applications, sync and health status."),
    ("fluxcd", "Flux CD", "automation", ["inventory", "metrics", "remediation:write"], "Flux resources, reconciliation and health."),
    ("tekton", "Tekton", "automation", ["inventory", "metrics"], "Tekton pipelines, tasks and runs."),
    ("spinnaker", "Spinnaker", "automation", ["inventory", "metrics"], "Spinnaker applications and delivery pipelines."),
    ("terraform-cloud", "Terraform Cloud", "automation", ["cost", "inventory", "metrics"], "Terraform workspaces, runs and state metadata."),
    ("pulumi", "Pulumi Cloud", "automation", ["inventory", "metrics"], "Pulumi stacks, updates and resource metadata."),
    ("harness", "Harness", "automation", ["cost", "inventory", "metrics"], "Harness services, pipelines and cloud cost signals."),
    # Data stores and streaming
    ("postgresql", "PostgreSQL", "database", ["inventory", "metrics"], "PostgreSQL databases, size, activity and performance."),
    ("mysql", "MySQL", "database", ["inventory", "metrics"], "MySQL databases, activity and performance."),
    ("mariadb", "MariaDB", "database", ["inventory", "metrics"], "MariaDB databases, activity and performance."),
    ("sql-server", "Microsoft SQL Server", "database", ["inventory", "metrics"], "SQL Server databases, waits and performance."),
    ("redis", "Redis", "database", ["inventory", "metrics"], "Redis instances, memory, clients and keyspace metrics."),
    ("opensearch", "OpenSearch", "database", ["inventory", "metrics", "logs"], "OpenSearch clusters, indices and health."),
    ("clickhouse", "ClickHouse", "database", ["inventory", "metrics"], "ClickHouse clusters, databases and query metrics."),
    ("apache-kafka", "Apache Kafka", "data", ["inventory", "metrics"], "Kafka clusters, topics, consumer lag and brokers."),
    ("confluent-cloud", "Confluent Cloud", "data", ["cost", "inventory", "metrics"], "Confluent clusters, topics, connectors and billing."),
    ("rabbitmq", "RabbitMQ", "data", ["inventory", "metrics"], "RabbitMQ nodes, queues and message rates."),
    ("nats", "NATS", "data", ["inventory", "metrics"], "NATS servers, streams and consumers."),
    ("databricks", "Databricks", "data", ["cost", "inventory", "metrics"], "Databricks workspaces, clusters, jobs and DBUs."),
    ("dbt-cloud", "dbt Cloud", "data", ["cost", "inventory", "metrics"], "dbt projects, jobs and run status."),
    ("supabase", "Supabase", "data", ["cost", "inventory", "metrics"], "Supabase projects, databases and usage."),
    ("firebase", "Firebase", "data", ["cost", "inventory", "metrics"], "Firebase projects, products and usage."),
    # Security and identity
    ("wiz", "Wiz", "security", ["inventory", "alerts"], "Wiz cloud assets, issues and security posture."),
    ("prisma-cloud", "Prisma Cloud", "security", ["inventory", "alerts"], "Prisma Cloud assets, findings and posture."),
    ("crowdstrike", "CrowdStrike Falcon", "security", ["inventory", "alerts"], "Falcon hosts, detections and incidents."),
    ("okta", "Okta", "security", ["inventory", "logs"], "Okta users, applications and system events."),
    ("auth0", "Auth0", "security", ["inventory", "logs"], "Auth0 tenants, clients and authentication logs."),
    ("keycloak", "Keycloak", "security", ["inventory", "logs"], "Keycloak realms, clients and authentication events."),
    ("sonarqube", "SonarQube", "security", ["inventory", "metrics", "alerts"], "SonarQube projects, quality gates and findings."),
    ("snyk", "Snyk", "security", ["inventory", "alerts"], "Snyk projects, vulnerabilities and fixable issues."),
    ("trivy", "Trivy", "security", ["inventory", "alerts"], "Trivy vulnerability and misconfiguration reports."),
    ("falco", "Falco", "security", ["logs", "alerts"], "Falco runtime security events."),
    ("gitguardian", "GitGuardian", "security", ["inventory", "alerts"], "GitGuardian secret incidents and perimeter findings."),
]


ADAPTER_CATALOG = [AdapterCatalogConnector(*spec) for spec in CATALOG_SPECS]
