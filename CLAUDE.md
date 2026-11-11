# Claude notes

This repository is a **client-neutral Google Ads MCP server**.

- Canonical Python package: `src/google_ads_mcp/`
- Claude plugin metadata only: `google-ads-manager/`
- Prefer `uv run google-ads-mcp` from the repo root
- Client guides: `docs/clients/`

Do not reintroduce a second copy of the Python package under `google-ads-manager/`.

## Safety rules for code changes

- Any new tool that can start spend, raise spend, enable something or remove something must take
  `confirm: bool = False`, call `require_confirmation(...)` from `google_ads_mcp/safety.py` before
  any API call, run the relevant spend-limit checks first, and be added to `GATED_TOOLS`.
- Pausing must never be gated.
- `tests/test_safety.py` fails if a tool exposes `confirm` but is missing from `GATED_TOOLS` (or the reverse).
- Credit contributors as Claude and Cursor. Keep `LICENSE` and `NOTICE` (Apache-2.0 attribution).
