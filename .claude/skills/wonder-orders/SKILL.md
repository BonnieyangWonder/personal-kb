---
name: wonder-orders
description: Expert knowledge of Wonder's order and sales data including hdr_orders, order_items, and customer survey tables. Use when analyzing sales trends, order volume, channel performance, on-time delivery rates, order-to-eat times, menu item sales, revenue metrics, and customer satisfaction across Wonder HDRs.
allowed-tools: Read, Grep, Glob
---

# Wonder Orders & Sales Expert

This skill provides expertise in analyzing Wonder's order and sales data from the `wonder-dw-prod-brd.orders` dataset. It covers the complete order lifecycle from placement through delivery, including financial metrics, timing performance, and item-level details.

## Customer Orders vs Supply Chain Orders - IMPORTANT

This skill covers **customer orders** (people ordering food). If the user is asking about **supply chain orders** (inventory replenishment from DISH to HDRs), use the **wonder-supply-chain** skill instead.

**Ambiguous requests - clarify before querying:**
- "Orders to HDRs" → Could mean customer orders OR supply chain replenishment
- "When did orders start?" → Customer demand OR inventory wave timing?
- "Order placement timing" → Which type of order?

Ask: *"Are you asking about customer orders (people ordering food via app/web) or supply chain orders (inventory replenishment from DISH to HDRs)?"*

## What This Skill Provides

- **Sales Analysis** - Revenue trends, same-store sales, average order value across time periods and HDRs
- **Channel Performance** - Compare APP, GRUB_HUB, DOOR_DASH, UBER_EATS, WEB, and IN_PERSON channels
- **Order Timing Metrics** - On-time delivery rate, order-to-eat (O2E) time, SLA compliance
- **Item-Level Analysis** - Top selling items, category performance, pricing analysis
- **Operational Metrics** - Order volume, status distribution, cooking/bagging/delivery timing
- **Customer Behavior** - Dining options (delivery vs pickup), order patterns, tip analysis
- **Customer Satisfaction** - NPS scores and written reviews for menu items

## When to Use This Skill

Use this skill when you need to:
- Analyze daily, weekly, or monthly sales trends
- Calculate same-store sales comparisons across time periods
- Measure on-time delivery performance and O2E metrics
- Compare performance across different order channels (APP vs marketplaces)
- Identify top selling menu items or categories
- Calculate average order values or revenue by HDR
- Analyze order status distribution or cancellation rates
- Understand kitchen timing metrics (queue, cook, bag, deliver)
- Track order volume and capacity by restaurant
- Analyze customer satisfaction (NPS) or get written reviews

## Core Concepts

### Database Location
- **BigQuery Dataset**: `wonder-dw-prod-brd.orders`
- **Primary Tables**: `hdr_orders`, `order_items`
- **Customer Feedback Tables**: `customer_survey_responses`, `customer_survey_dish_responses`
- **Supporting Tables**:
  - `wonder-dw-prod-brd.dw.dim_restaurants` (restaurant instances - brand at specific HDR)
  - `wonder-dw-prod-brd.dw.dim_restaurant_brands` (restaurant brands - aggregated across all HDRs)
- **Access**: Via bq CLI or BigQuery Console
- **Data Warehouse**: Transformed data from operational systems

### Terminology: HDR vs Restaurant Concept vs Brand

**IMPORTANT**: The term "restaurant" is overloaded in Wonder's data model:

- **HDR (High Density Restaurant)** - A physical brick-and-mortar location that serves multiple restaurant concepts (20-30 brands per location). Referenced by `hdr_id` in `hdr_orders`.
- **Restaurant Instance** - A specific brand at a specific HDR location (e.g., "Limesalt Fishtown", "Limesalt Yardley"). Referenced by `restaurant_id` in `order_items`. **This is NOT the same as a brand concept.**
- **Restaurant Brand/Concept** - The actual brand across all locations (e.g., "Limesalt", "Bobby Flay Steak"). Referenced by `restaurant_brand_id` in `dim_restaurants` and `dim_restaurant_brands`.

One customer order can include items from multiple restaurant instances, all prepared in the same HDR.

**Example**: Order at "Yardley HDR" containing a burger from "Fred's Meat & Bread" (restaurant instance at Yardley) and a salad from "Royal Greens" (restaurant instance at Yardley).

**Critical Schema Quirk**: `restaurant_id` refers to a brand instance at a specific HDR, NOT to the brand itself. To analyze true brand performance across all locations, you must join through to `dim_restaurant_brands`.

### Key Entity Relationships

```
hdr_orders (1) → (many) order_items
  ↓ order_id = order_id

hdr_orders.hdr_id → HDR location (physical building)
hdr_orders.user_id → Customer
order_items.restaurant_id → Restaurant instance at specific HDR (e.g., "Limesalt Fishtown")
order_items.menu_item_id → Menu item

dim_restaurants:
  restaurant_id → Restaurant instance ID (Limesalt at Fishtown)
  restaurant_name → Display name (includes location, e.g., "Limesalt Fishtown")
  restaurant_brand_id → Foreign key to dim_restaurant_brands

dim_restaurant_brands:
  restaurant_brand_id → Brand/concept ID (Limesalt across all locations)
  restaurant_brand_name → Brand name (e.g., "Limesalt", "Bobby Flay Steak")
```

### Order Lifecycle

Orders flow through these statuses:
1. **PENDING_PAYMENT** - Order created, awaiting payment
2. **PAID** - Payment received, awaiting assignment
3. **ASSIGNED** - Assigned to kitchen
4. **IN_COOKING** - Being prepared
5. **READY_FOR_PICKUP** - Awaiting courier pickup
6. **DELIVERING** - In transit to customer
7. **COMPLETE** - Successfully delivered/picked up

Failed states: **PAYMENT_FAILED**, **CANCELED**

### Order Channels

- **APP** - Wonder mobile app (highest volume)
- **WEB** - Wonder website
- **GRUB_HUB** - GrubHub marketplace
- **DOOR_DASH** - DoorDash marketplace
- **UBER_EATS** - Uber Eats marketplace
- **IN_PERSON** - In-person at HDR

### Dining Options

- **DELIVERY** - Courier delivery to customer (~65% of orders)
- **PICKUP** - Customer pickup at HDR (~35% of orders)

### Timing Metrics

Key fields for performance analysis:
- **actual_o2e_mins** - Actual order-to-eat time (order placed → delivered)
- **estimated_o2e_mins** - Estimated O2E at order placement
- **delivery_sla_difference** - Minutes difference from promised delivery time (negative = early)
- **actual_queue_mins** - Time order waited before cooking started
- **actual_cook_duration_mins** - Time spent cooking
- **actual_packaging_bagging_mins** - Time spent bagging/packaging
- **actual_delivery_duration_mins** - Time from pickup to delivery

### Timezone Handling

All timestamps stored in UTC, but business operates in America/New_York:
- **order_placed_date_utc** - TIMESTAMP in UTC
- **service_date_et** - DATE in Eastern Time (use for daily aggregations)

Convert UTC to ET for time-of-day analysis:
```sql
DATETIME(order_placed_date_utc, 'America/New_York') as order_time_et
```

## Query Patterns

### Daily Sales by HDR

```sql
-- Calculate daily sales with order metrics
SELECT
  service_date_et,
  hdr_id,
  COUNT(DISTINCT order_id) as total_orders,
  COUNT(DISTINCT user_id) as unique_customers,
  ROUND(SUM(subtotal), 2) as total_subtotal,
  ROUND(SUM(tax), 2) as total_tax,
  ROUND(SUM(total_amount), 2) as total_revenue,
  ROUND(AVG(total_amount), 2) as avg_order_value
FROM `wonder-dw-prod-brd.orders.hdr_orders`
WHERE service_date_et >= '2025-10-01'
  AND order_status = 'COMPLETE'
GROUP BY service_date_et, hdr_id
ORDER BY service_date_et DESC, total_revenue DESC;
```

### Same Store Sales Comparison

```sql
-- Compare sales for same HDRs across two periods
WITH current_period AS (
  SELECT
    hdr_id,
    SUM(total_amount) as current_revenue,
    COUNT(DISTINCT order_id) as current_orders
  FROM `wonder-dw-prod-brd.orders.hdr_orders`
  WHERE service_date_et BETWEEN '2025-10-01' AND '2025-10-31'
    AND order_status = 'COMPLETE'
  GROUP BY hdr_id
),
prior_period AS (
  SELECT
    hdr_id,
    SUM(total_amount) as prior_revenue,
    COUNT(DISTINCT order_id) as prior_orders
  FROM `wonder-dw-prod-brd.orders.hdr_orders`
  WHERE service_date_et BETWEEN '2025-09-01' AND '2025-09-30'
    AND order_status = 'COMPLETE'
  GROUP BY hdr_id
)
SELECT
  c.hdr_id,
  c.current_revenue,
  p.prior_revenue,
  ROUND((c.current_revenue - p.prior_revenue) / p.prior_revenue * 100, 2) as revenue_growth_pct,
  c.current_orders,
  p.prior_orders,
  ROUND((c.current_orders - p.prior_orders) / CAST(p.prior_orders AS FLOAT64) * 100, 2) as order_growth_pct
FROM current_period c
JOIN prior_period p ON c.hdr_id = p.hdr_id
ORDER BY revenue_growth_pct DESC;
```

### Channel Performance Analysis

```sql
-- Compare order volume and metrics across channels
SELECT
  order_channel,
  dining_option,
  COUNT(DISTINCT order_id) as total_orders,
  ROUND(AVG(total_amount), 2) as avg_order_value,
  ROUND(SUM(total_amount), 2) as total_revenue,
  ROUND(AVG(actual_o2e_mins), 2) as avg_o2e_mins,
  ROUND(AVG(tip_amount), 2) as avg_tip
FROM `wonder-dw-prod-brd.orders.hdr_orders`
WHERE service_date_et >= '2025-10-01'
  AND order_status = 'COMPLETE'
GROUP BY order_channel, dining_option
ORDER BY total_orders DESC;
```

### Tip Analysis (Delivery Orders)

```sql
-- Analyze tipping behavior - MUST filter to direct Wonder orders only
SELECT
  COUNT(*) as total_delivery_orders,
  COUNTIF(tip_amount > 0) as orders_with_tips,
  ROUND(COUNTIF(tip_amount > 0) / COUNT(*) * 100, 2) as tip_rate_pct,
  ROUND(AVG(CASE WHEN tip_amount > 0 THEN tip_amount END), 2) as avg_tip_dollars,
  ROUND(AVG(CASE WHEN tip_amount > 0 THEN tip_amount / NULLIF(subtotal, 0) * 100 END), 2) as avg_tip_pct
FROM `wonder-dw-prod-brd.orders.hdr_orders`
WHERE service_date_et >= '2025-10-01'
  AND order_status = 'COMPLETE'
  AND dining_option = 'DELIVERY'
  AND order_business_type IN ('WONDER_HDR', 'WONDER_LOCAL');  -- Critical: excludes 3P & Wonder Spot
```

**Why filter order_business_type?** 3P marketplace orders (DoorDash, etc.) and Wonder Spot (B2B) show 0% tips in our system because tips flow through external platforms. Direct Wonder orders have ~91% tip rate.

### On-Time Delivery Rate

```sql
-- Calculate on-time delivery percentage
SELECT
  service_date_et,
  COUNT(DISTINCT order_id) as total_deliveries,
  COUNTIF(delivery_sla_difference <= 0) as on_time_deliveries,
  ROUND(COUNTIF(delivery_sla_difference <= 0) / COUNT(DISTINCT order_id) * 100, 2) as on_time_rate_pct,
  ROUND(AVG(delivery_sla_difference), 2) as avg_sla_diff_mins
FROM `wonder-dw-prod-brd.orders.hdr_orders`
WHERE service_date_et >= '2025-10-01'
  AND order_status = 'COMPLETE'
  AND dining_option = 'DELIVERY'
  AND delivery_sla_difference IS NOT NULL
GROUP BY service_date_et
ORDER BY service_date_et DESC;
```

### Order-to-Eat Time Analysis

```sql
-- Analyze O2E performance with breakdown
SELECT
  service_date_et,
  hdr_id,
  COUNT(DISTINCT order_id) as total_orders,
  ROUND(AVG(estimated_o2e_mins), 2) as avg_estimated_o2e,
  ROUND(AVG(actual_o2e_mins), 2) as avg_actual_o2e,
  ROUND(AVG(actual_o2e_mins - estimated_o2e_mins), 2) as avg_o2e_error,
  ROUND(AVG(actual_queue_mins), 2) as avg_queue_mins,
  ROUND(AVG(actual_cook_duration_mins), 2) as avg_cook_mins,
  ROUND(AVG(actual_delivery_duration_mins), 2) as avg_delivery_mins
FROM `wonder-dw-prod-brd.orders.hdr_orders`
WHERE service_date_et >= '2025-10-01'
  AND order_status = 'COMPLETE'
  AND actual_o2e_mins IS NOT NULL
GROUP BY service_date_et, hdr_id
ORDER BY service_date_et DESC, avg_actual_o2e DESC;
```

### Top Selling Menu Items

```sql
-- Find best selling items with revenue
SELECT
  oi.menu_item_name,
  oi.menu_item_category_name,
  COUNT(DISTINCT oi.order_id) as orders_with_item,
  SUM(oi.order_quantity) as total_quantity_sold,
  ROUND(AVG(oi.unit_price), 2) as avg_unit_price,
  ROUND(SUM(oi.total_amount), 2) as total_item_revenue
FROM `wonder-dw-prod-brd.orders.order_items` oi
JOIN `wonder-dw-prod-brd.orders.hdr_orders` o
  ON oi.order_id = o.order_id
WHERE o.service_date_et >= '2025-10-01'
  AND o.order_status = 'COMPLETE'
GROUP BY oi.menu_item_name, oi.menu_item_category_name
ORDER BY total_quantity_sold DESC
LIMIT 20;
```

### Top Selling Restaurant Instances (by Location)

```sql
-- Find top performing restaurant instances at specific HDR locations
SELECT
  r.restaurant_name,
  r.chef_owner,
  r.primary_cuisine,
  COUNT(DISTINCT oi.order_id) as orders_with_items,
  SUM(oi.order_quantity) as total_items_sold,
  ROUND(SUM(oi.total_amount), 2) as total_revenue,
  ROUND(AVG(oi.total_amount), 2) as avg_item_revenue
FROM `wonder-dw-prod-brd.orders.order_items` oi
JOIN `wonder-dw-prod-brd.orders.hdr_orders` o
  ON oi.order_id = o.order_id
JOIN `wonder-dw-prod-brd.dw.dim_restaurants` r
  ON oi.restaurant_id = r.restaurant_id
WHERE o.service_date_et >= '2025-10-01'
  AND o.order_status = 'COMPLETE'
GROUP BY r.restaurant_name, r.chef_owner, r.primary_cuisine
ORDER BY total_revenue DESC
LIMIT 20;
-- Note: This shows individual instances like "Limesalt Fishtown" and "Limesalt Yardley" separately
```

### Top Selling Restaurant Brands (Aggregated Across All Locations)

```sql
-- Find top performing brands aggregated across all HDR locations
-- This is the correct way to analyze brand/concept performance
SELECT
  rb.restaurant_brand_name,
  COUNT(DISTINCT oi.order_id) as orders_with_items,
  SUM(oi.order_quantity) as total_items_sold,
  ROUND(SUM(oi.total_amount), 2) as gross_order_value,
  ROUND(AVG(oi.total_amount), 2) as avg_item_revenue
FROM `wonder-dw-prod-brd.orders.order_items` oi
JOIN `wonder-dw-prod-brd.orders.hdr_orders` o
  ON oi.order_id = o.order_id
JOIN `wonder-dw-prod-brd.dw.dim_restaurants` r
  ON oi.restaurant_id = r.restaurant_id
JOIN `wonder-dw-prod-brd.dw.dim_restaurant_brands` rb
  ON r.restaurant_brand_id = rb.restaurant_brand_id
WHERE o.service_date_et >= '2025-10-01'
  AND o.order_status = 'COMPLETE'
GROUP BY rb.restaurant_brand_name
ORDER BY gross_order_value DESC
LIMIT 20;
-- Note: This properly aggregates all locations of "Limesalt" into one brand
```

### Order Status Distribution

```sql
-- Understand order funnel and failure rates
SELECT
  order_status,
  COUNT(DISTINCT order_id) as order_count,
  ROUND(COUNT(DISTINCT order_id) / SUM(COUNT(DISTINCT order_id)) OVER () * 100, 2) as pct_of_total,
  ROUND(AVG(subtotal), 2) as avg_subtotal
FROM `wonder-dw-prod-brd.orders.hdr_orders`
WHERE order_placed_date_utc >= TIMESTAMP('2025-10-01')
GROUP BY order_status
ORDER BY order_count DESC;
```

### Hourly Order Volume Pattern

```sql
-- Analyze order volume by hour of day
SELECT
  EXTRACT(HOUR FROM DATETIME(order_placed_date_utc, 'America/New_York')) as hour_et,
  EXTRACT(DAYOFWEEK FROM service_date_et) as day_of_week,
  COUNT(DISTINCT order_id) as order_count,
  ROUND(AVG(total_amount), 2) as avg_order_value
FROM `wonder-dw-prod-brd.orders.hdr_orders`
WHERE service_date_et >= '2025-10-01'
  AND order_status = 'COMPLETE'
GROUP BY hour_et, day_of_week
ORDER BY day_of_week, hour_et;
```

### Orders with Item Details

```sql
-- Get complete order with all items
SELECT
  o.order_id,
  o.order_number,
  o.hdr_id,
  o.service_date_et,
  o.order_channel,
  o.order_status,
  o.total_amount as order_total,
  oi.menu_item_name,
  oi.order_quantity,
  oi.unit_price,
  oi.total_amount as item_total
FROM `wonder-dw-prod-brd.orders.hdr_orders` o
JOIN `wonder-dw-prod-brd.orders.order_items` oi
  ON o.order_id = oi.order_id
WHERE o.service_date_et = '2025-11-03'
  AND o.order_status = 'COMPLETE'
ORDER BY o.order_placed_date_utc DESC
LIMIT 100;
```

### Customer Satisfaction - NPS and Reviews

```sql
-- Calculate NPS and get sample reviews
-- Note: All ratings use 1-5 scale (5=Promoter, 4=Passive, 1-3=Detractor)
SELECT
  o.hdr_id,
  COUNT(*) as survey_count,
  ROUND(AVG(s.raw_nps), 2) as avg_rating,
  ROUND((COUNTIF(s.raw_nps = 5) - COUNTIF(s.raw_nps <= 3)) / COUNT(*) * 100, 2) as nps_score
FROM `wonder-dw-prod-brd.orders.hdr_orders` o
JOIN `wonder-dw-prod-brd.orders.customer_survey_responses` s
  ON o.order_id = s.order_id
WHERE o.service_date_et >= '2025-10-01'
  AND s.finished = 1
  AND s.raw_nps IS NOT NULL
GROUP BY o.hdr_id
ORDER BY nps_score DESC;
```

```sql
-- Get written reviews for a menu item with ratings
SELECT
  dish.other_text_feedback as review_text,
  dish.raw_taste_rating,
  orders.service_date_et
FROM `wonder-dw-prod-brd.orders.customer_survey_dish_responses` dish
JOIN `wonder-dw-prod-brd.orders.customer_survey_responses` survey
  ON dish.response_id = survey.response_id
JOIN `wonder-dw-prod-brd.orders.hdr_orders` orders
  ON survey.order_id = orders.order_id
WHERE dish.menu_item_id = 'abc-123-xyz'
  AND dish.other_text_feedback IS NOT NULL
ORDER BY orders.service_date_et DESC
LIMIT 100;
```

## Best Practices

1. **Always Filter by Status** - Use `WHERE order_status = 'COMPLETE'` for revenue analysis to exclude canceled/failed orders

2. **Use service_date_et for Daily Aggregations** - The `service_date_et` field is pre-calculated in Eastern Time for daily rollups

3. **Convert Timestamps for Time-of-Day Analysis** - Use `DATETIME(timestamp_field, 'America/New_York')` to analyze by hour in ET

4. **Be Careful with Item Joins** - Joining hdr_orders to order_items creates multiple rows per order. Use `DISTINCT order_id` when counting orders

5. **Check for NULL in Timing Fields** - Not all timing metrics are populated for all orders. Filter or handle NULLs appropriately

6. **Use Proper Date Filtering** - For TIMESTAMP fields use `TIMESTAMP('2025-01-01')`, for DATE fields use `'2025-01-01'`

7. **Consider Channel Differences** - Marketplace orders (GRUB_HUB, DOOR_DASH) may have different fee structures and timing expectations

8. **Filter Recent Data** - For large date ranges, add date filters early in WHERE clause for better query performance

## Supporting Documentation

- [schema-reference.md](schema-reference.md) - Complete table schemas and field descriptions
- [common-pitfalls.md](common-pitfalls.md) - Common mistakes and how to avoid them
