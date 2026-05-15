# Rule Design Patterns for Order Splitting

Best practices for designing, testing, and deploying SKU grouping rules in the Command Center Splitter service.

---

## The Golden Rule

**NEVER design rules without first establishing an accurate baseline with proper data scoping.**

Bad baseline → Bad rules → Wasted effort → Failed optimization

---

## Phase 1: Data Scoping and Baseline Establishment

### Step 1: Analyze Full Scope

Start by understanding ALL data in the target category:

```sql
-- See complete distribution of SKU prefixes
SELECT
  SUBSTR(item_sku, 1, 2) as sku_prefix,
  COUNT(*) as assignment_count,
  COUNT(DISTINCT facility_id) as facility_count,
  ROUND(AVG(COUNT(*)) OVER (), 1) as avg_per_prefix
FROM `wonder-raw-prod.pg_batch_command_center.order_split_cache`
WHERE order_split_value = 'Global'  -- or target split
GROUP BY SUBSTR(item_sku, 1, 2)
ORDER BY assignment_count DESC;
```

### Step 2: Identify Object Type Distribution

```sql
-- Check what object types exist in the target split
SELECT
  si.object_type,
  COUNT(*) as count,
  COUNT(DISTINCT osc.facility_id) as facilities,
  ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) as pct
FROM `wonder-raw-prod.pg_batch_command_center.order_split_cache` osc
JOIN `wonder-raw-prod.pg_batch_command_center.sku_info` si
  ON osc.item_sku = si.item_number
WHERE osc.order_split_value = 'Global'
GROUP BY si.object_type
ORDER BY count DESC;
```

### Step 3: Ask Critical Questions

Before proceeding, clarify with stakeholders:

- **Are NON_FOOD items relevant?** (Usually no - they're not warehouse-fulfilled)
- **Which item number prefixes are in scope?** (e.g., only 88*, exclude 80* and 5*)
- **Are there special handling categories?** (e.g., packaged goods, beverages)
- **What's the actual operational problem?** (Too many SKUs? Wrong grouping?)

### Step 4: Establish Corrected Baseline

Apply appropriate filters and recalculate baseline:

```sql
-- Baseline with proper scoping
WITH actual_scope AS (
  SELECT
    facility_id,
    COUNT(*) as sku_count
  FROM `wonder-raw-prod.pg_batch_command_center.order_split_cache` osc
  JOIN `wonder-raw-prod.pg_batch_command_center.sku_info` si
    ON osc.item_sku = si.item_number
  WHERE order_split_value = 'Global'
    -- Apply discovered filters
    AND si.object_type != 'NON_FOOD'      -- Exclude non-warehouse items
    AND osc.item_sku LIKE '88%'           -- Only relevant prefix
    -- Add more filters as needed
  GROUP BY facility_id
)
SELECT
  MIN(sku_count) as min_size,
  ROUND(AVG(sku_count), 1) as avg_size,
  APPROX_QUANTILES(sku_count, 100)[OFFSET(50)] as median_size,
  MAX(sku_count) as max_size,
  COUNT(CASE WHEN sku_count >= 100 THEN 1 END) as problem_facilities,
  COUNT(*) as total_facilities
FROM actual_scope;
```

### Real-World Example

**Initial (wrong) analysis**: "Global orders have 274 SKUs average"

**After excluding NON_FOOD**: 140 SKUs average (49% reduction!)

**After excluding 80\* items**: 54 SKUs average (80% reduction from original!)

**Final scope (88\* items only)**: 55 SKUs average

**Completely different problem space!** Rules designed on wrong baseline would fail.

---

## Phase 2: Rule Design and Simulation

### Step 1: Identify High-Impact Categories

Find categories that affect the most SKUs:

```sql
-- Which object_sub_types could be split out?
SELECT
  si.object_sub_type,
  COUNT(DISTINCT osc.facility_id) as facilities_affected,
  ROUND(AVG(COUNT(*)) OVER (PARTITION BY si.object_sub_type), 1) as avg_skus_per_facility,
  COUNT(*) as total_assignments
FROM `wonder-raw-prod.pg_batch_command_center.order_split_cache` osc
JOIN `wonder-raw-prod.pg_batch_command_center.sku_info` si
  ON osc.item_sku = si.item_number
WHERE osc.order_split_value = 'Global'
  AND si.object_type != 'NON_FOOD'
  AND osc.item_sku LIKE '88%'
GROUP BY si.object_sub_type, osc.facility_id
ORDER BY avg_skus_per_facility DESC;
```

**Prioritize categories by**:
- Largest average SKU count per facility
- Operationally logical groupings (kitchen staff will understand)
- Clear distinction from other categories

### Step 2: Design Rule Priority Sequence

Rules are evaluated in priority order (lowest number first). **First match wins**.

**Example Priority Design**:
```
Priority 1: Frozen (storage_type = FROZEN)
Priority 2: Beverages (object_sub_type = BEVERAGE)
Priority 3: Common Stock (object_sub_type = COMMON_STOCK)
Priority 4: Packaged Items (object_sub_type = PACKAGED)
Priority 5-8: Pod assignments (if applicable)
Priority 99: Global (catch-all, implicit)
```

**Key Principle**: Start with most specific/highest-impact rules first.

### Step 3: Simulate Proposed Rules

Test rule effectiveness BEFORE deployment:

```sql
-- Simulate rule application
WITH rule_simulation AS (
  SELECT
    facility_id,
    item_sku,
    -- Apply rules in priority order
    CASE
      WHEN si.storage_type = 'FROZEN' THEN 'Frozen'
      WHEN si.object_sub_type IN ('ALCOHOLIC_BEVERAGE', 'NON_ALCOHOLIC_BEVERAGE') THEN 'Beverages'
      WHEN si.object_sub_type = 'COMMON_STOCK' THEN 'Common Stock'
      WHEN si.object_sub_type = 'PACKAGED' THEN 'Packaged Items'
      ELSE 'Global'
    END as proposed_split
  FROM `wonder-raw-prod.pg_batch_command_center.order_split_cache` osc
  JOIN `wonder-raw-prod.pg_batch_command_center.sku_info` si
    ON osc.item_sku = si.item_number
  WHERE osc.order_split_value = 'Global'
    AND si.object_type != 'NON_FOOD'
    AND osc.item_sku LIKE '88%'
),
split_sizes AS (
  SELECT
    proposed_split,
    facility_id,
    COUNT(*) as sku_count
  FROM rule_simulation
  GROUP BY proposed_split, facility_id
)
SELECT
  proposed_split,
  COUNT(DISTINCT facility_id) as facilities,
  MIN(sku_count) as min_skus,
  ROUND(AVG(sku_count), 1) as avg_skus,
  APPROX_QUANTILES(sku_count, 100)[OFFSET(50)] as median_skus,
  MAX(sku_count) as max_skus
FROM split_sizes
GROUP BY proposed_split
ORDER BY avg_skus DESC;
```

### Step 4: Validate Success Criteria

Define clear success metrics:

```sql
-- Check if rules achieve target (e.g., no facility > 99 SKUs per split)
WITH rule_simulation AS (
  SELECT
    facility_id,
    item_sku,
    CASE
      WHEN si.storage_type = 'FROZEN' THEN 'Frozen'
      WHEN si.object_sub_type IN ('ALCOHOLIC_BEVERAGE', 'NON_ALCOHOLIC_BEVERAGE') THEN 'Beverages'
      WHEN si.object_sub_type = 'COMMON_STOCK' THEN 'Common Stock'
      WHEN si.object_sub_type = 'PACKAGED' THEN 'Packaged Items'
      ELSE 'Global'
    END as proposed_split
  FROM `wonder-raw-prod.pg_batch_command_center.order_split_cache` osc
  JOIN `wonder-raw-prod.pg_batch_command_center.sku_info` si
    ON osc.item_sku = si.item_number
  WHERE osc.order_split_value = 'Global'
    AND si.object_type != 'NON_FOOD'
    AND osc.item_sku LIKE '88%'
),
split_sizes AS (
  SELECT
    facility_id,
    proposed_split,
    COUNT(*) as sku_count
  FROM rule_simulation
  GROUP BY facility_id, proposed_split
)
SELECT
  proposed_split,
  COUNT(CASE WHEN sku_count <= 99 THEN 1 END) as success_count,
  COUNT(*) as total_facilities,
  ROUND(100.0 * COUNT(CASE WHEN sku_count <= 99 THEN 1 END) / COUNT(*), 1) as success_pct
FROM split_sizes
GROUP BY proposed_split
ORDER BY success_pct DESC;
```

**Target**: 100% success rate on defined metric before deployment.

---

## Phase 3: Iterative Refinement

### When Rules Don't Hit Target

If simulation shows some facilities still exceed target:

1. **Analyze failures**: Which facilities? Which SKUs?
   ```sql
   SELECT facility_id, proposed_split, sku_count
   FROM split_sizes
   WHERE sku_count > 99
   ORDER BY sku_count DESC;
   ```

2. **Identify additional split opportunities**:
   ```sql
   -- What else can we split from the failing facilities?
   -- Note: This assumes 'failures' CTE exists with facility_id of failing facilities
   SELECT
     si.object_sub_type,
     COUNT(*) as sku_count
   FROM rule_simulation rs
   JOIN `wonder-raw-prod.pg_batch_command_center.sku_info` si
     ON rs.item_sku = si.item_number
   WHERE rs.facility_id IN (SELECT facility_id FROM failures)
     AND rs.proposed_split = 'Global'  -- Still in catch-all
   GROUP BY si.object_sub_type
   ORDER BY sku_count DESC;
   ```

3. **Add more granular rules**: Split large categories further
   ```sql
   -- Example: Split Common Stock by temperature
   WHEN si.object_sub_type = 'COMMON_STOCK' AND si.storage_type = 'FROZEN' THEN 'Common Stock Frozen'
   WHEN si.object_sub_type = 'COMMON_STOCK' AND si.storage_type = 'CHILLED' THEN 'Common Stock Chilled'
   WHEN si.object_sub_type = 'COMMON_STOCK' THEN 'Common Stock Ambient'
   ```

4. **Re-simulate and validate**: Repeat until 100% success

---

## Phase 4: Deployment and Monitoring

### Pre-Deployment Checklist

- [ ] Baseline established with correct data scope
- [ ] Rules tested on actual relevant data subset
- [ ] 100% success rate achieved on target metric
- [ ] Rule priority sequence finalized
- [ ] Rule parameters documented
- [ ] Stakeholder approval obtained

### Deployment Pattern

Rules are typically configured through the rules engine application, not via direct SQL INSERTs.

**Configuration Example** (conceptual):
```
Priority 1: Frozen          → StorageTypeRule    → {"include": ["FROZEN"]}
Priority 2: Beverages       → ObjectSubTypeRule  → {"include": ["ALCOHOLIC_BEVERAGE", "NON_ALCOHOLIC_BEVERAGE"]}
Priority 3: Common Stock    → ObjectSubTypeRule  → {"include": ["COMMON_STOCK"]}
Priority 4: Packaged Items  → ObjectSubTypeRule  → {"include": ["PACKAGED"]}
```

**Verify Deployment**:
```sql
-- Check rules in sku_grouping_rules table
SELECT priority, group_name, rule_id, parameters
FROM `wonder-raw-prod.pg_batch_command_center.sku_grouping_rules`
WHERE policy_id = 1
ORDER BY priority;

-- Verify results match simulation
SELECT order_split_value, COUNT(DISTINCT facility_id) as facilities, COUNT(*) as assignments
FROM `wonder-raw-prod.pg_batch_command_center.order_split_cache`
GROUP BY order_split_value
ORDER BY assignments DESC;
```

### Post-Deployment Monitoring

```sql
-- Monitor recent changes
SELECT
  order_split_value,
  operation,
  COUNT(*) as change_count
FROM `wonder-raw-prod.pg_batch_command_center.order_split_cache_logs`
WHERE created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR)
GROUP BY order_split_value, operation
ORDER BY change_count DESC;

-- Validate no facilities exceed target
SELECT
  order_split_value,
  facility_id,
  COUNT(*) as sku_count
FROM `wonder-raw-prod.pg_batch_command_center.order_split_cache`
GROUP BY order_split_value, facility_id
HAVING COUNT(*) > 99
ORDER BY sku_count DESC;
-- Expect: No results if rules working correctly
```

---

## Common Mistakes

For detailed guidance on avoiding common mistakes including data scoping errors, BigQuery syntax issues, and rule design pitfalls, see [common-pitfalls.md](common-pitfalls.md).

**Key pitfalls when designing rules:**
1. ❌ Skipping data scoping - Always establish accurate baseline with proper filters first
2. ❌ Not testing on actual data - Simulate rules before deployment
3. ❌ Ignoring rule priority - First matching rule wins; sequence matters
4. ❌ Accepting partial success - Iterate until 100% facilities meet target
5. ❌ Not validating with stakeholders - Ensure split names make operational sense

---

## Template Workflow

Copy this for each rule design project:

```sql
-- ============================================
-- RULE DESIGN: [Name of optimization]
-- Target: [Define success metric]
-- ============================================

-- 1. BASELINE (with proper scope)
WITH actual_scope AS (
  SELECT facility_id, COUNT(*) as sku_count
  FROM `wonder-raw-prod.pg_batch_command_center.order_split_cache` osc
  JOIN `wonder-raw-prod.pg_batch_command_center.sku_info` si
    ON osc.item_sku = si.item_number
  WHERE order_split_value = 'Global'
    AND si.object_type != 'NON_FOOD'  -- Adjust filters
    -- Add more scope filters
  GROUP BY facility_id
)
SELECT
  MIN(sku_count) as min,
  ROUND(AVG(sku_count), 1) as avg,
  MAX(sku_count) as max,
  COUNT(CASE WHEN sku_count > 99 THEN 1 END) as failures
FROM actual_scope;

-- 2. IDENTIFY OPPORTUNITIES
SELECT
  si.object_sub_type,
  COUNT(*) / COUNT(DISTINCT osc.facility_id) as avg_per_facility
FROM `wonder-raw-prod.pg_batch_command_center.order_split_cache` osc
JOIN `wonder-raw-prod.pg_batch_command_center.sku_info` si
  ON osc.item_sku = si.item_number
WHERE [proper scope filters]
GROUP BY si.object_sub_type
ORDER BY avg_per_facility DESC;

-- 3. SIMULATE RULES
WITH rule_simulation AS (
  SELECT
    facility_id, item_sku,
    CASE
      -- Add your proposed rules here in priority order
      WHEN [rule 1 condition] THEN 'Split 1'
      WHEN [rule 2 condition] THEN 'Split 2'
      ELSE 'Global'
    END as proposed_split
  FROM `wonder-raw-prod.pg_batch_command_center.order_split_cache` osc
  JOIN `wonder-raw-prod.pg_batch_command_center.sku_info` si
    ON osc.item_sku = si.item_number
  WHERE [proper scope filters]
)
SELECT
  proposed_split,
  MIN(sku_count) as min,
  ROUND(AVG(sku_count), 1) as avg,
  MAX(sku_count) as max
FROM (
  SELECT proposed_split, facility_id, COUNT(*) as sku_count
  FROM rule_simulation
  GROUP BY proposed_split, facility_id
) subquery
GROUP BY proposed_split;

-- 4. VALIDATE SUCCESS
-- [Check if rules achieve 100% success on target metric]

-- 5. ITERATE if needed
-- [Refine rules and repeat steps 3-4]
```

---

## Summary

**The Rule Design Process**:
1. ✅ Establish accurate baseline with proper data scoping
2. ✅ Identify high-impact categories
3. ✅ Design rule priority sequence
4. ✅ Simulate rules on actual data
5. ✅ Validate 100% success on target metric
6. ✅ Iterate until target achieved
7. ✅ Deploy and monitor

**Success Formula**: Accurate Baseline + Iterative Testing + 100% Validation = Successful Rules
