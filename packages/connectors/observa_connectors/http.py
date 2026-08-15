from __future__ import annotations

from typing import Any

DEFAULT_TIMEOUT = 20


def request_json(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
    auth: tuple[str, str] | None = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> tuple[int, Any]:
    """Thin wrapper around requests so connectors don't each re-implement error handling.

    Import is lazy: the base API app doesn't need `requests` unless a real
    (non-stub) connector actually runs a sync.
    """
    import requests

    resp = requests.request(
        method,
        url,
        headers=headers,
        params=params,
        json=json_body,
        auth=auth,
        timeout=timeout,
    )
    try:
        body = resp.json()
    except ValueError:
        body = resp.text
    return resp.status_code, body


class ConnectorAuthError(Exception):
    """Raised by a connector when credentials are rejected by the upstream API."""
