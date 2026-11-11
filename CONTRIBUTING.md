# Contributing

Thanks for helping improve Google Ads Manager AI Plugin.

## Setup

```bash
git clone https://github.com/nexoradev-stack/google-ads-manager-ai-plugin.git
cd google-ads-manager-ai-plugin
uv sync --all-groups
```

## Run the checks

```bash
uv run pytest -q              # all tests mock the Google Ads API
uv run google-ads-mcp --help  # entry point still works
docker build -t google-ads-manager-ai-plugin:dev .
```

Never add tests that need real Google Ads credentials.

## Where code goes

| Path | What lives there |
|---|---|
| `src/google_ads_mcp/tools/` | Tool definitions, one file per area |
| `src/google_ads_mcp/safety.py` | Confirmation gate and spend limits |
| `src/google_ads_mcp/http_security.py` | Bearer login, rate limit, allowed hosts for HTTP transports |
| `clients/`, `docs/clients/` | Client launch configs and guides (no Google Ads logic) |
| `google-ads-manager/` | Claude plugin metadata, command and skill only |

## Rules for new or changed tools

1. Keep existing tool names stable.
2. If a tool can **start spend, raise spend, enable something or remove something**:
   - add `confirm: bool = False`;
   - run the relevant spend-limit checks (`check_daily_budget`, `check_budget_increase`, `check_cpc_bid`) first;
   - call `require_confirmation(...)` before any API call, with a clear `financial_impact`;
   - add the tool name to `GATED_TOOLS`;
   - add cases to `tests/test_tools/test_gated_tools.py`.
3. Never gate pausing. Stopping spend must always be instant.
4. Give every tool the right annotation in `annotations.py` and update `tests/test_annotations.py`.

## Pull requests

1. Branch from `main` (`feat/…`, `fix/…`, `docs/…`).
2. All tests pass and no secrets are committed (`.env`, service-account JSON, tokens).
3. Update `README.md`, `docs/tools.md` and `CHANGELOG.md` when behaviour changes.

## Credits

Contributors to this project are **Claude** and **Cursor**. The project is derived from
Neelkant Ekbote's Apache-2.0 licensed `google-ads-claude-plugin`; keep `LICENSE` and `NOTICE` intact.
