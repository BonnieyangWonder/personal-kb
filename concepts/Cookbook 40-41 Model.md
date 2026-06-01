---
title: Cookbook 40-41 Model
date: 2026-05-29
created: 2026-06-01
updated: 2026-06-01
type: concept
domain: cookbook
tags:
  - cookbook
  - kitchen-operations
status: active
description: The HDR Consumable (40*) and WSKU (41*) model for IKC inventory — how consumption tracking differs from procurement, and the pack relationship chain linking 40*/41*/88* items.
sources:
  - Z01-Resource/CB-business/core/item-lifecycle.md
  - Z01-Resource/CB-business/core/item-and-object-type.md
  - Z01-Resource/CB-bigquery/SKILL.md
author: bonnie
---

# Cookbook 40-41 Model

The 40/41 model separates **what gets consumed** at IKC locations from **what gets ordered** from the warehouse. This distinction is critical for inventory analysis — confusing the two leads to incorrect procurement and stock-level analysis.

## The Two Item Types

| Type | Prefix | Role | Appears in Purchase Orders |
|------|--------|------|---------------------------|
| **HDR Consumable** | 40* | What's consumed at HDR/IKC | ❌ No |
| **WSKU** | 41* | What's ordered from warehouse | ✅ Yes |

Each 40\* item is linked 1:1 to at least one 41\* WSKU via the `hdr_consumable_item_number` field on the 41\* item. One 40\* can have multiple 41\* WSKUs (different pack sizes), but only ONE is "active for ordering."

## Analysis Rules

| Analysis Type | Use |
|---------------|-----|
| Consumption at kitchen level | 40\* items |
| Procurement and ordering | 41\* items |
| Link them | `41*.hdr_consumable_item_number = 40*.item_number` |

## The Pack Relationship Chain

The 40/41 model connects to packaged items (88\*) through a supply chain:

```
88* PACKAGED ← fulfillment option ← 41* WSKU ← linked ← 40* HDR CONSUMABLE
```

When dormanting an 88\* item, the 5-step decision tree (MD-17876) must consider whether it's the sole fulfillment option for a 41\* that feeds an active 40\* consumable in live menus. Dormanting the wrong 88\* silently breaks the kitchen supply chain.

## Key States and Actions

### Activate for Ordering
A 41\* WSKU must have "Active for Ordering" toggled before the paired 40\* can be ordered. Both items must be published.

### Hot Holding
40\* items carry hot holding instructions: retherm appliance/time, holding appliance/time, batch limits. These feed into IKC station operations.

### Dormant Rules
- **40\*/41\* excluded from automated weekly bulk dormant job** — must be dormanted manually
- 41\* cannot be dormanted while `active_for_ordering = true` AND linked 40\* not yet dormant
- Dormanting 41\* triggers nutrition recalculation of linked 40\*
- Post-cutover: 41\* items no longer dormanted separately — managed through the 40\* item

### Sold Status
WSKU (41\*) has no direct service date source. Its Sold Status inherits from the linked 40\* HDR Consumable.


## Common Pitfall

**Using 40\* for procurement analysis**: 40\* items don't appear in purchase orders or inventory receipts. Always use 41\* items for ordering/procurement queries, and link back to 40\* for consumption context.

## Related

- [[Cookbook Item Taxonomy]] — 40\* and 41\* in the object type system
- [[Cookbook Item Lifecycle]] — special dormant rules for 40\*/41\*
- [[Cookbook Sold Status]] — WSKU inheritance from parent 40\*
- [[Cookbook Wonder Create]] — 40\* items as primary WC component type
- [[Z01-Resource/CB-business/core/item-lifecycle.md]] — 88\* dormant 5-step tree
- [[Z01-Resource/CB-bigquery/SKILL.md]] Section on 40 Model — BQ query patterns
