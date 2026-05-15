# Logistics - Storage, Receiving, and Space Management

The logistics data in Cookbook tracks storage requirements, receiving specifications, and space management for items. This documentation is cross-referenced with Confluence pages "Logistics Card" (4166451268), "Receiving Info Card" (4210131244), and "Space Management" (4210589727).

## Overview

Logistics data exists at the **version level** (not item level) and covers three main areas:

1. **Logistics Card** - Storage type, location, lot tracking, classification
2. **Receiving Info** - Quality criteria, temperature class, dimensions for receiving
3. **Space Management** - Appliance and vessel specifications (non-food items only)

## Key Fields in item_versions / effective_items

### Core Logistics Fields

```sql
-- Storage configuration
storage_type             STRING    -- Storage requirements: AMBIENT, FROZEN, CHILLED
storage_location         STRING    -- Primary storage location
storage_sub_location     STRING    -- Sub-location within storage area

-- Tracking and classification
pick_by_type             STRING    -- Pick by type for warehouse operations
lot_type                 STRING    -- Lot tracking type (e.g., FIFO, LIFO)
classification_type      STRING    -- Item classification for logistics

-- Units of measure (logistics context)
uoms                     STRING    -- UOMs for logistics purposes (JSON)
```

### Non-Food Item Specific Fields

```sql
-- Packaging dimensions (ONLY for non-food items, 90* prefix)
packaging_length         FLOAT64   -- Package length
packaging_width          FLOAT64   -- Package width
packaging_height         FLOAT64   -- Package height
variable_dimensions      BOOLEAN   -- Whether dimensions can vary
```

## Receiving Info Fields

Receiving info is for ingredients and non-food items, providing quality criteria for incoming goods:

```sql
-- Receiving category and temperature
receiving_category       STRING    -- Category for receiving protocol
temperature_class        STRING    -- CHILLED, FROZEN, or AMBIENT (auto-set by category)

-- Physical specifications (for produce, meat, fish, shellfish)
receiving_length         FLOAT64   -- Length in inches (1 decimal place max)
receiving_width          FLOAT64   -- Width in inches (1 decimal place max)
receiving_height         FLOAT64   -- Height in inches (1 decimal place max)
receiving_weight         FLOAT64   -- Weight in ounces (1 decimal place max)

-- Description
receiving_description    STRING    -- Quality criteria text (max 200 chars)
```

### Receiving Category to Temperature Class Mapping

| Category | Temperature Class |
|----------|-------------------|
| Produce | Chilled |
| Meat (fresh) | Chilled |
| Fish (fresh) | Chilled |
| Shellfish | Chilled |
| Dairy | Chilled |
| Frozen | Frozen |
| Baked Goods | Ambient |
| Canned & Bottled Goods | Ambient |
| Dry Goods | Ambient |
| Non-Food | Ambient |

**Note**: Temperature Class is auto-defined based on Category and cannot be edited manually.

### Receiving Category Field Display Rules

- **Full fields shown** (Category, Temperature Class, Length, Width, Height, Weight, Description): Produce, Meat (fresh), Fish (fresh), Shellfish
- **Minimal fields shown** (Category, Description only): Non-Food, Baked Goods, Dairy, Frozen, Canned & Bottled Goods, Dry Goods

## Space Management Fields (Non-Food Only)

Space Management applies only to non-food items with subtype `appliance` or `vessel`.

### Appliance Fields (subtype = 'appliance')

```sql
-- Appliance type and configuration
appliance_type           STRING    -- Refrigerator, Freezer, or Flex (required)
number_of_doors          INT64     -- Range 0-4 (optional)
max_interior_shelves     INT64     -- Range 0-9 (optional)
max_capacity             INT64     -- In cm^3 (optional)
number_of_slots_per_shelf INT64    -- Range 0-10 (optional)

-- Interior dimensions (cm, up to 3 decimal places)
interior_length          FLOAT64   -- Interior length in cm
interior_width           FLOAT64   -- Interior width in cm
interior_height          FLOAT64   -- Interior height in cm

-- Minimum shelf dimensions (cm, up to 3 decimal places)
min_shelf_length         FLOAT64   -- Minimum shelf length in cm
min_shelf_width          FLOAT64   -- Minimum shelf width in cm
min_shelf_height         FLOAT64   -- Minimum shelf height in cm
```

### Vessel Fields (subtype = 'vessel')

```sql
-- Vessel type and capacity
vessel_type              STRING    -- Akro Bin or Other (required)
vessel_capacity          INT64     -- Range 0-24 (optional)

-- Vessel dimensions (cm, up to 3 decimal places)
vessel_length            FLOAT64   -- Vessel length in cm
vessel_width             FLOAT64   -- Vessel width in cm
vessel_height            FLOAT64   -- Vessel height in cm
```

**Important**: When subtype changes (appliance <-> vessel, or to others), Space Management parameters are cleared.

## Query Patterns

### Get Logistics Info for an Item

```sql
SELECT
  item_number,
  name,
  object_type,
  storage_type,
  storage_location,
  storage_sub_location,
  pick_by_type,
  lot_type,
  classification_type
FROM `secure-recipe-prod.recipe_v2.effective_items`
WHERE item_number = '5001234'
  AND deleted = false;
```

### Find Items by Storage Type

```sql
SELECT
  item_number,
  name,
  object_type,
  storage_type,
  storage_location
FROM `secure-recipe-prod.recipe_v2.effective_items`
WHERE storage_type = 'FROZEN'
  AND deleted = false
  AND item_status = 'ACTIVE'
ORDER BY object_type, name;
```

### Analyze Storage Distribution by Object Type

```sql
SELECT
  object_type,
  storage_type,
  COUNT(*) as item_count
FROM `secure-recipe-prod.recipe_v2.effective_items`
WHERE storage_type IS NOT NULL
  AND deleted = false
  AND item_status = 'ACTIVE'
GROUP BY object_type, storage_type
ORDER BY object_type, item_count DESC;
```

### Find Ingredients by Lot Type

```sql
SELECT
  item_number,
  name,
  lot_type,
  storage_type
FROM `secure-recipe-prod.recipe_v2.effective_items`
WHERE object_type = 'INGREDIENT'
  AND lot_type IS NOT NULL
  AND deleted = false
  AND item_status = 'ACTIVE'
ORDER BY lot_type, name;
```

### Get Receiving Info for Chilled Items

```sql
SELECT
  item_number,
  name,
  receiving_category,
  temperature_class,
  receiving_length,
  receiving_width,
  receiving_height,
  receiving_weight,
  receiving_description
FROM `secure-recipe-prod.recipe_v2.effective_items`
WHERE temperature_class = 'Chilled'
  AND deleted = false
  AND item_status = 'ACTIVE'
ORDER BY receiving_category, name;
```

### Find Non-Food Appliances with Space Management

```sql
SELECT
  item_number,
  name,
  appliance_type,
  interior_length,
  interior_width,
  interior_height,
  max_capacity,
  max_interior_shelves,
  number_of_doors
FROM `secure-recipe-prod.recipe_v2.effective_items`
WHERE object_type = 'NON_FOOD'
  AND object_sub_type = 'appliance'
  AND deleted = false
  AND item_status = 'ACTIVE'
ORDER BY appliance_type, name;
```

### Find Vessels by Type

```sql
SELECT
  item_number,
  name,
  vessel_type,
  vessel_length,
  vessel_width,
  vessel_height,
  vessel_capacity
FROM `secure-recipe-prod.recipe_v2.effective_items`
WHERE object_type = 'NON_FOOD'
  AND object_sub_type = 'vessel'
  AND deleted = false
  AND item_status = 'ACTIVE'
ORDER BY vessel_type, name;
```

### Storage Type Summary for Supply Chain Planning

```sql
SELECT
  storage_type,
  COUNT(*) as total_items,
  COUNT(DISTINCT CASE WHEN object_type = 'INGREDIENT' THEN item_number END) as ingredients,
  COUNT(DISTINCT CASE WHEN object_type = 'PACKAGED' THEN item_number END) as packaged,
  COUNT(DISTINCT CASE WHEN object_type = 'NON_FOOD' THEN item_number END) as non_food
FROM `secure-recipe-prod.recipe_v2.effective_items`
WHERE storage_type IS NOT NULL
  AND deleted = false
  AND item_status = 'ACTIVE'
GROUP BY storage_type
ORDER BY total_items DESC;
```

## Critical Rules

### Storage Type Values

| Value | Description | Typical Items |
|-------|-------------|---------------|
| `AMBIENT` | Room temperature storage | Dry goods, canned items, non-food |
| `FROZEN` | Freezer storage required | Frozen proteins, ice cream bases |
| `CHILLED` | Refrigeration required | Fresh produce, dairy, proteins |

### Validation Rules

1. **Receiving Info Category**: Required before other receiving fields can be set
2. **Temperature Class**: Auto-calculated from Category, not editable
3. **Space Management**: Only displayed for non-food items with subtype `appliance` or `vessel`
4. **Subtype Changes**: Changing subtype clears all Space Management parameters
5. **Dimension Precision**: Receiving dimensions max 1 decimal place; Space Management max 3 decimal places
6. **Field Units**:
   - Receiving dimensions: inches
   - Receiving weight: ounces
   - Space Management dimensions: centimeters
   - Space Management capacity: cubic centimeters

### Integration with Supply Chain

Logistics fields are critical for supply chain operations:

- **storage_type** determines warehouse zone assignment
- **lot_type** affects inventory tracking and FIFO/LIFO management
- **pick_by_type** influences warehouse picking operations
- **receiving_category** and **temperature_class** guide dock-to-stock procedures

## Related Documentation

- [food-science.md](food-science.md) - Shelf life and safety (related to storage)
- [vendor-items.md](vendor-items.md) - Vendor-level storage specifications
- [../cross-system/supply-chain-integration.md](../cross-system/supply-chain-integration.md) - POMS integration

## Source Documentation

- Confluence: [Logistics Card](https://wonder.atlassian.net/wiki/spaces/TECHXIAMEN/pages/4166451268) - Storage, classification, UOMs
- Confluence: [Receiving Info Card](https://wonder.atlassian.net/wiki/spaces/TECHXIAMEN/pages/4210131244) - Quality criteria, receiving protocol
- Confluence: [Space Management](https://wonder.atlassian.net/wiki/spaces/TECHXIAMEN/pages/4210589727) - Appliance and vessel specifications

---

## Code References (Java Codebase)

> **Codebase**: `master-data-management-2`
> **Validated**: 2026-01-28

### Domain Models

- **Facility**: `backend/domain-library/src/main/java/app/internalrecipe/facility/Facility.java`
  - MongoDB collection: `facilities`
  - Key fields: `name`, `code`, `ogWarehouseId`, `description`, `active`, `addressLine` (nested Address), `addressLine2`, `phoneNumber`, `type`
  - Nested class: `Address` with `name`, `city`, `state`, `zipCode`
  - **@Deprecated (1)**: `address` field → use `addressLine` instead

- **FacilityType**: `backend/domain-library/src/main/java/app/internalrecipe/facility/FacilityType.java`
  - Values: `PRODUCTION`, `WAREHOUSE`

- **Route**: `backend/domain-library/src/main/java/app/internalrecipe/route/Route.java`
  - MongoDB collection: `routes`
  - Key fields: `name`, `createdBy`, `createdTime`

- **FacilityCode**: `backend/domain-library/src/main/java/app/internalrecipe/route/FacilityCode.java`
  - Predefined facility codes: `NJ0001`, `NJ0002`, `NJ0018`, `NJ0022`, `NJ0033`, `NJ0039`, `NJ0050`

- **LocationMapping**: `backend/domain-library/src/main/java/app/internalrecipe/locationmapping/LocationMapping.java`
  - MongoDB collection: `location_mappings`
  - Key fields: `routeId`, `routeName`, `facilityId`, `facilityName`, `facilityCode`, `kitchenLocationUUID`, `kitchenLocationName`, `kitchenSubLocationUUIDs`, `active`
  - Maps routes to facilities and kitchen locations

### Enums

- **StorageType** (vendor context): `backend/domain-library/src/main/java/app/internalrecipe/vendor/constant/StorageType.java`
  - Values: `AMBIENT`, `CHILLED`, `FROZEN`

- **StorageType** (item context): `backend/domain-library/src/main/java/app/internalrecipe/item/innerclassview/StorageType.java`
  - Values: `AMBIENT`, `CHILLED`, `FROZEN`, `MISSING`
  - Note: Item context includes additional `MISSING` value for data validation

- **StorageDimensionGroup**: `backend/domain-library/src/main/java/app/internalrecipe/item/innerclassview/StorageDimensionGroup.java`
  - Values: `WMS`, `SITE_WH`, `WMS_SITEPP`
  - Maps to ERP values: "WMS", "Site-WH", "WMS-SitePP"

### Service Layer

- **BOFacilityService**: `backend/internal-recipe-service/src/main/java/app/internalrecipe/facility/service/BOFacilityService.java`
  - Facility CRUD operations
  - Validates unique name, code, and ogWarehouseId
  - Cascades updates to LocationMapping collection

- **BORouteService**: `backend/internal-recipe-service/src/main/java/app/internalrecipe/route/service/BORouteService.java`
  - Route CRUD operations
  - Integrates with LocationMapping and KitchenSubLocation

### API Endpoints

- **BOFacilityWebService**: `backend/internal-recipe-service-interface/src/main/java/app/internalrecipe/api/BOFacilityWebService.java`
  - `GET /bo/facility` - List all facilities
  - `POST /bo/facility` - Create new facility
  - `PUT /bo/facility/:id` - Update existing facility
  - `DELETE /bo/facility/:id` - Delete facility
  - `PUT /bo/facility` (search) - Search facilities with pagination

- **BORouteWebService**: `backend/internal-recipe-service-interface/src/main/java/app/internalrecipe/api/BORouteWebService.java`
  - `GET /bo/route` - List all routes
  - `POST /bo/route` - Create new route

### Business Logic Patterns

- **Facility-Route-Location Mapping**: Routes are mapped to facilities through LocationMapping, enabling kitchen location assignment
- **Unique Constraint Validation**: Facility name, code, and ogWarehouseId must be unique across all facilities
- **Cascade Delete Protection**: Cannot delete facility if it's mapped to items through routes
- **Storage Type Consistency**: Two StorageType enums exist (vendor vs item context) with slightly different values

### @Deprecated Field Summary

| Field | Location | Replacement |
|-------|----------|-------------|
| `address` | Facility | `addressLine` |
