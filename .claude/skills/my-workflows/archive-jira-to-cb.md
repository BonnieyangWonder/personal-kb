# Archive Jira Ticket to CB-Full-Feature

Archive a Jira ticket's feature requirements into the Cookbook Full Features Detail Requirements documentation (`Z01-Resource/CB-full-feature/`). This is a personal workflow for Bonnie's Wonder Cookbook documentation maintenance.

## Language

**All documentation updates must be in English.** Page content, Change Log tables, new pages — everything written into CB-full-feature is English-only.

## Target Directory

**`Z01-Resource/CB-full-feature/`** — the dedicated directory for all Cookbook feature requirement pages (mirrored from Confluence space RT).

## When to Use

- User provides a Jira ticket link (e.g., MD-XXXXX) and asks to integrate its requirements into CB-full-feature
- User says "archive ticket to CB", "integrate into full feature docs", or similar

## Workflow

### Step 1: Read the Ticket

Fetch the full Jira ticket via Atlassian MCP tools (`jira_get_issue` with `fields=*all`). Capture:
- Summary, description, acceptance criteria
- All comments (especially implementation summaries and clarifications)
- Linked Confluence pages or Figma references
- **Always read the latest ticket description** — it is the authoritative source. Comments may contain outdated discussions.

### Step 2: Explore the Documentation

Thoroughly explore `Z01-Resource/CB-full-feature/`:

1. Read `README.md` for directory overview
2. Read `Cookbook Full Features Detail Requirements.md` (the summary index)
3. Use `find` or `ls -R` to enumerate all sub-directories and files
4. Read every page that could be related to the ticket's feature area
5. Pay special attention to:
   - `01 Fields & Cards in Items.md` — card/item-type matrix
   - `02Common Features/Item Validations-Missing Info.md` — validation rules
   - `02Common Features/Publish Version.md` — publish workflow
   - `02Common Features/Copy Item.md` — copy behavior
   - `02Common Features/Create new version.md` — version creation
   - `Item Details/` — all card-specific pages
   - `Item Details/Item Information/Change History.md` — change tracking
   - `Item Details/Item Information/Compare Change History.md` — comparison view

### Step 3: Analyze & Plan

Map ticket requirements to documentation pages. For each page, determine:
- **Modify existing page** — what exact content to add/change
- **Create new page** — what the page should contain
- **No change needed** — pages that are unaffected

### Step 4: Present Plan for Review (DO NOT EXECUTE YET)

Present a structured plan showing for EACH page:
- **Before** — the current content (exact excerpt)
- **After** — the proposed new content
- **Rationale** — why this change is needed

Also list pages that were analyzed but do NOT need changes (with reasons).

**Critical: Wait for user approval before making ANY edits.**

### Step 5: Execute After Approval

Only after the user explicitly approves (item by item or all at once), execute the changes.

## Editing Conventions

### Change Log Table

**Every modified page MUST have a Change Log table at the bottom** tracking the update:

```markdown
---

## Change Log

| Version | Date | Updated By | Description |
| --- | --- | --- | --- |
| 1.0 | YYYY-MM-DD | System | Initial fetch from Confluence |
| 1.1 | YYYY-MM-DD | Bonnie Yang | [MD-XXXXX](https://wonder.atlassian.net/browse/MD-XXXXX) — Brief description of what was changed. |
```

- If the page already has a Change Log, append a new row
- If the page doesn't have one, add the full table (including the initial fetch row)
- Date format: `YYYY-MM-DD`
- Ticket link must be a clickable markdown link to the Jira issue

### Page Content Rules

- **All content in English**
- **Do NOT delete pages** — only modify or create
- **Do NOT modify unrelated content** — stay focused on the ticket's scope
- **Do NOT duplicate content** across pages — if a topic is already documented in its dedicated page, use a brief cross-reference wikilink instead of repeating it
- Use `[[wikilinks]]` for internal references between CB-full-feature pages
- Preserve existing frontmatter, images, and formatting

### Section Numbering

- Insert new sections with sequential numbering
- When adding a section between existing ones, shift subsequent section numbers
- Peer-level features get their own top-level section number (not a sub-section of another feature)

### Validation Levels

Pay close attention to whether a validation is:
- **required** / **error** — blocks publishing
- **warning** / **optional** — shows warning but allows "Publish Anyway"

The ticket description is the authoritative source. Cross-check against comments — if there's a conflict, the ticket description wins.

### Cross-References

When a topic spans multiple pages:
- Write the full detail in the most relevant dedicated page
- Other pages reference it with a brief wikilink + one-line summary
- Example: Missing Info validation details go in `Item Validations-Missing Info.md`; the card page just says "See [[Item Validations-Missing Info]], section X."

## Common Pitfalls

1. **Assuming validation level**: Always check the ticket for "required" vs "warning". Don't copy the validation level from a similar existing feature.
2. **Duplicating content**: If Change History, Missing Info, or Publish behavior is already in its dedicated page, use cross-references instead of repeating.
3. **Wrong parent-child hierarchy**: A new card/feature is a peer of existing ones, not a child. Give it its own top-level section number.
4. **Forgetting Change Log tables**: Every modified page gets one at the bottom.
5. **Modifying unrelated pages**: Only touch pages directly affected by the ticket.
6. **Editing before approval**: Never modify files until the user explicitly approves the plan.

## Quick Reference

| Task | Tool |
|------|------|
| Read Jira ticket | `mcp__mcp-atlassian__jira_get_issue` |
| List CB-full-feature files | `find Z01-Resource/CB-full-feature -name "*.md"` |
| Read a page | `Read` tool with absolute path |
| Edit a page | `Edit` tool with exact `old_string` match |
| Create a new page | `Write` tool with full content + frontmatter |
| Search within files | `grep` via Bash |