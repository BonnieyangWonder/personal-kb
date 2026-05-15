# Inventory State Lifecycle - Wonder Pantry

Deep dive into Pantry's inventory state tracking system. This guide explains how inventory flows through different states from order to consumption.

---

## Overview

Pantry tracks inventory at two levels:
1. **Location-level**: `inventory_on_hand` and `inventory_ledgers` - specific locations and batches
2. **Site-level aggregate**: `inventory_state` and `inventory_state_tracking` - totals across all locations

This guide focuses on the **site-level aggregate state system**, which tracks inventory as it moves through the supply chain.

---

## State Fields Explained

### on_order

**Definition**: Items ordered from suppliers but not yet shipped

**When it increases**:
- Purchase order created in POMS or OrderGrid
- Transaction type: "Ordered" (System operation)

**When it decreases**:
- Supplier marks order as shipped
- Transaction type: "Shipped" (System operation)

**Example**: You place an order for 100 units of chicken. `on_order` increases by 100. When supplier ships it, `on_order` decreases by 100 and `shipped` increases by 100.

---

### shipped

**Definition**: Items in transit from supplier to HDR

**When it increases**:
- Supplier marks order as shipped
- Transaction type: "Shipped"

**When it decreases**:
- Items are received at HDR (even partially)
- Transaction type: "Received" (Add operation)

**Example**: Shipment of 100 units arrives. As items are received and put into inventory, `shipped` decreases and `not_received` or `on_hand` increases.

---

### not_received

**Definition**: Items that arrived but haven't been put away yet

**When it increases**:
- Items physically arrive but receiving is incomplete
- May increase during partial receiving

**When it decreases**:
- Items are put away into storage locations
- Transaction type: "Received"

**Example**: Delivery truck arrives with 100 units. During receiving, items are scanned but not yet placed in fridges. `not_received` holds these items until they're placed in `on_hand` locations.

**Note**: In many cases, items go directly from `shipped` to `on_hand`, bypassing `not_received`.

---

### on_hand

**Definition**: Total inventory physically at the HDR across all locations

**Relationship**: `on_hand` = sum of all `inventory_on_hand.quantity` for this item at this site

**When it increases**:
- Items received and put away
- Transaction type: "Received" (Add operation)
- Inventory adjustments up
- Transaction type: "Cycle Counted", "Location Counted" (Adjust operation)

**When it decreases**:
- Items consumed, expired, damaged, cooked
- Transaction types: "Expired", "Damaged", "Cooked", "Consumed for Standard Operation" (Remove operation)
- Items transferred out
- Transaction type: "System-Directed Movement" (Move operation)
- Inventory adjustments down
- Transaction type: "Cycle Counted" (Adjust operation)

**Example**: You have 50 units in Pod Storage and 30 units in Reserve Storage. `on_hand` = 80.

---

### reserved

**Definition**: Items allocated for specific purposes (typically customer orders)

**When it increases**:
- Customer places an order that requires this item
- Transaction type: "Customer Order Placed" (System operation)
- Internal demand request
- Transaction type: "Internal Demand"

**When it decreases**:
- Order is fulfilled or cancelled
- Items are cooked/prepared for the order
- Transaction type: "Cooked" (Remove operation)

**Example**: Customer orders a burger that requires a 4oz patty. When order is placed, `reserved` increases by 4oz. When burger is cooked, `reserved` decreases by 4oz and `on_hand` decreases by 4oz.

---

### available

**Definition**: Inventory available for use (not allocated to anything)

**Relationship**: `available = on_hand - reserved`

**Calculation**: This is a derived field, always calculated from `on_hand` and `reserved`

**When it changes**:
- Any change to `on_hand` or `reserved` affects `available`

**Example**:
- `on_hand` = 100, `reserved` = 30 → `available` = 70
- Customer orders increase `reserved` to 50 → `available` = 50
- New shipment increases `on_hand` to 150 → `available` = 100

**Critical**: This is what menu availability calculations use. If `available` for an ingredient is 0, menu items requiring it become unavailable.

---

### tsl (Total Shelf Life)

**Definition**: Shortest time to expiry across all batches of this item (measured in hours)

**Calculation**: Minimum of `(expires_at - current_time)` across all `inventory_on_hand` records for this item

**When it changes**:
- New batch received with different expiry
- Batch expires and is removed
- Batch expiry is extended
- Transaction type: "Shelf Life Extension" (Adjust operation)

**Units**: Hours (divide by 24 to get days)

**Example**:
- Batch A expires in 48 hours
- Batch B expires in 72 hours
- `tsl` = 48 (the shortest)

**Usage**: Used to trigger alerts when items are close to expiry and to calculate menu item availability based on whether items will last through service.

---

## State Transition Flow

### Normal Order Flow

```
1. Order Placed
   on_order: 0 → 100
   (Transaction: "Ordered")

2. Supplier Ships
   on_order: 100 → 0
   shipped: 0 → 100
   (Transaction: "Shipped")

3. Items Received
   shipped: 100 → 0
   on_hand: 0 → 100
   available: 0 → 100
   tsl: N/A → 168 (7 days in hours)
   (Transaction: "Received")

4. Customer Orders
   on_hand: 100 (no change)
   reserved: 0 → 30
   available: 100 → 70
   (Transaction: "Customer Order Placed")

5. Items Cooked
   on_hand: 100 → 70
   reserved: 30 → 0
   available: 70 (no change)
   (Transaction: "Cooked")

6. Items Expire
   on_hand: 70 → 50
   available: 70 → 50
   (Transaction: "Expired")
```

---

## inventory_state vs inventory_state_tracking

### inventory_state (Current Snapshot)

**Purpose**: Current state of each item at each site

**Update Pattern**: Updated in-place with each transaction

**Record Count**: One record per item per site

**Query Pattern**: Use this to get current state

```sql
-- Current inventory state
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

### inventory_state_tracking (History)

**Purpose**: History of all state changes over time

**Update Pattern**: New record inserted for each transaction that changes state

**Record Count**: Many records per item per site (one per transaction)

**Query Pattern**: Use this to analyze how state changed over time

```sql
-- State change history for an item
SELECT
  ist.created_at,
  tt.operation,
  tt.reason_code,
  ist.on_order_change,
  ist.shipped_change,
  ist.on_hand_change,
  ist.on_hand_result,
  ist.reserved_change,
  ist.available_change,
  ist.available_result
FROM `wonder-raw-prod.mysql_batch_inventory.inventory_state_tracking` ist
JOIN `wonder-raw-prod.mysql_batch_inventory.inventory_transactions` it ON ist.transaction_id = it.id
JOIN `wonder-raw-prod.mysql_batch_inventory.transaction_types` tt ON it.transaction_type_id = tt.id
WHERE ist.site_id = 'YOUR_SITE_ID'
  AND ist.consumable_item_number = 'YOUR_ITEM'
  AND ist.created_at >= '2025-10-01'
  AND tt.deleted_at IS NULL
ORDER BY ist.created_at DESC;
```

**Key Difference**:
- `inventory_state` → "What is the state NOW?"
- `inventory_state_tracking` → "How did the state change over time?"

---

## Common State Analysis Patterns

### Finding Items Low on Available Inventory

```sql
-- Items with low availability
SELECT
  s.name AS site_name,
  ist.consumable_item_number,
  ist.on_hand,
  ist.reserved,
  ist.available,
  ROUND(ist.tsl / 24, 1) AS days_until_expiry
FROM `wonder-raw-prod.mysql_batch_inventory.inventory_state` ist
JOIN `wonder-raw-prod.mysql_batch_inventory.sites` s ON ist.site_id = s.id
WHERE ist.available < 10  -- Low threshold
  AND ist.available > 0
  AND s.deleted_at IS NULL
ORDER BY ist.available;
```

---

### Tracking Reserved Inventory Changes

```sql
-- When did reserved inventory spike?
SELECT
  ist.created_at,
  tt.operation,
  tt.reason_code,
  ist.reserved_change,
  ist.reserved_result,
  ist.available_result,
  it.source
FROM `wonder-raw-prod.mysql_batch_inventory.inventory_state_tracking` ist
JOIN `wonder-raw-prod.mysql_batch_inventory.inventory_transactions` it ON ist.transaction_id = it.id
JOIN `wonder-raw-prod.mysql_batch_inventory.transaction_types` tt ON it.transaction_type_id = tt.id
WHERE ist.site_id = 'YOUR_SITE_ID'
  AND ist.consumable_item_number = 'YOUR_ITEM'
  AND ist.reserved_change != 0
  AND ist.created_at >= '2025-10-01'
  AND tt.deleted_at IS NULL
ORDER BY ist.created_at DESC;
```

---

### Analyzing Order to Receipt Time

```sql
-- Track how long from order to receipt
WITH order_events AS (
  SELECT
    ist.consumable_item_number,
    ist.created_at AS order_time,
    ist.transaction_id
  FROM `wonder-raw-prod.mysql_batch_inventory.inventory_state_tracking` ist
  JOIN `wonder-raw-prod.mysql_batch_inventory.inventory_transactions` it ON ist.transaction_id = it.id
  JOIN `wonder-raw-prod.mysql_batch_inventory.transaction_types` tt ON it.transaction_type_id = tt.id
  WHERE ist.site_id = 'YOUR_SITE_ID'
    AND ist.on_order_change > 0
    AND tt.operation = 'System'
    AND tt.reason_code = 'Ordered'
    AND tt.deleted_at IS NULL
),
receipt_events AS (
  SELECT
    ist.consumable_item_number,
    ist.created_at AS receipt_time
  FROM `wonder-raw-prod.mysql_batch_inventory.inventory_state_tracking` ist
  JOIN `wonder-raw-prod.mysql_batch_inventory.inventory_transactions` it ON ist.transaction_id = it.id
  JOIN `wonder-raw-prod.mysql_batch_inventory.transaction_types` tt ON it.transaction_type_id = tt.id
  WHERE ist.site_id = 'YOUR_SITE_ID'
    AND ist.on_hand_change > 0
    AND tt.operation = 'Add'
    AND tt.reason_code = 'Received'
    AND tt.deleted_at IS NULL
)
SELECT
  oe.consumable_item_number,
  oe.order_time,
  re.receipt_time,
  DATETIME_DIFF(re.receipt_time, oe.order_time, HOUR) AS hours_to_receive
FROM order_events oe
JOIN receipt_events re
  ON oe.consumable_item_number = re.consumable_item_number
  AND re.receipt_time > oe.order_time
WHERE oe.order_time >= '2025-10-01';
```

---

### Finding Items with Short TSL

```sql
-- Items expiring soon
SELECT
  s.name AS site_name,
  ist.consumable_item_number,
  ist.on_hand,
  ist.available,
  ROUND(ist.tsl / 24, 1) AS days_until_expiry,
  ist.updated_at
FROM `wonder-raw-prod.mysql_batch_inventory.inventory_state` ist
JOIN `wonder-raw-prod.mysql_batch_inventory.sites` s ON ist.site_id = s.id
WHERE ist.tsl < (48)  -- Less than 48 hours (2 days)
  AND ist.on_hand > 0
  AND s.deleted_at IS NULL
ORDER BY ist.tsl;
```

---

### Comparing on_hand to Available

```sql
-- How much inventory is reserved vs available?
SELECT
  s.name AS site_name,
  ist.consumable_item_number,
  ist.on_hand,
  ist.reserved,
  ist.available,
  ROUND(ist.reserved / NULLIF(ist.on_hand, 0) * 100, 1) AS reserved_percent
FROM `wonder-raw-prod.mysql_batch_inventory.inventory_state` ist
JOIN `wonder-raw-prod.mysql_batch_inventory.sites` s ON ist.site_id = s.id
WHERE ist.on_hand > 0
  AND ist.reserved > 0
  AND s.deleted_at IS NULL
ORDER BY reserved_percent DESC;
```

---

## State Change Triggers by Transaction Type

### Increases on_order
- Transaction: "Ordered" (System)

### Increases shipped
- Transaction: "Shipped" (System)

### Increases on_hand
- Transaction: "Received" (Add)
- Transaction: "Cycle Counted" (Adjust) - if count > current
- Transaction: "Shelf Life Extension" (Adjust)

### Decreases on_hand
- Transaction: "Expired", "Auto-Expired" (Remove)
- Transaction: "Damaged", "Received Damaged" (Remove)
- Transaction: "Temperature Breach" (Remove)
- Transaction: "Cooked" (Remove)
- Transaction: "Consumed for Standard Operation" (Remove)
- Transaction: "Cycle Counted" (Adjust) - if count < current

### Increases reserved
- Transaction: "Customer Order Placed" (System)
- Transaction: "Internal Demand" (Remove)

### Decreases reserved
- Transaction: "Cooked" (Remove) - fulfills reservation
- Order cancellation

### Changes tsl
- Any transaction that adds/removes batches
- Transaction: "Shelf Life Extension" (Adjust)
- Transaction: "TSL Changed" (System)

---

## Key Insights

### 1. available is the Critical Metric
Menu item availability depends on `available`, not `on_hand`. Items can be on_hand but not available if they're reserved.

### 2. State Tracking is Append-Only
`inventory_state_tracking` never updates or deletes records. It's a complete audit trail of state changes.

### 3. TSL is the Minimum
If you have 10 batches with different expiry dates, `tsl` shows the soonest expiry. This is critical for food safety.

### 4. reserved Can Exceed available
If you have 100 units but 120 reserved, you're oversold. `available` becomes negative, triggering OOS.

### 5. State Changes are Transactional
Every change to state is tied to an `inventory_transaction` and `transaction_type`. No state changes happen without a transaction.

---

## Troubleshooting State Issues

### Problem: available is negative

**Cause**: More items reserved than on_hand

**Investigation**:
```sql
-- Find items with negative availability
SELECT
  consumable_item_number,
  on_hand,
  reserved,
  available
FROM `wonder-raw-prod.mysql_batch_inventory.inventory_state`
WHERE site_id = 'YOUR_SITE_ID'
  AND available < 0;
```

---

### Problem: on_hand doesn't match sum of inventory_on_hand

**Cause**: Sync issue or recent transaction not yet reflected

**Investigation**:
```sql
-- Compare state to actual sum
WITH actual_on_hand AS (
  SELECT
    site_id,
    consumable_item_number,
    SUM(quantity) AS actual_quantity
  FROM `wonder-raw-prod.mysql_batch_inventory.inventory_on_hand`
  WHERE site_id = 'YOUR_SITE_ID'
  GROUP BY site_id, consumable_item_number
)
SELECT
  ist.consumable_item_number,
  ist.on_hand AS state_on_hand,
  COALESCE(aoh.actual_quantity, 0) AS actual_on_hand,
  ist.on_hand - COALESCE(aoh.actual_quantity, 0) AS difference
FROM `wonder-raw-prod.mysql_batch_inventory.inventory_state` ist
LEFT JOIN actual_on_hand aoh
  ON ist.site_id = aoh.site_id
  AND ist.consumable_item_number = aoh.consumable_item_number
WHERE ist.site_id = 'YOUR_SITE_ID'
  AND ABS(ist.on_hand - COALESCE(aoh.actual_quantity, 0)) > 0.01
ORDER BY ABS(difference) DESC;
```

---

### Problem: tsl seems wrong

**Cause**: Batch with wrong expiry date, or calculation timing

**Investigation**:
```sql
-- Check all batches and their expiry
SELECT
  consumable_item_number,
  batch_id,
  expires_at,
  DATETIME_DIFF(expires_at, CURRENT_DATETIME('UTC'), HOUR) AS hours_until_expiry,
  quantity
FROM `wonder-raw-prod.mysql_batch_inventory.inventory_on_hand`
WHERE site_id = 'YOUR_SITE_ID'
  AND consumable_item_number = 'YOUR_ITEM'
  AND quantity > 0
ORDER BY expires_at;
```

---

## Summary

The inventory state system provides:
- **Real-time tracking** of inventory through supply chain stages
- **Aggregate view** of inventory across all locations at an HDR
- **Historical audit trail** of all state changes
- **Availability calculation** for menu item planning
- **Expiry monitoring** via TSL tracking

Use `inventory_state` for current state and `inventory_state_tracking` for historical analysis.
