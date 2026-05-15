-- ============================================================================
-- INVENTORY ANALYSIS QUERIES
-- ============================================================================
-- Purpose: Track inventory levels, in-transit items, and stock movements
-- Use Cases: Inventory reconciliation, fulfillment analysis, shortage detection
-- ============================================================================

-- ----------------------------------------------------------------------------
-- IN-TRANSIT INVENTORY: CK1 → DISH
-- ----------------------------------------------------------------------------
-- Purpose: Items shipped from CK1 but not yet received at DISH
-- Use Case: Monitor inventory in transit, identify potential receiving issues
-- Gotchas:
--   - CK1/DISH use facility names directly ('CK1', 'DISH'), not UUIDs
--   - Do NOT join these to the nodes table
--   - in_transit_quantity = shipped_quantity - received_quantity

SELECT
  poi.wonder_sku,
  poi.supplier_sku,
  SUM(poi.placed_quantity) AS total_placed,
  SUM(poi.shipped_quantity) AS total_shipped,
  SUM(poi.received_quantity) AS total_received,
  SUM(poi.shipped_quantity - poi.received_quantity) AS in_transit_quantity
FROM `wonder-raw-prod.pg_batch_supplychain.purchase_orders` po
JOIN `wonder-raw-prod.pg_batch_supplychain.purchase_order_items` poi
  ON po.id = poi.purchase_order_id
WHERE
  -- CK1 supplier and DISH receiver (EXCEPTION: use names not UUIDs)
  po.supplier_node_id = 'CK1'
  AND po.receiver_node_id = 'DISH'

  -- Only items that have been shipped
  AND poi.shipped_quantity > 0

  -- But not fully received yet
  AND poi.received_quantity < poi.shipped_quantity

GROUP BY
  poi.wonder_sku,
  poi.supplier_sku
HAVING
  SUM(poi.shipped_quantity - poi.received_quantity) > 0
ORDER BY
  in_transit_quantity DESC;


-- ----------------------------------------------------------------------------
-- IN-TRANSIT INVENTORY: SIMPLIFIED VIEW
-- ----------------------------------------------------------------------------
-- Purpose: Quick 4-column view of in-transit items
-- Use Case: Dashboard display, quick checks

SELECT
  poi.wonder_sku,
  SUM(poi.placed_quantity) AS placed_qty,
  SUM(poi.shipped_quantity) AS shipped_qty,
  SUM(poi.shipped_quantity - poi.received_quantity) AS in_transit_qty
FROM `wonder-raw-prod.pg_batch_supplychain.purchase_orders` po
JOIN `wonder-raw-prod.pg_batch_supplychain.purchase_order_items` poi
  ON po.id = poi.purchase_order_id
WHERE
  po.supplier_node_id = 'CK1'
  AND po.receiver_node_id = 'DISH'
  AND poi.shipped_quantity > poi.received_quantity
GROUP BY
  poi.wonder_sku
ORDER BY
  in_transit_qty DESC;


-- ----------------------------------------------------------------------------
-- SHORT PICKS ANALYSIS (Last Night)
-- ----------------------------------------------------------------------------
-- Purpose: Identify items where shipped quantity < placed quantity
-- Use Case: Supplier performance, shortage analysis
-- Gotchas:
--   - Timezone critical! Use America/New_York for "last night"
--   - Short pick = placed_quantity - shipped_quantity
--   - Filter out items not yet shipped (shipped_quantity > 0)

WITH last_night AS (
  SELECT
    po.id as order_id,
    DATETIME(TIMESTAMP(po.place_at), 'America/New_York') as placed_at_ny,
    supplier.facility_name as supplier_name,
    receiver.facility_name as receiver_name,
    poi.wonder_sku,
    poi.placed_quantity,
    poi.shipped_quantity,
    poi.placed_quantity - poi.shipped_quantity as short_pick_qty
  FROM `wonder-raw-prod.pg_batch_supplychain.purchase_orders` po
  JOIN `wonder-raw-prod.pg_batch_supplychain.purchase_order_items` poi
    ON po.id = poi.purchase_order_id
  JOIN `wonder-dw-prod-brd.command_center.nodes` supplier
    ON po.supplier_node_id = supplier.facility_id
  JOIN `wonder-dw-prod-brd.command_center.nodes` receiver
    ON po.receiver_node_id = receiver.facility_id
  WHERE
    -- Last night's orders (4pm yesterday to 2am today)
    DATETIME(TIMESTAMP(po.place_at), 'America/New_York') >= DATETIME_SUB(CURRENT_DATETIME('America/New_York'), INTERVAL 1 DAY)
    AND DATETIME(TIMESTAMP(po.place_at), 'America/New_York') < CURRENT_DATETIME('America/New_York')

    -- Only items that were shipped
    AND poi.shipped_quantity > 0

    -- But shipped less than placed
    AND poi.shipped_quantity < poi.placed_quantity
)
SELECT
  supplier_name,
  receiver_name,
  wonder_sku,
  placed_quantity,
  shipped_quantity,
  short_pick_qty,
  ROUND(100.0 * short_pick_qty / placed_quantity, 1) as short_pick_pct
FROM last_night
ORDER BY
  short_pick_qty DESC,
  supplier_name,
  receiver_name;


-- ----------------------------------------------------------------------------
-- RECEIVING DISCREPANCIES
-- ----------------------------------------------------------------------------
-- Purpose: Items where received quantity doesn't match delivered quantity
-- Use Case: Identify receiving issues, quality control

SELECT
  receiver.facility_name as receiver,
  poi.wonder_sku,
  poi.delivered_quantity,
  poi.received_quantity,
  poi.receiving_rejected_quantity,
  poi.delivered_quantity - poi.received_quantity as discrepancy_qty,
  CASE
    WHEN poi.receiving_rejected_quantity > 0 THEN 'QUALITY_REJECT'
    WHEN poi.received_quantity < poi.delivered_quantity THEN 'COUNT_SHORTAGE'
    WHEN poi.received_quantity > poi.delivered_quantity THEN 'COUNT_OVERAGE'
  END as discrepancy_type
FROM `wonder-raw-prod.pg_batch_supplychain.purchase_orders` po
JOIN `wonder-raw-prod.pg_batch_supplychain.purchase_order_items` poi
  ON po.id = poi.purchase_order_id
JOIN `wonder-dw-prod-brd.command_center.nodes` receiver
  ON po.receiver_node_id = receiver.facility_id
WHERE
  -- Recent deliveries (last 7 days)
  poi.delivery_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)

  -- Items that were delivered
  AND poi.delivered_quantity > 0

  -- But received amount differs
  AND poi.received_quantity != poi.delivered_quantity

ORDER BY
  ABS(poi.delivered_quantity - poi.received_quantity) DESC,
  receiver.facility_name;


-- ----------------------------------------------------------------------------
-- INVENTORY VELOCITY BY FACILITY
-- ----------------------------------------------------------------------------
-- Purpose: How quickly facilities turn over inventory
-- Use Case: Identify slow-moving items, optimize stocking levels

SELECT
  receiver.facility_name,
  receiver.facility_type,
  poi.wonder_sku,
  COUNT(DISTINCT po.id) as order_count,
  SUM(poi.placed_quantity) as total_ordered,
  SUM(poi.received_quantity) as total_received,
  AVG(TIMESTAMP_DIFF(
    CAST(poi.updated_at AS TIMESTAMP),
    CAST(po.place_at AS TIMESTAMP),
    DAY
  )) as avg_days_to_receive,
  SUM(poi.placed_quantity) / COUNT(DISTINCT po.id) as avg_qty_per_order
FROM `wonder-raw-prod.pg_batch_supplychain.purchase_orders` po
JOIN `wonder-raw-prod.pg_batch_supplychain.purchase_order_items` poi
  ON po.id = poi.purchase_order_id
JOIN `wonder-dw-prod-brd.command_center.nodes` receiver
  ON po.receiver_node_id = receiver.facility_id
WHERE
  -- Last 30 days
  po.place_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)

  -- Only received items
  AND poi.received_quantity > 0

  -- Focus on HDR facilities
  AND receiver.facility_type = 'HDR'

GROUP BY
  receiver.facility_name,
  receiver.facility_type,
  poi.wonder_sku
HAVING
  COUNT(DISTINCT po.id) >= 3  -- At least 3 orders
ORDER BY
  receiver.facility_name,
  total_ordered DESC;


-- ============================================================================
-- USAGE NOTES
-- ============================================================================
-- 1. Run with BigQuery CLI:
--    bq query --use_legacy_sql=false --format=pretty < inventory-analysis.sql
--
-- 2. Timezone handling is critical for "last night" queries:
--    - Always convert UTC to America/New_York
--    - DATETIME(TIMESTAMP(utc_col), 'America/New_York')
--
-- 3. CK1/DISH exception:
--    - Use 'CK1' and 'DISH' strings directly
--    - Do NOT join to nodes table for these facilities
--
-- 4. Quantity field selection:
--    - placed_quantity: What was ordered
--    - shipped_quantity: What supplier sent
--    - delivered_quantity: What arrived at receiving
--    - received_quantity: What was confirmed and accepted
--    - in_transit: shipped - received
--    - short_pick: placed - shipped
--
-- 5. Check data freshness:
--    SELECT MAX(_sync_time) FROM purchase_orders;
-- ============================================================================
