from observa_connectors.providers.linode import LinodeConnector

CONFIG = {}
SECRETS = {"token": "tok"}


def test_test_connection_ok(monkeypatch):
    monkeypatch.setattr(
        "observa_connectors.providers.linode.request_json",
        lambda *a, **k: (200, {"email": "a@b.com"}),
    )
    assert LinodeConnector().test_connection(CONFIG, SECRETS).ok


def test_test_connection_invalid_token(monkeypatch):
    monkeypatch.setattr(
        "observa_connectors.providers.linode.request_json",
        lambda *a, **k: (401, {"errors": [{"reason": "Invalid Token"}]}),
    )
    result = LinodeConnector().test_connection(CONFIG, SECRETS)
    assert not result.ok


def test_pull_instances_and_balance(monkeypatch):
    responses = {
        "https://api.linode.com/v4/linode/instances": (200, {"data": [
            {"id": 111, "label": "web-1", "region": "us-east", "status": "running", "type": "g6-standard-2"},
        ]}),
        "https://api.linode.com/v4/account": (200, {
            "balance_uninvoiced": 12.5, "company": "Acme", "email": "a@b.com",
        }),
    }

    def fake_request(method, url, **kwargs):
        return responses[url]

    monkeypatch.setattr("observa_connectors.providers.linode.request_json", fake_request)

    result = LinodeConnector().pull(CONFIG, SECRETS)
    assert len(result.resources) == 1
    assert result.resources[0].id == "111"
    assert result.resources[0].status == "running"
    assert len(result.costs) == 1
    assert result.costs[0].amount == 12.5
    assert result.costs[0].account == "Acme"
