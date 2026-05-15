# Wonder Kitchen Ops Skill - Changelog

## 2026-02-05 - Initial Skill Creation

**Note**: This is the initial creation of the wonder-kitchen-ops skill. The sections below document the conceptual corrections and refinements made during the research and development process, not changes to a previous version of this skill.

### Major Changes

#### 1. Terminology Correction: "Implicit Batching" Removed

**WRONG (Previous Understanding)**:
- Items with NULL `batch_item_number` use "implicit batching"
- These items batch "at runtime" based on other criteria

**CORRECT (Updated Understanding)**:
- Items with NULL `sub_steps_related_item_number` ARE batchable, but **only with identical selections/option values**
- Wing Trip wings currently batch only by flavor because the `related_item_number` is configured to point to the SAUCE
- **Root cause**: Configuration issue - should point to chicken SKU (base component) instead of sauce
- **Planned fix**: Culinary team will update line builds to use chicken SKU as the batch component, enabling cross-flavor batching

**Impact**: This is a **configuration issue**, not a fundamental limitation. Wings with different flavors will be able to batch together once the culinary team updates the `related_item_number` to point to the chicken component instead of the sauce.

#### 2. Line Builds as Batch Configuration Source

Added comprehensive coverage of `item_line_builds` table as the **source of truth** for batch configuration:

**Key Fields**:
- `sub_steps_related_item_number`: Batch component (NULL = batchable only with identical option values; see Clarifications section below)
- `procedures_batch_limit`: Maximum items per batch
- `sub_steps_order`: Only order=1 contains batch configuration
- `service_start_time` / `service_end_time`: Version windows (what matters for filtering)
- `status`: LINE_BUILD_CREATED or PENDING_UPDATE (less relevant than service dates)

**Critical Rules**:
1. Only substep 1 (`sub_steps_order = 1`) has batch configuration
2. NULL component number allows batching only with identical option values (see Wing Trip wings in Clarifications section)
3. **Filter by `service_end_time >= CURRENT_DATE()` to get active configurations** - the status field is less relevant

#### 3. Operational Batching Data (`hdr_kitchen_pod_item`)

Added proper batch definition for analyzing actual kitchen execution:

**Proper Batch Criteria**:
```sql
WHERE CAST(items_in_batch AS INT64) > 1
  AND batch_id != cooking_task_item_id
```

**Why Both Conditions**:
- Without the second condition, solo items (where `batch_id = cooking_task_item_id`) appear as "batches"
- Approximately 80% of items with `batch_id` are NOT actually batched

#### 4. Wing Batching Clarification

**Line Build Configuration**:
- **Batchable wings** (some brands): Have explicit batch component numbers (4000475, 4000478)
- **Not batchable wings** (Wing Trip): NULL component (8011272, 8011274, 8011275, 8011276)

**Operational Reality**:
- Wings that CAN batch (have components) batch by flavor only
- Different sauces = different `batch_eligible_item_id` in sequencing contexts
- Operational data confirms: Zero batches mix different wing flavors
- Reason: Post-fry batch saucing workflow (entire batch tossed in sauce together)

#### 5. Component Name Lookup

Added query pattern for retrieving human-readable component names:

```sql
LEFT JOIN `secure-recipe-prod.recipe_v2.item_versions` iv
  ON batch_item_number = iv.item_number
  AND iv.effective = TRUE
  AND iv.deleted = FALSE
```

**Examples**:
- 4000053 → "Fries, French, Fridge Friendly, 5/16" (Buyout) HC"
- 4000113 → "Chicken Sandwich Filet"
- 4000475 → "Fully Cooked Bone-in Chicken Wing"

### Files Updated

1. **schema-reference.md**:
   - Added `item_line_builds` as primary batch configuration source
   - Added `hdr_kitchen_pod_item` operational batching section
   - Updated NULL batch component explanation (removed "implicit" language)
   - Added proper batch definition with both conditions

2. **common-pitfalls.md**:
   - Added pitfall: "Confusing NULL with Implicit Batching"
   - Added pitfall: "Wrong Batch Definition in Operational Data"
   - Updated wing batching pitfalls with Wing Trip examples

3. **SKILL.md**:
   - Removed all "implicit batching" references
   - Updated core concepts with line build configuration
   - Added operational vs configuration batching distinction
   - Updated wing batching section with NOT batchable examples

### Query Pattern Updates

#### New: Get All Fryer Batch Configuration
```sql
SELECT DISTINCT
  ilb.item_number,
  ilb.sub_steps_related_item_number AS batch_item_number,
  ilb.procedures_batch_limit AS batch_limit,
  CASE
    WHEN ilb.sub_steps_related_item_number IS NULL THEN 'Not Batchable'
    ELSE 'Batchable'
  END AS batch_type
FROM `secure-recipe-prod.recipe_v2.item_line_builds` ilb
WHERE ilb.status = 'LINE_BUILD_CREATED'
  AND ilb.procedures_appliance = 'FRYER'
  AND ilb.sub_steps_order = 1;
```

#### New: Proper Operational Batch Analysis
```sql
SELECT batch_id, COUNT(*) as items
FROM `wonder-dw-prod-brd.orders.hdr_kitchen_pod_item`
WHERE CAST(items_in_batch AS INT64) > 1
  AND batch_id != cooking_task_item_id
GROUP BY batch_id;
```

### Documentation Improvements

- Added examples of NOT batchable items (Wing Trip wings: 8011272, 8011274, 8011275, 8011276)
- Clarified relationship between line build configuration and sequencing runtime behavior
- Distinguished configuration (what CAN batch) from operational reality (what DID batch)
- Added proper batch scoring formula with CP-SAT behavior

### Related Output Files

Generated during this investigation:
- `outputs/all-fryer-items-batch-config-with-names.csv` - Complete fryer batch configuration
- `outputs/all-fryer-items-batch-config-with-names.sql` - Query for batch configuration with component names
- `outputs/WING-BATCHING-FLOW-DIAGRAM.md` - Visual explanation of why wings don't mix flavors
- `outputs/GENERAL-TSOS-FRYER-SUMMARY.md` - Case study showing PENDING_UPDATE items

### Clarifications and Further Details

#### Status Field Clarification

**Status Field Clarification**: The `status` field (LINE_BUILD_CREATED vs PENDING_UPDATE) is less relevant than initially documented. What matters for determining active configurations is **`service_end_time >= CURRENT_DATE()`**. The status field doesn't reliably distinguish deployed vs future configurations - the service date window is the source of truth.

#### NULL Component Number - Configuration Issue, Not Limitation

**CRITICAL CORRECTION**: The characterization of NULL `sub_steps_related_item_number` as "not batchable" was WRONG.

**Actual Behavior**:
- Wing Trip wings with NULL component number ARE batchable
- Currently batch only by identical option values (same flavor) because `related_item_number` points to the SAUCE
- This is a **configuration choice**, not a system limitation

**Current Configuration** (Wing Trip):
```
sub_steps_related_item_number: NULL
→ Batching determined by option values (flavor selection)
→ Buffalo with Buffalo only, BBQ with BBQ only
```

**Planned Fix** (Culinary Team):
```
sub_steps_related_item_number: [chicken_sku]
→ Batching by base chicken component
→ Buffalo with BBQ with Teriyaki (all flavors batch together)
```

**Why the Change Enables Cross-Flavor Batching**:
- Setting `related_item_number` to the chicken SKU makes all wing flavors share the same batch component
- The sauce becomes a post-cooking step (just like fries with different seasonings)
- Allows fryer to batch 3+ wings regardless of flavor, improving throughput

This explains why operational data showed ZERO mixed-flavor batches - it's not that the system can't batch them, it's that the line build configuration currently groups them by sauce.
