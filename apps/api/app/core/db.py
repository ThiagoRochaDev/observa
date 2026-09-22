from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Iterator

from app.core.config import get_settings
from app.core.crypto import decrypt_json, encrypt_json

_lock = threading.Lock()


def _connect() -> sqlite3.Connection:
    path = get_settings().db_path
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _lock:
        conn = _connect()
        try:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS settings (
                  key TEXT PRIMARY KEY,
                  value TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS connections (
                  id TEXT PRIMARY KEY,
                  name TEXT NOT NULL,
                  connector_id TEXT NOT NULL,
                  config_json TEXT NOT NULL,
                  secrets_enc TEXT NOT NULL,
                  enabled INTEGER NOT NULL DEFAULT 1,
                  last_sync_at TEXT,
                  last_sync_status TEXT,
                  last_sync_message TEXT,
                  created_at TEXT NOT NULL,
                  updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS cost_records (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  connection_id TEXT NOT NULL,
                  date TEXT NOT NULL,
                  provider TEXT NOT NULL,
                  amount REAL NOT NULL,
                  currency TEXT NOT NULL,
                  account TEXT,
                  service TEXT,
                  resource_id TEXT,
                  product TEXT,
                  squad TEXT,
                  environment TEXT,
                  sku TEXT
                );

                CREATE TABLE IF NOT EXISTS resources (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  connection_id TEXT NOT NULL,
                  provider TEXT NOT NULL,
                  type TEXT NOT NULL,
                  resource_key TEXT NOT NULL,
                  name TEXT,
                  region TEXT,
                  product TEXT,
                  squad TEXT,
                  status TEXT,
                  labels_json TEXT
                );

                CREATE TABLE IF NOT EXISTS metrics (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  connection_id TEXT NOT NULL,
                  name TEXT NOT NULL,
                  value REAL NOT NULL,
                  unit TEXT,
                  ts TEXT NOT NULL,
                  resource_id TEXT,
                  product TEXT,
                  labels_json TEXT
                );

                CREATE TABLE IF NOT EXISTS alerts (
                  id TEXT PRIMARY KEY,
                  severity TEXT NOT NULL,
                  category TEXT NOT NULL,
                  product TEXT,
                  title TEXT NOT NULL,
                  message TEXT,
                  status TEXT NOT NULL,
                  detected_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS automation_policies (
                  id TEXT PRIMARY KEY,
                  name TEXT NOT NULL,
                  resource_ids_json TEXT NOT NULL,
                  selector_json TEXT NOT NULL,
                  timezone TEXT NOT NULL,
                  weekdays_json TEXT NOT NULL,
                  start_time TEXT,
                  stop_time TEXT,
                  expires_at TEXT,
                  expiration_action TEXT NOT NULL DEFAULT 'stop',
                  enabled INTEGER NOT NULL DEFAULT 1,
                  require_approval INTEGER NOT NULL DEFAULT 1,
                  dry_run INTEGER NOT NULL DEFAULT 1,
                  created_at TEXT NOT NULL,
                  updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS action_runs (
                  id TEXT PRIMARY KEY,
                  policy_id TEXT,
                  resource_uid INTEGER NOT NULL,
                  action TEXT NOT NULL,
                  status TEXT NOT NULL,
                  scheduled_for TEXT,
                  reason TEXT,
                  result_message TEXT,
                  dry_run INTEGER NOT NULL DEFAULT 1,
                  created_at TEXT NOT NULL,
                  updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS budget_rules (
                  id TEXT PRIMARY KEY,
                  name TEXT NOT NULL,
                  scope_type TEXT NOT NULL,
                  scope_value TEXT NOT NULL,
                  amount REAL NOT NULL,
                  currency TEXT NOT NULL,
                  window_days INTEGER NOT NULL DEFAULT 30,
                  warning_threshold REAL NOT NULL DEFAULT 0.8,
                  critical_threshold REAL NOT NULL DEFAULT 1.0,
                  response_mode TEXT NOT NULL DEFAULT 'notify',
                  owner TEXT,
                  resource_ids_json TEXT NOT NULL,
                  dry_run INTEGER NOT NULL DEFAULT 1,
                  enabled INTEGER NOT NULL DEFAULT 1,
                  created_at TEXT NOT NULL,
                  updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS budget_events (
                  id TEXT PRIMARY KEY,
                  rule_id TEXT NOT NULL,
                  dedupe_key TEXT NOT NULL UNIQUE,
                  level TEXT NOT NULL,
                  status TEXT NOT NULL,
                  actual_cost REAL NOT NULL,
                  projected_cost REAL NOT NULL,
                  usage_pct REAL NOT NULL,
                  period_start TEXT NOT NULL,
                  period_end TEXT NOT NULL,
                  action_ids_json TEXT NOT NULL,
                  message TEXT NOT NULL,
                  created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS audit_events (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  event_type TEXT NOT NULL,
                  subject TEXT NOT NULL,
                  payload_json TEXT NOT NULL,
                  created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_cost_date ON cost_records(date);
                CREATE INDEX IF NOT EXISTS idx_cost_product ON cost_records(product);
                CREATE INDEX IF NOT EXISTS idx_metrics_name ON metrics(name);
                CREATE INDEX IF NOT EXISTS idx_metrics_product ON metrics(product);
                CREATE UNIQUE INDEX IF NOT EXISTS idx_resource_identity
                  ON resources(connection_id, provider, resource_key);
                CREATE INDEX IF NOT EXISTS idx_actions_status ON action_runs(status);
                CREATE INDEX IF NOT EXISTS idx_actions_scheduled ON action_runs(scheduled_for);
                CREATE INDEX IF NOT EXISTS idx_budget_events_rule ON budget_events(rule_id);
                """
            )
            action_columns = {
                row["name"] for row in conn.execute("PRAGMA table_info(action_runs)").fetchall()
            }
            if "dry_run" not in action_columns:
                conn.execute("ALTER TABLE action_runs ADD COLUMN dry_run INTEGER NOT NULL DEFAULT 1")
            # defaults
            cur = conn.execute("SELECT value FROM settings WHERE key = 'auth'")
            if cur.fetchone() is None:
                conn.execute(
                    "INSERT INTO settings(key, value) VALUES (?, ?)",
                    (
                        "auth",
                        json.dumps(
                            {
                                "mode": "local",
                                "providers": {
                                    "gitlab": {
                                        "enabled": False,
                                        "client_id": "",
                                        "client_secret": "",
                                        "issuer": "https://gitlab.com",
                                    },
                                    "google": {
                                        "enabled": False,
                                        "client_id": "",
                                        "client_secret": "",
                                        "issuer": "https://accounts.google.com",
                                    },
                                },
                            }
                        ),
                    ),
                )
            conn.commit()
        finally:
            conn.close()


@contextmanager
def db() -> Iterator[sqlite3.Connection]:
    with _lock:
        conn = _connect()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


def get_setting(key: str) -> Any:
    with db() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        if not row:
            return None
        return json.loads(row["value"])


def set_setting(key: str, value: Any) -> None:
    with db() as conn:
        conn.execute(
            "INSERT INTO settings(key, value) VALUES(?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, json.dumps(value)),
        )


def list_connections() -> list[dict]:
    with db() as conn:
        rows = conn.execute(
            "SELECT id, name, connector_id, config_json, enabled, "
            "last_sync_at, last_sync_status, last_sync_message, created_at, updated_at "
            "FROM connections ORDER BY created_at DESC"
        ).fetchall()
    return [_conn_public(r) for r in rows]


def get_connection(conn_id: str) -> dict | None:
    with db() as conn:
        row = conn.execute(
            "SELECT id, name, connector_id, config_json, secrets_enc, enabled, "
            "last_sync_at, last_sync_status, last_sync_message, created_at, updated_at "
            "FROM connections WHERE id = ?",
            (conn_id,),
        ).fetchone()
    if not row:
        return None
    out = _conn_public(row)
    out["_secrets"] = decrypt_json(row["secrets_enc"])
    return out


def create_connection(
    *,
    conn_id: str,
    name: str,
    connector_id: str,
    config: dict,
    secrets: dict,
) -> dict:
    now = datetime.utcnow().isoformat() + "Z"
    with db() as conn:
        conn.execute(
            "INSERT INTO connections("
            "id, name, connector_id, config_json, secrets_enc, enabled, "
            "created_at, updated_at"
            ") VALUES (?, ?, ?, ?, ?, 1, ?, ?)",
            (
                conn_id,
                name,
                connector_id,
                json.dumps(config),
                encrypt_json(secrets or {}),
                now,
                now,
            ),
        )
    return get_connection(conn_id)  # type: ignore


def update_connection(
    conn_id: str,
    *,
    name: str | None = None,
    config: dict | None = None,
    secrets: dict | None = None,
    enabled: bool | None = None,
) -> dict | None:
    existing = get_connection(conn_id)
    if not existing:
        return None
    now = datetime.utcnow().isoformat() + "Z"
    with db() as conn:
        if name is not None:
            conn.execute(
                "UPDATE connections SET name = ?, updated_at = ? WHERE id = ?",
                (name, now, conn_id),
            )
        if config is not None:
            conn.execute(
                "UPDATE connections SET config_json = ?, updated_at = ? WHERE id = ?",
                (json.dumps(config), now, conn_id),
            )
        if secrets is not None:
            conn.execute(
                "UPDATE connections SET secrets_enc = ?, updated_at = ? WHERE id = ?",
                (encrypt_json(secrets), now, conn_id),
            )
        if enabled is not None:
            conn.execute(
                "UPDATE connections SET enabled = ?, updated_at = ? WHERE id = ?",
                (1 if enabled else 0, now, conn_id),
            )
    return get_connection(conn_id)


def delete_connection(conn_id: str) -> bool:
    with db() as conn:
        cur = conn.execute("DELETE FROM connections WHERE id = ?", (conn_id,))
        conn.execute("DELETE FROM cost_records WHERE connection_id = ?", (conn_id,))
        conn.execute("DELETE FROM resources WHERE connection_id = ?", (conn_id,))
        return cur.rowcount > 0


def mark_sync(conn_id: str, status: str, message: str) -> None:
    now = datetime.utcnow().isoformat() + "Z"
    with db() as conn:
        conn.execute(
            "UPDATE connections SET last_sync_at = ?, last_sync_status = ?, "
            "last_sync_message = ?, updated_at = ? WHERE id = ?",
            (now, status, message, now, conn_id),
        )


def replace_costs(connection_id: str, rows: list[dict]) -> None:
    with db() as conn:
        conn.execute("DELETE FROM cost_records WHERE connection_id = ?", (connection_id,))
        conn.executemany(
            "INSERT INTO cost_records("
            "connection_id, date, provider, amount, currency, account, service, "
            "resource_id, product, squad, environment, sku"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    connection_id,
                    r["date"],
                    r["provider"],
                    r["amount"],
                    r.get("currency") or "BRL",
                    r.get("account"),
                    r.get("service"),
                    r.get("resource_id"),
                    r.get("product"),
                    r.get("squad"),
                    r.get("environment"),
                    r.get("sku"),
                )
                for r in rows
            ],
        )


def replace_resources(connection_id: str, rows: list[dict]) -> None:
    with db() as conn:
        conn.executemany(
            "INSERT INTO resources("
            "connection_id, provider, type, resource_key, name, region, product, "
            "squad, status, labels_json"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(connection_id, provider, resource_key) DO UPDATE SET "
            "type = excluded.type, name = excluded.name, region = excluded.region, "
            "product = COALESCE(excluded.product, resources.product), "
            "squad = COALESCE(excluded.squad, resources.squad), status = excluded.status, "
            "labels_json = CASE WHEN excluded.labels_json = '{}' THEN resources.labels_json "
            "ELSE excluded.labels_json END",
            [
                (
                    connection_id,
                    r["provider"],
                    r["type"],
                    r["id"],
                    r.get("name"),
                    r.get("region"),
                    r.get("product"),
                    r.get("squad"),
                    r.get("status"),
                    json.dumps(r.get("labels") or {}),
                )
                for r in rows
            ],
        )
        identities = [(r["provider"], r["id"]) for r in rows]
        if identities:
            placeholders = ",".join("(?, ?)" for _ in identities)
            flat = [value for identity in identities for value in identity]
            conn.execute(
                f"DELETE FROM resources WHERE connection_id = ? "
                f"AND (provider, resource_key) NOT IN ({placeholders})",
                [connection_id, *flat],
            )
        else:
            conn.execute("DELETE FROM resources WHERE connection_id = ?", (connection_id,))


def replace_metrics(connection_id: str, rows: list[dict]) -> None:
    with db() as conn:
        conn.execute("DELETE FROM metrics WHERE connection_id = ?", (connection_id,))
        conn.executemany(
            "INSERT INTO metrics("
            "connection_id, name, value, unit, ts, resource_id, product, labels_json"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    connection_id,
                    r["name"],
                    r["value"],
                    r.get("unit") or "",
                    r["ts"],
                    r.get("resource_id"),
                    r.get("product"),
                    json.dumps(r.get("labels") or {}),
                )
                for r in rows
            ],
        )


def replace_alerts(rows: list[dict]) -> None:
    with db() as conn:
        conn.execute("DELETE FROM alerts")
        conn.executemany(
            "INSERT INTO alerts(id, severity, category, product, title, message, status, detected_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    r["id"],
                    r["severity"],
                    r["category"],
                    r.get("product"),
                    r["title"],
                    r.get("message"),
                    r.get("status") or "open",
                    r.get("detected_at") or datetime.utcnow().isoformat() + "Z",
                )
                for r in rows
            ],
        )


def cost_summary(days: int = 30) -> dict:
    with db() as conn:
        total = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) AS t FROM cost_records "
            "WHERE date >= date('now', ?)",
            (f"-{days} days",),
        ).fetchone()["t"]
        prev = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) AS t FROM cost_records "
            "WHERE date >= date('now', ?) AND date < date('now', ?)",
            (f"-{days * 2} days", f"-{days} days"),
        ).fetchone()["t"]
        by_provider = {
            r["provider"]: r["s"]
            for r in conn.execute(
                "SELECT provider, ROUND(SUM(amount), 2) AS s FROM cost_records "
                "WHERE date >= date('now', ?) GROUP BY provider ORDER BY s DESC",
                (f"-{days} days",),
            ).fetchall()
        }
        by_product = {
            r["product"] or "unmapped": r["s"]
            for r in conn.execute(
                "SELECT product, ROUND(SUM(amount), 2) AS s FROM cost_records "
                "WHERE date >= date('now', ?) GROUP BY product ORDER BY s DESC",
                (f"-{days} days",),
            ).fetchall()
        }
        by_squad = {
            r["squad"] or "unmapped": r["s"]
            for r in conn.execute(
                "SELECT squad, ROUND(SUM(amount), 2) AS s FROM cost_records "
                "WHERE date >= date('now', ?) GROUP BY squad ORDER BY s DESC",
                (f"-{days} days",),
            ).fetchall()
        }
        records = conn.execute("SELECT COUNT(*) AS c FROM cost_records").fetchone()["c"]
        open_alerts = conn.execute(
            "SELECT COUNT(*) AS c FROM alerts WHERE status IN ('open', 'pending')"
        ).fetchone()["c"]
    total_f = float(total)
    prev_f = float(prev)
    change = ((total_f - prev_f) / prev_f * 100) if prev_f else 0.0
    return {
        "days": days,
        "total": round(total_f, 2),
        "previous_total": round(prev_f, 2),
        "change_pct": round(change, 1),
        "by_provider": by_provider,
        "by_product": by_product,
        "by_squad": by_squad,
        "records": records,
        "open_alerts": open_alerts,
    }


def cost_trend(days: int = 30) -> list[dict]:
    with db() as conn:
        rows = conn.execute(
            "SELECT date, provider, ROUND(SUM(amount), 2) AS s FROM cost_records "
            "WHERE date >= date('now', ?) GROUP BY date, provider ORDER BY date",
            (f"-{days} days",),
        ).fetchall()
    by_day: dict[str, dict] = {}
    for r in rows:
        d = r["date"]
        slot = by_day.setdefault(d, {"date": d, "total": 0.0})
        slot[r["provider"]] = r["s"]
        slot["total"] = round(slot["total"] + r["s"], 2)
    return list(by_day.values())


def list_products() -> list[dict]:
    catalog = {p["slug"]: p for p in (get_setting("product_catalog") or [])}
    with db() as conn:
        rows = conn.execute(
            "SELECT product AS slug, "
            "ROUND(SUM(amount), 2) AS total_brl, "
            "COUNT(DISTINCT service) AS service_count "
            "FROM cost_records WHERE product IS NOT NULL AND product != '' "
            "GROUP BY product ORDER BY total_brl DESC"
        ).fetchall()
        resources = conn.execute(
            "SELECT product, COUNT(*) AS c FROM resources "
            "WHERE product IS NOT NULL GROUP BY product"
        ).fetchall()
    res_map = {r["product"]: r["c"] for r in resources}
    out = []
    for r in rows:
        meta = catalog.get(r["slug"], {})
        out.append(
            {
                "slug": r["slug"],
                "name": meta.get("name") or r["slug"],
                "squad": meta.get("squad"),
                "tribe": meta.get("tribe"),
                "aliases": meta.get("aliases") or [],
                "services": meta.get("services") or [],
                "total_brl": r["total_brl"],
                "service_count": r["service_count"],
                "resource_count": res_map.get(r["slug"], 0),
            }
        )
    return out


def get_product(slug: str) -> dict | None:
    products = {p["slug"]: p for p in list_products()}
    base = products.get(slug)
    if not base:
        return None
    with db() as conn:
        services = conn.execute(
            "SELECT service, ROUND(SUM(amount), 2) AS total_brl FROM cost_records "
            "WHERE product = ? AND service IS NOT NULL GROUP BY service ORDER BY total_brl DESC",
            (slug,),
        ).fetchall()
        by_provider = {
            r["provider"]: r["s"]
            for r in conn.execute(
                "SELECT provider, ROUND(SUM(amount), 2) AS s FROM cost_records "
                "WHERE product = ? GROUP BY provider",
                (slug,),
            ).fetchall()
        }
    return {
        **base,
        "by_provider": by_provider,
        "service_costs": [{"service": s["service"], "total_brl": s["total_brl"]} for s in services],
        "resources": list_resources(slug),
        "metrics_latest": latest_metrics(product=slug),
    }


def list_resources(product: str | None = None) -> list[dict]:
    with db() as conn:
        if product:
            rows = conn.execute(
                "SELECT * FROM resources WHERE product = ? ORDER BY product, type",
                (product,),
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM resources ORDER BY product, type").fetchall()
    return [
        {
            "uid": r["id"],
            "connection_id": r["connection_id"],
            "provider": r["provider"],
            "type": r["type"],
            "id": r["resource_key"],
            "name": r["name"],
            "region": r["region"],
            "product": r["product"],
            "squad": r["squad"],
            "status": r["status"],
            "labels": json.loads(r["labels_json"] or "{}"),
        }
        for r in rows
    ]


def get_resource(resource_uid: int) -> dict | None:
    with db() as conn:
        row = conn.execute("SELECT * FROM resources WHERE id = ?", (resource_uid,)).fetchone()
    if not row:
        return None
    return {
        "uid": row["id"],
        "connection_id": row["connection_id"],
        "provider": row["provider"],
        "type": row["type"],
        "id": row["resource_key"],
        "name": row["name"],
        "region": row["region"],
        "product": row["product"],
        "squad": row["squad"],
        "status": row["status"],
        "labels": json.loads(row["labels_json"] or "{}"),
    }


def update_resource_tags(resource_uid: int, tags: dict[str, str]) -> dict | None:
    resource = get_resource(resource_uid)
    if not resource:
        return None
    labels = {**resource["labels"], **tags}
    product = tags.get("product", resource.get("product"))
    squad = tags.get("squad", resource.get("squad"))
    with db() as conn:
        conn.execute(
            "UPDATE resources SET labels_json = ?, product = ?, squad = ? WHERE id = ?",
            (json.dumps(labels), product, squad, resource_uid),
        )
    return get_resource(resource_uid)


def update_resource_status(resource_uid: int, status: str) -> dict | None:
    with db() as conn:
        cur = conn.execute("UPDATE resources SET status = ? WHERE id = ?", (status, resource_uid))
    return get_resource(resource_uid) if cur.rowcount else None


def create_policy(policy: dict) -> dict:
    now = datetime.utcnow().isoformat() + "Z"
    with db() as conn:
        conn.execute(
            "INSERT INTO automation_policies("
            "id, name, resource_ids_json, selector_json, timezone, weekdays_json, "
            "start_time, stop_time, expires_at, expiration_action, enabled, "
            "require_approval, dry_run, created_at, updated_at"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                policy["id"],
                policy["name"],
                json.dumps(policy.get("resource_ids") or []),
                json.dumps(policy.get("selector") or {}),
                policy.get("timezone") or "UTC",
                json.dumps(policy.get("weekdays") or [0, 1, 2, 3, 4]),
                policy.get("start_time"),
                policy.get("stop_time"),
                policy.get("expires_at"),
                policy.get("expiration_action") or "stop",
                1 if policy.get("enabled", True) else 0,
                1 if policy.get("require_approval", True) else 0,
                1 if policy.get("dry_run", True) else 0,
                now,
                now,
            ),
        )
    return get_policy(policy["id"])  # type: ignore[return-value]


def list_policies() -> list[dict]:
    with db() as conn:
        rows = conn.execute("SELECT * FROM automation_policies ORDER BY created_at DESC").fetchall()
    return [_policy_dict(row) for row in rows]


def get_policy(policy_id: str) -> dict | None:
    with db() as conn:
        row = conn.execute("SELECT * FROM automation_policies WHERE id = ?", (policy_id,)).fetchone()
    return _policy_dict(row) if row else None


def update_policy(policy_id: str, changes: dict) -> dict | None:
    current = get_policy(policy_id)
    if not current:
        return None
    merged = {**current, **{key: value for key, value in changes.items() if value is not None}}
    now = datetime.utcnow().isoformat() + "Z"
    with db() as conn:
        conn.execute(
            "UPDATE automation_policies SET name = ?, resource_ids_json = ?, selector_json = ?, "
            "timezone = ?, weekdays_json = ?, start_time = ?, stop_time = ?, expires_at = ?, "
            "expiration_action = ?, enabled = ?, require_approval = ?, dry_run = ?, updated_at = ? "
            "WHERE id = ?",
            (
                merged["name"], json.dumps(merged["resource_ids"]), json.dumps(merged["selector"]),
                merged["timezone"], json.dumps(merged["weekdays"]), merged.get("start_time"),
                merged.get("stop_time"), merged.get("expires_at"), merged["expiration_action"],
                1 if merged["enabled"] else 0, 1 if merged["require_approval"] else 0,
                1 if merged["dry_run"] else 0, now, policy_id,
            ),
        )
    return get_policy(policy_id)


def delete_policy(policy_id: str) -> bool:
    with db() as conn:
        cur = conn.execute("DELETE FROM automation_policies WHERE id = ?", (policy_id,))
    return cur.rowcount > 0


def create_action(action: dict) -> dict:
    now = datetime.utcnow().isoformat() + "Z"
    with db() as conn:
        conn.execute(
            "INSERT INTO action_runs(id, policy_id, resource_uid, action, status, scheduled_for, "
            "reason, result_message, dry_run, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (action["id"], action.get("policy_id"), action["resource_uid"], action["action"],
             action["status"], action.get("scheduled_for"), action.get("reason"),
             action.get("result_message"), 1 if action.get("dry_run", True) else 0, now, now),
        )
    return get_action(action["id"])  # type: ignore[return-value]


def list_actions(status: str | None = None) -> list[dict]:
    with db() as conn:
        if status:
            rows = conn.execute(
                "SELECT * FROM action_runs WHERE status = ? ORDER BY created_at DESC", (status,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM action_runs ORDER BY created_at DESC").fetchall()
    return [dict(row) for row in rows]


def get_action(action_id: str) -> dict | None:
    with db() as conn:
        row = conn.execute("SELECT * FROM action_runs WHERE id = ?", (action_id,)).fetchone()
    return dict(row) if row else None


def update_action(action_id: str, *, status: str, result_message: str | None = None) -> dict | None:
    now = datetime.utcnow().isoformat() + "Z"
    with db() as conn:
        cur = conn.execute(
            "UPDATE action_runs SET status = ?, result_message = ?, updated_at = ? WHERE id = ?",
            (status, result_message, now, action_id),
        )
    return get_action(action_id) if cur.rowcount else None


def add_audit_event(event_type: str, subject: str, payload: dict) -> None:
    with db() as conn:
        conn.execute(
            "INSERT INTO audit_events(event_type, subject, payload_json, created_at) VALUES (?, ?, ?, ?)",
            (event_type, subject, json.dumps(payload), datetime.utcnow().isoformat() + "Z"),
        )


def create_budget_rule(rule: dict) -> dict:
    now = datetime.utcnow().isoformat() + "Z"
    with db() as conn:
        conn.execute(
            "INSERT INTO budget_rules(id, name, scope_type, scope_value, amount, currency, "
            "window_days, warning_threshold, critical_threshold, response_mode, owner, "
            "resource_ids_json, dry_run, enabled, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                rule["id"], rule["name"], rule["scope_type"], rule["scope_value"],
                rule["amount"], rule.get("currency") or "BRL", rule.get("window_days") or 30,
                rule.get("warning_threshold", 0.8), rule.get("critical_threshold", 1.0),
                rule.get("response_mode") or "notify", rule.get("owner"),
                json.dumps(rule.get("resource_ids") or []),
                1 if rule.get("dry_run", True) else 0,
                1 if rule.get("enabled", True) else 0, now, now,
            ),
        )
    return get_budget_rule(rule["id"])  # type: ignore[return-value]


def list_budget_rules() -> list[dict]:
    with db() as conn:
        rows = conn.execute("SELECT * FROM budget_rules ORDER BY created_at DESC").fetchall()
    return [_budget_rule_dict(row) for row in rows]


def get_budget_rule(rule_id: str) -> dict | None:
    with db() as conn:
        row = conn.execute("SELECT * FROM budget_rules WHERE id = ?", (rule_id,)).fetchone()
    return _budget_rule_dict(row) if row else None


def update_budget_rule(rule_id: str, changes: dict) -> dict | None:
    current = get_budget_rule(rule_id)
    if not current:
        return None
    merged = {**current, **{key: value for key, value in changes.items() if value is not None}}
    now = datetime.utcnow().isoformat() + "Z"
    with db() as conn:
        conn.execute(
            "UPDATE budget_rules SET name = ?, scope_type = ?, scope_value = ?, amount = ?, "
            "currency = ?, window_days = ?, warning_threshold = ?, critical_threshold = ?, "
            "response_mode = ?, owner = ?, resource_ids_json = ?, dry_run = ?, enabled = ?, "
            "updated_at = ? WHERE id = ?",
            (
                merged["name"], merged["scope_type"], merged["scope_value"], merged["amount"],
                merged["currency"], merged["window_days"], merged["warning_threshold"],
                merged["critical_threshold"], merged["response_mode"], merged.get("owner"),
                json.dumps(merged["resource_ids"]), 1 if merged["dry_run"] else 0,
                1 if merged["enabled"] else 0, now, rule_id,
            ),
        )
    return get_budget_rule(rule_id)


def delete_budget_rule(rule_id: str) -> bool:
    with db() as conn:
        cur = conn.execute("DELETE FROM budget_rules WHERE id = ?", (rule_id,))
    return cur.rowcount > 0


def budget_spend(scope_type: str, scope_value: str, days: int) -> dict:
    columns = {
        "project": "account",
        "account": "account",
        "product": "product",
        "provider": "provider",
        "resource": "resource_id",
    }
    column = columns.get(scope_type)
    if not column:
        raise ValueError(f"Unsupported budget scope: {scope_type}")
    with db() as conn:
        rows = conn.execute(
            f"SELECT date, ROUND(SUM(amount), 4) AS amount FROM cost_records "
            f"WHERE {column} = ? AND date >= date('now', ?) GROUP BY date ORDER BY date",
            (scope_value, f"-{days - 1} days"),
        ).fetchall()
    daily = [{"date": row["date"], "amount": float(row["amount"])} for row in rows]
    actual = sum(item["amount"] for item in daily)
    observed_days = len(daily)
    projected = actual / observed_days * days if observed_days else 0.0
    return {
        "actual": round(actual, 2),
        "projected": round(projected, 2),
        "observed_days": observed_days,
        "daily": daily,
    }


def create_budget_event(event: dict) -> dict:
    now = datetime.utcnow().isoformat() + "Z"
    with db() as conn:
        conn.execute(
            "INSERT INTO budget_events(id, rule_id, dedupe_key, level, status, actual_cost, "
            "projected_cost, usage_pct, period_start, period_end, action_ids_json, message, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                event["id"], event["rule_id"], event["dedupe_key"], event["level"],
                event["status"], event["actual_cost"], event["projected_cost"], event["usage_pct"],
                event["period_start"], event["period_end"], json.dumps(event.get("action_ids") or []),
                event["message"], now,
            ),
        )
    return get_budget_event(event["id"])  # type: ignore[return-value]


def get_budget_event(event_id: str) -> dict | None:
    with db() as conn:
        row = conn.execute("SELECT * FROM budget_events WHERE id = ?", (event_id,)).fetchone()
    return _budget_event_dict(row) if row else None


def get_budget_event_by_dedupe(dedupe_key: str) -> dict | None:
    with db() as conn:
        row = conn.execute("SELECT * FROM budget_events WHERE dedupe_key = ?", (dedupe_key,)).fetchone()
    return _budget_event_dict(row) if row else None


def list_budget_events(rule_id: str | None = None) -> list[dict]:
    with db() as conn:
        if rule_id:
            rows = conn.execute(
                "SELECT * FROM budget_events WHERE rule_id = ? ORDER BY created_at DESC", (rule_id,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM budget_events ORDER BY created_at DESC").fetchall()
    return [_budget_event_dict(row) for row in rows]


def upsert_alert(row: dict) -> None:
    with db() as conn:
        conn.execute(
            "INSERT INTO alerts(id, severity, category, product, title, message, status, detected_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(id) DO UPDATE SET "
            "severity = excluded.severity, title = excluded.title, message = excluded.message, "
            "status = excluded.status, detected_at = excluded.detected_at",
            (
                row["id"], row["severity"], row.get("category") or "budget", row.get("product"),
                row["title"], row.get("message"), row.get("status") or "open",
                row.get("detected_at") or datetime.utcnow().isoformat() + "Z",
            ),
        )


def _budget_rule_dict(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"], "name": row["name"], "scope_type": row["scope_type"],
        "scope_value": row["scope_value"], "amount": row["amount"], "currency": row["currency"],
        "window_days": row["window_days"], "warning_threshold": row["warning_threshold"],
        "critical_threshold": row["critical_threshold"], "response_mode": row["response_mode"],
        "owner": row["owner"], "resource_ids": json.loads(row["resource_ids_json"] or "[]"),
        "dry_run": bool(row["dry_run"]), "enabled": bool(row["enabled"]),
        "created_at": row["created_at"], "updated_at": row["updated_at"],
    }


def _budget_event_dict(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"], "rule_id": row["rule_id"], "level": row["level"],
        "status": row["status"], "actual_cost": row["actual_cost"],
        "projected_cost": row["projected_cost"], "usage_pct": row["usage_pct"],
        "period_start": row["period_start"], "period_end": row["period_end"],
        "action_ids": json.loads(row["action_ids_json"] or "[]"),
        "message": row["message"], "created_at": row["created_at"],
    }


def _policy_dict(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"], "name": row["name"],
        "resource_ids": json.loads(row["resource_ids_json"] or "[]"),
        "selector": json.loads(row["selector_json"] or "{}"),
        "timezone": row["timezone"], "weekdays": json.loads(row["weekdays_json"] or "[]"),
        "start_time": row["start_time"], "stop_time": row["stop_time"],
        "expires_at": row["expires_at"], "expiration_action": row["expiration_action"],
        "enabled": bool(row["enabled"]), "require_approval": bool(row["require_approval"]),
        "dry_run": bool(row["dry_run"]), "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def latest_metrics(product: str | None = None) -> list[dict]:
    """Latest sample per (name, product, resource_id)."""
    with db() as conn:
        if product:
            rows = conn.execute(
                "SELECT m.* FROM metrics m "
                "INNER JOIN ("
                "  SELECT name, product, resource_id, MAX(ts) AS max_ts FROM metrics "
                "  WHERE product = ? GROUP BY name, product, resource_id"
                ") t ON m.name = t.name AND m.product = t.product "
                " AND IFNULL(m.resource_id,'') = IFNULL(t.resource_id,'') AND m.ts = t.max_ts "
                "ORDER BY m.name",
                (product,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT m.* FROM metrics m "
                "INNER JOIN ("
                "  SELECT name, product, resource_id, MAX(ts) AS max_ts FROM metrics "
                "  GROUP BY name, product, resource_id"
                ") t ON m.name = t.name AND IFNULL(m.product,'') = IFNULL(t.product,'') "
                " AND IFNULL(m.resource_id,'') = IFNULL(t.resource_id,'') AND m.ts = t.max_ts "
                "ORDER BY m.product, m.name"
            ).fetchall()
    return [
        {
            "name": r["name"],
            "value": r["value"],
            "unit": r["unit"],
            "ts": r["ts"],
            "resource_id": r["resource_id"],
            "product": r["product"],
            "labels": json.loads(r["labels_json"] or "{}"),
        }
        for r in rows
    ]


def metric_series(name: str, product: str | None = None, hours: int = 24) -> list[dict]:
    with db() as conn:
        if product:
            rows = conn.execute(
                "SELECT ts, value, unit, resource_id FROM metrics "
                "WHERE name = ? AND product = ? AND ts >= datetime('now', ?) "
                "ORDER BY ts",
                (name, product, f"-{hours} hours"),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT ts, ROUND(AVG(value), 2) AS value, unit FROM metrics "
                "WHERE name = ? AND ts >= datetime('now', ?) "
                "GROUP BY ts, unit ORDER BY ts",
                (name, f"-{hours} hours"),
            ).fetchall()
    return [
        {
            "ts": r["ts"],
            "value": r["value"],
            "unit": r["unit"] if "unit" in r.keys() else "",
            "resource_id": r["resource_id"] if "resource_id" in r.keys() else None,
        }
        for r in rows
    ]


def list_alerts(status: str | None = None) -> list[dict]:
    with db() as conn:
        if status:
            rows = conn.execute(
                "SELECT * FROM alerts WHERE status = ? ORDER BY detected_at DESC", (status,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM alerts ORDER BY detected_at DESC").fetchall()
    return [dict(r) for r in rows]


def observability_overview() -> dict:
    latest = latest_metrics()
    # aggregate by product for key KPIs
    by_product: dict[str, dict] = {}
    for m in latest:
        p = m.get("product") or "unknown"
        slot = by_product.setdefault(
            p,
            {
                "product": p,
                "latency_p95_ms": None,
                "error_rate_pct": None,
                "rpm": None,
                "cpu_pct": None,
                "db_connections": None,
                "db_cpu_pct": None,
            },
        )
        if m["name"] == "apm.latency_p95_ms":
            slot["latency_p95_ms"] = m["value"]
        elif m["name"] == "apm.error_rate_pct":
            slot["error_rate_pct"] = m["value"]
        elif m["name"] == "apm.requests_per_min":
            slot["rpm"] = m["value"]
        elif m["name"] == "infra.cpu_pct":
            slot["cpu_pct"] = m["value"]
        elif m["name"] == "db.connections":
            slot["db_connections"] = m["value"]
        elif m["name"] == "db.cpu_pct":
            slot["db_cpu_pct"] = m["value"]
    return {
        "products": list(by_product.values()),
        "metric_count": len(latest),
        "alert_count": len(list_alerts()),
    }


def _conn_public(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "connector_id": row["connector_id"],
        "config": json.loads(row["config_json"]),
        "enabled": bool(row["enabled"]),
        "last_sync_at": row["last_sync_at"],
        "last_sync_status": row["last_sync_status"],
        "last_sync_message": row["last_sync_message"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "has_secrets": True,
    }
