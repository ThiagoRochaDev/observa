def finding(external_id="scan-1", **overrides):
    row = {
        "external_id": external_id,
        "source": "trivy",
        "provider": "gcp",
        "resource_id": "gke/demo/api",
        "asset_type": "container_image",
        "title": "Demo package requires update",
        "description": "Synthetic test finding.",
        "severity": "critical",
        "cvss": 9.1,
        "package_name": "demo-lib",
        "installed_version": "1.0.0",
        "fixed_version": "1.0.1",
        "product": "observa",
        "environment": "prd",
        "exploitable": True,
        "internet_exposed": True,
        "detected_at": "2026-10-05T12:00:00Z",
        "labels": {"scanner": "trivy", "demo": "true"},
    }
    row.update(overrides)
    return row


def test_vulnerability_ingest_risk_filters_and_approval_flow(client):
    company = client.post("/api/companies", json={"name": "Vulnerability Flow Corp"}).json()
    tenancy = client.post(
        "/api/tenancies", json={"company_id": company["id"], "name": "Vulnerability Flow"}
    ).json()
    client.headers["X-Observa-Company-ID"] = company["id"]
    client.headers["X-Observa-Tenancy-ID"] = tenancy["id"]

    ingested = client.post(
        "/api/vulnerabilities/ingest",
        json={"connection_id": "scanner-test", "vulnerabilities": [finding()]},
    )
    assert ingested.status_code == 200
    assert ingested.json() == {"ok": True, "count": 1, "urgent_alerts": 1}

    rows = client.get("/api/vulnerabilities?severity=critical&provider=gcp").json()
    assert len(rows) == 1
    vulnerability = rows[0]
    assert vulnerability["priority"] == "urgent"
    assert vulnerability["risk_score"] == 10
    assert vulnerability["fixed_version"] == "1.0.1"
    assert vulnerability["labels"] == {"scanner": "trivy", "demo": "true"}

    summary = client.get("/api/vulnerabilities/summary").json()
    assert summary["active"] == 1
    assert summary["critical"] == 1
    assert summary["exploitable"] == 1
    assert summary["internet_exposed"] == 1

    proposal_response = client.post(
        f"/api/vulnerabilities/{vulnerability['id']}/remediation",
        json={"dry_run": True},
    )
    assert proposal_response.status_code == 200
    proposal = proposal_response.json()
    assert proposal["status"] == "suggested"
    assert proposal["action"]["type"] == "patch_vulnerability"

    pending = client.get("/api/vulnerabilities?status=remediation_pending").json()
    assert pending[0]["remediation_proposal_id"] == proposal["id"]
    approved = client.post(f"/api/remediations/{proposal['id']}/approve")
    assert approved.status_code == 200
    assert approved.json()["status"] == "simulated"

    resolved = client.patch(
        f"/api/vulnerabilities/{vulnerability['id']}/status", json={"status": "resolved"}
    )
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "resolved"
    client.headers.pop("X-Observa-Company-ID", None)
    client.headers.pop("X-Observa-Tenancy-ID", None)


def test_vulnerabilities_are_isolated_by_tenancy(client):
    company = client.post("/api/companies", json={"name": "Security Test Corp"}).json()
    tenancy_a = client.post(
        "/api/tenancies", json={"company_id": company["id"], "name": "Security Production"}
    ).json()
    tenancy_b = client.post(
        "/api/tenancies", json={"company_id": company["id"], "name": "Security Sandbox"}
    ).json()
    client.headers["X-Observa-Company-ID"] = company["id"]
    client.headers["X-Observa-Tenancy-ID"] = tenancy_a["id"]
    assert client.post(
        "/api/vulnerabilities/ingest",
        json={"connection_id": "openvas", "vulnerabilities": [finding("onprem-1", provider="on-prem")]},
    ).status_code == 200
    assert len(client.get("/api/vulnerabilities").json()) == 1

    client.headers["X-Observa-Tenancy-ID"] = tenancy_b["id"]
    assert client.get("/api/vulnerabilities").json() == []

    client.headers.pop("X-Observa-Company-ID", None)
    client.headers.pop("X-Observa-Tenancy-ID", None)


def test_existing_tenancy_schema_is_migrated_on_first_access(client):
    from app.core import db

    company = client.post("/api/companies", json={"name": "Schema Upgrade Corp"}).json()
    tenancy = client.post(
        "/api/tenancies", json={"company_id": company["id"], "name": "Legacy Tenant"}
    ).json()
    with db.tenancy_context(tenancy["id"]):
        with db.db() as connection:
            connection.execute("DROP TABLE vulnerabilities")
        db._initialized_tenancies.discard(tenancy["id"])

    client.headers["X-Observa-Company-ID"] = company["id"]
    client.headers["X-Observa-Tenancy-ID"] = tenancy["id"]
    response = client.get("/api/vulnerabilities/summary")
    assert response.status_code == 200
    assert response.json()["total"] == 0
    client.headers.pop("X-Observa-Company-ID", None)
    client.headers.pop("X-Observa-Tenancy-ID", None)
