-- ============================================================================
-- ORDER ANALYSIS QUERIES
-- ============================================================================
-- Purpose: Analyze purchase orders, fulfillment status, and order patterns
-- Use Cases: Operations monitoring, supplier performance, order tracking
-- ============================================================================

-- ----------------------------------------------------------------------------
-- DISH → HDR ORDERS (Last 6 Hours)
-- ----------------------------------------------------------------------------
-- Purpose: Recent DISH to HDR restaurant orders with quantities
-- Use Case: Real-time operations monitoring, dispatch tracking
-- Gotchas:
--   - DISH to HDR uses UUID for supplier_node_id: '46d337b4-7f61-4338-979a-5ee8d8e0071f'
--   - Must filter receiver by facility_type = 'HDR'
--   - Timezone: Convert to NY time for display

SELECT
  receiver.facility_name AS hdr_name,
  DATETIME(TIMESTAMP(po.place_at), 'America/New_York') AS placed_at_ny,
  COUNT(DISTINCT poi.id) as item_count,
  SUM(poi.placed_quantity) AS placed_qty,
  SUM(poi.shipped_quantity) AS shipped_qty,
  SUM(poi.received_quantity) AS received_qty,
  SUM(poi.shipped_quantity - poi.received_quantity) as in_transit_qty
FROM `wonder-raw-prod.pg_batch_supplychain.purchase_orders` po
JOIN `wonder-raw-prod.pg_batch_supplychain.purchase_order_items` poi
  ON po.id = poi.purchase_order_id
JOIN `wonder-dw-prod-brd.command_center.nodes` receiver
  ON po.receiver_node_id = receiver.facility_id
WHERE
  -- DISH supplier (UUID from nodes table - NOT 'DISH' string!)
  po.supplier_node_id = '46d337b4-7f61-4338-979a-5ee8d8e0071f'

  -- Receiver must be HDR facility
  AND receiver.facility_type = 'HDR'

  -- Orders placed in last 6 hours
  AND po.place_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 6 HOUR)

  -- Only include items with quantities
  AND poi.placed_quantity > 0
GROUP BY
  receiver.facility_name,
  po.place_at
ORDER BY
  po.place_at DESC,
  receiver.facility_name;


-- ----------------------------------------------------------------------------
-- PURCHASE ORDER STATUS BREAKDOWN
-- ----------------------------------------------------------------------------
-- Purpose: Count orders by status with key metrics
-- Use Case: Dashboard metrics, status distribution analysis

SELECT
  po.status,
  COUNT(DISTINCT po.id) as order_count,
  COUNT(DISTINCT poi.id) as item_count,
  SUM(poi.placed_quantity) as total_placed_qty,
  SUM(poi.shipped_quantity) as total_shipped_qty,
  SUM(poi.received_quantity) as total_received_qty,
  ROUND(100.0 * SUM(poi.received_quantity) / NULLIF(SUM(poi.placed_quantity), 0), 1) as fulfillment_pct
FROM `wonder-raw-prod.pg_batch_supplychain.purchase_orders` po
JOIN `wonder-raw-prod.pg_batch_supplychain.purchase_order_items` poi
  ON po.id = poi.purchase_order_id
WHERE
  -- Last 24 hours
  po.place_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
GROUP BY
  po.status
ORDER BY
  order_count DESC;


-- ----------------------------------------------------------------------------
-- DERIVED ORDER STATES (Quantity-Based)
-- ----------------------------------------------------------------------------
-- Purpose: More reliable state based on actual quantities vs status field
-- Use Case: Accurate fulfillment tracking, avoiding status field lag
-- Gotchas:
--   - Status field may lag behind operational reality
--   - Quantity-based states are more reliable for business logic

SELECT
  po.id as order_id,
  po.status as recorded_status,
  CASE
    WHEN SUM(poi.received_quantity) >= SUM(poi.placed_quantity) THEN 'FULLY_RECEIVED'
    WHEN SUM(poi.shipped_quantity) > SUM(poi.received_quantity) AND SUM(poi.shipped_quantity) > 0 THEN 'IN_TRANSIT'
    WHEN SUM(poi.shipped_quantity) > 0 AND SUM(poi.received_quantity) = 0 THEN 'SHIPPED_NOT_RECEIVED'
    WHEN SUM(poi.shipped_quantity) = 0 THEN 'NOT_SHIPPED'
    ELSE 'PARTIAL_STATUS'
  END as derived_status,
  supplier.facility_name as supplier,
  receiver.facility_name as receiver,
  SUM(poi.placed_quantity) as total_placed,
  SUM(poi.shipped_quantity) as total_shipped,
  SUM(poi.received_quantity) as total_received,
  DATETIME(TIMESTAMP(po.place_at), 'America/New_York') as placed_at_ny
FROM `wonder-raw-prod.pg_batch_supplychain.purchase_orders` po
JOIN `wonder-raw-prod.pg_batch_supplychain.purchase_order_items` poi
  ON po.id = poi.purchase_order_id
JOIN `wonder-dw-prod-brd.command_center.nodes` supplier
  ON po.supplier_node_id = supplier.facility_id
JOIN `wonder-dw-prod-brd.command_center.nodes` receiver
  ON po.receiver_node_id = receiver.facility_id
WHERE
  po.place_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 48 HOUR)
GROUP BY
  po.id,
  po.status,
  supplier.facility_name,
  receiver.facility_name,
  po.place_at
ORDER BY
  po.place_at DESC;


-- ----------------------------------------------------------------------------
-- DISH SHIPMENTS (Last 6 Hours)
-- ----------------------------------------------------------------------------
-- Purpose: Shipments departing DISH with purchase order details
-- Use Case: Outbound logistics monitoring, shipment tracking
-- Gotchas:
--   - Join chain: shipments → shipment_items → purchase_order_items → purchase_orders
--   - Cannot directly join shipments to purchase_orders!

SELECT
  s.shipment_number,
  s.carrier,
  s.tracking_number,
  DATETIME(TIMESTAMP(s.ship_date), 'America/New_York') as ship_date_ny,
  receiver.facility_name as destination,
  COUNT(DISTINCT si.id) as item_count,
  SUM(si.quantity) as total_quantity
FROM `wonder-raw-prod.pg_batch_supplychain.shipments` s
JOIN `wonder-raw-prod.pg_batch_supplychain.shipment_items` si
  ON s.id = si.shipment_id
JOIN `wonder-raw-prod.pg_batch_supplychain.purchase_order_items` poi
  ON si.purchase_order_item_id = poi.id
JOIN `wonder-raw-prod.pg_batch_supplychain.purchase_orders` po
  ON poi.purchase_order_id = po.id
JOIN `wonder-dw-prod-brd.command_center.nodes` receiver
  ON po.receiver_node_id = receiver.facility_id
WHERE
  -- DISH supplier
  po.supplier_node_id = '46d337b4-7f61-4338-979a-5ee8d8e0071f'

  -- Shipments in last 6 hours
  AND s.created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 6 HOUR)
GROUP BY
  s.shipment_number,
  s.carrier,
  s.tracking_number,
  s.ship_date,
  receiver.facility_name
ORDER BY
  s.ship_date DESC;


-- ----------------------------------------------------------------------------
-- SUPPLIER PERFORMANCE SCORECARD
-- ----------------------------------------------------------------------------
-- Purpose: Evaluate supplier reliability and accuracy
-- Use Case: Supplier KPIs, vendor management

SELECT
  supplier.facility_name as supplier,
  supplier.facility_type,
  COUNT(DISTINCT po.id) as order_count,
  COUNT(DISTINCT poi.id) as item_count,

  -- Fulfillment metrics
  SUM(poi.placed_quantity) as total_ordered,
  SUM(poi.shipped_quantity) as total_shipped,
  SUM(poi.received_quantity) as total_received,

  -- Performance percentages
  ROUND(100.0 * SUM(poi.shipped_quantity) / NULLIF(SUM(poi.placed_quantity), 0), 1) as ship_fulfillment_pct,
  ROUND(100.0 * SUM(poi.received_quantity) / NULLIF(SUM(poi.placed_quantity), 0), 1) as receive_fulfillment_pct,

  -- Issues
  SUM(CASE WHEN poi.shipped_quantity < poi.placed_quantity THEN 1 ELSE 0 END) as short_pick_count,
  SUM(poi.placed_quantity - poi.shipped_quantity) as total_short_pick_qty,
  SUM(poi.receiving_rejected_quantity) as total_rejected_qty,

  -- Timing
  AVG(TIMESTAMP_DIFF(CAST(poi.updated_at AS TIMESTAMP), CAST(po.place_at AS TIMESTAMP), HOUR)) as avg_hours_to_fulfill

FROM `wonder-raw-prod.pg_batch_supplychain.purchase_orders` po
JOIN `wonder-raw-prod.pg_batch_supplychain.purchase_order_items` poi
  ON po.id = poi.purchase_order_id
JOIN `wonder-dw-prod-brd.command_center.nodes` supplier
  ON po.supplier_node_id = supplier.facility_id
WHERE
  -- Last 30 days
  po.place_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)

  -- Only completed orders
  AND poi.received_quantity > 0
GROUP BY
  supplier.facility_name,
  supplier.facility_type
HAVING
  COUNT(DISTINCT po.id) >= 5  -- Minimum 5 orders for meaningful stats
ORDER BY
  order_count DESC;


-- ----------------------------------------------------------------------------
-- ORDER SIZE DISTRIBUTION BY RECEIVER TYPE
-- ----------------------------------------------------------------------------
-- Purpose: Analyze typical order patterns by facility type
-- Use Case: Capacity planning, forecasting

WITH order_sizes AS (
  SELECT
    po.id as order_id,
    receiver.facility_type,
    COUNT(DISTINCT poi.id) as item_count,
    SUM(poi.placed_quantity) as total_quantity
  FROM `wonder-raw-prod.pg_batch_supplychain.purchase_orders` po
  JOIN `wonder-raw-prod.pg_batch_supplychain.purchase_order_items` poi
    ON po.id = poi.purchase_order_id
  JOIN `wonder-dw-prod-brd.command_center.nodes` receiver
    ON po.receiver_node_id = receiver.facility_id
  WHERE
    po.place_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
    AND poi.placed_quantity > 0
  GROUP BY
    po.id,
    receiver.facility_type
)
SELECT
  facility_type,
  COUNT(*) as order_count,
  MIN(item_count) as min_items,
  ROUND(AVG(item_count), 1) as avg_items,
  APPROX_QUANTILES(item_count, 100)[OFFSET(50)] as median_items,
  MAX(item_count) as max_items,
  MIN(total_quantity) as min_qty,
  ROUND(AVG(total_quantity), 1) as avg_qty,
  MAX(total_quantity) as max_qty
FROM order_sizes
GROUP BY facility_type
ORDER BY order_count DESC;


-- ----------------------------------------------------------------------------
-- LATE ORDERS ANALYSIS
-- ----------------------------------------------------------------------------
-- Purpose: Identify orders that missed expected delivery dates
-- Use Case: SLA tracking, operational issues detection

SELECT
  receiver.facility_name as receiver,
  receiver.facility_type,
  poi.delivery_date as expected_delivery,
  DATE(DATETIME(TIMESTAMP(poi.updated_at), 'America/New_York')) as actual_delivery,
  DATE_DIFF(
    DATE(DATETIME(TIMESTAMP(poi.updated_at), 'America/New_York')),
    poi.delivery_date,
    DAY
  ) as days_late,
  COUNT(DISTINCT poi.id) as late_item_count,
  SUM(poi.placed_quantity) as affected_quantity
FROM `wonder-raw-prod.pg_batch_supplychain.purchase_orders` po
JOIN `wonder-raw-prod.pg_batch_supplychain.purchase_order_items` poi
  ON po.id = poi.purchase_order_id
JOIN `wonder-dw-prod-brd.command_center.nodes` receiver
  ON po.receiver_node_id = receiver.facility_id
WHERE
  -- Delivered in last 7 days
  poi.received_quantity > 0
  AND poi.updated_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)

  -- But delivered after expected date
  AND DATE(DATETIME(TIMESTAMP(poi.updated_at), 'America/New_York')) > poi.delivery_date
GROUP BY
  receiver.facility_name,
  receiver.facility_type,
  poi.delivery_date,
  DATE(DATETIME(TIMESTAMP(poi.updated_at), 'America/New_York'))
HAVING
  DATE_DIFF(
    DATE(DATETIME(TIMESTAMP(poi.updated_at), 'America/New_York')),
    poi.delivery_date,
    DAY
  ) >= 1  -- At least 1 day late
ORDER BY
  days_late DESC,
  affected_quantity DESC;


-- ============================================================================
-- USAGE NOTES
-- ============================================================================
-- 1. Run with BigQuery CLI:
--    bq query --use_legacy_sql=false --format=pretty < order-analysis.sql
--
-- 2. DISH facility node ID:
--    - CK1 → DISH: Use strings 'CK1' and 'DISH'
--    - DISH → HDR: Use DISH UUID '46d337b4-7f61-4338-979a-5ee8d8e0071f'
--
-- 3. Status vs quantity-based logic:
--    - Status field may lag operational reality
--    - Derive states from quantities for accurate business logic
--    - Use status field for audit trails only
--
-- 4. Shipment join chain (cannot skip steps):
--    shipments → shipment_items → purchase_order_items → purchase_orders
--
-- 5. Timezone conversions for display:
--    DATETIME(TIMESTAMP(utc_column), 'America/New_York')
-- ============================================================================
