"""Tests for remote-transport protection: bearer login, rate limit, allowed hosts, /health."""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from google_ads_mcp import http_security as hs

INIT = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2025-06-18",
        "capabilities": {},
        "clientInfo": {"name": "pytest", "version": "1"},
    },
}
MCP_HEADERS = {"accept": "application/json, text/event-stream", "content-type": "application/json"}


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for name in (
        "MCP_HTTP_BEARER_TOKEN",
        "MCP_ALLOW_UNAUTHENTICATED",
        "MCP_ALLOWED_HOSTS",
        "MCP_RATE_LIMIT_MAX",
        "MCP_RATE_LIMIT_WINDOW_SECONDS",
    ):
        monkeypatch.delenv(name, raising=False)


# ── pure helpers ──────────────────────────────────────────────────────────


def test_token_matches_is_exact():
    assert hs.token_matches("abc", "abc")
    assert not hs.token_matches("abc", "abd")
    assert not hs.token_matches("", "abc")


def test_startup_allows_localhost_without_token():
    hs.check_startup_safety("127.0.0.1")


def test_startup_refuses_public_without_token():
    with pytest.raises(SystemExit):
        hs.check_startup_safety("0.0.0.0")


def test_startup_allows_public_with_token(monkeypatch):
    monkeypatch.setenv("MCP_HTTP_BEARER_TOKEN", "t" * 40)
    hs.check_startup_safety("0.0.0.0")


def test_startup_explicit_unauthenticated_opt_in(monkeypatch):
    monkeypatch.setenv("MCP_ALLOW_UNAUTHENTICATED", "true")
    hs.check_startup_safety("0.0.0.0")


def test_transport_security_local_default():
    settings = hs.build_transport_security("127.0.0.1")
    assert settings.enable_dns_rebinding_protection
    assert "localhost:*" in settings.allowed_hosts


def test_transport_security_custom_domain(monkeypatch):
    monkeypatch.setenv("MCP_ALLOWED_HOSTS", "ads.example.com")
    settings = hs.build_transport_security("0.0.0.0")
    assert "ads.example.com" in settings.allowed_hosts
    assert "https://ads.example.com" in settings.allowed_origins
    assert "localhost:*" not in settings.allowed_hosts


def test_transport_security_public_without_hosts_is_off():
    assert hs.build_transport_security("0.0.0.0") is None


def test_rate_limiter_blocks_then_recovers():
    limiter = hs.SlidingWindowRateLimiter(max_requests=2, window_seconds=10)
    assert limiter.check("a", now=0)[0]
    assert limiter.check("a", now=1)[0]
    allowed, retry = limiter.check("a", now=2)
    assert not allowed and retry == pytest.approx(8)
    assert limiter.check("a", now=11)[0]


def test_rate_limiter_keys_are_independent_and_evicted():
    limiter = hs.SlidingWindowRateLimiter(max_requests=1, window_seconds=5)
    assert limiter.check("a", now=0)[0]
    assert limiter.check("b", now=0)[0]
    assert len(limiter) == 2
    limiter.check("c", now=100)  # sweeps idle keys
    assert len(limiter) == 1


# ── middleware on a tiny app ──────────────────────────────────────────────


async def _ok_app(scope, receive, send):
    if scope["type"] == "lifespan":
        while True:
            message = await receive()
            if message["type"] == "lifespan.startup":
                await send({"type": "lifespan.startup.complete"})
            else:
                await send({"type": "lifespan.shutdown.complete"})
                return
    await send({"type": "http.response.start", "status": 200, "headers": []})
    await send({"type": "http.response.body", "body": b"ok"})


def test_guard_requires_bearer():
    app = hs.HttpGuard(_ok_app, token="secret-token", limiter=None)
    with TestClient(app) as c:
        assert c.get("/mcp").status_code == 401
        assert c.get("/mcp", headers={"authorization": "Bearer wrong"}).status_code == 401
        assert c.get("/mcp", headers={"authorization": "Bearer secret-token"}).status_code == 200
        assert c.get("/health").status_code == 200  # exempt


def test_guard_rate_limits():
    app = hs.HttpGuard(_ok_app, token=None, limiter=hs.SlidingWindowRateLimiter(2, 60))
    with TestClient(app) as c:
        assert c.get("/mcp").status_code == 200
        assert c.get("/mcp").status_code == 200
        r = c.get("/mcp")
        assert r.status_code == 429
        assert int(r.headers["retry-after"]) >= 1


# ── the real MCP app ──────────────────────────────────────────────────────


@pytest.fixture
def fresh_mcp():
    """FastMCP caches one session manager per process; reset it between tests."""
    from google_ads_mcp.server import mcp

    mcp._session_manager = None
    yield
    mcp._session_manager = None


def test_real_app_health_and_auth(monkeypatch, fresh_mcp):
    monkeypatch.setenv("MCP_HTTP_BEARER_TOKEN", "a-long-random-test-token")
    from google_ads_mcp.server import build_http_app

    app = build_http_app("streamable-http", "127.0.0.1")
    with TestClient(app, base_url="http://localhost") as c:
        health = c.get("/health")
        assert health.status_code == 200
        body = health.json()
        assert body["status"] == "ok"
        assert body["auth_required"] is True
        assert body["gated_tools"] == 19
        assert "a-long-random-test-token" not in health.text

        assert c.post("/mcp", json=INIT, headers=MCP_HEADERS).status_code == 401
        ok = c.post(
            "/mcp",
            json=INIT,
            headers={**MCP_HEADERS, "authorization": "Bearer a-long-random-test-token"},
        )
        assert ok.status_code == 200
        assert "serverInfo" in ok.text


def test_real_app_rejects_unknown_host(monkeypatch, fresh_mcp):
    monkeypatch.setenv("MCP_ALLOWED_HOSTS", "ads.example.com")
    monkeypatch.setenv("MCP_HTTP_BEARER_TOKEN", "a-long-random-test-token")
    from google_ads_mcp.server import build_http_app

    app = build_http_app("streamable-http", "0.0.0.0")
    auth = {**MCP_HEADERS, "authorization": "Bearer a-long-random-test-token"}
    with TestClient(app, base_url="http://evil.example.net") as c:
        assert c.post("/mcp", json=INIT, headers=auth).status_code == 421
    from google_ads_mcp.server import mcp

    mcp._session_manager = None
    app = build_http_app("streamable-http", "0.0.0.0")
    with TestClient(app, base_url="http://ads.example.com") as c:
        assert c.post("/mcp", json=INIT, headers=auth).status_code == 200
