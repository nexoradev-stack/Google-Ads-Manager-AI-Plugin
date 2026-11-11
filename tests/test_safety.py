"""Unit tests for the confirmation gate and spend limits (google_ads_mcp.safety)."""

from __future__ import annotations

import pytest

from google_ads_mcp import safety


@pytest.fixture(autouse=True)
def _no_limits(monkeypatch):
    for name in (
        "GOOGLE_ADS_MAX_DAILY_BUDGET",
        "GOOGLE_ADS_MAX_BUDGET_INCREASE_PCT",
        "GOOGLE_ADS_MAX_CPC_BID",
    ):
        monkeypatch.delenv(name, raising=False)


# ── require_confirmation ──────────────────────────────────────────────────


def test_preview_returned_without_confirm():
    result = safety.require_confirmation(
        "update_budget",
        False,
        summary="Update budget 1",
        current_state={"daily_amount": 50.0},
        changes={"daily_amount": 75.0},
        financial_impact="+25/day",
    )
    assert result["success"] is False
    assert result["confirmation_required"] is True
    preview = result["preview"]
    assert preview["tool"] == "update_budget"
    assert preview["current_state"] == {"daily_amount": 50.0}
    assert preview["requested_changes"] == {"daily_amount": 75.0}
    assert preview["financial_impact"] == "+25/day"
    assert preview["reversible"] is True
    assert "spend_limits" in preview


def test_confirm_true_allows_action():
    assert safety.require_confirmation("x", True, summary="s", financial_impact="i") is None


@pytest.mark.parametrize("value", [None, 0, "true", "yes", 1])
def test_only_boolean_true_confirms(value):
    """Truthy strings or 1 must not count as confirmation."""
    result = safety.require_confirmation("x", value, summary="s", financial_impact="i")
    assert result is not None and result["confirmation_required"] is True


# ── statuses ──────────────────────────────────────────────────────────────


@pytest.mark.parametrize("status,risky", [("ENABLED", True), ("enabled", True), ("REMOVED", True), ("PAUSED", False), (None, False)])
def test_is_risky_status(status, risky):
    assert safety.is_risky_status(status) is risky


def test_removal_is_irreversible():
    _, reversible = safety.status_impact("REMOVED")
    assert reversible is False


# ── spend limits ──────────────────────────────────────────────────────────


def test_limits_off_by_default():
    assert safety.spend_limits() == {
        "max_daily_budget": None,
        "max_budget_increase_pct": None,
        "max_cpc_bid": None,
    }


def test_invalid_limit_values_ignored(monkeypatch):
    monkeypatch.setenv("GOOGLE_ADS_MAX_DAILY_BUDGET", "lots")
    monkeypatch.setenv("GOOGLE_ADS_MAX_CPC_BID", "-3")
    limits = safety.spend_limits()
    assert limits["max_daily_budget"] is None
    assert limits["max_cpc_bid"] is None


def test_daily_budget_limit(monkeypatch):
    monkeypatch.setenv("GOOGLE_ADS_MAX_DAILY_BUDGET", "200")
    assert safety.check_daily_budget(200) is None
    blocked = safety.check_daily_budget(2000)
    assert blocked["blocked_by_spend_limit"] is True
    assert blocked["details"] == {"requested": 2000, "limit": 200.0}


def test_daily_budget_must_be_positive():
    assert safety.check_daily_budget(0)["success"] is False
    assert safety.check_daily_budget(None) is None


def test_budget_increase_limit(monkeypatch):
    monkeypatch.setenv("GOOGLE_ADS_MAX_BUDGET_INCREASE_PCT", "50")
    assert safety.check_budget_increase(100, 150) is None
    assert safety.check_budget_increase(100, 80) is None  # decreases always allowed
    blocked = safety.check_budget_increase(100, 151)
    assert blocked["blocked_by_spend_limit"] is True
    assert blocked["details"]["increase_pct"] == 51.0


def test_budget_increase_blocks_when_current_unknown(monkeypatch):
    monkeypatch.setenv("GOOGLE_ADS_MAX_BUDGET_INCREASE_PCT", "50")
    assert safety.check_budget_increase(None, 100)["blocked_by_spend_limit"] is True


def test_budget_increase_ignored_without_limit():
    assert safety.check_budget_increase(None, 10_000) is None


def test_cpc_bid_limit(monkeypatch):
    monkeypatch.setenv("GOOGLE_ADS_MAX_CPC_BID", "5")
    assert safety.check_cpc_bid(5) is None
    assert safety.check_cpc_bid(50)["blocked_by_spend_limit"] is True
    assert safety.check_cpc_bid(-1)["success"] is False


def test_first_block_returns_first_problem():
    assert safety.first_block(None, None) is None
    assert safety.first_block(None, {"a": 1}, {"b": 2}) == {"a": 1}


def test_gated_tools_are_registered_with_confirm_param():
    """Every tool in GATED_TOOLS exists and exposes a `confirm` argument."""
    from google_ads_mcp.server import mcp

    tools = {t.name: t for t in mcp._tool_manager.list_tools()}
    for name in safety.GATED_TOOLS:
        assert name in tools, name
        assert "confirm" in tools[name].parameters["properties"], name
    exposing_confirm = {n for n, t in tools.items() if "confirm" in t.parameters["properties"]}
    assert exposing_confirm == set(safety.GATED_TOOLS)
