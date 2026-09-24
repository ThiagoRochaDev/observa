from __future__ import annotations

import hashlib
import threading
import time
from collections import defaultdict, deque

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.core.config import Settings


class FixedWindowRateLimiter:
    def __init__(self) -> None:
        self._requests: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str, *, limit: int, window_seconds: int) -> tuple[bool, int, int]:
        now = time.monotonic()
        cutoff = now - window_seconds
        with self._lock:
            timestamps = self._requests[key]
            while timestamps and timestamps[0] <= cutoff:
                timestamps.popleft()
            if len(timestamps) >= limit:
                retry_after = max(1, int(window_seconds - (now - timestamps[0])) + 1)
                return False, 0, retry_after
            timestamps.append(now)
            return True, max(0, limit - len(timestamps)), window_seconds

    def reset(self) -> None:
        with self._lock:
            self._requests.clear()


rate_limiter = FixedWindowRateLimiter()


class SecurityMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, settings: Settings) -> None:
        super().__init__(app)
        self.settings = settings

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                too_large = int(content_length) > self.settings.max_request_body_bytes
            except ValueError:
                return JSONResponse({"detail": "Invalid Content-Length"}, status_code=400)
            if too_large:
                return JSONResponse({"detail": "Request body too large"}, status_code=413)

        rate_headers: dict[str, str] = {}
        if self.settings.rate_limit_enabled and request.url.path not in {"/", "/healthz", "/readyz"}:
            is_auth = request.url.path.startswith("/auth/")
            limit = (
                self.settings.auth_rate_limit_requests
                if is_auth
                else self.settings.rate_limit_requests
            )
            key = self._rate_limit_key(request, "auth" if is_auth else "api")
            allowed, remaining, retry_after = rate_limiter.check(
                key,
                limit=limit,
                window_seconds=self.settings.rate_limit_window_seconds,
            )
            rate_headers = {
                "RateLimit-Limit": str(limit),
                "RateLimit-Remaining": str(remaining),
                "RateLimit-Reset": str(retry_after),
            }
            if not allowed:
                return JSONResponse(
                    {"detail": "Rate limit exceeded"},
                    status_code=429,
                    headers={**rate_headers, "Retry-After": str(retry_after)},
                )

        response = await call_next(request)
        response.headers.update(rate_headers)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Cache-Control"] = "no-store"
        return response

    def _rate_limit_key(self, request: Request, group: str) -> str:
        address = request.client.host if request.client else "unknown"
        if self.settings.trust_proxy_headers:
            forwarded = request.headers.get("x-forwarded-for", "").split(",", 1)[0].strip()
            if forwarded:
                address = forwarded
        credential = request.headers.get("x-observa-api-key") or request.headers.get(
            "authorization", ""
        )
        identity = hashlib.sha256(credential.encode("utf-8")).hexdigest()[:16] if credential else "anon"
        tenancy = request.headers.get("x-observa-tenancy-id", "default")
        return f"{group}:{address}:{tenancy}:{identity}"
