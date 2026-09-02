from __future__ import annotations

import base64
import hashlib
import json
from datetime import date, datetime, timedelta, timezone
from email.utils import format_datetime
from typing import Any
from urllib.parse import urlsplit

from observa_connectors.base import BaseConnector, CostSignal, PullResult, ResourceSignal, TestResult
from observa_connectors.http import request_json


class OciSigningError(Exception):
    pass


def _sign(method: str, url: str, config: dict[str, Any], secrets: dict[str, Any], body: bytes | None) -> dict[str, str]:
    """
    Implementa a assinatura de requisição da OCI (RSA-SHA256 sobre uma
    signing string canônica) — spec pública e estável:
    https://docs.oracle.com/en-us/iaas/Content/API/Concepts/signingrequests.htm
    Não usa SDK da OCI (dependência pesada); só `cryptography`, que já é
    transitiva de `google-auth` (extra "gcp" deste pacote) — import tardio
    pra não forçar quem só usa outro conector a instalar `cryptography`.
    """
    try:
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding
    except ImportError as exc:  # pragma: no cover
        raise OciSigningError(
            "Conector OCI precisa do pacote 'cryptography' (pip install cryptography)."
        ) from exc

    parts = urlsplit(url)
    host = parts.netloc
    request_target = parts.path + (f"?{parts.query}" if parts.query else "")
    date_header = format_datetime(datetime.now(timezone.utc), usegmt=True)

    signing_headers = ["date", "(request-target)", "host"]
    lines = {
        "date": date_header,
        "(request-target)": f"{method.lower()} {request_target}",
        "host": host,
    }

    extra_headers: dict[str, str] = {}
    if body is not None:
        content_sha256 = base64.b64encode(hashlib.sha256(body).digest()).decode("ascii")
        extra_headers["content-length"] = str(len(body))
        extra_headers["content-type"] = "application/json"
        extra_headers["x-content-sha256"] = content_sha256
        for h in ("content-length", "content-type", "x-content-sha256"):
            signing_headers.append(h)
            lines[h] = extra_headers[h]

    signing_string = "\n".join(f"{h}: {lines[h]}" for h in signing_headers)

    private_key_pem = secrets.get("private_key", "")
    passphrase = secrets.get("private_key_passphrase") or None
    private_key = serialization.load_pem_private_key(
        private_key_pem.encode("utf-8"),
        password=passphrase.encode("utf-8") if passphrase else None,
    )
    signature = private_key.sign(signing_string.encode("utf-8"), padding.PKCS1v15(), hashes.SHA256())
    signature_b64 = base64.b64encode(signature).decode("ascii")

    key_id = f"{config.get('tenancy_ocid', '')}/{secrets.get('user_ocid', '')}/{secrets.get('fingerprint', '')}"
    authorization = (
        f'Signature version="1",keyId="{key_id}",algorithm="rsa-sha256",'
        f'headers="{" ".join(signing_headers)}",signature="{signature_b64}"'
    )

    headers = {"date": date_header, "host": host, "authorization": authorization}
    headers.update(extra_headers)
    return headers


class OciConnector(BaseConnector):
    id = "oci"
    name = "Oracle Cloud (OCI)"
    description = "Oracle Cloud Infrastructure cost and inventory."
    capabilities = ["cost", "inventory"]
    category = "cloud"
    icon = "oci"
    docs_url = "https://docs.oracle.com/en-us/iaas/Content/API/Concepts/apisigningkey.htm"

    def config_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "tenancy_ocid": {"type": "string", "title": "Tenancy OCID"},
                "region": {"type": "string", "title": "Region", "default": "us-ashburn-1"},
            },
            "required": ["tenancy_ocid"],
        }

    def secrets_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "user_ocid": {"type": "string", "title": "User OCID"},
                "fingerprint": {"type": "string", "title": "API key fingerprint"},
                "private_key": {"type": "string", "title": "API private key (PEM)"},
            },
            "required": ["user_ocid", "fingerprint", "private_key"],
        }

    def test_connection(self, config: dict[str, Any], secrets: dict[str, Any]) -> TestResult:
        region = config.get("region") or "us-ashburn-1"
        tenancy = config.get("tenancy_ocid", "")
        url = f"https://identity.{region}.oraclecloud.com/20160918/tenancies/{tenancy}"
        try:
            headers = _sign("GET", url, config, secrets, body=None)
        except OciSigningError as exc:
            return TestResult(ok=False, message=str(exc))
        except Exception as exc:
            return TestResult(ok=False, message=f"Falha ao assinar a requisição: {exc}")

        status, body = request_json("GET", url, headers=headers)
        if status == 200:
            return TestResult(ok=True, message="Signature accepted — credentials are valid.")
        return TestResult(ok=False, message=f"HTTP {status}: {str(body)[:300]}")

    def pull(self, config: dict[str, Any], secrets: dict[str, Any], *, since: date | None = None) -> PullResult:
        region = config.get("region") or "us-ashburn-1"
        tenancy = config.get("tenancy_ocid", "")
        start = since or (date.today() - timedelta(days=30))

        costs: list[CostSignal] = []
        usage_url = f"https://usageapi.{region}.oraclecloud.com/20200107/usage"
        usage_body = json.dumps({
            "tenantId": tenancy,
            "timeUsageStarted": f"{start.isoformat()}T00:00:00.000Z",
            "timeUsageEnded": f"{date.today().isoformat()}T00:00:00.000Z",
            "granularity": "DAILY",
        }).encode("utf-8")
        try:
            headers = _sign("POST", usage_url, config, secrets, body=usage_body)
            status, body = request_json("POST", usage_url, headers=headers, json_body=json.loads(usage_body))
            if status == 200 and isinstance(body, dict):
                for item in body.get("items", []):
                    day_str = (item.get("timeUsageStarted") or "")[:10]
                    if not day_str:
                        continue
                    costs.append(
                        CostSignal(
                            date=date.fromisoformat(day_str), provider="oci",
                            amount=float(item.get("computedAmount") or 0),
                            currency=item.get("currency") or "USD",
                            service=item.get("service"), resource_id=item.get("resourceId"),
                        )
                    )
        except OciSigningError:
            pass  # cryptography não instalada — segue só com o que der (inventário pode ainda funcionar).

        resources: list[ResourceSignal] = []
        search_url = f"https://query.{region}.oraclecloud.com/20180409/resourceSearch"
        search_body = json.dumps({"type": "Structured", "query": "query all resources"}).encode("utf-8")
        try:
            headers = _sign("POST", search_url, config, secrets, body=search_body)
            status, body = request_json("POST", search_url, headers=headers, json_body=json.loads(search_body))
            if status == 200 and isinstance(body, dict):
                for item in body.get("items", []):
                    resources.append(
                        ResourceSignal(
                            provider="oci", type=item.get("resourceType", "resource"),
                            id=item.get("identifier", ""), name=item.get("displayName"),
                            region=item.get("regionName") or region,
                            status=item.get("lifecycleState"),
                        )
                    )
        except OciSigningError:
            pass

        return PullResult(costs=costs, resources=resources, message=f"{len(costs)} cost rows, {len(resources)} resources")
