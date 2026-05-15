# Common Pitfalls and Gotchas - Wonder Pantry

Critical mistakes to avoid when working with Pantry inventory data. This guide focuses on join patterns and common query mistakes.

---

## Item Identifier Joins - Using Wrong Identifier

**The most common mistake in Pantry queries.** There are three item identifiers, and using the wrong one causes incorrect joins or missing data.

### ❌ Wrong: Joining inventory tables on item_number

```sql
-- FAILS - misses records where item_number is NULL
SELECT
  ioh.quantity,
  ist.available
FROM `wonder-raw-prod.mysql_batch_inventory.inventory_on_hand` ioh
JOIN `wonder-raw-prod.mysql_batch_inventory.inventory_state` ist
  ON ioh.item_number = ist.item_number
  AND ioh.site_id = ist.site_id;
```

### ✅ Correct: Joining inventory tables on consumable_item_number

```sql
-- WORKS - consumable_item_number is always present for tracked inventory
SELECT
  ioh.quantity,
  ist.available
FROM `wonder-raw-prod.mysql_batch_inventory.inventory_on_hand` ioh
JOIN `wonder-raw-prod.mysql_batch_inventory.inventory_state` ist
  ON ioh.consumable_item_number = ist.consumable_item_number
  AND ioh.site_id = ist.site_id;
```

**Why This Matters**: Many inventory records have NULL `item_number` but always have `consumable_item_number`. Joining on `item_number` loses these records.

**Rule**: Use `consumable_item_number` for all inventory-to-inventory joins (on_hand, ledgers, state tracking).

---

## Item Identifier Joins - When to Use Which Field

### ❌ Wrong: Using consumable_item_number to join to order system

```sql
-- FAILS - order systems use item_number, not consumable_item_number
SELECT
  ioi.requested_quantity,
  ioh.quantity AS on_hand
FROM `wonder-raw-prod.mysql_batch_inventory.inventory_order_items` ioi
JOIN `wonder-raw-prod.mysql_batch_inventory.inventory_on_hand` ioh
  ON ioi.consumable_item_number = ioh.consumable_item_number;
```

### ✅ Correct: Use both fields to handle all cases

```sql
-- WORKS - handles records with or without item_number
SELECT
  ioi.requested_quantity,
  ioh.quantity AS on_hand
FROM `wonder-raw-prod.mysql_batch_inventory.inventory_order_items` ioi
JOIN `wonder-raw-prod.mysql_batch_inventory.inventory_on_hand` ioh
  ON ioi.consumable_item_number = ioh.consumable_item_number
  AND ioi.site_id = ioh.site_id;
```

**Why This Matters**: Different systems use different identifiers. Order items have both `item_number` and `consumable_item_number`.

**Pattern**:
- **Inventory ↔ Inventory**: Use `consumable_item_number`
- **Inventory ↔ Orders**: Use `consumable_item_number` (both have it)
- **Inventory ↔ External systems**: May need `item_number` or `wsku`

---

## Table Selection - Using Archived Tables

### ❌ Wrong: Using a dated archive table

```sql
-- FAILS or returns stale data - this is an archived backup
SELECT *
FROM `wonder-raw-prod.mysql_batch_inventory.inventory_ledgers_251013`
WHERE site_id = 'YOUR_SITE_ID';
```

### ✅ Correct: Using current table

```sql
-- WORKS - always use the base table name without date suffix
SELECT *
FROM `wonder-raw-prod.mysql_batch_inventory.inventory_ledgers`
WHERE site_id = 'YOUR_SITE_ID';
```

**Why This Matters**: Tables with date suffixes (`_YYMMDD`) are backups or archives. They contain stale data and shouldn't be queried.

**Rule**: Never use tables with date suffixes like `_250811`, `_251013`. Always use the base table name.

---

## Table Selection - Using Temp Tables

### ❌ Wrong: Querying temp/staging tables

```sql
-- FAILS or returns incomplete data - this is a staging table
SELECT *
FROM `wonder-raw-prod.mysql_batch_inventory.ztemp__inventory_on_hand`
WHERE site_id = 'YOUR_SITE_ID';
```

### ✅ Correct: Using production table

```sql
-- WORKS - use production tables without ztemp__ prefix
SELECT *
FROM `wonder-raw-prod.mysql_batch_inventory.inventory_on_hand`
WHERE site_id = 'YOUR_SITE_ID';
```

**Why This Matters**: Tables prefixed with `ztemp__` are staging tables used during batch sync. They contain incomplete or in-process data.

**Rule**: Never query `ztemp__` prefixed tables. Always use the base table name.

---

## Transaction Type Joining - transaction_type_id Format Issues

### ❌ Wrong: Attempting to join transaction_type_id directly when it's stored as JSON array string

```sql
-- FAILS - transaction_type_id in inventory_transactions is stored as '["uuid"]', not plain UUID
SELECT *
FROM `wonder-raw-prod.mysql_batch_inventory.inventory_ledgers` il
JOIN `wonder-raw-prod.mysql_batch_inventory.inventory_transactions` it ON il.transaction_id = it.id
JOIN `wonder-raw-prod.mysql_batch_inventory.transaction_types` tt ON it.transaction_type_id = tt.id
WHERE tt.operation = 'Remove';
-- Join fails because transaction_type_id format doesn't match tt.id
```

### ✅ Correct: Direct join from inventory_ledgers to transaction_types

```sql
-- WORKS - inventory_ledgers has transaction_type_id as plain UUID
SELECT *
FROM `wonder-raw-prod.mysql_batch_inventory.inventory_ledgers` il
JOIN `wonder-raw-prod.mysql_batch_inventory.transaction_types` tt ON il.transaction_type_id = tt.id
WHERE tt.operation = 'Remove'
  AND tt.reason_code IN ('Damaged', 'Expired')
  AND tt.deleted_at IS NULL;
```

### ⚠️ Workaround: If you must use inventory_transactions, parse the JSON array string

```sql
-- WORKS - extracts UUID from JSON array string format '["uuid"]'
SELECT *
FROM `wonder-raw-prod.mysql_batch_inventory.inventory_ledgers` il
JOIN `wonder-raw-prod.mysql_batch_inventory.inventory_transactions` it ON il.transaction_id = it.id
LEFT JOIN `wonder-raw-prod.mysql_batch_inventory.transaction_types` tt
  ON tt.id = TRIM(REPLACE(REPLACE(it.transaction_type_id, '[', ''), ']', ''), '"')
WHERE tt.operation = 'Remove'
  AND tt.deleted_at IS NULL;
```

**Why This Matters**:
- `inventory_ledgers.transaction_type_id` is stored as a plain UUID string ✅
- `inventory_transactions.transaction_type_id` is stored as a JSON array string like `["uuid"]` ⚠️
- `transaction_types.id` is a plain UUID string ✅

This inconsistency means you cannot directly join `inventory_transactions` to `transaction_types` without string parsing.

**Pattern**:
- **Preferred**: Join directly from `inventory_ledgers` → `transaction_types` using `transaction_type_id`
- **If needed**: Use the REPLACE workaround to extract UUID from `inventory_transactions.transaction_type_id`

---

## Transaction Type Filtering - Operation Only

### ❌ Wrong: Filtering by operation alone

```sql
-- FAILS - gets too many transaction types
-- "Remove" includes Expired, Damaged, Cooked, Consumed, etc.
SELECT *
FROM `wonder-raw-prod.mysql_batch_inventory.inventory_ledgers` il
JOIN `wonder-raw-prod.mysql_batch_inventory.transaction_types` tt ON il.transaction_type_id = tt.id
WHERE tt.operation = 'Remove';
```

### ✅ Correct: Filtering by operation AND reason_code

```sql
-- WORKS - precisely targets waste transactions
SELECT *
FROM `wonder-raw-prod.mysql_batch_inventory.inventory_ledgers` il
JOIN `wonder-raw-prod.mysql_batch_inventory.transaction_types` tt ON il.transaction_type_id = tt.id
WHERE tt.operation = 'Remove'
  AND tt.reason_code IN ('Damaged', 'Expired', 'Temperature Breach')
  AND tt.deleted_at IS NULL;
```

**Why This Matters**: `operation` is broad. `reason_code` is specific. You need both to filter precisely.

**Pattern**: Always use `operation` AND `reason_code` together when filtering transactions.

---

## Transaction Type Filtering - Forgetting Soft Deletes

### ❌ Wrong: Not filtering deleted transaction types

```sql
-- FAILS - includes deleted/archived transaction types
SELECT *
FROM `wonder-raw-prod.mysql_batch_inventory.inventory_transactions` it
JOIN `wonder-raw-prod.mysql_batch_inventory.transaction_types` tt ON it.transaction_type_id = tt.id
WHERE it.site_id = 'YOUR_SITE_ID';
```

### ✅ Correct: Filtering out soft-deleted records

```sql
-- WORKS - only includes active transaction types
SELECT *
FROM `wonder-raw-prod.mysql_batch_inventory.inventory_transactions` it
JOIN `wonder-raw-prod.mysql_batch_inventory.transaction_types` tt ON it.transaction_type_id = tt.id
WHERE it.site_id = 'YOUR_SITE_ID'
  AND tt.deleted_at IS NULL;
```

**Why This Matters**: `transaction_types`, `sites`, and `hdr_locations` have soft deletes. Deleted records remain in the table.

**Rule**: Always add `WHERE deleted_at IS NULL` when querying:
- `transaction_types`
- `sites`
- `hdr_locations`

---

## Waste Calculation - Wrong Aggregation

### ❌ Wrong: Summing result field for totals

```sql
-- FAILS - result is running balance, not the amount wasted per transaction
SELECT
  consumable_item_number,
  SUM(result) AS total_wasted
FROM `wonder-raw-prod.mysql_batch_inventory.inventory_ledgers` il
JOIN `wonder-raw-prod.mysql_batch_inventory.inventory_transactions` it ON il.transaction_id = it.id
JOIN `wonder-raw-prod.mysql_batch_inventory.transaction_types` tt ON it.transaction_type_id = tt.id
WHERE tt.operation = 'Remove'
  AND tt.reason_code = 'Expired'
GROUP BY consumable_item_number;
```

### ✅ Correct: Summing quantity_changed (absolute value)

```sql
-- WORKS - quantity_changed is the delta per transaction
SELECT
  il.consumable_item_number,
  SUM(ABS(il.quantity_changed)) AS total_wasted
FROM `wonder-raw-prod.mysql_batch_inventory.inventory_ledgers` il
JOIN `wonder-raw-prod.mysql_batch_inventory.inventory_transactions` it ON il.transaction_id = it.id
JOIN `wonder-raw-prod.mysql_batch_inventory.transaction_types` tt ON it.transaction_type_id = tt.id
WHERE tt.operation = 'Remove'
  AND tt.reason_code = 'Expired'
  AND tt.deleted_at IS NULL
GROUP BY il.consumable_item_number;
```

**Why This Matters**:
- `quantity_changed` = amount added/removed in this transaction (negative for removals)
- `result` = running balance after transaction

**Rule**: To calculate totals, sum `quantity_changed`. Use `ABS()` for removal amounts since they're negative.

---

## Waste Analysis - Reporting Weight Instead of Eaches (CRITICAL)

### ❌ Wrong: Reporting waste in grams/ounces (not actionable for business)

```sql
-- FAILS - results are hard to interpret for business users
-- "1,278,660g of pinto beans wasted" - what does this mean operationally?
SELECT
  il.consumable_item_number,
  il.item_number,
  SUM(ABS(il.quantity_changed)) AS total_quantity_wasted,
  il.uom
FROM `wonder-raw-prod.mysql_batch_inventory.inventory_ledgers` il
JOIN `wonder-raw-prod.mysql_batch_inventory.transaction_types` tt ON il.transaction_type_id = tt.id
WHERE tt.operation = 'Remove'
  AND tt.reason_code IN ('Damaged', 'Expired', 'Auto-Expired')
  AND tt.deleted_at IS NULL
GROUP BY il.consumable_item_number, il.item_number, il.uom
ORDER BY total_quantity_wasted DESC;
-- Returns: "1,278,660g pinto beans" - Heavy items dominate the list
```

### ✅ Correct: Converting to eaches (individual units/packages)

```sql
-- WORKS - results are actionable: "1,066 pouches of pinto beans wasted"
WITH waste_by_eaches AS (
  SELECT
    il.consumable_item_number,
    il.item_number,
    il.wsku,
    tt.reason_code,
    -- Convert to eaches: divide by conversion_factor for weight-based items
    CASE
      WHEN il.uom = 'ea' THEN ABS(il.quantity_changed)
      WHEN il.conversion_factor > 0 THEN ABS(il.quantity_changed) / il.conversion_factor
      ELSE ABS(il.quantity_changed)
    END AS eaches_wasted,
    s.name AS site_name
  FROM `wonder-raw-prod.mysql_batch_inventory.inventory_ledgers` il
  JOIN `wonder-raw-prod.mysql_batch_inventory.transaction_types` tt
    ON il.transaction_type_id = tt.id
  JOIN `wonder-raw-prod.mysql_batch_inventory.sites` s
    ON il.site_id = s.id
  WHERE tt.operation = 'Remove'
    AND tt.reason_code IN ('Damaged', 'Expired', 'Auto-Expired', 'Temperature Breach',
                          'Received Damaged', 'Lost', 'Hot Holding Expiration')
    AND tt.deleted_at IS NULL
    AND s.deleted_at IS NULL
)
SELECT
  wbe.consumable_item_number,
  wbe.item_number,
  wi.name AS item_name,
  ROUND(SUM(wbe.eaches_wasted), 2) AS total_eaches_wasted,
  COUNT(*) AS num_waste_transactions,
  COUNT(DISTINCT wbe.site_name) AS num_hdrs_affected
FROM waste_by_eaches wbe
LEFT JOIN `wonder-raw-prod.mysql_batch_product_catalog.wonder_items` wi
  ON wbe.item_number = wi.item_number
WHERE wbe.item_number IS NOT NULL
GROUP BY wbe.consumable_item_number, wbe.item_number, wi.name
ORDER BY total_eaches_wasted DESC;
-- Returns: "5,046 pita breads" - Shows real operational problems
```

**Why This Matters**: Weight-based and eaches-based waste analysis show COMPLETELY different results:

**By Weight (grams):**
1. Pinto Beans - 1,278,660g (heavy pouches)
2. Chicken Wings - 888,604g (heavy protein)
3. Black Beans - 829,800g (heavy pouches)
4. Lentil Mix - 788,250g (heavy pouches)
5. Fries - 524,233g (potatoes are heavy)

**By Eaches (units):**
1. Mini Pita Bread - 5,046 units (lightweight but frequent waste)
2. Pork Egg Rolls - 3,956 units (expiration issues)
3. Herb Butter Coins - 3,250 units (small packages)
4. Poke Rice - 2,508 units (frequent hot holding expiration)
5. Jasmine Rice - 1,848 units (expiration issues)

**The business implications are very different:**
- **Weight analysis** highlights heavy items → suggests cost/volume issues
- **Eaches analysis** highlights frequent waste → suggests operational/handling issues

**For most business questions (waste reduction, ordering, operations), eaches is the right metric.**

**Pattern**:
- **Use eaches for**: Waste reduction analysis, ordering decisions, operational improvements
- **Use weight for**: Cost analysis (when combined with per-gram pricing)
- **Default to eaches** unless specifically asked for weight or cost
- **conversion_factor**: How many base units (grams) in ONE package/unit
  - Example: Pinto Beans [Pouch, 1200g] → conversion_factor = 1200
  - 1,278,660g waste ÷ 1200 = 1,066 pouches

**Real Example**: When asked "which items caused the biggest waste", the answer changes dramatically:
- By weight: "Beans are the problem" (heavy items)
- By eaches: "We're wasting thousands of bread products" (lightweight but high frequency)

Both are true, but they point to different operational issues that need different solutions.

---

## State Calculation - Wrong Field Relationship

### ❌ Wrong: Assuming available equals on_hand

```sql
-- FAILS - available is not the same as on_hand
SELECT consumable_item_number
FROM `wonder-raw-prod.mysql_batch_inventory.inventory_state`
WHERE on_hand > 0
  AND available = on_hand;  -- This is not always true!
```

### ✅ Correct: Understanding available = on_hand - reserved

```sql
-- WORKS - available is on_hand minus reserved
SELECT
  consumable_item_number,
  on_hand,
  reserved,
  available,
  (on_hand - reserved) AS calculated_available
FROM `wonder-raw-prod.mysql_batch_inventory.inventory_state`
WHERE site_id = 'YOUR_SITE_ID'
  AND on_hand > 0;
```

**Why This Matters**: Items can be on_hand but not available because they're reserved for customer orders.

**Rule**: `available = on_hand - reserved`. Don't assume they're equal.

---

## Location Filtering - Confusing Class and Purpose

### ❌ Wrong: Filtering by purpose when you mean class

```sql
-- FAILS - purpose is specific location use, not temperature
-- This misses Reserve Storage, Pod Storage, etc.
SELECT *
FROM `wonder-raw-prod.mysql_batch_inventory.inventory_on_hand` ioh
JOIN `wonder-raw-prod.mysql_batch_inventory.hdr_locations` l ON ioh.location_id = l.id
WHERE l.purpose = 'CHILLED';  -- Purpose is not temperature!
```

### ✅ Correct: Using location_class for temperature

```sql
-- WORKS - location_class is the temperature classification
SELECT *
FROM `wonder-raw-prod.mysql_batch_inventory.inventory_on_hand` ioh
JOIN `wonder-raw-prod.mysql_batch_inventory.hdr_locations` l ON ioh.location_id = l.id
WHERE l.location_class = 'CHILLED'
  AND l.deleted_at IS NULL;
```

**Why This Matters**:
- `location_class` = Temperature zone (CHILLED, FROZEN, AMBIENT, HOT)
- `purpose` = Specific use (Pod Storage, Reserve Storage, Merchandiser, etc.)

**Rule**:
- Filter by `location_class` for temperature
- Filter by `purpose` for specific location type

---

## Location Filtering - Not Checking Soft Deletes

### ❌ Wrong: Including deleted locations

```sql
-- FAILS - includes deleted/decommissioned locations
SELECT
  l.name,
  SUM(ioh.quantity) AS total_quantity
FROM `wonder-raw-prod.mysql_batch_inventory.inventory_on_hand` ioh
JOIN `wonder-raw-prod.mysql_batch_inventory.hdr_locations` l ON ioh.location_id = l.id
GROUP BY l.name;
```

### ✅ Correct: Filtering out deleted locations

```sql
-- WORKS - only includes active locations
SELECT
  l.name,
  SUM(ioh.quantity) AS total_quantity
FROM `wonder-raw-prod.mysql_batch_inventory.inventory_on_hand` ioh
JOIN `wonder-raw-prod.mysql_batch_inventory.hdr_locations` l ON ioh.location_id = l.id
WHERE l.deleted_at IS NULL
GROUP BY l.name;
```

**Why This Matters**: Locations can be decommissioned but remain in the database. Historical inventory records still reference them.

**Rule**: Always add `WHERE l.deleted_at IS NULL` when joining to `hdr_locations`.

---

## Timezone - Using Raw Timestamps

### ❌ Wrong: Comparing UTC timestamps to Eastern dates

```sql
-- FAILS - created_at is UTC, but date filter might be interpreted as ET
SELECT *
FROM `wonder-raw-prod.mysql_batch_inventory.inventory_ledgers`
WHERE created_at >= '2025-10-23 00:00:00'
  AND created_at < '2025-10-24 00:00:00';
```

### ✅ Correct: Converting to target timezone or being explicit

```sql
-- WORKS - explicitly convert to ET for date boundaries
SELECT
  DATETIME(created_at, 'America/New_York') AS created_at_et,
  *
FROM `wonder-raw-prod.mysql_batch_inventory.inventory_ledgers`
WHERE DATETIME(created_at, 'America/New_York') >= '2025-10-23 00:00:00'
  AND DATETIME(created_at, 'America/New_York') < '2025-10-24 00:00:00';
```

**Why This Matters**: All Pantry timestamps are stored in UTC. Day boundaries in ET don't align with UTC boundaries.

**Rule**: When filtering by date, convert timestamps to target timezone using `DATETIME(field, 'America/New_York')`.

---

## Menu Availability - Wrong Join to Inventory

### ❌ Wrong: Joining menu tracking directly to on_hand

```sql
-- FAILS - menu_item_inventory_tracking doesn't have location_id
SELECT
  mit.menu_item_number,
  ioh.quantity
FROM `wonder-raw-prod.mysql_batch_inventory.menu_item_inventory_tracking` mit
JOIN `wonder-raw-prod.mysql_batch_inventory.inventory_on_hand` ioh
  ON mit.hdr_id = ioh.site_id;  -- Missing item join!
```

### ✅ Correct: Parsing caused_oos_item_numbers or using separate queries

```sql
-- WORKS - analyze OOS causes from tracking table
SELECT
  mit.menu_item_number,
  mit.available_result,
  mit.caused_oos_item_numbers,
  tt.operation,
  tt.reason_code
FROM `wonder-raw-prod.mysql_batch_inventory.menu_item_inventory_tracking` mit
JOIN `wonder-raw-prod.mysql_batch_inventory.inventory_transactions` it ON mit.transaction_id = it.id
JOIN `wonder-raw-prod.mysql_batch_inventory.transaction_types` tt ON it.transaction_type_id = tt.id
WHERE mit.hdr_id = 'YOUR_HDR_ID'
  AND mit.menu_item_number = 'YOUR_MENU_ITEM_NUMBER'
  AND tt.deleted_at IS NULL
ORDER BY mit.created_at DESC;
```

**Why This Matters**: `menu_item_inventory_tracking` tracks menu-level availability, not ingredient-level inventory. Use `caused_oos_item_numbers` to identify problem items.

**Pattern**: Don't join menu tracking to inventory directly. Instead, use the `caused_oos_item_numbers` field to identify which ingredients caused OOS.

---

## UOM Conversion - Comparing Different Units

### ❌ Wrong: Comparing quantities with different UOMs

```sql
-- FAILS - compares grams to ounces directly
SELECT
  consumable_item_number,
  SUM(quantity) AS total
FROM `wonder-raw-prod.mysql_batch_inventory.inventory_on_hand`
WHERE consumable_item_number = 'YOUR_ITEM'
GROUP BY consumable_item_number;
-- Result mixes 'g' and 'oz' if item has both UOMs!
```

### ✅ Correct: Filtering by UOM or converting to base units

```sql
-- WORKS - ensures consistent UOM
SELECT
  consumable_item_number,
  uom,
  SUM(quantity) AS total_quantity,
  SUM(quantity * conversion_factor) AS total_base_units
FROM `wonder-raw-prod.mysql_batch_inventory.inventory_on_hand`
WHERE consumable_item_number = 'YOUR_ITEM'
  AND quantity > 0
GROUP BY consumable_item_number, uom;
```

**Why This Matters**: Same item can be tracked in different UOMs (grams, ounces, each). Summing across UOMs gives meaningless results.

**Rule**: Either filter by specific UOM or multiply by `conversion_factor` to get base units before aggregating.

---

## Location Entry - Filtering by Operation Instead of Quantity Direction

### ❌ Wrong: Using operation = 'Move' to find items entering a location

```sql
-- FAILS - only shows Move operations, misses Receiving, Found items, Cycle Counts
SELECT
  il.batch_id,
  il.quantity_changed,
  l.name
FROM `wonder-raw-prod.mysql_batch_inventory.inventory_ledgers` il
JOIN `wonder-raw-prod.mysql_batch_inventory.hdr_locations` l ON il.location_id = l.id
JOIN `wonder-raw-prod.mysql_batch_inventory.transaction_types` tt ON il.transaction_type_id = tt.id
WHERE il.site_id = 'YOUR_SITE_ID'
  AND l.location_class = 'FROZEN'
  AND tt.operation = 'Move';  -- Wrong! Misses Add/Received, Adjust/Found, etc.
```

### ✅ Correct: Using quantity_changed > 0 for items entering

```sql
-- WORKS - finds all items entering freezer regardless of operation type
SELECT
  il.batch_id,
  il.quantity_changed,
  l.name,
  tt.operation,
  tt.reason_code
FROM `wonder-raw-prod.mysql_batch_inventory.inventory_ledgers` il
JOIN `wonder-raw-prod.mysql_batch_inventory.hdr_locations` l ON il.location_id = l.id
JOIN `wonder-raw-prod.mysql_batch_inventory.transaction_types` tt ON il.transaction_type_id = tt.id
WHERE il.site_id = 'YOUR_SITE_ID'
  AND l.location_class = 'FROZEN'
  AND il.quantity_changed > 0  -- Correct! Positive = entering location
  AND l.deleted_at IS NULL
  AND tt.deleted_at IS NULL;
```

**Why This Matters**: Items enter locations through multiple operations:
- **Add/Received** - Items received from supplier (most common for freezers/chillers)
- **Adjust/Cycle Counted** - Inventory count corrections (found more than expected)
- **Adjust/Found** - Previously missing items discovered
- **Move** - Items moved from another location (creates TWO entries: negative at source, positive at destination)

When someone asks about items "scanned into" or "entering" a location, they mean ALL ways items can be added, not just Move operations.

**Rule**:
- To find items entering a location: filter by `quantity_changed > 0` at that location
- To find items leaving a location: filter by `quantity_changed < 0` at that location
- Don't filter by `operation` type unless specifically asked for a particular operation

---

## Batch Identification - Using Non-Existent batch_number Field

### ❌ Wrong: Attempting to query batch_number field

```sql
-- FAILS - batch_number field does NOT exist in inventory_ledgers
SELECT
  il.batch_number,
  il.consumable_item_number,
  il.quantity_changed
FROM `wonder-raw-prod.mysql_batch_inventory.inventory_ledgers` il
WHERE il.site_id = 'YOUR_SITE_ID';
-- Error: Name batch_number not found
```

### ✅ Correct: Using batch_id or expires_at to identify batches

```sql
-- WORKS - use batch_id (UUID) to uniquely identify a batch
SELECT
  il.batch_id,
  il.consumable_item_number,
  il.quantity_changed,
  il.expires_at,
  il.uom
FROM `wonder-raw-prod.mysql_batch_inventory.inventory_ledgers` il
WHERE il.site_id = 'YOUR_SITE_ID'
ORDER BY il.consumable_item_number, il.expires_at;
```

### ✅ Alternative: Group by item and expiry date to see batch-level data

```sql
-- WORKS - batches are uniquely identified by item + location + expires_at
SELECT
  ioh.consumable_item_number,
  ioh.item_number,
  l.name AS location_name,
  ioh.expires_at,
  ioh.quantity,
  ioh.uom,
  ioh.batch_id  -- This is the unique batch identifier
FROM `wonder-raw-prod.mysql_batch_inventory.inventory_on_hand` ioh
JOIN `wonder-raw-prod.mysql_batch_inventory.hdr_locations` l ON ioh.location_id = l.id
WHERE ioh.site_id = 'YOUR_SITE_ID'
  AND ioh.quantity > 0
  AND l.deleted_at IS NULL
ORDER BY ioh.consumable_item_number, ioh.expires_at;
```

**Why This Matters**: There is no `batch_number` field in Pantry tables. Batches are identified by:
- `batch_id` (UUID) - Unique identifier for a specific batch
- Combination of `consumable_item_number` + `location_id` + `expires_at` - Natural batch grouping

**Rule**:
- Use `batch_id` when you need a unique batch identifier
- Use `expires_at` when grouping or displaying batch information
- Never query for `batch_number` - this field does not exist

---

## Missing Site Join - Ambiguous site_id

### ❌ Wrong: Not joining to sites table for site name

```sql
-- FAILS - only shows site_id UUID, not human-readable name
SELECT
  site_id,
  consumable_item_number,
  quantity
FROM `wonder-raw-prod.mysql_batch_inventory.inventory_on_hand`
WHERE quantity > 0;
-- Results show: "a2133e5b-021b-4340-9d8e-1b73294a79f8" instead of "Manhattan HDR"
```

### ✅ Correct: Joining to sites for readable names

```sql
-- WORKS - shows human-readable site name
SELECT
  s.name AS site_name,
  ioh.consumable_item_number,
  ioh.quantity
FROM `wonder-raw-prod.mysql_batch_inventory.inventory_on_hand` ioh
JOIN `wonder-raw-prod.mysql_batch_inventory.sites` s ON ioh.site_id = s.id
WHERE ioh.quantity > 0
  AND s.deleted_at IS NULL;
-- Results show: "Manhattan HDR"
```

**Why This Matters**: `site_id` is a UUID. Always join to `sites` table to get human-readable names.

**Rule**: When querying inventory, join to `sites` table for readable site names.

---

## Menu Item Name Joins - item_versions Duplication (CRITICAL)

### ❌ Wrong: Joining to item_versions without handling duplicates

```sql
-- FAILS - inflates counts due to duplicate rows in item_versions
-- item_versions has MULTIPLE rows per item_number (active, deleted, historical versions)
SELECT
  iv.name AS menu_item_name,
  COUNT(*) as times_cooked,
  SUM(ABS(mit.available_change)) as total_quantity_sold
FROM `wonder-raw-prod.mysql_batch_inventory.menu_item_inventory_tracking` mit
JOIN `wonder-raw-prod.mysql_batch_inventory.site_hdr_mapping` shm
  ON mit.hdr_id = shm.hdr_id
JOIN `wonder-raw-prod.mysql_batch_inventory.sites` s
  ON shm.site_id = s.id
JOIN `wonder-raw-prod.mysql_batch_inventory.transaction_types` tt
  ON mit.transaction_type_id = tt.id
JOIN `secure-recipe-prod.mongo_batch_recipe_v2.item_versions` iv
  ON mit.menu_item_number = iv.item_number  -- Joins to MULTIPLE rows!
WHERE s.name = 'HDR: West Harrison'
  AND tt.reason_code = 'Cooked'
  AND iv.object_type = 'MENU'
GROUP BY iv.name;
-- Returns inflated counts (e.g., 60 instead of 2) because each transaction matches multiple item_versions rows
```

### ✅ Correct: Using DISTINCT in CTE to deduplicate item_versions

```sql
-- WORKS - deduplicates item_versions first, then joins
WITH menu_items AS (
  SELECT DISTINCT item_number, name  -- CRITICAL: Use DISTINCT here
  FROM `secure-recipe-prod.mongo_batch_recipe_v2.item_versions`
  WHERE LOWER(name) LIKE '%poke%bowl%'
    AND object_type = 'MENU'
    AND item_status = 'ACTIVE'
)
SELECT
  iv.name AS menu_item_name,
  COUNT(*) as times_cooked,
  SUM(CASE WHEN mit.available_change < 0 THEN ABS(mit.available_change) ELSE 0 END) as items_sold
FROM `wonder-raw-prod.mysql_batch_inventory.menu_item_inventory_tracking` mit
JOIN `wonder-raw-prod.mysql_batch_inventory.site_hdr_mapping` shm
  ON mit.hdr_id = shm.hdr_id
JOIN `wonder-raw-prod.mysql_batch_inventory.sites` s
  ON shm.site_id = s.id
JOIN `wonder-raw-prod.mysql_batch_inventory.transaction_types` tt
  ON mit.transaction_type_id = tt.id
JOIN menu_items iv  -- Now joins to deduplicated set
  ON mit.menu_item_number = iv.item_number
WHERE s.name = 'HDR: West Harrison'
  AND tt.reason_code = 'Cooked'
  AND tt.deleted_at IS NULL
  AND s.deleted_at IS NULL
GROUP BY iv.name;
```

### ✅ Alternative: Using ANY_VALUE() with proper GROUP BY

```sql
-- WORKS - uses ANY_VALUE to pick one name from duplicate rows
SELECT
  mit.menu_item_number,
  ANY_VALUE(iv.name) as menu_item_name,  -- Picks one name from duplicates
  COUNT(*) as times_cooked,
  SUM(CASE WHEN mit.available_change < 0 THEN ABS(mit.available_change) ELSE 0 END) as items_sold
FROM `wonder-raw-prod.mysql_batch_inventory.menu_item_inventory_tracking` mit
JOIN `wonder-raw-prod.mysql_batch_inventory.site_hdr_mapping` shm
  ON mit.hdr_id = shm.hdr_id
JOIN `wonder-raw-prod.mysql_batch_inventory.sites` s
  ON shm.site_id = s.id
JOIN `wonder-raw-prod.mysql_batch_inventory.transaction_types` tt
  ON mit.transaction_type_id = tt.id
LEFT JOIN `secure-recipe-prod.mongo_batch_recipe_v2.item_versions` iv
  ON mit.menu_item_number = iv.item_number
  AND iv.object_type = 'MENU'
WHERE s.name = 'HDR: West Harrison'
  AND tt.reason_code = 'Cooked'
  AND tt.deleted_at IS NULL
  AND s.deleted_at IS NULL
GROUP BY mit.menu_item_number;  -- Group by item_number, not name
```

**Why This Matters**: The `item_versions` table contains multiple rows per `item_number`:
- Active version (current menu item)
- Deleted version(s) (e.g., "Classic Burger" and "Classic Burger(deleted)")
- Historical versions (previous revisions)

Joining directly to `item_versions` without deduplication causes **each transaction to match multiple rows**, inflating your counts dramatically (often 20-30x the actual value).

**Real Example**: A query for fries sold returned "60 fries" when only 2 were actually sold because:
- 2 transactions occurred
- Each transaction matched 30+ rows in `item_versions` (active, deleted, historical versions)
- Total: 2 × 30 = 60 (incorrect)

**Pattern**:
- **Always use `SELECT DISTINCT item_number, name` when creating a CTE from item_versions**
- Or use `ANY_VALUE()` with `GROUP BY item_number` to pick one name per item
- Never join `item_versions` directly without handling duplicates

---

## Menu Item Sales Counting - Using Wrong Aggregation

### ❌ Wrong: Using SUM(ABS(available_change)) for sales counts

```sql
-- FAILS - double counts when there are both positive and negative changes
-- available_change can be negative (items cooked) or positive (corrections/adjustments)
SELECT
  COUNT(*) as transactions,
  SUM(ABS(mit.available_change)) as quantity_sold  -- Wrong! Counts both + and -
FROM `wonder-raw-prod.mysql_batch_inventory.menu_item_inventory_tracking` mit
JOIN `wonder-raw-prod.mysql_batch_inventory.transaction_types` tt
  ON mit.transaction_type_id = tt.id
WHERE tt.reason_code = 'Cooked';
-- If there are 2 transactions: -2.0 (cooked) and +2.0 (correction)
-- This returns 4.0 instead of 2.0
```

### ✅ Correct: Only counting negative changes (actual items cooked)

```sql
-- WORKS - only counts items actually removed/cooked (negative changes)
SELECT
  COUNT(*) as transactions,
  SUM(CASE WHEN mit.available_change < 0 THEN ABS(mit.available_change) ELSE 0 END) as items_cooked
FROM `wonder-raw-prod.mysql_batch_inventory.menu_item_inventory_tracking` mit
JOIN `wonder-raw-prod.mysql_batch_inventory.transaction_types` tt
  ON mit.transaction_type_id = tt.id
WHERE tt.reason_code = 'Cooked'
  AND tt.deleted_at IS NULL;
```

**Why This Matters**: In `menu_item_inventory_tracking`:
- **Negative `available_change`** = Items removed/cooked (e.g., -1.0 means one item cooked)
- **Positive `available_change`** = Corrections or adjustments (e.g., +2.0 means availability increased)

Using `SUM(ABS(available_change))` counts BOTH positive and negative changes, which inflates your sales numbers. You should **only count negative changes** for actual items prepared/sold.

**Pattern**:
- For sales/cooked counts: `SUM(CASE WHEN available_change < 0 THEN ABS(available_change) ELSE 0 END)`
- For inventory changes (both directions): `SUM(ABS(available_change))` is appropriate
- Always consider whether you want unidirectional (cooked only) or bidirectional (all changes) counts

---

## Menu Item Filtering - Confusing Entrees with Sides

### ❌ Wrong: Counting fries when asked about burgers

```sql
-- FAILS - returns fries, not burger entrees
-- When someone asks "how many burgers", they usually mean burger entrees, not fries
WITH burger_items AS (
  SELECT DISTINCT item_number, name
  FROM `secure-recipe-prod.mongo_batch_recipe_v2.item_versions`
  WHERE LOWER(name) LIKE '%burger%'  -- Matches "Burger Baby" brand fries!
    AND object_type = 'MENU'
    AND item_status = 'ACTIVE'
)
SELECT COUNT(*) as burgers_sold
FROM menu_item_inventory_tracking mit
JOIN burger_items bi ON mit.menu_item_number = bi.item_number;
-- Returns count including "Classic Fries, Burger Baby" and "Truffle Fries, Burger Baby"
```

### ✅ Correct: Filtering out sides to get only entrees

```sql
-- WORKS - excludes fries, pizza, and other sides
WITH burger_entrees AS (
  SELECT DISTINCT item_number, name
  FROM `secure-recipe-prod.mongo_batch_recipe_v2.item_versions`
  WHERE LOWER(name) LIKE '%burger%'
    AND LOWER(name) NOT LIKE '%fries%'  -- Exclude fries
    AND LOWER(name) NOT LIKE '%pizza%'  -- Exclude burger pizza
    AND object_type = 'MENU'
    AND item_status = 'ACTIVE'
)
SELECT
  be.name,
  COUNT(*) as burgers_sold
FROM menu_item_inventory_tracking mit
JOIN burger_entrees be ON mit.menu_item_number = be.item_number
JOIN transaction_types tt ON mit.transaction_type_id = tt.id
WHERE tt.reason_code = 'Cooked'
  AND tt.deleted_at IS NULL
GROUP BY be.name;
-- Returns only actual burger entrees (Bacon Cheeseburger, Classic Burger, etc.)
```

**Why This Matters**: Brand names like "Burger Baby" appear in both burger entrees AND side items:
- **Entrees**: "Bacon Cheeseburger, Burger Baby", "Classic Hamburger, Burger Baby"
- **Sides**: "Classic Fries, Burger Baby", "Truffle Fries, Burger Baby"

When a user asks "how many burgers were sold", they typically mean burger entrees, not fries. Searching for `%burger%` matches both.

**Pattern**:
- When searching for food categories, explicitly exclude sides and related items
- Common exclusions:
  - Burgers: exclude `%fries%`, `%pizza%` (some brands have "Burger Pizza")
  - Salads: exclude `%dressing%`, `%croutons%` if searching by brand
  - Bowls: exclude `%sauce%`, `%topping%` if searching broadly
- Always review the menu item names returned to verify you're getting the right category

**Real Example**: "How many burgers sold on Sunday?" initially returned 152 (fries + burgers), but the actual answer was 0 burgers and 6 fries.

---

## Summary Checklist

Before running Pantry queries, verify:

### Item Identifiers
- [ ] Using `consumable_item_number` for inventory-to-inventory joins
- [ ] Handling NULL `item_number` and `wsku` fields appropriately
- [ ] Using correct identifier when joining to external systems

### Batch Identification
- [ ] Using `batch_id` (not `batch_number` - that field doesn't exist)
- [ ] Using `expires_at` for batch grouping and display
- [ ] Understanding batches are identified by item + location + expires_at

### Table Selection
- [ ] Using base table names (no `_YYMMDD` suffixes)
- [ ] Avoiding `ztemp__` prefixed tables
- [ ] Querying production tables, not archives or staging

### Transaction Filtering
- [ ] Filtering by both `operation` AND `reason_code`
- [ ] Adding `WHERE deleted_at IS NULL` for transaction_types
- [ ] Using correct transaction types for waste (Damaged, Expired, etc.)
- [ ] Joining directly from `inventory_ledgers` to `transaction_types` (not through `inventory_transactions`)
- [ ] If using `inventory_transactions`, parsing the JSON array format of `transaction_type_id`

### Joins and Aggregations
- [ ] Summing `quantity_changed` (not `result`) for totals
- [ ] Using `ABS()` on negative removals
- [ ] Understanding `available = on_hand - reserved`
- [ ] Joining locations with `deleted_at IS NULL`
- [ ] **Converting to eaches** using conversion_factor (default for waste/inventory analysis)

### Location Filtering
- [ ] Using `location_class` for temperature (CHILLED, FROZEN, AMBIENT, HOT)
- [ ] Using `purpose` for specific location type
- [ ] Checking `deleted_at IS NULL` on hdr_locations

### Location Entry and Exit
- [ ] Using `quantity_changed > 0` to find items entering a location (not `operation = 'Move'`)
- [ ] Using `quantity_changed < 0` to find items leaving a location
- [ ] Including ALL operation types (Add, Adjust, Move) unless specifically filtering
- [ ] Understanding "scanning" means any transaction that changes location quantity

### Data Types and Units
- [ ] Converting TSL from hours to days (divide by 24)
- [ ] Handling UOM differences (filtering or converting)
- [ ] Converting UTC timestamps to ET with `DATETIME(field, 'America/New_York')`

### Menu Item Queries (CRITICAL)
- [ ] Using DISTINCT in CTE when querying item_versions (avoids duplicate row inflation)
- [ ] Or using ANY_VALUE() with GROUP BY item_number when joining to item_versions
- [ ] Only counting negative available_change for sales (not SUM(ABS(...)))
- [ ] Excluding sides when asked about entrees (e.g., exclude '%fries%' for burgers)
- [ ] Using site_hdr_mapping to join menu_item_inventory_tracking to sites

### Readability
- [ ] Joining to `sites` table for human-readable site names
- [ ] Joining to `hdr_locations` for location names
- [ ] Joining to `transaction_types` for operation/reason_code
