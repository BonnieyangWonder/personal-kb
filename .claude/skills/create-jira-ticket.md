# Create Jira Ticket Skill

Create a Jira issue, automatically selecting the best available auth method.

## Execution Strategy (in priority order)

### Strategy 1: MCP Tool (preferred)

If the current session has the `mcp__atlassian__createJiraIssue` tool available, call it directly.

### Strategy 2: REST API + Cached OAuth Token (fallback)

If the MCP tool is unavailable (filtered due to Confluence-only OAuth scope), use the cached OAuth token on disk to call the REST API directly:

```bash
TOKEN=$(python3 -c "import json; print(json.load(open('$HOME/.mcp-auth/mcp-remote-0.1.37/8d8bab2a93ad41172215aecfb4b6d869_tokens.json'))['access_token'])")
CLOUD_ID="70497edc-9c59-45b2-8e47-e46913d4c6cf"
API="https://api.atlassian.com/ex/jira/${CLOUD_ID}/rest/api/3"

curl -s -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  "${API}/issue" \
  -d '{
    "fields": {
      "project": {"id": "PROJECT_ID"},
      "issuetype": {"id": "ISSUETYPE_ID"},
      "summary": "SUMMARY",
      "description": {"type":"doc","version":1,"content":[...]}
    }
  }'
```

Token location: `~/.mcp-auth/mcp-remote-{version}/{hash}_tokens.json`

The hash is `MD5(https://mcp.atlassian.com/v1/mcp/authv2)` = `8d8bab2a93ad41172215aecfb4b6d869` (stable as long as the auth URL doesn't change). The version directory changes when mcp-remote updates.

To find the token reliably, use:
```bash
TOKEN_FILE=$(find ~/.mcp-auth -name "8d8bab2a93ad41172215aecfb4b6d869_tokens.json" 2>/dev/null | head -1)
TOKEN=$(python3 -c "import json; print(json.load(open('$TOKEN_FILE'))['access_token'])")
```

### Strategy 3: Basic Auth + API Token (last resort)

If the OAuth token is also unavailable, fall back to Basic Auth. Requires the user to provide their Atlassian API token.

## Project Mapping

| Project Key | ID | Name |
|-------------|------|------|
| MD | 10024 | MasterData |
| MDD | 10533 | Cookbook Product Board |

## Issue Type Mapping (shared across MD/MDD)

| Type | ID |
|------|-----|
| Story | 10004 |
| Task | 10001 |
| Bug | 10023 |
| Epic | 10000 |
| Sub-task | 10002 |

## Description Format (ADF)

Jira REST API v3 requires Atlassian Document Format. Basic paragraph:

```json
{
  "type": "doc",
  "version": 1,
  "content": [
    {
      "type": "paragraph",
      "content": [{"type": "text", "text": "text here"}]
    }
  ]
}
```

Use `"marks": [{"type": "strong"}]` for bold text.

## Troubleshooting

### Token Expired
- Access token lifetime: 1 hour
- Refresh token lifetime: 90 days, auto-rotates on each use
- If both access and refresh tokens are expired, re-run OAuth:
  ```
  npx -y mcp-remote@latest https://mcp.atlassian.com/v1/mcp/authv2
  ```
  Then complete authorization in the browser.

### MCP Tools Filtered
- HTTP-mode MCP connection only has Confluence scope → use Strategy 2 (REST API)
- Ensure `~/.claude.json` does NOT contain a `type: "http"` atlassian config
- The correct mcp-remote config lives in `~/.claude/settings.json`

### MD Project Returns 404
- The REST API requires authentication to list projects
- Unauthenticated requests return "No project could be found"

## MCP Architecture

Two config sources exist; one can shadow the other:

| File | Config Name | Method | OAuth Scope | Jira Write |
|------|------------|--------|-------------|------------|
| `~/.claude/settings.json` | Atlassian-Rovo-MCP | mcp-remote + authv2 | Full | ✅ |
| `~/.claude.json` | atlassian | HTTP direct | Confluence only | ❌ |

**Important**: `~/.claude.json` config can shadow the global `settings.json` entry with the same key. Always ensure the atlassian MCP uses only the mcp-remote method, with no leftover HTTP-mode config.
