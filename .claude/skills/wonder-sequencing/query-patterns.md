# Sequencing Query Patterns

This document provides comprehensive SQL query examples for analyzing Wonder's kitchen sequencing system.

**Wonder Context**: Wonder operates High Density Restaurants (HDRs) where multiple restaurant brands share kitchen facilities. Sequencing optimizes menu item preparation across virtual pods (appliance groupings) to minimize expo sit time and meet customer promise times.

## Basic Queries

### Basic Item-Level Query (Optimizer Table)

```sql
SELECT
  opt._id,
  opt.context_id,
  opt.hdr_id,
  opt.order_number,
  opt.menu_item_name,
  opt.item_id,
  DATETIME(opt.t_s, 'America/New_York') as start_time_ny,
  DATETIME(opt.t_i, 'America/New_York') as item_finish_ny,
  DATETIME(opt.t_o, 'America/New_York') as order_finish_ny,
  DATETIME(opt.t_cp, 'America/New_York') as customer_promise_ny,
  opt.expo_sit_time_score,
  opt.customer_promise_score,
  opt.estimated_item_expo_wait_time_mins,
  opt.hold_back_strategy_v2
FROM `wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing_optimizer` opt
WHERE opt.order_number = 'YOUR_ORDER_NUMBER'
ORDER BY opt.created_time, opt.t_s
LIMIT 100;
```

### Joined Query with Batch Information

```sql
SELECT
  opt._id,
  opt.order_number,
  opt.menu_item_name,
  opt.item_id,
  DATETIME(opt.t_s, 'America/New_York') as start_time_ny,
  opt.estimated_item_expo_wait_time_mins,
  batch.group_id,
  batch.pod_id,
  batch.group_priority,
  batch.resultant_item_id_count,
  DATETIME(batch.estimated_start_time, 'America/New_York') as batch_start_ny,
  DATETIME(batch.estimated_finish_time, 'America/New_York') as batch_finish_ny
FROM `wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing_optimizer` opt
LEFT JOIN `wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing_optimizer_batch` batch
  ON opt._id = batch._id
  AND opt.item_id = batch.item_id
WHERE opt.hdr_id = 'YOUR_HDR_ID'
  AND DATE(opt.created_time) = '2025-12-22'
ORDER BY batch.pod_id, batch.group_id, opt.t_s
LIMIT 100;
```

### Single Order Analysis with Context

```sql
-- Step 1: Get sequencing data for the target order
WITH target_order AS (
  SELECT
    seq._id,
    seq.order_id,
    seq.order_number,
    seq.menu_item_name,
    seq.expo_sit_time_score,
    seq.customer_promise_score,
    seq.estimated_item_expo_wait_time_mins
  FROM `wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing_optimizer` seq
  WHERE seq.order_id = 'YOUR_ORDER_ID'
  ORDER BY seq.created_time DESC
  LIMIT 10
),
-- Step 2: Get all orders in the same sequencing run
run_context AS (
  SELECT
    seq.order_number,
    seq.menu_item_name,
    seq.expo_sit_time_score,
    seq.customer_promise_score,
    seq.estimated_item_expo_wait_time_mins
  FROM `wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing_optimizer` seq
  WHERE seq._id = (SELECT _id FROM target_order LIMIT 1)
)
-- Step 3: Compare target order to run averages
SELECT
  'Target Order' as group_type,
  (SELECT order_number FROM target_order LIMIT 1) as order_number,
  AVG(expo_sit_time_score) as avg_expo_score,
  AVG(customer_promise_score) as avg_cp_score,
  AVG(estimated_item_expo_wait_time_mins) as avg_expo_wait_mins
FROM target_order
UNION ALL
SELECT
  'Full Run' as group_type,
  'All Orders' as order_number,
  AVG(expo_sit_time_score) as avg_expo_score,
  AVG(customer_promise_score) as avg_cp_score,
  AVG(estimated_item_expo_wait_time_mins) as avg_expo_wait_mins
FROM run_context;
```

**Use case**: "Why did order X perform poorly?" This query shows how the target order's scores compare to all other items in the same sequencing run.

## Context and Input Analysis

### Fetch Sequencing Context

```sql
SELECT
  _id,
  hdr_id,
  created_time,
  kitchen_context,
  estimator_settings,
  -- Extract total item count from JSON
  (
    SELECT SUM(ARRAY_LENGTH(JSON_QUERY_ARRAY(super_pod_context, '$.items')))
    FROM UNNEST(JSON_QUERY_ARRAY(kitchen_context)) AS super_pod_context
  ) AS total_item_count
FROM `wonder-raw-prod.mongo_batch_cooking_optimization.sequencing_contexts`
WHERE _id = 'YOUR_CONTEXT_ID';
```

### Find Contexts with Item Counts

```sql
SELECT
  _id,
  hdr_id,
  created_time,
  (
    SELECT SUM(ARRAY_LENGTH(JSON_QUERY_ARRAY(super_pod_context, '$.items')))
    FROM UNNEST(JSON_QUERY_ARRAY(kitchen_context)) AS super_pod_context
  ) AS total_item_count
FROM `wonder-raw-prod.mongo_batch_cooking_optimization.sequencing_contexts`
WHERE hdr_id = 'YOUR_HDR_ID'
  AND created_time BETWEEN DATETIME("2025-12-22T15:00:00") AND DATETIME("2025-12-22T16:00:00")
  AND (
    SELECT SUM(ARRAY_LENGTH(JSON_QUERY_ARRAY(super_pod_context, '$.items')))
    FROM UNNEST(JSON_QUERY_ARRAY(kitchen_context)) AS super_pod_context
  ) > 0
ORDER BY created_time;
```

### Context Item Count Distribution

```sql
WITH item_counts AS (
  SELECT
    _id,
    hdr_id,
    created_time,
    (
      SELECT SUM(ARRAY_LENGTH(JSON_QUERY_ARRAY(super_pod_context, '$.items')))
      FROM UNNEST(JSON_QUERY_ARRAY(kitchen_context)) AS super_pod_context
    ) AS total_item_count
  FROM `wonder-raw-prod.mongo_batch_cooking_optimization.sequencing_contexts`
  WHERE DATE(created_time) = '2025-12-22'
)
SELECT
  CASE
    WHEN total_item_count <= 10 THEN '1-10'
    WHEN total_item_count <= 20 THEN '11-20'
    WHEN total_item_count <= 50 THEN '21-50'
    WHEN total_item_count <= 100 THEN '51-100'
    ELSE '100+'
  END as item_count_bucket,
  COUNT(*) as context_count,
  AVG(total_item_count) as avg_items_in_bucket
FROM item_counts
GROUP BY item_count_bucket
ORDER BY MIN(total_item_count);
```

## Delay Analysis

### Analyze Sequencing Delay for an Order

```sql
SELECT
  order_number,
  created_time,
  DATETIME(t_s, 'America/New_York') as start_time_ny,
  TIMESTAMP_DIFF(CAST(created_time AS TIMESTAMP), t_s, SECOND) as delay_seconds,
  ROUND(TIMESTAMP_DIFF(CAST(created_time AS TIMESTAMP), t_s, SECOND) / 60.0, 2) as delay_minutes,
  estimated_hold_back_time,
  hold_back_strategy_v2,
  customer_promise_score
FROM `wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing_optimizer`
WHERE order_number = 'YOUR_ORDER_NUMBER'
ORDER BY created_time;
```

### Find Orders with Excessive Delays

```sql
SELECT
  hdr_id,
  order_number,
  item_id,
  MIN(created_time) as first_sequencing_time,
  MAX(created_time) as last_sequencing_time,
  TIMESTAMP_DIFF(
    CAST(MAX(created_time) AS TIMESTAMP),
    CAST(MIN(created_time) AS TIMESTAMP),
    SECOND
  ) / 60.0 as total_delay_minutes
FROM `wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing_optimizer`
WHERE DATE(created_time) = '2025-12-22'
  AND estimated_hold_back_time > 0
GROUP BY hdr_id, order_number, item_id
HAVING TIMESTAMP_DIFF(
  CAST(MAX(created_time) AS TIMESTAMP),
  CAST(MIN(created_time) AS TIMESTAMP),
  SECOND
) > 30 * 60  -- More than 30 minutes
ORDER BY total_delay_minutes DESC
LIMIT 100;
```

### Delay Edge Case Analysis by Date

```sql
SELECT
  created_date,
  expo_threshold,
  delayed_orders / total_orders as delayed_order_pct,
  greater_30min_delay / total_orders as greater_30min_delay_pct,
  greater_60min_delay / total_orders as greater_60min_delay_pct,
  delayed_orders,
  greater_30min_delay,
  greater_60min_delay,
  total_orders
FROM (
  SELECT
    EXTRACT(DATE FROM first_sequencing_time) as created_date,
    CASE WHEN first_sequencing_time >= "2025-11-24" THEN "EXPO_THRESHOLD_3"
         ELSE "EXPO_THRESHOLD_7"
    END as expo_threshold,
    COUNT(DISTINCT order_number) as delayed_orders,
    COUNTIF(delay_seconds > 30*60) as greater_30min_delay,
    COUNTIF(delay_seconds > 60*60) as greater_60min_delay,
    (
      SELECT COUNT(DISTINCT order_number)
      FROM `wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing_optimizer`
      WHERE EXTRACT(DATE FROM created_time) = EXTRACT(DATE FROM first_sequencing_time)
    ) as total_orders
  FROM (
    SELECT
      order_number,
      item_id,
      MIN(created_time) as first_sequencing_time,
      MAX(created_time) as last_sequencing_time,
      TIMESTAMP_DIFF(
        CAST(MAX(created_time) AS TIMESTAMP),
        CAST(MIN(created_time) AS TIMESTAMP),
        SECOND
      ) as delay_seconds
    FROM `wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing_optimizer`
    WHERE created_time >= "2025-11-10"
      AND estimated_hold_back_time > 0
    GROUP BY order_number, item_id
  )
  GROUP BY created_date, expo_threshold
)
ORDER BY created_date, expo_threshold;
```

### Daily Delay Summary by HDR

```sql
SELECT
  hdr_id,
  DATE(created_time) as date,
  CASE WHEN created_time >= "2025-11-24" THEN "EXPO_THRESHOLD_3"
       ELSE "EXPO_THRESHOLD_7"
  END as expo_threshold,
  COUNT(DISTINCT order_number) as total_orders,
  COUNTIF(estimated_hold_back_time > 0) as orders_with_holdback,
  AVG(estimated_hold_back_time) as avg_holdback_mins,
  COUNTIF(TIMESTAMP_DIFF(CAST(created_time AS TIMESTAMP), t_s, SECOND) >= 1800) as orders_delayed_30min_plus,
  AVG(estimated_item_expo_wait_time_mins) as avg_expo_wait
FROM `wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing_optimizer`
WHERE DATE(created_time) = '2025-12-22'
GROUP BY hdr_id, date, expo_threshold
ORDER BY hdr_id;
```

## Expo Sit Time Analysis

### High Expo Sit Time Analysis

```sql
SELECT
  opt.hdr_id,
  opt.order_number,
  opt.menu_item_name,
  DATETIME(opt.t_i, 'America/New_York') as item_finish_ny,
  DATETIME(opt.t_o, 'America/New_York') as order_finish_ny,
  opt.estimated_item_expo_wait_time_mins,
  opt.estimated_order_level_expo_time_mins,
  opt.expo_sit_time_score,
  opt.hold_back_strategy_v2,
  batch.pod_id,
  batch.group_priority
FROM `wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing_optimizer` opt
LEFT JOIN `wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing_optimizer_batch` batch
  ON opt._id = batch._id
  AND opt.item_id = batch.item_id
WHERE DATE(opt.created_time) = '2025-12-22'
  AND opt.estimated_item_expo_wait_time_mins > 10.0
ORDER BY opt.estimated_item_expo_wait_time_mins DESC
LIMIT 100;
```

## Bug Detection

### Detect Bug: Late Orders with Holdback

This query detects a known bug where orders with poor customer promise scores are still held back:

```sql
SELECT
  EXTRACT(DATE FROM MIN(created_time)) as date,
  COUNT(DISTINCT order_number) as incorrect_orders
FROM (
  SELECT
    order_number,
    MIN(created_time) as created_time,
    MIN(customer_promise_score) as min_promise_score,
    MIN(estimated_hold_back_time) as min_holdback
  FROM `wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing_optimizer`
  GROUP BY order_number
  HAVING MIN(customer_promise_score) < -10
    AND MIN(estimated_hold_back_time) > 0
)
GROUP BY date
ORDER BY date;
```

## Performance Analysis

### Compare Sequencing Predictions to Actual Performance

```sql
SELECT
  s.order_number,
  DATETIME(s.t_o, 'America/New_York') as predicted_ready_ny,
  DATETIME(s.t_cp, 'America/New_York') as customer_promise_ny,
  DATETIME(o.actual_cooking_finish_time_utc, 'America/New_York') as actual_finish_ny,
  DATETIME(o.actual_completed_time_utc, 'America/New_York') as actual_complete_ny,
  s.customer_promise_score,
  s.estimate_order_complete_vs_customer_promise,
  TIMESTAMP_DIFF(o.actual_completed_time_utc, s.t_cp, MINUTE) as actual_vs_promise_mins,
  TIMESTAMP_DIFF(o.actual_completed_time_utc, s.t_o, MINUTE) as actual_vs_predicted_mins
FROM (
  SELECT DISTINCT
    order_number,
    MIN(created_time) OVER (PARTITION BY order_number) as first_sequencing,
    created_time,
    t_o,
    t_cp,
    customer_promise_score,
    estimate_order_complete_vs_customer_promise
  FROM `wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing_optimizer`
  WHERE DATE(created_time) >= CURRENT_DATE() - 7
) s
INNER JOIN `wonder-dw-prod-brd.orders.hdr_orders` o
  ON s.order_number = o.order_number
WHERE s.created_time = s.first_sequencing  -- Only use first sequencing run
ORDER BY s.order_number;
```

### Sequencing Prediction Accuracy

```sql
SELECT
  DATE(opt.created_time) as date,
  COUNT(DISTINCT opt.order_number) as orders,
  AVG(TIMESTAMP_DIFF(orders.actual_completed_time_utc, opt.t_o, MINUTE)) as avg_prediction_error_mins,
  STDDEV(TIMESTAMP_DIFF(orders.actual_completed_time_utc, opt.t_o, MINUTE)) as stddev_prediction_error,
  COUNTIF(ABS(TIMESTAMP_DIFF(orders.actual_completed_time_utc, opt.t_o, MINUTE)) <= 5) as within_5min,
  COUNTIF(ABS(TIMESTAMP_DIFF(orders.actual_completed_time_utc, opt.t_o, MINUTE)) > 10) as error_gt_10min
FROM (
  SELECT order_number, MIN(created_time) as first_seq
  FROM `wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing_optimizer`
  WHERE DATE(created_time) >= '2025-12-01'
  GROUP BY order_number
) first
INNER JOIN `wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing_optimizer` opt
  ON first.order_number = opt.order_number AND first.first_seq = opt.created_time
INNER JOIN `wonder-dw-prod-brd.orders.hdr_orders` orders
  ON opt.order_number = orders.order_number
WHERE orders.actual_completed_time_utc IS NOT NULL
GROUP BY date
ORDER BY date;
```

## Table Comparison

### Compare Optimizer vs Legacy Table

```sql
SELECT
  opt.order_number,
  COUNT(DISTINCT opt.context_id) as opt_context_count,
  COUNT(DISTINCT og.context_id) as legacy_context_count,
  MIN(opt.created_time) as opt_first_sequencing,
  MIN(og.created_time) as legacy_first_sequencing
FROM `wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing_optimizer` opt
INNER JOIN `wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing` og
  ON opt.order_number = og.order_number
WHERE DATE(opt.created_time) = '2025-12-22'
GROUP BY opt.order_number
HAVING COUNT(DISTINCT opt.context_id) != COUNT(DISTINCT og.context_id)
LIMIT 100;
```

## Common Use Cases

### 1. Why did this order get delayed so long?

```sql
SELECT
  order_number,
  item_id,
  MIN(created_time) as first_sequenced,
  MAX(created_time) as last_sequenced,
  TIMESTAMP_DIFF(CAST(MAX(created_time) AS TIMESTAMP), CAST(MIN(created_time) AS TIMESTAMP), MINUTE) as delay_mins,
  MIN(hold_back_strategy_v2) as holdback_strategy,
  MIN(estimated_hold_back_time) as estimated_holdback_mins,
  MIN(customer_promise_score) as promise_score
FROM `wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing_optimizer`
WHERE order_number = 'YOUR_ORDER_NUMBER'
GROUP BY order_number, item_id
ORDER BY delay_mins DESC;
```

### 2. What was the kitchen context for this sequencing run?

```sql
SELECT
  ctx._id,
  ctx.hdr_id,
  ctx.created_time,
  (
    SELECT SUM(ARRAY_LENGTH(JSON_QUERY_ARRAY(super_pod_context, '$.items')))
    FROM UNNEST(JSON_QUERY_ARRAY(ctx.kitchen_context)) AS super_pod_context
  ) AS total_items_to_sequence,
  ctx.kitchen_context,
  ctx.estimator_settings
FROM `wonder-raw-prod.mongo_batch_cooking_optimization.sequencing_contexts` ctx
WHERE ctx._id = 'YOUR_SEQUENCING_RUN_ID';
```

### 3. How many orders had excessive delays today?

```sql
SELECT
  hdr_id,
  COUNT(DISTINCT order_number) as orders_with_30min_delay,
  COUNTIF(max_delay_mins > 60) as orders_with_60min_delay,
  (SELECT COUNT(DISTINCT order_number)
   FROM `wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing_optimizer`
   WHERE hdr_id = delays.hdr_id AND DATE(created_time) = CURRENT_DATE()) as total_orders
FROM (
  SELECT
    hdr_id,
    order_number,
    MAX(TIMESTAMP_DIFF(CAST(created_time AS TIMESTAMP), t_s, SECOND)) / 60.0 as max_delay_mins
  FROM `wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing_optimizer`
  WHERE DATE(created_time) = CURRENT_DATE()
    AND estimated_hold_back_time > 0
  GROUP BY hdr_id, order_number
  HAVING max_delay_mins > 30
) delays
GROUP BY hdr_id
ORDER BY orders_with_30min_delay DESC;
```

### 4. Track the bug fix impact (promise score + holdback issue)

```sql
SELECT
  EXTRACT(DATE FROM MIN(created_time)) as date,
  COUNT(DISTINCT order_number) as orders_with_bug
FROM (
  SELECT order_number, MIN(created_time) as created_time
  FROM `wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing_optimizer`
  GROUP BY order_number
  HAVING MIN(customer_promise_score) < -10 AND MIN(estimated_hold_back_time) > 0
)
GROUP BY date
ORDER BY date;
```

## Data Quality Validation

### Check for NULL Timestamps

```sql
SELECT
  COUNT(*) as total_records,
  COUNTIF(t_s IS NULL) as null_t_s,
  COUNTIF(t_i IS NULL) as null_t_i,
  COUNTIF(t_o IS NULL) as null_t_o,
  COUNTIF(t_cp IS NULL) as null_t_cp
FROM `wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing_optimizer`
WHERE DATE(created_time) = CURRENT_DATE();
```

### Verify Timestamp Ordering

```sql
SELECT
  COUNT(*) as total,
  COUNTIF(t_s <= t_i) as valid_start_to_item,
  COUNTIF(t_i <= t_f) as valid_item_to_order_items,
  COUNTIF(t_f <= t_o) as valid_items_to_order,
  COUNTIF(t_s > t_i) as invalid_ordering
FROM `wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing_optimizer`
WHERE DATE(created_time) = CURRENT_DATE();
```

### Find Potentially Malformed Batch Groups

```sql
SELECT
  batch._id,
  batch.group_id,
  COUNT(DISTINCT batch.item_id) as items_in_group,
  STRING_AGG(DISTINCT opt.menu_item_name) as items
FROM `wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing_optimizer_batch` batch
LEFT JOIN `wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing_optimizer` opt
  ON batch._id = opt._id AND batch.item_id = opt.item_id
WHERE DATE(batch._sync_time) = '2025-12-22'
GROUP BY batch._id, batch.group_id
HAVING COUNT(DISTINCT batch.item_id) = 0  -- Groups with no items
   OR COUNT(DISTINCT batch.item_id) > 50;  -- Suspiciously large groups
```

## Best Practices for Query Construction

### Timezone Conversion
Always convert timestamps to America/New_York for display:
```sql
DATETIME(opt.t_s, 'America/New_York') as start_time_ny
```

### Date Filtering
Always filter on created_time for performance:
```sql
WHERE DATE(created_time) = '2025-12-22'
-- or
WHERE created_time BETWEEN DATETIME("2025-12-22T15:00:00") AND DATETIME("2025-12-22T16:00:00")
```

### Handling Multiple Sequencing Runs
Use first sequencing run for analysis:
```sql
-- Get first sequencing run per order
SELECT order_number, MIN(created_time) as first_sequencing
FROM `wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing_optimizer`
GROUP BY order_number
```

### Delay Detection Methods
Two complementary methods:

**Method 1 (most trusted)**:
```sql
WHERE estimated_hold_back_time > 0
```

**Method 2 (catches edge cases)**:
```sql
WHERE TIMESTAMP_DIFF(CAST(created_time AS TIMESTAMP), t_s, SECOND) >= -30
```

### Expo Threshold Periods
Always account for the expo threshold change:
```sql
CASE WHEN created_time >= "2025-11-24" THEN "EXPO_THRESHOLD_3"
     ELSE "EXPO_THRESHOLD_7"
END as expo_threshold
```

## Related Documentation

- **SKILL.md**: High-level overview and when to use this skill
- **schema-reference.md**: Complete table schemas and field descriptions
- **common-pitfalls.md**: Wrong vs. correct query patterns to avoid mistakes
