# Recipes and Procedures

The recipes and procedures system stores detailed cooking instructions, procedure steps, and preparation methods for menu items and components.

## Key Concepts

### Skill Levels

Skill levels indicate the training required to execute a procedure. Defined as 5 levels:

| Level | Description |
|-------|-------------|
| Level 1 | Lowest skill requirement |
| Level 2 | Basic skills |
| Level 3 | Intermediate |
| Level 4 | Advanced skills |
| Level 5 | Highest skill requirement |

**Note:** Skill level is **optional** for recipe items (benchtop recipes hide this field).

### Labor Time

Labor time is the total time for one person to complete a procedure. **This includes cook time.**

- Format: "xx hour xx min xx sec"
- **Required field** for procedures
- Stored as STRING in BigQuery (e.g., "1 hour 30 min 0 sec")

### Procedure Guidelines

Per Cookbook business rules, a valid procedure:
- May contain at most **one appliance**
- May contain at most **one tool**
- May contain both an appliance and a tool
- May contain at most **3 disposables**
- **Must include labor time**

### Blast Chiller Final Step

Toggle indicating whether the final step requires a blast chiller. Defaults to **Yes**.

### Yield (Cooking and Preparations)

Yield represents the output percentage after cooking/preparation:
- Must be positive with 1 decimal place
- Range: >0 and <=100
- Defaults to **100%** if not specified
- **Cannot be null** - inline error if deleted without value

**Important:** Yield changes propagate to **live and future versions only** (expired versions are not updated).

### Preparation Types

Two types of preparations exist:
- **Action type**: Active cooking/prep actions (shown when editing)
- **Reference type**: References only (hidden when editing yields)

## Core Tables

### recipes

Detailed recipe information including components, procedures, nutrition, and preparation details.

```sql
-- Key fields
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

### recipes_procedures

Recipe procedure definitions linking items to their cooking procedures.

```sql
-- Key fields
item_version_id          STRING    -- Version UUID
item_number              STRING    -- Item ID
skill_level              STRING    -- Skill level 1-5 (optional, NULL for benchtop recipes)
labor_time               STRING    -- Labor time "xx hour xx min xx sec" (required)
blast_chiller_final_step BOOLEAN   -- Whether blast chiller is final step (default: true)
service_start_time       DATETIME  -- Service window start
service_end_time         DATETIME  -- Service window end
line_order               INTEGER   -- Order on the cooking line
procedure_steps          STRING    -- Procedure steps (JSON)
```

**Skill Level Values:** `'Level 1'`, `'Level 2'`, `'Level 3'`, `'Level 4'`, `'Level 5'` (or NULL)

### recipes_procedure_steps

Individual procedure steps with detailed instructions.

```sql
-- Key fields
item_version_id          STRING    -- Version UUID
item_number              STRING    -- Item ID
service_start_time       DATETIME  -- Service window start
service_end_time         DATETIME  -- Service window end
line_order               INTEGER   -- Order on the cooking line
procedure_steps          STRING    -- Steps detail (JSON)
step                     STRING    -- Individual step content (free text, max 999 chars)
```

**Step Order:** Steps can be reordered via drag-and-drop in the UI. The `line_order` field reflects display sequence.

## Query Patterns

### Get Recipe Details with Nutrition

```sql
SELECT
  item_number,
  name,
  total_yield,
  yield_unit,
  skill_level,
  labor_time,
  nutrition_fact
FROM `secure-recipe-prod.recipe_v2.recipes`
WHERE effective = true
  AND item_number = '8009068';
```

### Get Procedure Steps for a Menu Item

```sql
SELECT
  rp.item_number,
  ei.name as item_name,
  rp.skill_level,
  rp.labor_time,
  rp.line_order,
  rp.blast_chiller_final_step,
  rp.procedure_steps
FROM `secure-recipe-prod.recipe_v2.recipes_procedures` rp
LEFT JOIN `secure-recipe-prod.recipe_v2.effective_items` ei
  ON rp.item_number = CAST(ei.item_number AS STRING)
WHERE rp.item_number = '8009068'
  AND CURRENT_TIMESTAMP() BETWEEN TIMESTAMP(rp.service_start_time) AND TIMESTAMP(rp.service_end_time)
ORDER BY rp.line_order;
```

### Get Individual Procedure Steps

```sql
SELECT
  rps.item_number,
  ei.name as item_name,
  rps.line_order,
  rps.step
FROM `secure-recipe-prod.recipe_v2.recipes_procedure_steps` rps
LEFT JOIN `secure-recipe-prod.recipe_v2.effective_items` ei
  ON rps.item_number = CAST(ei.item_number AS STRING)
WHERE rps.item_number = '8009068'
  AND CURRENT_TIMESTAMP() BETWEEN TIMESTAMP(rps.service_start_time) AND TIMESTAMP(rps.service_end_time)
ORDER BY rps.line_order;
```

### Find Items by Skill Level

```sql
-- Find high-skill items (Level 4 or 5)
SELECT DISTINCT
  rp.item_number,
  ei.name as item_name,
  rp.skill_level,
  rp.labor_time
FROM `secure-recipe-prod.recipe_v2.recipes_procedures` rp
LEFT JOIN `secure-recipe-prod.recipe_v2.effective_items` ei
  ON rp.item_number = CAST(ei.item_number AS STRING)
WHERE rp.skill_level IN ('Level 4', 'Level 5')
  AND ei.object_type = 'MENU'
  AND ei.item_status = 'ACTIVE'
  AND CURRENT_TIMESTAMP() BETWEEN TIMESTAMP(rp.service_start_time) AND TIMESTAMP(rp.service_end_time)
ORDER BY ei.name;
```

**Note:** Skill levels are stored as `'Level 1'` through `'Level 5'`, not descriptive terms like `'Advanced'`.

### Join Recipes to BOM Components

```sql
-- Get recipe with its required components
SELECT
  r.item_number,
  r.name as recipe_name,
  r.total_yield,
  r.yield_unit,
  bl.bom_line_item_number as component_id,
  ei_comp.name as component_name,
  bl.quantity,
  bl.unit
FROM `secure-recipe-prod.recipe_v2.recipes` r
INNER JOIN `secure-recipe-prod.recipe_v2.bom_headers` bh
  ON r.item_number = bh.item_number
INNER JOIN `secure-recipe-prod.recipe_v2.bom_lines` bl
  ON bh.item_number = bl.bom_header_item_number
LEFT JOIN `secure-recipe-prod.recipe_v2.effective_items` ei_comp
  ON CAST(bl.bom_line_item_number AS STRING) = CAST(ei_comp.item_number AS STRING)
WHERE r.effective = true
  AND r.item_number = '8009068'
  AND bh.is_active = true
  AND bl.manage_inventory = true
  AND CURRENT_TIMESTAMP() BETWEEN TIMESTAMP(bl.service_start_time) AND TIMESTAMP(bl.service_end_time)
ORDER BY component_id;
```

## JSON Field Parsing

The `procedures`, `components`, and `ingredients` fields contain JSON data. Parse them using BigQuery JSON functions:

```sql
-- Parse procedure steps from JSON
SELECT
  item_number,
  name,
  JSON_EXTRACT_ARRAY(procedures) as procedure_array
FROM `secure-recipe-prod.recipe_v2.recipes`
WHERE effective = true
  AND item_number = '8009068';
```

## Service Window Filtering

Like other Cookbook tables, recipes tables use service windows. Always filter:

```sql
AND CURRENT_TIMESTAMP() BETWEEN TIMESTAMP(service_start_time) AND TIMESTAMP(service_end_time)
```

## Preparation Usage Tracking

Preparations track usage counts across recipes:

```sql
-- Count preparation usage across recipes
SELECT
  prep_name,
  COUNT(*) as usage_count
FROM (
  -- Extract preparation references from recipes
  SELECT DISTINCT
    r.item_number,
    JSON_EXTRACT_SCALAR(prep, '$.name') as prep_name
  FROM `secure-recipe-prod.recipe_v2.recipes` r,
    UNNEST(JSON_EXTRACT_ARRAY(r.procedures)) as prep
  WHERE r.effective = true
)
GROUP BY prep_name
ORDER BY usage_count DESC;
```

**Usage Calculation Rules:**
- If a recipe uses an ingredient 2+ times with the same preparation, each use counts
- Usage includes preparations tagged on component items
- Example: Carrot with [Sliced] preparation used in 2 components = usage of 2

## Version Propagation

When preparation yields change:
- **Live versions**: Updated immediately
- **Future/scheduled versions**: Updated immediately
- **Expired versions**: NOT updated (preserves historical data)

**Warning Trigger:** When updating yield to a value different from other versions, UI shows confirmation dialog listing affected preparations.

## Related Documentation

- [../core/bom-components.md](../core/bom-components.md) - BOM structure
- [../core/service-windows.md](../core/service-windows.md) - Recipe versioning
- [line-build.md](line-build.md) - Kitchen line assignments

## Source Documentation

- Confluence: [Procedure Card](https://wonder.atlassian.net/wiki/spaces/3185017363/pages/4202463306) - Procedure definitions
- Confluence: [Cooking and Preparation Card](https://wonder.atlassian.net/wiki/spaces/3185017363/pages/4219240510) - Cooking instructions

---

## Code References (Java Codebase)

> **Codebase**: `master-data-management-2`
> **Validated**: 2026-01-28

### Domain Models

- **Recipe (Inner Class)**: `backend/domain-library/src/main/java/app/internalrecipe/item/innerclassview/Recipe.java`
  - Embedded in ItemVersion.recipe field
  - Key fields: `totalYield`, `yieldUnit`, `skillLevel`, `laborTime`, `blastChillerFinalStep`
  - Procedure fields: `procedures` (List<Procedure>), `skillLevel` (SkillLevelEnum)
  - Nutrition: `nutritionFact`, `dietaryFlags`, `nutritionReviewedInfo`
  - Components: `components` (List<RecipeComponent>), `ingredients` (List<Ingredient>)
  - **@Deprecated fields (5)**:
    - `cost` → use `itemCostV2` on ItemVersion
    - `costSource` → cost source refactored
    - `applianceAndEquipment` → moved to separate card
    - `price` → use `menuPrice` on ItemVersion
    - `kitchenLocationId` → kitchen location refactored

- **Recipe.Procedure**: Nested class for procedure steps
  - Fields: `order` (Integer), `procedureSteps` (List<ProcedureStep>)

- **Recipe.ProcedureStep**: Individual step text
  - Fields: `text` (String, max 999 chars)

- **Recipe.NutritionFact**: Nutrition data container
  - All standard nutrition fields (calories, fat, sodium, carbs, etc.)
  - Both calculated and `_input` suffix fields for override values

- **BasicRecipe**: `backend/domain-library/src/main/java/app/internalrecipe/basicrecipe/BasicRecipe.java`
  - MongoDB Collection: `basic_recipes`
  - Simple entity for basic recipe types (tag-like)
  - Key fields: `uuid`, `name`, `createdTime`, `updatedTime`

- **Preparation**: `backend/domain-library/src/main/java/app/internalrecipe/preparation/Preparation.java`
  - MongoDB Collection: `preparations`
  - Key fields: `name`, `type` (PreparationType), `active`, `usages`
  - Used for preparation methods (sliced, diced, etc.)

- **SkillLevelEnum**: `backend/domain-library/src/main/java/app/internalrecipe/item/appliancesandequipment/SkillLevelEnum.java`
  - Values: `Level_1`, `Level_2`, `Level_3`, `Level_4`, `Level_5`

### Service Layer

- **BOItemRecipeQueryService**: `backend/recipe-service-v2/src/main/java/app/recipev2/item/service/BOItemRecipeQueryService.java`
  - Recipe query operations

- **ItemRecipeService**: `backend/recipe-service-v2/src/main/java/app/recipev2/item/service/ItemRecipeService.java`
  - Core recipe service operations

- **BOItemRecipeNutritionCalculateService**: `backend/recipe-service-v2/src/main/java/app/recipev2/item/service/BOItemRecipeNutritionCalculateService.java`
  - Nutrition calculation from components

### API Endpoints

- **BOItemRecipeWebService**: `backend/internal-recipe-service-interface/src/main/java/app/internalrecipe/api/BOItemRecipeWebService.java`
  - Recipe CRUD operations

- **BOItemRecipeWebServicePart2**: `backend/internal-recipe-service-interface/src/main/java/app/internalrecipe/api/BOItemRecipeWebServicePart2.java`
  - Additional recipe endpoints

- **BOBasicRecipeWebService**: `backend/internal-recipe-service-interface/src/main/java/app/internalrecipe/api/BOBasicRecipeWebService.java`
  - Basic recipe type management

- **BOItemRecipeComponentOutputWebService**: `backend/internal-recipe-service-interface/src/main/java/app/internalrecipe/api/BOItemRecipeComponentOutputWebService.java`
  - Recipe component output operations

- **ItemRecipeWebService**: `backend/recipe-service-v2-interface/src/main/java/app/recipev2/api/ItemRecipeWebService.java`
  - Public recipe API

### Business Logic Patterns

- **Recipe Embedded in ItemVersion**: Recipe data is stored as `recipe` field in ItemVersion, not a separate collection
- **Procedure Step Ordering**: Steps have `order` field for sequence, supports drag-and-drop reordering
- **Nutrition Calculation**: Aggregated from component items, with manual override via `*_input` fields
- **Yield Propagation**: Yield changes propagate to live/future versions only, not expired

### @Deprecated Field Summary

| Field | Location | Replacement |
|-------|----------|-------------|
| `cost` | Recipe | `itemCostV2` on ItemVersion |
| `costSource` | Recipe | Cost source refactored |
| `applianceAndEquipment` | Recipe | Moved to separate card |
| `price` | Recipe | `menuPrice` on ItemVersion |
| `kitchenLocationId` | Recipe | Kitchen location refactored |
