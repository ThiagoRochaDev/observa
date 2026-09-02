from __future__ import annotations

from typing import Any

from observa_connectors.base import BaseConnector, PullResult, ResourceSignal, TestResult
from observa_connectors.http import request_json


class BitbucketConnector(BaseConnector):
    id = "bitbucket"
    name = "Bitbucket"
    description = "Workspace repos and pipeline minutes."
    capabilities = ["inventory", "cost"]
    category = "vcs_cicd"
    icon = "bitbucket"
    docs_url = "https://support.atlassian.com/bitbucket-cloud/docs/app-passwords/"

    def config_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {"workspace": {"type": "string", "title": "Workspace"}},
            "required": ["workspace"],
        }

    def secrets_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "username": {"type": "string", "title": "Username"},
                "app_password": {"type": "string", "title": "App password"},
            },
            "required": ["username", "app_password"],
        }

    def _auth(self, secrets: dict[str, Any]) -> tuple[str, str]:
        return (secrets.get("username", ""), secrets.get("app_password", ""))

    def test_connection(self, config: dict[str, Any], secrets: dict[str, Any]) -> TestResult:
        workspace = config.get("workspace", "")
        status, body = request_json(
            "GET", f"https://api.bitbucket.org/2.0/workspaces/{workspace}", auth=self._auth(secrets)
        )
        if status == 200:
            return TestResult(ok=True, message="Credentials valid.")
        return TestResult(ok=False, message=f"HTTP {status}: {str(body)[:300]}")

    def pull(self, config: dict[str, Any], secrets: dict[str, Any], *, since=None) -> PullResult:
        workspace = config.get("workspace", "")
        auth = self._auth(secrets)
        resources: list[ResourceSignal] = []
        url = f"https://api.bitbucket.org/2.0/repositories/{workspace}"
        page_guard = 0
        while url and page_guard < 20:
            page_guard += 1
            status, body = request_json("GET", url, auth=auth, params={"pagelen": 100})
            if status != 200 or not isinstance(body, dict):
                break
            for repo in body.get("values", []):
                resources.append(
                    ResourceSignal(
                        provider="bitbucket",
                        type="repository",
                        id=repo.get("uuid") or repo.get("slug", ""),
                        name=repo.get("full_name") or repo.get("name"),
                        status="private" if repo.get("is_private") else "public",
                        labels={"language": repo.get("language") or ""},
                    )
                )
            url = body.get("next")

        return PullResult(resources=resources, message=f"{len(resources)} repositories")
