# Common Pitfalls and Gotchas - Wonder Orders

Critical mistakes to avoid when working with Wonder order and sales data.

---

## Customer Survey Ratings - Use 1-5 Scale, Not 0-10

All customer ratings (`raw_taste_rating`, `raw_nps`, etc.) use a **1-5 scale**, not 0-10.

### ❌ Wrong: Treating as 0-10 scale
```sql
-- WRONG: 5/5 is "excellent", not "50%"
COUNTIF(raw_taste_rating >= 7)  -- Nothing is >5!
COUNTIF(raw_nps >= 9)            -- Max is 5
```

### ✅ Correct: Using 1-5 scale
```sql
-- CORRECT: 5=excellent, 4=good, 3=neutral, 1-2=poor
COUNTIF(raw_taste_rating >= 4)   -- Positive reviews
COUNTIF(raw_nps = 5)              -- Promoters
COUNTIF(raw_nps = 4)              -- Passives
COUNTIF(raw_nps <= 3)             -- Detractors
```

**Also**: Use `raw_*` fields (current), not `div_2_*` fields (deprecated legacy).

---

## Status Filtering - Include COMPLETE Orders Only for Revenue

Filter to completed orders when analyzing revenue and sales.

### ❌ Wrong: Including all statuses
```sql
-- WRONG - includes canceled and failed orders
SELECT SUM(total_amount) as revenue
FROM `wonder-dw-prod-brd.orders.hdr_orders`
WHERE service_date_et >= '2025-10-01';
```

### ✅ Correct: Filter to COMPLETE status
```sql
-- CORRECT - only completed orders
SELECT SUM(total_amount) as revenue
FROM `wonder-dw-prod-brd.orders.hdr_orders`
WHERE service_date_et >= '2025-10-01'
  AND order_status = 'COMPLETE';
```

**Why This Matters**: Including PAYMENT_FAILED and CANCELED orders inflates order counts and includes revenue that was never collected. The status value is `COMPLETE` (not COMPLETED or DELIVERED).

**Pattern**: Always add `WHERE order_status = 'COMPLETE'` for revenue/sales queries.

---

## Timezone Handling - Convert UTC to Eastern Time

All timestamps are stored in UTC but business operates in Eastern Time.

### ❌ Wrong: Using UTC directly for time-of-day analysis
```sql
-- WRONG - shows UTC hours (off by 4-5 hours)
SELECT
  EXTRACT(HOUR FROM order_placed_date_utc) as hour,
  COUNT(*) as orders
FROM `wonder-dw-prod-brd.orders.hdr_orders`
GROUP BY hour;
```

### ✅ Correct: Convert to Eastern Time
```sql
-- CORRECT - converts to ET for accurate time-of-day
SELECT
  EXTRACT(HOUR FROM DATETIME(order_placed_date_utc, 'America/New_York')) as hour_et,
  COUNT(*) as orders
FROM `wonder-dw-prod-brd.orders.hdr_orders`
GROUP BY hour_et;
```

**Why This Matters**: Without timezone conversion, 7 PM ET orders appear as midnight UTC, making time-of-day patterns meaningless.

**Pattern**: Use `DATETIME(timestamp_field, 'America/New_York')` for ET conversion.

---

## Date Filtering - Use service_date_et for Daily Aggregations

Use the pre-calculated ET date field for daily rollups.

### ❌ Wrong: Converting timestamp for date filtering
```sql
-- SLOWER - converts timestamp to date for every row
SELECT *
FROM `wonder-dw-prod-brd.orders.hdr_orders`
WHERE DATE(order_placed_date_utc) = '2025-11-01';
```

### ✅ Correct: Use service_date_et field
```sql
-- FASTER - uses indexed date field
SELECT *
FROM `wonder-dw-prod-brd.orders.hdr_orders`
WHERE service_date_et = '2025-11-01';
```

**Why This Matters**: `service_date_et` is already in ET and optimized for date filtering. Converting timestamps is slower and uses more resources.

**Pattern**: Use `service_date_et` for date-based WHERE clauses and GROUP BY.

---

## Counting Orders with Item Joins - Use DISTINCT

When joining to order_items, remember each order appears multiple times.

### ❌ Wrong: Counting rows after join
```sql
-- WRONG - counts items, not orders (will overcount by 3x on average)
SELECT COUNT(*) as order_count
FROM `wonder-dw-prod-brd.orders.hdr_orders` o
JOIN `wonder-dw-prod-brd.orders.order_items` oi
  ON o.order_id = oi.order_id
WHERE o.order_status = 'COMPLETE';
```

### ✅ Correct: Count distinct order IDs
```sql
-- CORRECT - counts unique orders
SELECT COUNT(DISTINCT o.order_id) as order_count
FROM `wonder-dw-prod-brd.orders.hdr_orders` o
JOIN `wonder-dw-prod-brd.orders.order_items` oi
  ON o.order_id = oi.order_id
WHERE o.order_status = 'COMPLETE';
```

**Why This Matters**: Each order has multiple items (avg ~3), so joining creates one row per item. Without DISTINCT, you count items instead of orders.

**Pattern**: Always use `COUNT(DISTINCT order_id)` when counting orders after joining to items.

---

## Summing Order Totals with Item Joins - Avoid Double Counting

Don't sum order-level fields after joining to items.

### ❌ Wrong: Summing order total after item join
```sql
-- WRONG - sums order total once per item (3x overcount on average)
SELECT SUM(o.total_amount) as revenue
FROM `wonder-dw-prod-brd.orders.hdr_orders` o
JOIN `wonder-dw-prod-brd.orders.order_items` oi
  ON o.order_id = oi.order_id;
```

### ✅ Correct: Sum item totals OR aggregate orders separately
```sql
-- OPTION 1: Sum at item level
SELECT SUM(oi.total_amount) as revenue
FROM `wonder-dw-prod-brd.orders.hdr_orders` o
JOIN `wonder-dw-prod-brd.orders.order_items` oi
  ON o.order_id = oi.order_id
WHERE o.order_status = 'COMPLETE';

-- OPTION 2: Aggregate orders without join (preferred for order-level metrics)
SELECT SUM(total_amount) as revenue
FROM `wonder-dw-prod-brd.orders.hdr_orders`
WHERE order_status = 'COMPLETE';
```

**Why This Matters**: Joining to items multiplies each order row by the number of items. Summing order-level fields counts each order N times (where N = number of items). This can inflate revenue by 3x or more.

**Pattern**: Either sum item-level fields, or avoid the join entirely if you only need order-level aggregates.

---

## NULL Handling in Timing Fields - Filter or Handle NULLs

Many timing fields are NULL for certain order types or incomplete orders.

### ❌ Wrong: Ignoring NULL values in metrics
```sql
-- MISLEADING - reports on all orders but only some have SLA data
SELECT
  hdr_id,
  COUNT(*) as total_orders,
  AVG(delivery_sla_difference) as avg_sla_diff
FROM `wonder-dw-prod-brd.orders.hdr_orders`
WHERE order_status = 'COMPLETE'
GROUP BY hdr_id;
```

### ✅ Correct: Explicitly filter NULL values
```sql
-- CLEAR - shows how many orders have timing data
SELECT
  hdr_id,
  COUNT(*) as orders_with_sla_data,
  AVG(delivery_sla_difference) as avg_sla_diff
FROM `wonder-dw-prod-brd.orders.hdr_orders`
WHERE order_status = 'COMPLETE'
  AND delivery_sla_difference IS NOT NULL
GROUP BY hdr_id;
```

**Why This Matters**: Fields like `delivery_sla_difference`, `actual_o2e_mins`, and kitchen timing metrics are NULL for pickup orders, incomplete orders, or orders that skipped certain stages. The order count will be misleading if it includes orders without the metric.

**Pattern**: Add `IS NOT NULL` filters for timing metrics, especially: `delivery_sla_difference`, `actual_o2e_mins`, `actual_queue_mins`, `actual_cook_duration_mins`.

---

## Delivery vs Pickup Filtering - Filter by dining_option

Don't calculate delivery-specific metrics on pickup orders.

### ❌ Wrong: Delivery metrics without filtering dining option
```sql
-- WRONG - includes pickup orders which have NULL delivery metrics
SELECT
  COUNT(*) as orders,
  AVG(delivery_sla_difference) as avg_delivery_sla,
  AVG(actual_delivery_duration_mins) as avg_delivery_time
FROM `wonder-dw-prod-brd.orders.hdr_orders`
WHERE order_status = 'COMPLETE';
```

### ✅ Correct: Filter to DELIVERY orders only
```sql
-- CORRECT - only delivery orders
SELECT
  COUNT(*) as delivery_orders,
  AVG(delivery_sla_difference) as avg_delivery_sla,
  AVG(actual_delivery_duration_mins) as avg_delivery_time
FROM `wonder-dw-prod-brd.orders.hdr_orders`
WHERE order_status = 'COMPLETE'
  AND dining_option = 'DELIVERY'
  AND delivery_sla_difference IS NOT NULL;
```

**Why This Matters**: Pickup orders (~35% of volume) don't have delivery SLA, transit time, or courier metrics. Including them makes the count misleading and skews averages.

**Pattern**: Add `WHERE dining_option = 'DELIVERY'` for delivery-specific metrics, or `dining_option = 'PICKUP'` for pickup metrics.

---

## Restaurant Terminology - HDR vs Restaurant Instance vs Restaurant Brand

Understand the three-level hierarchy in Wonder's restaurant data model.

### ❌ Wrong: Confusing restaurant_id with brand
```sql
-- WRONG - returns restaurant INSTANCES (e.g., "Limesalt Fishtown", "Limesalt Yardley" separately)
-- This is NOT brand performance, it's instance performance
SELECT
  r.restaurant_name,
  r.chef_owner,
  COUNT(DISTINCT oi.order_id) as orders,
  ROUND(SUM(oi.total_amount), 2) as revenue
FROM `wonder-dw-prod-brd.orders.order_items` oi
JOIN `wonder-dw-prod-brd.orders.hdr_orders` o
  ON oi.order_id = o.order_id
JOIN `wonder-dw-prod-brd.dw.dim_restaurants` r
  ON oi.restaurant_id = r.restaurant_id
WHERE o.order_status = 'COMPLETE'
GROUP BY r.restaurant_name, r.chef_owner
ORDER BY revenue DESC;
-- This shows "Limesalt Fishtown" and "Limesalt Yardley" as separate entries
```

### ✅ Correct: Query restaurant BRANDS from dim_restaurant_brands
```sql
-- CORRECT - returns true brand performance aggregated across all locations
SELECT
  rb.restaurant_brand_name,
  COUNT(DISTINCT oi.order_id) as orders,
  ROUND(SUM(oi.total_amount), 2) as revenue
FROM `wonder-dw-prod-brd.orders.order_items` oi
JOIN `wonder-dw-prod-brd.orders.hdr_orders` o
  ON oi.order_id = o.order_id
JOIN `wonder-dw-prod-brd.dw.dim_restaurants` r
  ON oi.restaurant_id = r.restaurant_id
JOIN `wonder-dw-prod-brd.dw.dim_restaurant_brands` rb
  ON r.restaurant_brand_id = rb.restaurant_brand_id
WHERE o.order_status = 'COMPLETE'
GROUP BY rb.restaurant_brand_name
ORDER BY revenue DESC;
-- This properly shows "Limesalt" as one brand across all locations
```

**Why This Matters**:
- **HDR (hdr_id)** = Physical location that houses 20-30 restaurant brands
- **Restaurant Instance (restaurant_id)** = Specific brand at specific HDR (e.g., "Limesalt Fishtown")
- **Restaurant Brand (restaurant_brand_id)** = Actual brand concept across all locations (e.g., "Limesalt")
- Order headers (`hdr_orders`) contain HDR location info
- Order items (`order_items`) contain restaurant instance info
- To analyze true brand performance, you MUST join to `dim_restaurant_brands`

**Critical Schema Quirk**: `restaurant_id` is NOT a brand ID - it's an instance ID (brand + location).

**Key Insight**: The term "restaurant" is overloaded in Wonder's system:
- When users ask about "restaurants" or "brands" or "concepts", they usually mean brands
- `restaurant_id` refers to instances, NOT brands
- Always join through to `dim_restaurant_brands` for true brand analysis

**Pattern**: For brand analysis, always join: `order_items` → `dim_restaurants` → `dim_restaurant_brands`.

---

## Repeated Fields - Unnest restaurant_ids Array

The restaurant_ids field is an array and needs unnesting to query individual restaurants.

### ❌ Wrong: Treating array as single value
```sql
-- WRONG - can't filter/join on array directly
SELECT order_id, restaurant_ids
FROM `wonder-dw-prod-brd.orders.hdr_orders`
WHERE restaurant_ids = '73b8e56f-8f8d-45a1-a48f-2b032f0789f8';
```

### ✅ Correct: Unnest array to query individual values
```sql
-- CORRECT - unnest the array
SELECT o.order_id, restaurant_id
FROM `wonder-dw-prod-brd.orders.hdr_orders` o,
UNNEST(o.restaurant_ids) as restaurant_id
WHERE restaurant_id = '73b8e56f-8f8d-45a1-a48f-2b032f0789f8';
```

**Why This Matters**: `restaurant_ids` is a repeated field (array) containing all restaurants/brands in a multi-restaurant order. You must unnest it to filter or join on individual values.

**Pattern**: Use `UNNEST(restaurant_ids) as restaurant_id` when you need to work with individual restaurants within an order.

---

## Same Store Sales - Match Stores Across Periods

When comparing time periods, ensure same HDRs exist in both periods.

### ❌ Wrong: Comparing all stores without matching
```sql
-- WRONG - includes new stores that opened mid-period
SELECT
  'Current Period' as period,
  SUM(total_amount) as revenue
FROM `wonder-dw-prod-brd.orders.hdr_orders`
WHERE service_date_et BETWEEN '2025-10-01' AND '2025-10-31'
  AND order_status = 'COMPLETE'
UNION ALL
SELECT
  'Prior Period' as period,
  SUM(total_amount) as revenue
FROM `wonder-dw-prod-brd.orders.hdr_orders`
WHERE service_date_et BETWEEN '2025-09-01' AND '2025-09-30'
  AND order_status = 'COMPLETE';
```

### ✅ Correct: Only compare stores present in both periods
```sql
-- CORRECT - only same stores across both periods
WITH stores_both_periods AS (
  SELECT DISTINCT hdr_id
  FROM `wonder-dw-prod-brd.orders.hdr_orders`
  WHERE service_date_et BETWEEN '2025-09-01' AND '2025-10-31'
    AND order_status = 'COMPLETE'
  GROUP BY hdr_id
  HAVING
    COUNTIF(service_date_et >= '2025-10-01') > 0  -- Has orders in current period
    AND COUNTIF(service_date_et < '2025-10-01') > 0  -- Has orders in prior period
)
SELECT
  'Current Period' as period,
  SUM(total_amount) as revenue
FROM `wonder-dw-prod-brd.orders.hdr_orders`
WHERE service_date_et BETWEEN '2025-10-01' AND '2025-10-31'
  AND order_status = 'COMPLETE'
  AND hdr_id IN (SELECT hdr_id FROM stores_both_periods)
UNION ALL
SELECT
  'Prior Period' as period,
  SUM(total_amount) as revenue
FROM `wonder-dw-prod-brd.orders.hdr_orders`
WHERE service_date_et BETWEEN '2025-09-01' AND '2025-09-30'
  AND order_status = 'COMPLETE'
  AND hdr_id IN (SELECT hdr_id FROM stores_both_periods);
```

**Why This Matters**: New store openings or closures skew period-over-period comparisons. Same-store sales (a key business metric) should only include stores operating in both periods to show true growth.

**Pattern**: Filter to HDRs that have at least one order in both comparison periods.

---

## Marketplace Orders - Different Fee Structures

Orders from marketplaces have different fee allocations than Wonder direct orders.

### ❌ Wrong: Assuming consistent fee structure across all channels
```sql
-- MISLEADING - service_fee and hospitality_fee vary by channel
SELECT
  AVG(service_fee) as avg_service_fee,
  AVG(hospitality_fee) as avg_hospitality_fee
FROM `wonder-dw-prod-brd.orders.hdr_orders`
WHERE order_status = 'COMPLETE';
```

### ✅ Correct: Segment by channel when analyzing fees
```sql
-- CORRECT - shows fee differences by channel
SELECT
  order_channel,
  COUNT(*) as orders,
  AVG(service_fee) as avg_service_fee,
  AVG(hospitality_fee) as avg_hospitality_fee,
  AVG(delivery_fee) as avg_delivery_fee
FROM `wonder-dw-prod-brd.orders.hdr_orders`
WHERE order_status = 'COMPLETE'
GROUP BY order_channel;
```

**Why This Matters**: Marketplace orders (GRUB_HUB, DOOR_DASH, UBER_EATS) may have NULL or different values for Wonder-specific fees. Commission structures also differ. Aggregating across all channels without segmentation hides important differences.

**Pattern**: Group by `order_channel` when analyzing fees, commissions, or comparing direct vs marketplace performance.

---

## Summary Checklist

Before running order/sales queries:

**Terminology & Data Model**:
- [ ] Clarify if "restaurant" means HDR location (hdr_id) or brand/concept (restaurant_id)
- [ ] For brand analysis, join order_items to dim_restaurants (not just hdr_orders)
- [ ] Extract base concept name when aggregating brands across locations

**Business Logic**:
- [ ] Filter to `order_status = 'COMPLETE'` for revenue (not CANCELED/PAYMENT_FAILED)
- [ ] Use `dining_option = 'DELIVERY'` filter for delivery-specific metrics
- [ ] For same-store sales, filter to HDRs present in both periods
- [ ] Segment by `order_channel` when analyzing fees or commissions

**Data Quality**:
- [ ] Add `IS NOT NULL` filters for timing metrics (delivery_sla_difference, actual_o2e_mins)
- [ ] Handle repeated fields with UNNEST (restaurant_ids)
- [ ] Check which orders have complete data for your metric

**Performance & Accuracy**:
- [ ] Use `service_date_et` for date filtering (not converted timestamps)
- [ ] Convert UTC to ET for time-of-day: `DATETIME(field, 'America/New_York')`
- [ ] Use `COUNT(DISTINCT order_id)` when joining to order_items
- [ ] Don't sum order-level fields after joining to items (sum item fields instead)

---

## Tip Analysis - Filter by Order Business Type

Tip analysis requires filtering to direct Wonder orders to avoid misleading 0% rates from marketplace and B2B orders.

### ❌ Wrong: Not filtering by order_business_type
```sql
-- WRONG - includes 3P marketplace & Wonder Spot (B2B) orders with 0% tips
SELECT
  COUNTIF(tip_amount > 0) / COUNT(*) * 100 as tip_rate_pct
FROM `wonder-dw-prod-brd.orders.hdr_orders`
WHERE service_date_et >= '2025-10-01'
  AND order_status = 'COMPLETE'
  AND dining_option = 'DELIVERY';
-- Result: ~44% tip rate (misleading)
```

### ✅ Correct: Filter to direct Wonder orders only
```sql
-- CORRECT - excludes marketplace & Wonder Spot orders
SELECT
  COUNTIF(tip_amount > 0) / COUNT(*) * 100 as tip_rate_pct
FROM `wonder-dw-prod-brd.orders.hdr_orders`
WHERE service_date_et >= '2025-10-01'
  AND order_status = 'COMPLETE'
  AND dining_option = 'DELIVERY'
  AND order_business_type IN ('WONDER_HDR', 'WONDER_LOCAL');
-- Result: ~91% tip rate (accurate)
```

**Why This Matters**: 3P marketplace orders (DoorDash, etc.) and Wonder Spot (B2B) orders show 0% tips because tips flow through external platforms or are corporate-billed. Not filtering makes tip rates appear 2x lower than reality.

**Note**: The `tip_type` field (pre-tip vs post-tip) is not populated and should not be used.
