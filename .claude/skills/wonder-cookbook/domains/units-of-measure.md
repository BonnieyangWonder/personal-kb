# Units of Measure - UOM Conversions Across Contexts

Cookbook uses multiple unit of measure (UOM) fields for different contexts: inventory, purchasing, BOM, and ERP systems. Understanding when to use each is critical for accurate calculations.

---

## Unit System Architecture

Cookbook's unit system has two layers:

1. **Global Unit Conversions**: System-wide standard conversions (weight, volume)
2. **Item-Specific Unit Conversions**: Custom conversions defined per item

Both are checked when determining if a conversion path exists.

---

## UOM Fields in item_versions

| Field | Context | Description |
|-------|---------|-------------|
| `inventory_uom` | Inventory tracking | Unit used in Pantry/inventory systems |
| `erp_inventory_uom` | ERP system | Unit used in ERP (NetSuite, etc.) |
| `bom_line_unit` | BOM lines | Unit used in Bills of Materials |
| `stock_uom` | Stock keeping | Unit for physical stock tracking |
| `purchase_unit` | Purchasing | Unit used when ordering from vendors |

---

## Standard Units Reference

Units are synced with the ERP system. The standard unit definitions:

| UnitID | UnitCode | Unit |
|--------|----------|------|
| 1 | oz | ounce |
| 2 | lb | pound |
| 3 | mg | milligram |
| 4 | g | gram |
| 5 | kg | kilogram |
| 6 | tsp | teaspoon |
| 7 | tbsp | tablespoon |
| 8 | floz | fluid ounce |
| 9 | cup | cup |
| 10 | pt | pint |
| 11 | qt | quart |
| 12 | gal | gallon |
| 13 | ml | milliliter |
| 14 | l | liter |

**Note**: Unit codes can only include a-z and A-Z (case insensitive matching).

---

## Global Unit Conversions

These conversions apply system-wide and do NOT need to be defined per item:

### Weight Conversions

| From | To | Factor |
|------|-----|--------|
| 1 kg | g | 1000 |
| 1 g | mg | 1000 |
| 1 lb | oz | 16 |
| 1 oz | g | 28.3495 |

### Volume Conversions

| From | To | Factor |
|------|-----|--------|
| 1 l | ml | 1000 |
| 1 tbsp | tsp | 3 |
| 1 floz | tbsp | 2 |
| 1 cup | floz | 8 |
| 1 pt | cup | 2 |
| 1 qt | pt | 2 |
| 1 gal | qt | 4 |
| 1 floz | ml | 29.5735 |

**Important**: Global conversions can be chained. For example:
- 1 cup = 8 floz = 16 tbsp = 48 tsp

---

## Item-Specific Unit Conversions

Items can define custom conversions that supplement global conversions.

### Unit Conversion Card (per item)

Located on: ingredient items, recipe items, 40 items, packaged items, non-food items

Fields:
- `from_quantity`: Source quantity (positive, 2 decimal places)
- `from_unit`: Source unit code
- `to_quantity`: Target quantity (positive, 2 decimal places)
- `to_unit`: Target unit code

### Conversion Validation Rules

1. **No duplicates**: Cannot have multiple conversions for the same from_unit → to_unit pair
2. **No conflicts with global**: Custom conversions cannot conflict with derived global conversions
3. **Required conversions must exist**: Cannot delete conversions used in calculation workflows

---

## Critical Validation: ea ↔ g/lb Requirement

**For items with BOM unit = ea (each)**, the system requires:
- A conversion from `ea` to `g`, OR
- A conversion from `ea` to `lb`

This can be:
- Direct: `ea → g`
- Indirect via chained conversions: `ea → floz, floz → g`

This applies to:
- Published ingredient versions with BOM UOM or inventory UOM = ea
- 40 items with BOM unit = ea

---

## Common UOM Values

| UOM | Description | Common Usage |
|-----|-------------|--------------|
| `ea` | Each/unit | Discrete items (pouches, packages) |
| `g` | Grams | Small ingredients |
| `kg` | Kilograms | Bulk ingredients |
| `oz` | Ounces | US weight measurements |
| `lb` | Pounds | US bulk weights |
| `ml` | Milliliters | Small liquid volumes |
| `l` | Liters | Bulk liquids |
| `floz` | Fluid ounces | US liquid measurements |
| `gal` | Gallons | US bulk liquids |
| `cs` | Case | Supplier packaging |
| `pk` | Pack | Multi-unit packaging |

---

## OG UOMs

A separate category for "OG UOMs" exists in the Units configuration page. These are:
- Create-only (cannot edit or delete)
- Separate from standard Cookbook units

---

## UOM Reference Tables

### Units Table

```sql
-- Unit definitions
SELECT *
FROM `wonder-recipe-prod.mongo_batch_recipe_v2.units`
LIMIT 100;
```

### Unit Conversions Table

```sql
-- Item-specific conversion factors between units
SELECT *
FROM `wonder-recipe-prod.mongo_batch_recipe_v2.unit_conversions`
WHERE from_unit = 'oz' AND to_unit = 'g';
```

### Global Unit Conversions

Global conversions are built into the system. To see what's available:

```sql
-- Global weight conversions (built-in)
-- 1 kg = 1000 g
-- 1 g = 1000 mg
-- 1 lb = 16 oz
-- 1 oz = 28.3495 g

-- Global volume conversions (built-in)
-- 1 l = 1000 ml
-- 1 tbsp = 3 tsp
-- 1 floz = 2 tbsp
-- 1 cup = 8 floz
-- 1 pt = 2 cup
-- 1 qt = 2 pt
-- 1 gal = 4 qt
-- 1 floz = 29.5735 ml
```

---

## Query Patterns

### Get UOM Fields for an Item

```sql
SELECT
  item_number,
  name,
  inventory_uom,
  erp_inventory_uom,
  stock_uom,
  purchase_unit
FROM `secure-recipe-prod.recipe_v2.item_versions`
WHERE item_number = '8009068'
  AND effective = true
  AND deleted = false;
```

### Find Items with Mismatched UOMs

```sql
SELECT
  item_number,
  name,
  inventory_uom,
  erp_inventory_uom,
  stock_uom
FROM `secure-recipe-prod.recipe_v2.item_versions`
WHERE effective = true
  AND deleted = false
  AND inventory_uom != erp_inventory_uom
  AND inventory_uom IS NOT NULL
  AND erp_inventory_uom IS NOT NULL
LIMIT 100;
```

### Get BOM Line Units

```sql
SELECT
  m.item_number,
  m.name,
  JSON_VALUE(bom_line, '$.item_number') AS component_item,
  JSON_VALUE(bom_line, '$.uom') AS bom_unit,
  SAFE_CAST(JSON_EXTRACT_SCALAR(bom_line, '$.quantity') AS FLOAT64) AS quantity
FROM `secure-recipe-prod.recipe_v2.item_versions` m,
UNNEST(JSON_EXTRACT_ARRAY(m.bom_header, '$.bom_lines')) AS bom_line
WHERE m.effective = true
  AND m.deleted = false
  AND m.item_number = '8009068';
```

### Look Up Conversion Factor

```sql
SELECT
  from_unit,
  to_unit,
  conversion_factor
FROM `wonder-recipe-prod.mongo_batch_recipe_v2.unit_conversions`
WHERE from_unit = 'lb'
  AND to_unit = 'g';
-- Note: This may return no results if using global conversion (1 lb = 16 oz, 1 oz = 28.3495 g)
-- Global equivalent: 1 lb = 453.592 g (16 * 28.3495)
```

### Convert Quantity Between Units

```sql
WITH conversion AS (
  SELECT conversion_factor
  FROM `wonder-recipe-prod.mongo_batch_recipe_v2.unit_conversions`
  WHERE from_unit = 'oz' AND to_unit = 'g'
)
SELECT
  12.5 as quantity_oz,
  12.5 * conversion_factor as quantity_g
FROM conversion;
-- Note: If no item-specific conversion, use global: 1 oz = 28.3495 g
```

### Vendor Item Units

```sql
SELECT
  item_number,
  vendor_name,
  purchase_unit,
  case_unit,
  units_per_case
FROM `wonder-recipe-prod.mongo_batch_recipe_v2.vendor_item_units`
WHERE item_number = '5000001'
LIMIT 10;
```

---

## Inventory Item Conversions

For complex inventory-to-BOM conversions:

```sql
SELECT
  item_number,
  from_unit,
  to_unit,
  conversion_factor,
  context
FROM `wonder-recipe-prod.mongo_batch_recipe_v2.inventory_item_conversions`
WHERE item_number = '5000001';
```

---

## Critical Rules

1. **Always check the UOM context** - inventory_uom vs bom_line_unit can differ
2. **Use conversion tables** for accurate unit conversions
3. **Don't assume 1:1 conversion** - many items have different purchase vs inventory units
4. **Handle NULL UOMs** - not all fields are populated for all items
5. **Include `deleted = false`** when querying item_versions
6. **Check both global AND item-specific conversions** - a conversion may exist in either place
7. **For ea items, ensure ea ↔ g or ea ↔ lb exists** - required for cost/weight calculations

---

## Unit Conversion Impact Areas

When unit conversions are modified, the following calculations may be affected:

| Area | Description |
|------|-------------|
| **Cost calculation** | Item cost = (component usage / yield) * recipe cost |
| **Weight calculation** | Total weight of components |
| **Nutrition calculation** | Per-serving nutrition derived from component quantities |
| **All ingredients rollup** | Ingredient list for labeling |
| **BOM line usage** | Component quantities in parent items |
| **ERP inventory** | Inventory unit ↔ ERP inventory unit |

### Required Unit Conversion Checks

The system validates these conversion paths must exist:

1. **inventory_uom ↔ yield_unit**: For items included in parent recipes
2. **BOM unit ↔ parent component usage unit**: For BOM lines
3. **yield_unit ↔ serving_size_unit**: For nutrition calculations
4. **yield_unit ↔ parent component usage unit**: For cost calculations
5. **serving_size_unit ↔ parent component usage unit**: For nested nutrition
6. **inventory_uom ↔ BOM unit**: For inventory to production conversion

---

## UOM in Cross-System Joins

When joining to Pantry inventory, ensure UOM compatibility:

```sql
-- Check UOM matches between Cookbook and Pantry
SELECT
  iv.item_number,
  iv.name,
  iv.inventory_uom as cookbook_uom,
  ioh.uom as pantry_uom,
  CASE
    WHEN iv.inventory_uom = ioh.uom THEN 'MATCH'
    ELSE 'MISMATCH - needs conversion'
  END as uom_status
FROM `secure-recipe-prod.recipe_v2.item_versions` iv
LEFT JOIN `wonder-raw-prod.mysql_batch_inventory.inventory_on_hand` ioh
  ON CAST(iv.item_number AS STRING) = CAST(ioh.item_number AS STRING)
WHERE iv.effective = true
  AND iv.deleted = false
  AND iv.item_number = '5000001';
```

---

## Common Pitfalls

### Wrong: Assuming only item-specific conversions exist

```sql
-- May return no results even if conversion is possible via global conversions
SELECT * FROM unit_conversions WHERE from_unit = 'oz' AND to_unit = 'g';
```

### Correct: Check global conversions as fallback

Global conversions (1 oz = 28.3495 g) are built-in and don't appear in the unit_conversions table. Always consider:
- Direct item-specific conversion
- Global conversion
- Chained conversions (e.g., oz → lb → kg via multiple global conversions)

### Wrong: Assuming 'ea' items don't need weight conversions

Items with BOM unit = ea still need ea → g or ea → lb conversions for:
- Cost calculations
- Nutrition per-gram calculations
- Weight rollups

---

## Related Documentation

- [../core/bom-components.md](../core/bom-components.md) - BOM structure with units
- [../cross-system/pantry-integration.md](../cross-system/pantry-integration.md) - Inventory integration
- [../reference/datasets-overview.md](../reference/datasets-overview.md) - Dataset locations

---

## Confluence References

- [Unit Conversion](https://wonder.atlassian.net/wiki/spaces/.../pages/4088070287) - Item-level conversion management
- [Unit](https://wonder.atlassian.net/wiki/spaces/.../pages/4213572312) - Unit definitions and global conversions

---

## Code References (Java Codebase)

> **Codebase**: `master-data-management-2`
> **Validated**: 2026-01-28

### Domain Models

- **Unit**: `backend/domain-library/src/main/java/app/internalrecipe/unit/Unit.java`
  - MongoDB collection: `units`
  - Key fields: `code`, audit fields (createdBy, createdTime, updatedBy, updatedTime)
  - Standard cookbook units (g, kg, oz, lb, ml, l, etc.)

- **OGUnit**: `backend/domain-library/src/main/java/app/internalrecipe/unit/OGUnit.java`
  - MongoDB collection: `og_units`
  - Key fields: `code`, audit fields
  - Oracle Grocers unit definitions (create-only, cannot edit/delete)

- **UnitConversion** (Item-level): `backend/domain-library/src/main/java/app/internalrecipe/item/innerclassview/UnitConversion.java`
  - Embedded in ItemVersion.unitConversions
  - Key fields: `fromQuantity`, `fromUnit`, `toQuantity`, `toUnit`
  - Item-specific conversions that supplement global conversions

- **UnitConversion** (Global): `backend/domain-library/src/main/java/app/internalrecipe/vendor/UnitConversion.java`
  - MongoDB collection: `unit_conversions`
  - Key fields: `fromUnitId`, `fromUnitName`, `toUnitId`, `toUnitName`, `factor`, `numerator`, `denominator`, `rounding`, `type`, `source`
  - System-wide unit conversions (GLOBAL type) and item-specific (ITEM_SPECIFIC type)

- **VendorBaseUnit**: `backend/domain-library/src/main/java/app/internalrecipe/vendor/VendorBaseUnit.java`
  - MongoDB collection: `vendor_base_unit`
  - Key fields: `itemNumber`, `itemSku`, `bomLineUnit`, `inventoryUom`, `vendorInventoryUom`, `vendorPackSize`
  - Vendor-specific unit mappings for procurement

### Enums

- **UnitOfMeasure**: `backend/domain-library/src/main/java/app/internalrecipe/vendor/UnitOfMeasure.java`
  - Values: `PIECE`, `G`, `KG`, `LB`, `OZ`, `ML`, `L`, `FL_OZ`, `QT`, `GAL`, `EA` (deprecated)
  - **@Deprecated (1)**: `EA` enum value

- **UnitConversionType**: `backend/domain-library/src/main/java/app/internalrecipe/vendor/constant/UnitConversionType.java`
  - Values: `GLOBAL`, `ITEM_SPECIFIC`
  - Distinguishes system-wide vs item-level conversions

- **UnitOfMeasureEnum**: `backend/domain-library/src/main/java/app/internalrecipe/item/appliancesandequipment/UnitOfMeasureEnum.java`
  - UOM enum for appliance/equipment context

### Service Layer

- **BOUnitService**: `backend/internal-recipe-service/src/main/java/app/internalrecipe/unit/service/BOUnitService.java`
  - Unit CRUD operations

- **BOCheckItemUnitService**: `backend/internal-recipe-service/src/main/java/app/internalrecipe/item/service/BOCheckItemUnitService.java`
  - Validates unit conversion requirements (ea ↔ g/lb check)

- **BOEnableUpdateYieldUnitService**: `backend/internal-recipe-service/src/main/java/app/internalrecipe/item/service/recipe/BOEnableUpdateYieldUnitService.java`
  - Yield unit update validation

- **BOUpdateItemIngredientInventoryUnitService**: `backend/internal-recipe-service/src/main/java/app/internalrecipe/item/service/ingredient/BOUpdateItemIngredientInventoryUnitService.java`
  - Inventory unit updates for ingredients

### API Endpoints

- **BOUnitWebService**: `backend/internal-recipe-service-interface/src/main/java/app/internalrecipe/api/BOUnitWebService.java`
  - `POST /bo/unit` - Create standard unit
  - `POST /bo/og/unit` - Create OG unit
  - `GET /bo/unit` - List standard units
  - `GET /bo/og/unit` - List OG units
  - `PUT /bo/unit/check` - Validate unit code
  - `PUT /bo/og/unit/check` - Validate OG unit code
  - `PUT /bo/stock-uom` - List stock UOMs

### Business Logic Patterns

- **Two-Layer Conversion System**: Global conversions (built-in) + item-specific conversions (user-defined)
- **Conversion Chaining**: System automatically chains conversions (e.g., oz → lb → kg)
- **ea ↔ g/lb Requirement**: Items with BOM unit = ea must have conversion path to g or lb
- **OG Units Immutability**: OG units are create-only, cannot be edited or deleted

### @Deprecated Field Summary

| Field | Location | Replacement |
|-------|----------|-------------|
| `EA` | UnitOfMeasure enum | Use `ea` string directly or other units |
