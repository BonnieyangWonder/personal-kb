---
name: wonder-command-center
description: Expert knowledge of Wonder's Command Center order splitting system (Splitter service) including order split cache, SKU grouping rules, and rules engine configuration. Useful when the user wants to know WHY an item was placed in a particular order (e.g. Pod C order and not Frozen).
allowed-tools: Read, Grep, Glob
---

# Wonder Command Center Expert

Expert knowledge of Wonder's Command Center **Splitter service** for HDR order optimization and kitchen workflow management.

## What This Skill Provides

- **Complete schema knowledge** for Splitter tables (order_split_cache, sku_grouping_rules, hdr_sku_scope, sku_info)
- **Rules engine expertise** for designing and testing order splitting rules
- **Data scoping patterns** for accurate baseline analysis (NON_FOOD exclusions, item prefix filtering)
- **Iterative rule development** workflow for optimizing order splits
- **Rule effectiveness testing** strategies for validating rule changes

## When to Use This Skill

Use this skill when you need to:
- Analyze current order split assignments (which SKUs go to which orders)
- Design new SKU grouping rules for the rules engine
- Debug why a SKU is assigned to "Global" instead of a specific order
- Optimize HDR order sizes to reduce kitchen complexity
- Understand pod assignments (Pod A, Pod B, Pod C, Pod D)
- Work with frozen item splits or beverage assignments
- Test rule effectiveness before deployment
- Analyze SKU scope forecasts and demand patterns

## Core Concepts

### Database Location
- **BigQuery Dataset**: `wonder-raw-prod.pg_batch_command_center`
- **Access**: Via bq CLI or BigQuery Console

### Business Flow

```
1. Input:        hdr_sku_scope      (forecasted demand: which HDRs order which SKUs)
2. Configuration: sku_grouping_rules (business rules for assignment)
3. Reference:    sku_info           (SKU metadata: storage type, object type)
4. Output:       order_split_cache   (final SKU → order split mapping)
```

### Key Entity Relationships

```
hdr_sku_scope.item_number ↔ sku_info.item_number ↔ order_split_cache.item_sku
hdr_sku_scope.hdr_id ↔ order_split_cache.facility_id
sku_grouping_rules.group_name ↔ order_split_cache.order_split_value
```

For complete schema details, see [schema-reference.md](schema-reference.md).

## Critical Data Scoping Pattern

### ⚠️ Always Clarify Scope Before Analysis

**Problem**: Different SKU prefixes and object types have vastly different operational characteristics. Analyzing the wrong subset leads to incorrect conclusions.

**Discovery Workflow**:
```sql
-- Step 1: Analyze full scope
SELECT
  SUBSTR(item_sku, 1, 2) as sku_prefix,
  COUNT(*) as assignments,
  COUNT(DISTINCT facility_id) as facilities
FROM `wonder-raw-prod.pg_batch_command_center.order_split_cache`
WHERE order_split_value = 'Global'
GROUP BY SUBSTR(item_sku, 1, 2)
ORDER BY assignments DESC;

-- Step 2: Check object types
SELECT object_type, COUNT(*) as count
FROM `wonder-raw-prod.pg_batch_command_center.sku_info` si
JOIN `wonder-raw-prod.pg_batch_command_center.order_split_cache` osc
  ON si.item_number = osc.item_sku
WHERE osc.order_split_value = 'Global'
GROUP BY object_type
ORDER BY count DESC;

-- Step 3: Apply filters and recalculate baseline
SELECT facility_id, COUNT(*) as sku_count
FROM `wonder-raw-prod.pg_batch_command_center.order_split_cache` osc
JOIN `wonder-raw-prod.pg_batch_command_center.sku_info` si
  ON osc.item_sku = si.item_number
WHERE order_split_value = 'Global'
  AND si.object_type != 'NON_FOOD'  -- Exclude non-warehouse items
  AND osc.item_sku LIKE '88%'       -- Focus on specific prefix if needed
GROUP BY facility_id;
```

### Common Exclusions
- **NON_FOOD items**: Not fulfilled by warehouse
- **Item prefix 80\***: May have different fulfillment path
- **Item prefix 5\***: May be handled differently

**Always ask about scope before designing rules!**

## Rules Engine Patterns

### Rule Priority System

Rules are applied in priority order (lower number = higher priority). First matching rule wins.

```sql
-- Example rule structure
SELECT priority, group_name, rule_id, parameters
FROM `wonder-raw-prod.pg_batch_command_center.sku_grouping_rules`
WHERE policy_id = 1
ORDER BY priority ASC;
```

**Common priority pattern**:
1. Frozen items (storage_type = FROZEN)
2. Beverages (object_sub_type = BEVERAGE)
3-7. Pod assignments (Pod A, B, C, D)
8+. Fallback to Global

### Rule Design Workflow

```sql
-- 1. Establish current baseline (with proper filters)
WITH current_state AS (
  SELECT facility_id, COUNT(*) as global_sku_count
  FROM `wonder-raw-prod.pg_batch_command_center.order_split_cache` osc
  JOIN `wonder-raw-prod.pg_batch_command_center.sku_info` si
    ON osc.item_sku = si.item_number
  WHERE order_split_value = 'Global'
    AND si.object_type != 'NON_FOOD'  -- Apply appropriate filters
  GROUP BY facility_id
)
SELECT
  AVG(global_sku_count) as avg_global_skus,
  MAX(global_sku_count) as max_global_skus
FROM current_state;

-- 2. Simulate proposed rule
WITH rule_simulation AS (
  SELECT
    facility_id,
    item_sku,
    CASE
      WHEN si.object_sub_type = 'COMMON_STOCK' THEN 'Common Stock'
      WHEN si.storage_type = 'FROZEN' THEN 'Frozen'
      ELSE 'Global'
    END as proposed_split
  FROM `wonder-raw-prod.pg_batch_command_center.order_split_cache` osc
  JOIN `wonder-raw-prod.pg_batch_command_center.sku_info` si
    ON osc.item_sku = si.item_number
  WHERE order_split_value = 'Global'
    AND si.object_type != 'NON_FOOD'
)
SELECT
  proposed_split,
  AVG(sku_count) as avg_sku_count,
  MAX(sku_count) as max_sku_count
FROM (
  SELECT proposed_split, facility_id, COUNT(*) as sku_count
  FROM rule_simulation
  GROUP BY proposed_split, facility_id
) stats
GROUP BY proposed_split;

-- 3. Validate 100% success on target metric
-- Example: Ensure no facility has > 99 SKUs in any split
```

For complete rule design patterns, see [rule-design-patterns.md](rule-design-patterns.md).

## Query Patterns

### Check Current Order Assignments for an HDR

```sql
SELECT
  item_sku,
  order_split_value,
  updated_at,
  details  -- Contains rules engine decision trace
FROM `wonder-raw-prod.pg_batch_command_center.order_split_cache`
WHERE facility_id = '867877e0-36ea-42c5-84d8-11668897dc85'
ORDER BY order_split_value, item_sku;
```

### Analyze Rules Engine Decision

```sql
-- See detailed reasoning for a specific assignment
SELECT
  osc.item_sku,
  osc.order_split_value,
  si.object_type,
  si.object_sub_type,
  si.storage_type,
  osc.details  -- JSON trace of which rules were evaluated
FROM `wonder-raw-prod.pg_batch_command_center.order_split_cache` osc
JOIN `wonder-raw-prod.pg_batch_command_center.sku_info` si
  ON osc.item_sku = si.item_number
WHERE osc.facility_id = '844f34e5-19ee-4289-b3e9-d01c80600349'
  AND osc.item_sku = '8806668';
```

### Monitor Recent Order Split Changes

```sql
SELECT
  facility_id,
  item_sku,
  order_split_value,
  operation,  -- 'INSERT' or 'UPDATE'
  created_at
FROM `wonder-raw-prod.pg_batch_command_center.order_split_cache_logs`
WHERE created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
ORDER BY created_at DESC;
```

### Distribution Analysis by Order Split

```sql
-- How many SKUs assigned to each order type?
SELECT
  order_split_value,
  COUNT(DISTINCT item_sku) as unique_skus,
  COUNT(DISTINCT facility_id) as facilities,
  COUNT(*) as total_assignments
FROM `wonder-raw-prod.pg_batch_command_center.order_split_cache`
GROUP BY order_split_value
ORDER BY total_assignments DESC;
```

### SKU Metadata Lookup

```sql
-- Understand SKU characteristics
SELECT
  item_number,
  object_type,
  object_sub_type,
  storage_type
FROM `wonder-raw-prod.pg_batch_command_center.sku_info`
WHERE item_number IN ('8805753', '8806668', '8003399');
```

## Common Order Split Values

- **Global**: Default assignment for items without specific rules (catch-all)
- **Frozen**: Items requiring frozen storage (storage_type = FROZEN)
- **Beverages**: Alcoholic and non-alcoholic beverages
- **Pod A/B/C/D**: Pod-specific assignments for optimized kitchen workflow
- **Common Stock**: Frequently used items across all HDRs
- **Packaged Items**: Pre-packaged items requiring minimal prep

## Rule Effectiveness Metrics

When testing rules, measure:

1. **Order size reduction**: Average SKUs per order split after rule
2. **Success rate**: % of facilities meeting target (e.g., < 100 SKUs per order)
3. **Distribution**: Min/max/avg SKU counts across facilities
4. **Operational logic**: Do the splits make sense to kitchen staff?

```sql
-- Success metric template
WITH split_sizes AS (
  SELECT
    facility_id,
    order_split_value,
    COUNT(*) as sku_count
  FROM `wonder-raw-prod.pg_batch_command_center.order_split_cache`
  WHERE order_split_value IN ('Global', 'Common Stock', 'Frozen')
  GROUP BY facility_id, order_split_value
)
SELECT
  order_split_value,
  COUNT(CASE WHEN sku_count <= 99 THEN 1 END) as success_count,
  COUNT(*) as total_facilities,
  ROUND(100.0 * COUNT(CASE WHEN sku_count <= 99 THEN 1 END) / COUNT(*), 1) as success_pct
FROM split_sizes
GROUP BY order_split_value;
```

## Audit Trail

All changes to order_split_cache are logged in order_split_cache_logs:

- `operation`: INSERT or UPDATE
- `created_at`: Timestamp of change
- `created_by`: User/service that made the change
- `details`: Additional context about the change

## BigQuery Specifics

**Command Center** data is in BigQuery:
- Use `bq` CLI or BigQuery Console
- Use `CURRENT_TIMESTAMP()` for current time
- Use `INTERVAL 24 HOUR` syntax (not `INTERVAL '24 hours'`)
- Timezone conversion: `DATETIME(TIMESTAMP(column), 'America/New_York')`
- Always use fully qualified table names: `` `wonder-raw-prod.pg_batch_command_center.table_name` ``

## Best Practices

1. **Always establish accurate baseline** with proper data scoping before designing rules
2. **Test rules iteratively** on the actual relevant data subset
3. **Sequence rules by impact** - start with highest-impact categories first
4. **Validate 100% success** on target metric before finalizing
5. **Use operationally logical categories** that warehouse staff will understand
6. **Document rule reasoning** in the details field for auditability

## Supporting Documentation

- [schema-reference.md](schema-reference.md) - Complete table schemas and relationships
- [common-pitfalls.md](common-pitfalls.md) - Common mistakes and how to avoid them
- [rule-design-patterns.md](rule-design-patterns.md) - Iterative rule development workflow
