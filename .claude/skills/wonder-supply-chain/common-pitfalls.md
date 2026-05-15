# Common Pitfalls and Gotchas - POMS

Critical mistakes to avoid when working with Wonder's Purchase Order Management System.

---

## Using hdr_orders Instead of purchase_orders

### ❌ Wrong: Using hdr_orders for supply chain analysis
```sql
-- WRONG - hdr_orders contains customer orders, not supply chain orders
SELECT order_id, order_placed_date_utc
FROM `wonder-dw-prod-brd.orders.hdr_orders`
WHERE hdr_id = 'some-hdr-uuid'
```

### ✅ Correct: Use purchase_orders for supply chain
```sql
-- WORKS - purchase_orders contains supply chain orders to HDRs
SELECT po.id, po.place_at
FROM `wonder-raw-prod.pg_batch_supplychain.purchase_orders` po
JOIN `wonder-dw-prod-brd.command_center.nodes` receiver
  ON po.receiver_node_id = receiver.facility_id
WHERE receiver.facility_type = 'HDR'
```

**Key Distinction:**
| Table | Contains | Use For |
|-------|----------|---------|
| `hdr_orders` | Customer orders (app/web/marketplace) | Sales analysis, customer behavior |
| `purchase_orders` | Supply chain orders (DISH → HDR) | Inventory flow, wave timing, replenishment |

**POMS URL Format** - To view a purchase order in the UI:
```
https://supplychain.remarkablefoods.net/purchase-orders/<purchase_order_id>
```

---

## Purchase Plan Items - Field Name Errors

### ❌ Wrong: Using purchase_plan_id
```sql
-- FAILS - column doesn't exist
SELECT * FROM `wonder-raw-prod.pg_batch_supplychain.purchase_plan_items` WHERE purchase_plan_id = 'some-uuid'
```

### ✅ Correct: Use plan_id
```sql
-- WORKS
SELECT * FROM `wonder-raw-prod.pg_batch_supplychain.purchase_plan_items` WHERE plan_id = 'some-uuid'
```

**Join Pattern**:
```sql
-- Correct join
FROM `wonder-raw-prod.pg_batch_supplychain.purchase_plans` pp
JOIN `wonder-raw-prod.pg_batch_supplychain.purchase_plan_items` ppi ON pp.id = ppi.plan_id
```

---

## Purchase Plan Items - Missing wonder_sku

### ❌ Wrong: Looking for wonder_sku
```sql
-- FAILS - column doesn't exist in purchase_plan_items
SELECT wonder_sku FROM `wonder-raw-prod.pg_batch_supplychain.purchase_plan_items`
```

### ✅ Correct: Use supplier_sku only
```sql
-- WORKS
SELECT supplier_sku FROM `wonder-raw-prod.pg_batch_supplychain.purchase_plan_items`
```

**Field Comparison**:
| Table | Has supplier_sku | Has wonder_sku |
|-------|------------------|----------------|
| purchase_plan_items | ✅ Yes | ❌ No |
| purchase_order_items | ✅ Yes | ✅ Yes |

---

## CK1 ↔ DISH Node ID Exception

Most critical gotcha in the entire system.

### ❌ Wrong: Joining CK1/DISH to nodes table with UUIDs
```sql
-- FAILS - returns no results
SELECT *
FROM `wonder-raw-prod.pg_batch_supplychain.purchase_orders` po
JOIN `wonder-dw-prod-brd.command_center.nodes` n ON po.supplier_node_id = n.facility_id
WHERE po.supplier_node_id = 'CK1'
```

### ✅ Correct: Use facility names directly
```sql
-- WORKS - CK1 and DISH use string names
SELECT *
FROM `wonder-raw-prod.pg_batch_supplychain.purchase_orders` po
WHERE po.supplier_node_id = 'CK1'
  AND po.receiver_node_id = 'DISH'
```

**When to use UUIDs vs Names**:
- **CK1 → DISH**: Use `'CK1'` and `'DISH'` strings
- **DISH → HDR**: Use DISH UUID `'46d337b4-7f61-4338-979a-5ee8d8e0071f'` and HDR UUIDs
- **All other facilities**: Use UUIDs from nodes table

**Discovery Pattern**:
```sql
-- Check if facility uses names or UUIDs
SELECT DISTINCT
  supplier_node_id,
  receiver_node_id,
  CASE
    WHEN LENGTH(supplier_node_id) = 36 AND supplier_node_id LIKE '%-%' THEN 'UUID'
    ELSE 'NAME'
  END as id_format
FROM `wonder-raw-prod.pg_batch_supplychain.purchase_orders`
WHERE supplier_node_id IN ('CK1', 'DISH')
   OR receiver_node_id IN ('CK1', 'DISH')
LIMIT 10
```

---

## HDR Order Timing - Wrong Data Source

### ❌ Wrong: Querying purchase_orders for future HDR orders
```sql
-- Returns incomplete data - orders don't exist yet!
SELECT *
FROM `wonder-raw-prod.pg_batch_supplychain.purchase_orders`
WHERE place_at > CURRENT_TIMESTAMP()
  AND receiver_node_id IN (
    SELECT facility_id FROM `wonder-dw-prod-brd.command_center.nodes` WHERE facility_type = 'HDR'
  )
```

### ✅ Correct: Use purchase_plans for future analysis
```sql
-- WORKS - plans exist hours before orders
SELECT pp.place_at, COUNT(DISTINCT ppi.supplier_sku) as sku_count
FROM `wonder-raw-prod.pg_batch_supplychain.purchase_plans` pp
JOIN `wonder-raw-prod.pg_batch_supplychain.purchase_plan_items` ppi ON pp.id = ppi.plan_id
WHERE pp.place_at BETWEEN CURRENT_TIMESTAMP()
  AND TIMESTAMP_ADD(CURRENT_TIMESTAMP(), INTERVAL 8 HOUR)
GROUP BY pp.place_at
```

**Critical Timing**:
- **Purchase plans**: Created hours in advance
- **Purchase orders**: Created ~5 minutes before `place_at`
- **Cutoff**: For next 8 hours, use `purchase_plans`; for history, use `purchase_orders`

---

## Quantity Field Selection - Wrong Field for Analysis

### ❌ Wrong: Using shipped_quantity for order totals
```sql
-- Incorrect - this is what actually shipped, not what was ordered
SELECT SUM(shipped_quantity) as order_total
FROM `wonder-raw-prod.pg_batch_supplychain.purchase_order_items`
```

### ✅ Correct: Use placed_quantity for order totals
```sql
-- WORKS - final committed order amount
SELECT SUM(placed_quantity) as order_total
FROM `wonder-raw-prod.pg_batch_supplychain.purchase_order_items`
```

**Quantity Field Guide**:
| Field | Meaning | Use For |
|-------|---------|---------|
| `placed_quantity` | Final committed order | Order totals, planning analysis |
| `shipped_quantity` | Actually shipped | Fulfillment analysis, short picks |
| `received_quantity` | Confirmed received | Inventory updates, reconciliation |
| `shipped - received` | In transit | Current inventory in transit |

---

## Timezone Handling - Wrong Date Function

### ❌ Wrong: Using CURRENT_DATE() without timezone
```sql
-- Wrong timezone - compares UTC dates
WHERE DATE(place_at) = CURRENT_DATE()
```

### ✅ Correct: Convert to business timezone
```sql
-- WORKS - compares NY dates
WHERE DATE(DATETIME(TIMESTAMP(place_at), 'America/New_York'))
  = CURRENT_DATE('America/New_York')
```

**Critical Pattern**:
All timestamps in BigQuery are UTC. Wonder operates in America/New_York. **Always convert for business logic.**

```sql
-- Standard conversion pattern
DATETIME(TIMESTAMP(utc_column), 'America/New_York') as local_time
```

---

## Status vs Quantity-Based Business Logic

### ❌ Wrong: Trusting status field alone
```sql
-- Status field may lag operational reality
WHERE status = 'RECEIVED'
```

### ✅ Correct: Derive state from quantities
```sql
-- More reliable - based on actual quantities
WHERE received_quantity >= placed_quantity
```

**Recommended Pattern**:
```sql
SELECT
  id,
  status as recorded_status,
  CASE
    WHEN received_quantity >= placed_quantity THEN 'FULLY_RECEIVED'
    WHEN shipped_quantity > received_quantity THEN 'IN_TRANSIT'
    WHEN shipped_quantity = 0 THEN 'NOT_SHIPPED'
  END as derived_status
FROM `wonder-raw-prod.pg_batch_supplychain.purchase_order_items`
```

Use `derived_status` for business logic; use `recorded_status` for audit trails.

---

## Event Sourcing Pattern Context

**Note**: The source POMS database is PostgreSQL, so event records are created via PostgreSQL INSERT statements. However, when querying from BigQuery, you'll query the replicated event tables using BigQuery syntax. The event sourcing pattern in the source system creates immutable event records rather than updating existing rows.

---

## Schema Verification - Skipping Validation

### ❌ Wrong: Assuming column names without checking
```sql
-- Fails if you assumed wrong column name
SELECT purchase_plan_id FROM `wonder-raw-prod.pg_batch_supplychain.purchase_plan_items`
```

### ✅ Correct: Always verify schemas first
```bash
# Check schema before writing queries
bq show --schema wonder-raw-prod:pg_batch_supplychain.purchase_plan_items

# Test assumptions with sample query
bq query --dry_run "SELECT plan_id FROM \`wonder-raw-prod.pg_batch_supplychain.purchase_plan_items\` LIMIT 1"
```

**Mandatory Workflow**:
1. `bq show --schema` to verify column names
2. Sample query with `LIMIT 5` to verify data structure
3. Write full query with confidence

---

## Cross-Schema Joins - Missing Dataset Prefix

### ❌ Wrong: Forgetting dataset prefix
```sql
-- FAILS - ambiguous table reference
FROM purchase_orders po
JOIN nodes n ON po.supplier_node_id = n.facility_id
```

### ✅ Correct: Use fully qualified table names
```sql
-- WORKS - explicit dataset references
SELECT po.*, n.facility_name
FROM `wonder-raw-prod.pg_batch_supplychain.purchase_orders` po
JOIN `wonder-dw-prod-brd.command_center.nodes` n
  ON po.supplier_node_id = n.facility_id
```

**Pattern**: Always use backticks with full project.dataset.table format for cross-project joins.

---

## Facility Lookup - Using Wrong Identifier

### ❌ Wrong: Searching by wrong field
```sql
-- Returns nothing - DISH doesn't have a GP code
SELECT facility_id FROM `wonder-dw-prod-brd.command_center.nodes`
WHERE facility_name LIKE 'GP%' AND facility_name = 'DISH'
```

### ✅ Correct: Search by appropriate field
```sql
-- WORKS - DISH is a warehouse
SELECT facility_id, facility_name
FROM `wonder-dw-prod-brd.command_center.nodes`
WHERE facility_name = 'DISH'
  AND facility_type = 'WAREHOUSE'
```

**Facility Naming Patterns**:
- **HDRs**: GP codes (GP709, GP318, etc.) + facility_type = 'HDR'
- **Warehouses**: Names (DISH, CK1) + facility_type = 'WAREHOUSE'
- **Suppliers**: Company names + facility_type = 'SUPPLIER'

---

## Shipment Analysis - Incomplete Join Chain

### ❌ Wrong: Missing intermediate joins
```sql
-- FAILS - can't directly join shipments to purchase_orders
FROM `wonder-raw-prod.pg_batch_supplychain.shipments` s
JOIN `wonder-raw-prod.pg_batch_supplychain.purchase_orders` po ON s.??? = po.???  -- No direct relationship!
```

### ✅ Correct: Follow the complete join chain
```sql
-- WORKS - complete chain
SELECT s.*, po.id as order_id
FROM `wonder-raw-prod.pg_batch_supplychain.shipments` s
JOIN `wonder-raw-prod.pg_batch_supplychain.shipment_items` si ON s.id = si.shipment_id
JOIN `wonder-raw-prod.pg_batch_supplychain.purchase_order_items` poi ON si.purchase_order_item_id = poi.id
JOIN `wonder-raw-prod.pg_batch_supplychain.purchase_orders` po ON poi.purchase_order_id = po.id
```

**Critical Chain**:
```
shipments
  → shipment_items (via shipment_id)
    → purchase_order_items (via purchase_order_item_id)
      → purchase_orders (via purchase_order_id)
        → nodes (via supplier_node_id / receiver_node_id)
```

---

## Time Range Selection - Wrong Interval Syntax

### ❌ Wrong: Using INTERVAL incorrectly
```sql
-- FAILS - wrong syntax
WHERE created_at >= CURRENT_TIMESTAMP() - INTERVAL 6 HOUR
```

### ✅ Correct: Use TIMESTAMP_SUB
```sql
-- WORKS - BigQuery syntax
WHERE created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 6 HOUR)
```

**BigQuery vs PostgreSQL**:
| Operation | BigQuery | PostgreSQL |
|-----------|----------|------------|
| Subtract time | `TIMESTAMP_SUB(ts, INTERVAL 6 HOUR)` | `ts - INTERVAL '6 hours'` |
| Add time | `TIMESTAMP_ADD(ts, INTERVAL 1 DAY)` | `ts + INTERVAL '1 day'` |
| Current time | `CURRENT_TIMESTAMP()` | `NOW()` |

---

## Data Freshness - Ignoring _sync_time

### ❌ Wrong: Assuming data is real-time
```sql
-- May be analyzing stale data without knowing
SELECT COUNT(*)
FROM `wonder-raw-prod.pg_batch_supplychain.purchase_orders`
WHERE created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR)
```

### ✅ Correct: Check data freshness first
```sql
-- Verify data is fresh enough for analysis
SELECT
  MAX(_sync_time) as last_sync,
  TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), MAX(_sync_time), MINUTE) as minutes_stale
FROM `wonder-raw-prod.pg_batch_supplychain.purchase_orders`;

-- Then query with confidence
SELECT COUNT(*)
FROM `wonder-raw-prod.pg_batch_supplychain.purchase_orders`
WHERE created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR)
  AND _sync_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 MINUTE)
```

**Rule**: For operational queries (last few hours), always check `_sync_time` to ensure data is recent enough.

---

## Summary Checklist

Before writing a complex query, verify:

- [ ] Checked schema with `bq show --schema`
- [ ] Verified join column names (e.g., `plan_id` not `purchase_plan_id`)
- [ ] Identified if facilities use UUIDs or names (CK1/DISH exception)
- [ ] Chose correct data source (plans for future, orders for history)
- [ ] Selected appropriate quantity field for analysis
- [ ] Included timezone conversion for timestamps
- [ ] Used fully qualified table names for cross-project joins
- [ ] Followed complete join chains (especially for shipments)
- [ ] Checked data freshness with `_sync_time`
