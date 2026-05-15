---
name: wonder-sporklift
description: Expert knowledge of Wonder's Sporklift warehouse management system including the inventory transaction ledger (int_shiphero_ledger), inventory snapshots at ShipHero 3PL facilities, and purchase order fulfillment. Covers transaction-level tracking (outbound shipments, inbound receipts, waste, production), on-hand inventory levels, lot/batch tracking, expiration dates, regular purchase orders, DTC HDR orders, and ShipHero integration. Use when tracking specific order shipments, querying warehouse inventory levels, analyzing inventory movements, or investigating PO status across DISH, Millington, and Arcadia facilities.
allowed-tools: Read, Grep, Glob
---

# Wonder Sporklift Expert

Sporklift is Wonder's warehouse management integration system that tracks real-time inventory at three ShipHero-managed 3PL facilities and handles purchase order fulfillment. The system captures inventory snapshots every ~5 minutes and manages two types of purchase orders: regular inter-facility/vendor POs and DTC (Direct-to-Consumer) HDR-level orders.

## What This Skill Provides

- **Real-time Inventory Visibility** - Current on-hand quantities, allocations, and availability across 3 warehouses (DISH, Millington, Arcadia)
- **Transaction-Level Tracking** - Complete inventory movement ledger with outbound shipments, inbound receipts, production consumption, waste/shrinkage
- **Purchase Order Tracking** - Status monitoring for regular POs (CK1/DISH shipments, 3P vendors) and DTC POs (HDR-level ordering)
- **Outbound Shipment Details** - Item-level pick data with batch/lot tracking, picker information, bin locations, and timestamps
- **Expiration Management** - Lot-level tracking with expiration dates for perishable items, FEFO analysis
- **Historical Inventory Trends** - Time-series analysis of inventory levels with 216M+ snapshot records (5-minute intervals)
- **Supply Chain Integration** - Cross-project joins with POMS for replenishment planning, vendor SKU mapping
- **ShipHero Reconciliation** - Audit trails, shipment tracking, and ShipHero API data access via CloudFront URLs

## When to Use This Skill

Use this skill when you need to:
- Check current on-hand inventory levels at Wonder's warehouses
- Find which warehouse(s) have a specific SKU available
- Track outbound shipments (what items, batches, quantities shipped on specific orders)
- Investigate what was picked for a specific PO/transfer order
- Track purchase order status (pending, in progress, closed, canceled)
- Analyze inventory trends over time (velocity, stockouts, replenishment patterns)
- Identify expiring or expired inventory for waste prevention
- Monitor DTC purchase orders from HDR locations
- Trace shipments through the fulfillment pipeline with batch-level detail
- Investigate order fulfillment rates (quantity ordered vs received vs rejected)
- Audit purchase order changes and status transitions
- Analyze inventory movements (inbound, outbound, waste, production, adjustments)
- Plan replenishment by combining on-hand levels with open POs

## Core Concepts

### Database Locations

**Inventory Ledger (Transaction Log)**:
- **BigQuery Dataset**: `wonder-dw-prod-brd.inventory`
- **Table**: `int_shiphero_ledger`
- **Purpose**: Complete transaction-level inventory movement tracking (outbound shipments, inbound receipts, waste, production, adjustments)
- **Best For**: Tracking what was shipped, when, by whom, and in what batch/lot

**Inventory Snapshots**:
- **BigQuery Dataset**: `wonder-sporklift-prod.sporklift`
- **Tables**: `dish_inventory_snapshot`, `dish_inventory_snapshot_runs`
- **Purpose**: Point-in-time warehouse inventory levels from ShipHero API (snapshots every ~5 minutes)
- **Best For**: Current on-hand quantities, availability, historical trends

**Purchase Orders**:
- **BigQuery Dataset**: `wonder-raw-prod.mysql_batch_sporklift`
- **Tables**: `purchase_orders`, `purchase_order_items`, `dtc_purchase_orders`, `dtc_purchase_order_items`, plus `_audit` tables
- **Purpose**: Operational transaction data (MySQL batch replication)
- **Best For**: PO status, expected dates, fulfillment tracking

### ShipHero Facilities

Sporklift tracks inventory at three 3PL warehouses:

| Facility | Facility ID (UUID) | Location | Launched |
|----------|-------------------|----------|----------|
| **DISH** | `46d337b4-7f61-4338-979a-5ee8d8e0071f` | Fairfield, NJ | Aug 18, 2025 |
| **Millington** | `de117c76-d46f-4cf3-943e-37513b32be47` | Millington, NJ | Aug 13, 2025 |
| **Arcadia** | `070f0993-93d0-4518-bc58-b957130b3b81` | Hazle Township, PA | Sep 23, 2025 |

### Virtual Lots vs Real Lots

**Virtual Lots** (~92% of inventory):
- `lot_id` format: `"NO_LOT_QmluOjI0NzAyNTM2_150"` (base64 + quantity)
- Used when ShipHero doesn't track specific lot numbers
- Often have NULL `expiration_date`
- `lot_name` typically matches `lot_id`

**Real Lots** (~8% of inventory):
- `lot_id` is numeric: `"760670"`
- Used for products with batch tracking (especially perishables)
- Always have `expiration_date` populated
- `lot_name` contains supplier's lot code (e.g., "25203")

### Regular POs vs DTC POs

**Regular Purchase Orders** (`purchase_orders` table):
- Inter-facility transfers: CK1/DISH → Newark DISH facility
- Third-party vendor shipments → ShipHero warehouses
- Lower volume: ~2,100 POs total
- Status: PENDING, IN_PROGRESS, CLOSED, CANCELED

**DTC Purchase Orders** (`dtc_purchase_orders` table):
- HDR-level ordering (87 HDR locations)
- Much higher volume: ~66,000 POs, 1.4M items
- Status: IN_PROGRESS (96%), CANCELLED, PLACED
- Different schema from regular POs

### Snapshot Frequency

- **Target**: Every 5 minutes per facility
- **Actual Average**: 5.03 minutes (very consistent)
- **Daily Volume**: ~252 snapshots per facility
- **24/7 Operation**: No maintenance windows

## Query Patterns

### Outbound Shipment Details by Order ID (Ledger)

```sql
-- Get detailed line items for a specific outbound order/transfer
SELECT
  vendor_sku as item_number,
  sku_name,
  lot_expiration_id as batch_id,
  lot_expiration_date as batch_expiration,
  ABS(change_in_on_hand) as quantity_picked,
  uom,
  -- Convert to eaches where applicable
  CASE
    WHEN uom = 'ea' THEN ABS(change_in_on_hand)
    WHEN conversion_factor > 0 THEN ABS(change_in_on_hand) / conversion_factor
    ELSE NULL
  END as quantity_in_eaches,
  datetime_et as picked_at,
  location_id as bin_location,
  previous_on_hand,
  new_on_hand,
  user_id as picker_id
FROM `wonder-dw-prod-brd.inventory.int_shiphero_ledger`
WHERE ref_order_id = 'PO-82834'  -- Replace with your order ID
  AND l1_action = 'Remove'
  AND l2_action = 'Transfer Out'
ORDER BY datetime_utc;
```

### Recent Outbound Shipments Summary (Ledger)

```sql
-- Summarize recent outbound orders from warehouses
SELECT
  ref_order_id,
  ref_order_type,
  facility_id as source_warehouse,
  COUNT(*) as num_line_items,
  COUNT(DISTINCT vendor_sku) as unique_skus,
  SUM(ABS(change_in_on_hand)) as total_quantity,
  MIN(datetime_et) as first_pick_time,
  MAX(datetime_et) as last_pick_time,
  TIMESTAMP_DIFF(MAX(datetime_utc), MIN(datetime_utc), MINUTE) as pick_duration_minutes,
  STRING_AGG(DISTINCT user_id) as picker_ids
FROM `wonder-dw-prod-brd.inventory.int_shiphero_ledger`
WHERE datetime_utc >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
  AND l1_action = 'Remove'
  AND l2_action = 'Transfer Out'
  AND consumption_bucket = 'Outbound Shipment'
GROUP BY ref_order_id, ref_order_type, facility_id
ORDER BY first_pick_time DESC;
```

### Inventory Movement Analysis by Action Type (Ledger)

```sql
-- Analyze all types of inventory movements over a time period
SELECT
  l1_action,
  l2_action,
  consumption_bucket,
  COUNT(*) as num_transactions,
  SUM(CASE WHEN change_in_on_hand < 0 THEN 1 ELSE 0 END) as outbound_count,
  SUM(CASE WHEN change_in_on_hand > 0 THEN 1 ELSE 0 END) as inbound_count,
  SUM(change_in_on_hand) as total_net_change,
  COUNT(DISTINCT ref_order_id) as unique_orders
FROM `wonder-dw-prod-brd.inventory.int_shiphero_ledger`
WHERE datetime_utc >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
GROUP BY l1_action, l2_action, consumption_bucket
ORDER BY num_transactions DESC;
```

### Latest Inventory Snapshot Across All Warehouses

```sql
-- Get most recent on-hand inventory for all SKUs at all facilities
WITH latest_snapshots AS (
  SELECT
    facility_id,
    snapshot_id,
    created_at
  FROM `wonder-sporklift-prod.sporklift.dish_inventory_snapshot_runs`
  WHERE facility_id IS NOT NULL
  QUALIFY ROW_NUMBER() OVER (PARTITION BY facility_id ORDER BY created_at DESC) = 1
)
SELECT
  n.facility_name,
  s.vendor_sku,
  SUM(s.on_hand) as total_on_hand,
  SUM(s.allocated) as total_allocated,
  SUM(s.available) as total_available,
  COUNT(DISTINCT s.lot_id) as num_lots,
  DATETIME(MAX(ls.created_at), 'America/New_York') as snapshot_time_ny
FROM `wonder-sporklift-prod.sporklift.dish_inventory_snapshot` s
JOIN latest_snapshots ls ON s.snapshot_id = ls.snapshot_id
JOIN `wonder-dw-prod-brd.command_center.nodes` n ON s.facility_id = n.facility_id
GROUP BY n.facility_name, s.vendor_sku
ORDER BY n.facility_name, total_on_hand DESC;
```

### Inventory Trends Over Time for Specific SKUs

```sql
-- Track daily inventory levels for specific vendor SKUs
SELECT
  DATE(DATETIME(r.created_at, 'America/New_York')) as date_ny,
  n.facility_name,
  s.vendor_sku,
  AVG(s.on_hand) as avg_on_hand,
  MIN(s.on_hand) as min_on_hand,
  MAX(s.on_hand) as max_on_hand,
  COUNT(*) as num_snapshots
FROM `wonder-sporklift-prod.sporklift.dish_inventory_snapshot` s
JOIN `wonder-sporklift-prod.sporklift.dish_inventory_snapshot_runs` r
  ON s.snapshot_id = r.snapshot_id
JOIN `wonder-dw-prod-brd.command_center.nodes` n
  ON s.facility_id = n.facility_id
WHERE s.vendor_sku IN ('8806886', '8806887')
  AND r.created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
GROUP BY date_ny, n.facility_name, s.vendor_sku
ORDER BY date_ny DESC, n.facility_name;
```

### Expiring Inventory Report (FEFO Analysis)

```sql
-- Find inventory expiring in next 30 days with lot details
WITH latest_snapshot AS (
  SELECT snapshot_id
  FROM `wonder-sporklift-prod.sporklift.dish_inventory_snapshot_runs`
  WHERE facility_id IS NOT NULL
  ORDER BY created_at DESC
  LIMIT 1
)
SELECT
  n.facility_name,
  s.vendor_sku,
  s.lot_name,
  s.on_hand,
  s.available,
  s.expiration_date,
  DATE_DIFF(s.expiration_date, CURRENT_DATE(), DAY) as days_until_expiry,
  CASE
    WHEN DATE_DIFF(s.expiration_date, CURRENT_DATE(), DAY) < 0 THEN 'EXPIRED'
    WHEN DATE_DIFF(s.expiration_date, CURRENT_DATE(), DAY) <= 7 THEN 'URGENT'
    WHEN DATE_DIFF(s.expiration_date, CURRENT_DATE(), DAY) <= 14 THEN 'WARNING'
    ELSE 'NORMAL'
  END as urgency
FROM `wonder-sporklift-prod.sporklift.dish_inventory_snapshot` s
JOIN latest_snapshot ls ON s.snapshot_id = ls.snapshot_id
JOIN `wonder-dw-prod-brd.command_center.nodes` n ON s.facility_id = n.facility_id
WHERE s.expiration_date IS NOT NULL
  AND s.on_hand > 0
  AND s.expiration_date <= DATE_ADD(CURRENT_DATE(), INTERVAL 30 DAY)
ORDER BY s.expiration_date, n.facility_name;
```

### Multi-Warehouse SKU Distribution

```sql
-- Find SKUs available at multiple warehouses with quantities
WITH latest_snapshots AS (
  SELECT
    facility_id,
    snapshot_id
  FROM `wonder-sporklift-prod.sporklift.dish_inventory_snapshot_runs`
  WHERE facility_id IS NOT NULL
  QUALIFY ROW_NUMBER() OVER (PARTITION BY facility_id ORDER BY created_at DESC) = 1
)
SELECT
  s.vendor_sku,
  COUNT(DISTINCT s.facility_id) as num_warehouses,
  SUM(s.on_hand) as total_on_hand,
  SUM(s.available) as total_available,
  STRING_AGG(CONCAT(n.facility_name, ': ', s.on_hand) ORDER BY n.facility_name) as distribution
FROM `wonder-sporklift-prod.sporklift.dish_inventory_snapshot` s
JOIN latest_snapshots ls ON s.snapshot_id = ls.snapshot_id AND s.facility_id = ls.facility_id
JOIN `wonder-dw-prod-brd.command_center.nodes` n ON s.facility_id = n.facility_id
WHERE s.on_hand > 0
GROUP BY s.vendor_sku
HAVING COUNT(DISTINCT s.facility_id) > 1
ORDER BY total_on_hand DESC;
```

### Open Purchase Orders by Status

```sql
-- List all open regular POs with item counts and status
SELECT
  po.order_number,
  po.status,
  supplier.facility_name as supplier_name,
  receiver.facility_name as receiver_name,
  po.expected_date,
  COUNT(DISTINCT poi.purchase_order_item_id) as num_items,
  SUM(poi.quantity) as total_quantity,
  SUM(poi.quantity_received) as total_received,
  DATETIME(TIMESTAMP(po.created_at), 'America/New_York') as created_at_ny
FROM `wonder-raw-prod.mysql_batch_sporklift.purchase_orders` po
LEFT JOIN `wonder-dw-prod-brd.command_center.nodes` supplier
  ON po.supplier_node_id = supplier.facility_id
LEFT JOIN `wonder-dw-prod-brd.command_center.nodes` receiver
  ON po.receiver_node_id = receiver.facility_id
LEFT JOIN `wonder-raw-prod.mysql_batch_sporklift.purchase_order_items` poi
  ON po.purchase_order_id = poi.purchase_order_id
WHERE UPPER(po.status) IN ('PENDING', 'IN_PROGRESS')
GROUP BY po.order_number, po.status, supplier_name, receiver_name, po.expected_date, po.created_at
ORDER BY po.expected_date, po.created_at DESC;
```

### Purchase Order Fulfillment Rate

```sql
-- Calculate fulfillment metrics for completed POs
SELECT
  po.order_number,
  po.status,
  DATETIME(TIMESTAMP(po.po_created_at), 'America/New_York') as po_created_ny,
  DATETIME(TIMESTAMP(po.updated_at), 'America/New_York') as po_updated_ny,
  COUNT(DISTINCT poi.purchase_order_item_id) as num_items,
  SUM(poi.quantity) as quantity_ordered,
  SUM(poi.quantity_received) as quantity_received,
  SUM(poi.shipped_count) as quantity_shipped,
  SUM(poi.rejected_count) as quantity_rejected,
  ROUND(SAFE_DIVIDE(SUM(poi.quantity_received), SUM(poi.quantity)) * 100, 2) as fulfillment_pct,
  ROUND(SAFE_DIVIDE(SUM(poi.rejected_count), SUM(poi.quantity)) * 100, 2) as rejection_pct
FROM `wonder-raw-prod.mysql_batch_sporklift.purchase_orders` po
JOIN `wonder-raw-prod.mysql_batch_sporklift.purchase_order_items` poi
  ON po.purchase_order_id = poi.purchase_order_id
WHERE UPPER(po.status) = 'CLOSED'
  AND TIMESTAMP(po.po_created_at) >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
GROUP BY po.order_number, po.status, po.po_created_at, po.updated_at
ORDER BY po_updated_ny DESC;
```

### DTC Purchase Orders by HDR Location

```sql
-- Analyze DTC ordering patterns by HDR location
SELECT
  dtc.hdr_id,
  n.facility_name as hdr_name,
  UPPER(dtc.status) as status,
  COUNT(DISTINCT dtc.purchase_order_id) as num_orders,
  COUNT(DISTINCT dtci.purchase_order_item_id) as num_items,
  SUM(dtci.quantity) as total_quantity,
  MIN(DATETIME(TIMESTAMP(dtc.created_at), 'America/New_York')) as first_order_ny,
  MAX(DATETIME(TIMESTAMP(dtc.created_at), 'America/New_York')) as last_order_ny
FROM `wonder-raw-prod.mysql_batch_sporklift.dtc_purchase_orders` dtc
LEFT JOIN `wonder-dw-prod-brd.command_center.nodes` n
  ON dtc.hdr_id = n.facility_id
LEFT JOIN `wonder-raw-prod.mysql_batch_sporklift.dtc_purchase_order_items` dtci
  ON dtc.purchase_order_id = dtci.purchase_order_id
WHERE TIMESTAMP(dtc.created_at) >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
GROUP BY dtc.hdr_id, hdr_name, status
ORDER BY num_orders DESC;
```

### Purchase Order Audit Trail

```sql
-- Track status changes and modifications for a specific PO
SELECT
  audit.purchase_order_id,
  audit.operation,
  audit.status as new_status,
  audit.order_number,
  DATETIME(audit.created_at, 'America/New_York') as changed_at_ny,
  audit.updated_by
FROM `wonder-raw-prod.mysql_batch_sporklift.purchase_orders_audit` audit
WHERE audit.order_number = '251117DISH-SHIP00001'
ORDER BY audit.created_at DESC;
```

### Combined On-Hand + On-Order Analysis

```sql
-- Join inventory snapshots with open POs to show total available + incoming
WITH latest_snapshots AS (
  SELECT
    facility_id,
    snapshot_id
  FROM `wonder-sporklift-prod.sporklift.dish_inventory_snapshot_runs`
  WHERE facility_id IS NOT NULL
  QUALIFY ROW_NUMBER() OVER (PARTITION BY facility_id ORDER BY created_at DESC) = 1
),
on_hand AS (
  SELECT
    s.facility_id,
    s.vendor_sku,
    SUM(s.on_hand) as current_on_hand,
    SUM(s.available) as current_available
  FROM `wonder-sporklift-prod.sporklift.dish_inventory_snapshot` s
  JOIN latest_snapshots ls ON s.snapshot_id = ls.snapshot_id
  GROUP BY s.facility_id, s.vendor_sku
),
on_order AS (
  SELECT
    po.receiver_node_id as facility_id,
    poi.vendor_sku,
    SUM(poi.quantity - COALESCE(poi.quantity_received, 0)) as quantity_on_order
  FROM `wonder-raw-prod.mysql_batch_sporklift.purchase_orders` po
  JOIN `wonder-raw-prod.mysql_batch_sporklift.purchase_order_items` poi
    ON po.purchase_order_id = poi.purchase_order_id
  WHERE UPPER(po.status) IN ('PENDING', 'IN_PROGRESS')
  GROUP BY facility_id, poi.vendor_sku
)
SELECT
  n.facility_name,
  COALESCE(oh.vendor_sku, oo.vendor_sku) as vendor_sku,
  COALESCE(oh.current_on_hand, 0) as on_hand,
  COALESCE(oh.current_available, 0) as available,
  COALESCE(oo.quantity_on_order, 0) as on_order,
  COALESCE(oh.current_available, 0) + COALESCE(oo.quantity_on_order, 0) as total_future_available
FROM on_hand oh
FULL OUTER JOIN on_order oo
  ON oh.facility_id = oo.facility_id AND oh.vendor_sku = oo.vendor_sku
JOIN `wonder-dw-prod-brd.command_center.nodes` n
  ON COALESCE(oh.facility_id, oo.facility_id) = n.facility_id
WHERE COALESCE(oh.current_on_hand, 0) + COALESCE(oo.quantity_on_order, 0) > 0
ORDER BY n.facility_name, vendor_sku;
```

### Supply Chain Integration - Vendor SKU Mapping

```sql
-- Join Sporklift inventory to Supply Chain purchase orders
WITH latest_snapshot AS (
  SELECT snapshot_id
  FROM `wonder-sporklift-prod.sporklift.dish_inventory_snapshot_runs`
  WHERE facility_id IS NOT NULL
  ORDER BY created_at DESC
  LIMIT 1
)
SELECT
  sp.vendor_sku,
  SUM(sp.on_hand) as sporklift_on_hand,
  poms_poi.wonder_sku,
  poms_po.supplier_name,
  COUNT(DISTINCT poms_po.purchase_order_id) as num_poms_orders
FROM `wonder-sporklift-prod.sporklift.dish_inventory_snapshot` sp
JOIN latest_snapshot ls ON sp.snapshot_id = ls.snapshot_id
LEFT JOIN `wonder-raw-prod.pg_batch_supplychain.purchase_order_items` poms_poi
  ON sp.vendor_sku = poms_poi.supplier_sku
LEFT JOIN `wonder-raw-prod.pg_batch_supplychain.purchase_orders` poms_po
  ON poms_poi.purchase_order_id = poms_po.id
WHERE sp.on_hand > 0
GROUP BY sp.vendor_sku, poms_poi.wonder_sku, poms_po.supplier_name
ORDER BY sporklift_on_hand DESC;
```

## Best Practices

1. **Always Use Fully Qualified Table Names** - Use backticks and full project.dataset.table format to avoid ambiguity

2. **Filter NULL Facilities in Snapshots** - Add `WHERE facility_id IS NOT NULL` when querying snapshot data to exclude early system testing records

3. **Convert Timestamps to Eastern Time** - Wonder operates in America/New_York timezone, always use `DATETIME(timestamp_field, 'America/New_York')`

4. **Distinguish Regular vs DTC POs** - Use `purchase_orders` table for inter-facility/vendor POs and `dtc_purchase_orders` for HDR-level orders (different schemas)

5. **Use Window Functions for Latest Snapshots** - Get the most recent snapshot per facility using `ROW_NUMBER() OVER (PARTITION BY facility_id ORDER BY created_at DESC) = 1`

6. **Join to Command Center Nodes** - Always join `facility_id` to `command_center.nodes` for human-readable facility names and addresses

7. **Understand Virtual Lot Conventions** - "NO_LOT" prefix indicates virtual lots without specific lot tracking (not missing data)

8. **Case-Insensitive Status Checks** - Status values are inconsistent (CLOSED vs closed), use `UPPER(status)` for comparisons

9. **Filter by Date Range for Performance** - With 216M+ snapshot records, always limit queries by time period using `created_at >= TIMESTAMP_SUB(...)`

10. **Use Audit Tables for Change History** - Query `purchase_orders_audit` and `dtc_purchase_orders_audit` tables to track PO modifications over time

## Supporting Documentation

- [schema-reference.md](schema-reference.md) - Complete table schemas, field descriptions, and relationships
- [common-pitfalls.md](common-pitfalls.md) - Common mistakes and how to avoid them

## Data Lineage

The BigQuery tables used in this skill are built by data pipelines in the `data` folder.

### Key dbt Models

| BigQuery Table | dbt Model | Source |
|----------------|-----------|--------|
| `wonder-dw-prod-brd.inventory.int_shiphero_ledger` | `int_shiphero_ledger.sql` | ShipHero `location_change_log` + corrections |
| `wonder-dw-prod-brd.inventory.consolidated_inventory_ledger` | `consolidated_inventory_ledger.sql` | Union of Pantry, OrderGrid, ShipHero ledgers |

### Pipeline Location

```
data/data_inventory/dbt_inventory_bq/
├── models/
│   ├── inventory_ledger/
│   │   ├── consolidated_inventory_ledger.sql    # Main unified ledger
│   │   ├── consolidated_inventory_ledger.yml    # Schema/tests
│   │   └── intermediate/
│   │       ├── int_shiphero_ledger.sql          # ⭐ Key model for Sporklift
│   │       ├── int_pantry_ledger.sql            # Pantry transactions
│   │       ├── int_og_ledger.sql                # OrderGrid transactions
│   │       ├── int_vendor_uom_conversions.sql   # UOM mapping
│   │       └── int_shiphero_waste_corrections.sql
│   ├── inventory/                               # 47 inventory models
│   │   ├── dish_inventory_history.sql
│   │   ├── hdr_inventory_history.sql
│   │   └── ...
│   └── purchase_orders/
│       ├── purchase_order_details.sql
│       └── staging/
└── inventory.yml                                # Source definitions
```

### How `int_shiphero_ledger` Works

The `int_shiphero_ledger` model transforms raw ShipHero data into the standardized inventory ledger:

1. **Sources**:
   - `shiphero.location_change_log` - Raw inventory change events from ShipHero API
   - `mysql_batch_sporklift.purchase_orders` - PO data for order type classification
   - `recipe_prod_v2.item_versions` - Item metadata and costs
   - Various correction/exclusion seed tables

2. **Key Transformations**:
   - Maps `reason` text to standardized `l1_action` (Add/Remove/Adjust/Move) and `l2_action` (Transfer Out, PO Receipt, etc.)
   - Converts vendor SKUs to Wonder SKUs via `vendor_sku_mappings`
   - Applies UOM conversions using `int_vendor_uom_conversions`
   - Extracts `ref_order_id` from HTML-formatted reason strings
   - Classifies `consumption_bucket` (Outbound Shipment, Waste, Production, etc.)

3. **Warehouse Initialization Dates** (hardcoded in model):
   - Millington: `2025-08-11 17:40:20`
   - DISH: `2025-09-03 11:18:43`
   - Arcadia: `2025-10-28 00:00:00`

### Raw Source Tables

The skill queries these raw tables directly (not dbt-transformed):

| Table | Source System | Notes |
|-------|---------------|-------|
| `wonder-sporklift-prod.sporklift.dish_inventory_snapshot` | ShipHero API | 5-min snapshots, 216M+ rows |
| `wonder-sporklift-prod.sporklift.dish_inventory_snapshot_runs` | ShipHero API | Snapshot metadata |
| `wonder-raw-prod.mysql_batch_sporklift.purchase_orders` | MySQL batch sync | Regular POs |
| `wonder-raw-prod.mysql_batch_sporklift.purchase_order_items` | MySQL batch sync | PO line items |
| `wonder-raw-prod.mysql_batch_sporklift.dtc_purchase_orders` | MySQL batch sync | DTC/HDR POs |
| `wonder-raw-prod.mysql_batch_sporklift.dtc_purchase_order_items` | MySQL batch sync | DTC line items |
| `wonder-raw-prod.mysql_batch_sporklift.purchase_orders_audit` | MySQL batch sync | PO change history |

### Related dbt Sources (from `inventory.yml`)

```yaml
sources:
  - name: shiphero
    tables:
      - location_change_log        # Raw ledger events

  - name: mysql_batch_sporklift
    tables:
      - purchase_orders
      - purchase_order_items

  - name: recipe_prod_v2
    tables:
      - item_versions              # SKU metadata, costs, UOM
```

### When to Check dbt Code

Look at the dbt models when:
- **Derived columns don't match expectations** - Check transformation logic in `int_shiphero_ledger.sql`
- **UOM conversions seem wrong** - Review `int_vendor_uom_conversions.sql`
- **Action classifications are unexpected** - The `l1_action`/`l2_action` CASE statements are extensive
- **Missing data after certain dates** - Check warehouse initialization date filters
- **Need to understand consumption buckets** - See `shiphero_consumption_mapping` seed
