# Wonder Orders - Schema Reference

## Overview

The Wonder orders dataset contains comprehensive order and sales data for all Wonder HDR locations. This includes order headers with financial and timing information, plus item-level detail for menu items within each order. Data is stored in BigQuery and refreshed regularly from operational systems.

## Database Connection

- **BigQuery Dataset**: `wonder-dw-prod-brd.orders`
- **Access**: Via bq CLI or BigQuery Console
- **Data Source**: Data warehouse with transformed/joined data from operational systems

---

## Core Tables

### hdr_orders

**Purpose**: Header-level information for each order including identifiers, status, financial totals, and timing metrics across the order lifecycle.

**Row Count**: ~5M orders (as of Nov 2025)

**Schema Categories**:

#### Order Identifiers
```sql
order_id                    STRING      -- Primary key, unique order identifier
order_number                STRING      -- Human-readable order number (e.g., "5368865")
user_id                     STRING      -- Customer identifier
hdr_id                      STRING      -- Restaurant/HDR location identifier
fulfillment_id              STRING      -- Fulfillment system identifier
channel_order_id            STRING      -- External channel order ID (for marketplaces)
channel_order_display_id    STRING      -- External channel display ID
```

**Key Fields**:
- `order_id` - Use for joins and unique counting
- `order_number` - Use for display to users
- `hdr_id` - Join to HDR/location reference tables
- `user_id` - Join to customer tables

#### Order Placement & Timing
```sql
order_placed_date_utc       TIMESTAMP   -- When order was placed (UTC)
service_date_et             DATE        -- Service date in Eastern Time
accepted_time_utc           TIMESTAMP   -- When HDR accepted the order
canceled_time_utc           TIMESTAMP   -- When order was canceled (if applicable)
order_completed_time_utc    TIMESTAMP   -- When order completed
actual_completed_time_utc   TIMESTAMP   -- Actual completion time
```

**Key Fields**:
- `order_placed_date_utc` - Use for time-of-day analysis (convert to ET)
- `service_date_et` - Use for daily aggregations (already in ET)

**Timezone Pattern**:
```sql
-- Convert UTC to Eastern Time
DATETIME(order_placed_date_utc, 'America/New_York') as order_time_et
```

#### Order Status & Classification
```sql
order_status                STRING      -- Current order status
cancel_reason               STRING      -- Reason for cancellation (if canceled)
order_business_type         STRING      -- Business classification (CRITICAL for tip analysis)
brand_category              STRING      -- Brand category
component_order_flag        STRING      -- Whether this is a component order
delayed_order_flag          STRING      -- Whether order was delayed
scanned_order_flag          STRING      -- Whether order went through scanning
corporate_client_id         STRING      -- Corporate client ID (populated for WONDER_SPOT)
corporate_client_name       STRING      -- Corporate client name (populated for WONDER_SPOT)
```

**Common Values for order_status**:
- `COMPLETE` - Successfully completed (96% of orders)
- `PAYMENT_FAILED` - Payment failed
- `CANCELED` - Order canceled
- `READY_FOR_PICKUP` - Ready for courier pickup
- `IN_COOKING` - Being prepared
- `PAID` - Payment received, awaiting assignment
- `DELIVERING` - In transit
- `ASSIGNED` - Assigned to kitchen
- `PENDING_PAYMENT` - Awaiting payment

**Usage**:
```sql
-- Filter to completed orders for revenue analysis
WHERE order_status = 'COMPLETE'

-- Exclude failed/canceled orders
WHERE order_status NOT IN ('PAYMENT_FAILED', 'CANCELED')
```

**Common Values for order_business_type**:
- `WONDER_HDR` - Direct Wonder orders from HDR locations
- `WONDER_LOCAL` - Wonder Local orders
- `3P_ORDER_PLATFORM` - Third-party marketplace orders (DoorDash, Grubhub, UberEats)
- `WONDER_SPOT` - B2B corporate lunch service
- `3P_PLATFORM_CORPORATE` - Corporate orders through marketplaces

**For tip analysis**: Filter to `order_business_type IN ('WONDER_HDR', 'WONDER_LOCAL')` since 3P and Wonder Spot orders show 0% tips (tips flow through external platforms or are corporate-billed).

#### Channel & Delivery Information
```sql
order_channel               STRING      -- Order source channel
dining_option               STRING      -- Delivery or pickup
delivery_zone_id            STRING      -- Delivery zone identifier
courier_platform            STRING      -- Courier platform used
delivery_task_provider      STRING      -- Delivery task provider
delivery_transportation_type STRING     -- Transportation method
channel_courier_type        STRING      -- Courier type for channel orders
```

**Common Values for order_channel**:
- `APP` - Wonder mobile app (55k/week, highest volume)
- `WEB` - Wonder website
- `GRUB_HUB` - GrubHub marketplace (15k/week)
- `DOOR_DASH` - DoorDash marketplace (13k/week)
- `UBER_EATS` - Uber Eats marketplace (2k/week)
- `IN_PERSON` - In-person at HDR (12k/week)

**Common Values for dining_option**:
- `DELIVERY` - Courier delivery (~65% of orders)
- `PICKUP` - Customer pickup (~35% of orders)

**Usage**:
```sql
-- Compare channel performance
SELECT order_channel, dining_option, COUNT(*) as orders
FROM `wonder-dw-prod-brd.orders.hdr_orders`
WHERE order_status = 'COMPLETE'
GROUP BY order_channel, dining_option;
```

#### Item Counts
```sql
item_count                  INTEGER     -- Number of distinct items in order
item_quantity               INTEGER     -- Total quantity of all items
need_utensils               BOOLEAN     -- Whether customer requested utensils
```

#### Financial Fields
```sql
subtotal                    NUMERIC     -- Order subtotal (items only)
tax                         NUMERIC     -- Tax amount
tip_amount                  NUMERIC     -- Tip amount
delivery_fee                NUMERIC     -- Delivery fee charged
service_fee                 NUMERIC     -- Service fee charged
small_order_fee             NUMERIC     -- Small order fee (if applicable)
hospitality_fee             NUMERIC     -- Hospitality fee
fast_pass_fee               NUMERIC     -- Fast pass fee (if applicable)
total_amount                NUMERIC     -- Total order amount
credit_amount_used          NUMERIC     -- Credit/promo amount used
discount                    NUMERIC     -- Discount amount
promo_amount                NUMERIC     -- Promotion discount amount
commission_amount           NUMERIC     -- Commission amount
commission_rate             FLOAT       -- Commission rate
```

**Key Fields**:
- `subtotal` - Items only, before fees/taxes
- `total_amount` - Final amount charged to customer
- `tip_amount` - Customer tip
- `delivery_fee` - Delivery charge
- `service_fee` - Service fee

**Usage**:
```sql
-- Calculate revenue and average order value
SELECT
  SUM(total_amount) as total_revenue,
  AVG(total_amount) as avg_order_value,
  SUM(subtotal) as total_item_sales,
  SUM(tax) as total_tax,
  SUM(tip_amount) as total_tips
FROM `wonder-dw-prod-brd.orders.hdr_orders`
WHERE order_status = 'COMPLETE';
```

#### Customer-Facing Timing
```sql
customer_facing_estimated_delivery_time_lower_utc  TIMESTAMP  -- Promised delivery window lower
customer_facing_estimated_delivery_time_upper_utc  TIMESTAMP  -- Promised delivery window upper
original_customer_facing_eta_utc                   TIMESTAMP  -- Original ETA mid-point
original_customer_facing_eta_lower_utc             TIMESTAMP  -- Original ETA lower bound
original_customer_facing_eta_upper_utc             TIMESTAMP  -- Original ETA upper bound
modified_delivery_time_utc                         TIMESTAMP  -- Modified delivery time (if changed)
pre_checkout_eta_mid_utc                           TIMESTAMP  -- ETA shown at checkout
pre_check_out_eta_lower_utc                        TIMESTAMP  -- Checkout ETA lower
pre_check_out_eta_upper_utc                        TIMESTAMP  -- Checkout ETA upper
```

#### Expected Timing (System Estimates)
```sql
expected_cooking_start_time_utc           TIMESTAMP  -- Expected cooking start
expected_cooking_finish_time_utc          TIMESTAMP  -- Expected cooking finish
expected_ready_for_pickup_time_utc        TIMESTAMP  -- Expected ready for pickup
expected_ready_for_pickup_time_lower_utc  TIMESTAMP  -- Expected ready lower bound
expected_ready_for_pickup_time_upper_utc  TIMESTAMP  -- Expected ready upper bound
expected_pickup_time_utc                  TIMESTAMP  -- Expected courier pickup
expected_arrival_time_utc                 TIMESTAMP  -- Expected courier arrival
expected_delivery_time_utc                TIMESTAMP  -- Expected delivery
expected_delivery_time_lower_utc          TIMESTAMP  -- Expected delivery lower
expected_delivery_time_upper_utc          TIMESTAMP  -- Expected delivery upper
expected_assign_time_utc                  TIMESTAMP  -- Expected assignment time
```

#### Last Estimated Timing (Most Recent Estimates)
```sql
last_estimated_delivery_time_utc          TIMESTAMP  -- Latest delivery estimate
last_estimated_delivery_time_lower_utc    TIMESTAMP  -- Latest delivery lower
last_estimated_delivery_time_upper_utc    TIMESTAMP  -- Latest delivery upper
last_estimated_cooking_start_time_utc     TIMESTAMP  -- Latest cooking start estimate
last_estimated_cooking_finish_time_utc    TIMESTAMP  -- Latest cooking finish estimate
last_estimated_ready_for_pickup_time_utc  TIMESTAMP  -- Latest pickup ready estimate
last_estimated_ready_for_pickup_time_lower_utc TIMESTAMP -- Latest pickup ready lower
last_estimated_ready_for_pickup_time_upper_utc TIMESTAMP -- Latest pickup ready upper
last_estimated_pickup_time_utc            TIMESTAMP  -- Latest pickup estimate
last_estimated_arrival_time_utc           TIMESTAMP  -- Latest arrival estimate
```

#### Actual Timing (What Really Happened)
```sql
actual_cooking_start_time_utc             TIMESTAMP  -- When cooking actually started
actual_cooking_finish_time_utc            TIMESTAMP  -- When cooking actually finished
actual_ready_for_pickup_time_utc          TIMESTAMP  -- When order was ready for pickup
actual_pickup_time_utc                    TIMESTAMP  -- When courier picked up order
pickup_arrived_time_utc                   TIMESTAMP  -- When courier arrived for pickup
actual_arrival_time_utc                   TIMESTAMP  -- When courier arrived at customer
actual_delivery_time_utc                  TIMESTAMP  -- When order was delivered
order_started_time_utc                    TIMESTAMP  -- When order started being prepared
order_pending_bagging_utc                 TIMESTAMP  -- When order entered bagging queue
order_assigned_to_pod_time_utc            TIMESTAMP  -- When assigned to pod
order_first_focus_time_utc                TIMESTAMP  -- When first focused
order_first_assigned_time_utc             TIMESTAMP  -- When first assigned
```

#### Order-to-Eat (O2E) and Service Windows
```sql
o2e_window_time_lower_utc   TIMESTAMP  -- O2E window lower bound
o2e_window_time_upper_utc   TIMESTAMP  -- O2E window upper bound
service_time_type           STRING     -- Service time type
schedule_type               STRING     -- Schedule type (ASAP vs scheduled)
```

#### Estimated Duration Metrics (Minutes)
```sql
estimated_o2e_mins                      FLOAT  -- Estimated total order-to-eat time
estimated_queue_mins                    FLOAT  -- Estimated queue time
estimated_cook_duration_mins            FLOAT  -- Estimated cooking duration
estimated_queue_cook_mins               FLOAT  -- Estimated queue + cook time
estimated_packaging_bagging_mins        FLOAT  -- Estimated packaging/bagging time
estimated_pickup_waiting_duration_mins  FLOAT  -- Estimated pickup wait time
estimated_transit_mins                  FLOAT  -- Estimated transit time
estimated_dropoff_mins                  FLOAT  -- Estimated dropoff time
estimated_delivery_duration_mins        FLOAT  -- Estimated total delivery time
```

**Key Field**:
- `estimated_o2e_mins` - Total estimated time from order placed to eat

#### Actual Duration Metrics (Minutes)
```sql
actual_o2e_mins                         FLOAT  -- Actual total order-to-eat time
wonder_1p_o2e_mins                      FLOAT  -- Wonder first-party O2E time
actual_queue_mins                       FLOAT  -- Actual queue time before cooking
actual_kds_queue_mins                   FLOAT  -- Actual KDS queue time
actual_prep_queue_mins                  FLOAT  -- Actual prep queue time
actual_cook_duration_mins               FLOAT  -- Actual cooking duration
actual_queue_cook_mins                  FLOAT  -- Actual queue + cook time
actual_packaging_bagging_mins           FLOAT  -- Actual packaging/bagging time
actual_packaging_mins                   FLOAT  -- Actual packaging time
actual_active_bagging_duration_sec      INTEGER -- Active bagging duration (seconds)
actual_order_runner_duration_sec        INTEGER -- Order runner duration (seconds)
actual_order_runner_duration_mins       FLOAT  -- Order runner duration (minutes)
actual_scanner_queue_sec                INTEGER -- Scanner queue time (seconds)
actual_scanner_queue_mins               FLOAT  -- Scanner queue time (minutes)
actual_pickup_waiting_duration_mins     FLOAT  -- Actual pickup wait time
actual_transit_mins                     FLOAT  -- Actual transit time
actual_dropoff_mins                     FLOAT  -- Actual dropoff time
actual_delivery_duration_mins           FLOAT  -- Actual total delivery time
ticket_time_mins                        FLOAT  -- Ticket time
```

**Key Fields**:
- `actual_o2e_mins` - Actual total time from placed to eat (primary metric)
- `actual_queue_mins` - Time order waited before cooking
- `actual_cook_duration_mins` - Time spent cooking
- `actual_packaging_bagging_mins` - Time spent packaging
- `actual_delivery_duration_mins` - Time from pickup to delivery

**Usage**:
```sql
-- Analyze O2E performance with breakdown
SELECT
  hdr_id,
  AVG(actual_o2e_mins) as avg_o2e,
  AVG(actual_queue_mins) as avg_queue,
  AVG(actual_cook_duration_mins) as avg_cook,
  AVG(actual_delivery_duration_mins) as avg_delivery
FROM `wonder-dw-prod-brd.orders.hdr_orders`
WHERE order_status = 'COMPLETE'
  AND actual_o2e_mins IS NOT NULL
GROUP BY hdr_id;
```

#### Timing Error/Difference Metrics
```sql
delivery_sla_difference                 FLOAT  -- Actual vs promised delivery (negative = early)
ready_for_pickup_sla_difference         FLOAT  -- Ready for pickup vs SLA difference
pickup_sla_difference                   FLOAT  -- Pickup vs SLA difference
browse_delivery_sla_difference          FLOAT  -- Browse delivery SLA difference
browse_pickup_sla_difference            FLOAT  -- Browse pickup SLA difference
browse_ready_for_pickup_sla_difference  FLOAT  -- Browse ready for pickup difference
queue_error                             FLOAT  -- Queue time error
cook_error                              FLOAT  -- Cook time error
queue_cook_error                        FLOAT  -- Queue + cook error
packaging_bagging_error                 FLOAT  -- Packaging/bagging error
pickup_error                            FLOAT  -- Pickup error
transit_error                           FLOAT  -- Transit error
dropoff_error                           FLOAT  -- Dropoff error
delivery_error                          FLOAT  -- Delivery error
total_eta_error                         FLOAT  -- Total ETA error
total_absolute_eta_error                FLOAT  -- Total absolute ETA error
```

**Key Fields**:
- `delivery_sla_difference` - Minutes late (positive) or early (negative) from promised time
- `total_eta_error` - Overall accuracy of time estimate

**Usage**:
```sql
-- Calculate on-time delivery rate
SELECT
  COUNTIF(delivery_sla_difference <= 0) / COUNT(*) * 100 as on_time_rate_pct,
  AVG(delivery_sla_difference) as avg_sla_diff_mins
FROM `wonder-dw-prod-brd.orders.hdr_orders`
WHERE order_status = 'COMPLETE'
  AND dining_option = 'DELIVERY'
  AND delivery_sla_difference IS NOT NULL;
```

#### Courier Metrics
```sql
courier_response_time_mins              FLOAT  -- Time for courier to respond
kitchen_handoff_time_mins               FLOAT  -- Time for kitchen handoff
pickup_start_to_arrived_mins            FLOAT  -- Pickup start to arrived duration
pickup_arrived_to_completed_mins        FLOAT  -- Pickup arrived to completed duration
```

#### Order Level Expo Wait Times
```sql
order_level_expo_wait_time_mins            FLOAT  -- Order level expo wait
menu_item_order_level_expo_wait_time_mins  FLOAT  -- Menu item expo wait
hot_item_order_level_expo_wait_time_mins   FLOAT  -- Hot item expo wait
hot_menu_item_order_level_expo_wait_time_mins FLOAT -- Hot menu item expo wait
```

#### Scanning Metrics
```sql
expected_scanned_item_count   INTEGER  -- Expected number of items to scan
actual_incomplete_item_scans  INTEGER  -- Number of incomplete scans
```

#### Restaurant Information
```sql
restaurant_ids          STRING (repeated)  -- Array of restaurant IDs in order
num_restaurants         INTEGER            -- Number of restaurants in order
```

**Usage**:
```sql
-- Unnest repeated field to get individual restaurants
SELECT order_id, restaurant_id
FROM `wonder-dw-prod-brd.orders.hdr_orders`,
UNNEST(restaurant_ids) as restaurant_id;
```

#### Tip Information
```sql
tip_type   STRING  -- Type of tip (pre-tip vs post-tip) - NOT POPULATED (all NULL)
```

**Tip Analysis Notes**:
- `tip_type` field is not populated (all NULL values)
- Tips are delivery-only - pickup orders rarely have tips
- For accurate tip rates, filter to `order_business_type IN ('WONDER_HDR', 'WONDER_LOCAL')` to exclude 3P marketplace and Wonder Spot orders
- Direct Wonder delivery orders: ~91% tip rate, ~16% of subtotal when tipped

---

### order_items

**Purpose**: Item-level detail for each menu item within an order, including pricing, quantities, and fees allocated to each item.

**Row Count**: ~15M items (as of Nov 2025)

**Schema**:

#### Item Identifiers
```sql
order_item_id           STRING  -- Primary key, unique item identifier
order_id                STRING  -- Foreign key to hdr_orders.order_id
restaurant_id           STRING  -- Restaurant/brand ID for this item
menu_item_id            STRING  -- Menu item identifier
item_number             STRING  -- Item number within order
bundle_item_id          STRING  -- Bundle item identifier (if part of bundle)
brand_bundle_item_id    STRING  -- Brand bundle item identifier
```

**Key Fields**:
- `order_item_id` - Unique item identifier
- `order_id` - Join to hdr_orders
- `restaurant_id` - Which brand/restaurant this item is from
- `menu_item_id` - Menu item reference

**Join Pattern**:
```sql
-- Join orders to items
FROM `wonder-dw-prod-brd.orders.hdr_orders` o
JOIN `wonder-dw-prod-brd.orders.order_items` oi
  ON o.order_id = oi.order_id
```

#### Menu Item Information
```sql
menu_item_name              STRING  -- Display name of menu item
menu_item_category_id       STRING  -- Category identifier
menu_item_category_name     STRING  -- Category display name (e.g., "Main Courses", "Sides")
image_key                   STRING  -- Image reference key
item_subtype                STRING  -- Item subtype
business_line               STRING  -- Business line (e.g., "WONDER_HDR")
```

**Key Fields**:
- `menu_item_name` - Item name for display and grouping
- `menu_item_category_name` - Use for category-level analysis

**Usage**:
```sql
-- Top selling items by category
SELECT
  menu_item_category_name,
  menu_item_name,
  SUM(order_quantity) as total_sold
FROM `wonder-dw-prod-brd.orders.order_items` oi
JOIN `wonder-dw-prod-brd.orders.hdr_orders` o ON oi.order_id = o.order_id
WHERE o.order_status = 'COMPLETE'
GROUP BY menu_item_category_name, menu_item_name
ORDER BY total_sold DESC;
```

#### Pricing
```sql
base_price   NUMERIC  -- Base price of item
unit_price   NUMERIC  -- Actual unit price charged (may include modifications)
```

**Key Fields**:
- `unit_price` - Price actually charged per item

#### Quantities
```sql
order_quantity  INTEGER  -- Quantity ordered
ship_quantity   INTEGER  -- Quantity shipped/fulfilled
```

#### Item-Level Financial Fields
```sql
subtotal                    NUMERIC  -- Item subtotal (unit_price * quantity)
tax                         NUMERIC  -- Tax allocated to this item
total_amount                NUMERIC  -- Total amount for this item
tip                         NUMERIC  -- Tip allocated to this item
delivery_fee                NUMERIC  -- Delivery fee allocated to this item
discount                    NUMERIC  -- Discount for this item
service_fee                 NUMERIC  -- Service fee allocated to this item
small_order_fee             NUMERIC  -- Small order fee allocated
expected_small_order_fee    NUMERIC  -- Expected small order fee
adjust_small_order_fee      NUMERIC  -- Adjustment to small order fee
hospitality_fee             NUMERIC  -- Hospitality fee allocated
initial_hospitality_fee     NUMERIC  -- Initial hospitality fee
expected_hospitality_fee    NUMERIC  -- Expected hospitality fee
hospitality_fee_tax         NUMERIC  -- Tax on hospitality fee
adjust_hospitality_fee      NUMERIC  -- Adjustment to hospitality fee
adjust_hospitality_fee_tax  NUMERIC  -- Adjustment to hospitality fee tax
promotion                   NUMERIC  -- Promotion discount
initial_promotion           NUMERIC  -- Initial promotion amount
adjust_service_fee          NUMERIC  -- Service fee adjustment
fast_pass_fee               NUMERIC  -- Fast pass fee
initial_fast_pass_fee       NUMERIC  -- Initial fast pass fee
adjust_fast_pass_fee        NUMERIC  -- Fast pass fee adjustment
bundle_discount             NUMERIC  -- Bundle discount amount
gov                         NUMERIC  -- Government fees/taxes
```

**Key Fields**:
- `subtotal` - Item revenue before fees
- `total_amount` - Total revenue for item including fees
- `tax` - Tax portion

**Usage**:
```sql
-- Item-level revenue with proper aggregation
SELECT
  menu_item_name,
  SUM(order_quantity) as units_sold,
  ROUND(SUM(subtotal), 2) as item_subtotal,
  ROUND(SUM(total_amount), 2) as item_total_revenue
FROM `wonder-dw-prod-brd.orders.order_items` oi
JOIN `wonder-dw-prod-brd.orders.hdr_orders` o ON oi.order_id = o.order_id
WHERE o.order_status = 'COMPLETE'
GROUP BY menu_item_name;
```

#### Marketplace Refunds
```sql
marketplace_refund_item_subtotal  INTEGER  -- Marketplace refund for item subtotal
marketplace_refund_tax            INTEGER  -- Marketplace refund for tax
marketplace_refund_delivery       INTEGER  -- Marketplace refund for delivery
marketplace_final_amount          INTEGER  -- Final amount after marketplace refund
```

#### Metadata
```sql
created_time  DATETIME  -- When item record was created
created_by    STRING    -- Who created the record
special_instructions  INTEGER  -- Whether item has special instructions
```

---

## Key Relationships

### Order to Items (One-to-Many)

One order can have multiple items:

```sql
-- Get order with all items
SELECT
  o.order_id,
  o.order_number,
  o.total_amount as order_total,
  oi.menu_item_name,
  oi.order_quantity,
  oi.total_amount as item_total
FROM `wonder-dw-prod-brd.orders.hdr_orders` o
JOIN `wonder-dw-prod-brd.orders.order_items` oi
  ON o.order_id = oi.order_id
WHERE o.order_id = 'abc123';
```

**WARNING**: When joining to items, remember that each order will appear multiple times (once per item). Use `DISTINCT order_id` when counting orders:

```sql
-- CORRECT: Count distinct orders
SELECT COUNT(DISTINCT o.order_id) as order_count
FROM `wonder-dw-prod-brd.orders.hdr_orders` o
JOIN `wonder-dw-prod-brd.orders.order_items` oi ON o.order_id = oi.order_id;

-- WRONG: Will overcount orders
SELECT COUNT(*) as order_count  -- This counts items, not orders!
FROM `wonder-dw-prod-brd.orders.hdr_orders` o
JOIN `wonder-dw-prod-brd.orders.order_items` oi ON o.order_id = oi.order_id;
```

---

## Related Tables

### dim_restaurants (Restaurant Instance Reference)

**Purpose**: Dimension table containing restaurant instance details (specific brand at specific HDR location) including names, chef/owner info, cuisine types, and operational settings.

**Location**: `wonder-dw-prod-brd.dw.dim_restaurants`

**Row Count**: ~120K rows (includes all historical restaurant configurations)

**CRITICAL**: This table represents **restaurant instances**, NOT brands. Each row is a specific brand at a specific HDR location.

**Key Fields**:
```sql
restaurant_id                 STRING   -- Primary key, joins to order_items.restaurant_id (instance ID)
restaurant_name               STRING   -- Display name with location (e.g., "Limesalt Fishtown", "Bobby Flay Steak HDR UWS")
restaurant_brand_id           STRING   -- Foreign key to dim_restaurant_brands (the actual brand)
chef_owner                    STRING   -- Chef/owner name (e.g., "Bobby Flay", "Marcus Samuelsson")
primary_cuisine               STRING   -- Primary cuisine type
secondary_cuisine             STRING   -- Secondary cuisine type
restaurant_concept_type       STRING   -- Concept type classification
brand_category                STRING   -- Brand category
business_line                 STRING   -- Business line (e.g., "WONDER_HDR")
partnership_type              STRING   -- Partnership type
publish_status                STRING   -- Publication status
is_deleted                    BOOLEAN  -- Whether restaurant instance is deleted
```

**Important Notes**:
- `restaurant_id` represents a brand instance at a specific HDR (e.g., "Limesalt at Fishtown")
- `restaurant_name` includes both brand and location (e.g., "Limesalt Fishtown")
- To aggregate by brand across all locations, join to `dim_restaurant_brands` via `restaurant_brand_id`
- **DO NOT** use REGEXP_EXTRACT to parse brand names - use the proper join to dim_restaurant_brands
- Table contains historical records; filter by `is_deleted = false` for active instances

**Join Pattern for Restaurant Instances**:
```sql
-- Join order items to restaurant instances (shows "Limesalt Fishtown" separately from "Limesalt Yardley")
FROM `wonder-dw-prod-brd.orders.order_items` oi
JOIN `wonder-dw-prod-brd.dw.dim_restaurants` r
  ON oi.restaurant_id = r.restaurant_id
WHERE r.is_deleted = false
```

**Join Pattern for Restaurant Brands**:
```sql
-- Join to brands to aggregate across all locations (shows "Limesalt" as one brand)
FROM `wonder-dw-prod-brd.orders.order_items` oi
JOIN `wonder-dw-prod-brd.dw.dim_restaurants` r
  ON oi.restaurant_id = r.restaurant_id
JOIN `wonder-dw-prod-brd.dw.dim_restaurant_brands` rb
  ON r.restaurant_brand_id = rb.restaurant_brand_id
WHERE r.is_deleted = false
```

### dim_restaurant_brands (Restaurant Brand Reference)

**Purpose**: Dimension table containing true restaurant brand/concept information aggregated across all HDR locations. This is the table to use when analyzing brand performance.

**Location**: `wonder-dw-prod-brd.dw.dim_restaurant_brands`

**Row Count**: ~53 rows (one per unique brand/concept)

**Key Fields**:
```sql
restaurant_brand_id           STRING   -- Primary key, joins to dim_restaurants.restaurant_brand_id
restaurant_brand_name         STRING   -- Brand name (e.g., "Limesalt", "Bobby Flay Steak")
restaurant_brand_nickname     STRING   -- Brand nickname/short name
short_description             STRING   -- Brief description of the brand
long_description              STRING   -- Detailed description
price_rating                  INTEGER  -- Price tier (1-4, $-$$$$)
```

**Important Notes**:
- This is the authoritative source for brand-level analysis
- One row per brand concept across all locations
- `restaurant_brand_name` does NOT include location (just "Limesalt", not "Limesalt Fishtown")

**Join Pattern**:
```sql
-- Full chain from orders → items → restaurant instances → brands
FROM `wonder-dw-prod-brd.orders.order_items` oi
JOIN `wonder-dw-prod-brd.orders.hdr_orders` o
  ON oi.order_id = o.order_id
JOIN `wonder-dw-prod-brd.dw.dim_restaurants` r
  ON oi.restaurant_id = r.restaurant_id
JOIN `wonder-dw-prod-brd.dw.dim_restaurant_brands` rb
  ON r.restaurant_brand_id = rb.restaurant_brand_id
WHERE o.order_status = 'COMPLETE'
GROUP BY rb.restaurant_brand_name
```

### customer_survey_responses

**Purpose**: Order-level customer satisfaction surveys including NPS, service ratings, and overall feedback. Links to hdr_orders via order_id.

**Location**: `wonder-dw-prod-brd.orders.customer_survey_responses`

**Row Count**: ~1M survey responses (as of Nov 2025)

**Key Fields**:
```sql
response_id                                STRING    -- Primary key, joins to customer_survey_dish_responses
order_id                                   STRING    -- Foreign key to hdr_orders.order_id
survey_response_date                       DATETIME  -- When survey was completed
finished                                   INTEGER   -- Whether survey was finished
is_in_app_review                           BOOLEAN   -- Whether this was an in-app review
review_credit_amount                       NUMERIC   -- Credit amount given for review

-- NPS and Overall Rating (1-5 star scale)
-- IMPORTANT: NPS uses a 1-5 scale (5 = would definitely recommend, 1 = would not recommend)
raw_nps                                    INTEGER   -- NPS score (1-5 stars)
div_2_nps                                  FLOAT     -- DEPRECATED: Legacy field from old 10-point scale
nps_upper                                  FLOAT     -- NPS upper bound
nps_lower                                  FLOAT     -- NPS lower bound

-- Service Ratings (1-5 star scale)
raw_wonder_chef_interaction_rating         INTEGER   -- Chef interaction rating (1-5 stars)
div_2_wonder_chef_interaction_rating       FLOAT     -- DEPRECATED: Legacy field
wonder_chef_interaction_rating_upper       FLOAT     -- Chef interaction upper bound
wonder_chef_interaction_rating_lower       FLOAT     -- Chef interaction lower bound
better_chef_interaction_feedback           STRING    -- Open text: how to improve chef interaction

raw_tableware_experience                   INTEGER   -- Tableware rating (1-5 stars)
div_2_tableware_experience                 FLOAT     -- DEPRECATED: Legacy field
tableware_experience_upper                 FLOAT     -- Tableware upper bound
tableware_experience_lower                 FLOAT     -- Tableware lower bound
tableware_experience_open_response         STRING    -- Open text: tableware feedback
tableware_experience_call_yes_no           INTEGER   -- Whether to call customer about tableware

-- Other Survey Questions
eating_time                                INTEGER   -- When customer ate the food
eating_time_enum                           INTEGER   -- Eating time enumeration
restaurant_name                            INTEGER   -- Restaurant name response
household_size                             INTEGER   -- Customer household size
how_did_you_order                          INTEGER   -- How customer ordered
menu_options_rating                        INTEGER   -- Menu options rating
improve_menu_options                       INTEGER   -- How to improve menu
satisfied_if_paid                          INTEGER   -- Would pay for this
satisfied_if_paid_enum                     INTEGER   -- Satisfaction if paid enum
overall_improve_feedback                   INTEGER   -- Overall improvement feedback
other_text_feedback                        INTEGER   -- Other text feedback
ordering_experience                        STRING    -- Ordering experience description
order_agreement                            INTEGER   -- Order agreement
order_agreement_reason                     INTEGER   -- Reason for order agreement
acquistion_channel                         INTEGER   -- How customer learned about Wonder
was_there_a_specific_restaurant            INTEGER   -- Wanted specific restaurant
was_it_the_restaurant_you_wanted           INTEGER   -- Got desired restaurant
reason_for_switch                          INTEGER   -- Why switched restaurant

-- Metadata
use_five_point_scale_rating                BOOLEAN   -- Whether 5-point scale was used
YY_MM                                      STRING    -- Year-month of survey
```

**Join Pattern**:
```sql
-- Join orders to overall survey responses
FROM `wonder-dw-prod-brd.orders.hdr_orders` o
LEFT JOIN `wonder-dw-prod-brd.orders.customer_survey_responses` s
  ON o.order_id = s.order_id
WHERE s.finished = 1  -- Filter to completed surveys
```

**NPS Calculation**: Use 1-5 scale where 5=Promoter, 4=Passive, 1-3=Detractor. Formula: ((Promoters - Detractors) / Total) × 100

---

### customer_survey_dish_responses

**Purpose**: Menu item-level reviews with ratings and written feedback. Contains detailed dish ratings (taste, temperature, portion, etc.) and customer's written review text.

**Location**: `wonder-dw-prod-brd.orders.customer_survey_dish_responses`

**Row Count**: ~2.45M dish reviews (as of Nov 2025)

**Key Fields**:
```sql
response_id                      STRING    -- Foreign key to customer_survey_responses.response_id
menu_item_id                     STRING    -- Menu item that was reviewed
menu_item_name                   INTEGER   -- Menu item name (encoded)
menu_item_number                 INTEGER   -- Menu item number in order

-- Written Review
other_text_feedback              STRING    -- WRITTEN REVIEW TEXT - customer's written feedback about dish

-- Rating Fields (1-5 star scale)
-- IMPORTANT: All ratings use a 1-5 scale (5 = excellent, 1 = poor)
raw_taste_rating                 INTEGER   -- Taste rating (1-5 stars)
raw_portion_size                 INTEGER   -- Portion size rating (1-5 stars)
raw_presentation_rating          INTEGER   -- Presentation rating (1-5 stars)
raw_temperature                  INTEGER   -- Temperature rating (1-5 stars)
raw_reorder_rating               INTEGER   -- Would reorder rating (1-5 stars)
raw_texture_rating               INTEGER   -- Texture rating (1-5 stars)
raw_value_price                  INTEGER   -- Value for price rating (1-5 stars)

-- Legacy Normalized Fields (no longer used - div_2 fields were from old 10-point scale)
div_2_taste_rating               FLOAT     -- DEPRECATED: Legacy field
div_2_portion_size               FLOAT     -- DEPRECATED: Legacy field
div_2_presentation               FLOAT     -- DEPRECATED: Legacy field
div_2_temperature                FLOAT     -- DEPRECATED: Legacy field
div_2_reorder                    FLOAT     -- DEPRECATED: Legacy field
div_2_texture                    FLOAT     -- DEPRECATED: Legacy field
div_2_value_price                FLOAT     -- DEPRECATED: Legacy field

-- Upper/Lower Bounds for each rating
taste_rating_upper               INTEGER   -- Taste rating upper bound
taste_rating_lower               INTEGER   -- Taste rating lower bound
portion_size_rating_upper        FLOAT     -- Portion upper bound
portion_size_rating_lower        FLOAT     -- Portion lower bound
presentation_rating_upper        FLOAT     -- Presentation upper bound
presentation_rating_lower        FLOAT     -- Presentation lower bound
temperature_rating_upper         FLOAT     -- Temperature upper bound
temperature_rating_lower         FLOAT     -- Temperature lower bound
reorder_rating_upper             FLOAT     -- Reorder upper bound
reorder_rating_lower             FLOAT     -- Reorder lower bound
texture_rating_upper             FLOAT     -- Texture upper bound
texture_rating_lower             FLOAT     -- Texture lower bound
value_price_rating_upper         FLOAT     -- Value upper bound
value_price_rating_lower         FLOAT     -- Value lower bound

-- Aggregate Ratings
dish_rating_upper                FLOAT     -- Overall dish rating upper bound
dish_rating_lower                FLOAT     -- Overall dish rating lower bound
min_avg_rating_field             NUMERIC   -- Minimum average rating field

-- Additional Feedback
best_rating_feedback             INTEGER   -- Best aspect of dish
how_did_you_eat                  INTEGER   -- How customer consumed dish
how_did_you_eat_enum             INTEGER   -- Eating method enumeration
temperature_enum                 INTEGER   -- Temperature category
did_not_receive_item             BOOLEAN   -- Whether customer didn't receive item

-- Rating Counts
count_reorder_rating             INTEGER   -- Count of reorder ratings
count_temperature_rating         INTEGER   -- Count of temperature ratings
count_taste_rating               INTEGER   -- Count of taste ratings

-- Metadata
use_five_point_scale_rating      BOOLEAN   -- Whether 5-point scale was used
```

**Key Points**:
- **`other_text_feedback`** contains written review text
- **All `raw_*_rating` fields use 1-5 scale** (5=excellent, 1=poor) - NOT 0-10
- **Use `raw_*` fields, not `div_2_*`** (div_2 fields are deprecated legacy)
- Join through `customer_survey_responses` to link to orders

**Join Pattern**:
```sql
-- Link reviews to orders: dish_responses → survey_responses → hdr_orders
FROM `wonder-dw-prod-brd.orders.customer_survey_dish_responses` dish
JOIN `wonder-dw-prod-brd.orders.customer_survey_responses` survey
  ON dish.response_id = survey.response_id
JOIN `wonder-dw-prod-brd.orders.hdr_orders` orders
  ON survey.order_id = orders.order_id
```

---

### Envoy Rating Tables

- `envoy_order_ratings` - Order ratings
- `envoy_order_delivery_rating_tags` - Delivery rating tags
- `envoy_order_pickup_rating_tags` - Pickup rating tags
- `envoy_order_restaurant_rating_tags` - Restaurant rating tags

### Operational Tables

- `hdr_delivery_tasks` - Delivery task details
- `daily_hdr_metrics` - Daily aggregated HDR metrics
- `fct_order_rca` - Root cause analysis for orders

---

## Timezone Handling

**Storage**: All TIMESTAMP fields are stored in UTC

**Conversion Pattern**:
```sql
-- Convert UTC timestamp to Eastern Time
DATETIME(order_placed_date_utc, 'America/New_York') as order_time_et

-- Extract hour in Eastern Time
EXTRACT(HOUR FROM DATETIME(order_placed_date_utc, 'America/New_York')) as hour_et
```

**Pre-Converted Fields**:
- `service_date_et` - Already in Eastern Time (DATE type), use for daily aggregations

---

## Query Performance Tips

1. **Filter by Date Early** - Add date filters at the beginning of WHERE clause:
```sql
WHERE service_date_et >= '2025-10-01'  -- Good for performance
  AND order_status = 'COMPLETE'
```

2. **Use service_date_et for Date Ranges** - It's a DATE field and performs better than converting timestamps:
```sql
-- GOOD
WHERE service_date_et BETWEEN '2025-10-01' AND '2025-10-31'

-- SLOWER
WHERE DATE(order_placed_date_utc) BETWEEN '2025-10-01' AND '2025-10-31'
```

3. **Be Selective with Timing Fields** - Don't select all timing fields unless needed. Query only the metrics you need.

4. **Filter by Status** - Most analyses should filter to `COMPLETE` orders to exclude in-progress and failed orders.

---

## Data Quality Notes

### NULL Values in Timing Fields

Not all timing metrics are populated for all orders:
- `delivery_sla_difference` - Only populated for completed delivery orders
- Kitchen timing fields - May be NULL for orders that never entered cooking
- Courier timing fields - May be NULL for pickup orders

**Pattern**: Always filter or handle NULLs in timing analysis:
```sql
WHERE actual_o2e_mins IS NOT NULL
```

### Multi-Restaurant Orders

Some orders span multiple restaurants (indicated by `num_restaurants > 1`). The `restaurant_ids` field is a repeated/array field.

### Marketplace Order Differences

Orders from marketplaces (GRUB_HUB, DOOR_DASH, UBER_EATS) may have:
- Different fee structures
- Different timing expectations
- External order IDs in `channel_order_id`
