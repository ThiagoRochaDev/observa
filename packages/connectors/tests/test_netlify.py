from observa_connectors.providers.netlify import NetlifyConnector

CONFIG = {}
SECRETS = {"token": "tok"}


def test_test_connection_ok(monkeypatch):
    monkeypatch.setattr(
        "observa_connectors.providers.netlify.request_json",
        lambda *a, **k: (200, []),
    )
    assert NetlifyConnector().test_connection(CONFIG, SECRETS).ok


def test_pull_sites_and_build_minutes(monkeypatch):
    responses = {
        "https://api.netlify.com/api/v1/sites": (200, [
            {"site_id": "s1", "name": "marketing-site", "state": "current", "url": "https://x.netlify.app"},
        ]),
        "https://api.netlify.com/api/v1/accounts": (200, [
            {"slug": "acme-team", "capabilities": {"build_minutes": {"used": 340, "included": 300}}},
        ]),
    }

    def fake_request(method, url, **kwargs):
        return responses[url]

    monkeypatch.setattr("observa_connectors.providers.netlify.request_json", fake_request)

    result = NetlifyConnector().pull(CONFIG, SECRETS)
    assert len(result.resources) == 1
    assert result.resources[0].id == "s1"
    assert result.metrics[0].name == "netlify.build_minutes.used"
    assert result.metrics[0].value == 340.0
    assert result.metrics[0].labels["account"] == "acme-team"
