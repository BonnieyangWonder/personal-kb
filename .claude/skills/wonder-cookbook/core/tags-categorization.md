# Tags and Categorization System

Wonder's Cookbook uses a tagging system (also called "Attributes" in the UI) to categorize and classify items. Tags are organized into groups (called "Categories" in admin interfaces), and items reference tags through their `attributes` JSON field.

> **Terminology Note**: The database uses `tag_groups` and `tags`, while the Cookbook UI refers to these as "Categories" (or "Attributes" at the group level) and "Sub-Attributes" (or "Attribute Values"). This documentation uses database terminology.

---

## Data Model

```
tag_groups (1) ──< (many) tags (many) >── (many) item_versions
                     │                          │
                 tag_group_id                attributes (JSON array)
                     │                          │
                  _id ──────────────────────> tag_id
```

**Key Relationship**: Item versions store tag assignments in the `attributes` JSON field, which contains an array of objects with `tag_id` references to `tags._id`.

---

## Core Tables

### tag_groups

Defines categories of tags. Located in `wonder-recipe-prod.recipe_v2.tag_groups`.

```sql
_id                  STRING    -- UUID identifier (FK for tags.tag_group_id)
name                 STRING    -- Group name (e.g., "Beverage Type", "Primary Cuisine")
description          STRING    -- Group description (up to 200 characters)
type                 STRING    -- Input type: DROP_DOWN, DATE, or NUMBER
taggable_sources     STRING    -- JSON array: data domains where tags apply (see below)
is_deprecated        BOOLEAN   -- Soft-delete flag
permission_type      STRING    -- PUBLIC or PRIVATE (controls edit access)
user_admin_access    STRING    -- JSON array of user IDs with admin access (for PRIVATE)
role_admin_access    STRING    -- JSON array of role names with admin access (for PRIVATE)
created_by           STRING    -- Creator name
created_user_id      STRING    -- Creator UUID
created_time         DATETIME  -- Creation timestamp
updated_by           STRING    -- Last updater name
updated_user_id      STRING    -- Last updater UUID
updated_time         DATETIME  -- Last update timestamp
```

**Attribute Types**:
- `DROP_DOWN`: Predefined values (sub-attributes) that users select from a list
- `DATE`: Date values in MM/DD/YYYY format; can only be tagged once per item
- `NUMBER`: Numeric values up to 3 decimal places; can only be tagged once per item

**Common Tag Groups**:

| Group Name | taggable_sources | Type | Purpose |
|------------|------------------|------|---------|
| Primary Cuisine | MARKETPLACE, MERCHANDISING | DROP_DOWN | Menu item cuisine classification |
| Beverage Type | MARKETPLACE, MERCHANDISING | DROP_DOWN | Beverage categorization |
| Dish Archetype | MARKETPLACE, MERCHANDISING | DROP_DOWN | Dish type (entree, side, dessert) |
| Spicy | MARKETPLACE, MERCHANDISING | DROP_DOWN | Spice level indicator |
| Health Profile | MERCHANDISING | DROP_DOWN | Health/dietary attributes |
| Production Station | MASTERDATA | DROP_DOWN | Kitchen station assignment |
| Bulk Recipe Type | MASTERDATA | DROP_DOWN | Recipe production type |
| R&D Stage | MASTERDATA | DROP_DOWN | Development stage (allows new values) |
| Basic Recipe | MASTERDATA | DROP_DOWN | Recipe classification (allows new values) |

---

### tags

Individual tags within groups. Located in `wonder-recipe-prod.recipe_v2.tags`.

```sql
_id                  STRING    -- UUID identifier (referenced by item_versions.attributes)
tag_group_id         STRING    -- FK to tag_groups._id
name                 STRING    -- Tag display name (e.g., "Coffee", "Italian", "Spicy")
description          STRING    -- Tag description
is_deprecated        BOOLEAN   -- Soft-delete flag
created_by           STRING    -- Creator name
created_user_id      STRING    -- Creator UUID
created_time         DATETIME  -- Creation timestamp
updated_by           STRING    -- Last updater name
updated_user_id      STRING    -- Last updater UUID
updated_time         DATETIME  -- Last update timestamp
```

---

### Item-Tag Mapping (via attributes field)

Item versions store tag assignments in the `attributes` JSON field in `secure-recipe-prod.recipe_v2.item_versions`:

```json
[
  {
    "id": "uuid-of-mapping",
    "tag_id": "uuid-referencing-tags._id",
    "created_by": "User Name",
    "created_user_id": "user-uuid",
    "created_time": "2023-01-30T20:23:30.129000",
    "updated_by": "User Name",
    "updated_user_id": "user-uuid",
    "updated_time": "2023-01-30T20:23:30.129000"
  }
]
```

---

## Query Patterns

### List All Active Tag Groups

```sql
SELECT _id, name, type, taggable_sources
FROM `wonder-recipe-prod.recipe_v2.tag_groups`
WHERE is_deprecated = false
ORDER BY name;
```

### List Tags in a Group

```sql
SELECT t._id, t.name, t.description
FROM `wonder-recipe-prod.recipe_v2.tags` t
JOIN `wonder-recipe-prod.recipe_v2.tag_groups` tg
  ON t.tag_group_id = tg._id
WHERE tg.name = 'Beverage Type'
  AND t.is_deprecated = false
ORDER BY t.name;
```

### Get All Tags for a Menu Item

```sql
SELECT
  iv.item_number,
  iv.name as item_name,
  tg.name as tag_group,
  t.name as tag_name
FROM `secure-recipe-prod.recipe_v2.item_versions` iv,
UNNEST(JSON_EXTRACT_ARRAY(iv.attributes)) as attr
JOIN `wonder-recipe-prod.recipe_v2.tags` t
  ON JSON_VALUE(attr, '$.tag_id') = t._id
JOIN `wonder-recipe-prod.recipe_v2.tag_groups` tg
  ON t.tag_group_id = tg._id
WHERE iv.effective = true
  AND iv.deleted = false
  AND iv.item_number = '8002003'
  AND t.is_deprecated = false;
```

### Find Items with a Specific Tag

```sql
SELECT DISTINCT
  iv.item_number,
  iv.name as item_name,
  t.name as tag_name
FROM `secure-recipe-prod.recipe_v2.item_versions` iv,
UNNEST(JSON_EXTRACT_ARRAY(iv.attributes)) as attr
JOIN `wonder-recipe-prod.recipe_v2.tags` t
  ON JSON_VALUE(attr, '$.tag_id') = t._id
WHERE iv.effective = true
  AND iv.deleted = false
  AND iv.item_status = 'ACTIVE'
  AND t.name = 'Coffee'
  AND t.is_deprecated = false;
```

### Find Items by Tag Group

```sql
SELECT DISTINCT
  iv.item_number,
  iv.name as item_name,
  t.name as tag_value
FROM `secure-recipe-prod.recipe_v2.item_versions` iv,
UNNEST(JSON_EXTRACT_ARRAY(iv.attributes)) as attr
JOIN `wonder-recipe-prod.recipe_v2.tags` t
  ON JSON_VALUE(attr, '$.tag_id') = t._id
JOIN `wonder-recipe-prod.recipe_v2.tag_groups` tg
  ON t.tag_group_id = tg._id
WHERE iv.effective = true
  AND iv.deleted = false
  AND iv.object_type = 'MENU'
  AND tg.name = 'Primary Cuisine'
  AND t.is_deprecated = false
ORDER BY t.name, iv.name;
```

### Count Items by Tag

```sql
SELECT
  tg.name as tag_group,
  t.name as tag_name,
  COUNT(DISTINCT iv.item_number) as item_count
FROM `secure-recipe-prod.recipe_v2.item_versions` iv,
UNNEST(JSON_EXTRACT_ARRAY(iv.attributes)) as attr
JOIN `wonder-recipe-prod.recipe_v2.tags` t
  ON JSON_VALUE(attr, '$.tag_id') = t._id
JOIN `wonder-recipe-prod.recipe_v2.tag_groups` tg
  ON t.tag_group_id = tg._id
WHERE iv.effective = true
  AND iv.deleted = false
  AND iv.item_status = 'ACTIVE'
  AND t.is_deprecated = false
GROUP BY tg.name, t.name
ORDER BY tg.name, item_count DESC;
```

---

## Data Domains (taggable_sources)

The `taggable_sources` field in tag_groups controls which teams/systems can use tags. These are called "Data Domains" in the admin UI:

| Source | UI Name | Description |
|--------|---------|-------------|
| `MASTERDATA` | Master Data | Core operational data used in Cookbook |
| `MERCHANDISING` | Merchandising Tool | Marketing and merchandising classification |
| `MARKETPLACE` | Marketplace | Customer-facing attributes (menus, app) |
| `HDR` | HDR | High Density Restaurant operations |
| `PLANNING` | Planning | Planning and forecasting systems |

**Domain Restrictions**:
- DATE and NUMBER type attributes can only be assigned to `MASTERDATA` domain
- Bulk import via Excel template only supports `MASTERDATA` domain attributes
- Items may have tags from multiple sources depending on their use case

---

## Permission Model

Tag groups have a permission system controlling who can edit and apply them:

### Permission Types

| Type | Description |
|------|-------------|
| `PUBLIC` | Any user with "Edit Attributes" permission can edit and apply |
| `PRIVATE` | Only users/roles in `user_admin_access` or `role_admin_access` can edit/apply |

### Admin Roles

For PRIVATE attributes, access can be granted by role. Role display name mappings:

| Display Name | Internal Role |
|--------------|---------------|
| CDT | CDT Publish |
| CE | Culinary Engineering |
| Production | Culinary Production |
| Supply Chain | Supply Chain & Packaging |
| Food Science | Food Science |

### Permission Hierarchy

1. **Read**: View the attributes list page
2. **Create Attributes**: Create new tag groups and sub-attributes
3. **Edit Attributes**: Modify existing tag groups and sub-attributes
4. **Map Attributes**: Apply/tag attributes on items' attributes card

For private attributes, users need both the base permission AND be listed in the attribute's admin access.

### Querying Permission Info

```sql
SELECT
  _id,
  name,
  permission_type,
  role_admin_access,
  user_admin_access
FROM `wonder-recipe-prod.recipe_v2.tag_groups`
WHERE permission_type = 'PRIVATE'
  AND is_deprecated = false;
```

---

## Admin Workflows

### Deprecation

Tag groups and tags can be deprecated rather than deleted:
- Deprecated items remain in the database but are hidden from UI selection
- Use `is_deprecated = true` to soft-delete
- Undeprecation is possible to restore visibility

### Version Handling

When attributes are assigned to items:
- Changes apply to both the active version AND future versions of the item
- Inactive items are excluded from the Items' Attributes grid
- Dormant items are still shown if they match attribute filters

### Audit Tracking

All attribute operations (Create, Update, Delete) on items are tracked with:
- Action type (CUD)
- Item number
- Operator (login user)
- Description of change
- Operated timestamp

---

## Filtering Best Practices

1. **Always filter deprecated tags**: `t.is_deprecated = false`
2. **Always filter deprecated tag groups**: `tg.is_deprecated = false`
3. **When querying item_versions, apply essential filter**:
   ```sql
   WHERE iv.effective = true
     AND iv.deleted = false
     AND iv.item_status != 'DORMANT'
   ```
4. **Handle NULL attributes**: Some items have no tags (`attributes IS NULL` or `attributes = '[]'`)
5. **For public permission analysis**: Check `permission_type = 'PUBLIC'`
6. **For private permission analysis**: Also check `user_admin_access` and `role_admin_access` fields

---

## Bulk Operations

### Excel Import

Attributes can be bulk-imported via Excel template:
- **Domain Restriction**: Only `MASTERDATA` domain attributes can be imported
- **Validation**: Template must match expected column names exactly
- **Updates**: Applies to both active and future versions of items

### Validation Rules

When assigning attributes:
- DROP_DOWN: Must select from predefined values in the tag group
- DATE: Must be valid date in MM/DD/YYYY format
- NUMBER: Must be numeric with up to 3 decimal places, >= 0
- DATE/NUMBER types can only be tagged once per item (no duplicates)
- Duplicate attribute+value combinations on same item are rejected

### Bulk Update All Usages

Administrators can bulk-change a tag value across all items:
- Example: Change all items tagged "Salads" to "Noodles"
- Requires confirmation before applying
- Private attribute bulk updates require appropriate permissions

---

## Related Documentation

- [item-master.md](item-master.md) - Item versions and attributes field
- [../schema-reference.md](../schema-reference.md) - Complete table schemas

---

## Code References (Java Codebase)

> **Codebase**: `master-data-management-2`
> **Validated**: 2026-01-28

### Domain Models

- **Tag**: `backend/domain-library/src/main/java/app/internalrecipe/attribute/Tag.java`
  - MongoDB Collection: `tags`
  - Primary key: `id` (UUID)
  - Key fields: `tagGroupId` (FK to TagGroup), `name`, `description`, `isDeprecated`
  - Maps to BigQuery: `wonder-recipe-prod.recipe_v2.tags`

- **TagGroup**: `backend/domain-library/src/main/java/app/internalrecipe/attribute/TagGroup.java`
  - MongoDB Collection: `tag_groups`
  - Primary key: `id` (UUID)
  - Key fields: `name`, `type` (TagGroupType), `permissionType` (TagGroupPermission), `taggableSources`, `isDeprecated`
  - Permission fields: `userAdminAccess`, `roleAdminAccess`
  - Maps to BigQuery: `wonder-recipe-prod.recipe_v2.tag_groups`

- **TagGroupType**: `backend/domain-library/src/main/java/app/internalrecipe/attribute/TagGroupType.java`
  - Enum values: `DROP_DOWN`, `DATE`, `NUMBER`

- **TagGroupPermission**: `backend/domain-library/src/main/java/app/internalrecipe/attribute/TagGroupPermission.java`
  - Enum values: `PUBLIC`, `PRIVATE`

- **EntitySourceType**: `backend/domain-library/src/main/java/app/internalrecipe/attribute/EntitySourceType.java`
  - Enum values for taggable sources: `MASTERDATA`, `MERCHANDISING`, `MARKETPLACE`, `HDR`, `PLANNING`

- **Attribute (Inner Class)**: `backend/domain-library/src/main/java/app/internalrecipe/item/innerclassview/Attribute.java`
  - Embedded in ItemVersion.attributes (List<Attribute>)
  - Key fields: `id`, `tagId` (references Tag._id), audit fields

### Service Layer

- **TagService**: `backend/recipe-service-v2/src/main/java/app/recipev2/attribute/service/TagService.java`
  - Tag and tag group query operations

- **BOAttributeV4Service**: `backend/internal-recipe-service/src/main/java/app/internalrecipe/attribute/service/BOAttributeV4Service.java`
  - Latest version of attribute management service

- **BOAttributeUpdateService**: `backend/internal-recipe-service/src/main/java/app/internalrecipe/attribute/service/BOAttributeUpdateService.java`
  - Attribute CRUD operations

- **BOAttributeBulkInsertService**: `backend/internal-recipe-service/src/main/java/app/internalrecipe/attribute/service/BOAttributeBulkInsertService.java`
  - Bulk import via Excel template

- **BOItemAttributeService**: `backend/internal-recipe-service/src/main/java/app/internalrecipe/item/service/attribute/BOItemAttributeService.java`
  - Item-to-attribute mapping operations

- **BOItemAttributeQueryService**: `backend/internal-recipe-service/src/main/java/app/internalrecipe/item/service/attribute/BOItemAttributeQueryService.java`
  - Query attributes assigned to items

- **ItemAttributeService**: `backend/recipe-service-v2/src/main/java/app/recipev2/item/service/ItemAttributeService.java`
  - Item attribute operations (v2 service)

### API Endpoints

- **BOAttributeWebService**: `backend/internal-recipe-service-interface/src/main/java/app/internalrecipe/api/BOAttributeWebService.java`
  - `GET /bo/attribute` - List all attributes (tag groups)
  - `GET /bo/attribute/:id` - Get attribute details
  - `GET /bo/attribute/:id/value` - List values (tags) in attribute
  - `POST /bo/attribute` - Create attribute (tag group)
  - `POST /bo/attribute/:id/value` - Create value (tag)
  - `POST /bo/attribute/value/bulk-create` - Bulk create tags
  - `PUT /bo/attribute/:id` - Update attribute
  - `PUT /bo/attribute/:id/deprecated` - Deprecate/undeprecate attribute
  - `PUT /v4/bo/attribute` - Search attributes (v4)

- **BOItemAttributeWebService**: `backend/internal-recipe-service-interface/src/main/java/app/internalrecipe/api/BOItemAttributeWebService.java`
  - Item-attribute mapping endpoints

- **TagWebService**: `backend/recipe-service-v2-interface/src/main/java/app/recipev2/api/TagWebService.java`
  - Public tag query API

### MongoDB Operations

- **Tag Collection**: Collection name `tags`, indexed on `tag_group_id`, `is_deprecated`
- **TagGroup Collection**: Collection name `tag_groups`, indexed on `is_deprecated`, `permission_type`
- **Item Attributes**: Stored as embedded array in `item_versions.attributes`

### Business Logic Patterns

- **Soft Delete via isDeprecated**: Tags and TagGroups use `isDeprecated = true` instead of hard delete
- **Permission Model**: PUBLIC vs PRIVATE tag groups with `userAdminAccess` and `roleAdminAccess` lists
- **Domain Restrictions**: `taggableSources` controls which data domains can use each tag group
- **Type Restrictions**: DATE and NUMBER types can only be assigned once per item

### @Deprecated Fields

No @Deprecated annotations found in attribute/tag domain classes.
