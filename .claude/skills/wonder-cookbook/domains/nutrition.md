# Nutrition Facts

The nutrition system tracks nutritional information for menu items, including how customizations affect nutrition values. Nutrition is **calculated** by rolling up component nutrition through the BOM tree, scaled by serving size and contribution percentages.

## Core Table

### all_item_version_customization_nutrition

Nutrition facts per menu item and customization option.

```sql
-- Key identification fields
_id                      STRING    -- Unique record ID
item_number              STRING    -- Item ID
version_id               INTEGER   -- Version number
name                     STRING    -- Item/customization name
is_preset                STRING    -- Whether this is a preset customization

-- Customization context
option_name              STRING    -- Customization option name
option_type              STRING    -- Option type
opv_mapping_items        STRING    -- Option value mapping (JSON)

-- Core macronutrients (FDA Standard 14 nutrients)
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

-- Serving info
quantity                 STRING    -- Serving quantity
unit                     STRING    -- Serving unit

-- Dietary information
opv_allergens            STRING    -- Allergens (JSON array)
opv_ingredients          STRING    -- Ingredients list (JSON array)
opv_collected_dietary_tags STRING  -- Dietary tags (JSON array)
```

## Nutrition Calculation Logic

Nutrition values are **calculated**, not manually entered, following these formulas:

### Recipe Nutrition Calculation

```
Recipe Nutrition = SUM(Component Nutrition * Contribution%)
                   * (Serving Size / Yield)
```

**For Ingredient Components:**
```
Component Nutrition = (Ingredient Standard Nutrition / Serving Size)
                      * Usage Quantity
                      * Contribution%
```

**For Sub-Recipe Components:**
```
Component Nutrition = (Sub-Recipe Nutrition / Sub-Recipe Serving Size)
                      * Usage Quantity
                      * Contribution%
```

### Yield vs Serving Size Adjustment

When Yield differs from Serving Size, nutrition is scaled:
```sql
-- If yield = 1000g and serving_size = 100g
-- Final nutrition = calculated_nutrition * (100/1000)
adjusted_nutrition = raw_nutrition * (serving_size / yield)
```

### Unit Conversion Requirements

- Serving size unit MUST be compatible with yield unit
- If units differ, a unit conversion must exist
- Missing conversions result in partial/failed nutrition calculation

## Allergen System

Allergens are **rolled up** from ingredients through the BOM tree to menu items. They are NOT manually entered at the menu item level.

### FDA Big 9 Allergens (Primary)

| Allergen | Visible on App | Sub Types (Examples) |
|----------|----------------|----------------------|
| Milk/Dairy | Yes | Milk |
| Eggs | Yes | Egg |
| Fish | Yes | Salmon, Tuna, Cod, Anchovy, Sea Bass, etc. |
| Shellfish | Yes | Shrimp, Crab, Lobster, Scallop, Squid, etc. |
| Tree Nuts | Yes | Almond, Cashew, Walnut, Pecan, Pistachio, Hazelnut, Pine Nut |
| Peanuts | Yes | Peanut |
| Wheat | Yes | Wheat |
| Soy | Yes | Soy |
| Sesame | Yes | Sesame |

### Additional Allergens (Not Visible on App)

| Allergen | Sub Types |
|----------|-----------|
| Gluten | Gluten |
| Mustard | Mustard |
| Celery | Celery |
| Crustaceans | Crustaceans |
| Lupin | Lupin |
| Molluscs | Molluscs |
| Sulphites | Sulphites |

### Allergen Abbreviations

Each allergen has an abbreviation used in regulation labeling:
- Allergens are displayed with different color chips in the UI
- Hovering shows source ingredient/component item
- Allergens are deduplicated in UI but stored with duplicates in DB

## Dietary Flags (Calculated)

Dietary flags are **system-calculated** based on allergens in the BOM:

### Gluten-Related Flags

| Flag | Condition |
|------|-----------|
| **Gluten Free** | BOM and all eligible mandatory choice options have NO gluten |
| **Gluten Free Optional** | Not Gluten Free, but gluten can be removed via customization (removal options that remove all gluten items from BOM) |

### Vegetarian/Vegan Flags

| Flag | Condition |
|------|-----------|
| **Vegan** | All 1st layer components have 'Vegan' tag AND default mandatory choice option = 'Vegan' |
| **Vegetarian** | All 1st layer components are either 'Vegetarian' or 'Vegan' |
| **Vegan-optional** | Can be made Vegan through customization |
| **Vegetarian-optional** | Can be made Vegetarian through customization |

### Dietary Tags

Stored in `opv_collected_dietary_tags` as JSON. Common values:
- Vegan
- Vegetarian
- Doesn't contain peanuts
- Doesn't contain tree nuts

Tags are **inherited** from ingredients up through parent items.

## Regulation Labeling (88* Items)

For packaged items (88* prefix), additional regulation fields exist:

### Key Regulation Fields

| Field | Description |
|-------|-------------|
| **Statement of Identity** | Product identity statement |
| **Regulatory Body** | FDA or USDA (radio button) |
| **Establishment Code** | For USDA items only, must start with "M-" or "P-" |
| **Individual Use Statement** | Yes/No - prints "For Food Service Only" on labels |
| **Bioengineered?** | Rolled up from ingredients - Yes/No/Unreviewed |
| **Allergen Label** | System-generated allergen abbreviations |
| **Ingredients (system-generated)** | Auto-generated ingredient statement sorted by usage DESC |
| **Ingredients** | Manually adjusted ingredient statement (max 2100 chars) |

### Bioengineered (BE) Flag Logic

```sql
-- BE flag is calculated from ingredient BOM tree:
-- If ANY ingredient has BE=Yes -> Item BE=Yes
-- If ALL ingredients have BE=No -> Item BE=No
-- Otherwise -> Item BE=Unreviewed
```

### Ingredient Statement Generation

Ingredients are listed sorted by **usage quantity DESC** and include:
- Ingredient names from the nested BOM tree
- Byproduct item ingredient statements
- Usage calculated including contribution percentages

## All Ingredients Card

The All Ingredients view shows rolled-up ingredient usage and cost:

### Usage Calculation Formula

```sql
-- Direct ingredient usage
usage = usage_quantity

-- Ingredient in sub-recipe
usage = (sub_recipe_usage / sub_recipe_yield) * ingredient_usage_in_sub_recipe

-- With contribution
final_usage = usage * contribution_percent
```

### Cost Calculation

```
Ingredient Cost = Cost Per BOM Unit * Untrimmed Usage
```

### Unit Handling

- Defaults to grams (g) where possible
- If units differ, unit conversion is applied
- Missing conversions show "---" with warning tooltip

## Query Patterns

### Get Nutrition Facts for a Menu Item

```sql
SELECT
  n.item_number,
  n.name,
  SAFE_CAST(n.calories_k_cal AS FLOAT64) as calories,
  SAFE_CAST(n.total_fat_g AS FLOAT64) as fat_g,
  SAFE_CAST(n.protein_g AS FLOAT64) as protein_g,
  SAFE_CAST(n.carbs_g AS FLOAT64) as carbs_g,
  SAFE_CAST(n.sodium_mg AS FLOAT64) as sodium_mg
FROM `secure-recipe-prod.recipe_v2.all_item_version_customization_nutrition` n
WHERE n.item_number = '8009068'
  AND n.is_preset = 'true'  -- Base nutrition (no customization)
ORDER BY n.name;
```

### Compare Nutrition Across Customizations

```sql
SELECT
  n.item_number,
  n.name,
  n.option_name,
  SAFE_CAST(n.calories_k_cal AS FLOAT64) as calories,
  SAFE_CAST(n.total_fat_g AS FLOAT64) as fat_g,
  SAFE_CAST(n.sodium_mg AS FLOAT64) as sodium_mg
FROM `secure-recipe-prod.recipe_v2.all_item_version_customization_nutrition` n
WHERE n.item_number = '8009068'
ORDER BY SAFE_CAST(n.calories_k_cal AS FLOAT64) DESC;
```

### Find High-Calorie Menu Items

```sql
SELECT DISTINCT
  n.item_number,
  n.name,
  SAFE_CAST(n.calories_k_cal AS FLOAT64) as calories,
  SAFE_CAST(n.protein_g AS FLOAT64) as protein_g
FROM `secure-recipe-prod.recipe_v2.all_item_version_customization_nutrition` n
JOIN `secure-recipe-prod.recipe_v2.effective_items` ei
  ON n.item_number = CAST(ei.item_number AS STRING)
WHERE ei.object_type = 'MENU'
  AND ei.item_status = 'ACTIVE'
  AND n.is_preset = 'true'
  AND SAFE_CAST(n.calories_k_cal AS FLOAT64) > 800
ORDER BY SAFE_CAST(n.calories_k_cal AS FLOAT64) DESC
LIMIT 50;
```

### Find Low-Sodium Options

```sql
SELECT DISTINCT
  n.item_number,
  n.name,
  SAFE_CAST(n.sodium_mg AS FLOAT64) as sodium_mg,
  SAFE_CAST(n.calories_k_cal AS FLOAT64) as calories
FROM `secure-recipe-prod.recipe_v2.all_item_version_customization_nutrition` n
JOIN `secure-recipe-prod.recipe_v2.effective_items` ei
  ON n.item_number = CAST(ei.item_number AS STRING)
WHERE ei.object_type = 'MENU'
  AND ei.item_status = 'ACTIVE'
  AND n.is_preset = 'true'
  AND SAFE_CAST(n.sodium_mg AS FLOAT64) < 500
ORDER BY SAFE_CAST(n.sodium_mg AS FLOAT64)
LIMIT 50;
```

### Get Allergen Information

```sql
SELECT
  n.item_number,
  n.name,
  n.opv_allergens,
  n.opv_ingredients
FROM `secure-recipe-prod.recipe_v2.all_item_version_customization_nutrition` n
WHERE n.item_number = '8009068'
  AND n.opv_allergens IS NOT NULL;
```

### Parse Allergens from JSON

```sql
SELECT
  n.item_number,
  n.name,
  allergen
FROM `secure-recipe-prod.recipe_v2.all_item_version_customization_nutrition` n,
  UNNEST(JSON_EXTRACT_ARRAY(n.opv_allergens)) AS allergen
WHERE n.item_number = '8009068'
  AND n.is_preset = 'true';
```

### Find Items Containing Specific Allergen

```sql
SELECT DISTINCT
  n.item_number,
  n.name
FROM `secure-recipe-prod.recipe_v2.all_item_version_customization_nutrition` n
JOIN `secure-recipe-prod.recipe_v2.effective_items` ei
  ON n.item_number = CAST(ei.item_number AS STRING)
WHERE ei.object_type = 'MENU'
  AND ei.item_status = 'ACTIVE'
  AND n.is_preset = 'true'
  AND n.opv_allergens LIKE '%Shellfish%'
ORDER BY n.name;
```

### Find Items with Specific Dietary Tags

```sql
SELECT DISTINCT
  n.item_number,
  n.name,
  n.opv_collected_dietary_tags
FROM `secure-recipe-prod.recipe_v2.all_item_version_customization_nutrition` n
JOIN `secure-recipe-prod.recipe_v2.effective_items` ei
  ON n.item_number = CAST(ei.item_number AS STRING)
WHERE ei.object_type = 'MENU'
  AND ei.item_status = 'ACTIVE'
  AND n.opv_collected_dietary_tags LIKE '%vegetarian%'
ORDER BY n.name;
```

### Calculate Macronutrient Percentages

```sql
SELECT
  n.item_number,
  n.name,
  SAFE_CAST(n.calories_k_cal AS FLOAT64) as total_calories,
  -- Fat: 9 calories per gram
  ROUND(SAFE_CAST(n.total_fat_g AS FLOAT64) * 9 / SAFE_CAST(n.calories_k_cal AS FLOAT64) * 100, 1) as fat_pct,
  -- Protein: 4 calories per gram
  ROUND(SAFE_CAST(n.protein_g AS FLOAT64) * 4 / SAFE_CAST(n.calories_k_cal AS FLOAT64) * 100, 1) as protein_pct,
  -- Carbs: 4 calories per gram
  ROUND(SAFE_CAST(n.carbs_g AS FLOAT64) * 4 / SAFE_CAST(n.calories_k_cal AS FLOAT64) * 100, 1) as carbs_pct
FROM `secure-recipe-prod.recipe_v2.all_item_version_customization_nutrition` n
WHERE n.item_number = '8009068'
  AND n.is_preset = 'true'
  AND SAFE_CAST(n.calories_k_cal AS FLOAT64) > 0;
```

## Data Type Notes

Nutrition values are stored as STRING type. Use `SAFE_CAST` for numeric comparisons:

```sql
SAFE_CAST(n.calories_k_cal AS FLOAT64)
```

### Decimal Precision

- **Cost**: 6 decimal places
- **Untrimmed/Usage**: 4 decimal places
- **Nutrition comparison**: First 6 decimal places (truncated, not rounded)

## Nutrition Review Status

Nutrition data has a review workflow:

| Status | Description |
|--------|-------------|
| **Approved** | Reviewed and confirmed by user |
| **Needs Review** | Auto-recalculation changed values |

### Auto-Recalculation Triggers

Nutrition is automatically recalculated when:
- Component usage changes
- Components added/removed
- Sub-item nutrition changes
- Unit conversions change
- Yield or serving size changes

When recalculation changes values, review status changes to "Needs Review".

## Warning Messages

Common nutrition calculation warnings:

| Warning | Cause |
|---------|-------|
| "Partial recipe nutrition is being shown" | Some components missing data |
| "Unable to calculate recipe nutrition" | All components missing data or fatal error |
| "Serving size unit incompatible with yield unit" | Missing unit conversion |
| "Missing Cost Per BOM Unit" | Ingredient missing cost data |
| "Missing usage data" | Component usage not specified |

## Related Documentation

- [food-science.md](food-science.md) - Shelf life and food safety
- [../core/item-master.md](../core/item-master.md) - Item metadata
- [recipes-procedures.md](recipes-procedures.md) - Recipe details with nutrition

## Reference: Confluence Documentation

Cross-checked against official Confluence documentation:
- "Regulation Labeling" (MD-12823) - 88* item labeling requirements
- "All Ingredients Card" - Ingredient roll-up and cost calculation
- "Menu Item's Nutrition & Allergens" - Allergen display and dietary flags
- "Nutrition Calculation" - Calculation formulas and unit handling
- "Allergens" - Complete allergen taxonomy and visibility settings

---

## Code References (Java Codebase)

> **Codebase**: `master-data-management-2`
> **Validated**: 2026-01-28

### Domain Models

- **Recipe.NutritionFact** (Nested in Recipe): `backend/domain-library/src/main/java/app/internalrecipe/item/innerclassview/Recipe.java`
  - Embedded nutrition data with all FDA 14 nutrients
  - Both calculated fields (e.g., `caloriesKCal`) and input overrides (`caloriesKCalInput`)

- **ItemNutrition**: `backend/domain-library/src/main/java/app/internalrecipe/item/ItemNutrition.java`
  - Item-level nutrition wrapper

- **ItemCustomizationNutrition**: `backend/domain-library/src/main/java/app/internalrecipe/item/customization/ItemCustomizationNutrition.java`
  - Nutrition per customization option

- **ItemCustomizationNutritionConfig**: `backend/domain-library/src/main/java/app/internalrecipe/item/customization/ItemCustomizationNutritionConfig.java`
  - Configuration for nutrition calculation

- **VendorNutritionFact**: `backend/domain-library/src/main/java/app/internalrecipe/item/innerclassview/VendorNutritionFact.java`
  - Vendor-supplied nutrition data

- **FoodNutritionFact**: `backend/domain-library/src/main/java/app/internalrecipe/nutrition/FoodNutritionFact.java`
  - Base nutrition fact structure

### Dietary Flags & Tags

- **DietaryFlagEnum**: `backend/domain-library/src/main/java/app/internalrecipe/item/innerclassview/DietaryFlagEnum.java`
  - Values: `VEGAN`, `VEGETARIAN`, `GLUTEN_FREE`, `GLUTEN_FREE_OPTIONAL`

- **DietaryTag**: `backend/domain-library/src/main/java/app/internalrecipe/item/innerclassview/DietaryTag.java`
  - Dietary tag definitions

- **DietaryTagInfo**: `backend/domain-library/src/main/java/app/internalrecipe/item/innerclassview/DietaryTagInfo.java`
  - Dietary tag metadata

### Service Layer

- **BOItemCustomizationNutritionService**: `backend/internal-recipe-service/src/main/java/app/internalrecipe/item/service/customization/nutrition/BOItemCustomizationNutritionService.java`
  - Core nutrition operations

- **BOItemCustomizationNutritionCalculateServiceV3**: `backend/internal-recipe-service/src/main/java/app/internalrecipe/item/service/customization/nutrition/BOItemCustomizationNutritionCalculateServiceV3.java`
  - Nutrition calculation logic (latest version)

- **BOItemCustomizationNutritionQueryService**: `backend/internal-recipe-service/src/main/java/app/internalrecipe/item/service/customization/nutrition/BOItemCustomizationNutritionQueryService.java`
  - Nutrition query operations

- **BOCalculateNutritionUsageQuantityService**: `backend/internal-recipe-service/src/main/java/app/internalrecipe/item/service/customization/nutrition/BOCalculateNutritionUsageQuantityService.java`
  - Usage quantity calculations for nutrition

- **BOItemRecipeNutritionCalculateService**: `backend/recipe-service-v2/src/main/java/app/recipev2/item/service/BOItemRecipeNutritionCalculateService.java`
  - Recipe-level nutrition calculation

- **ItemCustomizationNutritionService**: `backend/recipe-service-v2/src/main/java/app/recipev2/item/service/ItemCustomizationNutritionService.java`
  - Public nutrition service

### API Endpoints

- **BOItemCustomizationNutritionWebService**: `backend/internal-recipe-service-interface/src/main/java/app/internalrecipe/api/BOItemCustomizationNutritionWebService.java`
  - Nutrition CRUD endpoints

- **BOFoodNutritionFactWebService**: `backend/internal-recipe-service-interface/src/main/java/app/internalrecipe/api/BOFoodNutritionFactWebService.java`
  - Food nutrition fact endpoints

- **ItemCustomizationNutritionWebService**: `backend/recipe-service-v2-interface/src/main/java/app/recipev2/api/ItemCustomizationNutritionWebService.java`
  - Public nutrition API

### @Deprecated Classes (Entire Package)

The `app.internalrecipe.nutrition` package contains **deprecated classes** (class-level @Deprecated):

| Class | Description |
|-------|-------------|
| `Food.java` | Legacy food entity |
| `FoodCategory.java` | Legacy food category |
| `FoodNutrient.java` | Legacy nutrient data |
| `FoodPortion.java` | Legacy portion data |
| `MeasureUnit.java` | Legacy measurement unit |

These are from an older nutrition system and should not be used in new code. Use `Recipe.NutritionFact` and `ItemCustomizationNutrition` instead.
