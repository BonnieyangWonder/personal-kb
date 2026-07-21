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

Fetch the full Jira ticket via Atlassian MCP tools (`jira_get_issue` with `fields=*all`, `include=comments`) **directly yourself** — do not rely on a sub-agent's paraphrased summary for anything that will be written into CB-full-feature. Sub-agent summaries have repeatedly been observed to blend description and comment content indiscriminately, and even to invent plausible-sounding details with no ticket basis at all (a fabricated UI button, a fabricated backend function name). Capture:
- Summary, description, acceptance criteria
- All comments (especially implementation summaries and clarifications)
- Linked Confluence pages or Figma references
- **Always read the latest ticket description** — it is the authoritative source. Comments may contain outdated discussions.

### Step 1.5: Source Discipline (Critical)

This is the most common failure mode in past archives. Follow strictly:

1. **The `description` field is the source of truth for requirements.** Every requirement documented in CB-full-feature must be traceable to a specific line in a ticket's description. Go through the description **line-by-line, not just the parts that feel most salient** — past archives missed real requirements (an API field-exposure requirement, an attribute-update-propagation rule) sitting in the description the whole time, because analysis jumped straight to the most visually prominent requirement (a UI checkbox) and treated everything else as secondary.
2. **Comments are supplementary, not authoritative for requirements** — but not all comment content is equal:
   - A comment describing *actual implemented behavior* from the engineer who built it (e.g. a "What Changed" note naming a real UI position, a real preserved/cleared field behavior) is generally trustworthy and MAY be used, since it reflects what actually shipped.
   - A comment describing *internal implementation mechanics* (function names, exception types, backend call paths) should almost never be written into CB-full-feature — this is the wrong altitude for a requirements/behavior doc.
   - When in doubt whether a comment detail is real-implementation vs. speculative, ask the user rather than guessing.
3. **Never fabricate.** If a plausible-sounding UI affordance, message, or mechanism is not explicitly stated anywhere in the ticket (description OR comment), do not invent it to make the documentation feel "complete." Omit it, or flag it to the user as unconfirmed.
4. **Do not propose changes beyond what the tickets state.** A page or behavior that seems like a "reasonable product extension" but has no basis in any ticket's description must NOT be added to the archive — flag it separately as a suggestion if worth raising, but keep it out of the CB-full-feature update itself.
5. **When multiple tickets touch the same feature, the later-released ticket's description wins on conflicts** — but confirm this against actual resolution/release dates, not creation dates.
6. **`jira_get_issue`'s `description` field is a lossy pseudo-Markdown conversion of Jira's native wiki markup — its list numbering does NOT reliably reflect the true nesting level.** Confirmed by testing: neither `expand=renderedFields` nor any other fetch option fixes this; the tool always flattens multi-level ordered lists (e.g. a heading + 3 sub-items can come back as a flat `1. 2. 3. 4.` sequence that resets arbitrarily). When extracting requirements, judge the real hierarchy from the content's logic, not from the literal numbers shown. When writing into CB-full-feature pages, always author fresh, correctly-nested Markdown yourself — never mechanically copy-paste a ticket's raw numbered list text as if its markers were trustworthy.

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
6. **Never assume a page's scope from its title alone.** Read its full content before deciding it needs a specific field/behavior added. Past archives proposed changes to a page based only on what its name suggested, without ever reading the page — and the assumption was wrong.
7. **Distinguish display/view pages from create/edit pages.** Editing-time interaction logic (what happens when a field changes, validation triggered on save, activity-switch preserve/clear behavior) belongs on the edit page. A display/view page should only describe the read-only final-state rendering — do not duplicate edit-time behavior there.

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

1. **Reverse-engineer the requirement analysis this ticket would have needed**, using the ticket plus what's now documented in CB-full-feature — what would a thorough RA of this ticket have had to cover, now that the real, shipped answer is visible? Bring whatever analysis lenses are actually relevant to this specific ticket, the way an experienced requirements analyst sizing up a real case would — do not force it into a fixed checklist. Prior functionality/state, impact scope, related/connected features, cross-team dependencies, risks, and which dimensions turned out to matter are common starting points, not a mandatory or exhaustive list.
2. **Compare against the current Cookbook RA skill's framework** — its resource registry, escalation signals, and content axes (A: business rule/capability change vs B: item type attribute management). Does this real case reveal something the current framework would miss or handle awkwardly?
3. **Append findings to the design log, not the skill file**: `A1-RA Rough/2026-07-06_Cookbook RA Skill_设计讨论.md`, under its case-retrospective section (use the entry format documented there). Do not edit `cookbook-ra.md` directly from this step — Bonnie reviews the accumulated log periodically and decides when/how to fold findings into the actual skill.

### Step 7: Mark the Ticket as Archived

**Trigger: only when the user explicitly confirms the archive is fully complete** for a ticket or batch of tickets. Do not do this automatically right after executing edits, and do not do it per-page as individual pages get approved — wait for the user's final "done" signal for the whole batch.

1. For each archived ticket, **add a comment** (do NOT modify the `description` field — see rationale below):

   `Note: Updated to Obsidian CB Full Feature page`

2. Use `mcp__mcp-atlassian__jira_add_comment`. A comment is plain text with no structural formatting to preserve, so there is nothing to corrupt.
3. **Never modify the `description` field for this or any other non-substantive purpose.** `jira_get_issue` converts Jira's native wiki markup (`h2.` headings, `#`/`##`/`###` nested ordered lists, `||...||` tables, `-strikethrough-`) into an approximate, lossy pseudo-Markdown when displaying it to you. Round-tripping that text back through `jira_update_issue` (which parses the input as standard Markdown) does NOT correctly reconstruct the original nesting/tables/headings/bold — this already happened on a real archive (2026-07-21, MD-17690/17820/17947/18130): all multi-level numbering, table structure, and bold styling in the descriptions was flattened/lost. Recovery required pulling the pre-edit raw wiki markup from the issue changelog (`jira_get_issue` with `include=changelog`, read the `from_string` of the `description` field change) and handing it to the user to manually restore in Jira's rich editor — the API round-trip cannot be trusted to fix itself.
4. This is a one-line marker on the Jira side so future readers know the ticket's requirements have been folded into CB-full-feature — it is not a substitute for the Change Log entries already added to the CB-full-feature pages themselves.

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
7. **Trusting sub-agent paraphrase over the ticket's raw text**: always fetch and read the raw `description` field yourself for anything going into CB-full-feature; sub-agent summaries can blend in comment content or invent details.
8. **Treating all comment content as equally reliable**: distinguish "engineer describing real shipped behavior" from "internal implementation mechanics" or unconfirmed speculation (see Source Discipline, Step 1.5).
9. **Filling gaps with plausible invention**: a missing detail (a button, a function name, a scope limitation) should be flagged as unconfirmed or omitted, never invented.
10. **Scope creep beyond the ticket**: don't add "reasonable" product extensions (e.g. a new table column, a new publish-time check) that no ticket description actually asked for.
11. **Assuming a page's role from its title without reading it**: verify whether a page is a display page or an edit page, and whether it's even the right home for the content, by reading its actual content first.
12. **Modifying a ticket's `description` field for any reason (e.g. marking it as archived)**: reading it via `jira_get_issue` and writing it back via `jira_update_issue` is a lossy round-trip for nested lists/tables/headings in Jira's native wiki markup — confirmed by a real incident (2026-07-21). Use a comment (`jira_add_comment`) for any post-archive annotation instead; never touch `description` after the initial read.

## Quick Reference

| Task | Tool |
|------|------|
| Read Jira ticket | `mcp__mcp-atlassian__jira_get_issue` |
| List CB-full-feature files | `find Z01-Resource/CB-full-feature -name "*.md"` |
| Read a page | `Read` tool with absolute path |
| Edit a page | `Edit` tool with exact `old_string` match |
| Create a new page | `Write` tool with full content + frontmatter |
| Search within files | `grep` via Bash |
| Mark ticket as archived (Step 7, after final confirmation) | `mcp__mcp-atlassian__jira_add_comment` (never `jira_update_issue` on `description`) |