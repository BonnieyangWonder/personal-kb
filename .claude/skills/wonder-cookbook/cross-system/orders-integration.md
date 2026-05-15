# Orders Integration - Cookbook to Sales Data

This guide covers joining Cookbook recipe data to order/sales data for analyzing menu item performance.

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
| Cookbook | `secure-recipe-prod.recipe_v2` | `effective_items` | Menu item metadata |
| Orders | `wonder-dw-prod-brd.wonder_dw` | `hdr_orders` | Order headers |
| Orders | `wonder-dw-prod-brd.wonder_dw` | `order_items` | Individual order items |

## Join Pattern

The key join between Cookbook items and order data:

```sql
-- Join via item_number/sku
effective_items.item_number = order_items.sku
```

## Query Patterns

### Get Sales for a Menu Item

```sql
SELECT
  ei.item_number,
  ei.name as menu_item_name,
  COUNT(DISTINCT oi.order_id) as order_count,
  SUM(oi.quantity) as total_quantity,
  SUM(oi.total_price) as total_revenue
FROM `secure-recipe-prod.recipe_v2.effective_items` ei
JOIN `wonder-dw-prod-brd.wonder_dw.order_items` oi
  ON CAST(ei.item_number AS STRING) = oi.sku
WHERE ei.item_number = '8009068'
  AND ei.deleted = false
  AND oi.created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
GROUP BY ei.item_number, ei.name;
```

### Top Selling Menu Items

```sql
SELECT
  ei.item_number,
  ei.name as menu_item_name,
  COUNT(DISTINCT oi.order_id) as order_count,
  SUM(oi.quantity) as total_quantity
FROM `secure-recipe-prod.recipe_v2.effective_items` ei
JOIN `wonder-dw-prod-brd.wonder_dw.order_items` oi
  ON CAST(ei.item_number AS STRING) = oi.sku
WHERE ei.object_type = 'MENU'
  AND ei.deleted = false
  AND ei.item_status = 'ACTIVE'
  AND oi.created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
GROUP BY ei.item_number, ei.name
ORDER BY total_quantity DESC
LIMIT 20;
```

### Menu Item Sales by HDR

```sql
SELECT
  o.hdr_id,
  ei.item_number,
  ei.name as menu_item_name,
  SUM(oi.quantity) as total_quantity
FROM `secure-recipe-prod.recipe_v2.effective_items` ei
JOIN `wonder-dw-prod-brd.wonder_dw.order_items` oi
  ON CAST(ei.item_number AS STRING) = oi.sku
JOIN `wonder-dw-prod-brd.wonder_dw.hdr_orders` o
  ON oi.order_id = o.order_id
WHERE ei.item_number = '8009068'
  AND ei.deleted = false
  AND o.created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
GROUP BY o.hdr_id, ei.item_number, ei.name
ORDER BY total_quantity DESC;
```

### Analyze Recipe Cost vs Revenue

```sql
WITH recipe_cost AS (
  SELECT
    bh.item_number as menu_item_id,
    SUM(bl.cost) as total_component_cost
  FROM `secure-recipe-prod.recipe_v2.bom_headers` bh
  INNER JOIN `secure-recipe-prod.recipe_v2.bom_lines` bl
    ON bh.item_number = bl.bom_header_item_number
  WHERE bh.is_active = true
    AND CURRENT_TIMESTAMP() BETWEEN TIMESTAMP(bl.service_start_time) AND TIMESTAMP(bl.service_end_time)
  GROUP BY bh.item_number
),
item_sales AS (
  SELECT
    oi.sku as menu_item_id,
    AVG(oi.unit_price) as avg_selling_price,
    SUM(oi.quantity) as total_quantity
  FROM `wonder-dw-prod-brd.wonder_dw.order_items` oi
  WHERE oi.created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
  GROUP BY oi.sku
)
SELECT
  ei.item_number,
  ei.name as menu_item_name,
  rc.total_component_cost,
  s.avg_selling_price,
  s.avg_selling_price - rc.total_component_cost as margin,
  s.total_quantity
FROM `secure-recipe-prod.recipe_v2.effective_items` ei
JOIN recipe_cost rc ON ei.item_number = rc.menu_item_id
JOIN item_sales s ON CAST(ei.item_number AS STRING) = s.menu_item_id
WHERE ei.object_type = 'MENU'
  AND ei.deleted = false
  AND ei.item_status = 'ACTIVE'
ORDER BY margin DESC
LIMIT 20;
```

### Menu Items Never Ordered

```sql
SELECT
  ei.item_number,
  ei.name as menu_item_name
FROM `secure-recipe-prod.recipe_v2.effective_items` ei
LEFT JOIN `wonder-dw-prod-brd.wonder_dw.order_items` oi
  ON CAST(ei.item_number AS STRING) = oi.sku
  AND oi.created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 90 DAY)
WHERE ei.object_type = 'MENU'
  AND ei.deleted = false
  AND ei.item_status = 'ACTIVE'
  AND oi.sku IS NULL
ORDER BY ei.name;
```

## Menu Availability Analysis

To understand how recipe availability affects orders, combine with the **wonder-menu-availability** skill:

```sql
-- Check if an item was on the menu when ordered
SELECT
  o.hdr_id,
  o.created_at as order_time,
  oi.sku as item_number,
  am.is_available
FROM `wonder-dw-prod-brd.wonder_dw.hdr_orders` o
JOIN `wonder-dw-prod-brd.wonder_dw.order_items` oi
  ON o.order_id = oi.order_id
LEFT JOIN `wonder-dw-prod-brd.forecast.active_menu_v2` am
  ON oi.sku = CAST(am.item_number AS STRING)
  AND o.hdr_id = am.hdr_id
  AND DATE(o.created_at) = am.date
WHERE oi.sku = '8009068'
LIMIT 100;
```

### Get Kitchen Orders by Menu Item Numbers

Query kitchen orders for specific menu items with date and weekday breakdown:

```sql
SELECT
  DATE(ko.created_time) AS order_date,
  FORMAT_DATE('%A', DATE(ko.created_time)) AS weekday,
  COUNT(DISTINCT ko.order_id) AS total_orders
FROM `wonder-raw-prod.mysql_batch_kitchen_order.kitchen_orders` ko
JOIN `wonder-raw-prod.mysql_batch_kitchen_order.order_items` oi
  ON ko.order_id = oi.order_id
WHERE oi.item_number IN (
  '8008712','8008711','8008710','8008707','8008706',
  '8008705','8008704','8008703','8008702','8008698','8006886'
)
AND ko.created_time BETWEEN '2025-08-20' AND '2025-09-11 23:59:59'
GROUP BY order_date, weekday
ORDER BY order_date DESC;
```

### Get Menu Item Number from Order Number

Reverse lookup: find which menu items were in a specific order:

```sql
SELECT
  ko.order_id,
  ko.order_number,
  oi.item_number,
  ei.name as item_name,
  oi.quantity,
  ko.created_time
FROM `wonder-raw-prod.mysql_batch_kitchen_order.kitchen_orders` ko
JOIN `wonder-raw-prod.mysql_batch_kitchen_order.order_items` oi
  ON ko.order_id = oi.order_id
LEFT JOIN `secure-recipe-prod.recipe_v2.effective_items` ei
  ON oi.item_number = CAST(ei.item_number AS STRING)
  AND ei.deleted = false
WHERE ko.order_number = 'YOUR_ORDER_NUMBER'  -- Replace with actual order number
ORDER BY ko.created_time DESC;
```

### Query Restaurant Menu Items with Mapping Sources

Find all mapped items (from customization and line build) for menu items at a specific HDR:

```sql
SELECT DISTINCT
  ai.item_number,
  iv.name AS item_name,
  ai.source_type
FROM (
  SELECT item_number, STRING_AGG(DISTINCT source, ', ' ORDER BY source) AS source_type
  FROM (
    -- From Customization
    SELECT DISTINCT
      JSON_VALUE(customization_option_value_item_raw, '$.item_number') AS item_number,
      'CUSTOMIZATION' AS source
    FROM `secure-recipe-prod.recipe_v2.item_versions` iv,
      UNNEST(JSON_EXTRACT_ARRAY(iv.item_customization, '$.options')) AS customization_options_raw,
      UNNEST(JSON_EXTRACT_ARRAY(customization_options_raw, '$.option_values')) AS customization_option_value_raw,
      UNNEST(JSON_EXTRACT_ARRAY(customization_option_value_raw, '$.items')) AS customization_option_value_item_raw
    WHERE item_status != 'DORMANT'
      AND deleted = false
      AND object_type = 'MENU'
      AND effective = true
      AND iv.item_number IN (
        SELECT DISTINCT item_number
        FROM `wonder-dw-prod.dw_restaurant.dim_menu_items`
        WHERE hdr_name = 'Westfield'  -- Replace with your HDR
          AND item_number IS NOT NULL
      )
      AND JSON_VALUE(customization_option_value_item_raw, '$.item_number') IS NOT NULL

    UNION ALL

    -- From Line Build Procedures
    SELECT DISTINCT
      JSON_VALUE(p, '$.related_item_number') AS item_number,
      'LINE_BUILD' AS source
    FROM `secure-recipe-prod.recipe_v2.item_versions` iv_base,
      UNNEST(JSON_EXTRACT_ARRAY(iv_base.item_line_build, '$.line_builds')) AS lb,
      UNNEST(JSON_EXTRACT_ARRAY(lb, '$.tasks')) AS t,
      UNNEST(JSON_EXTRACT_ARRAY(t, '$.procedures')) AS p
    WHERE iv_base.object_type = 'MENU'
      AND iv_base.item_line_build IS NOT NULL
      AND iv_base.effective = true
      AND iv_base.item_status != 'DORMANT'
      AND iv_base.deleted = false
      AND JSON_VALUE(p, '$.activity') IN ('VEND', 'COMPLETE', 'COOK', 'GARNISH')
      AND JSON_VALUE(p, '$.related_item_number') IS NOT NULL
      AND iv_base.item_number IN (
        SELECT DISTINCT item_number
        FROM `wonder-dw-prod.dw_restaurant.dim_menu_items`
        WHERE hdr_name = 'Westfield'
          AND item_number IS NOT NULL
      )

    UNION ALL

    -- From Line Build Procedure Steps
    SELECT DISTINCT
      JSON_VALUE(ps, '$.related_item_number') AS item_number,
      'LINE_BUILD' AS source
    FROM `secure-recipe-prod.recipe_v2.item_versions` iv_base,
      UNNEST(JSON_EXTRACT_ARRAY(iv_base.item_line_build, '$.line_builds')) AS lb,
      UNNEST(JSON_EXTRACT_ARRAY(lb, '$.tasks')) AS t,
      UNNEST(JSON_EXTRACT_ARRAY(t, '$.procedures')) AS proc,
      UNNEST(JSON_EXTRACT_ARRAY(proc, '$.procedure_steps')) AS ps
    WHERE iv_base.object_type = 'MENU'
      AND iv_base.item_line_build IS NOT NULL
      AND iv_base.effective = true
      AND iv_base.item_status != 'DORMANT'
      AND iv_base.deleted = false
      AND JSON_VALUE(ps, '$.related_item_number') IS NOT NULL
      AND iv_base.item_number IN (
        SELECT DISTINCT item_number
        FROM `wonder-dw-prod.dw_restaurant.dim_menu_items`
        WHERE hdr_name = 'Westfield'
          AND item_number IS NOT NULL
      )
  ) all_mapped_items
  WHERE item_number IS NOT NULL
  GROUP BY item_number
) ai
LEFT JOIN `secure-recipe-prod.recipe_v2.item_versions` iv
  ON ai.item_number = iv.item_number
  AND iv.effective = true
  AND iv.deleted = false
ORDER BY ai.item_number;
```

---

## Data Type Notes

- CAST `item_number` to STRING when joining to order tables
- **Always include `deleted = false`** when joining to Cookbook item tables
- Order timestamps are in UTC - convert for business analysis
- Use LEFT JOIN when looking for items with no orders

## Related Documentation

- [../core/item-master.md](../core/item-master.md) - Menu item metadata
- [pantry-integration.md](pantry-integration.md) - Inventory checks
- See **wonder-orders** skill for detailed order data documentation
- See **wonder-menu-availability** skill for menu availability patterns
