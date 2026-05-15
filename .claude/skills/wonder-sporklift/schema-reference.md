# Wonder Sporklift - Schema Reference

## Overview

Sporklift is Wonder's warehouse management integration system built on top of ShipHero WMS. It tracks real-time inventory at three 3PL facilities and manages purchase order fulfillment. The system consists of three primary BigQuery datasets: a transaction-level inventory ledger, point-in-time inventory snapshots, and operational purchase order data.

## Database Connections

**Inventory Ledger (Processed)**:
- **BigQuery Dataset**: `wonder-dw-prod-brd.inventory`
- **Table**: `int_shiphero_ledger`
- **Access**: Via bq CLI or BigQuery Console
- **Purpose**: Complete transaction log of inventory movements (outbound shipments, inbound receipts, production, waste, adjustments)
- **Best Use**: Track specific order shipments, batch/lot movements, picker activity, and inventory consumption patterns

**Inventory Snapshots**:
- **BigQuery Dataset**: `wonder-sporklift-prod.sporklift`
- **Access**: Via bq CLI or BigQuery Console
- **Purpose**: Processed snapshot data from ShipHero API (captured every ~5 minutes)
- **Best Use**: Current on-hand quantities, availability trends, and point-in-time analysis

**Purchase Orders (Operational)**:
- **BigQuery Dataset**: `wonder-raw-prod.mysql_batch_sporklift`
- **Access**: Via bq CLI or BigQuery Console
- **Purpose**: MySQL batch replication from Sporklift service database
- **Replication**: Synced continuously via `_sync_time` field
- **Best Use**: PO status tracking, expected delivery dates, and order metadata

---

## Inventory Ledger Table

### int_shiphero_ledger

**Purpose**: Event-sourced transaction log tracking every inventory movement at ShipHero warehouses. This is the primary table for understanding what inventory moved, when, where, why, and by whom.

**Data Volume**: 1.2M+ transactions (Aug 2025 - Present)

**Schema**:
```sql
id                       STRING       -- Unique transaction ID (hash)
record_id                STRING       -- ShipHero record identifier
system_of_origin         STRING       -- Source system (typically "Shiphero")
origin_record_id         STRING       -- Original record ID from source system
datetime_utc             TIMESTAMP    -- Transaction timestamp (UTC)
datetime_et              DATETIME     -- Transaction timestamp (Eastern Time)
facility_id              STRING       -- Source/destination warehouse (DISH, Millington, Arcadia)
facility_type            STRING       -- Warehouse type designation
location_id              STRING       -- Warehouse bin/location ID where item was picked/placed
location_quality         STRING       -- Location classification (typically "Quality")
consumable_sku           STRING       -- Wonder's consumable SKU identifier
wonder_sku               STRING       -- Wonder's internal SKU identifier
vendor_sku               STRING       -- Vendor/supplier SKU code (joins to other systems)
sku_name                 STRING       -- Human-readable product name
l1_action                STRING       -- Level 1 action: Remove, Add, Move, Adjust, Correction, tbd
l2_action                STRING       -- Level 2 action: Transfer Out, Transfer In, PO Receipt, etc.
raw_action               STRING       -- Raw ShipHero action description with HTML links
consumption_bucket       STRING       -- Business classification: Outbound Shipment, Receive, Production, Shrinkage, etc.
conversion_factor        FLOAT        -- Units per package (e.g., 681g package = 681.0)
change_in_on_hand        FLOAT        -- Quantity change (negative = removed, positive = added)
uom                      STRING       -- Unit of measure: ea, g, kg, lb
previous_on_hand_raw     INTEGER      -- Raw on-hand before transaction
previous_on_hand         FLOAT        -- Converted on-hand before transaction
new_on_hand              FLOAT        -- On-hand after transaction
ref_order_id             STRING       -- Reference order ID (PO-#####, DISH_DTC###, "PO #####")
ref_order_type           STRING       -- Order type: Transfer Order, Purchase Order
correction_ref_id        STRING       -- Reference ID for correction transactions
lot_expiration_id        STRING       -- Lot/batch identifier (unique per lot)
lot_expiration_date      DATE         -- Product expiration date for this lot
user_id                  STRING       -- ShipHero user ID (picker/receiver)
accounting_posted_date   DATE         -- Accounting posting date (often NULL)
inventory_uom            STRING       -- Inventory unit of measure
bom_line_unit            STRING       -- Bill of materials line unit
inventory_bom_factor     FLOAT        -- BOM conversion factor
purchased_pack_code      STRING       -- Purchase package code
purchased_pack_size      INTEGER      -- Purchase package size
each_pack_size           INTEGER      -- Each package size
inventory_pack_code      STRING       -- Inventory package code
inventory_pack_size      INTEGER      -- Inventory package size
vendor_inventory_factor  FLOAT        -- Vendor-specific inventory factor
manual_field_entry       BOOLEAN      -- Whether entry was manual (typically false)
price                    NUMERIC      -- Item cost/price
```

**Key Fields**:

- **Action Classification** (use these to filter transaction types):
  - **Outbound Shipments**: `l1_action = 'Remove'`, `l2_action = 'Transfer Out'`, `consumption_bucket = 'Outbound Shipment'`
  - **Inbound Receipts**: `l1_action = 'Add'`, `l2_action IN ('Transfer In', 'PO Receipt')`, `consumption_bucket = 'Receive'`
  - **Production Consumption**: `l1_action = 'Remove'`, `l2_action = 'Consume for Production'`, `consumption_bucket = 'Production'`
  - **Waste**: `consumption_bucket IN ('Shrinkage', 'Expiry Waste', 'Operational Issues', 'Purge Waste')`
  - **Adjustments**: `l1_action IN ('Adjust', 'Correction')`, `l2_action IN ('Cycle Count', 'Lost', 'Damage', 'Found', 'Correct Input Error')`

- **`ref_order_id` Formats**:
  - **`PO-#####`**: Outbound transfer orders (e.g., PO-82834) - overnight/early morning shipments
  - **`DISH_DTC###`**: DTC outbound orders (e.g., DISH_DTC458) - morning shipments
  - **`PO #####`** (with space): Inbound purchase order receipts (e.g., "PO 50911")

- **`vendor_sku`**: Primary join key to inventory snapshots and supply chain tables

- **`lot_expiration_id` & `lot_expiration_date`**: Track specific batch/lot movements with expiration dates

- **`change_in_on_hand`**:
  - Negative values = inventory removed (outbound, consumption, waste)
  - Positive values = inventory added (inbound, production output, found items)
  - Use `ABS()` when calculating quantities shipped/received

- **`conversion_factor`**: Used to convert weight-based UOM to package count
  - Example: 681g cheese package → conversion_factor = 681.0
  - To get eaches: `ABS(change_in_on_hand) / conversion_factor`

- **`location_id`**: Warehouse bin location (numeric IDs like 23161014)

- **`user_id`**: ShipHero user who performed the transaction (e.g., 588722 for picker "Lina M.")

**Common Query Patterns**:
```sql
-- Get all items picked for a specific outbound order
WHERE ref_order_id = 'PO-82834'
  AND l1_action = 'Remove'
  AND l2_action = 'Transfer Out'

-- Get all outbound shipments in last 24 hours
WHERE datetime_utc >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
  AND consumption_bucket = 'Outbound Shipment'

-- Get all waste/shrinkage transactions
WHERE consumption_bucket IN ('Shrinkage', 'Expiry Waste', 'Operational Issues', 'Purge Waste')

-- Convert to eaches for outbound items
CASE
  WHEN uom = 'ea' THEN ABS(change_in_on_hand)
  WHEN conversion_factor > 0 THEN ABS(change_in_on_hand) / conversion_factor
  ELSE NULL
END as quantity_in_eaches
```

**Join Patterns**:
```sql
-- To get facility names
int_shiphero_ledger.facility_id = command_center.nodes.facility_id

-- To join with inventory snapshots (by SKU, not by lot)
int_shiphero_ledger.vendor_sku = dish_inventory_snapshot.vendor_sku

-- To join with supply chain
int_shiphero_ledger.vendor_sku = pg_batch_supplychain.purchase_order_items.supplier_sku
```

**Usage Notes**:
- Always use `datetime_utc` for time-based filtering (better performance, partitioned)
- Use `datetime_et` for display purposes
- Filter on `l1_action`, `l2_action`, and `consumption_bucket` together for best results
- The ledger contains ALL inventory movements - be specific with filters to avoid massive result sets

---

## Inventory Snapshot Tables

### dish_inventory_snapshot

**Purpose**: Stores detailed lot-level inventory positions from ShipHero for all SKUs at all facilities, captured approximately every 5 minutes.

**Data Volume**: 216M+ records (Aug 2025 - Present)

**Schema**:
```sql
lot_id               STRING       -- Unique lot identifier (virtual or real)
vendor_sku           STRING       -- Vendor's SKU code, maps to supplier_sku in Supply Chain
on_hand              INTEGER      -- Total physical units in warehouse
allocated            INTEGER      -- Units reserved for orders (rarely used)
available            INTEGER      -- Units available for new orders (on_hand - allocated)
snapshot_id          STRING       -- Foreign key to dish_inventory_snapshot_runs
facility_id          STRING       -- UUID reference to warehouse (joins to command_center.nodes)
created_at           DATETIME     -- Record creation timestamp (UTC, convert to America/New_York)
updated_at           DATETIME     -- Record update timestamp (UTC)
expiration_date      DATE         -- Product expiration date (NULL for ~13% of records)
lot_name             STRING       -- Human-readable lot identifier
synced_at            DATETIME     -- Intended for sync tracking (NULL for all records - unused)
```

**Key Fields**:

- **`lot_id`**: Two formats depending on lot tracking:
  - **Virtual Lots** (majority): `"NO_LOT_QmluOjI0NzAyNTM2_150"` - Base64-encoded identifier + quantity suffix
  - **Real Lots** (minority): `"760670"` - Numeric lot ID from ShipHero

- **`vendor_sku`**: The supplier's SKU code. This is the key field for joining to Supply Chain's `supplier_sku` in `purchase_order_items`

- **`on_hand`** vs **`available`**:
  - `on_hand` = total physical inventory
  - `allocated` = reserved for orders (usually 0)
  - `available` = on_hand - allocated (what can be used for new orders)

- **`facility_id`**: UUID reference to ShipHero warehouse. Always join to `command_center.nodes` for facility names:
  - DISH: `46d337b4-7f61-4338-979a-5ee8d8e0071f`
  - Millington: `de117c76-d46f-4cf3-943e-37513b32be47`
  - Arcadia: `070f0993-93d0-4518-bc58-b957130b3b81`

- **`expiration_date`**: Only populated for ~8% of lots (real lots with perishable tracking). NULL for virtual lots.

**Common Values**:
- `allocated`: 0 for 99.9% of records (allocations handled externally)
- `synced_at`: NULL for 100% of records (field not currently used)

**Usage**:
```sql
-- Get latest inventory for a specific SKU at all facilities
WITH latest_snapshots AS (
  SELECT
    facility_id,
    snapshot_id
  FROM `wonder-sporklift-prod.sporklift.dish_inventory_snapshot_runs`
  WHERE facility_id IS NOT NULL
  QUALIFY ROW_NUMBER() OVER (PARTITION BY facility_id ORDER BY created_at DESC) = 1
)
SELECT
  n.facility_name,
  s.vendor_sku,
  SUM(s.on_hand) as total_on_hand,
  SUM(s.available) as total_available,
  COUNT(DISTINCT s.lot_id) as num_lots
FROM `wonder-sporklift-prod.sporklift.dish_inventory_snapshot` s
JOIN latest_snapshots ls ON s.snapshot_id = ls.snapshot_id
JOIN `wonder-dw-prod-brd.command_center.nodes` n ON s.facility_id = n.facility_id
WHERE s.vendor_sku = '8806886'
GROUP BY n.facility_name, s.vendor_sku;
```

**Join Patterns**:
```sql
-- To get facility names
dish_inventory_snapshot.facility_id = command_center.nodes.facility_id

-- To get snapshot metadata
dish_inventory_snapshot.snapshot_id = dish_inventory_snapshot_runs.snapshot_id

-- To join with Supply Chain
dish_inventory_snapshot.vendor_sku = pg_batch_supplychain.purchase_order_items.supplier_sku
```

---

### dish_inventory_snapshot_runs

**Purpose**: Metadata table tracking each snapshot execution, including timing and ShipHero API URLs.

**Data Volume**: 59,331 snapshot runs (Aug 2025 - Present)

**Schema**:
```sql
snapshot_id          STRING       -- Primary key, unique identifier for snapshot run
created_at           TIMESTAMP    -- When snapshot was captured (UTC timezone)
facility_id          STRING       -- UUID of warehouse (NULL for early system testing)
snapshot_url         STRING       -- CloudFront URL to raw JSON snapshot from ShipHero API
```

**Key Fields**:

- **`snapshot_id`**: Use this to filter `dish_inventory_snapshot` to a specific point-in-time view

- **`created_at`**: Stored in UTC. Always convert to Eastern Time:
  ```sql
  DATETIME(created_at, 'America/New_York') as snapshot_time_ny
  ```

- **`snapshot_url`**: Points to raw ShipHero API response stored on CloudFront:
  ```
  https://d2lvvgmvu4c2gi.cloudfront.net/inventory_snapshots/87255/{facility_code}/Any/{uuid}.json
  ```
  - Facility codes: 127552 (Arcadia), 126631 (Millington), 121521 (DISH)
  - "87255" is Wonder's ShipHero account/tenant ID
  - Useful for debugging or accessing raw API data

- **`facility_id`**: NULL for 3,276 early snapshot runs (Aug 1-13, 2025) - these are system testing records with no corresponding inventory data

**Common Values**:
- Snapshot frequency: Every ~5.03 minutes per facility (target: 5 minutes)
- Daily snapshots per facility: ~252 (target: 288)
- Coverage: 24/7 with no maintenance windows

**Usage**:
```sql
-- Get the most recent snapshot for each facility
SELECT
  n.facility_name,
  r.snapshot_id,
  DATETIME(r.created_at, 'America/New_York') as snapshot_time_ny,
  TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), r.created_at, MINUTE) as minutes_old,
  r.snapshot_url
FROM `wonder-sporklift-prod.sporklift.dish_inventory_snapshot_runs` r
JOIN `wonder-dw-prod-brd.command_center.nodes` n ON r.facility_id = n.facility_id
WHERE r.facility_id IS NOT NULL
QUALIFY ROW_NUMBER() OVER (PARTITION BY r.facility_id ORDER BY r.created_at DESC) = 1
ORDER BY snapshot_time_ny DESC;
```

**Join Patterns**:
```sql
-- One-to-many with inventory snapshot records
dish_inventory_snapshot_runs.snapshot_id = dish_inventory_snapshot.snapshot_id

-- To get facility details
dish_inventory_snapshot_runs.facility_id = command_center.nodes.facility_id
```

---

## Purchase Order Tables (Regular POs)

### purchase_orders

**Purpose**: Tracks shipments between Wonder facilities and third-party vendors to ShipHero warehouses. Two main types: CK1/DISH → Newark transfers and Third Party Vendor → ShipHero shipments.

**Data Volume**: 2,109 purchase orders (Aug 21, 2025 - Present)

**Schema**:
```sql
order_number             STRING       -- Human-readable PO number (e.g., "251117DISH-SHIP00001")
purchase_order_id        STRING       -- Primary key (non-UUID string)
purchase_order_uuid      STRING       -- UUID representation of PO
warehouse_id             STRING       -- ShipHero warehouse identifier
status                   STRING       -- PENDING, IN_PROGRESS, CLOSED, CANCELED
supplier_node_id         STRING       -- UUID of supplier facility (joins to nodes)
receiver_node_id         STRING       -- UUID of receiver facility (joins to nodes)
shipment_reference_id    STRING       -- Links to shipment tracking system
expected_date            DATETIME     -- Expected delivery date (UTC)
po_created_at            DATETIME     -- Original PO creation timestamp (UTC)
created_at               DATETIME     -- Record creation timestamp (UTC)
updated_at               DATETIME     -- Record update timestamp (UTC)
created_by               STRING       -- Service name that created record
updated_by               STRING       -- Service name that updated record
_sync_time               DATETIME     -- MySQL replication sync timestamp
```

**Key Fields**:

- **`order_number`**: Primary business identifier. Two formats:
  - CK1/DISH shipments: `"251117DISH-SHIP00001"` (date prefix + facility + sequence)
  - Third party: `"PO-6224"` (simple sequential)

- **`status`**: Four possible values (case inconsistent - use `UPPER()` for comparisons):
  - `PENDING`: PO created but not yet in transit
  - `IN_PROGRESS`: Shipment in transit or being received
  - `CLOSED`: Fully received and completed
  - `CANCELED`: Cancelled before completion

- **`supplier_node_id`** and **`receiver_node_id`**: Two different patterns depending on order type:
  - **Inter-facility transfers** (CK1/DISH → Newark):
    - `supplier_node_id` = facility UUID (e.g., `c4de0fa3-1058-4671-897d-de271efb5a0a`)
    - `receiver_node_id` = facility UUID (e.g., `46d337b4-7f61-4338-979a-5ee8d8e0071f`)
    - Both can be joined to `command_center.nodes.facility_id`
  - **Third-party vendor orders** (External vendor → ShipHero warehouse):
    - `supplier_node_id` = literal string "Third Party Vendor"
    - `receiver_node_id` = **base64-encoded vendor name** (e.g., "VmVuZG9yOjEwNjgxNjk=" decodes to "Vendor:1068169")
    - `warehouse_id` = ShipHero warehouse numeric ID (e.g., "126631" for Millington)
    - To decode vendor: `SAFE_CAST(FROM_BASE64(receiver_node_id) AS STRING)` → "Vendor:1068169"
    - To join warehouse_id to facilities, use ShipHero ID extraction:
      ```sql
      REGEXP_EXTRACT(
        SAFE_CAST(FROM_BASE64(nodes.shiphero_facility_id) AS STRING),
        r'Warehouse:(\d+)'
      ) = purchase_orders.warehouse_id
      ```

- **`created_by`** / **`updated_by`**: Service names like `"sporklift-po-consumer-service"`, useful for debugging

**Common Values**:
- 769 POs: CK1/DISH → Newark
- 1,340 POs: Third Party Vendor → ShipHero

**Usage**:
```sql
-- List open POs with supplier/receiver names
SELECT
  po.order_number,
  po.status,
  supplier.facility_name as supplier,
  receiver.facility_name as receiver,
  DATETIME(TIMESTAMP(po.expected_date), 'America/New_York') as expected_date_ny,
  DATETIME(TIMESTAMP(po.po_created_at), 'America/New_York') as created_ny
FROM `wonder-raw-prod.mysql_batch_sporklift.purchase_orders` po
LEFT JOIN `wonder-dw-prod-brd.command_center.nodes` supplier
  ON po.supplier_node_id = supplier.facility_id
LEFT JOIN `wonder-dw-prod-brd.command_center.nodes` receiver
  ON po.receiver_node_id = receiver.facility_id
WHERE UPPER(po.status) IN ('PENDING', 'IN_PROGRESS')
ORDER BY po.expected_date;
```

**Join Patterns**:
```sql
-- One-to-many with purchase order items
purchase_orders.purchase_order_id = purchase_order_items.purchase_order_id

-- To get supplier/receiver facility names
purchase_orders.supplier_node_id = command_center.nodes.facility_id
purchase_orders.receiver_node_id = command_center.nodes.facility_id

-- To audit trail
purchase_orders.purchase_order_id = purchase_orders_audit.purchase_order_id
```

---

### purchase_order_items

**Purpose**: Line items for regular purchase orders with SKU-level quantity tracking, lot/batch information, and ShipHero references.

**Data Volume**: 30,462 line items across 2,109 POs

**Schema**:
```sql
purchase_order_item_id           STRING       -- Primary key
purchase_order_id                STRING       -- Foreign key to purchase_orders
sku                              STRING       -- SKU code for this line item
quantity                         INTEGER      -- Quantity ordered
quantity_received                INTEGER      -- Quantity actually received
shipped_count                    INTEGER      -- Quantity shipped
rejected_count                   INTEGER      -- Quantity rejected during receiving
shipment_item_id                 STRING       -- Shipment tracking reference
shipment_id                      STRING       -- Shipment tracking ID
shipment_reference_id            STRING       -- Shipment reference (also in parent PO)
batch_id                         STRING       -- Batch/lot identifier
expiration_date                  DATE         -- Product expiration date
status                           STRING       -- Item-level status
shiphero_order_line_item_id      STRING       -- ShipHero line item ID (numeric string)
shiphero_order_line_item_uuid    STRING       -- ShipHero line item UUID
vendor_id                        STRING       -- ShipHero vendor ID (numeric string)
vendor_uuid                      STRING       -- ShipHero vendor UUID
vendor_account_number            STRING       -- Vendor's account number
vendor_sku                       STRING       -- Vendor's SKU code (maps to inventory snapshots)
po_created_at                    DATETIME     -- Parent PO creation time
created_at                       DATETIME     -- Item creation timestamp
updated_at                       DATETIME     -- Item update timestamp
created_by                       STRING       -- Service name that created record
updated_by                       STRING       -- Service name that updated record
error_message                    STRING       -- Error details if item had issues
_sync_time                       DATETIME     -- MySQL replication sync timestamp
```

**Key Fields**:

- **`sku`** vs **`vendor_sku`** - CRITICAL DISTINCTION:
  - **`sku`**: Wonder's internal SKU code **with case pack information** (e.g., "5181546-24", "5181546-24pk")
    - Format includes base SKU + case pack size: `{base_sku}-{pack_size}` or `{base_sku}-{pack_size}pk`
    - Example: "5181546-24" = Coca-Cola 12oz cans in cases of 24
    - This is the field to search when looking for specific products in purchase orders
  - **`vendor_sku`**: Supplier's catalog SKU code (e.g., "3554565")
    - This is the vendor's own product identifier, NOT Wonder's SKU
    - Use this to join with inventory snapshots (`dish_inventory_snapshot.vendor_sku`)
  - **SEARCH PATTERN**: To find items in purchase orders, search **`sku` column** (e.g., `WHERE sku LIKE '5181546%'`), not `vendor_sku`

- **Quantity Tracking**:
  - `quantity`: Amount ordered
  - `quantity_received`: Amount actually received (may differ due to shortages/overages)
  - `shipped_count`: Amount shipped by supplier
  - `rejected_count`: Amount rejected during QC
  - Formula: `quantity_received = shipped_count - rejected_count` (approximately)

- **ShipHero References**:
  - `shiphero_order_line_item_id` / `shiphero_order_line_item_uuid`: Line item in ShipHero WMS
  - `vendor_id` / `vendor_uuid`: Vendor/supplier in ShipHero system
  - Useful for reconciliation with ShipHero API

- **`error_message`**: Populated when item has issues (e.g., receiving errors, validation failures)

**Usage**:
```sql
-- CORRECT: Search for Coca-Cola orders using the sku column (with case pack info)
SELECT
  po.order_number,
  poi.sku,            -- Wonder's SKU with case pack: "5181546-24"
  poi.vendor_sku,     -- Vendor's catalog SKU: "3554565"
  poi.quantity as cases_ordered,
  poi.quantity_received as cases_received,
  DATETIME(TIMESTAMP(po.po_created_at), 'America/New_York') as created_ny
FROM `wonder-raw-prod.mysql_batch_sporklift.purchase_orders` po
JOIN `wonder-raw-prod.mysql_batch_sporklift.purchase_order_items` poi
  ON po.purchase_order_id = poi.purchase_order_id
WHERE poi.sku LIKE '5181546%'  -- Search Wonder's SKU, not vendor_sku
  AND po.warehouse_id = '126631'
ORDER BY po.po_created_at DESC
LIMIT 10;

-- Calculate fulfillment rate for a specific PO
SELECT
  po.order_number,
  poi.sku,
  poi.vendor_sku,
  poi.quantity as ordered,
  poi.quantity_received as received,
  poi.rejected_count as rejected,
  ROUND(SAFE_DIVIDE(poi.quantity_received, poi.quantity) * 100, 2) as fulfillment_pct,
  poi.expiration_date,
  poi.error_message
FROM `wonder-raw-prod.mysql_batch_sporklift.purchase_orders` po
JOIN `wonder-raw-prod.mysql_batch_sporklift.purchase_order_items` poi
  ON po.purchase_order_id = poi.purchase_order_id
WHERE po.order_number = '251117DISH-SHIP00001';
```

**Join Patterns**:
```sql
-- Many-to-one with purchase orders
purchase_order_items.purchase_order_id = purchase_orders.purchase_order_id

-- To join with inventory snapshots
purchase_order_items.vendor_sku = dish_inventory_snapshot.vendor_sku

-- To Supply Chain system
purchase_order_items.vendor_sku = pg_batch_supplychain.purchase_order_items.supplier_sku
```

---

## DTC Purchase Order Tables

### dtc_purchase_orders

**Purpose**: Direct-to-Consumer purchase orders placed at HDR (restaurant) locations. Much higher volume than regular POs, representing HDR-level inventory ordering.

**Data Volume**: 66,452 purchase orders, 1.4M line items (Jul 30, 2025 - Present)

**Schema**:
```sql
purchase_order_id    STRING       -- Primary key (UUID format)
status               STRING       -- IN_PROGRESS, CANCELLED, PLACED
shipment_id          STRING       -- Shipment tracking identifier
hdr_id               STRING       -- HDR location UUID or "DISH" string
order_number         STRING       -- Sequential order number (e.g., "PO-386")
supplier_id          STRING       -- Supplier identifier
order_name           STRING       -- Human-readable order name
created_at           DATETIME     -- Order creation timestamp (UTC)
updated_at           DATETIME     -- Order update timestamp (UTC)
_sync_time           DATETIME     -- MySQL replication sync timestamp
```

**Key Fields**:

- **`purchase_order_id`**: UUID format (different from regular POs which use non-UUID strings)

- **`status`**: Three possible values:
  - `IN_PROGRESS`: 96% of all DTC POs (active/open orders)
  - `CANCELLED`: Order cancelled before completion
  - `PLACED`: Order successfully placed with supplier

- **`hdr_id`**: References HDR location (87 distinct locations):
  - Usually UUID format
  - Special case: String `"DISH"` for DISH facility orders
  - Join to `command_center.nodes` where `node_type = 'HDR'`

- **`order_number`**: Simple sequential format `"PO-{number}"` (e.g., "PO-386", "PO-12345")

**Common Values**:
- 96% of orders have status `IN_PROGRESS`
- 87 distinct HDR locations + "DISH"
- Average 21 line items per DTC PO

**Usage**:
```sql
-- DTC order volume by HDR location over last 7 days
SELECT
  dtc.hdr_id,
  n.facility_name as hdr_name,
  UPPER(dtc.status) as status,
  COUNT(DISTINCT dtc.purchase_order_id) as num_orders,
  COUNT(DISTINCT dtci.purchase_order_item_id) as num_items,
  SUM(dtci.quantity) as total_quantity
FROM `wonder-raw-prod.mysql_batch_sporklift.dtc_purchase_orders` dtc
LEFT JOIN `wonder-dw-prod-brd.command_center.nodes` n
  ON dtc.hdr_id = n.facility_id
LEFT JOIN `wonder-raw-prod.mysql_batch_sporklift.dtc_purchase_order_items` dtci
  ON dtc.purchase_order_id = dtci.purchase_order_id
WHERE TIMESTAMP(dtc.created_at) >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
GROUP BY dtc.hdr_id, hdr_name, status
ORDER BY num_orders DESC;
```

**Join Patterns**:
```sql
-- One-to-many with DTC purchase order items
dtc_purchase_orders.purchase_order_id = dtc_purchase_order_items.purchase_order_id

-- To get HDR facility names
dtc_purchase_orders.hdr_id = command_center.nodes.facility_id (WHERE node_type = 'HDR')

-- To audit trail
dtc_purchase_orders.purchase_order_id = dtc_purchase_orders_audit.purchase_order_id
```

---

### dtc_purchase_order_items

**Purpose**: Line items for DTC purchase orders with SKU, quantity, pricing, and status tracking.

**Data Volume**: 1,397,238 line items (Jul 30, 2025 - Present)

**Schema**:
```sql
purchase_order_item_id   STRING       -- Primary key (UUID format)
purchase_order_id        STRING       -- Foreign key to dtc_purchase_orders (UUID)
sku                      STRING       -- SKU code for this line item
quantity                 NUMERIC      -- Quantity ordered (note: NUMERIC type, not INTEGER)
price                    STRING       -- Item price (stored as string)
status                   STRING       -- Item-level status
error_message            STRING       -- Error details if item had issues
shipment_id              STRING       -- Shipment tracking ID
created_at               DATETIME     -- Item creation timestamp (UTC)
updated_at               DATETIME     -- Item update timestamp (UTC)
_sync_time               DATETIME     -- MySQL replication sync timestamp
```

**Key Fields**:

- **`quantity`**: NUMERIC type (not INTEGER like regular PO items) - can represent fractional quantities

- **`price`**: Stored as STRING (not NUMERIC) - cast to NUMERIC for calculations:
  ```sql
  CAST(price AS NUMERIC) as price_numeric
  ```

- **`error_message`**: Populated when line item encounters issues (validation, availability, etc.)

- **`shipment_id`**: Links to shipment tracking (same field exists in parent DTC PO)

**Usage**:
```sql
-- Analyze DTC order items with pricing
SELECT
  dtci.sku,
  COUNT(DISTINCT dtci.purchase_order_id) as num_orders,
  SUM(dtci.quantity) as total_quantity,
  AVG(CAST(dtci.price AS NUMERIC)) as avg_price,
  COUNT(CASE WHEN dtci.error_message IS NOT NULL THEN 1 END) as num_errors
FROM `wonder-raw-prod.mysql_batch_sporklift.dtc_purchase_order_items` dtci
WHERE TIMESTAMP(dtci.created_at) >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
GROUP BY dtci.sku
ORDER BY total_quantity DESC;
```

**Join Patterns**:
```sql
-- Many-to-one with DTC purchase orders
dtc_purchase_order_items.purchase_order_id = dtc_purchase_orders.purchase_order_id
```

---

## Audit Tables

### purchase_orders_audit

**Purpose**: Complete audit trail of all changes to regular purchase orders, tracking INSERT and UPDATE operations.

**Data Volume**: 60,272 audit records

**Schema**: Same as `purchase_orders` table plus:
```sql
operation            STRING       -- INSERT or UPDATE
audit_created_at     DATETIME     -- When audit record was created
```

All fields from `purchase_orders` are included in each audit record, allowing full reconstruction of PO history.

**Usage**:
```sql
-- Track status transitions for a specific PO
SELECT
  audit.operation,
  audit.status,
  audit.order_number,
  DATETIME(TIMESTAMP(audit.created_at), 'America/New_York') as event_time_ny,
  audit.updated_by
FROM `wonder-raw-prod.mysql_batch_sporklift.purchase_orders_audit` audit
WHERE audit.order_number = '251117DISH-SHIP00001'
ORDER BY audit.created_at;
```

---

### dtc_purchase_orders_audit

**Purpose**: Complete audit trail of all changes to DTC purchase orders.

**Data Volume**: 146,413 audit records

**Schema**: Same as `dtc_purchase_orders` table plus `operation` field (INSERT or UPDATE)

**Usage**: Similar to `purchase_orders_audit` but for DTC orders

---

## Facility Reference

### Three ShipHero Warehouses

| Facility | Facility ID | Location | ShipHero ID | Launched | Inventory Profile |
|----------|------------|----------|-------------|----------|-------------------|
| **DISH** | `46d337b4-7f61-4338-979a-5ee8d8e0071f` | 149 New Dutch Lane, Fairfield, NJ 07004 | V2FyZWhvdXNlOjEyMTUyMQ== | Aug 18, 2025 | 20K+ SKUs, 198K units |
| **Millington** | `de117c76-d46f-4cf3-943e-37513b32be47` | 50 Division Avenue, Millington, NJ 07946 | V2FyZWhvdXNlOjEyNjYzMQ== | Aug 13, 2025 | 1K SKUs, 1.5M units |
| **Arcadia** | `070f0993-93d0-4518-bc58-b957130b3b81` | 300 Parkview Road, Hazle Township, PA 18202 | V2FyZWhvdXNlOjEyNzU1Mg== | Sep 23, 2025 | 59 SKUs, 46K units |

**Query to Get Facility Details**:
```sql
SELECT
  facility_id,
  facility_name,
  facility_type,
  address,
  shiphero_facility_id
FROM `wonder-dw-prod-brd.command_center.nodes`
WHERE facility_id IN (
  '46d337b4-7f61-4338-979a-5ee8d8e0071f',
  'de117c76-d46f-4cf3-943e-37513b32be47',
  '070f0993-93d0-4518-bc58-b957130b3b81'
);
```

---

## Key Relationships

### Cross-Dataset Integration

**Inventory Snapshots → Purchase Orders**:
```sql
-- Join on-hand inventory with incoming POs
SELECT
  s.vendor_sku,
  SUM(s.on_hand) as current_on_hand,
  SUM(poi.quantity - COALESCE(poi.quantity_received, 0)) as quantity_on_order
FROM `wonder-sporklift-prod.sporklift.dish_inventory_snapshot` s
LEFT JOIN `wonder-raw-prod.mysql_batch_sporklift.purchase_order_items` poi
  ON s.vendor_sku = poi.vendor_sku
WHERE s.snapshot_id = '<latest_snapshot_id>'
  AND UPPER(poi.status) IN ('PENDING', 'IN_PROGRESS')
GROUP BY s.vendor_sku;
```

**Sporklift → Supply Chain (POMS)**:
```sql
-- Map vendor SKUs to Wonder SKUs
SELECT
  sp.vendor_sku,
  poms.wonder_sku,
  poms.supplier_name,
  SUM(sp.on_hand) as sporklift_on_hand
FROM `wonder-sporklift-prod.sporklift.dish_inventory_snapshot` sp
LEFT JOIN `wonder-raw-prod.pg_batch_supplychain.purchase_order_items` poms
  ON sp.vendor_sku = poms.supplier_sku
GROUP BY sp.vendor_sku, poms.wonder_sku, poms.supplier_name;
```

**Sporklift → Command Center (Nodes)**:
```sql
-- Always join facility_id to get human-readable names
FROM table t
JOIN `wonder-dw-prod-brd.command_center.nodes` n
  ON t.facility_id = n.facility_id
```

---

## Timezone Handling

**Storage**: All timestamps stored in UTC

**Conversion Pattern**:
```sql
-- For TIMESTAMP fields (snapshot_runs.created_at)
DATETIME(timestamp_column, 'America/New_York') as local_time

-- For DATETIME fields (purchase_orders.created_at, po_created_at, etc.)
DATETIME(TIMESTAMP(datetime_column), 'America/New_York') as local_time
```

**Key Distinction**:
- **Inventory snapshot tables** use TIMESTAMP type → direct conversion works
- **Purchase order tables** (MySQL replicas) use DATETIME type → must wrap in TIMESTAMP() first

**Example**:
```sql
SELECT
  order_number,
  po_created_at as utc_time,
  DATETIME(TIMESTAMP(po_created_at), 'America/New_York') as ny_time,
  TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), TIMESTAMP(po_created_at), HOUR) as hours_old
FROM `wonder-raw-prod.mysql_batch_sporklift.purchase_orders`
ORDER BY po_created_at DESC
LIMIT 10;
```

---

## Query Performance Tips

1. **Filter by Date Range** - With 216M snapshot records, always limit queries by time:
   ```sql
   WHERE created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
   ```

2. **Use snapshot_id for Point-in-Time** - More efficient than date filtering:
   ```sql
   WHERE snapshot_id = '<specific_snapshot_id>'
   ```

3. **Filter NULL Facilities Early** - Exclude test data:
   ```sql
   WHERE facility_id IS NOT NULL
   ```

4. **Use Window Functions for Latest Snapshots** - More efficient than subqueries:
   ```sql
   QUALIFY ROW_NUMBER() OVER (PARTITION BY facility_id ORDER BY created_at DESC) = 1
   ```

5. **Aggregate Before Joining** - Reduce data volume before cross-dataset joins

6. **Consider Partitioning** - For very large date ranges, partition by DATE(created_at)

---

## Data Quality Notes

### Known Issues

1. **synced_at Field Unused**: `dish_inventory_snapshot.synced_at` is NULL for all 216M records (intended feature not implemented)

2. **Early August Test Data**: 3,276 snapshot runs with NULL `facility_id` and `snapshot_url` (Aug 1-13, 2025) - always filter these out

3. **Status Value Inconsistency**:
   - Regular POs: `CLOSED` (uppercase) and `closed` (lowercase) both exist
   - Always use `UPPER(status)` for comparisons

4. **Allocation Field Rarely Populated**: Only 7 allocated units across 1.7M+ on-hand in latest snapshot - don't rely on this field

5. **hdr_id Data Type Inconsistency**: DTC POs have `hdr_id` as UUID strings, except for "DISH" which is a plain string

6. **price Field Type**: DTC items store price as STRING, not NUMERIC - must cast for calculations

### Facility Launch Dates Matter

Be aware of different data coverage periods when doing time-series analysis:
- **Millington**: Oldest data (Aug 13, 2025)
- **DISH**: Aug 18, 2025
- **Arcadia**: Newest (Sep 23, 2025)

Don't compare 90-day trends across facilities - Arcadia only has 56 days of data.
