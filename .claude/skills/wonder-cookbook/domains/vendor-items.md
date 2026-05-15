# Vendor Items - External Vendor SKU Linkage

Vendor items link Cookbook ingredient/non-food items to external vendor products (Order Grid). This linkage enables procurement, cost calculation, and nutrition sourcing from supplier data.

---

## Essential Filter (ALWAYS USE)

When querying vendor items:

```sql
-- For vendor_items (linkage table)
WHERE status = 'ACTIVE'

-- For vendor_items_v2 (detailed vendor SKU data)
WHERE status = 'ACTIVE'
  AND og_active = true
```

---

## Core Tables

### vendor_items (Item-to-SKU Linkage)

Links cookbook items to vendor SKUs. The `item` JSON field contains the linkage details.

**Primary Project**: `wonder-recipe-prod.recipe_v2.vendor_items`

| Field | Type | Description |
|-------|------|-------------|
| `_id` | STRING | Unique vendor item record ID |
| `vendor_sku` | STRING | Vendor SKU code |
| `vendor_sku_name` | STRING | Vendor SKU name |
| `vendor_id` | STRING | Reference to vendor record |
| `status` | STRING | `ACTIVE` or `INACTIVE` |
| `item` | JSON | Linked cookbook item details |
| `trades` | STRING | Trading/purchasing info |
| `created_time` | DATETIME | Creation timestamp |
| `updated_time` | DATETIME | Last update timestamp |

#### Item JSON Structure

The `item` field contains the linkage to cookbook items:

```json
{
  "id": "uuid",
  "item_number": "5074001",
  "object_type": "INGREDIENT",
  "object_sub_type": null,
  "is_primary_sku": true,
  "primary_sku_source": "DEFAULT",
  "stock_or_custom": null
}
```

| JSON Field | Description |
|------------|-------------|
| `id` | UUID of the linked item version |
| `item_number` | Cookbook item number (50* = ingredient, 60* = non-food) |
| `object_type` | `INGREDIENT` or `NON_FOOD` |
| `is_primary_sku` | Whether this is the preferred vendor SKU |
| `primary_sku_source` | `DEFAULT`, `SC_APPROVED`, or `NULL` |

---

### vendor_items_v2 (Detailed Vendor SKU Data)

Contains detailed vendor SKU information synced from Order Grid (OG).

**Primary Project**: `wonder-recipe-prod.recipe_v2.vendor_items_v2`

| Field | Type | Description |
|-------|------|-------------|
| `_id` | STRING | Unique vendor item ID |
| `vendor_sku` | STRING | Vendor SKU code |
| `external_sku_name` | STRING | External vendor name |
| `og_vendor_item_name` | STRING | Order Grid item name |
| `og_code` | STRING | Order Grid code |
| `og_partner` | STRING | Partner/vendor code in OG |
| `og_partner_name` | STRING | Partner/vendor name |
| `og_brand` | STRING | Product brand |
| `og_type` | STRING | Item type in OG |
| `og_active` | BOOLEAN | Active in Order Grid |
| `og_unpurchasable` | BOOLEAN | Cannot be purchased |
| `status` | STRING | `ACTIVE` or `INACTIVE` |
| `discontinued_reason` | STRING | `EXTERNAL` or `INTERNAL` |

#### UOM Fields

| Field | Type | Description |
|-------|------|-------------|
| `inventory_uom` | STRING | Base inventory unit (e.g., `EA`, `LB`, `GAL`) |
| `inventory_uom_qty` | FLOAT | Quantity per inventory unit |
| `purchase_uom` | STRING | Unit for purchasing (e.g., `CS`) |
| `stock_uom` | STRING | Unit for stocking |
| `pack_size` | FLOAT | Pack size (units per case) |
| `uoms` | STRING | JSON array of all UOM conversions |

#### Pricing Fields

| Field | Type | Description |
|-------|------|-------------|
| `price` | STRING | Current price (JSON or string) |
| `price_per_base_unit` | STRING | Price per base unit |
| `price_per_base_unit_double` | FLOAT | Numeric price per base unit |

#### Storage Fields

| Field | Type | Description |
|-------|------|-------------|
| `storage_type` | STRING | `AMBIENT`, `FROZEN`, or `CHILLED` |
| `receiving_temperature` | STRING | Required receiving temp |

#### Nutrition Fields

| Field | Type | Description |
|-------|------|-------------|
| `nutrition_fact` | STRING | Nutrition data (JSON) |
| `nutrition_reviewed_info` | STRING | Nutrition review status |
| `allergens_reviewed_info` | STRING | Allergen review status |
| `dietary_tag_info` | STRING | Dietary tags |
| `ingredient_statement` | STRING | Ingredient list text |

---

## Key Concepts

### Primary SKU Preference

When an ingredient has multiple linked vendor SKUs:
- **Preference ranking** (1-10): Lower number = higher preference
- **is_primary_sku**: Indicates the currently preferred vendor SKU
- **primary_sku_source**: How preference was determined
  - `DEFAULT`: Auto-set when only one SKU linked
  - `SC_APPROVED`: Approved by Supply Chain team
  - `NULL`: Manually set or multiple SKUs without explicit preference

### UOM Validation Rules

From the Confluence documentation:
1. Ingredient inventory UOM must match vendor SKU base UOM category
2. For non-food items: base UOM must be `EA` with qty=1
3. UOM categories:
   - **Mass**: oz, kg, g, lb, mg
   - **Volume**: ml, gal, l, floz, pt, tbsp, tsp, cup, fl.oz, qt
   - **Count**: EA, CS

### Nutrition Review Status

Vendor SKU nutrition data has review tracking:

```json
{
  "has_reviewed": true,
  "reviewed_time": "2023-08-31T13:04:51.694000",
  "reviewed_by": "Nicole Sayre",
  "reviewed_user_id": "uuid",
  "is_back_filled": true
}
```

- `has_reviewed`: Whether nutrition has been reviewed
- `is_back_filled`: Whether data was back-filled vs manually entered

### Discontinued Reasons

| Value | Description |
|-------|-------------|
| `EXTERNAL` | Vendor discontinued the product |
| `INTERNAL` | Wonder discontinued usage |

---

## Query Patterns

### Get Vendor SKUs Linked to an Ingredient

```sql
SELECT
  vi._id,
  vi.vendor_sku,
  vi.vendor_sku_name,
  JSON_VALUE(vi.item, '$.item_number') as linked_item_number,
  JSON_VALUE(vi.item, '$.is_primary_sku') as is_primary_sku,
  JSON_VALUE(vi.item, '$.primary_sku_source') as primary_sku_source,
  vi.status
FROM `wonder-recipe-prod.recipe_v2.vendor_items` vi
WHERE JSON_VALUE(vi.item, '$.item_number') = '5074001'
  AND vi.status = 'ACTIVE';
```

### Get Detailed Vendor SKU Information

```sql
SELECT
  v2.vendor_sku,
  v2.og_vendor_item_name,
  v2.og_partner_name,
  v2.inventory_uom,
  v2.pack_size,
  v2.storage_type,
  v2.price_per_base_unit_double
FROM `wonder-recipe-prod.recipe_v2.vendor_items_v2` v2
WHERE v2.vendor_sku = 'OILT3'
  AND v2.status = 'ACTIVE'
  AND v2.og_active = true;
```

### Join Vendor Items to Ingredient Details

```sql
SELECT
  ei.item_number,
  ei.name as ingredient_name,
  vi.vendor_sku,
  vi.vendor_sku_name,
  v2.og_partner_name as vendor_name,
  v2.inventory_uom,
  v2.price_per_base_unit_double,
  JSON_VALUE(vi.item, '$.is_primary_sku') as is_primary
FROM `wonder-recipe-prod.recipe_v2.effective_items` ei
JOIN `wonder-recipe-prod.recipe_v2.vendor_items` vi
  ON CAST(ei.item_number AS STRING) = JSON_VALUE(vi.item, '$.item_number')
LEFT JOIN `wonder-recipe-prod.recipe_v2.vendor_items_v2` v2
  ON vi.vendor_sku = v2.vendor_sku
WHERE ei.object_type = 'INGREDIENT'
  AND ei.deleted = false
  AND ei.item_status = 'ACTIVE'
  AND vi.status = 'ACTIVE'
LIMIT 20;
```

### Find Ingredients with Multiple Vendor SKUs

```sql
SELECT
  JSON_VALUE(vi.item, '$.item_number') as item_number,
  COUNT(*) as sku_count,
  STRING_AGG(vi.vendor_sku, ', ') as vendor_skus
FROM `wonder-recipe-prod.recipe_v2.vendor_items` vi
WHERE vi.status = 'ACTIVE'
  AND vi.item IS NOT NULL
GROUP BY JSON_VALUE(vi.item, '$.item_number')
HAVING COUNT(*) > 1
ORDER BY sku_count DESC
LIMIT 20;
```

### Get Vendor SKU Nutrition Facts

```sql
SELECT
  v2.vendor_sku,
  v2.og_vendor_item_name,
  JSON_VALUE(v2.nutrition_fact, '$.calories_k_cal') as calories,
  JSON_VALUE(v2.nutrition_fact, '$.protein_g') as protein_g,
  JSON_VALUE(v2.nutrition_fact, '$.total_fat_g') as fat_g,
  JSON_VALUE(v2.nutrition_fact, '$.sodium_mg') as sodium_mg,
  JSON_VALUE(v2.nutrition_reviewed_info, '$.has_reviewed') as nutrition_reviewed
FROM `wonder-recipe-prod.recipe_v2.vendor_items_v2` v2
WHERE v2.nutrition_fact IS NOT NULL
  AND v2.status = 'ACTIVE'
LIMIT 20;
```

### Find Vendor SKUs by Storage Type

```sql
SELECT
  v2.vendor_sku,
  v2.og_vendor_item_name,
  v2.og_partner_name,
  v2.storage_type,
  v2.pack_size
FROM `wonder-recipe-prod.recipe_v2.vendor_items_v2` v2
WHERE v2.storage_type = 'FROZEN'
  AND v2.status = 'ACTIVE'
  AND v2.og_active = true
ORDER BY v2.og_vendor_item_name
LIMIT 50;
```

### Find Unlinked Vendor SKUs

```sql
SELECT
  v2.vendor_sku,
  v2.og_vendor_item_name,
  v2.og_partner_name,
  v2.inventory_uom
FROM `wonder-recipe-prod.recipe_v2.vendor_items_v2` v2
LEFT JOIN `wonder-recipe-prod.recipe_v2.vendor_items` vi
  ON v2.vendor_sku = vi.vendor_sku
WHERE vi._id IS NULL
  AND v2.status = 'ACTIVE'
  AND v2.og_active = true
LIMIT 50;
```

### Count Vendor SKUs by Vendor

```sql
SELECT
  v2.og_partner_name as vendor_name,
  COUNT(*) as sku_count,
  SUM(CASE WHEN v2.storage_type = 'FROZEN' THEN 1 ELSE 0 END) as frozen_count,
  SUM(CASE WHEN v2.storage_type = 'CHILLED' THEN 1 ELSE 0 END) as chilled_count,
  SUM(CASE WHEN v2.storage_type = 'AMBIENT' THEN 1 ELSE 0 END) as ambient_count
FROM `wonder-recipe-prod.recipe_v2.vendor_items_v2` v2
WHERE v2.status = 'ACTIVE'
  AND v2.og_active = true
  AND v2.og_partner_name IS NOT NULL
GROUP BY v2.og_partner_name
ORDER BY sku_count DESC
LIMIT 20;
```

### Get Vendor SKU UOM Hierarchy

Extract the full UOM (Unit of Measure) hierarchy for a vendor SKU:

```sql
SELECT
  vi.og_brand,
  vi.og_partner AS vendor,
  vi.og_vendor_item_name AS vendor_name,
  vi.vendor_sku,

  -- Flattened UOM fields
  JSON_EXTRACT_SCALAR(uom_item, '$.pack_code') AS pack_code,
  CAST(JSON_EXTRACT_SCALAR(uom_item, '$.pack_size') AS FLOAT64) AS pack_size,
  JSON_EXTRACT_SCALAR(uom_item, '$.barcode') AS barcode,
  JSON_EXTRACT_SCALAR(uom_item, '$.description') AS description,
  CAST(JSON_EXTRACT_SCALAR(uom_item, '$.length') AS FLOAT64) AS length,
  CAST(JSON_EXTRACT_SCALAR(uom_item, '$.width') AS FLOAT64) AS width,
  CAST(JSON_EXTRACT_SCALAR(uom_item, '$.height') AS FLOAT64) AS height,
  CAST(JSON_EXTRACT_SCALAR(uom_item, '$.weight') AS FLOAT64) AS weight,
  CAST(JSON_EXTRACT_SCALAR(uom_item, '$.purchase_default') AS BOOL) AS purchase_default,
  CAST(JSON_EXTRACT_SCALAR(uom_item, '$.pick_by') AS BOOL) AS pick_by

FROM `wonder-recipe-prod.mongo_batch_recipe_v2.vendor_items_v2` vi,
  UNNEST(JSON_EXTRACT_ARRAY(vi.uoms)) AS uom_item
WHERE vi.vendor_sku = 'KSF-CHARC'  -- Replace with your vendor SKU
  AND vi.og_active = true
  AND vi.uoms IS NOT NULL
  AND JSON_EXTRACT_ARRAY(vi.uoms) IS NOT NULL
ORDER BY pack_size;
```

### Get Item with All Mapped Vendors

Join cookbook items to their mapped vendor SKUs with complete vendor information:

```sql
SELECT
  iv.item_number,
  iv.name,
  iv.inventory_uom,
  STRING_AGG(CAST(sm.vendor_sku AS STRING), '; ' ORDER BY iv.item_number) AS mapped_vendor_sku,
  STRING_AGG(CAST(vi2.inventory_uom AS STRING), '; ' ORDER BY iv.item_number) AS mapped_vendor_inventory_uom,
  STRING_AGG(CAST(sm.vendor_sku_name AS STRING), '; ' ORDER BY iv.item_number) AS mapped_vendor_name,
  COUNT(*) AS mapping_count
FROM `secure-recipe-prod.recipe_v2.item_versions` iv
LEFT JOIN `wonder-recipe-prod.mongo_batch_recipe_v2.sku_mappings` sm
  ON sm.item_number = iv.item_number
LEFT JOIN `wonder-recipe-prod.recipe_v2.vendor_items_v2` vi2
  ON sm.vendor_sku = vi2.vendor_sku
WHERE iv.effective = true
  AND iv.deleted = false
GROUP BY iv.item_number, iv.name, iv.inventory_uom
HAVING mapped_vendor_sku IS NOT NULL
  AND mapped_vendor_inventory_uom IS NOT NULL
  AND mapped_vendor_name IS NOT NULL;
```

---

## Critical Rules

1. **Always filter by status** - Use `status = 'ACTIVE'` for both tables
2. **Filter og_active** - In `vendor_items_v2`, also filter `og_active = true`
3. **Use JSON_VALUE for item field** - The `item` column is JSON, extract fields with `JSON_VALUE()`
4. **Join on vendor_sku** - Link `vendor_items` to `vendor_items_v2` via `vendor_sku`
5. **Primary SKU matters** - Use `is_primary_sku = 'true'` when you need the preferred vendor
6. **UOM compatibility** - Ingredient inventory UOM must match vendor SKU base UOM category
7. **Nutrition review status** - Check `nutrition_reviewed_info.has_reviewed` before trusting nutrition data
8. **Project is wonder-recipe-prod** - Unlike other cookbook tables, vendor tables are NOT in `secure-recipe-prod`
9. **Avoid deprecated fields** - See Deprecation Notes section for fields to avoid

---

## Table Statistics

| Table | Row Count | Description |
|-------|-----------|-------------|
| `vendor_items` | ~5,500 | Item-to-SKU linkages |
| `vendor_items_v2` | ~6,400 | Detailed vendor SKU data |

---

## Deprecation Notes

### Vendor.java Class Deprecation

> **Deprecated**: The entire `Vendor.java` class is deprecated. Use `VendorV2` for vendor data.

The `vendor_id` field references the deprecated Vendor model. New implementations should use the vendor data from `vendor_items_v2` directly.

### SKUMapping Deprecated Fields

The following fields in SKUMapping/sku_mappings are deprecated:

| Deprecated Field | Replacement |
|------------------|-------------|
| `vendor_id` | Use vendor data from `vendor_items_v2` |
| `vendor_item_id` | Use `vendor_sku` to join to `vendor_items_v2` |
| `vendor_sku_name` | Use `og_vendor_item_name` from `vendor_items_v2` |

```sql
-- Deprecated pattern (avoid):
SELECT sm.vendor_sku_name FROM sku_mappings sm;

-- Preferred pattern:
SELECT vi2.og_vendor_item_name
FROM sku_mappings sm
JOIN vendor_items_v2 vi2 ON sm.vendor_sku = vi2.vendor_sku;
```

### UOM Deprecated Fields

The following fields in the UOM structure are deprecated:

| Deprecated Field | Notes |
|------------------|-------|
| `barcode` | Still present but deprecated |
| `price` | Use `purchase_uom_price` instead |
| `currency` | Still present but deprecated |

### UnitOfMeasure.EA Deprecation

> **Deprecated**: The `EA` unit of measure value is deprecated. Use `PIECE` instead.

---

## Related Documentation

- [../core/item-master.md](../core/item-master.md) - Ingredient/non-food items
- [nutrition.md](nutrition.md) - How vendor SKU nutrition flows to ingredients
- [cost-pricing.md](cost-pricing.md) - How vendor pricing affects item costs
- [units-of-measure.md](units-of-measure.md) - UOM conversions and compatibility

## Source References

- Confluence: "Vendor Items Card" (Page 4176675278) - Vendor item card UI and validation rules
- Confluence: "Vendor Items" (Page 4176740738) - Vendor items overview

---

## Code References (Java Codebase)

> **Codebase**: `master-data-management-2`
> **Validated**: 2026-01-28

### Domain Models

- **Vendor** (DEPRECATED): `backend/domain-library/src/main/java/app/internalrecipe/vendor/Vendor.java`
  - MongoDB collection: `vendors`
  - **@Deprecated**: Entire class is deprecated, use `VendorV2` instead
  - Fields: `vendorId`, `vendorName`, `vendorType`, `relateVendorIds`

- **VendorV2**: `backend/domain-library/src/main/java/app/internalrecipe/vendor/VendorV2.java`
  - MongoDB collection: `vendor_v2`
  - Replacement for deprecated Vendor class
  - Key fields: `name`, `vendorStatus`, `displayId` (e.g., VEN-001)

- **VendorItemV2**: `backend/domain-library/src/main/java/app/internalrecipe/vendor/VendorItemV2.java`
  - MongoDB collection: `vendor_items_v2`
  - Detailed vendor SKU data synced from Order Grid (OG)
  - Key fields: `vendorSKU`, `ogVendorItemName`, `ogPartner`, `ogPartnerName`, `ogBrand`, `ogType`, `ogLotType`
  - Pricing: `price`, `pricePerBaseUnit`, `pricePerBaseUnitDouble`
  - UOM: `inventoryUom`, `inventoryUomQty`, `purchaseUom`, `stockUom`, `packSize`
  - Storage: `storageType`, `receivingTemperature`
  - Nutrition: `nutritionFact`, `nutritionReviewedInfo`, `allergensReviewedInfo`, `dietaryTagInfo`, `ingredientStatement`
  - Nested classes: `ReviewedInfo`, `File`, `Planning`
  - Nested enums: `StorageType`, `DiscontinuedReason`

- **SKUMapping**: `backend/domain-library/src/main/java/app/internalrecipe/vendor/SKUMapping.java`
  - MongoDB collection: `sku_mappings`
  - Links cookbook items to vendor SKUs
  - Key fields: `vendorSKU`, `itemNumber`, `preference`, `isActive`, `objectType`
  - **@Deprecated fields (3)**: `vendorId`, `vendorItemId`, `vendorSKUName`

- **UOM**: `backend/domain-library/src/main/java/app/internalrecipe/vendor/UOM.java`
  - Unit of Measure structure for vendor items
  - Key fields: `packCode`, `packSize`, `toStockQty`, `uomAbbreviation`, `uomDetails`, `pickBy`, `purchaseDefault`
  - Dimension fields: `length`, `width`, `height`, `weight`
  - **@Deprecated fields (3)**: `currency`, `price`, `barcode`

- **VendorBaseUnit**: `backend/domain-library/src/main/java/app/internalrecipe/vendor/VendorBaseUnit.java`
  - MongoDB collection: `vendor_base_unit`
  - Vendor-specific unit mappings

- **UnlinkSKUMappingHistory**: `backend/domain-library/src/main/java/app/internalrecipe/vendor/UnlinkSKUMappingHistory.java`
  - Audit trail for SKU mapping removals

### Enums

- **VendorStatus**: `backend/domain-library/src/main/java/app/internalrecipe/vendor/VendorStatus.java`
  - Vendor status values

- **Status**: `backend/domain-library/src/main/java/app/internalrecipe/vendor/constant/Status.java`
  - Generic status values (ACTIVE, INACTIVE)

- **VendorType**: `backend/domain-library/src/main/java/app/internalrecipe/vendor/constant/VendorType.java`
  - Types of vendors

- **StorageType**: `backend/domain-library/src/main/java/app/internalrecipe/vendor/constant/StorageType.java`
  - Storage requirement types (AMBIENT, CHILLED, FROZEN)

### Service Layer

- **VendorItemService**: `backend/recipe-service-v2/src/main/java/app/recipev2/vendor/service/VendorItemService.java`
  - Vendor item CRUD operations

- **VendorItemServiceV2**: `backend/recipe-service-v2/src/main/java/app/recipev2/vendor/service/VendorItemServiceV2.java`
  - Enhanced vendor item operations

- **SKUMappingService**: `backend/recipe-service-v2/src/main/java/app/recipev2/skumapping/service/SKUMappingService.java`
  - SKU mapping CRUD operations

- **BOUnLinkSKUMappingUploadService**: `backend/internal-recipe-service/src/main/java/app/internalrecipe/ordergrid/service/BOUnLinkSKUMappingUploadService.java`
  - Bulk unlink SKU mappings via upload

### API Endpoints

- **BOVendorItemWebService**: `backend/internal-recipe-service-interface/src/main/java/app/internalrecipe/api/BOVendorItemWebService.java`
  - `PUT /bo/vendor-item/:id` - Update vendor item
  - `PUT /bo/vendor-item/:id/nutrition` - Update nutrition data
  - `PUT /bo/vendor-item` - Search vendor items
  - `PUT /bo/vendor-item/link/:id` - Link vendor item to cookbook item
  - `GET /bo/vendor-item/:id` - Get vendor item details
  - `GET /bo/item/:itemNumber/vendor-item` - Get vendor items for a cookbook item
  - `PUT /bo/vendor-item/sync-from-og` - Sync from Order Grid

- **BOSKUMappingWebService**: `backend/internal-recipe-service-interface/src/main/java/app/internalrecipe/api/BOSKUMappingWebService.java`
  - `PUT /bo/sku-mapping` - Search SKU mappings
  - `PUT /bo/sku-mapping/:uuid` - Update SKU mapping
  - `PUT /bo/sku-mapping/excel/bulk-update` - Bulk update via Excel
  - `DELETE /bo/sku-mapping/:uuid` - Delete SKU mapping
  - `PUT /bo/sku-mapping/:uuid/reuse` - Reuse SKU mapping
  - `PUT /bo/sku-mapping/item/:itemNumber/sync-to-og` - Sync to Order Grid

### Business Logic Patterns

- **Primary SKU Selection**: preference field (1-10), lower = higher preference; is_primary_sku indicates current preferred
- **OG Sync**: Vendor data synced bidirectionally with Order Grid
- **UOM Validation**: Ingredient inventory UOM must match vendor SKU base UOM category
- **Nutrition Review**: ReviewedInfo tracks whether nutrition data has been manually verified

### @Deprecated Field Summary

| Field | Location | Replacement |
|-------|----------|-------------|
| `Vendor` (class) | Vendor.java | Use `VendorV2` |
| `vendorId` | SKUMapping | Use vendor data from VendorItemV2 |
| `vendorItemId` | SKUMapping | Use `vendorSKU` to join |
| `vendorSKUName` | SKUMapping | Use `ogVendorItemName` from VendorItemV2 |
| `currency` | UOM | Removed from usage |
| `price` | UOM | Use `purchase_uom_price` |
| `barcode` | UOM | Removed from usage |
