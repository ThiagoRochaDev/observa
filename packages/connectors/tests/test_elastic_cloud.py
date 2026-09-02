from observa_connectors.providers.elastic_cloud import ElasticCloudConnector

SECRETS = {"api_key": "key"}


def test_test_connection_ok(monkeypatch):
    monkeypatch.setattr(
        "observa_connectors.providers.elastic_cloud.request_json",
        lambda *a, **k: (200, {"deployments": []}),
    )
    assert ElasticCloudConnector().test_connection({}, SECRETS).ok


def test_pull_deployments(monkeypatch):
    monkeypatch.setattr(
        "observa_connectors.providers.elastic_cloud.request_json",
        lambda *a, **k: (200, {"deployments": [
            {
                "id": "dep1", "name": "logging-cluster",
                "resources": {"elasticsearch": [{"info": {"health": "green", "region": "us-east-1"}}]},
            },
            {"id": "dep2", "name": "no-info-cluster", "resources": {"elasticsearch": []}},
        ]}),
    )
    result = ElasticCloudConnector().pull({}, SECRETS)
    assert len(result.resources) == 2
    assert result.resources[0].status == "green"
    assert result.resources[0].region == "us-east-1"
    assert result.resources[1].status is None
