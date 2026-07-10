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

### Step 2: Explore the Documentation — Read EVERY Page

**Do not skip any page.** You must read the full content of every single `.md` file in `Z01-Resource/CB-full-feature/` and all its sub-directories. This is not optional — a requirement buried in an unexpected page will be missed if you only read "related" pages.

1. **Enumerate all files**: Use `find Z01-Resource/CB-full-feature -name "*.md" | sort` to get the complete file list.
2. **Read the overview pages first**:
   - `README.md`
   - `Cookbook Full Features Detail Requirements.md` (the summary index)
3. **Read every sub-directory page, without exception**:
   - `01 Fields & Cards in Items.md`
   - Every page under `02Common Features/` (including `Backend Features/` sub-directory)
   - Every page under `Item Details/` (including all sub-directories like `Components/`, `Nutritions/`, `Procedure Card/`, `Item Information/`, `Hot Holding Card/`, `Customization V2/`, `Usages/`, etc.)
   - Every page under `Item Grid/`
   - Every page under `Configurations/` (including `Locations/` sub-directory)
   - Every page under `Menu/`
   - Every page under `Line Build/`
   - Every page under `Benchtop Recipe/`
   - Every page under `Variant-Test Kitchen/`
   - Every page under `WSKUs & Consumables Grid/`
   - Every page under `Vendor Items/`
   - Every page under `Features TBD/` (including `Create Item/Create Ingredient/` sub-directory)
   - `HDR Consumable Item 40 Detail.md`
   - `Scheduled changes.md`
   - `User List.md`
4. **Compare each page against the ticket**: After reading each page, ask: does this page intersect with any requirement in the ticket? If yes, flag it for potential modification. If no, explicitly note it as "no change needed."
5. **Pay extra attention to cross-cutting concerns** that span multiple pages:
   - A new card → affects Fields & Cards matrix, the card's own detail page, validations, publish flow, copy/version creation, change history, and compare change history
   - A validation rule change → may affect both the validations page and the publish workflow page
   - A field behavior change → may affect the card's detail page and the item grid page

**The goal**: after this step, you should have read every page and be able to state — for *each* page — why it does or does not need changes.

### Step 3: Analyze & Plan (internal)

Map ticket requirements to documentation pages. For each page, determine:
- **Modify existing page** — what exact content to add/change
- **Create new page** — what the page should contain
- **No change needed** — pages that are unaffected (track internally for completeness; do NOT include in user review)

### Step 4: Present Plan for Review (DO NOT EXECUTE YET)

Present a structured plan showing **only pages that need changes** (modify or create):

- **Before** — the current content (exact excerpt)
- **After** — the proposed new content
- **Rationale** — why this change is needed

**Do NOT list pages that need no changes** — they add noise without value for review. If the user asks whether a specific page was checked, answer directly.

**Critical: Wait for user approval before making ANY edits.**

### Step 5: Execute After Approval

Only after the user explicitly approves (item by item or all at once), execute the changes.

### Step 6: Feed the Cookbook RA Capability Log

After the archive is executed, treat this ticket as a retrospective test case for the Cookbook RA skill (`.claude/skills/my-workflows/cookbook-ra.md`). Skip this step only for clearly trivial tickets (pure copy-edits, one-line label changes) — default to doing it otherwise.

1. **Reverse-engineer the requirement analysis this ticket would have needed**, using the ticket plus what's now documented in CB-full-feature: prior functionality/state (现有功能), impact points (影响点), related/connected features (关联功能), risks (风险), and which analysis dimensions actually mattered (分析维度) — i.e., what would a thorough RA of this ticket have had to cover, now that the real, shipped answer is visible?
2. **Compare against the current Cookbook RA skill's framework** — its resource registry, escalation signals, and content axes (A: business rule/capability change vs B: item type attribute management). Does this real case reveal something the current framework would miss or handle awkwardly?
3. **Append findings to the design log, not the skill file**: `A1-RA Rough/2026-07-06_Cookbook RA Skill_设计讨论.md`, under its case-retrospective section (use the entry format documented there). Do not edit `cookbook-ra.md` directly from this step — Bonnie reviews the accumulated log periodically and decides when/how to fold findings into the actual skill.

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