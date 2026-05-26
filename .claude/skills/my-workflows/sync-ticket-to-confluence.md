# Sync Jira Ticket to Confluence

Sync a Jira ticket's full content into a Confluence page. Used for documentation, design reviews, and stakeholder visibility.

## Input

- Jira ticket key (e.g., MD-17984)
- Target Confluence space key
- Target page title (optional; defaults to Jira summary)

## Output

Creates or updates a Confluence page containing:

1. **Ticket Basic Info**
   - Key, title, type, status, priority
   - Reporter, assignee
   - Created / updated timestamps

2. **Description**
   - Full description (preserving formatting)
   - Sub-task list

3. **Technical Details** (auto-extracted)
   - Context / background
   - Implementation plan
   - Dependencies
   - Scope boundaries (in / out of scope)

4. **Related Info**
   - Parent Epic
   - Linked subtasks
   - Related PRs / builds (if available)

## Execution Steps

1. Fetch Jira ticket from REST API (reuse auth from [[create-jira-ticket]])
2. Convert content to Confluence storage format
3. Check if target Confluence page exists (MCP `getConfluencePage`)
   - Exists → MCP `updateConfluencePage`
   - Doesn't exist → MCP `createConfluencePage`
4. Include relevant attachments / screenshots from Jira

### Inaccessible Resources (CRITICAL)

**If ANY step fails due to an inaccessible resource, you MUST explicitly report it to the user.** Do not proceed silently with partial data.

Failure scenarios and required responses:

| Failure | Required Action |
|---------|-----------------|
| Jira ticket not found (404) | Report: `⚠ Jira ticket <KEY> not found — verify the ticket key.` |
| Jira ticket auth error (401/403) | Report: `⚠ Cannot access Jira ticket <KEY> — authentication failed.` |
| Confluence page fetch error (not "page doesn't exist") | Report: `⚠ Cannot check Confluence page — <reason>.` |
| Confluence create/update fails | Report: `⚠ Failed to sync to Confluence — <error details>.` |
| MCP tools unavailable for Confluence | Report: `⚠ Confluence MCP tools not available — cannot create/update page.` |
| Attachments fail to transfer | Report: `⚠ Could not transfer attachments: <list of failed files>.` |

Format the warning clearly:
```
⚠ Sync encountered inaccessible resources:
- Jira ticket MD-XXXXX — 404 not found
- Attachment screenshot.png — transfer failed

Sync completed with the following gaps: ...
```

This is a hard requirement — never suppress or skip these notifications.

## Auth Strategy (same as create-jira-ticket)

### Strategy 1: MCP Tools (preferred for Confluence)
- `mcp__atlassian__getConfluencePage` — check if page exists
- `mcp__atlassian__createConfluencePage` — create new
- `mcp__atlassian__updateConfluencePage` — update existing

### Strategy 2: REST API + Cached OAuth Token (fallback for Jira read)

For reading the Jira ticket when MCP Jira tools are unavailable:

```bash
TOKEN_FILE=$(find ~/.mcp-auth -name "8d8bab2a93ad41172215aecfb4b6d869_tokens.json" 2>/dev/null | head -1)
TOKEN=$(python3 -c "import json; print(json.load(open('$TOKEN_FILE'))['access_token'])")
CLOUD_ID="70497edc-9c59-45b2-8e47-e46913d4c6cf"
API="https://api.atlassian.com/ex/jira/${CLOUD_ID}/rest/api/3"

# Fetch issue
curl -s -H "Authorization: Bearer $TOKEN" "${API}/issue/MD-17984"
```

### Strategy 3: Basic Auth + API Token (last resort)
Requires user to provide their Atlassian API token.

## Confluence Content Format

Use wiki markup when creating via REST API, or ADF when using MCP tools.

### Wiki markup (REST API)
```
h1. Ticket: MD-17984

h2. Basic Info
||Key||MD-17984||
||Summary||Support Hot Hold configuration...||
||Type||Story||
||Status||To Do||

h2. Description
Full description text here...

h2. References
- [Related Page|https://wonder.atlassian.net/wiki/...]
```

### HTML format (MCP tools — preferred)
Use standard HTML with Confluence-specific elements. See [[atlassian-confluence]] for full syntax.

## Ticket Content Extraction

When fetching a Jira ticket via REST API, key fields to extract:

| Field | API Path | Notes |
|-------|----------|-------|
| Summary | `fields.summary` | Page title candidate |
| Description | `fields.description` | ADF format; convert to wiki/html |
| Status | `fields.status.name` | |
| Priority | `fields.priority.name` | |
| Assignee | `fields.assignee.displayName` | |
| Reporter | `fields.reporter.displayName` | |
| Created | `fields.created` | |
| Updated | `fields.updated` | |
| Epic Link | `fields.parent.key` | If story has parent epic |
| Subtasks | `fields.subtasks[].key` | List child issues |
| Issue Links | `fields.issuelinks[]` | Related PRs, blocks, etc. |

## MCP Architecture Note

Two config sources exist; one can shadow the other:

| File | Config Name | Method | OAuth Scope | Jira Write |
|------|------------|--------|-------------|------------|
| `~/.claude/settings.json` | Atlassian-Rovo-MCP | mcp-remote + authv2 | Full | ✅ |
| `~/.claude.json` | atlassian | HTTP direct | Confluence only | ❌ |

Confluence operations (create/update page) are available in both modes. Jira read for ticket fetching may need the REST API fallback if in HTTP-only mode.
