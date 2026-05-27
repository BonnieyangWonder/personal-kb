# Sync Jira Ticket to Confluence

Compare a Jira ticket with an existing Confluence page (and its child pages), identify what needs updating, present a before/after diff for review, and update only after user confirmation.

## Input

- **Jira ticket link** (e.g., `https://wonder.atlassian.net/browse/MD-17984`)
- **Confluence page link** (e.g., `https://wonder.atlassian.net/wiki/spaces/MD/pages/123456789/Page+Title`)

## Language Rule (HARD REQUIREMENT)

**All content written to Confluence MUST be in English.** This applies to:
- Page titles
- Page body content
- Version comments
- Any labels or metadata

When the Jira ticket description contains Chinese or other non-English content, translate it to English before writing to Confluence. Preserve the original meaning accurately.

## Execution Steps

### Phase 1: Fetch Source (Jira)

1. Extract the ticket key from the Jira link
2. Fetch the full Jira ticket via MCP `jira_get_issue` with all fields:
   - Basic info: summary, status, priority, issuetype, assignee, reporter, created, updated
   - Description (full ADF content)
   - Subtasks list
   - Parent Epic
   - Issue links
   - Comments
   - Attachments (list, not download)

### Phase 2: Fetch Target (Confluence)

1. Extract the page ID from the Confluence link
2. Fetch the target page via MCP `confluence_get_page`
3. Fetch ALL child pages via MCP `confluence_get_page_children` (with `include_content: true`)
4. Build a complete content map: `{page_title: {content, page_id, parent_id}}` for the target page and every descendant

### Phase 3: Compare & Identify Changes

Compare Jira ticket content against the full Confluence page tree. Check for:

| Aspect | What to check |
|--------|---------------|
| **Status** | Has the Jira status changed? Is the Confluence page reflecting the current status? |
| **Description** | Has the Jira description been updated? Are there new sections, changed requirements, updated AC? |
| **Subtasks** | New subtasks added? Existing ones completed? Status changes? |
| **Comments** | New comments on Jira that contain important context not yet in Confluence? |
| **Assignee/Reporter** | Personnel changes? |
| **Epic/ Links** | New parent Epic? New linked issues? |
| **Attachments** | New screenshots or files on Jira not in Confluence? |
| **Child pages** | Do child pages cover content that's now in the Jira description? Are they outdated? |

For each change identified:
- Note WHICH page(s) need updating (target page or specific child page)
- Capture the BEFORE content (current Confluence content)
- Draft the AFTER content (what it should become)

### Phase 4: Present Diff for Review

Present findings in this format:

```
## 📋 Sync Review: MD-XXXXX → Confluence

### Pages Examined
- Target: [Page Title] (page_id) — last updated YYYY-MM-DD
- Child: [Child Page Title] (page_id)
- Child: [Another Child] (page_id)
- ... (all child pages)

### Changes Identified: N changes across M pages

---

### Change 1: [Page Title] — Update Status
**Before:**
> Status: To Do

**After:**
> Status: In Progress

---

### Change 2: [Child Page Title] — Add New Acceptance Criteria
**Before:**
> (current content or "section does not exist")

**After:**
> (proposed new content in English)

---

### No Changes Needed
- [Page/Child Title] — content is up to date
- ...

---

### Summary
- X pages to update
- Y new child pages to create
- Z pages unchanged
```

**Wait for user confirmation before proceeding to Phase 5.**

### Phase 5: Apply Updates (after confirmation)

For each confirmed change:

1. **Update existing page** → MCP `confluence_update_page` with the new content
2. **Create new child page** → MCP `confluence_create_page` under the target parent
3. **Upload attachments** → MCP `confluence_upload_attachment` (if new Jira attachments found)
4. Each update should have a version comment like: `Synced from Jira MD-XXXXX — status update`

### Phase 6: Report Completion

```
## ✅ Sync Complete

- Updated: [Page Title] (link) — status changed, description updated
- Created: [New Child Page] (link) — new section extracted
- Unchanged: [list pages that were already up to date]
```

## Inaccessible Resources (CRITICAL)

**If ANY step fails due to an inaccessible resource, you MUST explicitly report it to the user.** Do not proceed silently with partial data.

| Failure | Required Action |
|---------|-----------------|
| Jira ticket not found (404) | Report: `⚠ Jira ticket <KEY> not found — verify the ticket link.` |
| Confluence page not found (404) | Report: `⚠ Confluence page not found — verify the page link.` |
| Confluence child pages fetch error | Report: `⚠ Cannot fetch child pages of <page title> — <reason>.` |
| Jira ticket auth error (401/403) | Report: `⚠ Cannot access Jira ticket <KEY> — authentication failed.` |
| Confluence create/update fails | Report: `⚠ Failed to update Confluence page <title> — <error details>.` |

Format the warning clearly:
```
⚠ Sync encountered inaccessible resources:
- Jira ticket MD-XXXXX — 404 not found
- Child pages of "Design Doc" — permission error

Sync halted. Please verify the links and retry.
```

This is a hard requirement — never suppress or skip these notifications.

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

## Auth Strategy

MCP tools are the preferred path (configured in `.claude/mcp.json`):

- `mcp__atlassian__jira_get_issue` — fetch Jira ticket
- `mcp__atlassian__confluence_get_page` — fetch target page
- `mcp__atlassian__confluence_get_page_children` — fetch all child pages
- `mcp__atlassian__confluence_update_page` — update existing page
- `mcp__atlassian__confluence_create_page` — create new child page

### Fallback: REST API + Cached OAuth Token

If MCP tools for Jira are unavailable:

```bash
TOKEN_FILE=$(find ~/.mcp-auth -name "8d8bab2a93ad41172215aecfb4b6d869_tokens.json" 2>/dev/null | head -1)
TOKEN=$(python3 -c "import json; print(json.load(open('$TOKEN_FILE'))['access_token'])")
CLOUD_ID="70497edc-9c59-45b2-8e47-e46913d4c6cf"
API="https://api.atlassian.com/ex/jira/${CLOUD_ID}/rest/api/3"

# Fetch issue
curl -s -H "Authorization: Bearer $TOKEN" "${API}/issue/MD-17984"
```

## MCP Architecture Note

Two config sources exist; one can shadow the other:

| File | Config Name | Method | OAuth Scope | Jira Write |
|------|------------|--------|-------------|------------|
| `~/.claude/settings.json` | Atlassian-Rovo-MCP | mcp-remote + authv2 | Full | ✅ |
| `~/.claude.json` | atlassian | HTTP direct | Confluence only | ❌ |

Confluence operations (create/update page) are available in both modes. Jira read for ticket fetching may need the REST API fallback if in HTTP-only mode.
