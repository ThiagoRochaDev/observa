from __future__ import annotations

import json
from datetime import date, datetime, timezone
from typing import Any
from urllib.parse import urlparse

from observa_connectors.base import (
    BaseConnector,
    CostSignal,
    LogSignal,
    MetricSignal,
    PullResult,
    ResourceSignal,
    TestResult,
)

DEFAULT_PROTOCOL_VERSION = "2026-07-28"


def _rpc(
    endpoint: str,
    method: str,
    params: dict[str, Any],
    *,
    token: str = "",
    protocol_version: str = DEFAULT_PROTOCOL_VERSION,
) -> tuple[int, dict[str, Any]]:
    import requests

    headers = {
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json",
        "MCP-Protocol-Version": protocol_version,
        "Mcp-Method": method,
    }
    if method == "tools/call" and params.get("name"):
        headers["Mcp-Name"] = str(params["name"])
    if token:
        headers["Authorization"] = f"Bearer {token}"

    payload = {
        "jsonrpc": "2.0",
        "id": "observa",
        "method": method,
        "params": {
            **params,
            "_meta": {
                "io.modelcontextprotocol/clientInfo": {
                    "name": "observa",
                    "version": "0.1.0",
                }
            },
        },
    }
    response = requests.post(endpoint, headers=headers, json=payload, timeout=30)
    content_type = response.headers.get("content-type", "")
    if "text/event-stream" in content_type:
        for line in response.text.splitlines():
            if line.startswith("data:"):
                event = json.loads(line[5:].strip())
                if isinstance(event, dict) and ("result" in event or "error" in event):
                    return response.status_code, event
        return response.status_code, {"error": {"message": "MCP stream returned no JSON-RPC result."}}
    try:
        body = response.json()
    except ValueError:
        body = {"error": {"message": response.text[:500]}}
    return response.status_code, body if isinstance(body, dict) else {"result": body}


class McpConnector(BaseConnector):
    id = "mcp"
    name = "Model Context Protocol (MCP)"
    description = "Discover and call a remote MCP tool that returns Observa canonical signals."
    capabilities = ["cost", "inventory", "metrics", "logs", "mcp:tools"]
    category = "automation"
    icon = "mcp"
    docs_url = "https://modelcontextprotocol.io/docs/getting-started/intro"

    def config_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "endpoint": {"type": "string", "title": "MCP Streamable HTTP endpoint"},
                "tool_name": {"type": "string", "title": "Ingestion tool name", "default": "observa_pull"},
                "tool_arguments_json": {"type": "string", "title": "Tool arguments (JSON)", "default": "{}"},
                "protocol_version": {
                    "type": "string",
                    "title": "MCP protocol version",
                    "default": DEFAULT_PROTOCOL_VERSION,
                },
            },
            "required": ["endpoint", "tool_name"],
        }

    def secrets_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "bearer_token": {"type": "string", "title": "Bearer token (optional)"},
            },
        }

    @staticmethod
    def _validated_endpoint(config: dict[str, Any]) -> str:
        endpoint = str(config.get("endpoint") or "")
        parsed = urlparse(endpoint)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("MCP endpoint must be an http:// or https:// URL.")
        return endpoint

    @staticmethod
    def _protocol(config: dict[str, Any]) -> str:
        return str(config.get("protocol_version") or DEFAULT_PROTOCOL_VERSION)

    @staticmethod
    def _token(secrets: dict[str, Any]) -> str:
        return str(secrets.get("bearer_token") or "")

    def test_connection(self, config: dict[str, Any], secrets: dict[str, Any]) -> TestResult:
        try:
            endpoint = self._validated_endpoint(config)
            status, body = _rpc(
                endpoint,
                "tools/list",
                {},
                token=self._token(secrets),
                protocol_version=self._protocol(config),
            )
        except Exception as exc:
            return TestResult(ok=False, message=f"MCP connection failed: {exc}")

        if status < 200 or status >= 300 or body.get("error"):
            message = (body.get("error") or {}).get("message", f"HTTP {status}")
            return TestResult(ok=False, message=f"MCP tools/list failed: {message}")

        tools = (body.get("result") or {}).get("tools") or []
        tool_name = str(config.get("tool_name") or "observa_pull")
        names = [str(tool.get("name")) for tool in tools if isinstance(tool, dict)]
        if tool_name not in names:
            return TestResult(ok=False, message=f"Connected, but tool '{tool_name}' was not found. Available: {', '.join(names[:12])}")
        return TestResult(ok=True, message=f"MCP connected. Tool '{tool_name}' is available among {len(names)} tools.")

    def pull(self, config, secrets, *, since=None) -> PullResult:
        endpoint = self._validated_endpoint(config)
        tool_name = str(config.get("tool_name") or "observa_pull")
        try:
            arguments = json.loads(str(config.get("tool_arguments_json") or "{}"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid tool arguments JSON: {exc}") from exc
        if not isinstance(arguments, dict):
            raise ValueError("Tool arguments JSON must be an object.")
        if since:
            arguments.setdefault("since", since.isoformat())

        status, body = _rpc(
            endpoint,
            "tools/call",
            {"name": tool_name, "arguments": arguments},
            token=self._token(secrets),
            protocol_version=self._protocol(config),
        )
        if status < 200 or status >= 300 or body.get("error"):
            message = (body.get("error") or {}).get("message", f"HTTP {status}")
            raise RuntimeError(f"MCP tools/call failed: {message}")

        result = body.get("result") or {}
        if result.get("isError"):
            raise RuntimeError("MCP tool returned isError=true.")
        payload = self._canonical_payload(result)
        return self._pull_result(payload)

    @staticmethod
    def _canonical_payload(result: dict[str, Any]) -> dict[str, Any]:
        structured = result.get("structuredContent")
        if isinstance(structured, dict):
            return structured
        for item in result.get("content") or []:
            if isinstance(item, dict) and item.get("type") == "text":
                try:
                    value = json.loads(str(item.get("text") or "{}"))
                except json.JSONDecodeError:
                    continue
                if isinstance(value, dict):
                    return value
        if any(key in result for key in ("costs", "resources", "metrics", "logs")):
            return result
        raise ValueError("MCP tool must return structuredContent or JSON text with Observa canonical signals.")

    def _pull_result(self, payload: dict[str, Any]) -> PullResult:
        costs = [
            CostSignal(
                date=date.fromisoformat(str(row.get("date") or date.today().isoformat())[:10]),
                provider=str(row.get("provider") or "mcp"),
                amount=float(row.get("amount") or 0),
                currency=str(row.get("currency") or "USD"),
                account=row.get("account"), service=row.get("service"), resource_id=row.get("resource_id"),
                product=row.get("product"), squad=row.get("squad"), environment=row.get("environment"), sku=row.get("sku"),
            )
            for row in payload.get("costs", []) if isinstance(row, dict)
        ]
        resources = [
            ResourceSignal(
                provider=str(row.get("provider") or "mcp"), type=str(row.get("type") or "resource"),
                id=str(row.get("id") or row.get("name") or "unknown"), name=row.get("name"), region=row.get("region"),
                product=row.get("product"), squad=row.get("squad"), status=row.get("status"),
                labels={str(key): str(value) for key, value in (row.get("labels") or {}).items()},
            )
            for row in payload.get("resources", []) if isinstance(row, dict)
        ]
        metrics = [
            MetricSignal(
                name=str(row.get("name") or "value"), value=float(row.get("value") or 0),
                ts=datetime.fromisoformat(str(row.get("ts") or datetime.now(timezone.utc).isoformat()).replace("Z", "+00:00")),
                unit=str(row.get("unit") or ""), resource_id=row.get("resource_id"), product=row.get("product"),
                labels={str(key): str(value) for key, value in (row.get("labels") or {}).items()},
            )
            for row in payload.get("metrics", []) if isinstance(row, dict)
        ]
        logs = [
            LogSignal(
                ts=datetime.fromisoformat(str(row.get("ts") or datetime.now(timezone.utc).isoformat()).replace("Z", "+00:00")),
                severity=str(row.get("severity") or "info"), source=str(row.get("source") or "mcp"),
                message=str(row.get("message") or ""), product=row.get("product"), service=row.get("service"),
                trace_id=row.get("trace_id"), labels={str(key): str(value) for key, value in (row.get("labels") or {}).items()},
            )
            for row in payload.get("logs", []) if isinstance(row, dict)
        ]
        return PullResult(costs=costs, resources=resources, metrics=metrics, logs=logs, message=str(payload.get("message") or "MCP tool synchronized."))
