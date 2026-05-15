---
name: wonder-sequencing
description: Expert knowledge of Wonder's kitchen sequencing system including hdr_kitchen_order_sequencing_optimizer, optimizer_batch, and sequencing_contexts tables. Covers item-level scores (expo sit time, customer promise), batch group assignments, holdback strategies, kitchen context analysis, and order performance metrics across HDRs.
allowed-tools: Read, Grep, Glob, Bash
---

# Wonder Sequencing Skill

## Overview

This skill provides expertise in querying and analyzing Wonder's kitchen sequencing system output tables in BigQuery. Sequencing is an operations research project that creates optimal kitchen schedules dynamically (every 30+ seconds) to minimize expo sit time and meet customer promise times.

**⚡ Quick Start**: When users ask for "HDR-insights", "order details", or "show me order X", immediately run `python3 hdr-insights-tool/hdr_insights.py <order_number>` to generate an interactive HTML dashboard. See "Quick Action" section below.

**Wonder Context**: Wonder operates High Density Restaurants (HDRs) - physical spaces that host multiple restaurant brands (e.g., "Bobby's Burgers", "Di Fara Pizza") which share kitchen facilities, equipment, and many ingredients. Sequencing coordinates the preparation of menu items across these brands to optimize kitchen efficiency and customer experience.

## What This Skill Provides

- **Order-level sequencing analysis** - Investigate specific order performance with scores, timelines, and kitchen context
- **Score interpretation** - Understand expo sit time (absolute value metric) and customer promise scores (signed metric)
- **Batch group visualization** - See how items are grouped across pods and assigned priorities
- **Kitchen context analysis** - Parse workflow steps, appliance states, and queued items from JSON
- **Performance comparisons** - Compare predictions vs actuals, rank orders within sequencing runs
- **Query patterns** - Pre-built SQL templates for common analysis scenarios

The sequencing system uses constraint programming (CP-SAT solver) with a three-stage simulation approach to determine the optimal order in which kitchen items should be prepared across different **pods** (virtual groupings of appliances, typically one per employee). The system stores:
- **Input context** for each sequencing run (kitchen state, settings)
- **Optimization results** with predicted timestamps and scores
- **Batch assignments** showing how items are grouped across pods

**Key Components:**
- **V2 Data Structure**: Current optimized tables with full sequence plans (batch groups), providing visibility into the complete schedule. The first data structure to publish detailed batch group information.
- **ThreeStageWrapperV2**: The main sequencing wrapper implementation live at most sites
- **Batch Groups**: Schedule structures organizing items into batches for efficient preparation. Displayed one at a time on Kitchen Display System (KDS) screens at each pod.
- **Pods & Super Pods**: Virtual concepts (that include physical stations) - pods group appliances for one employee; super pods combine multiple pods (typically one hot + one cold)
- **Holdback Logic**: Strategy to delay item preparation to optimize timing and reduce expo wait
- **Multi-objective Optimization**: Balances expo sit time, customer promise adherence, and throughput
- **Expo Thresholds**: Configurable limits (changed from 7 to 3 minutes on 2025-11-24)

**Code Architecture (KDS Repository)**:
- **Algorithm Implementation**: `wonder/kds/tool/cooking-optimization-library` - Core sequencing logic and optimization algorithms (ThreeStageWrapper, CP-SAT solver)
- **Backend Service**: `wonder/kds/backend/cooking-optimization-service` - Execution pipeline, result processing, and database persistence (saves to BigQuery tables)
- **Reference**: See KDS repository submodule at `/wonder/kds` for implementation details

**Primary Users**: Operations Research, Engineering, Product, and Analytics teams querying for algorithm performance, predictions vs actuals, operational metrics, and kitchen efficiency analysis.

## When to Use This Skill

Use this skill when you need to:

1. **Single-order analysis**: Investigate one specific order's sequencing performance and compare it to other orders in the same sequencing run
2. **Debug sequencing decisions**: Understand why an item was scheduled at a specific time
3. **Analyze expo sit times**: Investigate items with excessive wait time at expo
4. **Examine customer promise violations**: Find orders that didn't meet their target completion time
5. **Compare batch group assignments**: See how items are grouped across different pods
6. **Investigate holdback strategies**: Understand when and why items are held back from preparation
7. **Analyze delay edge cases**: Find orders that were delayed 30+ or 60+ minutes
8. **Compare predicted vs actual performance**: Link sequencing predictions to actual order outcomes
9. **Debug sequencing context**: Examine the kitchen state and settings used for a specific run
10. **Performance analysis**: Measure sequencing effectiveness across HDRs or time periods

## 🚀 Quick Action: Generate HDR-Insights Report

**IMPORTANT**: When users request any of the following, **immediately generate and open the HDR-insights HTML report** using the HDR-insights tool:

**Trigger Phrases**:
- "Show me HDR-insights for order X"
- "Show me hdr insights for order X"
- "Give me order details for X"
- "Show me order X" (when X is a number)
- "Analyze order X"
- "Why did order X perform poorly?"
- "Show me the sequencing for order X"

**Action**:
```bash
python3 hdr-insights-tool/hdr_insights.py <order_number> && open outputs/hdr-insights-<order_number>-*.html
```

**What Users Get**: Interactive HTML dashboard with complete order timeline, all sequencing runs, kitchen state visualization, score trends, batch groupings, and performance comparisons.

**Tool Documentation**: See **hdr-insights-tool/README.md** for complete feature list and implementation details.

## Core Concepts

### Sequencing Tables

**Primary Tables** (Current System):

**`wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing_optimizer`**
- Item-level sequencing optimization results with full history
- Contains timestamps, scores, holdback strategies, and detailed metrics
- Most comprehensive table for analysis
- Primary table for recent data (current implementation)

**`wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing_optimizer_batch`**
- Batch group schedule information with limited history
- Shows how items are grouped together across pods
- Contains pod assignments and group priorities
- **Data availability**: Started populating ~mid-December 2025. Earlier orders will not have batch data.
- **Fallback strategy**: Query optimizer table directly when batch data is unavailable

**`wonder-raw-prod.mongo_batch_cooking_optimization.sequencing_contexts`**
- Input context for each sequencing run
- Contains JSON fields: `kitchen_context` (items to sequence) and `estimator_settings` (configuration)
- Used to understand what inputs drove the optimization
- Can extract item counts and kitchen state

**Legacy Table**:

**`wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing`**
- Older sequencing output structure (may still be populated)
- Similar timestamps but fewer fields than optimizer table
- Has `hdr_name`, `type`, `duration_in_sequencing_minutes`
- Useful for historical comparisons and edge case analysis

### Key Timestamps (Five Critical Times)

1. **t_s** (Simulated Start): When the item should begin cooking
2. **t_i** (Item Finish): When this specific item completes
3. **t_f** (Order Items Finish): When all items in the order complete
4. **t_o** (Order Finish): When the entire order is ready at expo
5. **t_cp** (Customer Promise): Target completion time for the kitchen to finish cooking. Currently received from the ETA service (ML-driven model). Note: This feeds into the customer-facing completion estimate but is not 1:1 with what customers see. Future: Sequencing will set its own ETA and enforce it in subsequent runs.

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

### Delay Analysis

**Sequencing Delay** (queue time): Time from when sequencing completes (`created_time`) to when the item should start (`t_s`)

```sql
TIMESTAMP_DIFF(t_s, TIMESTAMP(created_time), SECOND) as queue_seconds
```

**Important**: Items can be sequenced significantly before they need to start:
- Normal: A few seconds to a few minutes
- Edge cases: 30+ or 60+ minutes of delay (potential issues)
- Filter: `TIMESTAMP_DIFF(CAST(created_time AS TIMESTAMP), t_s, SECOND) >= -30` to find anomalies

**Holdback Delay**: Time an item is intentionally delayed from immediate preparation
- Field: `estimated_hold_back_time` (in minutes)
- Used for strategic timing optimization
- `estimated_hold_back_time > 0` means item is being held back

**Delay Attribution**: For root cause analysis distinguishing algorithmic holdback from queue-driven delays, see **[delay-attribution-guide.md](delay-attribution-guide.md)**. Key insight: most holdback (52–67%) is redundant because the kitchen queue already delays items; true algorithmic holdback is only ~1.7% (mature) to ~3.5% (NSO).

### Scoring System

**CRITICAL - Read score semantics carefully to avoid misinterpretation:**

- **expo_sit_time_score**: Component measuring expo wait time impact
  - **THE SIGN IS MEANINGLESS**: Both +5 and -5 represent 5 minutes of expo sit time
  - **Always use ABS() for analysis**: `ABS(expo_sit_time_score)` gives actual minutes
  - Lower absolute values are better (target <3 min post-2025-11-24)

- **customer_promise_score**: Component measuring adherence to customer promise time
  - **Negative = LATE** (behind target): -2.5 = 2.5 minutes after promise time
  - **Positive = EARLY** (ahead of target): +4.0 = 4.0 minutes before promise time
  - **Zero = ON TIME**: Exactly meeting the promise
  - Acceptable range: typically ±10 minutes

- **score**: Overall optimization score (relative within a sequencing run, higher is better)
- **estimated_item_expo_wait_time_mins**: Predicted wait time for this item at expo
- **estimated_order_level_expo_time_mins**: Predicted wait time for the complete order
- **estimate_order_complete_vs_customer_promise**: How far order completion is from promise time

**Common Mistake**: Treating negative expo_sit_time_score as "good" - it's not! See **common-pitfalls.md** for detailed examples.

### Expo Threshold Configuration

The expo sit time threshold changed on 2025-11-24:
- **Before 2025-11-24**: EXPO_THRESHOLD_7 (7 minutes)
- **After 2025-11-24**: EXPO_THRESHOLD_3 (3 minutes)

Use this for period comparisons:
```sql
CASE WHEN created_time >= "2025-11-24" THEN "EXPO_THRESHOLD_3"
     ELSE "EXPO_THRESHOLD_7"
END as expo_threshold
```

### Multiple Sequencing Runs per Order

Orders can be re-sequenced multiple times:
- Each sequencing run creates a new `_id` and `context_id`
- Track with `COUNT(DISTINCT context_id)` per order
- First sequencing: `MIN(created_time)` for an order
- Use first run to avoid counting delays multiple times

### Joining Sequencing Data with Orders

**CRITICAL**: The `item_id` field in sequencing tables is NOT the same as `order_item_id` in order_items.

**Correct join pattern - Use order_id**:
```sql
-- Get sequencing data for a specific order
SELECT
  o.order_number,
  o.order_id,
  seq.item_id,  -- This is NOT order_items.order_item_id
  seq.menu_item_name,
  seq.expo_sit_time_score
FROM `wonder-dw-prod-brd.orders.hdr_orders` o
JOIN `wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing_optimizer` seq
  ON o.order_id = seq.order_id  -- ✅ Correct: Join on order_id
WHERE o.order_number = '6187677';
```

**❌ WRONG - Do NOT join on item_id**:
```sql
-- This will NOT work correctly
FROM order_items oi
JOIN hdr_kitchen_order_sequencing_optimizer seq
  ON oi.order_item_id = seq.item_id  -- ❌ These are different IDs!
```

**Merging batch and optimizer tables**:
```sql
-- User-provided pattern for complete sequencing data
SELECT
  batch.*,
  i_s.*
FROM `wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing_optimizer_batch` batch
LEFT JOIN `wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing_optimizer` i_s
  ON batch._id = i_s._id AND batch.item_id = i_s.item_id
WHERE i_s.order_id = 'c1c5d052-9777-44ba-8dfe-b2dd77a7ad3b';
```

**Key points**:
- Join sequencing to orders using `order_id` (NOT item IDs)
- The `item_id` in sequencing is an internal sequencing identifier
- When merging batch + optimizer: join on BOTH `_id` AND `item_id`
- If batch table returns no results, fall back to optimizer table only

## Query Patterns

For comprehensive SQL query examples, see **query-patterns.md**, which includes:

- **Basic queries**: Item-level queries, batch information joins
- **Context analysis**: Fetching sequencing contexts, item count distributions
- **Delay analysis**: Finding excessive delays, edge case analysis by date, daily summaries
- **Expo sit time analysis**: High expo wait time queries
- **Bug detection**: Queries for identifying known issues (late orders with holdback)
- **Performance analysis**: Comparing predictions to actual outcomes, accuracy metrics
- **Table comparison**: Optimizer vs legacy table queries
- **Common use cases**: Why was an order delayed? What was the kitchen context? How many orders had excessive delays?
- **Data quality validation**: NULL checks, timestamp ordering verification, malformed batch groups

Quick reference patterns:

**Basic item query**:
```sql
SELECT opt.*, DATETIME(opt.t_s, 'America/New_York') as start_time_ny
FROM `wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing_optimizer` opt
WHERE opt.order_number = 'YOUR_ORDER' AND DATE(opt.created_time) = '2025-12-22';
```

**Join with batch data**:
```sql
FROM `wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing_optimizer` opt
LEFT JOIN `wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing_optimizer_batch` batch
  ON opt._id = batch._id AND opt.item_id = batch.item_id
```

**Find delayed items**:
```sql
WHERE estimated_hold_back_time > 0
-- or for comprehensive analysis
WHERE (estimated_hold_back_time > 0
   OR TIMESTAMP_DIFF(CAST(created_time AS TIMESTAMP), t_s, SECOND) >= -30)
```

## Best Practices

### Timezone Handling

**Always convert timestamps to America/New_York** for analysis since Wonder kitchens operate in US time zones:

```sql
DATETIME(opt.t_s, 'America/New_York') as start_time_ny
```

Raw timestamps in these tables are stored in UTC but business logic operates in Eastern Time.

### Context and Run Identification

- Use `_id` to identify a specific sequencing run/optimization
- Use `context_id` to group related sequencing events
- A single `_id` represents one optimization cycle (runs every 30+ seconds)
- Orders can have multiple `context_id` values if re-sequenced

### Handling Multiple Sequencing Runs

Orders are often sequenced multiple times. For analysis, typically use the first run:

```sql
-- Get first sequencing run per order
SELECT order_number, MIN(created_time) as first_sequencing
FROM `wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing_optimizer`
GROUP BY order_number
```

### Delay Analysis Best Practices

**Two methods to detect delays:**

1. **Estimated Holdback Time** (most trusted):
```sql
WHERE estimated_hold_back_time > 0
```

2. **Timestamp Difference** (catches more edge cases):
```sql
WHERE TIMESTAMP_DIFF(CAST(created_time AS TIMESTAMP), t_s, SECOND) >= -30
```

Use both for comprehensive analysis.

**For root cause attribution** (queue vs algorithmic holdback), see **[delay-attribution-guide.md](delay-attribution-guide.md)**.

### Date Filtering

Filter on `created_time` for the optimizer table:

```sql
WHERE DATE(opt.created_time) = '2025-12-22'
```

For time ranges with HDR timezone:
```sql
WHERE created_time BETWEEN DATETIME("2025-12-22T15:00:00") AND DATETIME("2025-12-22T16:00:00")
```

### Expo Threshold Periods

Always account for the expo threshold change when comparing across dates:

```sql
CASE WHEN created_time >= "2025-11-24" THEN "EXPO_THRESHOLD_3"
     ELSE "EXPO_THRESHOLD_7"
END as expo_threshold
```

### Which Table to Use

- **Current analysis**: Use `hdr_kitchen_order_sequencing_optimizer` (most complete)
- **Input debugging**: Use `sequencing_contexts` to see kitchen state
- **Historical comparison**: May need both optimizer and legacy `hdr_kitchen_order_sequencing`
- **Batch assignments**: Join to `hdr_kitchen_order_sequencing_optimizer_batch`

## Data Quality and Validation

### Table Preference

**Always prefer BRD (Business Ready Data) tables over raw mongo tables**:
- ✅ Use: `wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing_optimizer`
- ✅ Use: `wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing_optimizer_batch`
- ⚠️ Use sparingly: `wonder-raw-prod.mongo_batch_cooking_optimization.sequencing_contexts` (when you need input context)
- ❌ Avoid: `wonder-raw-prod.mongo_batch_cooking_optimization.optimized_sequences` (use BRD tables instead)

The BRD tables are derived from raw mongo tables via hourly batch sync jobs and are optimized for querying.

### Malformed Batch Groups

Batch groups are validated by the Kitchen Cooking Service v2 (KCSV2) - the dispatching service that consumes optimized plans and displays them on KDS screens. Some batch groups fail validation due to:

**Common Issues**:
1. **Clamshell batching validation**: Discrepancies between sequencing output and frontend expectations
2. **Separated handoff/cook steps**: Water bath or fryer handoff steps getting separated from their cook steps
3. **Multiple cook steps**: Items with 2+ cook steps (e.g., water bath) causing batching issues
4. **Edge cases**: Rare appliance, item, or step combinations that haven't been tested

**Fallback Behavior**: When KCSV2 catches a malformed batch group, it creates a simple, valid single-item batch group and dispatches that. Sequencing then repeats on the next run (30+ seconds later) without this segment and almost always produces a valid sequence. **Impact**: This fallback logic is robust - errors don't repeat and kitchen operations continue smoothly. Cleanup is desirable but not critical.

**Tracking**: Malformed batch groups are logged and tracked in bug tickets.

### Known Bug: Late Orders with Holdback

Orders with poor customer promise scores (`customer_promise_score < -10`) should not be held back, but a bug causes some to be delayed anyway. Track this with:

```sql
WHERE customer_promise_score < -10 AND estimated_hold_back_time > 0
```

## Supporting Documentation

### Core Skill Documentation

- **[query-patterns.md](query-patterns.md)**: Comprehensive SQL query examples for all analysis scenarios
- **[schema-reference.md](schema-reference.md)**: Complete field definitions and detailed table schemas
- **[common-pitfalls.md](common-pitfalls.md)**: Wrong vs. correct query patterns to avoid common mistakes
- **[delay-attribution-guide.md](delay-attribution-guide.md)**: Root cause attribution framework — classifies first-run holdback into queue-driven vs algorithmic categories (with full query and visualization script)

### HDR-Insights Tool (Use Proactively)

**When users ask for order details, "show me order X", or order analysis**, immediately use the HDR-insights tool:

- **[hdr-insights-tool/README.md](hdr-insights-tool/README.md)**: Complete tool documentation, features, usage patterns
- **[hdr-insights-tool/hdr_insights.py](hdr-insights-tool/hdr_insights.py)**: Interactive HTML dashboard generator

**Usage**: `python3 hdr-insights-tool/hdr_insights.py <order_number>`

**Output**: Single HTML file with interactive timeline, score trends, kitchen state visualization, and performance comparisons.

### Algorithm Decision Logic (Optional - Read When Needed)

**When users ask "Why did the algorithm choose this?"** or **"How does the holdback strategy work?"**, read algorithm-reference/ files:

- **[algorithm-reference/README.md](algorithm-reference/README.md)**: Index explaining when to use algorithm docs
- **[algorithm-reference/three-stage-wrapper-logic.md](algorithm-reference/three-stage-wrapper-logic.md)**: ThreeStageWrapperV2 family logic (most HDRs)
- **[algorithm-reference/ortools-cpsat-logic.md](algorithm-reference/ortools-cpsat-logic.md)**: ORTools CP-SAT constraint programming approach

**Note**: Algorithm reference docs are optional/advanced. 95% of use cases involve querying and analyzing data using the core skill docs above.

## Related Skills

- **wonder-orders**: For joining with order-level data (`hdr_orders`, `order_items`) and actual performance metrics
- **wonder-cookbook**: For recipe and BOM (Bill of Materials) details - use to cross-reference component items in kitchen context, verify required vs optional components, and understand menu item composition
- **wonder-pantry**: For inventory and availability issues affecting sequencing
- **bigquery-query-crafter**: For timezone handling and query optimization techniques
