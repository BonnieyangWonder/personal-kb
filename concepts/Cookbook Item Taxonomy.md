---
title: Cookbook Item Taxonomy
date: 2026-05-29
created: 2026-06-01
updated: 2026-06-01
type: concept
domain: cookbook
tags:
  - cookbook
  - item-lifecycle
  - recipe-management
status: active
description: Classification system for all Cookbook items — object types, item number prefixes, sub-types, and business roles.
sources:
  - Z01-Resource/CB-business/core/item-and-object-type.md
  - Z01-Resource/CB-bigquery/SKILL.md
  - Z01-Resource/CB-bigquery/schema-reference.md
author: bonnie
---

# Cookbook Item Taxonomy

Every entity in Cookbook is an **item**. Items are classified by `object_type` (primary) and `object_sub_type` (secondary), with item number prefixes that encode the type.

## Object Types

| BQ `object_type` | New API | Prefix | Role |
|------------------|---------|--------|------|
| `MENU` | `MENU_ITEM` | 80* | Finished dish sold to customers |
| `RECIPE` | `RECIPE_ITEM` | 80* | Sub-recipe or prep component (not sold directly) |
| `HDR_RECIPE` | `HDR_RECIPE_ITEM` | 7* | IKC-specific recipe |
| `PACKAGED` | `PACKAGED_ITEM` | 88* | Pre-packaged goods from commissary/supplier |
| `INGREDIENT` | `INGREDIENT_ITEM` | 50* | Raw ingredient linked to Vendor SKUs |
| `BY_PRODUCT` | `BY_PRODUCT_ITEM` | 30* | Secondary output from production |
| `HDR_CONSUMABLE_ITEM` | `HDR_CONSUMABLE_ITEM` | 40* | Consumed at IKC locations |
| `WSKU` | `WSKU_ITEM` | 41* | Warehouse SKU (orderable unit) |
| `NON_FOOD` | `NON_FOOD_ITEM` | 90* | Packaging, smallwares, equipment |

**80* collision**: Both MENU and RECIPE use 80*. Distinguish by `object_type` field, not item number.

## Key Properties

Every item has: `item_number`, `object_type`, `object_sub_type`, `item_status` (R&D/ACTIVE/DORMANT), `name`, `version_id`, `version_status` (DRAFT/SCHEDULED/FINAL), `effective` flag, and `deleted` flag.

Items are **versioned** — editing creates a new Draft without touching the live Final version. See [[Cookbook Item Lifecycle]].

## Item Number Identification in SQL

```sql
CASE 
  WHEN CAST(item_number AS STRING) LIKE '88%' THEN 'PACKAGED'
  WHEN CAST(item_number AS STRING) LIKE '80%' THEN 'MENU_OR_RECIPE'
  WHEN CAST(item_number AS STRING) LIKE '41%' THEN 'WSKU'
  WHEN CAST(item_number AS STRING) LIKE '40%' THEN 'HDR_CONSUMABLE'
  WHEN CAST(item_number AS STRING) LIKE '7%'  THEN 'HDR_RECIPE'
  WHEN CAST(item_number AS STRING) LIKE '5%'  THEN 'INGREDIENT'
  WHEN CAST(item_number AS STRING) LIKE '90%' THEN 'NON_FOOD'
  WHEN CAST(item_number AS STRING) LIKE '3%'  THEN 'BY_PRODUCT'
END AS inferred_type
```

For 80\* items, use `object_type` to disambiguate. For 40\* vs 41\*, both start with `4`.

## Sub-Types (RECIPE)

| `object_sub_type` | Description |
|-------------------|-------------|
| `PRIMARY_RECIPE` | Main production recipe |
| `PREPARATION` | Named component prep (single ingredient + prep method) |
| `BYPRODUCT` | Secondary recipe output |
| `BT_PRIMARY` | R&D primary (not yet commercialized) |
| `BT_PREPARATION` | R&D preparation |
| `BT_BYPRODUCT` | R&D byproduct |

BENCHTOP items use the `RECIPE` object type with `BT_*` sub-types. They are R&D phase only and must be commercialized before production use.

## BOM Parent Rules

Only these types can own a BOM: MENU, RECIPE, PACKAGED, BENCHTOP, HDR_RECIPE.

INGREDIENT, NON_FOOD, BY_PRODUCT, WSKU, and HDR_CONSUMABLE_ITEM cannot own BOMs.

For full component-to-parent mapping, see [[Cookbook BOM Structure]].

## Related

- [[Cookbook]] — system overview
- [[Cookbook BOM Structure]] — which types can be components
- [[Cookbook Item Lifecycle]] — status workflow
- [[Cookbook 40-41 Model]] — HDR consumable and WSKU details
- [[Z01-Resource/CB-business/core/item-and-object-type.md]] — full reference
