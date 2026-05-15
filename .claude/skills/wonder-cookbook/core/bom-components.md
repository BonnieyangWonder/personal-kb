# BOM Components - Bill of Materials Structure

The BOM (Bill of Materials) system defines how to **produce one inventory unit** of an item. It specifies which child items, quantities, and units are needed.

**Key Concept**: BOM is a **tree/hierarchical data structure** - items in a BOM can themselves have BOMs, creating nested dependencies that may require recursive queries to fully expand.

**Which items have BOMs?** All item types **except** 5* (ingredients) and 9* (non-food) can have BOMs. This includes:
- 80* Menu items and commercial recipes
- 88* Packaged goods
- 3* Benchtop recipes (R&D reference only)

---

## Essential Filter (ALWAYS USE)

When querying BOM data, **always** include filters for deleted items:

```sql
WHERE effective = true
  AND deleted = false
  AND item_status != 'DORMANT'
```

---

## Two Ways to Access BOM Data

There are **two patterns** for accessing BOM data in Cookbook:

| Pattern | Source | Best For |
|---------|--------|----------|
| **Nested JSON** (Recommended) | `item_versions.bom_header.bom_lines` | Quick lookups, single-item analysis |
| **Separate Tables** | `bom_headers` + `bom_lines` tables | Cross-item analysis, bulk queries |

### Pattern 1: Nested JSON in item_versions (RECOMMENDED)

The **primary BOM access pattern** uses the nested JSON structure in `item_versions`. BOM data is stored as JSON in the `bom_header` field, with `bom_lines` as a nested array.

```sql
-- PRIMARY PATTERN: Extract BOM from nested JSON
SELECT
  m.item_number,
  m.name,
  JSON_VALUE(bom_line, '$.item_number') AS component_item,
  SAFE_CAST(JSON_EXTRACT_SCALAR(bom_line, '$.quantity') AS FLOAT64) AS quantity,
  JSON_VALUE(bom_line, '$.uom') AS uom,
  JSON_VALUE(bom_line, '$.object_type') AS component_type
FROM `secure-recipe-prod.recipe_v2.item_versions` m,
UNNEST(JSON_EXTRACT_ARRAY(m.bom_header, '$.bom_lines')) AS bom_line
WHERE m.effective = true
  AND m.deleted = false
  AND m.item_status != 'DORMANT'
  AND m.item_number = '8009068'  -- Your menu item
```

**BOM Line JSON Fields**:
| JSON Path | Description |
|-----------|-------------|
| `$.item_number` | Component item number |
| `$.quantity` | Quantity needed per unit |
| `$.uom` | Unit of measure |
| `$.object_type` | Component's object type |

**Advantages**:
- Single table query, no joins required
- Atomic - BOM and item metadata always consistent
- Faster for single-item lookups

### Pattern 2: Separate Tables (For Bulk Analysis)

Use `bom_headers` and `bom_lines` tables when you need to analyze BOMs across many items.

---

## Separate BOM Tables

### bom_headers

Top-level records defining which items have BOMs. One header per item version.

```sql
-- Key fields
item_number              STRING    -- Item ID (e.g., '8009068')
item_version_id          STRING    -- UUID referencing item_versions._id
id                       STRING    -- BOM header ID (format: item_number + version suffix)
name                     STRING    -- BOM name (typically matches item name)
is_active                BOOLEAN   -- Whether BOM is currently active
service_start_time       DATETIME  -- BOM versioning start (when this BOM becomes effective)
service_end_time         DATETIME  -- BOM versioning end (when this BOM expires)
object_type              STRING    -- Parent item's object type (MENU, PACKAGED, RECIPE, etc.)
object_sub_type          STRING    -- Parent item's sub-type
formula_batch_size       STRING    -- Production batch size
reason_for_change        STRING    -- Change documentation
bom_lines                STRING    -- JSON array of BOM line items (use bom_lines table instead)
-- Audit fields
created_by               STRING    -- User who created
created_time             DATETIME  -- Creation timestamp
updated_by               STRING    -- User who last modified
updated_time             DATETIME  -- Last modification timestamp
```

### bom_lines

Individual component lines within a BOM. Each line represents one ingredient, packaging item, or garnish.

```sql
-- Key fields (identifiers)
bom_header_item_number      STRING    -- FK to bom_headers.item_number (parent item)
bom_header_item_version_id  STRING    -- FK to bom_headers.item_version_id
bom_header_id               STRING    -- FK to bom_headers.id
bom_line_item_number        STRING    -- Component item ID (child item)
bom_line_item_version_id    STRING    -- Component's item version ID

-- Quantity and cost fields
quantity                    FLOAT64   -- Amount needed per inventory unit of parent
unit                        STRING    -- Unit of measure (ea, g, oz, lb, kg)
cost                        FLOAT64   -- Component cost contribution
item_cost_sources           STRING    -- Source of cost data (e.g., 'STANDARD_COST')
scrap_yield                 FLOAT64   -- Yield factor accounting for waste/loss (NULL if no scrap)

-- Inventory and availability flags
manage_inventory            BOOLEAN   -- CRITICAL: true=REQUIRED for availability, false=OPTIONAL
no_requires_packaging       BOOLEAN   -- Whether component requires packaging

-- Supply chain fields
lead_time_day               INTEGER   -- Lead time in days for procurement

-- Service window (versioning)
service_start_time          DATETIME  -- When this component line became active
service_end_time            DATETIME  -- When this component line expires

-- Audit fields
updated_time                DATETIME  -- Last modification timestamp
```

## Required vs Optional Components

**THE KEY FIELD**: `bom_lines.manage_inventory` determines whether a component affects menu item availability. In Cookbook UI, this is labeled as **"Used to determine Menu item's Availability?"**

| `manage_inventory` | Impact | Examples |
|-------------------|--------|----------|
| `true` | **REQUIRED** - Menu item goes out of stock if unavailable | Proteins, produce, signature sauces |
| `false` | **OPTIONAL** - Does not affect availability | Packaging, garnishes, shared ingredients |

**Important**: The `manage_inventory` flag is inherited from the stockable item level and flows through the "Transferred BOM" logic in Cookbook. When Pantry checks availability, only components with `manage_inventory = true` can trigger an out-of-stock condition.

## Join Pattern

```sql
-- Menu item to components relationship
bom_headers.item_number = bom_lines.bom_header_item_number
```

**Note**: Always include `AND bh.is_active = true` to exclude archived BOMs, and join to items with `deleted = false`.

## Query Patterns

### Get Current Recipe with Required/Optional Flags

```sql
SELECT DISTINCT
  bh.item_number as menu_item_id,
  ei.name as menu_item_name,
  bl.bom_line_item_number as component_id,
  ei_comp.name as component_name,
  bl.manage_inventory as is_required_for_service,
  CASE
    WHEN bl.manage_inventory = true THEN 'REQUIRED'
    ELSE 'OPTIONAL'
  END as requirement,
  bl.quantity,
  bl.unit
FROM `secure-recipe-prod.recipe_v2.bom_headers` bh
INNER JOIN `secure-recipe-prod.recipe_v2.bom_lines` bl
  ON bh.item_number = bl.bom_header_item_number
LEFT JOIN `secure-recipe-prod.recipe_v2.effective_items` ei
  ON bh.item_number = CAST(ei.item_number AS STRING)
  AND ei.deleted = false
LEFT JOIN `secure-recipe-prod.recipe_v2.effective_items` ei_comp
  ON CAST(bl.bom_line_item_number AS STRING) = CAST(ei_comp.item_number AS STRING)
  AND ei_comp.deleted = false
WHERE bh.is_active = true
  AND bh.item_number = '8009068'  -- Your menu item ID
  -- CRITICAL: Filter to current service window
  AND CURRENT_TIMESTAMP() BETWEEN TIMESTAMP(bl.service_start_time) AND TIMESTAMP(bl.service_end_time)
ORDER BY bl.manage_inventory DESC, component_id;
```

### Get Only Required Components (Availability Blockers)

```sql
SELECT DISTINCT
  bl.bom_line_item_number as component_id,
  ei.name as component_name,
  bl.quantity,
  bl.unit
FROM `secure-recipe-prod.recipe_v2.bom_headers` bh
INNER JOIN `secure-recipe-prod.recipe_v2.bom_lines` bl
  ON bh.item_number = bl.bom_header_item_number
LEFT JOIN `secure-recipe-prod.recipe_v2.effective_items` ei
  ON CAST(bl.bom_line_item_number AS STRING) = CAST(ei.item_number AS STRING)
  AND ei.deleted = false
WHERE bh.is_active = true
  AND bh.item_number = '8009068'
  AND bl.manage_inventory = true  -- Only required components
  AND CURRENT_TIMESTAMP() BETWEEN TIMESTAMP(bl.service_start_time) AND TIMESTAMP(bl.service_end_time)
ORDER BY component_id;
```

### Calculate Total Recipe Cost

```sql
SELECT
  bh.item_number as menu_item_id,
  ei.name as menu_item_name,
  SUM(bl.cost) as total_component_cost,
  COUNT(DISTINCT bl.bom_line_item_number) as num_components,
  COUNT(DISTINCT CASE WHEN bl.manage_inventory = true THEN bl.bom_line_item_number END) as num_required
FROM `secure-recipe-prod.recipe_v2.bom_headers` bh
INNER JOIN `secure-recipe-prod.recipe_v2.bom_lines` bl
  ON bh.item_number = bl.bom_header_item_number
LEFT JOIN `secure-recipe-prod.recipe_v2.effective_items` ei
  ON bh.item_number = CAST(ei.item_number AS STRING)
  AND ei.deleted = false
WHERE bh.is_active = true
  AND bh.item_number = '8009068'
  AND CURRENT_TIMESTAMP() BETWEEN TIMESTAMP(bl.service_start_time) AND TIMESTAMP(bl.service_end_time)
GROUP BY bh.item_number, ei.name;
```

### Find All Menu Items Using a Specific Component

```sql
SELECT DISTINCT
  bh.item_number as menu_item_id,
  ei.name as menu_item_name,
  bl.manage_inventory as is_required
FROM `secure-recipe-prod.recipe_v2.bom_headers` bh
INNER JOIN `secure-recipe-prod.recipe_v2.bom_lines` bl
  ON bh.item_number = bl.bom_header_item_number
LEFT JOIN `secure-recipe-prod.recipe_v2.effective_items` ei
  ON bh.item_number = CAST(ei.item_number AS STRING)
  AND ei.deleted = false
WHERE bh.is_active = true
  AND bl.bom_line_item_number = '4000053'  -- Component ID (e.g., fries)
  AND CURRENT_TIMESTAMP() BETWEEN TIMESTAMP(bl.service_start_time) AND TIMESTAMP(bl.service_end_time)
ORDER BY menu_item_name;
```

## BOM Recursive Queries

Since BOM is a tree structure, components can themselves have BOMs. To expand the full dependency tree, use a recursive CTE.

### Full Multi-Level BOM Expansion

This comprehensive recursive query expands all levels of a BOM hierarchy with accumulated quantities:

```sql
-- BOM Multi-Level Recursive Query with Accumulated Quantities
-- Purpose: Query all levels of Bill of Materials (BOM) structure under a specific BOM header
-- Key Fields:
-- - level: Hierarchy level (1 = first level components, 2 = second level, etc.)
-- - accumulated_quantity: Cumulative quantity (considers multiplication across all parent levels)
-- - path: Material path, showing the complete chain from top level to current item

WITH RECURSIVE bom_hierarchy AS (
  -- Level 1: Direct child items of the starting BOM header (anchor query)
  SELECT
    bom_header_id,
    bom_header_item_number,
    bom_header_item_version_id,
    bom_line_item_number,
    bom_line_item_version_id,
    service_start_time,
    service_end_time,
    quantity,
    unit,
    cost,
    manage_inventory,
    lead_time_day,
    scrap_yield,
    no_requires_packaging,
    1 AS level,  -- Hierarchy level
    CAST(bom_line_item_number AS STRING) AS path,  -- Path tracking
    quantity AS accumulated_quantity  -- Cumulative quantity
  FROM `secure-recipe-prod.recipe_v2.bom_lines`
  WHERE bom_header_item_number = '8000016'  -- Replace with your target BOM header item number

  UNION ALL

  -- Recursive part: Find next level of child items
  SELECT
    child.bom_header_id,
    child.bom_header_item_number,
    child.bom_header_item_version_id,
    child.bom_line_item_number,
    child.bom_line_item_version_id,
    child.service_start_time,
    child.service_end_time,
    child.quantity,
    child.unit,
    child.cost,
    child.manage_inventory,
    child.lead_time_day,
    child.scrap_yield,
    child.no_requires_packaging,
    parent.level + 1,
    CONCAT(parent.path, ' > ', child.bom_line_item_number),  -- Build material path
    parent.accumulated_quantity * child.quantity  -- Cumulative = parent × current
  FROM `secure-recipe-prod.recipe_v2.bom_lines` child
  INNER JOIN bom_hierarchy parent
    ON child.bom_header_item_number = parent.bom_line_item_number
  WHERE parent.level < 10  -- Limit maximum recursion depth
)
SELECT
  level,
  bom_header_item_number,
  bom_line_item_number,
  service_start_time,
  service_end_time,
  quantity,
  ROUND(accumulated_quantity, 4) AS accumulated_quantity,
  unit,
  cost,
  manage_inventory,
  lead_time_day,
  scrap_yield,
  path
FROM bom_hierarchy
ORDER BY level, bom_header_item_number, bom_line_item_number;
```

**Accumulated Quantity Calculation Example:**
- If item at Level 1 has quantity 892.8571g
- And that item's BOM has child with quantity 18.9125g
- Then accumulated_quantity = 892.8571 × 18.9125 = 16886.1599g

### Simple Recursive Query (Indented View)

For a simpler view with indentation:

```sql
-- Expand all levels of a BOM hierarchy
WITH RECURSIVE DependencyHierarchy AS (
    -- Base case: first-level components
    SELECT
        bom_header_item_number,
        bom_line_item_number AS item_number,
        CAST(NULL AS STRING) AS parent_item_number,
        1 AS level,
        quantity,
        unit
    FROM `secure-recipe-prod.recipe_v2.bom_lines`
    WHERE bom_header_item_number = '8009068'  -- Your menu item
      AND CURRENT_TIMESTAMP() BETWEEN TIMESTAMP(service_start_time) AND TIMESTAMP(service_end_time)

    UNION ALL

    -- Recursive case: components of components
    SELECT
        b.bom_header_item_number,
        b.bom_line_item_number,
        cte.item_number AS parent_item_number,
        cte.level + 1,
        b.quantity,
        b.unit
    FROM `secure-recipe-prod.recipe_v2.bom_lines` b
    JOIN DependencyHierarchy cte ON b.bom_header_item_number = cte.item_number
    WHERE cte.level < 10  -- Limit recursion depth
      AND CURRENT_TIMESTAMP() BETWEEN TIMESTAMP(b.service_start_time) AND TIMESTAMP(b.service_end_time)
)
SELECT
    LPAD('', (level - 1) * 2, '  ') || item_number AS indented_item,
    level,
    parent_item_number,
    quantity,
    unit
FROM DependencyHierarchy
ORDER BY level, parent_item_number, item_number;
```

### First Level BOM Only (All Menu Items)

For analyzing just the first level of BOM across all menu items:

```sql
WITH RECURSIVE bom_hierarchy AS (
  SELECT
    bom_header_item_number,
    bom_line_item_number,
    1 AS bom_level,
    quantity
  FROM `secure-recipe-prod.recipe_v2.bom_lines`

  UNION ALL

  SELECT
    child.bom_header_item_number,
    child.bom_line_item_number,
    parent.bom_level + 1,
    child.quantity
  FROM `secure-recipe-prod.recipe_v2.bom_lines` child
  INNER JOIN bom_hierarchy parent
    ON child.bom_header_item_number = parent.bom_line_item_number
  WHERE bom_level = 1  -- Only expand one more level
)
SELECT
  bom_header_item_number,
  bom_line_item_number,
  bom_level,
  t2.object_type,
  t2.item_status
FROM bom_hierarchy t1
LEFT JOIN `secure-recipe-prod.recipe_v2.item_versions` t2
  ON t1.bom_header_item_number = t2.item_number
WHERE t1.bom_level = 1
  AND t1.bom_header_item_number IS NOT NULL
  AND t2.object_type = 'MENU'
  AND t2.item_status NOT IN ('DORMANT')
  AND t2.deleted = false
  AND t2.sold_status = 'FOR_SALE';
```

## Critical Rules

1. **Prefer nested JSON pattern** for single-item BOM lookups (uses `item_versions.bom_header`)
2. **Always include `deleted = false`** when joining to item metadata
3. **Always filter `is_active = true`** on bom_headers to exclude archived BOMs
4. **Always filter by service window** to get current recipe (see [service-windows.md](service-windows.md))
5. **Use `manage_inventory` to distinguish required vs optional** components
6. **Use LEFT JOIN** when joining to item metadata tables to avoid losing BOM lines
7. **Use CAST for item_number joins** - types may differ between tables
8. **Use recursive CTEs** when you need to expand nested BOMs to find all leaf ingredients
9. **service_start_time and service_end_time are DATETIME** (not TIMESTAMP) - use `TIMESTAMP()` wrapper for comparisons

## BOM vs Component Distinction

Cookbook has two similar but distinct concepts:

| Concept | Purpose | Scope |
|---------|---------|-------|
| **BOM** (Bill of Materials) | How to **produce** one inventory unit | All item types except 5* and 9* |
| **Component** | How an item is **formed** (recipe structure) | Only ingredients, recipes, and by-products |

Key differences:
- BOM allows the same item only once per parent; Components allow the same item multiple times
- BOM defines production for one **inventory unit**; Component defines total yield production
- BOM is used by downstream systems (Pantry, KDS, etc.); Component is primarily for R&D/cost calculation

## Related Documentation

- [service-windows.md](service-windows.md) - Recipe versioning and time-based filtering
- [item-master.md](item-master.md) - Item types and metadata lookup
- [../cross-system/pantry-integration.md](../cross-system/pantry-integration.md) - Check if components are in stock

---

## Code References (Java Codebase)

> **Codebase**: `master-data-management-2`
> **Validated**: 2026-01-28

### Domain Models

- **BOMHeader**: `backend/domain-library/src/main/java/app/internalrecipe/item/innerclassview/BOMHeader.java`
  - Primary fields: `id`, `name`, `formulaBatchSize`, `reasonForChange`, `isActive`
  - Nested class `BomLine` contains: `itemNumber`, `itemVersionId`, `quantity`, `unit`, `manageInventory`, `scrapYield`, `cost`
  - Service window tracking via `usageItemVersionIds` and `usageItemVersionIdsByChangeStream`
  - Audit fields: `createdBy`, `createdTime`, `updatedBy`, `updatedTime`

- **BomLine** (inner class of BOMHeader): `backend/domain-library/src/main/java/app/internalrecipe/item/innerclassview/BOMHeader.java:74`
  - Key fields: `itemNumber`, `itemVersionId`, `quantity`, `unit`, `manageInventory`
  - `manageInventory` boolean determines required vs optional (maps to BigQuery `manage_inventory`)
  - `scrapYield` for waste/loss factor, `leadTimeDay` for procurement lead time
  - `packageSKUConfigs` for packaging SKU associations

- **PerBOMUnitCost**: `backend/domain-library/src/main/java/app/internalrecipe/item/innerclassview/PerBOMUnitCost.java`
  - Simple wrapper for per-BOM-unit cost calculation

### Service Layer

- **BOBOMService**: `backend/internal-recipe-service/src/main/java/app/internalrecipe/item/service/bomheader/BOBOMService.java`
  - `get(uuid)`: Retrieves BOM header by item version UUID
  - `bulkGetByItemNumber(request)`: Bulk retrieval by item numbers (filters `effective = true`)
  - `checkBeforeSave(id, itemVersionIds)`: Validates BOM lines before saving
  - `expandBOM(id)`: Expands BOM hierarchy for visualization

- **BOUpdateBOMService**: `backend/internal-recipe-service/src/main/java/app/internalrecipe/item/service/bomheader/BOUpdateBOMService.java`
  - Handles BOM updates with validation

- **CalculateBOMUsagesServiceV2**: `backend/internal-recipe-service/src/main/java/app/internalrecipe/item/service/usageitemversions/CalculateBOMUsagesServiceV2.java`
  - Calculates BOM usage relationships across items

- **BomHeaderService**: `backend/recipe-service-v2/src/main/java/app/recipev2/item/service/BomHeaderService.java`
  - Recipe service v2 BOM operations

### API Endpoints (Internal Recipe Service)

- **BOBOMHeaderWebService**: `backend/internal-recipe-service-interface/src/main/java/app/internalrecipe/api/BOBOMHeaderWebService.java`
  - `GET /bo/item/version/:uuid/bom-header` - Get BOM header
  - `POST /bo/item/version/:uuid/bom-header` - Create BOM header
  - `PUT /bo/item/version/:uuid/bom-header` - Update BOM header
  - `PUT /bo/item/version/:uuid/bom-header/manage-inventory` - Update manageInventory flags
  - `GET /bo/item/version/:uuid/expand-bom` - Expand full BOM hierarchy
  - `PUT /bo/item/version/bom-header/bulk-get-by-item-number` - Bulk get by item numbers

### Frontend API (Recipe Site)

- **ItemBOMController**: `frontend/recipe-site/src/main/java/app/recipe/web/controller/item/ItemBOMController.java`
  - `downloadAllV2()` → `/v2/excel/item-bom/download` - Export all BOMs
  - `downloadLatestV2()` → `/v2/excel/item-bom/latest/download` - Export latest BOMs
  - `downloadTruckItemV2()` → `/v2/excel/item-bom/download-truck-item` - Export truck item BOMs

### MongoDB Operations

- **ItemVersionCollectionManager**: `backend/internal-recipe-service/src/main/java/collectionmanager/ItemVersionCollectionManager.java`
  - Collection: `item_versions` (BOM stored as embedded document in `bom_header` field)
  - Key queries filter on: `effective = true`, `bom_header != null`, `item_number`

### Business Logic Patterns

- **Required vs Optional Logic**: Implemented via `BomLine.manageInventory` boolean
  - `true` = Required for menu item availability
  - `false` = Optional (packaging, garnishes)
- **Service Window Filtering**: BOM validity determined by `serviceStartTime`/`serviceEndTime` in parent ItemVersion
- **BOM Export to BigQuery**: MongoDB aggregation exports to `bom_headers` and `bom_lines` tables

### @Deprecated Fields

No @Deprecated annotations found in BOM-related domain classes.
