# Common Pitfalls and Gotchas - Command Center

Critical mistakes to avoid when working with the Command Center order splitting system.

---

## Table References - Missing Dataset Prefix

### ❌ Wrong: Forgetting dataset prefix
```sql
-- FAILS - ambiguous table reference
SELECT * FROM order_split_cache WHERE facility_id = 'some-uuid'
```

### ✅ Correct: Use fully qualified table names
```sql
-- WORKS - explicit dataset reference
SELECT * FROM `wonder-raw-prod.pg_batch_command_center.order_split_cache`
WHERE facility_id = 'some-uuid'
```

**Pattern**: Always use backticks with full `project.dataset.table` format.

---

## Data Scoping - Analyzing Wrong Subset

Most critical mistake in Command Center queries.

### ❌ Wrong: Querying without filters
```sql
-- Includes NON_FOOD items that aren't warehouse-fulfilled
SELECT facility_id, COUNT(*) as sku_count
FROM `wonder-raw-prod.pg_batch_command_center.order_split_cache`
WHERE order_split_value = 'Global'
GROUP BY facility_id
```

### ✅ Correct: Apply appropriate filters first
```sql
-- Excludes non-relevant items
SELECT facility_id, COUNT(*) as sku_count
FROM `wonder-raw-prod.pg_batch_command_center.order_split_cache` osc
JOIN `wonder-raw-prod.pg_batch_command_center.sku_info` si
  ON osc.item_sku = si.item_number
WHERE order_split_value = 'Global'
  AND si.object_type != 'NON_FOOD'  -- Exclude non-warehouse items
  AND osc.item_sku LIKE '88%'       -- Focus on relevant prefix
GROUP BY facility_id
```

**Why This Matters**: Wrong data scope can show problems 3-5x larger than they actually are. For example:
- Wrong analysis: "Global has 274 SKUs average"
- Correct analysis (after filtering): "Global has 55 SKUs average"
- **That's an 80% difference!**

**Always ask these questions before analyzing:**
1. Should NON_FOOD items be included?
2. Which item number prefixes are in scope? (88\*, 80\*, 5\*?)
3. Are there special handling categories to exclude?

---

## SKU Prefix Analysis - Wrong Function

### ❌ Wrong: Using SUBSTRING (PostgreSQL syntax)
```sql
-- FAILS in BigQuery
SELECT SUBSTRING(item_sku, 1, 2) as prefix
FROM `wonder-raw-prod.pg_batch_command_center.order_split_cache`
```

### ✅ Correct: Use SUBSTR (BigQuery syntax)
```sql
-- WORKS
SELECT SUBSTR(item_sku, 1, 2) as prefix
FROM `wonder-raw-prod.pg_batch_command_center.order_split_cache`
```

---

## Aggregating Distinct Values - Wrong STRING_AGG Usage

### ❌ Wrong: Using DISTINCT with STRING_AGG
```sql
-- FAILS - BigQuery doesn't support DISTINCT in STRING_AGG
SELECT
  item_sku,
  STRING_AGG(DISTINCT order_split_value, ', ') as splits
FROM `wonder-raw-prod.pg_batch_command_center.order_split_cache`
GROUP BY item_sku
```

### ✅ Correct: Remove duplicates first or omit DISTINCT
```sql
-- WORKS - remove duplicates in subquery if needed
WITH deduplicated AS (
  SELECT DISTINCT item_sku, order_split_value
  FROM `wonder-raw-prod.pg_batch_command_center.order_split_cache`
)
SELECT
  item_sku,
  STRING_AGG(order_split_value, ', ') as splits
FROM deduplicated
GROUP BY item_sku
```

---

## Timezone Handling - Wrong Functions

### ❌ Wrong: PostgreSQL timezone syntax
```sql
-- FAILS - PostgreSQL syntax
SELECT created_at AT TIME ZONE 'America/New_York' as created_at_ny
FROM `wonder-raw-prod.pg_batch_command_center.order_split_cache`
```

### ✅ Correct: BigQuery timezone functions
```sql
-- WORKS
SELECT DATETIME(created_at, 'America/New_York') as created_at_ny
FROM `wonder-raw-prod.pg_batch_command_center.order_split_cache`
```

**Common Conversions**:
| PostgreSQL | BigQuery |
|------------|----------|
| `NOW()` | `CURRENT_TIMESTAMP()` |
| `INTERVAL '24 hours'` | `INTERVAL 24 HOUR` |
| `AT TIME ZONE 'America/New_York'` | `DATETIME(TIMESTAMP(col), 'America/New_York')` |
| `DATE_TRUNC('hour', created_at)` | `DATETIME_TRUNC(DATETIME(created_at), HOUR)` |

---

## Date Filtering - Wrong CURRENT_DATE Usage

### ❌ Wrong: Using CURRENT_DATE without timezone
```sql
-- Uses UTC date, not business timezone
WHERE service_date >= CURRENT_DATE
```

### ✅ Correct: Specify timezone for business logic
```sql
-- Uses America/New_York timezone
WHERE service_date >= CURRENT_DATE('America/New_York')
```

---

## JSON Extraction - Wrong Operator

### ❌ Wrong: PostgreSQL JSON operator
```sql
-- FAILS - PostgreSQL syntax
SELECT details->>'matched_rule' as rule_id
FROM `wonder-raw-prod.pg_batch_command_center.order_split_cache`
```

### ✅ Correct: BigQuery JSON function
```sql
-- WORKS
SELECT JSON_EXTRACT_SCALAR(details, '$.matched_rule') as rule_id
FROM `wonder-raw-prod.pg_batch_command_center.order_split_cache`
```

---

## Cross-Project Joins - Missing Nodes Table Qualification

### ❌ Wrong: Unqualified nodes reference
```sql
-- FAILS or uses wrong nodes table
SELECT osc.*, n.facility_name
FROM `wonder-raw-prod.pg_batch_command_center.order_split_cache` osc
JOIN nodes n ON osc.facility_id = n.facility_id
```

### ✅ Correct: Fully qualify nodes table
```sql
-- WORKS - explicit cross-project reference
SELECT osc.*, n.facility_name
FROM `wonder-raw-prod.pg_batch_command_center.order_split_cache` osc
JOIN `wonder-dw-prod-brd.command_center.nodes` n
  ON osc.facility_id = n.facility_id
```

**Note**: The `nodes` table is in a different project/dataset than the order splitting tables.

---

## Schema Verification - Skipping Validation

### ❌ Wrong: Assuming column names
```sql
-- May fail if schema differs from assumptions
SELECT split_id, item_number FROM order_split_cache
```

### ✅ Correct: Verify schema first
```bash
# Check schema before writing queries
bq show --schema wonder-raw-prod:pg_batch_command_center.order_split_cache

# Or use dry run to validate
bq query --dry_run "SELECT * FROM \`wonder-raw-prod.pg_batch_command_center.order_split_cache\` LIMIT 1"
```

---

## Rule Design Workflow Pitfalls

These pitfalls are specific to designing SKU grouping rules in the rules engine.

### ❌ Pitfall 1: Skipping Data Scoping

**Mistake**: Designing rules on all data without filtering

**Result**: Rules optimized for wrong subset; may make actual problem worse

**Solution**: Always establish accurate baseline first with proper filters (see Data Scoping section above)

---

### ❌ Pitfall 2: Not Testing on Actual Data

**Mistake**: Creating rules based on assumptions without simulation

**Result**: Rules fail in production; require emergency rollback

**Solution**: Always simulate rules on actual data before deployment. Use CTEs to test:
```sql
WITH rule_simulation AS (
  SELECT
    facility_id, item_sku,
    CASE
      WHEN si.storage_type = 'FROZEN' THEN 'Frozen'
      WHEN si.object_sub_type = 'COMMON_STOCK' THEN 'Common Stock'
      ELSE 'Global'
    END as proposed_split
  FROM `wonder-raw-prod.pg_batch_command_center.order_split_cache` osc
  JOIN `wonder-raw-prod.pg_batch_command_center.sku_info` si
    ON osc.item_sku = si.item_number
  WHERE osc.order_split_value = 'Global'
    AND si.object_type != 'NON_FOOD'
)
SELECT
  proposed_split,
  COUNT(DISTINCT facility_id) as facilities,
  ROUND(AVG(sku_count), 1) as avg_skus,
  MAX(sku_count) as max_skus
FROM (
  SELECT proposed_split, facility_id, COUNT(*) as sku_count
  FROM rule_simulation
  GROUP BY proposed_split, facility_id
) subquery
GROUP BY proposed_split
```

---

### ❌ Pitfall 3: Ignoring Rule Priority

**Mistake**: Not sequencing rules by impact/specificity

**Result**: Wrong rules match first; incorrect assignments

**Solution**: Rules are evaluated in priority order (lowest number first). First match wins. Always design with this in mind:
```
Priority 1: Most specific (e.g., FROZEN storage)
Priority 2: Specific categories (e.g., BEVERAGES)
Priority 3: Broader categories (e.g., COMMON_STOCK)
Priority 99: Catch-all (Global)
```

---

### ❌ Pitfall 4: Accepting Partial Success

**Mistake**: Deploying rules that only solve 80% of problem

**Result**: Remaining 20% still causes operational issues

**Solution**: Iterate until 100% success on defined metric. If target is "no facility > 99 SKUs per order":
```sql
-- Validate ZERO facilities exceed target
SELECT order_split_value, facility_id, COUNT(*) as sku_count
FROM `wonder-raw-prod.pg_batch_command_center.order_split_cache`
GROUP BY order_split_value, facility_id
HAVING COUNT(*) > 99
ORDER BY sku_count DESC;
-- Should return zero rows
```

---

### ❌ Pitfall 5: Not Validating with Stakeholders

**Mistake**: Creating technically optimal rules that don't make operational sense

**Result**: Kitchen staff confused by assignments; rules ignored

**Solution**: Validate split names and logic with actual users before deployment. Ask:
- Do these category names make sense to kitchen staff?
- Will they understand why these items are grouped together?
- Is the operational workflow clear?

---

## Summary Checklist

Before running analysis queries:
- [ ] Used fully qualified table names with backticks
- [ ] Applied appropriate data scoping filters (NON_FOOD, item prefixes)
- [ ] Used BigQuery functions (SUBSTR, not SUBSTRING)
- [ ] Specified timezone for CURRENT_DATE if filtering by date
- [ ] Qualified nodes table with full cross-project path

Before designing rules:
- [ ] Established accurate baseline with proper data scoping
- [ ] Identified which SKU prefixes and object types are in scope
- [ ] Asked stakeholders about exclusions (NON_FOOD, special cases)
- [ ] Verified facility names (use actual names from nodes table)

Before deploying rules:
- [ ] Simulated rules on actual relevant data subset
- [ ] Validated 100% success rate on target metric
- [ ] Tested rule priority sequence
- [ ] Validated split names with operational users
- [ ] Documented rule reasoning in deployment notes
