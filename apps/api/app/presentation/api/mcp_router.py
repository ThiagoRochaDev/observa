from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Body, Depends, Header
from fastapi.responses import JSONResponse

from app.core import db
from app.core.tenancy import require_tenancy

MCP_PROTOCOL_VERSION = "2026-07-28"

mcp_router = APIRouter()


TOOLS = [
    {
        "name": "observa_context",
        "title": "Observa active context",
        "description": "Return the authorized company and tenancy currently selected for this MCP request.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
        "annotations": {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True},
    },
    {
        "name": "observa_cost_summary",
        "title": "Observa cost summary",
        "description": "Summarize cloud and platform costs by provider, product and squad.",
        "inputSchema": {
            "type": "object",
            "properties": {"days": {"type": "integer", "minimum": 1, "maximum": 365, "default": 30}},
            "additionalProperties": False,
        },
        "annotations": {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True},
    },
    {
        "name": "observa_inventory",
        "title": "Observa resource inventory",
        "description": "List normalized resources discovered by the active tenancy connectors.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "product": {"type": "string"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 500, "default": 100},
            },
            "additionalProperties": False,
        },
        "annotations": {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True},
    },
    {
        "name": "observa_products",
        "title": "Observa product catalog",
        "description": "List products with cost, service and resource counts in the active tenancy.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
        "annotations": {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True},
    },
    {
        "name": "observa_alerts",
        "title": "Observa alerts",
        "description": "List recent cost, infrastructure and application alerts in the active tenancy.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "status": {"type": "string"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 200, "default": 50},
            },
            "additionalProperties": False,
        },
        "annotations": {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True},
    },
]


def _response(request_id: Any, result: dict[str, Any], status_code: int = 200) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"jsonrpc": "2.0", "id": request_id, "result": result},
        headers={"MCP-Protocol-Version": MCP_PROTOCOL_VERSION},
    )


def _error(request_id: Any, code: int, message: str, status_code: int = 400) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}},
        headers={"MCP-Protocol-Version": MCP_PROTOCOL_VERSION},
    )


def _tool_result(value: dict[str, Any] | list[Any]) -> dict[str, Any]:
    return {
        "content": [{"type": "text", "text": json.dumps(value, ensure_ascii=False, default=str)}],
        "structuredContent": value,
        "isError": False,
    }


def _bounded_int(value: Any, default: int, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return min(max(parsed, minimum), maximum)


def _call_tool(name: str, arguments: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    if name == "observa_context":
        return _tool_result({"company": context["company"], "tenancy": context["tenancy"]})
    if name == "observa_cost_summary":
        days = _bounded_int(arguments.get("days"), 30, 1, 365)
        return _tool_result(db.cost_summary(days))
    if name == "observa_inventory":
        limit = _bounded_int(arguments.get("limit"), 100, 1, 500)
        resources = db.list_resources(arguments.get("product"))[:limit]
        return _tool_result({"count": len(resources), "resources": resources})
    if name == "observa_products":
        products = db.list_products()
        return _tool_result({"count": len(products), "products": products})
    if name == "observa_alerts":
        limit = _bounded_int(arguments.get("limit"), 50, 1, 200)
        alerts = db.list_alerts(arguments.get("status"))[:limit]
        return _tool_result({"count": len(alerts), "alerts": alerts})
    raise KeyError(name)


@mcp_router.post("/mcp")
def mcp_endpoint(
    payload: dict[str, Any] = Body(...),
    context: dict[str, Any] = Depends(require_tenancy),
    protocol_version: str | None = Header(default=None, alias="MCP-Protocol-Version"),
    routed_method: str | None = Header(default=None, alias="Mcp-Method"),
    routed_name: str | None = Header(default=None, alias="Mcp-Name"),
):
    request_id = payload.get("id")
    method = payload.get("method")
    params = payload.get("params") or {}

    if protocol_version != MCP_PROTOCOL_VERSION:
        return _error(request_id, -32600, f"MCP-Protocol-Version must be {MCP_PROTOCOL_VERSION}.")
    if routed_method != method:
        return _error(request_id, -32020, "Mcp-Method header does not match the JSON-RPC method.")

    if method == "server/discover":
        return _response(
            request_id,
            {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "serverInfo": {"name": "observa", "version": "0.1.0"},
                "capabilities": {"tools": {}},
            },
        )
    if method == "tools/list":
        return _response(request_id, {"tools": TOOLS, "ttlMs": 30000, "cacheScope": "private"})
    if method != "tools/call":
        return _error(request_id, -32601, f"Method not found: {method}")

    tool_name = str(params.get("name") or "")
    if not tool_name or routed_name != tool_name:
        return _error(request_id, -32020, "Mcp-Name header does not match the requested tool.")
    arguments = params.get("arguments") or {}
    if not isinstance(arguments, dict):
        return _error(request_id, -32602, "Tool arguments must be an object.")
    try:
        return _response(request_id, _call_tool(tool_name, arguments, context))
    except KeyError:
        return _error(request_id, -32602, f"Unknown tool: {tool_name}")
