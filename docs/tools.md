# Tool catalog (47 tools)

Tool names are stable across clients.

**Risk key:** 🟢 read · 🟡 write, runs immediately · 🔴 gated — returns a preview first and only runs when called again with `confirm=true`.

Pausing (`set_*_status` with `PAUSED`) is never gated. Spend limits (`GOOGLE_ADS_MAX_*`) can refuse 🔴 calls even when confirmed.

## Accounts (3)

| Tool | Risk | Gated when | What it does |
|---|:---:|---|---|
| `list_accessible_accounts` | 🟢 | — | List all Google Ads accounts accessible via current credentials. |
| `get_account_info` | 🟢 | — | Get details for a Google Ads account (name, currency, timezone, etc.). |
| `get_account_hierarchy` | 🟢 | — | Get the MCC account hierarchy tree. |

## Campaigns (6)

| Tool | Risk | Gated when | What it does |
|---|:---:|---|---|
| `list_campaigns` | 🟢 | — | List campaigns in a Google Ads account. |
| `get_campaign` | 🟢 | — | Get details for a single campaign. |
| `create_campaign` | 🔴 | always | Create a new campaign with a budget. |
| `update_campaign` | 🔴 | enable/remove, bidding targets or dates | Update an existing campaign's properties. |
| `set_campaign_status` | 🔴 | ENABLED or REMOVED | Set a campaign's status (enable, pause, or remove). |
| `remove_campaign` | 🔴 | always | Soft-delete (remove) a campaign. |

## Ad groups (5)

| Tool | Risk | Gated when | What it does |
|---|:---:|---|---|
| `list_ad_groups` | 🟢 | — | List ad groups in a campaign. |
| `get_ad_group` | 🟢 | — | Get details for a single ad group. |
| `create_ad_group` | 🔴 | ENABLED or with bids | Create a new ad group in a campaign. |
| `update_ad_group` | 🔴 | bids, enable or remove | Update an existing ad group. |
| `set_ad_group_status` | 🔴 | ENABLED or REMOVED | Set an ad group's status (enable, pause, or remove). |

## Budgets (4)

| Tool | Risk | Gated when | What it does |
|---|:---:|---|---|
| `list_budgets` | 🟢 | — | List campaign budgets in the account. |
| `create_budget` | 🔴 | always | Create a new campaign budget. |
| `update_budget` | 🔴 | amount or delivery change | Update an existing campaign budget. |
| `get_budget_utilization` | 🟢 | — | Get budget vs actual spend for campaigns. |

## Ads (7)

| Tool | Risk | Gated when | What it does |
|---|:---:|---|---|
| `list_ads` | 🟢 | — | List ads in an ad group with approval status. |
| `create_responsive_search_ad` | 🔴 | ENABLED | Create a Responsive Search Ad (RSA) for Search campaigns. |
| `create_responsive_display_ad` | 🔴 | ENABLED | Create a Responsive Display Ad for Display campaigns. |
| `create_video_ad` | 🔴 | ENABLED | Create a Video ad for Video campaigns (YouTube). |
| `create_demand_gen_ad` | 🔴 | ENABLED | Create a Demand Gen ad (serves on YouTube, Gmail, Discover). |
| `set_ad_status` | 🔴 | ENABLED or REMOVED | Set an ad's status (enable, pause, or remove). |
| `get_ad_details` | 🟢 | — | Get full details of an ad (headlines, descriptions, URLs, assets). |

## Keywords (5)

| Tool | Risk | Gated when | What it does |
|---|:---:|---|---|
| `list_keywords` | 🟢 | — | List keywords in an ad group. |
| `add_keywords` | 🔴 | always | Add keywords to an ad group (batch operation). |
| `remove_keyword` | 🔴 | always | Remove a keyword from an ad group. |
| `update_keyword_bid` | 🔴 | always | Update the CPC bid for a keyword. |
| `get_keyword_performance` | 🟢 | — | Get keyword performance metrics for an ad group. |

## Performance Max (8)

| Tool | Risk | Gated when | What it does |
|---|:---:|---|---|
| `create_performance_max_campaign` | 🔴 | always | Create a complete Performance Max campaign with budget, campaign, and asset group. |
| `list_asset_groups` | 🟢 | — | List asset groups in a Performance Max campaign. |
| `get_asset_group_details` | 🟢 | — | Get full details of an asset group including linked assets and signals. |
| `add_assets_to_group` | 🟡 | — | Add assets to an existing asset group (batch link operation). |
| `remove_asset_from_group` | 🔴 | always | Remove an asset from an asset group. |
| `add_audience_signal` | 🟡 | — | Add audience or search theme signals to a PMax asset group. |
| `get_asset_performance` | 🟢 | — | Get asset-level performance labels (BEST, GOOD, LOW, etc.) for PMax. |
| `get_pmax_placement_performance` | 🟢 | — | Get PMax placement performance breakdown (Search, YouTube, Display, Discover, Gmail). |

## Reporting (6)

| Tool | Risk | Gated when | What it does |
|---|:---:|---|---|
| `execute_gaql` | 🟢 | — | Execute an arbitrary GAQL (Google Ads Query Language) query. |
| `get_campaign_performance` | 🟢 | — | Get campaign performance metrics over a date range. |
| `get_ad_group_performance` | 🟢 | — | Get ad group performance metrics. |
| `get_search_terms_report` | 🟢 | — | Get search terms that triggered your ads. |
| `get_keyword_performance_report` | 🟢 | — | Get keyword-level performance metrics. |
| `get_account_performance_summary` | 🟢 | — | Get account-level daily performance summary. |

## Utilities (3)

| Tool | Risk | Gated when | What it does |
|---|:---:|---|---|
| `list_gaql_resources` | 🟢 | — | List available GAQL FROM-clause resources for use with execute_gaql. |
| `get_field_metadata` | 🟢 | — | Get selectable, filterable, and sortable fields for a GAQL resource. |
| `convert_micros` | 🟢 | — | Convert between micros and currency amounts. |
