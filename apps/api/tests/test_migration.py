def custom_payload():
    return {
        "scope_type": "custom",
        "target_providers": ["aws", "gcp", "azure"],
        "currency": "BRL",
        "usd_to_brl": 5.0,
        "components": [
            {
                "name": "Entrada pública",
                "category": "load_balancer",
                "usage": {"hours": 730, "processed_gb": 500},
            },
            {
                "name": "API serverless",
                "category": "serverless_container",
                "usage": {
                    "vcpu": 2,
                    "memory_gb": 4,
                    "active_hours": 220,
                    "requests_million": 15,
                    "egress_gb": 80,
                },
            },
            {
                "name": "Arquivos",
                "category": "object_storage",
                "usage": {"storage_gb": 750, "operations_10k": 120, "egress_gb": 90},
            },
        ],
    }


def test_migration_catalog_exposes_supported_clouds_and_categories(client):
    response = client.get("/api/migration/catalog")
    assert response.status_code == 200
    body = response.json()
    assert body["kind"] == "reference"
    assert {provider["id"] for provider in body["providers"]} == {"aws", "gcp", "azure"}
    assert all(len(provider["categories"]) == 7 for provider in body["providers"])
    assert "catálogos oficiais" in body["notice"]


def test_custom_architecture_compares_cloud_services_and_formulas(client):
    response = client.post("/api/migration/estimate", json=custom_payload())
    assert response.status_code == 200
    body = response.json()
    assert body["scope"] == {"type": "custom", "value": None}
    assert body["observed_current"]["amount"] == 0
    assert len(body["comparisons"]) == 3
    assert body["cheapest_provider"] == body["comparisons"][0]["provider"]
    assert {row["provider"] for row in body["comparisons"]} == {"aws", "gcp", "azure"}
    assert all(len(row["services"]) == 3 for row in body["comparisons"])
    assert all(service["sku"].startswith("reference.") for row in body["comparisons"] for service in row["services"])
    assert any(line["formula"] for row in body["comparisons"] for service in row["services"] for line in service["lines"])
    assert any("Catálogo de referência" in warning for warning in body["warnings"])


def test_product_resource_and_account_migration_scopes(client):
    product = client.post(
        "/api/migration/estimate",
        json={"scope_type": "product", "scope_value": "observa", "target_providers": ["gcp"]},
    )
    assert product.status_code == 200
    assert product.json()["components"]
    assert product.json()["observed_current"]["amount"] > 0

    resource = client.get("/api/resources").json()[0]
    resource_result = client.post(
        "/api/migration/estimate",
        json={"scope_type": "resource", "scope_value": str(resource["uid"]), "target_providers": ["aws"]},
    )
    assert resource_result.status_code == 200
    assert resource_result.json()["components"][0]["resource_uid"] == resource["uid"]

    account = client.post(
        "/api/migration/estimate",
        json={"scope_type": "account", "scope_value": resource["provider"], "target_providers": ["azure"]},
    )
    assert account.status_code == 200
    assert account.json()["components"]

    missing = client.post(
        "/api/migration/estimate",
        json={"scope_type": "resource", "scope_value": "999999", "target_providers": ["aws"]},
    )
    assert missing.status_code == 400


def test_saved_migration_scenarios_are_isolated_by_tenancy(client):
    company = client.post("/api/companies", json={"name": "Migration Corp"}).json()
    tenancy_a = client.post(
        "/api/tenancies", json={"company_id": company["id"], "name": "Production"}
    ).json()
    tenancy_b = client.post(
        "/api/tenancies", json={"company_id": company["id"], "name": "Sandbox"}
    ).json()
    client.headers["X-Observa-Company-ID"] = company["id"]
    client.headers["X-Observa-Tenancy-ID"] = tenancy_a["id"]

    created = client.post(
        "/api/migration/scenarios", json={"name": "LB + API + bucket", **custom_payload()}
    )
    assert created.status_code == 200
    scenario = created.json()
    assert client.get("/api/migration/scenarios").json()[0]["id"] == scenario["id"]

    client.headers["X-Observa-Tenancy-ID"] = tenancy_b["id"]
    assert client.get("/api/migration/scenarios").json() == []

    client.headers["X-Observa-Tenancy-ID"] = tenancy_a["id"]
    assert client.delete(f"/api/migration/scenarios/{scenario['id']}").status_code == 200
    assert client.get("/api/migration/scenarios").json() == []

    client.headers.pop("X-Observa-Company-ID", None)
    client.headers.pop("X-Observa-Tenancy-ID", None)
