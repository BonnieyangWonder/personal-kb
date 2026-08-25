# Check 40 Item / Menu Item Dormant Candidacy

Given a batch of Cookbook 40\* items (HDR Consumable Items) tracked in a local Excel workbook (e.g. an "Uncutover 40s" cutover tracker), find every menu item / HDR recipe item that currently uses each one, then build a review sheet so a human can confirm which of those menu items — and by extension which 40 items — are safe to mark dormant. This is Bonnie's personal workflow; it is read-only against BigQuery and never modifies live Cookbook data. It only edits the local Excel workbook (adding sheets/columns), never the vault.

For the underlying query patterns and gotchas referenced throughout, see:
- [[Z01-Resource/CB-bigquery/playbooks/data-research-patterns.md]] §13–14 — the two hard-won lessons this skill exists to encode
- [[.claude/skills/wonder-cookbook/domains/hdr-consumables.md]] — 40 Model domain reference, including the "F" suffix trap

## When to Use

Trigger on natural language and intent, not a fixed command. Examples:

**中文**:
- "查下这个 Excel 里的 40 item 有没有被 menu item 用"
- "帮我看看这批 40 item 能不能 dormant"
- "这些 menu item 是否可以 dormant"
- 直接甩一个本地 Excel 文件路径 + 一批 40 item 编号，隐含"看看谁在用、能不能下线"的诉求

**English**:
- "check which menu items use these 40 items"
- "can these 40 items be marked dormant"
- "audit this batch for dormant candidacy"

Input is normally a local Excel file (in `~/Downloads/` or wherever Bonnie points) with one or more sheets listing 40\* item numbers in a column. Read the exact column/sheet name before assuming a layout.

## Step 0 — Scope the Batch and Extract 40 Item Numbers

1. Read the target sheet(s) from the local Excel file (use `openpyxl` via Bash — this is a local file outside the vault, not an Obsidian CLI task).
2. Dedupe by item number.
3. **⚠️ Do not regex-strip non-numeric characters to normalize item numbers.** Some 40\* items carry a real, distinct trailing `F` (frozen variant) — e.g. `4001271F` is a completely different, real item from `4001271`, and in some cases the bare number doesn't exist at all. Stripping it silently drops or misidentifies real items. Before deduping, verify with:
   ```sql
   SELECT item_number, name, item_status, sold_status, effective, deleted
   FROM `secure-recipe-prod.recipe_v2.item_versions`
   WHERE item_number IN ('<bare>', '<bare>F');
   ```
   Treat every distinct string (bare and suffixed) as its own item to check.

## Step 1 — Usage Query (BOM + Customization)

For each 40\* item number, find every non-dormant, non-expired-version, non-preset menu item or HDR recipe item that references it, via BOM line or customization option mapping:

```sql
WITH bom_usage AS (
  SELECT
    JSON_VALUE(bom_line, '$.item_number') AS src_item_number,
    iv.item_number AS usage_item_number, iv.name AS usage_item_name,
    iv.item_status, iv.sold_status, iv.version_id AS version, iv.version_status,
    'BOM' AS used_in,
    CAST(NULL AS STRING) AS customization_type,
    CAST(NULL AS STRING) AS customization_name,
    CAST(NULL AS STRING) AS option_name
  FROM `secure-recipe-prod.recipe_v2.item_versions` iv,
  UNNEST(JSON_EXTRACT_ARRAY(iv.bom_header, '$.bom_lines')) AS bom_line
  WHERE iv.effective = true AND iv.deleted = false
    AND iv.item_status != 'DORMANT' AND iv.version_status != 'EXPIRED'
    AND iv.object_type IN ('MENU','HDR_RECIPE')
    AND iv.preset_item_version_info IS NULL
    AND JSON_VALUE(bom_line, '$.item_number') IN ({id_list})
),
cust_usage AS (
  SELECT
    JSON_VALUE(opt_item, '$.item_number') AS src_item_number,
    iv.item_number AS usage_item_number, iv.name AS usage_item_name,
    iv.item_status, iv.sold_status, iv.version_id AS version, iv.version_status,
    'customization' AS used_in,
    JSON_VALUE(opt, '$.type') AS customization_type,
    JSON_VALUE(opt, '$.name') AS customization_name,
    JSON_VALUE(opt_val, '$.name') AS option_name
  FROM `secure-recipe-prod.recipe_v2.item_versions` iv,
  UNNEST(JSON_EXTRACT_ARRAY(iv.item_customization, '$.options')) AS opt,
  UNNEST(JSON_EXTRACT_ARRAY(opt, '$.option_values')) AS opt_val,
  UNNEST(JSON_EXTRACT_ARRAY(opt_val, '$.items')) AS opt_item
  WHERE iv.effective = true AND iv.deleted = false
    AND iv.item_status != 'DORMANT' AND iv.version_status != 'EXPIRED'
    AND iv.object_type IN ('MENU','HDR_RECIPE')
    AND iv.preset_item_version_info IS NULL
    AND JSON_VALUE(opt_item, '$.item_number') IN ({id_list})
)
SELECT * FROM bom_usage UNION DISTINCT SELECT * FROM cust_usage
ORDER BY src_item_number, usage_item_number, used_in;
```

**If a usage-item hit is itself a `HDR_RECIPE` (7\* prefix), don't stop there** — reverse-query who uses *that* HDR recipe item, using the same query template with the 7\* item numbers as `{id_list}`. Keep following the chain until it terminates in `MENU` items with no further indirection (in practice this has been at most one hop deep so far, but don't assume that's a hard limit).

## Step 2 — Build/Update the Excel Sheets

Per batch (each source sheet of 40 items), add a `"<source sheet name> usages"` sheet with columns:

`40 item number, usage item number, usage item name, item status, sold status, version, version status, used in BOM/customization, customization type, customization name, option name`

Also add a `"No usage <source sheet name> items"` sheet listing the 40 items with **zero** hits — these are the strongest dormant candidates for the 40 item itself.

**Excel hygiene**:
- Load with `openpyxl.load_workbook(path)` (no `data_only=True` when you intend to save) so formulas/formatting on untouched sheets survive.
- Before rebuilding any sheet, re-read its *current* header row and column order — Bonnie edits this file by hand between turns (reordering columns, adding her own notes column, renaming headers). Never assume your last-known layout is still current; diff against what's actually in the file.
- Prefer targeted `ws.delete_rows()` / `ws.append()` / cell-level writes over full delete-and-recreate when a sheet has manual annotations you must preserve.
- When correcting or updating values, highlight the changed cells (light yellow = value refreshed, light green = label/id corrected, light blue = new row added) so Bonnie can see at a glance what changed without diffing manually.

## Step 3 — Menu Item Dormant Confirmation Sheet

Dedupe the usage items **by item number** across all the usage sheets from Step 2 (a menu item can appear via more than one 40 item, and once via BOM and once via customization). Build (or append to) a sheet, e.g. `Menu Item Dormant Confirmation`, with:

`menu item number, menu item name, item status, sold status, version, version status, referenced 40/hdr recipe item(s), source sheet(s), confirm OK to dormant?, comments`

- `referenced 40/hdr recipe item(s)`: every 40/7\* item that pulled this menu item in, comma-joined.
- `source sheet(s)`: which usage sheet(s) it came from.
- Leave `confirm OK to dormant?` / `comments` blank — that's the human sign-off, not something to infer.
- If asked to build the same confirmation sheet for a single batch's usages sheet (e.g. "B2B 88 usages" specifically), it's the same dedupe-and-format step scoped to one source sheet instead of several — keep sheet names under Excel's 31-character limit.

## Step 4 — Recency Check (Was It Recently Edited by a Human?)

For every item number in a confirmation sheet, check `wonder-recipe-prod.mongo_batch_recipe_v2.item_version_change_logs` for edits in the requested window (default ask if not specified; 90 days has been the default so far):

```sql
SELECT item_number, created_by, created_time, is_system_action, actions
FROM `wonder-recipe-prod.mongo_batch_recipe_v2.item_version_change_logs`
WHERE item_number IN ({id_list})
  AND TIMESTAMP(created_time) >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 90 DAY)
ORDER BY item_number, created_time DESC;
```

**`is_system_action = false` alone is not enough to call something "human."** First survey `GROUP BY created_by, is_system_action` for the actual item set — known non-human actors that slip through this flag include `SCC_SYNC` (nutrition-recalc sync) and `Wonder Create` (bulk authoring tool), on top of the reliably-flagged `recipe system` / `Recipe System (MD-xxxxx)` family. Build the exclusion list from what you actually see, don't hardcode a fixed list blindly — new automated actors may show up in a different batch.

Add columns to the confirmation sheet: `edited in last N days?`, `last edited by`, `last edited date`, and optionally `last edit detail (within N days)` (parse the `actions` JSON into a short human-readable string, e.g. `"Published: This Version"`, `"Edited: Component"` — this distinguishes substantive content edits from cosmetic/system-adjacent ones like `Recalculated: Nutrition` or attribute-only updates).

## Step 5 — Interpreting the Result (Don't Auto-Classify)

- An item with **no usage at all** (Step 2's "No usage" sheet) and **no recent human edit** (Step 4) is the strongest dormant candidate — but still needs human sign-off, not automatic action.
- An item **with usage** in only `R&D`/`DRAFT` menu items is genuinely ambiguous: `R&D`/`DRAFT` describes publishing stage, not whether the item is stale test data (safe to dormant alongside) or active in-flight work (not safe). **Don't infer either way from status fields alone** — surface it explicitly as "needs confirmation" and note the recency signal from Step 4 as a hint, not a verdict.
- An item recently edited with a substantive action (`Published: This Version`, `Edited: Component`, `Updated: BOM Line`) is a strong signal someone is actively maintaining it — flag for priority follow-up with that editor before recommending dormant.
- If a live `item_versions` re-check (re-running Step 1's status columns later) shows an item has vanished entirely (zero rows, not just `deleted=true`), it's been hard-deleted from Cookbook since the original pull — mark it as such (e.g. `DELETED` in the status columns, with a comment and timestamp) rather than leaving stale data, and treat it as no longer needing dormant confirmation.

## Step 6 — Report Results

Default to an in-chat summary: totals per batch (X checked / Y have usage / Z zero-usage), and call out anything actionable (recently-deleted items, ambiguous R&D/DRAFT clusters, items with substantive recent edits). Only write a persistent report note if Bonnie explicitly asks — then follow `report-paths.md` (data-research findings → `A2-Data Research/`).

## Boundaries

- Read-only against BigQuery. Never edit, publish, or otherwise act on live Cookbook data to test a finding.
- The Excel workbook is the only artifact this skill writes to, and only via adding/updating sheets and cells — never delete Bonnie's own manually-added columns, notes, or rows without being asked.
- Does not decide dormant status on anyone's behalf — the `confirm OK to dormant?` column is always left for a human, even when every other signal points the same way.
- Does not create a Jira ticket or a persistent vault report unless separately asked.

## Maintenance

The two core query gotchas (40\* "F" suffix, `is_system_action` unreliability) are documented in depth in [[Z01-Resource/CB-bigquery/playbooks/data-research-patterns.md]] §13–14 — update that file if a new variant of either surfaces, not this skill file, so the lesson is available to any Cookbook data-research task, not just this one.
