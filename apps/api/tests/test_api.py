"""Cobertura mínima da API: sobe a app de verdade (com o lifespan, que já
semeia o demo), bate nos endpoints principais e no ciclo de vida completo
de uma conexão usando o conector mock-demo (não precisa de credencial real).
"""


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["app"] == "observa"
    assert body["connections"] >= 1  # o demo do lifespan já criou uma


def test_root(client):
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["app"] == "observa"


def test_healthz_is_public(client):
    client.headers.pop("X-Observa-Api-Key", None)
    r = client.get("/healthz")
    assert r.status_code == 200


def test_api_requires_key(client):
    client.headers.pop("X-Observa-Api-Key", None)
    assert client.get("/api/connections").status_code == 401
    assert client.get("/api/health").status_code == 401


def test_connectors_catalog_has_mock_demo(client):
    r = client.get("/api/connectors")
    assert r.status_code == 200
    catalog = r.json()
    assert isinstance(catalog, list)
    assert len(catalog) > 0
    ids = {c["id"] for c in catalog}
    assert "mock-demo" in ids


def test_connection_lifecycle_create_sync_patch_delete(client):
    # create
    r = client.post(
        "/api/connections",
        json={"name": "Test Mock", "connector_id": "mock-demo", "config": {"days": 7}},
    )
    assert r.status_code == 200
    row = r.json()
    assert row["name"] == "Test Mock"
    assert "_secrets" not in row
    conn_id = row["id"]

    # aparece na listagem
    r = client.get("/api/connections")
    assert r.status_code == 200
    assert any(c["id"] == conn_id for c in r.json())

    # sync real (mock-demo gera dados sintéticos, não bate em API externa)
    r = client.post(f"/api/connections/{conn_id}/sync")
    assert r.status_code == 200

    # patch
    r = client.patch(f"/api/connections/{conn_id}", json={"name": "Renamed"})
    assert r.status_code == 200
    assert r.json()["name"] == "Renamed"

    # delete
    r = client.delete(f"/api/connections/{conn_id}")
    assert r.status_code == 200
    assert r.json()["ok"] is True

    r = client.get("/api/connections")
    assert not any(c["id"] == conn_id for c in r.json())


def test_connection_not_found_returns_404(client):
    assert client.patch("/api/connections/does-not-exist", json={"name": "x"}).status_code == 404
    assert client.delete("/api/connections/does-not-exist").status_code == 404
    assert client.post("/api/connections/does-not-exist/sync").status_code == 404


def test_create_connection_rejects_unknown_connector(client):
    r = client.post(
        "/api/connections",
        json={"name": "Bad", "connector_id": "not-a-real-connector"},
    )
    assert r.status_code == 400


def test_costs_summary_and_products_after_demo_seed(client):
    r = client.get("/api/costs/summary")
    assert r.status_code == 200
    assert "records" in r.json()

    r = client.get("/api/products")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_auth_settings_roundtrip(client):
    r = client.get("/api/auth/settings")
    assert r.status_code == 200
    assert r.json()["mode"] == "local"

    r = client.put("/api/auth/settings", json={"mode": "local", "providers": {}})
    assert r.status_code == 200
    assert r.json()["ok"] is True
