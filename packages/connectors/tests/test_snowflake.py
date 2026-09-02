"""
Testa o JWT key-pair da Snowflake sem conta real: gera um par de chaves RSA
de teste e verifica a assinatura RS256 do JWT produzido contra a chave
pública correspondente + confere que o fingerprint (`SHA256:...` no `iss`)
bate com o hash calculado à mão a partir da mesma chave pública — prova que
`_build_jwt` implementa a spec de verdade, não só "parece" um JWT.
"""
import base64
import hashlib
import json

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from observa_connectors.providers.snowflake import (
    SnowflakeConnector,
    _build_jwt,
    _qualified_username,
)

CONFIG = {"account": "myorg-myaccount", "warehouse": "COMPUTE_WH"}


@pytest.fixture(scope="module")
def keypair():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")
    return private_key, pem


def _secrets(pem: str) -> dict:
    return {"user": "svc_observa", "private_key": pem}


def _b64url_decode(segment: str) -> bytes:
    padding_needed = "=" * (-len(segment) % 4)
    return base64.urlsafe_b64decode(segment + padding_needed)


def test_qualified_username_uppercases_account_and_user():
    assert _qualified_username("myorg-myaccount", "svc_observa") == "MYORG-MYACCOUNT.SVC_OBSERVA"


def test_build_jwt_signature_verifies_against_public_key(keypair):
    private_key, pem = keypair
    token = _build_jwt(CONFIG, _secrets(pem))

    header_b64, payload_b64, signature_b64 = token.split(".")
    header = json.loads(_b64url_decode(header_b64))
    payload = json.loads(_b64url_decode(payload_b64))
    assert header == {"alg": "RS256", "typ": "JWT"}
    assert payload["sub"] == "MYORG-MYACCOUNT.SVC_OBSERVA"
    assert payload["exp"] > payload["iat"]

    # O fingerprint no `iss` precisa bater com SHA256(DER da chave pública) —
    # é isso que a Snowflake recalcula do lado dela pra achar a public key
    # cadastrada no usuário (`ALTER USER ... SET RSA_PUBLIC_KEY`).
    public_der = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.DER, format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    expected_fingerprint = "SHA256:" + base64.b64encode(hashlib.sha256(public_der).digest()).decode("ascii")
    assert payload["iss"] == f"MYORG-MYACCOUNT.SVC_OBSERVA.{expected_fingerprint}"

    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    private_key.public_key().verify(
        _b64url_decode(signature_b64), signing_input, padding.PKCS1v15(), hashes.SHA256(),
    )


def test_connection_ok(monkeypatch, keypair):
    _, pem = keypair
    monkeypatch.setattr(
        "observa_connectors.providers.snowflake.request_json",
        lambda *a, **k: (200, {"data": [["8.20.1"]]}),
    )
    result = SnowflakeConnector().test_connection(CONFIG, _secrets(pem))
    assert result.ok


def test_connection_rejected(monkeypatch, keypair):
    _, pem = keypair
    monkeypatch.setattr(
        "observa_connectors.providers.snowflake.request_json",
        lambda *a, **k: (401, {"message": "JWT token is invalid"}),
    )
    result = SnowflakeConnector().test_connection(CONFIG, _secrets(pem))
    assert not result.ok


def test_pull_parses_warehouse_credits_and_inventory(monkeypatch, keypair):
    _, pem = keypair
    calls = []

    def fake_request(method, url, headers=None, json_body=None, **kwargs):
        calls.append(json_body["statement"])
        if "WAREHOUSE_METERING_HISTORY" in json_body["statement"]:
            return 200, {"data": [["2026-08-01", "COMPUTE_WH", 3.5]]}
        if "SHOW WAREHOUSES" in json_body["statement"]:
            return 200, {
                "resultSetMetaData": {"rowType": [{"name": "name"}, {"name": "state"}, {"name": "size"}]},
                "data": [["COMPUTE_WH", "STARTED", "X-Small"]],
            }
        return 404, {}

    monkeypatch.setattr("observa_connectors.providers.snowflake.request_json", fake_request)
    result = SnowflakeConnector().pull(CONFIG, _secrets(pem))

    assert len(result.costs) == 1
    assert result.costs[0].amount == 3.5
    assert result.costs[0].service == "COMPUTE_WH"
    assert len(result.resources) == 1
    assert result.resources[0].status == "STARTED"
    assert result.resources[0].labels["size"] == "X-Small"
    assert len(calls) == 2
