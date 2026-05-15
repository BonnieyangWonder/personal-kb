# Transaction Types Reference - Wonder Pantry

Complete reference of all transaction operations and reason codes used in Pantry inventory tracking. Use this to understand what transactions are available and build precise queries.

---

## Overview

Every inventory change in Pantry has a `transaction_type` that consists of two parts:
- **`operation`**: The broad category of change (Add, Remove, Move, Adjust, System, Revise)
- **`reason_code`**: The specific reason for the change

You should **always filter by both** operation and reason_code for precise queries.

---

## All Operations

| Operation | Description | Usage |
|-----------|-------------|-------|
| `Add` | Items added to inventory | Receiving, production yield |
| `Remove` | Items removed from inventory | Waste, consumption, cooking |
| `Move` | Items moved between locations | Slacking, retherm, repositioning |
| `Adjust` | Quantity corrections | Cycle counts, found/lost items |
| `System` | System-initiated changes | Orders, reservations, availability |
| `Revise` | Historical corrections | Data migrations |

---

## Add Operation Reason Codes

Items being added to inventory (positive quantity changes).

| Reason Code | Description | Usage | Common Volume |
|-------------|-------------|-------|---------------|
| `Received` | Item received from supplier | Standard receiving process | Very High |
| `Yielded via Production` | Item produced from other items | Prep/production yield | Low |

### Common Add Queries

```sql
-- Track receiving activity
SELECT
  s.name AS site_name,
  il.consumable_item_number,
  SUM(il.quantity_changed) AS total_received
FROM `wonder-raw-prod.mysql_batch_inventory.inventory_ledgers` il
JOIN `wonder-raw-prod.mysql_batch_inventory.sites` s ON il.site_id = s.id
JOIN `wonder-raw-prod.mysql_batch_inventory.transaction_types` tt ON il.transaction_type_id = tt.id
WHERE tt.operation = 'Add'
  AND tt.reason_code = 'Received'
  AND DATE(il.created_at) >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
  AND tt.deleted_at IS NULL
  AND s.deleted_at IS NULL
GROUP BY s.name, il.consumable_item_number
ORDER BY total_received DESC;
```

---

## Remove Operation Reason Codes

Items being removed from inventory (negative quantity changes).

### Waste-Related Removals

These reason codes indicate food waste and are critical for waste analysis:

| Reason Code | Description | Volume | Notes |
|-------------|-------------|--------|-------|
| `Expired` | Item past expiration date | Medium | Manual expiration marking |
| `Auto-Expired` | Automatically expired by system | High | System checks expiration dates |
| `Hot Holding Expiration` | Food expired while held hot | Very High | Most common expiration type |
| `Expired Prepped Item` | Prepped items that expired | Medium | Prepared food shelf life |
| `Damaged` | Item physically damaged | Medium | Dropped, crushed, broken |
| `Received Damaged` | Item damaged upon receipt | Low | Supplier quality issue |
| `Temperature Breach` | Item exceeded safe temperature | Low | Cold chain failure |
| `Received Spoiled` | Item spoiled at receipt | Very Low | Supplier quality issue |
| `Received Mislabeled` | Item labeled incorrectly | Very Low | Labeling error |
| `Received with Other Quality Issue` | Other quality problems | Very Low | Various quality issues |
| `Received without Label` | Item missing required label | Very Low | Labeling compliance |
| `Food Quality` | General quality issue | Medium | Taste, appearance, etc. |

### Operational Removals

Normal business operations (not waste):

| Reason Code | Description | Volume | Notes |
|-------------|-------------|--------|-------|
| `Cooked` | Item cooked/prepared | Very High | Most common removal |
| `Consumed via Production` | Used in prep/production | High | Recipe consumption |
| `Consumed for Standard Operation` | Used in normal operations | High | Daily operations |
| `Internal Demand` | Used internally | Very Low | Staff meals, testing |
| `Surprise and Delight` | Given to customers | Very Low | Customer satisfaction |
| `Used for Testing or Training` | Training/testing purposes | Low | Staff training |

### Administrative Removals

Inventory adjustments and corrections:

| Reason Code | Description | Volume | Notes |
|-------------|-------------|--------|-------|
| `Purge` | System cleanup/reset | Low | System maintenance |
| `Inventory Inspection` | Inspection removal | Very Low | Regulatory/quality |
| `Clear Location` | Location cleared out | Low | Location management |
| `Marked OOS on KOM` | Marked out of stock on Kitchen Operations Manager | Low | Menu availability |
| `Returned to DISH` | Returned to distribution | Low | Return to warehouse |
| `Received in Error` | Received by mistake | Very Low | Order errors |
| `Other` | Miscellaneous removals | Very Low | Catch-all category |

### Common Remove Queries

```sql
-- Waste analysis by type (last 7 days)
SELECT
  tt.reason_code,
  COUNT(DISTINCT il.site_id) AS restaurants_affected,
  COUNT(DISTINCT il.transaction_id) AS waste_events,
  SUM(ABS(il.quantity_changed)) AS total_quantity_wasted
FROM `wonder-raw-prod.mysql_batch_inventory.inventory_ledgers` il
JOIN `wonder-raw-prod.mysql_batch_inventory.transaction_types` tt ON il.transaction_type_id = tt.id
WHERE tt.operation = 'Remove'
  AND tt.reason_code IN (
    'Expired', 'Auto-Expired', 'Hot Holding Expiration', 'Expired Prepped Item',
    'Damaged', 'Received Damaged', 'Temperature Breach', 'Received Spoiled',
    'Food Quality'
  )
  AND DATE(il.created_at) >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
  AND tt.deleted_at IS NULL
GROUP BY tt.reason_code
ORDER BY total_quantity_wasted DESC;
```

```sql
-- Top items damaged by restaurant
SELECT
  s.name AS restaurant_name,
  il.consumable_item_number,
  COUNT(*) AS damage_events,
  SUM(ABS(il.quantity_changed)) AS quantity_damaged,
  il.uom
FROM `wonder-raw-prod.mysql_batch_inventory.inventory_ledgers` il
JOIN `wonder-raw-prod.mysql_batch_inventory.sites` s ON il.site_id = s.id
JOIN `wonder-raw-prod.mysql_batch_inventory.transaction_types` tt ON il.transaction_type_id = tt.id
WHERE tt.operation = 'Remove'
  AND tt.reason_code IN ('Damaged', 'Received Damaged')
  AND DATE(il.created_at) >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
  AND tt.deleted_at IS NULL
  AND s.deleted_at IS NULL
GROUP BY s.name, il.consumable_item_number, il.uom
ORDER BY quantity_damaged DESC
LIMIT 20;
```

---

## Move Operation Reason Codes

Items moved between storage locations within the same HDR.

| Reason Code | Description | Volume | Notes |
|-------------|-------------|--------|-------|
| `System-Directed Movement` | System-initiated move | Medium | Automatic rebalancing |
| `User-Directed Movement` | Manual move by staff | Medium | Staff repositioning |
| `System-Directed Slack` | System-directed thawing | Low | Frozen → slacking fridge |
| `Self-Directed Retherm` | Staff-initiated reheating | Very Low | Manual retherm |
| `System-Directed Retherm` | System-directed reheating | Low | Automatic retherm |
| `Hot Hold` | Moved to hot holding | Medium | Cooked → hot hold |
| `Opened for Prep` | Opened package for prep | Low | Prep operations |

### Common Move Queries

```sql
-- Track slacking activity
SELECT
  s.name AS site_name,
  COUNT(*) AS slack_moves,
  COUNT(DISTINCT il.consumable_item_number) AS unique_items_slacked
FROM `wonder-raw-prod.mysql_batch_inventory.inventory_ledgers` il
JOIN `wonder-raw-prod.mysql_batch_inventory.sites` s ON il.site_id = s.id
JOIN `wonder-raw-prod.mysql_batch_inventory.transaction_types` tt ON il.transaction_type_id = tt.id
WHERE tt.operation = 'Move'
  AND tt.reason_code = 'System-Directed Slack'
  AND DATE(il.created_at) >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
  AND tt.deleted_at IS NULL
  AND s.deleted_at IS NULL
GROUP BY s.name
ORDER BY slack_moves DESC;
```

---

## Adjust Operation Reason Codes

Quantity adjustments and corrections (can be positive or negative).

| Reason Code | Description | Volume | Notes |
|-------------|-------------|--------|-------|
| `Cycle Counted` | Cycle count adjustment | Medium | Regular inventory counts |
| `Location Counted` | Location-specific count | Low | Specific location audit |
| `Found` | Item found (increase qty) | Low | Previously missing items |
| `Lost` | Item lost (decrease qty) | Low | Cannot locate item |
| `Shelf Life Extension` | Expiration date extended | Low | Quality assessment |
| `Update Received Order` | Correction to received qty | Low | Receiving adjustment |
| `Hot Hold Request Shortage Reported` | Shortage reported | Very Low | Hot hold inventory issue |
| `Hot Hold Find Reported upon Cook Request` | Item found during cook | Very Low | Found during cooking |
| `Hot Hold Shortage Reported upon Cook Request` | Shortage during cook | Very Low | Missing during cooking |
| `Migrate` | Data migration adjustment | Very Low | System migration |

### Common Adjust Queries

```sql
-- Cycle count discrepancies
SELECT
  s.name AS site_name,
  il.consumable_item_number,
  COUNT(*) AS adjustment_count,
  SUM(il.quantity_changed) AS net_adjustment,
  SUM(ABS(il.quantity_changed)) AS total_discrepancy
FROM `wonder-raw-prod.mysql_batch_inventory.inventory_ledgers` il
JOIN `wonder-raw-prod.mysql_batch_inventory.sites` s ON il.site_id = s.id
JOIN `wonder-raw-prod.mysql_batch_inventory.transaction_types` tt ON il.transaction_type_id = tt.id
WHERE tt.operation = 'Adjust'
  AND tt.reason_code = 'Cycle Counted'
  AND DATE(il.created_at) >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
  AND tt.deleted_at IS NULL
  AND s.deleted_at IS NULL
GROUP BY s.name, il.consumable_item_number
HAVING ABS(net_adjustment) > 100
ORDER BY total_discrepancy DESC;
```

---

## System Operation Reason Codes

System-initiated changes for order and reservation management.

| Reason Code | Description | Volume | Notes |
|-------------|-------------|--------|-------|
| `Ordered` | Item ordered from supplier | High | POMS integration |
| `Shipped` | Item shipped by supplier | High | Order tracking |
| `Not Received` | Item not received | Low | Receiving discrepancy |
| `Customer Order Placed` | Reserved for customer | Very High | Order reservation |
| `Customer Order Cancelled` | Reservation released | Medium | Order cancellation |
| `Customer Order Modified` | Reservation adjusted | Low | Order changes |
| `Customer Order Remade` | Order remade | Very Low | Quality issues |
| `Availability Refreshed` | Availability recalculated | High | System refresh |
| `Menu Item Refreshed` | Menu availability updated | High | Menu sync |
| `TSL Changed` | Shelf life updated | Medium | Expiration tracking |
| `Available Qty Updated by Purge` | Purge cleanup | Low | System cleanup |
| `Revert` | Transaction reverted | Very Low | Error correction |

### Common System Queries

```sql
-- Order reservation activity
SELECT
  DATE(il.created_at) AS order_date,
  COUNT(DISTINCT il.transaction_id) AS orders_placed,
  SUM(ABS(il.quantity_changed)) AS total_quantity_reserved
FROM `wonder-raw-prod.mysql_batch_inventory.inventory_ledgers` il
JOIN `wonder-raw-prod.mysql_batch_inventory.transaction_types` tt ON il.transaction_type_id = tt.id
WHERE tt.operation = 'System'
  AND tt.reason_code = 'Customer Order Placed'
  AND DATE(il.created_at) >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
  AND tt.deleted_at IS NULL
GROUP BY order_date
ORDER BY order_date DESC;
```

---

## Revise Operation Reason Codes

Historical data corrections and migrations.

| Reason Code | Description | Volume | Notes |
|-------------|-------------|--------|-------|
| `System Migration` | Data migration adjustment | Very Low | One-time migrations |

---

## Common Transaction Patterns

### Finding All Waste Transactions

```sql
SELECT
  tt.operation,
  tt.reason_code,
  COUNT(DISTINCT il.transaction_id) AS transaction_count,
  SUM(ABS(il.quantity_changed)) AS total_quantity
FROM `wonder-raw-prod.mysql_batch_inventory.inventory_ledgers` il
JOIN `wonder-raw-prod.mysql_batch_inventory.transaction_types` tt ON il.transaction_type_id = tt.id
WHERE tt.operation = 'Remove'
  AND tt.reason_code IN (
    -- Expiration waste
    'Expired', 'Auto-Expired', 'Hot Holding Expiration', 'Expired Prepped Item',
    -- Damage waste
    'Damaged', 'Received Damaged',
    -- Quality waste
    'Temperature Breach', 'Received Spoiled', 'Received Mislabeled',
    'Received with Other Quality Issue', 'Received without Label', 'Food Quality'
  )
  AND DATE(il.created_at) >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
  AND tt.deleted_at IS NULL
GROUP BY tt.operation, tt.reason_code
ORDER BY total_quantity DESC;
```

### Finding All Operational Consumption

```sql
SELECT
  tt.reason_code,
  COUNT(DISTINCT il.transaction_id) AS usage_events,
  SUM(ABS(il.quantity_changed)) AS total_consumed
FROM `wonder-raw-prod.mysql_batch_inventory.inventory_ledgers` il
JOIN `wonder-raw-prod.mysql_batch_inventory.transaction_types` tt ON il.transaction_type_id = tt.id
WHERE tt.operation = 'Remove'
  AND tt.reason_code IN ('Cooked', 'Consumed via Production', 'Consumed for Standard Operation')
  AND DATE(il.created_at) >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
  AND tt.deleted_at IS NULL
GROUP BY tt.reason_code
ORDER BY total_consumed DESC;
```

---

## Volume Guidelines

Based on actual data from Oct 17-23, 2025:

### Very High Volume (>100k transactions/week)
- `Cooked` (452k transactions)
- `Customer Order Placed` (System operation)

### High Volume (10k-100k transactions/week)
- `Hot Holding Expiration` (17k transactions)
- `Consumed via Production` (8k transactions)
- `Auto-Expired` (600 transactions)

### Medium Volume (100-10k transactions/week)
- `Expired` (2k transactions)
- `Expired Prepped Item` (600 transactions)
- `Food Quality` (400 transactions)
- `Damaged` (300 transactions)
- Various Move operations

### Low Volume (<100 transactions/week)
- Most receiving error types
- `Temperature Breach` (62 transactions)
- Administrative operations

---

## Best Practices

1. **Always filter by both operation AND reason_code**
   - Don't filter by operation alone - it's too broad
   - `Remove` includes 21+ different reason codes

2. **Use IN clauses for related reason codes**
   - Group related codes: all expiration types, all damage types
   - Makes queries more maintainable

3. **Always include deleted_at IS NULL**
   - `transaction_types` table has soft deletes
   - Deleted types should not be included in analysis

4. **Use ABS() for removal quantities**
   - Remove operations have negative `quantity_changed`
   - Use `ABS()` when summing to get positive totals

5. **Understand volume patterns**
   - Hot Holding Expiration is the most common expiration
   - Auto-Expired happens at scheduled system checks
   - Manual Expired requires staff action

---

## Quick Reference: Waste Categories

### Expiration Waste
```
'Expired', 'Auto-Expired', 'Hot Holding Expiration', 'Expired Prepped Item'
```

### Damage Waste
```
'Damaged', 'Received Damaged'
```

### Quality Waste
```
'Temperature Breach', 'Received Spoiled', 'Received Mislabeled',
'Received with Other Quality Issue', 'Received without Label', 'Food Quality'
```

### All Waste Combined
```
'Expired', 'Auto-Expired', 'Hot Holding Expiration', 'Expired Prepped Item',
'Damaged', 'Received Damaged', 'Temperature Breach', 'Received Spoiled',
'Received Mislabeled', 'Received with Other Quality Issue',
'Received without Label', 'Food Quality'
```
