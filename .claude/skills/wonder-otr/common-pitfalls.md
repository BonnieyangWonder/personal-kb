# Wonder OTR Common Pitfalls

Common mistakes when analyzing On-Time Rate and how to avoid them.

---

## 🚨 CRITICAL: Using Wrong Field for OTR Calculation

### The Problem

Using `delivery_sla_difference` directly to calculate OTR will give **drastically wrong results** (~24% instead of ~92%).

```sql
-- ❌ WRONG: Do NOT use delivery_sla_difference for OTR
SELECT
  ROUND(AVG(CASE WHEN delivery_sla_difference BETWEEN -8.99 AND 0.99 
    THEN 1 ELSE 0 END) * 100, 1) AS otr_pct
FROM hdr_orders
-- Result: ~24% OTR (WRONG!)
```

### Why It's Wrong

- `delivery_sla_difference` is the raw minutes difference, useful for **diagnostics**
- The business definition of "on time" involves complex rules not captured by a simple threshold
- Wonder's data team pre-calculates `on_time_issue` with all the correct business logic

### The Solution

**ALWAYS use `imperfect_orders.on_time_issue` or `hdr_on_time_orders.on_time_issue`:**

```sql
-- ✅ CORRECT: Use the on_time_issue flag
SELECT
  ROUND((1 - SAFE_DIVIDE(
    COUNT(DISTINCT CASE WHEN io.on_time_issue THEN o.order_id END),
    COUNT(DISTINCT o.order_id)
  )) * 100, 1) AS otr_pct
FROM `wonder-dw-prod-brd.orders.hdr_orders` o
LEFT JOIN `wonder-dw-prod-brd.orders.imperfect_orders` io ON o.order_id = io.order_id
WHERE o.order_status = 'COMPLETE'
  AND o.brand_category = 'WONDER_HDR'
  AND o.order_channel IN ('APP', 'WEB', 'IN_PERSON')
-- Result: ~92% OTR (CORRECT!)
```

### Quick Reference

| Field | Use For | NOT For |
|-------|---------|---------|
| `on_time_issue` | OTR calculation | - |
| `delivery_sla_difference` | Diagnostics (how early/late) | OTR calculation |
| `otr_sla_tier` | Bucketing orders | OTR calculation |

---

## 1. Inflated Order Counts from Joins

### The Problem

Joining `hdr_orders` to tables like `order_items`, `order_restaurants`, or complex HDR dimension chains creates multiple rows per order.

```sql
-- WRONG: Counts each order multiple times
SELECT COUNT(order_id) as order_count
FROM hdr_orders o
JOIN order_items oi ON o.order_id = oi.order_id
-- Result: 150,000 (inflated!)
```

### The Solution

Always use `COUNT(DISTINCT order_id)`:

```sql
-- RIGHT: Counts each order once
SELECT COUNT(DISTINCT o.order_id) as order_count
FROM hdr_orders o
JOIN order_items oi ON o.order_id = oi.order_id
-- Result: 50,000 (accurate!)
```

---

## 2. Confusing Error Sign Convention

### The Problem

Error fields can be confusing. A **negative** cook_error means the kitchen was **late**, not early.

```sql
-- WRONG interpretation: "positive cook_error = late"
WHERE cook_error > 0  -- Actually means kitchen was FAST
```

### The Solution

Remember: **Error = Predicted - Actual**
- **Negative error** = Actual exceeded prediction = LATE/SLOW
- **Positive error** = Actual was less than prediction = EARLY/FAST

```sql
-- RIGHT: Find orders where kitchen was late
WHERE cook_error < 0  -- Kitchen took longer than predicted

-- RIGHT: Find orders where kitchen was fast
WHERE cook_error > 0  -- Kitchen finished faster than predicted
```

---

## 3. Calculating OTR Wrong

### The Problem

OTR is the percentage of orders WITHOUT issues, not WITH issues.

```sql
-- WRONG: This calculates the imperfection rate, not OTR
SELECT 
  COUNT(DISTINCT CASE WHEN ot.on_time_issue THEN ot.order_id END) 
  / COUNT(DISTINCT ot.order_id) AS otr
-- Result: 0.15 (this is actually the FAILURE rate!)
```

### The Solution

OTR = 1 - (imperfect orders / total orders):

```sql
-- RIGHT: OTR calculation
SELECT 
  1 - SAFE_DIVIDE(
    COUNT(DISTINCT CASE WHEN ot.on_time_issue THEN ot.order_id END),
    COUNT(DISTINCT ot.order_id)
  ) AS otr_rate
-- Result: 0.85 (85% OTR)
```

---

## 4. Forgetting to Filter Order Status

### The Problem

Including canceled or incomplete orders skews OTR metrics.

```sql
-- WRONG: Includes canceled orders in OTR calculation
SELECT COUNT(DISTINCT o.order_id)
FROM hdr_orders o
LEFT JOIN hdr_on_time_orders ot ON o.order_id = ot.order_id
-- Result includes CANCELED, PENDING, etc.
```

### The Solution

Always filter to `COMPLETE` orders:

```sql
-- RIGHT: Only completed orders
SELECT COUNT(DISTINCT o.order_id)
FROM hdr_orders o
LEFT JOIN hdr_on_time_orders ot ON o.order_id = ot.order_id
WHERE o.order_status = 'COMPLETE'
```

---

## 5. Mixing Pickup and Delivery OTR

### The Problem

Pickup (~96% OTR) and Delivery (~86% OTR) have very different performance profiles. Aggregating them hides issues.

```sql
-- MISLEADING: Blended OTR masks delivery problems
SELECT 
  1 - SAFE_DIVIDE(
    COUNT(DISTINCT CASE WHEN on_time_issue THEN order_id END),
    COUNT(DISTINCT order_id)
  ) AS blended_otr
FROM ...
-- Result: 92% (looks good, but delivery is actually 86%!)
```

### The Solution

Always segment by `dining_option`:

```sql
-- RIGHT: Separate pickup and delivery
SELECT
  o.dining_option,
  1 - SAFE_DIVIDE(
    COUNT(DISTINCT CASE WHEN ot.on_time_issue THEN ot.order_id END),
    COUNT(DISTINCT ot.order_id)
  ) AS otr_rate
FROM hdr_orders o
LEFT JOIN hdr_on_time_orders ot ON o.order_id = ot.order_id
WHERE o.order_status = 'COMPLETE'
GROUP BY o.dining_option
```

---

## 6. Kitchen Handoff Scenarios Only Apply to Delivery

### The Problem

Pickup orders don't have courier/logistics components. Applying handoff scenarios to them is meaningless.

```sql
-- WRONG: Includes pickup orders in scenario analysis
SELECT
  CASE
    WHEN cook_error < 0 AND pickup_error > 0 THEN 'A. Kitchen LATE'
    ...
  END AS scenario
FROM hdr_orders
-- Pickup orders have NULL pickup_error!
```

### The Solution

Filter to delivery orders OR handle pickup explicitly:

```sql
-- RIGHT: Delivery-only scenario analysis
SELECT
  CASE
    WHEN dining_option != 'DELIVERY' THEN 'N/A (Pickup Order)'
    WHEN cook_error < 0 AND pickup_error > 0 THEN 'A. Kitchen LATE, Courier Waits'
    WHEN cook_error > 0 AND pickup_error < 0 THEN 'B. Kitchen FAST, Food Waits'
    ...
  END AS kitchen_handoff_scenario
FROM hdr_orders
WHERE order_status = 'COMPLETE'
```

---

## 7. Division by Zero in Rate Calculations

### The Problem

Standard division fails when denominator is zero.

```sql
-- WRONG: Crashes on zero orders
SELECT 
  COUNT(DISTINCT CASE WHEN on_time_issue THEN order_id END) 
  / COUNT(DISTINCT order_id) AS otr
-- ERROR: Division by zero
```

### The Solution

Use BigQuery's `SAFE_DIVIDE`:

```sql
-- RIGHT: Returns NULL instead of error
SELECT 
  SAFE_DIVIDE(
    COUNT(DISTINCT CASE WHEN on_time_issue THEN order_id END),
    COUNT(DISTINCT order_id)
  ) AS failure_rate
```

---

## 8. Including Wonder Spot / 3P Corporate Orders

### The Problem

Wonder Spot (B2B) and 3P Corporate orders have different operational patterns and shouldn't be mixed with standard HDR analysis.

```sql
-- WRONG: Includes all business types
SELECT ...
FROM hdr_orders
WHERE order_status = 'COMPLETE'
-- Includes WONDER_SPOT and 3P_PLATFORM_CORPORATE
```

### The Solution

Filter by brand_category and/or exclude specific business types:

```sql
-- RIGHT: Standard Wonder HDR orders only
SELECT ...
FROM hdr_orders
WHERE order_status = 'COMPLETE'
  AND brand_category = 'WONDER_HDR'
  AND (order_business_type <> 'WONDER_SPOT' OR order_business_type IS NULL)
  AND (order_business_type <> '3P_PLATFORM_CORPORATE' OR order_business_type IS NULL)
```

---

## 9. Not Volume-Weighting Aggregations

### The Problem

Simple averages across segments with different volumes are misleading.

```sql
-- WRONG: Unweighted average
SELECT AVG(otr_rate) AS network_otr
FROM (
  SELECT hdr_id, otr_rate
  FROM segment_metrics
)
-- A small HDR with 10 orders has same weight as 1000-order HDR
```

### The Solution

Volume-weight your aggregations:

```sql
-- RIGHT: Volume-weighted average
SELECT 
  SUM(order_count * otr_rate) / SUM(order_count) AS weighted_otr
FROM segment_metrics
```

---

## 10. Wrong Week Definition

### The Problem

Different week start days (Sunday vs Monday) cause week-over-week comparisons to be off.

```sql
-- INCONSISTENT: Default week starts Sunday
DATE_TRUNC(service_date_et, WEEK)  -- Week starts Sunday
```

### The Solution

Explicitly specify Monday start for business weeks:

```sql
-- RIGHT: Business week starts Monday
DATE_TRUNC(service_date_et, WEEK(MONDAY))

-- For formatted output
FORMAT_DATE('%F', DATE_TRUNC(service_date_et, WEEK(MONDAY))) AS service_week
```

---

## 11. Confusing otr_sla_tier Pattern Matching

### The Problem

Using exact string matching when tiers have slight variations.

```sql
-- FRAGILE: Exact match might miss variations
WHERE otr_sla_tier = '9+_EARLY'
```

### The Solution

Use `LIKE` for flexibility, but be careful with patterns:

```sql
-- RIGHT: Pattern matching for tier groups
WHERE otr_sla_tier LIKE '%EARLY'      -- All early tiers
WHERE otr_sla_tier LIKE '%LATE'       -- All late tiers
WHERE otr_sla_tier = 'ON_TIME'        -- Exact match for on-time
```

---

## 12. Forgetting NULL Handling for Error Fields

### The Problem

Error fields can be NULL for various reasons (pickup orders, data issues, etc.).

```sql
-- WRONG: NULLs affect averages unexpectedly
SELECT AVG(pickup_error) as avg_sit_error
FROM hdr_orders
-- Pickup orders have NULL pickup_error, skewing averages
```

### The Solution

Filter appropriately or use COALESCE:

```sql
-- RIGHT: Only delivery orders for sit/pickup error
SELECT AVG(pickup_error) as avg_sit_error
FROM hdr_orders
WHERE dining_option = 'DELIVERY'
  AND pickup_error IS NOT NULL

-- Or handle NULLs explicitly
SELECT AVG(COALESCE(pickup_error, 0)) as avg_sit_error
FROM hdr_orders
WHERE dining_option = 'DELIVERY'
```

---

## 13. Using the Wrong Table for OTR Flags

### The Problem

`hdr_orders` has timing error fields, but the boolean `on_time_issue` flag is in `hdr_on_time_orders`.

```sql
-- WRONG: on_time_issue doesn't exist in hdr_orders
SELECT on_time_issue FROM hdr_orders
-- ERROR: Unknown field
```

### The Solution

Join to `hdr_on_time_orders` for OTR flags:

```sql
-- RIGHT: Get OTR flags from correct table
SELECT 
  o.order_id,
  ot.on_time_issue,
  ot.otr_sla_tier
FROM hdr_orders o
LEFT JOIN hdr_on_time_orders ot ON o.order_id = ot.order_id
```

---

## 14. Comparing Absolute vs Signed Errors

### The Problem

Mixing absolute and signed error metrics leads to confusion.

- **Signed error**: Shows direction (late vs early)
- **Absolute error**: Shows magnitude only

```sql
-- MISLEADING: Average signed error can be near zero even with high variance
SELECT AVG(cook_error) as avg_cook_error  -- Might be 0.5
-- But orders swing from -10 to +10
```

### The Solution

Report both for complete picture:

```sql
-- RIGHT: Report both signed and absolute
SELECT
  AVG(cook_error) AS avg_cook_error,           -- Direction bias
  AVG(ABS(cook_error)) AS avg_abs_cook_error,  -- Magnitude
  STDDEV(cook_error) AS stddev_cook_error      -- Variability
FROM hdr_orders
```

---

## 15. Incorrect 1P vs 3P Classification

### The Problem

Incorrectly classifying channels as 1P (first-party) or 3P (third-party marketplace).

```sql
-- WRONG: Missing IN_PERSON from 1P
CASE WHEN order_channel IN ('APP', 'WEB') THEN '1P' ELSE '3P' END
```

### The Solution

Use the complete channel list:

```sql
-- RIGHT: Complete 1P/3P classification
CASE 
  WHEN order_channel IN ('APP', 'IN_PERSON', 'WEB') THEN '1P'
  ELSE '3P'
END AS channel_type
```

---

## 16. Not Using Sit Time Decomposition

### The Problem

Using `pickup_error` alone doesn't tell you WHO is responsible for sit time issues.

```sql
-- INCOMPLETE: Can't distinguish courier delay from handoff delay
SELECT AVG(pickup_error) as avg_sit_error
FROM hdr_orders
WHERE dining_option = 'DELIVERY'
-- Result: -3.2 mins (food sat too long, but WHY?)
```

### The Solution

Decompose sit time into its components:

```sql
-- RIGHT: Separate courier response from kitchen handoff
SELECT
  AVG(courier_response_time_mins) AS avg_courier_response,   -- Logistics responsible
  AVG(kitchen_handoff_time_mins) AS avg_kitchen_handoff,     -- Ops responsible
  AVG(COALESCE(kitchen_handoff_time_mins, 0) - COALESCE(courier_response_time_mins, 0)) AS avg_ops_gap
FROM hdr_orders
WHERE dining_option = 'DELIVERY'
-- Result: courier=4.1 mins, handoff=8.3 mins, ops_gap=+4.2 → Ops is the problem!
```

---

## 17. Using Wrong Fields for Kitchen Handoff Scenarios

### The Problem

Using `cook_error` and `pickup_error` for scenario classification is less accurate than the production definition.

```sql
-- LEGACY: Less precise scenario classification
CASE
  WHEN cook_error < 0 AND pickup_error > 0 THEN 'A. Kitchen LATE'
  ...
END
```

### The Solution

Use `ready_for_pickup_sla_difference` and `courier_response_time_mins`:

```sql
-- PRODUCTION: More precise scenario classification
CASE
  WHEN ready_for_pickup_sla_difference > 2.0 
   AND COALESCE(courier_response_time_mins, 0) <= 5.0 
  THEN 'A. Kitchen LATE, Courier Waits'
  WHEN ready_for_pickup_sla_difference <= 2.0 
   AND COALESCE(courier_response_time_mins, 0) > 5.0 
  THEN 'B. Kitchen FAST, Food Waits (Risk)'
  WHEN ready_for_pickup_sla_difference > 2.0 
   AND COALESCE(courier_response_time_mins, 0) > 5.0 
  THEN 'C. Compounding Failure (Both LATE)'
  ELSE 'D. Ideal State (Kitchen Fast, Handoff Fast)'
END
```

---

## 18. Hardcoding Threshold Values Inconsistently

### The Problem

Different analyses use different thresholds for "late" or "slow", making results incomparable.

```sql
-- INCONSISTENT: Different thresholds in different queries
WHERE ready_for_pickup_sla_difference > 3.0  -- Query 1
WHERE ready_for_pickup_sla_difference > 5.0  -- Query 2 (different!)
```

### The Solution

Use standard thresholds consistently:

| Metric | Standard Threshold |
|--------|-------------------|
| Kitchen "On Time" | ≤ 2 mins |
| Courier Response "Fast" | ≤ 5 mins |
| Handoff "Fast" | ≤ 5 mins |
| Handoff "Very Slow" | > 8 mins |

```sql
-- RIGHT: Consistent thresholds
WHERE ready_for_pickup_sla_difference > 2.0  -- Kitchen late
  AND COALESCE(courier_response_time_mins, 0) <= 5.0  -- Courier was fast
```

---

## 19. Ignoring Force Complete in RCA

### The Problem

Not considering force complete events when analyzing why handoff took so long.

```sql
-- MISSING CONTEXT: Doesn't account for force bumps
SELECT hdr_name, AVG(kitchen_handoff_time_mins) as avg_handoff
FROM hdr_orders o
JOIN dim_hdrs h ON o.hdr_id = h.hdr_id
WHERE dining_option = 'DELIVERY'
GROUP BY 1
-- High handoff time might be from fake bumps, not true handoff issues
```

### The Solution

Join to `imperfect_kitchen_items` to identify force complete patterns:

```sql
-- RIGHT: Consider force complete in analysis
SELECT
  h.hdr_name,
  AVG(o.kitchen_handoff_time_mins) as avg_handoff,
  SUM(CASE WHEN fc.has_force_complete = 1 THEN 1 ELSE 0 END) as force_complete_orders,
  AVG(CASE 
    WHEN fc.has_force_complete = 1 THEN o.kitchen_handoff_time_mins 
  END) as avg_handoff_with_force
FROM hdr_orders o
JOIN dim_hdrs h ON o.hdr_id = h.hdr_id
LEFT JOIN (
  SELECT order_id, MAX(has_force_progression) as has_force_complete
  FROM imperfect_kitchen_items
  GROUP BY 1
) fc ON o.order_id = fc.order_id
WHERE o.dining_option = 'DELIVERY'
GROUP BY 1
```

---

## 20. Confusing Courier Response Time vs Pickup Error

### The Problem

These fields measure different things and have different sign conventions.

| Field | Measures | Sign Convention |
|-------|----------|-----------------|
| `courier_response_time_mins` | Absolute time: Ready → Driver Arrival | Always positive (duration) |
| `pickup_error` | Prediction error: Expected - Actual sit time | Positive = fast, Negative = slow |

```sql
-- WRONG: Using pickup_error as if it were courier response time
WHERE pickup_error > 5.0  -- This means sit was FASTER than expected, not slow!
```

### The Solution

Use the right field for your question:

```sql
-- "How long did the courier take to arrive?"
WHERE courier_response_time_mins > 10.0  -- Courier took >10 mins

-- "Was the overall sit time better or worse than predicted?"
WHERE pickup_error < -5.0  -- Sit time was 5+ mins worse than predicted
```

---

## Pitfall 21: Blaming Handoff/Driver Without Checking Upstream Delays

### The Problem

A common mistake is blaming handoff time or driver response without first checking if the order was **already late** due to kitchen delays. This leads to incorrect root cause attribution and wasted improvement efforts.

**Example of wrong attribution:**
- Order was 5 mins late leaving kitchen (cook ran long)
- Driver then took 7 mins to arrive (2 mins "slow")
- Analysis says: "Driver was slow, need courier incentives"
- **Reality:** Kitchen was the root cause; driver was slightly slow but not the primary driver

### The Mistake

```sql
-- WRONG: Blaming driver without checking upstream
SELECT 
  hdr_name,
  AVG(courier_response_time_mins) AS avg_driver_time,
  AVG(kitchen_handoff_time_mins) AS avg_handoff
FROM orders
WHERE late = TRUE
GROUP BY 1
HAVING AVG(courier_response_time_mins) > 10
-- This flags locations as "logistics problems" even if kitchen was the root cause!
```

### The Solution

**Always check `ready_for_pickup_sla_difference` first** to see if the order was already delayed before the sit time began.

```sql
-- CORRECT: Check upstream before attributing blame
SELECT 
  hdr_name,
  
  -- Step 1: Was kitchen already late?
  AVG(ready_for_pickup_sla_difference) AS kitchen_delay,
  AVG(CASE WHEN ready_for_pickup_sla_difference > 2 THEN 1 ELSE 0 END) AS pct_kitchen_late,
  
  -- Step 2: Only blame driver/handoff IF kitchen was on time
  AVG(CASE 
    WHEN ready_for_pickup_sla_difference <= 2 AND courier_response_time_mins > kitchen_handoff_time_mins 
    THEN 1 ELSE 0 
  END) AS pct_blame_logistics,
  
  AVG(CASE 
    WHEN ready_for_pickup_sla_difference <= 2 AND kitchen_handoff_time_mins > courier_response_time_mins 
    THEN 1 ELSE 0 
  END) AS pct_blame_handoff

FROM orders
WHERE late = TRUE
GROUP BY 1
```

### Attribution Decision Tree

```
1. Check: ready_for_pickup_sla_difference > 5 mins?
   └── YES → PRIMARY BLAME = KITCHEN (cascading delay)
   └── NO → Continue to step 2
   
2. Check: ready_for_pickup_sla_difference > 2 mins?
   └── YES → MIXED: Kitchen + downstream issues
   └── NO → Kitchen was ON TIME, fair to compare handoff vs driver
   
3. If kitchen was on time:
   └── courier_response > handoff → LOGISTICS problem
   └── handoff > courier_response → OPS/EXPO problem
```

### Why This Matters

| Scenario | Wrong Attribution | Correct Attribution |
|----------|-------------------|---------------------|
| Kitchen 5m late, driver 7m | "Driver slow" | "Kitchen caused cascade" |
| Kitchen 0m late, driver 12m | "Driver slow" | ✅ "Driver slow" (correct) |
| Kitchen 8m late, handoff 10m | "Expo bottleneck" | "Kitchen delay + expo compounding" |

**Key metric:** If `pct_kitchen_late` > 50%, kitchen is likely the primary driver regardless of handoff/driver metrics.

---

## Pitfall #22: Using All Force Completes Instead of Premature Force Completes

### The Mistake

Flagging HDRs with high `has_force_progression` rates as problematic.

### Why It's Wrong

**Not all force completes are bad!** Items going through the **Hybrid pod** (vending, pre-made items) naturally trigger force completes because they don't have traditional cooking steps.

| HDR Type | All FC % | Premature FC % | Problem? |
|----------|----------|----------------|----------|
| High Hybrid pod mix | 60% | 5% | ❌ No - expected |
| Mostly Hot/Cold pod | 60% | 25% | ✅ Yes - gaming |

### The Fix

**Always use `has_premature_force_complete`** instead of `has_force_progression`:

```sql
-- ❌ WRONG: Flags all force completes (inflated by Hybrid pod)
COUNT(DISTINCT CASE WHEN fc.has_force_progression = 1 THEN o.order_id END) AS fc_orders

-- ✅ CORRECT: Flags only premature force completes (actual problems)
COUNT(DISTINCT CASE WHEN fc.has_premature_force_complete = 1 THEN o.order_id END) AS premature_fc_orders
```

### Threshold Guide (for Premature FC)

| Premature FC Rate | Status | Action |
|-------------------|--------|--------|
| < 5% | ✅ Normal | Monitor |
| 5-10% | 🟡 Elevated | Investigate capacity |
| 10-20% | 🟠 High | Audit shifts/pods |
| > 20% | 🔴 Critical | Immediate intervention |

---

## Pitfall #23: Ignoring Sequencer's Hot Hold Assumption as OTR Root Cause

### The Mistake

Attributing OTR misses to kitchen execution when the real cause is **sequencer-caused delay due to incorrect hot hold assumption**.

### Why It's Wrong

**The sequencer adds delay assuming items can be hot-held, but ETA correctly estimates fresh prep:**

| Component | What It Does | Impact |
|-----------|--------------|--------|
| **ETA Model** | Estimates fresh prep time | ✅ Correct |
| **Sequencer** | Assumes hot hold → adds `delay_duration` | ❌ Adds extra time |
| **Result** | Sequencer delay is ADDITIONAL to ETA | +4.5 min not planned |

### The Proof

```
BAD_INTERACTION orders:
├── Ticket error: +1.4 min (kitchen appears slow)
├── Sequencer delay: +4.5 min (item held back)
├── Ticket error MINUS delay: -3.1 min
└── Kitchen would be 3 min FASTER without sequencer hold!

The entire ticket error is sequencer-caused, not kitchen execution.
```

### Two Distinct Root Causes - Don't Conflate Them!

| Scenario | Prep Type | Issue | Owner | Fix |
|----------|-----------|-------|-------|-----|
| Sequencer holds ALM | `A_LA_MINUTE` | Sequencer adds delay | **Product** | Stop holding ALM |
| Missing pouch | `HOT_HOLDING` | No hot hold stocked | **Ops** | Better stocking |
| Missing pouch | `A_LA_MINUTE` | Inventory issue | **Ops** | Inventory mgmt |
| Surprise pouch | Either | Tracking off | **Ops** | Inventory tracking |

### Key Fields to Use

```sql
-- From hdr_kitchen_pod_item
preparation_type                    -- 'HOT_HOLDING' or 'A_LA_MINUTE'
system_overstated_hh_inventory = 1  -- Missing Pouch (Ops issue)
system_understated_hh_inventory = 1 -- Surprise Pouch (Ops issue)

-- From hdr_kitchen_order_item
hot_hold_item_a_la_minute_fl = 1    -- Needs fresh prep
delay_duration_mins > 0              -- Sequencer held item back (Product issue)
```

### Attribution Logic

```sql
CASE
  -- Sequencer-caused: ALM item was held back
  WHEN hot_hold_item_a_la_minute_fl = 1 AND delay_duration_mins > 0 
  THEN 'SEQUENCER_CAUSED_DELAY'
  
  -- Ops-caused: Missing pouch regardless of prep type
  WHEN system_overstated_hh_inventory = 1 
  THEN 'OPS_HOT_HOLD_MGMT_MISSING'
  
  -- Ops-caused: Surprise pouch
  WHEN system_understated_hh_inventory = 1 
  THEN 'OPS_HOT_HOLD_MGMT_SURPRISE'
  
  ELSE 'OK'
END AS hot_hold_root_cause
```

---

## Pitfall #24: Not Volume-Weighting Courier Platform Analysis

### The Mistake

Comparing courier platforms by metrics alone without considering their share of total volume.

```sql
-- WRONG: Makes DoorDash look like the biggest problem
SELECT courier_platform, AVG(actual_o2e_mins) AS avg_o2e
FROM hdr_orders WHERE dining_option = 'DELIVERY'
GROUP BY 1
-- DoorDash: 53 min, Relay: 41 min, GrubHub: 39 min
-- Conclusion: "DoorDash is killing our O2E" -- MISLEADING!
```

### Why It's Wrong

Courier platforms have vastly different order volumes. A platform with terrible metrics but <3% of volume has minimal network impact, while a platform with moderate degradation but 64% of volume drives the network miss.

**Real-world example from Jan 26, 2026 network analysis:**
| Platform | Orders | O2E | Volume Share | Network Impact |
|----------|--------|-----|--------------|----------------|
| GrubHub | 11,880 | 38.9 min | 64% | **PRIMARY DRIVER** |
| Relay | 6,131 | 40.8 min | 33% | Significant |
| DoorDash | 587 | 53.1 min | 3% | Negligible |

### The Solution

Always include order counts and volume share in courier analysis:

```sql
-- CORRECT: Volume-weighted platform analysis
WITH platform_metrics AS (
  SELECT
    o.courier_platform,
    COUNT(DISTINCT o.order_id) AS orders,
    AVG(o.actual_o2e_mins) AS avg_o2e,
    AVG(o.courier_response_time_mins) AS avg_courier_response,
    AVG(o.kitchen_handoff_time_mins) AS avg_handoff,
    1 - SAFE_DIVIDE(
      COUNT(DISTINCT CASE WHEN ot.on_time_issue THEN o.order_id END),
      COUNT(DISTINCT o.order_id)
    ) AS otr
  FROM `wonder-dw-prod-brd.orders.hdr_orders` o
  LEFT JOIN `wonder-dw-prod-brd.orders.hdr_on_time_orders` ot ON o.order_id = ot.order_id
  WHERE o.dining_option = 'DELIVERY'
    AND o.order_status = 'COMPLETE'
  GROUP BY 1
)
SELECT
  courier_platform,
  orders,
  ROUND(orders * 100.0 / SUM(orders) OVER (), 1) AS volume_share_pct,
  ROUND(avg_o2e, 1) AS avg_o2e,
  ROUND(otr * 100, 1) AS otr_pct
FROM platform_metrics
ORDER BY orders DESC
```

---

## Pitfall #25: Confusing Handoff vs Courier Response When Evaluating Ops Changes

### The Mistake

When evaluating operational changes (like ready-for-pickup signal changes), looking at overall sit time instead of separating ops-owned vs logistics-owned components.

```sql
-- WRONG: Can't tell if the ops change helped or hurt
SELECT AVG(actual_pickup_waiting_duration_mins) AS sit_time
FROM hdr_orders WHERE dining_option = 'DELIVERY'
-- Sit time increased 3 min -- is the signal change bad? NO WAY TO KNOW!
```

### Why It's Wrong

Sit time has TWO components owned by DIFFERENT teams:
- **`kitchen_handoff_time_mins`** = Driver Arrival → Pickup Complete (OPS-owned)
- **`courier_response_time_mins`** = Ready Signal → Driver Arrival (LOGISTICS-owned)

If you made an ops change, you need to look at handoff time specifically. Courier response is outside your control.

### The Solution

Decompose sit time to isolate ops vs logistics impact:

```sql
-- CORRECT: Separate ops-owned from logistics-owned
SELECT
  service_week,
  courier_platform,
  
  -- OPS-OWNED: Did the signal change affect handoff?
  ROUND(AVG(kitchen_handoff_time_mins), 1) AS avg_handoff_mins,
  
  -- LOGISTICS-OWNED: Couriers arriving after signal
  ROUND(AVG(courier_response_time_mins), 1) AS avg_courier_response_mins,
  
  -- TOTAL: For reference
  ROUND(AVG(actual_pickup_waiting_duration_mins), 1) AS avg_sit_time_mins

FROM `wonder-dw-prod-brd.orders.hdr_orders`
WHERE dining_option = 'DELIVERY'
  AND order_status = 'COMPLETE'
GROUP BY 1, 2
ORDER BY 1, 2
```

**Interpretation:**
- Handoff increased +3 min → **Ops change may have hurt** (investigate further)
- Handoff stable, courier response +3 min → **Ops change is fine**, logistics has a problem

---

## Pitfall #26: Not Using Baseline Comparison for Courier Analysis

### The Mistake

Comparing a single week's courier metrics without historical context, making it impossible to distinguish normal variance from actual degradation.

```sql
-- WRONG: Single week snapshot, no baseline
SELECT courier_platform, AVG(courier_response_time_mins)
FROM hdr_orders
WHERE service_date_et >= '2026-01-26'
-- Result: GrubHub 3.3 min -- Is this good or bad? NO CONTEXT!
```

### The Solution

Always compare to a multi-week baseline (typically 5-6 weeks, excluding anomalous weeks like snowstorms):

```sql
-- CORRECT: Compare to 5-week baseline
WITH baseline AS (
  SELECT courier_platform,
    AVG(courier_response_time_mins) AS baseline_courier_resp,
    AVG(kitchen_handoff_time_mins) AS baseline_handoff,
    AVG(actual_o2e_mins) AS baseline_o2e
  FROM `wonder-dw-prod-brd.orders.hdr_orders`
  WHERE service_date_et >= '2025-12-22' AND service_date_et < '2026-01-26'  -- 5 weeks
    AND dining_option = 'DELIVERY' AND order_status = 'COMPLETE'
  GROUP BY 1
),
current_week AS (
  SELECT courier_platform,
    AVG(courier_response_time_mins) AS current_courier_resp,
    AVG(kitchen_handoff_time_mins) AS current_handoff,
    AVG(actual_o2e_mins) AS current_o2e
  FROM `wonder-dw-prod-brd.orders.hdr_orders`
  WHERE service_date_et >= '2026-01-26' AND service_date_et < '2026-02-02'
    AND dining_option = 'DELIVERY' AND order_status = 'COMPLETE'
  GROUP BY 1
)
SELECT
  c.courier_platform,
  ROUND(b.baseline_courier_resp, 1) AS baseline_courier_resp,
  ROUND(c.current_courier_resp, 1) AS current_courier_resp,
  ROUND(c.current_courier_resp - b.baseline_courier_resp, 1) AS courier_resp_delta
FROM current_week c
JOIN baseline b ON c.courier_platform = b.courier_platform
```

---

## Pitfall #27: Ignoring Transit Accuracy When Analyzing Courier Issues

### The Mistake

Only looking at courier response time without checking transit accuracy. Some platforms systematically underestimate transit times, which compounds with response delays.

```sql
-- INCOMPLETE: Only checking courier response
SELECT courier_platform, AVG(courier_response_time_mins)
FROM hdr_orders WHERE dining_option = 'DELIVERY'
-- Missing: Does the platform also have transit estimation issues?
```

### Why It Matters

**Transit error** = `actual_transit_mins - estimated_transit_mins`
- **Positive** = Transit took longer than promised (customer experience suffers)
- **Negative** = Transit was faster than estimated (rare, usually good)

Some platforms (e.g., DoorDash) systematically underestimate transit by 2-3 minutes at baseline, which compounds into OTR misses.

### The Solution

Include transit accuracy in courier platform analysis:

```sql
-- CORRECT: Full courier logistics picture
SELECT
  courier_platform,
  COUNT(DISTINCT order_id) AS orders,
  
  -- Response time
  ROUND(AVG(courier_response_time_mins), 1) AS avg_courier_response,
  
  -- Transit accuracy
  ROUND(AVG(estimated_transit_mins), 1) AS avg_estimated_transit,
  ROUND(AVG(actual_transit_mins), 1) AS avg_actual_transit,
  ROUND(AVG(actual_transit_mins - estimated_transit_mins), 1) AS avg_transit_error,
  
  -- % of orders slower than estimated
  ROUND(AVG(CASE WHEN actual_transit_mins > estimated_transit_mins THEN 1 ELSE 0 END) * 100, 1) AS pct_slower_than_estimated,
  
  -- % of orders >5 min slower than estimated (severe)
  ROUND(AVG(CASE WHEN actual_transit_mins - estimated_transit_mins > 5 THEN 1 ELSE 0 END) * 100, 1) AS pct_5min_slower

FROM `wonder-dw-prod-brd.orders.hdr_orders`
WHERE dining_option = 'DELIVERY'
  AND order_status = 'COMPLETE'
  AND actual_transit_mins IS NOT NULL
  AND estimated_transit_mins IS NOT NULL
GROUP BY 1
ORDER BY orders DESC
```

---

## Pitfall #28: Not Breaking Down by Population Type for Courier Analysis

### The Mistake

Analyzing courier performance at network level without checking Urban vs Suburban patterns. Urban areas often have systematically different transit challenges.

### The Solution

Join to `dim_hdrs` for population type breakdown:

```sql
-- CORRECT: Courier analysis by population type
SELECT
  o.courier_platform,
  h.population_type,
  COUNT(DISTINCT o.order_id) AS orders,
  ROUND(AVG(o.actual_transit_mins - o.estimated_transit_mins), 1) AS avg_transit_error,
  ROUND(AVG(o.courier_response_time_mins), 1) AS avg_courier_response
FROM `wonder-dw-prod-brd.orders.hdr_orders` o
JOIN `wonder-dw-prod-brd.dw.dim_hdrs` h ON o.hdr_id = h.hdr_id
WHERE o.dining_option = 'DELIVERY'
  AND o.order_status = 'COMPLETE'
GROUP BY 1, 2
ORDER BY 1, 2
```

**Typical Pattern:** Urban areas have 2-4x worse transit error than Suburban due to:
- Traffic congestion
- Parking difficulty
- Building access (apartments, doorman delays)

---

## Quick Reference: Standard OTR Query Template

```sql
-- Template for OTR analysis with common pitfalls avoided
SELECT
  FORMAT_DATE('%F', DATE_TRUNC(o.service_date_et, WEEK(MONDAY))) AS service_week,
  o.dining_option,
  h.hdr_class,
  COUNT(DISTINCT o.order_id) AS order_count,
  1 - SAFE_DIVIDE(
    COUNT(DISTINCT CASE WHEN ot.on_time_issue THEN ot.order_id END),
    COUNT(DISTINCT ot.order_id)
  ) AS otr_rate,
  ROUND(AVG(CASE WHEN o.dining_option = 'DELIVERY' THEN o.cook_error END), 2) AS avg_cook_error,
  ROUND(AVG(CASE WHEN o.dining_option = 'DELIVERY' THEN o.pickup_error END), 2) AS avg_sit_error
FROM `wonder-dw-prod-brd.orders.hdr_orders` o
JOIN `wonder-dw-prod-brd.dw.dim_hdrs` h ON o.hdr_id = h.hdr_id
LEFT JOIN `wonder-dw-prod-brd.orders.hdr_on_time_orders` ot ON o.order_id = ot.order_id
WHERE o.order_status = 'COMPLETE'
  AND o.brand_category = 'WONDER_HDR'
  AND o.service_date_et >= DATE_SUB(CURRENT_DATE('America/New_York'), INTERVAL 4 WEEK)
GROUP BY 1, 2, 3
ORDER BY 1 DESC, 2, 3;
```

