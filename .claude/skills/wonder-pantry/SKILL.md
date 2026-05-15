---
name: wonder-pantry
description: Expert knowledge of Wonder's Pantry inventory tracking system at HDRs (restaurants). Use when asked about anything to do with inventory at our restaurants, including waste, sales, inventory movement in their 4 walls of the restaurant, slacking, hot holding, menu item availability, task workflows, and more.
allowed-tools: Read, Grep, Glob
---

# Wonder Pantry Expert

Pantry is Wonder's inventory management system for tracking food and supplies at HDR (restaurant) locations. It manages inventory from order placement through receiving, storage, usage, and waste, tracking everything at the batch level with expiry dates.

## What This Skill Provides

- **Menu Item Sales Queries** - Find how many of each menu item was sold/prepared at HDRs
- **Current Inventory Queries** - Find what's on-hand at HDRs, by location, item, and batch
- **Transaction History** - Track how inventory moved and changed over time
- **Waste Analysis** - Identify items that were damaged, expired, or scrapped
- **Receiving Tracking** - Monitor what was ordered, shipped, and received
- **State Lifecycle** - Understand inventory flow through on_order → shipped → on_hand → reserved → available
- **Menu Availability** - Analyze why menu items went out of stock
- **Task Management** - Query cycle counts, pulls, slacking, and retherm operations
- **Cross-Dataset Join Guidance** - Navigate joins to product catalog and recipe databases

## When to Use This Skill

Use this skill when you need to:
- **Query menu item sales** - Find how many burgers, salads, poke bowls, etc. were sold at an HDR
- Query current inventory levels at specific HDRs or storage locations
- Analyze inventory transactions and movement history
- Calculate waste amounts (damaged, expired, scrapped items)
- Track purchase orders from POMS and OrderGrid
- Understand why menu items became unavailable
- Investigate inventory discrepancies or alerts
- Analyze task completion (cycle counts, pulls, retherm, slacking)
- Write queries joining Pantry tables with correct item identifiers
- Understand inventory state transitions and TSL calculations

## Core Concepts

### Database Locations

**Primary Pantry Data:**
- **Dataset**: `wonder-raw-prod.mysql_batch_inventory`
- **Access**: Via bq CLI or BigQuery Console
- **Source**: PostgreSQL database replicated to BigQuery

**Cross-Dataset References:**
- **Product Catalog**: `wonder-raw-prod.mysql_batch_product_catalog.wonder_items` - Component/ingredient names
- **Menu Item Names**: `secure-recipe-prod.mongo_batch_recipe_v2.item_versions` - Menu item names and metadata (object_type='MENU')
- **Supply Chain**: `wonder-raw-prod.mysql_batch_poms.*` - Purchase orders and shipments (see wonder-supply-chain skill)

**BRD Tables (Advanced Analytics Only):**
- **Dataset**: `wonder-dw-prod-brd.inventory`
- **When to use**: For pre-computed analytics like L4W rolling averages, forecast vs actual comparisons, or stockout RCA breakdowns
- **Key table**: `component_scorecard` - daily item/HDR metrics with 100+ pre-computed fields
- **Why raw is preferred**: BRD lacks menu item sales (the #1 query pattern), task management, and location-level detail. Most Pantry questions are better answered with raw data.

### Item Identifiers (CRITICAL)

Pantry tracks items using three different identifiers. Understanding which to use is critical for correct joins:

- **`item_number`** - The original item identifier, may be NULL for consumable-only items
- **`wsku`** - Wonder SKU, the sellable unit identifier, may be NULL for non-sellable items
- **`consumable_item_number`** - The consumable unit identifier, always present for tracked inventory

**Join Rule**: When joining tables, prefer `consumable_item_number` for inventory tracking and use `item_number` or `wsku` when you need to link to other systems. See [common-pitfalls.md](common-pitfalls.md) for detailed examples.

### Site and HDR Mapping (CRITICAL FOR MENU ITEM QUERIES)

**IMPORTANT**: The `menu_item_inventory_tracking` table uses a different identifier (`hdr_id`) than the rest of Pantry (`site_id`). You **MUST** use the `site_hdr_mapping` table to join menu item data to sites.

**The `site_hdr_mapping` table:**
- Maps `site_id` (used in most Pantry tables) to `hdr_id` (used in menu_item_inventory_tracking)
- Simple structure: `id`, `site_id`, `hdr_id`, timestamps
- Every site has exactly one corresponding hdr_id

**How to join menu item tracking to sites:**
```sql
FROM menu_item_inventory_tracking mit
JOIN site_hdr_mapping shm ON mit.hdr_id = shm.hdr_id
JOIN sites s ON shm.site_id = s.id
```

**Common mistake:** Trying to join `menu_item_inventory_tracking.hdr_id` directly to `sites.id` - this will return zero results because they use different ID spaces.

### Batch Tracking

**CRITICAL**: Pantry tracks inventory at the batch level. A "batch" is a group of the same item with the same expiration date at a specific location.

**Batch Identification:**
- **`batch_id`** (UUID) - Unique identifier for each batch
- **Natural batch key**: `consumable_item_number` + `location_id` + `expires_at`
- **⚠️ NO `batch_number` field exists** - Don't query for this field!

**How Batches Work:**
- Same item at same location with different expiry dates = different batches
- Same item at different locations with same expiry date = different batches
- Each batch is tracked separately with its own quantity and expiration

**Example**: If you receive 10 units of item 8805389 expiring 2026-04-17 and 8 units expiring 2026-02-19 in the same freezer, these are TWO separate batches with different `batch_id` values.

### Inventory State Lifecycle

Items progress through these states (see [state-lifecycle-guide.md](state-lifecycle-guide.md) for details):

1. **`on_order`** - Item ordered from supplier, not yet shipped
2. **`shipped`** - Item shipped from supplier, in transit
3. **`not_received`** - Item arrived but not fully received/put away
4. **`on_hand`** - Item received and available at HDR (sum across all locations and batches)
5. **`reserved`** - Item allocated for specific purpose (customer orders)
6. **`available`** - Item ready for use (on_hand - reserved)
7. **`tsl`** - Target Stock Level - quantity threshold used to trigger cycle counts when inventory exceeds this level

### Key Entity Relationships

```
COMPONENT INVENTORY (ingredients, supplies):
sites (HDR locations, site_id)
  ↓
hdr_locations (storage locations within HDR)
  ↓
inventory_on_hand (current inventory at specific location/batch)
  ↓
inventory_ledgers (transaction history by location/batch)
  ↑
inventory_transactions (transaction metadata)
  ↓
transaction_types (operation + reason_code)

inventory_state (aggregate state by item at HDR)
  ↓
inventory_state_tracking (state change history)

inventory_orders → inventory_order_items
receiving_groups (group orders for receiving)
task_cycle_counts (inventory count tasks)

MENU ITEM TRACKING (finished menu items):
sites (site_id) ← site_hdr_mapping → (hdr_id)
                                        ↓
                          menu_item_inventory_tracking (ledger of menu item availability changes)

CROSS-DATASET REFERENCES:
wonder_items (wonder-raw-prod.mysql_batch_product_catalog) - component/ingredient names
item_versions (secure-recipe-prod.mongo_batch_recipe_v2) - menu item names (MENU items)
```

### Location Classes and Purposes

**Location Classes**: CHILLED, FROZEN, AMBIENT, HOT

**Location Purposes**:
- Pod Storage - Chilled storage for ready-to-cook items
- Reserve Storage - Long-term storage (chilled or frozen)
- Merchandiser - Customer-facing display fridges
- Hot Hold Appliance - Holding cooked food hot
- Retherm Appliance - Reheating equipment
- Slacking Fridge - Thawing frozen items
- Non-Food - Supplies and packaging

### Transaction Operations

All inventory changes are recorded with a transaction_type_id that has:
- **`operation`**: Add, Remove, Move, Adjust, System, Revise
- **`reason_code`**: Specific reason (e.g., "Received", "Expired", "Cycle Counted")

**COMPREHENSIVE LIST - All transaction types seen in production (last 28 days):**

**Add Operations (items entering inventory):**
- **`Add/Received`** - Items received from supplier and put away (most common Add operation)
- `Add/Yielded via Production` - Finished products from production

**Remove Operations (items leaving inventory):**
- **`Remove/Cooked`** - Items used to prepare menu items for customers (THIS IS YOUR SALES PROXY! - 5.9M transactions)
- `Remove/Hot Holding Expiration` - Cooked items that expired in hot hold
- `Remove/Consumed via Production` - Items used as ingredients in production
- `Remove/Auto-Expired` - Items automatically marked expired by system
- `Remove/Consumed for Standard Operation` - Items consumed in daily operations
- `Remove/Expired` - Manually marked as expired
- `Remove/Expired Prepped Item` - Prepped items that expired
- **`Remove/Food Quality`** - Items removed due to food quality issues (1,748 transactions)
- `Remove/Damaged` - Items damaged during handling
- `Remove/Received Damaged` - Items damaged on receipt
- `Remove/Temperature Breach` - Items exposed to wrong temperature
- **`Remove/Received with Other Quality Issue`** - Items received with quality problems (93 transactions)
- `Remove/Received Spoiled` - Items received already spoiled
- `Remove/Received Mislabeled` - Items received with wrong labels
- `Remove/Received without Label` - Items received without labels
- `Remove/Returned to DISH` - Items sent back to distribution center
- `Remove/Purge` - Items purged from system
- `Remove/Marked OOS on KOM` - Items marked out of stock on Kitchen Operations Manager
- `Remove/Used for Testing or Training` - Items used in training
- `Remove/Internal Demand` - Items used internally
- `Remove/Inventory Inspection` - Items removed for inspection
- `Remove/Surprise and Delight` - Items given away for customer satisfaction

**Move Operations (items moving between locations):**
- `Move/Hot Hold` - Moving items to hot hold appliance (210K transactions)
- `Move/System-Directed Retherm` - System-triggered reheating (166K transactions)
- `Move/Self-Directed Retherm` - Manual reheating
- `Move/System-Directed Slack` - System-triggered thawing
- `Move/User-Directed Movement` - Manual movement between locations
- `Move/Opened for Prep` - Items opened and moved for prep

**Adjust Operations (inventory corrections):**
- `Adjust/Cycle Counted` - Regular inventory count corrections (326K transactions)
- `Adjust/Lost` - Items that went missing (33K transactions)
- `Adjust/Found` - Previously missing items discovered
- `Adjust/Location Counted` - Location-specific count corrections
- `Adjust/Hot Hold Shortage Reported upon Cook Request` - Shortage found when cooking
- `Adjust/Update Received Order` - Corrections to received orders
- `Adjust/Shelf Life Extension` - Extension of expiration dates
- `Adjust/Hot Hold Request Shortage Reported` - Hot hold shortage reported

**System Operations (system-generated transactions):**
- `System/Customer Order Remade` - Customer orders that were remade

**Revise Operations (data corrections):**
- `Revise/System Migration` - Historical data migration corrections

**Key Insights:**
- **Most common operation**: `Remove/Cooked` (5.9M transactions) - actual menu item sales
- **Food quality issues**: Use `Remove/Food Quality` and `Remove/Received with Other Quality Issue`
- **Waste analysis**: Focus on Expired, Damaged, Temperature Breach, and Food Quality reason codes
- **Inventory corrections**: `Adjust/Cycle Counted` is most common (326K transactions)

### UOM and Conversion Factors (CRITICAL FOR BUSINESS REPORTING)

**IMPORTANT**: Most business users care about **"eaches"** (individual units/packages) rather than total weight. Always calculate in eaches unless specifically asked for weight.

Items are tracked in various units of measure (UOM): ea (each), g (grams), oz (ounces), lb (pounds).

The `conversion_factor` in `inventory_ledgers`, `inventory_on_hand`, and related tables represents how many base units (grams) are in ONE package/unit.

**Converting to Eaches:**

```sql
-- Formula for converting any quantity to eaches (individual units)
CASE
  WHEN uom = 'ea' THEN quantity  -- Already in eaches
  WHEN conversion_factor > 0 THEN quantity / conversion_factor  -- Divide weight by package size
  ELSE quantity  -- Fallback if no conversion_factor
END AS eaches
```

**Example**: Pinto Beans [Pouch, 1200g]
- `conversion_factor` = 1200
- `uom` = 'g' (grams)
- If `quantity_changed` = 1200g, that's **1 pouch** (1200 / 1200 = 1)
- If `quantity_changed` = 2400g, that's **2 pouches** (2400 / 1200 = 2)

**Why This Matters:**
- By weight: "1,278,660g of pinto beans wasted" (hard to interpret)
- By eaches: "1,066 pouches of pinto beans wasted" (actionable)

**Critical Insight**: Items with different package weights will rank very differently when analyzed by weight vs. eaches:
- Heavy items (beans, proteins) dominate weight-based reports
- Lightweight items (bread, rice pouches) dominate count-based reports
- **Always ask which metric matters for the business question**

### Querying Menu Item Sales (CRITICAL)

**IMPORTANT**: Pantry tracks menu item preparation in the `menu_item_inventory_tracking` table. This is a ledger table that records every change to menu item availability.

**How to query menu item sales:**

**Step 1: Find the menu item**
Join to `secure-recipe-prod.mongo_batch_recipe_v2.item_versions` to search by menu item name:
```sql
SELECT DISTINCT item_number, name
FROM `secure-recipe-prod.mongo_batch_recipe_v2.item_versions`
WHERE LOWER(name) LIKE '%poke%bowl%'
  AND object_type = 'MENU'
  AND item_status = 'ACTIVE'
```

**Step 2: Count Cooked transactions**
Use `reason_code='Cooked'` in `menu_item_inventory_tracking` - each transaction with `available_change=-1.0` represents one menu item prepared:

```sql
SELECT
  COUNT(*) as items_prepared,
  SUM(ABS(mit.available_change)) as total_quantity
FROM `wonder-raw-prod.mysql_batch_inventory.menu_item_inventory_tracking` mit
JOIN `wonder-raw-prod.mysql_batch_inventory.site_hdr_mapping` shm
  ON mit.hdr_id = shm.hdr_id
JOIN `wonder-raw-prod.mysql_batch_inventory.sites` s
  ON shm.site_id = s.id
JOIN `wonder-raw-prod.mysql_batch_inventory.transaction_types` tt
  ON mit.transaction_type_id = tt.id
WHERE s.name = 'HDR: Astoria'
  AND DATE(DATETIME(TIMESTAMP(mit.created_at), 'America/New_York')) = '2025-10-23'
  AND tt.reason_code = 'Cooked'
  AND mit.menu_item_number = '8010695'
  AND tt.deleted_at IS NULL
  AND s.deleted_at IS NULL
```

**Key transaction types in menu_item_inventory_tracking:**
- **`System/Customer Order Placed`** - Customer places order (changes future availability)
- **`Remove/Cooked`** - Menu item actually prepared (THIS IS YOUR SALES METRIC!)
- **`System/Menu Item Refreshed`** - System recalculates availability
- **`Remove/Hot Holding Expiration`** - Prepared item expired
- **`System/Customer Order Cancelled`** - Customer cancelled order

**CRITICAL**: Use `Cooked` transactions, NOT `Customer Order Placed`. Cooked = actually prepared/sold.

**What menu_item_inventory_tracking DOES track:**
- When menu items are prepared/cooked (Cooked transactions)
- When customers place orders (Customer Order Placed)
- Menu item availability over time
- When menu items go out of stock

**What menu_item_inventory_tracking DOES NOT track:**
- Sales revenue or pricing
- Customer information
- Delivery status

### Locally-Sourced Orders (Instacart and Emergency Purchases)

**IMPORTANT**: Pantry tracks store manager emergency purchases (Instacart, local stores, etc.) but in a limited way that requires timestamp-based inference.

**Order Records** (`inventory_orders` table):
- **Order Type**: `LOCALLY_SOURCED_ORDER`
- **Order Method**: `PLACED_ON_PANTRY`
- **Display Name**: Usually indicates source - "instacart", "insta", "instacart shoprite", or item name like "guac", "guacamole"
- **Status**: Typically `RECEIVED`

**Key Limitation - No Item Linkage:**
- These order records have **ZERO items** in `inventory_order_items` table
- The order is essentially a placeholder/note that says "emergency purchase made"
- Actual items purchased appear separately in `inventory_ledgers` as:
  - `Add/Received` transactions (when items scanned and put away)
  - `Adjust/Found` transactions (when items added manually)

**To Find Locally-Sourced Orders:**
```sql
-- Find all Instacart/emergency purchases at an HDR
SELECT
  io.id,
  io.display_name,
  s.name AS site_name,
  io.order_status,
  DATETIME(io.created_time) AS created_at,
  io.created_by
FROM `wonder-raw-prod.mysql_batch_inventory.inventory_orders` io
JOIN `wonder-raw-prod.mysql_batch_inventory.sites` s ON io.site_id = s.id
WHERE io.order_type = 'LOCALLY_SOURCED_ORDER'
  AND s.name = 'HDR: Astoria'
  AND io.created_time >= DATETIME_SUB(CURRENT_DATETIME(), INTERVAL 7 DAY)
  AND s.deleted_at IS NULL
ORDER BY io.created_time DESC;
```

**To Infer Which Items Were From Instacart:**
Since there's no direct link, match by timestamp and site:
```sql
-- Items likely from an Instacart order (inference based on timing)
WITH instacart_order AS (
  SELECT id, site_id, display_name, created_time
  FROM `wonder-raw-prod.mysql_batch_inventory.inventory_orders`
  WHERE id = 'INSTACART_ORDER_ID'
)
SELECT
  DATETIME(TIMESTAMP(il.created_at), 'America/New_York') as created_at_et,
  il.consumable_item_number,
  il.item_number,
  wi.name as item_name,
  il.quantity_changed,
  il.uom,
  tt.operation,
  tt.reason_code,
  l.name as location_name,
  il.created_by
FROM `wonder-raw-prod.mysql_batch_inventory.inventory_ledgers` il
JOIN instacart_order io ON il.site_id = io.site_id
JOIN `wonder-raw-prod.mysql_batch_inventory.transaction_types` tt ON il.transaction_type_id = tt.id
JOIN `wonder-raw-prod.mysql_batch_inventory.hdr_locations` l ON il.location_id = l.id
LEFT JOIN `wonder-raw-prod.mysql_batch_product_catalog.wonder_items` wi ON il.item_number = wi.item_number
WHERE tt.operation IN ('Add', 'Adjust')
  AND tt.reason_code IN ('Received', 'Found')
  AND il.quantity_changed > 0
  -- Look within 2 hours before to 4 hours after order creation
  AND DATETIME(TIMESTAMP(il.created_at), 'America/New_York')
      BETWEEN DATETIME_SUB(io.created_time, INTERVAL 2 HOUR)
      AND DATETIME_ADD(io.created_time, INTERVAL 4 HOUR)
  AND tt.deleted_at IS NULL
  AND l.deleted_at IS NULL
ORDER BY il.created_at;
```

**Statistics (as of Nov 2025):**
- 566 total locally-sourced orders across 47 sites since May 2025
- Common uses: guacamole, tomatoes, and other fresh items that ran out
- All orders show as RECEIVED status

### Understanding "Scanning" and How Items Enter Locations

**CRITICAL**: When someone asks about items being "scanned into" a location or entering a location, they mean ANY transaction that adds positive quantity to that location, not just Move operations.

**Items enter a location through multiple operations:**

1. **Add/Received** - Items received from supplier and put away
   - Most common way items enter freezers, chillers, etc.
   - Positive `quantity_changed` at destination location

2. **Adjust/Cycle Counted** - Inventory count corrections
   - When physical count is higher than system count
   - Positive `quantity_changed` represents items "found"

3. **Adjust/Found** - Previously missing items discovered
   - Items found during operations
   - Positive `quantity_changed` at location where found

4. **Move** operations - Items moved between locations
   - Creates TWO ledger entries: negative at source, positive at destination
   - For "items entering", look for positive `quantity_changed` at destination

**To find items entering a location:**
- Filter by the destination location
- Look for `quantity_changed > 0` (positive values)
- Include ALL operation types (Add, Adjust, Move)
- Don't filter by operation type unless specifically asked

**Example - Wrong approach:**
```sql
-- INCORRECT - only shows Move operations, misses Receiving and Found items
WHERE tt.operation = 'Move' AND l.location_class = 'FROZEN'
```

**Example - Correct approach:**
```sql
-- CORRECT - shows all ways items entered the freezer
WHERE l.location_class = 'FROZEN' AND il.quantity_changed > 0
```

## Query Patterns

### Menu Item Sales - How Many Items Were Sold (MOST COMMON QUERY)

```sql
-- Find how many poke bowls (or any menu item) were sold at Astoria yesterday
-- Step 1: Search for the menu item by name
WITH menu_items AS (
  SELECT DISTINCT item_number, name
  FROM `secure-recipe-prod.mongo_batch_recipe_v2.item_versions`
  WHERE LOWER(name) LIKE '%poke%bowl%'  -- Search for menu item by name
    AND object_type = 'MENU'
    AND item_status = 'ACTIVE'
)
-- Step 2: Count Cooked transactions (actual items prepared)
SELECT
  iv.name AS menu_item_name,
  iv.item_number,
  COUNT(*) as times_cooked,
  SUM(CASE WHEN mit.available_change < 0 THEN ABS(mit.available_change) ELSE 0 END) as total_quantity_sold
FROM `wonder-raw-prod.mysql_batch_inventory.menu_item_inventory_tracking` mit
JOIN `wonder-raw-prod.mysql_batch_inventory.site_hdr_mapping` shm
  ON mit.hdr_id = shm.hdr_id
JOIN `wonder-raw-prod.mysql_batch_inventory.sites` s
  ON shm.site_id = s.id
JOIN `wonder-raw-prod.mysql_batch_inventory.transaction_types` tt
  ON mit.transaction_type_id = tt.id
JOIN menu_items iv
  ON mit.menu_item_number = iv.item_number
WHERE s.name = 'HDR: Astoria'  -- Or use s.id = 'site-uuid'
  AND DATE(DATETIME(TIMESTAMP(mit.created_at), 'America/New_York')) = '2025-10-23'
  AND tt.reason_code = 'Cooked'  -- CRITICAL: Cooked = actually prepared
  AND tt.deleted_at IS NULL
  AND s.deleted_at IS NULL
GROUP BY iv.name, iv.item_number
ORDER BY total_quantity_sold DESC;
```

**Key points:**
- Use `site_hdr_mapping` to join menu_item_inventory_tracking to sites (REQUIRED!)
- Filter by `reason_code='Cooked'` to get actual items prepared
- Join to `item_versions` to search by name and get readable menu item names
- Use `DISTINCT` in the CTE because item_versions has duplicate rows (CRITICAL - prevents count inflation!)
- Only count negative `available_change` (actual items cooked) - don't use `SUM(ABS(...))` which double-counts
- `available_change=-1.0` for most Cooked transactions (one item prepared)

### Current Inventory Levels at an HDR

```sql
-- Find all on-hand inventory at a specific HDR
SELECT
  s.name AS site_name,
  l.name AS location_name,
  l.location_class,
  ioh.consumable_item_number,
  ioh.item_number,
  ioh.wsku,
  ioh.quantity,
  ioh.uom,
  ioh.expires_at,
  ioh.updated_at
FROM `wonder-raw-prod.mysql_batch_inventory.inventory_on_hand` ioh
JOIN `wonder-raw-prod.mysql_batch_inventory.hdr_locations` l ON ioh.location_id = l.id
JOIN `wonder-raw-prod.mysql_batch_inventory.sites` s ON ioh.site_id = s.id
WHERE s.id = 'YOUR_SITE_ID'
  AND ioh.quantity > 0
  AND l.deleted_at IS NULL
  AND s.deleted_at IS NULL
ORDER BY ioh.consumable_item_number, ioh.expires_at;
```

### Items Entering a Location (Scanned In, Put Away, Received)

```sql
-- Find all items that entered a specific location or location type
-- Includes receiving, cycle count adjustments, found items, and moves
SELECT
  DATETIME(TIMESTAMP(il.created_at), 'America/New_York') AS created_at_et,
  il.batch_id,
  il.consumable_item_number,
  il.item_number,
  il.quantity_changed,
  il.uom,
  il.expires_at,
  l.name AS location_name,
  l.location_class,
  l.purpose,
  tt.operation,
  tt.reason_code,
  il.created_by
FROM `wonder-raw-prod.mysql_batch_inventory.inventory_ledgers` il
JOIN `wonder-raw-prod.mysql_batch_inventory.hdr_locations` l ON il.location_id = l.id
JOIN `wonder-raw-prod.mysql_batch_inventory.transaction_types` tt ON il.transaction_type_id = tt.id
WHERE il.site_id = 'YOUR_SITE_ID'
  AND l.location_class = 'FROZEN'  -- Or CHILLED, HOT, AMBIENT
  AND il.quantity_changed > 0  -- CRITICAL: positive = entering location
  AND DATE(DATETIME(TIMESTAMP(il.created_at), 'America/New_York')) = CURRENT_DATE()
  AND l.deleted_at IS NULL
  AND tt.deleted_at IS NULL
ORDER BY il.created_at DESC;
```

**Key Points:**
- Use `quantity_changed > 0` to find items entering (not `operation = 'Move'`)
- This captures Add/Received, Adjust/Cycle Counted, Adjust/Found, and Move operations
- Each Move creates two entries: negative at source, positive at destination
- Filter by `location_class` or `l.name` depending on specificity needed

### Aggregate Inventory State by Item

```sql
-- Get current inventory state for items at an HDR
SELECT
  s.name AS site_name,
  ist.consumable_item_number,
  ist.item_number,
  ist.on_order,
  ist.shipped,
  ist.not_received,
  ist.on_hand,
  ist.reserved,
  ist.available,
  ist.tsl AS target_stock_level,
  ist.updated_at
FROM `wonder-raw-prod.mysql_batch_inventory.inventory_state` ist
JOIN `wonder-raw-prod.mysql_batch_inventory.sites` s ON ist.site_id = s.id
WHERE s.id = 'YOUR_SITE_ID'
  AND (ist.on_hand > 0 OR ist.available > 0)
  AND s.deleted_at IS NULL
ORDER BY ist.consumable_item_number;
```

### Inventory Transaction History for an Item

```sql
-- Get transaction history for a specific item at an HDR
SELECT
  il.created_at,
  tt.operation,
  tt.reason_code,
  l.name AS location_name,
  il.consumable_item_number,
  il.quantity_changed,
  il.result AS quantity_after,
  il.uom,
  il.created_by,
  il.transaction_id
FROM `wonder-raw-prod.mysql_batch_inventory.inventory_ledgers` il
JOIN `wonder-raw-prod.mysql_batch_inventory.hdr_locations` l ON il.location_id = l.id
JOIN `wonder-raw-prod.mysql_batch_inventory.transaction_types` tt ON il.transaction_type_id = tt.id
WHERE il.site_id = 'YOUR_SITE_ID'
  AND il.consumable_item_number = 'YOUR_CONSUMABLE_ITEM_NUMBER'
  AND il.created_at >= '2025-10-01'
  AND l.deleted_at IS NULL
  AND tt.deleted_at IS NULL
ORDER BY il.created_at DESC;
```

### Waste Analysis - Items Damaged or Expired (IN EACHES)

**CRITICAL**: Most business users want waste in **eaches** (individual units), not weight. Use the conversion_factor to calculate units wasted.

```sql
-- Calculate waste in EACHES (individual units) across all HDRs
WITH waste_transactions AS (
  SELECT
    il.consumable_item_number,
    il.item_number,
    il.wsku,
    tt.reason_code,
    il.quantity_changed,
    il.conversion_factor,
    il.uom,
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
                          'Received Damaged', 'Hot Holding Expiration', 'Expired Prepped Item',
                          'Food Quality', 'Received with Other Quality Issue', 'Received Spoiled',
                          'Received Mislabeled', 'Received without Label')
    AND DATE(DATETIME(TIMESTAMP(il.created_at), 'America/New_York'))
        BETWEEN '2025-10-01' AND '2025-10-23'
    AND tt.deleted_at IS NULL
    AND s.deleted_at IS NULL
)
SELECT
  wt.consumable_item_number,
  wt.item_number,
  wi.name AS item_name,
  wt.uom,
  ROUND(SUM(wt.eaches_wasted), 2) AS total_eaches_wasted,
  COUNT(*) AS num_waste_transactions,
  COUNT(DISTINCT wt.site_name) AS num_hdrs_affected,
  STRING_AGG(DISTINCT wt.reason_code ORDER BY wt.reason_code) AS waste_reasons
FROM waste_transactions wt
LEFT JOIN `wonder-raw-prod.mysql_batch_product_catalog.wonder_items` wi
  ON wt.item_number = wi.item_number
WHERE wt.item_number IS NOT NULL
GROUP BY
  wt.consumable_item_number,
  wt.item_number,
  wi.name,
  wt.uom
ORDER BY total_eaches_wasted DESC
LIMIT 20;
```

**Key differences between weight and eaches analysis:**
- **By weight**: Heavy items (beans, proteins) dominate → "1,278kg of pinto beans"
- **By eaches**: Shows operational impact → "5,046 pita breads" (reveals handling/expiration issues)
- **Use eaches for**: Waste reduction, ordering decisions, expiration analysis
- **Use weight for**: Cost analysis (when you have per-gram pricing)

**Waste vs. Quality Issue Categories:**
- **Expiration waste**: Expired, Auto-Expired, Hot Holding Expiration, Expired Prepped Item
- **Damage/handling**: Damaged, Temperature Breach
- **Receiving issues**: Received Damaged, Received Spoiled, Received Mislabeled, Received without Label
- **Food quality**: Food Quality, Received with Other Quality Issue (specific quality concerns beyond damage/expiration)

### Order Tracking - What Was Received

```sql
-- Track orders and receiving status
SELECT
  io.poms_order_number,
  io.display_name,
  io.order_status,
  io.order_type,
  io.order_method,
  io.delivery_deadline,
  io.shipped_time,
  io.last_received_time,
  s.name AS site_name
FROM `wonder-raw-prod.mysql_batch_inventory.inventory_orders` io
JOIN `wonder-raw-prod.mysql_batch_inventory.sites` s ON io.site_id = s.id
WHERE io.site_id = 'YOUR_SITE_ID'
  AND io.delivery_deadline >= '2025-10-01'
  AND s.deleted_at IS NULL
ORDER BY io.delivery_deadline DESC;
```

### Finding Instacart and Locally-Sourced Orders

```sql
-- Find all Instacart/emergency purchases at an HDR
SELECT
  io.id,
  io.display_name,
  s.name AS site_name,
  io.order_status,
  DATETIME(io.created_time) AS created_at,
  io.created_by
FROM `wonder-raw-prod.mysql_batch_inventory.inventory_orders` io
JOIN `wonder-raw-prod.mysql_batch_inventory.sites` s ON io.site_id = s.id
WHERE io.order_type = 'LOCALLY_SOURCED_ORDER'
  AND s.name = 'HDR: Astoria'
  AND io.created_time >= DATETIME_SUB(CURRENT_DATETIME(), INTERVAL 30 DAY)
  AND s.deleted_at IS NULL
ORDER BY io.created_time DESC;
```

**To infer which items came from a specific Instacart order**, match ledger transactions by timestamp:
```sql
-- Items likely from an Instacart order (inference based on timing)
WITH instacart_order AS (
  SELECT id, site_id, display_name, created_time
  FROM `wonder-raw-prod.mysql_batch_inventory.inventory_orders`
  WHERE id = 'INSTACART_ORDER_ID'
)
SELECT
  DATETIME(TIMESTAMP(il.created_at), 'America/New_York') as created_at_et,
  il.consumable_item_number,
  il.item_number,
  wi.name as item_name,
  il.quantity_changed,
  il.uom,
  tt.operation,
  tt.reason_code,
  l.name as location_name,
  il.created_by
FROM `wonder-raw-prod.mysql_batch_inventory.inventory_ledgers` il
JOIN instacart_order io ON il.site_id = io.site_id
JOIN `wonder-raw-prod.mysql_batch_inventory.transaction_types` tt ON il.transaction_type_id = tt.id
JOIN `wonder-raw-prod.mysql_batch_inventory.hdr_locations` l ON il.location_id = l.id
LEFT JOIN `wonder-raw-prod.mysql_batch_product_catalog.wonder_items` wi ON il.item_number = wi.item_number
WHERE tt.operation IN ('Add', 'Adjust')
  AND tt.reason_code IN ('Received', 'Found')
  AND il.quantity_changed > 0
  -- Look within 2 hours before to 4 hours after order creation
  AND DATETIME(TIMESTAMP(il.created_at), 'America/New_York')
      BETWEEN DATETIME_SUB(io.created_time, INTERVAL 2 HOUR)
      AND DATETIME_ADD(io.created_time, INTERVAL 4 HOUR)
  AND tt.deleted_at IS NULL
  AND l.deleted_at IS NULL
ORDER BY il.created_at;
```

### Linking to POMS Purchase Orders (CROSS-SYSTEM JOIN)

**CRITICAL**: Pantry orders link directly to Supply Chain POMS purchase orders. Use this to trace items from supplier through receiving.

```sql
-- Link Pantry inventory to POMS purchase orders
WITH astoria AS (
  SELECT id FROM `wonder-raw-prod.mysql_batch_inventory.sites`
  WHERE name = 'HDR: Astoria' AND deleted_at IS NULL
),
-- Current inventory for an item
current_inventory AS (
  SELECT
    ioh.item_number,
    ioh.consumable_item_number,
    SUM(
      CASE
        WHEN ioh.uom = 'ea' THEN ioh.quantity
        WHEN ioh.conversion_factor > 0 THEN ioh.quantity / ioh.conversion_factor
        ELSE ioh.quantity
      END
    ) AS total_eaches
  FROM `wonder-raw-prod.mysql_batch_inventory.inventory_on_hand` ioh
  JOIN astoria a ON ioh.site_id = a.id
  WHERE ioh.item_number = 'YOUR_ITEM_NUMBER'
    AND ioh.quantity > 0
  GROUP BY ioh.item_number, ioh.consumable_item_number
),
-- Most recent POMS order for this item
most_recent_order AS (
  SELECT
    io.poms_order_id,
    io.poms_order_number,
    io.display_name AS pantry_order_name,
    DATETIME(TIMESTAMP(io.last_received_time), 'America/New_York') AS last_received_at_ny,
    ioi.item_number
  FROM `wonder-raw-prod.mysql_batch_inventory.inventory_orders` io
  JOIN astoria a ON io.site_id = a.id
  JOIN `wonder-raw-prod.mysql_batch_inventory.inventory_order_items` ioi
    ON io.id = ioi.order_id
  WHERE ioi.item_number = 'YOUR_ITEM_NUMBER'
    AND io.poms_order_id IS NOT NULL
  ORDER BY io.last_received_time DESC
  LIMIT 1
)
-- Join to POMS purchase orders (use supplier_sku for matching!)
SELECT
  ci.item_number,
  ci.total_eaches AS current_inventory_eaches,
  wi.name AS item_name,
  mro.poms_order_number,
  mro.pantry_order_name,
  mro.last_received_at_ny,
  DATETIME(TIMESTAMP(po.place_at), 'America/New_York') AS poms_placed_at_ny,
  po.status AS poms_order_status,
  supplier.facility_name AS supplier,
  poi.placed_quantity AS poms_placed_qty,
  poi.shipped_quantity AS poms_shipped_qty,
  poi.received_quantity AS poms_received_qty
FROM current_inventory ci
JOIN most_recent_order mro ON ci.item_number = mro.item_number
LEFT JOIN `wonder-raw-prod.mysql_batch_product_catalog.wonder_items` wi
  ON ci.item_number = wi.item_number
LEFT JOIN `wonder-raw-prod.pg_batch_supplychain.purchase_orders` po
  ON mro.poms_order_id = po.id
LEFT JOIN `wonder-raw-prod.pg_batch_supplychain.purchase_order_items` poi
  ON po.id = poi.purchase_order_id
  AND mro.item_number = poi.supplier_sku  -- CRITICAL: Use supplier_sku, not wonder_sku
LEFT JOIN `wonder-dw-prod-brd.command_center.nodes` supplier
  ON po.supplier_node_id = supplier.facility_id;
```

**Key Join Fields**:
- **Order level**: `inventory_orders.poms_order_id` = `purchase_orders.id`
- **Item level**: `inventory_order_items.poms_order_item_id` = `purchase_order_items.id`
- **Item matching**: Use `purchase_order_items.supplier_sku` (NOT `wonder_sku` which is often NULL)

**Important Notes**:
- Not all items flow through POMS - supply items (90xxxxx series) may have inventory but no POMS order linkage
- POMS data is in `wonder-raw-prod.pg_batch_supplychain` (PostgreSQL), not `mysql_batch_inventory`
- See the `wonder-supply-chain` skill for complete POMS schema details

### Menu Item Availability Analysis

```sql
-- Why did a menu item go out of stock?
SELECT
  s.name AS site_name,
  mit.service_date,
  mit.menu_item_number,
  mit.restaurant_id,
  mit.available_change,
  mit.available_result,
  mit.caused_oos_item_numbers,
  tt.operation,
  tt.reason_code,
  mit.created_at
FROM `wonder-raw-prod.mysql_batch_inventory.menu_item_inventory_tracking` mit
JOIN `wonder-raw-prod.mysql_batch_inventory.site_hdr_mapping` shm ON mit.hdr_id = shm.hdr_id
JOIN `wonder-raw-prod.mysql_batch_inventory.sites` s ON shm.site_id = s.id
JOIN `wonder-raw-prod.mysql_batch_inventory.transaction_types` tt ON mit.transaction_type_id = tt.id
WHERE s.name = 'HDR: Astoria'  -- Or use s.id = 'site-uuid'
  AND mit.menu_item_number = 'YOUR_MENU_ITEM_NUMBER'
  AND mit.service_date = '2025-10-23'
  AND s.deleted_at IS NULL
  AND tt.deleted_at IS NULL
ORDER BY mit.created_at DESC;
```

### Cycle Count Tasks

```sql
-- Get cycle count tasks and their status
SELECT
  tcc.id AS task_id,
  tcc.site_id,
  tcc.item_number,
  tcc.type,
  tcc.status,
  tcc.task_group,
  tcc.created_at,
  tcc.updated_at,
  tcc.created_by
FROM `wonder-raw-prod.mysql_batch_inventory.task_cycle_counts` tcc
WHERE tcc.site_id = 'YOUR_SITE_ID'
  AND tcc.created_at >= '2025-10-01'
  AND tcc.status IN ('pending', 'in_progress', 'completed')
ORDER BY tcc.created_at DESC;
```

### Receiving Groups - Batch Receiving

```sql
-- Track receiving groups and their completion status
SELECT
  rg.id AS receiving_group_id,
  rg.site_id,
  rg.group_order_type,
  rg.status,
  rg.delivery_deadline,
  rg.delivery_location,
  rg.completed_time,
  s.name AS site_name
FROM `wonder-raw-prod.mysql_batch_inventory.receiving_groups` rg
JOIN `wonder-raw-prod.mysql_batch_inventory.sites` s ON rg.site_id = s.id
WHERE rg.site_id = 'YOUR_SITE_ID'
  AND rg.delivery_deadline >= '2025-10-01'
  AND s.deleted_at IS NULL
ORDER BY rg.delivery_deadline DESC;
```

### Inventory State Changes Over Time

```sql
-- Track how inventory state changed for an item
SELECT
  ist.created_at,
  ist.consumable_item_number,
  ist.on_order_change,
  ist.shipped_change,
  ist.on_hand_change,
  ist.reserved_change,
  ist.available_change,
  ist.on_hand_result,
  ist.available_result,
  tt.operation,
  tt.reason_code
FROM `wonder-raw-prod.mysql_batch_inventory.inventory_state_tracking` ist
JOIN `wonder-raw-prod.mysql_batch_inventory.transaction_types` tt ON ist.transaction_type_id = tt.id
WHERE ist.site_id = 'YOUR_SITE_ID'
  AND ist.consumable_item_number = 'YOUR_CONSUMABLE_ITEM_NUMBER'
  AND ist.created_at >= '2025-10-01'
  AND tt.deleted_at IS NULL
ORDER BY ist.created_at DESC;
```

### Location Inventory Summary

```sql
-- Summarize inventory by location type
SELECT
  l.location_class,
  l.purpose,
  COUNT(DISTINCT ioh.consumable_item_number) AS unique_items,
  COUNT(*) AS total_batches,
  SUM(ioh.quantity) AS total_quantity
FROM `wonder-raw-prod.mysql_batch_inventory.inventory_on_hand` ioh
JOIN `wonder-raw-prod.mysql_batch_inventory.hdr_locations` l ON ioh.location_id = l.id
WHERE ioh.site_id = 'YOUR_SITE_ID'
  AND ioh.quantity > 0
  AND l.deleted_at IS NULL
GROUP BY l.location_class, l.purpose
ORDER BY l.location_class, l.purpose;
```

## Best Practices

1. **DEFAULT to eaches (units) for inventory analysis** - Unless specifically asked for weight or cost analysis, ALWAYS calculate inventory quantities in eaches (individual units/packages) using the conversion_factor. Business users care about "how many pita breads" not "how many grams of pita". See the "UOM and Conversion Factors" section for the formula.

2. **ALWAYS use site_hdr_mapping for menu item queries** - The `menu_item_inventory_tracking` table uses `hdr_id`, not `site_id`. You MUST join through `site_hdr_mapping` to connect menu items to sites. This is the #1 mistake when querying menu item data.

3. **Use DISTINCT when querying item_versions (CRITICAL!)** - The `secure-recipe-prod.mongo_batch_recipe_v2.item_versions` table has duplicate rows (active, deleted, historical versions). **ALWAYS** use `SELECT DISTINCT item_number, name` in CTEs or `ANY_VALUE()` with `GROUP BY item_number`. Joining without deduplication inflates counts by 20-30x. See common-pitfalls.md for detailed examples.

4. **For menu item sales, use Cooked transactions and count ONLY negative changes** - Filter by `reason_code='Cooked'` in `menu_item_inventory_tracking`, NOT `Customer Order Placed`. Cooked = actually prepared/sold. Use `SUM(CASE WHEN available_change < 0 THEN ABS(available_change) ELSE 0 END)` to count only items removed (cooked), NOT `SUM(ABS(available_change))` which double-counts.

5. **Distinguish entrees from sides** - When searching for food items (e.g., burgers), brand names like "Burger Baby" appear in both entrees AND sides (fries). Explicitly exclude sides with `AND LOWER(name) NOT LIKE '%fries%'` to get accurate entree counts.

6. **Always use fully qualified table names** - Include dataset: `` `wonder-raw-prod.mysql_batch_inventory.table_name` `` or `` `secure-recipe-prod.mongo_batch_recipe_v2.table_name` ``

7. **Use consumable_item_number for inventory joins** - When joining inventory tables (on_hand, ledgers, state), prefer `consumable_item_number` over `item_number` or `wsku` unless you specifically need to link to external systems

8. **Filter out archived tables** - Use current tables without date suffixes (e.g., use `inventory_ledgers` not `inventory_ledgers_251013`) and avoid `ztemp__` prefixed tables

9. **Check for deleted records** - Many tables have soft deletes. Add `WHERE deleted_at IS NULL` for sites, locations, and transaction_types

10. **Filter transaction types carefully** - Use both `operation` AND `reason_code` when filtering transactions, as reason codes can overlap across operations. See the comprehensive transaction type list in the "Transaction Operations" section for all available operations and reason codes used in production

11. **Handle NULL item identifiers** - Some records have NULL `item_number` or `wsku` but always have `consumable_item_number`. Use `COALESCE` or NULL-safe joins

12. **Use appropriate date filters** - All timestamps are in UTC. For Eastern Time, convert with `DATETIME(TIMESTAMP(field), 'America/New_York')`

13. **Join directly to transaction_types when possible** - `inventory_ledgers`, `inventory_state_tracking`, and `menu_item_inventory_tracking` have `transaction_type_id` as plain UUID strings. Join directly to `transaction_types` using this field. **Note**: `inventory_transactions.transaction_type_id` is stored as a JSON array string `["uuid"]` and requires string parsing if you must use it (see common-pitfalls.md)

14. **Sum quantities for totals** - When calculating totals from ledgers, sum `quantity_changed`. The `result` field shows running balance after each transaction

15. **Understand TSL** - TSL (Target Stock Level) is a quantity threshold, not a time duration. When inventory exceeds TSL, it may trigger cycle counts or other inventory management actions

## Supporting Documentation

- [schema-reference.md](schema-reference.md) - Complete table schemas, field descriptions, and relationships
- [common-pitfalls.md](common-pitfalls.md) - Common mistakes and correct patterns (especially join patterns)
- [state-lifecycle-guide.md](state-lifecycle-guide.md) - Deep dive on inventory state tracking system
- [transaction-types-reference.md](transaction-types-reference.md) - Complete list of all transaction operations and reason codes with usage examples
