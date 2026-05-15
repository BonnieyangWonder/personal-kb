# Wonder Kitchen Ops - Schema Reference

## Overview

This document provides detailed schema information for tables related to kitchen batching operations. Batching data spans multiple systems: CookBook (configuration), sequencing contexts (runtime state), optimizer tables (results), and operational execution data.

## Primary Data Sources

| System | Project | Purpose |
|--------|---------|---------|
| Sequencing Contexts | `wonder-raw-prod.mongo_batch_cooking_optimization` | Runtime kitchen state with batching criteria |
| Sequencing Results | `wonder-dw-prod-brd.orders` | Optimizer output with batch assignments |
| Operational Execution | `wonder-dw-prod-brd.orders` | Actual kitchen execution data (hdr_kitchen_pod_item) |
| CookBook | `secure-recipe-prod.recipe_v2` | Item definitions, BOMs, linebuild batch configuration |

---

## item_line_builds (CookBook) - BATCH CONFIGURATION SOURCE

**Location**: `secure-recipe-prod.recipe_v2.item_line_builds`

**Purpose**: Kitchen procedure steps and **batch configuration** for menu items. **This is the source of truth for batch eligibility settings.**

### Key Fields

```sql
item_number                    STRING   -- Menu item number
status                         STRING   -- LINE_BUILD_CREATED (deployed), PENDING_UPDATE (future changes)
procedures_cooking_phase       STRING   -- NULL or 'COOKING'
procedures_activity            STRING   -- COOK, GARNISH, COMPLETE
procedures_appliance           STRING   -- FRYER, TURBO_OVEN, etc.
sub_steps_order                INTEGER  -- Step sequence (CRITICAL: only order=1 has batch config)
sub_steps_title                STRING   -- Human-readable step description
sub_steps_related_item_number  STRING   -- Batch component item number (NULL = batchable only with identical option values)
procedures_batch_limit         INTEGER  -- Maximum items per batch
cooking_time                   STRING   -- Cook duration (format: 'MM:SS')
is_hot_hold_eligible_selected  BOOLEAN  -- Hot hold eligible flag
service_start_time             DATETIME -- When this line build version becomes active
service_end_time               DATETIME -- When this line build version expires
```

### Critical Batch Configuration Rules

1. **Only substep 1 contains batch configuration** - `sub_steps_order = 1` has the batch settings; subsequent substeps (2, 3+) are post-cook activities
2. **NULL `sub_steps_related_item_number` allows limited batching** - Items with NULL can batch only with identical option values (e.g., Wing Trip wings batch by matching sauce/flavor only)
3. **Status filters**: Use `status = 'LINE_BUILD_CREATED'` for deployed config, `status = 'PENDING_UPDATE'` for future changes
4. **Service window**: Filter by `service_start_time` and `service_end_time` to get active configurations

### Query Patterns

#### Get Batch Configuration for Fryer Items (Deployed Only)

```sql
SELECT DISTINCT
  ilb.item_number,
  ilb.sub_steps_related_item_number AS batch_item_number,
  ilb.procedures_batch_limit AS batch_limit,
  ilb.cooking_time,
  ilb.is_hot_hold_eligible_selected AS hot_hold_eligible,
  CASE
    WHEN ilb.sub_steps_related_item_number IS NULL THEN 'Not Batchable'
    ELSE 'Batchable'
  END AS batch_type,
  DATE(ilb.service_start_time) AS version_start,
  DATE(ilb.service_end_time) AS version_end
FROM `secure-recipe-prod.recipe_v2.item_line_builds` ilb
WHERE ilb.status = 'LINE_BUILD_CREATED'
  AND DATE(ilb.service_end_time) >= CURRENT_DATE()
  AND ilb.procedures_appliance = 'FRYER'
  AND ilb.procedures_activity = 'COOK'
  AND ilb.sub_steps_order = 1  -- CRITICAL: Only substep 1 has batch config
ORDER BY ilb.sub_steps_related_item_number NULLS LAST, ilb.cooking_time;
```

#### Get Component Names for Batch Items

```sql
SELECT
  ilb.sub_steps_related_item_number AS batch_item_number,
  iv.name AS batch_component_name,
  ilb.item_number AS menu_item_number,
  mi.name AS menu_item_name
FROM `secure-recipe-prod.recipe_v2.item_line_builds` ilb
LEFT JOIN `secure-recipe-prod.recipe_v2.item_versions` iv
  ON ilb.sub_steps_related_item_number = iv.item_number
  AND iv.effective = TRUE
  AND iv.deleted = FALSE
LEFT JOIN `wonder-dw-prod-brd.restaurants.menu_items` mi
  ON ilb.item_number = mi.item_number
WHERE ilb.status = 'LINE_BUILD_CREATED'
  AND ilb.procedures_appliance = 'FRYER'
  AND ilb.sub_steps_order = 1
  AND ilb.sub_steps_related_item_number IS NOT NULL;
```

---

## hdr_kitchen_pod_item - OPERATIONAL BATCHING DATA

**Location**: `wonder-dw-prod-brd.orders.hdr_kitchen_pod_item`

**Purpose**: Actual kitchen execution data showing which items were cooked together in practice.

### Key Fields for Batching Analysis

```sql
cooking_task_item_id    STRING   -- Individual item cooking task ID
batch_id                STRING   -- Batch identifier (items with same batch_id cooked together)
items_in_batch          INTEGER  -- Number of items in this batch
resource_type           STRING   -- FRYER, TURBO_OVEN, etc.
order_placed_time       TIMESTAMP -- When order was placed
order_number            STRING   -- Order identifier
```

### Proper Batch Definition

Items are considered "actually batched" when **BOTH** conditions are true:
```sql
WHERE CAST(items_in_batch AS INT64) > 1
  AND batch_id != cooking_task_item_id
```

**Why both conditions matter**:
- `items_in_batch > 1`: Indicates multiple items in the batch
- `batch_id != cooking_task_item_id`: Distinguishes actual batches from solo items (where batch_id = cooking_task_item_id)

Without both conditions, you'll get false positives (solo items counted as "batches").

### Operational Batching Query

```sql
SELECT
  kpi.batch_id,
  kpi.resource_type,
  CAST(kpi.items_in_batch AS INT64) as batch_size,
  COUNT(DISTINCT kpi.cooking_task_item_id) as item_count,
  COUNT(DISTINCT kpi.order_number) as order_count
FROM `wonder-dw-prod-brd.orders.hdr_kitchen_pod_item` kpi
WHERE kpi.resource_type = 'FRYER'
  AND DATE(kpi.order_placed_time, 'America/New_York') >= '2026-01-31'
  AND CAST(kpi.items_in_batch AS INT64) > 1
  AND kpi.batch_id != kpi.cooking_task_item_id
GROUP BY kpi.batch_id, kpi.resource_type, batch_size
ORDER BY batch_size DESC;
```

---

[Rest of schema-reference.md content continues with sequencing_contexts, optimizer_batch, bom_lines, item_versions, appliance configs, timezone handling, etc.]
