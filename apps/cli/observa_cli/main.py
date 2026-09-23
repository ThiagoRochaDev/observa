from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


class Client:
    def __init__(self, base_url: str, api_key: str, company_id: str = "", tenancy_id: str = ""):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.company_id = company_id
        self.tenancy_id = tenancy_id

    def request(self, method: str, path: str, body: dict | None = None) -> Any:
        data = json.dumps(body).encode() if body is not None else None
        headers = {"Content-Type": "application/json", "X-Observa-Api-Key": self.api_key}
        if self.company_id:
            headers["X-Observa-Company-ID"] = self.company_id
        if self.tenancy_id:
            headers["X-Observa-Tenancy-ID"] = self.tenancy_id
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=data,
            method=method,
            headers=headers,
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="replace")
            raise RuntimeError(f"Observa API returned HTTP {exc.code}: {detail}") from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="observa", description="Observa FinOps governance CLI")
    parser.add_argument("--url", default=os.getenv("OBSERVA_URL", "http://localhost:8080"))
    parser.add_argument("--api-key", default=os.getenv("OBSERVA_API_KEY", ""))
    parser.add_argument("--company-id", default=os.getenv("OBSERVA_COMPANY_ID", ""))
    parser.add_argument("--tenancy-id", default=os.getenv("OBSERVA_TENANCY_ID", ""))
    parser.add_argument("--json", action="store_true", help="Print raw JSON")
    commands = parser.add_subparsers(dest="command", required=True)

    companies = commands.add_parser("companies")
    companies_sub = companies.add_subparsers(dest="operation", required=True)
    companies_sub.add_parser("list")
    company_create = companies_sub.add_parser("create")
    company_create.add_argument("name")
    company_create.add_argument("--slug")

    tenancies = commands.add_parser("tenancies")
    tenancies_sub = tenancies.add_subparsers(dest="operation", required=True)
    tenancy_list = tenancies_sub.add_parser("list")
    tenancy_list.add_argument("--company")
    tenancy_create = tenancies_sub.add_parser("create")
    tenancy_create.add_argument("name")
    tenancy_create.add_argument("--company", required=True)
    tenancy_create.add_argument("--slug")

    members = commands.add_parser("members")
    members.add_argument("--company", required=True)
    members.add_argument("--add", metavar="OIDC_SUBJECT")
    members.add_argument("--email")
    members.add_argument("--role", default="viewer", choices=["owner", "admin", "operator", "viewer"])

    resources = commands.add_parser("resources")
    resources.add_argument("--untagged", action="store_true")
    resources.add_argument("--product")

    tag = commands.add_parser("tag")
    tag.add_argument("resource_uid", type=int)
    tag.add_argument("--set", action="append", required=True, metavar="KEY=VALUE")
    tag.add_argument("--apply", action="store_true", help="Apply instead of dry-run")
    tag.add_argument("--local-only", action="store_true", help="Do not write tags back to cloud")

    policies = commands.add_parser("policies")
    policies_sub = policies.add_subparsers(dest="operation", required=True)
    policies_sub.add_parser("list")
    create = policies_sub.add_parser("create")
    create.add_argument("name")
    create.add_argument("--resource", action="append", type=int, default=[])
    create.add_argument("--selector", action="append", default=[], metavar="KEY=VALUE")
    create.add_argument("--timezone", default="UTC")
    create.add_argument("--start")
    create.add_argument("--stop")
    create.add_argument("--expires-at")
    create.add_argument("--weekdays", default="0,1,2,3,4")
    create.add_argument("--no-approval", action="store_true")
    create.add_argument("--apply", action="store_true", help="Execute real cloud actions")

    actions = commands.add_parser("actions")
    actions_sub = actions.add_subparsers(dest="operation", required=True)
    actions_list = actions_sub.add_parser("list")
    actions_list.add_argument("--status")
    approve = actions_sub.add_parser("approve")
    approve.add_argument("action_id")
    reject = actions_sub.add_parser("reject")
    reject.add_argument("action_id")
    reject.add_argument("--reason", default="Rejected from CLI")

    budgets = commands.add_parser("budgets")
    budgets_sub = budgets.add_subparsers(dest="operation", required=True)
    budgets_sub.add_parser("list")
    budget_create = budgets_sub.add_parser("create")
    budget_create.add_argument("name")
    budget_create.add_argument("--scope", required=True, choices=["project", "account", "product", "provider", "resource"])
    budget_create.add_argument("--value", required=True)
    budget_create.add_argument("--amount", required=True, type=float)
    budget_create.add_argument("--currency", default="BRL")
    budget_create.add_argument("--days", default=30, type=int)
    budget_create.add_argument("--warning", default=80, type=float)
    budget_create.add_argument("--critical", default=100, type=float)
    budget_create.add_argument("--response", default="notify", choices=["notify", "approval", "ignore"])
    budget_create.add_argument("--owner")
    budget_create.add_argument("--resource", action="append", type=int, default=[])
    budget_create.add_argument("--apply", action="store_true")
    budgets_sub.add_parser("evaluate")
    budgets_sub.add_parser("monitor")
    budget_events = budgets_sub.add_parser("events")
    budget_events.add_argument("--rule")
    budget_delete = budgets_sub.add_parser("delete")
    budget_delete.add_argument("rule_id")

    remediations = commands.add_parser("remediations")
    remediation_sub = remediations.add_subparsers(dest="operation", required=True)
    remediation_sub.add_parser("list")
    remediation_analyze = remediation_sub.add_parser("analyze")
    remediation_analyze.add_argument("--executor")
    remediation_analyze.add_argument("--apply", action="store_true")
    remediation_approve = remediation_sub.add_parser("approve")
    remediation_approve.add_argument("proposal_id")
    remediation_reject = remediation_sub.add_parser("reject")
    remediation_reject.add_argument("proposal_id")
    remediation_reject.add_argument("--reason", default="Rejected from CLI")

    run = commands.add_parser("run-due")
    run.add_argument("--at", help="ISO-8601 timestamp used for deterministic evaluation")
    run_all = commands.add_parser("run-all-tenancies")
    run_all.add_argument("--at", help="ISO-8601 timestamp used for deterministic evaluation")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if not args.api_key:
        raise SystemExit("Set OBSERVA_API_KEY or pass --api-key")
    client = Client(args.url, args.api_key, args.company_id, args.tenancy_id)
    try:
        result = dispatch(client, args)
        print_result(result, raw=args.json)
    except (RuntimeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


def dispatch(client: Client, args: argparse.Namespace) -> Any:
    if args.command == "companies" and args.operation == "list":
        return client.request("GET", "/api/companies")
    if args.command == "companies" and args.operation == "create":
        return client.request("POST", "/api/companies", {"name": args.name, "slug": args.slug})
    if args.command == "tenancies" and args.operation == "list":
        query = f"?company_id={urllib.parse.quote(args.company)}" if args.company else ""
        return client.request("GET", f"/api/tenancies{query}")
    if args.command == "tenancies" and args.operation == "create":
        return client.request(
            "POST",
            "/api/tenancies",
            {"company_id": args.company, "name": args.name, "slug": args.slug},
        )
    if args.command == "members":
        if args.add:
            return client.request(
                "PUT",
                f"/api/companies/{args.company}/members",
                {"subject": args.add, "email": args.email, "role": args.role},
            )
        return client.request("GET", f"/api/companies/{args.company}/members")
    if args.command == "resources":
        query = urllib.parse.urlencode(
            {key: value for key, value in {"untagged": args.untagged, "product": args.product}.items() if value}
        )
        return client.request("GET", f"/api/resources{'?' + query if query else ''}")
    if args.command == "tag":
        return client.request(
            "PATCH",
            f"/api/resources/{args.resource_uid}/tags",
            {
                "tags": parse_pairs(args.set),
                "dry_run": not args.apply,
                "write_back": not args.local_only,
            },
        )
    if args.command == "policies" and args.operation == "list":
        return client.request("GET", "/api/automation/policies")
    if args.command == "policies" and args.operation == "create":
        return client.request(
            "POST",
            "/api/automation/policies",
            {
                "name": args.name,
                "resource_ids": args.resource,
                "selector": parse_pairs(args.selector),
                "timezone": args.timezone,
                "weekdays": [int(day) for day in args.weekdays.split(",")],
                "start_time": args.start,
                "stop_time": args.stop,
                "expires_at": args.expires_at,
                "require_approval": not args.no_approval,
                "dry_run": not args.apply,
            },
        )
    if args.command == "actions" and args.operation == "list":
        query = f"?status={urllib.parse.quote(args.status)}" if args.status else ""
        return client.request("GET", f"/api/automation/actions{query}")
    if args.command == "actions" and args.operation == "approve":
        return client.request("POST", f"/api/automation/actions/{args.action_id}/approve", {})
    if args.command == "actions" and args.operation == "reject":
        return client.request(
            "POST", f"/api/automation/actions/{args.action_id}/reject", {"reason": args.reason}
        )
    if args.command == "budgets" and args.operation == "list":
        return client.request("GET", "/api/budgets")
    if args.command == "budgets" and args.operation == "create":
        return client.request(
            "POST",
            "/api/budgets",
            {
                "name": args.name,
                "scope_type": args.scope,
                "scope_value": args.value,
                "amount": args.amount,
                "currency": args.currency,
                "window_days": args.days,
                "warning_threshold": args.warning / 100,
                "critical_threshold": args.critical / 100,
                "response_mode": args.response,
                "owner": args.owner,
                "resource_ids": args.resource,
                "dry_run": not args.apply,
                "enabled": True,
            },
        )
    if args.command == "budgets" and args.operation == "evaluate":
        return client.request("POST", "/api/budgets/evaluate", {})
    if args.command == "budgets" and args.operation == "monitor":
        return client.request("POST", "/api/budgets/monitor", {})
    if args.command == "budgets" and args.operation == "events":
        query = f"?rule_id={urllib.parse.quote(args.rule)}" if args.rule else ""
        return client.request("GET", f"/api/budgets/events{query}")
    if args.command == "budgets" and args.operation == "delete":
        return client.request("DELETE", f"/api/budgets/{args.rule_id}")
    if args.command == "remediations" and args.operation == "list":
        return client.request("GET", "/api/remediations")
    if args.command == "remediations" and args.operation == "analyze":
        return client.request(
            "POST",
            "/api/remediations/analyze",
            {"executor_connection_id": args.executor, "dry_run": not args.apply},
        )
    if args.command == "remediations" and args.operation == "approve":
        return client.request("POST", f"/api/remediations/{args.proposal_id}/approve", {})
    if args.command == "remediations" and args.operation == "reject":
        return client.request(
            "POST",
            f"/api/remediations/{args.proposal_id}/reject",
            {"reason": args.reason},
        )
    if args.command == "run-due":
        return client.request("POST", "/api/automation/run-due", {"at": args.at})
    if args.command == "run-all-tenancies":
        return client.request("POST", "/api/platform/run-all", {"at": args.at})
    raise ValueError("Unsupported command")


def parse_pairs(items: list[str]) -> dict[str, str]:
    pairs: dict[str, str] = {}
    for item in items:
        if "=" not in item:
            raise ValueError(f"Expected KEY=VALUE, received {item!r}")
        key, value = item.split("=", 1)
        if not key.strip():
            raise ValueError("Tag or selector key cannot be empty")
        pairs[key.strip()] = value.strip()
    return pairs


def print_result(result: Any, *, raw: bool) -> None:
    if raw or not isinstance(result, list):
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return
    if not result:
        print("No results")
        return
    columns = [key for key in ("uid", "id", "name", "provider", "type", "status", "action") if key in result[0]]
    widths = {column: max(len(column), *(len(str(row.get(column, ""))) for row in result)) for column in columns}
    print("  ".join(column.upper().ljust(widths[column]) for column in columns))
    print("  ".join("-" * widths[column] for column in columns))
    for row in result:
        print("  ".join(str(row.get(column, "")).ljust(widths[column]) for column in columns))


if __name__ == "__main__":
    main()
