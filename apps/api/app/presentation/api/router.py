from __future__ import annotations

from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field

from app.application import budget_service, governance_service, remediation_service, sync_service
from app.core import db
from app.core.crypto import encrypt_json
from app.core.security import require_api_key
from app.core.session import verify_session_token
from app.core.tenancy import (
    require_platform_admin,
    require_tenancy,
    require_tenancy_admin,
    require_tenancy_operator,
)

router = APIRouter(dependencies=[Depends(require_api_key), Depends(require_tenancy)])
organization_router = APIRouter(dependencies=[Depends(require_api_key)])


class CompanyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    slug: str | None = Field(default=None, min_length=1, max_length=80)


class TenancyCreate(BaseModel):
    company_id: str
    name: str = Field(min_length=1, max_length=120)
    slug: str | None = Field(default=None, min_length=1, max_length=80)


class PlatformRunBody(BaseModel):
    at: datetime | None = None


class CompanyMemberUpsert(BaseModel):
    subject: str = Field(min_length=1)
    email: str | None = None
    role: str = "viewer"


def _company_role(company_id: str, actor: dict) -> str | None:
    if actor["is_platform_admin"]:
        return "platform_admin"
    member = db.get_company_member(company_id, actor["subject"])
    return member["role"] if member else None


def _require_company_role(company_id: str, actor: dict, roles: set[str]) -> None:
    role = _company_role(company_id, actor)
    if role not in roles and role != "platform_admin":
        raise HTTPException(403, "Caller cannot manage this company")


class AuthSettingsUpdate(BaseModel):
    mode: str = Field(description="local | oidc")
    providers: dict[str, Any] = Field(default_factory=dict)


class ConnectionCreate(BaseModel):
    name: str
    connector_id: str
    config: dict[str, Any] = Field(default_factory=dict)
    secrets: dict[str, Any] = Field(default_factory=dict)


class ConnectionUpdate(BaseModel):
    name: str | None = None
    config: dict[str, Any] | None = None
    secrets: dict[str, Any] | None = None
    enabled: bool | None = None


class TestConnectionBody(BaseModel):
    connector_id: str
    config: dict[str, Any] = Field(default_factory=dict)
    secrets: dict[str, Any] = Field(default_factory=dict)


class ResourceTagsUpdate(BaseModel):
    tags: dict[str, str]
    dry_run: bool = True
    write_back: bool = True


class PolicyCreate(BaseModel):
    name: str
    resource_ids: list[int] = Field(default_factory=list)
    selector: dict[str, str] = Field(default_factory=dict)
    timezone: str = "UTC"
    weekdays: list[int] = Field(default_factory=lambda: [0, 1, 2, 3, 4])
    start_time: str | None = None
    stop_time: str | None = None
    expires_at: str | None = None
    expiration_action: str = "stop"
    enabled: bool = True
    require_approval: bool = True
    dry_run: bool = True


class PolicyUpdate(BaseModel):
    name: str | None = None
    resource_ids: list[int] | None = None
    selector: dict[str, str] | None = None
    timezone: str | None = None
    weekdays: list[int] | None = None
    start_time: str | None = None
    stop_time: str | None = None
    expires_at: str | None = None
    expiration_action: str | None = None
    enabled: bool | None = None
    require_approval: bool | None = None
    dry_run: bool | None = None


class AutomationRunBody(BaseModel):
    at: datetime | None = None


class ActionRejectBody(BaseModel):
    reason: str = "Rejected by operator"


class BudgetRuleCreate(BaseModel):
    name: str
    scope_type: str
    scope_value: str
    amount: float = Field(gt=0)
    currency: str = "BRL"
    window_days: int = Field(default=30, ge=1, le=366)
    warning_threshold: float = Field(default=0.8, gt=0)
    critical_threshold: float = Field(default=1.0, gt=0)
    response_mode: str = "notify"
    owner: str | None = None
    resource_ids: list[int] = Field(default_factory=list)
    dry_run: bool = True
    enabled: bool = True


class BudgetRuleUpdate(BaseModel):
    name: str | None = None
    scope_type: str | None = None
    scope_value: str | None = None
    amount: float | None = Field(default=None, gt=0)
    currency: str | None = None
    window_days: int | None = Field(default=None, ge=1, le=366)
    warning_threshold: float | None = Field(default=None, gt=0)
    critical_threshold: float | None = Field(default=None, gt=0)
    response_mode: str | None = None
    owner: str | None = None
    resource_ids: list[int] | None = None
    dry_run: bool | None = None
    enabled: bool | None = None


class BudgetEvaluateBody(BaseModel):
    at: date | None = None


class LogEventInput(BaseModel):
    ts: datetime
    severity: str = "INFO"
    source: str = "api"
    message: str = Field(min_length=1, max_length=20000)
    product: str | None = None
    service: str | None = None
    trace_id: str | None = None
    labels: dict[str, str] = Field(default_factory=dict)


class LogIngestBody(BaseModel):
    connection_id: str = "push-api"
    logs: list[LogEventInput] = Field(min_length=1, max_length=1000)


class RemediationAnalyzeBody(BaseModel):
    executor_connection_id: str | None = None
    dry_run: bool = True
    limit: int = Field(default=1000, ge=1, le=10000)


class RemediationRejectBody(BaseModel):
    reason: str = Field(min_length=1, max_length=2000)


class RemediationFeedbackBody(BaseModel):
    outcome: str
    notes: str | None = Field(default=None, max_length=4000)


@router.get("/health")
def health():
    summary = db.cost_summary(30)
    obs = db.observability_overview()
    context = db.tenancy_context_info()
    return {
        "status": "ok",
        "app": "observa",
        "connections": len(db.list_connections()),
        "cost_records": summary["records"],
        "open_alerts": summary.get("open_alerts", 0),
        "metric_series": obs.get("metric_count", 0),
        "auth_mode": (db.get_global_setting("auth") or {}).get("mode", "local"),
        "company_id": context["company"]["id"],
        "tenancy_id": context["tenancy"]["id"],
        "demo": True,
    }


@router.get("/context")
def context():
    return db.tenancy_context_info()


@organization_router.get("/companies")
def companies(actor: dict = Depends(require_api_key)):
    if actor["is_platform_admin"]:
        return db.list_companies()
    return db.list_companies_for_subject(actor["subject"])


@organization_router.post("/companies")
def create_company(body: CompanyCreate, actor: dict = Depends(require_api_key)):
    try:
        return db.create_company(
            body.name,
            body.slug,
            owner_subject=actor["subject"],
            owner_email=actor.get("email"),
        )
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@organization_router.get("/tenancies")
def tenancies(company_id: str | None = None, actor: dict = Depends(require_api_key)):
    if company_id and not db.get_company(company_id):
        raise HTTPException(404, "Company not found")
    if company_id:
        _require_company_role(company_id, actor, {"owner", "admin", "operator", "viewer"})
        return db.list_tenancies(company_id)
    allowed = {company["id"] for company in companies(actor)}
    return [row for row in db.list_tenancies() if row["company_id"] in allowed]


@organization_router.post("/tenancies")
def create_tenancy(body: TenancyCreate, actor: dict = Depends(require_api_key)):
    _require_company_role(body.company_id, actor, {"owner", "admin"})
    try:
        return db.create_tenancy(body.company_id, body.name, body.slug)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@organization_router.get("/companies/{company_id}/members")
def company_members(company_id: str, actor: dict = Depends(require_api_key)):
    _require_company_role(company_id, actor, {"owner", "admin"})
    return db.list_company_members(company_id)


@organization_router.put("/companies/{company_id}/members")
def put_company_member(
    company_id: str, body: CompanyMemberUpsert, actor: dict = Depends(require_api_key)
):
    _require_company_role(company_id, actor, {"owner", "admin"})
    try:
        return db.add_company_member(company_id, body.subject, body.email, body.role)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@organization_router.post("/platform/run-all")
def run_all_tenancies(
    body: PlatformRunBody | None = None, actor: dict = Depends(require_api_key)
):
    if not actor["is_platform_admin"]:
        raise HTTPException(403, "Platform administrator required")
    at = body.at if body and body.at else None
    results = []
    for tenancy in db.list_tenancies():
        if not tenancy["enabled"]:
            continue
        with db.tenancy_context(tenancy["id"]):
            try:
                budget = budget_service.monitor_budgets(at.date() if at else None)
                automation = governance_service.run_due(at)
                results.append(
                    {
                        "tenancy_id": tenancy["id"],
                        "status": "ok",
                        "budget": budget,
                        "automation": automation,
                    }
                )
            except Exception as exc:  # noqa: BLE001
                results.append(
                    {"tenancy_id": tenancy["id"], "status": "failed", "error": str(exc)[:500]}
                )
    return {"count": len(results), "tenancies": results}


@router.post("/demo/seed", dependencies=[Depends(require_tenancy_operator)])
def seed_demo():
    return sync_service.ensure_full_demo()


@router.get("/auth/me")
def auth_me(
    x_observa_api_key: str | None = Header(default=None, alias="X-Observa-Api-Key"),
    authorization: str | None = Header(default=None),
):
    """Who the caller is — a real identity if they're on an OIDC session, or
    just 'local' if they're using the shared key (require_api_key already
    accepted whichever it is; this only tells the two apart for the UI)."""
    provided = x_observa_api_key
    if not provided and authorization and authorization.lower().startswith("bearer "):
        provided = authorization[7:]
    claims = verify_session_token(provided) if provided else None
    if claims:
        return {
            "mode": "oidc",
            "subject": claims.get("sub"),
            "provider": claims.get("provider"),
            "email": claims.get("email"),
            "name": claims.get("name"),
        }
    return {"mode": "local"}


@router.get("/auth/settings", dependencies=[Depends(require_platform_admin)])
def get_auth_settings():
    auth = db.get_global_setting("auth") or {"mode": "local", "providers": {}}
    providers = {}
    for key, p in (auth.get("providers") or {}).items():
        p = dict(p)
        has_secret = bool(p.pop("client_secret_enc", None))
        p.pop("client_secret", None)  # legacy plaintext field, never echoed back
        providers[key] = {
            **p,
            "client_secret": "••••••••" if has_secret else "",
            "has_client_secret": has_secret,
        }
    return {"mode": auth.get("mode", "local"), "providers": providers}


@router.put("/auth/settings", dependencies=[Depends(require_platform_admin)])
def put_auth_settings(body: AuthSettingsUpdate):
    current = db.get_global_setting("auth") or {"mode": "local", "providers": {}}
    providers = dict(current.get("providers") or {})
    for key, incoming in (body.providers or {}).items():
        prev = dict(providers.get(key) or {})
        prev.pop("client_secret", None)  # drop any legacy plaintext value on write
        secret = incoming.get("client_secret") or ""
        if secret and secret != "••••••••":
            # Secrets at rest go through the same Fernet key as connection
            # secrets — never stored as plaintext JSON in the settings table.
            prev["client_secret_enc"] = encrypt_json({"v": secret})
        for field in ("enabled", "client_id", "issuer", "redirect_uri"):
            if field in incoming:
                prev[field] = incoming[field]
        providers[key] = prev
    saved = {"mode": body.mode, "providers": providers}
    db.set_global_setting("auth", saved)
    return {"ok": True, "mode": body.mode}


@router.get("/connectors")
def connectors():
    return sync_service.catalog_connectors()


@router.get("/connections")
def connections():
    return db.list_connections()


@router.post("/connections", dependencies=[Depends(require_tenancy_operator)])
def create_connection(body: ConnectionCreate):
    if not any(c["id"] == body.connector_id for c in sync_service.catalog_connectors()):
        raise HTTPException(400, f"Unknown connector: {body.connector_id}")
    conn_id = sync_service.new_connection_id()
    row = db.create_connection(
        conn_id=conn_id,
        name=body.name,
        connector_id=body.connector_id,
        config=body.config,
        secrets=body.secrets,
    )
    if row and "_secrets" in row:
        del row["_secrets"]
    return row


@router.patch("/connections/{conn_id}", dependencies=[Depends(require_tenancy_operator)])
def patch_connection(conn_id: str, body: ConnectionUpdate):
    row = db.update_connection(
        conn_id,
        name=body.name,
        config=body.config,
        secrets=body.secrets,
        enabled=body.enabled,
    )
    if not row:
        raise HTTPException(404, "Connection not found")
    row.pop("_secrets", None)
    return row


@router.delete("/connections/{conn_id}", dependencies=[Depends(require_tenancy_operator)])
def remove_connection(conn_id: str):
    if not db.delete_connection(conn_id):
        raise HTTPException(404, "Connection not found")
    return {"ok": True}


@router.post("/connections/test", dependencies=[Depends(require_tenancy_operator)])
def test_connection(body: TestConnectionBody):
    return sync_service.test_connection_payload(body.connector_id, body.config, body.secrets)


@router.post("/connections/{conn_id}/sync", dependencies=[Depends(require_tenancy_operator)])
def sync(conn_id: str):
    try:
        return sync_service.sync_connection(conn_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(500, str(exc)[:500]) from exc


@router.get("/costs/summary")
def costs_summary(days: int = 30):
    return db.cost_summary(days)


@router.get("/costs/trend")
def costs_trend(days: int = 30):
    return db.cost_trend(days)


@router.get("/budgets")
def budgets():
    return db.list_budget_rules()


@router.post("/budgets", dependencies=[Depends(require_tenancy_operator)])
def create_budget(body: BudgetRuleCreate):
    try:
        return budget_service.create_rule(body.model_dump())
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.patch("/budgets/{rule_id}", dependencies=[Depends(require_tenancy_operator)])
def patch_budget(rule_id: str, body: BudgetRuleUpdate):
    try:
        row = budget_service.update_rule(rule_id, body.model_dump(exclude_unset=True))
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    if not row:
        raise HTTPException(404, "Budget rule not found")
    return row


@router.delete("/budgets/{rule_id}", dependencies=[Depends(require_tenancy_operator)])
def delete_budget(rule_id: str):
    if not db.delete_budget_rule(rule_id):
        raise HTTPException(404, "Budget rule not found")
    return {"ok": True}


@router.post("/budgets/evaluate", dependencies=[Depends(require_tenancy_operator)])
def evaluate_budgets(body: BudgetEvaluateBody | None = None):
    return budget_service.evaluate_budgets(body.at if body else None)


@router.post("/budgets/monitor", dependencies=[Depends(require_tenancy_operator)])
def monitor_budgets(body: BudgetEvaluateBody | None = None):
    return budget_service.monitor_budgets(body.at if body else None)


@router.get("/budgets/events")
def budget_events(rule_id: str | None = None):
    return db.list_budget_events(rule_id)


@router.get("/products")
def products():
    return db.list_products()


@router.get("/products/{slug}")
def product_detail(slug: str):
    item = db.get_product(slug)
    if not item:
        raise HTTPException(404, "Product not found")
    return item


@router.get("/resources")
def resources(product: str | None = None, untagged: bool = False):
    rows = db.list_resources(product)
    if untagged:
        rows = [row for row in rows if not row.get("product") or not row.get("labels")]
    return rows


@router.patch("/resources/{resource_uid}/tags", dependencies=[Depends(require_tenancy_operator)])
def patch_resource_tags(resource_uid: int, body: ResourceTagsUpdate):
    try:
        return governance_service.apply_resource_tags(
            resource_uid, body.tags, dry_run=body.dry_run, write_back=body.write_back
        )
    except ValueError as exc:
        raise HTTPException(404 if "not found" in str(exc).lower() else 400, str(exc)) from exc
    except NotImplementedError as exc:
        raise HTTPException(409, str(exc)) from exc


@router.get("/automation/policies")
def automation_policies():
    return db.list_policies()


@router.post("/automation/policies", dependencies=[Depends(require_tenancy_operator)])
def create_automation_policy(body: PolicyCreate):
    try:
        return governance_service.create_policy(body.model_dump())
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.patch("/automation/policies/{policy_id}", dependencies=[Depends(require_tenancy_operator)])
def patch_automation_policy(policy_id: str, body: PolicyUpdate):
    row = db.update_policy(policy_id, body.model_dump(exclude_unset=True))
    if not row:
        raise HTTPException(404, "Policy not found")
    return row


@router.delete("/automation/policies/{policy_id}", dependencies=[Depends(require_tenancy_operator)])
def delete_automation_policy(policy_id: str):
    if not db.delete_policy(policy_id):
        raise HTTPException(404, "Policy not found")
    return {"ok": True}


@router.post("/automation/run-due", dependencies=[Depends(require_tenancy_operator)])
def run_due_automation(body: AutomationRunBody | None = None):
    return governance_service.run_due(body.at if body else None)


@router.get("/automation/actions")
def automation_actions(status: str | None = None):
    return db.list_actions(status)


@router.post("/automation/actions/{action_id}/approve", dependencies=[Depends(require_tenancy_operator)])
def approve_automation_action(action_id: str):
    try:
        return governance_service.approve_action(action_id)
    except ValueError as exc:
        raise HTTPException(404 if "not found" in str(exc).lower() else 409, str(exc)) from exc


@router.post("/automation/actions/{action_id}/reject", dependencies=[Depends(require_tenancy_operator)])
def reject_automation_action(action_id: str, body: ActionRejectBody):
    try:
        return governance_service.reject_action(action_id, body.reason)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.get("/observability")
def observability():
    return db.observability_overview()


@router.get("/metrics/series")
def metrics_series(name: str, product: str | None = None, hours: int = 24):
    return db.metric_series(name, product=product, hours=hours)


@router.get("/alerts")
def alerts(status: str | None = None):
    return db.list_alerts(status)


@router.get("/ecosystem")
def ecosystem(product: str = "hiperlocal"):
    from app.application.demo_platform import ecosystem as eco

    return eco(product)


@router.get("/dashboards")
def dashboards():
    from app.application.demo_platform import dashboards as dlist

    return dlist()


@router.get("/dashboards/{dash_id}")
def dashboard_detail(dash_id: str):
    from app.application.demo_platform import dashboard_detail as detail

    return detail(dash_id)


@router.get("/monitors")
def monitors():
    from app.application.demo_platform import monitors as mlist

    return mlist()


@router.get("/logs")
def logs(
    limit: int = 100,
    product: str | None = None,
    severity: str | None = None,
    source: str | None = None,
    q: str | None = None,
):
    return db.list_logs(
        limit=limit, product=product, severity=severity, source=source, query=q
    )


@router.post("/logs/ingest", dependencies=[Depends(require_tenancy_operator)])
def ingest_logs(body: LogIngestBody):
    rows = [
        {
            **item.model_dump(exclude={"ts"}),
            "ts": item.ts.isoformat().replace("+00:00", "Z"),
        }
        for item in body.logs
    ]
    count = db.append_logs(body.connection_id, rows)
    db.add_audit_event("logs.ingested", body.connection_id, {"count": count})
    return {"ok": True, "count": count}


@router.get("/remediations")
def remediations(status: str | None = None):
    return db.list_remediation_proposals(status)


@router.post("/remediations/analyze", dependencies=[Depends(require_tenancy_operator)])
def analyze_remediations(body: RemediationAnalyzeBody | None = None):
    payload = body or RemediationAnalyzeBody()
    return remediation_service.analyze_logs(
        executor_connection_id=payload.executor_connection_id,
        dry_run=payload.dry_run,
        limit=payload.limit,
    )


@router.post(
    "/remediations/{proposal_id}/approve", dependencies=[Depends(require_tenancy_admin)]
)
def approve_remediation(proposal_id: str):
    try:
        return remediation_service.approve_proposal(proposal_id)
    except (ValueError, NotImplementedError) as exc:
        raise HTTPException(409, str(exc)) from exc


@router.post(
    "/remediations/{proposal_id}/reject", dependencies=[Depends(require_tenancy_admin)]
)
def reject_remediation(proposal_id: str, body: RemediationRejectBody):
    try:
        return remediation_service.reject_proposal(proposal_id, body.reason)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.post(
    "/remediations/{proposal_id}/feedback", dependencies=[Depends(require_tenancy_operator)]
)
def remediation_feedback(proposal_id: str, body: RemediationFeedbackBody):
    try:
        return remediation_service.record_feedback(proposal_id, body.outcome, body.notes)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/traces")
def traces(limit: int = 50):
    from app.application.demo_platform import traces as trace_list

    return trace_list(limit=limit)


@router.get("/gcp/monitoring")
def gcp_monitoring():
    from app.application.demo_platform import gcp_monitoring_metrics

    return gcp_monitoring_metrics()


@router.get("/rum")
def rum():
    from app.application.demo_platform import rum_summary

    return rum_summary()


@router.get("/synthetics")
def synthetics():
    from app.application.demo_platform import synthetics as syn

    return syn()
