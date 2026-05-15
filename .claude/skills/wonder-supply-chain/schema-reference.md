# Purchase Order Management System (POMS) - Schema Reference

## BigQuery Dataset
**Location**: `wonder-raw-prod:pg_batch_supplychain`

All tables are batch-replicated from PostgreSQL with `_sync_time` tracking column.

---

## Core Entity Tables

### purchase_orders

Main purchase order records tracking orders from suppliers to receivers.

**Key Fields**:
- `id` (STRING/UUID) - Unique order identifier
- `supplier_node_id` (STRING) - References `nodes.facility_id` (EXCEPTION: 'CK1'/'DISH' use names)
- `receiver_node_id` (STRING) - References `nodes.facility_id` (EXCEPTION: 'CK1'/'DISH' use names)
- `place_at` (TIMESTAMP) - When order was/will be placed with supplier
- `status` (STRING) - Order status (see State Transitions below)
- `order_type` (STRING) - Type of order
- `created_at`, `updated_at` (TIMESTAMP) - Audit timestamps
- `created_by`, `updated_by` (STRING) - User attribution
- `_sync_time` (DATETIME) - Replication timestamp

**Indexes**:
- Primary: `id`
- Foreign: `supplier_node_id`, `receiver_node_id`

**Join Patterns**:
```sql
-- To items
purchase_orders.id = purchase_order_items.purchase_order_id

-- To facilities (except CK1/DISH)
purchase_orders.supplier_node_id = nodes.facility_id
purchase_orders.receiver_node_id = nodes.facility_id
```

---

### purchase_order_items

Individual line items within purchase orders.

**Key Fields**:
- `id` (STRING/UUID) - Unique item identifier
- `purchase_order_id` (STRING/UUID) - References `purchase_orders.id`
- `supplier_sku` (STRING) - Supplier's product identifier
- `wonder_sku` (STRING) - Wonder's internal product identifier
- `delivery_date` (DATE) - Expected/actual delivery date
- `status` (STRING) - Item status
- `uom` (STRING) - Unit of measure

**Quantity Fields** (all INTEGER):
- `ideal_quantity` - Planning target
- `planned_quantity` - Planned allocation
- `placed_quantity` - **Final committed order amount** ⭐ Use this for order totals
- `shipped_quantity` - Actually shipped by supplier
- `delivered_quantity` - Delivered to receiver
- `received_quantity` - Confirmed received and verified
- `vendor_accepted_quantity` - Vendor confirmation amount
- `vendor_rejected_quantity` - Vendor rejected amount
- `vendor_adjusted_quantity` - Vendor adjusted amount
- `cancelled_quantity` - Cancelled portion
- `receiving_rejected_quantity` - Rejected during receiving
- `not_received_quantity` - Expected but not received

**Derived Calculations**:
```sql
-- In transit inventory
shipped_quantity - received_quantity as in_transit_qty

-- Short pick (vendor sent less than placed)
placed_quantity - shipped_quantity as short_pick_qty

-- Receiving issues
received_quantity - delivered_quantity as receiving_discrepancy
```

**Audit Fields**:
- `created_at`, `updated_at` (TIMESTAMP)
- `created_by`, `updated_by` (STRING)
- `text_search_vector` (TSVECTOR) - Full-text search index

---

### purchase_plans

Future purchase planning data. HDR orders exist here before converting to purchase_orders.

**Key Fields**:
- `id` (STRING/UUID) - Unique plan identifier
- `ladle_run_id` (STRING) - Planning batch identifier
- `supplier_node_id` (STRING) - References `nodes.facility_id` (EXCEPTION: 'CK1'/'DISH' use names)
- `receiver_node_id` (STRING) - References `nodes.facility_id` (EXCEPTION: 'CK1'/'DISH' use names)
- `place_at` (TIMESTAMP) - **When order should be placed** ⭐ Key for future queries
- `plan_at` (TIMESTAMP) - When plan was created by planning system
- `status` (STRING) - DRAFT | PLANNED
- `plan_type` (STRING) - Type of plan
- `schedule_id` (STRING) - Associated schedule

**Critical Timing Pattern**:
- **Small gap** (plan_at → place_at: ~5 minutes) = Real-time demand response
- **Large gap** (plan_at → place_at: hours) = Scheduled/batched planning

**Usage**:
- Query `purchase_plans` for future dispatch analysis (next 8 hours)
- HDR orders convert to `purchase_orders` a few minutes before `place_at`

**Join Patterns**:
```sql
-- To plan items
purchase_plans.id = purchase_plan_items.plan_id  -- NOT purchase_plan_id!

-- To facilities
purchase_plans.supplier_node_id = nodes.facility_id
purchase_plans.receiver_node_id = nodes.facility_id
```

---

### purchase_plan_items

Items within purchase plans.

**Key Fields**:
- `id` (STRING/UUID) - Unique item identifier
- `plan_id` (STRING/UUID) - References `purchase_plans.id` ⚠️ **NOT** `purchase_plan_id`
- `supplier_sku` (STRING) - Product identifier ⚠️ **NO** `wonder_sku` field
- `delivery_date` (DATE) - Planned delivery date
- `ideal_quantity` (INTEGER) - Target quantity
- `allocated_quantity` (INTEGER) - **Actually allocated** ⭐ Use this for accurate planning
- `status` (STRING) - Item status

**Critical Differences from purchase_order_items**:
| Field | Purchase Plans | Purchase Orders |
|-------|---------------|-----------------|
| Join field | `plan_id` | `purchase_order_id` |
| Product ID | `supplier_sku` only | `supplier_sku` + `wonder_sku` |
| Quantity field | `allocated_quantity` | `placed_quantity` |

---

### shipments

Shipment records tracking physical movement of goods.

**Key Fields**:
- `id` (STRING/UUID) - Unique shipment identifier
- `shipment_number` (STRING) - Human-readable shipment number
- `carrier` (STRING) - Shipping carrier
- `tracking_number` (STRING) - Carrier tracking number
- `ship_date` (DATE) - Date shipped
- `expected_delivery_date` (DATE) - Expected arrival
- `actual_delivery_date` (DATE) - Actual arrival
- `status` (STRING) - SHIPPED | RECEIVED | RECEIVING_REJECTED | RECEIVING_COMPLETE

**State Transitions**:
- `SHIPPED` → `SHIPPED` | `RECEIVED`
- `RECEIVED` (terminal)
- `RECEIVING_REJECTED` (terminal)
- `RECEIVING_COMPLETE` (terminal - triggers not_received_quantity calculation)

---

### shipment_items

Individual items within shipments.

**Key Fields**:
- `id` (STRING/UUID) - Unique item identifier
- `shipment_id` (STRING/UUID) - References `shipments.id`
- `purchase_order_item_id` (STRING/UUID) - References `purchase_order_items.id`
- `quantity` (INTEGER) - Quantity in this shipment

**Critical Join Chain**:
```sql
shipments.id
  → shipment_items.shipment_id
    → shipment_items.purchase_order_item_id
      → purchase_order_items.id
        → purchase_order_items.purchase_order_id
          → purchase_orders.id
            → nodes.facility_id (supplier/receiver)
```

**Example**: Find shipments with facility details:
```sql
SELECT
  s.shipment_number,
  supplier.facility_name,
  receiver.facility_name,
  COUNT(DISTINCT si.id) as item_count
FROM shipments s
JOIN shipment_items si ON s.id = si.shipment_id
JOIN purchase_order_items poi ON si.purchase_order_item_id = poi.id
JOIN purchase_orders po ON poi.purchase_order_id = po.id
JOIN nodes supplier ON po.supplier_node_id = supplier.facility_id
JOIN nodes receiver ON po.receiver_node_id = receiver.facility_id
GROUP BY s.shipment_number, supplier.facility_name, receiver.facility_name
```

---

## Event Sourcing Tables

Complete audit trails for all entity changes. Use these for:
- Historical state analysis
- Audit compliance
- Debugging state transitions

### Event Tables

- `purchase_order_events` - All purchase order state changes
- `purchase_order_item_events` - All item-level changes
- `purchase_plan_events` - Planning system decisions
- `purchase_plan_item_events` - Item allocation changes
- `shipment_events` - Shipment lifecycle events
- `shipment_item_events` - Item-level shipment changes

**Common Event Fields**:
- `event_id` (STRING/UUID) - Unique event identifier
- `entity_id` (STRING/UUID) - Reference to parent entity
- `event_type` (STRING) - Type of event (CREATED, UPDATED, STATUS_CHANGE, etc.)
- `event_data` (JSON) - Event payload with before/after state
- `originated_at` (TIMESTAMP) - When event actually occurred
- `created_at` (TIMESTAMP) - When event was recorded
- `created_by` (STRING) - User/service that triggered event

**PostgreSQL Insert Pattern**:
```sql
-- Create events rather than updating existing records
INSERT INTO purchase_plan_events (plan_id, place_at, details, ...)
VALUES (..., new_timestamp, '{"reason": "change_description"}', ...)
```

---

## Entity State Transitions

### Purchase Plan States

Simple two-state system:
```
DRAFT → DRAFT | PLANNED
PLANNED (terminal)
```

### Purchase Order States

**Planning Phase**:
```
DRAFT → PLANNED → PLACED | CLOSED
```

**Placement Phase** (vendor response):
```
PLACED → VENDOR_ACCEPTED | VENDOR_REJECTED | VENDOR_PARTIALLY_ACCEPTED | EXCEPTION
```

**Fulfillment Phase**:
```
VENDOR_ACCEPTED → PARTIALLY_SHIPPED | SHIPPED | PARTIALLY_RECEIVED | RECEIVED | CANCELLED
PARTIALLY_SHIPPED → SHIPPED | PARTIALLY_RECEIVED | RECEIVED | CANCELLED
SHIPPED → PARTIALLY_RECEIVED | RECEIVED
PARTIALLY_RECEIVED → RECEIVED | CANCELLED
```

**Exception Handling**:
```
CLOSED → CANCELLED | PARTIALLY_SHIPPED | SHIPPED | PARTIALLY_RECEIVED | RECEIVED
EXCEPTION → DRAFT | VENDOR_ACCEPTED
CANCELLED → PARTIALLY_SHIPPED | SHIPPED | PARTIALLY_RECEIVED | RECEIVED
```

**Terminal States**: `RECEIVED`, `VENDOR_REJECTED`, `VENDOR_PARTIALLY_ACCEPTED`

**Derived States from Quantities** (more reliable than status field):
```sql
CASE
  WHEN received_quantity >= placed_quantity THEN 'FULLY_RECEIVED'
  WHEN shipped_quantity > received_quantity THEN 'IN_TRANSIT'
  WHEN shipped_quantity > 0 AND received_quantity = 0 THEN 'SHIPPED_NOT_RECEIVED'
  WHEN shipped_quantity = 0 THEN 'NOT_SHIPPED'
  ELSE 'UNKNOWN'
END as derived_state
```

---

## Node Reference System

### Nodes Table

**Location**: `wonder-dw-prod-brd:command_center.nodes`

Central facility reference used across all Wonder systems.

**Schema**:
- `facility_id` (STRING) - Unique facility identifier (UUID or name)
- `facility_name` (STRING) - Human-readable name (e.g., "GP709", "DISH", "CK1")
- `facility_type` (STRING) - Classification (see below)
- `address` (STRING) - Physical address
- `shiphero_facility_id` (STRING) - External system reference

**Facility Types**:
- `HDR` (110 facilities) - Wonder restaurants
- `SUPPLIER` (41 facilities) - External suppliers
- `MANUFACTURER & SUPPLIER` (13 facilities) - Combined facilities
- `PRODUCTION` (8 facilities) - Wonder production facilities
- `WAREHOUSE` (3 facilities) - Distribution centers
- `NULL` (115 facilities) - Unclassified

### CK1 ↔ DISH Node ID Exception

**Standard Pattern** (most facilities):
```sql
-- UUIDs reference nodes table
WHERE supplier_node_id = '46d337b4-7f61-4338-979a-5ee8d8e0071f'  -- DISH UUID
```

**Exception Pattern** (CK1 and DISH internal transfers):
```sql
-- Facility names used directly as strings
WHERE supplier_node_id = 'CK1' AND receiver_node_id = 'DISH'
```

**Lookup Pattern**:
```sql
-- Get UUIDs for facilities that need them
SELECT facility_id, facility_name, facility_type
FROM `wonder-dw-prod-brd.command_center.nodes`
WHERE facility_name IN ('DISH', 'CK1', 'GP709')
```

**Testing Node ID Format**:
```sql
-- Check if using names or UUIDs
SELECT
  supplier_node_id,
  receiver_node_id,
  CASE
    WHEN LENGTH(supplier_node_id) = 36 AND supplier_node_id LIKE '%-%' THEN 'UUID'
    ELSE 'NAME'
  END as supplier_format
FROM `wonder-raw-prod.pg_batch_supplychain.purchase_orders` LIMIT 100
```

---

## Timezone Handling

**Critical**: All timestamps stored in UTC, but Wonder operates in America/New_York timezone.

### Common Patterns

**Convert to business timezone**:
```sql
DATETIME(TIMESTAMP(place_at), 'America/New_York') as place_at_ny
```

**Filter by current date in business timezone**:
```sql
WHERE DATE(DATETIME(TIMESTAMP(place_at), 'America/New_York'))
  = CURRENT_DATE('America/New_York')
```

**Find future scheduled items**:
```sql
WHERE DATETIME(TIMESTAMP(place_at), 'America/New_York')
  > CURRENT_DATETIME('America/New_York')
```

**Business day ranges** (e.g., 4pm-2am overnight shift):
```sql
WHERE DATETIME(TIMESTAMP(place_at), 'America/New_York') >= '2025-09-03 16:00:00'
  AND DATETIME(TIMESTAMP(place_at), 'America/New_York') < '2025-09-04 02:00:00'
```

---

## Archived and Temporary Tables

### Archived Tables (suffix: `_250722`)

Historical data from July 25, 2022:
- `purchase_orders_250722`
- `purchase_order_items_250722`
- `purchase_order_events_250722`
- `purchase_order_item_events_250722`
- `purchase_order_item_logs_250722`
- `shipments_250722`
- `shipment_items_250722`
- `shipment_events_250722`
- `shipment_item_events_250722`

### Temporary Tables (prefix: `ztemp__`)

Staging tables for ETL operations:
- `ztemp__*` - Staging data
- `ztemp__*__merge` - Merge operations

**Do not query these directly** - they're internal to the replication process.

---

## Log Tables

### purchase_order_item_logs

Detailed operation logs for purchase order items.

**Usage**: Debugging item-level operations and tracking detailed changes beyond event sourcing.

---

## Query Performance Tips

1. **Always filter on timestamps** to limit data scanning:
   ```sql
   WHERE created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
   ```

2. **Use explicit column selection** - never `SELECT *`

3. **Verify schemas before complex joins**:
   ```bash
   bq show --schema wonder-raw-prod:pg_batch_supplychain.table_name
   ```

4. **Check node ID format** before writing facility joins

5. **Consider _sync_time** for data freshness:
   ```sql
   SELECT MAX(_sync_time) as last_sync
   FROM `wonder-raw-prod.pg_batch_supplychain.purchase_orders`
   ```
