# Cookbook Recipe System - Schema Reference

## Overview

Cookbook is Wonder's recipe management system. Data spans **4 BigQuery datasets** with **70+ tables**.

| Dataset | Purpose |
|---------|---------|
| `secure-recipe-prod.recipe_v2` | Primary - Sensitive item/recipe data (13 tables) |
| `wonder-recipe-prod.recipe_v2` | Non-sensitive item data (21 tables) |
| `wonder-recipe-prod.mongo_batch_recipe_v2` | Mappings & reference data (40+ tables) |
| `wonder-raw-prod.mysql_batch_product_catalog` | Product catalog & SKU mappings (8 tables) |

See [reference/datasets-overview.md](reference/datasets-overview.md) for complete table listings.

---

## Essential Filter (ALWAYS USE)

When querying item data, **always** include:

```sql
WHERE effective = true
  AND deleted = false
  AND item_status != 'DORMANT'
```

**Why Each Condition Matters**:
- `effective = true` - Only current active version
- `deleted = false` - **CRITICAL**: Excludes soft-deleted items
- `item_status != 'DORMANT'` - Excludes temporarily unavailable items

---

## Core Tables

### bom_headers

Top-level records for each menu item's Bill of Materials.

```sql
item_number              STRING    -- Menu item ID (e.g., '8009068')
item_version_id          STRING    -- Version UUID for the menu item
id                       STRING    -- BOM header unique ID
name                     STRING    -- BOM name
is_active                BOOLEAN   -- Whether this BOM is currently active
object_type              STRING    -- Item object type
object_sub_type          STRING    -- Item sub-type
service_start_time       DATETIME  -- Service window start (BOM versioning)
service_end_time         DATETIME  -- Service window end (BOM versioning)
formula_batch_size       STRING    -- Batch size for formula
reason_for_change        STRING    -- Change reason
bom_lines                STRING    -- Embedded BOM lines (JSON)
created_by               STRING    -- Creator name
created_time             DATETIME  -- Creation timestamp
updated_by               STRING    -- Last updater name
updated_time             DATETIME  -- Last update timestamp
```

**Join Pattern**: `bom_headers.item_number = bom_lines.bom_header_item_number`

---

### bom_lines

Individual component lines within a BOM.

```sql
bom_header_item_number      STRING    -- FK to bom_headers.item_number
bom_header_item_version_id  STRING    -- Version UUID of the parent BOM
bom_header_id               STRING    -- Alternative BOM header reference
bom_line_item_number        STRING    -- Component item ID
bom_line_item_version_id    STRING    -- Version UUID for component
service_start_time          TIMESTAMP -- When this component became active
service_end_time            TIMESTAMP -- When this component stopped being used
manage_inventory            BOOLEAN   -- CRITICAL: true=REQUIRED, false=OPTIONAL
quantity                    FLOAT64   -- Amount needed per menu item
unit                        STRING    -- Unit of measure (ea, g, oz, lb)
cost                        FLOAT64   -- Component cost
scrap_yield                 FLOAT64   -- Yield/waste factor
lead_time_day               INT64     -- Lead time for procurement
updated_time                TIMESTAMP -- Last update
```

**Critical Field**: `manage_inventory` - determines availability impact

---

### effective_items

Pre-filtered view containing only `effective = true` items. **Most queried table** (48k+/month).

```sql
version_id               INTEGER   -- Numeric version sequence (1, 2, 3...)
_id                      STRING    -- UUID identifier
item_number              STRING    -- Item ID
name                     STRING    -- Human-readable name
object_type              STRING    -- MENU, INGREDIENT, PACKAGED, NON_FOOD, etc.
item_status              STRING    -- ACTIVE, DORMANT, R&D
effective                BOOLEAN   -- Always true in this table
service_start_time       DATETIME  -- Service window start
service_end_time         DATETIME  -- Service window end
menu_price               FLOAT64   -- Menu selling price
shelf_life_period        FLOAT64   -- Shelf life in days
thawed_shelf_life_days   FLOAT64   -- Days after thawing
frozen_shelf_life_days   FLOAT64   -- Days when frozen
cooked_shelf_life_days   FLOAT64   -- Days after cooking
slacking_time_hours      FLOAT64   -- Slacking time in hours
```

**Use this table** instead of `item_versions WHERE effective = true`.

---

### item_versions

All item versions including historical records (140+ fields).

Same schema as `effective_items` plus:
- Contains both `effective = true` and `effective = false` records
- Use when you need version history

**ID Fields**:
- `item_number` - Business ID (STRING)
- `version_id` - Numeric sequence (INTEGER)
- `_id` - UUID identifier (STRING)

---

## Domain Tables

### recipes

Detailed recipe information with procedures and nutrition.

```sql
item_version_id          STRING    -- Version UUID
item_number              STRING    -- Item ID
name                     STRING    -- Recipe name
effective                BOOLEAN   -- Current version flag
service_start_time       DATETIME  -- Service window start
service_end_time         DATETIME  -- Service window end
components               STRING    -- Recipe components (JSON)
procedures               STRING    -- Cooking procedures (JSON)
ingredients              STRING    -- Ingredient list (JSON)
nutrition_fact           STRING    -- Nutrition facts (JSON)
total_yield              FLOAT64   -- Recipe yield amount
yield_unit               STRING    -- Yield unit of measure
skill_level              STRING    -- Required skill level
labor_time               STRING    -- Labor time estimate
```

---

### recipes_procedures

Recipe procedure definitions.

```sql
item_version_id          STRING    -- Version UUID
item_number              STRING    -- Item ID
skill_level              STRING    -- Required skill level
labor_time               STRING    -- Labor time estimate
blast_chiller_final_step BOOLEAN   -- Whether blast chiller is final step
service_start_time       DATETIME  -- Service window start
service_end_time         DATETIME  -- Service window end
line_order               INTEGER   -- Order on the cooking line
procedure_steps          STRING    -- Procedure steps (JSON)
```

---

### recipes_procedure_steps

Individual procedure steps.

```sql
item_version_id          STRING    -- Version UUID
item_number              STRING    -- Item ID
service_start_time       DATETIME  -- Service window start
service_end_time         DATETIME  -- Service window end
line_order               INTEGER   -- Order on the cooking line
procedure_steps          STRING    -- Steps detail (JSON)
step                     STRING    -- Individual step content
```

---

### item_line_builds

Kitchen prep line assignments.

```sql
item_version_id          STRING    -- Version UUID
item_number              STRING    -- Item ID
service_start_time       DATETIME  -- Service window start
service_end_time         DATETIME  -- Service window end
line_build_id            STRING    -- Unique line build identifier
status                   STRING    -- Line build status
restaurant_id            STRING    -- Associated HDR/restaurant

-- Procedure fields
procedures_step_order    INTEGER   -- Order of this step
procedures_cooking_phase STRING    -- PRE_ROUTE_PREP, PRE_ORDER_PREP, PRE_COOKING, COOKING, POST_COOKING
procedures_appliance     STRING    -- FRYER, CLAMSHELL, TURBO_OVEN, PIZZA_OVEN, etc.
procedures_activity      STRING    -- Activity description
procedures_batch_limit   STRING    -- Batch limit
procedures_holding_location STRING -- Where item is held

-- Timing fields
step_time                STRING    -- Total step time
cooking_time             STRING    -- Active cooking time
resting_time             STRING    -- Resting/cooling time
hold_time                STRING    -- Hold time before service

-- Hot hold
is_hot_hold_eligible_selected BOOLEAN -- Can be held hot
show_hot_hold            BOOLEAN   -- Display hot hold option
```

---

### assembly_instruction

Assembly instructions for menu items.

```sql
item_version_id          STRING    -- Version UUID
item_number              STRING    -- Item ID
service_start_time       DATETIME  -- Service window start
service_end_time         DATETIME  -- Service window end
name                     STRING    -- Instruction name
status                   STRING    -- Instruction status
document_type            STRING    -- Type of assembly document
concept_ids              STRING    -- Associated restaurant concepts (JSON)
bag_item_version_ids     STRING    -- Bag/packaging item versions (JSON)
film_item_version_id     STRING    -- Film packaging version
map_gas_type             STRING    -- Modified atmosphere packaging gas type
label                    STRING    -- Label information
image_keys               STRING    -- Image references (JSON)
notes                    STRING    -- Assembly notes
assembly_build_information STRING  -- Build details (JSON)
bom_lines                STRING    -- BOM lines for assembly (JSON)
created_by               STRING    -- Creator name
created_time             DATETIME  -- Creation timestamp
updated_by               STRING    -- Last updater
updated_time             DATETIME  -- Last update timestamp
```

---

### all_item_version_customization_nutrition

Nutrition facts per menu item and customization.

```sql
_id                      STRING    -- Unique record ID
item_number              STRING    -- Item ID
version_id               INTEGER   -- Version number
name                     STRING    -- Item/customization name
is_preset                STRING    -- Whether this is a preset customization
option_name              STRING    -- Customization option name
option_type              STRING    -- Option type
opv_mapping_items        STRING    -- Option value mapping (JSON)

-- Macronutrients (stored as STRING, use SAFE_CAST)
calories_k_cal           STRING    -- Calories (kcal)
total_fat_g              STRING    -- Total fat (grams)
saturated_fat_g          STRING    -- Saturated fat (grams)
trans_fat_g              STRING    -- Trans fat (grams)
cholesterol_mg           STRING    -- Cholesterol (mg)
sodium_mg                STRING    -- Sodium (mg)
carbs_g                  STRING    -- Total carbohydrates (grams)
fiber_g                  STRING    -- Dietary fiber (grams)
sugar_g                  STRING    -- Total sugars (grams)
protein_g                STRING    -- Protein (grams)
add_sugar_g              STRING    -- Added sugars (grams)

-- Vitamins and minerals
vitamin_d_mcg            STRING    -- Vitamin D (mcg)
calcium_mg               STRING    -- Calcium (mg)
iron_mg                  STRING    -- Iron (mg)
potassium_mg             STRING    -- Potassium (mg)

-- Serving and dietary
quantity                 STRING    -- Serving quantity
unit                     STRING    -- Serving unit
opv_allergens            STRING    -- Allergens (JSON)
opv_ingredients          STRING    -- Ingredients list (JSON)
opv_collected_dietary_tags STRING  -- Dietary tags (JSON)
```

---

### ingredients

Raw ingredient information.

```sql
item_version_id          STRING    -- Version UUID
item_number              STRING    -- Ingredient ID
name                     STRING    -- Ingredient name
external_name            STRING    -- External/display name
object_type              STRING    -- Usually 'INGREDIENT'
effective                BOOLEAN   -- Current version flag
nutrition_fact           STRING    -- Nutrition facts (JSON)
allergens_reviewed_info  STRING    -- Allergen review status (JSON)
ingredient_statement     STRING    -- Ingredient statement text
preparations             STRING    -- Preparation methods (JSON)
item_status              STRING    -- ACTIVE, DORMANT, etc.
storage_type             STRING    -- Storage requirements
lot_type                 STRING    -- Lot tracking type
```

---

### components

Recipe component relationships.

```sql
parent_item_version_uuid STRING    -- Parent item version UUID
parent_item_number       STRING    -- Parent item ID
uuid                     STRING    -- Component relationship UUID
item_number              STRING    -- Component item ID
item_version_id          STRING    -- Component version UUID
service_start_time       DATETIME  -- Service window start
service_end_time         DATETIME  -- Service window end
quantity                 FLOAT64   -- Component quantity
unit                     STRING    -- Unit of measure
type                     STRING    -- Component type
item_cost                FLOAT64   -- Component cost
```

---

## Tags and Categorization Tables

### tag_groups

Tag group definitions. Located in `wonder-recipe-prod.recipe_v2.tag_groups`.

```sql
_id                  STRING    -- UUID identifier (FK for tags.tag_group_id)
name                 STRING    -- Group name (e.g., "Beverage Type", "Primary Cuisine")
description          STRING    -- Group description
type                 STRING    -- Input type (DROP_DOWN, etc.)
taggable_sources     STRING    -- JSON array: where tags apply (MARKETPLACE, MERCHANDISING, MASTERDATA)
is_deprecated        BOOLEAN   -- Soft-delete flag
permission_type      STRING    -- Permission level
user_admin_access    STRING    -- User admin access settings
role_admin_access    STRING    -- Role-based admin access
created_by           STRING    -- Creator name
created_user_id      STRING    -- Creator UUID
created_time         DATETIME  -- Creation timestamp
updated_by           STRING    -- Last updater name
updated_user_id      STRING    -- Last updater UUID
updated_time         DATETIME  -- Last update timestamp
```

**Join Pattern**: `tag_groups._id = tags.tag_group_id`

---

### tags

Individual tags within groups. Located in `wonder-recipe-prod.recipe_v2.tags`.

```sql
_id                  STRING    -- UUID identifier (referenced by item_versions.attributes)
tag_group_id         STRING    -- FK to tag_groups._id
name                 STRING    -- Tag display name (e.g., "Coffee", "Italian")
description          STRING    -- Tag description
is_deprecated        BOOLEAN   -- Soft-delete flag
created_by           STRING    -- Creator name
created_user_id      STRING    -- Creator UUID
created_time         DATETIME  -- Creation timestamp
updated_by           STRING    -- Last updater name
updated_user_id      STRING    -- Last updater UUID
updated_time         DATETIME  -- Last update timestamp
```

**Join Pattern**: `JSON_VALUE(item_versions.attributes, '$.tag_id') = tags._id`

See [core/tags-categorization.md](core/tags-categorization.md) for detailed query patterns.

---

## Audit Tables

Located in `secure-recipe-prod.mongo_batch_recipe_v2`:

| Table | Purpose |
|-------|---------|
| `item_versions` | Historical item changes |
| `item_line_build_histories` | Line build change tracking |
| `assembly_instruction_histories` | Assembly instruction changes |
| `item_kitting_instruction_histories` | Kitting instruction history |

---

## Cross-Dataset Joins

### Cookbook → Pantry

```sql
CAST(bom_lines.bom_line_item_number AS STRING) = inventory_on_hand.item_number
```

Dataset: `wonder-raw-prod.mysql_batch_inventory`

### Cookbook → Product Catalog

```sql
CAST(bom_lines.bom_line_item_number AS STRING) = wonder_items.item_number
```

Dataset: `wonder-raw-prod.mysql_batch_product_catalog`

### Cookbook → Orders

```sql
effective_items.item_number = order_items.sku
```

Dataset: `wonder-dw-prod-brd.wonder_dw`

---

## Data Type Notes

- Item numbers may need CAST to STRING for joins
- Nutrition values are STRING - use `SAFE_CAST(field AS FLOAT64)`
- Timestamps use DATETIME or TIMESTAMP types
- JSON fields require `JSON_EXTRACT_*` functions

---

## Service Window Pattern

Always filter for current recipes:

```sql
AND CURRENT_TIMESTAMP() BETWEEN TIMESTAMP(service_start_time) AND TIMESTAMP(service_end_time)
```

For historical analysis at specific date:

```sql
AND TIMESTAMP('YYYY-MM-DD') BETWEEN TIMESTAMP(service_start_time) AND TIMESTAMP(service_end_time)
```

---

## Extended Tables Reference

### wonder-recipe-prod.recipe_v2 (Non-Sensitive)

| Table | Description |
|-------|-------------|
| `item_versions` | Item version data (subset of secure) |
| `effective_items` | Currently effective items |
| `allergens` | Allergen data |
| `assembly_instruction` | Assembly instructions |
| `assembly_instruction_histories` | Historical assembly instructions |
| `attributes` | Item attributes |
| `concepts` | Restaurant concepts |
| `food_nutrition_facts` | Nutrition facts data |
| `item_customization` | Item customization options |
| `item_customizations_flattened` | Flattened customization data |
| `kitchen_locations` | Kitchen location data |
| `kitchen_sub_locations` | Kitchen sub-location data |
| `menus` | Menu data |
| `preparations` | Preparation instructions |
| `smallwares` | Smallwares/equipment data |
| `tag_groups` | Tag group definitions |
| `tags` | Tag data |
| `units` | Unit of measure data |
| `vendor_items` | Vendor item data |
| `vendor_items_v2` | Vendor product catalog (v2) |

### wonder-recipe-prod.mongo_batch_recipe_v2 (Reference Data)

| Table | Description |
|-------|-------------|
| `units` | Unit of measure definitions |
| `unit_conversions` | Unit conversion factors |
| `vendors` | Vendor data |
| `vendor_items_v3` | Vendor items (latest) |
| `vendor_item_units` | Vendor item unit mappings |
| `concepts` | Restaurant concepts |
| `routes` | Route data |
| `route_mappings` | Route mapping data |
| `location_mappings` | Route/facility location mappings |
| `facilities` | Facility data |
| `inventory_consumable_items` | Inventory consumable items |
| `inventory_item_conversions` | Inventory item conversion data |
| `item_version_change_logs` | Item version change history |
| `transfer_cost_change_log` | Cost change history |
| `expanded_item_version_customization_costs` | Customization cost data |
| `appliance_programs` | Appliance program settings |
| `global_appliance_settings` | Global appliance settings |

### wonder-raw-prod.mysql_batch_product_catalog (Product Catalog)

| Table | Description |
|-------|-------------|
| `wonder_items` | Wonder items data |
| `wonder_sku_items` | Wonder SKU items |
| `wonder_sku_fulfillment_options` | SKU fulfillment options |
| `wonder_sku_to_fulfillment_options` | SKU to fulfillment mappings |
| `internal_fulfillment_items` | Internal fulfillment items |
| `ordergrid_items` | Order grid items |
| `pack_relationships` | Pack relationship data |

---

## Key Field Types

### Status Fields

| Field | Values | Description |
|-------|--------|-------------|
| `effective` | true/false | Current active version |
| `deleted` | true/false | Soft-deleted flag (**always filter!**) |
| `item_status` | ACTIVE, DORMANT, R&D | Item lifecycle status |
| `version_status` | DRAFT, APPROVED | Version workflow status |
| `sold_status` | | Sales availability status |

### Item Number Prefixes

| Prefix | Object Type | Description |
|--------|-------------|-------------|
| `80*` | MENU, RECIPE | Menu items and recipes |
| `88*` | PACKAGED | Pre-packaged items |
| `50*` | INGREDIENT | Raw ingredients |
| `30*` | BY_PRODUCT | By-products |
| `40*` | HDR_RECIPE | Header recipes |
| `90*` | NON_FOOD | Non-food items |

### Cost & Pricing Fields

| Field | Description |
|-------|-------------|
| `menu_price` | Customer-facing price |
| `item_cost` | Item cost data (JSON) |
| `item_cost_v2` | Updated cost structure |
| `standard_cost` | Standard cost for accounting |
| `landed_cost` | Total cost including logistics |
| `per_bom_unit_cost` | Cost per BOM unit |

### UOM Fields

| Field | Context |
|-------|---------|
| `inventory_uom` | Inventory tracking |
| `erp_inventory_uom` | ERP system |
| `bom_line_unit` | BOM lines |
| `stock_uom` | Stock keeping |
| `purchase_unit` | Purchasing |

### Shelf Life Fields

| Field | Description |
|-------|-------------|
| `shelf_life_period` | General shelf life |
| `shelf_life_minutes` | Shelf life in minutes |
| `thawed_shelf_life_days` | After thawing |
| `frozen_shelf_life_days` | When frozen |
| `cooked_shelf_life_days` | After cooking |
| `slacking_time_hours` | Time to thaw/slack |
