---
title: Cookbook BOM Structure
date: 2026-05-29
created: 2026-06-01
updated: 2026-06-01
type: concept
domain: cookbook
tags:
  - cookbook
  - recipe-management
status: active
description: Bill of Materials hierarchy, versioning, component rules, and the manage_inventory availability gate in Cookbook.
sources:
  - Z01-Resource/CB-business/core/bom-structure.md
  - Z01-Resource/CB-bigquery/SKILL.md
  - Z01-Resource/CB-bigquery/schema-reference.md
author: bonnie
---

# Cookbook BOM Structure

A BOM (Bill of Materials) defines exactly which component items — with quantities and units — are required to produce one inventory unit of a parent item. It is the formal recipe specification that drives **availability logic, cost rollup, nutrition rollup, and kitchen preparation**.

## Hierarchy

Every BOM has:

- **BOM Header** — anchors the BOM to an item version. One active header per item version.
- **BOM Lines** — individual component rows (item + quantity + UOM). Each component appears once per BOM.

BOMs are **recursive** — a component can itself have a BOM, creating a multi-level tree (typically 3-4 levels at Wonder). Recursive CTEs expand the full tree in BigQuery.

## The `manage_inventory` Field

**THE KEY FIELD** for availability analysis:

| Value | Impact | Examples |
|-------|--------|----------|
| `true` | **REQUIRED** — item unavailable if out of stock | Proteins, sauces |
| `false` | **OPTIONAL** — doesn't affect availability | Packaging, garnishes |

> Only `manage_inventory = true` components block menu item availability. Always filter on this when checking why an item is out of stock.

## Allowed Component Types Per Parent

| Parent | Allowed Components |
|--------|-------------------|
| MENU (80*) | RECIPE, INGREDIENT, PACKAGED, NON_FOOD, HDR_RECIPE, WSKU, HDR_CONSUMABLE_ITEM (40*), BY_PRODUCT, BENCHTOP |
| PACKAGED (88*) | RECIPE, INGREDIENT, PACKAGED, NON_FOOD, BY_PRODUCT, BENCHTOP |
| RECIPE (80*) | RECIPE, INGREDIENT, NON_FOOD, BY_PRODUCT, BENCHTOP |
| HDR_RECIPE (7*) | RECIPE, INGREDIENT, PACKAGED, WSKU, HDR_CONSUMABLE_ITEM (40*), NON_FOOD, BY_PRODUCT, BENCHTOP |

Cannot own BOMs: INGREDIENT, NON_FOOD, BY_PRODUCT, WSKU, HDR_CONSUMABLE_ITEM.

## BOM Versioning

BOM versions are **independent of item versions**. A BOM version has:
- **ERP Status**: New (not finalized) or Published (finalized)
- **Effective Start Date**: Always a future date at creation
- **Operational status**: Scheduled (future) → Held (past, not published) → Released (past, published)

Packaged items (88*) can have **two BOMs**: a commercial BOM (production) and a benchtop BOM (R&D). When commercialized, the commercial BOM is overridden in full.

## BOM Validation Rules

| Situation | Severity |
|-----------|----------|
| BOM missing entirely (and "No BOM" not set) | Error/Warning |
| "No BOM" toggle is TRUE but no Mandatory Choice customization | Error |
| Component version inactive (ingredient) | Blocking error |
| Component version inactive (non-ingredient) | Warning |
| 88* consumable with non-integer quantity | Error |

The **"No BOM" toggle** (`noBom = true`) means an item intentionally has no BOM and relies entirely on Customization.

## Primary Query Pattern (Nested JSON)

```sql
SELECT
  m.item_number, m.name,
  JSON_VALUE(bom_line, '$.item_number') AS component_item,
  SAFE_CAST(JSON_EXTRACT_SCALAR(bom_line, '$.quantity') AS FLOAT64) AS quantity,
  JSON_VALUE(bom_line, '$.uom') AS uom
FROM `secure-recipe-prod.recipe_v2.item_versions` m,
UNNEST(JSON_EXTRACT_ARRAY(m.bom_header, '$.bom_lines')) AS bom_line
WHERE m.effective = true AND m.deleted = false
  AND m.item_status != 'DORMANT'
  AND m.item_number = '8009068';
```

Use the separate `bom_headers`/`bom_lines` tables for cross-item analysis or historical queries. For single-item lookups, **prefer the nested JSON pattern**.

## Cross-System Connections

- **Cost Rollup**: Costs propagate up the BOM tree. Parent `per_bom_unit_cost` aggregates line costs.
- **Nutrition Rollup**: Ingredient nutrition values × BOM quantities = menu item nutrition.
- **Line Build Mapping**: BOM changes trigger "Pending Update" status on line builds.
- **Customization Mapping**: Customizations reference items that may appear in the BOM. Base BOM defines defaults; Customization defines guest choices.

## Related

- [[Cookbook]] — system overview
- [[Cookbook Item Taxonomy]] — object type rules for BOM components
- [[Cookbook Item Lifecycle]] — how item status affects BOM validity
- [[Cookbook BigQuery Query Patterns]] — SQL pitfalls for BOM queries
- [[Z01-Resource/CB-business/core/bom-structure.md]] — full reference
