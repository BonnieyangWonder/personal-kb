# Packaged SKUs - Pre-Packaged Components

Packaged SKUs are **pre-packaged items from suppliers** (88* prefix) and **HDR-specific recipes** (7* prefix) that appear on menu item component cards. They represent ready-to-use components that don't require additional preparation - typically pouches, sauces, or pre-portioned items.

> **Confluence Source**: "Packaged SKUs" page (MD-12926) in Cookbook product documentation.

---

## Essential Filter (ALWAYS USE)

When querying packaged items:

```sql
WHERE effective = true
  AND deleted = false
  AND item_status != 'DORMANT'
```

---

## Overview

**Packaged SKUs** appear in the "Packaged SKUs" section on menu item component cards in Cookbook. They are captured from two sources:

1. **BOM Lines**: 88*/7* items included in the first layer of a menu item's BOM
2. **Customization Options**: 88*/7* items directly mapped to mandatory choice or optional addition customizations

If an item appears in both BOM and customization, it is listed twice (not deduplicated).

---

## Item Number Prefixes

| Prefix | Object Type | Description | Examples |
|--------|-------------|-------------|----------|
| `88*` | PACKAGED | Pre-packaged components from suppliers | 8800311 (Cheesesteak Cheese Sauce [Pouch]) |
| `7*` | HDR_RECIPE | HDR-specific recipe items | 7000xxx |
| `80*` | MENU/RECIPE | Menu items that use packaged components | 8009068 |

**Relationship**: 80* menu items contain 88*/7* packaged items as BOM components or customization options.

---

## Packaged SKU Metadata

Each packaged SKU can have operational metadata for kitchen prep:

### Service Location

Where the item is staged during service. Multi-select field.

| Value | Description |
|-------|-------------|
| `Cold_Rail_Cold` | Cold rail (cold side) |
| `Cold_Rail_Hot` | Cold rail (hot side) |
| N/A | No specific location assigned |

**Note**: `Cold_Rail_Both` is mapped to both `Cold_Rail_Cold` and `Cold_Rail_Hot` during data import.

### Smallware Tool

Equipment used for portioning. Single-select field.

| Type | Subtypes |
|------|----------|
| N/A | (none) |
| Bottle | |
| Disher | |
| Laddle | |
| Other | |
| Portion Cup | |
| Scoop | |
| Shaker | |
| Slotted Scoop | |
| Tong | Mini Tong |

### Pan Size

Container size for staging. Single-select field (specific values defined in Cookbook UI).

---

## Customization Tag

When a packaged item (88*/7*) is captured from a **customization option** (rather than BOM), it displays a "Customization" tag in the UI. Hovering over the tag shows the option name.

---

## Data Storage

Packaged SKU data is stored in `item_versions` with the following relevant fields:

| Field | Description |
|-------|-------------|
| `object_type` | 'PACKAGED' for 88* items, 'HDR_RECIPE' for 7* items |
| `bom_header` | JSON containing BOM lines (nested packaged items) |
| `item_customization` | JSON containing customization options with mapped 88*/7* items |
| `net_weight_g` | Net weight in grams (PACKAGED items only) |
| `sold_status` | Whether item is actively being sold |

---

## Query Patterns

### List All Active Packaged Items (88*)

```sql
SELECT
  item_number,
  name,
  item_status,
  net_weight_g,
  sold_status
FROM `secure-recipe-prod.recipe_v2.effective_items`
WHERE item_number LIKE '88%'
  AND deleted = false
  AND item_status = 'ACTIVE'
ORDER BY name;
```

### Find Packaged Components in a Menu Item's BOM

```sql
SELECT
  m.item_number as menu_item,
  m.name as menu_item_name,
  JSON_VALUE(bom_line, '$.item_number') AS packaged_item,
  JSON_VALUE(bom_line, '$.name') AS packaged_name,
  SAFE_CAST(JSON_EXTRACT_SCALAR(bom_line, '$.quantity') AS FLOAT64) AS quantity,
  JSON_VALUE(bom_line, '$.uom') AS uom
FROM `secure-recipe-prod.recipe_v2.item_versions` m,
UNNEST(JSON_EXTRACT_ARRAY(m.bom_header, '$.bom_lines')) AS bom_line
WHERE m.effective = true
  AND m.deleted = false
  AND m.item_status != 'DORMANT'
  AND m.item_number = '8009068'
  AND (JSON_VALUE(bom_line, '$.item_number') LIKE '88%'
       OR JSON_VALUE(bom_line, '$.item_number') LIKE '7%');
```

### Find Packaged Items in Customization Options

```sql
SELECT
  iv.item_number as menu_item,
  iv.name as menu_item_name,
  JSON_VALUE(opt, '$.name') as customization_name,
  JSON_VALUE(opt, '$.type') as customization_type,
  JSON_VALUE(opt_val, '$.name') as option_name,
  JSON_VALUE(opt_val, '$.item_number') as packaged_item_number
FROM `secure-recipe-prod.recipe_v2.item_versions` iv,
  UNNEST(JSON_EXTRACT_ARRAY(item_customization, '$.options')) as opt,
  UNNEST(JSON_EXTRACT_ARRAY(opt, '$.option_values')) as opt_val
WHERE effective = true
  AND deleted = false
  AND item_status != 'DORMANT'
  AND object_type = 'MENU'
  AND JSON_VALUE(opt, '$.type') IN ('MANDATORY_CHOICE', 'OPTIONAL_ADDITION')
  AND (JSON_VALUE(opt_val, '$.item_number') LIKE '88%'
       OR JSON_VALUE(opt_val, '$.item_number') LIKE '7%');
```

### All Packaged SKUs for a Menu Item (BOM + Customization)

```sql
WITH bom_packaged AS (
  SELECT
    m.item_number as menu_item,
    JSON_VALUE(bom_line, '$.item_number') AS packaged_item,
    'BOM' as source
  FROM `secure-recipe-prod.recipe_v2.item_versions` m,
  UNNEST(JSON_EXTRACT_ARRAY(m.bom_header, '$.bom_lines')) AS bom_line
  WHERE m.effective = true
    AND m.deleted = false
    AND m.item_status != 'DORMANT'
    AND m.item_number = '8009068'
    AND (JSON_VALUE(bom_line, '$.item_number') LIKE '88%'
         OR JSON_VALUE(bom_line, '$.item_number') LIKE '7%')
),
customization_packaged AS (
  SELECT
    iv.item_number as menu_item,
    JSON_VALUE(opt_val, '$.item_number') as packaged_item,
    'CUSTOMIZATION' as source
  FROM `secure-recipe-prod.recipe_v2.item_versions` iv,
    UNNEST(JSON_EXTRACT_ARRAY(item_customization, '$.options')) as opt,
    UNNEST(JSON_EXTRACT_ARRAY(opt, '$.option_values')) as opt_val
  WHERE iv.effective = true
    AND iv.deleted = false
    AND iv.item_status != 'DORMANT'
    AND iv.item_number = '8009068'
    AND JSON_VALUE(opt, '$.type') IN ('MANDATORY_CHOICE', 'OPTIONAL_ADDITION')
    AND (JSON_VALUE(opt_val, '$.item_number') LIKE '88%'
         OR JSON_VALUE(opt_val, '$.item_number') LIKE '7%')
)
SELECT
  menu_item,
  packaged_item,
  source,
  ei.name as packaged_name
FROM (
  SELECT * FROM bom_packaged
  UNION ALL
  SELECT * FROM customization_packaged
) combined
LEFT JOIN `secure-recipe-prod.recipe_v2.effective_items` ei
  ON combined.packaged_item = ei.item_number
  AND ei.deleted = false
ORDER BY source, packaged_item;
```

### Find Menu Items Using a Specific Packaged SKU

```sql
-- In BOM
SELECT DISTINCT
  m.item_number as menu_item,
  m.name as menu_item_name
FROM `secure-recipe-prod.recipe_v2.item_versions` m,
UNNEST(JSON_EXTRACT_ARRAY(m.bom_header, '$.bom_lines')) AS bom_line
WHERE m.effective = true
  AND m.deleted = false
  AND m.item_status != 'DORMANT'
  AND m.object_type = 'MENU'
  AND JSON_VALUE(bom_line, '$.item_number') = '8800311'

UNION DISTINCT

-- In Customization
SELECT DISTINCT
  iv.item_number as menu_item,
  iv.name as menu_item_name
FROM `secure-recipe-prod.recipe_v2.item_versions` iv,
  UNNEST(JSON_EXTRACT_ARRAY(item_customization, '$.options')) as opt,
  UNNEST(JSON_EXTRACT_ARRAY(opt, '$.option_values')) as opt_val
WHERE iv.effective = true
  AND iv.deleted = false
  AND iv.item_status != 'DORMANT'
  AND iv.object_type = 'MENU'
  AND JSON_VALUE(opt_val, '$.item_number') = '8800311';
```

### Count Packaged Items by Type

```sql
SELECT
  CASE
    WHEN item_number LIKE '88%' THEN 'PACKAGED (88*)'
    WHEN item_number LIKE '7%' THEN 'HDR_RECIPE (7*)'
    ELSE 'OTHER'
  END as item_type,
  COUNT(*) as count
FROM `secure-recipe-prod.recipe_v2.effective_items`
WHERE deleted = false
  AND item_status = 'ACTIVE'
  AND (item_number LIKE '88%' OR item_number LIKE '7%')
GROUP BY 1
ORDER BY 1;
```

### Compare 41* and 88* Hot Hold Configuration

Compare hot hold configuration between linked 41* (WSKU) and 88* (Packaged) items to identify mismatches:

```sql
WITH linked_items AS (
  -- Get the 41* to 88* relationships from pack_relationships
  SELECT DISTINCT
    wonder_sku AS item_41,
    fulfillment_sku AS item_88
  FROM `wonder-raw-prod.mysql_batch_product_catalog.pack_relationships`
  WHERE wonder_sku LIKE '41%'
    AND fulfillment_sku LIKE '88%'
),
item_41_hh AS (
  SELECT
    item_number,
    name,
    hot_holds,
    -- Normalize by removing unique IDs for comparison
    REGEXP_REPLACE(hot_holds, r'"id": "[a-f0-9-]+"', '"id": ""') AS hot_holds_normalized
  FROM `secure-recipe-prod.recipe_v2.item_versions`
  WHERE effective = TRUE
    AND item_number LIKE '41%'
),
item_88_hh AS (
  SELECT
    item_number,
    name,
    hot_holds,
    REGEXP_REPLACE(hot_holds, r'"id": "[a-f0-9-]+"', '"id": ""') AS hot_holds_normalized
  FROM `secure-recipe-prod.recipe_v2.item_versions`
  WHERE effective = TRUE
    AND item_number LIKE '88%'
)
SELECT
  l.item_41,
  i41.name AS name_41,
  CASE
    WHEN i41.hot_holds IS NOT NULL AND i41.hot_holds != '' AND i41.hot_holds != '[]' THEN 'YES'
    ELSE 'NO'
  END AS has_hh_41,
  l.item_88,
  i88.name AS name_88,
  CASE
    WHEN i88.hot_holds IS NOT NULL AND i88.hot_holds != '' AND i88.hot_holds != '[]' THEN 'YES'
    ELSE 'NO'
  END AS has_hh_88,
  CASE
    WHEN COALESCE(i41.hot_holds, '') = COALESCE(i88.hot_holds, '') THEN 'EXACT_MATCH'
    WHEN (i41.hot_holds IS NULL OR i41.hot_holds = '' OR i41.hot_holds = '[]')
         AND (i88.hot_holds IS NULL OR i88.hot_holds = '' OR i88.hot_holds = '[]') THEN 'BOTH_EMPTY'
    WHEN COALESCE(i41.hot_holds_normalized, '') = COALESCE(i88.hot_holds_normalized, '') THEN 'MATCH_EXCEPT_ID'
    ELSE 'DIFFERENT'
  END AS comparison_result,
  i41.hot_holds_normalized AS hot_holds_41,
  i88.hot_holds_normalized AS hot_holds_88
FROM linked_items l
LEFT JOIN item_41_hh i41 ON l.item_41 = i41.item_number
LEFT JOIN item_88_hh i88 ON l.item_88 = i88.item_number
ORDER BY l.item_41, l.item_88;
```

**Comparison Results**:
- `EXACT_MATCH`: Hot hold configs are identical
- `BOTH_EMPTY`: Neither item has hot hold config
- `MATCH_EXCEPT_ID`: Configs match except for auto-generated IDs
- `DIFFERENT`: Hot hold configs don't match (potential data issue)

---

## Auto-Update Behavior

When a menu item's BOM or customization mapping is updated (adding/removing 88*/7* items), the "Packaged SKUs" section auto-updates:

- **Removed** 88*/7* items are automatically removed from the section
- **Added** 88*/7* items are automatically added to the section

---

## Version Copying

When copying a menu item version:

1. The "Packaged SKUs" section is copied along with the component card
2. If the customization section is NOT copied, the mapping 88*/7* items from customizations are excluded

---

## Permissions

The `'Edit Packaged SKUs'` permission controls who can modify packaged SKU metadata (Service Location, Smallware Tool, Pan Size).

---

## IK Dish Type & Wonder Create Packaging Auto-Assignment (9* containers)

> **Scope note**: this section is about **9\* physical containers** (bowls/cups) and the menu-item **IK Dish Type / IK Plating Rule attributes** — distinct from the 88*/7* packaged SKUs above. Kept in this doc because SKILL.md routes all 9* packaging/container questions here.
> **Sources**: Jira MD-17927 / MD-18063 / MD-18125 + Confluence (*Pre-Placing Dishes for Wonder IK*, *WC × Cookbook Integration Spec*, *IK Eligible Component Configured in Line Build*). Captured 2026-07-15 from ticket/design docs — **not** codebase-validated; re-verify field names before writing SQL.

### ⚠️ Terminology bridge — read before searching

**"IK dish type" and "packaging" are the same concept**: the 9\* container *is* the dish type. The ticket owning the Wonder Create dish-type logic is titled **"Auto Assign _Packaging_ for WC Menu Item" (MD-18063)** — "dish type" is not in its title, only in the body.

| Search for... | You get (wrong) | You want |
|---|---|---|
| `"IK dish type"` alone | MD-17927 (attr definition) + MD-18208 / MD-18209 (generic backfill) | — |
| `"Auto Assign Packaging"`, `"WC packaging"`, `Wonder Create + 9*` | **MD-18063** ✅ | the WC auto-assign logic |

**Rule**: for "how does dish type get set for WC/BYO items", search **packaging** + **Wonder Create / WC / 9\***, not the literal "dish type". Read the Confluence design docs first, then trace to the ticket.

### The 6 dish types + plating rules (MD-17927, Done)

| IK Dish Type | Typical use | IK Plating Rule |
|---|---|---|
| 48oz Bowl | large salads/bowls (≥2 greens or >32oz) | Layering |
| 32oz Bowl | smaller bowls | Center |
| 30oz Oval | — | Straight |
| Metal Bowl | wraps; reusable-bowl candidate | Prelap Center |
| Bellies Bowl | kids meals | Prelap Poke Press |
| 8oz Cup | sides | — |

IK **pre-places all 6** dish types at startup; physical constraint = **max 2 inserts**.

### Normal item vs Wonder Create item — the KEY difference

- **Normal menu item**: CDT sets IK Dish Type / Plating Rule **manually** (MD-17927).
- **Wonder Create menu item**: Cookbook **auto-derives & auto-tags** at create/publish (MD-18063), because WC line builds get **no manual review** (Confluence: *IK Eligible Component Configured in Line Build*).

### WC auto-assign logic — MD-18063 (Done)

Problem, verbatim: *"WC Portal ... does not include packaging type information. Cookbook defaults all WC items to a standard bowl, which breaks kitchen execution for dishes with multiple leafy greens or high total weight."*

- **Step 1 — pick 9\* packaging**: influencer picks **item type** only (WC portal doesn't send 9\*; ignored if it does). CDT tags components `Component Type = Green`. **green portions ≥ 2 OR total food weight > 32oz → 48oz bowl; else 32oz bowl.**
- **Step 2 — derive + auto-tag**: bowls + 48oz → **48oz Bowl / LAYERING**; bowls + 32oz → **32oz Bowl / LAYERING**; wrap → **Metal Bowl / CENTER**. Re-derived when components / non-food items change; used as the **default** in the line build.
- **Transfer**: WC → Cookbook `/wonder-create/publish` (auto packaging + auto-tag + auto line build) → KDS/IK — IK Dish Type returned at **line-build level**, IK Plating Rule at **sub-step level** (falls back to the menu-item attribute). Consumption gated by the component's **'IK eligible'** flag (MD-17927).

### Known open issues

- **[MD-18125](https://wonder.atlassian.net/browse/MD-18125) (To Do)** — after removing a component's `Component Type: Green` and dropping to <2 greens & <32oz, IK Dish Type should auto-update to "32oz Bowl" but the **update fails**.
- **"pending dish type issue"** — *6/16 IK Integration Test* **Scenario 11** (main + multiple sides = multiple containers per order); multi-dish-type single order not yet solved.
- **Reusable (Metal) bowl insert** TBD; team wants a no-deploy way (Fig/Contentful) to add/remove packaging types.

### Data-research relevance (BYO / zero-BOM)

For **BYO bowls with zero required BOM** (ingredients via customization; BOM = `manage_inventory = false` packaging only), the dish type is **NOT** in the BOM — it's inferred from the **Green component count / total weight** rule above. Don't read the container off required BOM. Example: *Royal Greens BYO Greens Bowl* (`8010459`) in [[A2-Data Research/byo-zero-bom-analysis-2026-07-02.md]].

**Where the attribute lives (TO VERIFY):** IK Dish Type / IK Plating Rule are menu-item **attributes** → most likely in `item_versions` attribute/tag JSON (see [../core/tags-categorization.md](../core/tags-categorization.md)). Exact JSON path / field name **not verified** — confirm against a known WC item before writing SQL; do not assume a column name.

### Source tickets (dish-type specific)

| Key | Summary | Status |
|---|---|---|
| [MD-17927](https://wonder.atlassian.net/browse/MD-17927) | Defines 6 dish types + 5 plating rules + KDS return contract | Done |
| [MD-18063](https://wonder.atlassian.net/browse/MD-18063) | **[WC] Auto Assign Packaging for WC Menu Item** — WC auto-assign + auto-tag (titled "packaging", not "dish type") | Done |
| [MD-18125](https://wonder.atlassian.net/browse/MD-18125) | WC Menu item: updating 'Attribute(IK Dish Type)' value failed | To Do |

**Not** these (generic attribute backfill, common false match): MD-18208 / MD-18209.

---

## Critical Rules

1. **Always include `deleted = false`** when querying any item data
2. **88* and 7* items can appear twice** - once from BOM, once from customization (not deduplicated)
3. **Customization tag** indicates the packaged item came from customization options
4. **Use nested JSON pattern** for single menu item lookups (more efficient)
5. **Check both BOM and customization** to find all packaged items for a menu item

---

## Related Documentation

- [../core/item-master.md](../core/item-master.md) - Item number prefixes and object types
- [../core/bom-components.md](../core/bom-components.md) - BOM structure and nested JSON pattern
- [customization.md](customization.md) - Customization options (MANDATORY_CHOICE, OPTIONAL_ADDITION)
- Confluence: [Packaged SKUs](https://wonder.atlassian.net/wiki/spaces/RT/pages/4176707924/Packaged+SKUs)

---

## Code References (Java Codebase)

> **Codebase**: `master-data-management-2`
> **Validated**: 2026-01-28

### Domain Models

- **PackageSKUConfig**: `backend/domain-library/src/main/java/app/internalrecipe/item/innerclassview/PackageSKUConfig.java`
  - Embedded in BOM lines and customization option values
  - Key fields: `consumableItemNumber`, `itemNumber`, `serviceLocations` (List<String>), `panSize`, `smallwareToolFirstLevel`, `smallwareToolSecondLevel`
  - References: ServiceLocationOption, PanSizeOption, SmallwareToolOption for valid values

### Option Value Classes

- **ServiceLocationOption**: `backend/domain-library/src/main/java/app/internalrecipe/item/innerclassview/ServiceLocationOption.java`
  - Static VALUES list: `No Selection`, `N/A`, `Freezer`, `Cold Storage Hot`, `Cold Storage Cold`, `Runner`, `Cold Rail Hot`, `Cold Rail Cold`, `Dry Rail Cold`, `Dry Rail Hot`, `Ambient Cold`, `Ambient Hot`, `Merchandiser`, `Steam Well`

- **SmallwareToolOption**: `backend/domain-library/src/main/java/app/internalrecipe/item/innerclassview/SmallwareToolOption.java`
  - Two-level hierarchy: `VALUES_MAP` (Map<String, List<String>>)
  - First level: `No Selection`, `N/A`, `Other`, `Scoop`, `Disher`, `Portion Cup`, `Tong`, `Bottle`, `Slotted Scoop`, `Shaker`, `Ladle`
  - Second level varies by first level (e.g., Scoop → `1 Tbsp`, `1 tsp`, `2 oz Spoodle`, etc.)

- **PanSizeOption**: `backend/domain-library/src/main/java/app/internalrecipe/item/innerclassview/PanSizeOption.java`
  - Static VALUES list: `No Selection`, `N/A`, `3`, `6`, `9`, `9.5`, `8 oz Bottle`, `16 oz Bottle`

### Service Layer

- **BOItemVersionPackageSKUService**: `backend/internal-recipe-service/src/main/java/app/internalrecipe/item/service/packagesku/service/BOItemVersionPackageSKUService.java`
  - Core packaged SKU operations
  - Key constants: `ALLOW_HAS_PACKAGE_SECTION_OBJECT_TYPE_FILTER` (MENU, HDR_RECIPE), `NEED_OPTION_TYPES` (MANDATORY_CHOICE, OPTIONAL_ADDITION)

- **BOItemVersionPackageSKURefreshService**: `backend/internal-recipe-service/src/main/java/app/internalrecipe/item/service/packagesku/service/BOItemVersionPackageSKURefreshService.java`
  - Auto-refresh packaged SKUs when BOM/customization changes

- **PackageSKUViewBuilder**: `backend/internal-recipe-service/src/main/java/app/internalrecipe/item/service/packagesku/builder/PackageSKUViewBuilder.java`
  - Builds packaged SKU list from BOM and customization data

- **PackageSKUConfigViewBuilder**: `backend/internal-recipe-service/src/main/java/app/internalrecipe/item/service/packagesku/builder/PackageSKUConfigViewBuilder.java`
  - Builds config view for UI

- **ItemVersionPackageSKUConfigValidator**: `backend/internal-recipe-service/src/main/java/app/internalrecipe/item/service/validationinformation/itemversion/validator/ItemVersionPackageSKUConfigValidator.java`
  - Validates packaged SKU configuration

- **BulkGetItemPackageSUKConfigService**: `backend/recipe-service-v2/src/main/java/app/recipev2/item/service/BulkGetItemPackageSUKConfigService.java`
  - Bulk query for packaged SKU configs

### API Endpoints

- **BOItemVersionPackageSKUWebService**: `backend/internal-recipe-service-interface/src/main/java/app/internalrecipe/api/BOItemVersionPackageSKUWebService.java`
  - `PUT /bo/item/version/:uuid/package-sku/update` - Update packaged SKU config
  - `GET /bo/item/version/:uuid/package-sku/list` - List packaged SKUs for item version
  - `GET /bo/component-bom/package-sku/option/list` - List all config options (service locations, pan sizes, smallwares)

### Change Stream Observers

- **ItemVersionPackageSKUConfigChangedObserver**: `backend/internal-recipe-service/src/main/java/app/internalrecipe/changestream/itemversionchange/observers/ItemVersionPackageSKUConfigChangedObserver.java`
  - Handles item version changes affecting packaged SKU config

- **ItemPackageSKUConfigChangedObserver**: `backend/internal-recipe-service/src/main/java/app/internalrecipe/changestream/itemchange/observers/ItemPackageSKUConfigChangedObserver.java`
  - Handles item changes affecting packaged SKU config

### Business Logic Patterns

- **PackageSKUConfig in BOM**: Stored in `BOMHeader.bomLines[].packageSKUConfigs` for 88*/7* items
- **PackageSKUConfig in Customization**: Stored in `ItemCustomization.Option.OptionValue.Item.packageSKUConfigs`
- **Auto-Update**: When BOM or customization mappings change, packaged SKU section auto-refreshes
- **Object Type Filter**: Only MENU and HDR_RECIPE items can have packaged SKU section

### @Deprecated Fields

No @Deprecated annotations found in PackageSKUConfig domain classes.
