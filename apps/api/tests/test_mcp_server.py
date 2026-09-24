MCP_VERSION = "2026-07-28"


def _headers(method: str, name: str | None = None) -> dict[str, str]:
    headers = {"MCP-Protocol-Version": MCP_VERSION, "Mcp-Method": method}
    if name:
        headers["Mcp-Name"] = name
    return headers


def _rpc(method: str, params: dict | None = None, request_id: str = "test") -> dict:
    return {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params or {}}


def test_mcp_requires_observa_authentication(client):
    client.headers.pop("X-Observa-Api-Key", None)
    response = client.post("/mcp", headers=_headers("tools/list"), json=_rpc("tools/list"))
    assert response.status_code == 401


def test_mcp_lists_only_read_only_observa_tools(client):
    response = client.post("/mcp", headers=_headers("tools/list"), json=_rpc("tools/list"))
    assert response.status_code == 200
    tools = response.json()["result"]["tools"]
    names = {tool["name"] for tool in tools}

    assert names == {
        "observa_context",
        "observa_cost_summary",
        "observa_inventory",
        "observa_products",
        "observa_alerts",
    }
    assert all(tool["annotations"]["readOnlyHint"] is True for tool in tools)
    assert all(tool["annotations"]["destructiveHint"] is False for tool in tools)


def test_mcp_calls_cost_and_inventory_tools(client):
    cost_name = "observa_cost_summary"
    cost_response = client.post(
        "/mcp",
        headers=_headers("tools/call", cost_name),
        json=_rpc("tools/call", {"name": cost_name, "arguments": {"days": 30}}),
    )
    assert cost_response.status_code == 200
    cost_result = cost_response.json()["result"]
    assert cost_result["isError"] is False
    assert cost_result["structuredContent"]["days"] == 30
    assert "total" in cost_result["structuredContent"]

    inventory_name = "observa_inventory"
    inventory_response = client.post(
        "/mcp",
        headers=_headers("tools/call", inventory_name),
        json=_rpc("tools/call", {"name": inventory_name, "arguments": {"limit": 2}}),
    )
    assert inventory_response.status_code == 200
    inventory = inventory_response.json()["result"]["structuredContent"]
    assert inventory["count"] <= 2
    assert "resources" in inventory


def test_mcp_rejects_header_body_mismatch(client):
    response = client.post(
        "/mcp",
        headers=_headers("tools/call", "observa_alerts"),
        json=_rpc("tools/list"),
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == -32020
