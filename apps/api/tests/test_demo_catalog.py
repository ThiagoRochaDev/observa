"""Public demo data must remain fictional and belong to TGR products only."""

from observa_connectors.mock_demo import demo_product_catalog, demo_alerts
from app.application import demo_platform


EXPECTED = {"move-easy", "easy-food", "detect-easy", "observa", "vr-archviz"}


def test_demo_catalog_and_alerts_use_only_tgr_products():
    assert {p["slug"] for p in demo_product_catalog()} == EXPECTED
    assert set(demo_platform.PRODUCTS) == EXPECTED
    assert {row["product"] for row in demo_alerts()} <= EXPECTED


def test_seeded_api_supports_each_tgr_demo_product(client):
    products = client.get("/api/products")
    assert products.status_code == 200
    assert {p["slug"] for p in products.json()} == EXPECTED
    for slug in EXPECTED:
        detail = client.get(f"/api/products/{slug}")
        assert detail.status_code == 200
        assert detail.json()["slug"] == slug
        resources = client.get("/api/resources", params={"product": slug})
        assert resources.status_code == 200
        assert resources.json()
        assert all(row["product"] == slug for row in resources.json())
        graph = client.get("/api/ecosystem", params={"product": slug})
        assert graph.status_code == 200
        assert graph.json()["nodes"]
