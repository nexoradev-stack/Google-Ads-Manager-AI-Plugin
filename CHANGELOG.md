# Changelog

All notable changes to this project are documented here. Versions follow [Semantic Versioning](https://semver.org/).

## 1.0.0 — 2026-11-11

First release of **Google Ads Manager AI Plugin**, derived from Neelkant Ekbote's Apache-2.0
licensed `google-ads-claude-plugin` 0.2.0 (see `NOTICE`).

### Added

- **Preview-and-confirm safety gate** (`safety.py`) on 19 tools that can start spend, raise spend
  or remove something. The first call returns a structured preview (summary, current state,
  requested changes, financial impact, reversibility) and changes nothing; the change runs only
  when the tool is called again with `confirm=true`. Pausing is never gated.
- **Spend limits** enforced even after confirmation: `GOOGLE_ADS_MAX_DAILY_BUDGET`,
  `GOOGLE_ADS_MAX_BUDGET_INCREASE_PCT`, `GOOGLE_ADS_MAX_CPC_BID`.
- **Budget previews** show current vs new daily amount and the monthly difference.
- **Remote transport protection** (`http_security.py`): bearer-token login with constant-time
  comparison, per-IP rate limiting with idle-key eviction, configurable allowed hosts
  (`MCP_ALLOWED_HOSTS`), and a `/health` endpoint that never returns secrets.
- Server refuses to listen on a non-local address without `MCP_HTTP_BEARER_TOKEN`
  (override only with `MCP_ALLOW_UNAUTHENTICATED=true` behind an authenticating proxy).
- Server instructions tell AI clients to show the preview and ask before confirming.
- 100 new tests: every gated tool is checked to make no API call without `confirm` and to call
  the API with it; spend limits; HTTP login, rate limits, host checks and `/health` against the real app.
- `NOTICE`, `CHANGELOG.md`, `ARCHITECTURE.md`, banner and architecture images, generated
  `docs/tools.md` with risk levels.

### Changed

- Removal tools accept `confirm=true`; the older `confirm_removal=True` still works.
- Docker health check calls `/health`; Docker Compose requires `MCP_HTTP_BEARER_TOKEN`.
- Package renamed to `google-ads-manager-ai-plugin` (CLI is still `google-ads-mcp`, import is still `google_ads_mcp`).
- Claude skill updated with the confirmation workflow.

### Fixed

- `set_campaign_status(status="REMOVED")` no longer bypasses the removal confirmation that
  `remove_campaign` required.
- Loopback `Host` headers without a port (`localhost`) are accepted by the host check.
