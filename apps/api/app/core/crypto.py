from __future__ import annotations

from cryptography.fernet import Fernet

from app.core.config import get_settings


def _fernet() -> Fernet:
    path = get_settings().key_file
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_bytes(Fernet.generate_key())
    return Fernet(path.read_bytes().strip())


def encrypt_json(data: dict) -> str:
    import json

    raw = json.dumps(data).encode("utf-8")
    return _fernet().encrypt(raw).decode("utf-8")


def decrypt_json(token: str) -> dict:
    import json

    if not token:
        return {}
    raw = _fernet().decrypt(token.encode("utf-8"))
    return json.loads(raw.decode("utf-8"))
