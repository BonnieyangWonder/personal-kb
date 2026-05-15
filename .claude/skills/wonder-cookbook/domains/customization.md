# Customization - Customer Choice Options

Menu items can have **customization options** - choices customers can make when ordering (e.g., spice level, protein choice, toppings). Customization data is owned by the Recipe Service (Cookbook) and affects menu item ordering in the Wonder App.

---

## Essential Filter (ALWAYS USE)

When querying customization data through `item_versions`:

```sql
WHERE effective = true
  AND deleted = false
  AND item_status != 'DORMANT'
```

---

## Customization Types (Option Types)

Wonder supports **6 customization types** that define how customers interact with menu item options:

| Type | Description | Min/Max | Example |
|------|-------------|---------|---------|
| `MANDATORY_CHOICE` | Customer **must** select at least one option | min >= 1 | Protein choice (chicken/beef/tofu) |
| `OPTIONAL_ADDITION` | Customer **can optionally** add items | min = 0 | Extra cheese, bacon |
| `DISH_PREFERENCE` | Preference selections (Featured or In-Drawer) | min >= 0 | Temperature preference, spice level |
| `OPTIONAL_SUBTRACTION` | Customer can **remove** items from dish | N/A | "No onions", "Hold the pickles" |
| `EXTRA_REQUESTS` | Special requests with additional pricing | N/A | Extra sauce, double portion |
| `ON_THE_SIDE` | Serve component separately | N/A | "Dressing on the side" |

### Type-Specific Behavior

- **MANDATORY_CHOICE**: Requires mapping item with `required_for_service = true`
- **OPTIONAL_ADDITION/EXTRA_REQUESTS**: Require mapping item and usage quantity
- **OPTIONAL_SUBTRACTION/ON_THE_SIDE**: Select from existing BOM components (no new items added)
- **DISH_PREFERENCE**: Mapping item is optional; can be used for non-inventory preferences

---

## Custom Types (Selection Modes)

Each customization can have a **custom type** that controls how customers select options:

| Custom Type | Description | Constraints |
|-------------|-------------|-------------|
| `Single-select` | Each option can be selected once | Default behavior |
| `Multi-select` | Same option can be selected multiple times | Requires `max_options`; total selections <= max |
| `Partial-select` | Half portions (1/2) of two options | `max_options` must = 1; up to 2 options at 50% each |

### Multi-select Example
- Max Options: 6
- Customer can select: 6 unique choices, 6x same option, or any combination totaling 6

### Partial-select Example
- Options: Ingredient A, B, C
- Customer can select: 50% A + 50% B, or 100% A, or 100% B, etc.

---

## Display Styles

Customizations have a **display style** that controls visibility in the Wonder App:

| Display Style | Description | Applicable Types |
|---------------|-------------|------------------|
| `Featured` | Shown directly on menu item detail page | MANDATORY_CHOICE (always), OPTIONAL_ADDITION, DISH_PREFERENCE |
| `In-Drawer` | Hidden in expandable "customize" section | OPTIONAL_ADDITION, DISH_PREFERENCE, others |

**Note**: MANDATORY_CHOICE is always Featured. ON_THE_SIDE, OPTIONAL_SUBTRACTION, and EXTRA_REQUESTS default to In-Drawer.

---

## Display Options

Controls how option values are presented:

| Display Option | Description | Requirement |
|----------------|-------------|-------------|
| `None` | Show option name only | Default |
| `Only Images` | Show images for each option value | Image required on each option |
| `Only Descriptions` | Show descriptions for each option value | Description required (max 45 chars) |

---

## Option Value Structure

Each customization option contains **option values** (the actual choices):

| Field | Description | Required |
|-------|-------------|----------|
| `id` | Unique option value ID (UUID) | Yes |
| `name` / `display_name` | Name shown to customer | Yes |
| `mapping_item_number` | Item number for inventory/BOM | Yes (except DISH_PREFERENCE, None type) |
| `usage_quantity` | Quantity consumed per selection | Yes for MANDATORY_CHOICE, OPTIONAL_ADDITION, EXTRA_REQUESTS |
| `default_price` | Additional charge ($0.00 default) | Yes (except OPTIONAL_SUBTRACTION, ON_THE_SIDE) |
| `is_default` | Pre-selected when customer views menu | No |
| `ineligible` | Hidden from main menu item (only for presets) | No |
| `nutrition_default` | Used for base nutrition calculation | MANDATORY_CHOICE only |
| `non_item` | "None" option with no mapping item | MANDATORY_CHOICE only |

### None Type Options
MANDATORY_CHOICE can have a "None" option (`non_item = true`) allowing customers to skip the selection. Only one None type option allowed per customization.

---

## Free Choices (Freemium Model)

Customizations can offer free selections up to a threshold:

| Field | Description |
|-------|-------------|
| `free_choices` | Number of free selections before charging |

- Must be between `min_options` and `max_options`
- All options must have `default_price > 0` when free_choices is set
- Not compatible with Partial-select

---

## Presets (BYO Menu Items)

**Presets** are pre-configured customization combinations for Build-Your-Own (BYO) menu items:

- Each preset gets its own **item number** (80* series)
- Inherits customizations from parent BYO menu item
- Can have different default options and ineligible options per preset
- Nutrition calculated based on preset's default options

### Preset Structure
```
BYO Menu Item (8010473)
├── Preset: Chilled Shrimp Bowl (8010474)
│   └── Default: Rice Base + Shrimp Protein
├── Preset: Grilled Chicken Bowl (8010475)
│   └── Default: Mixed Greens Base + Chicken Protein
```

### Preset-Specific Fields
| Field | Description |
|-------|-------------|
| `preset_type` | Y = preset item |
| `parent_item_number` | Links to BYO menu item |
| `ineligible` | Options hidden for this preset only |
| `default_portion` | Quantity for multi-select presets |

---

## Key Fields in item_versions

Customization data is stored as JSON fields in `item_versions`:

| Field | Type | Description |
|-------|------|-------------|
| `item_customization` | JSON | Customization options definition |
| `item_customization_nutrition` | JSON | Nutrition impact per customization |
| `preset_item_version_info` | JSON | **Preferred**: Pre-configured customization combinations |

> **Deprecated**: The `item_customization_presets` field is deprecated. Use `preset_item_version_info` instead for preset queries.

### item_customization JSON Structure
```json
{
  "options": [
    {
      "id": "uuid",
      "name": "Choose Your Protein",
      "type": "MANDATORY_CHOICE",
      "display_style": "Featured",
      "display_options": "None",
      "min_options": 1,
      "max_options": 2,
      "custom_type": "Single-select",
      "free_choices": null,
      "option_values": [
        {
          "id": "uuid",
          "name": "Grilled Chicken",
          "item_number": "8804257",
          "usage_quantity": 0.5,
          "unit": "ea",
          "default_price": 0.00,
          "is_default": true,
          "manage_inventory": true
        }
      ]
    }
  ]
}
```

---

## Related Tables

| Table | Description |
|-------|-------------|
| `wonder-recipe-prod.recipe_v2.item_customization` | Customization options by item |
| `wonder-recipe-prod.recipe_v2.item_customizations_flattened` | Flattened view for easier querying |
| `secure-recipe-prod.recipe_v2.all_item_version_customization_nutrition` | Nutrition data including customizations |

---

## Query Patterns

### Get Customization Options for a Menu Item

```sql
SELECT
  item_number,
  name,
  JSON_EXTRACT(item_customization, '$.options') as customization_options,
  item_customization
FROM `secure-recipe-prod.recipe_v2.item_versions`
WHERE item_number = '8009068'
  AND effective = true
  AND deleted = false
  AND item_customization IS NOT NULL;
```

### Find Items by Customization Type

```sql
SELECT DISTINCT
  iv.item_number,
  iv.name,
  JSON_VALUE(opt, '$.type') as customization_type,
  JSON_VALUE(opt, '$.name') as customization_name
FROM `secure-recipe-prod.recipe_v2.item_versions` iv,
  UNNEST(JSON_EXTRACT_ARRAY(item_customization, '$.options')) as opt
WHERE effective = true
  AND deleted = false
  AND item_status != 'DORMANT'
  AND object_type = 'MENU'
  AND JSON_VALUE(opt, '$.type') IN ('MANDATORY_CHOICE', 'OPTIONAL_ADDITION');
```

### Get Flattened Customization Data

```sql
SELECT
  item_number,
  customization_name,
  customization_type,
  option_name,
  option_price_adjustment,
  option_value_item_number,
  usage_quantity
FROM `wonder-recipe-prod.recipe_v2.item_customizations_flattened`
WHERE item_number = '8009068';
```

### Find Multi-select Customizations

```sql
SELECT
  iv.item_number,
  iv.name,
  JSON_VALUE(opt, '$.name') as customization_name,
  JSON_VALUE(opt, '$.custom_type') as custom_type,
  JSON_VALUE(opt, '$.max_options') as max_options
FROM `secure-recipe-prod.recipe_v2.item_versions` iv,
  UNNEST(JSON_EXTRACT_ARRAY(item_customization, '$.options')) as opt
WHERE effective = true
  AND deleted = false
  AND JSON_VALUE(opt, '$.custom_type') = 'Multi-select';
```

### Get Nutrition with Customizations

The `all_item_version_customization_nutrition` table has rows for both base items and each customization variant.

```sql
-- Base nutrition only (no customizations)
SELECT
  item_number,
  name,
  SAFE_CAST(calories_k_cal AS FLOAT64) as calories,
  SAFE_CAST(protein_g AS FLOAT64) as protein_g
FROM `secure-recipe-prod.recipe_v2.all_item_version_customization_nutrition`
WHERE item_number = '8009068'
  AND is_preset = 'true';  -- Base item only

-- All variants including customizations
SELECT
  item_number,
  name,
  customization_preset_name,
  SAFE_CAST(calories_k_cal AS FLOAT64) as calories
FROM `secure-recipe-prod.recipe_v2.all_item_version_customization_nutrition`
WHERE item_number = '8009068';
```

### Find Preset Menu Items

```sql
-- Using the preferred preset_item_version_info field
SELECT
  iv.item_number,
  iv.name,
  JSON_VALUE(iv.preset_item_version_info, '$.parent_item_number') as parent_byo_item
FROM `secure-recipe-prod.recipe_v2.item_versions` iv
WHERE effective = true
  AND deleted = false
  AND preset_item_version_info IS NOT NULL;

-- Legacy query using deprecated field (avoid in new code)
-- SELECT iv.item_number, iv.name,
--   JSON_VALUE(iv.item_customization_presets, '$.parent_item_number') as parent_byo_item
-- FROM ... WHERE item_customization_presets IS NOT NULL;
```

### All Menu Item BOM + Customization Combined

Get a complete view of all components for menu items - both from BOM lines and from customization options:

```sql
WITH basic_info AS (
  -- BOM Lines
  SELECT
    'BOM_LINE' AS bom_line_or_customization,
    iv.item_number AS parent_item_number,
    iv.name AS parent_item_name,
    iv.version_id,
    iv.sold_status,
    iv.version_status,
    iv.item_status,
    JSON_VALUE(bom_line_raw, '$.item_number') AS child_item_number,
    JSON_VALUE(bom_line_raw, '$.item_version_id') AS child_item_version_id,
    JSON_VALUE(bom_line_raw, '$.manage_inventory') AS is_integral
  FROM `secure-recipe-prod.recipe_v2.item_versions` iv,
    UNNEST(JSON_EXTRACT_ARRAY(iv.bom_header, '$.bom_lines')) AS bom_line_raw
  WHERE item_status != 'DORMANT'
    AND deleted = false
    AND object_type = 'MENU'
    AND effective = true

  UNION ALL

  -- Customization Options
  SELECT
    'CUSTOMIZATION' AS bom_line_or_customization,
    iv.item_number AS parent_item_number,
    iv.name AS parent_item_name,
    iv.version_id,
    iv.sold_status,
    iv.version_status,
    iv.item_status,
    JSON_VALUE(customization_option_value_item_raw, '$.item_number') AS child_item_number,
    JSON_VALUE(customization_option_value_item_raw, '$.version_id') AS child_item_version_id,
    JSON_VALUE(customization_option_value_item_raw, '$.manage_inventory') AS is_integral
  FROM `secure-recipe-prod.recipe_v2.item_versions` iv,
    UNNEST(JSON_EXTRACT_ARRAY(iv.item_customization, '$.options')) AS customization_options_raw,
    UNNEST(JSON_EXTRACT_ARRAY(customization_options_raw, '$.option_values')) AS customization_option_value_raw,
    UNNEST(JSON_EXTRACT_ARRAY(customization_option_value_raw, '$.items')) AS customization_option_value_item_raw
  WHERE item_status != 'DORMANT'
    AND deleted = false
    AND object_type = 'MENU'
    AND effective = true
    AND JSON_VALUE(customization_options_raw, '$.type') IN ('MANDATORY_CHOICE', 'OPTIONAL_ADDITION')
)
SELECT
  b.parent_item_number,
  b.parent_item_name,
  b.sold_status AS parent_item_sold_status,
  b.child_item_number,
  bom_line_item.name AS child_item_name,
  b.bom_line_or_customization,
  bom_line_item.version_id AS child_item_version_id,
  b.is_integral
FROM basic_info b
LEFT JOIN `secure-recipe-prod.recipe_v2.item_versions` bom_line_item
  ON bom_line_item._id = b.child_item_version_id
ORDER BY parent_item_number, bom_line_or_customization;
```

### Line Build Mapped Customization and Related Items

Find the relationship between customization option values and their line build step mappings:

```sql
WITH iv_base AS (
  SELECT item_number, name, sold_status, version_status, item_line_build, version_id, effective
  FROM `secure-recipe-prod.recipe_v2.item_versions`
  WHERE object_type = 'MENU'
    AND item_line_build IS NOT NULL
    AND effective = true
    AND item_status != 'DORMANT'
    AND deleted = false
),
line_build AS (
  SELECT iv_base.*, lb
  FROM iv_base,
  UNNEST(JSON_EXTRACT_ARRAY(iv_base.item_line_build, '$.line_builds')) AS lb
),
lb_task AS (
  SELECT line_build.*, t,
    JSON_EXTRACT(t, '$.customization_option') AS t_rc,
    JSON_EXTRACT_SCALAR(t, '$.name') AS t_name
  FROM line_build,
  UNNEST(JSON_EXTRACT_ARRAY(line_build.lb, '$.tasks')) AS t
),
lb_procedure AS (
  SELECT lb_task.*, p,
    JSON_VALUE(p, '$.related_item_number') AS p_ri,
    JSON_EXTRACT(p, '$.customization_option') AS p_rc,
    JSON_VALUE(p, '$.order') AS p_order,
    JSON_VALUE(p, '$.activity') AS activity
  FROM lb_task,
  UNNEST(JSON_EXTRACT_ARRAY(lb_task.t, '$.procedures')) AS p
),
lb_ps AS (
  SELECT lb_procedure.*, ps,
    JSON_VALUE(ps, '$.related_item_number') AS ps_ri,
    JSON_EXTRACT(ps, '$.related_customization_option') AS ps_rc,
    JSON_VALUE(ps, '$.order') AS ps_order
  FROM lb_procedure,
  UNNEST(JSON_EXTRACT_ARRAY(lb_procedure.p, '$.procedure_steps')) AS ps
),
lb AS (
  SELECT
    item_number, name, sold_status, version_status, version_id, effective, t_name, p_order, activity,
    t_rc AS task_related_customization,
    JSON_VALUE(t_rc, '$.option_value_id') AS t_rc_o_id,
    p_rc AS procedure_related_customization,
    JSON_VALUE(p_rc, '$.option_value_id') AS p_rc_o_id,
    ps_rc AS p_step_related_customization,
    JSON_VALUE(ps_rc, '$.option_value_id') AS ps_rc_o_id
  FROM lb_ps
  WHERE effective = true
    AND activity IN ('VEND', 'COMPLETE')
    AND (t_rc IS NOT NULL OR p_ri IS NOT NULL OR p_rc IS NOT NULL OR ps_ri IS NOT NULL OR ps_rc IS NOT NULL)
  ORDER BY version_id, p_order, ps_order
),
customization_raw AS (
  SELECT
    iv.item_number AS parent_item_number,
    iv.name AS parent_item_name,
    iv.version_id,
    iv.sold_status,
    iv.version_status,
    iv.item_status,
    JSON_VALUE(customization_option_value_raw, '$.id') AS id,
    JSON_VALUE(customization_option_value_item_raw, '$.item_number') AS child_item_number,
    JSON_VALUE(customization_option_value_item_raw, '$.version_id') AS child_item_version_id,
    JSON_VALUE(customization_option_value_item_raw, '$.manage_inventory') AS is_integral
  FROM `secure-recipe-prod.recipe_v2.item_versions` iv,
    UNNEST(JSON_EXTRACT_ARRAY(iv.item_customization, '$.options')) AS customization_options_raw,
    UNNEST(JSON_EXTRACT_ARRAY(customization_options_raw, '$.option_values')) AS customization_option_value_raw,
    UNNEST(JSON_EXTRACT_ARRAY(customization_option_value_raw, '$.items')) AS customization_option_value_item_raw
  WHERE item_status != 'DORMANT'
    AND deleted = false
    AND object_type = 'MENU'
    AND effective = true
)
SELECT
  'Customization data | ' AS separator1,
  cr.parent_item_number AS menu_item_number,
  cr.parent_item_name AS menu_item_name,
  cr.child_item_number AS mapped_item_number,
  cr.child_item_version_id AS mapped_item_version_id,
  cr.id AS customization_option_value_id,
  'Line build data | ' AS separator2,
  lb.*
FROM customization_raw cr
LEFT JOIN lb
  ON (lb.t_rc_o_id = cr.id OR lb.p_rc_o_id = cr.id OR lb.ps_rc_o_id = cr.id)
WHERE (lb.t_rc_o_id IS NOT NULL OR lb.p_rc_o_id IS NOT NULL OR lb.ps_rc_o_id IS NOT NULL);
```

---

## Inventory Impact

Customization affects inventory through the `manage_inventory` flag:

| Customization Type | manage_inventory | Inventory Impact |
|--------------------|------------------|------------------|
| MANDATORY_CHOICE | true | Decrements inventory |
| OPTIONAL_ADDITION | true | Decrements inventory |
| EXTRA_REQUESTS | true | Decrements inventory |
| DISH_PREFERENCE | false | No inventory impact |
| OPTIONAL_SUBTRACTION | null | No inventory impact |
| ON_THE_SIDE | null | No inventory impact |

**Multi-select quantity calculation:**
- Customer selects "Grilled Chicken x 2"
- Usage: 8804257 (0.5 ea) x 2 = 1 ea decremented

---

## Critical Rules

1. **Always include `deleted = false`** when querying item_versions
2. **Use `is_preset = 'true'`** to get base nutrition without customizations
3. **Use SAFE_CAST** for nutrition values (stored as STRING)
4. **Check for NULL** - not all items have customizations
5. **Partial-select max must = 1** - only supports half portions of two options
6. **None type option** - only one allowed per MANDATORY_CHOICE customization
7. **Free choices requires max_options** and all options must have price > 0

---

## Deprecation Notes

### item_customization_presets

> **Deprecated**: The `item_customization_presets` field is deprecated. Use `preset_item_version_info` instead.

The preset system has been refactored. The new `preset_item_version_info` structure contains:

```json
{
  "parent_item_number": "8010473",
  "parent_item_version_id": "uuid",
  "preset_options": [
    {
      "option_id": "uuid",
      "option_value_id": "uuid",
      "is_default": true,
      "default_portion": 1
    }
  ]
}
```

### Query Migration

```sql
-- Old (deprecated):
SELECT * FROM item_versions WHERE item_customization_presets IS NOT NULL;

-- New (preferred):
SELECT * FROM item_versions WHERE preset_item_version_info IS NOT NULL;
```

---

## Related Documentation

- [nutrition.md](nutrition.md) - Nutrition data including customization impacts
- [../core/item-master.md](../core/item-master.md) - Item master data
- Confluence: [Customization V2](https://wonder.atlassian.net/wiki/spaces/RT/pages/3954836149/Customization+V2)

---

## Code References (Java Codebase)

> **Codebase**: `master-data-management-2`
> **Validated**: 2026-01-28

### Domain Models

- **ItemCustomization**: `backend/domain-library/src/main/java/app/internalrecipe/item/customization/ItemCustomization.java`
  - Embedded in ItemVersion.itemCustomization field
  - Key fields: `options` (List<Option>), audit fields (createdTime, updatedTime)
  - Nested classes: `Option`, `OptionValue`, `Item`

- **ItemCustomization.Option**: Nested class for customization options
  - Key fields: `id`, `name`, `type` (CustomizationOptionType), `optionValues`, `displayStyle`, `displayOption`
  - Selection: `customType` (ItemCustomizationType), `minChoices`, `maxChoices`, `freemium`, `isQuantitySelector`

- **ItemCustomization.OptionValue**: Nested class for option values
  - Key fields: `id`, `name`, `items`, `isNone`, `isDefaultValue`, `defaultPortion`, `price`, `description`
  - Image: `imageKey`, `taxCategoryId`, `inEligible`, `componentIncludedInRecipe`

- **ItemCustomization.Item**: Nested class for mapped items
  - Key fields: `versionId`, `itemNumber`, `usageQuantity`, `bomLineUnit`, `noRequiresPackaging`, `manageInventory`
  - Package: `packageSKUConfigs` (List<PackageSKUConfig>)

- **ItemCustomizationPreset**: `backend/domain-library/src/main/java/app/internalrecipe/item/customization/ItemCustomizationPreset.java`
  - Pre-configured customization combinations for BYO items
  - Key fields: `id`, `name`, `deleted`, `options` (List<Option>)
  - Nested classes: `Option`, `OptionValue` with `isSelected`, `inEligible`, `defaultPortion`

- **ItemCustomizationNutrition**: `backend/domain-library/src/main/java/app/internalrecipe/item/customization/ItemCustomizationNutrition.java`
  - Nutrition calculations with customization impacts
  - Key fields: `itemNumber`, `nutritionFact`, `allergens`, `dietaryFlags`, `ingredients`, `inputNutrition`, `options`
  - Nested classes: `InputNutrition`, `ComponentNutrition`, `ReviewedInfo`, `Option`, `OptionValue`, `NutritionFact`, `Allergen`

### Enums

- **CustomizationOptionType**: `backend/domain-library/src/main/java/app/internalrecipe/item/linebuild/CustomizationOptionType.java`
  - Values: `MANDATORY_CHOICE`, `OPTIONAL_ADDITION`, `DISH_PREFERENCE`, `OPTIONAL_SUBTRACTION`, `EXTRA_REQUESTS`, `ON_THE_SIDE`

- **ItemCustomizationType**: `backend/domain-library/src/main/java/app/internalrecipe/item/customization/ItemCustomizationType.java`
  - Selection modes: `SINGLE_SELECT`, `MULTI_SELECT`, `PARTIAL_SELECT`

- **ItemCustomizationDisplayStyle**: `backend/domain-library/src/main/java/app/internalrecipe/item/customization/ItemCustomizationDisplayStyle.java`
  - Values: `FEATURED`, `IN_DRAWER`

- **ItemCustomizationDisplayOption**: `backend/domain-library/src/main/java/app/internalrecipe/item/customization/ItemCustomizationDisplayOption.java`
  - Values: `NONE`, `SHOW_IMAGE`, `SHOW_DESCRIPTION`

### Service Layer

- **BOItemCustomizationService**: `backend/internal-recipe-service/src/main/java/app/internalrecipe/item/service/BOItemCustomizationService.java`
  - Core customization operations

- **BOItemCustomizationUpdateService**: `backend/internal-recipe-service/src/main/java/app/internalrecipe/item/service/customization/BOItemCustomizationUpdateService.java`
  - Customization CRUD operations

- **BOItemCustomizationCheckService**: `backend/internal-recipe-service/src/main/java/app/internalrecipe/item/service/customization/BOItemCustomizationCheckService.java`
  - Validation for customization operations

- **BOItemCustomizationSortService**: `backend/internal-recipe-service/src/main/java/app/internalrecipe/item/service/customization/BOItemCustomizationSortService.java`
  - Customization option ordering

- **BOCustomizationPublishMessageService**: `backend/internal-recipe-service/src/main/java/app/internalrecipe/item/service/customization/BOCustomizationPublishMessageService.java`
  - Kafka publishing for customization changes

- **BOItemCustomizationNutritionQueryService**: `backend/internal-recipe-service/src/main/java/app/internalrecipe/item/service/customization/nutrition/BOItemCustomizationNutritionQueryService.java`
  - Query customization nutrition data

- **BOItemCustomizationAndPresetCrossCheckService**: `backend/internal-recipe-service/src/main/java/app/internalrecipe/item/service/customization/preset/BOItemCustomizationAndPresetCrossCheckService.java`
  - Preset validation against customizations

### API Endpoints

- **BOItemCustomizationWebService**: `backend/internal-recipe-service-interface/src/main/java/app/internalrecipe/api/BOItemCustomizationWebService.java`
  - `GET /bo/item/:itemNumber/customization` - Get customization for item
  - `GET /bo/item/version/:uuid/customization` - Get version customization
  - `POST /bo/item/version/:uuid/customization/option` - Create option
  - `PUT /bo/item/version/:uuid/customization/option/:optionId` - Update option
  - `DELETE /bo/item/version/:uuid/customization/option/:optionId` - Delete option
  - `POST /bo/item/version/:uuid/customization/option/:optionId/option-value` - Create option value
  - `PUT /bo/item/version/:uuid/customization/option/:optionId/option-value/:optionValueId` - Update option value
  - Various check and validation endpoints

- **BOItemCustomizationNutritionWebService**: `backend/internal-recipe-service-interface/src/main/java/app/internalrecipe/api/BOItemCustomizationNutritionWebService.java`
  - Customization nutrition endpoints

- **BOItemCustomizationWebServiceV3**: `backend/internal-recipe-service-interface/src/main/java/app/internalrecipe/api/BOItemCustomizationWebServiceV3.java`
  - V3 customization API with sort, replace, and preset operations

### Business Logic Patterns

- **Customization Embedded in ItemVersion**: Stored as `itemCustomization` field in ItemVersion
- **Option Type Validation**: Different rules per CustomizationOptionType (MANDATORY requires item, DISH_PREFERENCE optional)
- **Preset Cross-Check**: Presets validated against parent BYO item customizations
- **Nutrition Recalculation**: Triggered when customization options change

### @Deprecated Fields

No @Deprecated annotations found in customization domain classes.
