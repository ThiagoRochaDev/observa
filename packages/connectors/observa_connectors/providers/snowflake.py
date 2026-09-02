from __future__ import annotations

import base64
import hashlib
import time
from datetime import date, datetime, timezone
from typing import Any

from observa_connectors.base import BaseConnector, CostSignal, PullResult, ResourceSignal, TestResult
from observa_connectors.http import request_json


class SnowflakeAuthError(Exception):
    pass


def _qualified_username(account: str, user: str) -> str:
    """
    Snowflake exige `{ACCOUNT}.{USER}` em maiúsculas no `iss`/`sub` do JWT —
    ver https://docs.snowflake.com/en/user-guide/key-pair-auth. NOTA: contas
    no formato "organization-account_name" (accounts mais novas) normalizam
    diferente de account locators legados; se a autenticação falhar com uma
    conta desse formato, é o primeiro lugar a conferir contra a conta real
    (não valida sozinho sem uma conta Snowflake de verdade pra testar).
    """
    return f"{account.upper()}.{user.upper()}"


def _build_jwt(config: dict[str, Any], secrets: dict[str, Any]) -> str:
    """JWT assinado RS256 (key-pair auth) — spec pública:
    https://docs.snowflake.com/en/user-guide/key-pair-auth"""
    try:
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding
    except ImportError as exc:  # pragma: no cover
        raise SnowflakeAuthError("Conector Snowflake precisa do pacote 'cryptography'.") from exc

    account = config.get("account", "")
    user = secrets.get("user", "")
    qualified = _qualified_username(account, user)

    private_key_pem = secrets.get("private_key", "")
    passphrase = secrets.get("private_key_passphrase") or None
    private_key = serialization.load_pem_private_key(
        private_key_pem.encode("utf-8"),
        password=passphrase.encode("utf-8") if passphrase else None,
    )
    public_key_der = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    fingerprint = "SHA256:" + base64.b64encode(hashlib.sha256(public_key_der).digest()).decode("ascii")

    now = int(time.time())
    header = {"alg": "RS256", "typ": "JWT"}
    payload = {
        "iss": f"{qualified}.{fingerprint}",
        "sub": qualified,
        "iat": now,
        "exp": now + 55 * 60,  # limite da Snowflake é 1h
    }

    def _b64url(obj_or_bytes) -> str:
        raw = obj_or_bytes if isinstance(obj_or_bytes, bytes) else __import__("json").dumps(obj_or_bytes).encode("utf-8")
        return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")

    signing_input = f"{_b64url(header)}.{_b64url(payload)}".encode("ascii")
    signature = private_key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
    return signing_input.decode("ascii") + "." + base64.urlsafe_b64encode(signature).rstrip(b"=").decode("ascii")


def _headers(config: dict[str, Any], secrets: dict[str, Any]) -> dict[str, str]:
    jwt = _build_jwt(config, secrets)
    return {
        "Authorization": f"Bearer {jwt}",
        "X-Snowflake-Authorization-Token-Type": "KEYPAIR_JWT",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _run_statement(config: dict[str, Any], secrets: dict[str, Any], sql: str) -> tuple[int, Any]:
    account = config.get("account", "")
    url = f"https://{account}.snowflakecomputing.com/api/v2/statements"
    body: dict[str, Any] = {"statement": sql, "timeout": 60}
    if config.get("warehouse"):
        body["warehouse"] = config["warehouse"]
    return request_json("POST", url, headers=_headers(config, secrets), json_body=body)


class SnowflakeConnector(BaseConnector):
    id = "snowflake"
    name = "Snowflake"
    description = "Warehouse credit usage and storage cost."
    capabilities = ["cost"]
    category = "saas"
    icon = "snowflake"
    docs_url = "https://docs.snowflake.com/en/user-guide/key-pair-auth"

    def config_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "account": {"type": "string", "title": "Account identifier"},
                "warehouse": {"type": "string", "title": "Warehouse"},
            },
            "required": ["account"],
        }

    def secrets_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "user": {"type": "string", "title": "User"},
                "private_key": {"type": "string", "title": "Key-pair private key (PEM)"},
            },
            "required": ["user", "private_key"],
        }

    def test_connection(self, config: dict[str, Any], secrets: dict[str, Any]) -> TestResult:
        try:
            status, body = _run_statement(config, secrets, "SELECT CURRENT_VERSION()")
        except SnowflakeAuthError as exc:
            return TestResult(ok=False, message=str(exc))
        except Exception as exc:
            return TestResult(ok=False, message=f"Falha ao autenticar: {exc}")
        if status in (200, 202):
            return TestResult(ok=True, message="Key-pair JWT accepted.")
        return TestResult(ok=False, message=f"HTTP {status}: {str(body)[:300]}")

    def pull(self, config: dict[str, Any], secrets: dict[str, Any], *, since: date | None = None) -> PullResult:
        start = since or date.today().replace(day=1)
        costs: list[CostSignal] = []
        try:
            status, body = _run_statement(
                config, secrets,
                "SELECT TO_DATE(START_TIME) AS DAY, WAREHOUSE_NAME, SUM(CREDITS_USED) AS CREDITS "
                f"FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY "
                f"WHERE START_TIME >= '{start.isoformat()}' "
                "GROUP BY 1, 2 ORDER BY 1",
            )
            if status == 200 and isinstance(body, dict):
                for row in body.get("data", []):
                    day_str, warehouse, credits = row[0], row[1], row[2]
                    costs.append(
                        CostSignal(
                            date=date.fromisoformat(day_str[:10]), provider="snowflake",
                            amount=float(credits or 0), currency="CREDITS",
                            service=warehouse, sku="warehouse_credits",
                        )
                    )
        except SnowflakeAuthError:
            pass

        resources: list[ResourceSignal] = []
        try:
            status, body = _run_statement(config, secrets, "SHOW WAREHOUSES")
            if status == 200 and isinstance(body, dict):
                columns = [c.get("name") for c in body.get("resultSetMetaData", {}).get("rowType", [])]
                idx = {name: i for i, name in enumerate(columns) if name}
                for row in body.get("data", []):
                    resources.append(
                        ResourceSignal(
                            provider="snowflake", type="warehouse",
                            id=row[idx["name"]] if "name" in idx else "",
                            name=row[idx["name"]] if "name" in idx else None,
                            status=row[idx["state"]] if "state" in idx else None,
                            labels={"size": row[idx["size"]]} if "size" in idx else {},
                        )
                    )
        except (SnowflakeAuthError, KeyError, IndexError):
            pass

        return PullResult(costs=costs, resources=resources, message=f"{len(costs)} cost rows, {len(resources)} warehouses")
