"""Protection for the remote (SSE / streamable-http) transports.

The stdio transport is a local child process and needs none of this. When the
server listens on a network port, this module adds:

* **Bearer-token login** — ``MCP_HTTP_BEARER_TOKEN``; compared in constant time.
* **Rate limiting** — ``MCP_RATE_LIMIT_MAX`` requests per
  ``MCP_RATE_LIMIT_WINDOW_SECONDS`` per client IP (default 120 per 60 s).
* **Allowed hosts** — ``MCP_ALLOWED_HOSTS`` (comma-separated) for the
  ``Host`` header check that blocks DNS-rebinding attacks.
* **/health** — a liveness endpoint that never needs a token and never
  reveals credential values.

Binding to a non-local address without a bearer token is refused unless
``MCP_ALLOW_UNAUTHENTICATED=true`` is set explicitly (for example when a
trusted reverse proxy already handles login).
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import time
from collections import deque
from collections.abc import Awaitable, Callable
from typing import Any

from mcp.server.transport_security import TransportSecuritySettings

logger = logging.getLogger(__name__)

LOCAL_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})
DEFAULT_EXEMPT_PATHS = frozenset({"/health"})

Scope = dict[str, Any]
Receive = Callable[[], Awaitable[dict[str, Any]]]
Send = Callable[[dict[str, Any]], Awaitable[None]]
ASGIApp = Callable[[Scope, Receive, Send], Awaitable[None]]


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        logger.warning("Ignoring %s=%r: not an integer", name, raw)
        return default
    return value if value > 0 else default


# ── Bearer token ──────────────────────────────────────────────────────────


def bearer_token() -> str | None:
    """Return the configured bearer token, or None when login is off."""
    token = os.environ.get("MCP_HTTP_BEARER_TOKEN", "").strip()
    return token or None


def token_matches(provided: str, expected: str) -> bool:
    """Constant-time comparison that also hides the token length."""
    a = hashlib.sha256(provided.encode("utf-8")).digest()
    b = hashlib.sha256(expected.encode("utf-8")).digest()
    return hmac.compare_digest(a, b)


def check_startup_safety(host: str) -> None:
    """Refuse to expose an unauthenticated server on a non-local address."""
    if host in LOCAL_HOSTS or bearer_token():
        return
    if _truthy(os.environ.get("MCP_ALLOW_UNAUTHENTICATED")):
        logger.warning(
            "Serving on %s WITHOUT a bearer token because MCP_ALLOW_UNAUTHENTICATED is set. "
            "Anyone who can reach this port can manage the Google Ads account.",
            host,
        )
        return
    raise SystemExit(
        f"Refusing to listen on {host} without MCP_HTTP_BEARER_TOKEN. "
        "Set a long random MCP_HTTP_BEARER_TOKEN, bind to 127.0.0.1, or (only behind a "
        "trusted authenticating proxy) set MCP_ALLOW_UNAUTHENTICATED=true."
    )


# ── Allowed hosts ─────────────────────────────────────────────────────────


def build_transport_security(host: str) -> TransportSecuritySettings | None:
    """Build Host-header protection from MCP_ALLOWED_HOSTS.

    Local binds always allow the loopback names. Returns None (no Host check)
    only for a non-local bind with no MCP_ALLOWED_HOSTS set.
    """
    extra = [h.strip() for h in os.environ.get("MCP_ALLOWED_HOSTS", "").split(",") if h.strip()]
    hosts: list[str] = []
    origins: list[str] = []
    if host in LOCAL_HOSTS or not extra:
        hosts += ["127.0.0.1", "localhost", "[::1]", "127.0.0.1:*", "localhost:*", "[::1]:*"]
        origins += ["http://127.0.0.1:*", "http://localhost:*", "http://[::1]:*"]
    for h in extra:
        hosts += [h, f"{h}:*"] if ":" not in h else [h]
        origins += [f"https://{h}", f"http://{h}"]
    if host not in LOCAL_HOSTS and not extra:
        logger.warning(
            "No MCP_ALLOWED_HOSTS set while listening on %s; Host-header checking is off. "
            "Set MCP_ALLOWED_HOSTS=your-domain.example.com for public deployments.",
            host,
        )
        return None
    return TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=hosts,
        allowed_origins=origins,
    )


# ── Rate limiting ─────────────────────────────────────────────────────────


class SlidingWindowRateLimiter:
    """In-memory per-key sliding window. Empty keys are evicted."""

    def __init__(self, max_requests: int, window_seconds: float) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = {}

    def check(self, key: str, now: float | None = None) -> tuple[bool, float]:
        """Return (allowed, retry_after_seconds)."""
        now = time.monotonic() if now is None else now
        cutoff = now - self.window_seconds
        hits = self._hits.get(key)
        if hits is None:
            hits = deque()
            self._hits[key] = hits
        while hits and hits[0] <= cutoff:
            hits.popleft()
        if len(hits) >= self.max_requests:
            return False, max(hits[0] + self.window_seconds - now, 0.0)
        hits.append(now)
        self._sweep(cutoff)
        return True, 0.0

    def _sweep(self, cutoff: float) -> None:
        for key in [k for k, v in self._hits.items() if not v or v[-1] <= cutoff]:
            del self._hits[key]

    def __len__(self) -> int:
        return len(self._hits)


def default_rate_limiter() -> SlidingWindowRateLimiter:
    return SlidingWindowRateLimiter(
        max_requests=_env_int("MCP_RATE_LIMIT_MAX", 120),
        window_seconds=_env_int("MCP_RATE_LIMIT_WINDOW_SECONDS", 60),
    )


# ── ASGI middleware ───────────────────────────────────────────────────────


async def _json(send: Send, status: int, body: dict, headers: list[tuple[bytes, bytes]] | None = None) -> None:
    payload = json.dumps(body).encode("utf-8")
    await send(
        {
            "type": "http.response.start",
            "status": status,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(payload)).encode()),
                *(headers or []),
            ],
        }
    )
    await send({"type": "http.response.body", "body": payload})


class HttpGuard:
    """ASGI middleware: bearer login + rate limit in front of the MCP app."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        token: str | None,
        limiter: SlidingWindowRateLimiter | None,
        exempt_paths: frozenset[str] = DEFAULT_EXEMPT_PATHS,
    ) -> None:
        self.app = app
        self.token = token
        self.limiter = limiter
        self.exempt_paths = exempt_paths

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope.get("type") != "http" or scope.get("path") in self.exempt_paths:
            await self.app(scope, receive, send)
            return

        if self.token:
            headers = dict(scope.get("headers") or [])
            auth = headers.get(b"authorization", b"").decode("latin-1")
            if not auth.lower().startswith("bearer "):
                await _json(send, 401, {"error": "Missing bearer token"}, [(b"www-authenticate", b"Bearer")])
                return
            if not token_matches(auth[7:].strip(), self.token):
                await _json(send, 401, {"error": "Invalid bearer token"}, [(b"www-authenticate", b"Bearer")])
                return

        if self.limiter is not None:
            client = scope.get("client") or ("anonymous", 0)
            allowed, retry_after = self.limiter.check(str(client[0]))
            if not allowed:
                seconds = max(int(retry_after) + 1, 1)
                await _json(
                    send,
                    429,
                    {"error": "Rate limit exceeded", "retry_after_seconds": seconds},
                    [(b"retry-after", str(seconds).encode())],
                )
                return

        await self.app(scope, receive, send)
