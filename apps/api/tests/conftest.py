"""Isola os testes num DATA_DIR temporário — precisa acontecer ANTES de
qualquer `from app...` (get_settings() é @lru_cache, então o primeiro
import já fixa o caminho do banco pro resto do processo)."""

import os
import tempfile

_TMP_DATA_DIR = tempfile.mkdtemp(prefix="observa-test-data-")
os.environ["DATA_DIR"] = _TMP_DATA_DIR

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.security import get_or_create_api_key  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture()
def client() -> TestClient:
    with TestClient(app) as c:
        # Every /api route requires the key generated on first boot — tests
        # authenticate as the local operator would.
        c.headers["X-Observa-Api-Key"] = get_or_create_api_key()
        yield c
