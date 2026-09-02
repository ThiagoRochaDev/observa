from observa_connectors.providers.bitbucket import BitbucketConnector

CONFIG = {"workspace": "acme"}
SECRETS = {"username": "bot", "app_password": "pw"}


def test_test_connection_ok(monkeypatch):
    monkeypatch.setattr(
        "observa_connectors.providers.bitbucket.request_json",
        lambda *a, **k: (200, {"slug": "acme"}),
    )
    result = BitbucketConnector().test_connection(CONFIG, SECRETS)
    assert result.ok


def test_test_connection_bad_credentials(monkeypatch):
    monkeypatch.setattr(
        "observa_connectors.providers.bitbucket.request_json",
        lambda *a, **k: (401, {"error": {"message": "Invalid credentials"}}),
    )
    result = BitbucketConnector().test_connection(CONFIG, SECRETS)
    assert not result.ok
    assert "401" in result.message


def test_pull_paginates_repositories(monkeypatch):
    pages = [
        (200, {
            "values": [{"uuid": "{1}", "full_name": "acme/repo1", "is_private": True, "language": "python"}],
            "next": "https://api.bitbucket.org/2.0/repositories/acme?page=2",
        }),
        (200, {
            "values": [{"uuid": "{2}", "full_name": "acme/repo2", "is_private": False, "language": "go"}],
        }),
    ]
    calls = iter(pages)
    monkeypatch.setattr(
        "observa_connectors.providers.bitbucket.request_json",
        lambda *a, **k: next(calls),
    )

    result = BitbucketConnector().pull(CONFIG, SECRETS)
    assert len(result.resources) == 2
    assert result.resources[0].id == "{1}"
    assert result.resources[0].status == "private"
    assert result.resources[1].status == "public"


def test_pull_stops_when_first_page_fails(monkeypatch):
    monkeypatch.setattr(
        "observa_connectors.providers.bitbucket.request_json",
        lambda *a, **k: (500, "boom"),
    )
    result = BitbucketConnector().pull(CONFIG, SECRETS)
    assert result.resources == []
