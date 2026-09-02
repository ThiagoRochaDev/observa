from observa_connectors.providers.grafana_cloud import GrafanaCloudConnector

SECRETS = {"api_token": "tok"}


def test_test_connection_ok(monkeypatch):
    monkeypatch.setattr(
        "observa_connectors.providers.grafana_cloud.request_json",
        lambda *a, **k: (200, {"items": []}),
    )
    assert GrafanaCloudConnector().test_connection({}, SECRETS).ok


def test_pull_filters_by_stack_slug(monkeypatch):
    monkeypatch.setattr(
        "observa_connectors.providers.grafana_cloud.request_json",
        lambda *a, **k: (200, {"items": [
            {"id": 1, "slug": "acme-prod", "name": "Production", "status": "active", "clusterSlug": "us-east", "url": "https://acme-prod.grafana.net"},
            {"id": 2, "slug": "acme-staging", "name": "Staging", "status": "active", "clusterSlug": "us-east"},
        ]}),
    )

    result = GrafanaCloudConnector().pull({"stack_slug": "acme-prod"}, SECRETS)
    assert len(result.resources) == 1
    assert result.resources[0].id == "1"
    assert result.resources[0].region == "us-east"


def test_pull_lists_all_stacks_when_no_filter(monkeypatch):
    monkeypatch.setattr(
        "observa_connectors.providers.grafana_cloud.request_json",
        lambda *a, **k: (200, {"items": [
            {"id": 1, "slug": "a"}, {"id": 2, "slug": "b"},
        ]}),
    )
    result = GrafanaCloudConnector().pull({}, SECRETS)
    assert len(result.resources) == 2
