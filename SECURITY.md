# Security

## Reporting a vulnerability

Please **do not open a public issue** for a vulnerability, especially one that could expose
credentials or let someone change an ad account. Use GitHub's
[private vulnerability reporting](https://github.com/nexoradev-stack/google-ads-manager-ai-plugin/security/advisories/new)
for this repository. You should get a first reply within 7 days.

## What the server can and cannot do

- It can read and change campaigns, ad groups, ads, keywords, budgets and Performance Max assets
  in accounts the service account can access.
- It **cannot** change billing, user access, account permissions or credentials.
- `execute_gaql` is read-only, but it can read sensitive resources such as `customer_user_access`.

## Built-in safeguards

| Safeguard | Where | What it does |
|---|---|---|
| Confirmation gate | `safety.py` | 19 tools that can start spend, raise spend or remove something return a preview first and only run with `confirm=true`. Pausing is never gated. |
| Spend limits | `safety.py` | `GOOGLE_ADS_MAX_DAILY_BUDGET`, `GOOGLE_ADS_MAX_BUDGET_INCREASE_PCT`, `GOOGLE_ADS_MAX_CPC_BID` refuse requests even when confirmed. |
| Bearer login | `http_security.py` | `MCP_HTTP_BEARER_TOKEN`, compared in constant time. Required to listen on a non-local address. |
| Rate limit | `http_security.py` | `MCP_RATE_LIMIT_MAX` per `MCP_RATE_LIMIT_WINDOW_SECONDS` per client IP (default 120/60 s). |
| Allowed hosts | `http_security.py` | `MCP_ALLOWED_HOSTS` blocks DNS-rebinding requests with an unexpected `Host` header. |
| Health without secrets | `server.py` | `/health` reports only whether credentials are set, never their values. |

## Credentials

- Load credentials from environment variables, a local `.env`, or mounted secrets.
- Never commit `.env`, service-account JSON, developer tokens, bearer tokens or keys.
- Docker images receive credentials at runtime (env + read-only bind mount); none are baked in.
- Logs may include file paths but never credential values.

## Running remotely

- Prefer local **stdio** for Claude Desktop, Cursor and Gemini CLI.
- For remote clients (ChatGPT), put TLS in front, set `MCP_HTTP_BEARER_TOKEN` and `MCP_ALLOWED_HOSTS`,
  and keep client-side approval for write tools turned on as a second layer.
- `MCP_ALLOW_UNAUTHENTICATED=true` exists only for deployments behind a proxy that already
  authenticates users. Do not use it on an open port.

## Ignored secret patterns

`.gitignore` excludes `.env`, `.env.local`, `service-account*.json`, `google-ads.yaml`, `*.pem` and `*.key`.
