# Common Pitfalls - Sequencing Queries

This document highlights common mistakes when querying Wonder's sequencing tables and shows the correct approach.

**Wonder Context**: Wonder operates High Density Restaurants (HDRs) where multiple restaurant brands share kitchen facilities. Sequencing optimizes menu item preparation across virtual pods (appliance groupings) to minimize expo sit time and meet customer promise times from the ETA service.

For advanced query patterns and edge cases, see **advanced-pitfalls.md**.

## Timezone Handling

### ❌ Wrong: Displaying UTC timestamps directly

```sql
SELECT
  order_number,
  menu_item_name,
  t_s as start_time,
  t_o as order_finish
FROM `wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing_optimizer`
WHERE order_number = '12345';
```

**Problem**: Timestamps are stored in UTC but Wonder kitchens operate in America/New_York. This will show times that are 4-5 hours off depending on DST.

### ✅ Correct: Convert timestamps to America/New_York

```sql
SELECT
  order_number,
  menu_item_name,
  DATETIME(t_s, 'America/New_York') as start_time_ny,
  DATETIME(t_o, 'America/New_York') as order_finish_ny
FROM `wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing_optimizer`
WHERE order_number = '12345';
```

**Why**: Always use `DATETIME(timestamp_field, 'America/New_York')` for display and business logic analysis.

---

## Date Filtering

### ❌ Wrong: Querying without date filters

```sql
SELECT *
FROM `wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing_optimizer`
WHERE hdr_id = 'HDR_123';
```

**Problem**: The optimizer table has full history. This will scan massive amounts of data and may timeout or be very expensive.

### ✅ Correct: Always filter by date

```sql
SELECT *
FROM `wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing_optimizer`
WHERE hdr_id = 'HDR_123'
  AND DATE(created_time) = '2025-12-22';
```

**Why**: The `DATE(created_time)` filter dramatically reduces scan size. Use specific date ranges for analysis.

---

## Table Name Qualification

### ❌ Wrong: Using unqualified table names

```sql
SELECT *
FROM hdr_kitchen_order_sequencing_optimizer
WHERE order_number = '12345';
```

**Problem**: Table name is ambiguous without project and dataset qualifiers. Query will fail.

### ✅ Correct: Use fully qualified names with backticks

```sql
SELECT *
FROM `wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing_optimizer`
WHERE order_number = '12345';
```

**Why**: BigQuery requires fully qualified table names: `` `project.dataset.table` `` format with backticks.

---

## Joining Optimizer and Batch Tables

### ❌ Wrong: Joining only on _id

```sql
SELECT
  opt.order_number,
  opt.menu_item_name,
  batch.pod_id
FROM `wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing_optimizer` opt
LEFT JOIN `wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing_optimizer_batch` batch
  ON opt._id = batch._id
WHERE opt.order_number = '12345';
```

**Problem**: Joining only on `_id` will return a cartesian product - every item matched with every batch in that sequencing run. This produces incorrect and duplicated results.

### ✅ Correct: Join on both _id AND item_id

```sql
SELECT
  opt.order_number,
  opt.menu_item_name,
  batch.pod_id
FROM `wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing_optimizer` opt
LEFT JOIN `wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing_optimizer_batch` batch
  ON opt._id = batch._id
  AND opt.item_id = batch.item_id
WHERE opt.order_number = '12345';
```

**Why**: Both `_id` (sequencing run) and `item_id` (specific menu item) are required to correctly match items to their batch assignments.

---

## Understanding Multiple Batches per Item

### ❌ Wrong: Assuming one batch per item

```sql
SELECT
  opt.item_id,
  opt.menu_item_name,
  batch.pod_id,
  batch.group_id
FROM `wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing_optimizer` opt
LEFT JOIN `wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing_optimizer_batch` batch
  ON opt._id = batch._id
  AND opt.item_id = batch.item_id
WHERE opt.order_number = '12345';
-- Expecting exactly 1 row per item
```

**Problem**: Items can appear in multiple batch groups if they span multiple pods. This query may return more rows than items.

### ✅ Correct: Account for multiple batches with aggregation

```sql
SELECT
  opt.item_id,
  opt.menu_item_name,
  opt.batch_group_count,
  COUNT(DISTINCT batch.group_id) as actual_batches,
  STRING_AGG(DISTINCT batch.pod_id) as pods,
  STRING_AGG(DISTINCT batch.group_id) as group_ids
FROM `wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing_optimizer` opt
LEFT JOIN `wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing_optimizer_batch` batch
  ON opt._id = batch._id
  AND opt.item_id = batch.item_id
WHERE opt.order_number = '12345'
GROUP BY opt.item_id, opt.menu_item_name, opt.batch_group_count;
```

**Why**: Use `STRING_AGG` or `ARRAY_AGG` to see all batch assignments, or filter to single batch items with `HAVING COUNT(DISTINCT batch.group_id) = 1`.

---

## Timestamp Semantics and Ordering

### ❌ Wrong: Using t_s to calculate expo wait time

```sql
SELECT
  order_number,
  menu_item_name,
  TIMESTAMP_DIFF(t_o, t_s, MINUTE) as expo_wait_mins
FROM `wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing_optimizer`
WHERE DATE(created_time) = '2025-12-22';
```

**Problem**: `t_s` is when cooking starts, not when the item reaches expo. Expo wait is from item finish to order finish.

### ✅ Correct: Calculate expo wait from item finish (t_i) to order finish (t_o)

```sql
SELECT
  order_number,
  menu_item_name,
  TIMESTAMP_DIFF(t_o, t_i, MINUTE) as expo_wait_mins,
  estimated_item_expo_wait_time_mins as predicted_expo_wait
FROM `wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing_optimizer`
WHERE DATE(created_time) = '2025-12-22';
```

**Why**: Expo wait is how long a finished item sits at expo. That's `t_o - t_i`, not `t_o - t_s`. Compare with `estimated_item_expo_wait_time_mins` to validate.

---

## Customer Promise Time Comparison

### ❌ Wrong: Comparing t_i to customer promise

```sql
SELECT
  order_number,
  CASE
    WHEN t_i > t_cp THEN 'LATE'
    ELSE 'ON_TIME'
  END as status
FROM `wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing_optimizer`
WHERE DATE(created_time) = '2025-12-22';
```

**Problem**: `t_i` is when an individual item finishes. The customer promise is for the entire order finish (`t_o`).

### ✅ Correct: Compare t_o (order finish) to customer promise

```sql
SELECT
  order_number,
  DATETIME(t_o, 'America/New_York') as order_finish_ny,
  DATETIME(t_cp, 'America/New_York') as promise_ny,
  CASE
    WHEN t_o > t_cp THEN 'LATE'
    WHEN t_o <= t_cp THEN 'ON_TIME'
  END as status,
  TIMESTAMP_DIFF(t_o, t_cp, MINUTE) as minutes_vs_promise
FROM `wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing_optimizer`
WHERE DATE(created_time) = '2025-12-22';
```

**Why**: Customer promise time (`t_cp`) is compared to order finish time (`t_o`), not individual item finish times.

---

## Aggregating to Order Level

### ❌ Wrong: Treating optimizer table as order-level

```sql
SELECT
  order_id,
  order_number,
  t_o as order_finish,
  COUNT(*) as items_in_order
FROM `wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing_optimizer`
WHERE DATE(created_time) = '2025-12-22'
GROUP BY order_id, order_number, t_o;
```

**Problem**: `t_o` should be the same for all items in an order, but grouping by it is fragile. If there are any discrepancies, you'll get duplicate order rows.

### ✅ Correct: Use MAX/MIN aggregation for order-level fields

```sql
SELECT
  order_id,
  order_number,
  COUNT(*) as items_in_order,
  MIN(DATETIME(t_s, 'America/New_York')) as first_item_start_ny,
  MAX(DATETIME(t_i, 'America/New_York')) as last_item_finish_ny,
  MAX(DATETIME(t_o, 'America/New_York')) as order_finish_ny,
  MAX(DATETIME(t_cp, 'America/New_York')) as customer_promise_ny
FROM `wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing_optimizer`
WHERE DATE(created_time) = '2025-12-22'
GROUP BY order_id, order_number;
```

**Why**: Use `MAX(t_o)` and `MAX(t_cp)` in aggregation to safely get order-level timestamps even if there are minor inconsistencies.

---

## Handling NULL Holdback Strategies

### ❌ Wrong: Filtering with = NULL

```sql
SELECT
  COUNT(*) as no_holdback_items
FROM `wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing_optimizer`
WHERE DATE(created_time) = '2025-12-22'
  AND hold_back_strategy_v2 = NULL;
```

**Problem**: In SQL, `= NULL` never matches. Use `IS NULL` for NULL comparisons.

### ✅ Correct: Use IS NULL for NULL checking

```sql
SELECT
  COUNT(*) as no_holdback_items
FROM `wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing_optimizer`
WHERE DATE(created_time) = '2025-12-22'
  AND hold_back_strategy_v2 IS NULL;
```

**Why**: SQL requires `IS NULL` or `IS NOT NULL` for NULL comparisons. `= NULL` always evaluates to FALSE.

**Also Correct**: Filter for items with any holdback:
```sql
WHERE hold_back_strategy_v2 IS NOT NULL
```

**Note**: Most items have NULL `hold_back_strategy_v2` (no holdback). Only items with specific optimization strategies (EXPO_THRESHOLD, CUSTOMER_PROMISE, etc.) will have non-NULL values.

---

## Counting Unique Orders

### ❌ Wrong: COUNT(*) for order count

```sql
SELECT
  hdr_id,
  COUNT(*) as order_count
FROM `wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing_optimizer`
WHERE DATE(created_time) = '2025-12-22'
GROUP BY hdr_id;
```

**Problem**: The optimizer table is item-level. `COUNT(*)` counts items, not orders.

### ✅ Correct: COUNT(DISTINCT order_id) for order count

```sql
SELECT
  hdr_id,
  COUNT(DISTINCT order_id) as order_count,
  COUNT(*) as item_count,
  COUNT(*) / COUNT(DISTINCT order_id) as avg_items_per_order
FROM `wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing_optimizer`
WHERE DATE(created_time) = '2025-12-22'
GROUP BY hdr_id;
```

**Why**: Use `COUNT(DISTINCT order_id)` to count unique orders. `COUNT(*)` gives you item count.

---

## Score Interpretation

### ❌ Wrong: Treating negative expo_sit_time_score as better performance

```sql
SELECT
  order_number,
  expo_sit_time_score,
  CASE
    WHEN expo_sit_time_score < 0 THEN 'GOOD'
    WHEN expo_sit_time_score > 0 THEN 'BAD'
  END as performance
FROM `wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing_optimizer`
WHERE DATE(created_time) = '2025-12-22';
```

**Problem**: The sign of `expo_sit_time_score` is meaningless. Both +5 and -5 represent 5 minutes of expo sit time. This query incorrectly labels -5 as "GOOD" when it's just as bad as +5.

### ✅ Correct: Use ABSOLUTE VALUE for expo sit time analysis

```sql
SELECT
  order_number,
  expo_sit_time_score,
  ABS(expo_sit_time_score) as actual_expo_sit_mins,
  CASE
    WHEN ABS(expo_sit_time_score) < 3 THEN 'GOOD'
    WHEN ABS(expo_sit_time_score) BETWEEN 3 AND 7 THEN 'ACCEPTABLE'
    WHEN ABS(expo_sit_time_score) > 7 THEN 'POOR'
  END as performance
FROM `wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing_optimizer`
WHERE DATE(created_time) = '2025-12-22';
```

**Why**: The sign is an artifact of the scoring formula. Always use `ABS(expo_sit_time_score)` to measure actual expo wait time in minutes. Target is <3 minutes post-2025-11-24.

---

### ❌ Wrong: Treating negative customer_promise_score as good

```sql
SELECT
  order_number,
  customer_promise_score,
  CASE
    WHEN customer_promise_score < 0 THEN 'GOOD_OPTIMIZATION'
    ELSE 'NEEDS_WORK'
  END as status
FROM `wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing_optimizer`
WHERE DATE(created_time) = '2025-12-22';
```

**Problem**: Negative `customer_promise_score` means LATE (behind target). This query incorrectly labels late orders as "good optimization".

### ✅ Correct: Interpret customer_promise_score correctly

```sql
SELECT
  order_number,
  customer_promise_score,
  CASE
    WHEN customer_promise_score > 0 THEN 'EARLY'
    WHEN customer_promise_score = 0 THEN 'ON_TIME'
    WHEN customer_promise_score < 0 THEN 'LATE'
  END as timing_status,
  CASE
    WHEN ABS(customer_promise_score) <= 10 THEN 'WITHIN_TOLERANCE'
    ELSE 'OUTSIDE_TOLERANCE'
  END as performance
FROM `wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing_optimizer`
WHERE DATE(created_time) = '2025-12-22';
```

**Why**:
- Negative = LATE (behind customer promise): -2.5 means 2.5 minutes after target
- Positive = EARLY (ahead of promise): +4.0 means 4.0 minutes before target
- Zero = ON TIME
- Acceptable range is typically ±10 minutes

---

### ❌ Wrong: Comparing first and last run scores without absolute values

```sql
WITH first_last AS (
  SELECT
    order_number,
    FIRST_VALUE(expo_sit_time_score) OVER (PARTITION BY order_number ORDER BY created_time) as first_score,
    LAST_VALUE(expo_sit_time_score) OVER (PARTITION BY order_number ORDER BY created_time) as last_score
  FROM `wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing_optimizer`
  WHERE DATE(created_time) = '2025-12-22'
)
SELECT
  order_number,
  first_score,
  last_score,
  CASE
    WHEN last_score < first_score THEN 'IMPROVED'
    ELSE 'DEGRADED'
  END as trend
FROM first_last;
```

**Problem**: This treats a shift from +1.0 to -5.0 as "improvement" when actually expo sit time increased from 1 minute to 5 minutes (major degradation).

### ✅ Correct: Use absolute values to measure actual performance changes

```sql
WITH sequencing_runs AS (
  SELECT
    order_number,
    created_time,
    ABS(expo_sit_time_score) as expo_sit_abs,
    customer_promise_score,
    ROW_NUMBER() OVER (PARTITION BY order_number ORDER BY created_time ASC) as run_sequence,
    COUNT(*) OVER (PARTITION BY order_number) as total_runs
  FROM `wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing_optimizer`
  WHERE DATE(created_time) = '2025-12-22'
),
first_last_runs AS (
  SELECT
    order_number,
    MAX(CASE WHEN run_sequence = 1 THEN expo_sit_abs END) as first_expo_abs,
    MAX(CASE WHEN run_sequence = total_runs THEN expo_sit_abs END) as last_expo_abs,
    MAX(CASE WHEN run_sequence = 1 THEN customer_promise_score END) as first_cp_score,
    MAX(CASE WHEN run_sequence = total_runs THEN customer_promise_score END) as last_cp_score
  FROM sequencing_runs
  GROUP BY order_number
)
SELECT
  order_number,
  first_expo_abs,
  last_expo_abs,
  last_expo_abs - first_expo_abs as expo_change_mins,
  CASE
    WHEN last_expo_abs < first_expo_abs THEN 'IMPROVED'
    WHEN last_expo_abs > first_expo_abs THEN 'DEGRADED'
    ELSE 'UNCHANGED'
  END as expo_trend,
  first_cp_score,
  last_cp_score,
  last_cp_score - first_cp_score as cp_change_mins,
  CASE
    WHEN last_cp_score > 0 AND first_cp_score > 0 THEN 'BOTH_EARLY'
    WHEN last_cp_score < 0 AND first_cp_score < 0 THEN 'BOTH_LATE'
    WHEN last_cp_score < 0 AND first_cp_score > 0 THEN 'EARLY_TO_LATE'
    WHEN last_cp_score > 0 AND first_cp_score < 0 THEN 'LATE_TO_EARLY'
  END as cp_trend
FROM first_last_runs;
```

**Why**: This correctly measures:
- Expo sit time using absolute values (degradation when it increases)
- Customer promise score with proper sign semantics (negative = late)
- Provides accurate trend analysis showing operational reality vs initial predictions

**Common Pattern**: First runs typically show excellent predictions (median 0.25 min expo sit, +4 min early). Last runs show operational reality (median 5.3 min expo sit, -0.77 min late). This degradation reflects kitchen execution variability, not algorithm failure.

---

## Summary

---

## Joining Sequencing to Orders

### ❌ Wrong: Joining on item_id with order_items

```sql
-- This will NOT work!
SELECT
  oi.order_item_id,
  oi.menu_item_name,
  seq.expo_sit_time_score
FROM `wonder-dw-prod-brd.orders.order_items` oi
JOIN `wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing_optimizer` seq
  ON oi.order_item_id = seq.item_id;  -- ❌ These are different IDs!
```

**Problem**: The `item_id` in sequencing tables is NOT the same as `order_item_id` in order_items. These are completely different identifiers. Joining on them will return no results or incorrect matches.

### ✅ Correct: Join on order_id

```sql
-- Correct approach: Use order_id to link orders to sequencing
SELECT
  o.order_number,
  o.order_id,
  seq.item_id,           -- Internal sequencing ID (not order_item_id)
  seq.menu_item_name,    -- Use this to match items
  seq.expo_sit_time_score
FROM `wonder-dw-prod-brd.orders.hdr_orders` o
JOIN `wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing_optimizer` seq
  ON o.order_id = seq.order_id   -- ✅ Correct join key
WHERE o.order_number = '6187677';
```

**Why**: The sequencing `item_id` is an internal identifier used within the sequencing system. To link orders to their sequencing data, always join on `order_id`.

---

## Missing Batch Data (Historical Orders)

### ❌ Wrong: Assuming batch table has all data

```sql
-- This may return 0 rows for older orders!
SELECT
  batch.group_id,
  batch.pod_id
FROM `wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing_optimizer_batch` batch
WHERE batch._id = 'some-old-run-id';
```

**Problem**: The batch table started populating around mid-December 2025. Orders before this date will not have batch data.

### ✅ Correct: Use fallback strategy

```sql
-- Try batch data first, fall back to optimizer if needed
SELECT
  seq._id,
  seq.order_id,
  seq.menu_item_name,
  seq.expo_sit_time_score,
  seq.customer_promise_score,
  DATETIME(TIMESTAMP(seq.created_time), 'America/New_York') as run_time_et
FROM `wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing_optimizer` seq
WHERE seq.order_id = 'c1c5d052-9777-44ba-8dfe-b2dd77a7ad3b'
ORDER BY seq.created_time DESC;
```

**Why**: For historical analysis or older orders, query the optimizer table directly. The optimizer table has full history. Batch data (pod assignments, group IDs) is only available for recent orders.

**Best Practice**: When building tools, check if batch query returns results. If not, fall back to optimizer-only query.

---

## Kitchen Context Lookup

### ❌ Wrong: Using _id to fetch kitchen context

```python
# Trying to fetch kitchen context using optimizer._id
run_id = optimizer_row['_id']
query = f"""
SELECT kitchen_context
FROM `wonder-raw-prod.mongo_batch_cooking_optimization.sequencing_contexts`
WHERE _id = '{run_id}'
"""
```

**Problem**: The optimizer table's `_id` field is NOT the same as the contexts table's `_id`. This will return no results even though kitchen context exists.

### ✅ Correct: Use context_id to fetch kitchen context

```python
# Use context_id from optimizer table
context_id = optimizer_row['context_id']
query = f"""
SELECT kitchen_context
FROM `wonder-raw-prod.mongo_batch_cooking_optimization.sequencing_contexts`
WHERE _id = '{context_id}'
"""
```

**Why**: The optimizer table has TWO identifier fields:
- **`_id`**: Sequencing run identifier (unique per run)
- **`context_id`**: Links to `sequencing_contexts._id` (may be shared across multiple runs)

**Correct mapping**: `optimizer.context_id` = `sequencing_contexts._id`

**SQL Example**:
```sql
SELECT
  opt.order_number,
  opt._id as run_id,
  opt.context_id,
  ctx.kitchen_context
FROM `wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing_optimizer` opt
LEFT JOIN `wonder-raw-prod.mongo_batch_cooking_optimization.sequencing_contexts` ctx
  ON opt.context_id = ctx._id  -- Use context_id, not _id!
WHERE opt.order_number = '6187677'
LIMIT 1;
```

---

## Kitchen Context JSON Parsing

### ❌ Wrong: Assuming simple structure

```python
kitchen_context = json.loads(row['kitchen_context'])
pods = kitchen_context['pods']  # AttributeError: list has no 'pods'
```

**Problem**: The `kitchen_context` JSON is a LIST, not a dict with a `pods` key at the root.

### ✅ Correct: Parse nested structure

```python
kitchen_context = json.loads(row['kitchen_context'])  # Returns a list

# Extract pod codes from nested super_pod structure
for context_item in kitchen_context:
    super_pod = context_item.get('super_pod', {})
    super_pod_code = super_pod.get('code')  # e.g., "Super_Pod_A"

    for pod in super_pod.get('pods', []):
        pod_code = pod.get('code')  # e.g., "Cold_Pod_1A"

        for appliance in pod.get('appliances', []):
            appliance_code = appliance.get('code')  # e.g., "Press_A"
```

**Structure**:
```json
[
  {
    "super_pod": {
      "id": "uuid",
      "code": "Super_Pod_A",
      "pods": [
        {
          "id": "uuid",
          "code": "Cold_Pod_1A",
          "appliances": [
            {"id": "uuid", "code": "Press_A", "type": "PRESS"}
          ]
        }
      ]
    },
    "items": [...]
  }
]
```

**Why**: Kitchen context is a list where each element contains a `super_pod` object with nested pods and appliances.

---

## CSV Field Size Limits for Large JSON

### ❌ Wrong: Using default CSV parser for kitchen context

```python
import csv
reader = csv.DictReader(StringIO(bq_result))
rows = list(reader)  # Error: field larger than field limit (131072)
```

**Problem**: Kitchen context JSON can exceed 130KB, hitting Python's CSV parser default field size limit.

### ✅ Correct: Increase field size limit

```python
import csv
csv.field_size_limit(10000000)  # Set to 10MB
reader = csv.DictReader(StringIO(bq_result))
rows = list(reader)  # Works with large JSON fields
```

**Why**: The `kitchen_context` field contains detailed JSON for entire kitchen state including all pods, appliances, items, timers, and queued items. This can easily exceed default limits.

**Best Practice**: Set this at the start of your script if you're querying kitchen context.

---

## Root Cause Diagnosis Patterns

**When to use these patterns**: After analyzing sequencing optimizer scores and timestamps (the core purpose of this skill), use these diagnostic patterns to distinguish true sequencing issues from other operational problems (kitchen execution, menu coordination, capacity constraints).

When investigating poor order performance, it's critical to identify the TRUE root cause rather than assuming sequencing is at fault. Sequencing data often reveals symptoms of upstream or downstream issues unrelated to the optimizer algorithm itself. Here are common patterns:

### Pattern 1: High Expo Wait ≠ Sequencing Failure

**Symptom**: High `expo_sit_time_score` (e.g., 12+ minutes)

**What it LOOKS like**: "Sequencing scheduled item too early"

**What it OFTEN means**: The item finished cooking and sat at expo waiting for OTHER items in the order to complete

**Example** (Order with 4 items):
- Kids Mac & Cheese: expo score 12.55, CP score -5.23
- Order had multiple items from single restaurant
- Mac & Cheese finished and waited 12+ min for other items

**How to diagnose**:
```sql
-- Check if one item waited for others in same order
SELECT
  order_number,
  menu_item_name,
  ABS(expo_sit_time_score) as expo_mins,
  DATETIME(t_i, 'America/New_York') as item_finish,
  DATETIME(t_o, 'America/New_York') as order_finish,
  TIMESTAMP_DIFF(t_o, t_i, MINUTE) as waited_for_order_mins
FROM `wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing_optimizer`
WHERE order_number = 'YOUR_ORDER'
ORDER BY t_i;
```

**Verdict**: If items have staggered finish times, high expo scores may be unavoidable for early-finishing items.

### Pattern 2: Faster-Than-Expected Cook Time Still Late

**Symptom**: 
- Actual cook time < expected cook time
- Order still missed SLA significantly

**Example**:
| Item | Actual Cook | Expected Cook | Status |
|------|-------------|---------------|--------|
| Kids Mac & Cheese | 12.08 min | 15.0 min | Faster than expected |

But order was 19.5 min LATE overall.

**What this means**: The sequencing/cook prediction was actually GENEROUS - the lateness came from elsewhere:
- Kitchen throughput constraints
- Delivery/transit issues
- Other items in order took longer
- Expo coordination delays

**Verdict**: Don't blame sequencing when cook estimates were pessimistic and actual cook was faster.

### Pattern 3: UI/Communication Issues vs Algorithm Issues

**Example complaint**: "ETA is not possible. Does this include packaging time?"

**What this indicates**: Operator confusion about what the ETA display means, NOT that the algorithm calculated wrong.

**Root causes that are NOT sequencing**:
- UI clarity issues (operators don't understand what ETA represents)
- Communication gaps (ETA doesn't include packaging/handoff time)
- Expectation mismatch (customer vs operator vs system understanding)

**How to identify**: If the sequencing scores look reasonable but operators/customers are confused, it's a communication issue.

### Pattern 4: Operational vs Algorithmic Issues

**Signs it's OPERATIONAL (not sequencing)**:
- Actual cook times close to or faster than expected
- No force completes triggered
- Single restaurant order (no cross-brand coordination needed)
- High expo wait (throughput bottleneck, not scheduling)
- SLA miss much larger than individual item delays

**Signs it's ALGORITHMIC (sequencing issue)**:
- Holdback applied to already-late orders (`customer_promise_score < -10` AND `estimated_hold_back_time > 0`)
- Predicted vs actual cook times wildly different
- Systematic pattern across many orders/HDRs
- Force completes triggered by sequencing decisions

### Root Cause Analysis Template

When investigating an order, check:

1. **ERPU Performance**: How late was kitchen ready vs expected?
2. **SLA Difference**: Total lateness to customer
3. **Expo Wait**: Time items sat after cooking
4. **Cook Time Analysis**: Actual vs expected per item
5. **Force Completes**: Were items force-finished?
6. **Sequencing Scores**: Final expo and CP scores
7. **Multi-item coordination**: Did one item wait for others?

**Example Analysis** (Order 6894146-related):
```
Order placed: 12:03 PM ET, Completed: 12:59 PM ET
ERPU Performance: 4.5 min LATE (ready 12:17 vs expected 12:13)
SLA difference: 19.53 min LATE (MISSED SLA)
Actual expo wait: 12.63 min
Items: 4 items (single restaurant)
Force Completes: No

Sequencing Final Scores:
| Item              | Expo Score | CP Score | Holdback |
|-------------------|------------|----------|----------|
| Kids Mac & Cheese | 12.55      | -5.23    | 0.0      |

Cook Time Analysis:
| Item              | Actual | Expected | Status  |
|-------------------|--------|----------|---------|
| Kids Mac & Cheese | 12.08  | 15.0     | FASTER  |

VERDICT: OPERATIONAL/EXTERNAL - Not a sequencing issue
- Cook time was actually faster than expected
- High expo wait = item waiting for other items
- 19.5 min SLA miss due to kitchen throughput, not scheduling
```

---

## Known ETA Model Limitations

### Hot Hold vs A La Minute Cook Time Discrepancy

**Context**: Some menu items are "hot hold eligible" - they can either be pre-cooked and held in a warming unit (hot hold) OR cooked fresh to order (a la minute). The current ETA model doesn't distinguish between these cooking modes.

**The Problem**: When analyzing historical sequencing data, you may notice that:
- **Predicted cook durations** for hot hold eligible items appear lower than **actual cook times**
- Orders with these items show worse performance than predictions suggested

**Root Cause**: The ETA model uses historical cook time distributions that include BOTH:
1. **Hot hold pulls** (fast - just retrieve from warmer): ~30 seconds
2. **A la minute cooks** (full cook time): 5-10+ minutes depending on item

When the model averages these, it produces an estimate that's too optimistic for a la minute scenarios.

**Example** (Order 6894146): Mac and cheese was cooked a la minute, but the ETA model assumed a shorter duration based on hot hold distribution, leading to underestimated cook time and late delivery.

**Items Commonly Affected**:
- Mac and cheese
- Mashed potatoes
- Soups
- Other items that can be batch-prepped and held warm

**Why This Matters for Analysis**:
- Don't assume poor sequencing performance for hot hold eligible items indicates algorithm issues
- Historical metrics for these items will show bimodal distributions (fast hot hold pulls vs longer a la minute cooks)
- Performance may appear worse than actual optimization quality

**Future Fixes** (planned):
1. **Pantry signals integration**: Use real-time inventory data to know if item is available in hot hold
2. **Disable "assume hot holding"**: Stop defaulting to optimistic hot hold estimates
3. **Sequencing as ETA**: Move from ETA service to sequencing-driven estimates that account for actual kitchen state

**Workaround for Analysis**:
When analyzing orders with hot hold eligible items, check if the item was likely cooked a la minute vs pulled from hot hold. Poor performance on these orders may not indicate sequencing issues but rather ETA model limitations.

```sql
-- Example: Flag orders that may have hot hold vs a la minute discrepancies
-- Look for high expo scores on items known to be hot hold eligible
SELECT
  order_number,
  menu_item_name,
  ABS(expo_sit_time_score) as expo_mins,
  customer_promise_score,
  estimated_item_expo_wait_time_mins,
  CASE 
    WHEN menu_item_name LIKE '%Mac%Cheese%' THEN 'HOT_HOLD_ELIGIBLE'
    WHEN menu_item_name LIKE '%Mashed Potato%' THEN 'HOT_HOLD_ELIGIBLE'
    -- Add other hot hold eligible items as identified
    ELSE 'STANDARD'
  END as cooking_mode_flag
FROM `wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing_optimizer`
WHERE DATE(created_time) = '2025-01-15'
  AND customer_promise_score < -5  -- Late orders
ORDER BY customer_promise_score ASC;
```

---

**Key Takeaways**:

1. **CRITICAL - Score interpretation**:
   - **expo_sit_time_score**: Always use `ABS()` - sign is meaningless! Both +5 and -5 = 5 minutes
   - **customer_promise_score**: Negative = LATE, Positive = EARLY, Zero = On-time
2. **Always convert timestamps**: Use `DATETIME(field, 'America/New_York')` for display
3. **Always filter by date**: Add `DATE(created_time) = 'YYYY-MM-DD'` to every query
4. **Use fully qualified table names**: `` `wonder-dw-prod-brd.orders.table_name` ``
5. **Join correctly**: Both `_id` AND `item_id` when joining optimizer to batch
6. **Join orders to sequencing**: Use `order_id`, NOT item IDs
7. **Understand timestamp semantics**: t_s → t_i → t_f → t_o, with t_cp as promise
8. **Handle multiple batches**: Items can span multiple batch groups
9. **Compare t_o to t_cp**: For on-time analysis (not t_i to t_cp)
10. **Aggregate carefully**: Use `COUNT(DISTINCT order_id)` for order counts
11. **NULL handling**: Use `IS NULL` not `= NULL`
12. **Batch data availability**: Fallback to optimizer table for orders before mid-December 2025
13. **Kitchen context lookup**: Use `context_id` (not `_id`) to join to sequencing_contexts
14. **Kitchen context parsing**: Expect a LIST with `super_pod` nested structure
15. **CSV field limits**: Set `csv.field_size_limit(10000000)` when parsing kitchen context JSON

For more advanced patterns including score comparisons, cook time calculations, pod filtering, context joins, and more, see **advanced-pitfalls.md**.

For query examples and use cases, see **query-patterns.md** and **SKILL.md**.
