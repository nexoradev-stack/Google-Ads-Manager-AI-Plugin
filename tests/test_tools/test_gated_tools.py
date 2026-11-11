"""Every gated tool must return a preview (and call no mutate API) without confirm,
and must reach the Google Ads API when confirm=True.

The Google Ads client is fully mocked; no credentials or network are used.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from google_ads_mcp.tools import ad_groups, ads, budgets, campaigns, keywords, performance_max

CID = "1234567890"


@pytest.fixture(autouse=True)
def _no_limits(monkeypatch):
    for name in (
        "GOOGLE_ADS_MAX_DAILY_BUDGET",
        "GOOGLE_ADS_MAX_BUDGET_INCREASE_PCT",
        "GOOGLE_ADS_MAX_CPC_BID",
    ):
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def client():
    c = MagicMock()
    c.resolve_customer_id.side_effect = lambda cid: (cid or CID).replace("-", "")
    # Previews look up current values via GoogleAdsService.search; return no rows.
    c.get_service.return_value.search.return_value = []
    return c


@pytest.fixture
def ctx(client):
    return SimpleNamespace(
        request_context=SimpleNamespace(lifespan_context=SimpleNamespace(client=client))
    )


def mutate_calls(client) -> list[str]:
    """Names of every mutate* method called on any Google Ads service."""
    service = client.get_service.return_value
    return [name for name, _args, _kw in service.method_calls if name.startswith("mutate")]


PMAX_ARGS = dict(
    customer_id=CID,
    campaign_name="PMax Test",
    budget_amount=40.0,
    asset_group_name="AG",
    final_urls=["https://example.com"],
    headlines=["One", "Two", "Three"],
    long_headlines=["A long headline"],
    descriptions=["Desc one", "Desc two"],
    business_name="Example",
)

# (tool function, kwargs) for calls that MUST be gated
GATED_CALLS = [
    (budgets.create_budget, dict(customer_id=CID, name="B", amount=50.0)),
    (budgets.update_budget, dict(customer_id=CID, budget_id="11", amount=75.0)),
    (budgets.update_budget, dict(customer_id=CID, budget_id="11", delivery_method="ACCELERATED")),
    (campaigns.create_campaign, dict(customer_id=CID, name="C", budget_amount=30.0)),
    (campaigns.create_campaign, dict(customer_id=CID, name="C", budget_amount=30.0, status="ENABLED")),
    (campaigns.update_campaign, dict(customer_id=CID, campaign_id="22", status="ENABLED")),
    (campaigns.update_campaign, dict(customer_id=CID, campaign_id="22", target_cpa=12.0)),
    (campaigns.update_campaign, dict(customer_id=CID, campaign_id="22", end_date="2027-01-31")),
    (campaigns.set_campaign_status, dict(customer_id=CID, campaign_id="22", status="ENABLED")),
    (campaigns.set_campaign_status, dict(customer_id=CID, campaign_id="22", status="REMOVED")),
    (campaigns.remove_campaign, dict(customer_id=CID, campaign_id="22")),
    (ad_groups.create_ad_group, dict(customer_id=CID, campaign_id="22", name="AG")),
    (ad_groups.create_ad_group, dict(customer_id=CID, campaign_id="22", name="AG", status="PAUSED", cpc_bid=2.0)),
    (ad_groups.update_ad_group, dict(customer_id=CID, ad_group_id="33", cpc_bid=3.0)),
    (ad_groups.update_ad_group, dict(customer_id=CID, ad_group_id="33", status="REMOVED")),
    (ad_groups.set_ad_group_status, dict(customer_id=CID, ad_group_id="33", status="ENABLED")),
    (ads.create_responsive_search_ad, dict(customer_id=CID, ad_group_id="33", headlines=["h1", "h2", "h3"], descriptions=["d1", "d2"], final_urls=["https://example.com"])),
    (ads.set_ad_status, dict(customer_id=CID, ad_group_id="33", ad_id="44", status="ENABLED")),
    (ads.set_ad_status, dict(customer_id=CID, ad_group_id="33", ad_id="44", status="REMOVED")),
    (keywords.add_keywords, dict(customer_id=CID, ad_group_id="33", keywords=[{"text": "shoes", "match_type": "PHRASE"}])),
    (keywords.update_keyword_bid, dict(customer_id=CID, ad_group_id="33", criterion_id="55", cpc_bid=1.5)),
    (keywords.remove_keyword, dict(customer_id=CID, ad_group_id="33", criterion_id="55")),
    (performance_max.create_performance_max_campaign, PMAX_ARGS),
    (performance_max.remove_asset_from_group, dict(customer_id=CID, asset_group_id="66", asset_resource_name="customers/1/assets/2", field_type="HEADLINE")),
]


def _id(param):
    fn, kwargs = param
    extra = kwargs.get("status") or ("amount" if "amount" in kwargs else "")
    return f"{fn.__name__}-{extra}" if extra else fn.__name__


@pytest.mark.parametrize("call", GATED_CALLS, ids=[_id(c) for c in GATED_CALLS])
def test_gated_call_returns_preview_and_does_not_mutate(call, client, ctx):
    fn, kwargs = call
    result = fn(ctx=ctx, **kwargs)
    assert result["success"] is False, result
    assert result["confirmation_required"] is True, result
    assert result["preview"]["tool"] in {
        fn.__name__,
        "update_campaign",  # set_campaign_status / remove_campaign delegate here
        "update_ad_group",  # set_ad_group_status delegates here
    }
    assert result["preview"]["financial_impact"]
    assert mutate_calls(client) == [], f"{fn.__name__} mutated without confirm"


@pytest.mark.parametrize("call", GATED_CALLS, ids=[_id(c) for c in GATED_CALLS])
def test_gated_call_runs_with_confirm(call, client, ctx):
    fn, kwargs = call
    result = fn(ctx=ctx, confirm=True, **kwargs)
    assert result.get("confirmation_required") is not True, result
    assert result["success"] is True, result
    assert mutate_calls(client), f"{fn.__name__} did not call the API after confirm"


# Calls that must run immediately (no gate): pausing, renaming, paused creation.
UNGATED_CALLS = [
    (campaigns.set_campaign_status, dict(customer_id=CID, campaign_id="22", status="PAUSED")),
    (campaigns.update_campaign, dict(customer_id=CID, campaign_id="22", name="New name")),
    (ad_groups.set_ad_group_status, dict(customer_id=CID, ad_group_id="33", status="PAUSED")),
    (ad_groups.create_ad_group, dict(customer_id=CID, campaign_id="22", name="AG", status="PAUSED")),
    (ads.set_ad_status, dict(customer_id=CID, ad_group_id="33", ad_id="44", status="PAUSED")),
    (budgets.update_budget, dict(customer_id=CID, budget_id="11", name="Renamed")),
]


@pytest.mark.parametrize("call", UNGATED_CALLS, ids=[_id(c) for c in UNGATED_CALLS])
def test_pause_and_rename_are_never_gated(call, client, ctx):
    fn, kwargs = call
    result = fn(ctx=ctx, **kwargs)
    assert result.get("confirmation_required") is not True, result
    assert mutate_calls(client)


def test_legacy_confirm_removal_still_works(client, ctx):
    result = keywords.remove_keyword(ctx=ctx, customer_id=CID, ad_group_id="33", criterion_id="55", confirm_removal=True)
    assert result["success"] is True
    result = campaigns.remove_campaign(ctx=ctx, customer_id=CID, campaign_id="22", confirm_removal=True)
    assert result["success"] is True


def test_set_campaign_status_removed_no_longer_bypasses_confirmation(client, ctx):
    """Regression: REMOVED via set_campaign_status used to skip confirm_removal."""
    result = campaigns.set_campaign_status(ctx=ctx, customer_id=CID, campaign_id="22", status="REMOVED")
    assert result["confirmation_required"] is True
    assert result["preview"]["reversible"] is False
    assert mutate_calls(client) == []


# ── spend limits are enforced even with confirm=True ──────────────────────


def test_daily_budget_limit_blocks_confirmed_create(monkeypatch, client, ctx):
    monkeypatch.setenv("GOOGLE_ADS_MAX_DAILY_BUDGET", "100")
    result = budgets.create_budget(ctx=ctx, customer_id=CID, name="Big", amount=1000.0, confirm=True)
    assert result["blocked_by_spend_limit"] is True
    assert mutate_calls(client) == []


def test_daily_budget_limit_blocks_confirmed_campaigns(monkeypatch, client, ctx):
    monkeypatch.setenv("GOOGLE_ADS_MAX_DAILY_BUDGET", "100")
    r1 = campaigns.create_campaign(ctx=ctx, customer_id=CID, name="C", budget_amount=500.0, confirm=True)
    r2 = performance_max.create_performance_max_campaign(ctx=ctx, confirm=True, **{**PMAX_ARGS, "budget_amount": 500.0})
    assert r1["blocked_by_spend_limit"] and r2["blocked_by_spend_limit"]
    assert mutate_calls(client) == []


def test_budget_increase_limit_uses_current_amount(monkeypatch, client, ctx):
    monkeypatch.setenv("GOOGLE_ADS_MAX_BUDGET_INCREASE_PCT", "20")
    with patch.object(budgets, "lookup_budget_amount", return_value=100.0):
        ok = budgets.update_budget(ctx=ctx, customer_id=CID, budget_id="11", amount=120.0)
        assert ok["confirmation_required"] is True
        assert ok["preview"]["current_state"] == {"daily_amount": 100.0}
        blocked = budgets.update_budget(ctx=ctx, customer_id=CID, budget_id="11", amount=1000.0, confirm=True)
    assert blocked["blocked_by_spend_limit"] is True
    assert mutate_calls(client) == []


def test_cpc_limit_blocks_keywords_and_bids(monkeypatch, client, ctx):
    monkeypatch.setenv("GOOGLE_ADS_MAX_CPC_BID", "4")
    r1 = keywords.add_keywords(
        ctx=ctx, customer_id=CID, ad_group_id="33",
        keywords=[{"text": "a", "cpc_bid": 2}, {"text": "b", "cpc_bid": 40}], confirm=True,
    )
    r2 = keywords.update_keyword_bid(ctx=ctx, customer_id=CID, ad_group_id="33", criterion_id="55", cpc_bid=9.0, confirm=True)
    r3 = ad_groups.update_ad_group(ctx=ctx, customer_id=CID, ad_group_id="33", cpc_bid=9.0, confirm=True)
    assert all(r["blocked_by_spend_limit"] for r in (r1, r2, r3))
    assert mutate_calls(client) == []


def test_budget_preview_shows_monthly_difference(client, ctx):
    with patch.object(budgets, "lookup_budget_amount", return_value=50.0):
        result = budgets.update_budget(ctx=ctx, customer_id=CID, budget_id="11", amount=75.0)
    impact = result["preview"]["financial_impact"]
    assert "50.00" in impact and "75.00" in impact and "+25.00/day" in impact
