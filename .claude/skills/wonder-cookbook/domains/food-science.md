# Food Science - Shelf Life and Safety

The food science data in Cookbook tracks shelf life, storage requirements, and food safety parameters for items. This documentation is cross-referenced with Confluence pages "Food Science Card" (4162520992) and "Hot Holding Card" (4210098546).

## Key Fields in item_versions / effective_items

Food science fields are part of the item metadata tables:

```sql
-- Shelf life fields (stored in MINUTES - see migration notes below)
shelf_life_minutes           FLOAT64   -- Default shelf life in minutes
reduced_shelf_life_minutes   FLOAT64   -- Reduced shelf life in minutes
reduced_label_category       STRING    -- Required if reduced_shelf_life is set
reduced_label_details        STRING    -- Optional details for reduced shelf life
thawed_shelf_life_minutes    FLOAT64   -- Minutes after thawing
frozen_shelf_life_minutes    FLOAT64   -- Minutes when frozen
cooked_shelf_life_minutes    FLOAT64   -- Minutes after cooking
slacking_time_minutes        FLOAT64   -- Slacking time in minutes - must set thawed if this is set

-- COB (Close of Business) flag
cob                      BOOLEAN   -- If true, item expires at close of business
                                   -- Default: true for food items (7*/88*/80*/5*/6*)
                                   -- NOT set for 9* non-food items

-- Storage and safety
storage_type             STRING    -- Storage requirements
lot_type                 STRING    -- Lot tracking type
```

> **Important**: All shelf life fields now use minutes as the standard unit. See [Deprecation Notes](#deprecation-notes) for migration details.

### Reduced-Label Category Values

When `reduced_shelf_life` is set, `reduced_label_category` is required:
- `Bulk Kit`
- `HDR`
- `HDR - Sushi/Poke`
- `HDR - Other Pizza`
- `Public Health Control`

### Reduced-Label Details Values (Optional)

- `Keep Covered and Refrigerated`
- `Quality Hold Time`
- `Removed from freezer - Keep Refrigerated`
- `Sourced Local Program`
- `Time as Public Health Control`

### Shelf Life Time Format

The UI supports Days/Hrs/Mins format with validation:
- Hours: should be < 24
- Minutes: should be < 60
- Days/hrs/mins: should be >= 0
- Thawed shelf life is stored in minutes in DB
- Thawed shelf life does NOT include slacking time

## Query Patterns

### Get Shelf Life for Items

```sql
SELECT
  item_number,
  name,
  object_type,
  shelf_life_minutes,
  ROUND(shelf_life_minutes / 1440, 2) as shelf_life_days,  -- Convert to days for readability
  thawed_shelf_life_minutes,
  frozen_shelf_life_minutes,
  cooked_shelf_life_minutes,
  slacking_time_minutes
FROM `secure-recipe-prod.recipe_v2.effective_items`
WHERE item_number = '8009068';
```

### Find Items with Short Shelf Life

```sql
SELECT
  item_number,
  name,
  object_type,
  shelf_life_minutes,
  ROUND(shelf_life_minutes / 1440, 2) as shelf_life_days
FROM `secure-recipe-prod.recipe_v2.effective_items`
WHERE shelf_life_minutes IS NOT NULL
  AND shelf_life_minutes <= 2880  -- 2 days or less (2 * 1440 minutes)
  AND item_status = 'ACTIVE'
ORDER BY shelf_life_minutes, name;
```

### Analyze Shelf Life by Object Type

```sql
SELECT
  object_type,
  COUNT(*) as item_count,
  ROUND(AVG(shelf_life_minutes) / 1440, 2) as avg_shelf_life_days,
  ROUND(MIN(shelf_life_minutes) / 1440, 2) as min_shelf_life_days,
  ROUND(MAX(shelf_life_minutes) / 1440, 2) as max_shelf_life_days
FROM `secure-recipe-prod.recipe_v2.effective_items`
WHERE shelf_life_minutes IS NOT NULL
  AND item_status = 'ACTIVE'
GROUP BY object_type
ORDER BY avg_shelf_life_days;
```

### Find Items Requiring Thaw Management

```sql
SELECT
  item_number,
  name,
  object_type,
  frozen_shelf_life_minutes,
  ROUND(frozen_shelf_life_minutes / 1440, 2) as frozen_shelf_life_days,
  thawed_shelf_life_minutes,
  ROUND(thawed_shelf_life_minutes / 1440, 2) as thawed_shelf_life_days,
  slacking_time_minutes,
  ROUND(slacking_time_minutes / 60, 2) as slacking_time_hours
FROM `secure-recipe-prod.recipe_v2.effective_items`
WHERE thawed_shelf_life_minutes IS NOT NULL
  AND item_status = 'ACTIVE'
ORDER BY thawed_shelf_life_minutes;
```

### Get Cooked Shelf Life for Menu Items

```sql
SELECT
  item_number,
  name,
  cooked_shelf_life_minutes,
  ROUND(cooked_shelf_life_minutes / 1440, 2) as cooked_shelf_life_days,
  shelf_life_minutes
FROM `secure-recipe-prod.recipe_v2.effective_items`
WHERE object_type = 'MENU'
  AND item_status = 'ACTIVE'
  AND cooked_shelf_life_minutes IS NOT NULL
ORDER BY cooked_shelf_life_minutes;
```

### Find Items with Slacking Requirements

```sql
SELECT
  item_number,
  name,
  object_type,
  slacking_time_minutes,
  ROUND(slacking_time_minutes / 60, 2) as slacking_time_hours,
  thawed_shelf_life_minutes
FROM `secure-recipe-prod.recipe_v2.effective_items`
WHERE slacking_time_minutes IS NOT NULL
  AND slacking_time_minutes > 0
  AND item_status = 'ACTIVE'
ORDER BY slacking_time_minutes DESC;
```

### Find Items with COB (Close of Business) Expiration

```sql
SELECT
  item_number,
  name,
  object_type,
  shelf_life_minutes,
  cob
FROM `secure-recipe-prod.recipe_v2.effective_items`
WHERE cob = TRUE
  AND item_status = 'ACTIVE'
ORDER BY object_type, name;
```

### Find Items with Reduced Shelf Life Requirements

```sql
SELECT
  item_number,
  name,
  object_type,
  shelf_life_minutes,
  reduced_shelf_life_minutes,
  ROUND(reduced_shelf_life_minutes / 1440, 2) as reduced_shelf_life_days,
  reduced_label_category,
  reduced_label_details
FROM `secure-recipe-prod.recipe_v2.effective_items`
WHERE reduced_shelf_life_minutes IS NOT NULL
  AND item_status = 'ACTIVE'
ORDER BY reduced_label_category, name;
```

### Analyze Reduced Label Categories

```sql
SELECT
  reduced_label_category,
  COUNT(*) as item_count,
  ROUND(AVG(reduced_shelf_life_minutes) / 1440, 2) as avg_reduced_shelf_life_days,
  ROUND(AVG(shelf_life_minutes) / 1440, 2) as avg_default_shelf_life_days
FROM `secure-recipe-prod.recipe_v2.effective_items`
WHERE reduced_shelf_life_minutes IS NOT NULL
  AND item_status = 'ACTIVE'
GROUP BY reduced_label_category
ORDER BY item_count DESC;
```

## Food Safety Measurements (pH and Water Activity)

Items can have pH and Water Activity measurements with acceptable range calculations:

```sql
-- pH measurement fields
ph_ideal_value           FLOAT64   -- Required, must be 0.00-14.00
ph_bias                  FLOAT64   -- Required, default 0.5
ph_governing_value       FLOAT64   -- Optional, default 4.60 when enabled
ph_acceptable_range_min  FLOAT64   -- Auto-calculated
ph_acceptable_range_max  FLOAT64   -- Auto-calculated

-- Water Activity (aw) measurement fields
aw_ideal_value           FLOAT64   -- Required, must be 0.000-1.000
aw_bias                  FLOAT64   -- Required, 3 decimal places
aw_governing_value       FLOAT64   -- Optional, default 0.830 when enabled
aw_acceptable_range_min  FLOAT64   -- Auto-calculated
aw_acceptable_range_max  FLOAT64   -- Auto-calculated
```

### Acceptable Range Calculation Logic

The acceptable range is calculated as:
- **Range Max** = min{(ideal + bias), governing_value, ceiling}
- **Range Min** = max{(ideal - bias), floor}
- **pH**: floor = 0.00, ceiling = 14.00
- **Water Activity**: floor = 0.000, ceiling = 1.000

Examples for pH:
- Ideal=10, Bias=0.8, No governing: Range = 9.2 - 10.8
- Ideal=10, Bias=0.8, Governing=10.3: Range = 9.2 - 10.3
- Ideal=4, Bias=6, Governing=15: Range = 0 - 10
- Ideal=10, Bias=3, Governing=6: ERROR (minimum 7 > governing 6)

## Hot Holding Instructions (88*/70*/41* only)

Hot holding data is at the item version level for packaged items:

```sql
-- Hot holding fields (check schema for exact names)
retherm_appliance        STRING    -- Appliance for reheating
retherm_time             INT64     -- Time for reheating
holding_appliance        STRING    -- Appliance for holding
holding_time             INT64     -- Holding duration
labor_time               INT64     -- Labor time required
batch_limit              INT64     -- Maximum batch size
drop_enabled_brands      ARRAY     -- Brands with auto-drop task generation
instructions             STRING    -- Hot hold instructions text
```

**Note**: Multiple appliance configurations can exist per item. Each retherm appliance has its own tab with distinct settings and images (retherm image, holding image).

## Measurement Trials (88* Items)

Additional measurement fields for 88* items (all optional, 3 decimal places):

| Measurement | Fields | Unit |
|-------------|--------|------|
| Cut Dimension | length_avg, length_sd, width_avg, width_sd, thickness_avg, thickness_sd | inches |
| Piece Weight | weight_avg, weight_sd | grams |
| Texture (Peak Force) | peak_force_avg, peak_force_sd, rate (%), attachment | grams |
| Color | l_avg, l_sd, a_avg, a_sd, b_avg, b_sd | unitless (integer) |
| Viscosity | viscosity_avg, viscosity_sd, spindle, speed, torque, temperature | cP, RPM, F |
| Turbidity | turbidity_avg, turbidity_sd | NTU |
| Density | density_avg, density_sd | g/mL |
| Water Activity | water_activity_avg, water_activity_sd | unitless |
| Moisture | moisture_avg, moisture_sd | % |
| Brix | brix_avg, brix_sd | degrees |
| Powder Size | mesh_size_1, mesh_1_avg, mesh_1_sd, mesh_size_2, mesh_2_avg, mesh_2_sd | % |

**Note**: For 88* items, component item measurements from 1st layer BOM (recipe/ingredient/byproduct) are auto-aggregated.

## Shelf Life Categories

| Shelf Life | Category | Examples |
|------------|----------|----------|
| 1-2 days | Very short | Fresh proteins, prepared salads |
| 3-7 days | Short | Sauces, prepped vegetables |
| 7-14 days | Medium | Pickled items, some condiments |
| 14+ days | Extended | Dry goods, frozen items |

## Food Safety Considerations

When analyzing food science data:

1. **COB flag**: Items with `cob=true` expire at close of business regardless of time remaining
2. **Thaw management**: Items with `thawed_shelf_life_minutes` need FIFO tracking
3. **Slacking dependency**: If `slacking_time_minutes` is set, `thawed_shelf_life_minutes` must also be set
4. **Cooked hold times**: `cooked_shelf_life_minutes` affects hot holding decisions
5. **Reduced shelf life**: Requires `reduced_label_category` for regulatory compliance
6. **Hot holding**: Only applies to 88*/70*/41* object types

## Integration with Pantry

For inventory management with shelf life awareness:

```sql
-- Join shelf life to inventory
SELECT
  ei.item_number,
  ei.name,
  ei.shelf_life_minutes,
  ROUND(ei.shelf_life_minutes / 1440, 2) as shelf_life_days,
  ioh.quantity,
  ioh.lot_number,
  ioh.expiration_date
FROM `secure-recipe-prod.recipe_v2.effective_items` ei
JOIN `wonder-raw-prod.mysql_batch_inventory.inventory_on_hand` ioh
  ON CAST(ei.item_number AS STRING) = ioh.item_number
WHERE ei.shelf_life_minutes IS NOT NULL
  AND ei.shelf_life_minutes <= 4320  -- Short shelf life items (3 days or less)
ORDER BY ei.shelf_life_minutes, ei.name;
```

## Validation Rules

### Required for Publishing

- If `reduced_shelf_life_minutes` is set, `reduced_label_category` must be set
- If `reduced_shelf_life_minutes` is cleared, both label fields must be cleared
- If `slacking_time_minutes` is set, `thawed_shelf_life_minutes` must be set

### Acceptable Range Validation

- pH acceptable range must be within 0-14
- Water Activity acceptable range must be within 0-1
- If min > governing value, calculation returns ERROR

### Downstream Integration

Food science data is provided to Pantry via API:
- Shelf life values
- Reduced-Label Category and Details
- COB flag
- Slacking time (if set, Pantry treats item as slack-eligible)
- Thawed shelf life

---

## Deprecation Notes

### Shelf Life Field Migration

All shelf life fields have migrated from days/hours to **minutes**. The system uses a dual-write pattern during migration, so both deprecated and new fields may contain data.

| Deprecated Field | Replacement Field | Conversion |
|------------------|-------------------|------------|
| `shelf_life_period` | `shelf_life_minutes` | days * 1440 |
| `thawed_shelf_life_days` | `thawed_shelf_life_minutes` | days * 1440 |
| `frozen_shelf_life_days` | `frozen_shelf_life_minutes` | days * 1440 |
| `cooked_shelf_life_days` | `cooked_shelf_life_minutes` | days * 1440 |
| `reduced_shelf_life` | `reduced_shelf_life_minutes` | days * 1440 |
| `slacking_time_hours` | `slacking_time_minutes` | hours * 60 |

> **Deprecated**: The `food_science_range_info` field is deprecated (since MD-12979). Use `food_science_v2` nested structure instead.

> **Deprecated**: The `texture_rate` and `viscosity_torque` measurement fields have been removed from the schema.

### Conversion Helpers

When converting from deprecated fields (if needed for historical data):
- **Days to minutes**: `field_value * 1440`
- **Hours to minutes**: `field_value * 60`
- **Minutes to days**: `field_value / 1440`
- **Minutes to hours**: `field_value / 60`

### Common Thresholds in Minutes

| Human-Readable | Minutes |
|----------------|---------|
| 1 hour | 60 |
| 4 hours | 240 |
| 8 hours | 480 |
| 1 day | 1440 |
| 2 days | 2880 |
| 3 days | 4320 |
| 7 days | 10080 |
| 14 days | 20160 |

---

## Related Documentation

- [nutrition.md](nutrition.md) - Nutrition facts
- [../core/item-master.md](../core/item-master.md) - Full item metadata
- [../cross-system/pantry-integration.md](../cross-system/pantry-integration.md) - Inventory joins

## Source Documentation

- Confluence: [Food Science Card](https://wonder.atlassian.net/wiki/spaces/TECHXIAMEN/pages/4162520992) - Shelf life and measurement trials
- Confluence: [Hot Holding Card](https://wonder.atlassian.net/wiki/spaces/TECHXIAMEN/pages/4210098546) - Hot holding requirements

---

## Code References (Java Codebase)

> **Codebase**: `master-data-management-2`
> **Validated**: 2026-01-28

### Domain Models

- **FoodScienceV2**: `backend/domain-library/src/main/java/app/internalrecipe/item/FoodScienceV2.java`
  - Embedded in ItemVersion.foodScienceV2
  - Key field: `measurements` (List<FoodScienceMeasurement>)

- **FoodScienceMeasurement**: `backend/domain-library/src/main/java/app/internalrecipe/item/FoodScienceMeasurement.java`
  - Comprehensive measurement data for food science
  - Shelf life fields: `shelfLifeMinutes`, `thawedShelfLifeMinutes`, `reducedShelfLifeMinutes`, `frozenShelfLifeMinutes`, `slackingTimeMinutes`, `cookedShelfLifeMinutes`, `cob`
  - Cut dimension: `cutDimensionLengthAVG/SD/Min/Max`, `cutDimensionWidthAVG/SD/Min/Max`, `cutDimensionThicknessAVG/SD/Min/Max`
  - Piece weight: `pieceWeightAVG/SD/Min/Max`
  - Texture: `texturePeakForceAVG/SD/Min/Max`, `textureAttachment`
  - Color (L*a*b*): `colorLAVG/SD/Min/Max`, `colorAAVG/SD/Min/Max`, `colorBAVG/SD/Min/Max`
  - pH: `phAVG/SD/Min/Max`
  - Viscosity: `viscosityAVG/SD/Min/Max`, `viscositySpindle`, `viscositySpeed`, `viscosityTemperature`
  - Turbidity: `turbidityAVG/SD/Min/Max`
  - Density: `densityAVG/SD/Min/Max`
  - Water activity: `waterActivityAVG/SD/Min/Max`
  - Moisture: `moistureAVG/SD/Min/Max`
  - Brix: `brixAVG/SD/Min/Max`
  - Powder: `powderAVG/SD/Min/Max`, `powderMeshOn`, `powderAVG2/SD2/Min2/Max2`, `powderMeshOn2`
  - Nested enums: `TextureAttachmentType`, `ViscositySpindleOption`, `PowderMeshOnOption`
  - **@Deprecated fields (8)**: `shelfLifePeriod`, `thawedShelfLifeDays`, `reducedShelfLifeDays`, `frozenShelfLifeDays`, `slackingTimeHours`, `cookedShelfLifeDays`, `textureRate`, `viscosityTorque`

- **ItemFoodScience**: `backend/domain-library/src/main/java/app/internalrecipe/item/innerclassview/ItemFoodScience.java`
  - pH and Water Activity range calculations
  - Nested classes: `RangeInfo` with `idealValue`, `bias`, `useGoverningValue`, `governingValue`
  - Nested enum: `RangeType` (PH, WATER_ACTIVITY)

- **StorageType**: `backend/domain-library/src/main/java/app/internalrecipe/item/innerclassview/StorageType.java`
  - Storage requirement enum
  - Values: `AMBIENT`, `CHILLED`, `FROZEN`, `MISSING`

### Enums

- **FoodSciencePickCard**: `backend/domain-library/src/main/java/app/internalrecipe/item/FoodSciencePickCard.java`
  - Values: `SHELF_LIFE`, `CUT_DIMENSION`, `PIECE_WEIGHT`, `TEXTURE_PEAK_FORCE`, `COLOR`, `PH`, `VISCOSITY`, `TURBIDITY`, `DENSITY`, `WATER_ACTIVITY`, `MOISTURE`, `BRIX`, `POWDER_SIZE`

- **ReducedShelfLifeLabelCategory**: `backend/domain-library/src/main/java/app/internalrecipe/item/appliancesandequipment/ReducedShelfLifeLabelCategory.java`
  - Values: `BULK_KIT`, `HDR`, `HDR_SUSHI_POKE`, `HDR_OTHER`, `PIZZA`, `PUBLIC_HEALTH_CONTROL`

### Service Layer

- **BOItemFoodScienceService**: `backend/internal-recipe-service/src/main/java/app/internalrecipe/item/service/BOItemFoodScienceService.java`
  - Food science CRUD operations at item level

- **BOItemVersionFoodScienceService**: `backend/internal-recipe-service/src/main/java/app/internalrecipe/itemversion/service/BOItemVersionFoodScienceService.java`
  - Food science operations at item version level

- **FoodScienceSpecExportService**: `backend/master-data-file-service/src/main/java/app/file/word/service/FoodScienceSpecExportService.java`
  - Word document export for food science specifications

### API Endpoints

- **BOGetFoodScienceSpecService**: `backend/internal-recipe-service-interface/src/main/java/app/internalrecipe/api/BOGetFoodScienceSpecService.java`
  - `GET /bo/item/version/:uuid/food-science-spec` - Get food science specifications

### Business Logic Patterns

- **Minutes as Standard**: All shelf life fields use minutes (deprecated day/hour fields still exist for backward compatibility)
- **Acceptable Range Calculation**: Range Max = min{(ideal + bias), governing_value, ceiling}; Range Min = max{(ideal - bias), floor}
- **COB Flag**: Items with cob=true expire at close of business
- **Slacking Dependency**: If slacking_time_minutes is set, thawed_shelf_life_minutes must be set

### @Deprecated Field Summary

| Field | Location | Replacement |
|-------|----------|-------------|
| `shelfLifePeriod` | FoodScienceMeasurement | `shelfLifeMinutes` |
| `thawedShelfLifeDays` | FoodScienceMeasurement | `thawedShelfLifeMinutes` |
| `reducedShelfLifeDays` | FoodScienceMeasurement | `reducedShelfLifeMinutes` |
| `frozenShelfLifeDays` | FoodScienceMeasurement | `frozenShelfLifeMinutes` |
| `slackingTimeHours` | FoodScienceMeasurement | `slackingTimeMinutes` |
| `cookedShelfLifeDays` | FoodScienceMeasurement | `cookedShelfLifeMinutes` |
| `textureRate` | FoodScienceMeasurement | Removed from schema (no longer captured) |
| `viscosityTorque` | FoodScienceMeasurement | Removed from schema (no longer captured) |
