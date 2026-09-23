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


def test_company_with_multiple_tenancies_isolates_data(client):
    company_response = client.post(
        "/api/companies", json={"name": "Acme Corp", "slug": "acme-corp"}
    )
    assert company_response.status_code == 200
    company = company_response.json()

    tenancy_a = client.post(
        "/api/tenancies",
        json={"company_id": company["id"], "name": "Production", "slug": "production"},
    ).json()
    tenancy_b = client.post(
        "/api/tenancies",
        json={"company_id": company["id"], "name": "Sandbox", "slug": "sandbox"},
    ).json()
    assert tenancy_a["company_id"] == company["id"]
    assert tenancy_b["company_id"] == company["id"]

    client.headers["X-Observa-Company-ID"] = company["id"]
    client.headers["X-Observa-Tenancy-ID"] = tenancy_a["id"]
    created = client.post(
        "/api/connections",
        json={"name": "Production Mock", "connector_id": "mock-demo", "config": {"days": 7}},
    )
    assert created.status_code == 200
    assert len(client.get("/api/connections").json()) == 1
    assert client.get("/api/context").json()["tenancy"]["id"] == tenancy_a["id"]

    client.headers["X-Observa-Tenancy-ID"] = tenancy_b["id"]
    assert client.get("/api/connections").json() == []
    assert client.get("/api/resources").json() == []

    client.headers["X-Observa-Company-ID"] = "cmp_wrong"
    assert client.get("/api/connections").status_code == 409

    client.headers.pop("X-Observa-Company-ID", None)
    client.headers.pop("X-Observa-Tenancy-ID", None)


def test_oidc_identity_cannot_discover_or_read_unassigned_company(client):
    from fastapi.testclient import TestClient

    from app.core.session import create_session_token
    from app.main import app

    company = client.post(
        "/api/companies", json={"name": "Private Corp", "slug": "private-corp"}
    ).json()
    tenancy = client.post(
        "/api/tenancies",
        json={"company_id": company["id"], "name": "Secret", "slug": "secret"},
    ).json()
    token = create_session_token(
        provider="test", subject="outsider", email="outsider@example.test", name="Outsider"
    )
    outsider = TestClient(app, headers={"X-Observa-Api-Key": token})

    assert company["id"] not in {row["id"] for row in outsider.get("/api/companies").json()}
    denied = outsider.get(
        "/api/health",
        headers={
            "X-Observa-Company-ID": company["id"],
            "X-Observa-Tenancy-ID": tenancy["id"],
        },
    )
    assert denied.status_code == 403

    client.put(
        f"/api/companies/{company['id']}/members",
        json={"subject": "test:outsider", "email": "outsider@example.test", "role": "viewer"},
    )
    allowed = outsider.get(
        "/api/health",
        headers={
            "X-Observa-Company-ID": company["id"],
            "X-Observa-Tenancy-ID": tenancy["id"],
        },
    )
    assert allowed.status_code == 200
    denied_write = outsider.post(
        "/api/connections",
        headers={
            "X-Observa-Company-ID": company["id"],
            "X-Observa-Tenancy-ID": tenancy["id"],
        },
        json={"name": "Must not be created", "connector_id": "mock-demo"},
    )
    assert denied_write.status_code == 403


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


def test_resource_tags_support_preview_and_apply(client):
    resource = client.get("/api/resources").json()[0]

    preview = client.patch(
        f"/api/resources/{resource['uid']}/tags",
        json={"tags": {"owner": "platform", "product": "observa"}, "dry_run": True},
    )
    assert preview.status_code == 200
    assert preview.json()["dry_run"] is True

    applied = client.patch(
        f"/api/resources/{resource['uid']}/tags",
        json={"tags": {"owner": "platform", "product": "observa"}, "dry_run": False},
    )
    assert applied.status_code == 200
    assert applied.json()["resource"]["labels"]["owner"] == "platform"
    assert applied.json()["resource"]["product"] == "observa"


def test_policy_schedules_action_and_approval_simulates(client):
    resource = client.get("/api/resources").json()[0]
    created = client.post(
        "/api/automation/policies",
        json={
            "name": "Stop demo at night",
            "resource_ids": [resource["uid"]],
            "timezone": "UTC",
            "weekdays": [0],
            "stop_time": "20:00",
            "require_approval": True,
            "dry_run": True,
        },
    )
    assert created.status_code == 200

    run = client.post("/api/automation/run-due", json={"at": "2026-09-14T20:00:00Z"})
    assert run.status_code == 200
    assert run.json()["count"] == 1
    action = run.json()["created"][0]
    assert action["status"] == "pending_approval"

    approved = client.post(f"/api/automation/actions/{action['id']}/approve")
    assert approved.status_code == 200
    assert approved.json()["status"] == "simulated"


def test_policy_requires_scope(client):
    response = client.post("/api/automation/policies", json={"name": "Invalid"})
    assert response.status_code == 400


def test_scheduler_accepts_empty_body(client):
    response = client.post("/api/automation/run-due")
    assert response.status_code == 200
    assert "created" in response.json()


def test_resource_identity_survives_connector_sync(client):
    before = client.get("/api/resources").json()
    identity = {(row["provider"], row["id"]): row["uid"] for row in before}
    connection_id = before[0]["connection_id"]

    response = client.post(f"/api/connections/{connection_id}/sync")
    assert response.status_code == 200

    after = client.get("/api/resources").json()
    assert {(row["provider"], row["id"]): row["uid"] for row in after} == identity


def test_budget_exceeded_creates_approval_action_and_deduplicates(client):
    resource = next(row for row in client.get("/api/resources").json() if row["product"] == "hiperlocal")
    created = client.post(
        "/api/budgets",
        json={
            "name": "Hiperlocal guardrail",
            "scope_type": "product",
            "scope_value": "hiperlocal",
            "amount": 1,
            "window_days": 30,
            "warning_threshold": 0.8,
            "critical_threshold": 1.0,
            "response_mode": "approval",
            "owner": "squad-hiperlocal",
            "resource_ids": [resource["uid"]],
            "dry_run": True,
        },
    )
    assert created.status_code == 200
    rule = created.json()

    evaluated = client.post("/api/budgets/evaluate", json={"at": "2026-09-17"})
    assert evaluated.status_code == 200
    event = next(item for item in evaluated.json()["created"] if item["rule_id"] == rule["id"])
    assert event["level"] == "critical"
    assert event["status"] == "pending_approval"
    assert len(event["action_ids"]) == 1

    duplicate = client.post("/api/budgets/evaluate", json={"at": "2026-09-17"})
    assert duplicate.status_code == 200
    assert not any(item["rule_id"] == rule["id"] for item in duplicate.json()["created"])

    approved = client.post(f"/api/automation/actions/{event['action_ids'][0]}/approve")
    assert approved.status_code == 200
    assert approved.json()["status"] == "simulated"


def test_budget_ignore_records_event_without_action(client):
    created = client.post(
        "/api/budgets",
        json={
            "name": "Ignored provider budget",
            "scope_type": "provider",
            "scope_value": "gcp",
            "amount": 1,
            "response_mode": "ignore",
        },
    )
    assert created.status_code == 200
    rule_id = created.json()["id"]

    evaluated = client.post("/api/budgets/evaluate", json={"at": "2026-09-18"})
    event = next(item for item in evaluated.json()["created"] if item["rule_id"] == rule_id)
    assert event["status"] == "ignored"
    assert event["action_ids"] == []


def test_budget_approval_requires_owner(client):
    response = client.post(
        "/api/budgets",
        json={
            "name": "Invalid approval budget",
            "scope_type": "product",
            "scope_value": "hiperlocal",
            "amount": 100,
            "response_mode": "approval",
        },
    )
    assert response.status_code == 400


def test_budget_warning_starts_preventive_approval(client):
    product = client.get("/api/products/hiperlocal").json()
    resource = product["resources"][0]
    amount_for_ninety_percent = product["total_brl"] / 0.9
    created = client.post(
        "/api/budgets",
        json={
            "name": "Preventive hiperlocal cap",
            "scope_type": "product",
            "scope_value": "hiperlocal",
            "amount": amount_for_ninety_percent,
            "warning_threshold": 0.8,
            "critical_threshold": 1.0,
            "response_mode": "approval",
            "owner": "squad-hiperlocal",
            "resource_ids": [resource["uid"]],
        },
    )
    rule_id = created.json()["id"]

    evaluated = client.post("/api/budgets/evaluate", json={"at": "2026-09-19"}).json()
    event = next(item for item in evaluated["created"] if item["rule_id"] == rule_id)
    assert event["level"] == "warning"
    assert event["status"] == "pending_approval"
    assert len(event["action_ids"]) == 1


def test_budget_monitor_syncs_cost_connectors_before_evaluation(client):
    response = client.post("/api/budgets/monitor", json={"at": "2026-09-20"})
    assert response.status_code == 200
    body = response.json()
    assert any(item["status"] == "ok" for item in body["synced"])
    assert "evaluation" in body


def test_log_analysis_requires_approval_and_defaults_to_dry_run(client):
    ingested = client.post(
        "/api/logs/ingest",
        json={
            "connection_id": "test-agent",
            "logs": [
                {
                    "ts": "2026-09-23T10:00:00Z",
                    "severity": "ERROR",
                    "source": "app",
                    "product": "observa",
                    "service": "api",
                    "message": "upstream timeout calling billing",
                },
                {
                    "ts": "2026-09-23T10:01:00Z",
                    "severity": "ERROR",
                    "source": "app",
                    "product": "observa",
                    "service": "api",
                    "message": "upstream timeout calling billing",
                },
            ],
        },
    )
    assert ingested.status_code == 200
    assert ingested.json()["count"] == 2

    analyzed = client.post("/api/remediations/analyze", json={"dry_run": True})
    assert analyzed.status_code == 200
    proposal = next(
        row for row in analyzed.json()["proposals"] if "observa/api" in row["title"]
    )
    assert proposal["status"] == "suggested"
    assert "upstream timeout calling billing" not in str(proposal)

    approved = client.post(f"/api/remediations/{proposal['id']}/approve")
    assert approved.status_code == 200
    assert approved.json()["status"] == "simulated"
