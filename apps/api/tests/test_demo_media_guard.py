import importlib.util
from pathlib import Path
import pytest

path = Path(__file__).resolve().parents[3] / "scripts" / "demo_media_guard.py"
spec = importlib.util.spec_from_file_location("demo_media_guard", path)
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


def test_capture_rejects_real_connections_even_alongside_demo():
    products = [{"slug": slug} for slug in guard.TGR_PRODUCTS]
    guard.validate_catalog([{"connector_id": "mock-demo"}], products)
    with pytest.raises(ValueError, match="Mock Demo"):
        guard.validate_catalog([{"connector_id": "mock-demo"}, {"connector_id": "gcp"}], products)


def test_capture_rejects_any_extra_non_tgr_product():
    products = [{"slug": slug} for slug in guard.TGR_PRODUCTS]
    with pytest.raises(ValueError, match="TGR"):
        guard.validate_catalog([{"connector_id": "mock-demo"}], products + [{"slug": "external-project"}])


def test_capture_rejects_remote_origin_without_network_access(monkeypatch):
    monkeypatch.setenv("OBSERVA_DEMO_SYNTHETIC_ONLY", "1")
    with pytest.raises(ValueError, match="local"):
        guard.verify_demo_source("https://example.test", "http://127.0.0.1:8080", "unused")
