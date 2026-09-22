from __future__ import annotations

import uuid
from datetime import date, timedelta
from typing import Any

from app.core import db
from app.application import sync_service


VALID_SCOPES = {"project", "account", "product", "provider", "resource"}
VALID_RESPONSES = {"notify", "approval", "ignore"}


def create_rule(payload: dict[str, Any]) -> dict:
    _validate_rule(payload)
    rule = {**payload, "id": f"bud_{uuid.uuid4().hex[:12]}"}
    saved = db.create_budget_rule(rule)
    db.add_audit_event("budget.rule.created", saved["id"], saved)
    return saved


def update_rule(rule_id: str, changes: dict[str, Any]) -> dict | None:
    current = db.get_budget_rule(rule_id)
    if not current:
        return None
    merged = {**current, **{key: value for key, value in changes.items() if value is not None}}
    _validate_rule(merged)
    saved = db.update_budget_rule(rule_id, changes)
    if saved:
        db.add_audit_event("budget.rule.updated", rule_id, changes)
    return saved


def evaluate_budgets(today: date | None = None) -> dict[str, Any]:
    current_day = today or date.today()
    results = []
    created_events = []
    for rule in db.list_budget_rules():
        if not rule["enabled"]:
            continue
        spend = db.budget_spend(rule["scope_type"], rule["scope_value"], rule["window_days"])
        evaluated_cost = max(spend["actual"], spend["projected"])
        usage_pct = evaluated_cost / rule["amount"] if rule["amount"] else 0.0
        level = _level(usage_pct, rule)
        result = {
            "rule_id": rule["id"],
            "level": level,
            "actual_cost": spend["actual"],
            "projected_cost": spend["projected"],
            "usage_pct": round(usage_pct, 4),
            "observed_days": spend["observed_days"],
        }
        results.append(result)
        if level == "normal":
            continue
        dedupe_key = f"{rule['id']}:{current_day.isoformat()}:{level}"
        existing = db.get_budget_event_by_dedupe(dedupe_key)
        if existing:
            result["event_id"] = existing["id"]
            result["deduplicated"] = True
            continue
        event = _create_event(rule, spend, usage_pct, level, current_day, dedupe_key)
        result["event_id"] = event["id"]
        created_events.append(event)
    return {
        "evaluated_at": current_day.isoformat(),
        "rules": results,
        "created": created_events,
        "count": len(created_events),
    }


def monitor_budgets(today: date | None = None) -> dict[str, Any]:
    cost_connectors = {
        item["id"] for item in sync_service.catalog_connectors() if "cost" in item["capabilities"]
    }
    synced = []
    failed = []
    for connection in db.list_connections():
        if not connection["enabled"] or connection["connector_id"] not in cost_connectors:
            continue
        try:
            result = sync_service.sync_connection(connection["id"])
            synced.append({"connection_id": connection["id"], "status": result["status"]})
        except Exception as exc:
            failed.append({"connection_id": connection["id"], "message": str(exc)[:300]})
    evaluation = evaluate_budgets(today)
    return {"synced": synced, "failed": failed, "evaluation": evaluation}


def _create_event(
    rule: dict,
    spend: dict,
    usage_pct: float,
    level: str,
    current_day: date,
    dedupe_key: str,
) -> dict:
    response = rule["response_mode"]
    action_ids: list[str] = []
    status = "ignored" if response == "ignore" else "notified"
    if response == "approval":
        resources = _matching_resources(rule)
        for resource in resources:
            existing = _pending_action(rule["name"], resource["uid"])
            if existing:
                action_ids.append(existing["id"])
            else:
                action = db.create_action(
                    {
                        "id": f"act_{uuid.uuid4().hex[:12]}",
                        "policy_id": None,
                        "resource_uid": resource["uid"],
                        "action": "stop",
                        "status": "pending_approval",
                        "scheduled_for": None,
                        "reason": (
                            f"Budget {rule['name']} protection triggered: "
                            f"{usage_pct * 100:.1f}% of {rule['currency']} {rule['amount']:.2f}"
                        ),
                        "dry_run": rule["dry_run"],
                    }
                )
                action_ids.append(action["id"])
        status = "pending_approval" if action_ids else "needs_mapping"

    period_start = current_day - timedelta(days=rule["window_days"] - 1)
    message = (
        f"{rule['name']}: actual {rule['currency']} {spend['actual']:.2f}, "
        f"projected {rule['currency']} {spend['projected']:.2f}, "
        f"budget usage {usage_pct * 100:.1f}%"
    )
    event = db.create_budget_event(
        {
            "id": f"bev_{uuid.uuid4().hex[:12]}",
            "rule_id": rule["id"],
            "dedupe_key": dedupe_key,
            "level": level,
            "status": status,
            "actual_cost": spend["actual"],
            "projected_cost": spend["projected"],
            "usage_pct": round(usage_pct, 4),
            "period_start": period_start.isoformat(),
            "period_end": current_day.isoformat(),
            "action_ids": action_ids,
            "message": message,
        }
    )
    if response != "ignore":
        db.upsert_alert(
            {
                "id": f"budget-{rule['id']}-{current_day.isoformat()}-{level}",
                "severity": "high" if level == "critical" else "medium",
                "category": "budget",
                "product": rule["scope_value"] if rule["scope_type"] == "product" else None,
                "title": f"Budget {level}: {rule['name']}",
                "message": message,
                "status": "pending" if status == "pending_approval" else "open",
            }
        )
    db.add_audit_event("budget.event.created", event["id"], event)
    return event


def _matching_resources(rule: dict) -> list[dict]:
    resources = db.list_resources()
    explicit = set(rule.get("resource_ids") or [])
    if explicit:
        return [resource for resource in resources if resource["uid"] in explicit]
    scope_type = rule["scope_type"]
    scope_value = rule["scope_value"]
    if scope_type == "resource":
        return [
            resource for resource in resources
            if resource["id"] == scope_value or str(resource["uid"]) == scope_value
        ]
    if scope_type in {"product", "provider"}:
        return [resource for resource in resources if resource.get(scope_type) == scope_value]
    if scope_type in {"project", "account"}:
        matched = []
        for resource in resources:
            labels = resource.get("labels") or {}
            connection = db.get_connection(resource["connection_id"])
            config = connection.get("config") if connection else {}
            candidates = {
                labels.get("project"), labels.get("project_id"), labels.get("account"),
                config.get("project_id"), config.get("account_label"), config.get("subscription_id"),
            }
            if scope_value in candidates:
                matched.append(resource)
        return matched
    return []


def _pending_action(rule_name: str, resource_uid: int) -> dict | None:
    prefix = f"Budget {rule_name} protection triggered:"
    for action in db.list_actions():
        if (
            action["resource_uid"] == resource_uid
            and action["status"] in {"pending_approval", "approved", "planned"}
            and str(action.get("reason") or "").startswith(prefix)
        ):
            return action
    return None


def _level(usage_pct: float, rule: dict) -> str:
    if usage_pct >= rule["critical_threshold"]:
        return "critical"
    if usage_pct >= rule["warning_threshold"]:
        return "warning"
    return "normal"


def _validate_rule(rule: dict[str, Any]) -> None:
    if rule.get("scope_type") not in VALID_SCOPES:
        raise ValueError(f"scope_type must be one of {sorted(VALID_SCOPES)}")
    if not str(rule.get("scope_value") or "").strip():
        raise ValueError("scope_value is required")
    if float(rule.get("amount") or 0) <= 0:
        raise ValueError("amount must be greater than zero")
    if int(rule.get("window_days") or 0) < 1:
        raise ValueError("window_days must be at least 1")
    warning = float(rule.get("warning_threshold", 0.8))
    critical = float(rule.get("critical_threshold", 1.0))
    if not 0 < warning <= critical:
        raise ValueError("thresholds must satisfy 0 < warning <= critical")
    if rule.get("response_mode") not in VALID_RESPONSES:
        raise ValueError(f"response_mode must be one of {sorted(VALID_RESPONSES)}")
    if rule.get("response_mode") == "approval" and not rule.get("owner"):
        raise ValueError("owner is required when response_mode is approval")
