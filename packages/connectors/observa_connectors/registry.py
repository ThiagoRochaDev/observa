from __future__ import annotations

from observa_connectors.base import BaseConnector
from observa_connectors.mock_demo import MockDemoConnector
from observa_connectors.providers.aws import AwsCostConnector
from observa_connectors.providers.azure import AzureCostConnector
from observa_connectors.providers.bitbucket import BitbucketConnector
from observa_connectors.providers.datadog import DatadogConnector
from observa_connectors.providers.elastic_cloud import ElasticCloudConnector
from observa_connectors.providers.gcp import GcpBillingConnector
from observa_connectors.providers.grafana_cloud import GrafanaCloudConnector
from observa_connectors.providers.linode import LinodeConnector
from observa_connectors.providers.netlify import NetlifyConnector
from observa_connectors.providers.oci import OciConnector
from observa_connectors.providers.onprem import (
    KubernetesConnector,
    OnPremAgentConnector,
    PrometheusConnector,
)
from observa_connectors.providers.opsgenie import OpsgenieConnector
from observa_connectors.providers.saas import (
    CloudflareConnector,
    DigitalOceanConnector,
    GitHubConnector,
    GitLabConnector,
    MongoDbAtlasConnector,
    NewRelicConnector,
    PagerDutyConnector,
    SentryConnector,
    StripeConnector,
    VercelConnector,
)
from observa_connectors.providers.snowflake import SnowflakeConnector
from observa_connectors.providers.splunk import SplunkConnector

# Ordered roughly: demo first, then the big public clouds, then everything else
# grouped by category. `apps/web` groups these by `.category` for the catalog UI.
_CONNECTORS: list[BaseConnector] = [
    MockDemoConnector(),
    # Cloud
    AwsCostConnector(),
    GcpBillingConnector(),
    AzureCostConnector(),
    OciConnector(),
    DigitalOceanConnector(),
    LinodeConnector(),
    CloudflareConnector(),
    VercelConnector(),
    NetlifyConnector(),
    MongoDbAtlasConnector(),
    # Observability / APM
    DatadogConnector(),
    NewRelicConnector(),
    GrafanaCloudConnector(),
    ElasticCloudConnector(),
    SentryConnector(),
    # Incident management
    PagerDutyConnector(),
    OpsgenieConnector(),
    # VCS / CI-CD
    GitHubConnector(),
    GitLabConnector(),
    BitbucketConnector(),
    # On-premise / self-hosted
    KubernetesConnector(),
    PrometheusConnector(),
    SplunkConnector(),
    OnPremAgentConnector(),
    # Billing / data SaaS
    StripeConnector(),
    SnowflakeConnector(),
]


def list_connectors() -> list[BaseConnector]:
    return list(_CONNECTORS)


def get_connector(connector_id: str) -> BaseConnector | None:
    for c in _CONNECTORS:
        if c.id == connector_id:
            return c
    return None
