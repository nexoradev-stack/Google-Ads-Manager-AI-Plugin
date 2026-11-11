<p align="center">
  <img src="assets/banner.png" alt="Google Ads Manager AI Plugin — manage Google Ads from Claude, ChatGPT, Gemini and Cursor, with a preview before anything spends money" width="100%">
</p>

<h1 align="center">Google Ads Manager AI Plugin</h1>

<p align="center">
  <b>Run your Google Ads account by chatting with the AI tool you already use.</b><br>
  47 tools for campaigns, ads, keywords, Performance Max, budgets and reporting —<br>
  and a built-in safety check that shows you the cost before anything goes live.
</p>

<p align="center">
  <img alt="Version" src="https://img.shields.io/badge/version-1.0.0-34D399?style=flat-square">
  <img alt="License" src="https://img.shields.io/badge/license-Apache--2.0-0F2A1F?style=flat-square">
  <img alt="Python" src="https://img.shields.io/badge/python-3.12%20%7C%203.13-3776AB?style=flat-square&logo=python&logoColor=white">
  <img alt="MCP" src="https://img.shields.io/badge/MCP-stdio%20%7C%20HTTP%20%7C%20SSE-34D399?style=flat-square">
  <img alt="Tools" src="https://img.shields.io/badge/tools-47-FBBF24?style=flat-square">
  <img alt="Tests" src="https://img.shields.io/badge/tests-253%20passing-2EA44F?style=flat-square">
  <a href="https://github.com/nexoradev-stack/google-ads-manager-ai-plugin/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/nexoradev-stack/google-ads-manager-ai-plugin/actions/workflows/ci.yml/badge.svg"></a>
</p>

<p align="center">
  <a href="#-quick-start">Quick start</a> ·
  <a href="#-what-you-can-ask-it">Examples</a> ·
  <a href="#-the-safety-check">Safety check</a> ·
  <a href="#-tools">Tools</a> ·
  <a href="ARCHITECTURE.md">Architecture</a> ·
  <a href="#-contributors">Contributors</a>
</p>

---

## 📌 Contents

1. [Why this exists](#-why-this-exists)
2. [Features](#-features)
3. [The safety check](#-the-safety-check)
4. [How it works](#-how-it-works)
5. [What you can ask it](#-what-you-can-ask-it)
6. [Quick start](#-quick-start)
7. [Google Ads credentials](#-google-ads-credentials)
8. [Connect your AI client](#-connect-your-ai-client)
9. [Configuration reference](#%EF%B8%8F-configuration-reference)
10. [Tools](#-tools)
11. [Running it remotely](#-running-it-remotely)
12. [Security](#-security)
13. [Project structure](#-project-structure)
14. [Development](#-development)
15. [Troubleshooting](#-troubleshooting)
16. [Contributing](#-contributing)
17. [Contributors](#-contributors)
18. [License and attribution](#-license-and-attribution)

---

## 💡 Why this exists

Google Ads gives you a lot of power and a lot of screens. Checking last week's spend, finding wasted keywords, or setting up a Performance Max campaign can take many clicks — and a single typo in a budget can cost real money.

This project is a **Model Context Protocol (MCP) server**: a small service that gives AI assistants a safe, well-defined set of Google Ads actions. You ask in plain language; the assistant uses the right tool; and **anything that could spend money shows you a preview first and waits for your OK.**

| Without this | With this |
|---|---|
| Build reports by hand in the Ads UI | *"Which campaigns spent the most last 30 days, and what was their ROAS?"* |
| Hunt through search terms | *"Show search terms with spend but no conversions this month"* |
| Hope nobody mistypes a budget | Budget changes show **$50 → $75/day, ≈ +$760/month** and need your approval |
| Trust every AI client to ask first | The **server itself** refuses to apply risky changes without `confirm=true` |

---

## ✨ Features

| | Feature | Details |
|---|---|---|
| 📊 | **Reporting** | Campaign, ad group, keyword and search-term reports; account summaries; any read-only GAQL query |
| 🚀 | **Campaigns** | Search, Display, Video, Demand Gen and Shopping — created **PAUSED** by default |
| ⚡ | **Performance Max** | Full PMax setup in one call: budget, campaign, asset group, assets, audience signals |
| ✍️ | **Ads** | Responsive search, responsive display, video and Demand Gen ads |
| 🔑 | **Keywords** | Add, remove, re-bid and analyse keywords |
| 💰 | **Budgets** | Create, change and check budget use |
| 🏢 | **Accounts** | Accessible accounts and full MCC (manager) hierarchy |
| 🛡️ | **Safety check** | Preview + `confirm=true` on 19 spend, launch and removal tools |
| 🚧 | **Spend limits** | Optional hard caps on daily budget, % increase and CPC — enforced even after confirmation |
| 🔐 | **Remote security** | Bearer login, rate limiting, allowed hosts, secret-free `/health` |
| 🐳 | **Docker** | Non-root image, credentials mounted at runtime, health check |
| 🧩 | **Claude plugin** | `/google-ads-setup` command and a `google-ads-manager` skill that follows the safety workflow |

---

## 🛡️ The safety check

Every tool that can **start spend, raise spend, turn something on, or remove something** works in two steps:

```mermaid
sequenceDiagram
    participant You
    participant AI as AI client
    participant S as MCP server
    participant G as Google Ads
    You->>AI: "Raise the Brand campaign budget to $75/day"
    AI->>S: update_budget(budget_id=…, amount=75)
    S->>G: read current budget ($50)
    S-->>AI: confirmation_required + preview<br/>$50 → $75 (+$25/day, ≈ +$760/month)<br/>nothing changed
    AI-->>You: shows the preview, asks to approve
    You->>AI: "Yes"
    AI->>S: update_budget(…, confirm=true)
    S->>G: apply change
    S-->>AI: success
```

**What a preview looks like**

```json
{
  "success": false,
  "confirmation_required": true,
  "message": "Confirmation required. Nothing has been changed yet. …",
  "preview": {
    "tool": "update_budget",
    "summary": "Update budget 1234567",
    "current_state": { "daily_amount": 50.0 },
    "requested_changes": { "daily_amount": 75.0 },
    "financial_impact": "Daily budget changes from 50.00 to 75.00 (+25.00/day, about +760.00/month).",
    "reversible": true,
    "spend_limits": { "max_daily_budget": 500.0, "max_budget_increase_pct": 50.0, "max_cpc_bid": null }
  }
}
```

**The rules**

| Action | What happens |
|---|---|
| Reading, reporting, GAQL | Runs instantly |
| **Pausing** anything | Runs instantly — stopping spend is never delayed |
| Renaming | Runs instantly |
| Budgets, bids, creating or enabling campaigns / ad groups / ads, adding keywords, PMax creation | **Preview first**, then `confirm=true` |
| Removing campaigns, ad groups, ads, keywords or PMax assets | **Preview first** (marked *not reversible*), then `confirm=true` |
| Anything above a configured spend limit | **Refused**, even with `confirm=true` |

Spend limits are optional environment variables — see [Configuration](#%EF%B8%8F-configuration-reference). They catch the "extra zero" mistake no matter who or what confirmed it.

---

## 🧭 How it works

<p align="center">
  <img src="assets/architecture.png" alt="Architecture: AI clients connect over stdio or HTTP to one MCP server; spend limits and a confirmation gate sit in front of the Google Ads API" width="100%">
</p>

One Python server in [`src/google_ads_mcp/`](src/google_ads_mcp/) serves every AI client. Folders under `clients/` and `docs/clients/` only explain how to launch or connect it. The full design is in **[ARCHITECTURE.md](ARCHITECTURE.md)**.

---

## 💬 What you can ask it

> **Reporting**
> - "How did my campaigns perform this week compared to last week?"
> - "Which keywords spent over $100 with no conversions in the last 30 days?"
> - "Show the search terms report for the Brand campaign."
> - "What's our budget utilisation for active campaigns?"

> **Building (you'll see a preview first)**
> - "Create a paused Search campaign called *Spring Sale* with a $40/day budget."
> - "Add these 10 phrase-match keywords to ad group 12345."
> - "Write a responsive search ad for our landing page."
> - "Set up a Performance Max campaign for the new product line."

> **Changes**
> - "Pause every campaign with CPA over $80." *(runs immediately)*
> - "Raise the Brand budget by 20%." *(preview, then confirm)*
> - "Remove the old Black Friday campaign." *(preview, marked not reversible)*

---

## ⚡ Quick start

**You need:** Python 3.12+, [uv](https://docs.astral.sh/uv/) (or Docker), a Google Ads **developer token**, and a GCP **service account** with access to your Ads account ([details](#-google-ads-credentials)).

```bash
# 1. Get the code
git clone https://github.com/nexoradev-stack/google-ads-manager-ai-plugin.git
cd google-ads-manager-ai-plugin

# 2. Install
uv sync

# 3. Add credentials (never commit .env)
cp .env.example .env
#   edit: GOOGLE_ADS_DEVELOPER_TOKEN, GOOGLE_ADS_SERVICE_ACCOUNT_PATH,
#         GOOGLE_ADS_LOGIN_CUSTOMER_ID (if you use an MCC)
#   recommended: GOOGLE_ADS_MAX_DAILY_BUDGET=500

# 4. Run (local stdio — what Claude Desktop, Cursor and Gemini CLI use)
uv run google-ads-mcp
```

Then [connect your AI client](#-connect-your-ai-client) and start with a read-only question such as *"List my accessible Google Ads accounts."*

---

## 🔑 Google Ads credentials

| Variable | Required | What it is |
|---|:---:|---|
| `GOOGLE_ADS_DEVELOPER_TOKEN` | ✅ | From the API Center in your Google Ads manager account |
| `GOOGLE_ADS_SERVICE_ACCOUNT_PATH` | ✅ | Path to the service-account JSON key |
| `GOOGLE_ADS_LOGIN_CUSTOMER_ID` | MCC only | Your manager (MCC) account ID |
| `GOOGLE_ADS_CUSTOMER_ID` | | Default account when a tool call omits `customer_id` |
| `GOOGLE_ADS_IMPERSONATED_EMAIL` | Workspace only | User to impersonate with domain-wide delegation |

**Steps**

1. In Google Cloud, create a **service account**, enable the **Google Ads API**, and download its JSON key.
2. Give the service account access to your Ads account: add its email as a user in Google Ads where your account supports it, or, for Workspace-owned accounts, enable domain-wide delegation and set `GOOGLE_ADS_IMPERSONATED_EMAIL`. Google's [service account guide](https://developers.google.com/google-ads/api/docs/oauth/service-accounts) has the current options.
3. Get a **developer token** from *Tools → API Center* in your manager account.
4. Put the values in `.env`. Dashes in customer IDs are fine — they're removed automatically.

If credentials are missing or wrong, the server still starts so offline tools (`convert_micros`, `list_gaql_resources`, `get_field_metadata`) keep working, and the log explains what's missing.

---

## 🔌 Connect your AI client

| Client | Local (stdio) | Remote (HTTP) | Guide |
|---|:---:|:---:|---|
| **Claude** (Desktop, Code, plugin) | ✅ | ✅ | [docs/clients/claude.md](docs/clients/claude.md) |
| **ChatGPT** | — | ✅ *(HTTPS or Secure MCP Tunnel)* | [docs/clients/chatgpt.md](docs/clients/chatgpt.md) |
| **Gemini CLI** | ✅ | ✅ | [docs/clients/gemini.md](docs/clients/gemini.md) |
| **Cursor** | ✅ | ✅ | [docs/clients/cursor.md](docs/clients/cursor.md) |

<details>
<summary><b>Local config (Claude Desktop / Cursor / Gemini CLI)</b></summary>

```json
{
  "mcpServers": {
    "google-ads": {
      "command": "uv",
      "args": ["run", "--directory", "/ABSOLUTE/PATH/TO/google-ads-manager-ai-plugin", "google-ads-mcp"]
    }
  }
}
```

Credentials are read from the `.env` file in that folder. Ready-made files: [`clients/`](clients/).
</details>

<details>
<summary><b>Remote config</b></summary>

```json
{
  "mcpServers": {
    "google-ads": {
      "url": "https://ads-mcp.example.com/mcp",
      "headers": { "Authorization": "Bearer YOUR_MCP_HTTP_BEARER_TOKEN" }
    }
  }
}
```
</details>

<details>
<summary><b>Claude plugin</b></summary>

Add this repository as a plugin marketplace in Claude, install **google-ads-manager**, then run `/google-ads-setup`. The bundled skill tells Claude to show every preview and ask before confirming.
</details>

---

## ⚙️ Configuration reference

**Spend limits** (optional, recommended — refused even after confirmation)

| Variable | Example | Effect |
|---|---|---|
| `GOOGLE_ADS_MAX_DAILY_BUDGET` | `500` | No budget, campaign or PMax campaign above 500/day |
| `GOOGLE_ADS_MAX_BUDGET_INCREASE_PCT` | `50` | No single budget increase above +50% |
| `GOOGLE_ADS_MAX_CPC_BID` | `20` | No ad-group or keyword max-CPC bid above 20 |

**Transport and remote protection**

| Variable | Default | Effect |
|---|---|---|
| `MCP_TRANSPORT` | `stdio` | `stdio`, `streamable-http` or `sse` |
| `MCP_HOST` / `MCP_PORT` | `127.0.0.1` / `8000` | Bind address for HTTP transports (`PORT` also works) |
| `MCP_HTTP_BEARER_TOKEN` | — | Required `Authorization: Bearer …` on `/mcp`. **Mandatory** to bind a non-local address |
| `MCP_ALLOWED_HOSTS` | — | Your public domain(s), comma-separated, for `Host`-header checks |
| `MCP_RATE_LIMIT_MAX` | `120` | Requests per window per client IP |
| `MCP_RATE_LIMIT_WINDOW_SECONDS` | `60` | Rate-limit window |
| `MCP_ALLOW_UNAUTHENTICATED` | `false` | Only behind a proxy that already authenticates users |

---

## 🧰 Tools

47 tools in 9 areas. 🟢 read · 🟡 write (instant) · 🔴 gated (preview, then `confirm=true`)

| Area | Tools |
|---|---|
| **Accounts** 🟢 | `list_accessible_accounts` · `get_account_info` · `get_account_hierarchy` |
| **Campaigns** | 🟢 `list_campaigns` · `get_campaign` — 🔴 `create_campaign` · `update_campaign`* · `set_campaign_status`* · `remove_campaign` |
| **Ad groups** | 🟢 `list_ad_groups` · `get_ad_group` — 🔴 `create_ad_group`* · `update_ad_group`* · `set_ad_group_status`* |
| **Budgets** | 🟢 `list_budgets` · `get_budget_utilization` — 🔴 `create_budget` · `update_budget`* |
| **Ads** | 🟢 `list_ads` · `get_ad_details` — 🔴 `create_responsive_search_ad`* · `create_responsive_display_ad`* · `create_video_ad`* · `create_demand_gen_ad`* · `set_ad_status`* |
| **Keywords** | 🟢 `list_keywords` · `get_keyword_performance` — 🔴 `add_keywords` · `update_keyword_bid` · `remove_keyword` |
| **Performance Max** | 🟢 `list_asset_groups` · `get_asset_group_details` · `get_asset_performance` · `get_pmax_placement_performance` — 🟡 `add_assets_to_group` · `add_audience_signal` — 🔴 `create_performance_max_campaign` · `remove_asset_from_group` |
| **Reporting** 🟢 | `execute_gaql` · `get_campaign_performance` · `get_ad_group_performance` · `get_search_terms_report` · `get_keyword_performance_report` · `get_account_performance_summary` |
| **Utilities** 🟢 | `list_gaql_resources` · `get_field_metadata` · `convert_micros` |

\* Gated only for the risky case — e.g. `set_campaign_status` gates `ENABLED` and `REMOVED` but **pauses instantly**; ads and ad groups created `PAUSED` with no bids run instantly. Exact rules per tool: **[docs/tools.md](docs/tools.md)**.

---

## 🌐 Running it remotely

ChatGPT (and any hosted setup) needs the HTTP transport.

```bash
export MCP_HTTP_BEARER_TOKEN="$(openssl rand -hex 32)"
export MCP_ALLOWED_HOSTS=ads-mcp.example.com
uv run google-ads-mcp --transport streamable-http --host 0.0.0.0 --port 8000
curl http://localhost:8000/health
```

**Docker**

```bash
export GOOGLE_ADS_DEVELOPER_TOKEN=...
export GOOGLE_ADS_LOGIN_CUSTOMER_ID=...
export GOOGLE_ADS_SERVICE_ACCOUNT_HOST_PATH=/absolute/path/to/service-account.json
export MCP_HTTP_BEARER_TOKEN="$(openssl rand -hex 32)"
export MCP_ALLOWED_HOSTS=ads-mcp.example.com
docker compose up --build
```

The service-account key is bind-mounted read-only — never copied into the image. Put HTTPS in front (reverse proxy or platform ingress). The server **refuses to start** on a public address without a bearer token.

`/health` reports version, whether credentials are configured (never their values), whether login is on, and the active spend limits.

---

## 🔐 Security

- Credentials come only from environment variables, `.env` or mounted secrets, and are never logged.
- The server **cannot** change billing, user access or account permissions.
- 19 risky tools need explicit confirmation; spend limits are enforced server-side.
- Remote mode: constant-time bearer check, per-IP rate limit, `Host` allow-list, secret-free `/health`.

Report vulnerabilities privately — see **[SECURITY.md](SECURITY.md)**.

---

## 🗂️ Project structure

```text
google-ads-manager-ai-plugin/
├── src/google_ads_mcp/          # ⭐ the one MCP server
│   ├── server.py                # FastMCP app, /health, CLI, transport startup
│   ├── safety.py                # confirmation gate + spend limits
│   ├── http_security.py         # bearer login, rate limit, allowed hosts
│   ├── client.py · config.py    # Google Ads client wrapper and settings
│   ├── annotations.py           # MCP tool hints (read-only / destructive …)
│   ├── helpers.py               # GAQL, micros, responses
│   └── tools/                   # 9 files, 47 tools
├── tests/                       # 253 tests, Google Ads API fully mocked
├── google-ads-manager/          # Claude plugin: command, skill, .mcp.json
├── clients/ · docs/clients/     # per-client configs and guides
├── docs/tools.md                # full tool catalog with risk levels
├── assets/                      # banner + architecture (SVG source, PNG)
├── Dockerfile · docker-compose.yml
├── ARCHITECTURE.md · CHANGELOG.md · SECURITY.md · CONTRIBUTING.md
└── LICENSE · NOTICE
```

---

## 🛠️ Development

```bash
uv sync --all-groups
uv run pytest -q              # 253 tests, no credentials needed
uv run google-ads-mcp --help
docker build -t google-ads-manager-ai-plugin:dev .
```

CI runs the tests on Python 3.12 and 3.13 and builds the Docker image on every push and pull request.

---

## 🧯 Troubleshooting

| Symptom | Fix |
|---|---|
| `Google Ads client is not available` | Check the `GOOGLE_ADS_*` variables and that the key file path exists |
| `confirmation_required: true` | Expected — review the preview and call again with `confirm=true` |
| `blocked_by_spend_limit` | A `GOOGLE_ADS_MAX_*` limit was hit; change the request or the limit |
| `Refusing to listen on 0.0.0.0 without MCP_HTTP_BEARER_TOKEN` | Set a bearer token, or bind to `127.0.0.1` |
| `401` on `/mcp` | Send `Authorization: Bearer <token>` from the client |
| `421 Misdirected Request` | Add your domain to `MCP_ALLOWED_HOSTS` |
| `429 Rate limit exceeded` | Wait `Retry-After` seconds or raise `MCP_RATE_LIMIT_MAX` |
| ChatGPT can't use stdio | Deploy streamable-http or use a Secure MCP Tunnel |
| Client can't start the server | Use absolute paths and make sure `uv` is on `PATH` |

---

## 🤝 Contributing

See **[CONTRIBUTING.md](CONTRIBUTING.md)**. The short version: put logic in `src/google_ads_mcp/`, keep tool names stable, route any spend/launch/removal tool through the safety gate, never gate pausing, and never commit credentials.

---

## 👥 Contributors

| | Contributor | Role |
|:---:|---|---|
| 🤖 | **Claude** (Anthropic) | Safety gate, spend limits, remote security, tests, documentation, architecture |
| ⌨️ | **Cursor** | AI code editor — implementation and refactoring |

---

## 📄 License and attribution

Licensed under the **Apache License 2.0** — see [LICENSE](LICENSE).

This project is derived from [google-ads-claude-plugin](https://github.com/eneelkant/google-ads-claude-plugin) by Neelkant Ekbote (Apache-2.0). The required attribution and a summary of changes are in [NOTICE](NOTICE).

<p align="center"><sub>Not affiliated with or endorsed by Google LLC. "Google Ads" is a trademark of Google LLC.</sub></p>
