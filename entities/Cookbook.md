---
title: Cookbook
date: 2026-05-29
created: 2026-05-29
updated: 2026-05-29
type: entity
domain: cookbook
tags:
  - bigquery
  - cookbook
  - recipe-management
status: active
description: Wonder's recipe and BOM management system. Defines what goes into every menu item, from ingredients and quantities to kitchen prep instructions and availability logic.
sources:
  - Z01-Resource/CB-bigquery/SKILL.md
  - Z01-Resource/CB-business/README.md
  - Z01-Resource/CB-bigquery/schema-reference.md
  - Z01-Resource/CB-business/core/bom-structure.md
  - Z01-Resource/CB-business/core/item-and-object-type.md
  - Z01-Resource/CB-business/core/item-lifecycle.md
author: bonnie
---

# Cookbook

Cookbook is Wonder's central master data system for recipe and Bill of Materials (BOM) management. It is the single source of truth for every item Wonder produces and sells — menu items, ingredients, packaged goods, HDR consumables, and non-food supplies.

## What Cookbook Manages

Cookbook tracks **items** — the atomic units of master data. Every item has a unique `item_number`, a lifecycle status, and a version history. Items are classified by `object_type` into 9 categories (see [[Cookbook Item Taxonomy]]).

For each item, Cookbook stores:

| Data | What it defines |
|------|----------------|
| **BOM (Bill of Materials)** | Which components go into this item, in what quantities, and which are required vs optional |
| **Line Build** | Kitchen execution instructions — stations, appliances, timing, sequence |
| **Customization** | Customer-facing choices (proteins, toppings, removals) and pricing |
| **Nutrition** | Calories, macros, allergens — auto-calculated from BOM |
| **Cost & Price** | Standard costs, rolled-up BOM costs, menu prices |
| **Sold Status** | Whether this item is currently being sold (system-calculated daily) |
| **Food Science** | Shelf life, storage requirements, thaw/cook times |

## Cookbook's Role in Wonder

Cookbook sits between culinary R&D (who design the food) and downstream operational systems (who execute):

```
Culinary Engineering → Cookbook → Kitchen Display System (KDS)
                                 → Consumer App (menus, nutrition, customization)
                                 → Pantry (inventory availability)
                                 → OrderGrid / Procurement
                                 → SPORK (warehouse fulfillment)
                                 → ERP (financials)
```

Every other system reads Cookbook as its source of truth. If a BOM is wrong in Cookbook, availability checks fail, nutrition labels are incorrect, and kitchens can't execute.

## The Two Knowledge Bases

The vault contains two complementary reference sets:

| Reference | Focus | Location |
|-----------|-------|----------|
| **CB-bigquery** | SQL query patterns, table schemas, pitfalls, cross-system joins | [[Z01-Resource/CB-bigquery/SKILL.md]] |
| **CB-business** | Business rules, product logic, feature specifications, object type rules | [[Z01-Resource/CB-business/README.md]] |

CB-bigquery tells you *how to query* the data. CB-business tells you *what the data means*.

## BigQuery Data

Cookbook data spans **4 BigQuery datasets** with **70+ tables**:

- `secure-recipe-prod.recipe_v2` — Primary dataset (sensitive item/recipe/cost data, 13 tables)
- `wonder-recipe-prod.recipe_v2` — Non-sensitive attributes, tags, menus, customization (21 tables)
- `wonder-recipe-prod.mongo_batch_recipe_v2` — Mappings, reference data, unit conversions (40+ tables)
- `wonder-raw-prod.mysql_batch_product_catalog` — Product catalog, SKU mappings (8 tables)

**Most queried table**: `effective_items` (48k+ queries/month) — a pre-filtered view of currently active items.

See [[Cookbook BigQuery Query Patterns]] for the essential filters and common query patterns.

## Key Numbers

| Prefix | Object Type | Examples |
|--------|-------------|----------|
| `3*` | BY_PRODUCT | Secondary production outputs |
| `40*` | HDR_CONSUMABLE_ITEM | Consumed at IKC locations |
| `41*` | WSKU | Orderable warehouse SKU |
| `50*` | INGREDIENT | Raw food ingredients |
| `7*` | HDR_RECIPE | IKC-specific recipes |
| `80*` | MENU or RECIPE | Customer-facing dishes + production recipes |
| `88*` | PACKAGED | Pre-packaged goods |
| `90*` | NON_FOOD | Packaging, smallwares, equipment |

## Related

- [[Cookbook Item Taxonomy]] — full object type classification
- [[Cookbook BOM Structure]] — Bill of Materials hierarchy and rules
- [[Cookbook Item Lifecycle]] — item and version status transitions
- [[Cookbook BigQuery Query Patterns]] — SQL patterns and common pitfalls
- [[Cookbook Customization]] — customer choice system
- [[Cookbook Line Build]] — kitchen execution blueprints
- [[Cookbook Sold Status]] — system-calculated sales status
- [[Cookbook Version Publish]] — publish validation workflow
- [[Cookbook Wonder Create]] — automated item creation
- [[Cookbook 40-41 Model]] — HDR consumables and WSKUs
