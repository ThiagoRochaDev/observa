from __future__ import annotations

import os
import stat

from cryptography.fernet import Fernet

from app.core.config import get_settings


def _restrict(path) -> None:
    """Best-effort chmod 0600 — no-op on platforms without POSIX perms (Windows)."""
    try:
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    except (OSError, NotImplementedError):
        pass


def _fernet() -> Fernet:
    path = get_settings().key_file
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_bytes(Fernet.generate_key())
        _restrict(path)
    else:
        _restrict(path)
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
