"""
Testa a assinatura de requisição da OCI sem conta real: gera um par de
chaves RSA de teste (mesmo formato que a OCI exige — RSA 2048, PEM) e
verifica a assinatura produzida contra a CHAVE PÚBLICA correspondente, ou
seja, confirma que `_sign()` implementa a spec de verdade (não só que "algo"
foi assinado) — mesma técnica usada pro NVR/câmera ONVIF simulado localmente
no detect-easy: validar o protocolo contra um verificador de referência.
"""
import base64
import re

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from observa_connectors.providers.oci import OciConnector, _sign

CONFIG = {"tenancy_ocid": "ocid1.tenancy.oc1..aaaa", "region": "us-ashburn-1"}


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
    return {"user_ocid": "ocid1.user.oc1..bbbb", "fingerprint": "aa:bb:cc:dd", "private_key": pem}


def test_sign_get_produces_valid_signature_verifiable_by_public_key(keypair):
    private_key, pem = keypair
    url = "https://identity.us-ashburn-1.oraclecloud.com/20160918/tenancies/ocid1.tenancy.oc1..aaaa"
    headers = _sign("GET", url, CONFIG, _secrets(pem), body=None)

    auth = headers["authorization"]
    assert 'keyId="ocid1.tenancy.oc1..aaaa/ocid1.user.oc1..bbbb/aa:bb:cc:dd"' in auth
    assert 'algorithm="rsa-sha256"' in auth
    signed_headers = re.search(r'headers="([^"]+)"', auth).group(1).split()
    assert signed_headers == ["date", "(request-target)", "host"]

    signing_string = "\n".join(
        f"{h}: {headers[h] if h != '(request-target)' else 'get /20160918/tenancies/ocid1.tenancy.oc1..aaaa'}"
        for h in signed_headers
    )
    signature_b64 = re.search(r'signature="([^"]+)"', auth).group(1)

    # Se a assinatura bater contra a chave pública correspondente, a
    # implementação está correta — não é só "parece" com o formato da OCI.
    private_key.public_key().verify(
        base64.b64decode(signature_b64), signing_string.encode("utf-8"),
        padding.PKCS1v15(), hashes.SHA256(),
    )


def test_sign_post_includes_body_hash_headers(keypair):
    _, pem = keypair
    body = b'{"tenantId": "x"}'
    headers = _sign("POST", "https://usageapi.us-ashburn-1.oraclecloud.com/20200107/usage", CONFIG, _secrets(pem), body=body)

    assert headers["content-length"] == str(len(body))
    assert headers["content-type"] == "application/json"
    assert "x-content-sha256" in headers
    signed_headers = re.search(r'headers="([^"]+)"', headers["authorization"]).group(1).split()
    assert signed_headers == ["date", "(request-target)", "host", "content-length", "content-type", "x-content-sha256"]


def test_connection_ok_when_api_accepts_signature(monkeypatch, keypair):
    _, pem = keypair
    monkeypatch.setattr("observa_connectors.providers.oci.request_json", lambda *a, **k: (200, {"id": "..."}))
    result = OciConnector().test_connection(CONFIG, _secrets(pem))
    assert result.ok


def test_connection_fails_on_invalid_signature(monkeypatch, keypair):
    _, pem = keypair
    monkeypatch.setattr(
        "observa_connectors.providers.oci.request_json",
        lambda *a, **k: (401, {"code": "NotAuthenticated"}),
    )
    result = OciConnector().test_connection(CONFIG, _secrets(pem))
    assert not result.ok


def test_pull_parses_usage_and_resource_search(monkeypatch, keypair):
    _, pem = keypair

    def fake_request(method, url, **kwargs):
        if "usageapi" in url:
            return 200, {"items": [
                {"timeUsageStarted": "2026-08-01T00:00:00Z", "computedAmount": 42.5,
                 "currency": "USD", "service": "Compute", "resourceId": "ocid1.instance.1"},
            ]}
        if "query." in url:
            return 200, {"items": [
                {"resourceType": "Instance", "identifier": "ocid1.instance.1",
                 "displayName": "web-1", "regionName": "us-ashburn-1", "lifecycleState": "RUNNING"},
            ]}
        return 404, {}

    monkeypatch.setattr("observa_connectors.providers.oci.request_json", fake_request)
    result = OciConnector().pull(CONFIG, _secrets(pem))

    assert len(result.costs) == 1
    assert result.costs[0].amount == 42.5
    assert len(result.resources) == 1
    assert result.resources[0].name == "web-1"
    assert result.resources[0].status == "RUNNING"


def test_missing_cryptography_gives_clear_error(monkeypatch, keypair):
    _, pem = keypair
    import builtins
    real_import = builtins.__import__

    def blocked_import(name, *args, **kwargs):
        if name == "cryptography.hazmat.primitives":
            raise ImportError("no module named cryptography")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", blocked_import)
    result = OciConnector().test_connection(CONFIG, _secrets(pem))
    assert not result.ok
    assert "cryptography" in result.message
