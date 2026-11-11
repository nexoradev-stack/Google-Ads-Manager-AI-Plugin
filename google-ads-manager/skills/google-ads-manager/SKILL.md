# Google Ads Manager

Manage Google Ads accounts through the universal Google Ads MCP server
(`google-ads-mcp` in the repository root). The same server works with Cursor,
Claude, Gemini CLI, ChatGPT (remote MCP), and other MCP clients.

## Capabilities

- Review Google Ads accounts and MCC hierarchies
- Create and manage campaigns
- Manage Search, Display, Video, Demand Gen, and Performance Max campaigns
- Create Responsive Search Ads
- Create Responsive Display Ads
- Manage ad groups
- Add, update, and remove keywords
- Manage campaign budgets
- Analyze campaign, ad group, ad, and keyword performance
- Run GAQL reporting queries
- Review targeting and campaign configuration
- Identify underperforming campaigns and ads
- Support campaign optimization workflows

## Safety

The server has a built-in safety gate. Any tool that can start spend, raise spend or remove
something (19 tools: budgets, campaign/ad group/ad creation and enabling, keyword adds and bids,
Performance Max creation, removals) does **not** change anything on the first call. It returns:

```json
{"success": false, "confirmation_required": true, "preview": {"summary": "...", "current_state": {}, "requested_changes": {}, "financial_impact": "...", "reversible": true}}
```

Rules for this skill:

1. Show the user the preview in plain language: what changes, from what to what, the money impact and whether it can be undone.
2. Only call the same tool again with `confirm=true` after the user explicitly says yes. Never set `confirm=true` on the first call.
3. Pausing is never gated. If a user asks to stop spend, pause immediately.
4. If a result contains `blocked_by_spend_limit`, tell the user which limit was hit. Do not retry with smaller steps to get around it.

Do not expose API credentials, service account private keys, access tokens, or `.env` contents.

Never commit credentials or secrets to the repository.

## Ad Creation

When creating ads, collect the required information before executing the operation.

### Responsive Search Ads

Support:

- Headlines
- Descriptions
- Final URL
- Display URL paths where applicable

### Responsive Display Ads

Support:

- Headlines
- Long headline
- Descriptions
- Business name
- Marketing images
- Logos
- Final URL
- Required display assets

Always validate required assets and fields before attempting to create an ad.

## Reporting

Use the reporting tools to answer questions about:

- Spend
- Impressions
- Clicks
- CTR
- CPC
- Conversions
- Conversion value
- ROAS
- Campaign performance
- Ad group performance
- Keyword performance
- Ad performance

Prefer the most specific reporting tool available before falling back to a custom GAQL query.

## Campaign Changes

Before making significant campaign changes, summarize:

- Campaign
- Current state
- Requested change
- Expected impact

For budget increases, campaign launches, and other potentially costly actions, obtain explicit confirmation before execution.

## Natural Language Examples

Users can ask:

- "Show me my Google Ads campaigns."
- "How did my campaigns perform this week?"
- "Create a Search campaign."
- "Create a responsive search ad."
- "Create a responsive display ad."
- "Pause this campaign."
- "Increase this campaign's budget."
- "Show me my highest-spending campaigns."
- "Find underperforming keywords."
- "Run a Google Ads performance report."
