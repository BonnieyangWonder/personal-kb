# Check 40 Item Fulfillment Gaps

Audit a batch of Cookbook 40\* items (HDR Consumable Items) for whether each one has a **usable fulfillment option** behind it, and flag only the genuine gaps — filtering out items that look suspicious at first glance but are actually fine for a documented business reason. This is Bonnie's personal workflow; it does not modify any Cookbook data (read-only BigQuery throughout).

Full rationale, SQL templates, and worked examples live in [[个人/missing fulfillment option 分析方法]] — read it once per session for the complete methodology; this skill file is the condensed, executable version.

## When to Use

Trigger on natural language and intent, not a fixed command. Examples:

**中文**:
- "查一下这些40 item有没有对应的fulfillment option"
- "这批40 item背后是否有可用的fulfillment"
- "40 item fulfillment异常排查"
- A list of 40\* item numbers (possibly with a 40→42 mapping attached) handed over with an implicit "check these"

**English**:
- "check if these 40 items have a usable fulfillment option"
- "audit these 40 items for fulfillment gaps"

Input is normally a list of 40\* item numbers. The user may also paste a 40→42 mapping alongside them — **note it but do not trust it as ground truth** (see Step 2).

## Step 0 — Scope the Batch

Collect the full list of 40\* item numbers to check. If the user pasted a 40→42 mapping, keep it only as a hint of what used to be true; the actual check always re-derives the current WSKU set from the database (Step 2).

## Step 1 — Brand Check

Goal: is this 40 item used by any brand outside the allowed list?

1. Pull the 40 item's own `concept_ids` from `secure-recipe-prod.recipe_v2.item_versions` (`effective=true, deleted=false`) — this field is already system-calculated from the menu items that use this item, so there is normally no need to drill down to individual menu items.
2. Resolve each concept_id → `wonder-recipe-prod.recipe_v2.concepts.brand_ids` → `wonder-dw-prod-brd.dw.dim_restaurant_brands.restaurant_brand_name`. This gives the real commercial brand(s) — concept name and brand name are **not** the same thing (e.g. concept "Wonder Café" resolves to brand "Grab & Go").
3. Apply the known exemption: if the resolved brand set contains both **Ess-a-Bagel** and **Grab & Go** (i.e. concept_ids has both Ess-a-Bagel and Wonder Café), drop Grab & Go from the set — Wonder Café is a shared resale channel, not an independent operating brand, per Bonnie's standing call.
4. Allowed brand list (default, ask Bonnie before changing): **{Happy Tuna, Ess-a-Bagel}**.
5. Remaining brand set ⊆ allowed list → item is **normal, skip**. Otherwise → continue to Step 2.

**Edge case**: if a 40 item's rolled-up `concept_ids` includes a brand-exempt concept (like Wonder Café) alongside something that ISN'T Ess-a-Bagel/Happy Tuna, and you suspect the rollup might be hiding a "concept X used alone on some menu item" case the aggregate can't distinguish, drill down to actual consuming menu items (BOM + customization, see the playbook's §4 query) and check each menu item's own concept individually. This has not been needed in practice yet — the item-level rollup has matched the menu-item-level truth every time so far — but keep it as a fallback if a future batch looks inconsistent.

## Step 2 — Fulfillment Availability Check

Only for items that failed Step 1. Query `wonder-raw-prod.mysql_batch_product_catalog.wonder_sku_items` **comprehensively** by `consumable_item_number` for both the thawed 40 and its 40F (if it exists) — never rely on a single externally-given 40→42 mapping, since a 40/40F can have several WSKUs and some may be dormant or superseded by a newer one.

A WSKU (41\* or 42\*) counts as **usable** only if:
- `wonder_sku_items.deleted = false` and `item_status != 'DORMANT'`
- it has a row in `wonder_sku_to_fulfillment_options` with `deleted = false` and `status = 'ACTIVE'` (the other two possible values, `INACTIVE_BY_USER` and `INACTIVE_BY_SYSTEM`, do **not** count)

Check in this order, any hit = normal:

1. **40F route**: does a 40F exist, and does it have ≥1 usable 42 item?
2. **Thawed route**: does the 40 itself have ≥1 usable 42 item?
3. **Pre-cutover route**: is the 40 not yet cut over to SCC (`scc_source = NULL` on its WSKUs, no 42 item exists at all), and does it have ≥1 usable 41 item?
4. None of the above → **flag as abnormal**.

Distinguish clearly in the writeup between "cut over to SCC but the fulfillment option is missing/inactive" (real gap, needs a fix on the 42 side) vs. "not yet cut over, and the legacy 41 path also has no usable option" (different kind of gap — likely needs SCC cutover work, not just a fulfillment-option fix). Use `scc_source` to tell these apart, not just "does a 42 exist."

## Step 3 — Report Results

Default to an in-chat summary, grouped for readability:
- Normal items: summarize by why they're normal (e.g. "61 items, Ess-a-Bagel/Wonder Café only" as one line, not 61 rows) — don't force a full row-per-item table when a group-level statement says the same thing.
- Abnormal items: one row each — item number, name, brand(s) that triggered Step 1, and which specific Step 2 route failed and why.

**Do not write a persistent report note by default.** Only create one if Bonnie explicitly asks to save/archive the analysis — then follow `report-paths.md`'s routing (data-research-style findings → `A2-Data Research/`) unless she names a different location directly (e.g. `个人/`).

## Boundaries

- Read-only. Never edit, publish, or otherwise act on live Cookbook/SCC data to "test" a finding.
- Does not create a Jira ticket for flagged gaps — that's a separate, explicit ask (see `ticket-workflow`).
- Does not decide the allowed-brand list or concept→brand exemptions on its own — those are Bonnie's calls (see the playbook's "参数化配置" table for the current values). If a batch surfaces a brand/concept combination not already covered there, surface it and ask rather than guessing.

## Maintenance

The allowed-brand list and concept→brand exemption table live in [[个人/missing fulfillment option 分析方法]], not hardcoded here — update that file when Bonnie changes them, this skill file should not need to change as a result.
