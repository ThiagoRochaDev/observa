"""Isola os testes num DATA_DIR temporário — precisa acontecer ANTES de
qualquer `from app...` (get_settings() é @lru_cache, então o primeiro
import já fixa o caminho do banco pro resto do processo)."""

import os
import tempfile

_TMP_DATA_DIR = tempfile.mkdtemp(prefix="observa-test-data-")
os.environ["DATA_DIR"] = _TMP_DATA_DIR

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture()
def client() -> TestClient:
    with TestClient(app) as c:
        yield c
