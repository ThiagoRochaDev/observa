from observa_connectors.providers.opsgenie import OpsgenieConnector

CONFIG = {}
SECRETS = {"api_key": "key123"}


def test_test_connection_ok(monkeypatch):
    monkeypatch.setattr(
        "observa_connectors.providers.opsgenie.request_json",
        lambda *a, **k: (200, {"data": {"name": "acme"}}),
    )
    assert OpsgenieConnector().test_connection(CONFIG, SECRETS).ok


def test_pull_alerts_and_schedules(monkeypatch):
    responses = {
        "https://api.opsgenie.com/v2/alerts": (200, {"data": [
            {"id": "a1", "message": "Disk full", "status": "open", "priority": "P1"},
            {"id": "a2", "message": "CPU high", "status": "open", "priority": "P3"},
        ]}),
        "https://api.opsgenie.com/v2/schedules": (200, {"data": [
            {"id": "s1", "name": "On-call primary", "enabled": True},
        ]}),
    }

    def fake_request(method, url, **kwargs):
        return responses[url]

    monkeypatch.setattr("observa_connectors.providers.opsgenie.request_json", fake_request)

    result = OpsgenieConnector().pull(CONFIG, SECRETS)
    assert len(result.resources) == 3
    alert_ids = {r.id for r in result.resources if r.type == "alert"}
    assert alert_ids == {"a1", "a2"}
    schedule = next(r for r in result.resources if r.type == "schedule")
    assert schedule.status == "enabled"
    assert result.metrics[0].name == "opsgenie.alerts.open"
    assert result.metrics[0].value == 2.0
