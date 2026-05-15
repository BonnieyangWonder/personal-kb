---
name: wonder-otr
description: Expert knowledge of Wonder's On-Time Rate (OTR) performance metrics and Root Cause Analysis. Generates tiered leadership reports (Product/Culinary/Ops views) with analysis by population type, maturity phase, HDR class, and weeks open. Includes NSO stabilization tracking, Dual OTR Framework (Customer vs Kitchen Process), and stakeholder-specific insights. Trigger with "generate WBR summary" or "weekly OTR report".
allowed-tools: Read, Grep, Glob, Terminal
---

# Wonder On-Time Rate & RCA Expert

This skill provides expertise in analyzing Wonder's On-Time Rate (OTR) performance and conducting Root Cause Analysis (RCA) for delivery and pickup orders. It covers the complete timing lifecycle from order placement through customer delivery, with deep diagnostics for identifying failure modes.

## What This Skill Provides

- **OTR Metrics** - On-Time Rate calculations with and without earlies, by channel and HDR
- **Dual OTR Framework** - Separates Customer OTR (delivery outcome) from Kitchen Process OTR (internal target)
- **SLA Tier Analysis** - Distribution across timing buckets (9+ Early through 31+ Late)
- **Kitchen Handoff Scenarios** - Diagnose whether delays come from kitchen, courier, or both
- **Error Breakdown** - Queue, Cook, Pack/Bag, Sit, Transit, Dropoff error decomposition (avg, absolute, stddev)
- **Force Complete Analysis** - Track fake bumping patterns and their impact on OTR
- **Order Size (IPC) Impact** - How items per check affects ticket time and O2E
- **Expo Wait Time** - Order-level wait time at expo window analysis (**1P vs 3P structural differences explained**)
- **MRO (Multi-Restaurant Order) Support** - 1P supports MRO orders, 3P does not — impacts expo wait interpretation
- **NSO Performance** - New Store Opening timing performance tracking
- **Imperfect Orders** - General order imperfection rates and accuracy issues
- **Weekly Performance Reports** - WBR-style analysis patterns
- **Location Spotlights** - HDR-level diagnosis of courier vs kitchen failures
- **Leadership Intelligence Stack** - Three-tier report structure (Executive/Domain/Deep Dive)
- **NSO Stabilization Framework** - Track maturation phases (Launch/Ramp/Maturing/Mature) with benchmarks
- **Dimension Breakdowns** - Analysis by population type, maturity, class, weeks open
- **Stakeholder Views** - Product (ETA accuracy), Culinary (kitchen execution), Ops (location execution)

## Data Validation

**✓ Queries in this skill tie out to Looker WBR reports.** Validated metrics include:
- 1P Delivery O2E (Order-to-Eat time)
- 1P Delivery/Pickup OTR
- HDR-level OTR rankings
- Component timing breakdowns (queue, cook, pack/bag, sit time, transit)
- Reason code attribution (long production, bad interaction, force complete, long queue, trickling)
- Courier platform performance (RELAY, GRUB_HUB, DOORDASH)
- Sequencer holdback impact on queue time (`has_delay_applied`)
- Queue scenario analysis (sequencer hold + long queue vs capacity only)
- Weekend stress patterns (Friday/Saturday concentration)
- NSO concentration patterns (Suburban 2025 New)
- Top offending HDR patterns (2025/2026 New, 8-11 weeks open)

**Validated Patterns (Jan 2026):**
- Long Production: 71.8% of late orders (vs ~43% all orders) = +29 pt enrichment
- Long Queue: 51.4% of late orders (vs ~20% all orders) = +31 pt enrichment
- Weekend concentration: Friday/Saturday drive 40-50% of weekly late orders
- NSO Suburban 2025 New: 30%+ of late orders with 15-20% of volume = 1.5-2.0x concentration

Last validated: January 2026

---

## ⚠️ CRITICAL: Standard Business Type Exclusions

**ALWAYS exclude WONDER_SPOT and 3P_PLATFORM_CORPORATE from OTR, Ticket Time, and Expo Wait Time queries.**

```sql
-- Standard exclusions for ALL timing/OTR queries
AND (o.order_business_type <> 'WONDER_SPOT' OR o.order_business_type IS NULL)
AND (o.order_business_type <> '3P_PLATFORM_CORPORATE' OR o.order_business_type IS NULL)
```

| Business Type | Why Excluded |
|---------------|--------------|
| `WONDER_SPOT` | Pop-up/event orders with non-standard timing expectations |
| `3P_PLATFORM_CORPORATE` | Corporate/catering orders with different SLAs |

**Note:** Both conditions use `OR ... IS NULL` to handle NULL values (which represent standard Wonder orders).

---

## ⚠️ CRITICAL: Correct OTR Calculation Method

**ALWAYS use `imperfect_orders.on_time_issue` or `hdr_on_time_orders.on_time_issue` for OTR calculations.**

### ❌ WRONG - Do NOT calculate OTR this way:
```sql
-- THIS IS WRONG! Will give ~24% OTR instead of ~92%
AVG(CASE WHEN delivery_sla_difference BETWEEN -8.99 AND 0.99 THEN 1 ELSE 0 END)
```

### ✅ CORRECT - Use the on_time_issue flag:
```sql
-- This is the correct method that matches WBR/Looker
(1 - SAFE_DIVIDE(
  COUNT(DISTINCT CASE WHEN io.on_time_issue THEN o.order_id END),
  COUNT(DISTINCT o.order_id)
)) * 100 AS otr_pct

-- OR using hdr_on_time_orders
(1 - SAFE_DIVIDE(
  COUNT(DISTINCT CASE WHEN ot.on_time_issue THEN o.order_id END),
  COUNT(DISTINCT o.order_id)
)) * 100 AS otr_pct
```

### Why?
- `on_time_issue` is a **boolean flag** pre-calculated by Wonder's data team
- It incorporates complex business rules for what counts as "on time"
- `delivery_sla_difference` is useful for **diagnostics** (how early/late) but NOT for OTR calculation
- Using the raw field directly will give drastically wrong results (~24% vs ~92%)

### Tables with on_time_issue:
| Table | Use Case |
|-------|----------|
| `imperfect_orders` | General order-level OTR |
| `hdr_on_time_orders` | HDR-specific OTR with additional fields |

### Example: 1P OTR by Dining Option
```sql
SELECT
  o.dining_option,
  COUNT(DISTINCT o.order_id) AS orders,
  ROUND((1 - SAFE_DIVIDE(
    COUNT(DISTINCT CASE WHEN io.on_time_issue THEN o.order_id END),
    COUNT(DISTINCT o.order_id)
  )) * 100, 1) AS otr_pct
FROM `wonder-dw-prod-brd.orders.hdr_orders` o
LEFT JOIN `wonder-dw-prod-brd.orders.imperfect_orders` io ON o.order_id = io.order_id
WHERE o.order_status = 'COMPLETE'
  AND o.brand_category = 'WONDER_HDR'
  AND o.order_channel IN ('APP', 'WEB', 'IN_PERSON')  -- 1P only
  AND (o.order_business_type <> 'WONDER_SPOT' OR o.order_business_type IS NULL)
  AND (o.order_business_type <> '3P_PLATFORM_CORPORATE' OR o.order_business_type IS NULL)
  AND o.service_date_et >= DATE_SUB(CURRENT_DATE('America/New_York'), INTERVAL 7 DAY)
GROUP BY 1
```

---

## Enhanced WBR Analysis Framework

When generating comprehensive OTR reports, include these key dimensions:

### 1. Executive Summary Metrics
- Network OTR (1P All, Delivery, Pickup)
- OTR excluding earlies (only 9+ min early counts against OTR)
- Week-over-week delta
- Channel gap (Pickup - Delivery)

### 2. Segment Performance
| Segment Type | Dimensions | Key Insight |
|--------------|------------|-------------|
| **Population Type** | Urban, Suburban, Big Box | Suburban typically has lowest OTR due to longer cook times |
| **HDR Class** | 2023, 2024, 2025, 2025 New, 2026 New | NSO (2025/2026 New) typically 5-9 pts below mature |
| **Maturity Phase** | Launch (0-4 wks), Ramp (5-12), Maturing (13-24), Mature (25+) | Expect 7-9 pt gap between Launch and Mature |

### 3. Delivery Mix Impact Analysis
Assess whether poor OTR is driven by delivery mix vs actual performance:
```sql
-- Calculate expected OTR based on delivery mix (network rates)
expected_otr = (delivery_pct * network_delivery_otr) + ((1-delivery_pct) * network_pickup_otr)
otr_vs_expected = actual_otr - expected_otr  -- Negative = underperforming
```
**Key insight:** Correlation between delivery % and OTR is typically weak (r ≈ -0.03). Bottom performers are genuinely underperforming, not just delivery-heavy.

### 4. Reason Code Attribution

#### Network Benchmarks (typical values)
| Reason Code | All Orders | Late Orders | Enrichment | Owner |
|-------------|------------|-------------|------------|-------|
| Long Production | ~43% | ~66-72% | +23-29 pts | Ops/Kitchen |
| Long Queue | ~20% | ~33-51% | +13-31 pts | Capacity/Ops |
| Force Complete | ~37% | ~34-45% | -3 to +8 pts | Training |
| Bad Interaction | ~22% | ~26-29% | +4-7 pts | Sequencer |
| Trickling | ~29% | ~33-42% | +4-13 pts | Sequencer |
| ALM Items | ~30% | ~35-40% | +5-10 pts | Menu |

**Interpretation:** High enrichment = strong predictor of lateness. Long Production and Long Queue have highest enrichment.

**Recent Pattern (Jan 2026):**
- **Long Production** is the #1 driver (71.8% of late orders) — kitchen execution speed bottleneck
- **Long Queue** is #2 driver (51.4% of late orders) — capacity/staffing constraint
- **Force Complete** at 44.9% typically indicates "rescue FCs" (items already behind when FC'd)
- Weekend stress amplifies these issues — Friday/Saturday can drive 40-50% of weekly late orders

#### By HDR Class Pattern
| Class | Primary Issue | Secondary Issue |
|-------|---------------|-----------------|
| **2026 New** | Long Production (80%+) | Force Complete (60%+) |
| **2025 New** | Long Production (55-60%) | Bad Interaction (28%) |
| **Mature (2023-2025)** | Bad Interaction (32-33%) | Long Production (38-48%) |

#### Weekend Stress Pattern
**⚠️ CRITICAL: Weekend operations are the highest risk period for OTR misses.**

| Pattern | Typical Impact | Root Cause |
|---------|----------------|------------|
| **Friday/Saturday** | 40-50% of weekly late orders | Volume surge + insufficient staffing |
| **Late Rate** | 2x weekday late rate (6-8% vs 3-4%) | Kitchen capacity can't scale |
| **Ops Delay** | 2x weekday delay (12-13 min vs 6-8 min) | Execution speed degrades under stress |

**Key Insight:** Weekend late orders are concentrated in:
- **NSO stores** (2025/2026 New) — 60-70% of weekend late orders
- **Suburban locations** — higher volume + ops challenges
- **High-IPC orders** — complex orders break down first

**Action:** Always review weekend staffing and capacity planning when investigating OTR degradation.

#### NSO Concentration Pattern
**⚠️ CRITICAL: NSO stores drive disproportionate share of late orders.**

| Segment | Typical % of Late Orders | Typical % of Volume | Concentration Factor |
|---------|--------------------------|---------------------|---------------------|
| **NSO + Suburban + 2025 New** | 25-35% | 15-20% | 1.5-2.0x |
| **NSO + Urban + 2025 New** | 5-10% | 8-12% | 0.8-1.2x |
| **Mature + Suburban** | 15-20% | 25-30% | 0.6-0.8x |
| **Mature + Urban** | 10-15% | 20-25% | 0.5-0.7x |

**Key Insight:** NSO Suburban 2025 New stores are the highest concentration — typically 30%+ of late orders with only 15-20% of volume. These stores have:
- **16+ min ops delay** (vs 6-8 min mature)
- **2x late rate** (8-10% vs 4-5% mature)
- **Not stabilizing** on expected timeline (still struggling at 8-11 weeks open)

**Action:** Focus NSO stabilization efforts on Suburban 2025 New locations first.

#### Top Offending HDR Pattern
**⚠️ CRITICAL: Top offenders consistently follow a pattern.**

| Pattern | Typical Characteristics | Root Cause |
|---------|------------------------|------------|
| **2025/2026 New Class** | 80-90% of top 10 offenders | Not stabilizing on expected timeline |
| **8-11 Weeks Open** | Sweet spot for worst performance | Past initial ramp, not yet mature |
| **18-25 min Ops Delay** | 2-3x network average | Kitchen execution speed + capacity |
| **15-20% Late Rate** | 3-4x network average (5-6%) | Multiple compounding issues |

**Key Insight:** Top offending HDRs typically have:
- **Long Production** (70-80% of late orders) — execution speed issue
- **Long Queue** (50-60% of late orders) — capacity constraint
- **High Force Complete** (40-50% FC rate) — rescue FCs, not aggressive
- **Weekend collapse** — late rate 2-3x weekday rate

**Action:** When investigating top offenders, check:
1. Pod-level performance (Cold Pod often the bottleneck)
2. Weekend vs weekday staffing ratios
3. Items per order (high IPC = more complex = breaks first)
4. Force Complete pattern (rescue vs aggressive)

### 5. Volume Normalization for WoW Comparisons

**⚠️ CRITICAL: Always normalize volume comparisons for holidays and new HDR openings.**

When comparing week-over-week volume, account for:

#### Holidays
| Holiday | Typical Impact | How to Normalize |
|---------|----------------|------------------|
| New Year's Day (Jan 1) | -5 to -15% | Exclude Thursday or compare ex-holiday |
| Thanksgiving | -30 to -50% | Compare to prior non-holiday week |
| Christmas | -40 to -60% | Compare to prior non-holiday week |

#### New HDR Openings
New HDRs can inflate WoW volume growth. Always calculate:
1. **All HDRs (incl new):** Raw comparison
2. **Same-Store:** Exclude HDRs that opened in current week
3. **Same-Store ex Holiday:** Exclude both new HDRs AND holiday day

```sql
-- Check for new HDRs opened in current week
WITH hdr_first_order AS (
  SELECT hdr_id, MIN(service_date_et) AS first_order_date
  FROM hdr_orders
  WHERE order_status = 'COMPLETE' AND brand_category = 'WONDER_HDR'
  GROUP BY 1
)
SELECT hdr_id FROM hdr_first_order
WHERE first_order_date >= '[CURRENT_WEEK_START]';

-- Same-store comparison (exclude new HDRs)
WITH existing_hdrs AS (
  SELECT DISTINCT hdr_id FROM hdr_orders
  WHERE service_date_et < '[CURRENT_WEEK_START]'
)
SELECT week, SUM(orders) AS total
FROM orders o
JOIN existing_hdrs e ON o.hdr_id = e.hdr_id
GROUP BY week;
```

#### Volume vs Records
Compare to `hdr_records.weekly_total_orders_record` to understand if weeks are normal or suppressed:
```sql
SELECT 
  week,
  SUM(orders) AS actual,
  AVG(r.weekly_total_orders_record) AS record,
  SUM(orders) * 100.0 / AVG(r.weekly_total_orders_record) AS pct_of_record
FROM orders o
JOIN hdr_records r ON o.hdr_id = r.hdr_id
GROUP BY week;
```

**Key Insight:** If both weeks are 40-50% of record, volume differences may be noise rather than real growth.

---

### 6. Queue Time Analysis: Sequencer Holdback vs Capacity

Understanding queue time requires separating sequencer-driven delays from capacity constraints.

#### ⚠️ CRITICAL: 1P vs 3P Order Architecture (MRO Support)

**1P orders support MRO (Multi-Restaurant Orders). 3P orders do NOT.**

| Capability | 1P Orders | 3P Orders |
|------------|-----------|-----------|
| **MRO Support** | ✅ Yes | ❌ No |
| **Multi-Restaurant Items** | Can combine items from multiple restaurants in one order | Single restaurant only |
| **Item Coordination** | Sequencer orchestrates timing across restaurants | Items fire immediately, no cross-restaurant sync |
| **Expo Wait Impact** | Higher (MRO coordination) | Lower (single restaurant, no MRO) |

**What is MRO (Multi-Restaurant Order)?**
- A single customer order containing items from **multiple restaurant brands** (e.g., Bobby Flay burger + Di Fara pizza)
- Requires the sequencer to coordinate cooking across different pods/restaurants
- All items must be ready together for a single handoff → creates intentional expo wait

**Why this matters for analysis:**
- 1P expo wait includes **MRO coordination time** when orders span multiple restaurants
- 3P orders are single-restaurant only — no MRO complexity → lower expo wait
- **Don't compare 1P and 3P expo wait directly** — 1P handles more complex multi-restaurant orders

#### ⚠️ CRITICAL: Sequencer Selection Bias

**The sequencer is applied to MORE COMPLEX orders by design.** When you cut data by "sequencer involved" vs "not involved", you will see worse metrics for sequencer orders. This does NOT mean sequencer CAUSED the problem — it handled harder orders.

| Metric | With Holdback | Without Holdback | Why Different? |
|--------|---------------|------------------|----------------|
| Avg Queue | 2.65 min | 1.64 min | Complex orders need orchestration |
| Avg Ticket Time | 17.4 min | 9.8 min | More items, longer cook times |
| % Long Queue | 13.0% | 6.2% | Expected for multi-item orders |

**Proper Analysis:** Compare sequencer vs non-sequencer **within the same complexity tier** (see Complexity Analysis section). If same-tier OTR is worse with sequencer → Sequencer issue. If same/better → Sequencer is helping.

### ✅ Sequencer Validation: Expo Wait vs Step Time Variance

**The sequencer is working correctly if:**
```
Expo Wait Time < Step Time Variance (cook_time_range)
```

| Metric | Definition |
|--------|------------|
| **Expo Wait Time** | Time first item waits at expo for other items to complete |
| **Step Time Variance** | MAX(expected_step_time) - MIN(expected_step_time) across items in order |

**Logic:**
- Step time variance = the spread in cook times between items
- If expo wait < variance → Sequencer successfully coordinated items to finish together
- If expo wait > variance → Items sitting too long; sequencer may be over-holding OR ops issue

**Validation Query:**
```sql
SELECT
  CASE 
    WHEN order_level_expo_wait_time <= cook_time_range THEN 'Sequencer Working'
    WHEN order_level_expo_wait_time > cook_time_range THEN 'Expo Wait Exceeded Variance'
  END AS sequencer_status,
  COUNT(DISTINCT order_id) AS orders,
  ROUND(AVG(order_level_expo_wait_time), 1) AS avg_expo_wait,
  ROUND(AVG(cook_time_range), 1) AS avg_cook_time_range,
  ROUND((1 - SAFE_DIVIDE(
    COUNT(DISTINCT CASE WHEN on_time_issue THEN order_id END),
    COUNT(DISTINCT order_id)
  )) * 100, 1) AS otr_pct
FROM (
  SELECT
    o.order_id,
    ot.order_level_expo_wait_time,
    ot.on_time_issue,
    -- Cook time range: spread of cook times in order
    MAX(ki.expected_step_time/60.0) - MIN(ki.expected_step_time/60.0) AS cook_time_range
  FROM `wonder-dw-prod-brd.orders.hdr_orders` o
  JOIN `wonder-dw-prod-brd.orders.hdr_on_time_orders` ot ON o.order_id = ot.order_id
  JOIN `wonder-dw-prod-brd.orders.hdr_kitchen_order_item` ki ON o.order_id = ki.order_id
  WHERE o.order_status = 'COMPLETE'
    AND o.brand_category = 'WONDER_HDR'
  GROUP BY 1, 2, 3
)
GROUP BY 1;
```

**Interpretation:**
| Scenario | Expo Wait | vs Variance | Diagnosis |
|----------|-----------|-------------|-----------|
| **Ideal** | 1-2 min | ≤ Variance | Sequencer orchestrated correctly |
| **Acceptable** | 2-4 min | ≤ Variance | Working, minor timing gaps |
| **Investigate** | >4 min | > Variance | Possible over-hold or ops delay |
| **Critical** | >8 min | >> Variance | Systematic issue |

#### Queue Scenarios
| Scenario | % of Orders | Avg Queue | OTR | Interpretation |
|----------|-------------|-----------|-----|----------------|
| No Hold + Normal Queue | ~53% | 1.3 min | 95% | Simple orders, ideal state |
| Sequencer Held + Normal Queue | ~27% | 1.2 min | 92% | Complex orders, sequencer working correctly |
| **Sequencer Held + Long Queue** | ~17% | 4.9 min | 85% | Complex orders with extended hold — investigate |
| **No Hold + Long Queue (Capacity)** | ~3% | 6.9 min | 81% | Pure capacity constraint |

#### Late Order Queue Attribution
| Scenario | % of Late Orders | Avg Queue | Root Cause |
|----------|------------------|-----------|------------|
| **Sequencer Held + Long Queue** | ~40% | 11+ min | Complex order + possible over-hold OR capacity |
| No Hold + Normal Queue | ~28% | 2 min | Cook/delivery issues (not queue) |
| Sequencer Held + Normal Queue | ~22% | 1 min | Cook/delivery issues (not queue) |
| **No Hold + Long Queue (Capacity)** | ~9% | 11 min | Pure capacity — needs staffing |

**Key Insight:** 
- ~40% of late orders have sequencer holdback + long queue — BUT these are complex orders that inherently take longer
- ~9% are pure capacity constraints (no sequencer hold but still long queue) — these are actionable via staffing
- To determine if sequencer is over-holding, compare to expected cook time and complexity tier

#### Queue Driver Analysis
| Factor | Impact | Evidence | Actionable? |
|--------|--------|----------|-------------|
| **Volume** | r ≈ 0.43 | High-volume HDRs have 2.6x longer queue | Yes — staffing |
| **Maturity** | Strong | NSO has 2-2.5x longer queue than mature | Yes — training |
| **Daypart** | Moderate | Dinner peak has 70% more queue than off-peak | Yes — peak staffing |
| **Order Complexity** | Strong | Complex orders have longer queue BY DESIGN | No — expected |

**Note on Sequencer:** Orders with sequencer holdback have ~1 min longer queue, but these are inherently more complex orders. The sequencer is HELPING these orders — without it, they would likely have worse OTR due to food sitting.

### 5b. Capacity & Staffing Analysis

#### Orders Per Hour Framework
| Daypart | Typical Orders/Hour | Queue Expectation | Action if Elevated |
|---------|---------------------|-------------------|-------------------|
| **Dinner (5-8pm)** | 80-100+ | Higher (2+ min) | Peak staffing |
| **Lunch (11am-1pm)** | 50-70 | Moderate (1.5 min) | Monitor |
| **Off-Peak** | 20-40 | Low (1 min) | Baseline |

#### Volume Tier Diagnosis
| Volume Tier | Typical Queue | If Queue Elevated | Diagnosis |
|-------------|---------------|-------------------|-----------|
| High (300+/day) | 3-4 min | Expected | Capacity constrained, staff up |
| Medium (200-300/day) | 2-3 min | Investigate | May need staffing |
| Low (100-200/day) | 1-2 min | Ops issue | Training needed |
| Very Low (<100/day) | <1 min | Ops issue | Investigate execution |

### 5c. Bad Interaction Analysis

#### What Causes Bad Interactions?
| Root Cause | Description | Identification | Fix |
|------------|-------------|----------------|-----|
| **ALM Held Too Long** | Sequencer waits for other items | High ALM % + Bad Int | Algorithm tuning |
| **Hot Hold Mismatch** | System expected pouch, wasn't there | `has_missing_pouch` | Inventory sync |
| **Release Too Early** | Items released before optimal | Trickling violations | Release logic |
| **MRO Sync Issues** | Multi-restaurant orders misaligned | High MRO % + Bad Int | MRO handling |

#### Bad Interaction Enrichment
- Network baseline: ~22% of all orders, ~26% of late orders
- Enrichment: +4 pts — moderate predictor of lateness
- **Key insight:** Bad interactions correlate with ALM items. Control for ALM % when comparing HDRs.

### 5d. ETA Analysis: Over/Under Prediction

#### Prediction Error Impact
| Error Type | Definition | OTR Impact | Customer Impact |
|------------|------------|------------|-----------------|
| **Under-prediction** | Actual > Estimated | Direct SLA miss | "Late" even if ops normal |
| **Over-prediction** | Actual < Estimated | No SLA impact | Early arrival, food may sit |
| **Accurate** | Within ±5 min | Ideal | Correct expectations |

#### Typical Error by Component
| Component | Typical Error | If Elevated | Fix Owner |
|-----------|---------------|-------------|-----------|
| **Queue Error** | ±1-2 min | Capacity or sequencer | Ops/Product |
| **Cook Error** | ±2-3 min | Recipe timing | Culinary |
| **Transit Error** | ±3-5 min | Route/traffic | Logistics/ETA model |

#### Under-Prediction Impact
When ETA is too optimistic:
1. Kitchen executes normally (e.g., 15 min ticket)
2. But we promised 12 min → Customer sees "3 min late"
3. OTR hit even though ops was fine

**Diagnosis:** If HDR has normal timing metrics but poor OTR, check ETA underestimation.

### 6. Courier Platform Analysis

#### Platform Performance Benchmarks
| Platform | Typical OTR | Courier Resp | Transit | Best For |
|----------|-------------|--------------|---------|----------|
| **RELAY** | 88-89% | 0.6-0.9 min | 7 min | Urban |
| **GRUB_HUB** | 85-86% | 1.3-1.6 min | 11 min | Suburban, Mature |
| **DOORDASH** | 68-69% | 5-6 min | 12 min | Avoid |

#### Late Order Fault by Platform
| Platform | Kitchen Late | Courier Slow | Primary Issue |
|----------|--------------|--------------|---------------|
| GRUB_HUB | ~57% | ~23% | Kitchen |
| RELAY | ~53% | ~27% | Balanced |
| DOORDASH | ~42% | **~54%** | Courier |

### 7. Achievability Analysis

#### Late Order Severity Distribution
| Tier | % of Delivery Late | % of Pickup Late | Ease of Fix |
|------|-------------------|------------------|-------------|
| 1-4 min late | ~39% | ~52% | Easy wins |
| 5-15 min late | ~40% | ~36% | Achievable |
| 16-30 min late | ~13% | ~8% | Hard |
| 31+ min late | ~7% | ~4% | Systemic |

#### OTR Uplift Potential
| Fix | Orders Saved | OTR Uplift |
|-----|--------------|------------|
| 1-4 min late | ~2,400 | +2-3 pts |
| 1-15 min late | ~4,600 | +4-5 pts |
| All late | ~5,600 | +7-8 pts |

### 8. Bottom Performer Deep Dive Template

For each bottom 5 HDR, report:
1. **OTR** (All, Delivery, Pickup)
2. **Delivery Mix** vs network and expected OTR
3. **Timing** (Ticket, Queue, Cook, Courier Resp, Handoff)
4. **Reason Codes** (Long Prod, Bad Interaction, Force Complete, Long Queue, Trickling)
5. **Queue Attribution** (Sequencer Hold + Long Queue vs Capacity Only)
6. **Primary Driver** (Ops vs Sequencer vs Capacity vs Courier)
7. **Recommended Action**

---

## 📋 WBR Output Template (Confluence Format)

When generating a WBR summary, use this comprehensive format. **Pay attention to scope labels** to clarify which data is being shown.

### Scope Labels Used in This Template:
- **[ALL 1P]** = All 1P orders (Delivery + Pickup), excludes 3P/Wonder Spot
- **[1P DELIVERY]** = 1P Delivery orders only
- **[1P PICKUP]** = 1P Pickup orders only
- **[LATE ORDERS]** = Late orders only (on_time_issue = TRUE AND otr_sla_tier LIKE '%LATE')

```markdown
# 📊 1P On-Time Rate Weekly Business Review
## Week of [DATE RANGE]

---

# Executive Summary [ALL 1P]

| Metric | Prior Week | Current Week | WoW Change | Status |
|--------|------------|--------------|------------|--------|
| **Total Orders** | XX,XXX | XX,XXX | +X.X% | 📈/📉 |
| **Network OTR** | XX.X% | XX.X% | +X.X pts | ✅/⚠️/🔴 |
| Delivery OTR | XX.X% | XX.X% | +X.X pts | |
| Pickup OTR | XX.X% | XX.X% | +X.X pts | |
| **Late Orders** | X,XXX (X.X%) | X,XXX (X.X%) | +X.X% | 🔴 |
| Early Orders (9+ min) | X,XXX (X.X%) | X,XXX (X.X%) | +X.X pts | |
| Avg Ticket Time | X.X min | X.X min | +X.X min | |
| Late Ticket Time | X.X min | X.X min | +X.X min | 🔴 |
| Avg Expo Wait | X.X min | X.X min | +X.X min | |
| Late Expo Wait | X.X min | X.X min | +X.X min | |

### 🚨 Attribution Shift Summary [LATE ORDERS]
| Week | Ops Mins | Ops % | Logistics Mins | Logistics % | Primary Driver |
|------|----------|-------|----------------|-------------|----------------|
| Prior | X.X min | XX% | X.X min | XX% | 🚚/🍳/⚖️ |
| Current | X.X min | XX% | X.X min | XX% | 🚚/🍳/⚖️ |
| **Change** | +X.X min | +XX pts | +X.X min | +XX pts | |

**📝 Executive Summary Narrative:**

[Summarize the week in 3-4 sentences. Example:]
> Volume surged +22% week-over-week, but kitchen operations couldn't scale proportionally. Late orders increased +34% despite logistics improvements (courier response improved -3.3 min). The attribution shift from logistics-driven (74% prior) to balanced (56% ops, 53% logistics) indicates the kitchen became the bottleneck. Weekend operations (Friday/Saturday) collapsed, driving 75% of the ops degradation.

**Bottom Line:** [One sentence summary of the primary issue and impact]

---

# 1. On-Time Rate Performance [ALL 1P]

## 1.1 Network Summary
| Segment | Orders | OTR | Late Orders | Early Orders | On-Time |
|---------|--------|-----|-------------|--------------|---------|
| **All 1P** | XX,XXX | XX.X% | X,XXX (X.X%) | X,XXX (X.X%) | XX,XXX (XX.X%) |
| Delivery | XX,XXX | XX.X% | X,XXX (X.X%) | X,XXX (X.X%) | XX,XXX (XX.X%) |
| Pickup | XX,XXX | XX.X% | X,XXX (X.X%) | X,XXX (X.X%) | XX,XXX (XX.X%) |

**📝 Insight:** [e.g., "Delivery drives X% of late orders despite only X% of volume. Pickup OTR declined -X pts, watch for capacity issues."]

## 1.2 By Maturity (16 week threshold) [ALL 1P]
| Segment | Orders | OTR | Late Rate | Ops Mins | Logistics Mins | Driver |
|---------|--------|-----|-----------|----------|----------------|--------|
| Mature (16+ wks) | XX,XXX | XX.X% | X.X% | X min (XX%) | X min (XX%) | 🚚/🍳/⚖️ |
| NSO (0-15 wks) | XX,XXX | XX.X% | X.X% | X min (XX%) | X min (XX%) | 🚚/🍳/⚖️ |
| Gap | | X.X pts | +X.X pts | | | |

**📝 Insight:** [e.g., "NSO locations running 2.3x the late rate of mature stores (9.5% vs 4.2%). NSO is ops-driven (73%), while mature is logistics-driven (66%). Focus on kitchen execution at new stores."]

## 1.3 By Population Type [ALL 1P]
| Segment | Orders | OTR | Late Rate | Ops Mins | Logistics Mins | Driver |
|---------|--------|-----|-----------|----------|----------------|--------|
| Big Box | X,XXX | XX.X% | X.X% | X min (XX%) | X min (XX%) | |
| Urban | XX,XXX | XX.X% | X.X% | X min (XX%) | X min (XX%) | |
| Suburban | XX,XXX | XX.X% | X.X% | X min (XX%) | X min (XX%) | |

**📝 Insight:** [e.g., "Suburban drives X% of late orders despite X% of volume — X pt OTR gap vs Urban. Suburban is balanced/ops-driven while Big Box is logistics-driven."]

## 1.4 By HDR Class [ALL 1P]
| Class | Orders | OTR | Late Orders | WoW Ops Change |
|-------|--------|-----|-------------|----------------|
| 2023 | XX,XXX | XX.X% | XXX | +X.X min |
| 2024 | XX,XXX | XX.X% | XXX | +X.X min |
| 2025 | XX,XXX | XX.X% | XXX | +X.X min |
| 2025 New | XX,XXX | XX.X% | X,XXX | +X.X min 🔴 |
| 2026 New | X,XXX | XX.X% | XXX | +X.X min 🔴 |

**📝 Insight:** [e.g., "2025/2026 New classes account for X% of late orders with only X% of volume. Ops degradation concentrated in new stores (+8-13 min WoW) while mature classes stable (+0.8-1.9 min)."]

---

# 2. Ticket Time Summary [ALL 1P]

*Bagging = order_pending_bagging_utc → actual_ready_for_pickup_time_utc*

## 2.1 All Orders vs Late Orders
| Segment | Orders | Ticket Time | Queue | Cook | Bagging | Late Ticket | Late Queue | Late Cook |
|---------|--------|-------------|-------|------|---------|-------------|------------|-----------|
| **Network** | XX,XXX | X.X min | X.X | X.X | X.X | X.X min | X.X | X.X |
| Mature | XX,XXX | X.X min | X.X | X.X | X.X | X.X min | X.X | X.X |
| NSO | XX,XXX | X.X min | X.X | X.X | X.X | X.X min | X.X | X.X |

**📝 Insight:** [e.g., "NSO late ticket time (43.6 min) is 2x mature (20.5 min). Both queue and cook are elevated at NSO — this is kitchen throughput, not just one component."]

## 2.2 Week-over-Week Change [ALL 1P]
| Component | Prior Week | Current Week | Change |
|-----------|------------|--------------|--------|
| Ticket Time | X.X min | X.X min | +X.X min |
| Queue | X.X min | X.X min | +X.X min |
| Cook | X.X min | X.X min | +X.X min |
| **Late Ticket Time** | X.X min | X.X min | +X.X min 🔴 |

**📝 Insight:** [e.g., "Late ticket time increased X% (+X min). Cook error (+103%) and queue error (+75%) both degraded — kitchen couldn't scale with volume surge."]

---

# 3. Expo Wait Time Deep Dive [ALL ORDERS]

*Note: Expo wait analysis covers ALL orders (1P + 3P) to capture complete kitchen handoff performance.*

## 3.1 Executive Summary
| Metric | Prior Week | Current Week | Change | Status |
|--------|------------|--------------|--------|--------|
| **Total Orders** | XX,XXX | XX,XXX | +X.X% | 📈/📉 |
| **Avg Expo Wait** | X.X min | X.X min | +X.X min | ✅/⚠️ |
| **Late Expo Wait** | X.X min | X.X min | +X.X min | 🔴 |
| % Orders >5 min | XX.X% | XX.X% | +X.X pts | |
| % Orders >10 min | XX.X% | XX.X% | +X.X pts | |

**📝 Insight:** [e.g., "Average expo wait held steady, but late order expo wait increased X% — when orders fall behind, they're waiting longer at expo. The tail is getting worse."]

## 3.2 By Channel Type (1P vs 3P)
| Channel | Orders | Mix | Avg Expo | Late Expo | >5 min |
|---------|--------|-----|----------|-----------|--------|
| **1P** | XX,XXX | XX% | X.X min | X.X min | XX.X% |
| **3P** | XX,XXX | XX% | X.X min | X.X min | XX.X% |

**⚠️ CRITICAL: 1P vs 3P Expo Wait Difference Explained**

*See detailed explanation in "1P vs 3P Order Architecture (MRO Support)" section above.*

| Channel | Supports MRO | Avg Expo | Late Expo | Interpretation |
|---------|--------------|----------|-----------|----------------|
| **1P** | ✅ Yes | X.X min | X.X min | Higher expo expected due to MRO coordination |
| **3P** | ❌ No | X.X min | X.X min | Lower expo — single restaurant only, no MRO |

**📝 Insight:** [e.g., "1P orders have X% higher expo wait than 3P. This is expected — 1P supports Multi-Restaurant Orders (MRO) which require cross-restaurant coordination. 3P is single-restaurant only with no MRO complexity."]

## 3.3 By Maturity
| Segment | Orders | Avg Expo | Late Expo | >5 min | >10 min |
|---------|--------|----------|-----------|--------|---------|
| **Mature** | XX,XXX | X.X min | X.X min | XX.X% | XX.X% |
| **NSO** | XX,XXX | X.X min | X.X min | XX.X% | XX.X% |
| **Gap** | | +X.X min | +X.X min | +X.X pts | +X.X pts |

**📝 Insight:** [e.g., "NSO expo wait is X% higher than Mature. NSO kitchens finish cooking but struggle with handoff coordination — likely due to inexperienced expo staff."]

## 3.4 By Population Type
| Population | Orders | Avg Expo | Late Expo | >5 min | >10 min |
|------------|--------|----------|-----------|--------|---------|
| **Suburban** | XX,XXX | X.X min | X.X min | XX.X% | XX.X% |
| Urban | XX,XXX | X.X min | X.X min | XX.X% | XX.X% |
| Big Box | X,XXX | X.X min | X.X min | XX.X% | XX.X% |

**📝 Insight:** [e.g., "Suburban expo wait is X% higher than Urban. Correlates with ops issues at Suburban locations."]

## 3.5 By IPC (Items Per Check)
| IPC | Orders | Mix | Avg Expo | Late Expo | >5 min |
|-----|--------|-----|----------|-----------|--------|
| **1 item** | XX,XXX | XX% | X.X min | X.X min | X.X% |
| **2 items** | XX,XXX | XX% | X.X min | X.X min | XX.X% |
| **3 items** | XX,XXX | XX% | X.X min | X.X min | XX.X% |
| **4-5 items** | XX,XXX | XX% | X.X min | X.X min | XX.X% |
| **6+ items** | XX,XXX | XX% | X.X min | X.X min | XX.X% |

**📝 Insight:** [e.g., "Expo wait scales 7x from 1-item to 6+ items (1.6 → 11.2 min). Each additional item adds ~2 min. Order complexity is the strongest driver of expo wait."]

## 3.6 By Force Complete Status
| Completion Type | Orders | Mix | Avg Expo | Late Expo | >5 min | >10 min | Avg IPC | OTR |
|-----------------|--------|-----|----------|-----------|--------|---------|---------|-----|
| **Force Complete** | XX,XXX | XX% | X.X min | X.X min | XX.X% | XX.X% | X.X | XX.X% |
| **Normal Complete** | XX,XXX | XX% | X.X min | X.X min | XX.X% | XX.X% | X.X | XX.X% |

**📝 Insight:** [e.g., "FC orders have X% higher expo wait than normal orders (5.7 vs 5.0 min). FC orders are already behind when completed, so they accumulate more expo wait before pickup."]

## 3.7 FC x Maturity Cross-Tab
| Maturity | Completion | Orders | Avg Expo | Late Expo | >5 min |
|----------|------------|--------|----------|-----------|--------|
| Mature | FC | XX,XXX | X.X min | X.X min | XX.X% |
| Mature | Normal | XX,XXX | X.X min | X.X min | XX.X% |
| **NSO** | **FC** | X,XXX | **X.X min** | **X.X min** | **XX.X%** |
| NSO | Normal | XX,XXX | X.X min | X.X min | XX.X% |

**📝 Insight:** [e.g., "NSO + FC orders have highest expo wait (8.0 min) — 78% higher than Mature + Normal (4.5 min). FC at NSO stores is a compounding problem."]

## 3.8 FC Impact at Bottom HDRs
| HDR | FC Orders | FC Expo | Normal Expo | **FC Premium** | FC >10 min | Normal >10 min |
|-----|-----------|---------|-------------|----------------|------------|----------------|
| [HDR 1] | XXX | X.X min | X.X min | **+X.X min** | XX.X% | XX.X% |
| [HDR 2] | XXX | X.X min | X.X min | +X.X min | XX.X% | XX.X% |
| (etc.) | | | | | | |

**📝 Insight:** [e.g., "At worst HDRs, FC orders have 3-4 min higher expo wait than normal orders. FC premium highest at Bellmore (+3.2 min) and Wilmington (+3.1 min). This confirms FC orders are already significantly behind when they reach expo."]

**Key Finding: FC + Expo Wait Relationship**
- FC orders have **14% higher expo wait** network-wide
- At NSO stores, FC orders have **27% higher expo wait** (8.0 vs 6.3 min)
- At bottom HDRs, FC orders wait **3-4 min longer** at expo
- **Interpretation:** FC is a symptom of items falling behind → more expo wait is the consequence

## 3.9 Bottom 10 HDRs by Expo Wait
| HDR | Class | Wks Open | Orders | Avg Expo | Late Expo | >5 min | >10 min |
|-----|-------|----------|--------|----------|-----------|--------|---------|
| [HDR 1] | 2025 New | X | X,XXX | X.X min | X.X min | XX.X% | XX.X% |
| [HDR 2] | 2025 New | X | X,XXX | X.X min | X.X min | XX.X% | XX.X% |
| (etc.) | | | | | | | |

**📝 Insight:** [e.g., "9 of 10 worst expo HDRs are NSO. Top 3 have 2x network expo wait. Investigate if mature stores appear on this list — they're anomalies."]

---

# 4. Late Delivery Attribution [1P DELIVERY, LATE ORDERS]

## 4.1 ⚠️ Critical: "Fast Handoff" ≠ "Kitchen On-Time"

| Pickup Scenario | Late Orders | % | Queue Error | Cook Error | Pickup Error | Transit Error | Total |
|-----------------|-------------|---|-------------|------------|--------------|---------------|-------|
| **Both Fast** | X,XXX | XX% | -X.X min | -X.X min | +X.X min | -X.X min | -X.X min |
| Ops Fault | XXX | XX% | -X.X min | -X.X min | -X.X min | -X.X min | -X.X min |
| Courier Late | XXX | XX% | -X.X min | -X.X min | -X.X min | -X.X min | -X.X min |
| Both Slow | XXX | XX% | -X.X min | -X.X min | -X.X min | -X.X min | -X.X min |

*(Negative = Late)*

### Key Insight: "Both Fast" Breakdown [1P DELIVERY, LATE ORDERS]
| Error Source | Minutes Late | % of Lateness |
|--------------|--------------|---------------|
| **Kitchen (Queue + Cook)** | X.X min | XX% |
| **Transit** | X.X min | XX% |

**❌ WRONG:** "Both Fast = Kitchen doing fine, must be transit"
**✅ CORRECT:** "Both Fast = Handoff efficient, but kitchen was ALREADY X min behind when food went out"

**📝 Insight:** [e.g., "40% of late delivery orders had 'fast' handoff AND courier, but kitchen was already 11 min behind. Don't use 'Both Fast' as a comfort metric — it means the courier picked up efficiently, not that the kitchen was on time."]

---

# 5. Per-Order Lateness Attribution Model [ALL 1P, LATE ORDERS]

| Segment | Late Orders | Late Rate | Avg Late | Ops | Ops % | Logistics | Log % | Primary Driver |
|---------|-------------|-----------|----------|-----|-------|-----------|-------|----------------|
| **Network** | X,XXX | X.X% | X min | X min | XX% | X min | XX% | ⚖️/🚚/🍳 |
| Mature | X,XXX | X.X% | X min | X min | XX% | X min | XX% | |
| NSO | X,XXX | X.X% | X min | X min | XX% | X min | XX% | |
| Suburban | X,XXX | X.X% | X min | X min | XX% | X min | XX% | |
| Urban | X,XXX | X.X% | X min | X min | XX% | X min | XX% | |
| Big Box | XX | X.X% | X min | X min | XX% | X min | XX% | |

**📝 Insight:** [e.g., "NSO is heavily ops-driven (73% / 18 min) while Mature is logistics-driven (66% / 11 min). Suburban and Urban are balanced. This confirms kitchen execution is the primary opportunity at new stores."]

---

# 6. Attribution Change Drivers (WoW) [LATE ORDERS]

## 6.1 Error Component Changes [1P DELIVERY, LATE ORDERS]
| Component | Prior Week | Current Week | **Change** | Direction |
|-----------|------------|--------------|------------|-----------|
| **🍳 OPS** |
| Queue Error | X.X min | X.X min | +X.X min (+XX%) | 📉 |
| Cook Error | X.X min | X.X min | +X.X min (+XX%) | 📉 |
| **Total Ops** | X.X min | X.X min | +X.X min | 🔴 |
| **🚚 LOGISTICS** |
| Pickup Error | X.X min | X.X min | -X.X min (-XX%) | ✅ |
| Transit Error | X.X min | X.X min | +X.X min | ⚠️ |
| Courier Response | X.X min | X.X min | -X.X min (-XX%) | ✅ |

**📝 Insight:** [e.g., "Courier partners improved significantly (-3.3 min response, -3.0 min pickup), but kitchen degraded faster. Cook error doubled (+103%), queue error up 75%. The attribution shift from logistics-driven to balanced means kitchen is now the bottleneck."]

## 6.2 By Day of Week [ALL 1P, LATE ORDERS]
| Day | Prior Late | Current Late | Ops Change | Key Finding |
|-----|------------|--------------|------------|-------------|
| Friday | XXX | X,XXX | +X.X min | 🔴 Collapsed |
| Saturday | XXX | X,XXX | +X.X min | 🔴 Collapsed |
| (other days) | | | | |

**📝 Insight:** [e.g., "Friday/Saturday drove 75% of ops degradation. Late orders 3x'd on both days. Weekday ops relatively stable (+0.2 to +2.3 min). Weekend staffing needs immediate review."]

## 6.3 By Population Type [ALL 1P, LATE ORDERS]
| Population | Prior Late | Current Late | Ops Change | Log Change |
|------------|------------|--------------|------------|------------|
| Suburban | X,XXX | X,XXX | +X.X min | -X.X min |
| Urban | X,XXX | X,XXX | +X.X min | -X.X min |
| Big Box | XX | XX | +X.X min | +X.X min |

**📝 Insight:** [e.g., "Suburban saw +71% late orders and +5.3 min ops degradation. Urban improved on logistics (-5.3 min) but still had ops issues (+3.0 min). Big Box stable."]

## 6.4 By HDR Class [ALL 1P, LATE ORDERS]
| Class | Prior Late | Current Late | Ops Change | Key Finding |
|-------|------------|--------------|------------|-------------|
| 2026 New | X | XXX | +X.X min | 🔴 New stores |
| 2025 New | XXX | X,XXX | +X.X min | 🔴 |
| 2023-2025 | Varies | Varies | +X.X min | Stable |

**📝 Insight:** [e.g., "New classes (2025 New, 2026 New) account for 50% of late orders with only 32% of volume. Ops degradation 5-10x worse at new stores vs mature (+8-13 min vs +0.8-1.9 min)."]

## 6.5 Top Offending HDRs [ALL 1P, LATE ORDERS]
| HDR | Class | Prior Late | Current Late | Ops Change |
|-----|-------|------------|--------------|------------|
| [HDR 1] | 2025 New | XX | XXX | +X.X min 🔴 |
| [HDR 2] | 2025 New | XX | XXX | +X.X min 🔴 |
| (etc.) | | | | |

**📝 Insight:** [e.g., "Top 5 offenders are all 2025/2026 New class. Wilmington and Holbrook saw late orders 5x. These stores are not stabilizing on expected timeline and need immediate intervention."]

---

# 7. Reason Code Analysis [ALL 1P, LATE ORDERS]

| Reason Code | Prior Week | Current Week | **Change** | Owner |
|-------------|------------|--------------|------------|-------|
| Long Production | XX.X% | XX.X% | +X.X pts | Ops |
| Long Queue | XX.X% | XX.X% | +X.X pts | Capacity |
| Force Complete | XX.X% | XX.X% | +X.X pts | Training |
| Trickling | XX.X% | XX.X% | +X.X pts | Sequencer |
| ALM Items | XX.X% | XX.X% | +X.X pts | Menu |
| Bad Interaction | XX.X% | XX.X% | +X.X pts | Sequencer |

**📝 Insight:** [e.g., "Long Production remains the strongest predictor (+22 pt enrichment vs all orders). Long Queue and Force Complete both increased +4 pts — capacity pressure and rescue FCs increasing. This pattern confirms kitchen throughput is the bottleneck."]

---

# 8. Force Complete & Pod Diagnosis [ALL 1P]

## 8.1 Force Complete Summary
| HDR | FC Rate | Network | vs Network | FC + Late % | Non-FC + Late % | Pattern |
|-----|---------|---------|------------|-------------|-----------------|---------|
| [HDR 1] | XX.X% | 18.0% | +XX.X pts | XX.X% | XX.X% | 🔴 RESCUE / 🟠 Process |
| [HDR 2] | XX.X% | 18.0% | +XX.X pts | XX.X% | XX.X% | |
| [HDR 3] | XX.X% | 18.0% | +XX.X pts | XX.X% | XX.X% | |
| [HDR 4] | XX.X% | 18.0% | +XX.X pts | XX.X% | XX.X% | |
| [HDR 5] | XX.X% | 18.0% | +XX.X pts | XX.X% | XX.X% | |

**FC Pattern Interpretation:**
*See detailed "Force Complete Pattern Analysis: Aggressive vs Rescue" section below for full methodology.*

- 🔴 **RESCUE FCs:** FC rate higher for late orders = Items already behind when FC'd (FC variance > Normal variance)
- 🟠 **Process FCs:** FC rate similar for late & on-time = Systematic FCs, review triggers (FC variance ≈ Normal variance)

**📝 Insight:** [e.g., "Hackettstown (48% FC), Wilmington (35%), and Holbrook (30%) show RESCUE pattern — late order FC% is 5-15 pts higher than on-time. These aren't aggressive FCs; they're reactive recovery attempts because items are already behind."]

## 8.2 FC Correlation with Issues (% of FC orders with each issue)
| HDR | FC + Long Prod | FC + Long Queue | FC + Bad Int | Non-FC Long Prod | Primary Driver |
|-----|----------------|-----------------|--------------|------------------|----------------|
| [HDR 1] | XX.X% | XX.X% | XX.X% | XX.X% | Long Prod / Bad Int |
| [HDR 2] | XX.X% | XX.X% | XX.X% | XX.X% | |

**📝 Insight:** [e.g., "75% of Hackettstown FCs have long production (vs 55% non-FC). Items were already behind before being force completed. Focus on execution speed, not FC reduction — 'reduce FCs' would make OTR worse, not better."]

## 8.3 Capacity vs Idle Time (Items Per Order + Step Lag)
| HDR | Orders | Avg IPC | Late IPC | Peak Orders/Hr | Avg Queue | Late Queue | Diagnosis |
|-----|--------|---------|----------|----------------|-----------|------------|-----------|
| [HDR 1] | X,XXX | X.X | X.X | XX | X.X min | XX.X min | 🔴 CAPACITY / 🔴 IDLE |
| [HDR 2] | X,XXX | X.X | X.X | XX | X.X min | XX.X min | |

**📝 Insight:** [e.g., "Late orders have +0.8-1.3 higher IPC than on-time — complex orders are getting stuck. Wilmington (79/hr peak) and Holbrook (94/hr peak) show capacity pressure. Bellmore has high queue despite normal volume — this is idle time, not capacity."]

## 8.4 Pod-Level Performance (All Orders, Including Hybrid)
| HDR | Pod | Items | Actual | Expected | **Variance** | Step Lag | vs Network | Status |
|-----|-----|-------|--------|----------|--------------|----------|------------|--------|
| [HDR 1] | Cold Pod | X,XXX | X.X min | X.X min | +X.X min | X.X sec | +X.X sec | 🔴 SLOW |
| [HDR 1] | Hot Pod | X,XXX | X.X min | X.X min | -X.X min | X.X sec | +X.X sec | ✅ OK |
| [HDR 1] | Hybrid Pod | X,XXX | X.X min | X.X min | -X.X min | X.X sec | +X.X sec | ✅ OK |
| [HDR 2] | Pizza Pod | XXX | X.X min | X.X min | +X.X min | X.X sec | — | 🔴 DRAGGING |

**Status Key:**
- 🔴 **SLOW:** Variance > +1 min (execution issue)
- 🔴 **HIGH IDLE:** Step Lag > Network + 10 sec (coordination issue)
- 🔴 **DRAGGING:** Variance > +2 min (major bottleneck)
- ✅ **OK:** Within normal range

**📝 Insight:** [e.g., "Cold Pod is ELEVATED at all 5 HDRs (+1.1 to +1.4 min variance). Holbrook Cold Pod has HIGH IDLE (29 sec step lag vs 2 sec network) — staff waiting between steps. Hackettstown Pizza Pod is DRAGGING (+2.3 min variance). Hybrid Pod is outperforming at all sites."]

## 8.5 Root Cause Summary by Site
| HDR | Primary Issue | Pod Driver | FC Pattern | Root Cause |
|-----|---------------|------------|------------|------------|
| [HDR 1] | 🔴 CAPACITY | Cold Pod slow | RESCUE | Volume + Cold Pod execution |
| [HDR 2] | 🔴 TRAINING | Pizza + Cold slow | RESCUE | New store + skills gap |
| [HDR 3] | 🔴 **IDLE TIME** | Cold Pod idle | RESCUE | Staff waiting between steps |
| [HDR 4] | 🟠 IDLE + COMPLEXITY | Hot Pod idle | Process | Staff coordination + complex orders |
| [HDR 5] | ✅ Bad Interactions | — | Process | Sequencer timing issues |

**📝 Insight:** [e.g., "Holbrook and Bellmore are NOT pure capacity problems — they have idle time issues (staff waiting). Wilmington and Hackettstown are capacity + speed problems. Different root causes require different interventions."]

---

# 9. Early Orders Analysis [1P DELIVERY]

## 9.1 Early Orders are ETA Model Driven
| Metric | Early Delivery Orders |
|--------|----------------------|
| Avg Estimated O2E | X.X min |
| Avg Actual O2E | X.X min |
| **Model Overestimate** | +X.X min 🔴 |

| SLA Bucket | Orders | Estimated | Actual | Model Error |
|------------|--------|-----------|--------|-------------|
| **Early (9+ min)** | X,XXX | X.X min | X.X min | +X.X min |
| On-Time | XX,XXX | X.X min | X.X min | +X.X min |
| Late | X,XXX | X.X min | X.X min | -X.X min |

**📝 Insight:** [e.g., "ETA model is quoting 48.5 min for orders that take 21.9 min (2.2x overestimate). Early orders are almost entirely ETA model driven, not kitchen overperformance. Product should investigate order profiles being overestimated."]

---

# 🎯 Key Takeaways

## 1. [Volume/Capacity Finding]
- [Data point]
- [Impact statement]

## 2. [Attribution Shift Finding]
- [Data point]
- [Impact statement]

## 3. [Weekend/Day-of-Week Finding]
- [Data point]
- [Impact statement]

## 4. [NSO/Maturity Finding]
- [Data point]
- [Impact statement]

## 5. [Population Finding]
- [Data point]
- [Impact statement]

## 6. [HDR-Specific Finding]
- [Data point]
- [Impact statement]

## 7. ["Both Fast" Insight]
- X% of late delivery orders had "fast" handoff AND courier
- But kitchen was already X min behind when food went out
- **Don't use "Both Fast" as a comfort metric**

## 8. [Early Orders / ETA Model Finding]
- [Data point]
- [Impact statement]

## 9. Force Complete Insight
- **Rescue FC Pattern:** If FC rate is higher for late orders than on-time orders, FCs are reactive recovery attempts
- **Root Cause Focus:** High FC + High Long Production = execution speed issue, not FC training issue
- **Pod-Specific:** Identify which pod is the bottleneck (Cold, Hot, Pizza, Hybrid) before taking action

---

# 📋 Recommended Actions

| Priority | Action | Owner |
|----------|--------|-------|
| 🔴 P0 | [Immediate action based on findings] | [Team] |
| 🔴 P0 | [Immediate action based on findings] | [Team] |
| 🔴 P0 | [Immediate action based on findings] | [Team] |
| 🟠 P1 | [Short-term action] | [Team] |
| 🟠 P1 | [Short-term action] | [Team] |
| 🟠 P1 | [Short-term action] | [Team] |
| 🟡 P2 | [Medium-term action] | [Team] |
| 🟡 P2 | [Medium-term action] | [Team] |

---

*Report generated: [DATE]*
*Data source: wonder-dw-prod-brd, validated against Looker WBR*
```

### Scope Reference

| Scope Label | Filter Criteria |
|-------------|-----------------|
| **[ALL 1P]** | `order_channel IN ('APP', 'WEB', 'IN_PERSON')` AND `brand_category = 'WONDER_HDR'` AND excludes WONDER_SPOT and 3P_PLATFORM_CORPORATE |
| **[1P DELIVERY]** | Above + `dining_option = 'DELIVERY'` |
| **[1P PICKUP]** | Above + `dining_option = 'PICKUP'` |
| **[LATE ORDERS]** | Above + `on_time_issue = TRUE AND otr_sla_tier LIKE '%LATE'` |
| **[EARLY ORDERS]** | Above + `on_time_issue = TRUE AND otr_sla_tier LIKE '%EARLY'` |

---

## Courier vs Handoff Analysis

---

## Segment Performance

### By Population Type
| Population | Orders | Mix | OTR | Ticket | Cook | Queue | Sit Time |
|------------|--------|-----|-----|--------|------|-------|----------|
| Urban | | | | | | | |
| Suburban | | | | | | | |
| Big Box | | | | | | | |

### By HDR Class
| Class | Orders | Mix | OTR | Ticket | Cook | Gap to Best |
|-------|--------|-----|-----|--------|------|-------------|
| 2024 | | | | | | — |
| 2025 | | | | | | |
| 2023 | | | | | | |
| 2025 New | | | | | | |
| 2026 New | | | | | | |

### By Maturity Phase
| Phase | Orders | Mix | OTR | Ticket | Gap to Mature |
|-------|--------|-----|-----|--------|---------------|
| 25+ wks (Mature) | | | | | — |
| 13-24 wks (Maturing) | | | | | |
| 5-12 wks (Ramp) | | | | | |
| 0-4 wks (Launch) | | | | | |

---

## Timing Breakdown (1P Delivery)

| Component | Time | % of O2E |
|-----------|------|----------|
| Queue | X.X min | X% |
| Cook | X.X min | X% |
| Pack/Bag | X.X min | X% |
| **Ticket Time** | **X.X min** | X% |
| Sit Time | X.X min | X% |
| Transit | X.X min | X% |
| **Actual O2E** | **X.X min** | 100% |
| Estimated O2E | X.X min | — |
| **O2E Error** | **-X.X min** | |

---

## Kitchen Handoff Scenarios (1P Delivery)

| Scenario | Volume | % | OTR | Courier Resp | Handoff |
|----------|--------|---|-----|--------------|---------|
| ✅ D. Ideal State | | | | | |
| 🔴 A. Kitchen LATE | | | | | |
| 🟡 B. Food Waits | | | | | |
| ⛔ C. Compounding | | | | | |

---

## Courier vs Handoff Analysis

### ⚠️ CRITICAL: "Fast Handoff" ≠ "Kitchen On-Time"

**The pickup scenario (Both Fast, Ops Fault, etc.) only measures pickup process efficiency, NOT whether kitchen was on schedule.**

A late order with "Both Fast" pickup means:
- ✅ Handoff was efficient (< 5 min)
- ✅ Courier arrived quickly (< 5 min)
- ❌ BUT kitchen was likely already 10+ minutes behind when food went out

### Error Decomposition for Late Deliveries

| Pickup Scenario | Late Orders | Queue Error | Cook Error | Pickup Error | Transit Error | Total Error |
|-----------------|-------------|-------------|------------|--------------|---------------|-------------|
| Both Fast | ~40% | -3.8 min | -7.6 min | +0.9 min | -6.8 min | -18.7 min |
| Ops Fault | ~32% | -1.8 min | -3.2 min | -12.8 min | -3.9 min | -22.0 min |
| Courier Late | ~19% | -0.9 min | -0.4 min | -16.9 min | -4.5 min | -22.6 min |
| Both Slow | ~8% | -0.1 min | -0.5 min | -27.8 min | -4.0 min | -31.3 min |

*(Negative = Late, Positive = Early)*

### 🔍 "Both Fast" Orders Are NOT Transit-Only Issues

For the ~40% of late orders with "Both Fast" pickup:

| Error Source | Minutes Late | % of Total Lateness |
|--------------|--------------|---------------------|
| Kitchen (Queue + Cook) | -11.4 min | **61%** |
| Transit | -6.8 min | 36% |
| Pickup (Handoff) | +0.9 min | (Early) |

**What this means:**
- ❌ **WRONG**: "Both Fast = Kitchen doing fine, must be transit"
- ✅ **CORRECT**: "Both Fast = Handoff was efficient, but kitchen was ALREADY 11 min behind when food went out, and transit added 7 min more"

### Revised Attribution Framework

| Scenario | What It ACTUALLY Means | Primary Driver | Secondary Driver |
|----------|------------------------|----------------|------------------|
| Both Fast | Efficient handoff, but kitchen was already late | 🍳 Kitchen (-11.4 min) | 🚚 Transit (-6.8 min) |
| Ops Fault | Slow handoff added to delays | 🍳 Kitchen/Handoff (-17.8 min) | 🚚 Transit (-3.9 min) |
| Courier Late | Courier arrival delay + transit | 🚚 Pickup+Transit (-21.4 min) | 🍳 Kitchen (-1.3 min) |
| Both Slow | Everything broke | 🍳 Pickup (-27.8 min) | 🚚 Transit (-4.0 min) |

### 💡 Actionable Insight

"Both Fast" should be split into:

1. **Kitchen-Driven Late (61%)**: Queue + Cook errors dominate
   - Fix: Address kitchen execution (staffing, pod bottlenecks)
   
2. **Transit-Driven Late (36%)**: Even if kitchen was behind, transit made it worse
   - Fix: Work with courier partners on routing/ETAs

**Recommendation:** Don't use "Both Fast" as a comfort metric - dig into `queue_error + cook_error` to see if kitchen was actually on schedule.

### Late Order Fault Attribution (Legacy)
| Upstream Status | Late Orders | % | Kitchen Delay | Courier Resp | Handoff | Ops Gap |
|-----------------|-------------|---|---------------|--------------|---------|---------|
| KITCHEN_ON_TIME | | | | | | |
| KITCHEN_PRIMARY | | | | | | |
| KITCHEN_CONTRIBUTING | | | | | | |

### Late Order Root Cause
| Root Cause | Late Orders | % of Late | % of All | Owner |
|------------|-------------|-----------|----------|-------|
| Kitchen Only | | | | Kitchen/Culinary |
| Kitchen + Handoff | | | | Kitchen + Ops |
| Handoff Only | | | | Ops (Expo) |
| Courier Only | | | | Logistics |

---

## Per-Order Lateness Attribution Model

This model attributes minutes late to specific drivers at the order level, then rolls up by segment.

### Attribution Logic

| Driver | Calculation | Description |
|--------|-------------|-------------|
| **Ops** | `GREATEST(-queue_error, 0) + GREATEST(-cook_error, 0)` | Kitchen execution (queue + cook time overruns) |
| **Logistics** | `GREATEST(-transit_error, 0) + GREATEST(-pickup_error, 0)` | Delivery only: transit + pickup delays |
| **Sequencer** | `expo_wait_mins` when: low complexity (`cook_range < 2`) + sequencer flags + `expo_wait > 2 min` | Sequencer adding delay on simple orders |
| **ETA Model** | `network_avg_o2e - estimated_o2e` when estimate was overly optimistic | Prediction error setting wrong expectations |

### Network Attribution Summary

| Segment | Late Orders | Late Rate | Avg Late | Ops | Logistics | Primary Driver |
|---------|-------------|-----------|----------|-----|-----------|----------------|
| **Network** | ~4,361 | 5.4% | 20 min | 11 min (56%) | 11 min (53%) | ⚖️ BALANCED |
| **Maturity: Mature** | ~2,660 | 4.2% | 17 min | 7 min (39%) | 11 min (66%) | 🚚 LOGISTICS-DRIVEN |
| **Maturity: NSO** | ~1,701 | 9.5% | 24 min | 18 min (73%) | 10 min (39%) | 🍳 OPS-DRIVEN |
| **Population: Suburban** | ~2,985 | 6.5% | 21 min | 12 min (59%) | 11 min (53%) | ⚖️ BALANCED |
| **Population: Urban** | ~1,340 | 3.9% | 17 min | 8 min (48%) | 9 min (53%) | ⚖️ BALANCED |
| **Population: Big Box** | ~36 | 3.1% | 21 min | 6 min (28%) | 16 min (73%) | 🚚 LOGISTICS-DRIVEN |

**Note:** Percentages can sum to >100% because both Ops and Logistics can contribute to the same late order.

### 🔍 Key Insights

1. **NSO stores are Ops-driven** (73%): Kitchen execution is the primary blocker
   - Focus: Training, staffing, process optimization

2. **Mature stores are Logistics-driven** (66%): Kitchen is stable, transit variability is the issue
   - Focus: Courier partner optimization, transit routing

3. **Suburban has the highest late rate** (6.5%): Balanced attribution suggests systemic issues
   - Focus: Both kitchen and logistics improvements needed

4. **Big Box is heavily Logistics-driven** (73%): Long transit distances
   - Focus: Courier wait time optimization, closer delivery radius

### Attribution Query

```sql
WITH order_base AS (
  SELECT 
    o.order_id,
    h.population_type,
    CASE WHEN h.calendar_weeks_from_opening_date <= 12 THEN 'NSO' ELSE 'Mature' END AS maturity,
    o.dining_option,
    COALESCE(o.queue_error, 0) AS queue_error,
    COALESCE(o.cook_error, 0) AS cook_error,
    COALESCE(o.pickup_error, 0) AS pickup_error,
    COALESCE(o.transit_error, 0) AS transit_error,
    COALESCE(o.total_eta_error, 0) AS total_eta_error,
    ot.on_time_issue,
    ot.otr_sla_tier
  FROM `wonder-dw-prod-brd.orders.hdr_orders` o
  JOIN `wonder-dw-prod-brd.dw.dim_hdrs` h ON o.hdr_id = h.hdr_id
  JOIN `wonder-dw-prod-brd.orders.hdr_on_time_orders` ot ON o.order_id = ot.order_id
  WHERE o.order_status = 'COMPLETE'
    AND o.brand_category = 'WONDER_HDR'
    AND o.order_channel IN ('APP', 'WEB', 'IN_PERSON')
    AND o.service_date_et >= DATE_TRUNC(DATE_SUB(CURRENT_DATE('America/New_York'), INTERVAL 1 WEEK), WEEK(MONDAY))
    AND o.service_date_et < DATE_TRUNC(CURRENT_DATE('America/New_York'), WEEK(MONDAY))
),
attributed AS (
  SELECT 
    *,
    CASE WHEN on_time_issue = TRUE AND otr_sla_tier LIKE '%LATE' THEN 1 ELSE 0 END AS is_late,
    GREATEST(-queue_error, 0) + GREATEST(-cook_error, 0) AS ops_mins,
    CASE WHEN dining_option = 'DELIVERY' 
         THEN GREATEST(-transit_error, 0) + GREATEST(-pickup_error, 0)
         ELSE 0 END AS logistics_mins,
    GREATEST(-total_eta_error, 0) AS total_late_mins
  FROM order_base
)
SELECT
  segment,
  late_orders,
  late_pct AS late_rate,
  avg_total_late AS avg_mins_late,
  avg_ops_mins AS ops_mins,
  ROUND(avg_ops_mins * 100.0 / NULLIF(avg_total_late, 0), 0) AS ops_pct,
  avg_logistics_mins AS logistics_mins,
  ROUND(avg_logistics_mins * 100.0 / NULLIF(avg_total_late, 0), 0) AS logistics_pct,
  CASE 
    WHEN avg_ops_mins > avg_logistics_mins * 1.3 THEN '🍳 OPS-DRIVEN'
    WHEN avg_logistics_mins > avg_ops_mins * 1.3 THEN '🚚 LOGISTICS-DRIVEN'
    ELSE '⚖️ BALANCED'
  END AS primary_driver
FROM (
  SELECT 'Network' AS segment, SUM(is_late) AS late_orders,
    ROUND(SUM(is_late) * 100.0 / COUNT(*), 1) AS late_pct,
    ROUND(AVG(CASE WHEN is_late = 1 THEN total_late_mins END), 1) AS avg_total_late,
    ROUND(AVG(CASE WHEN is_late = 1 THEN ops_mins END), 1) AS avg_ops_mins,
    ROUND(AVG(CASE WHEN is_late = 1 THEN logistics_mins END), 1) AS avg_logistics_mins
  FROM attributed
  UNION ALL
  SELECT CONCAT('Maturity: ', maturity), SUM(is_late),
    ROUND(SUM(is_late) * 100.0 / COUNT(*), 1),
    ROUND(AVG(CASE WHEN is_late = 1 THEN total_late_mins END), 1),
    ROUND(AVG(CASE WHEN is_late = 1 THEN ops_mins END), 1),
    ROUND(AVG(CASE WHEN is_late = 1 THEN logistics_mins END), 1)
  FROM attributed GROUP BY maturity
  UNION ALL
  SELECT CONCAT('Population: ', population_type), SUM(is_late),
    ROUND(SUM(is_late) * 100.0 / COUNT(*), 1),
    ROUND(AVG(CASE WHEN is_late = 1 THEN total_late_mins END), 1),
    ROUND(AVG(CASE WHEN is_late = 1 THEN ops_mins END), 1),
    ROUND(AVG(CASE WHEN is_late = 1 THEN logistics_mins END), 1)
  FROM attributed GROUP BY population_type
)
ORDER BY segment;
```

---

## Courier Platform Performance

### Overall
| Platform | Orders | Mix | OTR | O2E | Courier Resp | Transit |
|----------|--------|-----|-----|-----|--------------|---------|
| RELAY | | | | | | |
| GRUB_HUB | | | | | | |
| DOORDASH | | | | | | |

### Late Order Fault by Platform
| Platform | % Kitchen Late | % Courier Slow | Primary Issue |
|----------|----------------|----------------|---------------|
| GRUB_HUB | | | |
| RELAY | | | |
| DOORDASH | | | |

---

## Reason Code Attribution

### Network Totals
| Reason Code | All Orders | Late Orders | Enrichment | Owner |
|-------------|------------|-------------|------------|-------|
| Long Production | X% | X% | +X pts | Ops/Kitchen |
| Long Queue | X% | X% | +X pts | Capacity/Ops |
| Force Complete | X% | X% | +X pts | Training |
| Bad Interaction | X% | X% | +X pts | Sequencer |
| Trickling | X% | X% | +X pts | Sequencer |
| ALM Items | X% | X% | +X pts | Menu |

### Top 3 Offenders by Reason Code

#### 🔴 Long Production (Ops)
| ALL ORDERS | % | LATE ORDERS | % |
|------------|---|-------------|---|
| [HDR 1] | X% (+X) | [HDR 1] | X% (+X) |
| [HDR 2] | X% (+X) | [HDR 2] | X% (+X) |
| [HDR 3] | X% (+X) | [HDR 3] | X% (+X) |

[Repeat for Long Queue, Force Complete, Bad Interaction, Trickling]

---

## Queue Time Analysis: Capacity vs Sequencer

### ⚠️ Important: Sequencer Selection Bias
The sequencer is applied to MORE COMPLEX orders by design. Orders with holdback have more items, longer cook times, and ALM components. Comparing them to non-holdback orders is not apples-to-apples.

### Queue Scenarios — All Orders
| Scenario | Orders | % | Avg Queue | OTR | Interpretation |
|----------|--------|---|-----------|-----|----------------|
| No Hold + Normal Queue | | | | | Simple orders |
| Sequencer Held + Normal Queue | | | | | Working correctly |
| Sequencer Held + Long Queue | | | | | Investigate |
| No Hold + Long Queue | | | | | **Pure capacity** |

### Queue Scenarios — LATE Orders Only
| Scenario | Late Orders | % | Avg Queue | Root Cause |
|----------|-------------|---|-----------|------------|
| Seq Hold + Long Queue | | | | Complex (expected) |
| No Hold + Normal Queue | | | | Other issues |
| Seq Hold + Normal Queue | | | | Not queue-related |
| **No Hold + Long Queue** | | | | **Capacity — actionable** |

---

## Capacity & Staffing Analysis

### Orders Per Hour by Daypart
| Daypart | Avg Orders/Hour | Avg Queue | % Long Queue | Interpretation |
|---------|-----------------|-----------|--------------|----------------|
| Lunch (11am-1pm) | | | | |
| Dinner (5pm-8pm) | | | | Peak stress |
| Off-Peak | | | | Baseline |

### Volume Tier Analysis
| Volume Tier | HDR Count | Avg Orders/Day | Avg Queue | % Long Queue |
|-------------|-----------|----------------|-----------|--------------|
| High (300+/day) | | | | Capacity constrained |
| Medium (200-300/day) | | | | Watch list |
| Low (100-200/day) | | | | Normal |
| Very Low (<100/day) | | | | Baseline |

### Top 10 Worst Queue HDRs (Capacity Assessment)
| HDR | Class | Orders/Day | Avg Queue | % Long Queue | Avg Cook | Diagnosis |
|-----|-------|------------|-----------|--------------|----------|-----------|
| | | | | | | Capacity vs Ops |

**Capacity vs Ops Indicators:**
- **High volume + Long queue** = Capacity issue → Staff up
- **Low volume + Long queue** = Ops issue → Training
- **High volume + Normal queue** = Well-staffed
- **Peak hours only elevated** = Peak staffing issue

---

## Sequencer Analysis: Bad Interactions

### What Causes Bad Interactions?
| Root Cause | Description | Impact | Fix |
|------------|-------------|--------|-----|
| **ALM Held Too Long** | Sequencer held ALM item waiting for other items | Food quality degrades | Algorithm tuning |
| **Hot Hold Mismatch** | System expected hot hold item but it wasn't there | Reroute to cook from scratch | Inventory sync |
| **Release Timing** | Items released too early or late vs optimal | Trickling or sitting | Release logic |
| **Multi-Restaurant Coordination** | MRO items not synced properly | One restaurant waits | MRO handling |

### Bad Interaction Rate by Segment
| Segment | All Orders | Late Orders | Enrichment | Primary Cause |
|---------|------------|-------------|------------|---------------|
| Network | X% | X% | +X pts | |
| Urban | | | | |
| Suburban | | | | |
| NSO | | | | |
| Mature | | | | |

### Top 5 HDRs with Bad Interaction Issues
| HDR | Class | Bad Int % | ALM % | Hot Hold Issue % | Action |
|-----|-------|-----------|-------|------------------|--------|
| | | | | | |

### Bad Interaction + Late Order Correlation
| Has Bad Interaction | Orders | OTR | Avg Ticket | Interpretation |
|---------------------|--------|-----|------------|----------------|
| Yes | | | | |
| No | | | | |

> **Note:** Bad interactions are more common in complex orders. Compare within complexity tier for accurate assessment.

### Sequencer Validation: Expo Wait vs Step Time Variance

*See detailed explanation and validation query in "Sequencer Validation: Expo Wait vs Step Time Variance" section above.*

**Quick Reference:** Sequencer is working correctly if `Expo Wait Time ≤ Step Time Variance (cook_time_range)`

| Scenario | Orders | % | Avg Expo Wait | Avg Variance | OTR | Status |
|----------|--------|---|---------------|--------------|-----|--------|
| Expo Wait ≤ Variance | | | | | | ✅ Working |
| Expo Wait > Variance | | | | | | ⚠️ Investigate |

---

## ETA Analysis: Over/Under Prediction

### O2E Prediction Accuracy
| Metric | Value | Interpretation |
|--------|-------|----------------|
| Avg Estimated O2E | X.X min | |
| Avg Actual O2E | X.X min | |
| **Avg Error** | **X.X min** | Negative = faster than promised |
| Abs Error | X.X min | Magnitude of error |

### Over-Prediction vs Under-Prediction
| Category | Criteria | Orders | % | Impact |
|----------|----------|--------|---|--------|
| **Significantly Over** | Actual < Est - 15 min | | | Food sits, quality issue |
| **Over** | Actual < Est - 5 min | | | Early arrival |
| **Accurate** | Within ±5 min | | | Ideal |
| **Under** | Actual > Est + 5 min | | | Late, customer unhappy |
| **Significantly Under** | Actual > Est + 15 min | | | SLA miss |

### ETA Error by Segment
| Segment | Avg Est O2E | Avg Actual O2E | Error | Interpretation |
|---------|-------------|----------------|-------|----------------|
| Delivery | | | | |
| Pickup | | | | |
| Urban | | | | |
| Suburban | | | | |
| NSO | | | | |
| Mature | | | | |

### ETA Component Errors
| Component | Avg Est | Avg Actual | Error | Issue |
|-----------|---------|------------|-------|-------|
| Queue | | | | |
| Cook | | | | |
| Pack/Bag | | | | |
| Sit Time | | | | |
| Transit | | | | |

### Top Underestimate HDRs (ETA too optimistic)
| HDR | Class | Est O2E | Actual O2E | Error | Primary Component |
|-----|-------|---------|------------|-------|-------------------|
| | | | | | Queue/Cook/Transit |

> **ETA Underestimate Impact:** When we promise faster than we deliver, customers see "late" even if kitchen executes normally. Fix via ETA model tuning, not ops.

---

## Delivery Mix Impact

### Does Delivery % Explain Poor Performance?
| Correlation | Value | Interpretation |
|-------------|-------|----------------|
| Delivery % vs OTR | r = X.XX | [Interpretation] |

### Bottom 5 HDRs — Mix-Adjusted Analysis
| HDR | Delivery % | Actual OTR | Expected OTR | Gap | Diagnosis |
|-----|------------|------------|--------------|-----|-----------|
| | | | | | |

---

## Bottom 5 HDRs Deep Dive

### Summary
| HDR | Class | Orders | OTR | Del OTR | PU OTR | Ticket | Primary Issue |
|-----|-------|--------|-----|---------|--------|--------|---------------|
| | | | | | | | |

### Reason Codes (Late Orders)
| HDR | Long Prod | Bad Interact | Force Comp | Long Queue | Trickling |
|-----|-----------|--------------|------------|------------|-----------|
| **Network** | X% | X% | X% | X% | X% |
| [HDR 1] | X% (+X) | | | | |

### Recommended Actions
| HDR | Lever 1 | Lever 2 | Lever 3 |
|-----|---------|---------|---------|
| | | | |

---

## Achievability Analysis

### Late Order Severity
| Tier | Delivery | % | Pickup | % |
|------|----------|---|--------|---|
| 1-4 min late | | | | |
| 5-15 min late | | | | |
| 16-30 min late | | | | |
| 31+ min late | | | | |

### OTR Uplift Potential
| Fix | Orders Saved | New OTR | Uplift |
|-----|--------------|---------|--------|
| 1-4 min late (easy wins) | | | |
| 1-15 min late (achievable) | | | |
| All late (perfect) | | | |

---

## Key Takeaways

| # | Insight |
|---|---------|
| 1 | |
| 2 | |
| 3 | |

---

## Recommended Actions

| Priority | Area | Owner | Action | Impact |
|----------|------|-------|--------|--------|
| 🔴 #1 | | | | |
| 🟠 #2 | | | | |
| 🟡 #3 | | | | |

---

*Data validated against Looker WBR reports. Last updated: [DATE]*
```

---

## When to Use This Skill

Use this skill when you need to:
- **🚀 "Generate WBR summary"** - Auto-generates the full weekly leadership report
- **🚀 "Weekly OTR report"** - Same as above
- **🚀 "OTR for Product/Culinary/Ops"** - Domain-specific views
- **🚀 "NSO stabilization status"** - Track new store maturation
- Calculate On-Time Rate for a period, HDR, or channel
- Diagnose WHY orders are late (kitchen vs logistics vs both)
- Analyze SLA tier distribution (how early/late are orders?)
- Identify "Kitchen Fast, Food Waits" vs "Kitchen Late, Courier Waits" patterns
- Track expo wait time performance at HDR level
- Compare NSO vs mature store timing performance
- Investigate specific HDRs or time periods with poor OTR
- Break down OTR by population type (Urban/Suburban/Big Box)
- Analyze performance by maturity phase (Launch/Ramp/Maturing/Mature)
- Compare HDR classes and track weeks open impact
- **Analyze queue time drivers (sequencer holdback vs capacity)**
- **Assess reason code attribution for late orders**
- **Evaluate courier platform impact on OTR**
- **🔧 Force Complete & Pod Diagnosis:**
  - Identify if FCs are rescue (reactive) vs process (systematic)
  - Diagnose capacity vs idle time issues using IPC and step lag
  - Find which pod (Cold, Hot, Pizza) is the bottleneck
  - Determine if "reduce FCs" is the right intervention
- **📅 Weekend Stress Analysis:**
  - Identify if Friday/Saturday are driving disproportionate late orders
  - Assess weekend staffing vs weekday capacity
  - Determine if weekend ops delay is 2x weekday (typical pattern)
- **🏪 NSO Concentration Analysis:**
  - Identify if NSO Suburban 2025 New stores are driving late orders
  - Assess if new stores are stabilizing on expected timeline
  - Determine if 8-11 week old stores are the sweet spot for worst performance

## Related Skills

- **wonder-orders** - Base order data, sales metrics, channel performance
- **wonder-sequencing** - Kitchen sequencing algorithm, order batching, priority scoring

---

## 🚀 Quick Action: Generate WBR Summary

**Trigger phrases:** "generate WBR summary", "weekly OTR report", "prepare OTR summary for leadership"

When asked to generate a WBR summary, run these 4 queries using `bq query --use_legacy_sql=false --project_id=wonder-dw-prod-brd` and format the output:

### Step 1: Run Executive Summary Query
```bash
bq query --use_legacy_sql=false --project_id=wonder-dw-prod-brd --format=pretty 'WITH current_week AS (SELECT FORMAT_DATE("%F", DATE_TRUNC(o.service_date_et, WEEK(MONDAY))) AS service_week, o.dining_option, COUNT(DISTINCT o.order_id) AS order_count, COUNT(DISTINCT CASE WHEN ot.on_time_issue THEN ot.order_id END) AS orders_with_issues, COUNT(DISTINCT CASE WHEN ot.on_time_issue AND ot.otr_sla_tier NOT LIKE "%EARLY" THEN ot.order_id END) AS late_orders_only FROM `wonder-dw-prod-brd.orders.hdr_orders` o LEFT JOIN `wonder-dw-prod-brd.orders.hdr_on_time_orders` ot ON o.order_id = ot.order_id WHERE o.order_status = "COMPLETE" AND o.brand_category = "WONDER_HDR" AND (o.order_business_type <> "WONDER_SPOT" OR o.order_business_type IS NULL) AND (o.order_business_type <> "3P_PLATFORM_CORPORATE" OR o.order_business_type IS NULL) AND o.order_channel IN ("APP", "WEB", "IN_PERSON") AND o.service_date_et >= DATE_SUB(CURRENT_DATE("America/New_York"), INTERVAL 3 WEEK) AND o.service_date_et < DATE_TRUNC(CURRENT_DATE("America/New_York"), WEEK(MONDAY)) GROUP BY 1, 2), weekly_summary AS (SELECT service_week, SUM(order_count) AS total_orders, SUM(CASE WHEN dining_option = "PICKUP" THEN order_count ELSE 0 END) AS pickup_orders, SUM(CASE WHEN dining_option = "DELIVERY" THEN order_count ELSE 0 END) AS delivery_orders, 1 - SAFE_DIVIDE(SUM(orders_with_issues), SUM(order_count)) AS network_otr, 1 - SAFE_DIVIDE(SUM(late_orders_only), SUM(order_count)) AS network_otr_no_earlies, 1 - SAFE_DIVIDE(SUM(CASE WHEN dining_option = "PICKUP" THEN orders_with_issues END), SUM(CASE WHEN dining_option = "PICKUP" THEN order_count END)) AS pickup_otr, 1 - SAFE_DIVIDE(SUM(CASE WHEN dining_option = "DELIVERY" THEN orders_with_issues END), SUM(CASE WHEN dining_option = "DELIVERY" THEN order_count END)) AS delivery_otr FROM current_week GROUP BY service_week) SELECT curr.service_week, curr.total_orders, curr.pickup_orders, curr.delivery_orders, ROUND(curr.network_otr * 100, 1) AS network_otr_pct, ROUND(curr.network_otr_no_earlies * 100, 1) AS otr_no_earlies_pct, ROUND(curr.pickup_otr * 100, 1) AS pickup_otr_pct, ROUND(curr.delivery_otr * 100, 1) AS delivery_otr_pct, ROUND((curr.network_otr - prev.network_otr) * 100, 1) AS wow_delta, ROUND((curr.pickup_otr - curr.delivery_otr) * 100, 1) AS channel_gap FROM weekly_summary curr LEFT JOIN weekly_summary prev ON DATE(curr.service_week) = DATE_ADD(DATE(prev.service_week), INTERVAL 1 WEEK) ORDER BY curr.service_week DESC LIMIT 2'
```

### Step 2: Run Kitchen Handoff Scenarios Query
```bash
bq query --use_legacy_sql=false --project_id=wonder-dw-prod-brd --format=pretty 'WITH delivery_orders AS (SELECT o.order_id, o.ready_for_pickup_sla_difference, o.courier_response_time_mins, o.kitchen_handoff_time_mins, o.cook_error, o.pickup_error, ot.on_time_issue, CASE WHEN o.ready_for_pickup_sla_difference > 2.0 AND COALESCE(o.courier_response_time_mins, 0) <= 5.0 THEN "A. Kitchen LATE, Courier Waits" WHEN o.ready_for_pickup_sla_difference <= 2.0 AND COALESCE(o.courier_response_time_mins, 0) > 5.0 THEN "B. Kitchen FAST, Food Waits" WHEN o.ready_for_pickup_sla_difference > 2.0 AND COALESCE(o.courier_response_time_mins, 0) > 5.0 THEN "C. Compounding Failure" ELSE "D. Ideal State" END AS scenario FROM `wonder-dw-prod-brd.orders.hdr_orders` o LEFT JOIN `wonder-dw-prod-brd.orders.hdr_on_time_orders` ot ON o.order_id = ot.order_id WHERE o.order_status = "COMPLETE" AND o.brand_category = "WONDER_HDR" AND (o.order_business_type <> "WONDER_SPOT" OR o.order_business_type IS NULL) AND (o.order_business_type <> "3P_PLATFORM_CORPORATE" OR o.order_business_type IS NULL) AND o.dining_option = "DELIVERY" AND o.order_channel IN ("APP", "WEB", "IN_PERSON") AND o.service_date_et >= DATE_TRUNC(DATE_SUB(CURRENT_DATE("America/New_York"), INTERVAL 1 WEEK), WEEK(MONDAY)) AND o.service_date_et < DATE_TRUNC(CURRENT_DATE("America/New_York"), WEEK(MONDAY))) SELECT scenario, COUNT(DISTINCT order_id) AS volume, ROUND(COUNT(DISTINCT order_id) * 100.0 / SUM(COUNT(DISTINCT order_id)) OVER(), 1) AS pct, ROUND((1 - SAFE_DIVIDE(COUNT(DISTINCT CASE WHEN on_time_issue THEN order_id END), COUNT(DISTINCT order_id))) * 100, 1) AS otr_pct, ROUND(AVG(pickup_error), 1) AS sit_error, ROUND(AVG(cook_error), 1) AS cook_error, ROUND(AVG(courier_response_time_mins), 1) AS courier_resp, ROUND(AVG(kitchen_handoff_time_mins), 1) AS handoff FROM delivery_orders GROUP BY scenario ORDER BY volume DESC'
```

### Step 3: Run Profile A (Ops Failures) Query
```bash
bq query --use_legacy_sql=false --project_id=wonder-dw-prod-brd --format=pretty 'SELECT "Profile A: Ops Failure" AS profile, h.hdr_name, COUNT(DISTINCT o.order_id) AS late_orders, ROUND(AVG(o.courier_response_time_mins), 1) AS courier_resp, ROUND(AVG(o.kitchen_handoff_time_mins), 1) AS handoff, ROUND(AVG(o.kitchen_handoff_time_mins) - AVG(o.courier_response_time_mins), 1) AS ops_gap FROM `wonder-dw-prod-brd.orders.hdr_orders` o JOIN `wonder-dw-prod-brd.dw.dim_hdrs` h ON o.hdr_id = h.hdr_id JOIN `wonder-dw-prod-brd.orders.hdr_on_time_orders` ot ON o.order_id = ot.order_id WHERE o.order_status = "COMPLETE" AND o.brand_category = "WONDER_HDR" AND (o.order_business_type <> "WONDER_SPOT" OR o.order_business_type IS NULL) AND (o.order_business_type <> "3P_PLATFORM_CORPORATE" OR o.order_business_type IS NULL) AND o.dining_option = "DELIVERY" AND o.order_channel IN ("APP", "WEB", "IN_PERSON") AND ot.on_time_issue = TRUE AND ot.otr_sla_tier LIKE "%LATE" AND o.service_date_et >= DATE_TRUNC(DATE_SUB(CURRENT_DATE("America/New_York"), INTERVAL 1 WEEK), WEEK(MONDAY)) AND o.service_date_et < DATE_TRUNC(CURRENT_DATE("America/New_York"), WEEK(MONDAY)) GROUP BY 2 HAVING AVG(o.courier_response_time_mins) <= 5.0 AND AVG(o.kitchen_handoff_time_mins) > 8.0 AND COUNT(DISTINCT o.order_id) >= 5 ORDER BY handoff DESC LIMIT 10'
```

### Step 4: Run Profile B (Logistics Failures) Query
```bash
bq query --use_legacy_sql=false --project_id=wonder-dw-prod-brd --format=pretty 'SELECT "Profile B: Logistics" AS profile, h.hdr_name, COUNT(DISTINCT o.order_id) AS late_orders, ROUND(AVG(o.courier_response_time_mins), 1) AS courier_resp, ROUND(AVG(o.kitchen_handoff_time_mins), 1) AS handoff, ROUND(AVG(o.courier_response_time_mins) - AVG(o.kitchen_handoff_time_mins), 1) AS logistics_gap FROM `wonder-dw-prod-brd.orders.hdr_orders` o JOIN `wonder-dw-prod-brd.dw.dim_hdrs` h ON o.hdr_id = h.hdr_id JOIN `wonder-dw-prod-brd.orders.hdr_on_time_orders` ot ON o.order_id = ot.order_id WHERE o.order_status = "COMPLETE" AND o.brand_category = "WONDER_HDR" AND (o.order_business_type <> "WONDER_SPOT" OR o.order_business_type IS NULL) AND (o.order_business_type <> "3P_PLATFORM_CORPORATE" OR o.order_business_type IS NULL) AND o.dining_option = "DELIVERY" AND o.order_channel IN ("APP", "WEB", "IN_PERSON") AND ot.on_time_issue = TRUE AND ot.otr_sla_tier LIKE "%LATE" AND o.service_date_et >= DATE_TRUNC(DATE_SUB(CURRENT_DATE("America/New_York"), INTERVAL 1 WEEK), WEEK(MONDAY)) AND o.service_date_et < DATE_TRUNC(CURRENT_DATE("America/New_York"), WEEK(MONDAY)) GROUP BY 2 HAVING AVG(o.kitchen_handoff_time_mins) <= 5.0 AND AVG(o.courier_response_time_mins) > 10.0 AND COUNT(DISTINCT o.order_id) >= 5 ORDER BY courier_resp DESC LIMIT 10'
```

### Step 5: Run Chronic Underperformers Query
```bash
bq query --use_legacy_sql=false --project_id=wonder-dw-prod-brd --format=pretty 'WITH weekly_metrics AS (SELECT FORMAT_DATE("%F", DATE_TRUNC(o.service_date_et, WEEK(MONDAY))) AS service_week, h.hdr_name, h.hdr_class, COUNT(DISTINCT o.order_id) AS delivery_orders, ROUND(AVG(o.actual_o2e_mins), 2) AS avg_o2e_mins FROM `wonder-dw-prod-brd.orders.hdr_orders` o JOIN `wonder-dw-prod-brd.dw.dim_hdrs` h ON o.hdr_id = h.hdr_id WHERE o.order_status = "COMPLETE" AND o.brand_category = "WONDER_HDR" AND (o.order_business_type <> "WONDER_SPOT" OR o.order_business_type IS NULL) AND (o.order_business_type <> "3P_PLATFORM_CORPORATE" OR o.order_business_type IS NULL) AND o.dining_option = "DELIVERY" AND o.order_channel IN ("APP", "WEB", "IN_PERSON") AND o.service_date_et >= DATE_ADD(DATE_TRUNC(CURRENT_DATE("America/New_York"), WEEK(MONDAY)), INTERVAL -24 WEEK) AND o.service_date_et < DATE_TRUNC(CURRENT_DATE("America/New_York"), WEEK(MONDAY)) GROUP BY 1, 2, 3 HAVING COUNT(DISTINCT o.order_id) >= 30), weekly_stats AS (SELECT service_week, AVG(avg_o2e_mins) AS network_avg, STDDEV_POP(avg_o2e_mins) AS network_stddev FROM weekly_metrics GROUP BY service_week), weekly_ranked AS (SELECT wm.*, RANK() OVER (PARTITION BY wm.service_week ORDER BY wm.avg_o2e_mins DESC) AS o2e_rank, CASE WHEN wm.avg_o2e_mins > ws.network_avg + 2 * ws.network_stddev THEN TRUE ELSE FALSE END AS is_outlier FROM weekly_metrics wm JOIN weekly_stats ws ON wm.service_week = ws.service_week) SELECT hdr_name, hdr_class, COUNT(CASE WHEN o2e_rank <= 10 THEN 1 END) AS weeks_worst_10, COUNT(CASE WHEN is_outlier THEN 1 END) AS weeks_outlier, ROUND(AVG(avg_o2e_mins), 1) AS avg_o2e, CASE WHEN COUNT(CASE WHEN o2e_rank <= 10 THEN 1 END) >= 10 THEN "🔴 CRITICAL" WHEN COUNT(CASE WHEN o2e_rank <= 10 THEN 1 END) >= 5 THEN "🟠 HIGH" WHEN COUNT(CASE WHEN is_outlier THEN 1 END) >= 3 THEN "🟡 OUTLIER" ELSE "⚪ MONITOR" END AS priority FROM weekly_ranked GROUP BY 1, 2 HAVING COUNT(CASE WHEN o2e_rank <= 10 THEN 1 END) >= 5 OR COUNT(CASE WHEN is_outlier THEN 1 END) >= 3 ORDER BY weeks_worst_10 DESC LIMIT 15'
```

### Step 6: Run Validated Fault Attribution Query (With Upstream Check)
```bash
bq query --use_legacy_sql=false --project_id=wonder-dw-prod-brd --format=pretty 'WITH hdr_baselines AS (SELECT hdr_id, APPROX_QUANTILES(kitchen_handoff_time_mins, 100)[OFFSET(75)] AS p75_handoff, APPROX_QUANTILES(courier_response_time_mins, 100)[OFFSET(75)] AS p75_courier FROM `wonder-dw-prod-brd.orders.hdr_orders` WHERE service_date_et >= DATE_SUB(CURRENT_DATE("America/New_York"), INTERVAL 30 DAY) AND order_status = "COMPLETE" AND dining_option = "DELIVERY" GROUP BY 1), late_orders AS (SELECT o.order_id, o.hdr_id, h.hdr_name, h.hdr_class, h.population_type, o.ready_for_pickup_sla_difference, o.courier_response_time_mins, o.kitchen_handoff_time_mins, o.delivery_sla_difference, b.p75_handoff, b.p75_courier, CASE WHEN o.ready_for_pickup_sla_difference > 5.0 THEN "KITCHEN_PRIMARY" WHEN o.ready_for_pickup_sla_difference > 2.0 THEN "KITCHEN_CONTRIBUTING" ELSE "KITCHEN_ON_TIME" END AS upstream_status, CASE WHEN o.ready_for_pickup_sla_difference > 5.0 THEN true WHEN o.ready_for_pickup_sla_difference <= 2.0 AND o.kitchen_handoff_time_mins > COALESCE(b.p75_handoff, 3.0) THEN true ELSE false END AS is_hdr_fault_validated, CASE WHEN o.ready_for_pickup_sla_difference <= 2.0 AND o.courier_response_time_mins > COALESCE(b.p75_courier, 5.0) THEN true ELSE false END AS is_delivery_fault_validated FROM `wonder-dw-prod-brd.orders.hdr_orders` o JOIN `wonder-dw-prod-brd.dw.dim_hdrs` h ON o.hdr_id = h.hdr_id JOIN `wonder-dw-prod-brd.orders.hdr_on_time_orders` ot ON o.order_id = ot.order_id LEFT JOIN hdr_baselines b ON o.hdr_id = b.hdr_id WHERE o.order_status = "COMPLETE" AND o.brand_category = "WONDER_HDR" AND (o.order_business_type <> "WONDER_SPOT" OR o.order_business_type IS NULL) AND (o.order_business_type <> "3P_PLATFORM_CORPORATE" OR o.order_business_type IS NULL) AND o.dining_option = "DELIVERY" AND o.order_channel IN ("APP", "WEB", "IN_PERSON") AND ot.on_time_issue = TRUE AND ot.otr_sla_tier LIKE "%LATE" AND o.service_date_et >= DATE_TRUNC(DATE_SUB(CURRENT_DATE("America/New_York"), INTERVAL 1 WEEK), WEEK(MONDAY)) AND o.service_date_et < DATE_TRUNC(CURRENT_DATE("America/New_York"), WEEK(MONDAY))) SELECT upstream_status, COUNT(*) AS late_orders, ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 1) AS pct, ROUND(AVG(ready_for_pickup_sla_difference), 1) AS avg_kitchen_delay, ROUND(AVG(courier_response_time_mins), 1) AS avg_courier_resp, ROUND(AVG(kitchen_handoff_time_mins), 1) AS avg_handoff, COUNT(CASE WHEN is_hdr_fault_validated THEN 1 END) AS hdr_fault_count, COUNT(CASE WHEN is_delivery_fault_validated THEN 1 END) AS delivery_fault_count FROM late_orders GROUP BY 1 ORDER BY late_orders DESC'
```

### Step 7: Run Location Validated Fault Attribution
```bash
bq query --use_legacy_sql=false --project_id=wonder-dw-prod-brd --format=pretty 'WITH hdr_baselines AS (SELECT hdr_id, APPROX_QUANTILES(kitchen_handoff_time_mins, 100)[OFFSET(75)] AS p75_handoff, APPROX_QUANTILES(courier_response_time_mins, 100)[OFFSET(75)] AS p75_courier FROM `wonder-dw-prod-brd.orders.hdr_orders` WHERE service_date_et >= DATE_SUB(CURRENT_DATE("America/New_York"), INTERVAL 30 DAY) AND order_status = "COMPLETE" AND dining_option = "DELIVERY" GROUP BY 1), late_orders AS (SELECT o.hdr_id, h.hdr_name, h.hdr_class, h.population_type, o.ready_for_pickup_sla_difference, o.courier_response_time_mins, o.kitchen_handoff_time_mins, b.p75_handoff, b.p75_courier, CASE WHEN o.ready_for_pickup_sla_difference > 5.0 THEN "KITCHEN_PRIMARY" WHEN o.ready_for_pickup_sla_difference > 2.0 THEN "KITCHEN_CONTRIBUTING" ELSE "KITCHEN_ON_TIME" END AS upstream_status FROM `wonder-dw-prod-brd.orders.hdr_orders` o JOIN `wonder-dw-prod-brd.dw.dim_hdrs` h ON o.hdr_id = h.hdr_id JOIN `wonder-dw-prod-brd.orders.hdr_on_time_orders` ot ON o.order_id = ot.order_id LEFT JOIN hdr_baselines b ON o.hdr_id = b.hdr_id WHERE o.order_status = "COMPLETE" AND o.brand_category = "WONDER_HDR" AND (o.order_business_type <> "WONDER_SPOT" OR o.order_business_type IS NULL) AND (o.order_business_type <> "3P_PLATFORM_CORPORATE" OR o.order_business_type IS NULL) AND o.dining_option = "DELIVERY" AND o.order_channel IN ("APP", "WEB", "IN_PERSON") AND ot.on_time_issue = TRUE AND ot.otr_sla_tier LIKE "%LATE" AND o.service_date_et >= DATE_TRUNC(DATE_SUB(CURRENT_DATE("America/New_York"), INTERVAL 1 WEEK), WEEK(MONDAY)) AND o.service_date_et < DATE_TRUNC(CURRENT_DATE("America/New_York"), WEEK(MONDAY))) SELECT hdr_name, hdr_class, population_type, COUNT(*) AS late_orders, ROUND(AVG(CASE WHEN upstream_status = "KITCHEN_PRIMARY" THEN 1 ELSE 0 END) * 100, 0) AS pct_kitchen_primary, ROUND(AVG(CASE WHEN upstream_status = "KITCHEN_ON_TIME" THEN 1 ELSE 0 END) * 100, 0) AS pct_kitchen_on_time, ROUND(AVG(ready_for_pickup_sla_difference), 1) AS avg_kitchen_delay, ROUND(AVG(courier_response_time_mins), 1) AS avg_courier_resp, ROUND(AVG(kitchen_handoff_time_mins), 1) AS avg_handoff, ROUND(AVG(CASE WHEN upstream_status = "KITCHEN_ON_TIME" AND courier_response_time_mins > p75_courier THEN 1 ELSE 0 END) * 100, 0) AS pct_validated_logistics_fault, ROUND(AVG(CASE WHEN upstream_status = "KITCHEN_ON_TIME" AND kitchen_handoff_time_mins > p75_handoff THEN 1 ELSE 0 END) * 100, 0) AS pct_validated_handoff_fault FROM late_orders GROUP BY 1, 2, 3 HAVING COUNT(*) >= 20 ORDER BY late_orders DESC LIMIT 20'
```

### Step 8: Run Imperfect Orders Summary
```bash
bq query --use_legacy_sql=false --project_id=wonder-dw-prod-brd --format=pretty 'SELECT FORMAT_DATE("%F", DATE_TRUNC(i.service_date_et, WEEK(MONDAY))) AS service_week, i.dining_option, COUNT(DISTINCT i.order_id) AS total_orders, COUNT(DISTINCT CASE WHEN i.imperfect_order THEN i.order_id END) AS imperfect_orders, ROUND(COUNT(DISTINCT CASE WHEN i.imperfect_order THEN i.order_id END) * 100.0 / COUNT(DISTINCT i.order_id), 1) AS imperfect_rate, COUNT(DISTINCT CASE WHEN i.on_time_issue THEN i.order_id END) AS on_time_issues, COUNT(DISTINCT CASE WHEN i.order_accuracy_issue THEN i.order_id END) AS accuracy_issues, COUNT(DISTINCT CASE WHEN i.remake_issue THEN i.order_id END) AS remake_issues FROM `wonder-dw-prod-brd.orders.imperfect_orders` i WHERE i.service_date_et >= DATE_SUB(DATE_TRUNC(CURRENT_DATE("America/New_York"), WEEK(MONDAY)), INTERVAL 2 WEEK) AND i.service_date_et < DATE_TRUNC(CURRENT_DATE("America/New_York"), WEEK(MONDAY)) GROUP BY 1, 2 ORDER BY 1 DESC, 2'
```

### Step 9: Run Error Severity Breakdown
```bash
bq query --use_legacy_sql=false --project_id=wonder-dw-prod-brd --format=pretty 'WITH late_orders AS (SELECT o.order_id, o.ready_for_pickup_sla_difference, o.courier_response_time_mins, o.kitchen_handoff_time_mins, CASE WHEN o.kitchen_handoff_time_mins > 15 THEN "SEVERE" WHEN o.kitchen_handoff_time_mins > 8 THEN "MODERATE" WHEN o.kitchen_handoff_time_mins > 3 THEN "MINOR" ELSE "OK" END AS handoff_severity, CASE WHEN o.courier_response_time_mins > 15 THEN "SEVERE" WHEN o.courier_response_time_mins > 10 THEN "MODERATE" WHEN o.courier_response_time_mins > 5 THEN "MINOR" ELSE "OK" END AS courier_severity, CASE WHEN o.ready_for_pickup_sla_difference > 10 THEN "SEVERE" WHEN o.ready_for_pickup_sla_difference > 5 THEN "MODERATE" WHEN o.ready_for_pickup_sla_difference > 2 THEN "MINOR" ELSE "OK" END AS kitchen_severity FROM `wonder-dw-prod-brd.orders.hdr_orders` o JOIN `wonder-dw-prod-brd.orders.hdr_on_time_orders` ot ON o.order_id = ot.order_id WHERE o.order_status = "COMPLETE" AND o.brand_category = "WONDER_HDR" AND (o.order_business_type <> "WONDER_SPOT" OR o.order_business_type IS NULL) AND (o.order_business_type <> "3P_PLATFORM_CORPORATE" OR o.order_business_type IS NULL) AND o.dining_option = "DELIVERY" AND o.order_channel IN ("APP", "WEB", "IN_PERSON") AND ot.on_time_issue = TRUE AND ot.otr_sla_tier LIKE "%LATE" AND o.service_date_et >= DATE_TRUNC(DATE_SUB(CURRENT_DATE("America/New_York"), INTERVAL 1 WEEK), WEEK(MONDAY)) AND o.service_date_et < DATE_TRUNC(CURRENT_DATE("America/New_York"), WEEK(MONDAY))) SELECT "KITCHEN" AS component, kitchen_severity AS severity, COUNT(*) AS late_orders, ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 1) AS pct FROM late_orders GROUP BY 1, 2 UNION ALL SELECT "COURIER", courier_severity, COUNT(*), ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 1) FROM late_orders GROUP BY 1, 2 UNION ALL SELECT "HANDOFF", handoff_severity, COUNT(*), ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 1) FROM late_orders GROUP BY 1, 2 ORDER BY 1, CASE severity WHEN "SEVERE" THEN 1 WHEN "MODERATE" THEN 2 WHEN "MINOR" THEN 3 ELSE 4 END'
```

### Step 10: Format Output as Leadership Report

After running all queries, format the results into this template:

```markdown
# 📊 Weekly OTR Report - Week of [DATE]

## 1. Executive Summary: Network Health

| Metric | This Week | Last Week | Δ |
|--------|-----------|-----------|---|
| **Network OTR** | **X%** | X% | +/- X pts |
| OTR (No Earlies) | X% | X% | +/- X pts |
| **Total 1P Orders** | **X** | X | +X% |
| Pickup OTR | X% | X% | |
| Delivery OTR | X% | X% | |
| **Channel Gap** | **X pts** | | |

---

## 2. Kitchen Handoff Scenario Breakdown

| Scenario | Volume | % | OTR | Sit Error | Courier | Handoff |
|----------|--------|---|-----|-----------|---------|---------|
| D. Ideal State | X | X% | X% | X | X min | X min |
| A. Kitchen LATE | X | X% | X% | X | X min | X min |
| B. Food Waits | X | X% | X% | X | X min | X min |
| C. Compounding | X | X% | X% | X | X min | X min |

---

## 3. Location Spotlights

### Profile A: Ops Failures 🔧 (Audit Expo)
| HDR | Late Orders | Courier | Handoff | Ops Gap |
|-----|-------------|---------|---------|---------|
| X | X | X min | X min | +X |

### Profile B: Logistics Failures 🚗 (Courier Incentives)
| HDR | Late Orders | Courier | Handoff | Gap |
|-----|-------------|---------|---------|-----|
| X | X | X min | X min | +X |

---

## 4. Deep Dive Candidates (5+ Weeks on Worst List)

| HDR | Class | Weeks Worst | Avg O2E | Priority |
|-----|-------|-------------|---------|----------|
| X | X | X | X min | 🔴/🟠 |

---

## 5. Follow-Ups

| # | Action | Owner | Focus |
|---|--------|-------|-------|
| 1 | Audit Expo at [Profile A HDRs] | Regional Ops | Fake bumping |
| 2 | Courier incentives for [Profile B HDRs] | Logistics | Driver supply |
| 3 | Deep dive [Critical HDRs] | Ops + Logistics | Chronic failure |
```

**Important:** All queries must use `required_permissions: ["all"]` to bypass sandbox restrictions.

---

## Core Concepts

### Database Location

- **BigQuery Dataset**: `wonder-dw-prod-brd.orders`
- **Primary Tables**:
  - `hdr_orders` - Base order data with timing error fields
  - `hdr_on_time_orders` - Dedicated OTR metrics and SLA tiers
  - `imperfect_orders` - Order imperfection tracking
- **Supporting Tables**:
  - `wonder-dw-prod-brd.dw.dim_hdrs` - HDR dimensions (class, population type)
  - `wonder-dw-prod-brd.dw.dim_hdr_restaurants` - HDR to restaurant mapping
  - `wonder-dw-prod-brd.orders.order_restaurants` - Order to restaurant linkage

### On-Time Rate Definition

**On-Time Rate (OTR)** = Percentage of orders delivered/picked up within the promised SLA window.

```
OTR = 1 - (Orders with on_time_issue / Total Orders)
```

**Two OTR Variants:**
1. **OTR (Standard)** - Includes all timing issues (early + late)
2. **OTR (Excluding Earlies)** - Only counts late orders as failures

**Why both?** Extremely early orders (9+ minutes) can also indicate process issues but are generally less customer-impacting than late orders.

---

## 🆕 Dual OTR Framework: Customer vs Process OTR

**Critical Insight:** Separating what the customer experienced from how well the kitchen executed.

### The Problem with Single OTR

When courier arrives late, it can **mask** a kitchen that missed its target:
```
Timeline:
├── expected_ready_for_pickup: 5:00 PM
├── actual_ready_for_pickup: 5:08 PM   ← Kitchen 8 min LATE
├── courier_arrived: 5:10 PM           ← Courier ALSO late (arrived 10 min after expected)
├── pickup_complete: 5:12 PM
└── delivery: 5:25 PM                  ← Customer got order "on time"

Customer OTR: ✅ ON TIME (delivery was within window)
Kitchen Process OTR: ❌ LATE (missed expected_ready by 8 min)
```

### Three OTR Metrics

| Metric | Definition | Question Answered | Owner |
|--------|------------|-------------------|-------|
| **Customer OTR** | `delivery_sla_difference` within window | Did customer get food on time? | Final outcome |
| **Kitchen Process OTR** | `actual_ready <= expected_ready` | Did kitchen hit their target? | Ops |
| **Courier Arrival OTR** | `courier_arrived <= expected_ready` | Was courier there when food was expected? | Logistics |

### SQL Implementation (No Arbitrary Thresholds)

```sql
-- Kitchen Process OTR: Was food ready by expected time?
CASE 
  WHEN actual_ready_for_pickup_time_utc <= expected_ready_for_pickup_time_utc 
  THEN 'KITCHEN_ON_TIME'
  ELSE 'KITCHEN_LATE'
END AS kitchen_process_status

-- Courier Arrival: Was courier there when food was expected?
CASE 
  WHEN pickup_arrived_time_utc <= expected_ready_for_pickup_time_utc 
  THEN 'COURIER_ON_TIME'  -- Courier was waiting
  ELSE 'COURIER_LATE'     -- Courier arrived after expected
END AS courier_arrival_status

-- Did courier "save" a late kitchen?
CASE 
  WHEN actual_ready_for_pickup_time_utc > expected_ready_for_pickup_time_utc  -- Kitchen late
   AND pickup_arrived_time_utc > expected_ready_for_pickup_time_utc           -- Courier also late
   AND delivery_sla_difference BETWEEN -9 AND 1                                -- But delivery on time
  THEN TRUE
  ELSE FALSE
END AS courier_saved_kitchen
```

### Attribution Matrix

| Kitchen Status | Courier Status | Customer OTR | Customer Blame | Process Blame |
|----------------|----------------|--------------|----------------|---------------|
| ✅ On-time | ✅ On-time | ✅ On-time | Nobody | Nobody |
| ✅ On-time | ✅ On-time | ❌ Late | Transit | Transit |
| ✅ On-time | ❌ Late | ✅ On-time | Nobody | Courier (arrived late) |
| ✅ On-time | ❌ Late | ❌ Late | Courier | Courier |
| ❌ Late | ✅ On-time (waiting) | ✅ On-time | Nobody | **Kitchen** (masked) |
| ❌ Late | ✅ On-time (waiting) | ❌ Late | Kitchen | Kitchen |
| ❌ Late | ❌ Late | ✅ On-time | Nobody | **Both** (masked) |
| ❌ Late | ❌ Late | ❌ Late | Both | Both |

### The OTR Gap Analysis

**Key Metric:** `Customer OTR - Kitchen Process OTR = Hidden Kitchen Problems`

```sql
-- Query: Which HDRs have the biggest gap between customer OTR and kitchen process OTR?
WITH dual_otr AS (
  SELECT
    h.hdr_name,
    h.hdr_class,
    COUNT(DISTINCT o.order_id) AS total_orders,
    
    -- Customer-Facing OTR
    ROUND(AVG(CASE 
      WHEN o.delivery_sla_difference BETWEEN -9 AND 1 THEN 1 ELSE 0 
    END) * 100, 1) AS customer_otr,
    
    -- Kitchen Process OTR (did kitchen hit expected_ready?)
    ROUND(AVG(CASE 
      WHEN o.actual_ready_for_pickup_time_utc <= o.expected_ready_for_pickup_time_utc THEN 1 ELSE 0 
    END) * 100, 1) AS kitchen_process_otr,
    
    -- "Courier Saved Kitchen" rate
    ROUND(AVG(CASE 
      WHEN o.actual_ready_for_pickup_time_utc > o.expected_ready_for_pickup_time_utc  
       AND o.pickup_arrived_time_utc > o.expected_ready_for_pickup_time_utc           
       AND o.delivery_sla_difference BETWEEN -9 AND 1                               
      THEN 1 ELSE 0 
    END) * 100, 1) AS courier_saved_kitchen_pct
    
  FROM hdr_orders o
  JOIN dim_hdrs h ON o.hdr_id = h.hdr_id
  WHERE o.dining_option = 'DELIVERY'
    AND o.actual_ready_for_pickup_time_utc IS NOT NULL
    AND o.pickup_arrived_time_utc IS NOT NULL
  GROUP BY 1, 2
)
SELECT 
  hdr_name,
  customer_otr,
  kitchen_process_otr,
  ROUND(customer_otr - kitchen_process_otr, 1) AS otr_gap,  -- How much is masked
  courier_saved_kitchen_pct
FROM dual_otr
ORDER BY otr_gap DESC;
```

### Network Benchmark (Week of Jan 5, 2026)

| Metric | Value | Interpretation |
|--------|-------|----------------|
| **Customer OTR** | 86.7% | What customers experience |
| **Kitchen Process OTR** | 57.7% | Kitchen on-time to expected_ready |
| **OTR Gap** | **29 pts** | 29% of "on-time" deliveries had late kitchens |
| **Courier Saved Kitchen %** | 8.2% | Courier late too, masked kitchen delay |
| **Kitchen Late, Courier Waiting** | 27.8% | Kitchen late, but courier was waiting |

**Key Finding:** ~36% of "on-time" deliveries had kitchens that missed expected_ready!

### SLA Tier Breakdown

The `otr_sla_tier` field categorizes orders into timing buckets:

| Tier | Meaning | Impact |
|------|---------|--------|
| `9+_EARLY` | 9+ minutes early | Process concern (food sitting?) |
| `8_5_EARLY` | 5-8 minutes early | Slightly early |
| `4_1_EARLY` | 1-4 minutes early | Acceptable early |
| `ON_TIME` | Within SLA window | Target state |
| `1_4_LATE` | 1-4 minutes late | Minor delay |
| `5_15_LATE` | 5-15 minutes late | Moderate delay |
| `16_30_LATE` | 16-30 minutes late | Significant delay |
| `31+_LATE` | 31+ minutes late | Critical failure |

### Kitchen Handoff Scenarios (Delivery Only)

This is the core diagnostic framework for understanding WHY delivery orders fail. The classification uses `ready_for_pickup_sla_difference` (kitchen performance) and `courier_response_time_mins` (logistics performance).

**Key Thresholds:**
- Kitchen "On Time": ≤ 2 mins variance from expected ready time
- Courier Response "Fast": ≤ 5 mins from ready → driver arrival
- Handoff "Fast": ≤ 5 mins from driver arrival → pickup complete

| Scenario | Kitchen | Courier | Meaning |
|----------|---------|---------|---------|
| **A. Kitchen LATE, Courier Waits** | > 2 mins late | ≤ 5 mins response | Kitchen ran late, but driver was there waiting |
| **B. Kitchen FAST, Food Waits (Risk)** | ≤ 2 mins late | > 5 mins response | Kitchen was on time, but food sat waiting for courier |
| **C. Compounding Failure** | > 2 mins late | > 5 mins response | Both kitchen AND courier failed |
| **D. Ideal State** | ≤ 2 mins late | ≤ 5 mins response | Kitchen fast, courier fast, perfect sync |

**Scenario SQL (Production Definition):**
```sql
CASE
  WHEN dining_option != 'DELIVERY' THEN 'N/A (Pickup Order)'
  -- A. Kitchen LATE, Courier Waits: Kitchen slow, but driver was there waiting
  WHEN ready_for_pickup_sla_difference > 2.0 
   AND COALESCE(courier_response_time_mins, 0) <= 5.0 
  THEN 'A. Kitchen LATE, Courier Waits'
  -- B. Kitchen FAST, Food Waits (Risk): Kitchen on time, but food sat waiting for driver
  WHEN ready_for_pickup_sla_difference <= 2.0 
   AND COALESCE(courier_response_time_mins, 0) > 5.0 
  THEN 'B. Kitchen FAST, Food Waits (Risk)'
  -- C. Compounding Failure: Both kitchen and logistics failed
  WHEN ready_for_pickup_sla_difference > 2.0 
   AND COALESCE(courier_response_time_mins, 0) > 5.0 
  THEN 'C. Compounding Failure (Both LATE)'
  -- D. Ideal State: Kitchen fast and handoff fast
  ELSE 'D. Ideal State (Kitchen Fast, Handoff Fast)'
END AS kitchen_handoff_scenario
```

### Sit Time Decomposition

**Critical Insight:** Sit time (Ready → Pickup Complete) has TWO components with different owners:

| Component | Field | Owner | Definition |
|-----------|-------|-------|------------|
| **Courier Response Time** | `courier_response_time_mins` | Logistics | Ready for Pickup → Driver Arrival |
| **Kitchen Handoff Time** | `kitchen_handoff_time_mins` | Ops | Driver Arrival → Pickup Complete |

```
Ready for Pickup ──────────────────────────────────────────> Pickup Complete
                 │                        │                         │
                 └── Courier Response ────┴── Kitchen Handoff ──────┘
                     (Logistics)              (Ops)
```

**Why This Matters:**
- If `courier_response_time_mins` is high → Driver shortage/logistics issue
- If `kitchen_handoff_time_mins` is high → Expo/bagging issue, possible "fake bump"

### The "Ops Gap" Metric

A single number to diagnose who's at fault:

```sql
ops_gap_mins = kitchen_handoff_time_mins - courier_response_time_mins
```

| Value | Interpretation | Action |
|-------|----------------|--------|
| **Positive** | Ops is slower than Logistics | Audit expo window, bagging process |
| **Negative** | Logistics is slower than Ops | Courier incentives, driver allocation |
| **Near Zero** | Balanced | Look at total magnitude |

### Root Cause Attribution Framework

#### ⚠️ CRITICAL: Check Upstream Delays First

**Before attributing blame to handoff or driver, always check if the order was already delayed by kitchen issues upstream.** An order that was already 5+ minutes late leaving the kitchen cannot fairly blame the driver/handoff for the final OTR miss.

**Upstream Delay Check - Compare Expected vs Actual Timestamps:**

| Stage | Expected Field | Actual Field | Delay Calculation |
|-------|---------------|--------------|-------------------|
| Cooking Start | `expected_cooking_start_time_utc` | `actual_cooking_start_time_utc` | `queue_error` = actual - expected |
| Cooking Finish | `expected_cooking_finish_time_utc` | `actual_cooking_finish_time_utc` | `cook_error` = actual - expected |
| Ready for Pickup | `expected_ready_for_pickup_time_utc` | `actual_ready_for_pickup_time_utc` | `ready_for_pickup_sla_difference` |

**Attribution Logic:**

```
Step 1: Was the order already late when it became "Ready"?
        → Check: ready_for_pickup_sla_difference > 2 mins?
        
Step 2: IF YES (kitchen was late):
        → PRIMARY BLAME = KITCHEN (even if handoff/driver looks bad)
        → The delay cascaded downstream - kitchen is root cause
        
Step 3: IF NO (kitchen was on time):
        → Now we can fairly compare handoff vs driver:
           - If courier_response > handoff → LOGISTICS problem
           - If handoff > courier_response → OPS problem (handoff/expo)
```

**Why This Matters:**

If kitchen was 5 mins late, and then driver took 7 mins to arrive (2 mins "slow"):
- **Wrong attribution:** "Driver was slow" 
- **Correct attribution:** "Kitchen was the primary delay; driver was slightly slow but not the root cause"

For late orders, systematically identify the primary driver:

| Primary Root Cause | Conditions | Action |
|-------------------|------------|--------|
| **OPS: Kitchen Slow** | `ready_for_pickup_sla_difference > 5` AND `handoff ≤ 5` AND `courier_response ≤ 5` | Kitchen training, capacity |
| **OPS: Slow Handoff (Possible Fake Bump)** | `courier_response ≤ 5` AND `handoff > 8` **AND** `ready_for_pickup_sla_difference ≤ 2` | Audit expo, validate bumps |
| **LOGISTICS: Driver Shortage** | `ready_for_pickup_sla_difference ≤ 2` AND `courier_response > 10` | Courier incentives |
| **LOGISTICS: Slow Transit** | `transit_error > 5` AND `kitchen OK` | Route optimization |
| **COMPOUNDING** | `ready_for_pickup_sla_difference > 2` AND `courier_response > 5` | Multi-pronged intervention |
| **CASCADING from Kitchen** | `ready_for_pickup_sla_difference > 5` (regardless of handoff/driver) | Fix kitchen first |

### HDR Failure Profiles

When diagnosing underperforming HDRs, classify them into profiles:

| Profile | Pattern | Likely Cause | Action |
|---------|---------|--------------|--------|
| **Profile A: Ops Failure** | Fast drivers, slow handoffs | Expo bottleneck, fake bumping | Audit bagging, kitchen flow |
| **Profile B: Logistics Failure** | Fast handoffs, slow drivers | Driver shortage in area | Courier incentives, zone adjustments |
| **Profile C: Both Failing** | Both slow | Systemic issues | Full operational review |
| **Profile D: Ideal** | Both fast | Working as designed | Maintain current ops |

### Actionable Flags

Pre-calculated boolean flags for quick filtering:

| Flag | Condition | Investigation |
|------|-----------|---------------|
| `is_potential_fake_bump` | `courier_response ≤ 3` AND `handoff > 8` | Kitchen marked ready before food actually ready |
| `is_driver_shortage` | `ready_for_pickup ≤ 2` AND `courier_response > 15` | Food sat 15+ mins waiting for driver |
| `is_kitchen_bottleneck` | `ready_for_pickup > 5` AND `courier_response ≤ 5` AND `handoff ≤ 5` | Pure kitchen slowness |
| `is_compounding_failure` | `ready_for_pickup > 2` AND `courier_response > 5` | Both ops and logistics failed |
| `is_suspicious_force_bump` | Cook on target, but handoff slow, driver arrived quickly | Premature ready-for-pickup bump |

---

## Force Complete Analysis

**Force Completes** occur when kitchen staff manually progress orders before cooking/prep is actually finished.

### ⚠️ IMPORTANT: Monitor PREMATURE Force Completes Only

**Not all force completes are bad!** Items going through **Hybrid pod** (vending, pre-made items) naturally trigger force completes because they don't have traditional cooking steps.

| Metric | What It Measures | When to Worry |
|--------|------------------|---------------|
| `has_force_progression` | ANY force complete (includes Hybrid pod) | High % is normal (40-60%) |
| **`has_premature_force_complete`** | Force complete BEFORE reasonable cook time | **>10% needs attention** |
| `has_critical_force_complete` | Force complete of critical cooking step | Any occurrence is concerning |

### Key Force Complete Fields

| Field | Source Table | Description |
|-------|--------------|-------------|
| `has_force_progression` | `imperfect_kitchen_items` | Order had at least one force complete event (includes Hybrid pod - expected) |
| **`has_premature_force_complete`** | `imperfect_kitchen_items` | **THE KEY METRIC** - Force complete before reasonable cook time |
| `has_critical_force_complete` | `imperfect_kitchen_items` | Force complete of critical cooking step |
| `force_complete_item_count` | Aggregated | Number of items force-completed in order |
| `force_complete_pod_type` | `imperfect_kitchen_items` | Which pod type was force-completed (Hot/Cold/Hybrid) |

### Premature Force Complete Thresholds

| Premature FC Rate | Interpretation | Action |
|-------------------|----------------|--------|
| < 5% | Normal operations | Monitor |
| 5-10% | Elevated | Investigate capacity/training |
| 10-20% | High | Audit specific pods/shifts |
| **> 20%** | **Critical** | Immediate intervention required |

### Force Complete + Long Handoff Pattern

**The Fake Bump Signature:**
```
Fast courier response (< 5 min) + Long handoff (> 8 min) + Has PREMATURE Force Complete
```

This pattern indicates kitchen marked order "ready" prematurely, driver showed up, and then waited while food was actually being prepared.

### Why This Distinction Matters

| Scenario | All FC | Premature FC | Interpretation |
|----------|--------|--------------|----------------|
| High-volume Hybrid pod HDR | 60% | 5% | Normal - Hybrid items expected |
| High-volume Hot pod HDR | 60% | 25% | **Problem** - Staff gaming metrics |
| Low-volume new HDR | 40% | 15% | Training issue - staff confused |

### Query: Premature Force Complete Rate by HDR

```sql
WITH premature_fc AS (
  SELECT 
    o.hdr_id,
    h.hdr_name,
    h.hdr_class,
    COUNT(DISTINCT o.order_id) AS total_orders,
    -- All force completes (includes Hybrid pod - expected to be high)
    COUNT(DISTINCT CASE WHEN fc.has_force_progression = 1 THEN o.order_id END) AS all_fc_orders,
    -- PREMATURE force completes (the key metric)
    COUNT(DISTINCT CASE WHEN fc.has_premature_force_complete = 1 THEN o.order_id END) AS premature_fc_orders,
    ROUND(AVG(o.kitchen_handoff_time_mins), 1) AS avg_handoff,
    ROUND(AVG(CASE 
      WHEN o.actual_ready_for_pickup_time_utc <= o.expected_ready_for_pickup_time_utc THEN 1 ELSE 0 
    END) * 100, 1) AS kitchen_process_otr
  FROM `wonder-dw-prod-brd.orders.hdr_orders` o
  JOIN `wonder-dw-prod-brd.dw.dim_hdrs` h ON o.hdr_id = h.hdr_id
  LEFT JOIN (
    SELECT 
      order_id, 
      MAX(has_force_progression) AS has_force_progression,
      MAX(has_premature_force_complete) AS has_premature_force_complete
    FROM `wonder-dw-prod-brd.orders.imperfect_kitchen_items`
    GROUP BY 1
  ) fc ON o.order_id = fc.order_id
  WHERE o.order_status = 'COMPLETE'
    AND o.brand_category = 'WONDER_HDR'
    AND o.dining_option = 'DELIVERY'
    AND o.order_channel IN ('APP', 'WEB', 'IN_PERSON')
    AND o.service_date_et >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
  GROUP BY 1, 2, 3
  HAVING COUNT(DISTINCT o.order_id) >= 50
)
SELECT 
  hdr_name,
  hdr_class,
  total_orders,
  all_fc_orders,
  ROUND(all_fc_orders * 100.0 / total_orders, 1) AS all_fc_pct,
  premature_fc_orders,
  ROUND(premature_fc_orders * 100.0 / total_orders, 1) AS premature_fc_pct,  -- KEY METRIC
  avg_handoff,
  kitchen_process_otr,
  CASE 
    WHEN premature_fc_orders * 100.0 / total_orders > 20 THEN '🔴 CRITICAL'
    WHEN premature_fc_orders * 100.0 / total_orders > 10 THEN '🟠 HIGH'
    WHEN premature_fc_orders * 100.0 / total_orders > 5 THEN '🟡 ELEVATED'
    ELSE '✅ OK'
  END AS status
FROM premature_fc
ORDER BY premature_fc_pct DESC;
```

### 🔍 Force Complete Pattern Analysis: Aggressive vs Rescue

**Critical Insight:** Not all elevated FC rates mean the same thing. Understanding the *pattern* reveals whether FCs are preventative or reactive.

#### Two Types of Force Complete Patterns

| Pattern | What It Is | FC vs Normal Variance | What It Means |
|---------|------------|----------------------|---------------|
| **"Aggressive FCs"** | Staff proactively FC'ing items to clear queue | FC variance ≤ Normal variance | FC is preventative - items cut short early |
| **"Rescue FCs"** | Items drowning, FC used as last resort | FC variance > Normal variance | FC is reactive - damage already done |

#### How to Diagnose: Compare Production Variance by Completion Type

```sql
-- Compare production variance: Force Complete vs Normal Complete by Pod
WITH order_fc_status AS (
  SELECT 
    i.order_number,
    MAX(i.has_force_progression) AS is_force_complete
  FROM `wonder-dw-prod-brd.orders.imperfect_kitchen_items` i
  WHERE i.order_assigned_to_pod_date >= DATE_TRUNC(DATE_SUB(CURRENT_DATE("America/New_York"), INTERVAL 1 WEEK), WEEK(MONDAY))
    AND i.order_assigned_to_pod_date < DATE_TRUNC(CURRENT_DATE("America/New_York"), WEEK(MONDAY))
  GROUP BY 1
)
SELECT 
  h.hdr_name,
  lb.pod_type,
  CASE WHEN fc.is_force_complete = 1 THEN 'Force Complete' ELSE 'Normal Complete' END AS completion_type,
  COUNT(*) AS items,
  ROUND(AVG(lb.actual_duration_sec / 60.0), 2) AS avg_actual_min,
  ROUND(AVG(lb.expected_duration_sec / 60.0), 2) AS avg_expected_min,
  ROUND(AVG((lb.actual_duration_sec - lb.expected_duration_sec) / 60.0), 2) AS variance_min
FROM `wonder-dw-prod-brd.orders.hdr_kitchen_line_builds` lb
JOIN `wonder-dw-prod-brd.dw.dim_hdrs` h ON lb.hdr_id = h.hdr_id
LEFT JOIN order_fc_status fc ON lb.order_number = fc.order_number
WHERE DATE(lb.order_assigned_to_pod_time) >= DATE_TRUNC(DATE_SUB(CURRENT_DATE("America/New_York"), INTERVAL 1 WEEK), WEEK(MONDAY))
  AND DATE(lb.order_assigned_to_pod_time) < DATE_TRUNC(CURRENT_DATE("America/New_York"), WEEK(MONDAY))
  AND lb.pod_type IN ('Cold Pod', 'Hot Pod')
GROUP BY 1, 2, 3
ORDER BY hdr_name, pod_type, completion_type;
```

#### Network Benchmark (FC Gap)

| Pod Type | FC Variance | Normal Variance | FC Gap | Interpretation |
|----------|-------------|-----------------|--------|----------------|
| Cold Pod | +1.24 min | +0.96 min | **+0.28 min** | Normal: FC slightly slower |
| Hot Pod | -0.65 min | -0.56 min | -0.09 min | Normal: FC slightly faster (cut short) |

#### Interpreting the FC Gap

| Store FC Gap | vs Network Gap | Pattern | What It Means |
|--------------|----------------|---------|---------------|
| FC ≈ Normal | ≈ +0.28 min | Precautionary | FCs are routine, not rescues |
| FC much slower (+1-3 min) | 3-10x worse | **Rescue** | Items were drowning before FC |
| FC faster than Normal | Negative gap | **Aggressive** | Staff gaming the system |

#### Example: Rescue Pattern at New Stores

| HDR | Cold Pod FC Variance | Cold Pod Normal Variance | FC Gap | vs Network |
|-----|---------------------|-------------------------|--------|------------|
| Deer Park | +3.45 min | +1.96 min | **+1.49 min** | 5x worse |
| Port Jefferson | +4.55 min | +1.58 min | **+2.97 min** | 10x worse |
| Hackettstown | +1.40 min | +1.34 min | +0.06 min | Normal |

**Key Insight:** At Deer Park and Port Jefferson, FC Cold Pod items were **already 3-4 minutes behind** when force-completed. The FC didn't hide the problem - it *recorded* the problem.

#### Actionable Takeaways

| If You See | Diagnosis | Action |
|------------|-----------|--------|
| High FC rate + FC slower than Normal | **Rescue FCs** - kitchen can't keep up | Focus on execution speed, not FC reduction |
| High FC rate + FC ≈ Normal | **Precautionary FCs** - Normal ops | Monitor, no immediate action |
| High FC rate + FC faster than Normal | **Aggressive FCs** - Staff gaming | Training on proper FC usage |

#### Why "Reduce FCs" is the Wrong Intervention for Rescue Pattern

When FC items are slower than Normal items:
- FCs are a **symptom**, not a cause
- Items would take **even longer** without FC
- Reducing FCs would make OTR **worse**, not better
- The fix is **faster execution** so FCs aren't needed

---

## Order Size (IPC) Impact on Ticket Time

**Items Per Check (IPC)** strongly correlates with ticket time and O2E. Larger orders take longer to prepare and have compounding complexity.

### Network Benchmarks by IPC

| IPC | % of Orders | Avg Ticket | Avg Queue | Avg Cook | Avg Bagging | Avg O2E |
|-----|-------------|------------|-----------|----------|-------------|---------|
| 1 item | ~16% | 9.7 min | 2.2 min | 6.4 min | 1.0 min | 26.5 min |
| 2 items | ~22% | 12.8 min | 2.1 min | 9.5 min | 1.2 min | 28.6 min |
| 3 items | ~20% | 15.0 min | 2.2 min | 11.3 min | 1.5 min | 30.7 min |
| 4 items | ~14% | 16.8 min | 2.4 min | 12.8 min | 1.6 min | 32.7 min |
| 5 items | ~10% | 18.0 min | 2.4 min | 13.8 min | 1.8 min | 33.8 min |
| 6+ items | ~18% | 20.9 min | 2.8 min | 15.9 min | 2.2 min | 37.6 min |

### IPC Impact on Ticket Time (Regression)

From physics-based regression modeling:

```
ticket_time = anchor_cook_time 
            + β₀ (intercept: ~3.4 min base non-cook time)
            + β₁ (kitchen_load × 0.082 mins per order/hour)
```

**Key Insight:** Each additional item adds ~2.5-3 minutes to ticket time on average.

### Why IPC Matters for OTR

1. **Higher IPC = Longer Cook Time** - More items means more parallel cooking coordination
2. **Complexity Stacking** - Multi-restaurant orders (MROs) compound IPC impact
3. **ETA Estimation** - Algorithm must accurately predict IPC impact to set realistic promises
4. **Capacity Planning** - Peak hour + high IPC = capacity stress

---

## Sequencer Delay Analysis

### Key Fields for Sequencer Analysis

| Field | Table | Description |
|-------|-------|-------------|
| `delay_duration_mins` | `hdr_kitchen_order_item` | Time item was held back by sequencer |
| `initial_hold_back_strategy` | `hdr_kitchen_order_item` | Original sequencer decision |
| `final_hold_back_strategy` | `hdr_kitchen_order_item` | Actual hold back applied |
| `hot_hold_item_a_la_minute_fl` | `hdr_kitchen_order_item` | **KEY!** Flag for items that need fresh prep |
| `hot_hold_prep_fl` | `hdr_kitchen_order_item` | Hot hold prep eligible |

### Sequencer Contribution to Ticket Time

**How to measure sequencer's share of ticket time:**

```sql
-- If MIN(delay_duration_mins) > 0 for an order, 
-- the ENTIRE order was held back by sequencer
MIN(COALESCE(delay_duration_mins, 0)) > 0 AS entire_order_held
```

**Network Benchmark (Jan 2026):**

| Metric | Value |
|--------|-------|
| Orders with ANY item held | 42.2% |
| Orders with ENTIRE order held | 8.5% |
| Average max delay per order | 1.6 min |
| Sequencer delay % of ticket | ~10-15% |

### ⚠️ "Bad Interaction" Bucket: Hot Hold vs A La Minute

**The Problem:**
- Outside Pleasantville, system assumes all hot-hold-eligible items can be held
- But items flagged `hot_hold_item_a_la_minute_fl = 1` need **fresh prep (a la minute)**
- When sequencer holds back these items → quality degradation + timing mismatch

**Network Impact:**
| Metric | Value |
|--------|-------|
| Total A La Minute items | 44,659 (weekly) |
| A La Minute items held back | 17,021 (38.1%) |
| **"Bad Interaction" Rate** | **38.1%** |

**Pleasantville Exception:**
| Location | % ALM Items Held | Kitchen Process OTR |
|----------|------------------|---------------------|
| Pleasantville | 10.8% | **70.2%** |
| Network (others) | 16.7% | 57.9% |

Pleasantville's lower ALM hold rate correlates with 12+ point better Kitchen OTR.

### Order Complexity Impact on Sequencer & OTR

| Complexity | Order Size | Orders | Avg Seq Delay | % ALM Held | Avg Ticket | Kitchen OTR |
|------------|------------|--------|---------------|------------|------------|-------------|
| HIGH_VARIANCE | LARGE (5+) | 7,731 | 4.0 min | 42.2% | 21.0 min | **52.3%** |
| HIGH_VARIANCE | MEDIUM (3-4) | 5,871 | 3.3 min | 26.9% | 17.0 min | 54.2% |
| HIGH_VARIANCE | SMALL (1-2) | 2,325 | 3.2 min | 10.6% | 14.4 min | 55.6% |
| MED_VARIANCE | LARGE | 2,322 | 2.8 min | 9.0% | 17.6 min | 56.6% |
| LOW_VARIANCE | LARGE | 596 | 2.4 min | 3.7% | 16.6 min | 61.6% |
| LOW_VARIANCE | SMALL | 8,780 | 0.3 min | 1.8% | 10.6 min | **64.1%** |

**Key Insight:** HIGH_VARIANCE + LARGE_ORDER = 12 pt worse Kitchen OTR vs LOW_VARIANCE + SMALL_ORDER

### Complexity Definitions

```sql
-- Cook Time Variance (how spread out are the item cook times?)
STDDEV_POP(expected_step_time / 60.0) AS cook_time_stddev
MAX(expected_step_time / 60.0) - MIN(expected_step_time / 60.0) AS cook_time_range

-- Complexity Tier
CASE 
  WHEN cook_time_range > 6 THEN 'HIGH_VARIANCE'  -- Hard for sequencer
  WHEN cook_time_range > 3 THEN 'MED_VARIANCE'
  ELSE 'LOW_VARIANCE'                            -- Easy for sequencer
END AS complexity_tier
```

### Query: HDRs with Sequencer/Complexity Issues

```sql
WITH order_sequencer AS (
  SELECT 
    koi.order_id,
    koi.hdr_id,
    MIN(COALESCE(koi.delay_duration_mins, 0)) AS min_delay_mins,
    MAX(COALESCE(koi.delay_duration_mins, 0)) AS max_delay_mins,
    STDDEV_POP(koi.expected_step_time / 60.0) AS cook_time_stddev,
    MAX(koi.expected_step_time / 60.0) - MIN(koi.expected_step_time / 60.0) AS cook_time_range,
    COUNT(*) AS item_count,
    SUM(CASE WHEN koi.hot_hold_item_a_la_minute_fl = 1 AND koi.delay_duration_mins > 0 THEN 1 ELSE 0 END) AS alm_items_held,
    SUM(CASE WHEN koi.hot_hold_item_a_la_minute_fl = 1 THEN 1 ELSE 0 END) AS total_alm_items
  FROM `wonder-dw-prod-brd.orders.hdr_kitchen_order_item` koi
  WHERE koi.order_status = 'COMPLETED'
    AND DATE(koi.order_assigned_to_pod_time) >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
  GROUP BY 1, 2
)
SELECT 
  h.hdr_name,
  h.hdr_class,
  COUNT(*) AS total_orders,
  ROUND(AVG(os.max_delay_mins), 2) AS avg_seq_delay,
  ROUND(SUM(CASE WHEN os.min_delay_mins > 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS pct_entire_order_held,
  ROUND(AVG(os.cook_time_stddev), 2) AS avg_cook_stddev,
  ROUND(AVG(os.cook_time_range), 2) AS avg_cook_range,
  ROUND(AVG(os.item_count), 1) AS avg_ipc,
  ROUND(SUM(os.alm_items_held) * 100.0 / NULLIF(SUM(os.total_alm_items), 0), 1) AS pct_alm_held,
  CASE 
    WHEN SUM(os.alm_items_held) * 100.0 / NULLIF(SUM(os.total_alm_items), 0) > 50 THEN '🔴 HIGH ALM Risk'
    WHEN SUM(os.alm_items_held) * 100.0 / NULLIF(SUM(os.total_alm_items), 0) > 30 THEN '🟠 Elevated'
    ELSE '✅ OK'
  END AS alm_status
FROM order_sequencer os
JOIN `wonder-dw-prod-brd.dw.dim_hdrs` h ON os.hdr_id = h.hdr_id
GROUP BY 1, 2
HAVING COUNT(*) >= 200
ORDER BY pct_alm_held DESC NULLS LAST;
```

### Flags for Complex/Risky Orders

| Flag | Definition | Risk |
|------|------------|------|
| `high_variance_order` | `cook_time_range > 6 min` | Sequencer struggles |
| `large_complex_order` | `IPC >= 5 AND cook_time_range > 6` | Worst case |
| `has_alm_held` | ALM item held by sequencer | Quality risk |
| `entire_order_held` | `MIN(delay_duration) > 0` | Sequencer bottleneck |

---

## Hot Hold Management & OTR Impact

### The Hot Hold Problem

**Sequencer-caused delays due to incorrect hot hold assumptions** create a significant bucket of OTR misses.

The core issue: **Sequencer assumes items can be hot-held and adds delay, but ETA model correctly estimates fresh prep time.** The sequencer delay is ADDITIONAL time not in the ETA.

### Key Concepts

| Term | Definition | Impact |
|------|------------|--------|
| **Hot Hold Eligible** | Item can be pre-cooked and held warm | Sequencer may hold back |
| **Preparation Type** | `HOT_HOLDING` vs `A_LA_MINUTE` | Determines expected cooking method |
| **Missing Pouch** | System says hot hold available, but it's NOT | Kitchen must cook fresh → unplanned delay |
| **Surprise Pouch** | System says NO hot hold, but it IS available | Waterfall reprioritization chaos |
| **Compliance Rate** | 1 - (Missing + Surprise) | How accurate is hot hold inventory |
| **A La Minute (ALM)** | Item flagged as needing fresh prep | `hot_hold_item_a_la_minute_fl = 1` |

### Two Distinct Root Causes

| Root Cause | Description | Owner |
|------------|-------------|-------|
| **Sequencer-Caused Delay** | Sequencer holds ALM items assuming hot hold | Product/Sequencer |
| **Hot Hold Management** | Missing/surprise pouches, inventory tracking | Ops |

### ⚠️ Critical: Hot Hold Eligibility Varies by Location

**Not all HDRs have the same hot hold items enabled!**

Hot hold eligibility is configured per HDR via `int_hot_hold_components`:
- Pleasantville has more hot pod items enabled (test location)
- Other HDRs may have different item eligibility
- Must join to `int_hot_hold_components` to get location-specific eligibility

### Key Tables for Hot Hold Analysis

| Table | Purpose |
|-------|---------|
| `orders.hdr_kitchen_pod_item` | Task-level hot hold compliance data |
| `int_hot_hold_components` | Location × Item × Date hot hold eligibility |
| `hdr_kitchen_order_item.hot_hold_item_a_la_minute_fl` | Item needs fresh prep flag |
| `hdr_kitchen_order_item.delay_duration_mins` | Sequencer holdback time |

### Hot Hold Compliance Fields

| Field | Table | Description |
|-------|-------|-------------|
| `hot_hold_eligible` | `hdr_kitchen_pod_item` | Item is hot-hold-eligible at this HDR |
| `system_overstated_hh_inventory` | `hdr_kitchen_pod_item` | **Missing Pouch** - system said available, wasn't |
| `system_understated_hh_inventory` | `hdr_kitchen_pod_item` | **Surprise Pouch** - system said unavailable, was |
| `hot_hold_consumption_quantity` | `hdr_kitchen_pod_item` | Quantity consumed from hot hold |
| `hh_appliance_time_min` | `hdr_kitchen_pod_item` | Retherm time |
| `hot_hold_holding_time_minutes` | `hdr_kitchen_pod_item` | Time in hot hold |

### The Mismatch That Causes OTR Misses

```
ETA Model: Estimates fresh prep time (correctly - doesn't assume hot hold)
Sequencer: Assumes hot hold → adds delay_duration to hold items back
Result: Sequencer delay is ADDITIONAL time not in the ETA estimate

BAD_INTERACTION = Sequencer-Caused Delay Due to Hot Hold Assumption
├── Sequencer holds ALM item back (assumes it can be hot-held)
├── ETA model already estimated fresh prep time correctly
├── Sequencer delay (+4.5 min) is EXTRA, not in ETA
├── Total time = ETA estimate + Sequencer delay
├── Kitchen OTR: 50% (vs 57% without holdback)
└── Ticket error: +1.4 min (the sequencer delay that wasn't planned)

PROOF: If we subtract sequencer delay from ticket error:
├── BAD_INTERACTION: Ticket error (1.4) - Seq delay (4.5) = -3.1 min
├── Kitchen would be 3 min FASTER than ETA without sequencer hold
└── The entire ticket error is caused by sequencer's hot hold assumption
```

**Separate Issue: Hot Hold Management (Ops Responsibility)**

| Scenario | Prep Type | Pouch Status | Root Cause | Owner |
|----------|-----------|--------------|------------|-------|
| Sequencer holds ALM | `A_LA_MINUTE` | N/A | Sequencer shouldn't hold ALM | **Sequencer/Product** |
| Hot hold expected, missing | `HOT_HOLDING` | Missing | Should have stocked hot hold | **Ops/Hot Hold Mgmt** |
| ALM expected, missing | `A_LA_MINUTE` | Missing | Inventory not available | **Ops/Hot Hold Mgmt** |
| Surprise pouch appears | Either | Surprise | Inventory tracking off | **Ops/Hot Hold Mgmt** |

```
MISSING_POUCH with HOT_HOLDING prep type:
├── System expected hot hold to be available
├── Kitchen didn't have it stocked
├── Had to cook fresh (unplanned)
└── Owner: Ops/Hot Hold Management

MISSING_POUCH with A_LA_MINUTE prep type:
├── System expected inventory available
├── Inventory wasn't there
├── Execution delayed
└── Owner: Ops/Hot Hold Management

SURPRISE_POUCH (either prep type):
├── System didn't know hot hold existed
├── Kitchen started cooking fresh
├── Hot hold pouch appears!
├── Waterfall reprioritization chaos
└── Owner: Ops/Hot Hold Management (inventory tracking)
```

### Impact Quantification: Sequencer-Caused Delay

| Interaction Type | Orders/Week | Avg Ticket | Kitchen OTR | Ticket Error | Seq Delay |
|------------------|-------------|------------|-------------|--------------|-----------|
| **BAD_INTERACTION** (Sequencer held ALM) | 5,785 | 20.1 min | **49.5%** | +1.4 min | **+4.5 min** |
| **CORRECT** (ALM not held) | 5,659 | 12.1 min | 56.5% | +0.2 min | +0.4 min |
| **Delta** | | **+8.0 min** | **-7 pts** | **+1.2 min** | **+4.1 min** |

**Key Insight:** The +1.4 min ticket error is entirely explained by the +4.5 min sequencer delay. Without the sequencer holding these items, the kitchen would actually be 3 min FASTER than ETA.

### Network Hot Hold Compliance by Item

| Compliance Tier | Items | Strategy | Impact |
|-----------------|-------|----------|--------|
| 🔴 **<70%** | Jasmine Rice (31%), Mac & Cheese (37%), Barbacoa, Carnitas, Queso | `ASSUME_FRESH` | Stop holding ALM |
| 🟠 **70-90%** | Pinto Beans, Grain Mix, Poke Rice, Black Beans | `SHORT_HOLD` | Hold <2 min |
| ✅ **>90%** | Adobo Chicken (95%), White Rice (98%), Brown Rice, Souvlaki | `TRUST_HH` | Full holdback OK |

### Query: Hot Hold Compliance by Item (Network)

```sql
SELECT
  CASE WHEN consumption_type = 'check' THEN 'single' ELSE consumption_type END AS consumption_type,
  hot_hold_stock_item_number AS item_number,
  ROUND(COUNT(DISTINCT CASE 
    WHEN COALESCE(hot_hold_eligible, 0) = 1 AND system_overstated_hh_inventory = 1 
    THEN task_id END) * 100.0 / NULLIF(COUNT(DISTINCT CASE 
    WHEN COALESCE(hot_hold_eligible, 0) = 1 OR hot_hold_consumption_quantity IS NOT NULL 
    THEN task_id END), 0), 1) AS missing_pouch_pct,
  ROUND(COUNT(DISTINCT CASE 
    WHEN hot_hold_eligible = 1 AND system_understated_hh_inventory = 1 
    THEN task_id END) * 100.0 / NULLIF(COUNT(DISTINCT CASE 
    WHEN COALESCE(hot_hold_eligible, 0) = 1 OR hot_hold_consumption_quantity IS NOT NULL 
    THEN task_id END), 0), 1) AS surprise_pouch_pct,
  -- Compliance = 100 - missing - surprise
  ROUND(100 - (missing + surprise), 1) AS compliance_pct,
  COUNT(DISTINCT CASE 
    WHEN COALESCE(hot_hold_eligible, 0) = 1 OR hot_hold_consumption_quantity IS NOT NULL 
    THEN task_id END) AS total_tasks
FROM `wonder-dw-prod-brd.orders.hdr_kitchen_pod_item` hkpi
LEFT JOIN `wonder-dw-prod-brd.orders.hdr_kitchen_order_item` koi 
  ON hkpi.cooking_task_item_id = koi.id
WHERE koi.order_assigned_to_pod_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
  AND component_item_number IS NOT NULL
GROUP BY 1, 2
HAVING total_tasks >= 100
ORDER BY compliance_pct ASC;
```

### Query: Hot Hold Eligibility by HDR (Location-Specific)

```sql
-- Check which items are hot-hold-eligible at a specific HDR
SELECT DISTINCT
  hdr_id,
  service_date,
  component_item_number,
  component_item_name,
  hot_hold_item_number,
  holding_time_minutes,
  retherm_time_minutes
FROM `int_hot_hold_components`
WHERE hdr_id = 'YOUR_HDR_ID'
  AND service_date = CURRENT_DATE()
ORDER BY component_item_name;
```

### Recommended Item-Level Strategy

```sql
-- Apply item-level hot hold strategy based on compliance
CASE 
  WHEN item_compliance_rate >= 90 THEN 'TRUST_HOT_HOLD'    -- Hold ALM items
  WHEN item_compliance_rate >= 70 THEN 'SHORT_HOLD'        -- Hold <2 min only
  WHEN item_compliance_rate < 70 THEN 'ASSUME_FRESH_PREP'  -- Don't hold ALM
END AS hot_hold_strategy
```

### Key Takeaway

**Hot hold issues are a significant OTR miss bucket with TWO distinct root causes:**

| Root Cause | Impact | Owner | Fix |
|------------|--------|-------|-----|
| **Sequencer holds ALM** | +4.5 min delay, -7 pt OTR | Product/Sequencer | Stop holding ALM items |
| **Missing Pouch (HOT_HOLDING)** | Unplanned fresh cook | Ops | Better hot hold stocking |
| **Missing Pouch (A_LA_MINUTE)** | Inventory delay | Ops | Inventory management |
| **Surprise Pouch** | Waterfall chaos | Ops | Inventory tracking |

**For Sequencer-caused delays:** The sequencer delay is the ENTIRE source of ticket error (kitchen would be 3 min faster without hold)

**For Hot Hold Management:** Missing pouches mean Ops didn't have inventory ready when system expected it

---

## Imperfect Kitchen Items (Item-Level Diagnostics)

The `imperfect_kitchen_items` model provides **item-level** diagnostics for identifying inefficiencies in the cooking process. An "Imperfect Menu Item" is any completed menu item exhibiting one or more characteristics indicating a deviation from ideal/efficient cooking.

### Why This Matters for OTR

Imperfect items directly cause:
1. **Longer ticket times** → Kitchen delays → Late orders
2. **Force completes** → Quality issues → Remakes → More delays
3. **Expo bottlenecks** → Orders waiting → Delivery delays

### Actionable Flags (Count Toward `issue_count`)

| Flag | Definition | Threshold | Root Cause |
|------|------------|-----------|------------|
| `has_kds_remake` | Item was remade after cook | `remake_type = 'KDS_REMAKE'` | Quality/Recipe issue |
| `has_bump` | Item returned to previous pod | Action = 'RETURN' | Workflow error |
| `has_long_queue` | Item waited too long before cooking | `item_queue_time_min >= 5` | Bottleneck |
| `has_long_pending_packaging` | Item waited too long for expo | `item_pending_packaging_duration_mins >= 5` | Expo bottleneck |
| `has_longer_than_expected_production_time` | Actual cook exceeded expected | `(production_time_min - expected_step_time/60) > 3` | Recipe/Skill issue |
| `has_missing_signal` | Production time is 0 or NULL | `COALESCE(production_time_min, 0) = 0` | KDS tracking failure |
| `last_item_expo_wait_time_gt_2` | Last item waited >2 min at expo | Last item + `item_expo_wait_time > 2` | Expo bottleneck |
| `has_reset` | Cooking step/timer was reset | `reset = TRUE AND cooking_activity = 'COOK'` | Error/re-do |
| `has_missing_pouch` | Expected hot hold unavailable | `pouch_bucket = 'MISSING POUCH'` | Inventory issue |
| `has_surprise_pouch` | Unexpected hot hold appeared | `pouch_bucket = 'SURPRISE POUCH'` | Inventory tracking |
| `has_out_of_sync_sequencer_hh_alm` | Sequencer/hot hold mismatch | `pouch_bucket = 'OUT OF SYNC...'` | System sync issue |
| `has_sequencer_pantry_out_of_sync` | Sequencer/pantry mismatch | `bad_interaction_root_cause LIKE '%SEQUENCER & PANTRY OUT OF SYNC%'` | System sync issue |
| `has_bad_interaction` | Sequencer held ALM item incorrectly | From `hdr_kitchen_pod_item` | Sequencer logic |
| `has_double_delay` | Double delay applied | From `hdr_kitchen_pod_item` | Sequencer issue |
| `has_trickling_violation` | Item started before longer-cook item | Later item has higher cook time | FIFO violation |
| `has_critical_force_complete` | Force completed before <10% expected time | `is_critical_force_complete = 1` | Process failure |

### Force Complete Severity Tiers

| Tier | Definition | Severity Rank | Concern Level |
|------|------------|---------------|---------------|
| `Critical (Before Focus)` | Force completed before item even focused | 5 | 🔴 Process failure |
| `Critical (<10%)` | Force completed at <10% of expected time | 4 | 🔴 Severe |
| `High Concern (10-50%)` | Force completed at 10-50% of expected time | 3 | 🟠 High |
| `Low Concern (50-90%)` | Force completed at 50-90% of expected time | 2 | 🟡 Moderate |
| `On Time (>=90%)` | Force completed at >=90% of expected time | 1 | ✅ OK |

**Key Fields:**
- `has_premature_force_complete` - Force complete before expected (severity > Low Concern)
- `has_critical_force_complete` - Force complete at <10% of expected time
- `min_pct_of_expected_time_elapsed` - Lowest % across all pods for this item
- `first_force_progression_pod_type` - Which pod type force completed first
- `first_force_progression_pod_code` - Which specific pod

### Informational Flags (Context, Not Counted in `issue_count`)

| Flag | Definition | Purpose |
|------|------------|---------|
| `has_delay_applied` | Delay applied BEFORE cooking started | KDS communicated delay correctly |
| `has_unapplied_delay` | Delay applied AFTER cooking started | KDS delay communication failure |
| `has_hot_hold_eligible_component` | Item has hot-hold-eligible component | Context for pouch flags |
| `has_a_la_minute_component` | Item needs fresh prep (ALM) | Context for bad interaction |
| `is_speed_line` | Hybrid pod with no expected appliance time | Speed line context |
| `has_shorter_than_expected_production_time` | Actual cook < expected - 3 min | May indicate surprise pouch |

### Trickling Behavior (FIFO Violations)

Trickling occurs when shorter-cook-time items start AFTER longer-cook-time items in the same order/pod, causing sequencing inefficiency.

| Flag | Definition |
|------|------------|
| `has_trickling_violation` | Item started before a later item with longer cook time (>0.1 min diff) |
| `trickling_cook_time_diff_mins` | How much longer the later item's cook time was |
| `has_batched_trickling_violation` | Trickling violation occurred in a batched item |
| `trickling_batch_size` | Size of the batch involved in trickling |

### Line Skipper Detection

Identifies items that waited >30 mins while other items "skipped the line":

| Field | Definition |
|-------|------------|
| `time_waiting` | Minutes item waited before cooking (>30 min threshold) |
| `count_of_line_skippers` | Items that assigned AFTER but started cooking BEFORE this item |
| `incoming_orders` | Items that assigned during this item's wait time |
| `skipper_ratio` | `count_of_line_skippers / incoming_orders` |

### Issue Count Calculation

```sql
issue_count = (
  has_kds_remake
  + last_item_expo_wait_time_gt_2
  + has_longer_than_expected_production_time
  + has_long_pending_packaging
  + has_long_queue
  + has_bump
  + has_reset
  + has_missing_pouch
  + has_surprise_pouch
  + has_out_of_sync_sequencer_hh_alm
  + has_sequencer_pantry_out_of_sync
  + has_missing_signal
  + has_bad_interaction
  + has_double_delay
  + has_trickling_violation
  + has_critical_force_complete
)
```

### Query: Imperfect Items by HDR (Weekly)

```sql
SELECT
  hdr_name,
  COUNT(DISTINCT id) AS total_items,
  -- Actionable flags
  ROUND(SUM(has_kds_remake) * 100.0 / COUNT(*), 2) AS pct_kds_remake,
  ROUND(SUM(has_long_queue) * 100.0 / COUNT(*), 2) AS pct_long_queue,
  ROUND(SUM(has_long_pending_packaging) * 100.0 / COUNT(*), 2) AS pct_long_pending_packaging,
  ROUND(SUM(has_longer_than_expected_production_time) * 100.0 / COUNT(*), 2) AS pct_longer_than_expected,
  ROUND(SUM(last_item_expo_wait_time_gt_2) * 100.0 / COUNT(*), 2) AS pct_last_item_expo_wait,
  ROUND(SUM(has_bump) * 100.0 / COUNT(*), 2) AS pct_bump,
  ROUND(SUM(has_reset) * 100.0 / COUNT(*), 2) AS pct_reset,
  ROUND(SUM(has_missing_pouch) * 100.0 / COUNT(*), 2) AS pct_missing_pouch,
  ROUND(SUM(has_surprise_pouch) * 100.0 / COUNT(*), 2) AS pct_surprise_pouch,
  ROUND(SUM(has_bad_interaction) * 100.0 / COUNT(*), 2) AS pct_bad_interaction,
  ROUND(SUM(has_trickling_violation) * 100.0 / COUNT(*), 2) AS pct_trickling,
  -- Force complete severity
  ROUND(SUM(has_force_progression) * 100.0 / COUNT(*), 2) AS pct_force_complete,
  ROUND(SUM(has_premature_force_complete) * 100.0 / COUNT(*), 2) AS pct_premature_force,
  ROUND(SUM(has_critical_force_complete) * 100.0 / COUNT(*), 2) AS pct_critical_force,
  -- Overall imperfection
  ROUND(SUM(CASE WHEN issue_count > 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS pct_imperfect,
  ROUND(AVG(issue_count), 2) AS avg_issue_count
FROM `imperfect_kitchen_items`
WHERE order_assigned_to_pod_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
  AND order_status = 'COMPLETED'
GROUP BY 1
ORDER BY pct_imperfect DESC;
```

### Query: Imperfect Items by Menu Item

```sql
SELECT
  menu_item_name,
  COUNT(DISTINCT id) AS total_items,
  ROUND(SUM(CASE WHEN issue_count > 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS pct_imperfect,
  -- Top issue types
  ROUND(SUM(has_longer_than_expected_production_time) * 100.0 / COUNT(*), 2) AS pct_longer_than_expected,
  ROUND(SUM(has_long_queue) * 100.0 / COUNT(*), 2) AS pct_long_queue,
  ROUND(SUM(has_missing_pouch) * 100.0 / COUNT(*), 2) AS pct_missing_pouch,
  ROUND(SUM(has_critical_force_complete) * 100.0 / COUNT(*), 2) AS pct_critical_force
FROM `imperfect_kitchen_items`
WHERE order_assigned_to_pod_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
  AND order_status = 'COMPLETED'
GROUP BY 1
HAVING COUNT(*) >= 100
ORDER BY pct_imperfect DESC;
```

### Stakeholder Use Cases

**For Product/KDS:**
- Filter by `has_kds_remake`, `has_reset` → KDS instruction clarity issues
- Filter by `has_missing_signal` → KDS timer/tracking issues
- Analyze `has_bad_interaction`, `has_out_of_sync_sequencer_hh_alm` → Sequencer logic bugs
- Track `has_trickling_violation` → FIFO sequencing issues

**For Ops:**
- `has_long_queue`, `has_long_pending_packaging` → Kitchen flow bottlenecks
- `has_bump`, `has_kds_remake` → Staff training needs
- `has_missing_pouch`, `has_surprise_pouch` → Hot hold inventory compliance
- `has_critical_force_complete` → Process discipline issues
- `count_of_line_skippers` → Priority management issues

**For Culinary:**
- `has_longer_than_expected_production_time` by menu item → Recipe optimization
- `has_shorter_than_expected_production_time` → Recipe timing updates needed

---

## Vending Items & Expo Wait Time Analysis

### Vending Item Sequencing Logic

Vending items are simple retrieve-and-pack items routed to a vending pod near expo. The sequencer **intentionally holds vending items** to avoid early parking spot occupation.

**Sequencing Rules (in order):**
1. **Vending-only order?** → Release all vending items immediately
2. **Has ambient kitchen items?** → Wait until ANY ambient item reaches `pending_packaging`
3. **Has only hot kitchen items?** → Wait until ALL hot items are `focused`

### Why This Matters for Expo Wait Time

The KPI `order_level_expo_wait_time` measures: **first item pending_pack → last item triggers pending_bagging**

**Noise Sources:**
- Vending items completing fast but held by sequencer (expected behavior)
- Vending items force-completed with null focus time (potential data/process issue)
- Vending items dropping BEFORE kitchen items (sequencer failure)

### Vending Item Diagnostic Framework

| Scenario | Definition | Is It a Problem? |
|----------|------------|------------------|
| **Late Drop** | `vending_focus_time > first_kitchen_pending_pack` | ❌ No - EXPECTED behavior |
| **Early Drop** | `vending_focus_time < first_kitchen_pending_pack` | ⚠️ Yes - Causes early parking spot use |
| **Force Complete** | `vending_focus_time IS NULL` | ⚠️ Investigate - Could be intentional hold or error |
| **Very Late Drop** | `vending_focus_time > first_pending_pack + 2 min` | ⚠️ Maybe - Sequencer may be holding too long |

### Query: Vending Item Expo Analysis

```sql
-- Vending Item Expo Wait Analysis by HDR
WITH order_first_pending_pack AS (
  SELECT
    order_id,
    hdr_id,
    MIN(pending_package_time) AS first_item_pending_pack_time
  FROM `wonder-dw-prod-brd.orders.hdr_kitchen_order_item`
  WHERE order_status = 'COMPLETED'
    AND pending_package_time IS NOT NULL
    AND DATE(order_assigned_to_pod_time) >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
  GROUP BY 1, 2
),

vending_analysis AS (
  SELECT
    o.order_id,
    o.hdr_id,
    o.first_item_pending_pack_time,
    v.focus_time AS vending_focus_time,
    v.type AS vending_type,
    v.menu_item_name,
    -- Scenario Classification
    CASE WHEN v.focus_time IS NULL THEN 'FORCE_COMPLETE'
         WHEN v.focus_time < o.first_item_pending_pack_time THEN 'EARLY_DROP'
         WHEN v.focus_time > o.first_item_pending_pack_time THEN 'LATE_DROP'
         ELSE 'ON_TIME'
    END AS vending_scenario,
    -- Timing (minutes)
    CASE 
      WHEN v.focus_time IS NOT NULL AND o.first_item_pending_pack_time IS NOT NULL
      THEN TIMESTAMP_DIFF(v.focus_time, o.first_item_pending_pack_time, SECOND) / 60.0
      ELSE NULL
    END AS vending_vs_first_pending_mins
  FROM order_first_pending_pack o
  JOIN `wonder-dw-prod-brd.orders.hdr_kitchen_vending_tasks` v 
    ON o.order_id = v.order_id AND o.hdr_id = v.hdr_id
  WHERE v.status = 'COMPLETED'
    AND DATE(v.order_placed_time) >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
)

SELECT
  h.hdr_name,
  COUNT(DISTINCT va.order_id) AS orders_with_vending,
  COUNT(*) AS vending_items,
  -- Scenario breakdown
  ROUND(SUM(CASE WHEN vending_scenario = 'FORCE_COMPLETE' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS pct_force_complete,
  ROUND(SUM(CASE WHEN vending_scenario = 'EARLY_DROP' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS pct_early_drop,
  ROUND(SUM(CASE WHEN vending_scenario = 'LATE_DROP' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS pct_late_drop,
  -- Early drop timing (the problematic ones)
  ROUND(AVG(CASE WHEN vending_scenario = 'EARLY_DROP' THEN ABS(vending_vs_first_pending_mins) END), 2) AS avg_early_drop_mins,
  -- Late drop timing (expected behavior)
  ROUND(AVG(CASE WHEN vending_scenario = 'LATE_DROP' THEN vending_vs_first_pending_mins END), 2) AS avg_late_drop_mins
FROM vending_analysis va
JOIN `wonder-dw-prod-brd.dw.dim_hdrs` h ON va.hdr_id = h.hdr_id
GROUP BY 1
HAVING COUNT(*) >= 200
ORDER BY pct_early_drop DESC;
```

### Key Tables for Vending Analysis

| Table | Purpose |
|-------|---------|
| `hdr_kitchen_vending_tasks` | Vending item status, focus_time, pending_packaging_time |
| `hdr_kitchen_order_item` | Kitchen item pending_package_time (for first item timestamp) |
| `hdr_kitchen_order_parking_spots` | Parking spot reservation times |
| `post_cook` (dbt model) | Combined view of kitchen + vending items with parking |

### Vending Task Fields

| Field | Type | Description |
|-------|------|-------------|
| `focus_time` | TIMESTAMP | When vending item was focused (NULL = force complete) |
| `pending_packaging_time` | DATETIME | When item reached pending packaging |
| `pending_bagging_time` | DATETIME | When item reached pending bagging |
| `holding_temperature` | STRING | `WARM` or `AMBIENT` |
| `status` | STRING | `COMPLETED`, etc. |
| `type` | STRING | Vending item type |

### Network Benchmark (Jan 2026)

| Metric | Value | Notes |
|--------|-------|-------|
| **Force complete rate** | ~29% | Some HDRs at 100% (Chelsea, Quakertown) |
| **Late drop rate** | ~48% | Expected behavior per sequencing logic |
| **Avg late drop delay** | 1.33 min | Vending held appropriately |
| **P75 late drop delay** | 0.95 min | Most drops are well-timed |

### Investigation Priorities

1. **High Force Complete HDRs** (>50%): Investigate if this is expected (vending-only orders) or data/process issue
2. **High Early Drop HDRs** (>20%): Sequencer may not be holding vending correctly → causes early parking spot use
3. **High Late Drop Delay** (avg >3 min): Sequencer may be holding vending too long → increases expo wait

---

## Imperfect Order & Fault Attribution Framework

### Order Accuracy Classification (L1-L4 Hierarchy)

The `imperfect_orders` model provides a structured hierarchy for accuracy issues:

| Level | Categories | RCA Question |
|-------|------------|--------------|
| **L1** | `HDR 4-Wall Accuracy` vs `Courier Ops Accuracy` | Who owns the problem? |
| **L2** | `Kitchen Accuracy` vs `Inventory Accuracy` | What type of problem? |
| **L3** | `Pod Accuracy` vs `Expo Accuracy` | Where in kitchen? |
| **L4** | Specific codes (see below) | Exact failure mode |

**L4 Codes:**

| L4 Code | L3 Category | L2 Category | Description |
|---------|-------------|-------------|-------------|
| `INCORRECT_CUSTOMIZATION` | Pod Accuracy | Kitchen Accuracy | Wrong modifications |
| `MISSING_INGREDIENT(S)` | Pod Accuracy | Kitchen Accuracy | Missing components |
| `MISSING_ITEM` | Expo Accuracy | Kitchen Accuracy | Item not in bag |
| `INCORRECT_ITEM_DELIVERED` | Expo Accuracy | Kitchen Accuracy | Wrong item |
| `UTENSILS` | Expo Accuracy | Kitchen Accuracy | Missing utensils |
| `OUT_OF_STOCK` | N/A | Inventory Accuracy | Menu item unavailable |
| `ORDER_NOT_DELIVERED` | N/A | N/A | Courier failure |
| `INCORRECT_ORDER` | N/A | N/A | Courier delivered wrong order |

### Fault Attribution Logic

**Three fault categories:**

| Fault Type | Definition | Owner |
|------------|------------|-------|
| `is_hdr_fault` | Kitchen late, handoff error, accuracy (not courier), or remake | Ops |
| `is_delivery_fault` | Courier response error, delivery duration error, courier accuracy | Logistics |
| `is_eta_fault` | Order arrived too early (>9 min early) | Algorithm |

**Combined `imperfect_order_type`:**
- `HDR` - Only HDR issues
- `DELIVERY` - Only courier issues  
- `ETA` - Only early arrival
- `HDR & DELIVERY` - Both contributed
- `HDR & DELIVERY & ETA` - All three

### ⚠️ Removing Arbitrary Thresholds

**Problem:** Fixed thresholds like `> 2.00 min` don't account for context.

**Better Approaches:**

#### 1. Statistical Thresholds (Percentile-Based)

```sql
-- Use HDR's own P75 as threshold instead of fixed value
WITH hdr_baselines AS (
  SELECT 
    hdr_id,
    APPROX_QUANTILES(kitchen_handoff_time_mins, 100)[OFFSET(75)] AS p75_handoff,
    APPROX_QUANTILES(courier_response_time_mins, 100)[OFFSET(75)] AS p75_courier
  FROM hdr_orders
  WHERE service_date_et >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
    AND order_status = 'COMPLETE'
  GROUP BY 1
)
-- Flag as error only if worse than HDR's own typical performance
SELECT 
  o.*,
  CASE WHEN o.kitchen_handoff_time_mins > b.p75_handoff THEN true ELSE false END AS handoff_error_dynamic
FROM orders o
JOIN hdr_baselines b ON o.hdr_id = b.hdr_id
```

#### 2. Context-Aware Thresholds

| Context | Courier Response Threshold | Handoff Threshold |
|---------|---------------------------|-------------------|
| **Urban** | > 3 min | > 3 min |
| **Suburban** | > 5 min | > 4 min |
| **Peak Hour** | > 4 min | > 5 min |
| **Multi-Restaurant Order** | > 5 min | > 6 min |

#### 3. Z-Score Based (Standard Deviations)

```sql
-- Flag as error if > 2 standard deviations from HDR's mean
, (kitchen_handoff_time_mins - b.avg_handoff) / NULLIF(b.stddev_handoff, 0) AS handoff_z_score
, CASE WHEN handoff_z_score > 2.0 THEN 'OUTLIER' ELSE 'NORMAL' END AS handoff_status
```

### Enhanced Fault Attribution (With Upstream Check)

**Always check if kitchen was already late before blaming downstream:**

```sql
-- Step 1: Classify upstream delay status
, CASE 
    WHEN ready_for_pickup_sla_difference > 5.0 THEN 'KITCHEN_PRIMARY_DELAY'
    WHEN ready_for_pickup_sla_difference > 2.0 THEN 'KITCHEN_CONTRIBUTING'
    ELSE 'KITCHEN_ON_TIME'
  END AS upstream_delay_status

-- Step 2: Enhanced HDR fault (only blame handoff if kitchen was on time)
, CASE 
    WHEN ready_for_pickup_sla_difference > 5.0 THEN true  -- Kitchen was primary delay
    WHEN remake_issue THEN true
    WHEN order_accuracy_issue AND NOT courier_ops_accuracy_issue THEN true
    WHEN ready_for_pickup_sla_difference <= 2.0 
         AND kitchen_handoff_time_mins > COALESCE(b.p75_handoff, 3.0) THEN true
    ELSE false
  END AS is_hdr_fault_validated

-- Step 3: Enhanced delivery fault (only blame courier if kitchen was on time)
, CASE 
    WHEN ready_for_pickup_sla_difference <= 2.0 
         AND courier_response_time_mins > COALESCE(b.p75_courier, 5.0) THEN true
    WHEN actual_delivery_duration_mins > estimated_delivery_duration_mins * 1.5 THEN true
    WHEN order_accuracy_issue AND courier_ops_accuracy_issue THEN true
    ELSE false
  END AS is_delivery_fault_validated
```

### Error Severity Classification

Instead of boolean flags, classify by magnitude:

| Severity | Handoff Time | Courier Response | Customer Impact |
|----------|--------------|------------------|-----------------|
| **SEVERE** | > 15 min | > 15 min | High concession likely |
| **MODERATE** | 8-15 min | 10-15 min | Some impact |
| **MINOR** | 3-8 min | 5-10 min | Minimal impact |
| **OK** | ≤ 3 min | ≤ 5 min | No issue |

---

## Capacity Analysis Framework

### Why Capacity Matters

Before blaming a location for poor OTR, verify if they were operating above capacity. A location with insurmountable order volume needs capacity solutions, not operational coaching.

### Design Type Capacity Benchmarks

| Design Type | HDR Count | Avg Peak Orders/Hour | Avg Late Rate | Notes |
|-------------|-----------|---------------------|---------------|-------|
| **D5** | 8 | 15.9 | 5.0% | High capacity, best performance |
| **D4** | 14 | 8.7 | 6.4% | Medium-high capacity |
| **D3** | 66 | 9.2 | 10.1% | Standard, majority of network |
| **D2** | 2 | 4.9 | 15.0% | Lower capacity |
| **D1** | 3 | 2.4 | 6.8% | Smallest footprint |

### Volume Classification

```sql
-- Calculate volume z-score vs network
WITH network_avg AS (
  SELECT 
    AVG(peak_orders_per_hour) AS avg_peak,
    STDDEV(peak_orders_per_hour) AS stddev_peak
  FROM location_metrics
)
SELECT
  hdr_name,
  peak_orders_per_hour,
  (peak_orders_per_hour - avg_peak) / NULLIF(stddev_peak, 0) AS volume_z_score,
  CASE 
    WHEN volume_z_score > 1.0 THEN 'HIGH_VOLUME'
    WHEN volume_z_score < -1.0 THEN 'LOW_VOLUME'
    ELSE 'NORMAL'
  END AS volume_tier
```

### Capacity vs Performance Matrix

| Volume Tier | Late Rate | Diagnosis | Action |
|-------------|-----------|-----------|--------|
| **HIGH_VOLUME** | High | Capacity constraint | Add capacity, extend hours, limit orders |
| **HIGH_VOLUME** | Low | Handling well | Monitor, share best practices |
| **NORMAL** | High | Operational issue | Training, process improvement |
| **NORMAL** | Low | On track | Maintain |
| **LOW_VOLUME** | High | Serious ops issue | Deep dive - no volume excuse |

### Key Capacity Metrics

| Metric | Calculation | What It Shows |
|--------|-------------|---------------|
| `peak_orders_per_hour` | Peak orders / (7 days × 3 peak hours) | True peak load |
| `volume_z_score` | (HDR peak - network avg) / stddev | Relative volume pressure |
| `orders_above_design` | orders - design_capacity | Over/under capacity |
| `queue_mins_at_peak` | Avg queue during 5-8 PM | Capacity stress indicator |

### Capacity Query for WBR

```sql
WITH location_metrics AS (
  SELECT 
    h.hdr_name,
    h.design_type,
    h.hdr_class,
    h.population_type,
    COUNT(DISTINCT o.order_id) AS total_orders,
    COUNT(DISTINCT CASE 
      WHEN EXTRACT(HOUR FROM DATETIME(o.order_placed_date_utc, 'America/New_York')) BETWEEN 17 AND 20 
      THEN o.order_id 
    END) / 7.0 / 3.0 AS peak_orders_per_hour,
    COUNT(DISTINCT CASE WHEN ot.on_time_issue AND ot.otr_sla_tier LIKE '%LATE' THEN o.order_id END) AS late_orders,
    AVG(o.ready_for_pickup_sla_difference) AS avg_kitchen_delay,
    AVG(o.actual_queue_mins) AS avg_queue_mins
  FROM hdr_orders o
  JOIN dim_hdrs h ON o.hdr_id = h.hdr_id
  LEFT JOIN hdr_on_time_orders ot ON o.order_id = ot.order_id
  WHERE o.order_status = 'COMPLETE'
    AND o.dining_option = 'DELIVERY'
    AND o.service_date_et >= DATE_TRUNC(DATE_SUB(CURRENT_DATE(), INTERVAL 1 WEEK), WEEK(MONDAY))
  GROUP BY 1, 2, 3, 4
),
network_avg AS (
  SELECT AVG(peak_orders_per_hour) AS avg_peak, STDDEV(peak_orders_per_hour) AS stddev_peak
  FROM location_metrics
)
SELECT
  lm.*,
  ROUND((lm.peak_orders_per_hour - na.avg_peak) / NULLIF(na.stddev_peak, 0), 1) AS volume_z_score,
  CASE 
    WHEN (lm.peak_orders_per_hour - na.avg_peak) / NULLIF(na.stddev_peak, 0) > 1.0 THEN 'HIGH_VOLUME'
    WHEN (lm.peak_orders_per_hour - na.avg_peak) / NULLIF(na.stddev_peak, 0) < -1.0 THEN 'LOW_VOLUME'
    ELSE 'NORMAL'
  END AS volume_tier,
  ROUND(lm.late_orders * 100.0 / lm.total_orders, 1) AS late_rate
FROM location_metrics lm
CROSS JOIN network_avg na
WHERE lm.late_orders >= 20
ORDER BY late_orders DESC;
```

---

## Imperfect Order Reason Codes (For Field Managers)

### Purpose

Provide RGMs and field managers with clear, prioritized reason codes to understand opportunities to improve kitchen execution and observe patterns over time.

### Reason Code Hierarchy (Priority Order)

**Order Accuracy issues SUPERSEDE any timing issues.**

For timing issues, prioritize by sequence in the kitchen:

| Priority | Reason Code | Definition | Threshold | Owner |
|----------|-------------|------------|-----------|-------|
| **1** | `ACCURACY_POD` | Incorrect customization or missing ingredient | Any accuracy issue flagged | Pod Team |
| **2** | `ACCURACY_EXPO` | Missing item, incorrect item, utensils | Any expo accuracy issue | Expo Team |
| **3** | `ACCURACY_COURIER` | Order not delivered, incorrect order | Courier accuracy issue | Logistics |
| **4** | `EARLY_ORDER` | Order completed/delivered >9 min early | delivery_sla_diff < -9 | ETA Algorithm |
| **5** | `LATE_QUEUE` | Item sat in queue too long | queue_mins > 5 | Sequencing |
| **6** | `LATE_DELAYED_START` | Item focused on screen but not started | TBD - needs KDS data | Line Lead |
| **7** | `LATE_COOK` | Cook time exceeded expected | cook_error < -3 | Line Cook |
| **8** | `LATE_EXPO` | Slow bagging/expo after cook complete | packaging_bagging > 5 | Expo Team |
| **9** | `LATE_PICKUP` | Ready on time, but late pickup | kitchen on-time, handoff > 8 | Expo/Logistics |
| **10** | `LATE_DELIVERY` | Picked up on time, slow transit | transit_error < -5 | Courier |
| **11** | `LATE_OTHER` | Late but no single bottleneck identified | Catch-all | Multi-team |

### Reason Code Assignment Query

```sql
-- Assign single primary reason code per order (highest priority wins)
SELECT
  order_id,
  hdr_name,
  service_date_et,
  
  -- Assign reason code by priority
  CASE
    -- Priority 1-3: Accuracy issues (supersede timing)
    WHEN order_accuracy_issue AND l3_order_accuracy = 'Pod Accuracy' 
      THEN 'ACCURACY_POD'
    WHEN order_accuracy_issue AND l3_order_accuracy = 'Expo Accuracy' 
      THEN 'ACCURACY_EXPO'
    WHEN order_accuracy_issue AND courier_ops_accuracy_issue 
      THEN 'ACCURACY_COURIER'
    
    -- Priority 4: Early (ETA issue)
    WHEN delivery_sla_difference < -9.0 
      THEN 'EARLY_ORDER'
    
    -- Priority 5-8: Kitchen timing issues (by sequence)
    WHEN actual_queue_mins > 5.0 
      THEN 'LATE_QUEUE'
    WHEN cook_error < -3.0 
      THEN 'LATE_COOK'
    WHEN actual_packaging_bagging_mins > 5.0 
      THEN 'LATE_EXPO'
    
    -- Priority 9-10: Post-kitchen issues
    WHEN ready_for_pickup_sla_difference <= 2.0 AND kitchen_handoff_time_mins > 8.0 
      THEN 'LATE_PICKUP'
    WHEN ready_for_pickup_sla_difference <= 2.0 AND transit_error < -5.0 
      THEN 'LATE_DELIVERY'
    
    -- Priority 11: Catch-all
    WHEN on_time_issue 
      THEN 'LATE_OTHER'
    
    ELSE 'ON_TIME'
  END AS primary_reason_code,
  
  -- Supporting metrics for context
  actual_queue_mins,
  cook_error,
  actual_packaging_bagging_mins,
  ready_for_pickup_sla_difference,
  kitchen_handoff_time_mins,
  courier_response_time_mins,
  transit_error

FROM order_analysis
WHERE imperfect_order = TRUE
```

### Reason Code Distribution Query (For WBR)

```sql
-- Weekly reason code distribution by HDR
SELECT
  FORMAT_DATE('%F', DATE_TRUNC(service_date_et, WEEK(MONDAY))) AS service_week,
  hdr_name,
  primary_reason_code,
  COUNT(*) AS order_count,
  ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(PARTITION BY hdr_name), 1) AS pct_of_imperfect
FROM order_analysis
WHERE imperfect_order = TRUE
  AND service_date_et >= DATE_SUB(CURRENT_DATE(), INTERVAL 4 WEEK)
GROUP BY 1, 2, 3
ORDER BY 2, 1 DESC, order_count DESC
```

### Reason Code Summary for Leadership

```
┌─────────────────────────────────────────────────────────────────┐
│                    IMPERFECT ORDER BREAKDOWN                     │
├─────────────────────────────────────────────────────────────────┤
│ ACCURACY ISSUES (Fix First - Customer Impact)                   │
│   ACCURACY_POD:     X orders (Y%) - Wrong customization         │
│   ACCURACY_EXPO:    X orders (Y%) - Missing/wrong items         │
│   ACCURACY_COURIER: X orders (Y%) - Courier delivery error      │
├─────────────────────────────────────────────────────────────────┤
│ TIMING - KITCHEN SEQUENCE                                       │
│   LATE_QUEUE:       X orders (Y%) - Item stuck in queue >5m     │
│   LATE_COOK:        X orders (Y%) - Cook time exceeded target   │
│   LATE_EXPO:        X orders (Y%) - Slow bagging after cook     │
├─────────────────────────────────────────────────────────────────┤
│ TIMING - POST-KITCHEN                                           │
│   LATE_PICKUP:      X orders (Y%) - Ready on time, slow pickup  │
│   LATE_DELIVERY:    X orders (Y%) - Picked up OK, slow transit  │
├─────────────────────────────────────────────────────────────────┤
│ ETA ALGORITHM                                                   │
│   EARLY_ORDER:      X orders (Y%) - Delivered too early         │
└─────────────────────────────────────────────────────────────────┘
```

### Threshold Recommendations

| Reason Code | Suggested Threshold | Rationale |
|-------------|---------------------|-----------|
| `LATE_QUEUE` | > 5 min | Standard queue target |
| `LATE_DELAYED_START` | > 2 min focused before start | TBD with KDS team |
| `LATE_COOK` | > 3 min over expected | Allow buffer for complexity |
| `LATE_EXPO` | > 5 min bagging time | 5 min is reasonable for bagging |
| `LATE_PICKUP` | > 8 min handoff when kitchen on-time | Validated from data |
| `LATE_DELIVERY` | > 5 min over transit estimate | Standard transit buffer |
| `EARLY_ORDER` | > 9 min early | Current OTR definition |

---

## Early Order RCA Framework

### Why Orders Arrive Early

Early orders (>9 min early) are caused by **ETA over-estimation** - the algorithm predicted longer times than reality. This is an ETA/Algorithm issue, not an operations issue.

### Early Order Breakdown (Network)

| Primary Over-Estimate | % of Earlies | Avg Cook Error | Avg Transit Error |
|-----------------------|--------------|----------------|-------------------|
| **COOK_PREDICTION** | 48.3% | +6.3 min | +1.8 min |
| **TRANSIT_PREDICTION** | 24.6% | +2.0 min | +4.8 min |
| **QUEUE_PREDICTION** | 17.8% | +0.7 min | +1.6 min |
| **SIT_PREDICTION** | 9.3% | +1.6 min | +2.4 min |

**Key Finding:** ~48% of early orders are due to **cook time over-estimation**.

### Early Order RCA Query

```sql
WITH early_orders AS (
  SELECT 
    o.order_id,
    h.hdr_name,
    o.delivery_sla_difference,
    o.queue_error,
    o.cook_error,
    o.pickup_error,
    o.transit_error,
    -- Determine primary over-estimate (which component was most off)
    CASE 
      WHEN ABS(o.cook_error) >= GREATEST(ABS(o.queue_error), ABS(o.pickup_error), ABS(o.transit_error)) 
        THEN 'COOK_PREDICTION'
      WHEN ABS(o.transit_error) >= GREATEST(ABS(o.queue_error), ABS(o.pickup_error)) 
        THEN 'TRANSIT_PREDICTION'
      WHEN ABS(o.pickup_error) >= ABS(o.queue_error) 
        THEN 'SIT_PREDICTION'
      ELSE 'QUEUE_PREDICTION'
    END AS primary_over_estimate
  FROM hdr_orders o
  JOIN dim_hdrs h ON o.hdr_id = h.hdr_id
  WHERE o.delivery_sla_difference < -9.0  -- Early orders
    AND o.order_status = 'COMPLETE'
)
SELECT
  hdr_name,
  COUNT(*) AS early_orders,
  ROUND(AVG(delivery_sla_difference), 1) AS avg_early_mins,
  ROUND(AVG(cook_error), 1) AS cook_over_est,
  ROUND(AVG(transit_error), 1) AS transit_over_est,
  ROUND(AVG(queue_error), 1) AS queue_over_est,
  CASE 
    WHEN AVG(cook_error) > GREATEST(AVG(transit_error), AVG(queue_error)) THEN 'COOK'
    WHEN AVG(transit_error) > AVG(queue_error) THEN 'TRANSIT'
    ELSE 'QUEUE'
  END AS primary_driver
FROM early_orders
GROUP BY 1
ORDER BY early_orders DESC;
```

### Early Order Actions by Root Cause

| Primary Driver | Meaning | Action |
|----------------|---------|--------|
| **COOK** | Cook time prediction too high | Retrain ML model for this HDR's menu mix |
| **TRANSIT** | Transit prediction too high | Update routing/traffic models for area |
| **QUEUE** | Queue prediction too high | Adjust demand forecasting |
| **SIT** | Pickup time prediction too high | Improve driver dispatch timing |

---

## Advanced Percentile Metrics

For deeper analysis, use P50 (median) and P90 percentiles instead of just averages:

### Percentile Calculations in BigQuery

```sql
-- Median (P50) and P90 for handoff and courier response
SELECT
  hdr_name,
  COUNT(DISTINCT order_id) AS orders,
  
  -- Averages
  ROUND(AVG(kitchen_handoff_time_mins), 1) AS avg_handoff,
  ROUND(AVG(courier_response_time_mins), 1) AS avg_courier_resp,
  
  -- Medians (P50)
  ROUND(APPROX_QUANTILES(kitchen_handoff_time_mins, 100)[OFFSET(50)], 1) AS p50_handoff,
  ROUND(APPROX_QUANTILES(courier_response_time_mins, 100)[OFFSET(50)], 1) AS p50_courier_resp,
  
  -- P90 (90th percentile - worst 10%)
  ROUND(APPROX_QUANTILES(kitchen_handoff_time_mins, 100)[OFFSET(90)], 1) AS p90_handoff,
  ROUND(APPROX_QUANTILES(courier_response_time_mins, 100)[OFFSET(90)], 1) AS p90_courier_resp,
  
  -- Sit time components
  ROUND(AVG(actual_pickup_waiting_duration_mins), 1) AS avg_sit_time,
  ROUND(APPROX_QUANTILES(actual_pickup_waiting_duration_mins, 100)[OFFSET(90)], 1) AS p90_sit_time
  
FROM hdr_orders o
JOIN dim_hdrs h ON o.hdr_id = h.hdr_id
WHERE o.dining_option = 'DELIVERY'
  AND o.order_status = 'COMPLETE'
GROUP BY 1;
```

### Why Percentiles Matter

| Metric | Avg | P50 | P90 | Interpretation |
|--------|-----|-----|-----|----------------|
| Handoff | 5.2 | 3.1 | 12.8 | Most orders OK, but tail is bad |
| Handoff | 5.2 | 5.0 | 6.5 | Consistent performance |
| Handoff | 5.2 | 2.0 | 18.0 | Bimodal - some very good, some very bad |

- **P50 << Avg**: A few outliers are pulling up the average
- **P90 >> Avg**: Worst 10% are significantly worse than typical
- **P50 ≈ Avg ≈ P90**: Consistent (good or bad) performance

### Error Fields Explained

All error fields are in **minutes**. **Sign Convention: Positive = early/fast, Negative = late/slow**

| Field | Definition | Component |
|-------|------------|-----------|
| `queue_error` | Predicted vs actual queue time | Kitchen |
| `cook_error` | Predicted vs actual cook time | Kitchen |
| `packaging_bagging_error` | Predicted vs actual bag time | Kitchen |
| `queue_cook_error` | Combined queue + cook error | Kitchen |
| `pickup_error` | Time from ready → courier pickup | Handoff |
| `transit_error` | Predicted vs actual transit time | Logistics |
| `dropoff_error` | Predicted vs actual dropoff time | Logistics |
| `delivery_error` | Combined logistics error | Logistics |
| `total_eta_error` | End-to-end prediction error | System |
| `total_absolute_eta_error` | Absolute value of total error | System |

### Key Timing Fields in `hdr_orders`

**Actual Timing (what happened):**

| Field | Definition |
|-------|------------|
| `ticket_time_mins` | Total kitchen execution time (order placed → ready) |
| `actual_o2e_mins` | Actual order-to-eat time |
| `actual_queue_mins` | Time in queue before cooking |
| `actual_cook_duration_mins` | Time spent cooking |
| `actual_packaging_bagging_mins` | Time spent bagging (full) |
| `actual_packaging_mins` | Packing only (cooking_finish → pending_bagging) |
| `actual_pickup_waiting_duration_mins` | Sit time (ready → pickup complete) |
| `courier_response_time_mins` | Ready → Driver Arrival |
| `kitchen_handoff_time_mins` | Driver Arrival → Pickup Complete |
| `actual_transit_mins` | Pickup → Near Destination |
| `actual_delivery_duration_mins` | Pickup → Customer |

**Estimated Timing (what we predicted):**

| Field | Definition |
|-------|------------|
| `estimated_o2e_mins` | Predicted O2E at order time |
| `estimated_queue_mins` | Predicted queue time |
| `estimated_cook_duration_mins` | Predicted cook time |
| `estimated_packaging_bagging_mins` | Predicted bagging time |
| `estimated_pickup_waiting_duration_mins` | Predicted sit time |
| `estimated_transit_mins` | Predicted transit time |
| `estimated_delivery_duration_mins` | Predicted delivery duration |

**Derived Metrics:**

```sql
-- Make Time: cooking_start → ready_for_pickup (excludes queue)
actual_make_time_mins = actual_cook_duration_mins + actual_packaging_bagging_mins

-- Bagging-only duration
actual_bagging_mins = actual_packaging_bagging_mins - actual_packaging_mins
```

### HDR Classification Dimensions

Orders can be analyzed by HDR attributes from `dim_hdrs`:

- **HDR Class**: `2023`, `2024`, `2025`, `2025 New`, `2026 New` (year opened + maturity)
- **Population Type**: `Urban`, `Suburban`, `Big Box`

NSO (New Store Openings) typically refers to `2025 New` or `2026 New` classes.

### Key OTR Table Fields

**From `hdr_on_time_orders`:**
- `on_time_issue` - BOOLEAN: TRUE if order had any timing issue
- `kitchen_on_time_issue` - BOOLEAN: TRUE if kitchen caused the issue
- `delivery_on_time_issue` - BOOLEAN: TRUE if delivery caused the issue
- `otr_sla_tier` - STRING: The timing bucket category
- `delivery_sla_difference` - FLOAT: Minutes from promised delivery time
- `ready_for_pickup_sla_difference` - FLOAT: Minutes from promised ready time

**From `hdr_orders`:**
- All error fields listed above
- `queue_cook_error` - Combined queue + cook error
- `actual_o2e_mins` - Actual order-to-eat time
- `estimated_o2e_mins` - Predicted O2E at order time

**From `imperfect_orders`:**
- `on_time_issue` - BOOLEAN: Timing issue flag
- `on_time_issue_excludes_earlies` - BOOLEAN: Late-only timing issue
- `order_accuracy_issue` - BOOLEAN: Non-timing imperfection

### Error Metric Types

For each error field, track THREE metrics for complete analysis:

| Metric Type | SQL | Purpose |
|-------------|-----|---------|
| **Average (signed)** | `AVG(cook_error)` | Direction of bias (early vs late) |
| **Average Absolute** | `AVG(ABS(cook_error))` | Magnitude regardless of direction |
| **Standard Deviation** | `STDDEV_POP(cook_error)` | Variability/consistency |

**Example:** Avg cook error = +0.5 mins looks good, but STDDEV = 4.0 mins reveals high variability.

### Expo Wait Time & Tile Data

**IMPORTANT:** Expo Wait Time comes from a separate "tile" data source, not standard hdr_orders tables.

Key metrics from tile data:
- **Avg Order Level Expo Wait Time** - Time orders sit at expo window
- **Expo Wait Time Tiers** - Bucketed expo performance
- **Average Ticket Time** - Total ticket completion time
- **Is MRO** - Multi-Restaurant Order flag
- **Delayed Order Flag** - Boolean delay indicator
- **Kitchen Complexity** - Order/kitchen variance metrics
- **Quality Scores** - Portion, Taste, Temperature ratings

**Note:** The exact BigQuery table for this tile data needs to be identified. Current analysis uses CSV exports from Looker.

---

## Query Patterns

### Network OTR Summary (WBR Style)

```sql
-- Weekly network OTR summary with channel breakdown
WITH weekly_metrics AS (
  SELECT
    FORMAT_DATE('%F', DATE_TRUNC(o.service_date_et, WEEK(MONDAY))) AS service_week,
    o.dining_option,
    COUNT(DISTINCT o.order_id) AS completed_orders,
    COUNT(DISTINCT CASE WHEN ot.on_time_issue THEN ot.order_id END) AS orders_with_issues,
    1 - SAFE_DIVIDE(
      COUNT(DISTINCT CASE WHEN ot.on_time_issue THEN ot.order_id END),
      COUNT(DISTINCT ot.order_id)
    ) AS otr_rate,
    1 - SAFE_DIVIDE(
      COUNT(DISTINCT CASE WHEN ot.on_time_issue AND ot.otr_sla_tier NOT LIKE '%EARLY' THEN ot.order_id END),
      COUNT(DISTINCT ot.order_id)
    ) AS otr_rate_no_earlies
  FROM `wonder-dw-prod-brd.orders.hdr_orders` o
  LEFT JOIN `wonder-dw-prod-brd.orders.hdr_on_time_orders` ot
    ON o.order_id = ot.order_id
  WHERE o.order_status = 'COMPLETE'
    AND o.brand_category = 'WONDER_HDR'
    AND o.service_date_et >= DATE_SUB(CURRENT_DATE('America/New_York'), INTERVAL 12 WEEK)
  GROUP BY 1, 2
)
SELECT
  service_week,
  SUM(completed_orders) AS total_orders,
  SUM(CASE WHEN dining_option = 'PICKUP' THEN completed_orders END) AS pickup_orders,
  SUM(CASE WHEN dining_option = 'DELIVERY' THEN completed_orders END) AS delivery_orders,
  SAFE_DIVIDE(
    SUM(completed_orders * otr_rate),
    SUM(completed_orders)
  ) AS network_otr,
  SAFE_DIVIDE(
    SUM(CASE WHEN dining_option = 'PICKUP' THEN completed_orders * otr_rate END),
    SUM(CASE WHEN dining_option = 'PICKUP' THEN completed_orders END)
  ) AS pickup_otr,
  SAFE_DIVIDE(
    SUM(CASE WHEN dining_option = 'DELIVERY' THEN completed_orders * otr_rate END),
    SUM(CASE WHEN dining_option = 'DELIVERY' THEN completed_orders END)
  ) AS delivery_otr
FROM weekly_metrics
GROUP BY service_week
ORDER BY service_week DESC;
```

### SLA Tier Distribution

```sql
-- Calculate percentage of orders in each SLA tier
SELECT
  FORMAT_DATE('%F', DATE_TRUNC(o.service_date_et, WEEK(MONDAY))) AS service_week,
  o.dining_option,
  COUNT(DISTINCT o.order_id) AS total_orders,
  SAFE_DIVIDE(COUNT(DISTINCT CASE WHEN ot.otr_sla_tier = '9+_EARLY' THEN o.order_id END), COUNT(DISTINCT o.order_id)) AS pct_9_plus_early,
  SAFE_DIVIDE(COUNT(DISTINCT CASE WHEN ot.otr_sla_tier = '8_5_EARLY' THEN o.order_id END), COUNT(DISTINCT o.order_id)) AS pct_8_5_early,
  SAFE_DIVIDE(COUNT(DISTINCT CASE WHEN ot.otr_sla_tier = '4_1_EARLY' THEN o.order_id END), COUNT(DISTINCT o.order_id)) AS pct_4_1_early,
  SAFE_DIVIDE(COUNT(DISTINCT CASE WHEN ot.otr_sla_tier = 'ON_TIME' THEN o.order_id END), COUNT(DISTINCT o.order_id)) AS pct_on_time,
  SAFE_DIVIDE(COUNT(DISTINCT CASE WHEN ot.otr_sla_tier = '1_4_LATE' THEN o.order_id END), COUNT(DISTINCT o.order_id)) AS pct_1_4_late,
  SAFE_DIVIDE(COUNT(DISTINCT CASE WHEN ot.otr_sla_tier = '5_15_LATE' THEN o.order_id END), COUNT(DISTINCT o.order_id)) AS pct_5_15_late,
  SAFE_DIVIDE(COUNT(DISTINCT CASE WHEN ot.otr_sla_tier = '16_30_LATE' THEN o.order_id END), COUNT(DISTINCT o.order_id)) AS pct_16_30_late,
  SAFE_DIVIDE(COUNT(DISTINCT CASE WHEN ot.otr_sla_tier = '31+_LATE' THEN o.order_id END), COUNT(DISTINCT o.order_id)) AS pct_31_plus_late
FROM `wonder-dw-prod-brd.orders.hdr_orders` o
LEFT JOIN `wonder-dw-prod-brd.orders.hdr_on_time_orders` ot
  ON o.order_id = ot.order_id
WHERE o.order_status = 'COMPLETE'
  AND o.brand_category = 'WONDER_HDR'
  AND o.service_date_et >= DATE_SUB(CURRENT_DATE('America/New_York'), INTERVAL 4 WEEK)
GROUP BY 1, 2
ORDER BY 1 DESC, 2;
```

### Kitchen Handoff Scenario Analysis (Delivery)

```sql
-- Analyze delivery OTR by kitchen handoff scenario
SELECT
  FORMAT_DATE('%F', DATE_TRUNC(o.service_date_et, WEEK(MONDAY))) AS service_week,
  CASE
    WHEN o.dining_option != 'DELIVERY' THEN 'N/A (Pickup Order)'
    WHEN o.cook_error < 0 AND o.pickup_error > 0 THEN 'A. Kitchen LATE, Courier Waits'
    WHEN o.cook_error > 0 AND o.pickup_error < 0 THEN 'B. Kitchen FAST, Food Waits (Risk)'
    WHEN o.cook_error < 0 AND o.pickup_error < 0 THEN 'C. Compounding Failure (Both LATE)'
    WHEN o.cook_error > 0 AND o.pickup_error > 0 THEN 'D. Ideal State (Kitchen Fast, Handoff Fast)'
    ELSE 'E. Other (e.g., one error is zero)'
  END AS kitchen_handoff_scenario,
  COUNT(DISTINCT o.order_id) AS order_volume,
  1 - SAFE_DIVIDE(
    COUNT(DISTINCT CASE WHEN ot.on_time_issue THEN ot.order_id END),
    COUNT(DISTINCT ot.order_id)
  ) AS otr_rate,
  ROUND(AVG(o.pickup_error), 2) AS avg_sit_error_mins,
  ROUND(AVG(o.cook_error), 2) AS avg_cook_error_mins
FROM `wonder-dw-prod-brd.orders.hdr_orders` o
LEFT JOIN `wonder-dw-prod-brd.orders.hdr_on_time_orders` ot
  ON o.order_id = ot.order_id
WHERE o.order_status = 'COMPLETE'
  AND o.brand_category = 'WONDER_HDR'
  AND o.dining_option = 'DELIVERY'
  AND o.service_date_et >= DATE_SUB(CURRENT_DATE('America/New_York'), INTERVAL 4 WEEK)
GROUP BY 1, 2
ORDER BY 1 DESC, order_volume DESC;
```

### Error Component Breakdown

```sql
-- Detailed error breakdown by HDR class
SELECT
  h.hdr_class,
  o.dining_option,
  COUNT(DISTINCT o.order_id) AS order_count,
  -- Queue & Cook (Kitchen)
  ROUND(AVG(ABS(o.queue_error)), 2) AS avg_abs_queue_error,
  ROUND(AVG(o.queue_error), 2) AS avg_queue_error,
  ROUND(AVG(ABS(o.cook_error)), 2) AS avg_abs_cook_error,
  ROUND(AVG(o.cook_error), 2) AS avg_cook_error,
  ROUND(AVG(ABS(o.packaging_bagging_error)), 2) AS avg_abs_pack_bag_error,
  -- Handoff & Delivery (Logistics)
  ROUND(AVG(ABS(o.pickup_error)), 2) AS avg_abs_sit_error,
  ROUND(AVG(o.pickup_error), 2) AS avg_sit_error,
  ROUND(AVG(ABS(o.transit_error)), 2) AS avg_abs_transit_error,
  ROUND(AVG(ABS(o.dropoff_error)), 2) AS avg_abs_dropoff_error,
  -- Total
  ROUND(AVG(o.total_absolute_eta_error), 2) AS avg_total_abs_error,
  ROUND(AVG(o.total_eta_error), 2) AS avg_total_error
FROM `wonder-dw-prod-brd.orders.hdr_orders` o
JOIN `wonder-dw-prod-brd.dw.dim_hdrs` h
  ON o.hdr_id = h.hdr_id
WHERE o.order_status = 'COMPLETE'
  AND o.brand_category = 'WONDER_HDR'
  AND o.service_date_et >= DATE_SUB(CURRENT_DATE('America/New_York'), INTERVAL 1 WEEK)
GROUP BY 1, 2
ORDER BY h.hdr_class, o.dining_option;
```

### NSO Performance Comparison

```sql
-- Compare NSO (2025 New, 2026 New) vs Mature HDRs
SELECT
  CASE 
    WHEN h.hdr_class IN ('2025 New', '2026 New') THEN 'NSO'
    ELSE 'Mature'
  END AS hdr_maturity,
  o.dining_option,
  COUNT(DISTINCT o.order_id) AS order_count,
  1 - SAFE_DIVIDE(
    COUNT(DISTINCT CASE WHEN ot.on_time_issue THEN ot.order_id END),
    COUNT(DISTINCT ot.order_id)
  ) AS otr_rate,
  ROUND(AVG(o.total_absolute_eta_error), 2) AS avg_total_abs_error,
  ROUND(AVG(ABS(o.cook_error)), 2) AS avg_abs_cook_error,
  ROUND(AVG(ABS(o.pickup_error)), 2) AS avg_abs_sit_error
FROM `wonder-dw-prod-brd.orders.hdr_orders` o
JOIN `wonder-dw-prod-brd.dw.dim_hdrs` h ON o.hdr_id = h.hdr_id
LEFT JOIN `wonder-dw-prod-brd.orders.hdr_on_time_orders` ot ON o.order_id = ot.order_id
WHERE o.order_status = 'COMPLETE'
  AND o.brand_category = 'WONDER_HDR'
  AND o.service_date_et >= DATE_SUB(CURRENT_DATE('America/New_York'), INTERVAL 1 WEEK)
GROUP BY 1, 2
ORDER BY 1, 2;
```

### HDR-Level OTR Ranking

```sql
-- Find worst performing HDRs by OTR
SELECT
  h.hdr_name,
  h.hdr_class,
  h.population_type,
  COUNT(DISTINCT o.order_id) AS order_count,
  1 - SAFE_DIVIDE(
    COUNT(DISTINCT CASE WHEN ot.on_time_issue THEN ot.order_id END),
    COUNT(DISTINCT ot.order_id)
  ) AS otr_rate,
  ROUND(AVG(o.cook_error), 2) AS avg_cook_error,
  ROUND(AVG(o.pickup_error), 2) AS avg_sit_error,
  ROUND(AVG(o.transit_error), 2) AS avg_transit_error
FROM `wonder-dw-prod-brd.orders.hdr_orders` o
JOIN `wonder-dw-prod-brd.dw.dim_hdrs` h ON o.hdr_id = h.hdr_id
LEFT JOIN `wonder-dw-prod-brd.orders.hdr_on_time_orders` ot ON o.order_id = ot.order_id
WHERE o.order_status = 'COMPLETE'
  AND o.brand_category = 'WONDER_HDR'
  AND o.dining_option = 'DELIVERY'
  AND o.service_date_et >= DATE_SUB(CURRENT_DATE('America/New_York'), INTERVAL 1 WEEK)
GROUP BY 1, 2, 3
HAVING order_count >= 50  -- Minimum volume for statistical relevance
ORDER BY otr_rate ASC
LIMIT 20;
```

### 1P vs 3P Channel Comparison

```sql
-- Compare 1P (Wonder direct) vs 3P (marketplace) OTR
SELECT
  CASE 
    WHEN o.order_channel IN ('APP', 'IN_PERSON', 'WEB') THEN '1P'
    ELSE '3P'
  END AS channel_type,
  o.dining_option,
  COUNT(DISTINCT o.order_id) AS order_count,
  1 - SAFE_DIVIDE(
    COUNT(DISTINCT CASE WHEN ot.on_time_issue THEN ot.order_id END),
    COUNT(DISTINCT ot.order_id)
  ) AS otr_rate,
  1 - SAFE_DIVIDE(
    COUNT(DISTINCT CASE WHEN ot.on_time_issue AND ot.otr_sla_tier NOT LIKE '%EARLY' THEN ot.order_id END),
    COUNT(DISTINCT ot.order_id)
  ) AS otr_rate_no_earlies
FROM `wonder-dw-prod-brd.orders.hdr_orders` o
LEFT JOIN `wonder-dw-prod-brd.orders.hdr_on_time_orders` ot ON o.order_id = ot.order_id
WHERE o.order_status = 'COMPLETE'
  AND o.brand_category = 'WONDER_HDR'
  AND o.service_date_et >= DATE_SUB(CURRENT_DATE('America/New_York'), INTERVAL 1 WEEK)
GROUP BY 1, 2
ORDER BY 1, 2;
```

### Complete Error Breakdown with Standard Deviations

```sql
-- Full WBR-style error breakdown with avg, absolute avg, and stddev
SELECT
  FORMAT_DATE('%F', DATE_TRUNC(o.service_date_et, WEEK(MONDAY))) AS service_week,
  o.dining_option,
  h.hdr_class,
  h.population_type,
  COUNT(DISTINCT o.order_id) AS order_count,
  -- Queue Error
  ROUND(AVG(ABS(o.queue_error)), 2) AS avg_abs_queue_error,
  ROUND(AVG(o.queue_error), 2) AS avg_queue_error,
  ROUND(STDDEV_POP(o.queue_error), 2) AS stddev_queue_error,
  -- Cook Error
  ROUND(AVG(ABS(o.cook_error)), 2) AS avg_abs_cook_error,
  ROUND(AVG(o.cook_error), 2) AS avg_cook_error,
  ROUND(STDDEV_POP(o.cook_error), 2) AS stddev_cook_error,
  -- Queue + Cook Combined
  ROUND(AVG(ABS(o.queue_cook_error)), 2) AS avg_abs_queue_cook_error,
  ROUND(AVG(o.queue_cook_error), 2) AS avg_queue_cook_error,
  -- Pack & Bag Error
  ROUND(AVG(ABS(o.packaging_bagging_error)), 2) AS avg_abs_pack_bag_error,
  ROUND(AVG(o.packaging_bagging_error), 2) AS avg_pack_bag_error,
  ROUND(STDDEV_POP(o.packaging_bagging_error), 2) AS stddev_pack_bag_error,
  -- Sit/Pickup Error (Delivery only)
  ROUND(AVG(ABS(o.pickup_error)), 2) AS avg_abs_sit_error,
  ROUND(AVG(o.pickup_error), 2) AS avg_sit_error,
  ROUND(STDDEV_POP(o.pickup_error), 2) AS stddev_sit_error,
  -- Transit Error
  ROUND(AVG(ABS(o.transit_error)), 2) AS avg_abs_transit_error,
  ROUND(AVG(o.transit_error), 2) AS avg_transit_error,
  ROUND(STDDEV_POP(o.transit_error), 2) AS stddev_transit_error,
  -- Dropoff Error
  ROUND(AVG(ABS(o.dropoff_error)), 2) AS avg_abs_dropoff_error,
  ROUND(AVG(o.dropoff_error), 2) AS avg_dropoff_error,
  ROUND(STDDEV_POP(o.dropoff_error), 2) AS stddev_dropoff_error,
  -- Delivery Error (combined)
  ROUND(AVG(ABS(o.delivery_error)), 2) AS avg_abs_delivery_error,
  ROUND(AVG(o.delivery_error), 2) AS avg_delivery_error,
  ROUND(STDDEV_POP(o.delivery_error), 2) AS stddev_delivery_error,
  -- Total ETA Error
  ROUND(AVG(o.total_absolute_eta_error), 2) AS avg_total_abs_eta_error,
  ROUND(AVG(o.total_eta_error), 2) AS avg_total_eta_error
FROM `wonder-dw-prod-brd.orders.hdr_orders` o
JOIN `wonder-dw-prod-brd.dw.dim_hdrs` h ON o.hdr_id = h.hdr_id
WHERE o.order_status = 'COMPLETE'
  AND o.brand_category = 'WONDER_HDR'
  AND o.service_date_et >= DATE_SUB(CURRENT_DATE('America/New_York'), INTERVAL 4 WEEK)
GROUP BY 1, 2, 3, 4
ORDER BY 1 DESC, 2, 3, 4;
```

### Location Spotlights: Courier vs Kitchen Failures (Sit Time Decomposition)

```sql
-- Identify HDRs failing due to kitchen vs logistics using sit time decomposition
-- Uses courier_response_time_mins and kitchen_handoff_time_mins
-- "Profile A" = Ops Failure (fast drivers, slow handoffs)
-- "Profile B" = Logistics Failure (fast handoffs, slow drivers)
SELECT
  h.hdr_name,
  h.hdr_class,
  h.population_type,
  COUNT(DISTINCT o.order_id) AS delivery_orders,
  1 - SAFE_DIVIDE(
    COUNT(DISTINCT CASE WHEN ot.on_time_issue THEN ot.order_id END),
    COUNT(DISTINCT ot.order_id)
  ) AS otr_rate,
  
  -- Sit Time Decomposition (the key diagnostic)
  ROUND(AVG(o.courier_response_time_mins), 2) AS avg_courier_response_mins,
  ROUND(AVG(o.kitchen_handoff_time_mins), 2) AS avg_kitchen_handoff_mins,
  
  -- Ops Gap: Positive = Ops slower, Negative = Logistics slower
  ROUND(AVG(COALESCE(o.kitchen_handoff_time_mins, 0) - COALESCE(o.courier_response_time_mins, 0)), 2) AS avg_ops_gap_mins,
  
  -- Kitchen metrics
  ROUND(AVG(o.ready_for_pickup_sla_difference), 2) AS avg_ready_sla_diff,
  ROUND(AVG(o.cook_error), 2) AS avg_cook_error,
  
  -- Profile Classification
  CASE
    WHEN AVG(COALESCE(o.courier_response_time_mins, 0)) <= 5.0 
     AND AVG(COALESCE(o.kitchen_handoff_time_mins, 0)) > 8.0 
      THEN 'Profile A: Ops Failure (Possible Fake Bump)'
    WHEN AVG(COALESCE(o.courier_response_time_mins, 0)) > 8.0 
     AND AVG(COALESCE(o.kitchen_handoff_time_mins, 0)) <= 5.0 
      THEN 'Profile B: Logistics Failure (Driver Shortage)'
    WHEN AVG(COALESCE(o.courier_response_time_mins, 0)) > 8.0 
     AND AVG(COALESCE(o.kitchen_handoff_time_mins, 0)) > 8.0 
      THEN 'Profile C: Both Failing'
    ELSE 'Profile D: Balanced/Ideal'
  END AS failure_profile
FROM `wonder-dw-prod-brd.orders.hdr_orders` o
JOIN `wonder-dw-prod-brd.dw.dim_hdrs` h ON o.hdr_id = h.hdr_id
LEFT JOIN `wonder-dw-prod-brd.orders.hdr_on_time_orders` ot ON o.order_id = ot.order_id
WHERE o.order_status = 'COMPLETE'
  AND o.brand_category = 'WONDER_HDR'
  AND o.dining_option = 'DELIVERY'
  AND o.order_channel IN ('APP', 'WEB', 'IN_PERSON')  -- 1P only
  AND o.service_date_et >= DATE_SUB(CURRENT_DATE('America/New_York'), INTERVAL 1 WEEK)
GROUP BY 1, 2, 3
HAVING delivery_orders >= 50
ORDER BY otr_rate ASC;
```

### Root Cause Attribution Query

```sql
-- Classify late orders by primary root cause
SELECT
  FORMAT_DATE('%F', DATE_TRUNC(o.service_date_et, WEEK(MONDAY))) AS service_week,
  h.hdr_class,
  
  -- Root Cause Classification
  CASE 
    WHEN ot.otr_sla_tier = 'ON_TIME' OR ot.otr_sla_tier LIKE '%EARLY' 
      THEN 'N/A - On Time/Early'
    -- Kitchen is the bottleneck
    WHEN o.ready_for_pickup_sla_difference > 5.0 
     AND COALESCE(o.kitchen_handoff_time_mins, 0) <= 5.0 
     AND COALESCE(o.courier_response_time_mins, 0) <= 5.0
      THEN 'OPS: Kitchen Slow'
    -- Handoff is the bottleneck (possible fake bump)
    WHEN COALESCE(o.courier_response_time_mins, 0) <= 5.0 
     AND COALESCE(o.kitchen_handoff_time_mins, 0) > 8.0
      THEN 'OPS: Slow Handoff (Possible Fake Bump)'
    -- Courier is the bottleneck
    WHEN o.ready_for_pickup_sla_difference <= 2.0 
     AND COALESCE(o.courier_response_time_mins, 0) > 10.0
      THEN 'LOGISTICS: Driver Shortage'
    -- Both ops and logistics failed
    WHEN o.ready_for_pickup_sla_difference > 2.0 
     AND COALESCE(o.courier_response_time_mins, 0) > 5.0
      THEN 'COMPOUNDING: Both Ops & Logistics Failed'
    -- Transit took too long
    WHEN o.transit_error < -5.0  -- Remember: negative = late
      THEN 'LOGISTICS: Slow Transit'
    ELSE 'OTHER'
  END AS primary_root_cause,
  
  COUNT(DISTINCT o.order_id) AS order_count,
  ROUND(AVG(o.delivery_sla_difference), 2) AS avg_delivery_lateness
  
FROM `wonder-dw-prod-brd.orders.hdr_orders` o
JOIN `wonder-dw-prod-brd.dw.dim_hdrs` h ON o.hdr_id = h.hdr_id
LEFT JOIN `wonder-dw-prod-brd.orders.hdr_on_time_orders` ot ON o.order_id = ot.order_id
WHERE o.order_status = 'COMPLETE'
  AND o.brand_category = 'WONDER_HDR'
  AND o.dining_option = 'DELIVERY'
  AND o.order_channel IN ('APP', 'WEB', 'IN_PERSON')
  AND o.service_date_et >= DATE_SUB(CURRENT_DATE('America/New_York'), INTERVAL 4 WEEK)
GROUP BY 1, 2, primary_root_cause
ORDER BY 1 DESC, order_count DESC;
```

### Potential Fake Bump Detection

```sql
-- Find orders with suspicious force bump patterns
-- Pattern: Driver arrived quickly, but handoff took very long
SELECT
  h.hdr_name,
  h.hdr_class,
  COUNT(DISTINCT o.order_id) AS total_delivery_orders,
  
  -- Potential Fake Bumps: courier_response ≤ 3 AND handoff > 8
  COUNT(DISTINCT CASE 
    WHEN COALESCE(o.courier_response_time_mins, 0) <= 3.0 
     AND COALESCE(o.kitchen_handoff_time_mins, 0) > 8.0 
    THEN o.order_id 
  END) AS potential_fake_bumps,
  
  SAFE_DIVIDE(
    COUNT(DISTINCT CASE 
      WHEN COALESCE(o.courier_response_time_mins, 0) <= 3.0 
       AND COALESCE(o.kitchen_handoff_time_mins, 0) > 8.0 
      THEN o.order_id 
    END),
    COUNT(DISTINCT o.order_id)
  ) AS fake_bump_rate,
  
  -- Average handoff time for these suspicious orders
  ROUND(AVG(CASE 
    WHEN COALESCE(o.courier_response_time_mins, 0) <= 3.0 
     AND COALESCE(o.kitchen_handoff_time_mins, 0) > 8.0 
    THEN o.kitchen_handoff_time_mins 
  END), 2) AS avg_suspicious_handoff_mins

FROM `wonder-dw-prod-brd.orders.hdr_orders` o
JOIN `wonder-dw-prod-brd.dw.dim_hdrs` h ON o.hdr_id = h.hdr_id
WHERE o.order_status = 'COMPLETE'
  AND o.brand_category = 'WONDER_HDR'
  AND o.dining_option = 'DELIVERY'
  AND o.service_date_et >= DATE_SUB(CURRENT_DATE('America/New_York'), INTERVAL 1 WEEK)
GROUP BY 1, 2
HAVING total_delivery_orders >= 50
ORDER BY fake_bump_rate DESC;
```

### Upstream Delay Analysis - Proper Blame Attribution

**Before blaming handoff or driver, check if kitchen was already late.** This query shows the full timing chain to properly attribute root cause.

```sql
-- Upstream Delay Analysis: Check if order was already late before sit time
-- This helps properly attribute blame - don't blame driver if kitchen was already late
SELECT
  h.hdr_name,
  h.hdr_class,
  h.population_type,
  COUNT(DISTINCT o.order_id) AS late_orders,
  
  -- UPSTREAM CHECK: Was kitchen already late?
  ROUND(AVG(o.ready_for_pickup_sla_difference), 1) AS avg_kitchen_delay_mins,
  ROUND(AVG(CASE WHEN o.ready_for_pickup_sla_difference > 2 THEN 1 ELSE 0 END) * 100, 1) AS pct_kitchen_late,
  
  -- Kitchen timing breakdown
  ROUND(AVG(TIMESTAMP_DIFF(o.actual_cooking_start_time_utc, o.expected_cooking_start_time_utc, SECOND) / 60.0), 1) AS queue_delay_mins,
  ROUND(AVG(TIMESTAMP_DIFF(o.actual_cooking_finish_time_utc, o.expected_cooking_finish_time_utc, SECOND) / 60.0), 1) AS cook_delay_mins,
  ROUND(AVG(TIMESTAMP_DIFF(o.actual_ready_for_pickup_time_utc, o.expected_ready_for_pickup_time_utc, SECOND) / 60.0), 1) AS ready_delay_mins,
  
  -- DOWNSTREAM: Courier and Handoff
  ROUND(AVG(o.courier_response_time_mins), 1) AS courier_resp,
  ROUND(AVG(o.kitchen_handoff_time_mins), 1) AS handoff,
  
  -- PROPER ATTRIBUTION
  ROUND(AVG(CASE 
    WHEN o.ready_for_pickup_sla_difference > 5 THEN 1 ELSE 0 
  END) * 100, 1) AS pct_blame_kitchen,
  
  ROUND(AVG(CASE 
    WHEN o.ready_for_pickup_sla_difference <= 2 
     AND o.courier_response_time_mins > o.kitchen_handoff_time_mins THEN 1 ELSE 0 
  END) * 100, 1) AS pct_blame_logistics,
  
  ROUND(AVG(CASE 
    WHEN o.ready_for_pickup_sla_difference <= 2 
     AND o.kitchen_handoff_time_mins > o.courier_response_time_mins THEN 1 ELSE 0 
  END) * 100, 1) AS pct_blame_handoff

FROM `wonder-dw-prod-brd.orders.hdr_orders` o
JOIN `wonder-dw-prod-brd.dw.dim_hdrs` h ON o.hdr_id = h.hdr_id
JOIN `wonder-dw-prod-brd.orders.hdr_on_time_orders` ot ON o.order_id = ot.order_id
WHERE o.order_status = 'COMPLETE'
  AND o.brand_category = 'WONDER_HDR'
  AND (o.order_business_type <> 'WONDER_SPOT' OR o.order_business_type IS NULL)
  AND (o.order_business_type <> '3P_PLATFORM_CORPORATE' OR o.order_business_type IS NULL)
  AND o.dining_option = 'DELIVERY'
  AND o.order_channel IN ('APP', 'WEB', 'IN_PERSON')
  AND ot.on_time_issue = TRUE
  AND ot.otr_sla_tier LIKE '%LATE'
  AND o.service_date_et >= DATE_TRUNC(DATE_SUB(CURRENT_DATE('America/New_York'), INTERVAL 1 WEEK), WEEK(MONDAY))
  AND o.service_date_et < DATE_TRUNC(CURRENT_DATE('America/New_York'), WEEK(MONDAY))
GROUP BY 1, 2, 3
HAVING COUNT(DISTINCT o.order_id) >= 5
ORDER BY late_orders DESC
LIMIT 20;
```

**Interpreting Results:**

| If You See | Root Cause | Action |
|------------|------------|--------|
| `pct_kitchen_late` > 50% | Kitchen is primary driver | Fix kitchen first; don't blame driver |
| `pct_blame_logistics` > `pct_blame_handoff` | True logistics problem | Courier incentives |
| `pct_blame_handoff` > `pct_blame_logistics` AND `pct_kitchen_late` < 30% | True expo/handoff problem | Audit store process |
| High `queue_delay_mins` | Orders waiting too long before cooking | Sequencing issue |
| High `cook_delay_mins` | Kitchen execution slow | Line efficiency, staffing |

### Imperfect Order Analysis

```sql
-- Imperfect order rates including non-timing issues
SELECT
  FORMAT_DATE('%F', DATE_TRUNC(o.service_date_et, WEEK(MONDAY))) AS service_week,
  o.dining_option,
  COUNT(DISTINCT o.order_id) AS total_orders,
  -- On-time issues (all)
  SAFE_DIVIDE(
    COUNT(DISTINCT CASE WHEN imp.on_time_issue THEN imp.order_id END),
    COUNT(DISTINCT imp.order_id)
  ) AS pct_on_time_issues,
  -- On-time issues (excludes earlies)
  SAFE_DIVIDE(
    COUNT(DISTINCT CASE WHEN imp.on_time_issue_excludes_earlies THEN imp.order_id END),
    COUNT(DISTINCT imp.order_id)
  ) AS pct_on_time_issues_no_earlies,
  -- Order accuracy issues (non-timing)
  SAFE_DIVIDE(
    COUNT(DISTINCT CASE WHEN imp.order_accuracy_issue THEN imp.order_id END),
    COUNT(DISTINCT imp.order_id)
  ) AS pct_order_accuracy_issues,
  -- Any imperfection
  SAFE_DIVIDE(
    COUNT(DISTINCT CASE WHEN imp.on_time_issue OR imp.order_accuracy_issue THEN imp.order_id END),
    COUNT(DISTINCT imp.order_id)
  ) AS pct_any_imperfection
FROM `wonder-dw-prod-brd.orders.hdr_orders` o
LEFT JOIN `wonder-dw-prod-brd.orders.imperfect_orders` imp ON o.order_id = imp.order_id
WHERE o.order_status = 'COMPLETE'
  AND o.brand_category = 'WONDER_HDR'
  AND o.service_date_et >= DATE_SUB(CURRENT_DATE('America/New_York'), INTERVAL 4 WEEK)
GROUP BY 1, 2
ORDER BY 1 DESC, 2;
```

---

## Weekly Business Review (WBR) Query Template

This section provides the complete set of queries needed to generate the weekly On-Time Performance summary for leadership review.

### 1. Executive Summary: Network Health

```sql
-- =============================================================================
-- SECTION 1: EXECUTIVE SUMMARY - NETWORK HEALTH
-- =============================================================================
-- Produces: Network OTR, OTR (No Earlies), Volume, Channel Breakdown, WoW Delta

WITH current_week AS (
  SELECT
    FORMAT_DATE('%F', DATE_TRUNC(o.service_date_et, WEEK(MONDAY))) AS service_week,
    o.dining_option,
    COUNT(DISTINCT o.order_id) AS order_count,
    COUNT(DISTINCT CASE WHEN ot.on_time_issue THEN ot.order_id END) AS orders_with_issues,
    COUNT(DISTINCT CASE WHEN ot.on_time_issue AND ot.otr_sla_tier NOT LIKE '%EARLY' THEN ot.order_id END) AS late_orders_only
  FROM `wonder-dw-prod-brd.orders.hdr_orders` o
  LEFT JOIN `wonder-dw-prod-brd.orders.hdr_on_time_orders` ot ON o.order_id = ot.order_id
  WHERE o.order_status = 'COMPLETE'
    AND o.brand_category = 'WONDER_HDR'
    AND o.order_channel IN ('APP', 'WEB', 'IN_PERSON')  -- 1P only
    AND o.service_date_et >= DATE_SUB(CURRENT_DATE('America/New_York'), INTERVAL 3 WEEK)
    AND o.service_date_et < DATE_TRUNC(CURRENT_DATE('America/New_York'), WEEK(MONDAY))
  GROUP BY 1, 2
),

weekly_summary AS (
  SELECT
    service_week,
    SUM(order_count) AS total_orders,
    SUM(CASE WHEN dining_option = 'PICKUP' THEN order_count ELSE 0 END) AS pickup_orders,
    SUM(CASE WHEN dining_option = 'DELIVERY' THEN order_count ELSE 0 END) AS delivery_orders,
    
    -- Network OTR
    1 - SAFE_DIVIDE(SUM(orders_with_issues), SUM(order_count)) AS network_otr,
    1 - SAFE_DIVIDE(SUM(late_orders_only), SUM(order_count)) AS network_otr_no_earlies,
    
    -- Pickup OTR
    1 - SAFE_DIVIDE(
      SUM(CASE WHEN dining_option = 'PICKUP' THEN orders_with_issues END),
      SUM(CASE WHEN dining_option = 'PICKUP' THEN order_count END)
    ) AS pickup_otr,
    
    -- Delivery OTR
    1 - SAFE_DIVIDE(
      SUM(CASE WHEN dining_option = 'DELIVERY' THEN orders_with_issues END),
      SUM(CASE WHEN dining_option = 'DELIVERY' THEN order_count END)
    ) AS delivery_otr
  FROM current_week
  GROUP BY service_week
)

SELECT
  curr.service_week,
  curr.total_orders,
  curr.pickup_orders,
  curr.delivery_orders,
  
  -- Current Week Metrics
  ROUND(curr.network_otr * 100, 1) AS network_otr_pct,
  ROUND(curr.network_otr_no_earlies * 100, 1) AS network_otr_no_earlies_pct,
  ROUND(curr.pickup_otr * 100, 1) AS pickup_otr_pct,
  ROUND(curr.delivery_otr * 100, 1) AS delivery_otr_pct,
  
  -- WoW Delta
  ROUND((curr.network_otr - prev.network_otr) * 100, 1) AS network_otr_wow_delta,
  ROUND((curr.network_otr_no_earlies - prev.network_otr_no_earlies) * 100, 1) AS otr_no_earlies_wow_delta,
  
  -- Channel Gap
  ROUND((curr.pickup_otr - curr.delivery_otr) * 100, 1) AS pickup_delivery_gap

FROM weekly_summary curr
LEFT JOIN weekly_summary prev 
  ON DATE(curr.service_week) = DATE_ADD(DATE(prev.service_week), INTERVAL 1 WEEK)
ORDER BY curr.service_week DESC
LIMIT 2;
```

### 2. Network Diagnosis: Kitchen Handoff Scenarios

```sql
-- =============================================================================
-- SECTION 2: KITCHEN HANDOFF SCENARIO ANALYSIS (Delivery Only)
-- =============================================================================
-- Produces: Volume by scenario, OTR, Avg Sit/Cook Error, "Algo Surprise"

WITH delivery_orders AS (
  SELECT
    o.order_id,
    o.service_date_et,
    o.ready_for_pickup_sla_difference,
    o.courier_response_time_mins,
    o.kitchen_handoff_time_mins,
    o.actual_pickup_waiting_duration_mins,
    o.cook_error,
    o.pickup_error,
    ot.on_time_issue,
    ot.otr_sla_tier,
    
    -- Kitchen Handoff Scenario
    CASE
      WHEN o.ready_for_pickup_sla_difference > 2.0 
       AND COALESCE(o.courier_response_time_mins, 0) <= 5.0 
      THEN 'A. Kitchen LATE, Courier Waits'
      WHEN o.ready_for_pickup_sla_difference <= 2.0 
       AND COALESCE(o.courier_response_time_mins, 0) > 5.0 
      THEN 'B. Kitchen FAST, Food Waits (Risk)'
      WHEN o.ready_for_pickup_sla_difference > 2.0 
       AND COALESCE(o.courier_response_time_mins, 0) > 5.0 
      THEN 'C. Compounding Failure (Both LATE)'
      ELSE 'D. Ideal State (Kitchen Fast, Handoff Fast)'
    END AS kitchen_handoff_scenario
    
  FROM `wonder-dw-prod-brd.orders.hdr_orders` o
  LEFT JOIN `wonder-dw-prod-brd.orders.hdr_on_time_orders` ot ON o.order_id = ot.order_id
  WHERE o.order_status = 'COMPLETE'
    AND o.brand_category = 'WONDER_HDR'
    AND o.dining_option = 'DELIVERY'
    AND o.order_channel IN ('APP', 'WEB', 'IN_PERSON')
    AND o.service_date_et >= DATE_TRUNC(DATE_SUB(CURRENT_DATE('America/New_York'), INTERVAL 1 WEEK), WEEK(MONDAY))
    AND o.service_date_et < DATE_TRUNC(CURRENT_DATE('America/New_York'), WEEK(MONDAY))
)

SELECT
  kitchen_handoff_scenario,
  COUNT(DISTINCT order_id) AS order_volume,
  ROUND(COUNT(DISTINCT order_id) * 100.0 / SUM(COUNT(DISTINCT order_id)) OVER(), 1) AS pct_of_total,
  
  -- OTR for this scenario
  ROUND((1 - SAFE_DIVIDE(
    COUNT(DISTINCT CASE WHEN on_time_issue THEN order_id END),
    COUNT(DISTINCT order_id)
  )) * 100, 1) AS otr_pct,
  
  -- The "Algo Surprise" metrics
  ROUND(AVG(ready_for_pickup_sla_difference), 1) AS avg_kitchen_sla_diff_mins,
  ROUND(AVG(pickup_error), 1) AS avg_sit_error_mins,
  ROUND(AVG(cook_error), 1) AS avg_cook_error_mins,
  ROUND(AVG(courier_response_time_mins), 1) AS avg_courier_response_mins,
  ROUND(AVG(kitchen_handoff_time_mins), 1) AS avg_kitchen_handoff_mins

FROM delivery_orders
GROUP BY kitchen_handoff_scenario
ORDER BY order_volume DESC;
```

### 3. Sit Time Decomposition: Courier vs Handoff Attribution

```sql
-- =============================================================================
-- SECTION 3: SIT TIME DECOMPOSITION (NOT ON TIME Orders Only)
-- =============================================================================
-- Produces: % of sit time attributable to Courier vs Kitchen Handoff

WITH late_orders AS (
  SELECT
    o.order_id,
    o.courier_response_time_mins,
    o.kitchen_handoff_time_mins,
    o.actual_pickup_waiting_duration_mins,
    
    -- Scenario
    CASE
      WHEN o.ready_for_pickup_sla_difference > 2.0 
       AND COALESCE(o.courier_response_time_mins, 0) <= 5.0 
      THEN 'A. Kitchen LATE'
      WHEN o.ready_for_pickup_sla_difference <= 2.0 
       AND COALESCE(o.courier_response_time_mins, 0) > 5.0 
      THEN 'B. Kitchen FAST'
      WHEN o.ready_for_pickup_sla_difference > 2.0 
       AND COALESCE(o.courier_response_time_mins, 0) > 5.0 
      THEN 'C. Compounding'
      ELSE 'D. Ideal'
    END AS scenario

  FROM `wonder-dw-prod-brd.orders.hdr_orders` o
  JOIN `wonder-dw-prod-brd.orders.hdr_on_time_orders` ot ON o.order_id = ot.order_id
  WHERE o.order_status = 'COMPLETE'
    AND o.brand_category = 'WONDER_HDR'
    AND o.dining_option = 'DELIVERY'
    AND o.order_channel IN ('APP', 'WEB', 'IN_PERSON')
    AND ot.on_time_issue = TRUE
    AND ot.otr_sla_tier NOT LIKE '%EARLY'  -- Late orders only
    AND o.service_date_et >= DATE_TRUNC(DATE_SUB(CURRENT_DATE('America/New_York'), INTERVAL 1 WEEK), WEEK(MONDAY))
    AND o.service_date_et < DATE_TRUNC(CURRENT_DATE('America/New_York'), WEEK(MONDAY))
)

SELECT
  scenario,
  COUNT(DISTINCT order_id) AS late_order_count,
  ROUND(AVG(courier_response_time_mins), 1) AS avg_courier_response_mins,
  ROUND(AVG(kitchen_handoff_time_mins), 1) AS avg_kitchen_handoff_mins,
  ROUND(AVG(actual_pickup_waiting_duration_mins), 1) AS avg_total_sit_mins,
  
  -- Attribution %
  ROUND(SAFE_DIVIDE(AVG(courier_response_time_mins), AVG(actual_pickup_waiting_duration_mins)) * 100, 0) AS pct_courier_attribution,
  ROUND(SAFE_DIVIDE(AVG(kitchen_handoff_time_mins), AVG(actual_pickup_waiting_duration_mins)) * 100, 0) AS pct_handoff_attribution,
  
  -- Verdict
  CASE
    WHEN AVG(courier_response_time_mins) > AVG(kitchen_handoff_time_mins) THEN 'LOGISTICS is majority driver'
    ELSE 'OPS (Handoff) is majority driver'
  END AS primary_bottleneck

FROM late_orders
GROUP BY scenario
ORDER BY late_order_count DESC;
```

### 4. Location Spotlights: Profile A (Ops Failure) & Profile B (Logistics Failure)

```sql
-- =============================================================================
-- SECTION 4A: PROFILE A - OPS FAILURES (Fast Drivers, Slow Handoffs)
-- =============================================================================
-- Criteria: Courier Response ≤ 5 mins, Kitchen Handoff > 8 mins
-- Diagnosis: "Fake Bumping" or Expo Bottleneck

SELECT
  h.hdr_name,
  h.hdr_class,
  h.population_type,
  COUNT(DISTINCT o.order_id) AS late_delivery_orders,
  
  ROUND(AVG(o.courier_response_time_mins), 1) AS avg_courier_response_mins,
  ROUND(AVG(o.kitchen_handoff_time_mins), 1) AS avg_kitchen_handoff_mins,
  ROUND(AVG(o.kitchen_handoff_time_mins) - AVG(o.courier_response_time_mins), 1) AS ops_gap_mins,
  
  ROUND((1 - SAFE_DIVIDE(
    COUNT(DISTINCT CASE WHEN ot.on_time_issue THEN ot.order_id END),
    COUNT(DISTINCT ot.order_id)
  )) * 100, 1) AS otr_pct,
  
  'Profile A: Ops Failure - Audit Expo/Fake Bumping' AS diagnosis

FROM `wonder-dw-prod-brd.orders.hdr_orders` o
JOIN `wonder-dw-prod-brd.dw.dim_hdrs` h ON o.hdr_id = h.hdr_id
LEFT JOIN `wonder-dw-prod-brd.orders.hdr_on_time_orders` ot ON o.order_id = ot.order_id
WHERE o.order_status = 'COMPLETE'
  AND o.brand_category = 'WONDER_HDR'
  AND o.dining_option = 'DELIVERY'
  AND o.order_channel IN ('APP', 'WEB', 'IN_PERSON')
  AND ot.on_time_issue = TRUE
  AND ot.otr_sla_tier LIKE '%LATE'
  AND o.service_date_et >= DATE_TRUNC(DATE_SUB(CURRENT_DATE('America/New_York'), INTERVAL 1 WEEK), WEEK(MONDAY))
  AND o.service_date_et < DATE_TRUNC(CURRENT_DATE('America/New_York'), WEEK(MONDAY))
GROUP BY 1, 2, 3
HAVING AVG(o.courier_response_time_mins) <= 5.0 
   AND AVG(o.kitchen_handoff_time_mins) > 8.0
   AND COUNT(DISTINCT o.order_id) >= 10
ORDER BY avg_kitchen_handoff_mins DESC
LIMIT 10;


-- =============================================================================
-- SECTION 4B: PROFILE B - LOGISTICS FAILURES (Fast Handoffs, Slow Drivers)
-- =============================================================================
-- Criteria: Kitchen Handoff ≤ 5 mins, Courier Response > 15 mins
-- Diagnosis: True Driver Shortage

SELECT
  h.hdr_name,
  h.hdr_class,
  h.population_type,
  COUNT(DISTINCT o.order_id) AS late_delivery_orders,
  
  ROUND(AVG(o.courier_response_time_mins), 1) AS avg_courier_response_mins,
  ROUND(AVG(o.kitchen_handoff_time_mins), 1) AS avg_kitchen_handoff_mins,
  ROUND(AVG(o.courier_response_time_mins) - AVG(o.kitchen_handoff_time_mins), 1) AS logistics_gap_mins,
  
  ROUND((1 - SAFE_DIVIDE(
    COUNT(DISTINCT CASE WHEN ot.on_time_issue THEN ot.order_id END),
    COUNT(DISTINCT ot.order_id)
  )) * 100, 1) AS otr_pct,
  
  'Profile B: Logistics Failure - Courier Incentives Needed' AS diagnosis

FROM `wonder-dw-prod-brd.orders.hdr_orders` o
JOIN `wonder-dw-prod-brd.dw.dim_hdrs` h ON o.hdr_id = h.hdr_id
LEFT JOIN `wonder-dw-prod-brd.orders.hdr_on_time_orders` ot ON o.order_id = ot.order_id
WHERE o.order_status = 'COMPLETE'
  AND o.brand_category = 'WONDER_HDR'
  AND o.dining_option = 'DELIVERY'
  AND o.order_channel IN ('APP', 'WEB', 'IN_PERSON')
  AND ot.on_time_issue = TRUE
  AND ot.otr_sla_tier LIKE '%LATE'
  AND o.service_date_et >= DATE_TRUNC(DATE_SUB(CURRENT_DATE('America/New_York'), INTERVAL 1 WEEK), WEEK(MONDAY))
  AND o.service_date_et < DATE_TRUNC(CURRENT_DATE('America/New_York'), WEEK(MONDAY))
GROUP BY 1, 2, 3
HAVING AVG(o.kitchen_handoff_time_mins) <= 5.0 
   AND AVG(o.courier_response_time_mins) > 15.0
   AND COUNT(DISTINCT o.order_id) >= 10
ORDER BY avg_courier_response_mins DESC
LIMIT 10;
```

### 5. NSO Performance ("2025 New" / "2026 New" Class)

```sql
-- =============================================================================
-- SECTION 5: NSO (NEW STORE OPENING) PERFORMANCE
-- =============================================================================

WITH nso_metrics AS (
  SELECT
    CASE 
      WHEN h.hdr_class IN ('2025 New', '2026 New') THEN 'NSO'
      ELSE 'Mature'
    END AS store_maturity,
    o.order_id,
    ot.on_time_issue,
    ot.otr_sla_tier,
    
    -- Scenario for compounding failure rate
    CASE
      WHEN o.ready_for_pickup_sla_difference > 2.0 
       AND COALESCE(o.courier_response_time_mins, 0) > 5.0 
      THEN 1 ELSE 0
    END AS is_compounding_failure
    
  FROM `wonder-dw-prod-brd.orders.hdr_orders` o
  JOIN `wonder-dw-prod-brd.dw.dim_hdrs` h ON o.hdr_id = h.hdr_id
  LEFT JOIN `wonder-dw-prod-brd.orders.hdr_on_time_orders` ot ON o.order_id = ot.order_id
  WHERE o.order_status = 'COMPLETE'
    AND o.brand_category = 'WONDER_HDR'
    AND o.dining_option = 'DELIVERY'
    AND o.order_channel IN ('APP', 'WEB', 'IN_PERSON')
    AND o.service_date_et >= DATE_TRUNC(DATE_SUB(CURRENT_DATE('America/New_York'), INTERVAL 1 WEEK), WEEK(MONDAY))
    AND o.service_date_et < DATE_TRUNC(CURRENT_DATE('America/New_York'), WEEK(MONDAY))
)

SELECT
  store_maturity,
  COUNT(DISTINCT order_id) AS delivery_orders,
  
  -- OTR Metrics
  ROUND((1 - SAFE_DIVIDE(
    COUNT(DISTINCT CASE WHEN on_time_issue THEN order_id END),
    COUNT(DISTINCT order_id)
  )) * 100, 1) AS otr_pct,
  
  ROUND((1 - SAFE_DIVIDE(
    COUNT(DISTINCT CASE WHEN on_time_issue AND otr_sla_tier NOT LIKE '%EARLY' THEN order_id END),
    COUNT(DISTINCT order_id)
  )) * 100, 1) AS otr_no_earlies_pct,
  
  -- Compounding Failure Rate
  ROUND(SUM(is_compounding_failure) * 100.0 / COUNT(DISTINCT order_id), 1) AS compounding_failure_rate_pct

FROM nso_metrics
GROUP BY store_maturity;


-- NSO OUTLIERS: Specific underperforming new stores
SELECT
  h.hdr_name,
  h.hdr_class,
  COUNT(DISTINCT o.order_id) AS delivery_orders,
  ROUND((1 - SAFE_DIVIDE(
    COUNT(DISTINCT CASE WHEN ot.on_time_issue THEN ot.order_id END),
    COUNT(DISTINCT ot.order_id)
  )) * 100, 1) AS otr_pct,
  ROUND(AVG(o.courier_response_time_mins), 1) AS avg_courier_response,
  ROUND(AVG(o.kitchen_handoff_time_mins), 1) AS avg_handoff,
  CASE
    WHEN AVG(o.kitchen_handoff_time_mins) > AVG(o.courier_response_time_mins) + 3 THEN 'Ops Failure'
    WHEN AVG(o.courier_response_time_mins) > AVG(o.kitchen_handoff_time_mins) + 3 THEN 'Logistics Failure'
    ELSE 'Compounding'
  END AS failure_type
FROM `wonder-dw-prod-brd.orders.hdr_orders` o
JOIN `wonder-dw-prod-brd.dw.dim_hdrs` h ON o.hdr_id = h.hdr_id
LEFT JOIN `wonder-dw-prod-brd.orders.hdr_on_time_orders` ot ON o.order_id = ot.order_id
WHERE o.order_status = 'COMPLETE'
  AND o.brand_category = 'WONDER_HDR'
  AND o.dining_option = 'DELIVERY'
  AND o.order_channel IN ('APP', 'WEB', 'IN_PERSON')
  AND h.hdr_class IN ('2025 New', '2026 New')
  AND o.service_date_et >= DATE_TRUNC(DATE_SUB(CURRENT_DATE('America/New_York'), INTERVAL 1 WEEK), WEEK(MONDAY))
  AND o.service_date_et < DATE_TRUNC(CURRENT_DATE('America/New_York'), WEEK(MONDAY))
GROUP BY 1, 2
HAVING COUNT(DISTINCT o.order_id) >= 30
ORDER BY otr_pct ASC
LIMIT 10;
```

### 6. Worst Handoff Times: The "Ops Gap" Analysis

```sql
-- =============================================================================
-- SECTION 6: OPS GAP ANALYSIS - WORST HANDOFF TIMES (ALL ORDERS)
-- =============================================================================
-- The "Yardley Effect": Fast drivers wasted by slow handoffs

SELECT
  h.hdr_name,
  h.hdr_class,
  h.population_type,
  COUNT(DISTINCT o.order_id) AS delivery_orders,
  
  ROUND(AVG(o.kitchen_handoff_time_mins), 2) AS avg_handoff_mins,
  ROUND(AVG(o.courier_response_time_mins), 2) AS avg_courier_response_mins,
  ROUND(AVG(o.kitchen_handoff_time_mins) - AVG(o.courier_response_time_mins), 2) AS ops_gap_mins,
  
  ROUND((1 - SAFE_DIVIDE(
    COUNT(DISTINCT CASE WHEN ot.on_time_issue THEN ot.order_id END),
    COUNT(DISTINCT ot.order_id)
  )) * 100, 1) AS otr_pct,
  
  -- Diagnosis
  CASE
    WHEN AVG(o.courier_response_time_mins) < 2.0 AND AVG(o.kitchen_handoff_time_mins) > 4.0 
      THEN 'SEVERE OPS FAILURE - Likely Fake Bumping'
    WHEN AVG(o.kitchen_handoff_time_mins) > AVG(o.courier_response_time_mins) + 2.0 
      THEN 'OPS DRAG - Store process lagging'
    WHEN AVG(o.courier_response_time_mins) > AVG(o.kitchen_handoff_time_mins) + 2.0 
      THEN 'LOGISTICS DRAG - Driver supply issue'
    ELSE 'COMPOUNDING - Both ops and logistics need attention'
  END AS diagnosis

FROM `wonder-dw-prod-brd.orders.hdr_orders` o
JOIN `wonder-dw-prod-brd.dw.dim_hdrs` h ON o.hdr_id = h.hdr_id
LEFT JOIN `wonder-dw-prod-brd.orders.hdr_on_time_orders` ot ON o.order_id = ot.order_id
WHERE o.order_status = 'COMPLETE'
  AND o.brand_category = 'WONDER_HDR'
  AND o.dining_option = 'DELIVERY'
  AND o.order_channel IN ('APP', 'WEB', 'IN_PERSON')
  AND o.service_date_et >= DATE_TRUNC(DATE_SUB(CURRENT_DATE('America/New_York'), INTERVAL 1 WEEK), WEEK(MONDAY))
  AND o.service_date_et < DATE_TRUNC(CURRENT_DATE('America/New_York'), WEEK(MONDAY))
GROUP BY 1, 2, 3
HAVING COUNT(DISTINCT o.order_id) >= 50
ORDER BY avg_handoff_mins DESC
LIMIT 10;
```

### 7. Worst O2E: Kitchen Speed vs Handoff Comparison

```sql
-- =============================================================================
-- SECTION 7: WORST O2E - TICKET TIME vs HANDOFF BREAKDOWN
-- =============================================================================
-- For chronic underperformers: Is the problem in the kitchen or at expo?

SELECT
  h.hdr_name,
  h.hdr_class,
  COUNT(DISTINCT o.order_id) AS delivery_orders,
  
  -- Total O2E
  ROUND(AVG(o.actual_o2e_mins), 1) AS avg_o2e_mins,
  
  -- Kitchen Speed (Ticket Time)
  ROUND(AVG(o.ticket_time_mins), 1) AS avg_ticket_time_mins,
  
  -- Handoff Speed
  ROUND(AVG(o.kitchen_handoff_time_mins), 1) AS avg_handoff_mins,
  
  -- Sit Time
  ROUND(AVG(o.actual_pickup_waiting_duration_mins), 1) AS avg_sit_time_mins,
  
  -- Courier Response
  ROUND(AVG(o.courier_response_time_mins), 1) AS avg_courier_response_mins,
  
  -- Delivery Duration
  ROUND(AVG(o.actual_delivery_duration_mins), 1) AS avg_delivery_duration_mins,
  
  -- Root Cause
  CASE
    WHEN AVG(o.ticket_time_mins) > 16 AND AVG(o.kitchen_handoff_time_mins) <= 3.0 
      THEN 'KITCHEN SPEED - Slow Make Line'
    WHEN AVG(o.ticket_time_mins) <= 16 AND AVG(o.kitchen_handoff_time_mins) > 4.0 
      THEN 'EXPO BOTTLENECK - Fast Kitchen, Slow Handoff'
    WHEN AVG(o.actual_delivery_duration_mins) > 14 
      THEN 'DELIVERY ZONE - Long Drive Times'
    ELSE 'MIXED - Multiple factors'
  END AS root_cause,
  
  -- OTR
  ROUND((1 - SAFE_DIVIDE(
    COUNT(DISTINCT CASE WHEN ot.on_time_issue THEN ot.order_id END),
    COUNT(DISTINCT ot.order_id)
  )) * 100, 1) AS otr_pct

FROM `wonder-dw-prod-brd.orders.hdr_orders` o
JOIN `wonder-dw-prod-brd.dw.dim_hdrs` h ON o.hdr_id = h.hdr_id
LEFT JOIN `wonder-dw-prod-brd.orders.hdr_on_time_orders` ot ON o.order_id = ot.order_id
WHERE o.order_status = 'COMPLETE'
  AND o.brand_category = 'WONDER_HDR'
  AND o.dining_option = 'DELIVERY'
  AND o.order_channel IN ('APP', 'WEB', 'IN_PERSON')
  AND o.service_date_et >= DATE_TRUNC(DATE_SUB(CURRENT_DATE('America/New_York'), INTERVAL 1 WEEK), WEEK(MONDAY))
  AND o.service_date_et < DATE_TRUNC(CURRENT_DATE('America/New_York'), WEEK(MONDAY))
GROUP BY 1, 2
HAVING COUNT(DISTINCT o.order_id) >= 50
ORDER BY avg_o2e_mins DESC
LIMIT 10;
```

### 8. Chronic Underperformers: Deep Dive Candidates (5+ Weeks on Worst List)

```sql
-- =============================================================================
-- SECTION 8: CHRONIC UNDERPERFORMERS - IDENTIFY DEEP DIVE CANDIDATES
-- =============================================================================
-- Criteria: On worst O2E list for 5+ weeks OR super outliers (>2 std dev)

WITH weekly_metrics AS (
  SELECT
    FORMAT_DATE('%F', DATE_TRUNC(o.service_date_et, WEEK(MONDAY))) AS service_week,
    h.hdr_id,
    h.hdr_name,
    h.hdr_class,
    h.design_type,
    h.hdr_opening_date,
    COALESCE(h.calendar_weeks_from_friends_family_start, h.calendar_weeks_from_opening_date) AS weeks_open,
    
    COUNT(DISTINCT o.order_id) AS delivery_orders,
    ROUND(AVG(o.actual_o2e_mins), 2) AS avg_o2e_mins,
    
    -- OTR
    SAFE_DIVIDE(
      COUNT(DISTINCT CASE WHEN imp.on_time_issue THEN imp.order_id END),
      COUNT(DISTINCT imp.order_id)
    ) AS on_time_issue_rate
    
  FROM `wonder-dw-prod-brd.orders.hdr_orders` o
  JOIN `wonder-dw-prod-brd.dw.dim_hdrs` h ON o.hdr_id = h.hdr_id
  LEFT JOIN `wonder-dw-prod-brd.orders.imperfect_orders` imp ON o.order_id = imp.order_id
  WHERE o.order_status = 'COMPLETE'
    AND o.brand_category = 'WONDER_HDR'
    AND (o.order_business_type <> 'WONDER_SPOT' OR o.order_business_type IS NULL)
    AND (o.order_business_type <> '3P_PLATFORM_CORPORATE' OR o.order_business_type IS NULL)
    AND o.dining_option = 'DELIVERY'
    AND o.order_channel IN ('APP', 'WEB', 'IN_PERSON')
    AND o.service_date_et >= DATE_ADD(DATE_TRUNC(CURRENT_DATE('America/New_York'), WEEK(MONDAY)), INTERVAL -24 WEEK)
    AND o.service_date_et < DATE_TRUNC(CURRENT_DATE('America/New_York'), WEEK(MONDAY))
  GROUP BY 1, 2, 3, 4, 5, 6, 7
  HAVING COUNT(DISTINCT o.order_id) >= 30
),

-- Calculate network averages and std dev per week for outlier detection
weekly_stats AS (
  SELECT
    service_week,
    AVG(avg_o2e_mins) AS network_avg_o2e,
    STDDEV_POP(avg_o2e_mins) AS network_stddev_o2e
  FROM weekly_metrics
  GROUP BY service_week
),

-- Rank HDRs per week and flag outliers
weekly_ranked AS (
  SELECT
    wm.*,
    ws.network_avg_o2e,
    ws.network_stddev_o2e,
    RANK() OVER (PARTITION BY wm.service_week ORDER BY wm.avg_o2e_mins DESC) AS o2e_rank,
    CASE 
      WHEN wm.avg_o2e_mins > ws.network_avg_o2e + 2 * ws.network_stddev_o2e THEN TRUE 
      ELSE FALSE 
    END AS is_super_outlier
  FROM weekly_metrics wm
  JOIN weekly_stats ws ON wm.service_week = ws.service_week
)

SELECT
  hdr_name,
  hdr_class,
  design_type,
  MAX(weeks_open) AS current_weeks_open,
  
  -- Weeks on worst list
  COUNT(CASE WHEN o2e_rank <= 10 THEN 1 END) AS weeks_in_worst_10,
  COUNT(CASE WHEN is_super_outlier THEN 1 END) AS weeks_as_super_outlier,
  
  -- Average performance
  ROUND(AVG(avg_o2e_mins), 1) AS avg_o2e_across_weeks,
  ROUND(AVG(on_time_issue_rate) * 100, 1) AS avg_on_time_issue_rate_pct,
  
  -- Recent weeks on list
  STRING_AGG(
    CASE WHEN o2e_rank <= 10 THEN service_week END, 
    ', ' ORDER BY service_week DESC LIMIT 5
  ) AS recent_worst_weeks,
  
  -- Deep Dive Priority
  CASE
    WHEN COUNT(CASE WHEN o2e_rank <= 10 THEN 1 END) >= 10 THEN '🔴 CRITICAL - 10+ weeks'
    WHEN COUNT(CASE WHEN o2e_rank <= 10 THEN 1 END) >= 5 THEN '🟠 HIGH - 5+ weeks'
    WHEN COUNT(CASE WHEN is_super_outlier THEN 1 END) >= 3 THEN '🟡 OUTLIER - Super outlier 3+ times'
    ELSE '⚪ MONITOR'
  END AS deep_dive_priority

FROM weekly_ranked
GROUP BY 1, 2, 3
HAVING COUNT(CASE WHEN o2e_rank <= 10 THEN 1 END) >= 5 
    OR COUNT(CASE WHEN is_super_outlier THEN 1 END) >= 3
ORDER BY weeks_in_worst_10 DESC, weeks_as_super_outlier DESC;
```

### 9. Location Deep Dive: Complete Timing Breakdown

```sql
-- =============================================================================
-- SECTION 9: LOCATION DEEP DIVE - ALL TIMING METRICS
-- =============================================================================
-- Use for HDRs identified as chronic underperformers
-- Replace 'TARGET_HDR_NAME' with the HDR you're investigating

-- 9A: ALL ORDERS - Queue, Cook, Packing/Bagging vs Estimated
SELECT
  FORMAT_DATE('%F', DATE_TRUNC(o.service_date_et, WEEK(MONDAY))) AS service_week,
  h.hdr_name,
  h.hdr_class,
  o.dining_option,
  COUNT(DISTINCT o.order_id) AS order_count,
  
  -- Queue Time
  ROUND(AVG(o.actual_queue_mins), 2) AS avg_actual_queue_mins,
  ROUND(AVG(o.estimated_queue_mins), 2) AS avg_estimated_queue_mins,
  ROUND(AVG(o.actual_queue_mins - COALESCE(o.estimated_queue_mins, 0)), 2) AS avg_queue_variance,
  
  -- Cook Duration
  ROUND(AVG(o.actual_cook_duration_mins), 2) AS avg_actual_cook_mins,
  ROUND(AVG(o.estimated_cook_duration_mins), 2) AS avg_estimated_cook_mins,
  ROUND(AVG(o.actual_cook_duration_mins - COALESCE(o.estimated_cook_duration_mins, 0)), 2) AS avg_cook_variance,
  
  -- Packing/Bagging
  ROUND(AVG(o.actual_packaging_bagging_mins), 2) AS avg_actual_pack_bag_mins,
  ROUND(AVG(o.estimated_packaging_bagging_mins), 2) AS avg_estimated_pack_bag_mins,
  ROUND(AVG(o.actual_packaging_bagging_mins - COALESCE(o.estimated_packaging_bagging_mins, 0)), 2) AS avg_pack_bag_variance,
  
  -- Ticket Time (Total Kitchen)
  ROUND(AVG(o.ticket_time_mins), 2) AS avg_ticket_time_mins,
  
  -- OTR
  ROUND((1 - SAFE_DIVIDE(
    COUNT(DISTINCT CASE WHEN ot.on_time_issue THEN ot.order_id END),
    COUNT(DISTINCT ot.order_id)
  )) * 100, 1) AS otr_pct

FROM `wonder-dw-prod-brd.orders.hdr_orders` o
JOIN `wonder-dw-prod-brd.dw.dim_hdrs` h ON o.hdr_id = h.hdr_id
LEFT JOIN `wonder-dw-prod-brd.orders.hdr_on_time_orders` ot ON o.order_id = ot.order_id
WHERE o.order_status = 'COMPLETE'
  AND o.brand_category = 'WONDER_HDR'
  AND h.hdr_name = 'TARGET_HDR_NAME'  -- Replace with target HDR
  AND o.service_date_et >= DATE_SUB(CURRENT_DATE('America/New_York'), INTERVAL 12 WEEK)
GROUP BY 1, 2, 3, 4
ORDER BY service_week DESC, dining_option;


-- 9B: 1P DELIVERY ONLY - Handoff, Courier Response, Delivery Duration
SELECT
  FORMAT_DATE('%F', DATE_TRUNC(o.service_date_et, WEEK(MONDAY))) AS service_week,
  h.hdr_name,
  h.hdr_class,
  COUNT(DISTINCT o.order_id) AS delivery_orders,
  
  -- Sit Time Decomposition
  ROUND(AVG(o.courier_response_time_mins), 2) AS avg_courier_response_mins,
  ROUND(AVG(o.kitchen_handoff_time_mins), 2) AS avg_kitchen_handoff_mins,
  ROUND(AVG(o.actual_pickup_waiting_duration_mins), 2) AS avg_total_sit_mins,
  
  -- Ops Gap (positive = ops slower)
  ROUND(AVG(COALESCE(o.kitchen_handoff_time_mins, 0) - COALESCE(o.courier_response_time_mins, 0)), 2) AS ops_gap_mins,
  
  -- Delivery Duration
  ROUND(AVG(o.actual_delivery_duration_mins), 2) AS avg_delivery_duration_mins,
  ROUND(AVG(o.estimated_delivery_duration_mins), 2) AS avg_estimated_delivery_mins,
  ROUND(AVG(o.actual_delivery_duration_mins - COALESCE(o.estimated_delivery_duration_mins, 0)), 2) AS delivery_variance,
  
  -- Transit
  ROUND(AVG(o.actual_transit_mins), 2) AS avg_transit_mins,
  
  -- Total O2E
  ROUND(AVG(o.actual_o2e_mins), 2) AS avg_o2e_mins,
  
  -- OTR
  ROUND((1 - SAFE_DIVIDE(
    COUNT(DISTINCT CASE WHEN ot.on_time_issue THEN ot.order_id END),
    COUNT(DISTINCT ot.order_id)
  )) * 100, 1) AS otr_pct,
  
  -- Primary Bottleneck
  CASE
    WHEN AVG(o.ticket_time_mins) > 16 THEN 'KITCHEN SPEED'
    WHEN AVG(o.kitchen_handoff_time_mins) > 5 AND AVG(o.courier_response_time_mins) < 3 THEN 'EXPO/HANDOFF (Possible Fake Bump)'
    WHEN AVG(o.courier_response_time_mins) > 8 THEN 'DRIVER SUPPLY'
    WHEN AVG(o.actual_delivery_duration_mins) > 14 THEN 'DELIVERY ZONE'
    ELSE 'MIXED'
  END AS likely_bottleneck

FROM `wonder-dw-prod-brd.orders.hdr_orders` o
JOIN `wonder-dw-prod-brd.dw.dim_hdrs` h ON o.hdr_id = h.hdr_id
LEFT JOIN `wonder-dw-prod-brd.orders.hdr_on_time_orders` ot ON o.order_id = ot.order_id
WHERE o.order_status = 'COMPLETE'
  AND o.brand_category = 'WONDER_HDR'
  AND o.dining_option = 'DELIVERY'
  AND o.order_channel IN ('APP', 'WEB', 'IN_PERSON')  -- 1P only
  AND h.hdr_name = 'TARGET_HDR_NAME'  -- Replace with target HDR
  AND o.service_date_et >= DATE_SUB(CURRENT_DATE('America/New_York'), INTERVAL 12 WEEK)
GROUP BY 1, 2, 3
ORDER BY service_week DESC;


-- 9C: COMPARE TWO HDRS SIDE BY SIDE (e.g., Marlboro vs Green Brook)
WITH hdr_comparison AS (
  SELECT
    h.hdr_name,
    COUNT(DISTINCT o.order_id) AS delivery_orders,
    
    -- Kitchen Speed
    ROUND(AVG(o.ticket_time_mins), 1) AS avg_ticket_time,
    ROUND(AVG(o.actual_queue_mins), 1) AS avg_queue,
    ROUND(AVG(o.actual_cook_duration_mins), 1) AS avg_cook,
    ROUND(AVG(o.actual_packaging_bagging_mins), 1) AS avg_pack_bag,
    
    -- Handoff
    ROUND(AVG(o.kitchen_handoff_time_mins), 1) AS avg_handoff,
    ROUND(AVG(o.courier_response_time_mins), 1) AS avg_courier_response,
    
    -- Delivery
    ROUND(AVG(o.actual_delivery_duration_mins), 1) AS avg_delivery_duration,
    
    -- Total
    ROUND(AVG(o.actual_o2e_mins), 1) AS avg_o2e,
    
    -- OTR
    ROUND((1 - SAFE_DIVIDE(
      COUNT(DISTINCT CASE WHEN ot.on_time_issue THEN ot.order_id END),
      COUNT(DISTINCT ot.order_id)
    )) * 100, 1) AS otr_pct

  FROM `wonder-dw-prod-brd.orders.hdr_orders` o
  JOIN `wonder-dw-prod-brd.dw.dim_hdrs` h ON o.hdr_id = h.hdr_id
  LEFT JOIN `wonder-dw-prod-brd.orders.hdr_on_time_orders` ot ON o.order_id = ot.order_id
  WHERE o.order_status = 'COMPLETE'
    AND o.brand_category = 'WONDER_HDR'
    AND o.dining_option = 'DELIVERY'
    AND o.order_channel IN ('APP', 'WEB', 'IN_PERSON')
    AND h.hdr_name IN ('Marlboro Plaza', 'Green Brook')  -- Replace with comparison HDRs
    AND o.service_date_et >= DATE_TRUNC(DATE_SUB(CURRENT_DATE('America/New_York'), INTERVAL 4 WEEK), WEEK(MONDAY))
  GROUP BY 1
)

SELECT
  *,
  CASE
    WHEN avg_ticket_time > 16 AND avg_handoff <= 3 THEN 'Root Cause: KITCHEN SPEED'
    WHEN avg_ticket_time <= 16 AND avg_handoff > 4 THEN 'Root Cause: EXPO BOTTLENECK'
    WHEN avg_delivery_duration > 14 THEN 'Root Cause: DELIVERY ZONE'
    ELSE 'Root Cause: MIXED'
  END AS diagnosis
FROM hdr_comparison
ORDER BY avg_o2e DESC;
```

---

## WBR Core KPIs Framework

### The Three Core KPIs

| KPI | Definition | Primary Cut | Why This Cut |
|-----|------------|-------------|--------------|
| **On-Time Rate (OTR)** | Order within -9 to +1 min of promise | **1P All Orders** | Primary leadership KPI (Pickup + Delivery) |
| **Ticket Time** | Order placed → Ready for pickup | **All Orders** | Kitchen execution applies to all channels |
| **Order Expo Wait Time** | First item pending_pack → Last item pending_bag | **All Orders** | Expo efficiency affects all orders |

### OTR Cuts (All 1P-Based)

| Cut | Definition | Purpose |
|-----|------------|---------|
| **1P All Orders** | Pickup + Delivery combined | Network headline KPI |
| **1P Delivery** | Delivery only | Most complex channel, biggest opportunity |
| **1P Pickup** | Pickup only | Usually high performer (~96%), anchors network |
| **OTR Excluding Earlies** | 1P (removes >9 min early) | Removes ETA over-prediction noise |

> **Why 1P only?** 3P platform timestamps after `ready_for_pickup` are unreliable. Use Kitchen Process OTR for 3P accountability.

### Secondary Cuts

| KPI | Additional Cuts | Purpose |
|-----|-----------------|---------|
| **Ticket Time** | 1P vs 3P Delivery (not apples-to-apples) | Compare channel complexity |
| **Kitchen Process OTR** | All Orders (vs Expected Ready) | Isolate kitchen performance from logistics |

### Kitchen Process OTR vs Customer OTR

| Metric | Definition | Who Uses It |
|--------|------------|-------------|
| **Customer OTR** | Delivery vs Promise | Leadership KPI, Customer impact |
| **Kitchen Process OTR** | `ready_for_pickup_sla_difference <= 2` | Ops KPI, Kitchen accountability |

**Why both?** Customer OTR can mask kitchen delays if courier saves the order. Kitchen Process OTR shows true kitchen execution.

---

## WBR Reason Code Attribution

### The Attribution Challenge

**Sequencer Correlation ≠ Causation:**
- Sequencer is applied to MORE COMPLEX orders (larger orders, high cook time disparity, batched items)
- Cutting data by "sequencer involved" will show worse metrics
- This doesn't mean sequencer CAUSED the problem - it handled harder orders

### Reason Code Hierarchy (Prioritized)

**Priority 1: Accuracy Issues** (always supersede timing)
| Code | Definition | Owner |
|------|------------|-------|
| `ACCURACY_ISSUE` | Order had accuracy problem (L1-L4 hierarchy) | Ops/Kitchen |

**Priority 2: Timing Issues** (in kitchen sequence order)

| Code | Definition | Threshold | Owner |
|------|------------|-----------|-------|
| `EARLY_ORDER` | Delivered >9 min early | `delivery_sla_difference < -9` | ETA Model |
| `LONG_QUEUE` | Item queued too long | `item_queue_time_min >= 5` | Ops |
| `DELAYED_START` | Item focused but not started | `focus_to_cook_start > 2 min` | Ops |
| `LONG_COOK` | Cook time exceeded expected | `(actual - expected) > 3 min` | Ops/Culinary |
| `EXPO_DELAY` | Item waited at expo | `pending_pack_to_bag > 5 min` | Ops |
| `LATE_PICKUP` | Ready on time, picked up late | Kitchen on time + courier late | Logistics |
| `LATE_DELIVERY` | Picked up on time, delivered late | Courier on time + transit late | Logistics |

### Ops vs Sequencer vs ETA Attribution

```sql
-- Properly attribute misses controlling for order complexity
WITH order_complexity AS (
  SELECT
    koi.order_id,
    COUNT(*) AS item_count,
    MAX(koi.expected_step_time/60) - MIN(koi.expected_step_time/60) AS cook_time_range,
    CASE 
      WHEN MAX(koi.expected_step_time/60) - MIN(koi.expected_step_time/60) > 6 THEN 'HIGH'
      WHEN MAX(koi.expected_step_time/60) - MIN(koi.expected_step_time/60) > 3 THEN 'MEDIUM'
      ELSE 'LOW'
    END AS cook_time_disparity,
    MAX(CASE WHEN koi.delay_duration_mins > 0 THEN 1 ELSE 0 END) AS has_sequencer_delay,
    MAX(CASE WHEN ki.has_bad_interaction = 1 THEN 1 ELSE 0 END) AS has_bad_interaction,
    MAX(CASE WHEN ki.has_critical_force_complete = 1 THEN 1 ELSE 0 END) AS has_critical_force
  FROM `wonder-dw-prod-brd.orders.hdr_kitchen_order_item` koi
  LEFT JOIN `wonder-dw-prod-brd.orders.imperfect_kitchen_items` ki ON koi.id = ki.id
  WHERE koi.order_status = 'COMPLETED'
    AND DATE(koi.order_assigned_to_pod_time) >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
  GROUP BY 1
)
SELECT
  oc.cook_time_disparity AS complexity,
  
  -- Kitchen Process OTR by complexity tier
  ROUND(AVG(CASE WHEN o.ready_for_pickup_sla_difference <= 2 THEN 1 ELSE 0 END) * 100, 1) AS kitchen_otr,
  
  -- Attribution breakdown
  ROUND(AVG(oc.has_critical_force) * 100, 1) AS pct_critical_force,
  ROUND(AVG(oc.has_bad_interaction) * 100, 1) AS pct_bad_interaction,
  ROUND(AVG(oc.has_sequencer_delay) * 100, 1) AS pct_sequencer_involved,
  
  -- Average timing
  ROUND(AVG(o.ticket_time_mins), 1) AS avg_ticket_time,
  COUNT(DISTINCT o.order_id) AS orders
  
FROM order_complexity oc
JOIN `wonder-dw-prod-brd.orders.hdr_orders` o ON oc.order_id = o.order_id
WHERE o.order_status = 'COMPLETE'
  AND o.brand_category = 'WONDER_HDR'
GROUP BY 1
ORDER BY 1;
```

### Attribution Categories

| Category | Definition | Indicators |
|----------|------------|------------|
| **OPS - Force Complete** | Premature force completion | `has_critical_force_complete = 1` |
| **OPS - Long Handoff** | Slow expo handoff | `kitchen_handoff_time_mins > 5` AND kitchen on time |
| **OPS - Long Cook** | Cook exceeded expected | `has_longer_than_expected_production_time = 1` |
| **SEQUENCER - Bad Interaction** | Held ALM incorrectly | `has_bad_interaction = 1` |
| **SEQUENCER - Double Delay** | Applied double delay | `has_double_delay = 1` |
| **ETA - Over-prediction** | Order arrived early | `delivery_sla_difference < -9` |
| **ETA - Under-prediction** | ETA too optimistic for complexity | High complexity + no ops flags |
| **LOGISTICS** | Kitchen on time, driver late | `ready_for_pickup_sla_difference <= 2` AND late delivery |

### Complexity-Controlled Analysis

**Always segment by complexity when analyzing sequencer:**

```sql
-- Compare Kitchen OTR: Sequencer-involved vs Not, WITHIN same complexity tier
SELECT
  complexity_tier,
  has_sequencer_delay,
  COUNT(*) AS orders,
  ROUND(AVG(CASE WHEN ready_for_pickup_sla_difference <= 2 THEN 1 ELSE 0 END) * 100, 1) AS kitchen_otr
FROM (
  SELECT
    o.order_id,
    o.ready_for_pickup_sla_difference,
    CASE 
      WHEN oc.cook_time_range > 6 OR oc.item_count >= 5 THEN 'HIGH'
      WHEN oc.cook_time_range > 3 OR oc.item_count >= 3 THEN 'MEDIUM'
      ELSE 'LOW'
    END AS complexity_tier,
    oc.has_sequencer_delay
  FROM order_complexity oc
  JOIN `wonder-dw-prod-brd.orders.hdr_orders` o ON oc.order_id = o.order_id
)
GROUP BY 1, 2
ORDER BY 1, 2;
```

**Interpretation:**
- If sequencer-involved orders have WORSE OTR *within the same complexity tier* → Sequencer may need improvement
- If sequencer-involved orders have SAME or BETTER OTR within tier → Sequencer is helping

---

## WBR Concise Rollup Query

```sql
-- Single query for WBR core metrics
WITH weekly_metrics AS (
  SELECT
    FORMAT_DATE('%F', DATE_TRUNC(o.service_date_et, WEEK(MONDAY))) AS week,
    h.population_type,
    h.hdr_class,
    
    -- 1P Order Counts
    COUNT(DISTINCT CASE 
      WHEN o.order_channel IN ('APP','WEB','IN_PERSON') 
      THEN o.order_id END) AS orders_1p_all,
    COUNT(DISTINCT CASE 
      WHEN o.dining_option = 'DELIVERY' AND o.order_channel IN ('APP','WEB','IN_PERSON') 
      THEN o.order_id END) AS orders_1p_delivery,
    COUNT(DISTINCT CASE 
      WHEN o.dining_option = 'PICKUP' AND o.order_channel IN ('APP','WEB','IN_PERSON') 
      THEN o.order_id END) AS orders_1p_pickup,
    
    -- CORE KPI 1a: 1P All Orders OTR (Network Headline)
    ROUND((1 - SAFE_DIVIDE(
      COUNT(DISTINCT CASE WHEN o.order_channel IN ('APP','WEB','IN_PERSON') 
        AND ot.on_time_issue THEN o.order_id END),
      COUNT(DISTINCT CASE WHEN o.order_channel IN ('APP','WEB','IN_PERSON') 
        THEN o.order_id END)
    )) * 100, 1) AS otr_1p_all,
    
    -- CORE KPI 1b: 1P Delivery OTR
    ROUND((1 - SAFE_DIVIDE(
      COUNT(DISTINCT CASE WHEN o.dining_option = 'DELIVERY' AND o.order_channel IN ('APP','WEB','IN_PERSON') 
        AND ot.on_time_issue THEN o.order_id END),
      COUNT(DISTINCT CASE WHEN o.dining_option = 'DELIVERY' AND o.order_channel IN ('APP','WEB','IN_PERSON') 
        THEN o.order_id END)
    )) * 100, 1) AS otr_1p_delivery,
    
    -- CORE KPI 1c: 1P Pickup OTR
    ROUND((1 - SAFE_DIVIDE(
      COUNT(DISTINCT CASE WHEN o.dining_option = 'PICKUP' AND o.order_channel IN ('APP','WEB','IN_PERSON') 
        AND ot.on_time_issue THEN o.order_id END),
      COUNT(DISTINCT CASE WHEN o.dining_option = 'PICKUP' AND o.order_channel IN ('APP','WEB','IN_PERSON') 
        THEN o.order_id END)
    )) * 100, 1) AS otr_1p_pickup,
    
    -- CORE KPI 1d: 1P OTR Excluding Earlies
    ROUND((1 - SAFE_DIVIDE(
      COUNT(DISTINCT CASE WHEN o.order_channel IN ('APP','WEB','IN_PERSON') 
        AND ot.on_time_issue AND ot.otr_sla_tier NOT LIKE '%EARLY' THEN o.order_id END),
      COUNT(DISTINCT CASE WHEN o.order_channel IN ('APP','WEB','IN_PERSON') 
        THEN o.order_id END)
    )) * 100, 1) AS otr_1p_no_earlies,
    
    -- CORE KPI 2: Ticket Time (All Orders)
    ROUND(AVG(o.ticket_time_mins), 1) AS avg_ticket_time_all,
    ROUND(AVG(CASE WHEN o.order_channel IN ('APP','WEB','IN_PERSON') 
      THEN o.ticket_time_mins END), 1) AS avg_ticket_time_1p,
    ROUND(AVG(CASE WHEN o.dining_option = 'DELIVERY' AND o.order_channel IN ('APP','WEB','IN_PERSON') 
      THEN o.ticket_time_mins END), 1) AS avg_ticket_time_1p_del,
    ROUND(AVG(CASE WHEN o.dining_option = 'DELIVERY' AND o.order_channel NOT IN ('APP','WEB','IN_PERSON') 
      THEN o.ticket_time_mins END), 1) AS avg_ticket_time_3p_del,
    
    -- CORE KPI 3: Expo Wait Time (All Orders)
    ROUND(AVG(ot.order_level_expo_wait_time), 1) AS avg_expo_wait_time,
    
    -- Kitchen Process OTR (All Orders - for 3P accountability)
    ROUND(AVG(CASE WHEN o.ready_for_pickup_sla_difference <= 2 THEN 1 ELSE 0 END) * 100, 1) AS kitchen_process_otr,
    
    -- Total volume
    COUNT(DISTINCT o.order_id) AS total_orders
    
  FROM `wonder-dw-prod-brd.orders.hdr_orders` o
  JOIN `wonder-dw-prod-brd.dw.dim_hdrs` h ON o.hdr_id = h.hdr_id
  LEFT JOIN `wonder-dw-prod-brd.orders.hdr_on_time_orders` ot ON o.order_id = ot.order_id
  WHERE o.order_status = 'COMPLETE'
    AND o.brand_category = 'WONDER_HDR'
    AND (o.order_business_type <> 'WONDER_SPOT' OR o.order_business_type IS NULL)
    AND (o.order_business_type <> '3P_PLATFORM_CORPORATE' OR o.order_business_type IS NULL)
    AND o.service_date_et >= DATE_TRUNC(DATE_SUB(CURRENT_DATE('America/New_York'), INTERVAL 2 WEEK), WEEK(MONDAY))
    AND o.service_date_et < DATE_TRUNC(CURRENT_DATE('America/New_York'), WEEK(MONDAY))
  GROUP BY 1, 2, 3
)

SELECT
  week,
  population_type,
  hdr_class,
  -- Volume
  SUM(total_orders) AS total_orders,
  SUM(orders_1p_all) AS orders_1p,
  SUM(orders_1p_delivery) AS orders_1p_delivery,
  SUM(orders_1p_pickup) AS orders_1p_pickup,
  -- OTR (1P)
  ROUND(SUM(orders_1p_all * otr_1p_all) / NULLIF(SUM(orders_1p_all), 0), 1) AS otr_1p_all,
  ROUND(SUM(orders_1p_delivery * otr_1p_delivery) / NULLIF(SUM(orders_1p_delivery), 0), 1) AS otr_1p_delivery,
  ROUND(SUM(orders_1p_pickup * otr_1p_pickup) / NULLIF(SUM(orders_1p_pickup), 0), 1) AS otr_1p_pickup,
  ROUND(SUM(orders_1p_all * otr_1p_no_earlies) / NULLIF(SUM(orders_1p_all), 0), 1) AS otr_1p_no_earlies,
  -- Ticket Time
  ROUND(SUM(total_orders * avg_ticket_time_all) / NULLIF(SUM(total_orders), 0), 1) AS avg_ticket_time,
  -- Expo Wait
  ROUND(SUM(total_orders * avg_expo_wait_time) / NULLIF(SUM(total_orders), 0), 1) AS avg_expo_wait,
  -- Kitchen OTR
  ROUND(SUM(total_orders * kitchen_process_otr) / NULLIF(SUM(total_orders), 0), 1) AS kitchen_otr
FROM weekly_metrics
GROUP BY ROLLUP(week, population_type, hdr_class)
ORDER BY week DESC, population_type, hdr_class;
```

---

## WBR Report Structure Template

Use the queries above to populate this leadership-ready structure:

```
# On-Time Performance
**Period:** Week of [DATE]

## 1. Executive Summary: Network Health
- **Network OTR:** X% (▲/▼ X pts WoW)
- **OTR (Excluding Earlies):** X%
- **Total 1P Volume:** X Orders
- **Pickup OTR:** X% (X orders)
- **Delivery OTR:** X% (X orders)
- **Channel Gap:** X points

**Key Insight:** [One sentence summary of the week]

## 2. Network Diagnosis: The "Expectation Gap"
| Scenario | Volume (%) | OTR | The "Algo Surprise" |
|----------|------------|-----|---------------------|
| D. Ideal State | X (X%) | X% | Working as designed |
| B. Kitchen FAST, Food Waits | X (X%) | X% | Sit Surprise: +X mins |
| A. Kitchen LATE | X (X%) | X% | Prep Surprise: +X mins |
| C. Compounding Failure | X (X%) | X% | Double Miss |

## 3. Sit Time Decomposition: Who's at Fault?
| Scenario | Courier Response | Kitchen Handoff | Primary Bottleneck |
|----------|-----------------|-----------------|-------------------|
| B. Kitchen FAST | X mins (X%) | X mins (X%) | LOGISTICS |
| A. Kitchen LATE | X mins (X%) | X mins (X%) | OPS |

## 4. Location Spotlights
### Profile A: Ops Failures (Audit Expo)
| HDR | Courier Response | Kitchen Handoff | Gap |
|-----|-----------------|-----------------|-----|
| [HDR] | X mins | X mins | -X mins |

### Profile B: Logistics Failures (Courier Incentives)
| HDR | Courier Response | Kitchen Handoff | Gap |
|-----|-----------------|-----------------|-----|
| [HDR] | X mins | X mins | +X mins |

## 5. NSO Performance
- **NSO OTR:** X% (vs Network: X%)
- **NSO OTR (No Earlies):** X%
- **Compounding Failure Rate:** X%
- **Outliers:** [List specific struggling stores]

## 6. Ops Gap Analysis: Worst Handoffs
| Rank | HDR | Handoff | Driver Speed | Ops Gap | Diagnosis |
|------|-----|---------|--------------|---------|-----------|
| 1 | [HDR] | X min | X min | +X min | [Diagnosis] |

## 7. Deep Dive Candidates (5+ Weeks on Worst List)
| HDR | Class | Weeks on List | Avg O2E | Priority |
|-----|-------|---------------|---------|----------|
| [HDR] | [Class] | X | X mins | 🔴 CRITICAL |

## 8. Location Deep Dives
### [HDR Name] - Root Cause: [Kitchen Speed / Expo / Logistics]
**All Orders:**
| Metric | Actual | Estimated | Variance |
|--------|--------|-----------|----------|
| Queue | X min | X min | +X min |
| Cook | X min | X min | +X min |
| Pack/Bag | X min | X min | +X min |

**1P Delivery:**
| Metric | Value |
|--------|-------|
| Courier Response | X min |
| Kitchen Handoff | X min |
| Delivery Duration | X min |
| Ops Gap | +X min |

**Diagnosis:** [Specific recommendation]

## 9. Follow-Ups
| # | Action | Owner | Due |
|---|--------|-------|-----|
| 1 | [Action Item] | [Name] | [Date] |
| 2 | [Action Item] | [Name] | [Date] |
```

---

## 🆕 OTR Leadership Intelligence Stack

This section provides a **stakeholder-aligned roll-up** that gives each leadership team (Product, Culinary, Ops) exactly what they need to take action. The framework ensures analysis by **population type**, **maturity**, **class**, and **weeks open**.

### Three-Tier Framework

| Tier | Audience | Purpose | Frequency |
|------|----------|---------|-----------|
| **Tier 1** | All Leadership | Executive Snapshot - 30 second read | Weekly |
| **Tier 2** | Domain Teams | Product/Culinary/Ops specific views | Weekly |
| **Tier 3** | Analysts | Deep dive data for exploration | On-demand |

---

## NSO Stabilization Framework

### Understanding New Store Maturation

New Store Openings (NSOs) follow a predictable stabilization curve. Key milestones:

| Phase | Weeks Open | Expected OTR | Expected TT | Characteristics |
|-------|------------|--------------|-------------|-----------------|
| **Launch** | 0-4 | 75-82% | 17-20 min | High variability, learning curve |
| **Ramp** | 5-12 | 82-88% | 15-17 min | Stabilizing, still volatile |
| **Maturing** | 13-24 | 88-92% | 14-15 min | Approaching network norms |
| **Mature** | 25+ | 92%+ | 13-14 min | Stable, benchmark performance |

### Weeks Open Calculation

```sql
-- Use Friends & Family date when available, else opening date
COALESCE(
  calendar_weeks_from_friends_family_start, 
  calendar_weeks_from_opening_date
) AS weeks_open
```

### NSO Stabilization Query

```sql
-- Track OTR and Ticket Time by Weeks Open (Cohort Analysis)
WITH nso_metrics AS (
  SELECT
    COALESCE(h.calendar_weeks_from_friends_family_start, h.calendar_weeks_from_opening_date) AS weeks_open,
    h.hdr_name,
    h.population_type,
    h.hdr_class,
    COUNT(DISTINCT o.order_id) AS total_orders,
    ROUND((1 - SAFE_DIVIDE(
      COUNT(DISTINCT CASE WHEN ot.on_time_issue THEN ot.order_id END),
      COUNT(DISTINCT o.order_id)
    )) * 100, 1) AS otr_pct,
    ROUND((1 - SAFE_DIVIDE(
      COUNT(DISTINCT CASE WHEN ot.on_time_issue AND ot.otr_sla_tier NOT LIKE '%EARLY' THEN ot.order_id END),
      COUNT(DISTINCT o.order_id)
    )) * 100, 1) AS otr_no_earlies_pct,
    ROUND(AVG(o.ticket_time_mins), 1) AS avg_ticket_time,
    ROUND(AVG(o.actual_o2e_mins), 1) AS avg_o2e
  FROM `wonder-dw-prod-brd.orders.hdr_orders` o
  JOIN `wonder-dw-prod-brd.dw.dim_hdrs` h ON o.hdr_id = h.hdr_id
  LEFT JOIN `wonder-dw-prod-brd.orders.hdr_on_time_orders` ot ON o.order_id = ot.order_id
  WHERE o.order_status = 'COMPLETE'
    AND o.brand_category = 'WONDER_HDR'
    AND (o.order_business_type <> 'WONDER_SPOT' OR o.order_business_type IS NULL)
    AND (o.order_business_type <> '3P_PLATFORM_CORPORATE' OR o.order_business_type IS NULL)
    AND o.order_channel IN ('APP', 'WEB', 'IN_PERSON')
    AND o.service_date_et >= DATE_TRUNC(DATE_SUB(CURRENT_DATE('America/New_York'), INTERVAL 1 WEEK), WEEK(MONDAY))
    AND o.service_date_et < DATE_TRUNC(CURRENT_DATE('America/New_York'), WEEK(MONDAY))
    AND COALESCE(h.calendar_weeks_from_friends_family_start, h.calendar_weeks_from_opening_date) IS NOT NULL
  GROUP BY 1, 2, 3, 4
),

-- Calculate network benchmarks by maturity
maturity_benchmarks AS (
  SELECT
    CASE 
      WHEN weeks_open <= 4 THEN 'Launch (0-4 wks)'
      WHEN weeks_open <= 12 THEN 'Ramp (5-12 wks)'
      WHEN weeks_open <= 24 THEN 'Maturing (13-24 wks)'
      ELSE 'Mature (25+ wks)'
    END AS maturity_phase,
    ROUND(AVG(otr_pct), 1) AS phase_avg_otr,
    ROUND(AVG(avg_ticket_time), 1) AS phase_avg_ticket,
    SUM(total_orders) AS phase_orders
  FROM nso_metrics
  GROUP BY 1
)

SELECT
  nm.weeks_open,
  CASE 
    WHEN nm.weeks_open <= 4 THEN 'Launch'
    WHEN nm.weeks_open <= 12 THEN 'Ramp'
    WHEN nm.weeks_open <= 24 THEN 'Maturing'
    ELSE 'Mature'
  END AS phase,
  nm.hdr_name,
  nm.population_type,
  nm.hdr_class,
  nm.total_orders,
  nm.otr_pct,
  nm.otr_no_earlies_pct,
  nm.avg_ticket_time,
  nm.avg_o2e,
  -- Compare to phase benchmark
  ROUND(nm.otr_pct - mb.phase_avg_otr, 1) AS vs_phase_avg,
  CASE
    WHEN nm.otr_pct < mb.phase_avg_otr - 5 THEN '🔴 Below Phase'
    WHEN nm.otr_pct < mb.phase_avg_otr THEN '🟡 Slightly Below'
    WHEN nm.otr_pct >= mb.phase_avg_otr THEN '🟢 On Track'
  END AS stabilization_status
FROM nso_metrics nm
JOIN maturity_benchmarks mb ON 
  CASE 
    WHEN nm.weeks_open <= 4 THEN 'Launch (0-4 wks)'
    WHEN nm.weeks_open <= 12 THEN 'Ramp (5-12 wks)'
    WHEN nm.weeks_open <= 24 THEN 'Maturing (13-24 wks)'
    ELSE 'Mature (25+ wks)'
  END = mb.maturity_phase
ORDER BY nm.weeks_open ASC, nm.otr_pct ASC;
```

### NSO Cohort Trajectory (Weekly Trend by Weeks Open)

```sql
-- Show how each cohort week performs over time
SELECT
  COALESCE(h.calendar_weeks_from_friends_family_start, h.calendar_weeks_from_opening_date) AS weeks_open,
  FORMAT_DATE('%F', DATE_TRUNC(o.service_date_et, WEEK(MONDAY))) AS service_week,
  COUNT(DISTINCT h.hdr_id) AS hdrs_at_this_age,
  COUNT(DISTINCT o.order_id) AS total_orders,
  ROUND((1 - SAFE_DIVIDE(
    COUNT(DISTINCT CASE WHEN ot.on_time_issue THEN ot.order_id END),
    COUNT(DISTINCT o.order_id)
  )) * 100, 1) AS otr_pct,
  ROUND(AVG(o.ticket_time_mins), 1) AS avg_ticket_time
FROM `wonder-dw-prod-brd.orders.hdr_orders` o
JOIN `wonder-dw-prod-brd.dw.dim_hdrs` h ON o.hdr_id = h.hdr_id
LEFT JOIN `wonder-dw-prod-brd.orders.hdr_on_time_orders` ot ON o.order_id = ot.order_id
WHERE o.order_status = 'COMPLETE'
  AND o.brand_category = 'WONDER_HDR'
  AND (o.order_business_type <> 'WONDER_SPOT' OR o.order_business_type IS NULL)
  AND (o.order_business_type <> '3P_PLATFORM_CORPORATE' OR o.order_business_type IS NULL)
  AND o.order_channel IN ('APP', 'WEB', 'IN_PERSON')
  AND o.service_date_et >= DATE_SUB(CURRENT_DATE('America/New_York'), INTERVAL 12 WEEK)
  AND COALESCE(h.calendar_weeks_from_friends_family_start, h.calendar_weeks_from_opening_date) BETWEEN 0 AND 52
GROUP BY 1, 2
HAVING COUNT(DISTINCT o.order_id) >= 50
ORDER BY weeks_open, service_week;
```

---

## Tier 1: Executive Snapshot Queries

### 1A: Network OTR by Maturity and Population Type

```bash
bq query --use_legacy_sql=false --project_id=wonder-dw-prod-brd --format=pretty 'WITH weekly_data AS (SELECT FORMAT_DATE("%F", DATE_TRUNC(o.service_date_et, WEEK(MONDAY))) AS service_week, h.population_type, CASE WHEN COALESCE(h.calendar_weeks_from_friends_family_start, h.calendar_weeks_from_opening_date) <= 12 THEN "NSO/Ramp" ELSE "Mature" END AS maturity, h.hdr_class, COUNT(DISTINCT o.order_id) AS total_orders, ROUND((1 - SAFE_DIVIDE(COUNT(DISTINCT CASE WHEN ot.on_time_issue THEN ot.order_id END), COUNT(DISTINCT o.order_id))) * 100, 1) AS otr_pct, ROUND((1 - SAFE_DIVIDE(COUNT(DISTINCT CASE WHEN ot.on_time_issue AND ot.otr_sla_tier NOT LIKE "%EARLY" THEN ot.order_id END), COUNT(DISTINCT o.order_id))) * 100, 1) AS otr_no_earlies FROM `wonder-dw-prod-brd.orders.hdr_orders` o JOIN `wonder-dw-prod-brd.dw.dim_hdrs` h ON o.hdr_id = h.hdr_id LEFT JOIN `wonder-dw-prod-brd.orders.hdr_on_time_orders` ot ON o.order_id = ot.order_id WHERE o.order_status = "COMPLETE" AND o.brand_category = "WONDER_HDR" AND (o.order_business_type <> "WONDER_SPOT" OR o.order_business_type IS NULL) AND (o.order_business_type <> "3P_PLATFORM_CORPORATE" OR o.order_business_type IS NULL) AND o.order_channel IN ("APP", "WEB", "IN_PERSON") AND o.service_date_et >= DATE_TRUNC(DATE_SUB(CURRENT_DATE("America/New_York"), INTERVAL 1 WEEK), WEEK(MONDAY)) AND o.service_date_et < DATE_TRUNC(CURRENT_DATE("America/New_York"), WEEK(MONDAY)) GROUP BY 1, 2, 3, 4) SELECT population_type, maturity, hdr_class, SUM(total_orders) AS orders, ROUND(SUM(total_orders * otr_pct) / SUM(total_orders), 1) AS weighted_otr, ROUND(SUM(total_orders * otr_no_earlies) / SUM(total_orders), 1) AS weighted_otr_no_earlies FROM weekly_data GROUP BY ROLLUP(1, 2, 3) ORDER BY population_type NULLS FIRST, maturity NULLS FIRST, hdr_class NULLS FIRST'
```

### 1B: Executive Summary with All Dimensions

```bash
bq query --use_legacy_sql=false --project_id=wonder-dw-prod-brd --format=pretty 'SELECT h.population_type, CASE WHEN COALESCE(h.calendar_weeks_from_friends_family_start, h.calendar_weeks_from_opening_date) <= 4 THEN "0-4 wks (Launch)" WHEN COALESCE(h.calendar_weeks_from_friends_family_start, h.calendar_weeks_from_opening_date) <= 12 THEN "5-12 wks (Ramp)" WHEN COALESCE(h.calendar_weeks_from_friends_family_start, h.calendar_weeks_from_opening_date) <= 24 THEN "13-24 wks (Maturing)" ELSE "25+ wks (Mature)" END AS maturity_phase, h.hdr_class, o.dining_option, COUNT(DISTINCT o.order_id) AS orders, ROUND((1 - SAFE_DIVIDE(COUNT(DISTINCT CASE WHEN ot.on_time_issue THEN ot.order_id END), COUNT(DISTINCT o.order_id))) * 100, 1) AS otr_pct, ROUND(AVG(o.ticket_time_mins), 1) AS avg_ticket, ROUND(AVG(CASE WHEN o.dining_option = "DELIVERY" THEN o.actual_o2e_mins END), 1) AS avg_o2e FROM `wonder-dw-prod-brd.orders.hdr_orders` o JOIN `wonder-dw-prod-brd.dw.dim_hdrs` h ON o.hdr_id = h.hdr_id LEFT JOIN `wonder-dw-prod-brd.orders.hdr_on_time_orders` ot ON o.order_id = ot.order_id WHERE o.order_status = "COMPLETE" AND o.brand_category = "WONDER_HDR" AND (o.order_business_type <> "WONDER_SPOT" OR o.order_business_type IS NULL) AND (o.order_business_type <> "3P_PLATFORM_CORPORATE" OR o.order_business_type IS NULL) AND o.order_channel IN ("APP", "WEB", "IN_PERSON") AND o.service_date_et >= DATE_TRUNC(DATE_SUB(CURRENT_DATE("America/New_York"), INTERVAL 1 WEEK), WEEK(MONDAY)) AND o.service_date_et < DATE_TRUNC(CURRENT_DATE("America/New_York"), WEEK(MONDAY)) GROUP BY 1, 2, 3, 4 ORDER BY 1, 2, 3, 4'
```

---

## Tier 2: Domain-Specific Views

### 2A: Product View - ETA & System Performance

**Focus:** ETA accuracy, sequencer impact, model performance

```sql
-- Product Leadership: ETA Accuracy by Component
WITH delivery_orders AS (
  SELECT
    o.order_id,
    h.population_type,
    h.hdr_class,
    CASE 
      WHEN COALESCE(h.calendar_weeks_from_friends_family_start, h.calendar_weeks_from_opening_date) <= 12 
      THEN 'NSO/Ramp' ELSE 'Mature' 
    END AS maturity,
    
    -- Component Actuals vs Estimates
    o.actual_queue_mins,
    o.estimated_queue_mins,
    o.actual_cook_duration_mins,
    o.estimated_cook_duration_mins,
    o.actual_packaging_bagging_mins,
    o.estimated_packaging_bagging_mins,
    o.actual_pickup_waiting_duration_mins AS actual_sit_mins,
    o.estimated_pickup_waiting_duration_mins AS estimated_sit_mins,
    o.actual_transit_mins,
    o.estimated_transit_mins,
    
    -- Ticket Time
    o.ticket_time_mins,
    (COALESCE(o.estimated_queue_mins, 0) + COALESCE(o.estimated_cook_duration_mins, 0) 
     + COALESCE(o.estimated_packaging_bagging_mins, 0)) AS estimated_ticket_mins,
    
    -- OTR
    ot.on_time_issue
    
  FROM `wonder-dw-prod-brd.orders.hdr_orders` o
  JOIN `wonder-dw-prod-brd.dw.dim_hdrs` h ON o.hdr_id = h.hdr_id
  LEFT JOIN `wonder-dw-prod-brd.orders.hdr_on_time_orders` ot ON o.order_id = ot.order_id
  WHERE o.order_status = 'COMPLETE'
    AND o.brand_category = 'WONDER_HDR'
    AND (o.order_business_type <> 'WONDER_SPOT' OR o.order_business_type IS NULL)
    AND (o.order_business_type <> '3P_PLATFORM_CORPORATE' OR o.order_business_type IS NULL)
    AND o.dining_option = 'DELIVERY'
    AND o.order_channel IN ('APP', 'WEB', 'IN_PERSON')
    AND o.service_date_et >= DATE_TRUNC(DATE_SUB(CURRENT_DATE('America/New_York'), INTERVAL 1 WEEK), WEEK(MONDAY))
    AND o.service_date_et < DATE_TRUNC(CURRENT_DATE('America/New_York'), WEEK(MONDAY))
)

SELECT
  'ALL' AS segment,
  COUNT(*) AS orders,
  
  -- Queue Prediction
  ROUND(AVG(actual_queue_mins), 1) AS actual_queue,
  ROUND(AVG(estimated_queue_mins), 1) AS predicted_queue,
  ROUND(AVG(actual_queue_mins) - AVG(estimated_queue_mins), 1) AS queue_variance,
  
  -- Cook Prediction  
  ROUND(AVG(actual_cook_duration_mins), 1) AS actual_cook,
  ROUND(AVG(estimated_cook_duration_mins), 1) AS predicted_cook,
  ROUND(AVG(actual_cook_duration_mins) - AVG(estimated_cook_duration_mins), 1) AS cook_variance,
  
  -- Sit Time Prediction (biggest problem area)
  ROUND(AVG(actual_sit_mins), 1) AS actual_sit,
  ROUND(AVG(estimated_sit_mins), 1) AS predicted_sit,
  ROUND(AVG(actual_sit_mins) - AVG(estimated_sit_mins), 1) AS sit_variance,
  
  -- Transit Prediction
  ROUND(AVG(actual_transit_mins), 1) AS actual_transit,
  ROUND(AVG(estimated_transit_mins), 1) AS predicted_transit,
  ROUND(AVG(actual_transit_mins) - AVG(estimated_transit_mins), 1) AS transit_variance,
  
  -- Ticket Time (Total Kitchen)
  ROUND(AVG(ticket_time_mins), 1) AS actual_ticket,
  ROUND(AVG(estimated_ticket_mins), 1) AS predicted_ticket,
  ROUND(AVG(ticket_time_mins) - AVG(estimated_ticket_mins), 1) AS ticket_variance

FROM delivery_orders

UNION ALL

-- Break out by Population Type
SELECT
  population_type AS segment,
  COUNT(*),
  ROUND(AVG(actual_queue_mins), 1), ROUND(AVG(estimated_queue_mins), 1), ROUND(AVG(actual_queue_mins) - AVG(estimated_queue_mins), 1),
  ROUND(AVG(actual_cook_duration_mins), 1), ROUND(AVG(estimated_cook_duration_mins), 1), ROUND(AVG(actual_cook_duration_mins) - AVG(estimated_cook_duration_mins), 1),
  ROUND(AVG(actual_sit_mins), 1), ROUND(AVG(estimated_sit_mins), 1), ROUND(AVG(actual_sit_mins) - AVG(estimated_sit_mins), 1),
  ROUND(AVG(actual_transit_mins), 1), ROUND(AVG(estimated_transit_mins), 1), ROUND(AVG(actual_transit_mins) - AVG(estimated_transit_mins), 1),
  ROUND(AVG(ticket_time_mins), 1), ROUND(AVG(estimated_ticket_mins), 1), ROUND(AVG(ticket_time_mins) - AVG(estimated_ticket_mins), 1)
FROM delivery_orders
GROUP BY 1

UNION ALL

-- Break out by Maturity
SELECT
  maturity AS segment,
  COUNT(*),
  ROUND(AVG(actual_queue_mins), 1), ROUND(AVG(estimated_queue_mins), 1), ROUND(AVG(actual_queue_mins) - AVG(estimated_queue_mins), 1),
  ROUND(AVG(actual_cook_duration_mins), 1), ROUND(AVG(estimated_cook_duration_mins), 1), ROUND(AVG(actual_cook_duration_mins) - AVG(estimated_cook_duration_mins), 1),
  ROUND(AVG(actual_sit_mins), 1), ROUND(AVG(estimated_sit_mins), 1), ROUND(AVG(actual_sit_mins) - AVG(estimated_sit_mins), 1),
  ROUND(AVG(actual_transit_mins), 1), ROUND(AVG(estimated_transit_mins), 1), ROUND(AVG(actual_transit_mins) - AVG(estimated_transit_mins), 1),
  ROUND(AVG(ticket_time_mins), 1), ROUND(AVG(estimated_ticket_mins), 1), ROUND(AVG(ticket_time_mins) - AVG(estimated_ticket_mins), 1)
FROM delivery_orders
GROUP BY 1

ORDER BY segment;
```

### 2B: Culinary View - Kitchen Execution

**Focus:** Kitchen execution, ticket time, cookbook targets, IPC impact

```sql
-- Culinary Leadership: Kitchen Execution by Tier
WITH orders_with_ipc AS (
  SELECT
    o.order_id,
    o.hdr_id,
    h.hdr_name,
    h.population_type,
    h.hdr_class,
    CASE 
      WHEN COALESCE(h.calendar_weeks_from_friends_family_start, h.calendar_weeks_from_opening_date) <= 4 THEN '0-4 wks'
      WHEN COALESCE(h.calendar_weeks_from_friends_family_start, h.calendar_weeks_from_opening_date) <= 12 THEN '5-12 wks'
      WHEN COALESCE(h.calendar_weeks_from_friends_family_start, h.calendar_weeks_from_opening_date) <= 24 THEN '13-24 wks'
      ELSE '25+ wks'
    END AS weeks_open_bucket,
    o.ticket_time_mins,
    o.actual_queue_mins,
    o.actual_cook_duration_mins,
    o.actual_packaging_bagging_mins,
    o.ready_for_pickup_sla_difference,
    o.items_per_check,
    ot.on_time_issue
  FROM `wonder-dw-prod-brd.orders.hdr_orders` o
  JOIN `wonder-dw-prod-brd.dw.dim_hdrs` h ON o.hdr_id = h.hdr_id
  LEFT JOIN `wonder-dw-prod-brd.orders.hdr_on_time_orders` ot ON o.order_id = ot.order_id
  WHERE o.order_status = 'COMPLETE'
    AND o.brand_category = 'WONDER_HDR'
    AND (o.order_business_type <> 'WONDER_SPOT' OR o.order_business_type IS NULL)
    AND (o.order_business_type <> '3P_PLATFORM_CORPORATE' OR o.order_business_type IS NULL)
    AND o.order_channel IN ('APP', 'WEB', 'IN_PERSON')
    AND o.service_date_et >= DATE_TRUNC(DATE_SUB(CURRENT_DATE('America/New_York'), INTERVAL 1 WEEK), WEEK(MONDAY))
    AND o.service_date_et < DATE_TRUNC(CURRENT_DATE('America/New_York'), WEEK(MONDAY))
)

-- By Population Type
SELECT
  'By Population' AS analysis_type,
  population_type AS dimension,
  COUNT(*) AS orders,
  ROUND(AVG(ticket_time_mins), 1) AS avg_ticket,
  ROUND(AVG(actual_queue_mins), 1) AS avg_queue,
  ROUND(AVG(actual_cook_duration_mins), 1) AS avg_cook,
  ROUND(AVG(actual_packaging_bagging_mins), 1) AS avg_pack_bag,
  -- Kitchen Process OTR (hitting expected ready for pickup)
  ROUND(AVG(CASE WHEN ready_for_pickup_sla_difference <= 2 THEN 1 ELSE 0 END) * 100, 1) AS kitchen_process_otr,
  ROUND(AVG(items_per_check), 1) AS avg_ipc
FROM orders_with_ipc
GROUP BY 1, 2

UNION ALL

-- By Weeks Open
SELECT
  'By Maturity' AS analysis_type,
  weeks_open_bucket AS dimension,
  COUNT(*),
  ROUND(AVG(ticket_time_mins), 1),
  ROUND(AVG(actual_queue_mins), 1),
  ROUND(AVG(actual_cook_duration_mins), 1),
  ROUND(AVG(actual_packaging_bagging_mins), 1),
  ROUND(AVG(CASE WHEN ready_for_pickup_sla_difference <= 2 THEN 1 ELSE 0 END) * 100, 1),
  ROUND(AVG(items_per_check), 1)
FROM orders_with_ipc
GROUP BY 1, 2

UNION ALL

-- By Class
SELECT
  'By Class' AS analysis_type,
  hdr_class AS dimension,
  COUNT(*),
  ROUND(AVG(ticket_time_mins), 1),
  ROUND(AVG(actual_queue_mins), 1),
  ROUND(AVG(actual_cook_duration_mins), 1),
  ROUND(AVG(actual_packaging_bagging_mins), 1),
  ROUND(AVG(CASE WHEN ready_for_pickup_sla_difference <= 2 THEN 1 ELSE 0 END) * 100, 1),
  ROUND(AVG(items_per_check), 1)
FROM orders_with_ipc
GROUP BY 1, 2

UNION ALL

-- By IPC (Order Size)
SELECT
  'By Order Size' AS analysis_type,
  CASE 
    WHEN items_per_check = 1 THEN '1 item'
    WHEN items_per_check BETWEEN 2 AND 3 THEN '2-3 items'
    WHEN items_per_check BETWEEN 4 AND 5 THEN '4-5 items'
    ELSE '6+ items'
  END AS dimension,
  COUNT(*),
  ROUND(AVG(ticket_time_mins), 1),
  ROUND(AVG(actual_queue_mins), 1),
  ROUND(AVG(actual_cook_duration_mins), 1),
  ROUND(AVG(actual_packaging_bagging_mins), 1),
  ROUND(AVG(CASE WHEN ready_for_pickup_sla_difference <= 2 THEN 1 ELSE 0 END) * 100, 1),
  ROUND(AVG(items_per_check), 1)
FROM orders_with_ipc
GROUP BY 1, 2

ORDER BY analysis_type, dimension;
```

### 2C: Ops View - Location Execution & Root Cause

**Focus:** Location performance, root cause attribution, reason codes

```sql
-- Ops Leadership: Location Performance with Root Cause
WITH late_orders AS (
  SELECT
    o.order_id,
    h.hdr_id,
    h.hdr_name,
    h.population_type,
    h.hdr_class,
    COALESCE(h.calendar_weeks_from_friends_family_start, h.calendar_weeks_from_opening_date) AS weeks_open,
    o.dining_option,
    o.ready_for_pickup_sla_difference,
    o.courier_response_time_mins,
    o.kitchen_handoff_time_mins,
    o.actual_transit_mins,
    o.delivery_sla_difference,
    ot.on_time_issue,
    ot.otr_sla_tier,
    
    -- Root Cause Attribution
    CASE
      WHEN o.ready_for_pickup_sla_difference > 5.0 THEN 'KITCHEN_PRIMARY'
      WHEN o.ready_for_pickup_sla_difference > 2.0 THEN 'KITCHEN_CONTRIBUTING'
      WHEN o.ready_for_pickup_sla_difference <= 2.0 AND o.courier_response_time_mins > 10 THEN 'LOGISTICS_PRIMARY'
      WHEN o.ready_for_pickup_sla_difference <= 2.0 AND o.kitchen_handoff_time_mins > 8 THEN 'HANDOFF_PRIMARY'
      ELSE 'OTHER'
    END AS root_cause,
    
    -- Reason Code Priority
    CASE
      -- Early orders
      WHEN o.delivery_sla_difference < -9 THEN 'EARLY_ORDER'
      -- Kitchen delays (check upstream first)
      WHEN o.ready_for_pickup_sla_difference > 5.0 THEN 'LATE_COOK'
      WHEN o.ready_for_pickup_sla_difference > 2.0 AND o.actual_queue_mins > 5 THEN 'LATE_QUEUE'
      -- Handoff delays (only if kitchen was on time)
      WHEN o.ready_for_pickup_sla_difference <= 2.0 AND o.kitchen_handoff_time_mins > 8 THEN 'LATE_PICKUP'
      -- Logistics delays (only if kitchen + handoff were on time)
      WHEN o.ready_for_pickup_sla_difference <= 2.0 AND o.courier_response_time_mins > 10 THEN 'LATE_DELIVERY'
      ELSE 'OTHER'
    END AS reason_code

  FROM `wonder-dw-prod-brd.orders.hdr_orders` o
  JOIN `wonder-dw-prod-brd.dw.dim_hdrs` h ON o.hdr_id = h.hdr_id
  LEFT JOIN `wonder-dw-prod-brd.orders.hdr_on_time_orders` ot ON o.order_id = ot.order_id
  WHERE o.order_status = 'COMPLETE'
    AND o.brand_category = 'WONDER_HDR'
    AND (o.order_business_type <> 'WONDER_SPOT' OR o.order_business_type IS NULL)
    AND (o.order_business_type <> '3P_PLATFORM_CORPORATE' OR o.order_business_type IS NULL)
    AND o.dining_option = 'DELIVERY'
    AND o.order_channel IN ('APP', 'WEB', 'IN_PERSON')
    AND o.service_date_et >= DATE_TRUNC(DATE_SUB(CURRENT_DATE('America/New_York'), INTERVAL 1 WEEK), WEEK(MONDAY))
    AND o.service_date_et < DATE_TRUNC(CURRENT_DATE('America/New_York'), WEEK(MONDAY))
)

SELECT
  hdr_name,
  population_type,
  hdr_class,
  weeks_open,
  CASE 
    WHEN weeks_open <= 4 THEN 'Launch'
    WHEN weeks_open <= 12 THEN 'Ramp'
    WHEN weeks_open <= 24 THEN 'Maturing'
    ELSE 'Mature'
  END AS maturity,
  COUNT(*) AS total_orders,
  COUNT(CASE WHEN on_time_issue THEN 1 END) AS imperfect_orders,
  ROUND((1 - SAFE_DIVIDE(COUNT(CASE WHEN on_time_issue THEN 1 END), COUNT(*))) * 100, 1) AS otr_pct,
  
  -- Root Cause Breakdown (% of late orders)
  ROUND(AVG(CASE WHEN on_time_issue AND root_cause = 'KITCHEN_PRIMARY' THEN 1 ELSE 0 END) * 100, 0) AS pct_kitchen,
  ROUND(AVG(CASE WHEN on_time_issue AND root_cause = 'HANDOFF_PRIMARY' THEN 1 ELSE 0 END) * 100, 0) AS pct_handoff,
  ROUND(AVG(CASE WHEN on_time_issue AND root_cause = 'LOGISTICS_PRIMARY' THEN 1 ELSE 0 END) * 100, 0) AS pct_logistics,
  
  -- Timing Metrics
  ROUND(AVG(ready_for_pickup_sla_difference), 1) AS avg_kitchen_delay,
  ROUND(AVG(courier_response_time_mins), 1) AS avg_courier_resp,
  ROUND(AVG(kitchen_handoff_time_mins), 1) AS avg_handoff,
  ROUND(AVG(kitchen_handoff_time_mins) - AVG(courier_response_time_mins), 1) AS ops_gap,
  
  -- Primary Issue Diagnosis
  CASE
    WHEN AVG(ready_for_pickup_sla_difference) > 5 THEN '🔧 Kitchen Slow'
    WHEN AVG(kitchen_handoff_time_mins) > AVG(courier_response_time_mins) + 3 THEN '🔧 Slow Handoff'
    WHEN AVG(courier_response_time_mins) > 10 THEN '🚗 Driver Shortage'
    ELSE '✅ Balanced'
  END AS primary_issue

FROM late_orders
GROUP BY 1, 2, 3, 4, 5
HAVING COUNT(*) >= 30
ORDER BY otr_pct ASC
LIMIT 30;
```

---

## Dimension Breakdown Queries

### By Population Type (Urban/Suburban/Big Box)

```bash
bq query --use_legacy_sql=false --project_id=wonder-dw-prod-brd --format=pretty 'SELECT h.population_type, COUNT(DISTINCT o.order_id) AS orders, ROUND((1 - SAFE_DIVIDE(COUNT(DISTINCT CASE WHEN ot.on_time_issue THEN ot.order_id END), COUNT(DISTINCT o.order_id))) * 100, 1) AS otr_pct, ROUND(AVG(o.ticket_time_mins), 1) AS avg_ticket, ROUND(AVG(o.actual_o2e_mins), 1) AS avg_o2e, ROUND(AVG(CASE WHEN o.ready_for_pickup_sla_difference <= 2 THEN 1 ELSE 0 END) * 100, 1) AS kitchen_process_otr FROM `wonder-dw-prod-brd.orders.hdr_orders` o JOIN `wonder-dw-prod-brd.dw.dim_hdrs` h ON o.hdr_id = h.hdr_id LEFT JOIN `wonder-dw-prod-brd.orders.hdr_on_time_orders` ot ON o.order_id = ot.order_id WHERE o.order_status = "COMPLETE" AND o.brand_category = "WONDER_HDR" AND (o.order_business_type <> "WONDER_SPOT" OR o.order_business_type IS NULL) AND (o.order_business_type <> "3P_PLATFORM_CORPORATE" OR o.order_business_type IS NULL) AND o.order_channel IN ("APP", "WEB", "IN_PERSON") AND o.dining_option = "DELIVERY" AND o.service_date_et >= DATE_TRUNC(DATE_SUB(CURRENT_DATE("America/New_York"), INTERVAL 1 WEEK), WEEK(MONDAY)) AND o.service_date_et < DATE_TRUNC(CURRENT_DATE("America/New_York"), WEEK(MONDAY)) GROUP BY 1 ORDER BY orders DESC'
```

### By HDR Class

```bash
bq query --use_legacy_sql=false --project_id=wonder-dw-prod-brd --format=pretty 'SELECT h.hdr_class, COUNT(DISTINCT o.order_id) AS orders, ROUND((1 - SAFE_DIVIDE(COUNT(DISTINCT CASE WHEN ot.on_time_issue THEN ot.order_id END), COUNT(DISTINCT o.order_id))) * 100, 1) AS otr_pct, ROUND(AVG(o.ticket_time_mins), 1) AS avg_ticket, ROUND(AVG(o.actual_o2e_mins), 1) AS avg_o2e FROM `wonder-dw-prod-brd.orders.hdr_orders` o JOIN `wonder-dw-prod-brd.dw.dim_hdrs` h ON o.hdr_id = h.hdr_id LEFT JOIN `wonder-dw-prod-brd.orders.hdr_on_time_orders` ot ON o.order_id = ot.order_id WHERE o.order_status = "COMPLETE" AND o.brand_category = "WONDER_HDR" AND (o.order_business_type <> "WONDER_SPOT" OR o.order_business_type IS NULL) AND (o.order_business_type <> "3P_PLATFORM_CORPORATE" OR o.order_business_type IS NULL) AND o.order_channel IN ("APP", "WEB", "IN_PERSON") AND o.dining_option = "DELIVERY" AND o.service_date_et >= DATE_TRUNC(DATE_SUB(CURRENT_DATE("America/New_York"), INTERVAL 1 WEEK), WEEK(MONDAY)) AND o.service_date_et < DATE_TRUNC(CURRENT_DATE("America/New_York"), WEEK(MONDAY)) GROUP BY 1 ORDER BY orders DESC'
```

### By Maturity Phase (Weeks Open)

```bash
bq query --use_legacy_sql=false --project_id=wonder-dw-prod-brd --format=pretty 'SELECT CASE WHEN COALESCE(h.calendar_weeks_from_friends_family_start, h.calendar_weeks_from_opening_date) <= 4 THEN "0-4 wks (Launch)" WHEN COALESCE(h.calendar_weeks_from_friends_family_start, h.calendar_weeks_from_opening_date) <= 12 THEN "5-12 wks (Ramp)" WHEN COALESCE(h.calendar_weeks_from_friends_family_start, h.calendar_weeks_from_opening_date) <= 24 THEN "13-24 wks (Maturing)" ELSE "25+ wks (Mature)" END AS maturity_phase, COUNT(DISTINCT h.hdr_id) AS hdr_count, COUNT(DISTINCT o.order_id) AS orders, ROUND((1 - SAFE_DIVIDE(COUNT(DISTINCT CASE WHEN ot.on_time_issue THEN ot.order_id END), COUNT(DISTINCT o.order_id))) * 100, 1) AS otr_pct, ROUND((1 - SAFE_DIVIDE(COUNT(DISTINCT CASE WHEN ot.on_time_issue AND ot.otr_sla_tier NOT LIKE "%EARLY" THEN ot.order_id END), COUNT(DISTINCT o.order_id))) * 100, 1) AS otr_no_earlies, ROUND(AVG(o.ticket_time_mins), 1) AS avg_ticket, ROUND(AVG(o.actual_o2e_mins), 1) AS avg_o2e, ROUND(AVG(CASE WHEN o.ready_for_pickup_sla_difference <= 2 THEN 1 ELSE 0 END) * 100, 1) AS kitchen_process_otr FROM `wonder-dw-prod-brd.orders.hdr_orders` o JOIN `wonder-dw-prod-brd.dw.dim_hdrs` h ON o.hdr_id = h.hdr_id LEFT JOIN `wonder-dw-prod-brd.orders.hdr_on_time_orders` ot ON o.order_id = ot.order_id WHERE o.order_status = "COMPLETE" AND o.brand_category = "WONDER_HDR" AND (o.order_business_type <> "WONDER_SPOT" OR o.order_business_type IS NULL) AND (o.order_business_type <> "3P_PLATFORM_CORPORATE" OR o.order_business_type IS NULL) AND o.order_channel IN ("APP", "WEB", "IN_PERSON") AND o.dining_option = "DELIVERY" AND o.service_date_et >= DATE_TRUNC(DATE_SUB(CURRENT_DATE("America/New_York"), INTERVAL 1 WEEK), WEEK(MONDAY)) AND o.service_date_et < DATE_TRUNC(CURRENT_DATE("America/New_York"), WEEK(MONDAY)) GROUP BY 1 ORDER BY 1'
```

### Cross-Dimensional Analysis (Population × Maturity)

```bash
bq query --use_legacy_sql=false --project_id=wonder-dw-prod-brd --format=pretty 'SELECT h.population_type, CASE WHEN COALESCE(h.calendar_weeks_from_friends_family_start, h.calendar_weeks_from_opening_date) <= 12 THEN "NSO/Ramp" ELSE "Mature" END AS maturity, COUNT(DISTINCT h.hdr_id) AS hdr_count, COUNT(DISTINCT o.order_id) AS orders, ROUND((1 - SAFE_DIVIDE(COUNT(DISTINCT CASE WHEN ot.on_time_issue THEN ot.order_id END), COUNT(DISTINCT o.order_id))) * 100, 1) AS otr_pct, ROUND(AVG(o.ticket_time_mins), 1) AS avg_ticket, ROUND(AVG(o.actual_o2e_mins), 1) AS avg_o2e, ROUND(AVG(o.kitchen_handoff_time_mins), 1) AS avg_handoff, ROUND(AVG(o.courier_response_time_mins), 1) AS avg_courier FROM `wonder-dw-prod-brd.orders.hdr_orders` o JOIN `wonder-dw-prod-brd.dw.dim_hdrs` h ON o.hdr_id = h.hdr_id LEFT JOIN `wonder-dw-prod-brd.orders.hdr_on_time_orders` ot ON o.order_id = ot.order_id WHERE o.order_status = "COMPLETE" AND o.brand_category = "WONDER_HDR" AND (o.order_business_type <> "WONDER_SPOT" OR o.order_business_type IS NULL) AND (o.order_business_type <> "3P_PLATFORM_CORPORATE" OR o.order_business_type IS NULL) AND o.order_channel IN ("APP", "WEB", "IN_PERSON") AND o.dining_option = "DELIVERY" AND o.service_date_et >= DATE_TRUNC(DATE_SUB(CURRENT_DATE("America/New_York"), INTERVAL 1 WEEK), WEEK(MONDAY)) AND o.service_date_et < DATE_TRUNC(CURRENT_DATE("America/New_York"), WEEK(MONDAY)) GROUP BY 1, 2 ORDER BY 1, 2'
```

---

## Complete Leadership Report Template (With All Dimensions)

```markdown
# 📊 Weekly OTR Leadership Report - Week of [DATE]

---

## 🎯 TL;DR (30-Second Executive Summary)

| Metric | This Week | vs Last Week | Target | Status |
|--------|-----------|--------------|--------|--------|
| **Network OTR** | X% | +/- X pts | 94% | 🟢/🟡/🔴 |
| **OTR (No Earlies)** | X% | +/- X pts | 97% | 🟢/🟡/🔴 |
| **Kitchen Process OTR** | X% | - | 90% | 🟢/🟡/🔴 |
| **Avg Ticket Time** | X min | +/- X min | 13 min | 🟢/🟡/🔴 |

**Top 3 Opportunities:**
1. **[OPS]** [Specific HDR]: [Specific issue] → [Action]
2. **[PRODUCT]** [System issue]: [Impact] → [Action]
3. **[LOGISTICS]** [Specific HDR]: [Issue] → [Action]

---

## 📈 Dimension Breakdown

### By Population Type
| Population | Orders | OTR | Ticket Time | O2E | Status |
|------------|--------|-----|-------------|-----|--------|
| Urban | X | X% | X min | X min | |
| Suburban | X | X% | X min | X min | |
| Big Box | X | X% | X min | X min | |

### By Maturity Phase
| Phase | HDRs | Orders | OTR | OTR (No Early) | Ticket | Kitchen OTR |
|-------|------|--------|-----|----------------|--------|-------------|
| Launch (0-4 wks) | X | X | X% | X% | X min | X% |
| Ramp (5-12 wks) | X | X | X% | X% | X min | X% |
| Maturing (13-24 wks) | X | X | X% | X% | X min | X% |
| Mature (25+ wks) | X | X | X% | X% | X min | X% |

### By HDR Class
| Class | Orders | OTR | Ticket Time | Primary Issue |
|-------|--------|-----|-------------|---------------|
| 2025 New | X | X% | X min | |
| Class B | X | X% | X min | |
| ... | | | | |

### Cross-Cut: Population × Maturity
| | NSO/Ramp OTR | Mature OTR | Gap |
|---|-------------|------------|-----|
| Urban | X% | X% | X pts |
| Suburban | X% | X% | X pts |
| Big Box | X% | X% | X pts |

---

## 📱 Product Focus: ETA & System Performance

### Prediction Accuracy by Component
| Component | Actual | Predicted | Variance | Impact | Action |
|-----------|--------|-----------|----------|--------|--------|
| Queue | X min | X min | +X min | 🟡 | Monitor |
| Cook | X min | X min | +X min | 🟢 | OK |
| Pack/Bag | X min | X min | +X min | 🟢 | OK |
| **Sit Time** | X min | X min | **+X min** | 🔴 | **Fix** |
| Transit | X min | X min | +X min | 🟢 | OK |

**Key Insight:** Sit time consistently under-predicted by X mins. 
- Primary driver: [Courier response / Handoff delays]
- Sequencer potential savings: X min if removed

### Sequencer & Hot Hold Analysis
- Hot hold compliance: X%
- ALM item mis-classification rate: X%
- Sequencer delay impact: +X min to ticket time

---

## 🍳 Culinary Focus: Kitchen Execution

### Ticket Time by Order Size (IPC)
| IPC | Orders | % of Total | Avg Ticket | Δ from Base |
|-----|--------|------------|------------|-------------|
| 1 item | X | X% | X min | -X min |
| 2-3 items | X | X% | X min | baseline |
| 4-5 items | X | X% | X min | +X min |
| 6+ items | X | X% | X min | +X min |

### Kitchen Process OTR (Hitting Expected Ready for Pickup)
| Segment | Kitchen OTR | Customer OTR | Gap | Implication |
|---------|-------------|--------------|-----|-------------|
| ALL | X% | X% | X pts | Courier saves X% |
| NSO/Ramp | X% | X% | X pts | |
| Mature | X% | X% | X pts | |

### Force Complete Analysis
- Network FC rate: X%
- Premature FC rate: X% (problematic)
- Locations with >20% FC: [List HDRs]

---

## 🏪 Ops Focus: Location Execution

### Root Cause Breakdown (Late Orders Only)
| Root Cause | % of Late | Volume | Owner |
|------------|-----------|--------|-------|
| Kitchen Slow | X% | X | Ops |
| Slow Handoff | X% | X | Ops |
| Driver Late | X% | X | Logistics |
| Transit Slow | X% | X | Logistics |

### NSO Stabilization Status
| HDR | Weeks Open | Phase | OTR | vs Phase Avg | Status |
|-----|------------|-------|-----|--------------|--------|
| [HDR] | X | Launch | X% | -X pts | 🔴 Below Phase |
| [HDR] | X | Ramp | X% | +X pts | 🟢 On Track |

**NSO Summary:**
- X HDRs in Launch phase (avg OTR: X%)
- X HDRs in Ramp phase (avg OTR: X%)
- Expected stabilization: Week X for [HDRs]

### Location Spotlights

#### Profile A: Ops Failures 🔧 (Audit Expo)
| HDR | Pop Type | Class | Wks Open | Courier | Handoff | Ops Gap |
|-----|----------|-------|----------|---------|---------|---------|
| | | | | X min | X min | +X |

#### Profile B: Logistics Failures 🚗 (Driver Incentives)
| HDR | Pop Type | Class | Wks Open | Courier | Handoff | Gap |
|-----|----------|-------|----------|---------|---------|-----|
| | | | | X min | X min | -X |

---

## 🔴 Chronic Underperformers (Deep Dive Candidates)

| HDR | Pop Type | Class | Wks Open | Wks on List | Avg O2E | Primary Issue | Priority |
|-----|----------|-------|----------|-------------|---------|---------------|----------|
| | | | | | | | 🔴 CRITICAL |
| | | | | | | | 🟠 HIGH |

---

## 📋 Follow-Ups

| # | Action | Owner | Focus | Due |
|---|--------|-------|-------|-----|
| 1 | Audit Expo at [Profile A HDRs] | Regional Ops | Fake bumping | |
| 2 | Courier incentives for [Profile B HDRs] | Logistics | Driver supply | |
| 3 | NSO coaching for [Launch HDRs] | Training | Stabilization | |
| 4 | Review sit time prediction | Product | ETA accuracy | |
```

---

## Best Practices

### 1. Always Use DISTINCT for Order Counts

When joining `hdr_orders` to other tables, rows multiply. Always use `COUNT(DISTINCT order_id)`:

```sql
-- WRONG: Inflated counts
COUNT(order_id)

-- RIGHT: Accurate counts
COUNT(DISTINCT order_id)
```

### 2. Filter to COMPLETE Orders

OTR analysis should only include completed orders:

```sql
WHERE order_status = 'COMPLETE'
```

### 3. Filter to WONDER_HDR Brand Category

Exclude Wonder Spot and other business types for standard OTR:

```sql
WHERE brand_category = 'WONDER_HDR'
```

### 4. Use SAFE_DIVIDE for Rate Calculations

Prevent division by zero errors:

```sql
SAFE_DIVIDE(numerator, denominator)
```

### 5. Pickup vs Delivery Have Different Profiles

- **Pickup**: ~96% OTR, no logistics component
- **Delivery**: ~86% OTR, includes courier timing

Always segment by `dining_option` when analyzing.

### 6. Interpret Error Signs Correctly

- **Negative error** = LATE (actual > predicted)
- **Positive error** = EARLY/FAST (actual < predicted)

### 7. Week-over-Week Comparisons

Use consistent week definitions:

```sql
DATE_TRUNC(service_date_et, WEEK(MONDAY))
```

### 8. Volume-Weight Aggregations

When comparing across segments with different volumes, weight averages:

```sql
SUM(order_count * otr_rate) / SUM(order_count)
```

---

## Labor vs Production Volume Analysis

> ⚠️ **Data Access Caveat**: The labor data in `wonder-fin-prod.profit_loss_order_report.daily_labor_by_location_summary` may be access-restricted. This section documents the analysis framework for when access is available.

### Purpose
Determine if labor hours are properly distributed relative to production volume (expected cook/ticket time) across design types. D5 locations are larger square footage and should theoretically handle more volume but need proportionally more labor.

### Production Volume Distribution by Design Type

Based on recent data, production volume distributes as follows:

| Design | HDRs | % Orders | % Expected Cook | Avg Orders/HDR/Week | Notes |
|--------|------|----------|-----------------|---------------------|-------|
| **D1** | 3 | 1.2% | 0.9% | ~280 | Big Box, lowest complexity |
| **D2** | 2 | 1.2% | 1.1% | ~160 | Mixed |
| **D3** | 66 | 71.3% | 72.0% | ~740 | Core network |
| **D4** | 14 | 14.7% | 14.6% | ~720 | Similar to D3 |
| **D5** | 8 | **11.6%** | **11.4%** | **~1,000** | Largest, 35% more volume/HDR |

**Key Insight**: D5s handle ~35% more orders per location than D3s, but expected cook time per order is slightly LOWER (10.0 vs 10.4 mins) - likely due to simpler order mix at high-volume locations.

### Production Volume Query (Always Accessible)

```sql
-- Production Volume Distribution by Design Type
SELECT
  h.design_type,
  h.population_type,
  COUNT(DISTINCT h.hdr_id) AS hdr_count,
  SUM(total_orders) AS total_orders,
  ROUND(SUM(total_orders) * 100.0 / SUM(SUM(total_orders)) OVER(), 1) AS pct_of_orders,
  ROUND(SUM(total_expected_cook_mins) / 60, 0) AS expected_cook_hrs,
  ROUND(SUM(total_expected_cook_mins) * 100.0 / SUM(SUM(total_expected_cook_mins)) OVER(), 1) AS pct_of_expected_cook,
  ROUND(AVG(total_orders), 0) AS avg_orders_per_hdr,
  ROUND(AVG(avg_ticket_time), 1) AS avg_ticket_time
FROM (
  SELECT
    o.hdr_id,
    COUNT(DISTINCT o.order_id) AS total_orders,
    SUM(COALESCE(o.estimated_cook_duration_mins, 0)) AS total_expected_cook_mins,
    AVG(o.ticket_time_mins) AS avg_ticket_time
  FROM `wonder-dw-prod-brd.orders.hdr_orders` o
  WHERE o.order_status = 'COMPLETE'
    AND o.brand_category = 'WONDER_HDR'
    AND (o.order_business_type <> 'WONDER_SPOT' OR o.order_business_type IS NULL)
    AND (o.order_business_type <> '3P_PLATFORM_CORPORATE' OR o.order_business_type IS NULL)
    AND o.order_channel IN ('APP', 'WEB', 'IN_PERSON')
    AND o.service_date_et >= DATE_TRUNC(DATE_SUB(CURRENT_DATE('America/New_York'), INTERVAL 4 WEEK), WEEK(MONDAY))
    AND o.service_date_et < DATE_TRUNC(CURRENT_DATE('America/New_York'), WEEK(MONDAY))
  GROUP BY 1
) prod
JOIN `wonder-dw-prod-brd.dw.dim_hdrs` h ON prod.hdr_id = h.hdr_id
GROUP BY 1, 2
ORDER BY 1, 2;
```

### Labor vs Production Efficiency Query (Requires Labor Data Access)

```sql
-- ⚠️ REQUIRES ACCESS TO: wonder-fin-prod.profit_loss_order_report.daily_labor_by_location_summary

WITH labor_by_hdr_week AS (
  SELECT
    FORMAT_TIMESTAMP('%F', TIMESTAMP_TRUNC(TIMESTAMP(l.pay_date), WEEK(MONDAY))) AS service_week,
    d.hdr_id,
    d.hdr_name,
    d.design_type,
    d.population_type,
    SUM(CASE WHEN l.is_earnings AND l.pay_type = 'Hourly' THEN l.total_hours ELSE 0 END) AS hourly_labor_hours,
    SUM(l.total_hours) AS total_labor_hours,
    SUM(CASE WHEN l.pay_type = 'Hourly' THEN l.total_cost * -1 ELSE 0 END) AS hourly_labor_cost
  FROM `wonder-fin-prod.profit_loss_order_report.daily_labor_by_location_summary` l
  LEFT JOIN `wonder-fin-prod.profit_loss_order_report_seeds.location_mapping_v2` loc 
    ON UPPER(loc.dayforce_key) = UPPER(l.business_location)
  LEFT JOIN `wonder-dw-prod-brd.dw.dim_hdrs` d ON loc.oms_key = d.hdr_id
  WHERE l.pay_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 8 WEEK)
    AND l.pay_date < DATE_TRUNC(CURRENT_DATE(), WEEK(MONDAY))
    AND (l.sub_department <> 'Crr Ops' OR l.sub_department IS NULL)
    AND (l.sub_department <> 'Delivery By Wonder' OR l.sub_department IS NULL)
    AND (l.sub_department_2 <> 'Courier Ops' OR l.sub_department_2 IS NULL)
    AND (l.training_flag IS NULL OR CAST(l.training_flag AS BOOL) = FALSE)
    AND d.hdr_id IS NOT NULL
  GROUP BY 1, 2, 3, 4, 5
),

production_by_hdr_week AS (
  SELECT
    FORMAT_DATE('%F', DATE_TRUNC(o.service_date_et, WEEK(MONDAY))) AS service_week,
    o.hdr_id,
    COUNT(DISTINCT o.order_id) AS total_orders,
    SUM(COALESCE(o.estimated_cook_duration_mins, 0)) / 60 AS expected_cook_hrs,
    SUM(COALESCE(o.ticket_time_mins, 0)) / 60 AS actual_ticket_hrs
  FROM `wonder-dw-prod-brd.orders.hdr_orders` o
  WHERE o.order_status = 'COMPLETE'
    AND o.brand_category = 'WONDER_HDR'
    AND (o.order_business_type <> 'WONDER_SPOT' OR o.order_business_type IS NULL)
    AND o.order_channel IN ('APP', 'WEB', 'IN_PERSON')
    AND o.service_date_et >= DATE_SUB(CURRENT_DATE(), INTERVAL 8 WEEK)
    AND o.service_date_et < DATE_TRUNC(CURRENT_DATE(), WEEK(MONDAY))
  GROUP BY 1, 2
)

SELECT
  l.design_type,
  l.population_type,
  COUNT(DISTINCT l.hdr_id) AS hdr_count,
  
  -- Volume
  SUM(p.total_orders) AS total_orders,
  ROUND(SUM(p.total_orders) * 100.0 / SUM(SUM(p.total_orders)) OVER(), 1) AS pct_of_orders,
  
  -- Production time  
  ROUND(SUM(p.expected_cook_hrs), 0) AS expected_cook_hrs,
  ROUND(SUM(p.expected_cook_hrs) * 100.0 / SUM(SUM(p.expected_cook_hrs)) OVER(), 1) AS pct_of_expected_cook,
  
  -- Labor hours
  ROUND(SUM(l.hourly_labor_hours), 0) AS total_labor_hrs,
  ROUND(SUM(l.hourly_labor_hours) * 100.0 / SUM(SUM(l.hourly_labor_hours)) OVER(), 1) AS pct_of_labor,
  
  -- ⚠️ KEY METRIC: Labor-Production Alignment
  -- Negative = Under-staffed relative to production
  -- Positive = Over-staffed relative to production  
  ROUND(SUM(l.hourly_labor_hours) * 100.0 / SUM(SUM(l.hourly_labor_hours)) OVER() - 
        SUM(p.expected_cook_hrs) * 100.0 / SUM(SUM(p.expected_cook_hrs)) OVER(), 1) AS labor_vs_production_gap,
  
  -- Efficiency ratios
  ROUND(SUM(p.total_orders) / NULLIF(SUM(l.hourly_labor_hours), 0), 2) AS orders_per_labor_hour,
  ROUND(SUM(l.hourly_labor_hours) / NULLIF(SUM(p.expected_cook_hrs), 0), 2) AS labor_multiplier,
  ROUND(SUM(l.hourly_labor_cost) / NULLIF(SUM(p.total_orders), 0), 2) AS labor_cost_per_order

FROM labor_by_hdr_week l
LEFT JOIN production_by_hdr_week p ON l.hdr_id = p.hdr_id AND l.service_week = p.service_week
WHERE p.total_orders IS NOT NULL
GROUP BY 1, 2
ORDER BY 1, 2;
```

### Key Metrics to Evaluate

| Metric | What It Tells You | Expected Pattern |
|--------|-------------------|------------------|
| **labor_vs_production_gap** | If < 0, under-staffed relative to production | D5s should be ≈ 0 (balanced) |
| **orders_per_labor_hour** | Efficiency of labor | D5s should be HIGHER (scale efficiency) |
| **labor_multiplier** | Labor hours per production hour | D5s may need lower (more efficient) |
| **labor_cost_per_order** | Cost efficiency | D5s should be LOWER (economies of scale) |

### Interpretation Guide

**Properly Distributed Labor:**
- D5s have `pct_of_labor ≈ pct_of_expected_cook` (11-12%)
- D5s have HIGHER `orders_per_labor_hour` due to economies of scale
- If D5s have lower `labor_multiplier` but same OTR → Efficient
- If D5s have lower `labor_multiplier` AND worse OTR → Under-staffed

**Labor Tables Reference:**
- `wonder-fin-prod.profit_loss_order_report.daily_labor_by_location_summary` - Daily labor hours and cost
- `wonder-fin-prod.profit_loss_order_report_seeds.location_mapping_v2` - Maps dayforce_key to oms_key (hdr_id)

---

## Force Complete & Pod Diagnosis SQL Queries

### 8.1 Force Complete Summary by HDR

```sql
-- FC rates by HDR vs network
WITH target_hdrs AS (
  SELECT hdr_id, hdr_name 
  FROM `wonder-dw-prod-brd.dw.dim_hdrs`
  WHERE hdr_name IN ('[HDR1]', '[HDR2]', '[HDR3]', '[HDR4]', '[HDR5]')  -- Replace with target HDRs
),
fc_by_order AS (
  SELECT 
    t.hdr_name,
    i.order_id,
    MAX(i.has_force_progression) AS has_fc
  FROM `wonder-dw-prod-brd.orders.imperfect_kitchen_items` i
  JOIN target_hdrs t ON i.hdr_id = t.hdr_id
  WHERE i.order_assigned_to_pod_date >= DATE_TRUNC(DATE_SUB(CURRENT_DATE('America/New_York'), INTERVAL 1 WEEK), WEEK(MONDAY))
    AND i.order_assigned_to_pod_date < DATE_TRUNC(CURRENT_DATE('America/New_York'), WEEK(MONDAY))
    AND i.order_status = 'COMPLETED'
  GROUP BY 1, 2
),
fc_rates AS (
  SELECT hdr_name, COUNT(*) AS total_orders, SUM(has_fc) AS fc_orders,
    ROUND(SUM(has_fc) * 100.0 / COUNT(*), 1) AS fc_rate
  FROM fc_by_order GROUP BY 1
),
network_fc AS (
  SELECT COUNT(*) AS network_orders,
    SUM(CASE WHEN has_force_progression = 1 THEN 1 ELSE 0 END) AS network_fc_orders
  FROM `wonder-dw-prod-brd.orders.imperfect_kitchen_items`
  WHERE order_assigned_to_pod_date >= DATE_TRUNC(DATE_SUB(CURRENT_DATE('America/New_York'), INTERVAL 1 WEEK), WEEK(MONDAY))
    AND order_assigned_to_pod_date < DATE_TRUNC(CURRENT_DATE('America/New_York'), WEEK(MONDAY))
    AND order_status = 'COMPLETED'
)
SELECT fr.hdr_name, fr.total_orders, fr.fc_orders, fr.fc_rate AS fc_pct,
  ROUND(nfc.network_fc_orders * 100.0 / nfc.network_orders, 1) AS network_fc_pct,
  ROUND(fr.fc_rate - (nfc.network_fc_orders * 100.0 / nfc.network_orders), 1) AS fc_vs_network
FROM fc_rates fr CROSS JOIN network_fc nfc ORDER BY fr.fc_rate DESC;
```

### 8.2 FC Pattern Analysis: Rescue vs Process

```sql
-- Compare FC rates for late vs on-time orders (identifies rescue pattern)
WITH target_hdrs AS (
  SELECT hdr_id, hdr_name FROM `wonder-dw-prod-brd.dw.dim_hdrs`
  WHERE hdr_name IN ('[HDR1]', '[HDR2]', '[HDR3]', '[HDR4]', '[HDR5]')
),
fc_by_order AS (
  SELECT t.hdr_name, i.order_id, MAX(i.has_force_progression) AS has_fc
  FROM `wonder-dw-prod-brd.orders.imperfect_kitchen_items` i
  JOIN target_hdrs t ON i.hdr_id = t.hdr_id
  WHERE i.order_assigned_to_pod_date >= DATE_TRUNC(DATE_SUB(CURRENT_DATE('America/New_York'), INTERVAL 1 WEEK), WEEK(MONDAY))
    AND i.order_assigned_to_pod_date < DATE_TRUNC(CURRENT_DATE('America/New_York'), WEEK(MONDAY))
    AND i.order_status = 'COMPLETED'
  GROUP BY 1, 2
)
SELECT fc.hdr_name,
  CASE WHEN ot.on_time_issue AND ot.otr_sla_tier LIKE '%LATE' THEN 'Late' ELSE 'On-Time' END AS order_status,
  COUNT(*) AS orders, ROUND(SUM(fc.has_fc) * 100.0 / COUNT(*), 1) AS fc_pct
FROM fc_by_order fc
JOIN `wonder-dw-prod-brd.orders.hdr_on_time_orders` ot ON fc.order_id = ot.order_id
GROUP BY 1, 2 ORDER BY fc.hdr_name, order_status DESC;

-- INTERPRETATION:
-- If Late FC % > On-Time FC % = RESCUE FCs (items already behind)
-- If Late FC % ≈ On-Time FC % = PROCESS FCs (systematic, review triggers)
```

### 8.3 FC Correlation with Issues

```sql
-- What issues correlate with force completes?
WITH target_hdrs AS (
  SELECT hdr_id, hdr_name FROM `wonder-dw-prod-brd.dw.dim_hdrs`
  WHERE hdr_name IN ('[HDR1]', '[HDR2]', '[HDR3]', '[HDR4]', '[HDR5]')
),
fc_by_order AS (
  SELECT t.hdr_name, i.order_id,
    MAX(i.has_force_progression) AS has_fc,
    MAX(i.has_bad_interaction) AS has_bad_int,
    MAX(i.has_long_queue) AS has_long_queue,
    MAX(i.has_longer_than_expected_production_time) AS has_long_prod
  FROM `wonder-dw-prod-brd.orders.imperfect_kitchen_items` i
  JOIN target_hdrs t ON i.hdr_id = t.hdr_id
  WHERE i.order_assigned_to_pod_date >= DATE_TRUNC(DATE_SUB(CURRENT_DATE('America/New_York'), INTERVAL 1 WEEK), WEEK(MONDAY))
    AND i.order_assigned_to_pod_date < DATE_TRUNC(CURRENT_DATE('America/New_York'), WEEK(MONDAY))
    AND i.order_status = 'COMPLETED'
  GROUP BY 1, 2
)
SELECT hdr_name, COUNT(*) AS orders,
  ROUND(SUM(has_fc) * 100.0 / COUNT(*), 1) AS fc_pct,
  ROUND(SUM(CASE WHEN has_fc = 1 AND has_long_prod = 1 THEN 1 ELSE 0 END) * 100.0 / NULLIF(SUM(has_fc), 0), 1) AS fc_with_long_prod_pct,
  ROUND(SUM(CASE WHEN has_fc = 1 AND has_long_queue = 1 THEN 1 ELSE 0 END) * 100.0 / NULLIF(SUM(has_fc), 0), 1) AS fc_with_long_queue_pct,
  ROUND(SUM(CASE WHEN has_fc = 1 AND has_bad_int = 1 THEN 1 ELSE 0 END) * 100.0 / NULLIF(SUM(has_fc), 0), 1) AS fc_with_bad_int_pct,
  ROUND(SUM(CASE WHEN has_fc = 0 AND has_long_prod = 1 THEN 1 ELSE 0 END) * 100.0 / NULLIF(SUM(CASE WHEN has_fc = 0 THEN 1 ELSE 0 END), 0), 1) AS nonfc_long_prod_pct
FROM fc_by_order GROUP BY 1 ORDER BY fc_pct DESC;

-- KEY INSIGHT: If fc_with_long_prod_pct > nonfc_long_prod_pct, items were ALREADY behind before FC
```

### 8.4 Capacity vs Idle Time (IPC + Volume)

```sql
-- Diagnose capacity vs idle time using items per order and volume
WITH target_hdrs AS (
  SELECT hdr_id, hdr_name FROM `wonder-dw-prod-brd.dw.dim_hdrs`
  WHERE hdr_name IN ('[HDR1]', '[HDR2]', '[HDR3]', '[HDR4]', '[HDR5]')
),
order_metrics AS (
  SELECT t.hdr_name, o.order_id, o.item_count, o.actual_queue_mins, o.service_date_et,
    EXTRACT(HOUR FROM o.order_assigned_to_pod_time_utc AT TIME ZONE 'America/New_York') AS order_hour,
    ot.on_time_issue, ot.otr_sla_tier
  FROM `wonder-dw-prod-brd.orders.hdr_orders` o
  JOIN target_hdrs t ON o.hdr_id = t.hdr_id
  JOIN `wonder-dw-prod-brd.orders.hdr_on_time_orders` ot ON o.order_id = ot.order_id
  WHERE o.order_status = 'COMPLETE' AND o.brand_category = 'WONDER_HDR'
    AND o.order_channel IN ('APP', 'WEB', 'IN_PERSON')
    AND o.service_date_et >= DATE_TRUNC(DATE_SUB(CURRENT_DATE('America/New_York'), INTERVAL 1 WEEK), WEEK(MONDAY))
    AND o.service_date_et < DATE_TRUNC(CURRENT_DATE('America/New_York'), WEEK(MONDAY))
),
hourly_volume AS (
  SELECT hdr_name, service_date_et, order_hour, COUNT(*) AS orders_in_hour
  FROM order_metrics GROUP BY 1, 2, 3
)
SELECT om.hdr_name, COUNT(DISTINCT om.order_id) AS total_orders,
  ROUND(AVG(om.item_count), 1) AS avg_ipc,
  ROUND(AVG(CASE WHEN om.on_time_issue AND om.otr_sla_tier LIKE '%LATE' THEN om.item_count END), 1) AS late_ipc,
  ROUND(MAX(hv.orders_in_hour), 0) AS peak_orders_hr,
  ROUND(AVG(om.actual_queue_mins), 1) AS avg_queue,
  ROUND(AVG(CASE WHEN om.on_time_issue AND om.otr_sla_tier LIKE '%LATE' THEN om.actual_queue_mins END), 1) AS late_queue
FROM order_metrics om
LEFT JOIN hourly_volume hv ON om.hdr_name = hv.hdr_name AND om.service_date_et = hv.service_date_et AND om.order_hour = hv.order_hour
GROUP BY om.hdr_name ORDER BY late_queue DESC;

-- INTERPRETATION:
-- High peak_orders_hr + High late_queue = CAPACITY issue
-- Low peak_orders_hr + High late_queue = IDLE TIME/EXECUTION issue
-- Late IPC > Avg IPC = Complex orders getting stuck
```

### 8.5 Pod-Level Performance with Step Lag

```sql
-- Pod performance showing actual vs expected variance AND step lag (idle time indicator)
WITH target_hdrs AS (
  SELECT hdr_id, hdr_name FROM `wonder-dw-prod-brd.dw.dim_hdrs`
  WHERE hdr_name IN ('[HDR1]', '[HDR2]', '[HDR3]', '[HDR4]', '[HDR5]')
),
hdr_pod_performance AS (
  SELECT t.hdr_name, lb.pod_type, COUNT(*) AS items,
    ROUND(AVG(lb.step_focus_lag_seconds), 1) AS avg_step_lag_sec,
    ROUND(AVG(lb.actual_duration_sec / 60.0), 2) AS avg_actual_min,
    ROUND(AVG(lb.expected_duration_sec / 60.0), 2) AS avg_expected_min
  FROM `wonder-dw-prod-brd.orders.hdr_kitchen_line_builds` lb
  JOIN target_hdrs t ON lb.hdr_id = t.hdr_id
  WHERE lb.order_assigned_to_pod_time >= DATE_TRUNC(DATE_SUB(CURRENT_DATE('America/New_York'), INTERVAL 1 WEEK), WEEK(MONDAY))
    AND lb.order_assigned_to_pod_time < DATE_TRUNC(CURRENT_DATE('America/New_York'), WEEK(MONDAY))
    AND lb.pod_type IS NOT NULL AND lb.pod_type NOT IN ('EXPO', 'Expo Pod')
  GROUP BY 1, 2
),
network_pod_performance AS (
  SELECT lb.pod_type,
    ROUND(AVG(lb.step_focus_lag_seconds), 1) AS network_step_lag_sec,
    ROUND(AVG(lb.actual_duration_sec / 60.0), 2) AS network_actual_min
  FROM `wonder-dw-prod-brd.orders.hdr_kitchen_line_builds` lb
  WHERE lb.order_assigned_to_pod_time >= DATE_TRUNC(DATE_SUB(CURRENT_DATE('America/New_York'), INTERVAL 1 WEEK), WEEK(MONDAY))
    AND lb.order_assigned_to_pod_time < DATE_TRUNC(CURRENT_DATE('America/New_York'), WEEK(MONDAY))
    AND lb.pod_type IS NOT NULL AND lb.pod_type NOT IN ('EXPO', 'Expo Pod')
  GROUP BY 1
)
SELECT hp.hdr_name, hp.pod_type, hp.items,
  hp.avg_step_lag_sec AS step_lag,
  np.network_step_lag_sec AS network_lag,
  ROUND(hp.avg_step_lag_sec - np.network_step_lag_sec, 1) AS lag_vs_network,
  hp.avg_actual_min AS actual,
  hp.avg_expected_min AS expected,
  ROUND(hp.avg_actual_min - hp.avg_expected_min, 2) AS variance,
  CASE 
    WHEN hp.avg_step_lag_sec > np.network_step_lag_sec + 10 THEN '🔴 HIGH IDLE'
    WHEN hp.avg_step_lag_sec > np.network_step_lag_sec + 5 THEN '🟠 ELEVATED IDLE'
    WHEN hp.avg_actual_min - hp.avg_expected_min > 1.5 THEN '🔴 SLOW'
    ELSE '✅ OK'
  END AS status
FROM hdr_pod_performance hp
JOIN network_pod_performance np ON hp.pod_type = np.pod_type
WHERE hp.items >= 100 ORDER BY hp.hdr_name, hp.pod_type;

-- STATUS KEY:
-- 🔴 HIGH IDLE: Step lag > network + 10 sec (staff waiting between steps)
-- 🟠 ELEVATED IDLE: Step lag > network + 5 sec
-- 🔴 SLOW: Variance > +1.5 min (execution speed issue)
-- ✅ OK: Within normal range
```

### Interpretation Guide: Capacity vs Idle Time

| Symptom | High Peak Volume | Low Peak Volume |
|---------|------------------|-----------------|
| **High Queue** | 🔴 CAPACITY: Add staff, throttle orders | 🔴 IDLE: Workflow audit, training |
| **High Step Lag** | 🟠 COORDINATION: Improve handoffs | 🔴 IDLE: Staff not engaged |
| **High FC + Long Prod** | 🔴 RESCUE: Focus on execution speed | 🔴 RESCUE: Training issue |
| **High FC ≈ Late/On-Time** | 🟠 PROCESS: Review FC triggers | 🟠 PROCESS: Review FC triggers |

---

## Supporting Documentation

- [schema-reference.md](schema-reference.md) - Complete table schemas and field descriptions
- [common-pitfalls.md](common-pitfalls.md) - Common mistakes and how to avoid them

