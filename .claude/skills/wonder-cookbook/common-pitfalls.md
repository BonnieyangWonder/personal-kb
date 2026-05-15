# Common Pitfalls and Gotchas - Cookbook Recipe System

Critical mistakes to avoid when working with Wonder's Cookbook recipe and BOM data.

---

## CRITICAL: Missing `deleted = false` Filter

**The most dangerous mistake**: forgetting `deleted = false`, which returns soft-deleted items that should no longer exist.

### ❌ Wrong: Missing deleted Filter (Returns Deleted Items!)

```sql
-- FAILS: Returns items that have been deleted from Cookbook
SELECT item_number, name, object_type
FROM `secure-recipe-prod.recipe_v2.item_versions`
WHERE effective = true
  AND object_type = 'MENU';
```

**Result**: Includes items that no longer exist, leading to incorrect analysis.

### ❌ Also Wrong: Assuming effective_items Handles This

```sql
-- FAILS: effective_items is pre-filtered for effective=true, but NOT for deleted
SELECT item_number, name, object_type
FROM `secure-recipe-prod.recipe_v2.effective_items`
WHERE object_type = 'MENU';
```

**Result**: Still returns deleted items!

### ✅ Correct: Full Essential Filter

```sql
-- WORKS: Always include all three conditions
SELECT item_number, name, object_type
FROM `secure-recipe-prod.recipe_v2.item_versions`
WHERE effective = true
  AND deleted = false  -- CRITICAL: Must include!
  AND item_status != 'DORMANT'
  AND object_type = 'MENU';

-- Or with effective_items (still need deleted filter!)
SELECT item_number, name, object_type
FROM `secure-recipe-prod.recipe_v2.effective_items`
WHERE deleted = false  -- Still required!
  AND object_type = 'MENU'
  AND item_status = 'ACTIVE';
```

**Why This Matters**: Soft-deleted items remain in the database for audit purposes. Without `deleted = false`, you'll include items that shouldn't appear in any analysis.

**Pattern to Remember**:
```sql
WHERE effective = true
  AND deleted = false
  AND item_status != 'DORMANT'
```

---

## CRITICAL: Wrong BOM Access Pattern

Using only `bom_headers`/`bom_lines` tables when nested JSON is the primary pattern.

### ❌ Suboptimal: Only Using Separate BOM Tables

```sql
-- WORKS but not the primary pattern
-- Requires joins and service window filtering
SELECT
  bh.item_number,
  bl.bom_line_item_number as component
FROM `secure-recipe-prod.recipe_v2.bom_headers` bh
INNER JOIN `secure-recipe-prod.recipe_v2.bom_lines` bl
  ON bh.item_number = bl.bom_header_item_number
WHERE bh.is_active = true
  AND bh.item_number = '8009068'
  AND CURRENT_TIMESTAMP() BETWEEN TIMESTAMP(bl.service_start_time) AND TIMESTAMP(bl.service_end_time);
```

### ✅ Better: Use Nested JSON in item_versions

```sql
-- PRIMARY PATTERN: BOM is stored as nested JSON
SELECT
  m.item_number,
  m.name,
  JSON_VALUE(bom_line, '$.item_number') AS component_item,
  SAFE_CAST(JSON_EXTRACT_SCALAR(bom_line, '$.quantity') AS FLOAT64) AS quantity,
  JSON_VALUE(bom_line, '$.uom') AS uom
FROM `secure-recipe-prod.recipe_v2.item_versions` m,
UNNEST(JSON_EXTRACT_ARRAY(m.bom_header, '$.bom_lines')) AS bom_line
WHERE m.effective = true
  AND m.deleted = false
  AND m.item_status != 'DORMANT'
  AND m.item_number = '8009068';
```

**Why This Matters**:
- Nested JSON is the source of truth for current BOM
- Single table query, no joins needed
- Automatically gets current version (no service window logic)
- Use separate tables only for cross-item analysis or historical queries

---

## Service Windows - Missing Current Recipe Filter

The most common and impactful mistake: forgetting to filter by service windows, which returns ALL historical versions of components.

### ❌ Wrong: Getting All Historical Components (Including Expired)

```sql
-- FAILS: Returns multiple versions of the same component across different time periods
SELECT DISTINCT
  bl.bom_line_item_number as component_id,
  iv_comp.name as component_name
FROM `secure-recipe-prod.recipe_v2.bom_headers` bh
INNER JOIN `secure-recipe-prod.recipe_v2.bom_lines` bl
  ON bh.item_number = bl.bom_header_item_number
LEFT JOIN `secure-recipe-prod.recipe_v2.item_versions` iv_comp
  ON CAST(bl.bom_line_item_number AS STRING) = CAST(iv_comp.item_number AS STRING)
WHERE bh.is_active = true
  AND bh.item_number = '8009068';
-- Missing service window filter!
```

**Result**: Returns 7 different fry SKUs (4000053, 5182267, 8800311, 8805681) when only 1 is currently active.

### ✅ Correct: Filter to Current Service Window

```sql
-- WORKS: Returns only current active components
SELECT DISTINCT
  bl.bom_line_item_number as component_id,
  iv_comp.name as component_name
FROM `secure-recipe-prod.recipe_v2.bom_headers` bh
INNER JOIN `secure-recipe-prod.recipe_v2.bom_lines` bl
  ON bh.item_number = bl.bom_header_item_number
LEFT JOIN `secure-recipe-prod.recipe_v2.item_versions` iv_comp
  ON CAST(bl.bom_line_item_number AS STRING) = CAST(iv_comp.item_number AS STRING)
WHERE bh.is_active = true
  AND bh.item_number = '8009068'
  -- CRITICAL: Add service window filter
  AND CURRENT_TIMESTAMP() BETWEEN TIMESTAMP(bl.service_start_time) AND TIMESTAMP(bl.service_end_time);
```

**Why This Matters**: Without the service window filter, you'll analyze expired ingredients, calculate wrong costs, and check inventory for items no longer used.

**Pattern to Remember**: `CURRENT_TIMESTAMP() BETWEEN TIMESTAMP(service_start_time) AND TIMESTAMP(service_end_time)`

---

## Required vs Optional - Treating All Components as Required

Assuming all BOM components affect menu item availability, when many are optional (packaging, garnishes).

### ❌ Wrong: Checking All Components for Availability

```sql
-- FAILS: Checks packaging and garnishes as if they block availability
SELECT
  bl.bom_line_item_number as component_id,
  iv_comp.name as component_name
FROM `secure-recipe-prod.recipe_v2.bom_headers` bh
INNER JOIN `secure-recipe-prod.recipe_v2.bom_lines` bl
  ON bh.item_number = bl.bom_header_item_number
LEFT JOIN `secure-recipe-prod.recipe_v2.item_versions` iv_comp
  ON CAST(bl.bom_line_item_number AS STRING) = CAST(iv_comp.item_number AS STRING)
WHERE bh.is_active = true
  AND bh.item_number = '8009068'
  AND CURRENT_TIMESTAMP() BETWEEN TIMESTAMP(bl.service_start_time) AND TIMESTAMP(bl.service_end_time);
-- Missing manage_inventory filter!
```

**Result**: Returns 7 components including clamshells and souffle cups that don't affect availability.

### ✅ Correct: Filter to Required Components Only

```sql
-- WORKS: Only checks components that block availability when missing
SELECT
  bl.bom_line_item_number as component_id,
  iv_comp.name as component_name,
  bl.manage_inventory as is_required
FROM `secure-recipe-prod.recipe_v2.bom_headers` bh
INNER JOIN `secure-recipe-prod.recipe_v2.bom_lines` bl
  ON bh.item_number = bl.bom_header_item_number
LEFT JOIN `secure-recipe-prod.recipe_v2.item_versions` iv_comp
  ON CAST(bl.bom_line_item_number AS STRING) = CAST(iv_comp.item_number AS STRING)
WHERE bh.is_active = true
  AND bh.item_number = '8009068'
  AND bl.manage_inventory = true  -- CRITICAL: Only required components
  AND CURRENT_TIMESTAMP() BETWEEN TIMESTAMP(bl.service_start_time) AND TIMESTAMP(bl.service_end_time);
```

**Why This Matters**: `manage_inventory = false` means optional (packaging/garnishes). Only `manage_inventory = true` components block menu item availability.

**Pattern to Remember**: Filter by `bl.manage_inventory = true` when analyzing availability blockers.

---

## Type Confusion - version_id vs _id

Confusing `version_id` (INTEGER) with `_id` (STRING UUID) in item_versions table.

### ❌ Wrong: Treating version_id as UUID string

```sql
-- FAILS: version_id is INTEGER, not STRING
SELECT *
FROM `secure-recipe-prod.recipe_v2.item_versions`
WHERE version_id = '5570ab64-2933-4157-90e9-4e85addd6532';  -- Wrong field!
```

### ✅ Correct: Use Proper Field and Type

```sql
-- version_id is an INTEGER sequence number (1, 2, 3...)
SELECT *
FROM `secure-recipe-prod.recipe_v2.item_versions`
WHERE version_id = 37;  -- Correct: INTEGER

-- For UUID lookups, use _id field in item_versions
SELECT *
FROM `secure-recipe-prod.recipe_v2.item_versions`
WHERE _id = '5570ab64-2933-4157-90e9-4e85addd6532';  -- Correct: STRING UUID

-- Join bom_headers to item_versions using item_version_id = _id
SELECT bh.*, iv.name
FROM `secure-recipe-prod.recipe_v2.bom_headers` bh
JOIN `secure-recipe-prod.recipe_v2.item_versions` iv
  ON bh.item_version_id = iv._id;  -- Correct join pattern
```

**Why This Matters**:
- `version_id` (in item_versions) = INTEGER numeric sequence (1, 2, 3...)
- `_id` (in item_versions) = STRING UUID identifier
- `item_version_id` (in bom_headers/bom_lines) = STRING UUID that references `item_versions._id`

---

## Type Casting - Missing CAST on Item Numbers

Forgetting to cast item numbers when joining across tables, causing join failures.

### ❌ Wrong: Direct Join Without Casting

```sql
-- FAILS: Type mismatch error or zero results
SELECT
  bl.bom_line_item_number,
  iv_comp.name
FROM `secure-recipe-prod.recipe_v2.bom_lines` bl
LEFT JOIN `secure-recipe-prod.recipe_v2.item_versions` iv_comp
  ON bl.bom_line_item_number = iv_comp.item_number  -- Type mismatch!
WHERE bl.bom_header_item_number = '8009068';
```

**Result**: May return zero rows or type error depending on BigQuery's implicit casting.

### ✅ Correct: Cast Item Numbers to STRING

```sql
-- WORKS: Explicit casting ensures correct join
SELECT
  bl.bom_line_item_number,
  iv_comp.name
FROM `secure-recipe-prod.recipe_v2.bom_lines` bl
LEFT JOIN `secure-recipe-prod.recipe_v2.item_versions` iv_comp
  ON CAST(bl.bom_line_item_number AS STRING) = CAST(iv_comp.item_number AS STRING)
WHERE bl.bom_header_item_number = '8009068';
```

**Why This Matters**: Item numbers may be stored as different types (STRING vs INT64). Explicit casting ensures joins work correctly.

**Pattern to Remember**: `CAST(bl.bom_line_item_number AS STRING) = CAST(other_table.item_number AS STRING)`

---

## Join Type - Using INNER JOIN for item_versions

Using INNER JOIN when joining to item_versions, which drops BOM lines without metadata.

### ❌ Wrong: INNER JOIN Loses Components

```sql
-- FAILS: Drops BOM lines where component metadata doesn't exist
SELECT
  bl.bom_line_item_number,
  iv_comp.name as component_name
FROM `secure-recipe-prod.recipe_v2.bom_lines` bl
INNER JOIN `secure-recipe-prod.recipe_v2.item_versions` iv_comp  -- Wrong join type!
  ON CAST(bl.bom_line_item_number AS STRING) = CAST(iv_comp.item_number AS STRING)
WHERE bl.bom_header_item_number = '8009068';
```

**Result**: Missing components that don't have item_versions records (data quality issue).

### ✅ Correct: LEFT JOIN Preserves All Components

```sql
-- WORKS: Keeps all BOM lines even if metadata is missing
SELECT
  bl.bom_line_item_number,
  COALESCE(iv_comp.name, CONCAT('Unknown: ', bl.bom_line_item_number)) as component_name
FROM `secure-recipe-prod.recipe_v2.bom_lines` bl
LEFT JOIN `secure-recipe-prod.recipe_v2.item_versions` iv_comp  -- Correct join type
  ON CAST(bl.bom_line_item_number AS STRING) = CAST(iv_comp.item_number AS STRING)
  AND iv_comp.effective = true
WHERE bl.bom_header_item_number = '8009068';
```

**Why This Matters**: Not all components have metadata in item_versions. LEFT JOIN ensures you don't lose BOM lines.

**Pattern to Remember**: Use LEFT JOIN for item_versions, with NULL handling in SELECT.

---

## Performance - Using item_versions Instead of effective_items

Using `item_versions WHERE effective = true` when `effective_items` table exists and is optimized for this exact query.

### ❌ Suboptimal: Filtering item_versions

```sql
-- WORKS but slower: Requires filtering on every query
SELECT
  item_number,
  name,
  object_type
FROM `secure-recipe-prod.recipe_v2.item_versions`
WHERE effective = true
  AND object_type = 'MENU'
  AND item_status = 'ACTIVE';
```

### ✅ Better: Use effective_items

```sql
-- RECOMMENDED: Pre-filtered table, no need to filter by effective
SELECT
  item_number,
  name,
  object_type
FROM `secure-recipe-prod.recipe_v2.effective_items`
WHERE object_type = 'MENU'
  AND item_status = 'ACTIVE';
```

**Why This Matters**: `effective_items` is a pre-filtered view containing only `effective = true` records. It's the most queried table in the dataset (48,000+ queries/month) because it eliminates redundant filtering.

**When to Use item_versions**: Only when you need historical versions or need to analyze the `effective` flag itself.

---

## Duplicate Rows - Not Using DISTINCT with item_versions

Joining to item_versions without filtering by `effective = true` or using DISTINCT, causing duplicate rows.

### ❌ Wrong: Duplicate Components from Multiple Versions

```sql
-- FAILS: Returns duplicate rows for components with multiple item_version records
SELECT
  bl.bom_line_item_number,
  iv_comp.name
FROM `secure-recipe-prod.recipe_v2.bom_headers` bh
INNER JOIN `secure-recipe-prod.recipe_v2.bom_lines` bl
  ON bh.item_number = bl.bom_header_item_number
LEFT JOIN `secure-recipe-prod.recipe_v2.item_versions` iv_comp
  ON CAST(bl.bom_line_item_number AS STRING) = CAST(iv_comp.item_number AS STRING)
  -- Missing effective = true filter!
WHERE bh.item_number = '8009068'
  AND CURRENT_TIMESTAMP() BETWEEN TIMESTAMP(bl.service_start_time) AND TIMESTAMP(bl.service_end_time);
```

**Result**: Inflated component counts (same component appears multiple times).

### ✅ Correct: Filter effective = true AND Use DISTINCT

```sql
-- WORKS: Returns each component exactly once
SELECT DISTINCT
  bl.bom_line_item_number,
  iv_comp.name
FROM `secure-recipe-prod.recipe_v2.bom_headers` bh
INNER JOIN `secure-recipe-prod.recipe_v2.bom_lines` bl
  ON bh.item_number = bl.bom_header_item_number
LEFT JOIN `secure-recipe-prod.recipe_v2.item_versions` iv_comp
  ON CAST(bl.bom_line_item_number AS STRING) = CAST(iv_comp.item_number AS STRING)
  AND iv_comp.effective = true  -- Only current version
WHERE bh.item_number = '8009068'
  AND CURRENT_TIMESTAMP() BETWEEN TIMESTAMP(bl.service_start_time) AND TIMESTAMP(bl.service_end_time);
```

**Why This Matters**: item_versions has historical versions. Without filtering or DISTINCT, you'll get duplicate rows.

**Pattern to Remember**: Add `AND effective = true` to item_versions joins, or use `SELECT DISTINCT`.

---

## Active BOM Filter - Not Checking is_active

Querying archived/inactive BOMs instead of current active ones.

### ❌ Wrong: Including Inactive BOMs

```sql
-- FAILS: May return archived recipe versions
SELECT
  bh.item_number,
  COUNT(DISTINCT bl.bom_line_item_number) as num_components
FROM `secure-recipe-prod.recipe_v2.bom_headers` bh
INNER JOIN `secure-recipe-prod.recipe_v2.bom_lines` bl
  ON bh.item_number = bl.bom_header_item_number
WHERE bh.item_number = '8009068'
  -- Missing is_active filter!
GROUP BY bh.item_number;
```

**Result**: May analyze old/archived recipe versions instead of current ones.

### ✅ Correct: Filter to Active BOMs

```sql
-- WORKS: Only queries current active BOMs
SELECT
  bh.item_number,
  COUNT(DISTINCT bl.bom_line_item_number) as num_components
FROM `secure-recipe-prod.recipe_v2.bom_headers` bh
INNER JOIN `secure-recipe-prod.recipe_v2.bom_lines` bl
  ON bh.item_number = bl.bom_header_item_number
WHERE bh.item_number = '8009068'
  AND bh.is_active = true  -- CRITICAL: Only active BOMs
GROUP BY bh.item_number;
```

**Why This Matters**: Inactive BOMs are archived/historical. Always filter `is_active = true`.

**Pattern to Remember**: Add `bom_headers.is_active = true` to WHERE clause.

---

## Join Keys - Wrong Join Field on BOM Lines

Using the wrong field name when joining bom_headers to bom_lines.

### ❌ Wrong: Incorrect Join Field

```sql
-- FAILS: Field not found error
SELECT
  bh.item_number,
  bl.bom_line_item_number
FROM `secure-recipe-prod.recipe_v2.bom_headers` bh
INNER JOIN `secure-recipe-prod.recipe_v2.bom_lines` bl
  ON bh.item_number = bl.item_number  -- Wrong field name!
WHERE bh.is_active = true;
```

**Result**: Field not found error or zero results.

### ✅ Correct: Use bom_header_item_number

```sql
-- WORKS: Correct join field
SELECT
  bh.item_number,
  bl.bom_line_item_number
FROM `secure-recipe-prod.recipe_v2.bom_headers` bh
INNER JOIN `secure-recipe-prod.recipe_v2.bom_lines` bl
  ON bh.item_number = bl.bom_header_item_number  -- Correct field
WHERE bh.is_active = true;
```

**Why This Matters**: The join field is `bom_header_item_number`, not `item_number`.

**Pattern to Remember**: `bom_headers.item_number = bom_lines.bom_header_item_number`

---

## Cross-Dataset Joins - Wrong Database Reference

Trying to join Cookbook to Pantry/Product Catalog with wrong dataset names.

### ❌ Wrong: Incorrect Dataset Name

```sql
-- FAILS: Table not found
SELECT
  bl.bom_line_item_number,
  ioh.quantity
FROM `secure-recipe-prod.recipe_v2.bom_lines` bl
LEFT JOIN `secure-recipe-prod.inventory_on_hand` ioh  -- Wrong dataset!
  ON CAST(bl.bom_line_item_number AS STRING) = ioh.item_number
WHERE bl.bom_header_item_number = '8009068';
```

**Result**: Table not found error.

### ✅ Correct: Use Correct Dataset for Each System

```sql
-- WORKS: Correct dataset references
SELECT
  bl.bom_line_item_number,
  ioh.quantity
FROM `secure-recipe-prod.recipe_v2.bom_lines` bl
LEFT JOIN `wonder-raw-prod.mysql_batch_inventory.inventory_on_hand` ioh  -- Correct dataset
  ON CAST(bl.bom_line_item_number AS STRING) = ioh.item_number
WHERE bl.bom_header_item_number = '8009068';
```

**Why This Matters**: Cookbook is in `secure-recipe-prod.recipe_v2`, but Pantry is in `wonder-raw-prod.mysql_batch_inventory`.

**Pattern to Remember**:
- Cookbook: `secure-recipe-prod.recipe_v2.*`
- Pantry: `wonder-raw-prod.mysql_batch_inventory.*`
- Product Catalog: `wonder-raw-prod.mysql_batch_product_catalog.*`

---

## Aggregation - Counting Without Filtering Service Windows

Counting components or calculating totals without filtering to current service windows first.

### ❌ Wrong: Count Includes Historical Components

```sql
-- FAILS: Inflated count includes all historical versions
SELECT
  bh.item_number,
  COUNT(bl.bom_line_item_number) as num_components,
  SUM(bl.cost) as total_cost
FROM `secure-recipe-prod.recipe_v2.bom_headers` bh
INNER JOIN `secure-recipe-prod.recipe_v2.bom_lines` bl
  ON bh.item_number = bl.bom_header_item_number
WHERE bh.is_active = true
  AND bh.item_number = '8009068'
GROUP BY bh.item_number;
-- Missing service window filter before aggregation!
```

**Result**: num_components = 18 instead of actual 7, inflated costs.

### ✅ Correct: Filter Service Windows BEFORE Aggregating

```sql
-- WORKS: Count only current components
SELECT
  bh.item_number,
  COUNT(DISTINCT bl.bom_line_item_number) as num_components,
  SUM(bl.cost) as total_cost
FROM `secure-recipe-prod.recipe_v2.bom_headers` bh
INNER JOIN `secure-recipe-prod.recipe_v2.bom_lines` bl
  ON bh.item_number = bl.bom_header_item_number
WHERE bh.is_active = true
  AND bh.item_number = '8009068'
  AND CURRENT_TIMESTAMP() BETWEEN TIMESTAMP(bl.service_start_time) AND TIMESTAMP(bl.service_end_time)  -- Filter first!
GROUP BY bh.item_number;
```

**Why This Matters**: Aggregating before filtering service windows includes historical data, inflating counts and costs.

**Pattern to Remember**: Apply service window filter in WHERE clause, not after GROUP BY.

---

## Menu Item Status - Not Filtering object_type and item_status

Querying all items instead of just active menu items.

### ❌ Wrong: Includes Ingredients, Packaging, and Inactive Items

```sql
-- FAILS: Returns ingredients, packaging, R&D items, etc.
SELECT
  bh.item_number,
  iv.name
FROM `secure-recipe-prod.recipe_v2.bom_headers` bh
LEFT JOIN `secure-recipe-prod.recipe_v2.item_versions` iv
  ON bh.item_number = CAST(iv.item_number AS STRING)
WHERE bh.is_active = true;
-- Missing object_type and item_status filters!
```

**Result**: Includes non-menu items and inactive/R&D items.

### ✅ Correct: Filter to Active Menu Items

```sql
-- WORKS: Only returns active customer-facing menu items
SELECT
  bh.item_number,
  iv.name
FROM `secure-recipe-prod.recipe_v2.bom_headers` bh
LEFT JOIN `secure-recipe-prod.recipe_v2.item_versions` iv
  ON bh.item_number = CAST(iv.item_number AS STRING)
  AND iv.effective = true
WHERE bh.is_active = true
  AND iv.object_type = 'MENU'  -- Only menu items
  AND iv.item_status = 'ACTIVE';  -- Only active
```

**Why This Matters**: Not all items are customer-facing menu items. Filter by object_type and item_status.

**Pattern to Remember**: Add `object_type = 'MENU'` and `item_status = 'ACTIVE'` for customer menu items.

---

## Summary Checklist

### Essential Filter (EVERY QUERY):
- [ ] **`deleted = false`** - CRITICAL, always include even on effective_items
- [ ] `effective = true` - Only current version (not needed on effective_items)
- [ ] `item_status != 'DORMANT'` - Exclude temporarily unavailable items

### Before Querying Recipes:
- [ ] Consider using nested JSON pattern (`item_versions.bom_header.bom_lines`) first
- [ ] Filter `bom_headers.is_active = true` if using separate tables
- [ ] Filter service windows: `CURRENT_TIMESTAMP() BETWEEN TIMESTAMP(service_start_time) AND TIMESTAMP(service_end_time)`
- [ ] Check if you need only required components: `manage_inventory = true`
- [ ] Use CAST for all item_number joins: `CAST(item_number AS STRING)`

### When Joining to Item Metadata:
- [ ] **Always include `deleted = false`** on joined item tables
- [ ] **Prefer `effective_items` over `item_versions`** when you only need current versions
- [ ] Use LEFT JOIN (not INNER JOIN)
- [ ] If using `item_versions`, add `effective = true` AND `deleted = false` to join condition
- [ ] Use `SELECT DISTINCT` or handle duplicates
- [ ] Handle NULL names with COALESCE
- [ ] Remember: `version_id` is INTEGER, `item_version_id` is STRING UUID

### When Joining to Other Systems:
- [ ] Verify correct dataset names (secure-recipe-prod vs wonder-raw-prod)
- [ ] Cast item numbers to STRING for joins
- [ ] Use correct join key: `bom_header_item_number` not `item_number`

### When Aggregating/Counting:
- [ ] Apply service window filter BEFORE aggregation (in WHERE, not HAVING)
- [ ] Use COUNT(DISTINCT ...) when joining to item tables
- [ ] Verify time periods match your analysis needs

### When Analyzing Menu Availability:
- [ ] Join required components to Pantry inventory
- [ ] Check only `manage_inventory = true` components
- [ ] Handle cross-dataset type casting correctly

---

## Domain-Specific Pitfalls

### Line Build - Missing Service Window Filter

Like BOM lines, `item_line_builds` uses service windows for versioning.

#### ❌ Wrong: Getting All Line Build Versions

```sql
-- FAILS: Returns all historical line build configurations
SELECT item_number, procedures_appliance, cooking_time
FROM `secure-recipe-prod.recipe_v2.item_line_builds`
WHERE item_number = '8009068';
```

#### ✅ Correct: Filter to Current Line Build

```sql
-- WORKS: Returns only current line build configuration
SELECT item_number, procedures_appliance, cooking_time
FROM `secure-recipe-prod.recipe_v2.item_line_builds`
WHERE item_number = '8009068'
  AND CURRENT_TIMESTAMP() BETWEEN TIMESTAMP(service_start_time) AND TIMESTAMP(service_end_time);
```

---

### Nutrition - Forgetting to CAST String Values

Nutrition values are stored as STRING, not numeric types.

#### ❌ Wrong: Comparing Without CAST

```sql
-- FAILS: Type mismatch or unexpected results
SELECT item_number, name, calories_k_cal
FROM `secure-recipe-prod.recipe_v2.all_item_version_customization_nutrition`
WHERE calories_k_cal > 500;  -- Comparing STRING to INTEGER
```

#### ✅ Correct: Use SAFE_CAST

```sql
-- WORKS: Proper numeric comparison
SELECT item_number, name, SAFE_CAST(calories_k_cal AS FLOAT64) as calories
FROM `secure-recipe-prod.recipe_v2.all_item_version_customization_nutrition`
WHERE SAFE_CAST(calories_k_cal AS FLOAT64) > 500;
```

---

### Nutrition - Including Customizations Instead of Base

The nutrition table has rows for both base items (`is_preset = 'true'`) and customizations.

#### ❌ Wrong: Getting All Rows Including Customizations

```sql
-- FAILS: Returns multiple rows per item (base + each customization)
SELECT item_number, name, calories_k_cal
FROM `secure-recipe-prod.recipe_v2.all_item_version_customization_nutrition`
WHERE item_number = '8009068';
```

#### ✅ Correct: Filter to Base Nutrition Only

```sql
-- WORKS: Returns only base nutrition (no customizations)
SELECT item_number, name, calories_k_cal
FROM `secure-recipe-prod.recipe_v2.all_item_version_customization_nutrition`
WHERE item_number = '8009068'
  AND is_preset = 'true';
```

---

### Assembly Instructions - Missing Service Window Filter

Assembly instructions also use service windows.

#### ❌ Wrong: Getting All Assembly Versions

```sql
SELECT item_number, name, notes
FROM `secure-recipe-prod.recipe_v2.assembly_instruction`
WHERE item_number = '8009068';
```

#### ✅ Correct: Filter to Current Assembly Instructions

```sql
SELECT item_number, name, notes
FROM `secure-recipe-prod.recipe_v2.assembly_instruction`
WHERE item_number = '8009068'
  AND CURRENT_TIMESTAMP() BETWEEN TIMESTAMP(service_start_time) AND TIMESTAMP(service_end_time);
```

---

### Cross-System - Wrong Dataset for Pantry

Using the wrong project/dataset when joining to Pantry inventory.

#### ❌ Wrong: Wrong Dataset Reference

```sql
-- FAILS: Table not found
LEFT JOIN `secure-recipe-prod.inventory_on_hand` ioh
  ON ...
```

#### ✅ Correct: Use wonder-raw-prod

```sql
-- WORKS: Correct Pantry dataset
LEFT JOIN `wonder-raw-prod.mysql_batch_inventory.inventory_on_hand` ioh
  ON ...
```

**Dataset Reference**:
- Cookbook: `secure-recipe-prod.recipe_v2`
- Pantry: `wonder-raw-prod.mysql_batch_inventory`
- Product Catalog: `wonder-raw-prod.mysql_batch_product_catalog`
- Orders: `wonder-dw-prod-brd.wonder_dw`

---

### Domain Checklist

#### Line Build Queries:
- [ ] Filter service windows
- [ ] Check `procedures_cooking_phase` for specific phases
- [ ] Consider `restaurant_id` for HDR-specific builds

#### Nutrition Queries:
- [ ] Use `SAFE_CAST` for numeric comparisons
- [ ] Filter `is_preset = 'true'` for base nutrition
- [ ] Handle NULL values in nutrition fields

#### Assembly Instruction Queries:
- [ ] Filter service windows
- [ ] Check `status` field for active instructions
- [ ] Parse JSON fields with `JSON_EXTRACT_*`

#### Cross-System Joins:
- [ ] Use correct dataset for each system
- [ ] CAST item_number to STRING
- [ ] Use LEFT JOIN to preserve Cookbook records

---

## Advanced Domain Pitfalls

### Version Status vs Item Status Confusion

Two completely different status systems exist in Cookbook. Do not confuse them.

#### ❌ Wrong: Treating version_status like item_status

```sql
-- FAILS: version_status applies to specific versions, not items overall
SELECT item_number, name
FROM `secure-recipe-prod.recipe_v2.item_versions`
WHERE version_status = 'ACTIVE';  -- version_status doesn't have 'ACTIVE' value!
```

#### ✅ Correct: Understand Both Status Systems

```sql
-- version_status: Controls recipe version publishing lifecycle
-- Values: DRAFT, SCHEDULED, FINAL
SELECT item_number, name, version_status
FROM `secure-recipe-prod.recipe_v2.item_versions`
WHERE version_status = 'FINAL'  -- Published versions
  AND effective = true;

-- item_status: Controls item availability for production
-- Values: R&D, ACTIVE, DORMANT
SELECT item_number, name, item_status
FROM `secure-recipe-prod.recipe_v2.effective_items`
WHERE item_status = 'ACTIVE'  -- Available for production
  AND deleted = false;
```

**Why This Matters**:
- `version_status` = Publishing workflow (DRAFT → SCHEDULED → FINAL)
- `item_status` = Item lifecycle (R&D → ACTIVE → DORMANT)
- A FINAL version can belong to a DORMANT item

---

### DATETIME vs TIMESTAMP Type Handling in BOM Tables

BOM service windows use DATETIME (no timezone), but CURRENT_TIMESTAMP() returns TIMESTAMP with timezone.

#### ❌ Wrong: Direct Comparison Without Type Handling

```sql
-- FAILS: Comparing TIMESTAMP to DATETIME directly can cause issues
SELECT *
FROM `secure-recipe-prod.recipe_v2.bom_lines`
WHERE CURRENT_TIMESTAMP() BETWEEN service_start_time AND service_end_time;
```

#### ✅ Correct: Explicit TIMESTAMP Conversion

```sql
-- WORKS: Convert DATETIME to TIMESTAMP for reliable comparison
SELECT *
FROM `secure-recipe-prod.recipe_v2.bom_lines`
WHERE CURRENT_TIMESTAMP() BETWEEN TIMESTAMP(service_start_time) AND TIMESTAMP(service_end_time);
```

**Why This Matters**: `service_start_time` and `service_end_time` in BOM tables are DATETIME type. Always wrap them in `TIMESTAMP()` for comparisons with `CURRENT_TIMESTAMP()`.

---

### Benchtop Recipe Subtype Restrictions

Not all benchtop recipes can be commercialized, and commercialization has strict rules.

#### ❌ Wrong: Assuming All Benchtop Items Can Commercialize

```sql
-- FAILS: BT-BYPRODUCT items cannot be commercialized
SELECT item_number, name, subtype
FROM `secure-recipe-prod.recipe_v2.effective_items`
WHERE subtype LIKE 'BT-%'
-- Incorrectly assuming all can become production items
```

#### ✅ Correct: Check Subtype for Commercialization Eligibility

```sql
-- WORKS: Only BT-PRIMARY and BT-PREPARATION can commercialize
SELECT
  item_number,
  name,
  subtype,
  CASE
    WHEN subtype = 'BT-PRIMARY' THEN 'Yes - to recipe-primary (1:N)'
    WHEN subtype = 'BT-PREPARATION' THEN 'Yes - to recipe-preparation (1:1 only)'
    WHEN subtype = 'BT-BYPRODUCT' THEN 'No - cannot commercialize'
    ELSE 'Not a benchtop item'
  END as commercialization_status
FROM `secure-recipe-prod.recipe_v2.effective_items`
WHERE subtype LIKE 'BT-%'
  AND deleted = false;
```

**Commercialization Rules**:
- **BT-PRIMARY**: Can create multiple recipe-primary items (1:N)
- **BT-PREPARATION**: Can create only one recipe-preparation (1:1)
- **BT-BYPRODUCT**: Cannot be commercialized (output of other recipes)

---

### 40 Model - Stockable vs Consumable Confusion

The 40 Model separates what gets consumed (40*) from what gets ordered (41*). Confusing these leads to incorrect inventory analysis.

#### ❌ Wrong: Using 40* Items for Order/Procurement Analysis

```sql
-- FAILS: 40* items are consumable representations, not ordered
SELECT
  item_number,
  name,
  -- Trying to check purchase orders for 40* item directly
FROM `secure-recipe-prod.recipe_v2.effective_items`
WHERE item_number LIKE '40%'
  AND deleted = false;
-- 40* items don't appear in purchase orders!
```

#### ✅ Correct: Link 40* Consumables to 41* WSKUs for Ordering

```sql
-- WORKS: Find the WSKU (41*) linked to a consumable (40*)
-- The 40* item is consumed at HDR, the 41* is what's ordered
SELECT
  c.item_number as consumable_40,
  c.name as consumable_name,
  w.item_number as wsku_41,
  w.name as orderable_sku
FROM `secure-recipe-prod.recipe_v2.effective_items` c
JOIN `secure-recipe-prod.recipe_v2.effective_items` w
  ON c.item_number = w.hdr_consumable_item_number  -- 41* links to 40*
WHERE c.item_number LIKE '40%'
  AND c.deleted = false
  AND w.deleted = false
  AND w.object_type = 'WSKU';
```

**Why This Matters**:
- **40* (HDR Consumable)**: What's tracked/consumed at HDR level
- **41* (WSKU)**: What's ordered from warehouse and stocked
- Only 41* items appear in purchase orders and inventory receipts
- One 40* can have multiple 41* WSKUs (different pack sizes), but only ONE is "active for ordering"

**Pattern to Remember**:
- Consumption analysis → Use 40* items
- Procurement/ordering analysis → Use 41* items
- Link them via `hdr_consumable_item_number` field on 41* items
