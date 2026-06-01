---
title: Cookbook BigQuery Query Patterns
date: 2026-05-29
created: 2026-06-01
updated: 2026-06-01
type: concept
domain: cookbook
tags:
  - bigquery
  - cookbook
status: active
description: Essential SQL patterns, critical filters, and common pitfalls for querying Cookbook data in BigQuery.
sources:
  - Z01-Resource/CB-bigquery/SKILL.md
  - Z01-Resource/CB-bigquery/common-pitfalls.md
  - Z01-Resource/CB-bigquery/schema-reference.md
  - Z01-Resource/CB-bigquery/reference/datasets-overview.md
author: bonnie
---

# Cookbook BigQuery Query Patterns

Reference for querying Cookbook data in BigQuery. Covers essential filters, table selection, common pitfalls, and cross-system joins.

## Essential Filter (EVERY QUERY)

```sql
WHERE effective = true
  AND deleted = false
  AND item_status != 'DORMANT'
```

**Critical**: `deleted = false` is required even on `effective_items` — the pre-filtered view does NOT exclude soft-deleted items.

## Table Selection Guide

| Need | Use |
|------|-----|
| Current item lookup | `effective_items` (pre-filtered, fastest) |
| Historical analysis | `item_versions` (full history) |
| Recipe components (single item) | `item_versions` nested JSON BOM |
| Recipe components (cross-item) | `bom_headers` + `bom_lines` |
| Line build instructions | `item_line_builds` |
| Nutrition data | `all_item_version_customization_nutrition` |
| Customization options | `item_customizations_flattened` |

## 4 Datasets

| Dataset | Purpose | Tables |
|---------|---------|--------|
| `secure-recipe-prod.recipe_v2` | Sensitive item/recipe/cost data | 13 |
| `wonder-recipe-prod.recipe_v2` | Non-sensitive attributes, tags, menus | 21 |
| `wonder-recipe-prod.mongo_batch_recipe_v2` | Mappings, units, vendors, reference | 40+ |
| `wonder-raw-prod.mysql_batch_product_catalog` | Product catalog, SKU mappings | 8 |

## Primary BOM Query (Nested JSON)

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

**Prefer nested JSON for single-item BOM lookups.** Use separate `bom_headers`/`bom_lines` only for cross-item analysis or historical queries.

## Separate BOM Tables (Cross-Item)

```sql
SELECT DISTINCT
  bh.item_number as menu_item_id, ei.name,
  bl.bom_line_item_number as component_id,
  ei_comp.name as component_name, bl.manage_inventory as is_required
FROM `secure-recipe-prod.recipe_v2.bom_headers` bh
INNER JOIN `secure-recipe-prod.recipe_v2.bom_lines` bl
  ON bh.item_number = bl.bom_header_item_number
LEFT JOIN `secure-recipe-prod.recipe_v2.effective_items` ei
  ON bh.item_number = CAST(ei.item_number AS STRING) AND ei.deleted = false
LEFT JOIN `secure-recipe-prod.recipe_v2.effective_items` ei_comp
  ON CAST(bl.bom_line_item_number AS STRING) = CAST(ei_comp.item_number AS STRING)
  AND ei_comp.deleted = false
WHERE bh.is_active = true AND bh.item_number = '8009068'
  AND CURRENT_TIMESTAMP() BETWEEN TIMESTAMP(bl.service_start_time) AND TIMESTAMP(bl.service_end_time)
ORDER BY bl.manage_inventory DESC, component_id;
```

## Cross-System Join Reference

| From (Cookbook) | To System | Join Key |
|-----------------|-----------|----------|
| `item_versions` | Pantry inventory | `CAST(item_number AS STRING) = inventory_on_hand.item_number` |
| `bom_lines` | Product Catalog | `CAST(bom_line_item_number AS STRING) = wonder_items.item_number` |
| `effective_items` | Orders | `effective_items.item_number = order_items.sku` |

Datasets: Pantry = `wonder-raw-prod.mysql_batch_inventory`, Product Catalog = `wonder-raw-prod.mysql_batch_product_catalog`, Orders = `wonder-dw-prod-brd.wonder_dw`

## Top 10 Common Pitfalls

1. **Missing `deleted = false`** — returns soft-deleted items (even on `effective_items`)
2. **Wrong BOM pattern** — using separate tables for single-item lookups instead of nested JSON
3. **Missing service window filter** — returns all historical versions of components
4. **Not checking `manage_inventory`** — treats packaging/garnishes as availability blockers
5. **Confusing `version_id` (INT) with `_id` (UUID)** — type mismatch errors
6. **Missing CAST on item numbers** — join failures across tables
7. **INNER JOIN instead of LEFT JOIN** — loses BOM lines without metadata
8. **Using `item_versions` instead of `effective_items`** — slower queries
9. **Not using DISTINCT with item_versions joins** — duplicate rows from multiple versions
10. **Wrong join field: `bom_lines.item_number`** — should be `bom_header_item_number`

### Service Window Filter (ALWAYS ADD)

```sql
AND CURRENT_TIMESTAMP() BETWEEN TIMESTAMP(service_start_time) AND TIMESTAMP(service_end_time)
```

### Always CAST Item Numbers

```sql
CAST(bl.bom_line_item_number AS STRING) = CAST(iv.item_number AS STRING)
```

### Version Status ≠ Item Status

- `version_status`: DRAFT / SCHEDULED / FINAL (publishing workflow)
- `item_status`: R&D / ACTIVE / DORMANT (operational availability)

### Nutrition Values are STRING

```sql
SAFE_CAST(calories_k_cal AS FLOAT64) > 500  -- NOT calories_k_cal > 500
```

## Related

- [[Cookbook]] — system overview
- [[Cookbook BOM Structure]] — BOM query patterns in depth
- [[Z01-Resource/CB-bigquery/common-pitfalls.md]] — full pitfalls reference with SQL examples
- [[Z01-Resource/CB-bigquery/schema-reference.md]] — complete table schemas
- [[Z01-Resource/CB-bigquery/reference/datasets-overview.md]] — all tables per dataset
