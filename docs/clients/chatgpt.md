# ChatGPT / OpenAI

## Important: local vs remote MCP

ChatGPT **does not** launch local stdio MCP processes directly.

Supported options:

1. **Remote MCP** — expose this server over HTTPS with Streamable HTTP (or SSE)
2. **Secure MCP Tunnel** — keep the server private and connect through OpenAI's tunnel

The Google Ads implementation stays the same. Only the transport/deployment changes.

## Run the server for remote clients

```bash
export MCP_HTTP_BEARER_TOKEN="$(openssl rand -hex 32)"   # required on a public address
export MCP_ALLOWED_HOSTS=ads-mcp.example.com            # your public domain
uv run google-ads-mcp --transport streamable-http --host 0.0.0.0 --port 8000
```

The server refuses to start on `0.0.0.0` without `MCP_HTTP_BEARER_TOKEN`.

Or with Docker:

```bash
export GOOGLE_ADS_SERVICE_ACCOUNT_HOST_PATH=/path/to/service-account.json
export GOOGLE_ADS_DEVELOPER_TOKEN=...
export MCP_HTTP_BEARER_TOKEN="$(openssl rand -hex 32)"
export MCP_ALLOWED_HOSTS=ads-mcp.example.com
docker compose up
```

Check it is up: `curl https://ads-mcp.example.com/health`

Put TLS termination in front of the container (reverse proxy / platform ingress). The MCP path defaults to `/mcp`.

## ChatGPT developer mode

1. Enable Developer Mode in ChatGPT workspace settings (admin may be required)
2. Create a custom MCP connector / app
3. Point it at `https://YOUR_PUBLIC_HOST/mcp` and set the header `Authorization: Bearer <MCP_HTTP_BEARER_TOKEN>`
4. Scan tools and test before publishing

See `clients/chatgpt/remote-mcp.example.json` for metadata examples.

## OpenAI Responses API

```json
{
  "type": "mcp",
  "server_url": "https://YOUR_PUBLIC_HOST/mcp",
  "headers": { "Authorization": "Bearer YOUR_MCP_HTTP_BEARER_TOKEN" },
  "require_approval": "always"
}
```

For private networks, use Secure MCP Tunnel (`tunnel_id`) instead of a public URL.

## Security

- The server itself returns a preview and needs `confirm=true` for 19 spend, launch and removal tools
- Also require approval for write/destructive tools in ChatGPT for a second layer
- Do not embed Google Ads credentials in ChatGPT connector JSON
- Prefer private networking or tunnel for production

## Verify

After connecting, ask ChatGPT to list accessible Google Ads accounts (read-only first).
