from observa_connectors.providers.splunk import SplunkConnector

CONFIG = {"base_url": "https://splunk.acme.internal:8089"}
SECRETS = {"token": "tok"}


def test_test_connection_ok(monkeypatch):
    monkeypatch.setattr(
        "observa_connectors.providers.splunk.request_json",
        lambda *a, **k: (200, {"entry": []}),
    )
    assert SplunkConnector().test_connection(CONFIG, SECRETS).ok


def test_pull_indexes_and_license(monkeypatch):
    responses = {
        f"{CONFIG['base_url']}/services/data/indexes": (200, {"entry": [
            {"name": "main", "content": {"currentDBSizeMB": 1500.0, "disabled": False}},
            {"name": "security", "content": {"currentDBSizeMB": 500.0, "disabled": True}},
        ]}),
        f"{CONFIG['base_url']}/services/licenser/pools": (200, {"entry": [
            {"name": "auto_generated_pool_enterprise", "content": {"used_bytes": 123456789}},
        ]}),
    }

    def fake_request(method, url, **kwargs):
        return responses[url]

    monkeypatch.setattr("observa_connectors.providers.splunk.request_json", fake_request)

    result = SplunkConnector().pull(CONFIG, SECRETS)
    assert len(result.resources) == 2
    assert result.resources[1].status == "disabled"
    total_size_metric = next(m for m in result.metrics if m.name == "splunk.index.total_size_mb")
    assert total_size_metric.value == 2000.0
    license_metric = next(m for m in result.metrics if m.name == "splunk.license.used_bytes")
    assert license_metric.value == 123456789.0
