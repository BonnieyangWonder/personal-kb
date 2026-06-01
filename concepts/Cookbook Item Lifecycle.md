---
title: Cookbook Item Lifecycle
date: 2026-05-29
created: 2026-06-01
updated: 2026-06-01
type: concept
domain: cookbook
tags:
  - cookbook
  - item-lifecycle
status: active
description: How items move through Cookbook's two independent status systems — item status (R&D → Active → Dormant) and version status (Draft → Scheduled → Final).
sources:
  - Z01-Resource/CB-business/core/item-lifecycle.md
  - Z01-Resource/CB-bigquery/schema-reference.md
author: bonnie
---

# Cookbook Item Lifecycle

Cookbook has **two independent status systems** that answer different questions:

| System | Level | Question |
|--------|-------|----------|
| **Item Status** | Item | "Should this item be in service?" |
| **Version Status** | Version | "Is this particular version live?" |

## Item Status: R&D → Active → Dormant

```
R&D ── (version takes effect) ──► ACTIVE ── (user dormants) ──► DORMANT
                                      ▲                              │
                                      └── (user undormants) ─────────┘
```

### R&D
The item is being worked on. Visible in Cookbook but not served to downstream systems. Benchtop items (`BT-*`) live permanently in R&D until commercialized.

### Active
The item becomes Active **automatically** when a Final version takes effect. Active = fully visible to downstream systems (Wonder App, KDS, Pantry). Once Active, stays Active until explicitly dormanted.

### Dormant
Intentionally out of service. Data preserved, but item is excluded from active BOMs, customization options, and availability. Always manual (except the weekly automated bulk dormant job).

**Dormant cascade effects**: Dormanting a MENU item also dormants its presets. Dormanting a recipe also dormants its byproduct outputs.

## Version Status: Draft → Scheduled → Final

```
DRAFT ── (publish w/ future date) ──► SCHEDULED ── (start time elapses) ──► FINAL
DRAFT ── (publish immediately) ───────────────────────────────────────────────► FINAL
SCHEDULED ── (item dormanted) ──► DRAFT (commitment cancelled)
```

### Draft
Default for new versions. No committed service window. Free to edit. Service start time is a placeholder (12/31/2100).

### Scheduled
Published with a future service start time. Read-only except for the start time field. Downstream systems can prepare for the upcoming version.

### Final
Live version. Service start time has elapsed. Only one Final version can be currently active per item. Cannot be reverted — only superseded by publishing a new version.

## Valid Combinations

| Item Status | Valid Version Statuses |
|-------------|----------------------|
| R&D | Draft, Scheduled |
| Active | Final (live) + optionally Draft or Scheduled |
| Dormant | Final (expired), Draft |

Key rules:
- A Dormant item **cannot** have a Scheduled version (it gets reverted to Draft)
- An item **cannot** simultaneously have both a Scheduled and Draft version
- A Scheduled version **does not** make an item Active — Active only when it goes Final

## The `effective` Flag

Marks which version is the currently authoritative one. Only one version per item can have `effective = true`.

`effective_items` (BQ table) filters to `effective = true` rows only — but you **still** need `deleted = false` and `item_status != 'DORMANT'`.

## Automated Bulk Dormant Job

Runs weekly (Monday 8:00 AM EST). Dormants items meeting ALL criteria:
- Not produced in 3 months
- Not updated in 3 months
- All versions `sold_status = NOT_SOLD`
- Not referenced by any non-dormant parent

**Excluded**: NON_FOOD, benchtop, 40*, 41*, 88*, MENU items with presets, exempt concepts (Blue Apron, Alanza, etc.).

## Special Cases

### 88* PACKAGED Dormant (5-Step Tree)
Use the decision tree documented in MD-17876 for 88* dormant evaluation, accounting for the 40*/41*/88* pack relationship chain. See [[Z01-Resource/CB-business/core/item-lifecycle.md]] Section 7.2.

### Sold Status vs Item Status
`sold_status` (FOR_SALE/SCHEDULED/NOT_SOLD/N/A) is independent of `item_status`. An item can be ACTIVE but NOT_SOLD. Only FOR_SALE or SCHEDULED items block dormant.

## Related

- [[Cookbook]] — system overview
- [[Cookbook Item Taxonomy]] — object type definitions
- [[Cookbook BOM Structure]] — how dormant affects BOM validity
- [[Cookbook Version Publish]] — publish workflow detail
- [[Cookbook 40-41 Model]] — special dormant rules for 40*/41*
- [[Z01-Resource/CB-business/core/item-lifecycle.md]] — full reference
