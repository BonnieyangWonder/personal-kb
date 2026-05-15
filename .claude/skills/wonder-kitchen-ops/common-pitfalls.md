# Common Pitfalls - Wonder Kitchen Ops

Critical mistakes to avoid when working with batching data across CookBook and sequencing systems.

---

## JSON Extraction - Wrong Field Path

### ❌ Wrong: Accessing items directly from kitchen_context
```sql
-- FAILS: kitchen_context is a JSON array, not object
SELECT JSON_VALUE(kitchen_context, '$.items[0].id')
FROM sequencing_contexts
```

### ✅ Correct: UNNEST the array first
```sql
SELECT JSON_VALUE(item, '$.id') as item_id
FROM `wonder-raw-prod.mongo_batch_cooking_optimization.sequencing_contexts` ctx,
     UNNEST(JSON_QUERY_ARRAY(ctx.kitchen_context)) AS super_pod_context,
     UNNEST(JSON_QUERY_ARRAY(super_pod_context, '$.items')) AS item
```

**Why This Matters**: kitchen_context is a JSON array of super_pod contexts, each containing an items array.

---

## Wrong Join Key for Contexts

### ❌ Wrong: Joining on optimizer._id
```sql
-- WRONG: Uses wrong join key
FROM hdr_kitchen_order_sequencing_optimizer opt
JOIN sequencing_contexts ctx ON opt._id = ctx._id
```

### ✅ Correct: Join on optimizer.context_id
```sql
-- CORRECT: Use context_id
FROM hdr_kitchen_order_sequencing_optimizer opt
JOIN sequencing_contexts ctx ON opt.context_id = ctx._id
```

**Why This Matters**: The optimizer table has TWO ID fields - `_id` (run ID) and `context_id` (links to contexts).

---

## Forgetting to Filter COOK Steps

### ❌ Wrong: Querying all steps
```sql
-- Gets GARNISH, HANDOFF, COMPLETE steps too
SELECT JSON_VALUE(step, '$.batch_eligible_item_id')
FROM ... UNNEST(JSON_QUERY_ARRAY(item, '$.steps')) AS step
```

### ✅ Correct: Filter to COOK activity only
```sql
SELECT JSON_VALUE(step, '$.batch_eligible_item_id')
FROM ... UNNEST(JSON_QUERY_ARRAY(item, '$.steps')) AS step
WHERE JSON_VALUE(step, '$.cooking_activity') = 'COOK'
```

**Why This Matters**: Only COOK steps have batching criteria. GARNISH/HANDOFF have NULL batch_eligible_item_id.

---

## Missing Date Filter on Contexts

### ❌ Wrong: No date filter
```sql
-- Scans entire history (very slow, expensive)
SELECT * FROM sequencing_contexts WHERE hdr_id = 'xxx'
```

### ✅ Correct: Always filter by date
```sql
SELECT * FROM sequencing_contexts
WHERE hdr_id = 'xxx'
  AND DATE(created_time) >= '2026-01-31'
```

**Why This Matters**: sequencing_contexts has full history. Always add date filter for performance.

---

## Assuming Same Menu Item = Same Batch

### ❌ Wrong assumption
```
"Both items are 6 Piece Boneless Wings, so they should batch together"
```

### ✅ Correct understanding
Wings with different **sauces** have different `batch_eligible_item_id`:
- Buffalo Wings → 4000534
- Teriyaki Wings → 4000561
- Garlic Parm Wings → 4000562

**Why This Matters**: The batch_eligible_item_id is often the SAUCE, not the base item.

---

## Using BOM for Batching Instead of Sequencing Context

### ❌ Wrong: Looking only at BOM
```sql
-- BOM shows sauce is a component, but not the batching key
SELECT * FROM bom_lines WHERE bom_header_item_number = '8008268'
```

### ✅ Correct: Use sequencing context for actual batching criteria
```sql
-- Sequencing context shows actual batch_eligible_item_id used
SELECT JSON_VALUE(step, '$.batch_eligible_item_id')
FROM sequencing_contexts ...
WHERE JSON_VALUE(step, '$.cooking_activity') = 'COOK'
```

**Why This Matters**: BOM shows composition; sequencing context shows actual runtime batching criteria.

---

## Ignoring hot_hold_eligible Flag

### ❌ Wrong: Not checking hot hold
```sql
-- Assumes all FRYER items can batch
WHERE JSON_VALUE(step, '$.resource_type') = 'FRYER'
```

### ✅ Correct: Exclude hot hold items
```sql
WHERE JSON_VALUE(step, '$.resource_type') = 'FRYER'
  AND JSON_VALUE(step, '$.hot_hold_eligible') = 'false'
```

**Why This Matters**: Items with hot_hold_eligible=true CANNOT batch, regardless of other criteria.

---

## Confusing linebuild related_item_number with batch_eligible_item_id

### ❌ Wrong assumption
```
"The linebuild sub_steps_related_item_number is the batch_eligible_item_id"
```

### ✅ Correct understanding
- **linebuild**: `sub_steps_related_item_number` points to the **base ingredient** (e.g., 4000478 Boneless Chicken Wing)
- **sequencing**: `batch_eligible_item_id` points to the **sauce/variant** (e.g., 4000534 Buffalo Sauce)

**Why This Matters**: Different systems use different component references.

---

## Missing Service Window Filter for CookBook

### ❌ Wrong: No service window filter
```sql
SELECT * FROM bom_lines WHERE bom_line_item_number = '4000534'
```

### ✅ Correct: Filter by service window
```sql
SELECT * FROM bom_lines
WHERE bom_line_item_number = '4000534'
  AND CURRENT_TIMESTAMP() BETWEEN TIMESTAMP(service_start_time) AND TIMESTAMP(service_end_time)
```

**Why This Matters**: CookBook data is versioned. Without service window filter, you get historical/future data.

---

## Not Matching ALL FOUR Criteria

### ❌ Wrong: Checking only cook time
```
"Items have same cook time, so they should batch"
```

### ✅ Correct: Must match ALL FOUR
1. Same `pod_id`
2. Same `appliance_config_id` (resource_config_id)
3. Same `batch_eligible_item_id` (batch_item_number)
4. Same `cook_time_seconds` (step_time_seconds)

**Why This Matters**: Batching requires exact match on all four criteria.

---

## Expecting Eligible Items to Always Batch

### ❌ Wrong assumption
```
"These items match all four criteria, so they must have been batched together"
```

### ✅ Correct understanding
The CP-SAT sequencer **does not inherently value batching**. It only batches when:
- Queue load forces batching due to capacity constraints
- Time constraints (customer promise) make it necessary

Items may be eligible but not actually batched.

**Why This Matters**: Eligibility ≠ actual batching. Always compare `sequencing_contexts` (potential) with `optimizer_batch` (actual).

---

## Ignoring Human Batch Limit

### ❌ Wrong: Only checking physical batch_limit
```sql
WHERE batch_limit >= 5  -- Assumes 5 items can batch
```

### ✅ Correct: Understand operational vs physical limits
```sql
-- Physical limits range 1-9, but operational batches are typically 2-3, max 5
-- Don't assume batch_limit = actual batch size
-- Check hdr_kitchen_pod_item for actual batch sizes in practice
SELECT
  batch_limit,
  AVG(CAST(items_in_batch AS INT64)) as avg_actual_batch_size
FROM sequencing_contexts sc
JOIN hdr_kitchen_pod_item kpi ON ...
GROUP BY batch_limit
```

**Why This Matters**: The sequencer doesn't push toward maximum batch sizes. Physical batch_limit (e.g., 9 for chicken sandwiches) ≠ typical actual batch size (2-3 items most common, occasionally 4-5, max observed is 5).

---

## Assuming batch_eligible_item_id Works for All Appliances

### ❌ Wrong assumption
```
"batch_eligible_item_id determines batching for turbo ovens too"
```

### ✅ Correct understanding
`batch_eligible_item_id` is **FRYER-SPECIFIC**. The field exists in the schema for all items, but:
- **FRYER items**: Populated with sauce/variant component ID (e.g., 4000534 for Buffalo Sauce)
- **TURBO OVEN and other appliances**: Field exists but is NULL or not used; batching uses `resourceConfig` (temperature/windspeed settings) instead

**Query Implication**: When filtering for fryer batching, you should filter by appliance type (e.g., `appliance = 'FRYER'`) rather than assuming `batch_eligible_item_id IS NOT NULL` identifies all batchable items.

**Why This Matters**: Different appliance types use different batching identifiers, and the presence of the field doesn't indicate it's being used for batching.

---

## Wrong Year in Date Filter

### ❌ Wrong: Using wrong year
```sql
WHERE DATE(created_time) = '2025-01-31'  -- Wrong year!
```

### ✅ Correct: Check actual data year
```sql
WHERE DATE(created_time) = '2026-01-31'  -- Correct year
```

**Why This Matters**: Easy mistake when writing queries. Always verify data exists for your date range.

---

## Summary Checklist

Before querying batching data:

- [ ] Using correct JSON extraction pattern (UNNEST array first)
- [ ] Filtering to COOK activity only
- [ ] Including date filter on sequencing_contexts
- [ ] Using context_id (not _id) for context joins
- [ ] Checking hot_hold_eligible exclusion
- [ ] Understanding batch_eligible_item_id is FRYER-SPECIFIC (sauce/variant, not base item)
- [ ] Including service window filter for CookBook queries
- [ ] Verifying all four batching criteria when analyzing batch eligibility
- [ ] Distinguishing potential batches (sequencing_contexts) from actual batches (optimizer_batch)
- [ ] Accounting for human batch limit of 3 (not just physical batch_limit)
- [ ] Understanding CP-SAT may not batch even eligible items
