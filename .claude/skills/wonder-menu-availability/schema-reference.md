# Wonder Menu Availability - Schema Reference

## Overview

The Wonder menu availability system tracks customer-facing menu items available at each HDR (restaurant) on specific dates and service times. This data resides in BigQuery's data warehouse and is used by ordering systems, menu displays, and planning tools.

## Database Connection

- **BigQuery Project**: `wonder-dw-prod-brd`
- **Dataset**: `forecast`
- **Primary Table**: `active_menu_v2`
- **Legacy Table**: `active_menu`
- **Related Table**: `active_service_calendar_v2`
- **Access**: Via bq CLI (`bq query`) or BigQuery Console

---

## Core Tables

### active_menu_v2

**Purpose**: Primary table for customer-facing menu availability. Shows which menu items are available at each HDR on specific dates and service times.

**Table Name**: `wonder-dw-prod-brd.forecast.active_menu_v2`

**Schema**:
```sql
menu_item_id         STRING   -- UUID for specific menu item instance (unique per row)
menu_version_id      STRING   -- UUID for menu version/schedule
hdr_id               STRING   -- HDR/store UUID
restaurant_brand_id  STRING   -- Brand UUID (e.g., Burger Baby, Tejas BBQ)
restaurant_id        STRING   -- Restaurant UUID (brand + location combo)
service_date         DATE     -- Date when item is available
service_time_type    STRING   -- LUNCH or DINNER
item_number          STRING   -- Stable item identifier (8xxxxxx range)
item_name            STRING   -- Display name of menu item
category_name        STRING   -- Category (Sandwiches, Salads, etc.)
menu_course          STRING   -- Course (Entrees, Sides, Desserts, etc.)
```

**Key Characteristics**:
- **Row Count**: ~320,000 rows per day (same item appears multiple times)
- **Date Coverage**: Current date + 3 months future
- **Item Range**: 611 unique items (item_number 8000220 - 8011279)
- **HDR Coverage**: 94 unique HDRs
- **No NULL Values**: All fields are populated
- **Last Modified**: Updated daily at ~7:30 AM UTC

**Primary Keys/Indexes**:
- No formal primary key (data warehouse table)
- Unique row identifier: `menu_item_id`
- Natural key for items: `(hdr_id, service_date, service_time_type, item_number, restaurant_brand_id)`

**Field Details**:

#### menu_item_id
- **Type**: STRING (UUID format)
- **Purpose**: Unique identifier for this specific menu item instance
- **Uniqueness**: Each row has a unique value
- **Usage**: Rarely needed - use `item_number` instead for most queries
- **Example**: `e3af6be3-36da-43eb-8f5c-26c85a3d835e`

#### menu_version_id
- **Type**: STRING (UUID format)
- **Purpose**: Identifies the menu version/schedule
- **Characteristics**: Each HDR typically has one menu_version_id per week
- **Usage**: Track menu changes over time, group by menu version
- **Example**: `cd2b94e1-ffd6-4d4d-b0b5-ec73bce985c7`

#### hdr_id
- **Type**: STRING (UUID format)
- **Purpose**: Identifies the HDR/store location
- **Join Key**: Use this to join with wonder-pantry, wonder-orders, active_service_calendar_v2
- **Uniqueness**: 94 unique HDRs in current data
- **Example**: `f8ff6993-4cf0-4779-abb9-70e82f778ad2`

#### restaurant_brand_id
- **Type**: STRING (UUID format)
- **Purpose**: Identifies the restaurant brand (e.g., Burger Baby, Tejas BBQ, Di Fara Pizza)
- **Characteristics**: Same HDR can have multiple brands (multi-brand locations)
- **Uniqueness**: 29 unique brands in current data
- **Example**: `356049e8-fa7f-492d-80c7-98530972c0d7` (Tejas BBQ)

#### restaurant_id
- **Type**: STRING (UUID format)
- **Purpose**: Identifies specific restaurant instance (brand + location combination)
- **Relationship**: Each `restaurant_id` maps to one `restaurant_brand_id` and one `hdr_id`
- **Usage**: Join key for restaurant-specific data
- **Example**: `01b20dfa-8240-4f87-8cd5-f4017c598782`

#### service_date
- **Type**: DATE
- **Purpose**: Date when the menu item is available for ordering
- **Range**: Current date through ~3 months in future
- **Format**: YYYY-MM-DD (e.g., `2025-12-29`)
- **Edge Case**: Service extending past midnight is associated with the previous date (already handled in data)

#### service_time_type
- **Type**: STRING
- **Values**: `LUNCH` or `DINNER`
- **Purpose**: Distinguishes lunch vs dinner service periods
- **Characteristics**: Same item can appear for both lunch and dinner

#### item_number
- **Type**: STRING
- **Purpose**: Stable identifier for menu items (use this for joins and aggregations)
- **Range**: All menu items are 8xxxxxx (8000220 - 8011279)
- **Uniqueness**: 611 unique values across all menus
- **Duplicates**: Same `item_number` appears many times (across brands/categories)
- **Join Target**: Join to wonder-cookbook's `item_versions.item_number` (cast to string)
- **Example**: `8005217` (Coca-Cola)

#### item_name
- **Type**: STRING
- **Purpose**: Human-readable display name
- **Characteristics**: Same `item_number` always has same `item_name`
- **Examples**:
  - `Coca-Cola`
  - `Smoked Turkey BLT`
  - `Thai Vegetable Salad`
  - `Classic Brisket Sandwich on Gluten-Free Bun`

#### category_name
- **Type**: STRING
- **Purpose**: Specific category/grouping for menu items
- **Characteristics**:
  - More specific than `menu_course`
  - Same item can appear in multiple categories
  - Not hierarchically related to `menu_course` (they overlap)
- **Common Values**:
  - Sandwiches, Salads, Burgers, Pizza, BBQ
  - Sauces, Extras, Combos, Kids Combos
  - Appetizers, Sides, Beverages
- **Example**: Item "Small Ranch" might appear in both "Extras" and "Combos" categories

#### menu_course
- **Type**: STRING
- **Purpose**: High-level course classification
- **Values**:
  - `Entrees` - Main dishes
  - `Sides` - Side dishes
  - `Desserts` - Desserts and sweets
  - `Appetizers` - Starters and appetizers
  - `Beverages` - Drinks (most common: 26-27 per brand)
  - `Kids` - Kids menu items
  - `Ancillary Items` - Sauces, extras, add-ons
  - `Combo Meal` - Combo meals
  - `Large Format Meal` - Family-sized meals
- **Characteristics**: Same item can appear in multiple courses

---

### active_menu (v1 - Legacy)

**Purpose**: Legacy menu availability table. Will be deprecated in favor of `active_menu_v2`.

**Table Name**: `wonder-dw-prod-brd.forecast.active_menu`

**Schema**:
```sql
service_date         DATE     -- Date when item is available
service_time_type    STRING   -- LUNCH or DINNER
store_id             STRING   -- Store/HDR UUID (equivalent to hdr_id in v2)
business_line        STRING   -- WONDER or WONDER_SPOT
restaurant_brand_id  STRING   -- Brand UUID
restaurant_id        STRING   -- Restaurant UUID
item_number          STRING   -- Item identifier (8xxxxxx range)
menu_course          STRING   -- Course classification
```

**Key Differences from v2**:
- Uses `store_id` instead of `hdr_id` (same values, different name)
- Includes `business_line` field (WONDER vs WONDER_SPOT)
- Missing fields: `menu_item_id`, `menu_version_id`, `item_name`, `category_name`
- Fewer rows for same date (~252k vs ~318k in v2)
- Longer historical data (back to 2021)
- **Same item coverage**: 611 unique items

**Migration Path**:
- Use `active_menu_v2` for all new queries
- Only use `active_menu` for historical analysis (pre-2025)
- When migrating queries, replace `store_id` with `hdr_id`

**Data Volume**:
- **Total Rows**: 70.3 million (historical + future)
- **Date Range**: October 2021 - February 2026
- **Current Date Rows**: ~252k per day

---

### active_service_calendar_v2

**Purpose**: Defines which HDRs and restaurants are open on specific dates and service times. Use this to filter `active_menu_v2` to only open locations.

**Table Name**: `wonder-dw-prod-brd.forecast.active_service_calendar_v2`

**Schema**:
```sql
hdr_id               STRING   -- HDR/store UUID
restaurant_id        STRING   -- Restaurant UUID
service_date         DATE     -- Date
service_time_type    STRING   -- LUNCH or DINNER
```

**Key Characteristics**:
- Simple mapping table with no duplicates
- Each row represents one restaurant open for one service time on one date
- Join to `active_menu_v2` on `(hdr_id, service_date, service_time_type)` to filter to open restaurants only

**Common Join Pattern**:
```sql
-- Get menu items only for restaurants that are actually open
SELECT am.*
FROM `wonder-dw-prod-brd.forecast.active_menu_v2` am
INNER JOIN `wonder-dw-prod-brd.forecast.active_service_calendar_v2` cal
  ON am.hdr_id = cal.hdr_id
  AND am.service_date = cal.service_date
  AND am.service_time_type = cal.service_time_type
WHERE am.service_date = '2025-12-29';
```

---

## Related Dimension Tables

### dim_hdrs (HDR Dimension Table)

**Purpose**: Master dimension table for all HDR/store locations. Use this to look up HDR IDs from store names.

**Table Name**: `wonder-dw-prod-brd.dw.dim_hdrs`

**Key Fields**:
```sql
hdr_id                    STRING   -- HDR UUID (use this to join with active_menu_v2)
hdr_code                  STRING   -- Short code for HDR
hdr_name                  STRING   -- Display name (e.g., "Upper West Side")
current_hdr_status        STRING   -- OPEN, INACTIVE, DRAFT
hdr_opening_date          DATE     -- When HDR opened
city                      STRING   -- City name
state_code                STRING   -- Two-letter state code (e.g., "NY")
zip_code                  STRING   -- Zip code
full_address              STRING   -- Complete address
latitude                  FLOAT    -- Latitude coordinate
longitude                 FLOAT    -- Longitude coordinate
timezone_id               STRING   -- Timezone identifier
categorization            STRING   -- HDR categorization
design_type               STRING   -- Design type
location_type_category    STRING   -- Location type
```

**Common Usage Pattern**:
```sql
-- Look up HDR ID from store name
SELECT
  hdr_id,
  hdr_name,
  current_hdr_status,
  city,
  state_code
FROM `wonder-dw-prod-brd.dw.dim_hdrs`
WHERE LOWER(hdr_name) LIKE '%store name%'
  AND current_hdr_status = 'OPEN';
```

**Why Use This**: This is the canonical source for HDR information. Always use `dim_hdrs` to look up HDR IDs before querying menu availability, rather than searching through other tables like `command_center.nodes`.

---

### dim_restaurant_brands (Restaurant Brand Dimension Table)

**Purpose**: Master dimension table for restaurant brands (e.g., Tejas Barbecue, Burger Baby). Use this to look up restaurant brand IDs from brand names.

**Table Name**: `wonder-dw-prod-brd.dw.dim_restaurant_brands`

**Key Fields**:
```sql
restaurant_brand_id          STRING   -- Brand UUID (use to filter active_menu_v2)
restaurant_brand_name        STRING   -- Display name (e.g., "Tejas Barbecue")
restaurant_brand_nickname    STRING   -- Short name/nickname
short_description            STRING   -- Brief description
long_description             STRING   -- Detailed description
large_hero_image             STRING   -- Hero image URL
web_hero_image               STRING   -- Web hero image URL
```

**Common Usage Pattern**:
```sql
-- Look up restaurant brand ID from brand name
SELECT
  restaurant_brand_id,
  restaurant_brand_name,
  restaurant_brand_nickname
FROM `wonder-dw-prod-brd.dw.dim_restaurant_brands`
WHERE LOWER(restaurant_brand_name) LIKE '%tejas%';
```

**Restaurant Hierarchy**:
- **Restaurant Brands** (this table) - Brand concepts that exist across multiple HDRs (e.g., "Tejas Barbecue")
- **Restaurants** (see dim_restaurants) - Specific brand instance at an HDR (e.g., "Tejas at Upper West Side")
- **HDRs** (see dim_hdrs) - Physical store locations

---

### dim_restaurants (Restaurant Dimension Table)

**Purpose**: Maps specific restaurant instances (brand + HDR combinations). Use when you need restaurant-level (not brand-level) information.

**Table Name**: `wonder-dw-prod-brd.dw.dim_restaurants`

**Key Fields**:
```sql
restaurant_id                STRING      -- Restaurant UUID (maps to active_menu_v2.restaurant_id)
restaurant_name              STRING      -- Restaurant instance name
publish_status               STRING      -- Publication status
is_deleted                   BOOLEAN     -- Deletion flag
created_timestamp_utc        DATETIME    -- Creation timestamp
updated_timestamp_utc        DATETIME    -- Last update timestamp
```

**Relationship to active_menu_v2**:
- `active_menu_v2.restaurant_id` → `dim_restaurants.restaurant_id`
- `active_menu_v2.restaurant_brand_id` → `dim_restaurant_brands.restaurant_brand_id`

**When to Use**:
- Most queries should filter by `restaurant_brand_id` (brand-level filtering)
- Use `restaurant_id` only when you need to distinguish between different instances of the same brand at the same HDR (rare)

---

## Data Relationships

### Joins to Other Systems

#### To Wonder Cookbook (Recipes/BOMs)
```sql
-- Get recipe/BOM details for menu items
SELECT
  am.item_number,
  am.item_name,
  iv.object_type,
  iv.name as cookbook_name
FROM `wonder-dw-prod-brd.forecast.active_menu_v2` am
LEFT JOIN `secure-recipe-prod.recipe_v2.item_versions` iv
  ON CAST(iv.item_number AS STRING) = am.item_number
WHERE am.service_date = '2025-12-29';
```

#### To Wonder Orders (Sales Data)
```sql
-- Compare menu availability to actual sales
SELECT
  am.item_number,
  am.item_name,
  COUNT(DISTINCT o.order_id) as num_orders
FROM `wonder-dw-prod-brd.forecast.active_menu_v2` am
LEFT JOIN `wonder-dw-prod-brd.orders.hdr_orders` o
  ON am.hdr_id = o.hdr_id
  AND am.item_number = o.item_number
  AND am.service_date = DATE(o.order_placed_at, 'America/New_York')
WHERE am.service_date = '2025-12-29'
GROUP BY am.item_number, am.item_name;
```

#### To Wonder Pantry (Inventory)
```sql
-- Check which menu items have low inventory
SELECT
  am.item_number,
  am.item_name,
  p.on_hand_quantity
FROM `wonder-dw-prod-brd.forecast.active_menu_v2` am
LEFT JOIN `wonder-raw-prod.pg_batch_pantry.inventory_snapshots` p
  ON am.hdr_id = p.hdr_id
  AND am.item_number = p.item_number
WHERE am.service_date = CURRENT_DATE('America/New_York')
  AND p.on_hand_quantity < 10;
```

### Multi-Table Query Example

```sql
-- Complete menu analysis: availability + recipes + inventory
WITH active_items AS (
  SELECT DISTINCT
    hdr_id,
    item_number,
    item_name,
    menu_course
  FROM `wonder-dw-prod-brd.forecast.active_menu_v2`
  WHERE service_date = CURRENT_DATE('America/New_York')
    AND service_time_type = 'DINNER'
)
SELECT
  ai.item_number,
  ai.item_name,
  ai.menu_course,
  iv.object_type as cookbook_type,
  COUNT(DISTINCT bl.bom_line_item_number) as num_components,
  p.on_hand_quantity as inventory_level
FROM active_items ai
LEFT JOIN `secure-recipe-prod.recipe_v2.item_versions` iv
  ON CAST(iv.item_number AS STRING) = ai.item_number
LEFT JOIN `secure-recipe-prod.recipe_v2.bom_lines` bl
  ON CAST(bl.bom_header_item_number AS STRING) = ai.item_number
  AND CURRENT_TIMESTAMP() BETWEEN TIMESTAMP(bl.service_start_time)
                               AND TIMESTAMP(bl.service_end_time)
LEFT JOIN `wonder-raw-prod.pg_batch_pantry.inventory_snapshots` p
  ON ai.hdr_id = p.hdr_id
  AND ai.item_number = p.item_number
GROUP BY ai.item_number, ai.item_name, ai.menu_course, iv.object_type, p.on_hand_quantity
ORDER BY ai.menu_course, ai.item_name;
```

### Restaurant Brand Filtering Example

```sql
-- Get menu for specific restaurant brand with dimension table joins
SELECT
  h.hdr_name,
  rb.restaurant_brand_name,
  am.item_name,
  am.menu_course
FROM `wonder-dw-prod-brd.forecast.active_menu_v2` am
INNER JOIN `wonder-dw-prod-brd.dw.dim_hdrs` h
  ON am.hdr_id = h.hdr_id
INNER JOIN `wonder-dw-prod-brd.dw.dim_restaurant_brands` rb
  ON am.restaurant_brand_id = rb.restaurant_brand_id
WHERE h.hdr_name = 'Upper West Side'
  AND rb.restaurant_brand_name = 'Tejas Barbecue'
  AND am.service_date = '2026-01-02'
  AND am.service_time_type = 'DINNER'
ORDER BY am.menu_course, am.item_name;
```

**Result**: Readable query using store names and brand names instead of UUIDs.

---

## Table Statistics

### active_menu_v2 (Current)

**Volume by Date**:
```sql
SELECT
  service_date,
  COUNT(*) as total_rows,
  COUNT(DISTINCT item_number) as unique_items,
  COUNT(DISTINCT hdr_id) as num_hdrs,
  COUNT(DISTINCT restaurant_brand_id) as num_brands
FROM `wonder-dw-prod-brd.forecast.active_menu_v2`
GROUP BY service_date
ORDER BY service_date DESC
LIMIT 10;
```

**Typical Results** (Dec 2025):
- **Total rows per day**: ~318,000
- **Unique items**: 611
- **HDRs**: 94
- **Brands**: 29

**Item Distribution by Course**:
- Beverages: Most common (26-27 per brand, appears across almost all brands)
- Desserts: 13-14 per brand (standardized across brands)
- Entrees: Varies widely (4-23 per brand, brand-specific)
- Sides: Moderate variation
- Ancillary Items: 1-6 per brand

---

## Verification Queries

### Check Table Freshness
```sql
-- When was the table last updated?
SELECT
  MAX(service_date) as latest_date,
  COUNT(DISTINCT service_date) as num_dates_available
FROM `wonder-dw-prod-brd.forecast.active_menu_v2`;
```

### Validate Data Quality
```sql
-- Check for any NULL values (should be zero)
SELECT
  COUNTIF(menu_item_id IS NULL) as null_menu_item_id,
  COUNTIF(hdr_id IS NULL) as null_hdr_id,
  COUNTIF(item_number IS NULL) as null_item_number,
  COUNTIF(item_name IS NULL) as null_item_name,
  COUNTIF(service_date IS NULL) as null_service_date
FROM `wonder-dw-prod-brd.forecast.active_menu_v2`
WHERE service_date = CURRENT_DATE('America/New_York');
```

### Compare v1 vs v2 Coverage
```sql
-- Ensure v2 has at least as much data as v1
SELECT
  'v1 (legacy)' as version,
  COUNT(*) as total_rows,
  COUNT(DISTINCT store_id) as num_hdrs
FROM `wonder-dw-prod-brd.forecast.active_menu`
WHERE service_date = CURRENT_DATE('America/New_York')

UNION ALL

SELECT
  'v2 (current)' as version,
  COUNT(*) as total_rows,
  COUNT(DISTINCT hdr_id) as num_hdrs
FROM `wonder-dw-prod-brd.forecast.active_menu_v2`
WHERE service_date = CURRENT_DATE('America/New_York');
```

---

## Performance Tips

1. **Always filter by service_date** - Table contains 3 months of data; filtering by date is critical for performance

2. **Use DISTINCT for item counts** - Same item appears many times; always use `COUNT(DISTINCT item_number)`

3. **Index-friendly queries** - Filter on `service_date`, `hdr_id`, and `service_time_type` first before other conditions

4. **Avoid SELECT *** - Table has 11 columns with UUIDs; only select needed columns

5. **Limit joins to specific dates** - When joining with other tables, always include date filters on both sides
