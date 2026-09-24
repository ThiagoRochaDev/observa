from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Test one live connector without persisting secrets")
    parser.add_argument("--url", default="http://127.0.0.1:8080")
    parser.add_argument("--api-key", required=True)
    parser.add_argument("--connector", required=True)
    parser.add_argument("--payload", type=Path, required=True)
    parser.add_argument("--company-id")
    parser.add_argument("--tenancy-id")
    args = parser.parse_args()

    private_payload = json.loads(args.payload.read_text(encoding="utf-8"))
    body = json.dumps(
        {
            "connector_id": args.connector,
            "config": private_payload.get("config", {}),
            "secrets": private_payload.get("secrets", {}),
        }
    ).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "X-Observa-Api-Key": args.api_key,
    }
    if args.company_id:
        headers["X-Observa-Company-ID"] = args.company_id
    if args.tenancy_id:
        headers["X-Observa-Tenancy-ID"] = args.tenancy_id
    request = urllib.request.Request(
        f"{args.url.rstrip('/')}/api/connections/test",
        data=body,
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            result = json.load(response)
    except urllib.error.HTTPError as exc:
        raise SystemExit(f"Connector smoke test failed with HTTP {exc.code}") from exc
    if not result.get("ok"):
        raise SystemExit("Connector rejected the supplied credentials or endpoint")
    print(json.dumps({"ok": True, "connector": args.connector}, indent=2))


if __name__ == "__main__":
    main()
