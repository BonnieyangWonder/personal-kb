# Cost & Pricing - Item Cost and Menu Price Data

Cookbook tracks various cost and pricing fields for items, enabling cost analysis, margin calculations, and pricing decisions.

---

## Essential Filter (ALWAYS USE)

When querying cost data from `item_versions`:

```sql
WHERE effective = true
  AND deleted = false
  AND item_status != 'DORMANT'
```

---

## Cost & Pricing Fields in item_versions

| Field | Type | Description |
|-------|------|-------------|
| `menu_price` | FLOAT64 | Customer-facing selling price (now on ItemVersion, not item_cost_v2) |
| `item_cost_v2` | JSON | **Preferred** cost structure |
| `standard_cost` | FLOAT64 | Standard cost for accounting |
| `landed_cost` | FLOAT64 | Total cost including logistics/shipping |
| `per_bom_unit_cost` | FLOAT64 | Cost per BOM unit |
| `preference_vendor_cost` | FLOAT64 | Preferred vendor pricing |

> **Deprecated**: The `item_cost` field is deprecated. Use `item_cost_v2` instead for all cost queries.

> **Deprecated**: The `item_cost_v2.menu_price` field is deprecated. The `menu_price` field has been relocated to the `ItemVersion` level (accessible directly as `menu_price` on the item_versions table).

---

## BOM Line Cost Fields

Cost data is also available at the BOM line level in `bom_lines`:

| Field | Description |
|-------|-------------|
| `cost` | Component cost per unit |
| `quantity` | Quantity needed |
| `unit` | Unit of measure |

**Total component cost** = `cost * quantity`

---

## Decant Loss and Yield Factors

Decant loss captures the product lost during preparation/transfer (e.g., sauce stuck in packaging). This affects actual ingredient costs.

### Key Fields (Version Level)

| Field | Description |
|-------|-------------|
| `component_usage` | Total amount of component used (in grams) |
| `decant_loss` | Amount lost during decanting (in grams) |
| `usable_product` | Component Usage - Decant Loss (calculated) |
| `scrap_yield` | (Decant Loss / Usable Product) * 100% (calculated) |

### Decant Loss Formulas

```
Usable Product = Component Usage - Decant Loss
Scrap Yield = (Decant Loss / Usable Product) × 100%
Usable Quantity = Net Quantity / (1 + Scrap Yield)
```

**Example:**
- Net weight: 13,200g (BOM quantity)
- Usable weight: 8,100g
- Scrap yield: 62.96%
- 1 EA can serve: 8,100g / 17g per serving = 476 servings

### Impact on Cost Calculations

1. **Stockable-to-Consumable Conversion**: Cookbook returns the **usable quantity** (not net quantity) in stockable-consumable mappings
2. **Parent Item Costs**: When scrap yield is updated, costs of ALL parent usage items are auto-recalculated up the hierarchy
3. **Transformed BOM**: Returns consumable item quantity WITHOUT considering decant loss
4. **Consumable Item Usage**: `Usable qty = Round(Stockable usage qty × (1 + Scrap yield) × component pack qty)`

### 40 Model Specifics

For WSKU 41 & 40 item linkages:
- HDR consumable quantity in the linkage is the **usable amount**
- 88* items and vendor SKUs have their own decant loss data
- A single pack of linked 88*/vendor SKU fulfills the same usable amount of the WSKU41

---

## Production Cost Fields (88* Items)

| Field | Default | Description |
|-------|---------|-------------|
| `production_offset_days` | 0 | Days offset for scheduling production |
| `production_offset_reason` | NULL | Explanation for offset (up to 300 chars) |
| `production_lead_time` | 7 days | Lead time for production planning |
| `delivery_offset_days` | 0 | Days offset for delivery scheduling |
| `pack_size` | Derived | Auto-generated from sub item's BOM usage qty |

### Pack Size Derivation

Pack size is auto-calculated from the BOM:
- Only when BOM has exactly ONE food item
- `pack_size` = usage quantity of that food component
- If multiple food items in BOM, pack_size = NULL

**Example:** 88019021 with single food component at 1 unit = pack_size of 1

---

## Resource Type Cost Impact

When a non-food item's `resource_type` changes (e.g., REUSABLE to Consumable or NULL), the system **recalculates costs for all parent items** that use this component in their BOM.

---

## Query Patterns

### Get Menu Price and Cost for Items

```sql
SELECT
  item_number,
  name,
  menu_price,
  standard_cost,
  landed_cost,
  CASE
    WHEN menu_price > 0 THEN ROUND((menu_price - standard_cost) / menu_price * 100, 2)
    ELSE NULL
  END as margin_pct
FROM `secure-recipe-prod.recipe_v2.item_versions`
WHERE effective = true
  AND deleted = false
  AND object_type = 'MENU'
  AND item_status = 'ACTIVE'
  AND menu_price IS NOT NULL
ORDER BY menu_price DESC;
```

### Calculate Total BOM Cost for a Menu Item

```sql
SELECT
  m.item_number,
  m.name,
  m.menu_price,
  SUM(SAFE_CAST(JSON_EXTRACT_SCALAR(bom_line, '$.cost') AS FLOAT64) *
      SAFE_CAST(JSON_EXTRACT_SCALAR(bom_line, '$.quantity') AS FLOAT64)) as total_bom_cost
FROM `secure-recipe-prod.recipe_v2.item_versions` m,
UNNEST(JSON_EXTRACT_ARRAY(m.bom_header, '$.bom_lines')) AS bom_line
WHERE m.effective = true
  AND m.deleted = false
  AND m.item_number = '8009068'
GROUP BY m.item_number, m.name, m.menu_price;
```

### Using Separate BOM Tables for Cost Analysis

```sql
SELECT
  bh.item_number as menu_item_id,
  ei.name as menu_item_name,
  ei.menu_price,
  SUM(bl.cost) as total_component_cost,
  ei.menu_price - SUM(bl.cost) as gross_margin
FROM `secure-recipe-prod.recipe_v2.bom_headers` bh
INNER JOIN `secure-recipe-prod.recipe_v2.bom_lines` bl
  ON bh.item_number = bl.bom_header_item_number
LEFT JOIN `secure-recipe-prod.recipe_v2.effective_items` ei
  ON bh.item_number = CAST(ei.item_number AS STRING)
  AND ei.deleted = false
WHERE bh.is_active = true
  AND bh.item_number = '8009068'
  AND CURRENT_TIMESTAMP() BETWEEN TIMESTAMP(bl.service_start_time) AND TIMESTAMP(bl.service_end_time)
GROUP BY bh.item_number, ei.name, ei.menu_price;
```

### Find High-Margin Menu Items

```sql
SELECT
  item_number,
  name,
  menu_price,
  standard_cost,
  ROUND((menu_price - standard_cost) / menu_price * 100, 2) as margin_pct
FROM `secure-recipe-prod.recipe_v2.item_versions`
WHERE effective = true
  AND deleted = false
  AND object_type = 'MENU'
  AND item_status = 'ACTIVE'
  AND menu_price > 0
  AND standard_cost > 0
ORDER BY margin_pct DESC
LIMIT 20;
```

### Extract item_cost JSON Fields

```sql
SELECT
  item_number,
  name,
  JSON_EXTRACT_SCALAR(item_cost, '$.total_cost') as total_cost,
  JSON_EXTRACT_SCALAR(item_cost, '$.food_cost') as food_cost,
  JSON_EXTRACT_SCALAR(item_cost, '$.labor_cost') as labor_cost
FROM `secure-recipe-prod.recipe_v2.item_versions`
WHERE effective = true
  AND deleted = false
  AND item_cost IS NOT NULL
  AND object_type = 'MENU'
LIMIT 100;
```

---

## Cost Change Tracking

For tracking cost changes over time:

```sql
SELECT *
FROM `wonder-recipe-prod.mongo_batch_recipe_v2.transfer_cost_change_log`
WHERE item_number = '8009068'
ORDER BY created_time DESC
LIMIT 10;
```

For expanded customization costs:

```sql
SELECT *
FROM `wonder-recipe-prod.mongo_batch_recipe_v2.expanded_item_version_customization_costs`
WHERE item_number = '8009068';
```

---

## Query Patterns for Decant Loss

### Find Items with Scrap Yield

```sql
SELECT
  item_number,
  name,
  JSON_EXTRACT_SCALAR(decant_loss, '$.component_usage') as component_usage_g,
  JSON_EXTRACT_SCALAR(decant_loss, '$.decant_loss') as decant_loss_g,
  JSON_EXTRACT_SCALAR(decant_loss, '$.usable_product') as usable_product_g,
  JSON_EXTRACT_SCALAR(decant_loss, '$.scrap_yield') as scrap_yield_pct
FROM `secure-recipe-prod.recipe_v2.item_versions`
WHERE effective = true
  AND deleted = false
  AND decant_loss IS NOT NULL
  AND object_type IN ('PACKAGED', 'HDR_RECIPE');
```

### Calculate Effective Cost with Scrap Yield

```sql
-- Effective cost increases due to waste
SELECT
  item_number,
  name,
  standard_cost,
  SAFE_CAST(JSON_EXTRACT_SCALAR(decant_loss, '$.scrap_yield') AS FLOAT64) as scrap_yield_pct,
  standard_cost * (1 + SAFE_CAST(JSON_EXTRACT_SCALAR(decant_loss, '$.scrap_yield') AS FLOAT64) / 100) as effective_cost
FROM `secure-recipe-prod.recipe_v2.item_versions`
WHERE effective = true
  AND deleted = false
  AND decant_loss IS NOT NULL
  AND standard_cost IS NOT NULL;
```

---

## Critical Rules

1. **Always include `deleted = false`** in cost queries
2. **Use SAFE_CAST** when extracting numeric values from JSON
3. **Handle NULL values** - not all items have pricing data
4. **Filter by service window** when using BOM tables for cost calculation
5. **Always use `item_cost_v2`** - the `item_cost` field is deprecated
6. **Access menu_price directly** - use `menu_price` on item_versions, not from item_cost_v2
7. **Account for scrap yield** - actual ingredient costs are higher than net costs due to decant loss
8. **Parent cost propagation** - scrap yield updates trigger cascade recalculation up the item hierarchy

---

## Deprecation Notes

### item_cost vs item_cost_v2

> **Deprecated**: The `item_cost` field is deprecated. Always use `item_cost_v2` for cost data.

The `item_cost` field contains legacy cost data and should not be used in new queries. The `item_cost_v2` field contains the current cost model.

### menu_price Location

> **Deprecated**: The `menu_price` field inside `item_cost_v2` is deprecated.

The `menu_price` has been relocated to the `ItemVersion` level. Access it directly as `item_versions.menu_price` or `effective_items.menu_price`.

```sql
-- Correct: Access menu_price directly on item_versions
SELECT item_number, name, menu_price
FROM `secure-recipe-prod.recipe_v2.item_versions`
WHERE effective = true AND deleted = false;

-- Deprecated: Don't extract menu_price from item_cost_v2
-- JSON_EXTRACT_SCALAR(item_cost_v2, '$.menu_price')  -- AVOID
```

### Transfer Cost Fields

> **Deprecated**: The `at_scale_transfer_cost` and `current_state_transfer_cost` fields are deprecated.

These fields are still being written for backward compatibility but should not be used in new queries.

---

## Related Documentation

- [../core/bom-components.md](../core/bom-components.md) - BOM structure and cost fields
- [../core/item-master.md](../core/item-master.md) - Item master data
- [../reference/datasets-overview.md](../reference/datasets-overview.md) - Dataset locations

## Source References

- Confluence: "Decant Loss" (Page 4181721341) - Decant/waste loss factors and formulas
- Confluence: "Production Card" (Page 4188012871) - Production costs and scaling

---

## Code References (Java Codebase)

> **Codebase**: `master-data-management-2`
> **Validated**: 2026-01-28

### Domain Models

- **ItemCostV2**: `backend/domain-library/src/main/java/app/internalrecipe/item/innerclassview/ItemCostV2.java`
  - Primary cost structure embedded in ItemVersion.itemCostV2
  - Key fields: `totalCost`, `foodCost`, `nonFoodCost`, `internalPackagingCost`, `guestPackagingCost`, `componentCost`
  - Related: `itemCostSources` (List<ItemCostSource>), `bomLineCosts` (List<BOMLineCost>), `errors`
  - Nested classes: `Error`, `ItemVersion`, `BOMLineCost`
  - **@Deprecated fields (2)**: `menuPrice` → relocated to ItemVersion level; `ErrorType.MISS_STANDARD_COST` → deprecated enum value

- **TransferCost**: `backend/domain-library/src/main/java/app/internalrecipe/item/TransferCost.java`
  - Transfer pricing between facilities
  - Key fields: `ingredients`, `packaging`, `guestPackaging`, `directLabor`, `outboundAndFreight`, `feeRate`, `feeCost`, `totalTransferPriceCost`, `other`
  - Nested enum: `ErrorType` with MISSING_* values for validation

- **LandedCost**: `backend/domain-library/src/main/java/app/internalrecipe/item/landedcost/LandedCost.java`
  - Total cost including logistics and labor
  - Key fields: `directHourlyLaborCostPerUnit`, `directLaborCookingCostPerUnit`, `directLaborAssemblyCostPerUnit`, `indirectHourlyLaborCostPerUnit`, `salaryCostPerUnit`, `rentOpexCostPerUnit`, `obfCostPerUnit`, `landedCost`, `unit`

- **StandardCost**: `backend/domain-library/src/main/java/app/internalrecipe/item/innerclassview/StandardCost.java`
  - Standard cost for accounting
  - Key fields: `standardCost`, `unitOfMeasure`, `priceFrom`, `unitFrom`, `activationDate`, `isStandardCost`

- **PerBOMUnitCost**: `backend/domain-library/src/main/java/app/internalrecipe/item/innerclassview/PerBOMUnitCost.java`
  - Cost per BOM unit
  - Fields: `cost`

- **PreferenceVendorCost**: `backend/domain-library/src/main/java/app/internalrecipe/item/innerclassview/PreferenceVendorCost.java`
  - Preferred vendor pricing
  - Key fields: `cost`, `vendorSku`, `updatedTime`

- **DecantLoss**: `backend/domain-library/src/main/java/app/internalrecipe/item/innerclassview/DecantLoss.java`
  - Decant/waste loss factors
  - Key fields: `componentUsage`, `decantLoss`, `usableProduct`, `scrapYield`
  - Formulas documented in skill match Java implementation

- **TransferCostChangeLog**: `backend/domain-library/src/main/java/app/internalrecipe/item/TransferCostChangeLog.java`
  - MongoDB collection: `transfer_cost_change_log`
  - Audit trail for transfer cost changes with old/new values

- **ExpandedItemVersionCustomizationCost**: `backend/domain-library/src/main/java/app/internalrecipe/cost/ExpandedItemVersionCustomizationCost.java`
  - MongoDB collection: `expanded_item_version_customization_costs`
  - Customization cost tracking for menu items

### Enums

- **ItemCostSource**: `backend/domain-library/src/main/java/app/internalrecipe/item/innerclassview/ItemCostSource.java`
  - Values: `STANDARD_COST`, `USING_LATEST_INVOICE_COST`, `PREFERENCE_VENDOR_COST`, `ESTIMATE_COST`

### Service Layer

- **BOItemStandardCostServiceV2**: `backend/internal-recipe-service/src/main/java/app/internalrecipe/item/service/BOItemStandardCostServiceV2.java`
  - Standard cost synchronization and calculation

- **BOUpdateTransferCurrentCostService**: `backend/internal-recipe-service/src/main/java/app/internalrecipe/item/service/BOUpdateTransferCurrentCostService.java`
  - Transfer cost update operations

- **ExpandedItemVersionCustomizationCostService**: `backend/master-data-non-critical-business-service/src/main/java/app/noncritical/expandedcost/service/ExpandedItemVersionCustomizationCostService.java`
  - Customization cost expansion and calculation

- **TransferCostChangeObserver**: `backend/internal-recipe-service/src/main/java/app/internalrecipe/changestream/itemversionchange/observers/TransferCostChangeObserver.java`
  - Change stream observer for transfer cost updates

- **UpdateCurrentTransferCostObserver**: `backend/internal-recipe-service/src/main/java/app/internalrecipe/changestream/itemversionchange/observers/UpdateCurrentTransferCostObserver.java`
  - Change stream observer for current transfer cost

### API Endpoints

- **BOItemVersionCostWebService**: `backend/internal-recipe-service-interface/src/main/java/app/internalrecipe/api/BOItemVersionCostWebService.java`
  - `PUT /bo/item/version/:uuid/cost/calculate` - Calculate cost for item version
  - `PUT /bo/item/version/cost/batch-calculate` - Batch cost calculation

- **BOItemStandardCostWebService**: `backend/internal-recipe-service-interface/src/main/java/app/internalrecipe/api/BOItemStandardCostWebService.java`
  - `PUT /bo/v2/item/version/standard-cost-v2/sync` - Sync standard cost V2

- **BOItemLandedCostWebService**: `backend/internal-recipe-service-interface/src/main/java/app/internalrecipe/api/BOItemLandedCostWebService.java`
  - `PUT /item/version/landed-cost/bulk-edit` - Bulk edit landed costs
  - `PUT /landed-cost/log/back-up` - Backup landed cost logs

### Business Logic Patterns

- **Cost Hierarchy**: ItemCostV2 contains totalCost = foodCost + nonFoodCost, where nonFoodCost = internalPackagingCost + guestPackagingCost
- **Cost Source Tracking**: Each cost has associated `ItemCostSource` enum indicating origin (standard cost, invoice, vendor preference, estimate)
- **BOM Line Costs**: Individual component costs tracked in `bomLineCosts` list
- **Error Tracking**: Cost calculation errors captured in `errors` list with type and affected item versions
- **Decant Loss Impact**: scrapYield affects usable quantity calculations up the item hierarchy

### @Deprecated Field Summary

| Field | Location | Replacement |
|-------|----------|-------------|
| `menuPrice` | ItemCostV2 | Use `ItemVersion.menuPrice` directly |
| `ErrorType.MISS_STANDARD_COST` | ItemCostV2.ErrorType | Deprecated enum value |
