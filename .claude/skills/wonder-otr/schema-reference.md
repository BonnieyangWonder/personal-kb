# Wonder OTR Schema Reference

Complete schema documentation for On-Time Rate (OTR) and Root Cause Analysis tables.

---

## Core Tables

### `wonder-dw-prod-brd.orders.hdr_orders`

The primary orders table containing timing error fields for RCA.

#### Key Timing/Error Fields

| Field | Type | Description |
|-------|------|-------------|
| `order_id` | STRING | Unique order identifier |
| `hdr_id` | STRING | HDR location identifier |
| `service_date_et` | DATE | Service date in Eastern Time |
| `dining_option` | STRING | `DELIVERY` or `PICKUP` |
| `order_status` | STRING | Order lifecycle status |
| `order_channel` | STRING | `APP`, `WEB`, `GRUB_HUB`, `DOOR_DASH`, `UBER_EATS`, `IN_PERSON` |
| `brand_category` | STRING | `WONDER_HDR`, `WONDER_LOCAL`, etc. |
| `order_business_type` | STRING | `WONDER_HDR`, `WONDER_SPOT`, `3P_PLATFORM_CORPORATE` |

#### Actual Timing Fields (minutes)

| Field | Type | Description |
|-------|------|-------------|
| `ticket_time_mins` | FLOAT | Total kitchen execution (order placed → ready for pickup) |
| `actual_o2e_mins` | FLOAT | Actual order-to-eat time |
| `estimated_o2e_mins` | FLOAT | Predicted O2E at order time |
| `actual_queue_mins` | FLOAT | Time in queue before cooking |
| `actual_cook_duration_mins` | FLOAT | Time spent cooking |
| `actual_packaging_bagging_mins` | FLOAT | Time spent bagging (full) |
| `actual_packaging_mins` | FLOAT | Packing only (cooking_finish → pending_bagging) |
| `actual_pickup_waiting_duration_mins` | FLOAT | Sit time (ready → pickup complete) |
| `actual_transit_mins` | FLOAT | Transit time (pickup → near destination) |
| `actual_delivery_duration_mins` | FLOAT | Time from pickup to delivery |

#### Sit Time Decomposition Fields (Critical for RCA)

| Field | Type | Description |
|-------|------|-------------|
| `courier_response_time_mins` | FLOAT | Ready for Pickup → Driver Arrival (Logistics) |
| `kitchen_handoff_time_mins` | FLOAT | Driver Arrival → Pickup Complete (Ops) |

**Note:** `actual_pickup_waiting_duration_mins` = `courier_response_time_mins` + `kitchen_handoff_time_mins`

#### Estimated Timing Fields (minutes)

| Field | Type | Description |
|-------|------|-------------|
| `estimated_queue_mins` | FLOAT | Predicted queue time |
| `estimated_cook_duration_mins` | FLOAT | Predicted cook time |
| `estimated_packaging_bagging_mins` | FLOAT | Predicted bagging time |
| `estimated_pickup_waiting_duration_mins` | FLOAT | Predicted sit time |
| `estimated_transit_mins` | FLOAT | Predicted transit time |
| `estimated_delivery_duration_mins` | FLOAT | Predicted delivery duration |

#### Error Fields (predicted - actual, in minutes)

**Sign Convention:** Positive = early/fast, Negative = late/slow

| Field | Type | Description |
|-------|------|-------------|
| `queue_error` | FLOAT | Queue time error (predicted - actual) |
| `cook_error` | FLOAT | Cook time error (predicted - actual) |
| `packaging_bagging_error` | FLOAT | Pack/bag time error |
| `pickup_error` | FLOAT | Handoff/sit time error (ready → courier pickup) |
| `transit_error` | FLOAT | Transit time error (pickup → near destination) |
| `dropoff_error` | FLOAT | Dropoff time error (arrival → customer) |
| `delivery_error` | FLOAT | Combined delivery error (pickup → customer) |
| `queue_cook_error` | FLOAT | Combined queue + cook error |
| `total_eta_error` | FLOAT | End-to-end prediction error |
| `total_absolute_eta_error` | FLOAT | Absolute value of total error |

#### SLA Fields

| Field | Type | Description |
|-------|------|-------------|
| `delivery_sla_difference` | FLOAT | Minutes from promised delivery time |
| `ready_for_pickup_sla_difference` | FLOAT | Minutes from promised ready time |

#### Raw Timestamp Fields (UTC)

| Field | Type | Description |
|-------|------|-------------|
| `order_placed_date_utc` | TIMESTAMP | When order was placed |
| `actual_cooking_start_time_utc` | TIMESTAMP | When cooking started |
| `actual_cooking_finish_time_utc` | TIMESTAMP | When cooking finished |
| `actual_ready_for_pickup_time_utc` | TIMESTAMP | When food was ready |
| `pickup_arrived_time_utc` | TIMESTAMP | When driver arrived |
| `actual_pickup_time_utc` | TIMESTAMP | When pickup completed |
| `actual_arrival_time_utc` | TIMESTAMP | When near destination |
| `actual_delivery_time_utc` | TIMESTAMP | When delivered to customer |
| `expected_cooking_start_time_utc` | TIMESTAMP | Expected cook start |
| `expected_cooking_finish_time_utc` | TIMESTAMP | Expected cook finish |
| `expected_ready_for_pickup_time_utc` | TIMESTAMP | Expected ready time |
| `expected_pickup_time_utc` | TIMESTAMP | Expected pickup time |
| `expected_delivery_time_utc` | TIMESTAMP | Expected delivery time |
| `expected_delivery_time_upper_utc` | TIMESTAMP | Upper bound of delivery window |
| `expected_delivery_time_lower_utc` | TIMESTAMP | Lower bound of delivery window |

#### Additional Order Attributes

| Field | Type | Description |
|-------|------|-------------|
| `schedule_type` | STRING | `ASAP` or `SCHEDULED` |
| `courier_platform` | STRING | Courier service provider |

---

### `wonder-dw-prod-brd.orders.hdr_on_time_orders`

Dedicated table for On-Time Rate metrics and classifications.

| Field | Type | Description |
|-------|------|-------------|
| `order_id` | STRING | Unique order identifier (join key to hdr_orders) |
| `on_time_issue` | BOOLEAN | TRUE if order had any timing issue |
| `kitchen_on_time_issue` | BOOLEAN | TRUE if kitchen caused timing issue |
| `delivery_on_time_issue` | BOOLEAN | TRUE if delivery caused timing issue |
| `otr_sla_tier` | STRING | Timing bucket classification (see below) |
| `delivery_sla_difference` | FLOAT | Minutes from promised delivery time |
| `ready_for_pickup_sla_difference` | FLOAT | Minutes from promised ready time |
| `is_complete_within_original_window` | BOOLEAN | Completed within original promise |
| `is_complete_within_updated_window` | BOOLEAN | Completed within updated promise |
| `original_window_error` | FLOAT | Error vs original window |
| `updated_window_error` | FLOAT | Error vs updated window |

#### SLA Tier Values (`otr_sla_tier`)

| Value | Description |
|-------|-------------|
| `9+_EARLY` | 9+ minutes early |
| `8_5_EARLY` | 5-8 minutes early |
| `4_1_EARLY` | 1-4 minutes early |
| `ON_TIME` | Within SLA window |
| `1_4_LATE` | 1-4 minutes late |
| `5_15_LATE` | 5-15 minutes late |
| `16_30_LATE` | 16-30 minutes late |
| `31+_LATE` | 31+ minutes late |

---

### `wonder-dw-prod-brd.orders.imperfect_orders`

Tracks order imperfections including timing issues.

**⚠️ CRITICAL: Use `on_time_issue` for OTR calculation, NOT `delivery_sla_difference`!**

| Field | Type | Description |
|-------|------|-------------|
| `order_id` | STRING | Unique order identifier |
| `on_time_issue` | BOOLEAN | **USE THIS FOR OTR** - TRUE if order had timing issue |
| `on_time_issue_excludes_earlies` | BOOLEAN | TRUE if late (excludes early orders) |
| `order_accuracy_issue` | BOOLEAN | TRUE if order had accuracy issue |

**OTR Calculation Pattern:**
```sql
-- Correct OTR calculation
ROUND((1 - SAFE_DIVIDE(
  COUNT(DISTINCT CASE WHEN io.on_time_issue THEN o.order_id END),
  COUNT(DISTINCT o.order_id)
)) * 100, 1) AS otr_pct
```

---

### `wonder-dw-prod-brd.orders.fct_order_rca`

Root Cause Analysis classifications for order imperfections.

| Field | Type | Description |
|-------|------|-------------|
| `order_id` | STRING | Unique order identifier |
| `order_imperfection_score` | FLOAT | Overall imperfection score |
| `primary_issue_type` | STRING | Main issue classification |
| `primary_issue_menu_item` | STRING | Menu item related to primary issue |
| `secondary_issue_type` | STRING | Secondary issue classification |
| `secondary_issue_menu_item` | STRING | Menu item related to secondary issue |

#### Primary Issue Type Values

| Value | Description |
|-------|-------------|
| `Forced Progression` | Order was manually progressed |
| `Missing Signal` | Expected signal was not received |
| `Bad Interaction` | Problematic human interaction |
| `Long Production` | Production took longer than expected |
| `Early Courier Arrival` | Courier arrived before food ready |
| `Late Courier Arrival` | Courier arrived late |

---

### `wonder-dw-prod-brd.orders.hdr_kitchen_order_item`

Kitchen sequencing timestamps and item-level metrics. **Critical for ticket time decomposition and equipment bottleneck analysis.**

#### Identity & Timing Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | STRING | Unique cooking task item ID |
| `order_id` | STRING | Order identifier |
| `hdr_id` | STRING | HDR location identifier |
| `menu_item_id` | STRING | Menu item identifier |
| `menu_item_name` | STRING | Human-readable item name |
| `item_number` | STRING | SKU/item number (used for CFF classification) |
| `order_number` | STRING | Human-readable order number |
| `t_o` | TIMESTAMP | Initial estimated order complete time |
| `t_cp` | TIMESTAMP | Customer promise / final estimated complete time |
| `order_assigned_to_pod_time` | TIMESTAMP | When order was assigned to pod |
| `service_date_et` | DATE | Service date in Eastern Time |
| `cooking_item_status` | STRING | `COMPLETED`, `IN_PROGRESS`, etc. |
| `order_status` | STRING | Order status |
| `order_channel` | STRING | `APP`, `WEB`, `POS`, etc. |
| `order_business_type` | STRING | Exclude `TRAINING` in analyses |

#### Item-Level Ticket Time Metrics (Critical for Decomposition)

| Field | Type | Description |
|-------|------|-------------|
| `item_queue_time_min` | FLOAT | Time item spent in queue before cooking |
| `production_time_min` | FLOAT | Actual item production/cook time |
| `delay_duration_mins` | FLOAT | Sequencer delay applied to item |
| `delay_start_time` | TIMESTAMP | When delay started |
| `item_first_focus_time` | TIMESTAMP | When item was first focused |

#### Equipment Step Time Fields (For Bottleneck Analysis)

**Expected (predicted) step times:**

**⚠️ UNIT WARNING**: Equipment-specific fields are in MINUTES, but total time fields are in SECONDS!

| Field | Type | Description |
|-------|------|-------------|
| `expected_fryer_step_time_mins` | FLOAT | Expected fryer time (MINUTES) |
| `expected_turbo_oven_step_time_mins` | FLOAT | Expected turbo oven time (MINUTES) |
| `expected_clamshell_step_time_mins` | FLOAT | Expected clamshell/press time (MINUTES) |
| `expected_water_bath_step_time_mins` | FLOAT | Expected water bath time (MINUTES) |
| `expected_press_step_time_mins` | FLOAT | Expected press time (MINUTES) |
| `expected_pizza_conveyor_step_time_mins` | FLOAT | Expected pizza conveyor time (MINUTES) |
| `expected_cook_time` | INTEGER | **Total expected cook time (SECONDS)** - Divide by 60 to convert to minutes |
| `expected_step_time` | INTEGER | **Total expected step time (SECONDS)** - Divide by 60 to convert to minutes |

**Actual step times:**
| Field | Type | Description |
|-------|------|-------------|
| `actual_fryer_step_time_mins` | FLOAT | Actual fryer time |
| `actual_turbo_oven_step_time_mins` | FLOAT | Actual turbo oven time |
| `actual_clamshell_step_time_mins` | FLOAT | Actual clamshell time |
| `actual_water_bath_step_time_mins` | FLOAT | Actual water bath time |
| `actual_press_step_time_mins` | FLOAT | Actual press time |
| `actual_pizza_conveyor_step_time_mins` | FLOAT | Actual pizza conveyor time |

**Usage - Equipment Bottleneck Identification:**
```sql
-- Identify primary equipment bottleneck by HDR
SELECT
  hdr_name,
  -- Check which equipment has highest queue time
  AVG(CASE WHEN expected_fryer_step_time_mins > 0 THEN item_queue_time_min END) AS fryer_queue,
  AVG(CASE WHEN expected_turbo_oven_step_time_mins > 0 THEN item_queue_time_min END) AS turbo_queue,
  AVG(CASE WHEN expected_press_step_time_mins > 0 THEN item_queue_time_min END) AS press_queue,
  -- Equipment overage (actual - expected)
  AVG(GREATEST(actual_fryer_step_time_mins - expected_fryer_step_time_mins, 0)) AS fryer_overage
FROM hdr_kitchen_order_item
WHERE cooking_item_status = 'COMPLETED'
  AND order_business_type != 'TRAINING'
GROUP BY 1
```

#### Cook From Frozen (CFF) Item Classification

**⚠️ CRITICAL: Cook From Frozen items use FRYERS, not turbo ovens. CFF growth drives fryer bottlenecks.**

CFF items are identified by `item_number`. The canonical list:
```sql
-- Cook From Frozen SKU list (use for classification)
-- Last verified: 2026-01-30
-- To update: Query secure-recipe-prod.recipe_v2.item_versions for items with "Frozen" in name
--            and procedures_appliance = 'FRYER' in item_line_builds
item_number IN (
  '8006134', '8006140', '8006150', '8007213', '8007214', '8007252', '8007271', 
  '8007277', '8007279', '8007280', '8007299', '8008266', '8008268', '8008269', 
  '8008270', '8008271', '8008275', '8008406', '8008407', '8008408', '8008410', 
  '8008412', '8008414', '8008415', '8008416', '8008417', '8008418', '8008421', 
  '8008422', '8008423', '8008493', '8008516', '8008567', '8008568', '8008569', 
  '8008570', '8008648', '8008651', '8008779', '8008780', '8008781', '8008782', 
  '8008793', '8008794', '8008795', '8008796', '8008809', '8009002', '8009068', 
  '8009096', '8009427', '8009454', '8009456', '8009622', '8009932', '8009955', 
  '8010062', '8010867'
)
```

**Order-Level CFF Classification (Correct Approach):**
```sql
-- Classify orders (not items) as containing frozen items
WITH orders_with_frozen AS (
  SELECT DISTINCT order_id
  FROM hdr_kitchen_order_item
  WHERE item_number IN ('8006134', '8006140', /* ... full list */)
)
SELECT
  o.order_id,
  CASE WHEN f.order_id IS NOT NULL THEN 'Contains Frozen' ELSE 'No Frozen' END AS cff_status,
  o.ticket_time_mins
FROM hdr_orders o
LEFT JOIN orders_with_frozen f ON o.order_id = f.order_id
```

**Usage - Sequencing Timestamps:**
```sql
SELECT
  order_id,
  MIN(t_o) AS initial_order_complete,
  MIN(t_cp) AS final_order_complete
FROM hdr_kitchen_order_item
WHERE t_o IS NOT NULL OR t_cp IS NOT NULL
GROUP BY 1
```

---

### `wonder-dw-prod-brd.orders.hdr_kitchen_vending_tasks`

Vending item tracking - items routed directly to vending pod near expo.

| Field | Type | Description |
|-------|------|-------------|
| `order_id` | STRING | Order identifier |
| `order_item_id` | STRING | Order item identifier |
| `item_id` | STRING | Vending task item ID |
| `order_number` | STRING | Human-readable order number |
| `hdr_id` | STRING | HDR location ID |
| `menu_item_name` | STRING | Menu item name |
| `quantity` | FLOAT | Item quantity |
| `type` | STRING | Vending item type |
| `status` | STRING | `COMPLETED`, etc. |
| `holding_temperature` | STRING | `WARM` or `AMBIENT` |
| `expo_scanned_flag` | BOOLEAN | Whether item was scanned at expo |
| `focus_time` | TIMESTAMP | When item was focused (NULL = force complete or held) |
| `created_time` | TIMESTAMP | When vending task was created |
| `pending_packaging_time` | DATETIME | When item reached pending packaging |
| `pending_bagging_time` | DATETIME | When item reached pending bagging |
| `completed_time` | TIMESTAMP | When vending task completed |
| `order_placed_time` | DATETIME | When order was placed |
| `order_released_time` | DATETIME | When order was released to kitchen |
| `pod_id` | STRING | Vending pod ID |
| `bundle_id` | STRING | Bundle identifier |

**Vending Sequencing Logic:**
1. Vending-only orders → Release immediately
2. Orders with ambient kitchen items → Wait until ANY ambient item reaches `pending_packaging`
3. Orders with only hot kitchen items → Wait until ALL hot items are `focused`

**Key Analysis Pattern:**
```sql
-- Compare vending focus to first kitchen item pending_package
WITH first_kitchen_pending AS (
  SELECT order_id, MIN(pending_package_time) AS first_pending
  FROM hdr_kitchen_order_item
  WHERE pending_package_time IS NOT NULL
  GROUP BY 1
)
SELECT
  v.order_id,
  v.focus_time,
  fkp.first_pending,
  CASE 
    WHEN v.focus_time IS NULL THEN 'FORCE_COMPLETE'
    WHEN v.focus_time < fkp.first_pending THEN 'EARLY_DROP'  -- Problem: early parking spot use
    ELSE 'LATE_DROP'  -- Expected: sequencer held correctly
  END AS vending_scenario
FROM hdr_kitchen_vending_tasks v
JOIN first_kitchen_pending fkp ON v.order_id = fkp.order_id
```

---

### `wonder-dw-prod-brd.orders.hdr_kitchen_order_parking_spots`

Parking spot reservations at expo station.

| Field | Type | Description |
|-------|------|-------------|
| `order_id` | STRING | Order identifier |
| `item_id` | STRING | Item ID |
| `parking_spot_id` | STRING | Parking spot identifier |
| `parking_spot_name` | STRING | Human-readable spot name |
| `parking_spot_temp` | STRING | `WARM` or `AMBIENT` |
| `parking_spot_reservation_time_utc` | TIMESTAMP | When spot was reserved |
| `rn` | INTEGER | Row number (use `rn = 1` for first reservation) |

**Parking Spot Concurrency Analysis:**
```sql
-- Daily max concurrent parking spots used
SELECT
  hdr_id,
  DATE(parking_spot_reservation_time_utc) AS date,
  parking_spot_temp,
  COUNT(DISTINCT parking_spot_id) AS spots_used
FROM hdr_kitchen_order_parking_spots
WHERE rn = 1
GROUP BY 1, 2, 3
```

---

### `wonder-dw-prod-brd.orders.imperfect_kitchen_items`

Item-level diagnostics for kitchen process inefficiencies. Each row represents one cooking task item.

#### Identity Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | STRING | Cooking task item ID (unique) |
| `order_id` | STRING | Order identifier |
| `order_number` | STRING | Human-readable order number |
| `order_assigned_to_pod_date` | DATE | Date item was assigned to pod |
| `hdr_id` | STRING | HDR location ID |
| `hdr_name` | STRING | HDR display name |
| `menu_item_name` | STRING | Menu item name |
| `order_status` | STRING | `COMPLETED`, etc. |

#### Actionable Flags (Count Toward `issue_count`)

| Field | Type | Description |
|-------|------|-------------|
| `has_kds_remake` | INTEGER | 1 if item was remade after cook |
| `has_bump` | INTEGER | 1 if item was returned to previous pod |
| `has_long_queue` | INTEGER | 1 if queue time >= 5 min |
| `has_long_pending_packaging` | INTEGER | 1 if pending packaging >= 5 min |
| `has_longer_than_expected_production_time` | INTEGER | 1 if actual production > expected + 3 min |
| `has_missing_signal` | INTEGER | 1 if production_time_min is 0 or NULL |
| `last_item_expo_wait_time_gt_2` | INTEGER | 1 if last item waited >2 min at expo |
| `has_reset` | INTEGER | 1 if cooking step/timer was reset |
| `has_missing_pouch` | INTEGER | 1 if expected hot hold was unavailable |
| `has_surprise_pouch` | INTEGER | 1 if unexpected hot hold appeared |
| `has_out_of_sync_sequencer_hh_alm` | INTEGER | 1 if sequencer/hot hold ALM mismatch |
| `has_sequencer_pantry_out_of_sync` | INTEGER | 1 if sequencer/pantry out of sync |
| `has_bad_interaction` | INTEGER | 1 if sequencer held ALM item incorrectly |
| `has_double_delay` | INTEGER | 1 if double delay applied |
| `has_trickling_violation` | INTEGER | 1 if FIFO violation detected |
| `has_critical_force_complete` | INTEGER | 1 if force completed at <10% expected time |

#### Force Complete Fields

| Field | Type | Description |
|-------|------|-------------|
| `has_force_progression` | INTEGER | 1 if item was force progressed |
| `has_premature_force_complete` | INTEGER | 1 if force was premature (before expected) |
| `has_critical_force_complete` | INTEGER | 1 if force completed at <10% expected time |
| `first_force_progression_pod_type` | STRING | Pod type where force occurred (HOT/COLD/HYBRID) |
| `first_force_progression_pod_code` | STRING | Specific pod code |
| `force_complete_severity_tier` | STRING | `Critical (Before Focus)`, `Critical (<10%)`, `High Concern (10-50%)`, `Low Concern (50-90%)`, `On Time (>=90%)` |
| `min_pct_of_expected_time_elapsed` | FLOAT | Lowest % of expected time across all pods |

#### Informational Flags (Not in `issue_count`)

| Field | Type | Description |
|-------|------|-------------|
| `has_delay_applied` | INTEGER | 1 if delay applied before cooking started |
| `has_unapplied_delay` | INTEGER | 1 if delay applied after cooking started |
| `has_hot_hold_eligible_component` | INTEGER | 1 if item has hot-hold-eligible component |
| `has_a_la_minute_component` | INTEGER | 1 if item needs fresh prep (ALM) |
| `is_speed_line` | INTEGER | 1 if hybrid pod with no expected appliance time |
| `has_shorter_than_expected_production_time` | INTEGER | 1 if actual production < expected - 3 min |

#### Trickling/FIFO Violation Fields

| Field | Type | Description |
|-------|------|-------------|
| `has_trickling_violation` | INTEGER | 1 if item started before longer-cook item |
| `trickling_cook_time_diff_mins` | FLOAT | Cook time difference causing trickling |
| `has_batched_trickling_violation` | INTEGER | 1 if trickling in batched item |
| `trickling_batch_size` | INTEGER | Batch size involved in trickling |

#### Line Skipper Fields

| Field | Type | Description |
|-------|------|-------------|
| `time_waiting` | INTEGER | Minutes item waited (for items >30 min) |
| `count_of_line_skippers` | INTEGER | Items that skipped ahead in line |
| `incoming_orders` | INTEGER | Items assigned during wait time |
| `skipper_ratio` | FLOAT | `count_of_line_skippers / incoming_orders` |

#### Context Fields

| Field | Type | Description |
|-------|------|-------------|
| `bad_interaction_root_cause` | STRING | Root cause of bad interaction |
| `pouch_variance_to_expected` | FLOAT | Variance from expected pouch state |
| `issue_count` | INTEGER | Sum of all actionable flags |

**Usage:** Aggregate to order level for order-level analysis:

```sql
SELECT
  order_id,
  MAX(has_force_progression) AS has_force_complete,
  SUM(has_force_progression) AS force_complete_item_count,
  MAX(has_premature_force_complete) AS has_premature_force_complete,
  MAX(has_critical_force_complete) AS has_critical_force_complete,
  MAX(force_complete_severity_tier) AS force_complete_severity_tier,
  SUM(issue_count) AS total_issue_count,
  MAX(has_bad_interaction) AS has_bad_interaction,
  MAX(has_trickling_violation) AS has_trickling_violation
FROM imperfect_kitchen_items
WHERE order_status = 'COMPLETED'
GROUP BY 1
```

---

## Dimension Tables

### `wonder-dw-prod-brd.dw.dim_hdrs`

HDR (High Density Restaurant) location attributes.

| Field | Type | Description |
|-------|------|-------------|
| `hdr_id` | STRING | Unique HDR identifier |
| `hdr_name` | STRING | HDR display name |
| `hdr_code` | STRING | Short HDR code |
| `hdr_class` | STRING | Year class (`2023`, `2024`, `2025`, `2025 New`, `2026 New`) |
| `population_type` | STRING | `Urban`, `Suburban`, `Big Box` |
| `location_type_category` | STRING | Location category |
| `design_type` | STRING | HDR design type |
| `market` | STRING | Geographic market |
| `state` | STRING | State code |
| `hdr_opening_date` | DATE | Date HDR opened |
| `calendar_weeks_from_opening_date` | INTEGER | Weeks since opening |
| `calendar_weeks_from_friends_family_start` | INTEGER | Weeks since F&F start (preferred for maturity) |

**Weeks Open Calculation:**
```sql
-- Use F&F start if available, otherwise opening date
COALESCE(
  h.calendar_weeks_from_friends_family_start, 
  h.calendar_weeks_from_opening_date
) AS weeks_open
```

#### HDR Class Values

| Value | Description |
|-------|-------------|
| `2023` | Mature HDRs opened in 2023 |
| `2024` | HDRs opened in 2024 |
| `2025` | HDRs opened in early 2025 |
| `2025 New` | NSO HDRs opened in late 2025 |
| `2026 New` | NSO HDRs opened in 2026 |

---

### `wonder-dw-prod-brd.dw.dim_hdr_restaurants`

Mapping between HDRs and restaurant instances.

| Field | Type | Description |
|-------|------|-------------|
| `hdr_id` | STRING | HDR location identifier |
| `restaurant_id` | STRING | Restaurant instance identifier |

---

### `wonder-dw-prod-brd.orders.order_restaurants`

Order to restaurant linkage.

| Field | Type | Description |
|-------|------|-------------|
| `order_id` | STRING | Order identifier |
| `restaurant_id` | STRING | Restaurant instance identifier |

---

## Join Patterns

### Basic OTR Query Join

```sql
SELECT
  o.*,
  ot.on_time_issue,
  ot.otr_sla_tier
FROM `wonder-dw-prod-brd.orders.hdr_orders` o
LEFT JOIN `wonder-dw-prod-brd.orders.hdr_on_time_orders` ot
  ON o.order_id = ot.order_id
WHERE o.order_status = 'COMPLETE'
```

### With HDR Dimensions

```sql
SELECT
  h.hdr_name,
  h.hdr_class,
  h.population_type,
  o.*,
  ot.on_time_issue,
  ot.otr_sla_tier
FROM `wonder-dw-prod-brd.orders.hdr_orders` o
JOIN `wonder-dw-prod-brd.dw.dim_hdrs` h
  ON o.hdr_id = h.hdr_id
LEFT JOIN `wonder-dw-prod-brd.orders.hdr_on_time_orders` ot
  ON o.order_id = ot.order_id
WHERE o.order_status = 'COMPLETE'
```

### Full WBR Query Join Pattern

This complex join is used for comprehensive OTR analysis with all dimensions:

```sql
FROM wonder-dw-prod-brd.dw.dim_hdrs AS dim_hdrs
LEFT JOIN wonder-dw-prod-brd.dw.dim_hdr_restaurants AS dim_hdr_restaurants 
  ON dim_hdrs.hdr_id = dim_hdr_restaurants.hdr_id
INNER JOIN wonder-dw-prod-brd.dw.dim_restaurants AS restaurants 
  ON restaurants.restaurant_id = dim_hdr_restaurants.restaurant_id
LEFT JOIN wonder-dw-prod-brd.restaurants.menu_items AS menu_items 
  ON restaurants.restaurant_id = menu_items.restaurant_id
  AND dim_hdr_restaurants.restaurant_id = menu_items.restaurant_id
  AND (restaurants.brand_category='WONDER_HDR' OR restaurants.brand_category='WONDER_LOCAL')
LEFT JOIN wonder-dw-prod-brd.orders.order_items AS hdr_order_items 
  ON menu_items.menu_item_id = hdr_order_items.menu_item_id
LEFT JOIN wonder-dw-prod-brd.orders.order_restaurants AS order_restaurants 
  ON dim_hdr_restaurants.restaurant_id = order_restaurants.restaurant_id
  AND hdr_order_items.restaurant_id = order_restaurants.restaurant_id
  AND hdr_order_items.order_id = order_restaurants.order_id
LEFT JOIN wonder-dw-prod-brd.orders.hdr_orders AS hdr_orders 
  ON dim_hdrs.hdr_id = hdr_orders.hdr_id
  AND hdr_orders.order_id = order_restaurants.order_id
LEFT JOIN wonder-dw-prod-brd.orders.imperfect_orders AS imperfect_orders 
  ON hdr_orders.order_id = imperfect_orders.order_id
LEFT JOIN wonder-dw-prod-brd.orders.hdr_on_time_orders AS hdr_on_time_orders 
  ON hdr_orders.order_id = hdr_on_time_orders.order_id
```

**Note:** This complex join creates multiple rows per order. Always use `COUNT(DISTINCT order_id)` for accurate counts.

---

## Field Value Reference

### dining_option Values
- `DELIVERY` - Courier delivery (~65% of orders)
- `PICKUP` - Customer pickup (~35% of orders)

### order_channel Values
- `APP` - Wonder mobile app (1P)
- `WEB` - Wonder website (1P)
- `IN_PERSON` - In-person at HDR (1P)
- `GRUB_HUB` - GrubHub marketplace (3P)
- `DOOR_DASH` - DoorDash marketplace (3P)
- `UBER_EATS` - Uber Eats marketplace (3P)

### order_status Values (for filtering)
- `COMPLETE` - Successfully delivered/picked up (use this for OTR)
- `CANCELED` - Order was canceled
- `PAYMENT_FAILED` - Payment failed

### brand_category Values
- `WONDER_HDR` - Standard Wonder HDR orders
- `WONDER_LOCAL` - Wonder Local orders

### order_business_type Values
- `WONDER_HDR` - Standard Wonder orders
- `WONDER_SPOT` - B2B/Wonder Spot orders
- `3P_PLATFORM_CORPORATE` - Corporate 3P orders

---

## Common Filter Patterns

### Standard OTR Filter Set

```sql
WHERE o.order_status = 'COMPLETE'
  AND o.brand_category = 'WONDER_HDR'
  -- Exclude Wonder Spot and 3P Corporate
  AND (o.order_business_type <> 'WONDER_SPOT' OR o.order_business_type IS NULL)
  AND (o.order_business_type <> '3P_PLATFORM_CORPORATE' OR o.order_business_type IS NULL)
```

### 1P Only Filter

```sql
WHERE o.order_channel IN ('APP', 'IN_PERSON', 'WEB')
```

### Recent Weeks Filter

```sql
WHERE o.service_date_et >= DATE_SUB(CURRENT_DATE('America/New_York'), INTERVAL 12 WEEK)
  AND o.service_date_et < DATE_TRUNC(CURRENT_DATE('America/New_York'), WEEK(MONDAY))
```

### NSO Only Filter

```sql
WHERE h.hdr_class IN ('2025 New', '2026 New')
```

### Peak Hour Filter

```sql
-- Peak hours: 11am-1pm lunch, 5pm-8pm dinner (Eastern)
WHERE EXTRACT(HOUR FROM DATETIME(o.order_placed_date_utc, 'America/New_York')) BETWEEN 11 AND 13 
   OR EXTRACT(HOUR FROM DATETIME(o.order_placed_date_utc, 'America/New_York')) BETWEEN 17 AND 20
```

---

## RCA Thresholds Reference

Standard thresholds used in root cause analysis:

| Metric | Threshold | Meaning |
|--------|-----------|---------|
| Kitchen "On Time" | ≤ 2 mins | `ready_for_pickup_sla_difference <= 2.0` |
| Kitchen "Late" | > 2 mins | `ready_for_pickup_sla_difference > 2.0` |
| Kitchen "Very Late" | > 5 mins | `ready_for_pickup_sla_difference > 5.0` |
| Courier Response "Fast" | ≤ 5 mins | `courier_response_time_mins <= 5.0` |
| Courier Response "Slow" | > 5 mins | `courier_response_time_mins > 5.0` |
| Courier Response "Very Slow" | > 10 mins | `courier_response_time_mins > 10.0` |
| Handoff "Fast" | ≤ 5 mins | `kitchen_handoff_time_mins <= 5.0` |
| Handoff "Slow" | > 5 mins | `kitchen_handoff_time_mins > 5.0` |
| Handoff "Very Slow" | > 8 mins | `kitchen_handoff_time_mins > 8.0` |
| Transit Error "Significant" | > 5 mins | `transit_error < -5.0` (negative = late) |

---

## Ticket Time Decomposition Framework

**Ticket Time is the primary driver of OTR outcomes.** Understanding what drives ticket time helps identify actionable root causes for OTR issues.

### The Ticket Time → OTR Connection

```
Higher Ticket Time → Higher likelihood of on_time_issue → Lower OTR
```

**Key Insight:** Ticket time decomposition helps answer "WHY is OTR bad?" by breaking down the components:

| Component | Source | Ownership |
|-----------|--------|-----------|
| Queue Time | Item-level (`item_queue_time_min`) | Capacity/Ops |
| Production/Cook Time | Item-level (`production_time_min`) | Kitchen Execution |
| Expo Wait Time | Order-level (`order_level_expo_wait_time_mins`) | Expo/Handoff |
| Frozen Impact | CFF item mix | Menu/1P Delivery |

### Ticket Time Decomposition Query Pattern

**⚠️ CRITICAL: Item-level metrics (queue, production) require aggregation to order level. Expo wait is already order-level but duplicates across item rows — use MAX not AVG.**

```sql
-- Full Ticket Time Decomposition by HDR
WITH order_item_metrics AS (
  SELECT
    items.order_id,
    items.hdr_id,
    AVG(items.item_queue_time_min) AS avg_queue_time,
    AVG(items.production_time_min) AS avg_production_time,
    -- CFF classification at order level
    MAX(CASE WHEN items.item_number IN ('8006134', /* ... */) THEN 1 ELSE 0 END) AS has_frozen_item,
    COUNT(items.id) AS item_count
  FROM `wonder-dw-prod-brd.orders.hdr_kitchen_order_item` items
  WHERE items.cooking_item_status = 'COMPLETED'
    AND items.order_business_type != 'TRAINING'
    AND items.order_status = 'COMPLETED'
  GROUP BY 1, 2
),
order_metrics AS (
  SELECT
    o.order_id,
    o.hdr_id,
    o.ticket_time_mins,
    -- Use MAX for expo wait (it repeats per item)
    MAX(o.order_level_expo_wait_time_mins) AS expo_wait_time
  FROM `wonder-dw-prod-brd.orders.hdr_orders` o
  WHERE o.order_status = 'COMPLETED'
    AND o.order_business_type != 'TRAINING'
  GROUP BY 1, 2, 3
)
SELECT
  h.hdr_name,
  AVG(om.ticket_time_mins) AS avg_ticket_time,
  AVG(oim.avg_queue_time) AS avg_queue,
  AVG(oim.avg_production_time) AS avg_production,
  AVG(om.expo_wait_time) AS avg_expo,
  AVG(oim.has_frozen_item) * 100 AS pct_orders_with_frozen,
  AVG(oim.item_count) AS avg_items_per_order
FROM order_metrics om
JOIN order_item_metrics oim ON om.order_id = oim.order_id
JOIN `wonder-dw-prod-brd.dw.dim_hdrs` h ON om.hdr_id = h.hdr_id
GROUP BY 1
ORDER BY avg_ticket_time DESC
```

### Decomposition Impact Attribution Formula

To understand what's DRIVING ticket time changes (baseline vs current):

```sql
-- Volume Impact: How much TT change is due to order volume change
Volume_Impact = (current_orders - baseline_orders) / baseline_orders * baseline_tt

-- Queue Impact: Change in queue time contribution
Queue_Impact = current_queue - baseline_queue

-- Cook Impact: Change in production time contribution
Cook_Impact = current_production - baseline_production

-- Expo Impact: Change in expo wait time contribution
Expo_Impact = current_expo - baseline_expo

-- Frozen Impact: TT difference from frozen mix change
Frozen_Impact = (current_frozen_pct - baseline_frozen_pct) * (frozen_tt - non_frozen_tt)

-- Items Per Order Impact: Complexity change
Items_Per_Order_Impact = (current_items_per_order - baseline_items_per_order) * baseline_production_time

-- Other/Residual: What's not explained by known factors
Other_Impact = TT_Change - (Queue_Impact + Cook_Impact + Expo_Impact + Frozen_Impact + Items_Per_Order_Impact)
```

### Equipment Bottleneck → Queue Time → Ticket Time Chain

**⚠️ CRITICAL: Cook From Frozen items use FRYERS. High CFF mix → fryer congestion → queue time increase → ticket time increase → OTR degradation.**

```
1P Delivery Growth → Higher CFF Mix → Fryer Demand ↑
                                            ↓
                                    Fryer Queue Time ↑
                                            ↓
                                    Item Queue Time ↑
                                            ↓
                                    Ticket Time ↑
                                            ↓
                                    OTR Degradation
```

**Equipment bottleneck identification pattern:**
```sql
SELECT
  hdr_name,
  CASE
    WHEN fryer_queue > turbo_queue AND fryer_queue > press_queue THEN 'FRYER'
    WHEN turbo_queue > press_queue THEN 'TURBO_OVEN'
    WHEN press_queue IS NOT NULL THEN 'PRESS'
    ELSE 'NONE/MIXED'
  END AS primary_bottleneck
FROM (
  SELECT
    h.hdr_name,
    AVG(CASE WHEN items.expected_fryer_step_time_mins > 0 THEN items.item_queue_time_min END) AS fryer_queue,
    AVG(CASE WHEN items.expected_turbo_oven_step_time_mins > 0 THEN items.item_queue_time_min END) AS turbo_queue,
    AVG(CASE WHEN items.expected_press_step_time_mins > 0 THEN items.item_queue_time_min END) AS press_queue
  FROM `wonder-dw-prod-brd.orders.hdr_kitchen_order_item` items
  JOIN `wonder-dw-prod-brd.dw.dim_hdrs` h ON items.hdr_id = h.hdr_id
  WHERE items.cooking_item_status = 'COMPLETED'
  GROUP BY 1
)
```

### Why "Frozen Impact" Looks Small in Decomposition

The decomposition formula shows Frozen Impact as mix shift only. **The REAL frozen impact is hidden in other components:**

| Where Frozen Impact Hides | Why |
|---------------------------|-----|
| **Queue Impact** | Fryer congestion from more frozen items |
| **Cook Impact** | Longer fry times for frozen items |
| **Expo Impact** | Orders waiting for fried items to complete |
| **Other Impact** | Cascading operational effects |

**True frozen impact estimation:**
- Stores with Fryer Queue >5 min: avg TT change ~+2.8 min
- Stores with Fryer Queue <3 min: avg TT change ~+0.6 min
- **Implied fryer/frozen impact: ~2.2 min** (not the 0.04 min shown in decomposition)

---

## Derived Metric Calculations

### Make Time (Kitchen Execution Excluding Queue)

```sql
actual_make_time_mins = COALESCE(actual_cook_duration_mins, 0) + COALESCE(actual_packaging_bagging_mins, 0)
estimated_make_time_mins = COALESCE(estimated_cook_duration_mins, 0) + COALESCE(estimated_packaging_bagging_mins, 0)
make_time_error = actual_make_time_mins - estimated_make_time_mins
```

### Ops Gap (Who's at Fault?)

```sql
ops_gap_mins = COALESCE(kitchen_handoff_time_mins, 0) - COALESCE(courier_response_time_mins, 0)
-- Positive = Ops is slower → Fix Ops
-- Negative = Logistics is slower → Fix Logistics
```

### Sit Time % Decomposition

```sql
pct_sit_time_courier_response = SAFE_DIVIDE(courier_response_time_mins, actual_pickup_waiting_duration_mins) * 100
pct_sit_time_kitchen_handoff = SAFE_DIVIDE(kitchen_handoff_time_mins, actual_pickup_waiting_duration_mins) * 100
```

---

## Hot Hold Management Tables

### `hdr_kitchen_pod_item` (Dev)

**Location:** `wonder-dw-dev-brd.dbt_mbouchene_brd_orders.hdr_kitchen_pod_item`

Task-level hot hold compliance data.

| Field | Type | Description |
|-------|------|-------------|
| `task_id` | STRING | Unique task identifier |
| `cooking_task_item_id` | STRING | Links to `hdr_kitchen_order_item.id` |
| `consumption_type` | STRING | `single` or `multi` (batch) |
| `hot_hold_stock_item_number` | STRING | Stock item number for hot hold |
| `hot_hold_eligible` | INT64 | 1 if item is hot-hold-eligible at this HDR |
| `system_overstated_hh_inventory` | INT64 | **Missing Pouch** - system said available, wasn't |
| `system_understated_hh_inventory` | INT64 | **Surprise Pouch** - system said unavailable, was |
| `hot_hold_consumption_quantity` | FLOAT64 | Quantity consumed from hot hold |
| `hh_appliance_time_min` | FLOAT64 | Retherm time in minutes |
| `hot_hold_holding_time_minutes` | FLOAT64 | Time item was in hot hold |
| `component_item_number` | STRING | Component item number |
| `title` | STRING | Item name/description |

### `int_hot_hold_components`

**Purpose:** Location × Item × Date hot hold eligibility configuration.

| Field | Type | Description |
|-------|------|-------------|
| `hdr_id` | STRING | HDR location ID |
| `service_date` | DATE | Date eligibility applies |
| `daypart` | STRING | Daypart (lunch, dinner, etc.) |
| `component_item_number` | STRING | Component item number |
| `component_item_name` | STRING | Human-readable item name |
| `hot_hold_item_number` | STRING | Hot hold stock item number |
| `has_sku_replacement` | BOOLEAN | Item has SKU replacement |
| `inventory_item_number` | STRING | Effective inventory item number |
| `usage_quantity` | FLOAT64 | BOM usage quantity |
| `holding_time_minutes` | FLOAT64 | Max hot hold time (minutes) |
| `retherm_time_minutes` | FLOAT64 | Retherm time (minutes) |
| `units_per_drop` | FLOAT64 | Units per inventory drop |

### Hot Hold Compliance Calculations

```sql
-- Missing Pouch Rate (system overstated)
missing_pouch_pct = COUNT(CASE WHEN hot_hold_eligible = 1 AND system_overstated_hh_inventory = 1 THEN task_id END) 
                  / COUNT(CASE WHEN hot_hold_eligible = 1 OR hot_hold_consumption_quantity IS NOT NULL THEN task_id END)

-- Surprise Pouch Rate (system understated)
surprise_pouch_pct = COUNT(CASE WHEN hot_hold_eligible = 1 AND system_understated_hh_inventory = 1 THEN task_id END)
                   / COUNT(CASE WHEN hot_hold_eligible = 1 OR hot_hold_consumption_quantity IS NOT NULL THEN task_id END)

-- Compliance Rate
compliance_pct = 1 - missing_pouch_pct - surprise_pouch_pct
```

