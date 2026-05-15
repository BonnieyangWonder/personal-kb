# Sequencing Schema Reference

This document provides complete schema definitions for Wonder's kitchen sequencing tables in BigQuery.

**Wonder Context**: Wonder operates High Density Restaurants (HDRs) - physical spaces hosting multiple restaurant brands that share kitchen facilities. Sequencing coordinates menu item preparation across virtual **pods** (appliance groupings, typically one per employee) to optimize kitchen efficiency. The V2 data structure (current) provides full visibility into batch group sequences displayed on Kitchen Display System (KDS) screens.

## Table Overview

### Primary Tables (Current System)

### `wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing_optimizer`

**Purpose**: Item-level sequencing optimization results with full history. Primary table for detailed analysis of how individual menu items are scheduled in the kitchen.

**Update Frequency**: Every 30+ seconds as new sequencing optimization runs complete

**History**: Full history retained for analysis

**Primary Keys**: `_id` (sequencing run), `item_id` (menu item)

**Join Pattern**:
- Join to batch table using `_id` and `item_id`
- Join to contexts table using `_id` (note: contexts._id = optimizer._id, but optimizer.context_id != contexts._id)
- Join to hdr_orders using `order_id` or `order_number`

### `wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing_optimizer_batch`

**Purpose**: Batch group schedule information with limited history. Shows how items are grouped together across pods for efficient preparation.

**Update Frequency**: Every 30+ seconds as new sequencing optimization runs complete

**History**: Limited history (recent data preferred)

**Primary Keys**: `_id` (sequencing run), `group_id` (batch group), `item_id` (menu item)

**Join Pattern**: Join to optimizer table using `_id` and `item_id`

### `wonder-raw-prod.mongo_batch_cooking_optimization.sequencing_contexts`

**Purpose**: Input context for each sequencing run. Contains the kitchen state and configuration settings that drove the optimization.

**Update Frequency**: Every 30+ seconds as new sequencing runs start

**History**: Full history retained

**Primary Keys**: `_id` (sequencing context/run identifier)

**Join Pattern**: **CRITICAL** - Join to optimizer table using contexts.`_id` = optimizer.`context_id` (NOT optimizer._id)

```sql
-- CORRECT join pattern
FROM hdr_kitchen_order_sequencing_optimizer opt
LEFT JOIN sequencing_contexts ctx
  ON opt.context_id = ctx._id  -- Use context_id, not _id!
```

**Note**: The optimizer table has TWO identifier fields:
- `_id`: Sequencing run identifier (unique per run)
- `context_id`: Links to `sequencing_contexts._id` (use this for joins!)

**Data Availability**: Kitchen context available for recent orders (Dec 20, 2025+). Older orders may have `null` kitchen_context.

### Legacy Table

### `wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing`

**Purpose**: Older sequencing output structure (may still be populated). Similar to optimizer table but with fewer fields.

**Update Frequency**: Every 30+ seconds (may be deprecated)

**History**: Full history retained

**Primary Keys**: `_id` (sequencing run), `item_id` (menu item)

**Join Pattern**: Can be compared with optimizer table using `order_number` and `created_time`

---

## Complete Table Schemas

### hdr_kitchen_order_sequencing_optimizer

Complete field-level schema with descriptions:

| Field Name | Type | Description |
|------------|------|-------------|
| `_id` | STRING | Unique identifier for this sequencing optimization run. A single `_id` represents one complete optimization cycle (runs every 30+ seconds). Use this to identify all items scheduled in the same batch. Join key to contexts table. |
| `context_id` | STRING | Context identifier for grouping related sequencing events. Multiple `_id` runs may share the same `context_id` for tracking purposes. **Note**: This is NOT the same as `_id` in the contexts table. |
| `hdr_id` | STRING | HDR (High Density Restaurant) identifier - the physical kitchen location where this item is being prepared. One HDR can host multiple restaurant brands. |
| `created_time` | DATETIME | Timestamp when this sequencing record was created (stored as DATETIME in UTC, convert to America/New_York for analysis). This is when the sequencing completed, not when the item should start. |
| `created_by` | STRING | Service or user that created this sequencing record. Typically the sequencing service identifier. |
| `_sync_time` | DATETIME | Internal sync timestamp for data pipeline purposes (DATETIME in UTC). |
| `item_id` | STRING | Unique identifier for this specific menu item instance. An order may have multiple items, each with its own `item_id`. Join key to batch table. |
| `t_s` | TIMESTAMP | **Simulated Start Time**: When this item should begin cooking according to the optimization. This is the key timestamp for understanding when preparation starts. Convert to America/New_York for display. |
| `t_i` | TIMESTAMP | **Item Finish Time**: When this specific menu item completes cooking and is ready. This represents when the individual item is done, not when the whole order is ready. Convert to America/New_York for display. |
| `t_f` | TIMESTAMP | **Order Items Finish Time**: When all items in this order complete preparation. This may be the same as `t_i` for single-item orders, or later for multi-item orders. Convert to America/New_York for display. |
| `t_o` | TIMESTAMP | **Order Finish Time**: When the entire order is ready at expo station. This is typically the same as `t_f` but may differ based on expo coordination logic. Convert to America/New_York for display. |
| `t_cp` | TIMESTAMP | **Customer Promise Time**: Target completion time for kitchen to finish cooking. Currently received from ETA service (ML-driven). Feeds into customer-facing estimate but not 1:1. Compare with `t_o` to determine if order was on-time. Convert to America/New_York for display. Future: Sequencing will set and enforce its own ETA. |
| `score` | INTEGER | Overall optimization score for this item scheduling. Higher scores indicate better optimization results. This is the combined objective function value from the CP-SAT solver. |
| `expo_sit_time_score` | FLOAT | **Component score measuring expo wait time impact**. Part of the multi-objective optimization. **CRITICAL: Use ABSOLUTE VALUE for analysis** - both +5 and -5 represent 5 minutes of expo sit time. The sign is an artifact of the scoring formula and does NOT indicate quality (negative is not better than positive). To measure actual expo wait time performance, take `ABS(expo_sit_time_score)` and compare against thresholds (e.g., 3-minute target post-2025-11-24). |
| `customer_promise_score` | FLOAT | **Component score measuring adherence to customer promise time**. Part of the multi-objective optimization. **Interpretation: Negative = LATE (behind target), Positive = EARLY (ahead of target), Zero = On-time**. E.g., -1.5 means the order is predicted to finish 1.5 minutes AFTER the customer promise time. Values within ±10 minutes are typically acceptable. Compare against 0 to measure on-time performance: `customer_promise_score < 0` indicates late orders. |
| `hold_back_strategy_v2` | STRING | The holdback strategy applied to this item. Strategies determine when items are delayed from immediate preparation to optimize overall timing. Possible values documented below. NULL means no holdback applied. |
| `estimated_item_expo_wait_time_mins` | FLOAT | Predicted wait time (in minutes) for this specific item at the expo station. This is how long the item is expected to sit before the order completes. Critical metric for food quality. |
| `estimated_order_level_expo_time_mins` | FLOAT | Predicted wait time (in minutes) for the complete order at expo. This is how long from when the first item finishes until the last item finishes. |
| `is_corporate_order` | BOOLEAN | TRUE if this is a corporate/catering order, FALSE otherwise. Corporate orders are common and growing - challenging because many orders drop into kitchen simultaneously (especially at lunch). Not present at all HDRs. |
| `in_person_source` | STRING | Source of the in-person order. Currently only kiosk orders get a flag (value varies). NULL for all other orders (delivery, pickup, etc.). Future: May expand with geofencing or other signals. |
| `estimated_hold_back_time` | FLOAT | Calculated delay time (in minutes) that this item is held back from immediate preparation. Based on the `hold_back_strategy_v2` logic. 0.0 or NULL means no holdback. **Use `estimated_hold_back_time > 0` to find delayed items.** |
| `menu_item_name` | STRING | Human-readable name of the menu item (e.g., "Wonder Burger", "Caesar Salad"). For display and debugging purposes. |
| `order_number` | STRING | Customer-facing order number. Use this for customer service inquiries and debugging specific customer issues. |
| `order_id` | STRING | Internal system order identifier. Join key to order tables in wonder-orders skill. |
| `item_type` | STRING | Type of menu item (e.g., "ENTREE", "SIDE", "DESSERT", "BEVERAGE"). May affect sequencing priorities and batching logic. |
| `batch_group_count` | INTEGER | Number of batch groups this item belongs to. Typically 1, but may be >1 if the item spans multiple pods or batches. |

### hdr_kitchen_order_sequencing_optimizer_batch

Complete field-level schema with descriptions:

| Field Name | Type | Description |
|------------|------|-------------|
| `_id` | STRING | Unique identifier for this sequencing optimization run. Must match `_id` in optimizer table for joining. |
| `context_id` | STRING | Context identifier for grouping related sequencing events. Matches `context_id` in optimizer table. |
| `group_id` | STRING | Unique identifier for this batch group within the sequencing run. Items with the same `group_id` are batched together for preparation. |
| `pod_id` | STRING | Pod identifier - virtual concept (not physical station) grouping appliances for one employee. Each pod has KDS screen(s) displaying batch groups one at a time. Examples: grill pod, fryer pod, salad pod. |
| `item_id` | STRING | Menu item identifier. Join key to optimizer table. Note: An item may appear in multiple batch groups if it spans pods. |
| `resultant_item_id_count` | INTEGER | Total number of distinct items in this batch group. Indicates batch size for capacity planning. |
| `batch_id_count` | INTEGER | Number of batches within this group. Typically 1, but may be higher for large groups split into sub-batches. |
| `group_priority` | STRING | Priority level assigned to this batch group (e.g., "HIGH", "MEDIUM", "LOW"). Affects scheduling order within the pod. |
| `earliest_hold_back_time` | TIMESTAMP | Earliest time that any item in this batch group can be held back to. Represents the constraint on how early items can start. Convert to America/New_York for display. |
| `estimated_start_time` | TIMESTAMP | Predicted start time for this batch group. When the first item in the group should begin cooking. Convert to America/New_York for display. |
| `estimated_finish_time` | TIMESTAMP | Predicted finish time for this batch group. When the last item in the group should complete. Convert to America/New_York for display. |

### sequencing_contexts

Complete field-level schema with descriptions:

| Field Name | Type | Description |
|------------|------|-------------|
| `_id` | STRING | **CRITICAL**: Unique identifier for this sequencing context. Join pattern: `contexts._id` = `optimizer.context_id` (NOT `optimizer._id`). See join pattern warning above. |
| `hdr_id` | STRING | HDR (restaurant) identifier where this sequencing run occurred. |
| `kitchen_context` | STRING | JSON string containing detailed kitchen state, pod/appliance configuration, and items to be sequenced. **Structure**: List of context objects, each containing `super_pod` (with nested pods/appliances) and `items` arrays. See detailed structure below. |
| `estimator_settings` | STRING | JSON string containing the configuration settings used for this sequencing run (e.g., holdback strategies, expo thresholds, weights). |
| `created_time` | DATETIME | Timestamp when this sequencing context was created (DATETIME in UTC, convert to America/New_York). |
| `created_by` | STRING | Service or user that created this context. Typically the sequencing service identifier. |
| `_sync_time` | DATETIME | Internal sync timestamp for data pipeline purposes (DATETIME in UTC). |

**Kitchen Context JSON Structure**:

The `kitchen_context` field is a **JSON list** (not a dict) with this structure:

```json
[
  {
    "super_pod": {
      "id": "62f72622-0b31-479b-8a02-18ec261e10fa",
      "code": "Super_Pod_A",
      "pods": [
        {
          "id": "f0dbcf07-b5f1-453d-9922-8c9a20beb736",
          "code": "Cold_Pod_1A",
          "pod_type": "COLD",
          "human_resources": 1,
          "appliances": [
            {
              "id": "bd9d56f0-d8b3-466a-a06a-0d5ccdf5dcad",
              "code": "Press_A",
              "type": "PRESS",
              "appliance_config_ids": [],
              "decks": []
            },
            {
              "id": "af11b87f-9714-4b86-8080-33dc8d2e7029",
              "code": "Toaster_A",
              "type": "TOASTER"
            }
          ]
        },
        {
          "id": "...",
          "code": "Hot_Pod_1A",
          "pod_type": "HOT",
          "appliances": [...]
        }
      ]
    },
    "items": [
      {
        "item_id": "uuid",
        "order_id": "uuid",
        "order_number": "6187677",
        "menu_item_name": "Wonder Burger",
        "pod_id": "f0dbcf07-b5f1-453d-9922-8c9a20beb736",
        "appliance": "bd9d56f0-d8b3-466a-a06a-0d5ccdf5dcad",
        "state": "COOKING",
        "timer_remaining_secs": 180,
        "batch_id": "batch-uuid"
      }
    ],
    "order_priorities": [...],
    "hot_holding_inventory": [...]
  }
]
```

**Key Points**:
1. **List Structure**: kitchen_context is a list, not a dict. Each element represents a super pod context.
2. **Human-Readable Codes**: Pod and appliance codes (e.g., "Cold_Pod_1A", "Press_A") are in the `super_pod` nested structure
3. **Items Array**: Kitchen items with their current state, pod assignment, appliance, and timers
4. **Code Mappings**: Extract `super_pod['pods'][i]['code']` and `super_pod['pods'][i]['appliances'][j]['code']` to map UUIDs to human-readable names

**Extracting Pod/Appliance Codes (Python)**:
```python
import json
kitchen_context = json.loads(row['kitchen_context'])

code_mappings = {'pods': {}, 'appliances': {}, 'super_pods': {}}

for context_item in kitchen_context:
    super_pod = context_item.get('super_pod', {})

    # Super pod code
    sp_id = super_pod.get('id')
    sp_code = super_pod.get('code')
    if sp_id and sp_code:
        code_mappings['super_pods'][sp_id] = sp_code

    # Pod and appliance codes
    for pod in super_pod.get('pods', []):
        pod_id = pod.get('id')
        pod_code = pod.get('code')
        if pod_id and pod_code:
            code_mappings['pods'][pod_id] = pod_code

        for appliance in pod.get('appliances', []):
            app_id = appliance.get('id')
            app_code = appliance.get('code')
            if app_id and app_code:
                code_mappings['appliances'][app_id] = app_code
```

**Extracting Item Counts (SQL)**:
```sql
(
  SELECT SUM(ARRAY_LENGTH(JSON_QUERY_ARRAY(super_pod_context, '$.items')))
  FROM UNNEST(JSON_QUERY_ARRAY(kitchen_context)) AS super_pod_context
) AS total_item_count
```

**Parsing Note**: Kitchen context JSON can exceed 130KB. When using Python's CSV parser, increase field size limit: `csv.field_size_limit(10000000)`

### hdr_kitchen_order_sequencing (Legacy)

Complete field-level schema with descriptions:

| Field Name | Type | Description |
|------------|------|-------------|
| `order_number` | STRING | Customer-facing order number. |
| `order_id` | STRING | Internal system order identifier. |
| `menu_item_name` | STRING | Human-readable name of the menu item. |
| `_id` | STRING | Unique identifier for this sequencing run. |
| `context_id` | STRING | Context identifier for grouping related sequencing events. |
| `hdr_id` | STRING | HDR (restaurant) identifier. |
| `hdr_name` | STRING | Human-readable HDR name (e.g., "Hudson Square", "Middletown"). Not present in optimizer table. |
| `created_time` | DATETIME | Timestamp when this sequencing record was created (DATETIME in UTC). |
| `type` | STRING | Type or category field (usage varies). Not present in optimizer table. |
| `item_id` | STRING | Menu item identifier. |
| `t_s` | TIMESTAMP | Simulated Start Time (same as optimizer). |
| `t_i` | TIMESTAMP | Item Finish Time (same as optimizer). |
| `t_f` | TIMESTAMP | Order Items Finish Time (same as optimizer). |
| `t_o` | TIMESTAMP | Order Finish Time (same as optimizer). |
| `score` | INTEGER | Overall optimization score (INTEGER, not FLOAT like some optimizer fields). |
| `expo_sit_time_score` | INTEGER | Expo wait time component score (INTEGER in legacy, FLOAT in optimizer). |
| `customer_promise_score` | INTEGER | Customer promise component score (INTEGER in legacy, FLOAT in optimizer). |
| `t_cp` | TIMESTAMP | Customer Promise Time (same as optimizer). |
| `hold_back_strategy_v2` | STRING | Holdback strategy applied (same as optimizer). |
| `estimated_item_expo_wait_time_mins` | FLOAT | Predicted item-level expo wait time (same as optimizer). |
| `estimated_order_level_expo_time_mins` | FLOAT | Predicted order-level expo wait time (same as optimizer). |
| `estimate_order_complete_vs_customer_promise` | FLOAT | How far order completion is from customer promise time (in minutes). Positive = early, negative = late. Present in legacy table, may be missing in some optimizer records. |
| `duration_in_sequencing_minutes` | FLOAT | How long (in minutes) this item spent in the sequencing system. Not present in optimizer table. |

---

## Field Semantics and Usage

### Timestamp Fields (The Five Critical Times)

Understanding the five timestamp fields in the optimizer table is crucial for debugging:

1. **t_s (Simulated Start)**: Optimization says "start cooking now"
   - Use for: Understanding when items enter the production pipeline
   - Compare to: Actual start times from KDS system (if available)
   - **Delay calculation**: `TIMESTAMP_DIFF(CAST(created_time AS TIMESTAMP), t_s, SECOND)` shows how long before start time the sequencing completed

2. **t_i (Item Finish)**: This specific item is done cooking
   - Use for: Calculating individual item cook times
   - Formula: `TIMESTAMP_DIFF(t_i, t_s, MINUTE)` = cook duration

3. **t_f (Order Items Finish)**: All items in order are done cooking
   - Use for: Understanding when the complete order set is ready
   - Gap: `TIMESTAMP_DIFF(t_f, t_i, MINUTE)` = wait for other items

4. **t_o (Order Finish)**: Order ready at expo
   - Use for: Comparing to customer promise time
   - Typically equals t_f unless expo coordination logic differs

5. **t_cp (Customer Promise)**: When we told the customer
   - Use for: On-time performance analysis
   - Formula: `TIMESTAMP_DIFF(t_o, t_cp, MINUTE)` = late/early minutes

**Example Timeline**:
```
created_time = 11:55:00  Sequencing completes (5 min early)
t_s = 12:00:00  Item should start cooking
t_i = 12:05:00  Item finishes (5 min cook time)
t_f = 12:08:00  Other items in order finish (3 min wait)
t_o = 12:08:00  Order ready at expo
t_cp = 12:10:00 Customer promise (2 min buffer)
Result: Order is 2 minutes early, sequenced 5 minutes ahead of start time
```

### Delay Analysis Fields

**Sequencing Delay** (time from sequencing completion to start time):
```sql
TIMESTAMP_DIFF(CAST(created_time AS TIMESTAMP), t_s, SECOND) as delay_seconds
```
- **Normal**: -30 to 300 seconds (sequencing happens shortly before or after the planned start)
- **Edge case**: >= 1800 seconds (30+ minutes) indicates potential issues
- **Filter for anomalies**: `WHERE TIMESTAMP_DIFF(CAST(created_time AS TIMESTAMP), t_s, SECOND) >= -30`

**Holdback Delay** (intentional delay from optimization):
- Field: `estimated_hold_back_time` (minutes)
- **Filter for held back items**: `WHERE estimated_hold_back_time > 0`
- This is the most trusted method to find delayed items

**Multiple Sequencing Runs**:
- Orders can be re-sequenced multiple times
- Track delay between first and last sequencing:
  ```sql
  TIMESTAMP_DIFF(CAST(MAX(created_time) AS TIMESTAMP), CAST(MIN(created_time) AS TIMESTAMP), SECOND)
  ```

### Score Fields

The optimization uses a multi-objective scoring system:

**Overall Score Formula** (conceptual):
```
score = w1 * expo_sit_time_score + w2 * customer_promise_score + other_components
```

Where `w1` and `w2` are weights determined by the sequencing configuration.

**Interpreting Scores**:

**CRITICAL SEMANTICS - READ CAREFULLY**:

**expo_sit_time_score**:
- **THE SIGN DOES NOT MATTER**: Both +5 and -5 represent 5 minutes of expo sit time
- **Always use ABSOLUTE VALUE**: `ABS(expo_sit_time_score)` gives actual minutes of expo wait
- **Lower absolute values are better**: 0.25 is excellent, 5.0+ indicates degraded performance
- **Target**: Post-2025-11-24, aim for <3 minutes absolute value
- **Common mistake**: Thinking negative scores are "good" - they're not! -5 is just as bad as +5
- Critical for food quality (hot food should stay hot, cold food should stay cold)

**customer_promise_score**:
- **Negative = LATE (behind target)**: -2.5 means 2.5 minutes after customer promise time
- **Positive = EARLY (ahead of target)**: +4.0 means 4.0 minutes before customer promise time
- **Zero = On-time**: Exactly meeting the promise time
- **Acceptable range**: Typically ±10 minutes is within tolerance
- **Performance queries**: Use `customer_promise_score < 0` to find late orders
- **Degradation patterns**: Watch for median shifting from positive toward negative over sequencing runs

**overall score**:
- Relative within a sequencing run, not comparable across runs
- Higher scores indicate the optimizer preferred this solution
- Individual component scores show which objective is being prioritized
- Being early has diminishing returns (waste of capacity)
- Being late has severe penalties
- **Bug**: If `customer_promise_score < -10` AND `estimated_hold_back_time > 0`, this is an error condition

**estimate_order_complete_vs_customer_promise**: Direct measurement
- Positive value: Order completes before promise (early)
- Negative value: Order completes after promise (late)
- Zero: Order completes exactly at promise time
- Units: minutes

### Holdback Strategy Values

The `hold_back_strategy_v2` field indicates the logic used to delay item preparation:

Common strategy values (may vary by implementation version):

- **`null` or empty**: No holdback applied, item starts ASAP
- **`EXPO_THRESHOLD`**: Held back to avoid exceeding expo wait time threshold
- **`CUSTOMER_PROMISE`**: Held back to align with customer promise time
- **`BATCH_COORDINATION`**: Held back to coordinate with other items in batch
- **`POD_CAPACITY`**: Held back due to pod capacity constraints
- **`ORDER_SYNCHRONIZATION`**: Held back to synchronize with other items in order

**Usage Pattern**:
```sql
SELECT
  hold_back_strategy_v2,
  COUNT(*) as item_count,
  AVG(estimated_hold_back_time) as avg_delay_mins
FROM `wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing_optimizer`
WHERE DATE(created_time) = CURRENT_DATE()
GROUP BY hold_back_strategy_v2
ORDER BY item_count DESC;
```

### Expo Threshold Configuration

The expo sit time threshold changed on 2025-11-24:
- **Before 2025-11-24**: EXPO_THRESHOLD_7 (7 minutes max expo wait)
- **After 2025-11-24**: EXPO_THRESHOLD_3 (3 minutes max expo wait)

This affects holdback logic and scoring. Always segment by threshold period:
```sql
CASE WHEN created_time >= "2025-11-24" THEN "EXPO_THRESHOLD_3"
     ELSE "EXPO_THRESHOLD_7"
END as expo_threshold
```

---

## Join Patterns and Relationships

### Basic Join: Optimizer + Batch

**One-to-Many Relationship**: One optimizer item may map to multiple batch groups if it spans pods.

```sql
SELECT
  opt.item_id,
  opt.menu_item_name,
  opt.t_s,
  batch.group_id,
  batch.pod_id,
  batch.group_priority
FROM `wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing_optimizer` opt
LEFT JOIN `wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing_optimizer_batch` batch
  ON opt._id = batch._id
  AND opt.item_id = batch.item_id
WHERE opt.order_number = 'YOUR_ORDER';
```

### Join: Optimizer + Contexts

**One-to-Many Relationship**: One context produces multiple optimizer items.

```sql
SELECT
  ctx._id,
  ctx.hdr_id,
  ctx.created_time as context_created,
  (
    SELECT SUM(ARRAY_LENGTH(JSON_QUERY_ARRAY(super_pod_context, '$.items')))
    FROM UNNEST(JSON_QUERY_ARRAY(ctx.kitchen_context)) AS super_pod_context
  ) AS total_items_in_context,
  opt.order_number,
  opt.menu_item_name,
  opt.created_time as optimizer_created
FROM `wonder-raw-prod.mongo_batch_cooking_optimization.sequencing_contexts` ctx
LEFT JOIN `wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing_optimizer` opt
  ON ctx._id = opt._id
WHERE ctx._id = 'YOUR_CONTEXT_ID';
```

**Important**: Join on `contexts._id = optimizer._id`, NOT on `optimizer.context_id`.

### Join: Optimizer + HDR Orders (Actual Performance)

**Link predictions to actual outcomes**:

```sql
SELECT
  opt.order_number,
  DATETIME(opt.t_o, 'America/New_York') as predicted_ready_ny,
  DATETIME(opt.t_cp, 'America/New_York') as customer_promise_ny,
  DATETIME(orders.actual_cooking_finish_time_utc, 'America/New_York') as actual_finish_ny,
  DATETIME(orders.actual_completed_time_utc, 'America/New_York') as actual_complete_ny,
  TIMESTAMP_DIFF(orders.actual_completed_time_utc, opt.t_o, MINUTE) as prediction_error_mins,
  TIMESTAMP_DIFF(orders.actual_completed_time_utc, opt.t_cp, MINUTE) as actual_vs_promise_mins
FROM (
  SELECT order_number, MIN(created_time) as first_sequencing
  FROM `wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing_optimizer`
  GROUP BY order_number
) first
INNER JOIN `wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing_optimizer` opt
  ON first.order_number = opt.order_number
  AND first.first_sequencing = opt.created_time
INNER JOIN `wonder-dw-prod-brd.orders.hdr_orders` orders
  ON opt.order_number = orders.order_number
WHERE DATE(opt.created_time) = '2025-12-22';
```

**hdr_orders fields useful for comparison**:
- `actual_cooking_finish_time_utc`: When cooking actually finished
- `actual_completed_time_utc`: When order actually completed
- `expected_cooking_finish_time_utc`: Initial ETA estimate
- `last_estimated_cooking_finish_time_utc`: Most recent ETA update
- `customer_facing_estimated_delivery_time_lower_utc`: Lower bound of customer ETA range
- `customer_facing_estimated_delivery_time_upper_utc`: Upper bound of customer ETA range

### Compare: Optimizer vs Legacy Table

```sql
SELECT
  opt.order_number,
  opt.created_time as opt_created,
  legacy.created_time as legacy_created,
  TIMESTAMP_DIFF(CAST(opt.created_time AS TIMESTAMP), CAST(legacy.created_time AS TIMESTAMP), SECOND) as time_diff_seconds,
  opt.customer_promise_score as opt_promise_score,
  legacy.customer_promise_score as legacy_promise_score,
  legacy.duration_in_sequencing_minutes
FROM `wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing_optimizer` opt
INNER JOIN `wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing` legacy
  ON opt.order_number = legacy.order_number
  AND opt.item_id = legacy.item_id
WHERE DATE(opt.created_time) = '2025-12-22'
LIMIT 100;
```

---

## Data Quality and Constraints

### Known Data Characteristics

**History Retention**:
- Optimizer table: Full history retained
- Batch table: Limited history (exact retention policy TBD)
- Contexts table: Full history retained
- Legacy table: Full history retained
- Prefer recent dates (last 7-30 days) for batch analysis

**Update Frequency**:
- New records every 30+ seconds as sequencing runs
- Each run creates new `_id` with fresh optimization
- Historical records are immutable (no updates after creation)

**NULL Handling**:
- `hold_back_strategy_v2`: NULL means no holdback
- `in_person_source`: NULL means not an in-person order
- `is_corporate_order`: FALSE or NULL means regular order
- Most timestamp fields should never be NULL (data quality issue if NULL)
- `estimated_hold_back_time`: NULL or 0.0 means no holdback

**Multiple Sequencing Runs**:
- Orders are often sequenced multiple times
- Use `MIN(created_time)` per order to get first sequencing
- Track re-sequencing with `COUNT(DISTINCT context_id)` per order

### Validation Queries

**Check for NULL timestamps** (data quality):
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

**Verify timestamp ordering**:
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

**Expected ordering**: `t_s <= t_i <= t_f <= t_o` (customer promise `t_cp` may be before or after `t_o`)

**Detect bug condition** (late orders with holdback):
```sql
SELECT COUNT(*) as bug_count
FROM `wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing_optimizer`
WHERE DATE(created_time) = CURRENT_DATE()
  AND customer_promise_score < -10
  AND estimated_hold_back_time > 0;
```

### Performance Considerations

**Efficient Filtering**:
- Always filter on `DATE(created_time)` for optimizer table
- Use `_id` when analyzing a specific sequencing run
- Index-friendly: `hdr_id`, `order_id`, `order_number`

**Avoid Full Scans**:
- Don't query without date filters on optimizer table (full history)
- Limit result sets with `LIMIT` clause during exploration
- Use `COUNT(*)` before `SELECT *` for large date ranges

**Join Performance**:
- Batch table is smaller, join to it as needed (not by default)
- Contexts table has JSON fields which can be slow to parse
- Pre-filter both sides before joining when possible
- Use `LEFT JOIN` if you need all optimizer records even without batch data

---

## Example Analysis Queries

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

---

## Related Documentation

- **SKILL.md**: High-level overview and when to use this skill
- **query-patterns.md**: Comprehensive SQL query examples for all analysis scenarios
- **common-pitfalls.md**: Foundational wrong vs. correct query patterns
- **advanced-pitfalls.md**: Advanced query patterns and edge cases
- **algorithm-reference/three-stage-wrapper-logic.md**: Business logic for ThreeStageWrapperV2 family (simulation-based algorithms)
- **algorithm-reference/ortools-cpsat-logic.md**: Business logic for ORToolsCPSATV2 (constraint programming approach)
