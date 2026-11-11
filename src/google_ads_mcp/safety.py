"""Safety gate and spend limits for Google Ads write tools.

Two layers protect an ad account from mistakes:

1. **Confirmation gate** — any action that can start spending, raise spend,
   or remove something returns a *preview* first and only runs when the tool
   is called again with ``confirm=True``. Reads and pauses are never gated:
   pausing stops spend, so it must always be instant.

2. **Spend limits** — optional hard ceilings read from environment variables.
   A request that breaks a limit is refused even when ``confirm=True``, so a
   typo such as an extra zero on a budget is always caught.

    GOOGLE_ADS_MAX_DAILY_BUDGET          largest daily budget allowed (currency units)
    GOOGLE_ADS_MAX_BUDGET_INCREASE_PCT   largest % increase on an existing budget
    GOOGLE_ADS_MAX_CPC_BID               largest max-CPC bid allowed (currency units)

Limits are read on every call so they can be changed without a restart.
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

# Tools that can be gated. Used by tests and documentation to keep the
# list honest; each tool still decides *when* it needs confirmation
# (for example, pausing is never gated).
GATED_TOOLS: frozenset[str] = frozenset(
    {
        "create_budget",
        "update_budget",
        "create_campaign",
        "update_campaign",
        "set_campaign_status",
        "remove_campaign",
        "create_ad_group",
        "update_ad_group",
        "set_ad_group_status",
        "create_responsive_search_ad",
        "create_responsive_display_ad",
        "create_video_ad",
        "create_demand_gen_ad",
        "set_ad_status",
        "add_keywords",
        "update_keyword_bid",
        "remove_keyword",
        "create_performance_max_campaign",
        "remove_asset_from_group",
    }
)

# Statuses that start spend or delete something. PAUSED is deliberately absent.
RISKY_STATUSES: frozenset[str] = frozenset({"ENABLED", "REMOVED"})

CONFIRM_MESSAGE = (
    "Confirmation required. Nothing has been changed yet. Review the preview, "
    "then call this tool again with the same arguments and confirm=True to apply it."
)


# ── Spend limits ──────────────────────────────────────────────────────────


def _env_float(name: str) -> float | None:
    """Read a positive float from the environment, or None if unset/invalid."""
    raw = os.environ.get(name, "").strip()
    if not raw:
        return None
    try:
        value = float(raw)
    except ValueError:
        logger.warning("Ignoring %s: not a number", name)
        return None
    if value <= 0:
        logger.warning("Ignoring %s: must be greater than zero", name)
        return None
    return value


def spend_limits() -> dict[str, float | None]:
    """Return the currently configured spend limits (None = no limit)."""
    return {
        "max_daily_budget": _env_float("GOOGLE_ADS_MAX_DAILY_BUDGET"),
        "max_budget_increase_pct": _env_float("GOOGLE_ADS_MAX_BUDGET_INCREASE_PCT"),
        "max_cpc_bid": _env_float("GOOGLE_ADS_MAX_CPC_BID"),
    }


def _blocked(reason: str, **details: Any) -> dict:
    return {
        "success": False,
        "blocked_by_spend_limit": True,
        "error": f"Blocked by spend limit: {reason}",
        "details": details,
    }


def check_daily_budget(amount: float | None) -> dict | None:
    """Refuse a daily budget above GOOGLE_ADS_MAX_DAILY_BUDGET."""
    if amount is None:
        return None
    if amount <= 0:
        return {"success": False, "error": "Budget amount must be greater than zero."}
    limit = spend_limits()["max_daily_budget"]
    if limit is not None and amount > limit:
        return _blocked(
            f"daily budget {amount:.2f} is above the maximum of {limit:.2f} "
            "(GOOGLE_ADS_MAX_DAILY_BUDGET).",
            requested=amount,
            limit=limit,
        )
    return None


def check_budget_increase(current: float | None, new: float | None) -> dict | None:
    """Refuse a budget increase above GOOGLE_ADS_MAX_BUDGET_INCREASE_PCT."""
    if new is None:
        return None
    limit = spend_limits()["max_budget_increase_pct"]
    if limit is None:
        return None
    if current is None:
        return _blocked(
            "the current budget could not be read, so the maximum increase "
            "(GOOGLE_ADS_MAX_BUDGET_INCREASE_PCT) cannot be checked.",
            requested=new,
            limit_pct=limit,
        )
    if current <= 0 or new <= current:
        return None
    increase_pct = (new - current) / current * 100
    if increase_pct > limit:
        return _blocked(
            f"increase of {increase_pct:.1f}% (from {current:.2f} to {new:.2f}) is above "
            f"the maximum of {limit:.1f}% (GOOGLE_ADS_MAX_BUDGET_INCREASE_PCT).",
            current=current,
            requested=new,
            increase_pct=round(increase_pct, 1),
            limit_pct=limit,
        )
    return None


def check_cpc_bid(bid: float | None) -> dict | None:
    """Refuse a max-CPC bid above GOOGLE_ADS_MAX_CPC_BID."""
    if bid is None:
        return None
    if bid <= 0:
        return {"success": False, "error": "CPC bid must be greater than zero."}
    limit = spend_limits()["max_cpc_bid"]
    if limit is not None and bid > limit:
        return _blocked(
            f"CPC bid {bid:.2f} is above the maximum of {limit:.2f} (GOOGLE_ADS_MAX_CPC_BID).",
            requested=bid,
            limit=limit,
        )
    return None


def first_block(*results: dict | None) -> dict | None:
    """Return the first non-None limit result, if any."""
    for result in results:
        if result is not None:
            return result
    return None


# ── Confirmation gate ─────────────────────────────────────────────────────


def require_confirmation(
    tool: str,
    confirm: bool,
    *,
    summary: str,
    changes: dict[str, Any] | None = None,
    current_state: dict[str, Any] | None = None,
    financial_impact: str,
    reversible: bool = True,
) -> dict | None:
    """Return a preview response unless ``confirm`` is True.

    Returns None when the action may proceed.
    """
    if confirm is True:
        logger.info("safety.confirmed tool=%s", tool)
        return None
    return {
        "success": False,
        "confirmation_required": True,
        "message": CONFIRM_MESSAGE,
        "preview": {
            "tool": tool,
            "summary": summary,
            "current_state": current_state or {},
            "requested_changes": changes or {},
            "financial_impact": financial_impact,
            "reversible": reversible,
            "spend_limits": spend_limits(),
        },
    }


def is_risky_status(status: str | None) -> bool:
    """True when a status change can start spend or remove something."""
    return status is not None and status.upper() in RISKY_STATUSES


def status_impact(status: str) -> tuple[str, bool]:
    """Describe the money impact of a status change and whether it is reversible."""
    status = status.upper()
    if status == "ENABLED":
        return ("Turning this ON can start spending immediately if its campaign is live.", True)
    if status == "REMOVED":
        return ("Removing stops delivery permanently. Removed items cannot be re-enabled.", False)
    return ("Pausing stops spend.", True)


# ── Best-effort lookups for previews ──────────────────────────────────────


def lookup_budget_amount(client, customer_id: str, budget_id: str) -> float | None:
    """Return the current daily amount of a budget, or None if unavailable."""
    try:
        from .helpers import execute_query, micros_to_currency

        rows = execute_query(
            client,
            customer_id,
            "SELECT campaign_budget.amount_micros FROM campaign_budget "
            f"WHERE campaign_budget.id = {int(budget_id)}",
        )
        if not rows:
            return None
        micros = rows[0].get("campaign_budget", {}).get("amount_micros")
        return micros_to_currency(int(micros)) if micros is not None else None
    except Exception as exc:  # noqa: BLE001 — preview lookups must never break a tool
        logger.debug("safety.lookup_budget_failed: %s", exc)
        return None


def lookup_campaign(client, customer_id: str, campaign_id: str) -> dict[str, Any]:
    """Return name, status and daily budget of a campaign for previews (best effort)."""
    try:
        from .helpers import execute_query, micros_to_currency

        rows = execute_query(
            client,
            customer_id,
            "SELECT campaign.id, campaign.name, campaign.status, campaign_budget.amount_micros "
            f"FROM campaign WHERE campaign.id = {int(campaign_id)}",
        )
        if not rows:
            return {}
        row = rows[0]
        campaign = row.get("campaign", {})
        micros = row.get("campaign_budget", {}).get("amount_micros")
        return {
            "id": campaign.get("id", campaign_id),
            "name": campaign.get("name"),
            "status": campaign.get("status"),
            "daily_budget": micros_to_currency(int(micros)) if micros is not None else None,
        }
    except Exception as exc:  # noqa: BLE001
        logger.debug("safety.lookup_campaign_failed: %s", exc)
        return {}
