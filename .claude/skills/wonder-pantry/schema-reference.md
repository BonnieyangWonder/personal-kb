# Wonder Pantry - Schema Reference

## Overview

Pantry is Wonder's inventory management system for HDR locations. It tracks inventory from order placement through receiving, storage, usage, and disposal, maintaining batch-level tracking with expiry dates. This reference documents all core tables, their schemas, relationships, and query patterns.

## Database Connection
- **BigQuery Dataset**: `wonder-raw-prod.mysql_batch_inventory`
- **Access**: Via bq CLI or BigQuery Console
- **Source**: PostgreSQL database replicated to BigQuery via batch sync

---

## Core Inventory Tables

### inventory_on_hand

**Purpose**: Current inventory snapshot at specific locations and batches

**Schema**:
```sql
id                       INTEGER            -- Primary key
site_id                  STRING             -- FK to sites.id (HDR location)
location_id              STRING             -- FK to hdr_locations.id (storage location)
item_number              STRING             -- Original item identifier (may be NULL)
wsku                     STRING             -- Wonder SKU (may be NULL)
consumable_item_number   STRING             -- Consumable unit identifier (always present)
partial_unit_id          STRING             -- Identifier for partial units
batch_id                 STRING             -- Batch identifier for tracking
expires_at               DATETIME           -- Batch expiry date/time (UTC)
quantity                 NUMERIC            -- Current quantity on hand
conversion_factor        INTEGER            -- Base units per tracked unit
uom                      STRING             -- Unit of measure (ea, g, oz, lb)
last_transaction_id      STRING             -- FK to most recent transaction
updated_by               STRING             -- User/system that last updated
updated_at               DATETIME           -- Last update timestamp (UTC)
_sync_time               DATETIME           -- BigQuery sync timestamp
```

**Key Fields**:
- `consumable_item_number` - Primary identifier for joining inventory tables
- `location_id` - Specific storage location (fridge, freezer, pod)
- `batch_id` - Tracks specific batches with different expiry dates
- `quantity` - Current amount, 0 means depleted but record remains
- `expires_at` - Critical for FIFO (first-in-first-out) logic

**Usage**:
```sql
-- Current inventory at an HDR
SELECT
  l.name AS location,
  ioh.consumable_item_number,
  ioh.quantity,
  ioh.uom,
  ioh.expires_at
FROM `wonder-raw-prod.mysql_batch_inventory.inventory_on_hand` ioh
JOIN `wonder-raw-prod.mysql_batch_inventory.hdr_locations` l ON ioh.location_id = l.id
WHERE ioh.site_id = 'YOUR_SITE_ID'
  AND ioh.quantity > 0
  AND l.deleted_at IS NULL
ORDER BY ioh.expires_at;
```

**Join Patterns**:
```sql
-- Join to locations
inventory_on_hand.location_id = hdr_locations.id

-- Join to sites
inventory_on_hand.site_id = sites.id

-- Join by consumable_item_number (preferred for inventory tracking)
inventory_on_hand.consumable_item_number = other_table.consumable_item_number
```

---

### inventory_ledgers

**Purpose**: Transaction history showing all inventory changes by location and batch

**Schema**:
```sql
id                       INTEGER            -- Primary key
transaction_id           STRING             -- FK to inventory_transactions.id
transaction_type_id      STRING             -- FK to transaction_types.id
site_id                  STRING             -- FK to sites.id
location_id              STRING             -- FK to hdr_locations.id
item_number              STRING             -- Original item identifier
wsku                     STRING             -- Wonder SKU
consumable_item_number   STRING             -- Consumable unit identifier
partial_unit_id          STRING             -- Partial unit identifier
batch_id                 STRING             -- Batch identifier
expires_at               DATETIME           -- Batch expiry (UTC)
quantity_changed         NUMERIC            -- Amount added (+) or removed (-)
result                   NUMERIC            -- Running balance after transaction
conversion_factor        INTEGER            -- Base units per tracked unit
uom                      STRING             -- Unit of measure
source                   STRING             -- System/service that created transaction
created_by               STRING             -- User/system identifier
created_at               DATETIME           -- Transaction timestamp (UTC)
_sync_time               DATETIME           -- BigQuery sync timestamp
```

**Key Fields**:
- `quantity_changed` - Positive for additions, negative for removals
- `result` - Quantity remaining at this location/batch after transaction
- `transaction_id` - Links to transaction metadata
- `created_at` - When transaction occurred (use for time-based analysis)

**Common Values**:
- `source`: "pantry-service", "kitchen-order-service", "receiving-service", "pantry_daily_job"

**Usage**:
```sql
-- Transaction history for an item
SELECT
  il.created_at,
  tt.operation,
  tt.reason_code,
  il.quantity_changed,
  il.result,
  il.source,
  l.name AS location
FROM `wonder-raw-prod.mysql_batch_inventory.inventory_ledgers` il
JOIN `wonder-raw-prod.mysql_batch_inventory.inventory_transactions` it ON il.transaction_id = it.id
JOIN `wonder-raw-prod.mysql_batch_inventory.transaction_types` tt ON it.transaction_type_id = tt.id
JOIN `wonder-raw-prod.mysql_batch_inventory.hdr_locations` l ON il.location_id = l.id
WHERE il.consumable_item_number = 'YOUR_CONSUMABLE_ITEM_NUMBER'
  AND il.site_id = 'YOUR_SITE_ID'
  AND il.created_at >= '2025-10-01'
  AND l.deleted_at IS NULL
  AND tt.deleted_at IS NULL
ORDER BY il.created_at DESC;
```

**Join Patterns**:
```sql
-- Join to transactions
inventory_ledgers.transaction_id = inventory_transactions.id

-- Join to transaction types
inventory_transactions.transaction_type_id = transaction_types.id

-- Join to locations
inventory_ledgers.location_id = hdr_locations.id
```

---

### inventory_transactions

**Purpose**: Transaction metadata linking ledger entries to transaction types

**Schema**:
```sql
id                       STRING             -- Primary key (UUID)
site_id                  STRING             -- FK to sites.id
transaction_type_id      STRING             -- FK to transaction_types.id
source                   STRING             -- System/service that created transaction
created_by               STRING             -- User/system identifier
created_at               DATETIME           -- Transaction timestamp (UTC)
updated_by               STRING             -- Last updater
updated_at               DATETIME           -- Last update timestamp
_sync_time               DATETIME           -- BigQuery sync timestamp
```

**Key Fields**:
- `id` - Links to ledgers and state tracking records
- `transaction_type_id` - Defines operation and reason
- `source` - Which service created the transaction

**Usage**:
```sql
-- Transaction metadata with type details
SELECT
  it.id,
  it.created_at,
  tt.operation,
  tt.reason_code,
  it.source,
  it.created_by
FROM `wonder-raw-prod.mysql_batch_inventory.inventory_transactions` it
JOIN `wonder-raw-prod.mysql_batch_inventory.transaction_types` tt ON it.transaction_type_id = tt.id
WHERE it.site_id = 'YOUR_SITE_ID'
  AND it.created_at >= '2025-10-01'
  AND tt.deleted_at IS NULL
ORDER BY it.created_at DESC;
```

---

### transaction_types

**Purpose**: Defines types of inventory operations and their reasons

**Schema**:
```sql
id                       STRING             -- Primary key (UUID)
operation                STRING             -- Operation type: Add, Remove, Move, Adjust, System
reason_code              STRING             -- Specific reason for operation
created_at               DATETIME           -- Record creation timestamp
created_by               STRING             -- Creator
updated_at               DATETIME           -- Last update timestamp
updated_by               STRING             -- Last updater
deleted_at               DATETIME           -- Soft delete timestamp
deleted_by               STRING             -- Who deleted
_sync_time               DATETIME           -- BigQuery sync timestamp
```

**Key Fields**:
- `operation` - High-level category of transaction
- `reason_code` - Specific reason within operation type

**Common Operations and Reason Codes**:

**Add Operations**:
- Received

**Remove Operations**:
- Expired, Auto-Expired, Hot Holding Expiration, Expired Prepped Item
- Damaged, Received Damaged
- Temperature Breach
- Cooked
- Consumed for Standard Operation
- Internal Demand
- Surprise and Delight
- Returned to DISH
- Other

**Move Operations**:
- System-Directed Movement
- System-Directed Retherm

**Adjust Operations**:
- Cycle Counted
- Location Counted
- Shelf Life Extension
- Migrate
- Update Received Order
- Hot Hold Request Shortage Reported
- Hot Hold Find Reported upon Cook Request

**System Operations**:
- Ordered
- Shipped
- Customer Order Placed
- Availability Refreshed
- Menu Item Refreshed
- TSL Changed
- Revert

**Usage**:
```sql
-- Find all waste-related transaction types
SELECT id, operation, reason_code
FROM `wonder-raw-prod.mysql_batch_inventory.transaction_types`
WHERE operation = 'Remove'
  AND (
    LOWER(reason_code) LIKE '%damage%'
    OR LOWER(reason_code) LIKE '%expir%'
    OR reason_code = 'Temperature Breach'
  )
  AND deleted_at IS NULL;
```

---

## Inventory State Tables

### inventory_state

**Purpose**: Current aggregate state of inventory by item at HDR (not location-specific)

**Schema**:
```sql
id                       INTEGER            -- Primary key
site_id                  STRING             -- FK to sites.id
item_number              STRING             -- Original item identifier (may be NULL)
consumable_item_number   STRING             -- Consumable unit identifier
conversion_factor        INTEGER            -- Base units per tracked unit
uom                      STRING             -- Unit of measure
on_order                 NUMERIC            -- Ordered but not shipped
shipped                  NUMERIC            -- Shipped but not received
not_received             NUMERIC            -- Arrived but not put away
on_hand                  NUMERIC            -- Total across all locations
reserved                 NUMERIC            -- Allocated for specific use
available                NUMERIC            -- Available for use (on_hand - reserved)
tsl                      NUMERIC            -- Total shelf life remaining (hours)
last_transaction_id      STRING             -- FK to most recent transaction
updated_by               STRING             -- Last updater
updated_at               DATETIME           -- Last update timestamp (UTC)
_sync_time               DATETIME           -- BigQuery sync timestamp
```

**Key Fields**:
- `on_order` - Items in purchase orders not yet shipped
- `shipped` - Items in transit
- `not_received` - Items delivered but not put away
- `on_hand` - Sum of all inventory_on_hand records for this item
- `reserved` - Allocated inventory (e.g., for customer orders)
- `available` - Free inventory: on_hand - reserved
- `tsl` - Shortest time to expiry across all batches (hours)

**State Relationship**:
```
available = on_hand - reserved
on_hand = sum of inventory_on_hand.quantity for all locations
```

**Usage**:
```sql
-- Current state for all items at HDR
SELECT
  consumable_item_number,
  on_order,
  shipped,
  on_hand,
  reserved,
  available,
  ROUND(tsl / 24, 1) AS days_until_expiry
FROM `wonder-raw-prod.mysql_batch_inventory.inventory_state`
WHERE site_id = 'YOUR_SITE_ID'
  AND (on_hand > 0 OR available > 0)
ORDER BY tsl;
```

---

### inventory_state_tracking

**Purpose**: History of state changes for items (like ledgers but for aggregate state)

**Schema**:
```sql
id                       INTEGER            -- Primary key
site_id                  STRING             -- FK to sites.id
item_number              STRING             -- Original item identifier
consumable_item_number   STRING             -- Consumable unit identifier
conversion_factor        INTEGER            -- Base units per tracked unit
uom                      STRING             -- Unit of measure
on_order_change          FLOAT              -- Change to on_order
on_order_result          FLOAT              -- on_order after transaction
shipped_change           FLOAT              -- Change to shipped
shipped_result           FLOAT              -- shipped after transaction
not_received_change      FLOAT              -- Change to not_received
not_received_result      FLOAT              -- not_received after transaction
on_hand_change           FLOAT              -- Change to on_hand
on_hand_result           FLOAT              -- on_hand after transaction
reserved_change          FLOAT              -- Change to reserved
reserved_result          FLOAT              -- reserved after transaction
available_change         FLOAT              -- Change to available
available_result         FLOAT              -- available after transaction
tsl_change               FLOAT              -- Change to TSL
tsl_result               FLOAT              -- TSL after transaction (hours)
transaction_id           STRING             -- FK to inventory_transactions.id
transaction_type_id      STRING             -- FK to transaction_types.id
created_by               STRING             -- Creator
created_at               DATETIME           -- Transaction timestamp (UTC)
_sync_time               DATETIME           -- BigQuery sync timestamp
```

**Key Fields**:
- `*_change` - Delta for each state field
- `*_result` - Value after transaction
- All state fields tracked: on_order, shipped, not_received, on_hand, reserved, available, tsl

**Usage**:
```sql
-- Track state changes for an item over time
SELECT
  ist.created_at,
  tt.operation,
  tt.reason_code,
  ist.on_hand_change,
  ist.on_hand_result,
  ist.available_change,
  ist.available_result,
  ist.tsl_result
FROM `wonder-raw-prod.mysql_batch_inventory.inventory_state_tracking` ist
JOIN `wonder-raw-prod.mysql_batch_inventory.inventory_transactions` it ON ist.transaction_id = it.id
JOIN `wonder-raw-prod.mysql_batch_inventory.transaction_types` tt ON it.transaction_type_id = tt.id
WHERE ist.site_id = 'YOUR_SITE_ID'
  AND ist.consumable_item_number = 'YOUR_CONSUMABLE_ITEM_NUMBER'
  AND ist.created_at >= '2025-10-01'
  AND tt.deleted_at IS NULL
ORDER BY ist.created_at DESC;
```

---

## Master Data Tables

### sites

**Purpose**: HDR locations (restaurants)

**Schema**:
```sql
id                       STRING             -- Primary key (UUID)
name                     STRING             -- HDR display name
inventory_alert_channel  STRING             -- Slack channel for alerts
created_by               STRING             -- Creator
created_at               DATETIME           -- Creation timestamp
updated_by               STRING             -- Last updater
updated_at               DATETIME           -- Last update timestamp
deleted_by               STRING             -- Who deleted
deleted_at               DATETIME           -- Soft delete timestamp
_sync_time               DATETIME           -- BigQuery sync timestamp
```

**Usage**:
```sql
-- List active HDR sites
SELECT id, name
FROM `wonder-raw-prod.mysql_batch_inventory.sites`
WHERE deleted_at IS NULL
ORDER BY name;
```

---

### hdr_locations

**Purpose**: Storage locations within HDRs (fridges, freezers, pods, appliances)

**Schema**:
```sql
id                       STRING             -- Primary key (UUID)
name                     STRING             -- Location display name
site_id                  STRING             -- FK to sites.id
can_receive              BOOLEAN            -- Can receive shipments here
location_class           STRING             -- CHILLED, FROZEN, AMBIENT, HOT
purpose                  STRING             -- Specific purpose of location
eligible_for_customer_order BOOLEAN         -- Can fulfill customer orders
is_central_location      BOOLEAN            -- Is this a central/main location
capacity                 INTEGER            -- Storage capacity
created_by               STRING             -- Creator
created_at               DATETIME           -- Creation timestamp
updated_by               STRING             -- Last updater
updated_at               DATETIME           -- Last update timestamp
deleted_by               STRING             -- Who deleted
deleted_at               DATETIME           -- Soft delete timestamp
_sync_time               DATETIME           -- BigQuery sync timestamp
```

**Key Fields**:
- `location_class` - Temperature classification
- `purpose` - Specific use case

**Common Values**:
- `location_class`: CHILLED, FROZEN, AMBIENT, HOT
- `purpose`: Pod Storage, Reserve Storage, Merchandiser, Hot Hold Appliance, Retherm Appliance, Slacking Fridge, Non-Food

**Usage**:
```sql
-- List storage locations by type at an HDR
SELECT
  location_class,
  purpose,
  name,
  capacity
FROM `wonder-raw-prod.mysql_batch_inventory.hdr_locations`
WHERE site_id = 'YOUR_SITE_ID'
  AND deleted_at IS NULL
ORDER BY location_class, purpose, name;
```

---

### item_configs

**Purpose**: Global item configuration settings

**Schema**:
```sql
item_number              STRING             -- Primary key
able_to_expire_manually  BOOLEAN            -- Can be manually expired
decrease_without_reason  BOOLEAN            -- Can decrease without reason code
can_remove_for_surprise_and_delight BOOLEAN -- Can be used for S&D
updated_by               STRING             -- Last updater
updated_time             DATETIME           -- Last update timestamp
_sync_time               DATETIME           -- BigQuery sync timestamp
```

---

### hdr_item_configs

**Purpose**: HDR-specific item configuration

**Schema**:
```sql
id                       STRING             -- Primary key (UUID)
hdr_id                   STRING             -- FK to sites.id (note: called hdr_id here)
item_number              STRING             -- Item identifier
suppress_at_hdr          BOOLEAN            -- Item hidden at this HDR
bom_usage                BOOLEAN            -- Item used in bill of materials
used_at_hdr              BOOLEAN            -- Item actively used at this HDR
min_level                NUMERIC            -- Minimum inventory level
max_level                NUMERIC            -- Maximum inventory level
created_by               STRING             -- Creator
created_time             DATETIME           -- Creation timestamp
updated_by               STRING             -- Last updater
updated_time             DATETIME           -- Last update timestamp
_sync_time               DATETIME           -- BigQuery sync timestamp
```

**Usage**:
```sql
-- Get min/max levels for items at HDR
SELECT
  hic.item_number,
  hic.min_level,
  hic.max_level,
  hic.used_at_hdr,
  hic.suppress_at_hdr
FROM `wonder-raw-prod.mysql_batch_inventory.hdr_item_configs` hic
WHERE hic.hdr_id = 'YOUR_SITE_ID'
  AND hic.used_at_hdr = true
ORDER BY hic.item_number;
```

---

## Orders and Receiving Tables

### inventory_orders

**Purpose**: Purchase orders from POMS, OrderGrid, and locally-sourced emergency purchases

**Cross-System Link**: Links to Supply Chain POMS via `poms_order_id = purchase_orders.id`

**Schema**:
```sql
id                       STRING             -- Primary key (UUID)
site_id                  STRING             -- FK to sites.id
ordergrid_id             STRING             -- OrderGrid order ID
ordergrid_order_number   STRING             -- OrderGrid order number
poms_order_id            STRING             -- POMS order ID (links to pg_batch_supplychain.purchase_orders.id)
poms_order_number        STRING             -- POMS order number (human-readable)
display_name             STRING             -- Human-readable order name
user_entered_id          STRING             -- User-provided identifier
delivery_deadline        DATETIME           -- Expected delivery time (UTC)
storage_type             STRING             -- FROZEN, CHILLED, AMBIENT
order_status             STRING             -- Order status
order_type               STRING             -- Order type (see below)
order_method             STRING             -- How order was placed (see below)
shipment_departure_time  DATETIME           -- When shipment left supplier (UTC)
supplier_node_id         STRING             -- Supplier identifier
shipped_time             DATETIME           -- When marked as shipped (UTC)
last_received_time       DATETIME           -- When last item was received (UTC)
created_by               STRING             -- Creator
created_time             DATETIME           -- Creation timestamp
updated_by               STRING             -- Last updater
updated_time             DATETIME           -- Last update timestamp
_sync_time               DATETIME           -- BigQuery sync timestamp
```

**Order Types and Methods**:

**CUSTOMER Orders (from POMS/suppliers - most common)**:
- `order_type='CUSTOMER'` + `order_method='POMS'` - Regular supplier orders (26K+ orders/month)
- `poms_order_id` is populated
- `inventory_order_items` has full item details
- Links to `pg_batch_supplychain.purchase_orders`

**LOCALLY_SOURCED_ORDER (Instacart/emergency purchases - IMPORTANT)**:
- `order_type='LOCALLY_SOURCED_ORDER'` + `order_method='PLACED_ON_PANTRY'`
- Store manager emergency purchases (Instacart, local stores)
- `display_name` indicates source: "instacart", "insta", "guacamole", etc.
- **CRITICAL**: `inventory_order_items` has ZERO items (not linked)
- Items appear separately in `inventory_ledgers` as Add/Received or Adjust/Found
- Must infer item linkage by timestamp and site matching
- ~313 orders in last 30 days across 43 sites

**Other Order Types**:
- `CUSTOMER` + `SYNCED_FROM_ED_DON_EXCEL` - Excel-based orders (~865/month)
- `CUSTOMER` + `PLACED_ON_PANTRY` - Manual orders (~145/month)
- `INTERNAL` + `POMS` - Internal transfers (~929/month)
- `VENDOR_ORDER` + `PLACED_ON_PANTRY` - Direct vendor orders (rare)

**Common Values**:
- `storage_type`: FROZEN, CHILLED, AMBIENT
- `order_status`: pending, shipped, received, cancelled
- `order_type`: CUSTOMER, LOCALLY_SOURCED_ORDER, INTERNAL, VENDOR_ORDER
- `order_method`: POMS, PLACED_ON_PANTRY, SYNCED_FROM_ED_DON_EXCEL

**Usage**:
```sql
-- Recent orders with receiving status
SELECT
  poms_order_number,
  display_name,
  order_status,
  delivery_deadline,
  shipped_time,
  last_received_time,
  storage_type
FROM `wonder-raw-prod.mysql_batch_inventory.inventory_orders`
WHERE site_id = 'YOUR_SITE_ID'
  AND delivery_deadline >= '2025-10-01'
ORDER BY delivery_deadline DESC;
```

---

### inventory_order_items

**Purpose**: Line items within orders

**Cross-System Link**: Links to Supply Chain POMS items via `poms_order_item_id = purchase_order_items.id`

**Schema**:
```sql
id                       STRING             -- Primary key (UUID)
order_id                 STRING             -- FK to inventory_orders.id
poms_order_item_id       STRING             -- POMS order item ID (links to pg_batch_supplychain.purchase_order_items.id)
delivery_date            DATETIME           -- Expected delivery date
item_number              STRING             -- Item identifier (matches purchase_order_items.supplier_sku)
consumable_item_number   STRING             -- Consumable unit identifier
conversion_factor        INTEGER            -- Base units per tracked unit
uom                      STRING             -- Unit of measure
requested_quantity       INTEGER            -- Quantity ordered
cancelled_quantity       INTEGER            -- Quantity cancelled
poms_updated_at          DATETIME           -- Last update from POMS
created_by               STRING             -- Creator
created_time             DATETIME           -- Creation timestamp
updated_by               STRING             -- Last updater
updated_time             DATETIME           -- Last update timestamp
_sync_time               DATETIME           -- BigQuery sync timestamp
```

**Usage**:
```sql
-- Order items with quantities
SELECT
  io.poms_order_number,
  ioi.consumable_item_number,
  ioi.requested_quantity,
  ioi.cancelled_quantity,
  ioi.uom,
  ioi.delivery_date
FROM `wonder-raw-prod.mysql_batch_inventory.inventory_order_items` ioi
JOIN `wonder-raw-prod.mysql_batch_inventory.inventory_orders` io ON ioi.order_id = io.id
WHERE io.site_id = 'YOUR_SITE_ID'
  AND ioi.delivery_date >= '2025-10-01'
ORDER BY ioi.delivery_date DESC;
```

---

### receiving_groups

**Purpose**: Groups of orders received together in a batch

**Schema**:
```sql
id                       STRING             -- Primary key (UUID)
site_id                  STRING             -- FK to sites.id
delivery_deadline        DATETIME           -- Expected delivery time
delivery_location        STRING             -- Where shipment arrives
group_order_type         STRING             -- Type of orders in group
status                   STRING             -- Group receiving status
order_created_time_from  DATETIME           -- Earliest order creation time
completed_time           DATETIME           -- When receiving completed
created_by               STRING             -- Creator
created_time             DATETIME           -- Creation timestamp
updated_by               STRING             -- Last updater
updated_time             DATETIME           -- Last update timestamp
_sync_time               DATETIME           -- BigQuery sync timestamp
```

**Common Values**:
- `status`: pending, in_progress, completed

**Usage**:
```sql
-- Recent receiving groups
SELECT
  id,
  delivery_deadline,
  group_order_type,
  status,
  completed_time
FROM `wonder-raw-prod.mysql_batch_inventory.receiving_groups`
WHERE site_id = 'YOUR_SITE_ID'
  AND delivery_deadline >= '2025-10-01'
ORDER BY delivery_deadline DESC;
```

---

## Task Tables

### task_cycle_counts

**Purpose**: Inventory cycle count tasks (physical counts to verify inventory)

**Schema**:
```sql
id                       STRING             -- Primary key (UUID)
site_id                  STRING             -- FK to sites.id
item_number              STRING             -- Item being counted
type                     STRING             -- Count type
task_group               STRING             -- Group identifier
task_cycle_count_config_id STRING           -- Configuration reference
status                   STRING             -- Task status
created_at               DATETIME           -- Creation timestamp
created_by               STRING             -- Creator
updated_at               DATETIME           -- Last update timestamp
updated_by               STRING             -- Last updater
_sync_time               DATETIME           -- BigQuery sync timestamp
```

**Common Values**:
- `status`: pending, in_progress, completed, cancelled

**Usage**:
```sql
-- Recent cycle count tasks
SELECT
  id,
  item_number,
  type,
  status,
  created_at,
  updated_at
FROM `wonder-raw-prod.mysql_batch_inventory.task_cycle_counts`
WHERE site_id = 'YOUR_SITE_ID'
  AND created_at >= '2025-10-01'
ORDER BY created_at DESC;
```

---

### task_pulls

**Purpose**: Tasks to pull items from storage to active locations

**Schema**:
```sql
id                       STRING             -- Primary key (UUID)
site_id                  STRING             -- FK to sites.id
pull_id                  INTEGER            -- Pull batch identifier
item_number              STRING             -- Item to pull
batch_id                 STRING             -- Specific batch to pull
consumable_item_number   STRING             -- Consumable unit identifier
conversion_factor        INTEGER            -- Base units per tracked unit
uom                      STRING             -- Unit of measure
requested_quantity       FLOAT              -- Quantity requested
status                   STRING             -- Task status
created_by               STRING             -- Creator
created_time             DATETIME           -- Creation timestamp
updated_by               STRING             -- Last updater
updated_time             DATETIME           -- Last update timestamp
_sync_time               DATETIME           -- BigQuery sync timestamp
```

---

### task_slacking

**Purpose**: Tasks to move items from freezer to thaw (slack) for later use

**Schema**:
```sql
id                       STRING             -- Primary key (UUID)
site_id                  STRING             -- FK to sites.id
service_date             DATETIME           -- Date item will be used
item_number              STRING             -- Item to slack
consumable_item_number   STRING             -- Consumable unit identifier
slacking_method          STRING             -- How to slack (fridge, room temp)
slacking_item_type       STRING             -- Type of item being slacked
conversion_factor        INTEGER            -- Base units per tracked unit
requested_quantity       NUMERIC            -- Quantity to slack
tomorrow_tsl             NUMERIC            -- Tomorrow's TSL
today_tsl                NUMERIC            -- Today's TSL
today_non_expire         NUMERIC            -- Today's non-expiring inventory
today_expire             NUMERIC            -- Today's expiring inventory
slacking_location_id     STRING             -- FK to hdr_locations.id
slacking_quantity        NUMERIC            -- Actual quantity slacked
freezer_on_hand          NUMERIC            -- Available in freezer
requested_time           DATETIME           -- When task was requested
status                   STRING             -- Task status
resolved_time            DATETIME           -- When task completed
estimated_finish_slacking_time DATETIME     -- Estimated completion time
slacking_hours           NUMERIC            -- Hours needed to slack
thawed_shelf_life_days   INTEGER            -- Shelf life after thawing (days)
thawed_shelf_life_minutes INTEGER           -- Shelf life after thawing (minutes)
thawed_expires_at        DATETIME           -- When thawed item expires
created_by               STRING             -- Creator
created_time             DATETIME           -- Creation timestamp
updated_by               STRING             -- Last updater
updated_time             DATETIME           -- Last update timestamp
_sync_time               DATETIME           -- BigQuery sync timestamp
```

**Common Values**:
- `status`: pending, in_progress, completed

---

## Menu Availability Table

### menu_item_inventory_tracking

**Purpose**: Tracks menu item availability changes based on ingredient inventory

**Schema**:
```sql
id                       INTEGER            -- Primary key
hdr_id                   STRING             -- FK to sites.id (note: called hdr_id here)
service_date             DATETIME           -- Service date for menu
menu_item_number         STRING             -- Menu item identifier
menu_item_id             STRING             -- Menu item UUID
restaurant_id            STRING             -- Restaurant identifier
option_value_id          STRING             -- Customization option ID
available_change         FLOAT              -- Change in availability count
available_result         FLOAT              -- Availability after change
non_integral_oos_item_numbers STRING        -- Items causing partial OOS
non_integral_oos_item_maximum_count INTEGER -- Max items before OOS
caused_oos_item_numbers  STRING             -- Items that caused OOS
transaction_id           STRING             -- FK to inventory_transactions.id
transaction_type_id      STRING             -- FK to transaction_types.id
created_by               STRING             -- Creator
created_at               DATETIME           -- Transaction timestamp (UTC)
_sync_time               DATETIME           -- BigQuery sync timestamp
```

**Key Fields**:
- `available_result` - Number of menu items that can be made with current inventory
- `caused_oos_item_numbers` - Which ingredient items caused out-of-stock
- `menu_item_number` - Links to menu system

**Usage**:
```sql
-- Why did a menu item go OOS?
SELECT
  mit.created_at,
  mit.menu_item_number,
  mit.available_change,
  mit.available_result,
  mit.caused_oos_item_numbers,
  tt.operation,
  tt.reason_code
FROM `wonder-raw-prod.mysql_batch_inventory.menu_item_inventory_tracking` mit
JOIN `wonder-raw-prod.mysql_batch_inventory.inventory_transactions` it ON mit.transaction_id = it.id
JOIN `wonder-raw-prod.mysql_batch_inventory.transaction_types` tt ON it.transaction_type_id = tt.id
WHERE mit.hdr_id = 'YOUR_HDR_ID'
  AND mit.menu_item_number = 'YOUR_MENU_ITEM_NUMBER'
  AND mit.service_date = '2025-10-23'
  AND tt.deleted_at IS NULL
ORDER BY mit.created_at DESC;
```

---

## Key Relationships

### Inventory Tracking Join Pattern

The core join pattern for detailed inventory analysis:

```sql
-- Complete inventory transaction details
SELECT
  il.created_at,
  s.name AS site_name,
  l.name AS location_name,
  l.location_class,
  il.consumable_item_number,
  il.item_number,
  tt.operation,
  tt.reason_code,
  il.quantity_changed,
  il.result,
  il.uom
FROM `wonder-raw-prod.mysql_batch_inventory.inventory_ledgers` il
JOIN `wonder-raw-prod.mysql_batch_inventory.inventory_transactions` it ON il.transaction_id = it.id
JOIN `wonder-raw-prod.mysql_batch_inventory.transaction_types` tt ON it.transaction_type_id = tt.id
JOIN `wonder-raw-prod.mysql_batch_inventory.hdr_locations` l ON il.location_id = l.id
JOIN `wonder-raw-prod.mysql_batch_inventory.sites` s ON il.site_id = s.id
WHERE s.id = 'YOUR_SITE_ID'
  AND l.deleted_at IS NULL
  AND s.deleted_at IS NULL
  AND tt.deleted_at IS NULL
ORDER BY il.created_at DESC;
```

---

## Timezone Handling

**Storage**: All timestamps stored in UTC

**Conversion Pattern** to Eastern Time:
```sql
-- Convert UTC to ET
DATETIME(created_at, 'America/New_York') AS created_at_et

-- Get current time in ET
CURRENT_DATETIME('America/New_York')
```

---

## Query Performance Tips

1. **Filter by site_id first** - Most tables are partitioned or clustered by site
2. **Use date range filters** - Add `WHERE created_at >= 'YYYY-MM-DD'` to limit scans
3. **Avoid scanning archived tables** - Use current tables without date suffixes
4. **Join on indexed fields** - Use site_id, location_id, transaction_id, consumable_item_number
5. **Check for soft deletes** - Add `WHERE deleted_at IS NULL` for sites, locations, transaction_types

---

## Data Quality Notes

### NULL Item Identifiers

Some records have NULL `item_number` or `wsku` but always have `consumable_item_number`:
- Use `consumable_item_number` as the primary join key for inventory tracking
- Use `item_number` or `wsku` only when linking to external systems (POMS, menu, etc.)

**Example**:
```sql
-- Safe join pattern handling NULLs
SELECT *
FROM `wonder-raw-prod.mysql_batch_inventory.inventory_on_hand` ioh
JOIN `wonder-raw-prod.mysql_batch_inventory.inventory_state` ist
  ON ioh.consumable_item_number = ist.consumable_item_number
  AND ioh.site_id = ist.site_id;
```

### Archived and Temp Tables

- **Archived tables** have date suffixes (e.g., `inventory_ledgers_251013`) - avoid these
- **Temp tables** have `ztemp__` prefix - avoid these
- Always use base table names without suffixes

### Conversion Factors

The `conversion_factor` represents base units per package. For example:
- Item packaged as 115g has conversion_factor=115, uom='g'
- Item sold as 1 each has conversion_factor=1, uom='ea'

When aggregating across different UOMs, use conversion_factor to normalize.
