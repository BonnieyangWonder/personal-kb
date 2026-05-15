# Item Master - Item Versions and Effective Items

The item master system stores metadata for all items in Cookbook: menu items, ingredients, packaging, and more. Understanding the difference between `item_versions` and `effective_items` is critical for efficient queries.

> **Confluence Source**: "Fields & Cards in Items", "Item Status", "Item Version Status" pages in Cookbook product documentation.

---

## Essential Filter (ALWAYS USE)

When querying `item_versions` directly, **always** include this filter to exclude deleted and dormant items:

```sql
WHERE effective = true
  AND deleted = false
  AND item_status != 'DORMANT'
```

**Why Each Condition Matters**:
- `effective = true` - Only the current active version (not historical)
- `deleted = false` - **CRITICAL**: Excludes soft-deleted items
- `item_status != 'DORMANT'` - Excludes temporarily unavailable items

> **Note**: When using `effective_items` table, you don't need `effective = true` (it's pre-filtered), but you STILL need `deleted = false` and the status check.

---

## Item Number Prefix Conventions

Item numbers follow a prefix convention that identifies the object type at a glance:

| Prefix | Object Type | Description | Examples |
|--------|-------------|-------------|----------|
| `7*` | HDR_RECIPE | HDR-specific recipes | 7000xxx |
| `80*` | MENU, RECIPE | Menu items and recipes | 8000016, 8009068 |
| `88*` | PACKAGED | Pre-packaged items from suppliers | 8800311 |
| `50*` | INGREDIENT | Raw ingredients | 5000001, 5182267 |
| `30*` | BY_PRODUCT | By-products from production | 3000xxx |
| `40*` | HDR_CONSUMABLE | Items tracked in HDR inventory | 4000053 |
| `41*` | WSKU | Wonder SKU (warehouse SKU) | 4100xxx |
| `90*` | NON_FOOD | Non-food items (packaging, supplies) | 9000xxx |

**Benchtop Item Subtypes** (used in R&D before commercialization):
- BT-Byproduct, BT-Primary, BT-Preparation

**Common Filter Pattern - Exclude Non-Food Items**:
```sql
WHERE item_number NOT LIKE '90%'
```

**Identify Object Type from Item Number**:
```sql
SELECT
  item_number,
  name,
  CASE
    WHEN item_number LIKE '7%' THEN 'HDR_RECIPE'
    WHEN item_number LIKE '80%' THEN 'MENU/RECIPE'
    WHEN item_number LIKE '88%' THEN 'PACKAGED'
    WHEN item_number LIKE '50%' THEN 'INGREDIENT'
    WHEN item_number LIKE '30%' THEN 'BY_PRODUCT'
    WHEN item_number LIKE '40%' THEN 'HDR_CONSUMABLE'
    WHEN item_number LIKE '41%' THEN 'WSKU'
    WHEN item_number LIKE '90%' THEN 'NON_FOOD'
    ELSE 'OTHER'
  END as inferred_type
FROM `secure-recipe-prod.recipe_v2.item_versions`
WHERE effective = true AND deleted = false
```

---

## Table Selection Guide

| Use Case | Table | Why |
|----------|-------|-----|
| Current item lookup | `effective_items` | Pre-filtered, most queried (48k+/month) |
| Historical analysis | `item_versions` | Contains all versions |
| Joining to BOM | `effective_items` | Better performance |
| Tracking item changes | `item_versions` | Has version history |

**Default choice**: Use `effective_items` unless you need historical versions.

## Core Tables

### effective_items (Recommended)

Pre-filtered view containing only records where `effective = true`. This is the **most queried table** in the dataset.

```sql
-- Key fields (same as item_versions, but already filtered)
item_number         STRING    -- Item ID
name                STRING    -- Human-readable name
object_type         STRING    -- MENU, INGREDIENT, PACKAGED, etc.
item_status         STRING    -- ACTIVE, DORMANT, R&D
version_status      STRING    -- DRAFT, SCHEDULED, FINAL
effective           BOOLEAN   -- Always true in this table
deleted             BOOLEAN   -- Soft-delete flag (ALWAYS check!)
menu_price          FLOAT64   -- Menu selling price
shelf_life_minutes  FLOAT64   -- General shelf life in minutes (preferred)
sold_status         STRING    -- Whether item is actively being sold
```

### item_versions (Full History)

Contains all item versions including historical records. Use when you need version history or need to analyze the `effective` flag.

```sql
-- Key fields (140+ total)
version_id          INTEGER   -- Numeric sequence (1, 2, 3...)
_id                 STRING    -- UUID identifier (joins to bom_headers.item_version_id)
item_number         STRING    -- Item ID
name                STRING    -- Human-readable name
object_type         STRING    -- MENU, INGREDIENT, PACKAGED, etc.
item_status         STRING    -- ACTIVE, DORMANT, R&D
version_status      STRING    -- DRAFT, SCHEDULED, FINAL
effective           BOOLEAN   -- Current version flag
deleted             BOOLEAN   -- Soft-delete flag
attributes          STRING    -- JSON array of tag mappings (references tags._id)
dietary_tag_info    STRING    -- Dietary classification tags (JSON)

-- Time fields
production_time     TIMESTAMP -- When version should be produced
service_time        TIMESTAMP -- When version services customers (in consumer app)
effective_start_time TIMESTAMP -- When version takes effect
effective_end_time  TIMESTAMP -- When version expires (set when dormanted)

-- Cost fields (vary by object type)
menu_price          FLOAT64   -- Menu selling price (MENU items)
total_cost          FLOAT64   -- Total item cost
food_cost           FLOAT64   -- Food component cost
non_food_cost       FLOAT64   -- Non-food component cost (packaging, etc.)
standard_cost       FLOAT64   -- Derived cost (INGREDIENT, NON_FOOD)
cost_per_bom_unit   FLOAT64   -- Cost per BOM unit (HDR_CONSUMABLE)
item_cost           FLOAT64   -- Item cost (WSKU)
net_weight_g        FLOAT64   -- Net weight in grams (PACKAGED/88* only)

-- Status indicator (PACKAGED/NON_FOOD items)
sold_status         STRING    -- Whether item is actively being sold

-- Non-food specific fields (90* items only)
accounting_type     STRING    -- Accounting classification
accounting_sub_type STRING    -- Accounting sub-classification
```

**Accounting Type Values** (NON_FOOD items only):
- Uniforms, Marketing Materials, Operating Supplies (Multi-Use/One-Time Use)
- Office Supplies, Equipment (Long-Life 3+ years), Customer-facing Disposables

**Tag-Related Fields**: The `attributes` field stores tag assignments as a JSON array. Each element contains a `tag_id` that references `wonder-recipe-prod.recipe_v2.tags._id`. See [tags-categorization.md](tags-categorization.md) for query patterns.

## ID Field Semantics

**CRITICAL**: Don't confuse these fields:

| Field | Type | Description | Join Pattern |
|-------|------|-------------|--------------|
| `item_number` | STRING | Business ID (e.g., '8009068') | Most common join key |
| `version_id` | INTEGER | Numeric sequence (1, 2, 3...) | Rarely used for joins |
| `_id` | STRING | UUID identifier | Joins to `bom_headers.item_version_id` |

## Object Types

Items have an `object_type` that classifies their purpose:

| object_type | Prefix | Description | Example |
|-------------|--------|-------------|---------|
| `MENU` | 80* | Finished menu items sold to customers | "Cheese Fries, Burger Baby" |
| `RECIPE` | 80* | Recipe components/sub-assemblies | Sub-recipes |
| `HDR_RECIPE` | 7* | HDR-specific recipes | HDR recipe variations |
| `PACKAGED` | 88* | Pre-packaged components from suppliers | "Cheesesteak Cheese Sauce [Pouch]" |
| `INGREDIENT` | 50* | Raw ingredients | "Fries, French, Fridge Friendly" |
| `BY_PRODUCT` | 30* | By-products from production | Production outputs |
| `HDR_CONSUMABLE_ITEM` | 40* | Items tracked in HDR inventory | Various consumables |
| `WSKU` | 41* | Wonder SKU (warehouse-tracked items) | Warehouse items |
| `NON_FOOD` | 90* | Packaging, utensils, labels | "8oz Clamshell" |

**Recipe Subtypes** (for Recipe-Primary, Preparation, Byproduct):
- Recipe-Primary: Main recipe output
- Preparation: Pre-prepared components
- Byproduct: Secondary outputs from recipes

**Benchtop Types** (R&D phase items):
- BT-Byproduct, BT-Primary, BT-Preparation: Items in development before commercialization

## Item Status

The `item_status` field tracks the item's lifecycle:

| Status | Description | Transition |
|--------|-------------|------------|
| `R&D` | In development/testing | Default when item first created |
| `ACTIVE` | Currently available for use | Auto-change from R&D when version goes live |
| `DORMANT` | Temporarily unavailable | Manually set; requires usage validation |

**Status Transitions**:
- **R&D -> ACTIVE**: Automatic when a version's effective start time is reached
- **ACTIVE/R&D -> DORMANT**: Manual only; item must not be in use in active BOMs, components, or customizations
- **DORMANT -> R&D**: Manual via "Undormant" action; creates new draft version if needed

**Important**: Dormant items cannot be added to new BOMs or components. Dormanting an item soft-deletes all SKU mappings.

## Version Status

The `version_status` field tracks an individual version's publication state:

| Status | Description | Effective Time |
|--------|-------------|----------------|
| `DRAFT` | Default when version created | No effective start time |
| `SCHEDULED` | Published with future date | Effective start time > now |
| `FINAL` | Currently active/published | Effective start time elapsed |

**Status Transitions**:
- **DRAFT -> SCHEDULED**: When published with future effective start time
- **DRAFT -> FINAL**: When published immediately
- **SCHEDULED -> FINAL**: Auto-transition when effective start time elapses
- **SCHEDULED -> DRAFT**: When item is dormanted (reverts scheduled versions)

## ERP Integration Status

For items with ERP integration (primarily PACKAGED and NON_FOOD), there is a separate ERP status:

| ERP Status | Description |
|------------|-------------|
| `NEW` | Item exists in Cookbook but no ERP item info created |
| `ITEM_CREATED` | ERP item info created, but BOM not yet created in ERP |
| `BOM_CREATED` | Full ERP integration with BOM |

> **Note**: This is distinct from `item_status` - an item can be ACTIVE in Cookbook but still NEW in ERP.

## Query Patterns

### Quick Item Lookup (Recommended)

```sql
-- Fast lookup using effective_items (no need to filter by effective)
SELECT
  item_number,
  name,
  object_type,
  item_status,
  menu_price,
  shelf_life_minutes
FROM `secure-recipe-prod.recipe_v2.effective_items`
WHERE object_type = 'MENU'
  AND deleted = false  -- CRITICAL: Always include
  AND item_status = 'ACTIVE'
ORDER BY name;
```

### Find Item by Name Pattern

```sql
SELECT
  item_number,
  name,
  object_type,
  item_status
FROM `secure-recipe-prod.recipe_v2.effective_items`
WHERE LOWER(name) LIKE '%cheese%fries%'
  AND deleted = false
  AND item_status = 'ACTIVE';
```

### Get All Active Menu Items

```sql
SELECT
  item_number,
  name,
  menu_price
FROM `secure-recipe-prod.recipe_v2.effective_items`
WHERE object_type = 'MENU'
  AND deleted = false
  AND item_status = 'ACTIVE'
ORDER BY name;
```

### Compare effective_items vs item_versions

```sql
-- Using effective_items (recommended)
SELECT item_number, name
FROM `secure-recipe-prod.recipe_v2.effective_items`
WHERE item_number = '8009068'
  AND deleted = false;

-- Equivalent using item_versions (slower)
SELECT item_number, name
FROM `secure-recipe-prod.recipe_v2.item_versions`
WHERE item_number = '8009068'
  AND effective = true
  AND deleted = false;
```

### Join to BOM Headers (Menu Item Name Lookup)

```sql
SELECT
  bh.item_number,
  ei.name as menu_item_name,
  ei.object_type,
  ei.item_status
FROM `secure-recipe-prod.recipe_v2.bom_headers` bh
LEFT JOIN `secure-recipe-prod.recipe_v2.effective_items` ei
  ON bh.item_number = CAST(ei.item_number AS STRING)
WHERE bh.is_active = true;
```

### Join to BOM Lines (Component Name Lookup)

```sql
SELECT
  bl.bom_line_item_number as component_id,
  ei.name as component_name,
  ei.object_type
FROM `secure-recipe-prod.recipe_v2.bom_lines` bl
LEFT JOIN `secure-recipe-prod.recipe_v2.effective_items` ei
  ON CAST(bl.bom_line_item_number AS STRING) = CAST(ei.item_number AS STRING)
WHERE bl.bom_header_item_number = '8009068';
```

### UUID Join Pattern (Direct Version Reference)

```sql
-- When you have item_version_id (UUID) and need to join to item_versions
SELECT bh.*, iv.name
FROM `secure-recipe-prod.recipe_v2.bom_headers` bh
JOIN `secure-recipe-prod.recipe_v2.item_versions` iv
  ON bh.item_version_id = iv._id;
```

## Critical Rules

1. **Always include `deleted = false`** in ALL queries - even when using `effective_items`
2. **Prefer `effective_items` over `item_versions`** for current item lookups
3. **Use LEFT JOIN** when joining to item metadata - not all components have metadata
4. **Cast item_number to STRING** when joining across tables
5. **Handle NULL names** with COALESCE when components lack metadata
6. **Filter by object_type and item_status** when looking for active menu items
7. **Use item_number prefix** to quickly identify object type (80*=menu, 50*=ingredient, etc.)

## Common Anti-Patterns

```sql
-- ❌ Wrong: Missing deleted = false filter (returns deleted items!)
SELECT * FROM `secure-recipe-prod.recipe_v2.effective_items`
WHERE object_type = 'MENU';

-- ✅ Correct: Always include deleted = false
SELECT * FROM `secure-recipe-prod.recipe_v2.effective_items`
WHERE object_type = 'MENU'
  AND deleted = false;

-- ❌ Wrong: Missing full essential filter on item_versions
SELECT * FROM `secure-recipe-prod.recipe_v2.item_versions`
WHERE effective = true AND object_type = 'MENU';

-- ✅ Correct: Full essential filter
SELECT * FROM `secure-recipe-prod.recipe_v2.item_versions`
WHERE effective = true
  AND deleted = false
  AND item_status != 'DORMANT'
  AND object_type = 'MENU';

-- ❌ Wrong: Confusing version_id (INTEGER) with _id (STRING UUID)
WHERE version_id = '5570ab64-2933-4157-90e9-4e85addd6532'

-- ✅ Correct: Use _id for UUID lookups
WHERE _id = '5570ab64-2933-4157-90e9-4e85addd6532'
```

---

## Deprecation Notes

The following fields are deprecated and should be avoided in new queries:

> **Deprecated**: The `shelf_life_period` field is deprecated. Use `shelf_life_minutes` instead. The system uses a dual-write pattern during migration, so both fields may contain data.

> **Deprecated**: The `restaurant_ids` field is deprecated (since sprint 26). Restaurant assignments are now managed through a different mechanism.

> **Deprecated**: The `food_science_range_info` field is deprecated (since MD-12979). Use `food_science_v2` nested structure instead for food science data.

> **Deprecated**: The `effective_start_time` and `effective_end_time` fields do not exist in the current schema. Use `service_start_time` and `service_end_time` for service window filtering.

### Shelf Life Field Migration

All shelf life fields have migrated from days/hours to minutes:

| Deprecated Field | Replacement Field | Conversion |
|------------------|-------------------|------------|
| `shelf_life_period` (days) | `shelf_life_minutes` | days * 1440 |
| `thawed_shelf_life_days` | `thawed_shelf_life_minutes` | days * 1440 |
| `frozen_shelf_life_days` | `frozen_shelf_life_minutes` | days * 1440 |
| `cooked_shelf_life_days` | `cooked_shelf_life_minutes` | days * 1440 |
| `reduced_shelf_life` (days) | `reduced_shelf_life_minutes` | days * 1440 |
| `slacking_time_hours` | `slacking_time_minutes` | hours * 60 |

**Note**: The system currently dual-writes to both deprecated and new fields for backward compatibility.

---

## Related Documentation

- [bom-components.md](bom-components.md) - BOM headers and lines
- [service-windows.md](service-windows.md) - Recipe versioning
- [tags-categorization.md](tags-categorization.md) - Tags, tag groups, and item categorization
- [../domains/food-science.md](../domains/food-science.md) - Shelf life fields

---

## Code References (Java Codebase)

> **Codebase**: `master-data-management-2`
> **Validated**: 2026-01-28

### Domain Models

- **Item**: `backend/domain-library/src/main/java/app/internalrecipe/item/Item.java`
  - MongoDB Collection: `items`
  - Primary key: `id` (UUID), business key: `itemNumber`
  - Key fields: `objectType`, `objectSubType`, `status`, `deleted`
  - @Deprecated: `migrateFromItemVersionId`
  - Inner classes: `Enable40ModelMigrateFromItem`, `ConsumableItem`

- **ItemVersion**: `backend/domain-library/src/main/java/app/internalrecipe/item/ItemVersion.java`
  - MongoDB Collection: `item_versions`
  - Primary key: `id` (UUID), version tracking via `versionId` (Integer)
  - Maps to BigQuery: `secure-recipe-prod.recipe_v2.item_versions`
  - **@Deprecated fields (11 total)**:
    - `shelf_life_period` → use `shelf_life_minutes`
    - `thawed_shelf_life_days` → use `thawed_shelf_life_minutes`
    - `reduced_shelf_life_days` → use `reduced_shelf_life_minutes`
    - `frozen_shelf_life_days` → use `frozen_shelf_life_minutes`
    - `slacking_time_hours` → use `slacking_time_minutes`
    - `cooked_shelf_life_days` → use `cooked_shelf_life_minutes`
    - `item_customization_presets` → use `preset_item_version_info`
    - `at_scale_transfer_cost` → transfer cost refactored
    - `current_state_transfer_cost` → transfer cost refactored
    - `item_cost` → use `item_cost_v2`
    - `food_science_range_info` (since MD-12979) → use `food_science_v2`
    - `restaurant_ids` (since 2025 sprint 26) → assignment mechanism changed

- **ItemVersionVariant**: `backend/domain-library/src/main/java/app/internalrecipe/item/ItemVersionVariant.java`
  - MongoDB Collection: `item_version_variants`
  - Same @Deprecated fields as ItemVersion (10 fields, missing thawed_shelf_life_days deprecated annotation)
  - Used for item variations

### Service Layer

- **BOItemVersionService**: `backend/internal-recipe-service/src/main/java/app/internalrecipe/item/service/BOItemVersionService.java`
  - `searchCurrentAndFutureItemVersions(effectiveStartTime, itemNumbers)`: Find versions active from a given time
  - `searchTargetItemVersionsByDraft(itemNumbers, additionalFilters)`: Find versions with priority on active status
  - Uses filters: `deleted = false`, `service_end_time > now()`

- **BOItemVersionService (v2)**: `backend/recipe-service-v2/src/main/java/app/recipev2/item/service/BOItemVersionService.java`
  - Recipe service v2 item version operations

- **QueryItemService**: `backend/recipe-service-v2/src/main/java/app/recipev2/item/service/QueryItemService.java`
  - Query operations for items

- **BOSearchItemService**: `backend/recipe-service-v2/src/main/java/app/recipev2/item/service/BOSearchItemService.java`
  - Search functionality for items

### API Endpoints (Internal Recipe Service)

- **BOItemRecipeWebService**: `backend/internal-recipe-service-interface/src/main/java/app/internalrecipe/api/BOItemRecipeWebService.java`
  - Item recipe CRUD operations

- **BOItemVersionBulkEditWebService**: `backend/internal-recipe-service-interface/src/main/java/app/internalrecipe/api/BOItemVersionBulkEditWebService.java`
  - Bulk edit operations for item versions

- **BODeleteItemWebService**: `backend/internal-recipe-service-interface/src/main/java/app/internalrecipe/api/BODeleteItemWebService.java`
  - Soft delete operations for items

- **BOItemCommercializeWebService**: `backend/internal-recipe-service-interface/src/main/java/app/internalrecipe/api/BOItemCommercializeWebService.java`
  - Commercialization workflow (R&D → ACTIVE)

### MongoDB Operations

- **ItemVersionCollectionManager**: `backend/internal-recipe-service/src/main/java/collectionmanager/ItemVersionCollectionManager.java`
  - Collection: `item_versions`
  - Key filters: `deleted = false`, `effective = true`, `item_status != 'DORMANT'`
  - Sort: `service_start_time` ascending for versioning queries

### Item Number Prefix Logic

Item number prefixes are enforced at the domain level, not via a generator class. The prefix convention is:
- `7*` = HDR_RECIPE
- `80*` = MENU/RECIPE
- `88*` = PACKAGED
- `50*` = INGREDIENT
- `30*` = BY_PRODUCT
- `40*` = HDR_CONSUMABLE
- `41*` = WSKU
- `90*` = NON_FOOD

### Business Logic Patterns

- **Effective Version**: `effective = true` marks the current active version
- **Soft Delete**: `deleted = true` marks deleted items (ALWAYS filter out)
- **Item Status Flow**: R&D → ACTIVE → DORMANT (manual transition)
- **Version Status Flow**: DRAFT → SCHEDULED → FINAL (automatic on service time)
- **Service Window**: `serviceStartTime` and `serviceEndTime` define version validity

### @Deprecated Field Summary

| Field | Replacement | Ticket/Sprint |
|-------|-------------|---------------|
| `shelf_life_period` | `shelf_life_minutes` | - |
| `thawed_shelf_life_days` | `thawed_shelf_life_minutes` | - |
| `reduced_shelf_life_days` | `reduced_shelf_life_minutes` | - |
| `frozen_shelf_life_days` | `frozen_shelf_life_minutes` | - |
| `slacking_time_hours` | `slacking_time_minutes` | - |
| `cooked_shelf_life_days` | `cooked_shelf_life_minutes` | - |
| `item_customization_presets` | `preset_item_version_info` | - |
| `at_scale_transfer_cost` | Transfer cost refactored | - |
| `current_state_transfer_cost` | Transfer cost refactored | - |
| `item_cost` | `item_cost_v2` | - |
| `food_science_range_info` | `food_science_v2` | MD-12979 |
| `restaurant_ids` | New assignment mechanism | 2025 sprint 26 |
| `migrateFromItemVersionId` (Item) | - | - |
