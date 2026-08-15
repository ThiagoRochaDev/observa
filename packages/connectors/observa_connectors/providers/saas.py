from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from observa_connectors.base import (
    BaseConnector,
    CostSignal,
    PullResult,
    ResourceSignal,
    TestResult,
)
from observa_connectors.http import request_json


class GitHubConnector(BaseConnector):
    id = "github"
    name = "GitHub"
    description = "Org repos as inventory, plus Actions/Packages/Storage billing (org PAT)."
    capabilities = ["cost", "inventory"]
    category = "vcs_cicd"
    icon = "github"
    docs_url = "https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens"

    def config_schema(self) -> dict[str, Any]:
        return {"type": "object", "properties": {"org": {"type": "string", "title": "Organization"}}, "required": ["org"]}

    def secrets_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {"token": {"type": "string", "title": "Personal access token (PAT)"}},
            "required": ["token"],
        }

    def _headers(self, secrets: dict[str, Any]) -> dict[str, str]:
        return {"Authorization": f"Bearer {secrets.get('token', '')}", "Accept": "application/vnd.github+json"}

    def test_connection(self, config: dict[str, Any], secrets: dict[str, Any]) -> TestResult:
        status, body = request_json("GET", "https://api.github.com/user", headers=self._headers(secrets))
        if status == 200:
            return TestResult(ok=True, message=f"Authenticated as {body.get('login')}")
        return TestResult(ok=False, message=f"HTTP {status}: {str(body)[:300]}")

    def pull(self, config, secrets, *, since=None) -> PullResult:
        org = config["org"]
        headers = self._headers(secrets)
        resources: list[ResourceSignal] = []
        page = 1
        while page <= 5:
            status, body = request_json(
                "GET", f"https://api.github.com/orgs/{org}/repos", headers=headers,
                params={"per_page": 100, "page": page},
            )
            if status != 200 or not isinstance(body, list) or not body:
                break
            for repo in body:
                resources.append(
                    ResourceSignal(
                        provider="github", type="repo", id=str(repo["id"]), name=repo["full_name"],
                        status="archived" if repo.get("archived") else "active",
                        labels={"visibility": repo.get("visibility", "")},
                    )
                )
            page += 1

        costs: list[CostSignal] = []
        status, body = request_json(
            "GET", f"https://api.github.com/orgs/{org}/settings/billing/actions", headers=headers
        )
        if status == 200 and isinstance(body, dict):
            minutes = body.get("total_minutes_used", 0)
            costs.append(
                CostSignal(
                    date=date.today(), provider="github", amount=float(minutes), currency="minutes",
                    service="actions", account=org,
                )
            )
        return PullResult(costs=costs, resources=resources, message=f"{len(resources)} repos")


class GitLabConnector(BaseConnector):
    id = "gitlab"
    name = "GitLab"
    description = "Group/project inventory and CI pipeline minutes (PAT)."
    capabilities = ["cost", "inventory"]
    category = "vcs_cicd"
    icon = "gitlab"
    docs_url = "https://docs.gitlab.com/ee/user/profile/personal_access_tokens.html"

    def config_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "base_url": {"type": "string", "title": "GitLab URL", "default": "https://gitlab.com"},
                "group": {"type": "string", "title": "Group (optional — all visible projects if empty)"},
            },
        }

    def secrets_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {"token": {"type": "string", "title": "Personal access token (PAT)"}},
            "required": ["token"],
        }

    def _headers(self, secrets: dict[str, Any]) -> dict[str, str]:
        return {"PRIVATE-TOKEN": secrets.get("token", "")}

    def test_connection(self, config: dict[str, Any], secrets: dict[str, Any]) -> TestResult:
        base = (config.get("base_url") or "https://gitlab.com").rstrip("/")
        status, body = request_json("GET", f"{base}/api/v4/user", headers=self._headers(secrets))
        if status == 200:
            return TestResult(ok=True, message=f"Authenticated as {body.get('username')}")
        return TestResult(ok=False, message=f"HTTP {status}: {str(body)[:300]}")

    def pull(self, config, secrets, *, since=None) -> PullResult:
        base = (config.get("base_url") or "https://gitlab.com").rstrip("/")
        headers = self._headers(secrets)
        group = config.get("group")
        url = f"{base}/api/v4/groups/{group}/projects" if group else f"{base}/api/v4/projects"
        status, body = request_json("GET", url, headers=headers, params={"membership": True, "per_page": 100})
        resources: list[ResourceSignal] = []
        if status == 200 and isinstance(body, list):
            for p in body:
                resources.append(
                    ResourceSignal(
                        provider="gitlab", type="project", id=str(p["id"]), name=p.get("path_with_namespace"),
                        status="archived" if p.get("archived") else "active",
                    )
                )
        return PullResult(resources=resources, message=f"{len(resources)} projects")


class CloudflareConnector(BaseConnector):
    id = "cloudflare"
    name = "Cloudflare"
    description = "Zones and plan tier as inventory (API token)."
    capabilities = ["inventory"]
    category = "cloud"
    icon = "cloudflare"
    docs_url = "https://developers.cloudflare.com/fundamentals/api/get-started/create-token/"

    def config_schema(self) -> dict[str, Any]:
        return {"type": "object", "properties": {}}

    def secrets_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {"api_token": {"type": "string", "title": "API token"}},
            "required": ["api_token"],
        }

    def _headers(self, secrets: dict[str, Any]) -> dict[str, str]:
        return {"Authorization": f"Bearer {secrets.get('api_token', '')}"}

    def test_connection(self, config: dict[str, Any], secrets: dict[str, Any]) -> TestResult:
        status, body = request_json(
            "GET", "https://api.cloudflare.com/client/v4/user/tokens/verify", headers=self._headers(secrets)
        )
        if status == 200 and isinstance(body, dict) and body.get("success"):
            return TestResult(ok=True, message="Token is valid.")
        return TestResult(ok=False, message=f"HTTP {status}: {str(body)[:300]}")

    def pull(self, config, secrets, *, since=None) -> PullResult:
        status, body = request_json(
            "GET", "https://api.cloudflare.com/client/v4/zones", headers=self._headers(secrets),
            params={"per_page": 50},
        )
        resources: list[ResourceSignal] = []
        if status == 200 and isinstance(body, dict):
            for z in body.get("result", []):
                resources.append(
                    ResourceSignal(
                        provider="cloudflare", type="zone", id=z["id"], name=z.get("name"),
                        status=z.get("status"), labels={"plan": z.get("plan", {}).get("name", "")},
                    )
                )
        return PullResult(resources=resources, message=f"{len(resources)} zones")


class DigitalOceanConnector(BaseConnector):
    id = "digitalocean"
    name = "DigitalOcean"
    description = "Droplet inventory and month-to-date billing (PAT)."
    capabilities = ["cost", "inventory"]
    category = "cloud"
    icon = "digitalocean"
    docs_url = "https://docs.digitalocean.com/reference/api/create-personal-access-token/"

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
        status, body = request_json("GET", "https://api.digitalocean.com/v2/account", headers=self._headers(secrets))
        if status == 200:
            return TestResult(ok=True, message="Token is valid.")
        return TestResult(ok=False, message=f"HTTP {status}: {str(body)[:300]}")

    def pull(self, config, secrets, *, since=None) -> PullResult:
        headers = self._headers(secrets)
        resources: list[ResourceSignal] = []
        status, body = request_json("GET", "https://api.digitalocean.com/v2/droplets", headers=headers, params={"per_page": 100})
        if status == 200 and isinstance(body, dict):
            for d in body.get("droplets", []):
                resources.append(
                    ResourceSignal(
                        provider="digitalocean", type="droplet", id=str(d["id"]), name=d.get("name"),
                        region=d.get("region", {}).get("slug"), status=d.get("status"),
                    )
                )
        costs: list[CostSignal] = []
        status, body = request_json("GET", "https://api.digitalocean.com/v2/customers/my/balance", headers=headers)
        if status == 200 and isinstance(body, dict):
            costs.append(
                CostSignal(
                    date=date.today(), provider="digitalocean",
                    amount=float(body.get("month_to_date_usage") or 0), currency="USD",
                )
            )
        return PullResult(costs=costs, resources=resources, message=f"{len(resources)} droplets")


class PagerDutyConnector(BaseConnector):
    id = "pagerduty"
    name = "PagerDuty"
    description = "Open incidents and services as inventory (API token) — incident/health, not cost."
    capabilities = ["inventory", "metrics"]
    category = "incident"
    icon = "pagerduty"
    docs_url = "https://support.pagerduty.com/docs/generating-api-keys"

    def config_schema(self) -> dict[str, Any]:
        return {"type": "object", "properties": {}}

    def secrets_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {"api_token": {"type": "string", "title": "API token"}},
            "required": ["api_token"],
        }

    def _headers(self, secrets: dict[str, Any]) -> dict[str, str]:
        return {"Authorization": f"Token token={secrets.get('api_token', '')}", "Accept": "application/vnd.pagerduty+json;version=2"}

    def test_connection(self, config: dict[str, Any], secrets: dict[str, Any]) -> TestResult:
        status, body = request_json("GET", "https://api.pagerduty.com/users/me", headers=self._headers(secrets))
        if status == 200:
            return TestResult(ok=True, message="Token is valid.")
        return TestResult(ok=False, message=f"HTTP {status}: {str(body)[:300]}")

    def pull(self, config, secrets, *, since=None) -> PullResult:
        headers = self._headers(secrets)
        resources: list[ResourceSignal] = []
        status, body = request_json("GET", "https://api.pagerduty.com/services", headers=headers, params={"limit": 100})
        if status == 200 and isinstance(body, dict):
            for s in body.get("services", []):
                resources.append(
                    ResourceSignal(
                        provider="pagerduty", type="service", id=s["id"], name=s.get("name"),
                        status=s.get("status"),
                    )
                )
        from observa_connectors.base import MetricSignal

        metrics: list[MetricSignal] = []
        status, body = request_json(
            "GET", "https://api.pagerduty.com/incidents", headers=headers,
            params={"statuses[]": "triggered", "limit": 1},
        )
        if status == 200 and isinstance(body, dict):
            metrics.append(
                MetricSignal(
                    name="pagerduty.incidents.triggered", value=float(body.get("total", 0)),
                    ts=datetime.now(timezone.utc), unit="count",
                )
            )
        return PullResult(resources=resources, metrics=metrics, message=f"{len(resources)} services")


class SentryConnector(BaseConnector):
    id = "sentry"
    name = "Sentry"
    description = "Project inventory and unresolved issue counts (auth token)."
    capabilities = ["inventory", "metrics"]
    category = "observability"
    icon = "sentry"
    docs_url = "https://docs.sentry.io/api/auth/"

    def config_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {"org_slug": {"type": "string", "title": "Organization slug"}},
            "required": ["org_slug"],
        }

    def secrets_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {"auth_token": {"type": "string", "title": "Auth token"}},
            "required": ["auth_token"],
        }

    def _headers(self, secrets: dict[str, Any]) -> dict[str, str]:
        return {"Authorization": f"Bearer {secrets.get('auth_token', '')}"}

    def test_connection(self, config: dict[str, Any], secrets: dict[str, Any]) -> TestResult:
        status, body = request_json(
            "GET", f"https://sentry.io/api/0/organizations/{config.get('org_slug', '')}/",
            headers=self._headers(secrets),
        )
        if status == 200:
            return TestResult(ok=True, message="Token is valid.")
        return TestResult(ok=False, message=f"HTTP {status}: {str(body)[:300]}")

    def pull(self, config, secrets, *, since=None) -> PullResult:
        headers = self._headers(secrets)
        org = config["org_slug"]
        resources: list[ResourceSignal] = []
        status, body = request_json(
            "GET", f"https://sentry.io/api/0/organizations/{org}/projects/", headers=headers
        )
        if status == 200 and isinstance(body, list):
            for p in body:
                resources.append(
                    ResourceSignal(provider="sentry", type="project", id=str(p["id"]), name=p.get("slug"))
                )
        return PullResult(resources=resources, message=f"{len(resources)} projects")


class VercelConnector(BaseConnector):
    id = "vercel"
    name = "Vercel"
    description = "Project inventory and usage (access token)."
    capabilities = ["inventory", "cost"]
    category = "cloud"
    icon = "vercel"
    docs_url = "https://vercel.com/docs/rest-api#creating-an-access-token"

    def config_schema(self) -> dict[str, Any]:
        return {"type": "object", "properties": {"team_id": {"type": "string", "title": "Team ID (optional)"}}}

    def secrets_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {"token": {"type": "string", "title": "Access token"}},
            "required": ["token"],
        }

    def _headers(self, secrets: dict[str, Any]) -> dict[str, str]:
        return {"Authorization": f"Bearer {secrets.get('token', '')}"}

    def test_connection(self, config: dict[str, Any], secrets: dict[str, Any]) -> TestResult:
        status, body = request_json("GET", "https://api.vercel.com/v2/user", headers=self._headers(secrets))
        if status == 200:
            return TestResult(ok=True, message="Token is valid.")
        return TestResult(ok=False, message=f"HTTP {status}: {str(body)[:300]}")

    def pull(self, config, secrets, *, since=None) -> PullResult:
        headers = self._headers(secrets)
        params = {"teamId": config["team_id"]} if config.get("team_id") else {}
        resources: list[ResourceSignal] = []
        status, body = request_json("GET", "https://api.vercel.com/v9/projects", headers=headers, params=params)
        if status == 200 and isinstance(body, dict):
            for p in body.get("projects", []):
                resources.append(ResourceSignal(provider="vercel", type="project", id=p["id"], name=p.get("name")))
        return PullResult(resources=resources, message=f"{len(resources)} projects")


class StripeConnector(BaseConnector):
    id = "stripe"
    name = "Stripe"
    description = "Balance and recent charges (secret key) — useful for revenue-vs-cost views."
    capabilities = ["cost"]
    category = "saas"
    icon = "stripe"
    docs_url = "https://docs.stripe.com/keys"

    def config_schema(self) -> dict[str, Any]:
        return {"type": "object", "properties": {}}

    def secrets_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {"secret_key": {"type": "string", "title": "Secret key (sk_live_... / sk_test_...)"}},
            "required": ["secret_key"],
        }

    def test_connection(self, config: dict[str, Any], secrets: dict[str, Any]) -> TestResult:
        status, body = request_json(
            "GET", "https://api.stripe.com/v1/balance", auth=(secrets.get("secret_key", ""), "")
        )
        if status == 200:
            return TestResult(ok=True, message="Key is valid.")
        return TestResult(ok=False, message=f"HTTP {status}: {str(body)[:300]}")

    def pull(self, config, secrets, *, since=None) -> PullResult:
        auth = (secrets.get("secret_key", ""), "")
        status, body = request_json(
            "GET", "https://api.stripe.com/v1/charges", auth=auth, params={"limit": 100}
        )
        costs: list[CostSignal] = []
        if status == 200 and isinstance(body, dict):
            for c in body.get("data", []):
                costs.append(
                    CostSignal(
                        date=date.fromtimestamp(c["created"], tz=timezone.utc).date(),
                        provider="stripe", amount=c["amount"] / 100.0, currency=c.get("currency", "usd").upper(),
                        service="charges",
                    )
                )
        return PullResult(costs=costs, message=f"{len(costs)} charges")


class NewRelicConnector(BaseConnector):
    id = "newrelic"
    name = "New Relic"
    description = "Applications and alert conditions as inventory (User API key)."
    capabilities = ["inventory", "metrics"]
    category = "observability"
    icon = "newrelic"
    docs_url = "https://docs.newrelic.com/docs/apis/intro-apis/new-relic-api-keys/"

    def config_schema(self) -> dict[str, Any]:
        return {"type": "object", "properties": {}}

    def secrets_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {"api_key": {"type": "string", "title": "User API key"}},
            "required": ["api_key"],
        }

    def _headers(self, secrets: dict[str, Any]) -> dict[str, str]:
        return {"Api-Key": secrets.get("api_key", "")}

    def test_connection(self, config: dict[str, Any], secrets: dict[str, Any]) -> TestResult:
        status, body = request_json(
            "GET", "https://api.newrelic.com/v2/applications.json", headers=self._headers(secrets)
        )
        if status == 200:
            return TestResult(ok=True, message="API key is valid.")
        return TestResult(ok=False, message=f"HTTP {status}: {str(body)[:300]}")

    def pull(self, config, secrets, *, since=None) -> PullResult:
        status, body = request_json(
            "GET", "https://api.newrelic.com/v2/applications.json", headers=self._headers(secrets)
        )
        resources: list[ResourceSignal] = []
        if status == 200 and isinstance(body, dict):
            for app in body.get("applications", []):
                resources.append(
                    ResourceSignal(
                        provider="newrelic", type="application", id=str(app["id"]), name=app.get("name"),
                        status=app.get("health_status"),
                    )
                )
        return PullResult(resources=resources, message=f"{len(resources)} applications")


class MongoDbAtlasConnector(BaseConnector):
    id = "mongodb-atlas"
    name = "MongoDB Atlas"
    description = "Cluster inventory and invoices (public/private API key, digest auth)."
    capabilities = ["cost", "inventory"]
    category = "cloud"
    icon = "mongodb"
    docs_url = "https://www.mongodb.com/docs/atlas/configure-api-access/"

    def config_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {"project_id": {"type": "string", "title": "Project (group) ID"}},
            "required": ["project_id"],
        }

    def secrets_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "public_key": {"type": "string", "title": "Public API key"},
                "private_key": {"type": "string", "title": "Private API key"},
            },
            "required": ["public_key", "private_key"],
        }

    def _auth(self, secrets: dict[str, Any]):
        return (secrets.get("public_key", ""), secrets.get("private_key", ""))

    def test_connection(self, config: dict[str, Any], secrets: dict[str, Any]) -> TestResult:
        status, body = request_json(
            "GET", f"https://cloud.mongodb.com/api/atlas/v2/groups/{config.get('project_id', '')}/clusters",
            auth=self._auth(secrets), headers={"Accept": "application/vnd.atlas.2023-11-15+json"},
        )
        if status == 200:
            return TestResult(ok=True, message="Credentials are valid.")
        return TestResult(ok=False, message=f"HTTP {status}: {str(body)[:300]}")

    def pull(self, config, secrets, *, since=None) -> PullResult:
        project = config["project_id"]
        status, body = request_json(
            "GET", f"https://cloud.mongodb.com/api/atlas/v2/groups/{project}/clusters",
            auth=self._auth(secrets), headers={"Accept": "application/vnd.atlas.2023-11-15+json"},
        )
        resources: list[ResourceSignal] = []
        if status == 200 and isinstance(body, dict):
            for c in body.get("results", []):
                resources.append(
                    ResourceSignal(
                        provider="mongodb-atlas", type="cluster", id=c.get("id", c.get("name", "")),
                        name=c.get("name"), status=c.get("stateName"),
                    )
                )
        return PullResult(resources=resources, message=f"{len(resources)} clusters")
