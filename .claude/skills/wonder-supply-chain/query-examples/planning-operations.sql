-- ============================================================================
-- PLANNING & OPERATIONS QUERIES
-- ============================================================================
-- Purpose: Analyze purchase plans, planning timing, and facility operations
-- Use Cases: Demand forecasting, planning system analysis, facility lookup
-- ============================================================================

-- ----------------------------------------------------------------------------
-- PURCHASE PLANS WITH FACILITY NAMES
-- ----------------------------------------------------------------------------
-- Purpose: Future purchase plans with human-readable facility names
-- Use Case: Upcoming dispatch planning, demand visibility
-- Gotchas:
--   - HDR orders stay as purchase_plans until ~5 min before place_at
--   - Use this query for future analysis (next 8 hours)
--   - For historical analysis, use purchase_orders instead

SELECT
  pp.id as plan_id,
  supplier.facility_name as supplier,
  receiver.facility_name as receiver,
  receiver.facility_type as receiver_type,
  DATETIME(TIMESTAMP(pp.place_at), 'America/New_York') as place_at_ny,
  DATETIME(TIMESTAMP(pp.plan_at), 'America/New_York') as plan_at_ny,
  pp.status,
  COUNT(DISTINCT ppi.id) as item_count,
  SUM(ppi.allocated_quantity) as total_allocated_qty
FROM `wonder-raw-prod.pg_batch_supplychain.purchase_plans` pp
JOIN `wonder-raw-prod.pg_batch_supplychain.purchase_plan_items` ppi
  ON pp.id = ppi.plan_id  -- CRITICAL: plan_id NOT purchase_plan_id
JOIN `wonder-dw-prod-brd.command_center.nodes` supplier
  ON pp.supplier_node_id = supplier.facility_id
JOIN `wonder-dw-prod-brd.command_center.nodes` receiver
  ON pp.receiver_node_id = receiver.facility_id
WHERE
  -- Future plans only (next 8 hours)
  pp.place_at BETWEEN CURRENT_TIMESTAMP()
    AND TIMESTAMP_ADD(CURRENT_TIMESTAMP(), INTERVAL 8 HOUR)

  -- Only plans with allocated quantities
  AND ppi.allocated_quantity > 0
GROUP BY
  pp.id,
  supplier.facility_name,
  receiver.facility_name,
  receiver.facility_type,
  pp.place_at,
  pp.plan_at,
  pp.status
ORDER BY
  pp.place_at ASC;


-- ----------------------------------------------------------------------------
-- PURCHASE PLAN TIMING ANALYSIS
-- ----------------------------------------------------------------------------
-- Purpose: Understand planning system behavior via plan_at vs place_at gaps
-- Use Case: Identify real-time vs scheduled planning patterns
-- Gotchas:
--   - Small gaps (~5 min): Real-time demand response
--   - Large gaps (hours): Scheduled/batched planning

SELECT
  supplier.facility_name as supplier,
  receiver.facility_name as receiver,
  receiver.facility_type,
  pp.plan_type,

  -- Timing metrics
  AVG(TIMESTAMP_DIFF(pp.place_at, pp.plan_at, MINUTE)) as avg_planning_lead_minutes,
  MIN(TIMESTAMP_DIFF(pp.place_at, pp.plan_at, MINUTE)) as min_planning_lead_minutes,
  MAX(TIMESTAMP_DIFF(pp.place_at, pp.plan_at, MINUTE)) as max_planning_lead_minutes,

  -- Volume metrics
  COUNT(DISTINCT pp.id) as plan_count,
  AVG(ppi.allocated_quantity) as avg_item_quantity,

  -- Planning pattern classification
  CASE
    WHEN AVG(TIMESTAMP_DIFF(pp.place_at, pp.plan_at, MINUTE)) <= 10 THEN 'REAL_TIME'
    WHEN AVG(TIMESTAMP_DIFF(pp.place_at, pp.plan_at, MINUTE)) <= 60 THEN 'NEAR_TERM'
    WHEN AVG(TIMESTAMP_DIFF(pp.place_at, pp.plan_at, MINUTE)) <= 240 THEN 'SCHEDULED'
    ELSE 'LONG_RANGE'
  END as planning_pattern

FROM `wonder-raw-prod.pg_batch_supplychain.purchase_plans` pp
JOIN `wonder-raw-prod.pg_batch_supplychain.purchase_plan_items` ppi
  ON pp.id = ppi.plan_id
JOIN `wonder-dw-prod-brd.command_center.nodes` supplier
  ON pp.supplier_node_id = supplier.facility_id
JOIN `wonder-dw-prod-brd.command_center.nodes` receiver
  ON pp.receiver_node_id = receiver.facility_id
WHERE
  -- Last 7 days of planning activity
  pp.plan_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
GROUP BY
  supplier.facility_name,
  receiver.facility_name,
  receiver.facility_type,
  pp.plan_type
ORDER BY
  plan_count DESC;


-- ----------------------------------------------------------------------------
-- FACILITY LOOKUP BY NAME OR TYPE
-- ----------------------------------------------------------------------------
-- Purpose: Find facility IDs for use in node_id queries
-- Use Case: Discover UUIDs for facilities, verify facility types
-- Gotchas:
--   - CK1 and DISH may use names directly in some contexts
--   - Always verify which format a specific query context needs

-- Find specific facilities by name
SELECT
  facility_id,
  facility_name,
  facility_type,
  address,
  shiphero_facility_id
FROM `wonder-dw-prod-brd.command_center.nodes`
WHERE facility_name IN ('DISH', 'CK1', 'GP709')
ORDER BY facility_name;

-- Find all facilities of a type
SELECT
  facility_id,
  facility_name,
  facility_type,
  address
FROM `wonder-dw-prod-brd.command_center.nodes`
WHERE facility_type = 'HDR'
ORDER BY facility_name;

-- Count facilities by type
SELECT
  facility_type,
  COUNT(*) as count
FROM `wonder-dw-prod-brd.command_center.nodes`
GROUP BY facility_type
ORDER BY count DESC;


-- ----------------------------------------------------------------------------
-- UPCOMING HDR DISPATCH SCHEDULE
-- ----------------------------------------------------------------------------
-- Purpose: Next 4 hours of HDR orders with SKU counts
-- Use Case: Dispatch planning, kitchen prep visibility
-- Gotchas:
--   - Query purchase_plans for future, not purchase_orders
--   - HDR orders convert to purchase_orders ~5 min before dispatch
--   - Group by place_at for dispatch wave analysis

SELECT
  DATETIME(TIMESTAMP(pp.place_at), 'America/New_York') as dispatch_time_ny,
  receiver.facility_name as hdr,
  COUNT(DISTINCT pp.id) as order_count,
  COUNT(DISTINCT ppi.supplier_sku) as unique_sku_count,
  SUM(ppi.allocated_quantity) as total_items
FROM `wonder-raw-prod.pg_batch_supplychain.purchase_plans` pp
JOIN `wonder-raw-prod.pg_batch_supplychain.purchase_plan_items` ppi
  ON pp.id = ppi.plan_id
JOIN `wonder-dw-prod-brd.command_center.nodes` supplier
  ON pp.supplier_node_id = supplier.facility_id
JOIN `wonder-dw-prod-brd.command_center.nodes` receiver
  ON pp.receiver_node_id = receiver.facility_id
WHERE
  -- Next 4 hours
  pp.place_at BETWEEN CURRENT_TIMESTAMP()
    AND TIMESTAMP_ADD(CURRENT_TIMESTAMP(), INTERVAL 4 HOUR)

  -- HDR receivers only
  AND receiver.facility_type = 'HDR'

  -- DISH supplier (use UUID for DISH → HDR)
  AND pp.supplier_node_id = '46d337b4-7f61-4338-979a-5ee8d8e0071f'
GROUP BY
  pp.place_at,
  receiver.facility_name
ORDER BY
  pp.place_at ASC,
  receiver.facility_name;


-- ----------------------------------------------------------------------------
-- PLANNING SYSTEM ACCURACY
-- ----------------------------------------------------------------------------
-- Purpose: Compare planned vs actual quantities to evaluate forecasting
-- Use Case: Planning system KPIs, forecast accuracy
-- Gotchas:
--   - Requires matching plans to executed orders via schedule_id or timing
--   - This is a simplified version; production may need more sophisticated matching

WITH plans AS (
  SELECT
    pp.id as plan_id,
    pp.schedule_id,
    pp.place_at,
    ppi.supplier_sku,
    SUM(ppi.allocated_quantity) as planned_qty
  FROM `wonder-raw-prod.pg_batch_supplychain.purchase_plans` pp
  JOIN `wonder-raw-prod.pg_batch_supplychain.purchase_plan_items` ppi
    ON pp.id = ppi.plan_id
  WHERE pp.place_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
    AND pp.place_at < CURRENT_TIMESTAMP()
  GROUP BY pp.id, pp.schedule_id, pp.place_at, ppi.supplier_sku
),
actuals AS (
  SELECT
    po.place_at,
    poi.supplier_sku,
    SUM(poi.placed_quantity) as actual_qty
  FROM `wonder-raw-prod.pg_batch_supplychain.purchase_orders` po
  JOIN `wonder-raw-prod.pg_batch_supplychain.purchase_order_items` poi
    ON po.id = poi.purchase_order_id
  WHERE po.place_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
  GROUP BY po.place_at, poi.supplier_sku
)
SELECT
  plans.supplier_sku,
  COUNT(*) as comparison_count,
  SUM(plans.planned_qty) as total_planned,
  SUM(actuals.actual_qty) as total_actual,
  SUM(actuals.actual_qty) - SUM(plans.planned_qty) as variance,
  ROUND(100.0 * (SUM(actuals.actual_qty) - SUM(plans.planned_qty)) / NULLIF(SUM(plans.planned_qty), 0), 1) as variance_pct
FROM plans
JOIN actuals
  ON plans.supplier_sku = actuals.supplier_sku
  AND TIMESTAMP_DIFF(plans.place_at, actuals.place_at, MINUTE) <= 10  -- Match within 10 min
GROUP BY plans.supplier_sku
HAVING SUM(plans.planned_qty) > 100  -- Meaningful volume only
ORDER BY ABS(SUM(actuals.actual_qty) - SUM(plans.planned_qty)) DESC;


-- ----------------------------------------------------------------------------
-- SKU DEMAND PATTERNS BY RECEIVER TYPE
-- ----------------------------------------------------------------------------
-- Purpose: Which SKUs are most frequently ordered by facility type
-- Use Case: Stocking recommendations, capacity planning

SELECT
  receiver.facility_type,
  ppi.supplier_sku,
  COUNT(DISTINCT pp.id) as order_count,
  COUNT(DISTINCT receiver.facility_id) as facility_count,
  SUM(ppi.allocated_quantity) as total_quantity,
  ROUND(AVG(ppi.allocated_quantity), 1) as avg_qty_per_order,
  MIN(pp.place_at) as first_order,
  MAX(pp.place_at) as last_order,
  DATE_DIFF(DATE(MAX(pp.place_at)), DATE(MIN(pp.place_at)), DAY) as days_span
FROM `wonder-raw-prod.pg_batch_supplychain.purchase_plans` pp
JOIN `wonder-raw-prod.pg_batch_supplychain.purchase_plan_items` ppi
  ON pp.id = ppi.plan_id
JOIN `wonder-dw-prod-brd.command_center.nodes` receiver
  ON pp.receiver_node_id = receiver.facility_id
WHERE
  -- Last 30 days
  pp.place_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
  AND ppi.allocated_quantity > 0
GROUP BY
  receiver.facility_type,
  ppi.supplier_sku
HAVING
  COUNT(DISTINCT pp.id) >= 10  -- Minimum 10 orders
ORDER BY
  receiver.facility_type,
  order_count DESC;


-- ----------------------------------------------------------------------------
-- BATCH PLANNING RUNS ANALYSIS
-- ----------------------------------------------------------------------------
-- Purpose: Analyze ladle planning system batch runs
-- Use Case: Planning system monitoring, batch size optimization
-- Gotchas:
--   - ladle_run_id groups related plans created in same batch
--   - Helps identify planning system issues or unusual patterns

SELECT
  pp.ladle_run_id,
  MIN(DATETIME(TIMESTAMP(pp.plan_at), 'America/New_York')) as batch_time_ny,
  COUNT(DISTINCT pp.id) as plans_in_batch,
  COUNT(DISTINCT pp.receiver_node_id) as unique_receivers,
  COUNT(DISTINCT ppi.supplier_sku) as unique_skus,
  SUM(ppi.allocated_quantity) as total_allocated_qty,
  STRING_AGG(DISTINCT pp.plan_type) as plan_types
FROM `wonder-raw-prod.pg_batch_supplychain.purchase_plans` pp
JOIN `wonder-raw-prod.pg_batch_supplychain.purchase_plan_items` ppi
  ON pp.id = ppi.plan_id
WHERE
  -- Last 24 hours of planning
  pp.plan_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
  AND pp.ladle_run_id IS NOT NULL
GROUP BY
  pp.ladle_run_id
ORDER BY
  MIN(pp.plan_at) DESC;


-- ============================================================================
-- USAGE NOTES
-- ============================================================================
-- 1. Run with BigQuery CLI:
--    bq query --use_legacy_sql=false --format=pretty < planning-operations.sql
--
-- 2. Purchase Plans vs Purchase Orders:
--    - Future analysis (next 8 hours): Use purchase_plans
--    - Historical analysis: Use purchase_orders
--    - HDR orders convert from plans → orders ~5 min before place_at
--
-- 3. Critical join field:
--    - purchase_plans.id = purchase_plan_items.plan_id
--    - NOT purchase_plan_id!
--
-- 4. Purchase plan items fields:
--    - Only has supplier_sku (no wonder_sku)
--    - Use allocated_quantity (not placed_quantity)
--
-- 5. Timing analysis:
--    - Small plan_at → place_at gap: Real-time demand
--    - Large gap: Scheduled/batched planning
--
-- 6. Facility lookups:
--    - Always verify node ID format (UUID vs name string)
--    - CK1/DISH may use names in some contexts
-- ============================================================================
