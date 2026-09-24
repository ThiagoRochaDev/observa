from observa_connectors.catalog import ADAPTER_CATALOG, AdapterCatalogConnector


def test_catalog_has_broad_vendor_coverage():
    connector_ids = {connector.id for connector in ADAPTER_CATALOG}

    assert len(connector_ids) >= 75
    assert {
        "opentelemetry",
        "jenkins",
        "argocd",
        "postgresql",
        "apache-kafka",
        "servicenow",
        "slack",
        "sonarqube",
    }.issubset(connector_ids)


def test_adapter_tests_health_and_parses_canonical_payload(monkeypatch):
    connector = AdapterCatalogConnector(
        "example",
        "Example",
        "data",
        ["cost", "inventory", "metrics", "logs"],
        "Example adapter.",
    )

    def fake_request(method, url, **kwargs):
        assert kwargs["headers"] == {"Authorization": "Bearer secret"}
        if url.endswith("/health"):
            return 200, {"message": "ready"}
        return 200, {
            "costs": [{"date": "2026-09-24", "amount": 12.5, "currency": "BRL"}],
            "resources": [{"id": "resource-1", "type": "service", "name": "checkout"}],
            "metrics": [{"name": "latency", "value": 42, "ts": "2026-09-24T12:00:00Z"}],
            "logs": [{"message": "healthy", "severity": "info", "ts": "2026-09-24T12:00:00Z"}],
        }

    monkeypatch.setattr("observa_connectors.catalog.request_json", fake_request)

    config = {"base_url": "https://adapter.internal"}
    secrets = {"token": "secret"}
    assert connector.test_connection(config, secrets).ok is True

    result = connector.pull(config, secrets)
    assert result.costs[0].amount == 12.5
    assert result.resources[0].id == "resource-1"
    assert result.metrics[0].name == "latency"
    assert result.logs[0].message == "healthy"
