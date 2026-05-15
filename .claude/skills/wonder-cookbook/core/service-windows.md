# Service Windows - Recipe Versioning

Cookbook uses **service windows** (`service_start_time`, `service_end_time`) to track recipe changes over time. The same menu item can have different ingredients in different time periods without creating new item IDs.

## How Service Windows Work

Each BOM line has a service window defining when that component is active:

```
[service_start_time, service_end_time)  -- Left-inclusive, right-exclusive
```

**Key principles**:
- Multiple versions of the same component can exist with non-overlapping windows
- Far future end dates (2100-01-01) indicate currently active components
- Historical windows enable cost/ingredient analysis for past periods

## Example: Recipe Evolution

```
Menu Item: Cheese Fries (8009068)
Component: Fries

Timeline:
8800311  [Nov 2023 → Dec 2023]  French Fries (Global) [Kit]
8805681  [Dec 2023 → Jul 2025]  3/8th Skin On French Fries (Global) [Kit]
5182267  [Jul 2025 → Oct 2025]  Fries, French, Fridge Friendly (INGREDIENT)
4000053  [Oct 2025 → 2100]      Fries, French, Fridge Friendly ← CURRENT
```

## Query Patterns

### Get Current Recipe Only (Most Common)

```sql
-- Returns only components active right now
SELECT
  bl.bom_line_item_number as component_id,
  ei.name as component_name,
  bl.quantity,
  bl.unit
FROM `secure-recipe-prod.recipe_v2.bom_headers` bh
INNER JOIN `secure-recipe-prod.recipe_v2.bom_lines` bl
  ON bh.item_number = bl.bom_header_item_number
LEFT JOIN `secure-recipe-prod.recipe_v2.effective_items` ei
  ON CAST(bl.bom_line_item_number AS STRING) = CAST(ei.item_number AS STRING)
WHERE bh.is_active = true
  AND bh.item_number = '8009068'
  -- CRITICAL: Filter to current service window
  AND CURRENT_TIMESTAMP() BETWEEN TIMESTAMP(bl.service_start_time) AND TIMESTAMP(bl.service_end_time)
ORDER BY bl.bom_line_item_number;
```

### Get Recipe at a Specific Date

```sql
-- Recipe as it was on July 1, 2025
SELECT
  bl.bom_line_item_number as component_id,
  ei.name as component_name,
  bl.quantity,
  bl.unit
FROM `secure-recipe-prod.recipe_v2.bom_headers` bh
INNER JOIN `secure-recipe-prod.recipe_v2.bom_lines` bl
  ON bh.item_number = bl.bom_header_item_number
LEFT JOIN `secure-recipe-prod.recipe_v2.effective_items` ei
  ON CAST(bl.bom_line_item_number AS STRING) = CAST(ei.item_number AS STRING)
WHERE bh.is_active = true
  AND bh.item_number = '8009068'
  AND TIMESTAMP('2025-07-01') BETWEEN TIMESTAMP(bl.service_start_time) AND TIMESTAMP(bl.service_end_time)
ORDER BY bl.bom_line_item_number;
```

### View Full Recipe History

```sql
-- All component versions over time (no service window filter)
SELECT
  bl.bom_line_item_number as component_id,
  ei.name as component_name,
  bl.service_start_time,
  bl.service_end_time,
  bl.manage_inventory as is_required,
  bl.quantity,
  bl.unit,
  CASE
    WHEN CURRENT_TIMESTAMP() BETWEEN TIMESTAMP(bl.service_start_time) AND TIMESTAMP(bl.service_end_time)
    THEN 'CURRENT'
    WHEN CURRENT_TIMESTAMP() > TIMESTAMP(bl.service_end_time)
    THEN 'EXPIRED'
    ELSE 'FUTURE'
  END as status
FROM `secure-recipe-prod.recipe_v2.bom_headers` bh
INNER JOIN `secure-recipe-prod.recipe_v2.bom_lines` bl
  ON bh.item_number = bl.bom_header_item_number
LEFT JOIN `secure-recipe-prod.recipe_v2.effective_items` ei
  ON CAST(bl.bom_line_item_number AS STRING) = CAST(ei.item_number AS STRING)
WHERE bh.is_active = true
  AND bh.item_number = '8009068'
ORDER BY bl.service_start_time DESC, bl.bom_line_item_number;
```

### Find Recipe Changes in Date Range

```sql
-- Components that changed during Q4 2025
SELECT
  bh.item_number as menu_item_id,
  ei_menu.name as menu_item_name,
  bl.bom_line_item_number as component_id,
  ei_comp.name as component_name,
  bl.service_start_time,
  bl.service_end_time,
  CASE
    WHEN bl.service_start_time >= '2025-10-01' THEN 'ADDED'
    WHEN bl.service_end_time BETWEEN '2025-10-01' AND '2025-12-31' THEN 'REMOVED'
    ELSE 'CHANGED'
  END as change_type
FROM `secure-recipe-prod.recipe_v2.bom_headers` bh
INNER JOIN `secure-recipe-prod.recipe_v2.bom_lines` bl
  ON bh.item_number = bl.bom_header_item_number
LEFT JOIN `secure-recipe-prod.recipe_v2.effective_items` ei_menu
  ON bh.item_number = CAST(ei_menu.item_number AS STRING)
LEFT JOIN `secure-recipe-prod.recipe_v2.effective_items` ei_comp
  ON CAST(bl.bom_line_item_number AS STRING) = CAST(ei_comp.item_number AS STRING)
WHERE bh.is_active = true
  AND (
    -- Started in Q4 2025
    (bl.service_start_time >= '2025-10-01' AND bl.service_start_time < '2026-01-01')
    OR
    -- Ended in Q4 2025
    (bl.service_end_time >= '2025-10-01' AND bl.service_end_time < '2026-01-01')
  )
ORDER BY menu_item_name, bl.service_start_time;
```

### Compare Recipe Between Two Dates

```sql
-- Recipe comparison: before and after a specific date
WITH recipe_before AS (
  SELECT bl.bom_line_item_number
  FROM `secure-recipe-prod.recipe_v2.bom_headers` bh
  INNER JOIN `secure-recipe-prod.recipe_v2.bom_lines` bl
    ON bh.item_number = bl.bom_header_item_number
  WHERE bh.is_active = true
    AND bh.item_number = '8009068'
    AND TIMESTAMP('2025-06-01') BETWEEN TIMESTAMP(bl.service_start_time) AND TIMESTAMP(bl.service_end_time)
),
recipe_after AS (
  SELECT bl.bom_line_item_number
  FROM `secure-recipe-prod.recipe_v2.bom_headers` bh
  INNER JOIN `secure-recipe-prod.recipe_v2.bom_lines` bl
    ON bh.item_number = bl.bom_header_item_number
  WHERE bh.is_active = true
    AND bh.item_number = '8009068'
    AND TIMESTAMP('2025-11-01') BETWEEN TIMESTAMP(bl.service_start_time) AND TIMESTAMP(bl.service_end_time)
)
SELECT
  COALESCE(b.bom_line_item_number, a.bom_line_item_number) as component_id,
  CASE
    WHEN b.bom_line_item_number IS NULL THEN 'ADDED'
    WHEN a.bom_line_item_number IS NULL THEN 'REMOVED'
    ELSE 'UNCHANGED'
  END as change_status
FROM recipe_before b
FULL OUTER JOIN recipe_after a
  ON b.bom_line_item_number = a.bom_line_item_number
WHERE b.bom_line_item_number IS NULL OR a.bom_line_item_number IS NULL;
```

## The Critical Filter Pattern

**Always include this for current recipes:**

```sql
AND CURRENT_TIMESTAMP() BETWEEN TIMESTAMP(bl.service_start_time) AND TIMESTAMP(bl.service_end_time)
```

**For historical analysis at specific date:**

```sql
AND TIMESTAMP('YYYY-MM-DD') BETWEEN TIMESTAMP(bl.service_start_time) AND TIMESTAMP(bl.service_end_time)
```

## Why This Matters

Without service window filtering:
- **Inflated counts**: Same component appears multiple times (each version)
- **Wrong costs**: Historical costs mixed with current costs
- **Incorrect ingredients**: Analyzing expired components that are no longer used
- **Failed inventory checks**: Checking stock for items no longer in recipe

**Example problem**:
- Query without filter returns 18 components
- Query with filter returns 7 components (the actual current recipe)

## BOM Headers Also Have Service Windows

Note that `bom_headers` also has `service_start_time` and `service_end_time` for BOM-level versioning, though filtering `is_active = true` is typically sufficient.

## Related Documentation

- [bom-components.md](bom-components.md) - BOM structure and required/optional
- [item-master.md](item-master.md) - Item metadata lookup
- [../common-pitfalls.md](../common-pitfalls.md) - More wrong/right patterns

---

## Code References (Java Codebase)

> **Codebase**: `master-data-management-2`
> **Validated**: 2026-01-28

### Domain Models

Service windows are implemented through fields in existing domain models rather than dedicated classes:

- **ItemVersion**: `backend/domain-library/src/main/java/app/internalrecipe/item/ItemVersion.java`
  - `serviceStartTime` (ZonedDateTime): When version becomes active for customers
  - `serviceEndTime` (ZonedDateTime): When version expires
  - `productionStartTime` / `productionEndTime`: Production scheduling window

- **BOMHeader.BomLine**: `backend/domain-library/src/main/java/app/internalrecipe/item/innerclassview/BOMHeader.java`
  - BOM lines inherit service windows from parent ItemVersion
  - Service window filtering happens at query time

- **Preparation**: `backend/domain-library/src/main/java/app/internalrecipe/preparation/Preparation.java`
  - MongoDB Collection: `preparations`
  - Used for preparation types (prep procedures)
  - No service window fields directly - uses `active` boolean instead

### Schedule 40 Model (HDR Consumables Scheduling)

- **Schedule40ModelReplaceLog**: `backend/domain-library/src/main/java/app/internalrecipe/item/schedule40model/Schedule40ModelReplaceLog.java`
  - MongoDB Collection: `schedule_40_model_replace_logs`
  - Tracks scheduled replacements of consumable items
  - Key fields: `scheduleDate`, `hdrConsumableItemNumber`, `stockItems`

- **Schedule40ModelReplaceExecLog**: `backend/domain-library/src/main/java/app/internalrecipe/item/schedule40model/Schedule40ModelReplaceExecLog.java`
  - Execution logs for schedule 40 model replacements

### Service Layer

- **BOItemServiceSettingQueryService**: `backend/internal-recipe-service/src/main/java/app/internalrecipe/servicesetting/service/BOItemServiceSettingQueryService.java`
  - Queries service settings for items

- **BOItemServiceSettingUpdateService**: `backend/internal-recipe-service/src/main/java/app/internalrecipe/servicesetting/service/BOItemServiceSettingUpdateService.java`
  - Updates service start/end times for item versions

- **BOCustomSchedule40ModelService**: `backend/internal-recipe-service/src/main/java/app/internalrecipe/schedule40model/service/BOCustomSchedule40ModelService.java`
  - Custom scheduling logic for 40 model items

- **BomHeaderService**: `backend/recipe-service-v2/src/main/java/app/recipev2/item/service/BomHeaderService.java`
  - Handles service window filtering in BOM queries

### API Endpoints

- **BOItemServiceSettingWebService**: `backend/internal-recipe-service-interface/src/main/java/app/internalrecipe/api/BOItemServiceSettingWebService.java`
  - `GET /bo/item/version/:uuid/service-setting` - Get service settings
  - `PUT /bo/item/version/:uuid/service-setting/update-check` - Validate update
  - `PUT /bo/item/version/:uuid/service-setting` - Update service times

- **BOSchedule40ModelWebService**: `backend/internal-recipe-service-interface/src/main/java/app/internalrecipe/api/BOSchedule40ModelWebService.java`
  - Schedule 40 model operations for HDR consumables

- **BOScheduleChangeWebService**: `backend/internal-recipe-service-interface/src/main/java/app/internalrecipe/api/BOScheduleChangeWebService.java`
  - General schedule change operations

### Business Logic Patterns

- **Service Window Query Pattern**: All BOM queries must filter by service window to get current recipe
  ```java
  // MongoDB filter pattern
  and(
    gt("service_end_time", ZonedDateTime.now()),
    lte("service_start_time", ZonedDateTime.now())
  )
  ```

- **Far Future End Date**: Service end time of `2100-01-01` indicates currently active (no planned expiry)

- **Version Overlap Prevention**: System validates that service windows don't overlap for the same component

### @Deprecated Fields

No @Deprecated annotations found in service window related classes.
