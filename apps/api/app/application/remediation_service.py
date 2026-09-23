from __future__ import annotations

import hashlib
from collections import Counter
from typing import Any

from observa_connectors import get_connector

from app.core import db

PATTERNS = (
    (
        "timeout",
        ("timeout", "timed out", "deadline exceeded"),
        "Repeated dependency timeouts",
        "Requests are repeatedly exceeding a dependency or network deadline.",
        "Inspect dependency latency and saturation; apply bounded retries and tune timeouts only after measuring the downstream SLO.",
        {"kind": "runbook", "operation": "investigate_dependency_timeout"},
    ),
    (
        "connection-pool",
        ("connection pool", "too many connections", "pool exhausted"),
        "Connection pool exhaustion",
        "The application is exhausting its database or client connection pool.",
        "Check leaked connections, pool sizing and database limits before changing capacity.",
        {"kind": "runbook", "operation": "inspect_connection_pool"},
    ),
    (
        "memory",
        ("out of memory", "oomkilled", "memory limit"),
        "Memory pressure or OOM",
        "Processes or containers are reaching their memory limit.",
        "Capture a heap/profile sample, inspect recent releases, then resize or roll back through the approved deployment pipeline.",
        {"kind": "deployment", "operation": "investigate_memory_pressure"},
    ),
    (
        "panic",
        ("panic", "nullpointer", "null pointer", "unhandled exception"),
        "Unhandled application failure",
        "The application is emitting unhandled exceptions or panic recovery events.",
        "Correlate the trace and release, reproduce safely, and generate a reviewed patch or rollback through CI.",
        {"kind": "code", "operation": "open_fix_workflow"},
    ),
)


def analyze_logs(
    *, executor_connection_id: str | None = None, dry_run: bool = True, limit: int = 1000
) -> dict[str, Any]:
    logs = db.list_logs(limit=limit)
    counters: Counter[tuple[str, str, str]] = Counter()
    definitions = {pattern[0]: pattern for pattern in PATTERNS}
    for row in logs:
        message = row["message"].lower()
        for key, needles, *_ in PATTERNS:
            if any(needle in message for needle in needles):
                counters[(key, row.get("product") or "unknown", row.get("service") or "unknown")] += 1
                break

    proposals = []
    for (key, product, service), count in counters.items():
        if count < 2:
            continue
        _, _, title, diagnosis, recommendation, action = definitions[key]
        fingerprint = hashlib.sha256(f"{key}:{product}:{service}".encode()).hexdigest()
        existing = db.get_remediation_by_fingerprint(fingerprint)
        feedback = db.latest_remediation_feedback(existing["id"]) if existing else None
        if feedback and feedback["outcome"] == "false_positive":
            continue
        if feedback and feedback["outcome"] == "successful":
            recommendation = f"Previously validated in this tenancy. {recommendation}"
        proposals.append(
            db.upsert_remediation_proposal(
                {
                    "fingerprint": fingerprint,
                    "title": f"{title} · {product}/{service}",
                    "diagnosis": f"{diagnosis} Observa matched {count} tenant-local log events.",
                    "recommendation": recommendation,
                    "action": {**action, "product": product, "service": service},
                    "evidence_count": count,
                    "executor_connection_id": executor_connection_id,
                    "dry_run": dry_run,
                }
            )
        )
    db.add_audit_event(
        "remediation.analysis",
        db.current_tenancy_id(),
        {"logs_scanned": len(logs), "proposals": len(proposals), "local_only": True},
    )
    return {"logs_scanned": len(logs), "count": len(proposals), "proposals": proposals}


def approve_proposal(proposal_id: str) -> dict:
    proposal = db.get_remediation_proposal(proposal_id)
    if not proposal:
        raise ValueError("Remediation proposal not found")
    if proposal["status"] not in {"suggested", "rejected"}:
        raise ValueError(f"Proposal cannot be approved from status {proposal['status']}")
    if proposal["dry_run"]:
        updated = db.update_remediation_proposal(
            proposal_id, status="simulated", result_message="Approved dry-run; no external system changed."
        )
    else:
        connection_id = proposal.get("executor_connection_id")
        connection = db.get_connection(connection_id) if connection_id else None
        if not connection:
            raise ValueError("A remediation executor connection is required for a real change")
        connector = get_connector(connection["connector_id"])
        if not connector:
            raise ValueError("Remediation connector not found")
        safe_payload = {
            key: proposal[key]
            for key in ("id", "title", "diagnosis", "recommendation", "action")
        }
        result = connector.apply_remediation(
            connection["config"],
            connection.get("_secrets") or {},
            proposal=safe_payload,
            dry_run=False,
        )
        updated = db.update_remediation_proposal(
            proposal_id,
            status="applied" if result.ok else "failed",
            result_message=result.message,
        )
    db.add_audit_event("remediation.approved", proposal_id, {"status": updated["status"]})
    return updated


def reject_proposal(proposal_id: str, reason: str) -> dict:
    proposal = db.get_remediation_proposal(proposal_id)
    if not proposal:
        raise ValueError("Remediation proposal not found")
    updated = db.update_remediation_proposal(proposal_id, status="rejected", result_message=reason)
    db.add_remediation_feedback(proposal_id, "rejected", reason)
    db.add_audit_event("remediation.rejected", proposal_id, {"reason": reason})
    return updated


def record_feedback(proposal_id: str, outcome: str, notes: str | None) -> dict:
    if outcome not in {"successful", "failed", "false_positive"}:
        raise ValueError("Outcome must be successful, failed or false_positive")
    if not db.get_remediation_proposal(proposal_id):
        raise ValueError("Remediation proposal not found")
    feedback = db.add_remediation_feedback(proposal_id, outcome, notes)
    if outcome == "successful":
        db.update_remediation_proposal(proposal_id, status="resolved", result_message=notes)
    return feedback
