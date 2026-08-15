from __future__ import annotations

from observa_connectors.base import BaseConnector
from observa_connectors.mock_demo import MockDemoConnector
from observa_connectors.providers.aws import AwsCostConnector
from observa_connectors.providers.azure import AzureCostConnector
from observa_connectors.providers.datadog import DatadogConnector
from observa_connectors.providers.gcp import GcpBillingConnector
from observa_connectors.providers.onprem import (
    KubernetesConnector,
    OnPremAgentConnector,
    PrometheusConnector,
)
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
from observa_connectors.stubs import (
    BitbucketStub,
    ElasticCloudStub,
    GrafanaCloudStub,
    LinodeStub,
    NetlifyStub,
    OciStub,
    OpsgenieStub,
    SnowflakeStub,
    SplunkStub,
)

# Ordered roughly: demo first, then the big public clouds, then everything else
# grouped by category. `apps/web` groups these by `.category` for the catalog UI.
_CONNECTORS: list[BaseConnector] = [
    MockDemoConnector(),
    # Cloud
    AwsCostConnector(),
    GcpBillingConnector(),
    AzureCostConnector(),
    OciStub(),
    DigitalOceanConnector(),
    LinodeStub(),
    CloudflareConnector(),
    VercelConnector(),
    NetlifyStub(),
    MongoDbAtlasConnector(),
    # Observability / APM
    DatadogConnector(),
    NewRelicConnector(),
    GrafanaCloudStub(),
    ElasticCloudStub(),
    SentryConnector(),
    # Incident management
    PagerDutyConnector(),
    OpsgenieStub(),
    # VCS / CI-CD
    GitHubConnector(),
    GitLabConnector(),
    BitbucketStub(),
    # On-premise / self-hosted
    KubernetesConnector(),
    PrometheusConnector(),
    SplunkStub(),
    OnPremAgentConnector(),
    # Billing / data SaaS
    StripeConnector(),
    SnowflakeStub(),
]


def list_connectors() -> list[BaseConnector]:
    return list(_CONNECTORS)


def get_connector(connector_id: str) -> BaseConnector | None:
    for c in _CONNECTORS:
        if c.id == connector_id:
            return c
    return None
