---
name: wonder-menu-availability
description: Expert knowledge of Wonder's menu availability system for HDRs. Use when analyzing what menu items are available at specific stores on specific dates and service times (lunch/dinner). Covers active_menu_v2 (current) and active_menu (legacy) tables for customer-facing menu queries.
allowed-tools: Read, Grep, Glob
---

# Wonder Menu Availability Expert

Wonder's menu availability system tracks which menu items are available for customers to order at each HDR (restaurant) on specific dates and service times. This is the source of truth for customer-facing menu displays, ordering systems, and menu planning.

## What This Skill Provides

- **Menu Item Queries** - Find all available menu items for a specific HDR, date, and service time
- **Multi-Brand Coverage** - Query menu items across multiple restaurant brands at the same location
- **Time-Based Availability** - Understand menu changes over time with 3-month future visibility
- **Menu Course Organization** - Filter items by course (Entrees, Sides, Desserts, etc.) and category
- **Service Time Splitting** - Query lunch vs dinner menus separately
- **Legacy Migration Support** - Understand differences between active_menu (v1) and active_menu_v2

## When to Use This Skill

Use this skill when you need to:
- Find what menu items are available at a specific HDR on a specific date
- Compare lunch vs dinner menus for a location
- Count unique menu items across HDRs or brands
- Analyze menu overlap across multiple restaurant brands
- Understand which items appear in multiple categories
- Query future menu availability (up to 3 months ahead)
- Understand the difference between active_menu v1 and v2 tables
- Build reports for menu planning or sales forecasting

**Do NOT use this skill for**:
- Component item forecasting (use wonder-forecasting skill when it exists)
- Inventory planning (use wonder-pantry or wonder-sporklift skills)
- Recipe/BOM queries (use wonder-cookbook skill)

## Core Concepts

### Database Location

- **BigQuery Dataset**: `wonder-dw-prod-brd.forecast`
- **Primary Table**: `active_menu_v2` (current, preferred)
- **Legacy Table**: `active_menu` (v1, will be deprecated)
- **Access**: Via bq CLI or BigQuery Console
- **Related Table**: `active_service_calendar_v2` (defines which HDRs are open when)

### Key Entity Relationships

```
active_menu_v2
  ├─ hdr_id → HDR/store location
  ├─ restaurant_brand_id → Brand (Burger Baby, Tejas BBQ, etc.)
  ├─ restaurant_id → Specific restaurant instance
  ├─ item_number → Menu item (8xxxxxx range)
  ├─ service_date → Date of service
  └─ service_time_type → LUNCH or DINNER

active_service_calendar_v2
  ├─ hdr_id → HDR/store location
  ├─ restaurant_id → Restaurant instance
  ├─ service_date → Date
  └─ service_time_type → LUNCH or DINNER
```

### Menu Item Identifiers

**Two types of identifiers exist**:

1. **`item_number`** (STRING) - Stable numeric identifier for the menu item (e.g., "8005217" for Coca-Cola)
   - All menu items are in the 8xxxxxx range (8000220 - 8011279)
   - Use this for joins and aggregations
   - Same `item_number` can appear multiple times in the table

2. **`menu_item_id`** (STRING, UUID) - Unique identifier for a specific instance
   - Each row has a unique `menu_item_id`
   - Same item can have different `menu_item_id` values across brands/categories

**Rule of thumb**: Use `item_number` for most queries, not `menu_item_id`.

### Service Date Handling

- **`service_date`** (DATE) - The date customers order items for
- Service times extend past midnight but are associated with the previous date
- This is already handled in the data - no special logic needed
- Current data covers today through 3 months in the future (e.g., Dec 2025 - Mar 2026)

### Service Time Types

- **LUNCH** - Lunch service period
- **DINNER** - Dinner service period
- Same menu item can be available for both lunch and dinner
- Query both separately or use `DISTINCT` to deduplicate if needed

### Menu Courses and Categories

**`menu_course`** (high-level grouping):
- Entrees
- Sides
- Desserts
- Appetizers
- Beverages
- Kids
- Ancillary Items (sauces, extras, add-ons)
- Combo Meal
- Large Format Meal

**`category_name`** (more specific grouping):
- Examples: Sandwiches, Salads, Burgers, Pizza, BBQ, Sauces, etc.
- Items can appear in multiple categories

### Data Volume

Current statistics (as of Dec 2025):
- **611 unique menu items** (by `item_number`)
- **94 HDRs** tracked
- **~320,000 rows per day** (due to multiple brands/categories per item)
- **3-month future window** for planning
- **No NULL values** in any field (reliable for queries)

### Legacy Table: active_menu (v1)

The `active_menu` table is the **legacy version** that will eventually be deprecated:
- Different schema (uses `store_id` instead of `hdr_id`)
- Includes `business_line` field (WONDER vs WONDER_SPOT)
- Longer historical data (back to 2021)
- **Fewer rows** for the same date (~252k vs ~318k in v2)
- **Same item coverage** (611 items)

**Recommendation**: Use `active_menu_v2` for all new queries. Only reference v1 for historical analysis pre-2025.

## Query Patterns

### Look Up HDR ID by Name

```sql
-- Find HDR ID from store name using dim_hdrs
SELECT
  hdr_id,
  hdr_name,
  current_hdr_status,
  city,
  state_code
FROM `wonder-dw-prod-brd.dw.dim_hdrs`
WHERE LOWER(hdr_name) LIKE '%upper west%';
```

**Tip**: Always use `wonder-dw-prod-brd.dw.dim_hdrs` to look up HDR IDs from store names. This is the canonical HDR dimension table.

### Look Up Restaurant Brand ID by Name

```sql
-- Find restaurant brand ID from brand name
SELECT
  restaurant_brand_id,
  restaurant_brand_name,
  restaurant_brand_nickname
FROM `wonder-dw-prod-brd.dw.dim_restaurant_brands`
WHERE LOWER(restaurant_brand_name) LIKE '%tejas%';
```

**Tip**: Use `wonder-dw-prod-brd.dw.dim_restaurant_brands` to look up restaurant brand IDs. Restaurant brands are concepts like "Tejas Barbecue" or "Burger Baby" that exist across multiple HDRs.

### Get All Menu Items for a Specific HDR, Date, and Service Time

```sql
-- Get dinner menu for a specific HDR on a specific date
SELECT
  item_number,
  item_name,
  category_name,
  menu_course,
  restaurant_brand_id
FROM `wonder-dw-prod-brd.forecast.active_menu_v2`
WHERE hdr_id = 'f8ff6993-4cf0-4779-abb9-70e82f778ad2'
  AND service_date = '2025-12-29'
  AND service_time_type = 'DINNER'
ORDER BY menu_course, item_name;
```

### Get Menu Items for a Specific Restaurant Brand at an HDR

```sql
-- Get Tejas Barbecue menu at Upper West Side
SELECT DISTINCT
  item_number,
  item_name,
  menu_course,
  category_name
FROM `wonder-dw-prod-brd.forecast.active_menu_v2`
WHERE hdr_id = '74e8d0b9-3eda-4510-8ee2-95314a833b27'  -- Upper West Side
  AND restaurant_brand_id = '356049e8-fa7f-492d-80c7-98530972c0d7'  -- Tejas Barbecue
  AND service_date = '2026-01-02'
  AND service_time_type = 'DINNER'
ORDER BY menu_course, item_name;
```

**Note**: Individual restaurant brand menus are much smaller than full HDR menus. For example, Tejas might have 9 entrees while the full HDR has 254 entrees across all brands.

### Count Unique Menu Items by HDR

```sql
-- Count unique menu items per HDR for a given date
SELECT
  hdr_id,
  COUNT(DISTINCT item_number) as unique_menu_items,
  COUNT(DISTINCT restaurant_brand_id) as num_brands
FROM `wonder-dw-prod-brd.forecast.active_menu_v2`
WHERE service_date = '2025-12-29'
  AND service_time_type = 'DINNER'
GROUP BY hdr_id
ORDER BY unique_menu_items DESC;
```

### Find Items Available Across Multiple Brands

```sql
-- Find items that appear in 5+ brands at a specific HDR
SELECT
  item_number,
  item_name,
  COUNT(DISTINCT restaurant_brand_id) as num_brands,
  STRING_AGG(DISTINCT category_name ORDER BY category_name) as categories
FROM `wonder-dw-prod-brd.forecast.active_menu_v2`
WHERE hdr_id = 'f8ff6993-4cf0-4779-abb9-70e82f778ad2'
  AND service_date = '2025-12-29'
  AND service_time_type = 'DINNER'
GROUP BY item_number, item_name
HAVING num_brands >= 5
ORDER BY num_brands DESC;
```

### Compare Lunch vs Dinner Menu Availability

```sql
-- Compare menu sizes between lunch and dinner
SELECT
  service_time_type,
  COUNT(DISTINCT item_number) as unique_items,
  COUNT(DISTINCT restaurant_brand_id) as num_brands
FROM `wonder-dw-prod-brd.forecast.active_menu_v2`
WHERE hdr_id = 'f8ff6993-4cf0-4779-abb9-70e82f778ad2'
  AND service_date = '2025-12-29'
GROUP BY service_time_type;
```

### Get Menu Items by Course

```sql
-- Get all beverages available at an HDR
SELECT DISTINCT
  item_number,
  item_name,
  category_name
FROM `wonder-dw-prod-brd.forecast.active_menu_v2`
WHERE hdr_id = 'f8ff6993-4cf0-4779-abb9-70e82f778ad2'
  AND service_date = '2025-12-29'
  AND service_time_type = 'DINNER'
  AND menu_course = 'Beverages'
ORDER BY item_name;
```

### Track Menu Changes Over Time

```sql
-- See how menu changes over next 7 days
SELECT
  service_date,
  COUNT(DISTINCT item_number) as unique_items,
  COUNT(DISTINCT restaurant_brand_id) as num_brands
FROM `wonder-dw-prod-brd.forecast.active_menu_v2`
WHERE hdr_id = 'f8ff6993-4cf0-4779-abb9-70e82f778ad2'
  AND service_date BETWEEN '2025-12-29' AND '2026-01-05'
  AND service_time_type = 'DINNER'
GROUP BY service_date
ORDER BY service_date;
```

### Find Items Available at Multiple HDRs

```sql
-- Find items available at 50+ HDRs (popular items)
SELECT
  item_number,
  item_name,
  menu_course,
  COUNT(DISTINCT hdr_id) as num_hdrs
FROM `wonder-dw-prod-brd.forecast.active_menu_v2`
WHERE service_date = '2025-12-29'
  AND service_time_type = 'DINNER'
GROUP BY item_number, item_name, menu_course
HAVING num_hdrs >= 50
ORDER BY num_hdrs DESC;
```

### Join with Service Calendar (Only Open Restaurants)

```sql
-- Get menu items only for restaurants that are actually open
SELECT DISTINCT
  am.hdr_id,
  am.item_number,
  am.item_name,
  am.menu_course
FROM `wonder-dw-prod-brd.forecast.active_menu_v2` am
INNER JOIN `wonder-dw-prod-brd.forecast.active_service_calendar_v2` cal
  ON am.hdr_id = cal.hdr_id
  AND am.service_date = cal.service_date
  AND am.service_time_type = cal.service_time_type
WHERE am.service_date = '2025-12-29'
  AND am.service_time_type = 'DINNER';
```

## Best Practices

1. **Use DISTINCT for Item Counts** - Same `item_number` appears multiple times due to multiple brands/categories. Always use `COUNT(DISTINCT item_number)` to get accurate unique item counts.

2. **Always Specify Service Date** - The table contains 3 months of data. Always filter by `service_date` to avoid slow queries and incorrect results.

3. **Use item_number, Not menu_item_id** - For joins and aggregations, use `item_number`. Only use `menu_item_id` if you need to track specific instances.

4. **Prefer active_menu_v2 Over v1** - Use `active_menu_v2` for all current and future queries. Only use `active_menu` (v1) for historical analysis.

5. **Filter by Service Time Type When Needed** - If you need lunch-only or dinner-only data, always filter by `service_time_type`. If you want both, either query both or deduplicate with DISTINCT.

6. **No NULL Handling Required** - All fields have no NULL values, so you don't need COALESCE or NULL checks.

7. **Join on Multiple Keys for Precision** - When joining with other tables, use `hdr_id + service_date + service_time_type` for accurate matching.

## Related Tables

### HDR Dimension Table

To look up HDR IDs from store names, use:
- **Table**: `wonder-dw-prod-brd.dw.dim_hdrs`
- **Key fields**: `hdr_id`, `hdr_name`, `current_hdr_status`, `city`, `state_code`
- **Usage**: Look up HDR IDs before querying menu availability

```sql
-- Find HDR by name
SELECT hdr_id, hdr_name, city
FROM `wonder-dw-prod-brd.dw.dim_hdrs`
WHERE LOWER(hdr_name) LIKE '%store name%'
  AND current_hdr_status = 'OPEN';
```

### Restaurant Brand Dimension Table

To look up restaurant brand IDs from brand names, use:
- **Table**: `wonder-dw-prod-brd.dw.dim_restaurant_brands`
- **Key fields**: `restaurant_brand_id`, `restaurant_brand_name`, `restaurant_brand_nickname`
- **Usage**: Look up brand IDs to filter menus by specific restaurant (e.g., Tejas Barbecue, Burger Baby)

```sql
-- Find restaurant brand by name
SELECT restaurant_brand_id, restaurant_brand_name
FROM `wonder-dw-prod-brd.dw.dim_restaurant_brands`
WHERE LOWER(restaurant_brand_name) LIKE '%tejas%';
```

**Restaurant Hierarchy**:
- **Restaurant Brands** - Concepts like "Tejas Barbecue", "Burger Baby" (exist across HDRs)
- **Restaurants** - Brand instance at a specific HDR (e.g., "Tejas at Upper West Side")
- **HDRs** - Physical store locations that host multiple restaurant brands

### Restaurant Dimension Table

To look up specific restaurant instances (brand + HDR combination):
- **Table**: `wonder-dw-prod-brd.dw.dim_restaurants`
- **Key fields**: `restaurant_id`, `restaurant_name`, `publish_status`
- **Usage**: Map restaurant IDs if you need restaurant-level (not brand-level) filtering

## Cross-Skill References

- **wonder-cookbook** - To get recipe/BOM details for menu items, join on `item_number` (cast to string if needed)
- **wonder-pantry** - To check if components are in stock at HDRs (use `hdr_id` for joins)
- **wonder-orders** - To join with actual sales data (use `item_number` and date fields)
- **wonder-forecasting** (future skill) - For component-level demand forecasting (different from menu availability)

## Supporting Documentation

- [schema-reference.md](schema-reference.md) - Complete table schemas with all field descriptions
- [common-pitfalls.md](common-pitfalls.md) - Common mistakes and how to avoid them
