# HDR Consumables - The 40 Model

HDR Consumable Items (40* prefix) and WSKUs (41* prefix) together form the "40 Model" - Wonder's system for tracking consumable inventory at HDRs (High Density Restaurants). This model separates the **consumable representation** (40*) from the **stockable/orderable representation** (41*).

> **Confluence Source**: "HDR Consumable Item 40 Detail" (MD-15424) and "WSKUs & Consumables Grid" pages in Cookbook product documentation.

---

## Essential Filter (ALWAYS USE)

When querying HDR consumable items:

```sql
WHERE effective = true
  AND deleted = false
  AND item_status != 'DORMANT'
```

---

## Overview

The 40 Model establishes a clean separation between:

1. **HDR Consumable Items (40*)**: What gets consumed/tracked at HDRs - the consumable representation
2. **WSKUs (41*)**: What gets ordered/stocked from the warehouse - the stockable representation

**Key Relationship**: A single 40* item can have multiple 41* WSKUs linked to it (different pack sizes), but only **one 41* is "active for ordering"** at any given time.

---

## Item Number Prefixes

| Prefix | Object Type | Description | Example |
|--------|-------------|-------------|---------|
| `40*` | HDR_CONSUMABLE_ITEM | Items consumed/tracked at HDR level | 4000031, 4000053 |
| `41*` | WSKU | Wonder SKU - orderable warehouse items | 410001 |
| `88*` | PACKAGED | Pre-packaged items (legacy, being replaced by 40/41) | 8800311 |
| `5**/80*/88*` | Various | Legacy consumable items migrated to 40* | Various |

**Naming Convention**:
- 40* items: `{Original Name} HDR` - e.g., "Pulled Pork [Pouch, 150g] 3.0 HDR"
- 41* items: `{Name} WSKU` - e.g., "Pulled Pork [Pouch, 150g] 3.0 WSKU"

---

## The 40 Model Explained

### Stockable vs Consumable

The 40 Model separates two concerns:

| Aspect | 40* (HDR Consumable) | 41* (WSKU) |
|--------|---------------------|------------|
| Purpose | Track consumption at HDR | Track inventory ordering |
| Used By | Pantry, BOM, Kitchen | Supply Chain, Ordering |
| Quantity | Consumption quantity | Pack size quantity |
| Relationship | Has linked WSKUs | Links to one 40* item |

### Why This Matters

**Example**: A 40* item "Pulled Pork HDR" might have two 41* WSKUs:
- `410001`: 150g pouch (active for ordering)
- `410002`: 300g pouch (inactive, legacy size)

Both WSKUs link to the same consumable item, allowing:
- Pantry to see total on-hand inventory across both pack sizes
- Ordering to route through the currently active WSKU only

---

## Active for Ordering

Each 40* item must have exactly one 41* WSKU marked as **"Active for Ordering"**.

**Rules**:
1. Only one 41* per 40* can be active at a time
2. Activating a new 41* automatically deactivates the previous one
3. Cannot deactivate the last active 41* for a non-dormant 40*
4. Both active and inactive 41* items are synced to downstream systems (Pantry, Ladle)

**Downstream Behavior**:
- **Pantry**: Sees all linked 41* items (tracks on-hand inventory for both)
- **Ladle**: Uses only the "active for ordering" 41* for new orders

---

## Data Storage

### HDR Consumable Items (40*)

Stored in `item_versions` with `object_type = 'HDR_CONSUMABLE_ITEM'`:

| Field | Description |
|-------|-------------|
| `item_number` | 40* identifier |
| `name` | Item name with "HDR" suffix |
| `object_type` | 'HDR_CONSUMABLE_ITEM' |
| `production_start_time` | When item starts production |
| `service_start_time` | When item starts service |
| `sold_status` | Current sale status |
| `bom_unit` | Unit of measure for BOM |
| `inventory_unit` | Unit for inventory tracking |

**40* Item Characteristics**:
- Only has 1 version (no version history)
- Cannot create variants
- Not synced to ERP
- Shows "Pack Size List" card with linked WSKUs

### WSKUs (41*)

Stored in `item_versions` with `object_type = 'WSKU'`:

| Field | Description |
|-------|-------------|
| `item_number` | 41* identifier |
| `name` | Item name with "WSKU" suffix |
| `object_type` | 'WSKU' |
| `consumable_item_number` | Linked 40* item |
| `consumable_quantity` | Quantity of 40* per WSKU unit |
| `active_for_ordering` | Boolean - is this the active WSKU? |

**41* Item Characteristics**:
- Cannot create new versions
- Cannot create variants
- Not synced to ERP
- Shows Hot Hold, Fulfillment Option, SKU Unit Size Mapping cards

---

## Usages Card (40* Items)

HDR Consumable items have a "Usages" card with four tabs:

| Tab | Description |
|-----|-------------|
| Component Usages | Where this 40* appears as a BOM component |
| BOM Usages | Where this 40* appears in BOMs |
| Customization Usages | Where this 40* is a customization option |
| Linked WSKUs | All 41* items linked to this 40* |

---

## Data Migration Context

The 40 Model was created by migrating existing consumable items (5*/80*/88*) to the new structure:

**Migration Rules**:
1. Create new 40* item from existing consumable
2. If 41* WSKU was both stockable AND consumable with qty != 1ea, create separate 40*
3. Replace legacy consumable linkages (5*/80*/88*) with new 40* in WSKU definitions
4. If consumable qty = 1ea and item equals itself, no new 40* needed
5. Record linkage between new 40* and source 5*/80*/88* item

---

## Query Patterns

### List All Active HDR Consumable Items (40*)

```sql
SELECT
  item_number,
  name,
  item_status,
  sold_status
FROM `secure-recipe-prod.recipe_v2.effective_items`
WHERE item_number LIKE '40%'
  AND deleted = false
  AND item_status = 'ACTIVE'
ORDER BY name;
```

### List All WSKUs (41*)

```sql
SELECT
  item_number,
  name,
  item_status,
  sold_status
FROM `secure-recipe-prod.recipe_v2.effective_items`
WHERE item_number LIKE '41%'
  AND deleted = false
  AND item_status = 'ACTIVE'
ORDER BY name;
```

### Find WSKUs Linked to a 40* Item

```sql
-- Find all 41* WSKUs that link to a specific 40* consumable item
SELECT
  iv.item_number as wsku_number,
  iv.name as wsku_name,
  JSON_VALUE(iv.consumable_item, '$.item_number') as consumable_item,
  JSON_VALUE(iv.consumable_item, '$.quantity') as consumable_qty,
  JSON_VALUE(iv.consumable_item, '$.active_for_ordering') as active_for_ordering
FROM `secure-recipe-prod.recipe_v2.item_versions` iv
WHERE iv.effective = true
  AND iv.deleted = false
  AND iv.item_status != 'DORMANT'
  AND iv.object_type = 'WSKU'
  AND JSON_VALUE(iv.consumable_item, '$.item_number') = '4000053';
```

### Find Active WSKU for a 40* Item

```sql
SELECT
  iv.item_number as wsku_number,
  iv.name as wsku_name,
  JSON_VALUE(iv.consumable_item, '$.item_number') as consumable_item
FROM `secure-recipe-prod.recipe_v2.item_versions` iv
WHERE iv.effective = true
  AND iv.deleted = false
  AND iv.item_status != 'DORMANT'
  AND iv.object_type = 'WSKU'
  AND JSON_VALUE(iv.consumable_item, '$.item_number') = '4000053'
  AND CAST(JSON_VALUE(iv.consumable_item, '$.active_for_ordering') AS BOOL) = true;
```

### Find 40* Items with Multiple WSKUs

```sql
WITH wsku_counts AS (
  SELECT
    JSON_VALUE(iv.consumable_item, '$.item_number') as consumable_item,
    COUNT(*) as wsku_count
  FROM `secure-recipe-prod.recipe_v2.item_versions` iv
  WHERE iv.effective = true
    AND iv.deleted = false
    AND iv.item_status != 'DORMANT'
    AND iv.object_type = 'WSKU'
  GROUP BY 1
)
SELECT
  wc.consumable_item,
  ei.name as consumable_name,
  wc.wsku_count
FROM wsku_counts wc
LEFT JOIN `secure-recipe-prod.recipe_v2.effective_items` ei
  ON wc.consumable_item = ei.item_number
  AND ei.deleted = false
WHERE wc.wsku_count > 1
ORDER BY wc.wsku_count DESC;
```

### Find Menu Items Using a 40* Consumable

```sql
SELECT DISTINCT
  m.item_number as menu_item,
  m.name as menu_item_name
FROM `secure-recipe-prod.recipe_v2.item_versions` m,
UNNEST(JSON_EXTRACT_ARRAY(m.bom_header, '$.bom_lines')) AS bom_line
WHERE m.effective = true
  AND m.deleted = false
  AND m.item_status != 'DORMANT'
  AND m.object_type = 'MENU'
  AND JSON_VALUE(bom_line, '$.item_number') LIKE '40%'
ORDER BY menu_item;
```

### Count Items by 40/41 Type

```sql
SELECT
  CASE
    WHEN item_number LIKE '40%' THEN 'HDR_CONSUMABLE (40*)'
    WHEN item_number LIKE '41%' THEN 'WSKU (41*)'
    ELSE 'OTHER'
  END as item_type,
  COUNT(*) as count
FROM `secure-recipe-prod.recipe_v2.effective_items`
WHERE deleted = false
  AND item_status = 'ACTIVE'
  AND (item_number LIKE '40%' OR item_number LIKE '41%')
GROUP BY 1
ORDER BY 1;
```

### Find Consumable Items NOT Using 40 Model

Find items that are flagged as consumable but haven't been migrated to the 40 Model yet:

```sql
SELECT
  iv.item_number,
  i.enable_40_model_date,
  i.enable_40_model,
  iv.is_consumable_inventory,
  iv.name
FROM `secure-recipe-prod.recipe_v2.item_versions` iv
LEFT JOIN `wonder-recipe-prod.mongo_batch_recipe_v2.items` i
  ON iv.item_number = i.item_number
WHERE iv.is_consumable_inventory = true
  AND iv.item_status != 'DORMANT'
  AND iv.deleted = false
  AND iv.effective = true
  AND iv.object_type IN ('INGREDIENT', 'PACKAGED', 'RECIPE')
  AND i.enable_40_model_date IS NULL;  -- Not yet migrated to 40 Model
```

**Note**: `enable_40_model_date` being NULL indicates items that are consumable but haven't been converted to the new 40*/41* structure.

---

## Permissions

| Permission | Allows |
|------------|--------|
| Create WSKU | Creating new 41* items |
| Edit WSKU | Modifying 41* item details |
| Edit Pack Size | Changing consumable quantity in WSKU |
| N/A | Creating new 40* versions (not allowed) |
| N/A | Creating 40* variants (not allowed) |

---

## Critical Rules

1. **Always include `deleted = false`** when querying any item data
2. **40* items have only 1 version** - no version history or variants allowed
3. **One active WSKU per 40*** - only one 41* can be "active for ordering" at a time
4. **Both active and inactive WSKUs sync** - downstream systems see all linked 41* items
5. **Pantry tracks all WSKUs** - inventory aggregates across all linked pack sizes
6. **Ladle uses active WSKU only** - ordering routes through the active 41*
7. **41* items are NOT synced to ERP** - they exist only in Cookbook/PCS

---

## Related Documentation

- [../core/item-master.md](../core/item-master.md) - Item number prefixes and object types
- [../cross-system/pantry-integration.md](../cross-system/pantry-integration.md) - How Pantry tracks 40*/41* inventory
- [vendor-items.md](vendor-items.md) - External vendor SKU linkage
- Confluence: [HDR Consumable Item 40 Detail](https://wonder.atlassian.net/wiki/spaces/RC/pages/4179525649/)
- Confluence: [WSKUs & Consumables Grid](https://wonder.atlassian.net/wiki/spaces/RC/pages/4086892536/)

---

## Code References (Java Codebase)

> **Codebase**: `master-data-management-2`
> **Validated**: 2026-01-28

### Domain Models

- **Schedule40ModelReplaceLog**: `backend/domain-library/src/main/java/app/internalrecipe/item/schedule40model/Schedule40ModelReplaceLog.java`
  - MongoDB Collection: `schedule_40_model_replace_logs`
  - Tracks consumable-to-HDR consumable migrations
  - Key fields: `consumableItemNumber` (ID), `scheduleDate`, `hdrConsumableItemNumber`, `stockItems` (List<StockItem>)
  - Nested classes: `StockItem`, `WSKUItem` with conversion quantities

- **Schedule40ModelReplaceExecLog**: `backend/domain-library/src/main/java/app/internalrecipe/item/schedule40model/Schedule40ModelReplaceExecLog.java`
  - Execution log for 40 model migrations

- **HDRConsumableMigrateResult**: `backend/domain-library/src/main/java/app/internalrecipe/item/HDRConsumableMigrateResult.java`
  - MongoDB Collection: `hdr_consumable_migrate_results`
  - Records source item to HDR consumable mapping
  - Key fields: `fromItemVersionId`, `fromItemNumber`, `hdrConsumableItemNumber`, `hdrConsumableItemVersionId`

- **WSKUMappingHDRConsumableItemChangeLog**: `backend/domain-library/src/main/java/app/internalrecipe/item/WSKUMappingHDRConsumableItemChangeLog.java`
  - Tracks changes to WSKU-to-HDR consumable mappings

- **WSKUVendorMapping**: `backend/domain-library/src/main/java/app/internalrecipe/item/WSKUVendorMapping.java`
  - Maps WSKUs to vendor SKUs

### ItemVersion Fields for HDR Consumables

The 40 Model uses fields in ItemVersion (see item-master.md code references):
- `consumableItem` (JSON) - For WSKUs: linked 40* item info including `item_number`, `quantity`, `active_for_ordering`
- `objectType` - `HDR_CONSUMABLE_ITEM` for 40*, `WSKU` for 41*

### Service Layer

- **BOSchedule40ModelService**: `backend/internal-recipe-service/src/main/java/app/internalrecipe/schedule40model/service/BOSchedule40ModelService.java`
  - Core 40 model operations

- **BOSchedule40ModelReplaceService**: `backend/internal-recipe-service/src/main/java/app/internalrecipe/schedule40model/service/BOSchedule40ModelReplaceService.java`
  - Handles item replacement during 40 model migration

- **BOSchedule40ModelCheckService**: `backend/internal-recipe-service/src/main/java/app/internalrecipe/schedule40model/service/BOSchedule40ModelCheckService.java`
  - Validation before 40 model operations

- **BOSchedule40ModelQueryService**: `backend/internal-recipe-service/src/main/java/app/internalrecipe/schedule40model/service/BOSchedule40ModelQueryService.java`
  - Query schedule 40 model data

- **BOSchedule40ModelParamService**: `backend/internal-recipe-service/src/main/java/app/internalrecipe/schedule40model/service/BOSchedule40ModelParamService.java`
  - Parameter handling for 40 model operations

- **BOCustomSchedule40ModelService**: `backend/internal-recipe-service/src/main/java/app/internalrecipe/schedule40model/service/BOCustomSchedule40ModelService.java`
  - Custom 40 model handling

- **BOUpdateWSKUAndHDRConsumableItemCostService**: `backend/internal-recipe-service/src/main/java/app/internalrecipe/item/service/wsku/BOUpdateWSKUAndHDRConsumableItemCostService.java`
  - Cost updates for WSKU and HDR consumable items

- **BOWSKUMappingHDRConsumableChangeLogService**: `backend/internal-recipe-service/src/main/java/app/internalrecipe/item/service/BOWSKUMappingHDRConsumableChangeLogService.java`
  - Change log service for WSKU-HDR consumable mappings

- **BO40ModelItemLinkageCheckService**: `backend/internal-recipe-service/src/main/java/app/internalrecipe/item/service/BO40ModelItemLinkageCheckService.java`
  - Validates 40 model item linkages

- **BOHDRConsumableItemCheckService**: `backend/internal-recipe-service/src/main/java/app/internalrecipe/itemversion/service/BOHDRConsumableItemCheckService.java`
  - HDR consumable item validation

### API Endpoints

- **BOItemHDRConsumableWebService**: `backend/internal-recipe-service-interface/src/main/java/app/internalrecipe/api/BOItemHDRConsumableWebService.java`
  - `GET /bo/item/hdr-consumable/version/:id` - Get HDR consumable item
  - `GET /bo/item/hdr-consumable/version/:id/pack-size` - Get pack size info
  - `GET /bo/item/hdr-consumable/version/:id/nutrition` - Get nutrition
  - `PUT /bo/item/hdr-consumable/version/:id/wonder-app-name-and-hide-flag` - Update display settings
  - `GET /bo/item/hdr-consumable/version/:id/linked-wonder-skus` - Get linked WSKUs
  - `PUT /ajax/item/hdr-consumable/:itemNumber/active-for-ordering` - Update active WSKU
  - `GET /bo/item/hdr-consumable/:itemNumber/mapping-change-log` - Get change log

- **BOSchedule40ModelWebService**: `backend/internal-recipe-service-interface/src/main/java/app/internalrecipe/api/BOSchedule40ModelWebService.java`
  - `PUT /bo/item/:itemNumber/40-model/enable/check` - Check if 40 model can be enabled
  - `PUT /bo/item/:itemNumber/40-model/check` - Check 40 model update
  - `PUT /bo/item/:itemNumber/40-model` - Update to 40 model
  - `PUT /bo/item/:itemNumber/40-model/retry` - Retry failed migration
  - `GET /bo/item/:itemNumber/40-model/stock-items` - Get stock items for 40 model
  - `GET /bo/item/:itemNumber/40-model/get-packaged-items` - Get packaged items (88* from 5*/80*)
  - `PUT /bo/item/40-model/get-menu-hdr-recipe-items` - Find menu/HDR recipe items
  - `PUT /bo/item/40-model/swap-menu-hdr-recipe-items` - Swap sub-items

### WSKU Product Catalog Services

- **BOWSKUToFulfillmentOptionService**: `backend/product-catalog-internal-service/src/main/java/app/productcatalog/internal/wsku/service/BOWSKUToFulfillmentOptionService.java`
  - WSKU to fulfillment option mapping

- **BOWSKUWarehouseService**: `backend/product-catalog-internal-service/src/main/java/app/productcatalog/internal/wsku/service/BOWSKUWarehouseService.java`
  - WSKU warehouse operations

### Business Logic Patterns

- **Single Active WSKU**: Only one 41* per 40* can have `active_for_ordering = true`
- **Automatic Deactivation**: Activating a new WSKU auto-deactivates the previous one
- **Migration Tracking**: `HDRConsumableMigrateResult` maps legacy items to new 40* items
- **Change Logging**: `WSKUMappingHDRConsumableItemChangeLog` tracks all mapping changes
- **Object Type Filter**: 40* items have `objectType = HDR_CONSUMABLE_ITEM`, 41* have `objectType = WSKU`

### @Deprecated Fields

No @Deprecated annotations found in HDR consumable/Schedule40Model domain classes.
