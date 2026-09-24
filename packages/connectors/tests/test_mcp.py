from observa_connectors.providers.mcp import DEFAULT_PROTOCOL_VERSION, McpConnector


def test_mcp_discovers_tool_and_ingests_structured_content(monkeypatch):
    connector = McpConnector()
    calls = []

    def fake_rpc(endpoint, method, params, **kwargs):
        calls.append((endpoint, method, params, kwargs))
        if method == "tools/list":
            return 200, {"result": {"tools": [{"name": "observa_pull"}, {"name": "search"}]}}
        return 200, {
            "result": {
                "structuredContent": {
                    "costs": [{"date": "2026-09-24", "provider": "github", "amount": 7.5}],
                    "resources": [{"id": "repo-1", "type": "repository", "name": "observa"}],
                    "metrics": [{"name": "builds", "value": 3, "ts": "2026-09-24T12:00:00Z"}],
                    "logs": [{"message": "sync complete", "ts": "2026-09-24T12:00:00Z"}],
                }
            }
        }

    monkeypatch.setattr("observa_connectors.providers.mcp._rpc", fake_rpc)
    config = {
        "endpoint": "https://mcp.example.com/mcp",
        "tool_name": "observa_pull",
        "tool_arguments_json": '{"scope":"prod"}',
    }
    secrets = {"bearer_token": "secret"}

    result = connector.test_connection(config, secrets)
    assert result.ok is True
    pull = connector.pull(config, secrets)

    assert pull.costs[0].amount == 7.5
    assert pull.resources[0].name == "observa"
    assert pull.metrics[0].value == 3
    assert pull.logs[0].message == "sync complete"
    assert calls[0][3]["protocol_version"] == DEFAULT_PROTOCOL_VERSION
    assert calls[1][2]["arguments"] == {"scope": "prod"}


def test_mcp_rejects_missing_tool(monkeypatch):
    monkeypatch.setattr(
        "observa_connectors.providers.mcp._rpc",
        lambda *args, **kwargs: (200, {"result": {"tools": [{"name": "search"}]}}),
    )

    result = McpConnector().test_connection(
        {"endpoint": "https://mcp.example.com/mcp", "tool_name": "observa_pull"},
        {},
    )

    assert result.ok is False
    assert "was not found" in result.message


def test_mcp_rejects_non_http_endpoint():
    result = McpConnector().test_connection(
        {"endpoint": "file:///tmp/server", "tool_name": "observa_pull"},
        {},
    )

    assert result.ok is False
    assert "http:// or https://" in result.message
