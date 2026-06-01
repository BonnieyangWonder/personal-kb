---
title: Cookbook Version Publish
date: 2026-05-29
created: 2026-06-01
updated: 2026-06-01
type: concept
domain: cookbook
tags:
  - cookbook
  - item-lifecycle
status: active
description: Publishing workflow — 7-stage validation pipeline, Affect Immediately vs Affect Later, version copy rules, and sub-item dependency requirements.
sources:
  - Z01-Resource/CB-business/features/version-publish.md
author: bonnie
---

# Cookbook Version Publish

Publishing commits a Draft version to a service window, making it the authoritative record for all downstream systems. Two decisions determine the outcome:

1. **When** — immediately or at a future date?
2. **Does it pass** — all required validation checks?

## Version Status Lifecycle

```
DRAFT ── (publish, future date) ──► SCHEDULED ── (time elapses) ──► FINAL
DRAFT ── (publish immediately) ─────────────────────────────────────► FINAL
SCHEDULED ── (item dormanted) ──► DRAFT
```

| Status | effective flag | Downstream visibility |
|--------|---------------|----------------------|
| Draft | false | Hidden (unless only version) |
| Scheduled | false (until start time) | Visible as upcoming change |
| Final | true (when active) | Fully visible to all systems |

## Affect Immediately vs Affect Later

| | Affect Immediately | Affect Later |
|---|---|---|
| **Service start** | Exact publish moment | Future date (user picks) |
| **Results in** | FINAL | SCHEDULED |
| **Item becomes** | ACTIVE | Stays as-is |
| **Available when** | No existing live FINAL version | Default; greyed out for first-ever publish |
| **Use case** | Emergency fixes, first publish | Planned menu changes, seasonal swaps |

## 7-Stage Publish Validation

| Stage | Type | Key Checks |
|-------|------|------------|
| **0. Pre-Conditions** | Hard block | Only one Draft; no existing Scheduled; not a byproduct |
| **1. ERP Information** | Hard block | ERP info filled in (truck/commissary/ingredient items) |
| **2. Inline Completeness** | Hard block | No deleted/dormant sub-items; customization completeness; benchtop sub-items blocked |
| **3. Validation Score** | Hard block (required) | Background validation: required fields must pass; optional fields get warning |
| **4. Sub-Item Publish** | Hard block | All sub-items must be FINAL or SCHEDULED |
| **5. 40-Model Integrity** | Hard block | Every 40* must have active-for-ordering 41* |
| **6. Time Alignment** | Hard block | Ingredient start ≤ parent start; service start must be future |
| **7. Warnings** | User override | Missing concept; missing ERP (warning level); customization changes |

## Sub-Item Dependencies

**Core rule**: Sub-items must be published before parents. This cascades:
- To publish a MENU item → all PACKAGED/INGREDIENT sub-items must be FINAL or SCHEDULED
- To publish a PACKAGED item → all INGREDIENT sub-items must be FINAL or SCHEDULED

**Ingredient constraints are stricter**: ingredient sub-items cannot have a service start time later than the parent's.

## Version Copy Rules

Creating a new version does a **deep copy** of all data (BOM, customization, line build, nutrition, costs) into a new Draft. Reset: version ID incremented, new UUID, status = DRAFT, service times cleared to placeholder.

**Constraint**: Only one Draft at a time. No new version if Scheduled exists. NON_FOOD items cannot have new versions.

## Co-Publish Rules

- **Preset menu items**: Published with parent MENU item (async if > 5 presets)
- **By-products**: Published as part of parent Recipe
- All other sub-items must be published independently first

## Related

- [[Cookbook Item Lifecycle]] — item/version status relationship
- [[Cookbook BOM Structure]] — sub-item validation in BOM context
- [[Cookbook Wonder Create]] — bypasses standard checklist via `ignoreCheck=true`
- [[Z01-Resource/CB-business/features/version-publish.md]] — full reference
