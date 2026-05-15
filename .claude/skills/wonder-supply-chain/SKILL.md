---
name: wonder-supply-chain
description: Expert knowledge of Wonder's Purchase Order Management System (POMS). Useful when answering questions about how inventory moved around Wonder locations and who ordered what, when, and where. This includes purchase orders, purchase plans, and shipments. **Contains detailed schema information for POMS tables (purchase_orders, purchase_order_items, shipments, etc.) including column names, relationships, and field semantics. Use when working with supply chain data, POMS tables, CK1/DISH/HDR facilities, node references, or analyzing order fulfillment, inventory levels, and supplier relationships. Covers cross-schema joins, event sourcing patterns, and quantity field semantics. **Use this BEFORE manually checking BigQuery schemas with `bq show` commands.
allowed-tools: Read, Grep, Glob
---

# Wonder Supply Chain Expert

Expert knowledge of Wonder's Purchase Order Management System (POMS) covering the complete supply chain data infrastructure.

## What This Skill Provides

- **Complete schema knowledge** for POMS tables (purchase_orders, purchase_plans, shipments, etc.)
- **Cross-schema join patterns** between Supply Chain and Command Center projects
- **Event sourcing expertise** for audit trails and state transitions
- **Node reference system** including the CK1/DISH facility naming exception
- **Quantity field semantics** (placed vs shipped vs received vs in_transit)
- **Timezone handling** for UTC storage with America/New_York business operations
- **HDR order timing** (when to query purchase_plans vs purchase_orders)

## When to Use This Skill

Use this skill when you need to:
- Write queries against POMS tables (purchase_orders, purchase_plans, shipments)
- Understand relationships between suppliers, receivers, and facilities
- Analyze order fulfillment status or inventory movements
- Work with CK1 → DISH → HDR supply chains
- Join supply chain data with Command Center node references
- Understand quantity fields and their business meanings
- Debug data issues related to node IDs or facility references
- Analyze HDR order wave timing and placement schedules

## POMS vs hdr_orders - Critical Distinction

**Do NOT confuse these two order types:**

| Data Source | Table | Purpose |
|-------------|-------|---------|
| **POMS (Supply Chain)** | `wonder-raw-prod.pg_batch_supplychain.purchase_orders` | Supply chain orders from DISH/suppliers to HDRs |
| **Wonder Orders (Customer)** | `wonder-dw-prod-brd.orders.hdr_orders` | Customer-facing orders placed via app/web/marketplaces |

**When to use which:**
- **Analyzing supply chain/inventory flow** → Use `purchase_orders`
- **Analyzing customer sales/revenue** → Use `hdr_orders`
- **Investigating wave timing for HDR replenishment** → Use `purchase_orders`
- **Investigating customer order placement patterns** → Use `hdr_orders`

**Ambiguous requests - ASK FOR CLARIFICATION:**

When user asks about "orders" or "orders to HDRs", clarify which they mean:
- "Orders placed to HDRs" could mean customer orders OR supply chain replenishment
- "When did orders start?" could refer to customer demand OR inventory waves
- "Order timing" is ambiguous - ask if they mean customer orders or supply chain

Example clarifying question: *"Are you asking about customer orders (people ordering food via app/web) or supply chain orders (inventory replenishment from DISH to HDRs)?"*

**POMS URL Format** - To link to the supply chain UI:
```
https://supplychain.remarkablefoods.net/purchase-orders/<purchase_order_id>
```

## Core Concepts

### Database Location
- **BigQuery Dataset**: `wonder-raw-prod:pg_batch_supplychain`
- **Source**: Batch-replicated from PostgreSQL
- **Sync tracking**: All tables have `_sync_time` column

### Key Entity Relationships

```
purchase_orders → purchase_order_items
purchase_plans → purchase_plan_items
shipments → shipment_items → purchase_order_items → purchase_orders
```

### Product/Item Information

**CRITICAL**: Product names and descriptions are stored in `purchase_order_items.item_name`, NOT in a separate catalog table.

```sql
-- Search for products by name
SELECT item_name, supplier_sku, SUM(placed_quantity) as total
FROM `wonder-raw-prod.pg_batch_supplychain.purchase_order_items`
WHERE LOWER(item_name) LIKE '%search_term%'
GROUP BY item_name, supplier_sku
```

Common pitfalls:
- Don't search for `catalog_items` table - it doesn't exist in `pg_batch_supplychain`
- Don't rely on SKU codes containing product names (e.g., SKU 8805811 is "Poke Rice" but contains no "rice" string)
- Always use `item_name` field for product filtering by name
- `command_center.product_catalog` exists but only has item_number/facility mappings, not product names

### Node Reference System

**Critical Pattern**: POMS uses node IDs to reference facilities:
- `supplier_node_id` → who ships the order
- `receiver_node_id` → who receives the order

**Node ID Resolution**:
```sql
JOIN `wonder-dw-prod-brd.command_center.nodes`
  ON purchase_orders.supplier_node_id = nodes.facility_id
```

**Facility Names**: Use full facility names from the nodes table, not abbreviations:
- ✅ `facility_name = 'Upper West Side'`
- ❌ `facility_name = 'HDR_UWS'` or `facility_name = 'UWS'`

Common HDR facility names:
- "Upper West Side" (not HDR_UWS)
- "Upper East Side" (not HDR_UES)
- Check `command_center.nodes` for exact facility names

**EXCEPTION**: CK1 ↔ DISH transfers use facility name strings directly:
- `supplier_node_id = 'CK1'` and `receiver_node_id = 'DISH'`
- Do NOT join these to the nodes table with UUID matching

For complete schema details, see [schema-reference.md](schema-reference.md).

For common mistakes and gotchas, see [common-pitfalls.md](common-pitfalls.md).

## HDR Wave Timing

HDRs receive supply chain orders in **hourly waves** throughout the day. Orders are placed according to schedules configured in Command Center.

**Key tables for wave analysis:**
- `purchase_orders.place_at` - When orders were actually placed (historical)
- `wonder-dw-prod-brd.command_center.delivery_schedule` - Expected wave schedules (future dates only)

**Note**: The `delivery_schedule` table only contains **future** dates. For historical analysis, query `purchase_orders.place_at` directly.

## Query Patterns

### Purchase Orders with Facility Names and Items

```sql
SELECT
  po.id,
  supplier.facility_name as supplier,
  receiver.facility_name as receiver,
  po.place_at,
  po.status,
  poi.item_name,
  poi.supplier_sku,
  poi.placed_quantity
FROM `wonder-raw-prod.pg_batch_supplychain.purchase_orders` po
JOIN `wonder-dw-prod-brd.command_center.nodes` supplier
  ON po.supplier_node_id = supplier.facility_id
JOIN `wonder-dw-prod-brd.command_center.nodes` receiver
  ON po.receiver_node_id = receiver.facility_id
JOIN `wonder-raw-prod.pg_batch_supplychain.purchase_order_items` poi
  ON po.id = poi.purchase_order_id
WHERE receiver.facility_type = 'HDR'
  AND LOWER(poi.item_name) LIKE '%product_name%'
```

### Purchase Plans to Orders (Future vs Historical)

**Key distinction**: HDR orders convert from plans to orders a few minutes before dispatch.

**For future analysis** (next 8 hours):
```sql
SELECT
  pp.place_at,
  ppi.supplier_sku,
  ppi.allocated_quantity
FROM `wonder-raw-prod.pg_batch_supplychain.purchase_plans` pp
JOIN `wonder-raw-prod.pg_batch_supplychain.purchase_plan_items` ppi
  ON pp.id = ppi.plan_id  -- NOTE: plan_id not purchase_plan_id
WHERE pp.place_at BETWEEN CURRENT_TIMESTAMP()
  AND TIMESTAMP_ADD(CURRENT_TIMESTAMP(), INTERVAL 8 HOUR)
```

**For historical analysis**:
```sql
SELECT
  po.place_at,
  poi.item_name,
  poi.wonder_sku,
  poi.placed_quantity
FROM `wonder-raw-prod.pg_batch_supplychain.purchase_orders` po
JOIN `wonder-raw-prod.pg_batch_supplychain.purchase_order_items` poi
  ON po.id = poi.purchase_order_id
WHERE po.place_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
```

**Searching for specific products**:
```sql
-- Find orders for a specific product type (e.g., rice)
WITH yesterday_orders AS (
  SELECT
    po.id as order_id,
    DATETIME(TIMESTAMP(po.place_at), 'America/New_York') as place_at_ny,
    receiver.facility_name as receiver_name
  FROM `wonder-raw-prod.pg_batch_supplychain.purchase_orders` po
  JOIN `wonder-dw-prod-brd.command_center.nodes` receiver
    ON po.receiver_node_id = receiver.facility_id
  WHERE DATE(DATETIME(TIMESTAMP(po.place_at), 'America/New_York'))
    = DATE_SUB(CURRENT_DATE('America/New_York'), INTERVAL 1 DAY)
    AND receiver.facility_name = 'Upper West Side'
)
SELECT
  poi.item_name,
  poi.supplier_sku,
  poi.uom,
  SUM(poi.placed_quantity) as total_placed,
  SUM(poi.shipped_quantity) as total_shipped,
  SUM(poi.received_quantity) as total_received
FROM yesterday_orders yo
JOIN `wonder-raw-prod.pg_batch_supplychain.purchase_order_items` poi
  ON yo.order_id = poi.purchase_order_id
WHERE LOWER(poi.item_name) LIKE '%rice%'
GROUP BY poi.item_name, poi.supplier_sku, poi.uom
ORDER BY total_placed DESC
```

### Quantity Field Selection

Choose the right quantity field for your analysis:

- `placed_quantity` - Final committed order amount (use for order totals)
- `shipped_quantity` - What supplier actually shipped
- `received_quantity` - What we confirmed receiving
- **In transit**: Calculate as `shipped_quantity - received_quantity`

```sql
SELECT
  poi.id,
  poi.placed_quantity,
  poi.shipped_quantity,
  poi.received_quantity,
  poi.shipped_quantity - poi.received_quantity as in_transit_quantity,
  CASE
    WHEN poi.received_quantity >= poi.placed_quantity THEN 'FULLY_RECEIVED'
    WHEN poi.shipped_quantity > poi.received_quantity THEN 'IN_TRANSIT'
    WHEN poi.shipped_quantity = 0 THEN 'NOT_SHIPPED'
  END as derived_state
FROM `wonder-raw-prod.pg_batch_supplychain.purchase_order_items` poi
```

### Timezone Conversions

**Critical**: All timestamps stored in UTC, but business operates in America/New_York.

```sql
-- Convert to NY timezone for filtering and display
DATETIME(TIMESTAMP(po.place_at), 'America/New_York') as place_at_ny

-- Filter by current date in NY timezone
DATE(DATETIME(TIMESTAMP(po.place_at), 'America/New_York'))
  = CURRENT_DATE('America/New_York')

-- Find future orders in business timezone
DATETIME(TIMESTAMP(po.place_at), 'America/New_York')
  > CURRENT_DATETIME('America/New_York')
```

## Query Examples Library

See the `query-examples/` directory for complete, tested queries:

- **Inventory Analysis**: In-transit inventory, stock levels
- **Order Analysis**: Recent orders, fulfillment status, short picks
- **Planning Operations**: Purchase plans with facilities, timing analysis

## Critical Field Name Differences

### Purchase Plans vs Purchase Orders

| Concept | Purchase Plans | Purchase Orders |
|---------|---------------|-----------------|
| Join field | `plan_id` | `purchase_order_id` |
| Product ID | `supplier_sku` only | `supplier_sku` + `wonder_sku` |
| Quantity | `allocated_quantity` | `placed_quantity` |

### Shipment Chain

```
shipments.id
  → shipment_items.shipment_id
  → shipment_items.purchase_order_item_id
  → purchase_order_items.id
  → purchase_order_items.purchase_order_id
  → purchase_orders.id
```

## Event Sourcing Tables

For complete audit trails, use event tables:
- `purchase_order_events`
- `purchase_order_item_events`
- `purchase_plan_events`
- `purchase_plan_item_events`
- `shipment_events`
- `shipment_item_events`

These capture all state transitions with timestamps and attribution.

## Best Practices

1. **Always verify schemas first** using BigQuery CLI:
   ```bash
   bq show --schema wonder-raw-prod:pg_batch_supplychain.table_name
   ```

2. **Always include `item_name` when querying purchase_order_items** for product identification:
   ```sql
   SELECT poi.item_name, poi.supplier_sku, poi.placed_quantity
   FROM `wonder-raw-prod.pg_batch_supplychain.purchase_order_items` poi
   -- Not just SELECT poi.supplier_sku
   ```

3. **Verify facility names** before filtering - don't assume abbreviations:
   ```sql
   -- First, check actual facility names
   SELECT DISTINCT facility_name FROM `wonder-dw-prod-brd.command_center.nodes`
   WHERE facility_name LIKE '%West%' OR facility_name LIKE '%UWS%'
   ```

4. **Check node ID patterns** before writing joins:
   ```sql
   -- Test if facility uses names or UUIDs
   SELECT DISTINCT supplier_node_id, receiver_node_id
   FROM `wonder-raw-prod.pg_batch_supplychain.purchase_orders`
   WHERE supplier_node_id IN ('CK1', 'DISH') LIMIT 10
   ```

5. **Use explicit column selection** - never SELECT *

6. **Filter on partitioned columns** to reduce costs:
   - `created_at` for historical queries
   - `place_at` for order timing

7. **Include timezone conversion** for any timestamp display or filtering

## Supporting Documentation

- [schema-reference.md](schema-reference.md) - Complete table schemas and relationships
- [common-pitfalls.md](common-pitfalls.md) - Common mistakes and how to avoid them
- [query-examples/](query-examples/) - Tested SQL queries for common patterns

## Cross-System Integration

### Cookbook Integration

Supply chain `wonder_sku` maps directly to Cookbook `item_number`:

```sql
-- Join supply chain items to Cookbook for recipe/item details
SELECT poi.wonder_sku, ei.name, ei.object_type
FROM `wonder-raw-prod.pg_batch_supplychain.purchase_order_items` poi
JOIN `secure-recipe-prod.recipe_v2.effective_items` ei
  ON poi.wonder_sku = ei.item_number
  AND ei.deleted = false
```

See **wonder-cookbook** skill for recipe/BOM analysis and the `supply-chain-integration.md` guide.
