"""Fail closed before capturing public media from an Observa instance."""
import json
import os
from urllib.parse import urlparse
from urllib.request import Request, urlopen

TGR_PRODUCTS = {"move-easy", "easy-food", "detect-easy", "observa", "vr-archviz"}


def validate_catalog(connections: list[dict], products: list[dict]) -> None:
    if not connections or any(c.get("connector_id") != "mock-demo" for c in connections):
        raise ValueError("Public media requires Mock Demo connections only.")
    if {p.get("slug") for p in products} != TGR_PRODUCTS:
        raise ValueError("Public media requires the complete synthetic TGR product catalog.")


def verify_demo_source(web_url: str, api_url: str, api_key: str) -> None:
    if os.getenv("OBSERVA_DEMO_SYNTHETIC_ONLY") != "1":
        raise ValueError("Use a fresh disposable TGR demo and set OBSERVA_DEMO_SYNTHETIC_ONLY=1.")
    for url in (web_url, api_url):
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
            raise ValueError("Public media capture is restricted to a local disposable demo.")

    def read(path: str) -> list[dict]:
        request = Request(api_url.rstrip("/") + path, headers={"X-Observa-Api-Key": api_key})
        with urlopen(request, timeout=10) as response:
            return json.load(response)

    validate_catalog(read("/api/connections"), read("/api/products"))
