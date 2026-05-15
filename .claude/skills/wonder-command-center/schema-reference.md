# Command Center (Splitter) Schema Reference

## Overview

The Command Center database contains the **Splitter** service, which manages order splitting logic for Wonder's HDR restaurants. The service determines which orders (e.g., "Global", "Pod A", "Frozen") each SKU-facility combination should be assigned to, optimizing kitchen workflow and fulfillment efficiency.

## Database Connection
- **BigQuery Dataset**: `wonder-raw-prod.pg_batch_command_center`
- **Access**: Via bq CLI or BigQuery Console

---

## Core Business Flow

```
┌──────────────┐
│hdr_sku_scope │  Forecasted demand: which HDRs will order which SKUs
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  sku_info    │  SKU metadata: storage type, object type, sub-type
└──────┬───────┘
       │
       ▼
┌──────────────────┐
│sku_grouping_rules│  Business rules configuration (priority-based)
└──────┬───────────┘
       │
       ▼ [Rules Engine Processing]
       │
       ▼
┌──────────────────┐
│order_split_cache │  Final output: facility+SKU → order split assignment
└──────────────────┘
```

---

## Core Tables

### hdr_sku_scope

**Purpose**: Forecasted demand - which HDR restaurants will likely order which SKUs on specific dates. Feeds the rules engine with scope for cache pre-calculation.

**Schema**:
```sql
service_date                  DATE              -- Date the HDR might order this SKU
day_of_week                   INTEGER           -- Day of week (1=Monday, 7=Sunday)
hdr_id                        VARCHAR(36)       -- UUID of the HDR facility
item_number                   VARCHAR(36)       -- SKU identifier
item_type                     TEXT              -- Type of item (e.g., 'HDR_CONSUMABLE_ITEM')
menu_count_core               INTEGER           -- Core menu items count
menu_count_optional           INTEGER           -- Optional menu items count
menu_count_core_current       INTEGER           -- Current core menu items count
menu_count_optional_current   INTEGER           -- Current optional menu items count
menu_change_flag              INTEGER           -- Flag indicating menu changes (0/1)
naive_scope_flag              INTEGER           -- Flag for naive scoping logic (0/1)
```

**Usage**:
- Input for rules engine to know which facility-SKU pairs to calculate
- Forecasting tool to pre-cache order splits before actual orders arrive

**Sample Query**:
```sql
-- See which HDRs are forecasted to order a specific SKU
SELECT service_date, hdr_id, item_type
FROM `wonder-raw-prod.pg_batch_command_center.hdr_sku_scope`
WHERE item_number = '8805753'
  AND service_date >= CURRENT_DATE('America/New_York')
ORDER BY service_date, hdr_id;
```

---

### sku_info

**Purpose**: Reference data providing metadata about each SKU. Used by rules engine to make assignment decisions based on storage type, object type, etc.

**Schema**:
```sql
item_number       VARCHAR(36)     -- SKU identifier (PK)
object_type       VARCHAR(255)    -- Type (e.g., 'ORIGINAL_SUBRECIPE', 'NON_FOOD')
object_sub_type   VARCHAR(255)    -- Sub-type (e.g., 'ALCOHOLIC_BEVERAGE', 'COMMON_STOCK', 'PACKAGED')
storage_type      VARCHAR(255)    -- Storage requirements (e.g., 'FROZEN', 'CHILLED', 'AMBIENT', 'MISSING')
```

**Common Values**:

**object_type**:
- `ORIGINAL_SUBRECIPE` - Standard kitchen items
- `NON_FOOD` - Non-food items (cleaning supplies, etc.) - **Often excluded from warehouse analysis**
- `PACKAGED_GOOD` - Pre-packaged items
- `BEVERAGE` - Drink items

**object_sub_type**:
- `COMMON_STOCK` - Frequently used across all HDRs
- `PACKAGED` - Pre-packaged items
- `ALCOHOLIC_BEVERAGE` - Alcohol products
- `NON_ALCOHOLIC_BEVERAGE` - Soft drinks, juices
- `HOT` / `COLD` - Temperature-based classification

**storage_type**:
- `FROZEN` - Must be stored frozen
- `CHILLED` - Refrigerated storage
- `AMBIENT` - Room temperature
- `MISSING` - Storage type not defined

**Usage**:
```sql
-- Find all frozen items
SELECT item_number, object_type, object_sub_type
FROM `wonder-raw-prod.pg_batch_command_center.sku_info`
WHERE storage_type = 'FROZEN';

-- Find beverages
SELECT item_number, storage_type
FROM `wonder-raw-prod.pg_batch_command_center.sku_info`
WHERE object_sub_type IN ('ALCOHOLIC_BEVERAGE', 'NON_ALCOHOLIC_BEVERAGE');
```

---

### sku_grouping_rules

**Purpose**: Configuration table containing business rules for the rules engine. Rules are evaluated in priority order to determine order split assignments.

**Schema**:
```sql
policy_id     BIGINT              -- Policy identifier grouping related rules
group_name    VARCHAR(255)        -- Name of order split group (e.g., 'Frozen', 'Pod A Hot')
rule_id       VARCHAR(36)         -- Unique identifier for this rule (e.g., 'StorageTypeRule')
priority      INTEGER             -- Priority order (lower = higher priority, processed first)
parameters    JSON                -- Rule parameters (e.g., {"include": ["FROZEN"]})
```

**Rule Evaluation**:
- Rules processed in **ascending priority order** (priority 1 before priority 2)
- **First matching rule wins** - no further evaluation after match
- Unmatched SKUs fall through to "Global" (default catch-all)

**Common Rule Types**:

1. **StorageTypeRule**: Match on `sku_info.storage_type`
   ```json
   {"include": ["FROZEN"]}
   ```

2. **ObjectSubTypeRule**: Match on `sku_info.object_sub_type`
   ```json
   {"include": ["ALCOHOLIC_BEVERAGE", "NON_ALCOHOLIC_BEVERAGE"]}
   ```

3. **PodRule**: Match on pod assignment
   ```json
   {"pod_name": "A", "pod_type": "HOT"}
   ```

4. **CustomSKUListRule**: Match specific SKU list
   ```json
   {"item_numbers": ["8805753", "8806668", "8003399"]}
   ```

**Sample Data**:
```sql
-- Example rule set
policy_id: 1, group_name: "Frozen",        rule_id: "StorageTypeRule",    priority: 1
policy_id: 1, group_name: "Beverages",     rule_id: "ObjectSubTypeRule",  priority: 3
policy_id: 1, group_name: "Common Stock",  rule_id: "CommonStockRule",    priority: 5
policy_id: 1, group_name: "Pod A Hot",     rule_id: "PodRule",            priority: 8
policy_id: 1, group_name: "Pod B Hot",     rule_id: "PodRule",            priority: 9
```

**Query Patterns**:
```sql
-- View current rule configuration
SELECT priority, group_name, rule_id, parameters
FROM `wonder-raw-prod.pg_batch_command_center.sku_grouping_rules`
WHERE policy_id = 1
ORDER BY priority ASC;

-- Find rules assigning to a specific group
SELECT rule_id, priority, parameters
FROM `wonder-raw-prod.pg_batch_command_center.sku_grouping_rules`
WHERE group_name = 'Frozen'
ORDER BY priority;
```

---

### order_split_cache

**Purpose**: The final output - mapping of facility+SKU combinations to their assigned order split. This is what the rules engine produces and what operational systems consume.

**Schema**:
```sql
id                  STRING               -- UUID identifier
facility_id         STRING NOT NULL      -- Facility identifier (HDR UUID)
item_sku            STRING NOT NULL      -- SKU identifier
order_split_value   STRING NOT NULL      -- Assigned order split (e.g., "Pod A", "Frozen", "Global")
created_at          TIMESTAMP NOT NULL   -- Record creation timestamp
updated_at          TIMESTAMP NOT NULL   -- Last update timestamp
created_by          STRING NOT NULL      -- User/service that created
updated_by          STRING NOT NULL      -- User/service that last updated
details             STRING NOT NULL      -- Rules engine decision trace/reasoning (JSON)

-- Primary key: id
-- Unique constraint: (facility_id, item_sku)  -- One assignment per facility-SKU pair
```

**Indexes**:
- `UNIQUE (facility_id, item_sku)` - Ensures one assignment per combination
- `btree (facility_id)` - Fast facility lookups
- `btree (item_sku)` - Fast SKU lookups
- `btree (facility_id, item_sku)` - Composite lookups

**Common order_split_value Values**:
- `Global` - Default/catch-all order
- `Frozen` - Frozen items order
- `Beverages` - Beverage order
- `Common Stock` - Common stock items
- `Packaged Items` - Pre-packaged goods
- `Pod A` / `Pod B` / `Pod C` / `Pod D` - Pod-specific orders
- `Pod A Hot` / `Pod A Cold` - Temperature-specific pod orders

**details Field**:
Contains JSON trace of rules engine decision-making:
```json
{
  "matched_rule": "StorageTypeRule",
  "priority": 1,
  "group_name": "Frozen",
  "reason": "storage_type=FROZEN matched include list"
}
```

**Usage Patterns**:
```sql
-- Get all assignments for a facility
SELECT item_sku, order_split_value, updated_at
FROM `wonder-raw-prod.pg_batch_command_center.order_split_cache`
WHERE facility_id = '867877e0-36ea-42c5-84d8-11668897dc85'
ORDER BY order_split_value, item_sku;

-- Count SKUs by order split
SELECT order_split_value, COUNT(*) as sku_count
FROM `wonder-raw-prod.pg_batch_command_center.order_split_cache`
WHERE facility_id = '867877e0-36ea-42c5-84d8-11668897dc85'
GROUP BY order_split_value
ORDER BY sku_count DESC;

-- Find large "Global" orders (optimization candidates)
SELECT facility_id, COUNT(*) as global_sku_count
FROM `wonder-raw-prod.pg_batch_command_center.order_split_cache`
WHERE order_split_value = 'Global'
GROUP BY facility_id
HAVING COUNT(*) > 100
ORDER BY global_sku_count DESC;
```

---

### order_split_cache_logs

**Purpose**: Audit trail for all changes to order_split_cache. Tracks INSERT and UPDATE operations for compliance and debugging.

**Schema**:
```sql
id                  STRING               -- UUID identifier
facility_id         STRING NOT NULL      -- Facility identifier
item_sku            STRING NOT NULL      -- SKU identifier
order_split_value   STRING NOT NULL      -- Order split assignment at time of log
operation           STRING NOT NULL      -- 'INSERT' or 'UPDATE'
created_at          TIMESTAMP NOT NULL   -- When log entry was created
created_by          STRING NOT NULL      -- User/service that made change
details             STRING NOT NULL      -- Additional context
```

**Indexes**:
- `btree (created_at)` - Temporal queries
- `btree (facility_id, item_sku)` - Facility-SKU lookups
- `btree (operation)` - Filter by operation type

**Usage Patterns**:
```sql
-- Recent changes
SELECT facility_id, item_sku, order_split_value, operation, created_at
FROM `wonder-raw-prod.pg_batch_command_center.order_split_cache_logs`
WHERE created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
ORDER BY created_at DESC;

-- Changes to a specific SKU
SELECT order_split_value, operation, created_at, created_by
FROM `wonder-raw-prod.pg_batch_command_center.order_split_cache_logs`
WHERE item_sku = '8805753'
ORDER BY created_at DESC;

-- Bulk update detection
SELECT
  DATETIME_TRUNC(DATETIME(created_at), HOUR) as hour,
  operation,
  COUNT(*) as change_count
FROM `wonder-raw-prod.pg_batch_command_center.order_split_cache_logs`
WHERE created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
GROUP BY DATETIME_TRUNC(DATETIME(created_at), HOUR), operation
ORDER BY hour DESC;
```

---

## Key Relationships

### Rules Engine Flow

```
1. hdr_sku_scope
     → Identifies which facility+SKU pairs need assignments
     ↓
2. sku_info
     → Provides SKU metadata (storage_type, object_type, etc.)
     ↓
3. sku_grouping_rules
     → Defines assignment logic in priority order
     ↓
4. order_split_cache
     → Stores final assignment with decision trace
     ↓
5. order_split_cache_logs
     → Audit trail of all changes
```

### Cross-Table Joins

```sql
-- Complete picture: cache + SKU metadata
SELECT
  osc.facility_id,
  osc.item_sku,
  osc.order_split_value,
  si.object_type,
  si.object_sub_type,
  si.storage_type
FROM `wonder-raw-prod.pg_batch_command_center.order_split_cache` osc
JOIN `wonder-raw-prod.pg_batch_command_center.sku_info` si
  ON osc.item_sku = si.item_number
WHERE osc.facility_id = 'some-uuid';

-- Forecasted demand + current assignments
SELECT
  hss.service_date,
  hss.hdr_id,
  hss.item_number,
  osc.order_split_value,
  si.storage_type
FROM `wonder-raw-prod.pg_batch_command_center.hdr_sku_scope` hss
LEFT JOIN `wonder-raw-prod.pg_batch_command_center.order_split_cache` osc
  ON hss.hdr_id = osc.facility_id
  AND hss.item_number = osc.item_sku
LEFT JOIN `wonder-raw-prod.pg_batch_command_center.sku_info` si
  ON hss.item_number = si.item_number
WHERE hss.service_date = CURRENT_DATE('America/New_York');
```

---

## Audit & Event Sourcing Patterns

The schema follows Wonder's standard audit patterns:

### Standard Audit Fields
- `created_at` / `updated_at`: TIMESTAMP (stored in UTC)
- `created_by` / `updated_by`: User/service attribution
- `details`: STRING field for additional context/reasoning (often JSON)

### WORM (Write Once Read Many) Compatibility
- UUIDs as primary keys (STRING type)
- Unique constraints on business keys (facility_id, item_sku)
- Audit log table captures all mutations

### Timezone Handling
All timestamps are `TIMESTAMP` stored in UTC. BigQuery provides timezone conversion functions.

**Conversion Pattern**:
```sql
-- Convert to business timezone (America/New_York)
SELECT DATETIME(created_at, 'America/New_York') as created_at_ny
FROM `wonder-raw-prod.pg_batch_command_center.order_split_cache`;
```

---

## Query Performance Tips

1. **Always use facility_id in WHERE clause** when possible - heavily indexed
2. **Filter by order_split_value** for targeted analysis
3. **Join to sku_info** to understand why SKUs were assigned
4. **Check details field** for rules engine reasoning
5. **Use order_split_cache_logs** for historical changes, not current state

### Sample Performance Query
```sql
-- Efficient: Filters on facility_id first
-- Use --dry_run flag with bq to see query plan and bytes processed
SELECT item_sku, order_split_value
FROM `wonder-raw-prod.pg_batch_command_center.order_split_cache`
WHERE facility_id = '867877e0-36ea-42c5-84d8-11668897dc85'
  AND order_split_value = 'Global';
```

---

## Common Analysis Patterns

### Order Size Distribution
```sql
SELECT
  order_split_value,
  COUNT(DISTINCT facility_id) as facility_count,
  MIN(sku_count) as min_skus,
  ROUND(AVG(sku_count), 1) as avg_skus,
  MAX(sku_count) as max_skus
FROM (
  SELECT order_split_value, facility_id, COUNT(*) as sku_count
  FROM `wonder-raw-prod.pg_batch_command_center.order_split_cache`
  GROUP BY order_split_value, facility_id
) subquery
GROUP BY order_split_value
ORDER BY facility_count DESC;
```

### SKU Assignment Conflicts
```sql
-- Find SKUs assigned to different splits across facilities (unusual pattern)
SELECT
  item_sku,
  COUNT(DISTINCT order_split_value) as split_count,
  STRING_AGG(order_split_value, ', ') as splits
FROM `wonder-raw-prod.pg_batch_command_center.order_split_cache`
GROUP BY item_sku
HAVING COUNT(DISTINCT order_split_value) > 1
ORDER BY split_count DESC;
```

### Rule Effectiveness Analysis
```sql
-- How many SKUs matched each rule?
WITH rule_matches AS (
  SELECT
    order_split_value,
    JSON_EXTRACT_SCALAR(details, '$.matched_rule') as rule_id,
    COUNT(*) as match_count
  FROM `wonder-raw-prod.pg_batch_command_center.order_split_cache`
  WHERE details IS NOT NULL
    AND details != ''
  GROUP BY order_split_value, JSON_EXTRACT_SCALAR(details, '$.matched_rule')
)
SELECT * FROM rule_matches
ORDER BY match_count DESC;
```

---

## Data Quality Notes

### Storage Type Coverage
Many SKUs have `storage_type = 'MISSING'`. Rules should handle this gracefully:
```sql
-- Check storage type coverage
SELECT
  storage_type,
  COUNT(*) as sku_count,
  ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) as pct
FROM `wonder-raw-prod.pg_batch_command_center.sku_info`
GROUP BY storage_type
ORDER BY sku_count DESC;
```

### Object Type Filtering
`NON_FOOD` items often need to be excluded from warehouse-related analysis:
```sql
-- Exclude NON_FOOD for warehouse analysis (in context of larger query)
SELECT *
FROM `wonder-raw-prod.pg_batch_command_center.order_split_cache` osc
JOIN `wonder-raw-prod.pg_batch_command_center.sku_info` si
  ON osc.item_sku = si.item_number
WHERE si.object_type != 'NON_FOOD'
```

### Item Number Prefixes
Different prefixes indicate different item categories:
- `88*`: Standard food items
- `80*`: May have different fulfillment
- `5*`: May be handled separately
- Always verify with stakeholders which prefixes are in scope!
