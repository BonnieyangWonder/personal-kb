# Vendor Catalog Service - Kafka Event Store

The Vendor Catalog Service (ProductCatalog) provides the source of truth for vendor data via Kafka events. This is a **newer system** that provides real-time vendor product data, separate from the traditional Cookbook vendor tables.

> **Data Source**: `wonder-raw-prod.kafka.productcatalog_events` - Event-sourced Kafka stream

---

## Overview

The ProductCatalog system uses **event sourcing** - data is stored as a stream of events rather than mutable records. To get the current state of any entity, you query for the most recent event per entity ID.

**Key Concept**: `ROW_NUMBER() OVER (PARTITION BY entity_id ORDER BY timestamp DESC)` gives the most recent event per entity.

---

## Entity Types

| Entity | Proto Type | Count | Description |
|--------|------------|-------|-------------|
| Vendor | `wonder.supplychain.productcatalog.v1.Vendor` | ~180 | Supplier/vendor records |
| VendorProduct | `wonder.supplychain.productcatalog.v1.VendorProduct` | ~5,000+ | Individual vendor SKUs |
| UomHierarchy | `wonder.supplychain.productcatalog.v1.VendorProductUomHierarchy` | ~4,800+ | UOM conversion chains |

---

## Query Patterns

### Get All Vendors (Current State)

```sql
WITH ranked_events AS (
  SELECT
    *,
    ROW_NUMBER() OVER (
      PARTITION BY vendor.id
      ORDER BY _kafka_timestamp DESC
    ) AS _row_num
  FROM `wonder-raw-prod.kafka.productcatalog_events`
  WHERE _payload_case = 'vendor'
    AND vendor.id IS NOT NULL
)
SELECT
  -- Entity fields (from Vendor proto)
  vendor.id,
  vendor.name,
  vendor.status,                    -- Enum: ACTIVE, INACTIVE
  vendor.display_id,

  -- Event metadata
  _event_case AS last_event_type,   -- 'vendor_created', 'vendor_updated', 'vendor_deleted'
  event_id AS last_event_id,
  originated_at AS last_originated_at,
  metadata.user_id AS last_modified_by,

  -- Kafka metadata
  _kafka_timestamp AS last_kafka_timestamp,
  _kafka_partition,
  _kafka_offset

FROM ranked_events
WHERE _row_num = 1
ORDER BY vendor.name;
```

### Get All Vendor Products (Current State)

```sql
WITH ranked_events AS (
  SELECT
    *,
    ROW_NUMBER() OVER (
      PARTITION BY vendor_product.id
      ORDER BY _kafka_timestamp DESC
    ) AS _row_num
  FROM `wonder-raw-prod.kafka.productcatalog_events`
  WHERE _payload_case = 'vendor_product'
    AND vendor_product.id IS NOT NULL
)
SELECT
  -- Entity fields
  vendor_product.id,
  vendor_product.vendor_id,
  vendor_product.sku,
  vendor_product.name,
  vendor_product.description,
  -- Cleaned enum: strip VENDOR_PRODUCT_ prefix
  REPLACE(vendor_product.status, 'VENDOR_PRODUCT_', '') AS status,
  vendor_product.lot_type,                -- LOT_AND_EXPIRY, EXPIRY_ONLY, LOT_ONLY, N_A
  vendor_product.lead_time,               -- days
  vendor_product.min_order_qty,
  vendor_product.stop_ship,
  vendor_product.min_shelf_life,          -- days
  vendor_product.price.currency_code AS price_currency,
  vendor_product.price.units AS price_units,
  vendor_product.price.nanos AS price_nanos,
  -- Computed: price as decimal
  COALESCE(CAST(vendor_product.price.units AS FLOAT64), 0) +
    COALESCE(CAST(vendor_product.price.nanos AS FLOAT64), 0) / 1000000000 AS price_decimal,
  vendor_product.barcode,                 -- UPC/EAN/GTIN
  vendor_product.storage_type,            -- AMBIENT, CHILLED, FROZEN

  -- Event metadata
  _event_case AS last_event_type,
  _kafka_timestamp AS last_kafka_timestamp

FROM ranked_events
WHERE _row_num = 1
ORDER BY vendor_product.vendor_id, vendor_product.sku;
```

### Get UOM Hierarchies (Current State)

```sql
WITH ranked_events AS (
  SELECT
    *,
    ROW_NUMBER() OVER (
      PARTITION BY hierarchy.id
      ORDER BY _kafka_timestamp DESC
    ) AS _row_num
  FROM `wonder-raw-prod.kafka.productcatalog_events`
  WHERE _payload_case = 'uom_hierarchy'
    AND hierarchy.id IS NOT NULL
)
SELECT
  -- Entity identifiers
  hierarchy.id,
  hierarchy.vendor_product_id,

  -- BASE level (BaseConfig: uom, is_pickable)
  hierarchy.base.uom AS base_uom,         -- PIECE, G, KG, LB, OZ, ML, L, FL_OZ, QT, GAL
  hierarchy.base.is_pickable AS base_is_pickable,

  -- EACH level (always present)
  hierarchy.each.conversion_factor.value AS each_conversion_factor,
  hierarchy.each.is_pickable AS each_is_pickable,

  -- PACK level (optional)
  hierarchy.pack.conversion_factor.value AS pack_conversion_factor,
  hierarchy.pack.is_pickable AS pack_is_pickable,

  -- CASE level (optional)
  hierarchy.`case`.conversion_factor.value AS case_conversion_factor,
  hierarchy.`case`.is_pickable AS case_is_pickable,

  -- PALLET level (optional)
  hierarchy.pallet.conversion_factor.value AS pallet_conversion_factor,
  hierarchy.pallet.is_pickable AS pallet_is_pickable,

  -- Business configuration
  REPLACE(hierarchy.purchase_level, 'PACKAGING_LEVEL_', '') AS purchase_level,
  hierarchy.abbreviation,                 -- 10-char Fishbowl code
  hierarchy.purchase_detail,              -- 30-char Fishbowl description

  -- Computed field
  hierarchy.cumulative_conversion_factor.value AS cumulative_conversion_factor,

  -- Event metadata
  _event_case AS last_event_type,
  _kafka_timestamp AS last_kafka_timestamp

FROM ranked_events
WHERE _row_num = 1
ORDER BY hierarchy.vendor_product_id;
```

### Complete Product Catalog (Joined View)

Join all three entities for a complete picture of each product:

```sql
WITH
vendors_current AS (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY vendor.id ORDER BY _kafka_timestamp DESC) AS _row_num
  FROM `wonder-raw-prod.kafka.productcatalog_events`
  WHERE _payload_case = 'vendor' AND vendor.id IS NOT NULL
),
products_current AS (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY vendor_product.id ORDER BY _kafka_timestamp DESC) AS _row_num
  FROM `wonder-raw-prod.kafka.productcatalog_events`
  WHERE _payload_case = 'vendor_product' AND vendor_product.id IS NOT NULL
),
hierarchies_current AS (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY hierarchy.id ORDER BY _kafka_timestamp DESC) AS _row_num
  FROM `wonder-raw-prod.kafka.productcatalog_events`
  WHERE _payload_case = 'uom_hierarchy' AND hierarchy.id IS NOT NULL
)
SELECT
  -- Vendor fields
  v.vendor.id AS vendor_id,
  v.vendor.name AS vendor_name,
  v.vendor.status AS vendor_status,
  v.vendor.display_id AS vendor_display_id,

  -- Vendor Product fields
  p.vendor_product.id AS product_id,
  p.vendor_product.sku AS product_sku,
  p.vendor_product.name AS product_name,
  p.vendor_product.description AS product_description,
  REPLACE(p.vendor_product.status, 'VENDOR_PRODUCT_', '') AS product_status,
  p.vendor_product.lot_type,
  p.vendor_product.lead_time,
  p.vendor_product.min_order_qty,
  p.vendor_product.stop_ship,
  p.vendor_product.min_shelf_life,
  p.vendor_product.price.currency_code AS price_currency,
  COALESCE(CAST(p.vendor_product.price.units AS FLOAT64), 0) +
    COALESCE(CAST(p.vendor_product.price.nanos AS FLOAT64), 0) / 1000000000 AS price_decimal,
  p.vendor_product.barcode,
  p.vendor_product.storage_type,

  -- UOM Hierarchy fields
  h.hierarchy.id AS hierarchy_id,
  h.hierarchy.base.uom AS base_uom,
  h.hierarchy.base.is_pickable AS base_is_pickable,
  h.hierarchy.each.conversion_factor.value AS each_conversion_factor,
  h.hierarchy.pack.conversion_factor.value AS pack_conversion_factor,
  h.hierarchy.`case`.conversion_factor.value AS case_conversion_factor,
  h.hierarchy.pallet.conversion_factor.value AS pallet_conversion_factor,
  REPLACE(h.hierarchy.purchase_level, 'PACKAGING_LEVEL_', '') AS purchase_level,
  h.hierarchy.abbreviation AS uom_abbreviation,
  h.hierarchy.purchase_detail AS uom_purchase_detail,
  h.hierarchy.cumulative_conversion_factor.value AS cumulative_conversion_factor,

  -- Last update timestamps
  v._kafka_timestamp AS vendor_last_updated,
  p._kafka_timestamp AS product_last_updated,
  h._kafka_timestamp AS hierarchy_last_updated

FROM products_current p
LEFT JOIN vendors_current v ON p.vendor_product.vendor_id = v.vendor.id AND v._row_num = 1
LEFT JOIN hierarchies_current h ON p.vendor_product.id = h.hierarchy.vendor_product_id AND h._row_num = 1
WHERE p._row_num = 1
ORDER BY v.vendor.name, p.vendor_product.sku;
```

### Summary Statistics

```sql
WITH
vendors AS (
  SELECT vendor.status
  FROM (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY vendor.id ORDER BY _kafka_timestamp DESC) AS rn
    FROM `wonder-raw-prod.kafka.productcatalog_events`
    WHERE _payload_case = 'vendor' AND vendor.id IS NOT NULL
  ) WHERE rn = 1
),
products AS (
  SELECT vendor_product.status
  FROM (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY vendor_product.id ORDER BY _kafka_timestamp DESC) AS rn
    FROM `wonder-raw-prod.kafka.productcatalog_events`
    WHERE _payload_case = 'vendor_product' AND vendor_product.id IS NOT NULL
  ) WHERE rn = 1
),
hierarchies AS (
  SELECT hierarchy.id
  FROM (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY hierarchy.id ORDER BY _kafka_timestamp DESC) AS rn
    FROM `wonder-raw-prod.kafka.productcatalog_events`
    WHERE _payload_case = 'uom_hierarchy' AND hierarchy.id IS NOT NULL
  ) WHERE rn = 1
)
SELECT 'Vendors' AS entity, COUNT(*) AS total, COUNTIF(status = 'ACTIVE') AS active, COUNTIF(status = 'INACTIVE') AS inactive FROM vendors
UNION ALL
SELECT 'Products', COUNT(*), COUNTIF(status = 'VENDOR_PRODUCT_ACTIVE'), COUNTIF(status = 'VENDOR_PRODUCT_INACTIVE') FROM products
UNION ALL
SELECT 'UOM Hierarchies', COUNT(*), COUNT(*), 0 FROM hierarchies;
```

---

## Key Concepts

### Event Sourcing Pattern

Every query follows the same pattern to get current state:

```sql
WITH ranked_events AS (
  SELECT *,
    ROW_NUMBER() OVER (PARTITION BY {entity}.id ORDER BY _kafka_timestamp DESC) AS _row_num
  FROM `wonder-raw-prod.kafka.productcatalog_events`
  WHERE _payload_case = '{entity_type}'
)
SELECT ... FROM ranked_events WHERE _row_num = 1;
```

### Payload Types

The `_payload_case` field determines the entity type:
- `'vendor'` - Vendor records
- `'vendor_product'` - Product records
- `'uom_hierarchy'` - UOM hierarchy records

### Event Types

The `_event_case` field shows what action occurred:
- `vendor_created`, `vendor_updated`, `vendor_deleted`
- `vendor_product_created`, `vendor_product_updated`, etc.

### Price Calculation

Prices are stored as Money proto (units + nanos):
```sql
COALESCE(CAST(price.units AS FLOAT64), 0) +
  COALESCE(CAST(price.nanos AS FLOAT64), 0) / 1000000000 AS price_decimal
```

### Enum Cleaning

Status enums have prefixes that should be stripped:
```sql
REPLACE(vendor_product.status, 'VENDOR_PRODUCT_', '') AS status
REPLACE(hierarchy.purchase_level, 'PACKAGING_LEVEL_', '') AS purchase_level
```

---

## UOM Hierarchy Levels

The UOM hierarchy defines conversion factors at each packaging level:

| Level | Description | Example |
|-------|-------------|---------|
| `base` | Base unit of measure | PIECE, G, LB, etc. |
| `each` | Individual unit (always present) | 1 each = 100g |
| `pack` | Pack level (optional) | 6 each per pack |
| `case` | Case level (optional) | 4 packs per case |
| `pallet` | Pallet level (optional) | 20 cases per pallet |

The `cumulative_conversion_factor` gives the total conversion from base to purchase level.

---

## vs. Traditional Vendor Tables

| Aspect | ProductCatalog (Kafka) | vendor_items_v2 |
|--------|------------------------|-----------------|
| Data Source | `wonder-raw-prod.kafka` | `wonder-recipe-prod.recipe_v2` |
| Update Method | Event stream | Batch sync |
| Freshness | Near real-time | Periodic batch |
| Historical | Full event history | Current state only |
| Primary Use | Supply chain operations | Cookbook linkage |

---

## Critical Rules

1. **Always filter `_row_num = 1`** to get current state
2. **COALESCE price.nanos** - can be NULL, causing calculation errors
3. **Strip enum prefixes** for cleaner output
4. **Use `_kafka_timestamp`** for ordering, not `originated_at`
5. **Quote `case`** field - it's a SQL reserved word: `hierarchy.\`case\``

---

## Related Documentation

- [../domains/vendor-items.md](../domains/vendor-items.md) - Traditional Cookbook vendor tables
- [../domains/units-of-measure.md](../domains/units-of-measure.md) - UOM concepts in Cookbook
- See **wonder-supply-chain** skill for POMS purchase order data
