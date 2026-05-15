# Benchtop Recipes

Benchtop recipes are R&D/test kitchen items used for recipe development before commercialization. They allow culinary teams to experiment and refine recipes before promoting them to production use.

## Key Concepts

### Benchtop Subtypes

There are three benchtop recipe subtypes, each with different capabilities:

| Subtype | Code | Description | Can Commercialize |
|---------|------|-------------|-------------------|
| **BT-Primary** | `BT-PRIMARY` | Main benchtop recipes | Yes - to recipe-primary |
| **BT-Preparation** | `BT-PREPARATION` | Prep/component recipes | Yes - to recipe-preparation (1:1 only) |
| **BT-Byproduct** | `BT-BYPRODUCT` | Output items from other benchtop recipes | No |

### Item Naming Convention

Benchtop items have `[BT]` suffix in their names (e.g., "Chicken Tikka Masala [BT]"). When commercialized, this suffix is removed.

### Benchtop vs Commercial Items

| Feature | Benchtop | Commercialized |
|---------|----------|----------------|
| Purpose | R&D/testing | Production use |
| Name suffix | `[BT]` | No suffix |
| Inventory Unit | Same as recipe item logic | Must be `kg` |
| Yield Unit | Flexible | Must be `g` or have conversion |
| UI Cards | Fewer (no Logistics/Appliance & Equipment) | Full cards |
| Skill Level | Hidden/optional | Standard |

## Commercialization Workflow

Commercialization creates production-ready recipe items from benchtop recipes. The linkage is tracked at the version level.

### Commercialization Rules

1. **benchtop-primary** can commercialize to:
   - Multiple recipe-primary items (1:N relationship)
   - Multiple ingredient items

2. **benchtop-preparation** can commercialize to:
   - One recipe-preparation (1:1 relationship)
   - Multiple ingredient items

3. **benchtop-byproduct** cannot be commercialized

### Commercialization Requirements

Before commercializing:
- The benchtop version must be **published** (not draft)
- The benchtop item must not be **dormant**
- No **dormant sub-components** in the component tree
- Proper **unit conversions** must exist (yield unit to `g`, inventory unit to `kg`)

### Version Handling

When commercializing:
- Creates a new **draft** version of the commercialized recipe
- **Nutrition status** is set to "needs review"
- **Linkage** is recorded at the version level (benchtop version to commercialized recipe version)
- Linkage cannot be manually unlinked

### Commercialize to Existing Draft

Users can also commercialize to an existing commercialized recipe's draft version:
- **Creates new draft** if no draft/scheduled version exists
- **Overrides existing draft** if one exists
- Updates the linkage to the new benchtop version

### What Gets Copied

| Field/Card | Commercialize to Recipe | Commercialize to Draft | Commercialize to Ingredient |
|------------|------------------------|----------------------|---------------------------|
| Name | Remove `[BT]` suffix | Keep existing name | Remove `[BT]`, add increment |
| Components | Copied | Copied from benchtop | N/A (ingredients have no components) |
| Procedures | Copied | Copied from benchtop | N/A |
| Attributes | Copied | Copied from benchtop | Copied |
| Nutrition | Copied | Copied from benchtop | Not copied (starts null) |
| Unit Conversions | Copied | Copied from benchtop | Not copied |
| Comment | Copied | Override with benchtop | Not copied |
| Logistics/Production | N/A (not in benchtop) | Keep from effective version | N/A |
| Variant | N/A | Keep existing (not overridden) | N/A |

### Co-Manufactured Ingredients

When commercializing a benchtop to an ingredient:
- The ingredient gets the tag `Co-Manufactured`
- Shows "Co-Manufactured" label in UI next to the ingredient name
- Indicates the ingredient was created from a benchtop recipe

## Item Information Cards

### BT-Primary / BT-Preparation Cards

**Left Column Fields:**
- Production Start Time
- Object Type
- Concepts (editable)
- Menus
- Chef(s) (editable)
- Status

**Right Column Fields:**
- Inventory Unit
- Unit Used in BOM
- Total Cost
- Component Cost
- Allergens

### BT-Byproduct Cards

**Left Column Fields:**
- Production Start Time
- Object Type
- Concepts (editable)
- Parent Recipe
- Status

**Right Column Fields:**
- Inventory Unit
- Unit Used in BOM
- Total Cost
- Component Cost

**Note:** BT-Byproduct's Inventory Unit & Unit Used in BOM equal the output UOM in the parent benchtop recipe.

### Available Cards by Subtype

| Card | BT-Primary/Preparation | BT-Byproduct |
|------|----------------------|--------------|
| Overview | Yes | Yes |
| Files | Yes | Yes |
| Component | Yes | No |
| Procedures | Yes | No |
| Attributes | Yes | Yes |
| Nutrition & Allergens | Yes | Yes |
| Unit Conversions | Yes | Yes |
| All Ingredients | Yes | No |
| Usages | Yes | Yes |
| Related Items | Yes | No |
| Change History | Yes | Yes |
| Versions | Yes | Yes |

## Query Patterns

### Find All Benchtop Items

```sql
SELECT
  item_number,
  name,
  object_type,
  item_status,
  version_number
FROM `secure-recipe-prod.recipe_v2.item_versions`
WHERE effective = true
  AND deleted = false
  -- Benchtop items have [BT] suffix in name
  AND name LIKE '%[BT]%'
ORDER BY item_number;
```

### Find Benchtop Items by Subtype

```sql
SELECT
  item_number,
  name,
  object_type,
  item_status
FROM `secure-recipe-prod.recipe_v2.item_versions`
WHERE effective = true
  AND deleted = false
  -- Filter by object_type for benchtop subtypes
  AND object_type IN ('BT-PRIMARY', 'BT-PREPARATION', 'BT-BYPRODUCT')
ORDER BY object_type, item_number;
```

### Find Commercialized Recipe Linkages

```sql
-- Note: Linkages are stored in a dedicated table
-- The exact table name may vary - check recipe_v2 schema
SELECT
  bt.item_number as benchtop_item,
  bt.name as benchtop_name,
  bt.version_number as benchtop_version,
  comm.item_number as commercialized_item,
  comm.name as commercialized_name,
  comm.version_number as commercialized_version
FROM `secure-recipe-prod.recipe_v2.item_versions` bt
JOIN `secure-recipe-prod.recipe_v2.commercialize_linkages` cl
  ON bt.item_version_id = cl.benchtop_version_id
JOIN `secure-recipe-prod.recipe_v2.item_versions` comm
  ON cl.commercialized_version_id = comm.item_version_id
WHERE bt.deleted = false
  AND comm.deleted = false
ORDER BY bt.item_number, comm.item_number;
```

### Find BT-Byproducts and Their Parents

```sql
SELECT
  byp.item_number as byproduct_item,
  byp.name as byproduct_name,
  parent.item_number as parent_item,
  parent.name as parent_name
FROM `secure-recipe-prod.recipe_v2.item_versions` byp
JOIN `secure-recipe-prod.recipe_v2.bom_lines` bl
  ON byp.item_number = CAST(bl.bom_line_item_number AS STRING)
JOIN `secure-recipe-prod.recipe_v2.item_versions` parent
  ON bl.bom_header_item_number = parent.item_number
WHERE byp.object_type = 'BT-BYPRODUCT'
  AND byp.effective = true
  AND byp.deleted = false
  AND parent.effective = true
  AND parent.deleted = false
  AND CURRENT_TIMESTAMP() BETWEEN TIMESTAMP(bl.service_start_time) AND TIMESTAMP(bl.service_end_time);
```

### Check If Benchtop Can Be Commercialized

```sql
SELECT
  item_number,
  name,
  object_type,
  item_status,
  version_status,
  CASE
    WHEN item_status = 'DORMANT' THEN 'Cannot commercialize: item is dormant'
    WHEN version_status = 'DRAFT' THEN 'Cannot commercialize: version not published'
    WHEN version_status = 'EXPIRED' THEN 'Cannot commercialize: version expired'
    WHEN object_type = 'BT-BYPRODUCT' THEN 'Cannot commercialize: byproducts cannot be commercialized'
    ELSE 'Can commercialize'
  END as commercialize_status
FROM `secure-recipe-prod.recipe_v2.item_versions`
WHERE effective = true
  AND deleted = false
  AND name LIKE '%[BT]%'
ORDER BY item_number;
```

## Common Pitfalls

### Wrong: Assuming All Benchtop Items Can Be Commercialized

```sql
-- WRONG: Missing subtype check
SELECT * FROM item_versions
WHERE name LIKE '%[BT]%'
  AND effective = true;
```

```sql
-- CORRECT: Check subtype allows commercialization
SELECT * FROM item_versions
WHERE name LIKE '%[BT]%'
  AND effective = true
  AND deleted = false
  AND object_type IN ('BT-PRIMARY', 'BT-PREPARATION')  -- Exclude byproducts
  AND item_status != 'DORMANT';
```

### Wrong: Ignoring Version Status

```sql
-- WRONG: Not checking version status
SELECT bt.item_number
FROM item_versions bt
WHERE bt.object_type = 'BT-PRIMARY';
```

```sql
-- CORRECT: Only published non-expired versions can commercialize
SELECT bt.item_number
FROM item_versions bt
WHERE bt.object_type = 'BT-PRIMARY'
  AND bt.effective = true
  AND bt.deleted = false
  AND bt.version_status NOT IN ('DRAFT', 'EXPIRED');
```

### Wrong: Missing Linkage Type Filter

```sql
-- WRONG: May include other linkage types
SELECT * FROM commercialize_linkages;
```

```sql
-- CORRECT: Filter for commercialize linkage type
SELECT * FROM commercialize_linkages
WHERE linkage_type = 'commercialize';
```

## Naming Rules After Commercialization

When a benchtop item is commercialized multiple times:

1. First commercialization: "abc [BT]" becomes "abc"
2. Second commercialization: becomes "abc 2"
3. Third commercialization: becomes "abc 3"

**Special case for benchtop-preparation to ingredient:**
- Even the first commercialization adds increment: "abc 2", "abc 3", etc.
- This distinguishes it from the recipe-preparation commercialization

## Restricted UI Actions

In benchtop items:
- **Usages section**: No 'bulk edit' or 'swap component' buttons
- **Menu options**: Commercialize Item, Copy Item, Dormant Item, Delete This Version, Delete This Item
- **No** 'Commercialize Item' or 'Update Linked IDs' buttons for BT-Byproduct items

## Related Documentation

- [recipes-procedures.md](recipes-procedures.md) - Procedure definitions (shared with benchtop)
- [../core/item-master.md](../core/item-master.md) - Item versioning system
- [../core/bom-components.md](../core/bom-components.md) - BOM structure (benchtop follows same pattern)

## Source Documentation

- Confluence: [Benchtop Recipe](https://wonder.atlassian.net/wiki/spaces/3185017363/pages/4185096365) - Overview
- Confluence: [Benchtop Recipe Details](https://wonder.atlassian.net/wiki/spaces/3185017363/pages/4185030852) - Detailed specifications
- Confluence: [Commercialize Item](https://wonder.atlassian.net/wiki/spaces/3185017363/pages/4185292938) - Commercialization workflow

---

## Code References (Java Codebase)

> **Codebase**: `master-data-management-2`
> **Validated**: 2026-01-28

### Domain Models

- **Recipe**: `backend/domain-library/src/main/java/app/internalrecipe/item/innerclassview/Recipe.java`
  - Embedded in ItemVersion.recipe field
  - Key fields: `totalYield`, `yieldUnit`, `components`, `procedures`, `output`, `chefs`, `skillLevel`, `laborTime`
  - Benchtop-specific: `relatedBenchtopItemVersionId` - links commercialized recipe version to source benchtop version
  - **@Deprecated (5)**: `cost`, `costSource`, `applianceAndEquipment`, `price`, `kitchenLocationId` (relocated to ItemVersion level)

- **ItemVersion**: Contains `benchtopBomHeader` field for benchtop-specific BOM data
  - Field: `benchtop_bom_header` - BOM structure specifically for benchtop items

### Enums

- **NewObjectType**: `backend/domain-library/src/main/java/app/internalrecipe/item/innerclassview/NewObjectType.java`
  - Key values: `BENCHTOP`, `RECIPE`, `MENU`, `INGREDIENT`, `BY_PRODUCT`
  - **@Deprecated (2)**: `COMMON_STOCK_TOTE`, `MOBILE_SF`

- **ObjectSubType**: `backend/domain-library/src/main/java/app/internalrecipe/item/innerclassview/ObjectSubType.java`
  - Benchtop subtypes: `PRIMARY`, `PREPARATION`, `BY_PRODUCT` (all map to NewObjectType.BENCHTOP)
  - Each subtype links to allowed NewObjectType values via `objectTypes` field

### Service Layer

- **BOItemCommercializeService**: `backend/internal-recipe-service/src/main/java/app/internalrecipe/item/service/recipe/BOItemCommercializeService.java`
  - Core commercialization logic - creates recipe items from benchtop items

- **BOItemCommercializeVersionService**: `backend/internal-recipe-service/src/main/java/app/internalrecipe/item/service/recipe/BOItemCommercializeVersionService.java`
  - Version-level commercialization to existing draft

- **BOItemCommercializeRelationService**: `backend/internal-recipe-service/src/main/java/app/internalrecipe/item/service/recipe/BOItemCommercializeRelationService.java`
  - Manages benchtop-to-commercialized item linkages

### API Endpoints

- **BOItemCommercializeWebService**: `backend/internal-recipe-service-interface/src/main/java/app/internalrecipe/api/BOItemCommercializeWebService.java`
  - `POST /bo/v2/item/version/:id/commercialize` - Commercialize benchtop to new recipe
  - `PUT /bo/v2/item/version/:id/check-for-commercialize` - Validate commercialization requirements
  - `POST /bo/v2/item/version/:id/commercialize-to-draft-version/:commercializedItemNumber` - Commercialize to existing draft
  - `PUT /bo/v2/item/:itemNumber/list-commercialized-item` - List items commercialized from this benchtop

### Business Logic Patterns

- **Benchtop-to-Recipe Linkage**: `relatedBenchtopItemVersionId` in Recipe tracks source benchtop version
- **Subtype Restrictions**: PRIMARY/PREPARATION can commercialize; BY_PRODUCT cannot
- **Version Status Check**: Only published (non-draft, non-expired) benchtop versions can be commercialized
- **Dormancy Check**: Benchtop items and their sub-components cannot be dormant for commercialization
- **Naming Convention**: Benchtop items have `[BT]` suffix; removed during commercialization

### @Deprecated Field Summary

| Field | Location | Replacement |
|-------|----------|-------------|
| `cost` | Recipe | Relocated to ItemCostV2 |
| `costSource` | Recipe | Relocated to ItemCostV2 |
| `applianceAndEquipment` | Recipe | Relocated to ItemVersion.applianceAndEquipment |
| `price` | Recipe | Relocated to ItemVersion level |
| `kitchenLocationId` | Recipe | Relocated to ItemVersion level |
| `COMMON_STOCK_TOTE` | NewObjectType | Removed item type |
| `MOBILE_SF` | NewObjectType | Removed item type |
