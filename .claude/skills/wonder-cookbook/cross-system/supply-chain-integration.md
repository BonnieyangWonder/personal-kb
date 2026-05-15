# Supply Chain Integration - Cookbook to POMS

This guide covers joining Cookbook recipe data to the Purchase Order Management System (POMS) for supply chain analysis.

---

## Essential Filter (ALWAYS USE)

When joining to Cookbook item tables, always include:

```sql
AND ei.deleted = false
```

---

## Key Tables

| System | Dataset | Table | Purpose |
|--------|---------|-------|---------|
| Cookbook | `secure-recipe-prod.recipe_v2` | `effective_items` | Item master data |
| Cookbook | `secure-recipe-prod.recipe_v2` | `bom_lines` | Recipe components |
| POMS | `wonder-raw-prod.pg_batch_supplychain` | `purchase_orders` | Supply chain orders |
| POMS | `wonder-raw-prod.pg_batch_supplychain` | `purchase_order_items` | Order line items |
| Reference | `wonder-dw-prod-brd.command_center` | `nodes` | Facility/HDR lookup |

---

## Join Pattern

The key join between Cookbook and Supply Chain:

```sql
purchase_order_items.wonder_sku = effective_items.item_number
```

**Note**: `wonder_sku` in POMS matches `item_number` in Cookbook (e.g., "8805975").

---

## Common Use Cases

### 1. Find Recent Orders for a Recipe Component

Given a BOM component from Cookbook, find recent supply chain orders:

```sql
WITH recipe_components AS (
  SELECT DISTINCT bl.bom_line_item_number as component_id
  FROM `secure-recipe-prod.recipe_v2.bom_headers` bh
  INNER JOIN `secure-recipe-prod.recipe_v2.bom_lines` bl
    ON bh.item_number = bl.bom_header_item_number
  WHERE bh.is_active = true
    AND bh.item_number = '8009068'  -- Menu item
    AND bl.manage_inventory = true
    AND CURRENT_TIMESTAMP() BETWEEN TIMESTAMP(bl.service_start_time) AND TIMESTAMP(bl.service_end_time)
)
SELECT
  rc.component_id,
  ei.name as component_name,
  receiver.facility_name as hdr_name,
  poi.placed_quantity,
  poi.received_quantity,
  DATETIME(TIMESTAMP(po.place_at), 'America/New_York') as place_at_ny
FROM recipe_components rc
JOIN `secure-recipe-prod.recipe_v2.effective_items` ei
  ON rc.component_id = CAST(ei.item_number AS STRING)
  AND ei.deleted = false
JOIN `wonder-raw-prod.pg_batch_supplychain.purchase_order_items` poi
  ON rc.component_id = poi.wonder_sku
JOIN `wonder-raw-prod.pg_batch_supplychain.purchase_orders` po
  ON poi.purchase_order_id = po.id
JOIN `wonder-dw-prod-brd.command_center.nodes` receiver
  ON po.receiver_node_id = receiver.facility_id
WHERE po.place_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
  AND receiver.facility_type = 'HDR'
ORDER BY po.place_at DESC;
```

### 2. Analyze Supply Chain Volume by Object Type

Understand which Cookbook item types flow through supply chain:

```sql
SELECT
  ei.object_type,
  COUNT(DISTINCT poi.wonder_sku) as unique_skus,
  SUM(poi.placed_quantity) as total_placed
FROM `wonder-raw-prod.pg_batch_supplychain.purchase_order_items` poi
JOIN `secure-recipe-prod.recipe_v2.effective_items` ei
  ON poi.wonder_sku = ei.item_number
  AND ei.deleted = false
JOIN `wonder-raw-prod.pg_batch_supplychain.purchase_orders` po
  ON poi.purchase_order_id = po.id
WHERE po.place_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
GROUP BY ei.object_type
ORDER BY total_placed DESC;
```

### 3. Find Menu Items with Supply Chain Issues

Identify menu items where required components have low fill rates:

```sql
WITH component_fill_rates AS (
  SELECT
    poi.wonder_sku,
    SUM(poi.placed_quantity) as total_placed,
    SUM(poi.received_quantity) as total_received,
    SAFE_DIVIDE(SUM(poi.received_quantity), SUM(poi.placed_quantity)) as fill_rate
  FROM `wonder-raw-prod.pg_batch_supplychain.purchase_order_items` poi
  JOIN `wonder-raw-prod.pg_batch_supplychain.purchase_orders` po
    ON poi.purchase_order_id = po.id
  WHERE po.place_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
    AND poi.placed_quantity > 0
  GROUP BY poi.wonder_sku
  HAVING fill_rate < 0.95  -- Less than 95% fill rate
)
SELECT DISTINCT
  bh.item_number as menu_item_id,
  menu.name as menu_item_name,
  bl.bom_line_item_number as component_id,
  comp.name as component_name,
  cfr.fill_rate,
  cfr.total_placed,
  cfr.total_received
FROM `secure-recipe-prod.recipe_v2.bom_headers` bh
INNER JOIN `secure-recipe-prod.recipe_v2.bom_lines` bl
  ON bh.item_number = bl.bom_header_item_number
JOIN component_fill_rates cfr
  ON bl.bom_line_item_number = cfr.wonder_sku
LEFT JOIN `secure-recipe-prod.recipe_v2.effective_items` menu
  ON bh.item_number = CAST(menu.item_number AS STRING)
  AND menu.deleted = false
LEFT JOIN `secure-recipe-prod.recipe_v2.effective_items` comp
  ON bl.bom_line_item_number = CAST(comp.item_number AS STRING)
  AND comp.deleted = false
WHERE bh.is_active = true
  AND bl.manage_inventory = true  -- Only required components
  AND CURRENT_TIMESTAMP() BETWEEN TIMESTAMP(bl.service_start_time) AND TIMESTAMP(bl.service_end_time)
ORDER BY cfr.fill_rate ASC;
```

### 4. Track Component Orders to Specific HDR

See what's been ordered for a specific HDR based on its menu:

```sql
WITH hdr_info AS (
  SELECT facility_id, facility_name
  FROM `wonder-dw-prod-brd.command_center.nodes`
  WHERE facility_name = 'Upper West Side'
    AND facility_type = 'HDR'
)
SELECT
  ei.item_number,
  ei.name as component_name,
  ei.object_type,
  SUM(poi.placed_quantity) as total_ordered,
  SUM(poi.received_quantity) as total_received,
  COUNT(DISTINCT po.id) as order_count
FROM hdr_info h
JOIN `wonder-raw-prod.pg_batch_supplychain.purchase_orders` po
  ON po.receiver_node_id = h.facility_id
JOIN `wonder-raw-prod.pg_batch_supplychain.purchase_order_items` poi
  ON po.id = poi.purchase_order_id
JOIN `secure-recipe-prod.recipe_v2.effective_items` ei
  ON poi.wonder_sku = ei.item_number
  AND ei.deleted = false
WHERE po.place_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
GROUP BY ei.item_number, ei.name, ei.object_type
ORDER BY total_ordered DESC
LIMIT 50;
```

### 5. BOM Cost vs Supply Chain Cost Comparison

Compare recipe-specified costs with actual supply chain costs:

```sql
SELECT
  bl.bom_line_item_number as component_id,
  ei.name as component_name,
  bl.cost as bom_cost,
  AVG(poi.unit_cost) as avg_po_cost,
  bl.cost - AVG(poi.unit_cost) as cost_variance
FROM `secure-recipe-prod.recipe_v2.bom_lines` bl
JOIN `secure-recipe-prod.recipe_v2.effective_items` ei
  ON bl.bom_line_item_number = CAST(ei.item_number AS STRING)
  AND ei.deleted = false
JOIN `wonder-raw-prod.pg_batch_supplychain.purchase_order_items` poi
  ON bl.bom_line_item_number = poi.wonder_sku
JOIN `wonder-raw-prod.pg_batch_supplychain.purchase_orders` po
  ON poi.purchase_order_id = po.id
WHERE CURRENT_TIMESTAMP() BETWEEN TIMESTAMP(bl.service_start_time) AND TIMESTAMP(bl.service_end_time)
  AND po.place_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
  AND bl.cost IS NOT NULL
  AND poi.unit_cost IS NOT NULL
GROUP BY bl.bom_line_item_number, ei.name, bl.cost
HAVING ABS(bl.cost - AVG(poi.unit_cost)) > 0.10  -- $0.10+ variance
ORDER BY ABS(cost_variance) DESC;
```

---

## Data Flow Overview

```
Cookbook (Recipe Definition)
    │
    │  item_number (e.g., 8805975)
    │
    ▼
Supply Chain (POMS)
    │
    │  wonder_sku (same format)
    │  supplier_sku (may differ)
    │
    ▼
HDR Inventory (via purchase_orders)
```

**Key insight**: The same item_number/wonder_sku flows from recipe definition through supply chain to HDR inventory.

---

## Item Number Prefixes in Supply Chain

Supply chain primarily deals with:

| Prefix | Object Type | Description |
|--------|-------------|-------------|
| `88*` | PACKAGED | Pre-packaged items from suppliers (most common in POMS) |
| `50*` | INGREDIENT | Raw ingredients |
| `90*` | NON_FOOD | Packaging, supplies |

Menu items (`80*`) are NOT typically in supply chain - their components are.

---

## Timezone Notes

Supply chain timestamps are UTC. Convert for business analysis:

```sql
DATETIME(TIMESTAMP(po.place_at), 'America/New_York') as place_at_ny
```

---

## CK1/DISH Exception

When analyzing supply chain data:

- CK1 → DISH transfers use facility names as strings (`supplier_node_id = 'CK1'`)
- DISH → HDR transfers use UUIDs that join to `command_center.nodes`

See **wonder-supply-chain** skill for complete POMS documentation.

---

## Related Documentation

- [../core/bom-components.md](../core/bom-components.md) - Recipe BOM structure
- [pantry-integration.md](pantry-integration.md) - HDR inventory checks
- [orders-integration.md](orders-integration.md) - Customer order analysis
- See **wonder-supply-chain** skill for detailed POMS documentation
