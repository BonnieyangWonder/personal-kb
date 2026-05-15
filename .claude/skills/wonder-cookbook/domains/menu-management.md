# Menu Management - Collections of Menu Items

The menu management system organizes truck and original recipe items into named collections for specific concepts (restaurants/brands). Menus enable recipe scaling, bulk exports, and ingredient reporting for kitchen operations.

Menus are managed through the Cookbook UI and group items by concept for R&D planning, production, and reporting purposes.

---

## Essential Filter (ALWAYS USE)

When querying menus, filter to active menus only:

```sql
-- Most menus have NULL status, so include them
WHERE (status IS NULL OR status != 'DORMANT')
```

---

## Menu Status Lifecycle

| Status | Description |
|--------|-------------|
| `R&D` | Menu in development, not yet active |
| `Active` | Menu is currently in production |
| `Dormant` | Menu is no longer active |
| `NULL` | Legacy menus (treat as active) |

---

## Core Table

### menus

Collections of menu items organized by concept.

**Table**: `wonder-recipe-prod.recipe_v2.menus`

```sql
-- Key identification fields
_id                      STRING    -- Unique menu UUID
name                     STRING    -- Menu name (up to 250 chars, unique)
status                   STRING    -- R&D, Active, Dormant, or NULL
stage                    STRING    -- Menu stage (if applicable)

-- Relationships
concept_ids              STRING    -- JSON array of base64-encoded concept IDs
items                    STRING    -- JSON array of menu item objects
usage_items              STRING    -- JSON array of usage items

-- Date fields
launch_time              DATETIME  -- When menu launches (optional)
end_time                 DATETIME  -- When menu ends (optional)

-- Cost tracking
last_cost_calculate_time DATETIME  -- Last cost calculation timestamp

-- Status tracking
status_transition_info   STRING    -- Status change history

-- Audit fields
created_by               STRING    -- User who created
created_time             DATETIME  -- Creation timestamp
updated_by               STRING    -- Last user to update
updated_user_id          STRING    -- Last updater's user ID
updated_time             DATETIME  -- Last update timestamp
_sync_time               DATETIME  -- BigQuery sync timestamp
```

### concepts

Restaurant/brand concepts that menus are associated with.

**Table**: `wonder-recipe-prod.recipe_v2.concepts`

```sql
_id                STRING    -- Unique concept UUID
name               STRING    -- Concept display name (e.g., "JBird by Jonathan Waxman")
cdt_lead           STRING    -- CDT team lead
rd_lead            STRING    -- R&D team lead
restaurant_ids     STRING    -- JSON array of associated restaurant IDs
brand_ids          STRING    -- JSON array of associated brand IDs
is_global          BOOLEAN   -- Whether concept is global
deleted            BOOLEAN   -- Soft delete flag
created_by         STRING    -- Creator
created_time       DATETIME  -- Creation timestamp
updated_by         STRING    -- Last updater
updated_time       DATETIME  -- Last update timestamp
_sync_time         DATETIME  -- BigQuery sync timestamp
```

---

## Menu Items Structure

The `items` field contains a JSON array of menu item objects:

```json
{
  "item_id": "uuid",           // Item version UUID
  "item_number": "8009068",    // Item number (80* prefix for menu items)
  "is_new": null,              // Whether item is newly added
  "added_time": "2023-04-04T15:39:10.555000",  // When added to menu
  "added_by": "User Name"      // Who added the item
}
```

---

## Query Patterns

### Get All Menus with Item Counts

```sql
SELECT
  m._id as menu_id,
  m.name as menu_name,
  m.status,
  m.launch_time,
  m.end_time,
  JSON_ARRAY_LENGTH(m.items) as item_count,
  m.updated_time
FROM `wonder-recipe-prod.recipe_v2.menus` m
WHERE (m.status IS NULL OR m.status != 'DORMANT')
ORDER BY m.updated_time DESC
LIMIT 50;
```

### Get Menu Items with Details

```sql
WITH menu_items AS (
  SELECT
    m._id as menu_id,
    m.name as menu_name,
    JSON_VALUE(item, '$.item_number') as item_number,
    JSON_VALUE(item, '$.item_id') as item_version_id,
    JSON_VALUE(item, '$.added_by') as added_by,
    TIMESTAMP(JSON_VALUE(item, '$.added_time')) as added_time
  FROM `wonder-recipe-prod.recipe_v2.menus` m,
  UNNEST(JSON_EXTRACT_ARRAY(m.items)) as item
  WHERE m.name = 'Your Menu Name'
)
SELECT
  mi.menu_name,
  mi.item_number,
  ei.name as item_name,
  ei.item_status,
  mi.added_by,
  mi.added_time
FROM menu_items mi
LEFT JOIN `secure-recipe-prod.recipe_v2.effective_items` ei
  ON mi.item_number = CAST(ei.item_number AS STRING)
  AND ei.deleted = false
ORDER BY mi.item_number;
```

### Get Menus by Concept

```sql
WITH concept_menus AS (
  SELECT
    m._id as menu_id,
    m.name as menu_name,
    m.status,
    JSON_VALUE(concept_id, '$') as concept_id_encoded
  FROM `wonder-recipe-prod.recipe_v2.menus` m,
  UNNEST(JSON_EXTRACT_ARRAY(m.concept_ids)) as concept_id
  WHERE (m.status IS NULL OR m.status != 'DORMANT')
)
SELECT
  c.name as concept_name,
  cm.menu_name,
  cm.status
FROM concept_menus cm
LEFT JOIN `wonder-recipe-prod.recipe_v2.concepts` c
  ON c._id = cm.concept_id_encoded
  OR CONCAT('concept:', c._id) = cm.concept_id_encoded
WHERE c.deleted = false
ORDER BY c.name, cm.menu_name;
```

### List All Active Menus

```sql
SELECT
  m._id,
  m.name,
  m.status,
  m.launch_time,
  m.end_time,
  JSON_ARRAY_LENGTH(m.items) as item_count,
  m.updated_by,
  m.updated_time
FROM `wonder-recipe-prod.recipe_v2.menus` m
WHERE (m.status IS NULL OR m.status = 'Active')
  AND (m.end_time IS NULL OR m.end_time > CURRENT_TIMESTAMP())
ORDER BY m.name;
```

### Find Menus Containing a Specific Item

```sql
SELECT
  m._id as menu_id,
  m.name as menu_name,
  m.status,
  JSON_VALUE(item, '$.added_time') as added_to_menu
FROM `wonder-recipe-prod.recipe_v2.menus` m,
UNNEST(JSON_EXTRACT_ARRAY(m.items)) as item
WHERE JSON_VALUE(item, '$.item_number') = '8009068'
ORDER BY m.updated_time DESC;
```

### Get Menu with Full Recipe Details

```sql
WITH menu_data AS (
  SELECT
    m._id as menu_id,
    m.name as menu_name,
    JSON_VALUE(item, '$.item_number') as item_number
  FROM `wonder-recipe-prod.recipe_v2.menus` m,
  UNNEST(JSON_EXTRACT_ARRAY(m.items)) as item
  WHERE m._id = 'your-menu-uuid'
)
SELECT
  md.menu_name,
  md.item_number,
  ei.name as item_name,
  ei.object_type,
  ei.item_status,
  JSON_VALUE(ei.bom_header, '$.bom_lines') IS NOT NULL as has_bom
FROM menu_data md
LEFT JOIN `secure-recipe-prod.recipe_v2.effective_items` ei
  ON md.item_number = CAST(ei.item_number AS STRING)
  AND ei.deleted = false
ORDER BY ei.name;
```

### Analyze Menu Item Distribution by Type

```sql
WITH menu_items AS (
  SELECT
    m.name as menu_name,
    JSON_VALUE(item, '$.item_number') as item_number
  FROM `wonder-recipe-prod.recipe_v2.menus` m,
  UNNEST(JSON_EXTRACT_ARRAY(m.items)) as item
  WHERE (m.status IS NULL OR m.status = 'Active')
)
SELECT
  mi.menu_name,
  COUNT(*) as total_items,
  COUNTIF(ei.object_type = 'MENU') as menu_items,
  COUNTIF(ei.object_type = 'ORIGINAL') as original_items
FROM menu_items mi
LEFT JOIN `secure-recipe-prod.recipe_v2.effective_items` ei
  ON mi.item_number = CAST(ei.item_number AS STRING)
  AND ei.deleted = false
GROUP BY mi.menu_name
ORDER BY total_items DESC;
```

---

## Menu Operations (from Confluence)

### Available Actions

| Action | Description |
|--------|-------------|
| **Create Menu** | Create new menu with name, concepts, launch/end dates |
| **Edit Menu** | Update menu name, concepts, or dates |
| **Delete Menu** | Hard delete menu and all item mappings (requires typing "DELETE") |
| **Add Items** | Add truck/original recipes to menu |
| **Remove Items** | Remove items from menu (bulk or individual) |

### Export Options

Menus support several export formats:

| Export Type | File Format | Description |
|-------------|-------------|-------------|
| **Export Menu** | PDF | Recipe instructions for all items including subrecipes |
| **Kitting Instructions** | PDF | Truck recipe kitting procedures |
| **Assembly Instructions** | PDF | Post-cooking assembly procedures |
| **Ingredients Report** | XLSX | All ingredients used across menu recipes |
| **Scale Recipe** | PDF/XLSX | Scaled recipe quantities and ingredients |

### Recipe Scaling

Menus support bulk recipe scaling with two modes:

1. **Scale All Recipes**: Apply single multiplier to all selected recipes
2. **Scale Each Recipe**: Individual scaling per recipe (multiply or scale to yield)

Scaling options:
- **Scale on Active Version**: Uses currently active recipe version
- **Scale on Latest Version**: Uses most recent version (for R&D)

**Note**: Byproduct recipes are excluded from scaling but can be included in exports without scaling.

---

## Menu-Recipe Relationships

Menus contain **truck items** (80* prefix) and **original items** prepared at Wonder HDRs. When a menu is exported or scaled:

1. **Truck recipes**: Main items prepared on Wonder trucks/HDRs
2. **Subrecipes**: Components nested within truck recipes are included
3. **Ingredients**: All components exploded to lowest level

### Subrecipe Deduplication

When exporting recipes:
- Subrecipes appearing in multiple parent recipes are printed once at first appearance
- In scaling, subrecipe usage is aggregated across all parent recipes

---

## Integration with Other Systems

### Link to Items

```sql
-- Join menu items to effective_items for full recipe data
LEFT JOIN `secure-recipe-prod.recipe_v2.effective_items` ei
  ON JSON_VALUE(item, '$.item_number') = CAST(ei.item_number AS STRING)
  AND ei.deleted = false
```

### Link to Concepts

```sql
-- Concepts determine which restaurants/brands use this menu
LEFT JOIN `wonder-recipe-prod.recipe_v2.concepts` c
  ON c._id = concept_id_from_menu
  AND c.deleted = false
```

### Menu Cost Analysis

The `last_cost_calculate_time` tracks when menu costs were last computed. Costs roll up from component ingredients through the BOM hierarchy.

---

## Common Pitfalls

### Concept IDs Are Encoded

The `concept_ids` field contains base64-encoded or prefixed values, not raw UUIDs:

```sql
-- Concept IDs may be in different formats
-- Format 1: Base64 encoded (e.g., "Y29uY2VwdDozNzc=")
-- Format 2: UUID (e.g., "90becab5-6b0d-450f-ae97-368c413d0ec9")
```

### Items Field Is JSON

The `items` field is a JSON string, not an array column:

```sql
-- Correct: Parse JSON array
JSON_EXTRACT_ARRAY(m.items) as item

-- Wrong: Treat as native array
UNNEST(m.items)  -- This will fail
```

### Most Menus Have NULL Status

Many menus have NULL status rather than 'Active':

```sql
-- Correct: Include NULL status
WHERE (m.status IS NULL OR m.status = 'Active')

-- Wrong: Filter only 'Active'
WHERE m.status = 'Active'  -- Misses most menus
```

---

## Related Documentation

- [../core/bom-components.md](../core/bom-components.md) - Recipe BOMs for menu items
- [../core/item-master.md](../core/item-master.md) - Item master data
- [cost-pricing.md](cost-pricing.md) - Menu item costs and pricing
- [recipes-procedures.md](recipes-procedures.md) - Recipe cooking procedures

---

## Code References (Java Codebase)

> **Codebase**: `master-data-management-2`
> **Validated**: 2026-01-28

### Domain Models

- **Menu**: `backend/domain-library/src/main/java/app/internalrecipe/menu/Menu.java`
  - MongoDB collection: `menus`
  - Key fields: `name`, `conceptIds`, `items` (List<Item>), `usageItems` (List<UsageItem>), `launchTime`, `endTime`, `stage`, `status`, `lastCostCalculateTime`
  - Nested classes: `Item` (itemId, itemNumber, isNew, addedTime, addedBy), `UsageItem`, `StatusTransitionInfo`
  - **@Deprecated (1)**: `statusTransitionInfo` field - stage transitions tracked in MenuStageTransitionLog

- **MenuStageTransitionLog**: `backend/domain-library/src/main/java/app/internalrecipe/menu/MenuStageTransitionLog.java`
  - MongoDB collection: `menu_stage_transition_logs`
  - Key fields: `menuId`, `fromStage`, `toStage`, `isRollBack`, `dashboardSnapShot`, `errorMessage`
  - Tracks menu stage transitions with rollback support

- **Concept**: `backend/domain-library/src/main/java/app/internalrecipe/concept/Concept.java`
  - MongoDB collection: `concepts`
  - Key fields: `name`, `cdtLead`, `rdLead`, `restaurantIds`, `brandIds`, `isGlobal`, `deleted`
  - Restaurant/brand concepts that menus are associated with

### Enums

- **MenuStatus**: `backend/domain-library/src/main/java/app/internalrecipe/menu/MenuStatus.java`
  - Values: `R_AND_D` ("R&D"), `ACTIVE` ("ACTIVE"), `DORMANT` ("DORMANT")

- **MenuStage**: `backend/domain-library/src/main/java/app/internalrecipe/menu/MenuStage.java`
  - Values: `DISCOVERY_AND_DUE_DILIGENCE`, `TESTING_AND_FINAL_DEVELOPMENT`, `COMMERCIALIZATION`, `IMPLEMENTATION`, `PILOT`
  - Note: Order of values matters for stage progression

### Service Layer

- **BOMenuService**: `backend/internal-recipe-service/src/main/java/app/internalrecipe/menu/service/BOMenuService.java`
  - Menu CRUD operations

- **BOMenuDashboardService**: `backend/internal-recipe-service/src/main/java/app/internalrecipe/menu/service/BOMenuDashboardService.java`
  - Dashboard view of menu items and stages

- **BOMenuStageTransitionService**: `backend/internal-recipe-service/src/main/java/app/internalrecipe/menu/service/BOMenuStageTransitionService.java`
  - Stage progression and rollback

### API Endpoints

- **BOMenuWebService**: `backend/internal-recipe-service-interface/src/main/java/app/internalrecipe/api/BOMenuWebService.java`
  - `POST /bo/menu` - Create new menu
  - `PUT /bo/menu` - Search menus
  - `PUT /bo/v2/menu` - Search menus V2
  - `GET /bo/menu/:id` - Get menu by ID
  - `PUT /bo/menu/:id` - Update menu
  - `DELETE /bo/menu/:id` - Delete menu
  - `PUT /bo/menu/batch-delete` - Batch delete menus
  - `POST /bo/menu/item` - Bulk add items to menu
  - `DELETE /bo/menu/:id/item/:itemNumber` - Remove item from menu
  - `PUT /bo/menu/:id/item` - Bulk remove items
  - `PUT /bo/menu/:id/items` - Search menu items
  - `PUT /bo/menu/:id/list/items` - List menu items
  - `PUT /bo/menu/sub-items` - Search sub-items
  - `GET /bo/menu/:id/dashboard/header` - Dashboard header
  - `PUT /bo/menu/:id/dashboard/menu-items` - List dashboard menu items
  - `PUT /bo/menu/:id/dashboard/all-items` - Search all dashboard items
  - `PUT /bo/menu/:id/stage/advance-to-next` - Advance to next stage
  - `PUT /bo/menu/stage/roll-back` - Roll back stage
  - `PUT /bo/menu/:id/item/cost/batch-calculate` - Batch calculate costs

### Business Logic Patterns

- **Stage Progression**: Menus advance through stages in order; rollbacks create transition logs
- **Concept Association**: Menus link to concepts (restaurants/brands) via conceptIds
- **Item Management**: Items added/removed with audit trail (addedBy, addedTime)
- **Cost Calculation**: lastCostCalculateTime tracks when costs were computed

### @Deprecated Field Summary

| Field | Location | Replacement |
|-------|----------|-------------|
| `statusTransitionInfo` | Menu | Use MenuStageTransitionLog for stage tracking |
