from __future__ import annotations

from typing import Any

from observa_connectors.base import BaseConnector, PullResult, TestResult


class _StubConnector(BaseConnector):
    """UI-ready stub — credential form + catalog entry work now; `pull()` ships next.

    Use this for connectors that are in the catalog (so clients can already
    see the tool, its icon, and fill in credentials) but whose real API
    integration hasn't been wired up yet. Swap `_StubConnector` for
    `BaseConnector` and implement `test_connection`/`pull` the same way the
    ones in `providers/` do, once you're ready.
    """

    def test_connection(self, config: dict[str, Any], secrets: dict[str, Any]) -> TestResult:
        return TestResult(
            ok=False,
            message="Connector stub: credential form works; data pull ships in a future release.",
        )

    def pull(self, config: dict[str, Any], secrets: dict[str, Any], *, since=None) -> PullResult:
        raise NotImplementedError(self.id)


class OciStub(_StubConnector):
    id = "oci"
    name = "Oracle Cloud (OCI)"
    description = "Oracle Cloud Infrastructure cost and inventory."
    capabilities = ["cost", "inventory"]
    category = "cloud"
    icon = "oci"
    docs_url = "https://docs.oracle.com/en-us/iaas/Content/API/Concepts/apisigningkey.htm"

    def config_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "tenancy_ocid": {"type": "string", "title": "Tenancy OCID"},
                "region": {"type": "string", "title": "Region", "default": "us-ashburn-1"},
            },
            "required": ["tenancy_ocid"],
        }

    def secrets_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "user_ocid": {"type": "string", "title": "User OCID"},
                "fingerprint": {"type": "string", "title": "API key fingerprint"},
                "private_key": {"type": "string", "title": "API private key (PEM)"},
            },
            "required": ["user_ocid", "fingerprint", "private_key"],
        }


class LinodeStub(_StubConnector):
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


class NetlifyStub(_StubConnector):
    id = "netlify"
    name = "Netlify"
    description = "Site inventory and build minutes usage."
    capabilities = ["inventory", "cost"]
    category = "cloud"
    icon = "netlify"
    docs_url = "https://docs.netlify.com/api/get-started/#authentication"

    def config_schema(self) -> dict[str, Any]:
        return {"type": "object", "properties": {}}

    def secrets_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {"token": {"type": "string", "title": "Personal access token (PAT)"}},
            "required": ["token"],
        }


class GrafanaCloudStub(_StubConnector):
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


class ElasticCloudStub(_StubConnector):
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


class SnowflakeStub(_StubConnector):
    id = "snowflake"
    name = "Snowflake"
    description = "Warehouse credit usage and storage cost."
    capabilities = ["cost"]
    category = "saas"
    icon = "snowflake"
    docs_url = "https://docs.snowflake.com/en/user-guide/key-pair-auth"

    def config_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "account": {"type": "string", "title": "Account identifier"},
                "warehouse": {"type": "string", "title": "Warehouse"},
            },
            "required": ["account"],
        }

    def secrets_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "user": {"type": "string", "title": "User"},
                "private_key": {"type": "string", "title": "Key-pair private key (PEM)"},
            },
            "required": ["user", "private_key"],
        }


class SplunkStub(_StubConnector):
    id = "splunk"
    name = "Splunk (on-premise / Cloud)"
    description = "Index volume and license usage via the Splunk REST API."
    capabilities = ["metrics", "inventory"]
    category = "on_prem"
    icon = "splunk"
    docs_url = "https://docs.splunk.com/Documentation/Splunk/latest/Security/Setuptokenauthentication"

    def config_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {"base_url": {"type": "string", "title": "Splunk management URL"}},
            "required": ["base_url"],
        }

    def secrets_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {"token": {"type": "string", "title": "Auth token"}},
            "required": ["token"],
        }


class OpsgenieStub(_StubConnector):
    id = "opsgenie"
    name = "Opsgenie"
    description = "Alerts and on-call schedules as inventory."
    capabilities = ["inventory", "metrics"]
    category = "incident"
    icon = "opsgenie"
    docs_url = "https://support.atlassian.com/opsgenie/docs/api-key-management/"

    def config_schema(self) -> dict[str, Any]:
        return {"type": "object", "properties": {}}

    def secrets_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {"api_key": {"type": "string", "title": "API key"}},
            "required": ["api_key"],
        }


class BitbucketStub(_StubConnector):
    id = "bitbucket"
    name = "Bitbucket"
    description = "Workspace repos and pipeline minutes."
    capabilities = ["inventory", "cost"]
    category = "vcs_cicd"
    icon = "bitbucket"
    docs_url = "https://support.atlassian.com/bitbucket-cloud/docs/app-passwords/"

    def config_schema(self) -> dict[str, Any]:
        return {"type": "object", "properties": {"workspace": {"type": "string", "title": "Workspace"}}, "required": ["workspace"]}

    def secrets_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "username": {"type": "string", "title": "Username"},
                "app_password": {"type": "string", "title": "App password"},
            },
            "required": ["username", "app_password"],
        }
