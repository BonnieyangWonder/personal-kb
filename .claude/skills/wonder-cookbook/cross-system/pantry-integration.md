# Pantry Integration - Cookbook to Inventory

This guide covers joining Cookbook recipe data to Pantry inventory data to check component stock levels at HDRs.

---

## Essential Filter (ALWAYS USE)

When joining to Cookbook item tables, always include:

```sql
AND ei.deleted = false
```

---

## Key Tables

| System | Dataset | Table | Purpose |
|--------|---------|-------|---------|
| Cookbook | `secure-recipe-prod.recipe_v2` | `bom_lines` | Recipe components |
| Pantry | `wonder-raw-prod.mysql_batch_inventory` | `inventory_on_hand` | Current stock levels |
| Pantry | `wonder-raw-prod.mysql_batch_inventory` | `sites` | HDR/location info |
| Catalog | `wonder-raw-prod.mysql_batch_product_catalog` | `wonder_items` | Item names |

## Join Pattern

The key join between Cookbook and Pantry:

```sql
CAST(bom_lines.bom_line_item_number AS STRING) = inventory_on_hand.item_number
```

## Query Patterns

### Check Required Components in Stock at HDR

```sql
WITH required_components AS (
  SELECT DISTINCT bl.bom_line_item_number as component_id
  FROM `secure-recipe-prod.recipe_v2.bom_headers` bh
  INNER JOIN `secure-recipe-prod.recipe_v2.bom_lines` bl
    ON bh.item_number = bl.bom_header_item_number
  WHERE bh.is_active = true
    AND bh.item_number = '8006375'  -- Menu item ID
    AND bl.manage_inventory = true  -- Only required components
    AND CURRENT_TIMESTAMP() BETWEEN TIMESTAMP(bl.service_start_time) AND TIMESTAMP(bl.service_end_time)
),
target_site AS (
  SELECT id
  FROM `wonder-raw-prod.mysql_batch_inventory.sites`
  WHERE name = 'HDR: Hackensack'
    AND deleted_at IS NULL
)
SELECT
  rc.component_id,
  wi.name as component_name,
  CASE WHEN ioh.item_number IS NOT NULL THEN 'IN STOCK' ELSE 'OUT OF STOCK' END as status,
  COALESCE(SUM(
    CASE
      WHEN ioh.uom = 'ea' THEN ioh.quantity
      WHEN ioh.conversion_factor > 0 THEN ioh.quantity / ioh.conversion_factor
      ELSE ioh.quantity
    END
  ), 0) as total_eaches
FROM required_components rc
CROSS JOIN target_site ts
LEFT JOIN `wonder-raw-prod.mysql_batch_inventory.inventory_on_hand` ioh
  ON CAST(rc.component_id AS STRING) = ioh.item_number
  AND ioh.site_id = ts.id
  AND ioh.quantity > 0
LEFT JOIN `wonder-raw-prod.mysql_batch_product_catalog.wonder_items` wi
  ON CAST(rc.component_id AS STRING) = wi.item_number
GROUP BY rc.component_id, wi.name, ioh.item_number
ORDER BY status DESC, component_id;
```

### Find Menu Items Missing Components at HDR

```sql
WITH site_inventory AS (
  SELECT DISTINCT item_number
  FROM `wonder-raw-prod.mysql_batch_inventory.inventory_on_hand` ioh
  JOIN `wonder-raw-prod.mysql_batch_inventory.sites` s
    ON ioh.site_id = s.id
  WHERE s.name = 'HDR: Hackensack'
    AND s.deleted_at IS NULL
    AND ioh.quantity > 0
),
menu_required_components AS (
  SELECT
    bh.item_number as menu_item_id,
    ei.name as menu_item_name,
    bl.bom_line_item_number as component_id
  FROM `secure-recipe-prod.recipe_v2.bom_headers` bh
  INNER JOIN `secure-recipe-prod.recipe_v2.bom_lines` bl
    ON bh.item_number = bl.bom_header_item_number
  LEFT JOIN `secure-recipe-prod.recipe_v2.effective_items` ei
    ON bh.item_number = CAST(ei.item_number AS STRING)
    AND ei.deleted = false
  WHERE bh.is_active = true
    AND bl.manage_inventory = true
    AND ei.object_type = 'MENU'
    AND ei.item_status = 'ACTIVE'
    AND CURRENT_TIMESTAMP() BETWEEN TIMESTAMP(bl.service_start_time) AND TIMESTAMP(bl.service_end_time)
)
SELECT
  mrc.menu_item_id,
  mrc.menu_item_name,
  COUNT(DISTINCT mrc.component_id) as total_required,
  COUNT(DISTINCT CASE WHEN si.item_number IS NULL THEN mrc.component_id END) as missing_count
FROM menu_required_components mrc
LEFT JOIN site_inventory si
  ON CAST(mrc.component_id AS STRING) = si.item_number
GROUP BY mrc.menu_item_id, mrc.menu_item_name
HAVING COUNT(DISTINCT CASE WHEN si.item_number IS NULL THEN mrc.component_id END) > 0
ORDER BY missing_count DESC;
```

### Get HDR Sites

```sql
SELECT
  id,
  name,
  site_type
FROM `wonder-raw-prod.mysql_batch_inventory.sites`
WHERE deleted_at IS NULL
  AND name LIKE 'HDR:%'
ORDER BY name;
```

### Check Inventory with Lot/Expiration

```sql
SELECT
  bl.bom_line_item_number as component_id,
  wi.name as component_name,
  ioh.quantity,
  ioh.uom,
  ioh.lot_number,
  ioh.expiration_date
FROM `secure-recipe-prod.recipe_v2.bom_headers` bh
INNER JOIN `secure-recipe-prod.recipe_v2.bom_lines` bl
  ON bh.item_number = bl.bom_header_item_number
JOIN `wonder-raw-prod.mysql_batch_inventory.inventory_on_hand` ioh
  ON CAST(bl.bom_line_item_number AS STRING) = ioh.item_number
JOIN `wonder-raw-prod.mysql_batch_inventory.sites` s
  ON ioh.site_id = s.id
LEFT JOIN `wonder-raw-prod.mysql_batch_product_catalog.wonder_items` wi
  ON CAST(bl.bom_line_item_number AS STRING) = wi.item_number
WHERE bh.is_active = true
  AND bh.item_number = '8009068'
  AND bl.manage_inventory = true
  AND s.name = 'HDR: Hackensack'
  AND CURRENT_TIMESTAMP() BETWEEN TIMESTAMP(bl.service_start_time) AND TIMESTAMP(bl.service_end_time)
ORDER BY component_id;
```

## Unit Conversion

Inventory may be in different units. Convert to 'eaches' when needed:

```sql
CASE
  WHEN ioh.uom = 'ea' THEN ioh.quantity
  WHEN ioh.conversion_factor > 0 THEN ioh.quantity / ioh.conversion_factor
  ELSE ioh.quantity
END as quantity_in_eaches
```

## Data Type Notes

- Always CAST `bom_line_item_number` to STRING for joins
- **Always include `deleted = false`** when joining to Cookbook item tables
- Use LEFT JOIN to preserve BOM lines even if no inventory exists
- Filter `sites.deleted_at IS NULL` for active sites

## Related Documentation

- [../core/bom-components.md](../core/bom-components.md) - BOM structure
- [../domains/food-science.md](../domains/food-science.md) - Shelf life
- See **wonder-pantry** skill for detailed Pantry documentation
