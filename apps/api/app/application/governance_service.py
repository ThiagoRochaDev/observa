from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from observa_connectors import get_connector

from app.core import db


def apply_resource_tags(
    resource_uid: int,
    tags: dict[str, str],
    *,
    dry_run: bool = True,
    write_back: bool = True,
) -> dict[str, Any]:
    resource = db.get_resource(resource_uid)
    if not resource:
        raise ValueError("Resource not found")
    clean_tags = {str(key).strip(): str(value).strip() for key, value in tags.items() if str(key).strip()}
    if not clean_tags:
        raise ValueError("At least one tag is required")

    message = "Local metadata validated"
    if write_back:
        connection = db.get_connection(resource["connection_id"])
        if not connection:
            raise ValueError("Resource connection not found")
        connector = get_connector(connection["connector_id"])
        if not connector:
            raise ValueError("Resource connector not found")
        result = connector.apply_tags(
            connection["config"],
            connection.get("_secrets") or {},
            resource=resource,
            tags=clean_tags,
            dry_run=dry_run,
        )
        if not result.ok:
            raise RuntimeError(result.message)
        message = result.message

    updated = resource if dry_run else db.update_resource_tags(resource_uid, clean_tags)
    db.add_audit_event(
        "resource.tags.preview" if dry_run else "resource.tags.updated",
        str(resource_uid),
        {"tags": clean_tags, "write_back": write_back, "message": message},
    )
    return {"ok": True, "dry_run": dry_run, "message": message, "resource": updated}


def create_policy(payload: dict[str, Any]) -> dict:
    if not payload.get("resource_ids") and not payload.get("selector"):
        raise ValueError("Policy needs resource_ids or a selector")
    _validate_timezone(payload.get("timezone") or "UTC")
    policy = {**payload, "id": f"pol_{uuid.uuid4().hex[:12]}"}
    saved = db.create_policy(policy)
    db.add_audit_event("policy.created", saved["id"], saved)
    return saved


def run_due(at: datetime | None = None) -> dict[str, Any]:
    now = at or datetime.now(timezone.utc)
    created: list[dict] = []
    for policy in db.list_policies():
        if not policy["enabled"]:
            continue
        local_now = now.astimezone(_validate_timezone(policy["timezone"]))
        action, reason = _due_action(policy, local_now)
        if not action:
            continue
        scheduled_for = local_now.replace(second=0, microsecond=0).isoformat()
        resources = _matching_resources(policy)
        for resource in resources:
            if _already_planned(policy["id"], resource["uid"], action, scheduled_for):
                continue
            status = "pending_approval" if policy["require_approval"] else "planned"
            item = db.create_action(
                {
                    "id": f"act_{uuid.uuid4().hex[:12]}",
                    "policy_id": policy["id"],
                    "resource_uid": resource["uid"],
                    "action": action,
                    "status": status,
                    "scheduled_for": scheduled_for,
                    "reason": reason,
                }
            )
            created.append(item)
            if not policy["require_approval"]:
                execute_action(item["id"])
    return {"evaluated_at": now.isoformat(), "created": created, "count": len(created)}


def approve_action(action_id: str) -> dict:
    action = db.get_action(action_id)
    if not action:
        raise ValueError("Action not found")
    if action["status"] not in {"pending_approval", "planned"}:
        raise ValueError(f"Action cannot be approved from status {action['status']}")
    db.update_action(action_id, status="approved", result_message="Approved")
    return execute_action(action_id)


def reject_action(action_id: str, reason: str = "Rejected by operator") -> dict:
    action = db.update_action(action_id, status="rejected", result_message=reason)
    if not action:
        raise ValueError("Action not found")
    db.add_audit_event("action.rejected", action_id, {"reason": reason})
    return action


def execute_action(action_id: str) -> dict:
    action = db.get_action(action_id)
    if not action:
        raise ValueError("Action not found")
    policy = db.get_policy(action["policy_id"]) if action.get("policy_id") else None
    resource = db.get_resource(action["resource_uid"])
    if not resource:
        return db.update_action(action_id, status="failed", result_message="Resource not found")  # type: ignore[return-value]
    connection = db.get_connection(resource["connection_id"])
    connector = get_connector(connection["connector_id"]) if connection else None
    if not connection or not connector:
        return db.update_action(action_id, status="failed", result_message="Connector not found")  # type: ignore[return-value]

    dry_run = policy["dry_run"] if policy else bool(action.get("dry_run", True))
    try:
        result = connector.change_power_state(
            connection["config"],
            connection.get("_secrets") or {},
            resource=resource,
            action=action["action"],
            dry_run=dry_run,
        )
        status = "simulated" if dry_run else "executed"
        updated = db.update_action(action_id, status=status, result_message=result.message)
        if not dry_run:
            db.update_resource_status(resource["uid"], "running" if action["action"] == "start" else "stopped")
        db.add_audit_event(f"action.{status}", action_id, {"message": result.message})
        return updated  # type: ignore[return-value]
    except Exception as exc:
        return db.update_action(action_id, status="failed", result_message=str(exc)[:500])  # type: ignore[return-value]


def _due_action(policy: dict, local_now: datetime) -> tuple[str | None, str | None]:
    if policy.get("expires_at"):
        expires = datetime.fromisoformat(policy["expires_at"].replace("Z", "+00:00"))
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=ZoneInfo(policy["timezone"]))
        if local_now >= expires.astimezone(local_now.tzinfo):
            return policy["expiration_action"], "Policy expiration reached"
    if local_now.weekday() not in policy["weekdays"]:
        return None, None
    current = local_now.strftime("%H:%M")
    if policy.get("stop_time") == current:
        return "stop", "Scheduled stop time reached"
    if policy.get("start_time") == current:
        return "start", "Scheduled start time reached"
    return None, None


def _matching_resources(policy: dict) -> list[dict]:
    resources = db.list_resources()
    ids = set(policy.get("resource_ids") or [])
    selector = policy.get("selector") or {}
    selected = []
    for resource in resources:
        if ids and resource["uid"] in ids:
            selected.append(resource)
            continue
        if selector and all(
            resource.get(key) == value or resource.get("labels", {}).get(key) == value
            for key, value in selector.items()
        ):
            selected.append(resource)
    return selected


def _already_planned(policy_id: str, resource_uid: int, action: str, scheduled_for: str) -> bool:
    return any(
        item["policy_id"] == policy_id
        and item["resource_uid"] == resource_uid
        and item["action"] == action
        and item["scheduled_for"] == scheduled_for
        for item in db.list_actions()
    )


def _validate_timezone(name: str):
    if name.upper() in {"UTC", "ETC/UTC"}:
        return timezone.utc
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"Unknown timezone: {name}") from exc
