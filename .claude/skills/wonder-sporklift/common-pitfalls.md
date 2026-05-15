# Common Pitfalls and Gotchas - Wonder Sporklift

Critical mistakes to avoid when working with Sporklift warehouse inventory data, transaction ledgers, and purchase orders.

---

## Using Snapshots Instead of Ledger - Missing Transaction Details

Inventory snapshots only show point-in-time quantities, not the actual movements or shipment details.

### ❌ Wrong: Using snapshots to track outbound shipments
```sql
-- DOES NOT WORK: Snapshots don't have shipment/order information
SELECT
  vendor_sku,
  on_hand,
  snapshot_id
FROM `wonder-sporklift-prod.sporklift.dish_inventory_snapshot`
WHERE vendor_sku = '8805202'
ORDER BY created_at DESC;
-- Result: Only shows on-hand quantities at different times, no shipment data
```

### ✅ Correct: Use the ledger table for shipment tracking
```sql
-- Get actual outbound shipments with order IDs, batches, and quantities
SELECT
  ref_order_id,
  vendor_sku,
  sku_name,
  lot_expiration_id as batch,
  ABS(change_in_on_hand) as quantity_shipped,
  datetime_et as shipped_at,
  user_id as picker
FROM `wonder-dw-prod-brd.inventory.int_shiphero_ledger`
WHERE vendor_sku = '8805202'
  AND l1_action = 'Remove'
  AND l2_action = 'Transfer Out'
  AND datetime_utc >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
ORDER BY datetime_utc DESC;
```

**Why This Matters**: Snapshots are for "what's on hand now", ledger is for "what moved". Use the ledger when you need:
- Which order/PO an item was shipped on
- Batch/lot tracking for specific transactions
- Who picked/received items
- Timestamp of actual inventory movements
- Before/after quantities for each transaction

**Quick Decision Guide**:
- **Use Ledger** (`int_shiphero_ledger`) → Transaction questions: "What shipped on PO-82834?", "Who picked this order?", "What lots were used?"
- **Use Snapshots** (`dish_inventory_snapshot`) → Availability questions: "What's on-hand now?", "Do we have enough stock?", "When did we run out?"

---

## Table References - Unqualified Table Names

Using unqualified table names causes ambiguity and query failures in BigQuery.

### ❌ Wrong: Using unqualified table names
```sql
SELECT vendor_sku, on_hand
FROM dish_inventory_snapshot
WHERE facility_id = '46d337b4-7f61-4338-979a-5ee8d8e0071f';
```

### ✅ Correct: Fully qualified table names with backticks
```sql
SELECT vendor_sku, on_hand
FROM `wonder-sporklift-prod.sporklift.dish_inventory_snapshot`
WHERE facility_id = '46d337b4-7f61-4338-979a-5ee8d8e0071f';
```

**Why This Matters**: BigQuery requires fully qualified table names when querying across projects. Without them, queries will fail with "Table not found" errors.

**Pattern**: Always use backticks and format: `` `project-id.dataset.table_name` ``

---

## Snapshot Filtering - Including Test Data

Early August snapshot runs have NULL facility_id and no inventory data, which skews results.

### ❌ Wrong: Not filtering NULL facility_id records
```sql
SELECT
  COUNT(*) as num_snapshots
FROM `wonder-sporklift-prod.sporklift.dish_inventory_snapshot_runs`;
-- Returns 59,331 (includes 3,276 test records)
```

### ✅ Correct: Filter out test data with NULL facilities
```sql
SELECT
  COUNT(*) as num_snapshots
FROM `wonder-sporklift-prod.sporklift.dish_inventory_snapshot_runs`
WHERE facility_id IS NOT NULL;
-- Returns 56,055 (actual production snapshots)
```

**Why This Matters**: The 3,276 test snapshots (Aug 1-13, 2025) have NULL `facility_id` and `snapshot_url` with no corresponding inventory records. Including them produces incorrect counts and breaks joins.

**Pattern**: Always add `WHERE facility_id IS NOT NULL` when querying snapshot metadata

---

## Latest Snapshot Logic - Incorrect Window Functions

Getting the latest snapshot per facility requires proper partitioning to avoid returning all snapshots.

### ❌ Wrong: Using MAX without proper grouping
```sql
-- Returns multiple rows per facility
SELECT
  facility_id,
  snapshot_id,
  created_at
FROM `wonder-sporklift-prod.sporklift.dish_inventory_snapshot_runs`
WHERE created_at = (SELECT MAX(created_at) FROM `wonder-sporklift-prod.sporklift.dish_inventory_snapshot_runs`)
  AND facility_id IS NOT NULL;
```

### ✅ Correct: Window function with ROW_NUMBER per facility
```sql
-- Returns exactly one row per facility
SELECT
  facility_id,
  snapshot_id,
  created_at
FROM `wonder-sporklift-prod.sporklift.dish_inventory_snapshot_runs`
WHERE facility_id IS NOT NULL
QUALIFY ROW_NUMBER() OVER (PARTITION BY facility_id ORDER BY created_at DESC) = 1;
```

**Why This Matters**: Each facility has independent snapshot schedules. The first approach returns the absolute latest timestamp, which may exist for only one facility, excluding the others. The correct approach gets the latest snapshot for EACH facility independently.

**Pattern**: Use `ROW_NUMBER() OVER (PARTITION BY facility_id ORDER BY created_at DESC) = 1` with QUALIFY

---

## Timezone Confusion - Using Raw UTC Timestamps

All Sporklift timestamps are stored in UTC, but Wonder operates in Eastern Time (America/New_York).

### ❌ Wrong: Displaying UTC timestamps without conversion
```sql
SELECT
  order_number,
  po_created_at,
  expected_date
FROM `wonder-raw-prod.mysql_batch_sporklift.purchase_orders`
WHERE status = 'PENDING';
-- Returns timestamps like: 2025-11-17 18:29:05 (UTC)
```

### ✅ Correct: Convert to America/New_York timezone
```sql
SELECT
  order_number,
  DATETIME(TIMESTAMP(po_created_at), 'America/New_York') as po_created_ny,
  DATETIME(TIMESTAMP(expected_date), 'America/New_York') as expected_date_ny
FROM `wonder-raw-prod.mysql_batch_sporklift.purchase_orders`
WHERE status = 'PENDING';
-- Returns timestamps like: 2025-11-17 13:29:05 (Eastern)
```

**Why This Matters**: All business operations happen in Eastern Time. Displaying UTC timestamps confuses stakeholders and causes misalignment with other systems showing local time.

**Pattern**: For DATETIME fields: `DATETIME(TIMESTAMP(field), 'America/New_York')`. For TIMESTAMP fields: `DATETIME(field, 'America/New_York')`

---

## Virtual Lot Misunderstanding - Treating NO_LOT as Missing Data

Virtual lots with "NO_LOT" prefix are valid inventory records, not missing lot tracking.

### ❌ Wrong: Filtering out virtual lots as bad data
```sql
-- Excludes 92% of inventory!
SELECT vendor_sku, SUM(on_hand) as total_on_hand
FROM `wonder-sporklift-prod.sporklift.dish_inventory_snapshot`
WHERE snapshot_id = '<latest>'
  AND lot_id NOT LIKE 'NO_LOT%'
GROUP BY vendor_sku;
```

### ✅ Correct: Include virtual lots in analysis
```sql
-- Includes all inventory
SELECT
  vendor_sku,
  SUM(on_hand) as total_on_hand,
  SUM(CASE WHEN lot_id LIKE 'NO_LOT%' THEN on_hand ELSE 0 END) as virtual_lot_qty,
  SUM(CASE WHEN lot_id NOT LIKE 'NO_LOT%' THEN on_hand ELSE 0 END) as real_lot_qty
FROM `wonder-sporklift-prod.sporklift.dish_inventory_snapshot`
WHERE snapshot_id = '<latest>'
GROUP BY vendor_sku;
```

**Why This Matters**: Virtual lots (format: `"NO_LOT_QmluOjI0NzAyNTM2_150"`) represent items without specific lot/batch tracking in ShipHero. They are the majority of inventory (~92%) and should be included in all inventory counts.

**Pattern**: Don't filter out virtual lots unless specifically analyzing lot-tracked items

---

## Allocation Logic - Relying on Allocated Field

The `allocated` field in snapshots is rarely populated and doesn't reflect true allocations.

### ❌ Wrong: Using snapshot allocated field as source of truth
```sql
-- Returns misleading availability numbers
SELECT
  vendor_sku,
  SUM(on_hand) as total_on_hand,
  SUM(allocated) as total_allocated,
  SUM(available) as total_available
FROM `wonder-sporklift-prod.sporklift.dish_inventory_snapshot`
WHERE snapshot_id = '<latest>';
-- Shows only 7 allocated units across 1.7M+ on-hand (clearly incomplete)
```

### ✅ Correct: Understand allocations may be managed externally (Ladle)
```sql
-- Use on_hand as primary metric, note that allocations are external
SELECT
  vendor_sku,
  SUM(on_hand) as total_on_hand,
  -- Note: Allocations tracked in Ladle/Command Center, not here
  SUM(available) as snapshot_available
FROM `wonder-sporklift-prod.sporklift.dish_inventory_snapshot`
WHERE snapshot_id = '<latest>';
```

**Why This Matters**: Only 0.0004% of inventory shows allocations in snapshots (7 units out of 1.7M+). The true allocation logic likely happens in Ladle (demand planning) or Command Center before orders are placed. Don't rely on this field for availability decisions.

**Pattern**: Use `on_hand` as primary inventory metric; check with Ladle/Command Center for true allocations

---

## PO vs DTC PO Confusion - Querying Wrong Table

Regular purchase orders and DTC purchase orders have completely different schemas and purposes.

### ❌ Wrong: Querying purchase_orders for HDR ordering data
```sql
-- Returns only 769 CK1/DISH shipments + 1,340 vendor POs (not HDR orders!)
SELECT
  supplier_node_id,
  COUNT(*) as num_orders
FROM `wonder-raw-prod.mysql_batch_sporklift.purchase_orders`
GROUP BY supplier_node_id;
```

### ✅ Correct: Use dtc_purchase_orders for HDR-level ordering
```sql
-- Returns 66,452 DTC orders across 87 HDR locations
SELECT
  hdr_id,
  COUNT(*) as num_orders
FROM `wonder-raw-prod.mysql_batch_sporklift.dtc_purchase_orders`
GROUP BY hdr_id;
```

**Why This Matters**: Two completely separate systems:
- **`purchase_orders`**: Inter-facility transfers (CK1/DISH → Newark) and third-party vendor shipments to ShipHero (2,109 POs)
- **`dtc_purchase_orders`**: HDR-level ordering to stock individual restaurants (66,452 POs, 30x higher volume)

**Pattern**: Use `dtc_purchase_orders` for HDR analysis, `purchase_orders` for warehouse replenishment

---

## Status Value Inconsistency - Case-Sensitive Comparisons

Status fields have inconsistent casing (CLOSED vs closed, CANCELED vs CANCELLED).

### ❌ Wrong: Exact case-sensitive status matching
```sql
-- May miss records with lowercase 'closed'
SELECT COUNT(*) as closed_orders
FROM `wonder-raw-prod.mysql_batch_sporklift.purchase_orders`
WHERE status = 'CLOSED';
```

### ✅ Correct: Case-insensitive status comparison
```sql
-- Catches all variations
SELECT COUNT(*) as closed_orders
FROM `wonder-raw-prod.mysql_batch_sporklift.purchase_orders`
WHERE UPPER(status) = 'CLOSED';
```

**Why This Matters**: Data inconsistency exists in the source system. Regular POs use both `CLOSED` and `closed`, `CANCELED` and `CANCELLED`. Case-insensitive comparisons ensure complete results.

**Pattern**: Always use `UPPER(status)` or `LOWER(status)` when filtering by status

---

## Expiration Date Assumptions - Expecting Universal Coverage

Most inventory lots (~92%) don't have expiration dates because they use virtual lots.

### ❌ Wrong: Filtering only records with expiration_date
```sql
-- Excludes 92% of inventory!
SELECT vendor_sku, COUNT(*) as num_lots
FROM `wonder-sporklift-prod.sporklift.dish_inventory_snapshot`
WHERE snapshot_id = '<latest>'
  AND expiration_date IS NOT NULL
GROUP BY vendor_sku;
```

### ✅ Correct: Understand expiration dates only apply to lot-tracked items
```sql
-- Shows both tracked and untracked inventory
SELECT
  vendor_sku,
  COUNT(*) as total_lots,
  COUNT(expiration_date) as lots_with_expiry,
  SUM(on_hand) as total_on_hand,
  SUM(CASE WHEN expiration_date IS NOT NULL THEN on_hand ELSE 0 END) as tracked_on_hand
FROM `wonder-sporklift-prod.sporklift.dish_inventory_snapshot`
WHERE snapshot_id = '<latest>'
GROUP BY vendor_sku;
```

**Why This Matters**: Only ~8% of lots have expiration dates (real lots with perishable tracking). Virtual lots represent non-perishable or non-lot-tracked items. Filtering by expiration_date excludes most SKUs.

**Pattern**: For expiration analysis, filter for `expiration_date IS NOT NULL`. For inventory counts, include all records.

---

## SKU Column Confusion - Searching vendor_sku Instead of sku

**CRITICAL PITFALL**: The `purchase_order_items` table has TWO different SKU columns with very different meanings. Searching the wrong one will miss all results.

### ❌ Wrong: Searching vendor_sku for product SKUs
```sql
-- FINDS NOTHING: vendor_sku is the vendor's catalog number (e.g., "3554565"), not Wonder's SKU
SELECT
  po.order_number,
  poi.vendor_sku,
  poi.quantity
FROM `wonder-raw-prod.mysql_batch_sporklift.purchase_orders` po
JOIN `wonder-raw-prod.mysql_batch_sporklift.purchase_order_items` poi
  ON po.purchase_order_id = poi.purchase_order_id
WHERE poi.vendor_sku = '5181546'  -- This is Wonder's SKU, not vendor's!
  AND po.warehouse_id = '126631';
-- Returns: 0 rows (no matches)
```

### ✅ Correct: Search the sku column for Wonder's product SKUs
```sql
-- WORKS: sku contains Wonder's internal SKU with case pack info
SELECT
  po.order_number,
  poi.sku,            -- Wonder SKU with case pack: "5181546-24"
  poi.vendor_sku,     -- Vendor catalog SKU: "3554565"
  poi.quantity
FROM `wonder-raw-prod.mysql_batch_sporklift.purchase_orders` po
JOIN `wonder-raw-prod.mysql_batch_sporklift.purchase_order_items` poi
  ON po.purchase_order_id = poi.purchase_order_id
WHERE poi.sku LIKE '5181546%'  -- Search Wonder's SKU with wildcard for case packs
  AND po.warehouse_id = '126631';
-- Returns: 27 orders with "5181546-24" and "5181546-24pk"
```

**Why This Matters**:
- **`sku`** = Wonder's internal SKU **including case pack size** (e.g., "5181546-24", "5181546-24pk")
  - Format: `{base_sku}-{pack_size}` or `{base_sku}-{pack_size}pk`
  - This is what you search when looking for specific products
  - Example: "5181546-24" = Coca-Cola in 24-can cases
- **`vendor_sku`** = Vendor's own catalog number (e.g., "3554565")
  - This is the supplier's SKU, not Wonder's
  - Used for joining to inventory snapshots
  - You cannot search products by their Wonder SKU using this field

**Pattern**:
- **To find purchase orders for a product**: Search `poi.sku LIKE '{wonder_sku}%'`
- **To join to inventory snapshots**: Use `poi.vendor_sku = snapshot.vendor_sku`

---

## Cross-Dataset SKU Joins - Wrong Field Names

Vendor SKU field names differ across datasets, causing failed joins.

### ❌ Wrong: Assuming same field name everywhere
```sql
-- FAILS: purchase_order_items has 'sku' and 'vendor_sku', but which one?
SELECT s.vendor_sku, poi.sku
FROM `wonder-sporklift-prod.sporklift.dish_inventory_snapshot` s
JOIN `wonder-raw-prod.mysql_batch_sporklift.purchase_order_items` poi
  ON s.vendor_sku = poi.sku;
-- Produces wrong matches
```

### ✅ Correct: Join on vendor_sku in both tables
```sql
-- WORKS: Both tables have vendor_sku field
SELECT s.vendor_sku, poi.sku as wonder_sku, poi.vendor_sku
FROM `wonder-sporklift-prod.sporklift.dish_inventory_snapshot` s
JOIN `wonder-raw-prod.mysql_batch_sporklift.purchase_order_items` poi
  ON s.vendor_sku = poi.vendor_sku;
```

**Why This Matters**:
- Inventory snapshots use `vendor_sku` (supplier's SKU code)
- PO items have both `sku` (Wonder internal with case pack) AND `vendor_sku` (supplier's catalog SKU)
- Join on `vendor_sku` for correct mapping

**Pattern**: Always join inventory snapshots to PO items using `vendor_sku = vendor_sku`

---

## Facility Launch Dates - Comparing Unequal Time Periods

Facilities launched at different times, so historical comparisons are invalid.

### ❌ Wrong: Comparing 90-day trends across all facilities
```sql
-- MISLEADING: Arcadia only has 56 days of data!
SELECT
  facility_id,
  DATE(DATETIME(created_at, 'America/New_York')) as date_ny,
  COUNT(*) as snapshots_per_day
FROM `wonder-sporklift-prod.sporklift.dish_inventory_snapshot_runs`
WHERE facility_id IS NOT NULL
  AND created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 90 DAY)
GROUP BY facility_id, date_ny;
```

### ✅ Correct: Use relative launch-adjusted time periods
```sql
-- ACCURATE: Compare each facility from their launch date
SELECT
  n.facility_name,
  TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), MIN(r.created_at), DAY) as days_of_data,
  COUNT(*) as total_snapshots
FROM `wonder-sporklift-prod.sporklift.dish_inventory_snapshot_runs` r
JOIN `wonder-dw-prod-brd.command_center.nodes` n ON r.facility_id = n.facility_id
WHERE r.facility_id IS NOT NULL
GROUP BY n.facility_name;
-- Millington: 97 days, DISH: 92 days, Arcadia: 56 days
```

**Why This Matters**: Facilities launched on different dates:
- **Millington**: Aug 13, 2025 (oldest, 97 days)
- **DISH**: Aug 18, 2025 (92 days)
- **Arcadia**: Sep 23, 2025 (newest, 56 days)

**Pattern**: When doing time-series analysis, use facility-specific date ranges or note data coverage periods

---

## Audit Table Usage - Querying Main Table for History

Audit tables exist specifically for tracking change history, not main tables.

### ❌ Wrong: Trying to get status history from main purchase_orders table
```sql
-- Only shows current status, not historical transitions
SELECT
  order_number,
  status,
  updated_at
FROM `wonder-raw-prod.mysql_batch_sporklift.purchase_orders`
WHERE order_number = '251117DISH-SHIP00001';
-- Returns 1 row with current status
```

### ✅ Correct: Use audit table for change tracking
```sql
-- Shows all status transitions with timestamps
SELECT
  order_number,
  operation,
  status,
  DATETIME(TIMESTAMP(created_at), 'America/New_York') as changed_at_ny,
  updated_by
FROM `wonder-raw-prod.mysql_batch_sporklift.purchase_orders_audit`
WHERE order_number = '251117DISH-SHIP00001'
ORDER BY created_at;
-- Returns multiple rows showing PENDING → IN_PROGRESS → CLOSED
```

**Why This Matters**: Main tables only show current state. Audit tables (`purchase_orders_audit`, `dtc_purchase_orders_audit`) preserve complete history with INSERT and UPDATE operations, enabling root cause analysis and timeline reconstruction.

**Pattern**: Query `*_audit` tables when investigating order history, status transitions, or debugging issues

---

## Shipment Reference Confusion - Assuming External System Link

Shipment IDs in Sporklift may not directly map to Supply Chain shipment tables.

### ❌ Wrong: Joining Sporklift shipment_id to Supply Chain shipments
```sql
-- May produce no matches or wrong joins
SELECT po.order_number, s.shipment_id, sc_ship.status
FROM `wonder-raw-prod.mysql_batch_sporklift.purchase_orders` po
JOIN `wonder-raw-prod.pg_batch_supplychain.shipments` sc_ship
  ON po.shipment_reference_id = sc_ship.id;
-- Likely empty result set
```

### ✅ Correct: Understand Sporklift shipment IDs may be internal
```sql
-- Use shipment_reference_id for internal Sporklift tracking
SELECT
  po.order_number,
  po.shipment_reference_id,
  poi.shipment_id,
  poi.shipment_item_id
FROM `wonder-raw-prod.mysql_batch_sporklift.purchase_orders` po
JOIN `wonder-raw-prod.mysql_batch_sporklift.purchase_order_items` poi
  ON po.purchase_order_id = poi.purchase_order_id;
-- Shows Sporklift's internal shipment tracking
```

**Why This Matters**: Sporklift appears to maintain its own shipment tracking system separate from Supply Chain's shipment tables. Direct joins may not work without understanding the relationship mapping.

**Pattern**: Use shipment IDs within Sporklift tables; validate integration points before cross-system joins

---

## Performance - Full Table Scans on Snapshots

Querying 216M snapshot records without date filters causes slow, expensive queries.

### ❌ Wrong: Scanning entire snapshot history
```sql
-- Scans all 216M records (slow, expensive!)
SELECT vendor_sku, AVG(on_hand) as avg_on_hand
FROM `wonder-sporklift-prod.sporklift.dish_inventory_snapshot`
GROUP BY vendor_sku;
```

### ✅ Correct: Always filter by date range or snapshot_id
```sql
-- Scans only last 30 days (~25M records)
WITH recent_snapshots AS (
  SELECT snapshot_id
  FROM `wonder-sporklift-prod.sporklift.dish_inventory_snapshot_runs`
  WHERE facility_id IS NOT NULL
    AND created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
)
SELECT vendor_sku, AVG(on_hand) as avg_on_hand
FROM `wonder-sporklift-prod.sporklift.dish_inventory_snapshot` s
JOIN recent_snapshots rs ON s.snapshot_id = rs.snapshot_id
GROUP BY vendor_sku;
```

**Why This Matters**: The snapshot table contains 216M records. Scanning without filters:
- Takes 5-10 minutes to execute
- Processes GBs of data (high cost)
- Often times out

**Pattern**: Always filter snapshot queries by date range or specific `snapshot_id` values

---

## Missing Facility Name Joins - Showing UUIDs Instead of Names

Displaying facility UUIDs is not user-friendly; always join to Command Center nodes.

### ❌ Wrong: Returning raw facility_id UUIDs
```sql
SELECT
  facility_id,
  vendor_sku,
  SUM(on_hand) as total_on_hand
FROM `wonder-sporklift-prod.sporklift.dish_inventory_snapshot`
WHERE snapshot_id = '<latest>'
GROUP BY facility_id, vendor_sku;
-- Returns: 46d337b4-7f61-4338-979a-5ee8d8e0071f, 8806886, 1523
```

### ✅ Correct: Join to nodes table for human-readable names
```sql
SELECT
  n.facility_name,
  s.vendor_sku,
  SUM(s.on_hand) as total_on_hand
FROM `wonder-sporklift-prod.sporklift.dish_inventory_snapshot` s
JOIN `wonder-dw-prod-brd.command_center.nodes` n ON s.facility_id = n.facility_id
WHERE s.snapshot_id = '<latest>'
GROUP BY n.facility_name, s.vendor_sku;
-- Returns: DISH, 8806886, 1523
```

**Why This Matters**: Stakeholders don't know facility UUIDs. Always join to `command_center.nodes` for readable facility names, addresses, and metadata.

**Pattern**: Include `JOIN command_center.nodes ON facility_id = facility_id` in all facility-related queries

---

## DTC Item Quantity - Wrong Data Type Handling

DTC purchase order items use NUMERIC for quantity, not INTEGER like regular PO items.

### ❌ Wrong: Treating DTC quantity as INTEGER
```sql
-- May lose precision or fail type checks
SELECT
  sku,
  CAST(quantity AS INT64) as quantity
FROM `wonder-raw-prod.mysql_batch_sporklift.dtc_purchase_order_items`;
-- Truncates fractional quantities!
```

### ✅ Correct: Keep NUMERIC type for DTC quantities
```sql
-- Preserves fractional quantities
SELECT
  sku,
  quantity,  -- Already NUMERIC, no cast needed
  ROUND(quantity, 2) as quantity_rounded
FROM `wonder-raw-prod.mysql_batch_sporklift.dtc_purchase_order_items`;
```

**Why This Matters**: DTC POs can have fractional quantities (e.g., 2.5 units). Casting to INTEGER loses precision. Regular PO items use INTEGER because they don't need fractional quantities.

**Pattern**: Don't cast DTC `quantity` to INTEGER; use NUMERIC operations

---

## DTC Price Field - String Type Assumptions

DTC item prices are stored as STRING, not NUMERIC, requiring explicit casting.

### ❌ Wrong: Performing math on STRING price field
```sql
-- FAILS: Cannot multiply STRING by NUMERIC
SELECT
  sku,
  quantity,
  price,
  quantity * price as total_price
FROM `wonder-raw-prod.mysql_batch_sporklift.dtc_purchase_order_items`;
```

### ✅ Correct: Cast price to NUMERIC for calculations
```sql
-- WORKS: Cast STRING to NUMERIC first
SELECT
  sku,
  quantity,
  price,
  quantity * CAST(price AS NUMERIC) as total_price
FROM `wonder-raw-prod.mysql_batch_sporklift.dtc_purchase_order_items`;
```

**Why This Matters**: The `price` field in DTC items is stored as STRING type, likely due to historical data migration or schema evolution. Must cast to NUMERIC for any arithmetic operations.

**Pattern**: Always `CAST(price AS NUMERIC)` when doing calculations with DTC item prices

---

## HDR ID Special Case - DISH String vs UUID

The hdr_id field in DTC orders uses UUIDs for HDRs but the string "DISH" for the facility.

### ❌ Wrong: Assuming all hdr_id values are UUIDs
```sql
-- FAILS: "DISH" string doesn't exist in nodes table as facility_id
SELECT
  dtc.hdr_id,
  n.facility_name
FROM `wonder-raw-prod.mysql_batch_sporklift.dtc_purchase_orders` dtc
JOIN `wonder-dw-prod-brd.command_center.nodes` n ON dtc.hdr_id = n.facility_id;
-- Excludes all DISH orders
```

### ✅ Correct: Handle DISH string special case
```sql
-- WORKS: Use CASE or LEFT JOIN to handle "DISH" string
SELECT
  dtc.hdr_id,
  CASE
    WHEN dtc.hdr_id = 'DISH' THEN 'DISH'
    ELSE n.facility_name
  END as hdr_name
FROM `wonder-raw-prod.mysql_batch_sporklift.dtc_purchase_orders` dtc
LEFT JOIN `wonder-dw-prod-brd.command_center.nodes` n
  ON dtc.hdr_id = n.facility_id;
```

**Why This Matters**: Most `hdr_id` values are UUIDs referencing HDR locations in the nodes table. However, orders for the DISH facility use the literal string `"DISH"` instead of its UUID. This breaks standard joins.

**Pattern**: Use LEFT JOIN and CASE statement to handle "DISH" special case in DTC queries

---

## Summary Checklist

Before running Sporklift queries, verify:

**Table References**:
- [ ] All table names fully qualified with backticks: `` `project.dataset.table` ``
- [ ] No ambiguous or unqualified table names

**Snapshot Queries**:
- [ ] Filter `facility_id IS NOT NULL` to exclude test data
- [ ] Use window functions for latest snapshot per facility: `ROW_NUMBER() OVER (PARTITION BY facility_id ...)`
- [ ] Apply date range filters on queries scanning full snapshot history

**Timezone Handling**:
- [ ] Convert timestamps to America/New_York: DATETIME fields use `DATETIME(TIMESTAMP(field), 'America/New_York')`, TIMESTAMP fields use `DATETIME(field, 'America/New_York')`
- [ ] Document timezone in column aliases: `created_at_ny`, `snapshot_time_ny`

**PO Analysis**:
- [ ] Use correct table: `purchase_orders` for warehouse/vendor POs, `dtc_purchase_orders` for HDR orders
- [ ] Case-insensitive status comparisons: `UPPER(status) = 'CLOSED'`
- [ ] Join to `command_center.nodes` for facility names, not raw UUIDs

**Data Type Handling**:
- [ ] Cast DTC `price` to NUMERIC for calculations: `CAST(price AS NUMERIC)`
- [ ] Preserve NUMERIC type for DTC `quantity` (don't cast to INTEGER)
- [ ] Handle "DISH" string in `hdr_id` field (not a UUID)

**Cross-Dataset Joins**:
- [ ] Join snapshots to PO items using `vendor_sku = vendor_sku`
- [ ] Join to Supply Chain using `vendor_sku = supplier_sku`
- [ ] Verify shipment ID mappings before joining across systems

**Performance**:
- [ ] Date range filters on large tables (snapshots have 216M records)
- [ ] Use specific `snapshot_id` values when possible
- [ ] Aggregate before joining across datasets

**Data Quality**:
- [ ] Understand virtual lots ("NO_LOT" prefix) are valid inventory
- [ ] Don't rely on `allocated` field (rarely populated)
- [ ] Be aware of different facility launch dates for time-series analysis
- [ ] Use `*_audit` tables for change history, not main tables
