# Cookbook Requirements Analysis (RA)

Analyze an incoming Wonder Cookbook requirement and produce a requirements analysis report. Scales depth to what the requirement actually turns out to need — a lean efficiency pass for bounded, well-understood changes, or a full expert analysis with solution design and risk assessment when it turns out to be more complex than it first looked. This is Bonnie's personal workflow for Cookbook requirements work — it orchestrates across the shared `wonder-*` domain skills but is not itself one of them.

## When to Use

Trigger on natural language and intent, not a fixed command. Examples:
- "分析下 XX 需求" / "帮我分析一下这个需求" / "RA 一下" / "ra 分析"
- "requirements analysis for X" / "analyze this requirement"
- A Jira ticket link, Confluence link, or screenshot(s) handed over with an implicit ask like "cookbook 要怎么支持这个" / "what would it take to support this"

Input arrives in whatever form Bonnie gives it — don't require a specific format:
- Plain business-language description (e.g., "餐厅 cook dish 时需要支持 timer")
- A Jira ticket link/key
- Confluence page link(s)
- Screenshot(s) — read them, they often carry UI context or error detail that text alone won't
- Any combination of the above

## Step 0 — Resource Scan (always run first, cheap)

Orient before analyzing. This registry is the checklist — don't skip straight to reasoning without checking it.

### Cookbook domain knowledge (3 layers, coarse → fine)

| Layer | Location | Use for |
|---|---|---|
| wonder-cookbook skill | invoke via Skill tool | SQL patterns, schema, code references — activate this first for most lookups |
| CB-business | `Z01-Resource/CB-business/` | Business rules, field calculation logic. Has its own Trigger Topics routing table — use it |
| CB-full-feature | `Z01-Resource/CB-full-feature/` | UI/feature-level detail, mirrors Confluence space RT. Lazy-load via `Cookbook Full Features Detail Requirements.md` index — don't read all 179 pages for a routine RA |

`.claude/skills/wonder-cookbook/{core,domains,cross-system,reference}/` and `Z01-Resource/CB-bigquery/` are largely the same underlying knowledge in two forms. Loading the wonder-cookbook skill is usually enough; only go into raw `CB-bigquery/` for things it doesn't link (metrics/, saved queries/, datasets index).

**Important limitation**: CB-full-feature only reflects features that have **shipped**, and only up to whatever point Bonnie has manually archived through (see "Unarchived tickets" below) — it is not a live mirror.

### Cross-system skills — load automatically, don't ask first

The moment the requirement touches another system's domain, go load that skill's knowledge yourself. Briefly state which systems you pulled in (one line, not a permission request):

wonder-pantry, wonder-orders, wonder-otr, wonder-sporklift, wonder-supply-chain, wonder-menu-availability, wonder-command-center, wonder-sequencing, wonder-kitchen-ops.

`wonder-ladle` is WIP/empty — known gap. If the requirement touches Ladle, say so explicitly rather than silently skipping it.

### Live sources

- **BigQuery** (4 datasets, 70+ tables) — for real impact numbers (see Step 2).
- **Jira / Confluence** via `mcp-atlassian` — if the requirement references a ticket or page, read the actual content (ticket description + comments, page body), not just the title.
- **Unarchived recent Jira tickets** — CB-full-feature lags shipped work because Bonnie archives it incrementally (via her separate `archive-jira-to-cb` workflow), whenever she has time, sprint by sprint. If the requirement touches an area that's likely mid-migration (e.g., currently: WSKU/40\*/41\*/SCC/fulfillment options — an in-flight SCC catalog migration spans MD 2026 Sprint 8 onward as of this writing), ask Bonnie for her current "archived-through" sprint checkpoint and query recent tickets yourself:
  `project = MD AND sprint in ("MD 2026 Sprint <checkpoint+1>", ..., "<current sprint>")`
  Track the checkpoint **by sprint number, given directly by Bonnie** — never infer it from file modification dates. Archiving is incremental and not date-ordered, so dates don't reflect real progress. This check only matters for areas plausibly affected by an active migration — don't run it on every RA.

### Known gaps (flag when relevant, don't block on them)

- No team/owner contact map in the vault (e.g., who owns SCC integration) — lives only in Confluence ("Cookbook system overview" page). Check there or ask Bonnie if a cross-team contact matters to the analysis.
- No backend code repository access by default. If a claim needs code-level verification (exact field names, service classes) and isn't already documented, mark it "needs code verification" rather than guessing.
- `wonder-ladle` skill is empty/WIP.

## Step 1 — Understand the Ask

Read everything provided, fully: full ticket body + all comments (not just the summary line), linked Confluence pages (and their child pages / footer / inline comments if linked), screenshots. Don't analyze off a title or a one-line paraphrase.

### Map the Cross-System Blast Radius (always, no exceptions)

A ticket that names one counterparty system (e.g. "VCS wants to change X") is rarely actually a two-party negotiation. Before moving to Step 2, nail down three things — they compound, do all three:

1. **Full consumer graph, not just the named counterparty.** Find every system that reads or writes the same field/entity, not only the one named in the ticket. Check what's downstream of Cookbook directly (via the relevant wonder-* skills and CB-full-feature — Order Grid, ShipHero, Sporklift, Pantry, etc. each have independent sync paths) AND what's downstream of the named counterparty itself (e.g. what reads *from* VCS, not just what VCS reads from Cookbook). Don't stop at the first system named in the ticket — explicitly ask "who else touches this data."
2. **Which side actually implements the described behavior?** Don't assume the change is symmetric. A counterparty's proposed change ("we'll ignore your updates from now on") may require zero code change on Cookbook's side — the logic can live entirely in their own ingestion layer. Pin this down explicitly: whose code changes, whose doesn't. This directly shapes the answer to "what does Cookbook need to do" — sometimes the honest answer is "supply data to inform their decision, write no code."
3. **Consistency consequence, given 1 and 2.** Once the consumer graph and the implementation side are both known, work out what happens once the two sides diverge: which systems keep tracking Cookbook's live value, which inherit the counterparty's altered/frozen value, and what breaks — or just looks contradictory — for anyone who ends up comparing the two.

Not a one-time gate — revisit if Step 2's data analysis surfaces a system you hadn't accounted for.

## Step 2 — Data Impact Analysis (always, no exceptions)

Always run real BigQuery queries to quantify impact — how many items/HDRs/orders/menus are actually affected. This is a firm default for every RA, not something to skip because the requirement looks simple; logical reasoning alone is not sufficient.

**Read-only, always** — query existing data, never act on a live system to produce new data to analyze. See the hard safety rule in Step 5.

## Step 3 — Escalation Check (this decides output depth — not the requirement's wording)

Do **not** pre-classify the requirement as simple or complex from how it's phrased — that's unreliable. Three real precedents ([[2026-05-25_Gluten-Free_标签系统推断改人工指定_需求分析]], [[2026-05-21_40_item_number_F-T_suffix_影响评估]], [[2026-06-24_Wonder_Create_BYO_Customization_Analysis]]) all read as simple/bounded on the surface and all escalated once actually investigated. Complexity shows up during analysis, not in the initial ask.

The first two signals below are often exactly what Step 1's blast-radius mapping surfaces — don't skip straight to eyeballing this table without having actually done that mapping.

After Steps 0–2, check whether any of these signals turned up:

| Signal | Example |
|---|---|
| Touches a contract/boundary another team already depends on | F/T suffix hit SCC's `4000555 = thawed` assumption |
| Violates an existing system invariant/assumption | item_number uniqueness change; system-inferred → manually-certified breaks the no-human-in-loop assumption |
| Requires structural change to production data at scale | F/T suffix's item number rename = mass reference update risk |
| Involves compliance/legal/food-safety risk, not just technical risk | Gluten-Free allergen declaration risk |
| No existing pattern to reuse — needs new mechanism design | BYO's Material Category auto-classification rules |
| Needs coordination across 3+ teams | Gluten-Free touched 8 teams |

**None triggered → Mode 1 (Efficiency).** Bounded, well-understood change.
**Any triggered → Mode 2 (Expert).** Full solution design + risk analysis, even if it didn't look that way at first.

This check isn't a one-time gate — if a Mode 1 analysis is underway and a signal turns up mid-way, say so and escalate rather than forcing the original scope.

## Step 4 — Write the Report

**Draft first, archive only after Bonnie approves.** Do not call a file-write tool to save the report as the first move. Present the full report content in-chat — same structure and content it would have as a file — and explicitly ask for review. Only after Bonnie confirms it's good (with or without revisions) do you write it to disk per the Output section below. This holds for both modes. The archived file is the final, reviewed record of the analysis, not a place to iterate — treat it as the last step, not a draft dump.

**Mode 1 (Efficiency) output** — lightweight: current state → what changes → checklist of things to verify/watch. No need to force the full Mode 2 structure.

**Mode 2 (Expert) output** — full: background → current system analysis → solution options → data-backed impact analysis → cross-team matrix → roadmap → open decisions → risks/rollback. Use [[2026-05-25_Gluten-Free_标签系统推断改人工指定_需求分析]] as the structural reference.

Keep in mind two content axes while scoping either mode (independent of Mode 1/2 — these affect which knowledge sources matter most, not the depth):

- **A. Business rule / capability change** — validation logic, data maintenance, new fields/features/API, usually driven by downstream system needs. Look mainly at feature/API docs.
- **B. Item type attribute management** — common or type-specific attribute changes across the 9 `object_type`s ([[Cookbook Item Taxonomy]]), usually driven by product/process needs. Look mainly at `core/item-and-object-type.md` + the relevant `features/*.md`.

A requirement can be both at once.

## Step 5 — Boundaries (what this skill does not do)

- **Never verify a finding by acting on a live environment.** No publishing, editing, deleting, or otherwise triggering business logic in Cookbook — not in prod, not in any environment tied to the master branch, not "just to see what happens." This holds everywhere in the workflow, especially Step 2's data impact analysis: quantify impact by querying *existing* data (BigQuery `SELECT`, reading Jira/Confluence/docs) and reading *existing* records of what happened (e.g. QA test-case text already written by someone else) — never by performing the action being analyzed yourself. If a claim can't be confirmed from existing data or documentation, say so as an open question rather than going to test it live.
- **Do not propose creating a Jira ticket.** RA stops at the analysis report.
- **Do not write into CB-full-feature or CB-business.** CB-full-feature only records features that have shipped; RA-stage analysis isn't there yet. If a requirement here later ships, archiving it (via the separate `archive-jira-to-cb` workflow) or formalizing it (via `biz-req`) is Bonnie's own later, separate, manually-triggered decision — not something this skill chains into.

## Output

- **Location**: `A1-RA Rough/` — verified against the actual filesystem: 3 precedent docs already live here, and a sibling `A2-RA Rough/` (mentioned in the generic `report-paths.md` rule) does not exist anywhere in this vault. If `report-paths.md` and this file ever disagree on the Cookbook RA output directory, **this file wins** — it's the more specific instruction and matches what's actually on disk. Don't re-derive this from scratch next time; it's settled.
- **Do not archive before review.** Write the file only after Bonnie has reviewed the drafted report in-chat and approved it — see Step 4.
- **Filename** — no date:
  - Ticket-based: `<TICKET-KEY>_<Topic>_<描述>.md` (e.g. `MD-17701_Timer支持_需求分析.md`)
  - Not ticket-based: `<Topic>_<描述>.md`
- **Must include a Reference Linkage section**: ticket link(s), Confluence link(s), related RA docs, related CB-business/CB-full-feature pages — wikilink internal references.
- **Language**: match whatever the requirement source uses; mixed Chinese/English is normal.

## Reference precedents

- [[2026-05-25_Gluten-Free_标签系统推断改人工指定_需求分析]] — Mode 2, structural template
- [[2026-05-21_40_item_number_F-T_suffix_影响评估]] — Mode 2, cross-team contract conflict
- [[2026-06-24_Wonder_Create_BYO_Customization_Analysis]] — Mode 2, new-mechanism design
