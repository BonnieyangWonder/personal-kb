# Delay Attribution Analysis Guide

Framework for classifying first-run holdback into root cause categories. Distinguishes genuine algorithmic holdback from queue-driven delays.

## When to Use

- "Why are items being held back?" — attribute holdback to queue congestion vs algorithm
- "Is holdback helping or hurting?" — measure true holdback rate vs redundant holdback
- "How does holdback differ across NSO vs mature sites?" — segment by site maturity
- Weekend trend analysis — track attribution shifts over time
- Quantifying the impact of holdback algorithm changes

## Core Concept: Queue Makes Holdback Redundant

The sequencer applies holdback (`estimated_hold_back_time > 0`) to delay items from immediate preparation. But when the kitchen queue is already long, items naturally wait regardless of holdback. The key question:

> **Was the holdback decision the binding constraint, or would the item have waited anyway?**

**Queue time** = `TIMESTAMP_DIFF(t_s, TIMESTAMP(created_time), SECOND)` — the gap between when the sequencing run completes and when the item is predicted to start cooking.

If queue time > 15 seconds, the item has a natural wait period. Any holdback applied is **redundant** — the queue itself causes the delay, not the algorithm.

## Attribution Categories

Every first-run item is classified into exactly one category (mutually exclusive):

| Category | Condition | Meaning |
|----------|-----------|---------|
| **No Delay** | `estimated_hold_back_time = 0` or `NULL` | No holdback applied on first run |
| **Queue-Caused** | holdback > 0 AND queue > 15s | Holdback is redundant; queue already delays the item |
| **True HB High CP** | holdback > 0, queue ≤ 15s, `customer_promise_score > 0` | Item is early vs customer promise; algo holds to avoid premature expo |
| **True HB All Items** | holdback > 0, queue ≤ 15s, all order items have holdback | Blanket holdback on entire order (not item-selective) |
| **True HB Both** | Both High CP and All Items | Both conditions simultaneously |

### Why 15 Seconds?

The 15-second threshold separates "effectively immediate" items from those with meaningful queue waits. Items with < 15s queue time are essentially at the front of the queue — any holdback applied to them is a genuine algorithmic delay, not a side effect of congestion.

### "All Items" Subcategory

To identify blanket holdback (entire order held vs selective item holdback), check whether **every item in the order** has `estimated_hold_back_time > 0` on its first run:

```sql
-- Per-order holdback status
SELECT
  hdr_id,
  order_number,
  COUNT(*) AS total_items,
  COUNTIF(COALESCE(estimated_hold_back_time, 0) > 0) AS held_items,
  COUNTIF(COALESCE(estimated_hold_back_time, 0) > 0) = COUNT(*) AS all_items_held
FROM first_run_items
GROUP BY 1, 2
```

## Full Query

### Step 1: Extract First-Run Items

Each item can appear in many sequencing runs. Use `ROW_NUMBER()` to isolate the first run:

```sql
WITH first_runs AS (
  SELECT
    hdr_id,
    order_number,
    item_id,
    created_time,
    TIMESTAMP(created_time) AS created_ts,
    t_s,
    estimated_hold_back_time,
    customer_promise_score,
    TIMESTAMP_DIFF(t_s, TIMESTAMP(created_time), SECOND) AS queue_seconds,
    DATE(DATETIME(TIMESTAMP(created_time), "America/New_York")) AS date_ny,
    ROW_NUMBER() OVER (
      PARTITION BY hdr_id, order_number, item_id
      ORDER BY created_time ASC
    ) AS run_num
  FROM `wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing_optimizer`
  WHERE hdr_id NOT LIKE 'T_%'  -- Exclude test HDRs
    AND DATE(DATETIME(TIMESTAMP(created_time), "America/New_York"))
        BETWEEN '2026-01-02' AND '2026-02-01'  -- Adjust date range
),

first_run_items AS (
  SELECT * FROM first_runs WHERE run_num = 1
)
```

### Step 2: Compute Per-Order Holdback Status

```sql
order_holdback_status AS (
  SELECT
    hdr_id,
    order_number,
    COUNTIF(COALESCE(estimated_hold_back_time, 0) > 0) = COUNT(*) AS all_items_held
  FROM first_run_items
  GROUP BY 1, 2
)
```

### Step 3: Classify Each Item

```sql
classified AS (
  SELECT
    f.*,
    CASE WHEN h.is_currently_mature THEN 'Mature' ELSE 'NSO' END AS site_type,
    CASE
      WHEN COALESCE(f.estimated_hold_back_time, 0) = 0 THEN 'No Delay'
      WHEN f.queue_seconds > 15 THEN 'Queue-Caused'
      WHEN f.customer_promise_score > 0 AND oh.all_items_held THEN 'True HB Both'
      WHEN f.customer_promise_score > 0 THEN 'True HB High CP'
      WHEN oh.all_items_held THEN 'True HB All Items'
      ELSE 'True HB Other'
    END AS attribution
  FROM first_run_items f
  JOIN `wonder-dw-prod-brd.dw.dim_hdrs` h ON f.hdr_id = h.hdr_id
  JOIN order_holdback_status oh ON f.hdr_id = oh.hdr_id AND f.order_number = oh.order_number
)
```

### Step 4: Aggregate by Site Type and Weekend

```sql
SELECT
  site_type,
  -- Group Fri-Sun into weekend buckets labeled by Friday date
  CASE
    WHEN date_ny IN ('2026-01-30', '2026-01-31', '2026-02-01') THEN 'Jan 30'
    WHEN date_ny IN ('2026-01-23', '2026-01-24', '2026-01-25') THEN 'Jan 23'
    -- ... additional weekends
  END AS weekend_label,
  COUNT(*) AS items,
  ROUND(COUNTIF(attribution = 'No Delay') * 100.0 / COUNT(*), 1) AS pct_no_delay,
  ROUND(COUNTIF(attribution = 'Queue-Caused') * 100.0 / COUNT(*), 1) AS pct_queue_caused,
  ROUND(COUNTIF(attribution = 'True HB High CP') * 100.0 / COUNT(*), 2) AS pct_true_hb_high_cp,
  ROUND(COUNTIF(attribution = 'True HB All Items') * 100.0 / COUNT(*), 2) AS pct_true_hb_all_items,
  ROUND(COUNTIF(attribution = 'True HB Both') * 100.0 / COUNT(*), 2) AS pct_true_hb_both
FROM classified
GROUP BY site_type, weekend_label
ORDER BY site_type DESC, weekend_label
```

## Site Classification

Uses `wonder-dw-prod-brd.dw.dim_hdrs`:

| Field | Usage |
|-------|-------|
| `is_currently_mature` | `TRUE` → Mature, `FALSE` → NSO |
| `hdr_class` | Alternative: `IN ('2025 New', '2026 New')` for NSO |

Both approaches work. `is_currently_mature` is simpler; `hdr_class` gives finer granularity (year cohorts).

## Weekend Definition

"Weekends" = Friday through Sunday (peak restaurant volume). Labeled by the Friday date:

```sql
EXTRACT(DAYOFWEEK FROM date_ny) IN (1, 6, 7)  -- 1=Sun, 6=Fri, 7=Sat
```

Or enumerate dates explicitly as shown in the full query for exact control.

## Typical Results (Jan 2026 Baseline)

### Mature Sites

| Weekend | Items | No Delay | Queue-Caused | True HB (all) |
|---------|-------|----------|--------------|----------------|
| Jan 02  | ~35K  | ~46%     | ~52%         | ~1.9%          |
| Jan 30  | ~64K  | ~35%     | ~64%         | ~1.7%          |

### NSO Sites

| Weekend | Items | No Delay | Queue-Caused | True HB (all) |
|---------|-------|----------|--------------|----------------|
| Jan 02  | ~7K   | ~38%     | ~56%         | ~5.8%          |
| Jan 30  | ~14K  | ~31%     | ~67%         | ~3.4%          |

**Key observations**:
- Queue-caused is the dominant holdback category (52–67%)
- True algorithmic holdback is rare: ~1.7% at mature, ~3.5% at NSO sites
- As volume grows (Jan 02 → Jan 30), queue-caused % increases and no-delay % decreases
- NSO sites have 2–3x the true holdback rate of mature sites

## Visualization

A runnable Python script for generating the full stacked bar chart + tables report is in:
`outputs/sequencing-delay-attribution/02-generate-chart.py`

The chart includes:
1. **Summary tables** — one per site type with all attribution percentages
2. **Stacked bar charts** — full attribution breakdown per weekend
3. **Zoomed breakdown** — True Holdback subcategories only (excludes No Delay and Queue-Caused)

## Adapting This Analysis

### Different Time Periods
Change the date filter in the `WHERE` clause. For a single day:
```sql
AND DATE(DATETIME(TIMESTAMP(created_time), "America/New_York")) = '2026-02-05'
```

### Different Queue Threshold
Replace `> 15` with a different threshold. Lower values (e.g., 5s) will classify more holdback as "true"; higher values (e.g., 30s) will classify more as queue-caused.

### Per-HDR Breakdown
Add `hdr_id` (or join `dim_hdrs.hdr_name`) to the GROUP BY for site-level attribution.

### Hourly Patterns
Add `EXTRACT(HOUR FROM DATETIME(TIMESTAMP(created_time), "America/New_York"))` to study how attribution shifts during peak vs off-peak hours.
