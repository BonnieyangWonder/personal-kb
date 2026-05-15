---
name: wonder-kitchen-ops
description: Expert knowledge of Wonder's kitchen operations including batching eligibility, fryer batching criteria, and kitchen workflow optimization. Covers the relationship between CookBook BOM, linebuild, and sequencing batch assignments.
allowed-tools: Read, Grep, Glob, Bash
---

# Wonder Kitchen Operations Skill

This skill provides expertise in Wonder's kitchen operations systems, with a primary focus on **batching** - how items are grouped together for efficient preparation in HDR kitchens. It bridges CookBook configuration, KDS sequencing, and kitchen execution.

## What This Skill Provides

- **Batching eligibility analysis** - Understand why items can or cannot batch together
- **Batch criteria lookup** - Query the four batching eligibility fields from sequencing contexts
- **CookBook-to-sequencing mapping** - Trace how BOM components become batch_eligible_item_id
- **Fryer batching patterns** - Analyze the most common batching scenario (fryer items)
- **Cross-system data tracing** - Connect CookBook, sequencing contexts, and optimizer tables

## When to Use This Skill

Use this skill when you need to:

1. **Investigate why items didn't batch together** - Check the four eligibility criteria
2. **Understand batch_eligible_item_id values** - Trace back to CookBook components
3. **Analyze fryer batching patterns** - Most common batching use case
4. **Debug batching issues** - When items should batch but don't (or vice versa)
5. **Query batching data from sequencing contexts** - Extract eligibility fields from JSON
6. **Understand the relationship between sauces and wings** - Why different sauces create different batch groups

## Core Concepts

### The Four Batching Eligibility Criteria

For items to batch together, they must match on ALL FOUR criteria:

| Criterion | Field in Sequencing Context | Description |
|-----------|----------------------------|-------------|
| **Pod ID** | `$.active_pod_id` | Items must be on the same pod |
| **Appliance Config ID** | `$.steps[].resource_config_id` | Items must use same appliance configuration |
| **Batch Item Number** | `$.steps[].batch_eligible_item_id` | Component identifier (**FRYER-SPECIFIC** - see note below) |
| **Cook Time** | `$.steps[].step_time_seconds` | Items must have same cook duration |

**Important**: The `batch_eligible_item_id` field is **specifically for FRYER batching**. It's an abstracted ID ensuring fryer items are compatible for batching together. Turbo ovens and other appliances use `resourceConfig` (temperature/windspeed settings) for batch eligibility instead.

**Batch Limits**:
- **Physical batch limit** (`batch_limit` field): Maximum items per batch based on appliance capacity (ranges 1-9 depending on item type - e.g., chicken sandwiches can batch up to 9, fries up to 4)
- **Operational reality**: Despite physical limits, actual batches are typically 2-3 items (most common), occasionally 4-5 items (rare), max observed is 5. The sequencer doesn't inherently push toward maximum batch sizes.

**Exclusion rule**: Items with `hot_hold_eligible = true` are NOT batch-eligible regardless of other criteria.

### Why Items Sometimes Don't Batch (CP-SAT Behavior)

**Critical insight**: The CP-SAT sequencer **does not inherently value batching**. It only batches items when:
- Queue load forces batching due to capacity constraints
- Time constraints (customer promise) make batching necessary

This means you may see items that are **eligible** to batch but weren't **actually** batched. The system optimizes for customer promise and expo wait time, not batching efficiency.

### Potential vs Actual Batches

| Concept | Data Source | Description |
|---------|-------------|-------------|
| **Potential Batches** | `sequencing_contexts` (kitchen_context JSON) | Items that COULD batch based on four criteria |
| **Actual Batches** | `hdr_kitchen_order_sequencing_optimizer_batch` | Items the optimizer ACTUALLY grouped together |

When investigating batching issues, check both: items may be eligible but not batched due to CP-SAT optimization decisions.

### Batch Scoring & Prioritization

The sequencer uses **bucket-based prioritization** with multi-objective scoring:

| Bucket | Description | Priority |
|--------|-------------|----------|
| **Bucket 1** | Tasks for items already cooking | Highest |
| **Bucket 2** | Tasks where order has started but this item hasn't | Medium |
| **Bucket 3** | Tasks for completely unstarted orders | Lowest |

**Multi-Objective Score Formula** (Conceptual Model):
```
Full Score = Expo_Score + Promise_Score + Batch_Score
```

Where:
- **Expo Score**: `W_ex × (Buffer - (T_f - T_i))` - penalizes expo sit time
- **Promise Score**: `W_cp × -(late penalty)` - penalizes customer promise lateness
- **Batch Score**: `W_b × (N_batch - 1)` - rewards larger batches

Default weights: `W_ex=1`, `W_cp=0.5`, `W_b=0.5` (1 min expo = 2 min late = 2 concurrent orders)

### Data Flow: CookBook to Sequencing

```
CookBook BOM (bom_lines)
    ↓ bom_line_item_number (sauce component)
Sequencing Context (kitchen_context JSON)
    ↓ batch_eligible_item_id
Optimizer Batch Table (optimizer_batch)
    ↓ group_id, pod_id
KDS Screen (batch groups displayed)
```

### Key Tables

**Eligibility & Context Tables** (determine what CAN batch):

| Table | Purpose | Key Fields |
|-------|---------|------------|
| `wonder-raw-prod.mongo_batch_cooking_optimization.sequencing_contexts` | Input kitchen state with batching criteria | `kitchen_context` (JSON) |

**Optimizer Output Tables** (show what DID batch):

| Table | Purpose | Key Fields |
|-------|---------|------------|
| `wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing_optimizer` | Item-level sequencing results | `order_number`, `item_id`, `context_id` |
| `wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing_optimizer_batch` | Actual batch group assignments | `group_id`, `pod_id`, `item_id` |

**Reference/Mapping Tables** (for lookups, NOT eligibility criteria):

| Table | Purpose | Key Fields |
|-------|---------|------------|
| `secure-recipe-prod.recipe_v2.bom_lines` | Map item IDs to names; does NOT define batching rules | `bom_line_item_number`, `bom_header_item_number` |
| `secure-recipe-prod.recipe_v2.item_versions` | Item metadata (names, types) | `item_number`, `name`, `object_type` |
| `secure-recipe-prod.recipe_v2.item_line_builds` | Kitchen procedure steps (batch_limit defined here) | `procedures_batch_limit` |

> **Warning**: Do not use `bom_lines` to determine batching eligibility. Use it only as a dictionary to map item IDs to human-readable names. Actual batching criteria come from `sequencing_contexts`.

### Understanding batch_eligible_item_id

The `batch_eligible_item_id` field represents the **component that determines batching** - often a sauce or flavor variant for fried items.

**Example: Wing flavors**
| batch_eligible_item_id | Component Name | Menu Items Using It |
|------------------------|----------------|---------------------|
| 4000534 | Buffalo Sauce, Trappys HC | Buffalo Wings (6pc, 12pc, boneless, classic) |
| 4000536 | Sweet and Sticky Sauce | BBQ Wings, BBQ Fries, BBQ Pizza |
| 4000561 | Teriyaki Sauce | Teriyaki Wings (6pc, 12pc, boneless, classic) |
| 4000562 | Garlic Parmesan Sauce | Garlic Parm Wings |
| 4000563 | Honey, Hot (HDR Only) HC | Hot Honey Wings |

**Why sauces matter for batching**: Wings with different sauces have different `batch_eligible_item_id` values, so they CANNOT batch together even if cook time and appliance are identical.

## Query Patterns

### Extract Batching Criteria for an Order

```sql
WITH item_data AS (
  SELECT
    JSON_VALUE(item, '$.id') as item_id,
    JSON_VALUE(item, '$.order_id') as order_id,
    JSON_VALUE(item, '$.active_pod_id') as pod_id,
    item as full_item
  FROM `wonder-raw-prod.mongo_batch_cooking_optimization.sequencing_contexts` ctx,
       UNNEST(JSON_QUERY_ARRAY(ctx.kitchen_context)) AS super_pod_context,
       UNNEST(JSON_QUERY_ARRAY(super_pod_context, '$.items')) AS item
  WHERE ctx._id = 'YOUR_CONTEXT_ID'
),
step_data AS (
  SELECT
    i.item_id,
    i.order_id,
    i.pod_id,
    JSON_VALUE(step, '$.batch_eligible_item_id') as batch_item_number,
    JSON_VALUE(step, '$.hot_hold_eligible') as hot_hold_eligible,
    JSON_VALUE(step, '$.resource_config_id') as appliance_config_id,
    CAST(JSON_VALUE(step, '$.step_time_seconds') AS INT64) as cook_time_seconds,
    CAST(JSON_VALUE(step, '$.batch_limit') AS INT64) as batch_limit,
    JSON_VALUE(step, '$.resource_type') as resource_type
  FROM item_data i,
       UNNEST(JSON_QUERY_ARRAY(i.full_item, '$.steps')) AS step
  WHERE JSON_VALUE(step, '$.cooking_activity') = 'COOK'
)
SELECT * FROM step_data
WHERE order_id = 'YOUR_ORDER_ID'
ORDER BY resource_type, batch_item_number;
```

### Find Menu Items Using a Sauce Component

```sql
SELECT
  bl.bom_line_item_number as sauce_item_number,
  cb.name as sauce_name,
  STRING_AGG(DISTINCT bl.bom_header_item_number, ', ') as menu_item_numbers
FROM `secure-recipe-prod.recipe_v2.bom_lines` bl
LEFT JOIN `secure-recipe-prod.recipe_v2.item_versions` cb
  ON bl.bom_line_item_number = cb.item_number
  AND cb.effective = true AND cb.deleted = false
WHERE bl.bom_line_item_number IN ('4000561', '4000562', '4000534', '4000536', '4000563')
GROUP BY bl.bom_line_item_number, cb.name
ORDER BY bl.bom_line_item_number;
```

### Aggregate Fryer Batching Summary

```sql
WITH item_data AS (
  SELECT
    ctx._id as context_id,
    ctx.hdr_id,
    DATE(ctx.created_time) as context_date,
    JSON_VALUE(item, '$.id') as item_id,
    JSON_VALUE(item, '$.order_id') as order_id,
    item as full_item
  FROM `wonder-raw-prod.mongo_batch_cooking_optimization.sequencing_contexts` ctx,
       UNNEST(JSON_QUERY_ARRAY(ctx.kitchen_context)) AS super_pod_context,
       UNNEST(JSON_QUERY_ARRAY(super_pod_context, '$.items')) AS item
  WHERE DATE(ctx.created_time) >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
),
step_data AS (
  SELECT
    i.item_id,
    i.order_id,
    i.hdr_id,
    JSON_VALUE(step, '$.batch_eligible_item_id') as batch_item_number,
    JSON_VALUE(step, '$.resource_config_id') as appliance_config_id,
    CAST(JSON_VALUE(step, '$.step_time_seconds') AS INT64) as cook_time_seconds,
    CAST(JSON_VALUE(step, '$.batch_limit') AS INT64) as batch_limit
  FROM item_data i,
       UNNEST(JSON_QUERY_ARRAY(i.full_item, '$.steps')) AS step
  WHERE JSON_VALUE(step, '$.cooking_activity') = 'COOK'
    AND JSON_VALUE(step, '$.resource_type') = 'FRYER'
)
SELECT
  s.batch_item_number,
  cb.name as batch_item_name,
  s.appliance_config_id,
  s.cook_time_seconds,
  s.batch_limit,
  COUNT(DISTINCT s.item_id) as unique_items,
  COUNT(DISTINCT s.order_id) as unique_orders,
  COUNT(DISTINCT s.hdr_id) as hdrs
FROM step_data s
LEFT JOIN `secure-recipe-prod.recipe_v2.item_versions` cb
  ON s.batch_item_number = cb.item_number
  AND cb.effective = true AND cb.deleted = false
GROUP BY s.batch_item_number, cb.name, s.appliance_config_id, s.cook_time_seconds, s.batch_limit
ORDER BY unique_items DESC;
```

### Look Up Component Item Details

```sql
SELECT
  item_number,
  name,
  object_type,
  object_sub_type,
  item_status
FROM `secure-recipe-prod.recipe_v2.item_versions`
WHERE item_number IN ('4000053', '4000113', '4000478', '4000534')
  AND effective = true
  AND deleted = false;
```

### Compare Potential vs Actual Batches

Find items that were eligible to batch but weren't actually batched together:

```sql
WITH eligible_items AS (
  -- Extract potential batch groups from sequencing context
  SELECT
    ctx._id as context_id,
    JSON_VALUE(item, '$.id') as item_id,
    JSON_VALUE(item, '$.active_pod_id') as pod_id,
    JSON_VALUE(step, '$.batch_eligible_item_id') as batch_item_number,
    JSON_VALUE(step, '$.resource_config_id') as appliance_config_id,
    CAST(JSON_VALUE(step, '$.step_time_seconds') AS INT64) as cook_time_seconds
  FROM `wonder-raw-prod.mongo_batch_cooking_optimization.sequencing_contexts` ctx,
       UNNEST(JSON_QUERY_ARRAY(ctx.kitchen_context)) AS super_pod_context,
       UNNEST(JSON_QUERY_ARRAY(super_pod_context, '$.items')) AS item,
       UNNEST(JSON_QUERY_ARRAY(item, '$.steps')) AS step
  WHERE DATE(ctx.created_time) = '2026-01-31'
    AND JSON_VALUE(step, '$.cooking_activity') = 'COOK'
    AND JSON_VALUE(step, '$.resource_type') = 'FRYER'
    AND JSON_VALUE(step, '$.hot_hold_eligible') = 'false'
),
actual_batches AS (
  -- Get actual batch assignments from optimizer
  SELECT
    opt.context_id,
    opt.item_id,
    batch.group_id,
    batch.resultant_item_id_count as batch_size
  FROM `wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing_optimizer` opt
  LEFT JOIN `wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing_optimizer_batch` batch
    ON opt._id = batch._id AND opt.item_id = batch.item_id
  WHERE DATE(opt.created_time) = '2026-01-31'
)
SELECT
  e.context_id,
  e.pod_id,
  e.batch_item_number,
  e.appliance_config_id,
  e.cook_time_seconds,
  COUNT(DISTINCT e.item_id) as eligible_count,
  COUNT(DISTINCT a.group_id) as actual_batch_groups,
  MAX(a.batch_size) as largest_actual_batch
FROM eligible_items e
LEFT JOIN actual_batches a ON e.context_id = a.context_id AND e.item_id = a.item_id
GROUP BY e.context_id, e.pod_id, e.batch_item_number, e.cook_time_seconds, e.appliance_config_id
HAVING eligible_count > 1  -- Multiple eligible items
ORDER BY eligible_count DESC;
```

## Best Practices

1. **Always filter by date** - Sequencing contexts table has full history; use `DATE(created_time)` filter
2. **Use context_id for joins** - Join sequencing_contexts._id to optimizer.context_id (NOT optimizer._id)
3. **Filter COOK steps only** - Batching applies to COOK activity, not GARNISH/HANDOFF/COMPLETE
4. **Check hot_hold_eligible** - Items with hot_hold_eligible=true cannot batch
5. **Match ALL FOUR criteria** - Items must match pod, appliance_config, batch_item_number, AND cook_time
6. **Use item_versions for names** - Always join to CookBook item_versions to get human-readable names

## Common Fryer Items

| batch_item_number | Name | Cook Time | Batch Limit |
|-------------------|------|-----------|-------------|
| 4000053 | French Fries | 270s | 3 |
| 4000113 | Chicken Sandwich Filet | 315s | 9 |
| 4000477 | Fully Cooked Chicken Tender | 330-345s | 3-5 |
| 4000478 | Boneless Chicken Wing | 300s | 3 |
| 4000605 | Onion Rings | 135s | 4 |
| 4000606 | Fried Sliced Beef | 135s | 2 |

## Related Skills

- **[wonder-sequencing](../wonder-sequencing/SKILL.md)** - Sequencing optimizer tables, scores, timestamps
- **[wonder-cookbook](../wonder-cookbook/SKILL.md)** - BOM structure, item_versions, component relationships
- **[wonder-pantry](../wonder-pantry/SKILL.md)** - Inventory at HDRs, availability

## Supporting Documentation

- [schema-reference.md](schema-reference.md) - Complete table schemas for batching-related fields
- [common-pitfalls.md](common-pitfalls.md) - Common mistakes when querying batching data
