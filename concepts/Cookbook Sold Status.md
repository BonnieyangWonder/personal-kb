---
title: Cookbook Sold Status
date: 2026-05-29
created: 2026-06-01
updated: 2026-06-01
type: concept
domain: cookbook
tags:
  - cookbook
  - item-lifecycle
status: active
description: System-calculated sales status — the 4 status values, 8 data sources by item type, daily batch calculation, and special inheritance cases.
sources:
  - Z01-Resource/CB-business/features/sold-status.md
author: bonnie
---

# Cookbook Sold Status

Sold Status answers: **"Is this item currently being sold, or scheduled to be sold?"** It is always system-calculated — users cannot set or override it. Updated once per day at 00:15 AM New York time.

## The Four Values

| Status | Meaning |
|--------|---------|
| **For Sale** | Service date ≤ today (NY 23:59), version is Final |
| **Scheduled** | Earliest service date is still in the future |
| **Not Sold** | No service signals, version is Draft, or already expired |
| **N/A** | This item type is never sold to customers |

Sold Status is at the **version level** — different versions can have different statuses.

## Data Sources by Item Type

| Item Type | Signal Source |
|-----------|--------------|
| **Menu Item** (80*) | Active menu scheduling system |
| **HDR Consumable** (40*) | IKC scope system + internal demand |
| **HDR Recipe** (7*) | IKC scope + internal demand |
| **Packaged Item** (88*) | CK production tasks + raw material fulfillment |
| **Recipe** (80*) | CK production tasks |
| **Ingredient** (50*) | Raw material fulfillment |
| **Non-food** (90*) | Purchase orders (ShipHero) |
| **B2B items** | Simplified — no service dates required |

Calculation window: **14 days past to 180 days future** (configurable).

## Determination Order

1. Draft? → **Not Sold**
2. Expired? → **Not Sold**
3. No service signals? → **Not Sold**
4. Version is Scheduled? → **Scheduled**
5. Earliest service date ≤ today? → **For Sale**; else → **Scheduled**

## Special Inheritance Cases

| Case | Rule |
|------|------|
| **WSKU (41*)** | Inherits from linked 40* HDR Consumable |
| **B2B items** | If Final and not expired → For Sale |
| **SCC WSKU (42*)** | Always N/A |
| **Byproduct (30*)** | Aggregated from parent items |
| **Benchtop** | Inherits from commercialized production item |
| **Non-food sub-types** | Marketing, Smallware, Equipment, PPE, Sanitation, Storage, Appliance, Vessel → always N/A |

## Update Mechanism

Daily batch job at 00:15 AM NY. Only writes back to items whose status actually changed. Can be triggered manually for urgent refreshes.

## Common Pitfall

Sold Status ≠ Item Status. An ACTIVE item with no service signals is NOT_SOLD. A DORMANT item can have its last Final version showing FOR_SALE until the next batch recalculation.

## Related

- [[Cookbook Item Lifecycle]] — item status vs sold status distinction
- [[Cookbook 40-41 Model]] — WSKU inheritance from HDR Consumable
- [[Z01-Resource/CB-business/features/sold-status.md]] — full reference
