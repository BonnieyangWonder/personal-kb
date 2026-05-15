# Wonder Menu Availability - Common Pitfalls

This document covers common mistakes when querying menu availability data and how to avoid them.

---

## Pitfall 1: Counting Items Without DISTINCT

### Problem
Same `item_number` appears multiple times in the table (across brands and categories), leading to inflated counts.

### ❌ Wrong
```sql
-- This counts every row, not unique items!
SELECT
  hdr_id,
  COUNT(item_number) as num_items  -- WRONG: counts duplicates
FROM `wonder-dw-prod-brd.forecast.active_menu_v2`
WHERE service_date = '2025-12-29'
  AND service_time_type = 'DINNER'
GROUP BY hdr_id;
```

**Result**: Returns ~407 items per HDR (inflated due to duplicates)

### ✅ Correct
```sql
-- Count unique items only
SELECT
  hdr_id,
  COUNT(DISTINCT item_number) as num_items  -- CORRECT: unique items
FROM `wonder-dw-prod-brd.forecast.active_menu_v2`
WHERE service_date = '2025-12-29'
  AND service_time_type = 'DINNER'
GROUP BY hdr_id;
```

**Result**: Returns actual unique item count (e.g., 238-491 items per HDR)

**Why**: Same item like "Coca-Cola" (8005217) appears once per brand at the HDR, creating duplicate rows for the same menu item.

---

## Pitfall 2: Using menu_item_id Instead of item_number

### Problem
`menu_item_id` is unique per row (UUID), while `item_number` is the stable identifier for the menu item itself.

### ❌ Wrong
```sql
-- Trying to join on menu_item_id
SELECT
  am.menu_item_id,
  iv.name
FROM `wonder-dw-prod-brd.forecast.active_menu_v2` am
LEFT JOIN `secure-recipe-prod.recipe_v2.item_versions` iv
  ON CAST(iv.item_number AS STRING) = am.menu_item_id  -- WRONG!
WHERE am.service_date = '2025-12-29';
```

**Result**: Zero matches - `menu_item_id` is a UUID that doesn't exist in other systems

### ✅ Correct
```sql
-- Join on item_number
SELECT
  am.item_number,
  am.item_name,
  iv.name as cookbook_name
FROM `wonder-dw-prod-brd.forecast.active_menu_v2` am
LEFT JOIN `secure-recipe-prod.recipe_v2.item_versions` iv
  ON CAST(iv.item_number AS STRING) = am.item_number  -- CORRECT!
WHERE am.service_date = '2025-12-29';
```

**Result**: Successful join on stable `item_number` identifier

**Why**: `menu_item_id` is internal to this table; `item_number` is the standard identifier across all systems.

---

## Pitfall 3: Forgetting to Filter by service_date

### Problem
Table contains 3 months of data (~32M rows). Queries without date filters are slow and return incorrect aggregates.

### ❌ Wrong
```sql
-- No date filter - scans entire table!
SELECT
  hdr_id,
  COUNT(DISTINCT item_number) as num_items
FROM `wonder-dw-prod-brd.forecast.active_menu_v2`
WHERE service_time_type = 'DINNER'
GROUP BY hdr_id;
```

**Result**:
- Slow query (scans 32M rows)
- Incorrect counts (aggregates across multiple dates)

### ✅ Correct
```sql
-- Always filter by service_date
SELECT
  hdr_id,
  COUNT(DISTINCT item_number) as num_items
FROM `wonder-dw-prod-brd.forecast.active_menu_v2`
WHERE service_date = '2025-12-29'  -- REQUIRED!
  AND service_time_type = 'DINNER'
GROUP BY hdr_id;
```

**Result**: Fast, accurate results for specific date

**Why**: Table is designed for time-series queries; always specify the date(s) you're analyzing.

---

## Pitfall 4: Mixing Lunch and Dinner Without Deduplication

### Problem
Same item appears for both LUNCH and DINNER. Queries that don't filter `service_time_type` double-count items.

### ❌ Wrong
```sql
-- Gets both lunch and dinner, double-counts items
SELECT
  hdr_id,
  COUNT(item_number) as total_menu_instances
FROM `wonder-dw-prod-brd.forecast.active_menu_v2`
WHERE service_date = '2025-12-29'
GROUP BY hdr_id;
```

**Result**: Inflated counts (items counted twice if available for both lunch and dinner)

### ✅ Correct Option 1: Filter by Service Time
```sql
-- Get dinner menu only
SELECT
  hdr_id,
  COUNT(DISTINCT item_number) as num_items
FROM `wonder-dw-prod-brd.forecast.active_menu_v2`
WHERE service_date = '2025-12-29'
  AND service_time_type = 'DINNER'  -- Pick one service time
GROUP BY hdr_id;
```

### ✅ Correct Option 2: Deduplicate Across Service Times
```sql
-- Get unique items across both lunch and dinner
SELECT
  hdr_id,
  COUNT(DISTINCT item_number) as unique_items_either_service
FROM `wonder-dw-prod-brd.forecast.active_menu_v2`
WHERE service_date = '2025-12-29'
GROUP BY hdr_id;
```

**Why**: Be explicit about whether you want lunch-only, dinner-only, or union of both.

---

## Pitfall 5: Using Legacy Table (active_menu v1)

### Problem
`active_menu` (v1) is the legacy table with less data and different schema. New queries should use v2.

### ❌ Wrong (Unless Intentionally Accessing Historical Data)
```sql
-- Using legacy table
SELECT
  store_id,
  business_line,
  COUNT(DISTINCT item_number) as num_items
FROM `wonder-dw-prod-brd.forecast.active_menu`  -- OLD TABLE!
WHERE service_date = '2025-12-29'
GROUP BY store_id, business_line;
```

**Result**:
- Fewer rows (~252k vs ~318k)
- Missing fields (no `item_name`, `category_name`, `menu_item_id`, `menu_version_id`)

### ✅ Correct
```sql
-- Use current v2 table
SELECT
  hdr_id,  -- Note: field renamed from store_id
  COUNT(DISTINCT item_number) as num_items
FROM `wonder-dw-prod-brd.forecast.active_menu_v2`  -- CURRENT TABLE!
WHERE service_date = '2025-12-29'
GROUP BY hdr_id;
```

**Result**: Complete data with all fields

**Why**: v2 is the current standard; v1 will be deprecated. Only use v1 for historical queries (pre-2025).

---

## Pitfall 6: Treating category_name and menu_course as Hierarchical

### Problem
Assuming `category_name` rolls up to `menu_course`, when they're actually independent classifications.

### ❌ Wrong Assumption
```sql
-- Assuming one category per course
SELECT
  menu_course,
  category_name,
  COUNT(DISTINCT item_number) as num_items
FROM `wonder-dw-prod-brd.forecast.active_menu_v2`
WHERE service_date = '2025-12-29'
  AND service_time_type = 'DINNER'
GROUP BY menu_course, category_name
HAVING COUNT(DISTINCT item_number) > 1;
```

**Reality**: Same item appears in multiple (course, category) combinations:
- "Small Ranch" → (Ancillary Items, Extras), (Ancillary Items, Combos), (Sides, Extras), etc.
- No clean hierarchy exists

### ✅ Correct Approach
```sql
-- Treat them as independent dimensions
SELECT
  item_number,
  item_name,
  STRING_AGG(DISTINCT menu_course ORDER BY menu_course) as courses,
  STRING_AGG(DISTINCT category_name ORDER BY category_name) as categories
FROM `wonder-dw-prod-brd.forecast.active_menu_v2`
WHERE service_date = '2025-12-29'
  AND service_time_type = 'DINNER'
  AND hdr_id = 'f8ff6993-4cf0-4779-abb9-70e82f778ad2'
GROUP BY item_number, item_name
ORDER BY item_name;
```

**Why**: Items can appear in multiple courses and multiple categories. They're independent classification dimensions.

---

## Pitfall 7: Joining Without All Required Keys

### Problem
Joining on `hdr_id` alone without `service_date` and `service_time_type` creates cartesian product.

### ❌ Wrong
```sql
-- Incomplete join - missing date and service time
SELECT
  am.item_number,
  am.item_name,
  cal.service_date,
  cal.service_time_type
FROM `wonder-dw-prod-brd.forecast.active_menu_v2` am
INNER JOIN `wonder-dw-prod-brd.forecast.active_service_calendar_v2` cal
  ON am.hdr_id = cal.hdr_id  -- INCOMPLETE!
WHERE am.service_date = '2025-12-29';
```

**Result**: Cartesian explosion - each menu item matched to all calendar entries for that HDR

### ✅ Correct
```sql
-- Complete join with all matching keys
SELECT
  am.item_number,
  am.item_name,
  cal.service_date,
  cal.service_time_type
FROM `wonder-dw-prod-brd.forecast.active_menu_v2` am
INNER JOIN `wonder-dw-prod-brd.forecast.active_service_calendar_v2` cal
  ON am.hdr_id = cal.hdr_id
  AND am.service_date = cal.service_date              -- ADD DATE!
  AND am.service_time_type = cal.service_time_type    -- ADD SERVICE TIME!
WHERE am.service_date = '2025-12-29';
```

**Result**: Accurate 1:1 match between menu items and calendar entries

**Why**: Time-series data requires date and time period in joins to avoid cartesian products.

---

## Pitfall 8: Expecting Menu Availability = Component Availability

### Problem
Assuming `active_menu_v2` shows component-level forecasts or inventory needs.

### ❌ Wrong Expectation
```sql
-- Trying to find forecasted component demand in active_menu_v2
SELECT
  item_number,
  item_name
FROM `wonder-dw-prod-brd.forecast.active_menu_v2`
WHERE item_number LIKE '4%'  -- Looking for component items (4xxxxxx)
  AND service_date = '2025-12-29';
```

**Result**: Zero rows - `active_menu_v2` only has menu items (8xxxxxx)

### ✅ Correct Approach
```sql
-- For component forecasts, use different table
SELECT
  item_number,
  forecasted_consumption
FROM `wonder-dw-prod-brd.forecast.latest_customer_forecast_v2`
WHERE item_number LIKE '4%'  -- Component items ARE here
  AND service_date = '2025-12-29';
```

**Result**: Component-level forecasts (fries, chicken, rice, etc.)

**Why**:
- `active_menu_v2` = customer-facing menu items (what customers order)
- `latest_customer_forecast_v2` = component-level demand (what to stock)
- These are different tables serving different use cases

---

## Pitfall 9: Ignoring Row Duplication by Brand

### Problem
Trying to get "one row per item per HDR per date" without accounting for multiple brands.

### ❌ Wrong
```sql
-- Expecting one row per item, but getting multiple
SELECT
  hdr_id,
  service_date,
  item_number,
  item_name
FROM `wonder-dw-prod-brd.forecast.active_menu_v2`
WHERE hdr_id = 'f8ff6993-4cf0-4779-abb9-70e82f778ad2'
  AND service_date = '2025-12-29'
  AND service_time_type = 'DINNER'
  AND item_number = '8005217'  -- Coca-Cola
ORDER BY restaurant_brand_id;
```

**Result**: Multiple rows for Coca-Cola (appears once per brand at this HDR)

### ✅ Correct Option 1: Deduplicate
```sql
-- Get one row per item
SELECT DISTINCT
  hdr_id,
  service_date,
  item_number,
  item_name
FROM `wonder-dw-prod-brd.forecast.active_menu_v2`
WHERE hdr_id = 'f8ff6993-4cf0-4779-abb9-70e82f778ad2'
  AND service_date = '2025-12-29'
  AND service_time_type = 'DINNER'
  AND item_number = '8005217';
```

### ✅ Correct Option 2: Aggregate Brands
```sql
-- Show which brands have this item
SELECT
  hdr_id,
  service_date,
  item_number,
  item_name,
  COUNT(DISTINCT restaurant_brand_id) as num_brands,
  STRING_AGG(DISTINCT category_name) as categories
FROM `wonder-dw-prod-brd.forecast.active_menu_v2`
WHERE hdr_id = 'f8ff6993-4cf0-4779-abb9-70e82f778ad2'
  AND service_date = '2025-12-29'
  AND service_time_type = 'DINNER'
  AND item_number = '8005217'
GROUP BY hdr_id, service_date, item_number, item_name;
```

**Why**: Items appear once per brand they're available in. Use DISTINCT or GROUP BY to deduplicate.

---

## Pitfall 10: Confusing item_number with item_name for Joins

### Problem
Trying to join on `item_name` instead of `item_number` when linking to other systems.

### ❌ Wrong
```sql
-- Joining on name instead of number
SELECT
  am.item_name,
  iv.object_type
FROM `wonder-dw-prod-brd.forecast.active_menu_v2` am
LEFT JOIN `secure-recipe-prod.recipe_v2.item_versions` iv
  ON iv.name = am.item_name  -- FRAGILE!
WHERE am.service_date = '2025-12-29';
```

**Problems**:
- Names can change over time
- Names may have slight variations ("Coca-Cola" vs "Coca Cola")
- Names are not unique across systems
- Slow string matching

### ✅ Correct
```sql
-- Always join on stable numeric identifiers
SELECT
  am.item_number,
  am.item_name,
  iv.object_type
FROM `wonder-dw-prod-brd.forecast.active_menu_v2` am
LEFT JOIN `secure-recipe-prod.recipe_v2.item_versions` iv
  ON CAST(iv.item_number AS STRING) = am.item_number  -- STABLE!
WHERE am.service_date = '2025-12-29';
```

**Result**: Reliable, performant joins using numeric IDs

**Why**: `item_number` is the stable system identifier across all Wonder systems. Always join on numbers, not names.

---

---

## Pitfall 11: Using Wrong Table for HDR Lookups

### Problem
Searching for HDR IDs in wrong tables like `command_center.nodes` instead of the canonical dimension table.

### ❌ Wrong
```sql
-- Using command_center.nodes (less direct)
SELECT
  facility_id as hdr_id,
  facility_name
FROM `wonder-dw-prod-brd.command_center.nodes`
WHERE LOWER(facility_name) LIKE '%upper west%'
  AND facility_type = 'HDR';
```

**Problems**:
- Not the canonical source for HDR information
- Different field names (`facility_id` vs `hdr_id`, `facility_name` vs `hdr_name`)
- Missing useful HDR attributes (opening date, status, location details)

### ✅ Correct
```sql
-- Use dim_hdrs (canonical HDR dimension table)
SELECT
  hdr_id,
  hdr_name,
  current_hdr_status,
  city,
  state_code
FROM `wonder-dw-prod-brd.dw.dim_hdrs`
WHERE LOWER(hdr_name) LIKE '%upper west%'
  AND current_hdr_status = 'OPEN';
```

**Result**: Clean lookup with consistent field names and access to full HDR metadata

**Why**: `wonder-dw-prod-brd.dw.dim_hdrs` is the master dimension table for HDRs. Always use this for HDR lookups.

---

## Pitfall 12: Forgetting to Filter by Restaurant Brand

### Problem
Querying entire HDR menu when you only want a specific restaurant brand's menu.

### ❌ Wrong
```sql
-- Gets ALL items at Upper West Side (254 entrees across all brands)
SELECT DISTINCT
  item_number,
  item_name
FROM `wonder-dw-prod-brd.forecast.active_menu_v2`
WHERE hdr_id = '74e8d0b9-3eda-4510-8ee2-95314a833b27'
  AND service_date = '2026-01-02'
  AND service_time_type = 'DINNER'
  AND menu_course = 'Entrees';
```

**Result**: Returns 254 entrees across all restaurant brands (Tejas, Burger Baby, Di Fara, etc.)

### ✅ Correct
```sql
-- Gets ONLY Tejas Barbecue items (9 entrees)
SELECT DISTINCT
  item_number,
  item_name
FROM `wonder-dw-prod-brd.forecast.active_menu_v2`
WHERE hdr_id = '74e8d0b9-3eda-4510-8ee2-95314a833b27'
  AND restaurant_brand_id = '356049e8-fa7f-492d-80c7-98530972c0d7'  -- Tejas Barbecue
  AND service_date = '2026-01-02'
  AND service_time_type = 'DINNER'
  AND menu_course = 'Entrees';
```

**Result**: Returns 9 Tejas-specific entrees

**With Dimension Table Join** (more readable):
```sql
-- Look up brand ID first, then filter
SELECT DISTINCT
  am.item_number,
  am.item_name
FROM `wonder-dw-prod-brd.forecast.active_menu_v2` am
INNER JOIN `wonder-dw-prod-brd.dw.dim_restaurant_brands` rb
  ON am.restaurant_brand_id = rb.restaurant_brand_id
WHERE am.hdr_id = '74e8d0b9-3eda-4510-8ee2-95314a833b27'
  AND rb.restaurant_brand_name = 'Tejas Barbecue'
  AND am.service_date = '2026-01-02'
  AND am.service_time_type = 'DINNER'
  AND am.menu_course = 'Entrees';
```

**Why**: HDRs host multiple restaurant brands. Individual brand menus are much smaller than full HDR menus.

---

## Quick Reference: Common Mistakes Summary

| Mistake | Impact | Fix |
|---------|--------|-----|
| Not using DISTINCT for counts | Inflated item counts | `COUNT(DISTINCT item_number)` |
| Using `menu_item_id` for joins | Zero matches | Use `item_number` instead |
| No `service_date` filter | Slow query, wrong aggregates | Always filter by date |
| No `service_time_type` filter | Double-counting lunch+dinner | Specify LUNCH/DINNER or use DISTINCT |
| Using `active_menu` (v1) | Missing data and fields | Use `active_menu_v2` |
| Assuming category hierarchy | Logic errors | Treat course and category as independent |
| Incomplete join keys | Cartesian product | Join on `(hdr_id, service_date, service_time_type)` |
| Looking for components | Zero results | Use `latest_customer_forecast_v2` for components |
| Ignoring brand duplication | Duplicate rows | Use DISTINCT or GROUP BY |
| Joining on `item_name` | Fragile, slow joins | Join on `item_number` |
| Using wrong table for HDR lookup | Indirect, inconsistent | Use `dw.dim_hdrs` not `command_center.nodes` |
| Not filtering by restaurant brand | Get all brands, not specific one | Add `restaurant_brand_id` filter |

---

## Testing Your Queries

### Validation Checklist

Before running a query in production, verify:

1. ✅ **HDR lookup using dim_hdrs?** - Use `dw.dim_hdrs` not `command_center.nodes`
2. ✅ **Date filter present?** - `WHERE service_date = ...`
3. ✅ **DISTINCT for counts?** - `COUNT(DISTINCT item_number)`
4. ✅ **Using v2 table?** - `active_menu_v2`, not `active_menu`
5. ✅ **Service time specified?** - If needed, filter `service_time_type`
6. ✅ **Joining on item_number?** - Not `menu_item_id` or `item_name`
7. ✅ **Complete join keys?** - Include date and service time in joins
8. ✅ **Expected row count?** - Sample with LIMIT first to verify

### Sample Validation Query
```sql
-- Template for safe queries
SELECT
  hdr_id,
  COUNT(DISTINCT item_number) as unique_items,
  COUNT(*) as total_rows
FROM `wonder-dw-prod-brd.forecast.active_menu_v2`
WHERE service_date = CURRENT_DATE('America/New_York')  -- ✅ Date filter
  AND service_time_type = 'DINNER'                      -- ✅ Service time
GROUP BY hdr_id
LIMIT 10;  -- ✅ Limit for testing
```
