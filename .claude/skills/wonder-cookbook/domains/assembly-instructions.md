# Assembly Instructions

The assembly instruction system defines how menu items are assembled after cooking, including packaging, labeling, and presentation steps. Assembly instructions exist for two distinct item types:

- **88\* (Packaged Items)**: Individual packaged components with their own assembly instructions
- **80\* (Menu/Truck Items)**: Complete menu items that aggregate assembly instructions from their BOM components

## Item Type Distinctions

### 88* Packaged Items
- Have direct assembly instructions attached
- Include packaging specifications (bag, film, MAP gas)
- Document types include: **Cold Pouch ROP**
- Cold Pouch Type values: **"With Retherm ROP"**, **"W/O Retherm ROP"**

### 80* Menu Items (Truck Items)
- Aggregate assembly instructions from nested packaged items
- BOM is exploded until sub-component is NOT a packaged item (!= 88* item)
- Include customization options: **mandatory choice**, **optional addition**, **Dish Preference**, **extra option**
- Deduplicate items (each packaged item appears only once)

## Status Values

Assembly instructions use these status values:
- **ACTIVE** - Published and in use
- **Draft** - In development, shows "Draft" watermark on preview
- **Pending Update** - Awaiting approval, shows "Pending Update" watermark on preview

## Core Table

### assembly_instruction

Assembly instructions for menu items including packaging and presentation.

```sql
-- Key identification fields
item_version_id          STRING    -- Version UUID
item_number              STRING    -- Item ID (88* for packaged, 80* for menu)
service_start_time       DATETIME  -- Service window start
service_end_time         DATETIME  -- Service window end
name                     STRING    -- Instruction name (Document Name in UI)
status                   STRING    -- Instruction status (ACTIVE, Draft, Pending Update)

-- Document and concept
document_type            STRING    -- Type: Cold Pouch ROP, Assembly Build, Kitting, etc.
concept_ids              STRING    -- Associated restaurant concepts (JSON)

-- Cold Pouch specific (when document_type = 'Cold Pouch ROP')
cold_pouch_type          STRING    -- Values: 'With Retherm ROP', 'W/O Retherm ROP'

-- Packaging fields
bag_item_version_ids     STRING    -- Bag/packaging item versions (JSON array)
film_item_version_id     STRING    -- Film packaging version UUID
map_gas_type             STRING    -- Modified atmosphere packaging gas type

-- Assembly details
label                    STRING    -- Label information
image_keys               STRING    -- Image references (JSON array)
notes                    STRING    -- Assembly notes
assembly_build_information STRING  -- Build details (JSON)
bom_lines                STRING    -- BOM lines for assembly (JSON)

-- Audit fields
created_by               STRING    -- Creator name
created_time             DATETIME  -- Creation timestamp
updated_by               STRING    -- Last updater (Last Updated in UI)
updated_time             DATETIME  -- Last update timestamp
```

## Query Patterns

### Get Assembly Instructions for a Menu Item

```sql
SELECT
  ai.item_number,
  ei.name as item_name,
  ai.name as instruction_name,
  ai.status,
  ai.document_type,
  ai.label,
  ai.notes,
  ai.map_gas_type
FROM `secure-recipe-prod.recipe_v2.assembly_instruction` ai
LEFT JOIN `secure-recipe-prod.recipe_v2.effective_items` ei
  ON ai.item_number = CAST(ei.item_number AS STRING)
WHERE ai.item_number = '8009068'
  AND CURRENT_TIMESTAMP() BETWEEN TIMESTAMP(ai.service_start_time) AND TIMESTAMP(ai.service_end_time)
ORDER BY ai.name;
```

### Find Items with Specific Packaging Type

```sql
SELECT DISTINCT
  ai.item_number,
  ei.name as item_name,
  ai.map_gas_type,
  ai.label
FROM `secure-recipe-prod.recipe_v2.assembly_instruction` ai
LEFT JOIN `secure-recipe-prod.recipe_v2.effective_items` ei
  ON ai.item_number = CAST(ei.item_number AS STRING)
WHERE ai.map_gas_type IS NOT NULL
  AND ei.object_type = 'MENU'
  AND ei.item_status = 'ACTIVE'
  AND CURRENT_TIMESTAMP() BETWEEN TIMESTAMP(ai.service_start_time) AND TIMESTAMP(ai.service_end_time)
ORDER BY ei.name;
```

### Get Assembly Instructions by Concept

```sql
SELECT
  ai.item_number,
  ei.name as item_name,
  ai.name as instruction_name,
  ai.concept_ids
FROM `secure-recipe-prod.recipe_v2.assembly_instruction` ai
LEFT JOIN `secure-recipe-prod.recipe_v2.effective_items` ei
  ON ai.item_number = CAST(ei.item_number AS STRING)
WHERE ai.concept_ids LIKE '%"concept_id_here"%'
  AND CURRENT_TIMESTAMP() BETWEEN TIMESTAMP(ai.service_start_time) AND TIMESTAMP(ai.service_end_time)
ORDER BY ei.name;
```

### List All Active Assembly Instructions

```sql
SELECT
  ai.item_number,
  ei.name as item_name,
  ai.name as instruction_name,
  ai.status,
  ai.updated_time
FROM `secure-recipe-prod.recipe_v2.assembly_instruction` ai
LEFT JOIN `secure-recipe-prod.recipe_v2.effective_items` ei
  ON ai.item_number = CAST(ei.item_number AS STRING)
WHERE ai.status = 'ACTIVE'
  AND ei.object_type = 'MENU'
  AND ei.item_status = 'ACTIVE'
  AND CURRENT_TIMESTAMP() BETWEEN TIMESTAMP(ai.service_start_time) AND TIMESTAMP(ai.service_end_time)
ORDER BY ai.updated_time DESC
LIMIT 100;
```

### Find Cold Pouch ROP Items

```sql
-- Find packaged items (88*) with Cold Pouch ROP instructions
SELECT
  ai.item_number,
  ei.name as item_name,
  ai.document_type,
  ai.cold_pouch_type,
  ai.map_gas_type,
  ai.status
FROM `secure-recipe-prod.recipe_v2.assembly_instruction` ai
LEFT JOIN `secure-recipe-prod.recipe_v2.effective_items` ei
  ON ai.item_number = CAST(ei.item_number AS STRING)
WHERE ai.document_type = 'Cold Pouch ROP'
  AND ai.item_number LIKE '88%'
  AND CURRENT_TIMESTAMP() BETWEEN TIMESTAMP(ai.service_start_time) AND TIMESTAMP(ai.service_end_time)
ORDER BY ei.name;
```

### Get Assembly Instructions for 88* Packaged Items

```sql
-- Get assembly instructions for packaged items only
SELECT
  ai.item_number,
  ei.name as item_name,
  ai.name as instruction_name,
  ai.document_type,
  ai.cold_pouch_type,
  ai.bag_item_version_ids,
  ai.film_item_version_id,
  ai.status
FROM `secure-recipe-prod.recipe_v2.assembly_instruction` ai
LEFT JOIN `secure-recipe-prod.recipe_v2.effective_items` ei
  ON ai.item_number = CAST(ei.item_number AS STRING)
WHERE ai.item_number LIKE '88%'
  AND CURRENT_TIMESTAMP() BETWEEN TIMESTAMP(ai.service_start_time) AND TIMESTAMP(ai.service_end_time)
ORDER BY ei.name;
```

### Parse Assembly Build Information

```sql
-- Extract assembly build details from JSON
SELECT
  ai.item_number,
  ei.name as item_name,
  JSON_EXTRACT_SCALAR(ai.assembly_build_information, '$.step') as build_step,
  ai.assembly_build_information
FROM `secure-recipe-prod.recipe_v2.assembly_instruction` ai
LEFT JOIN `secure-recipe-prod.recipe_v2.effective_items` ei
  ON ai.item_number = CAST(ei.item_number AS STRING)
WHERE ai.assembly_build_information IS NOT NULL
  AND ai.item_number = '8009068'
  AND CURRENT_TIMESTAMP() BETWEEN TIMESTAMP(ai.service_start_time) AND TIMESTAMP(ai.service_end_time);
```

## Audit Table

For tracking assembly instruction changes:

```sql
-- Assembly instruction change history
SELECT *
FROM `secure-recipe-prod.mongo_batch_recipe_v2.assembly_instruction_histories`
WHERE item_number = '8009068'
ORDER BY updated_time DESC
LIMIT 10;
```

## Service Window Filtering

Assembly instructions use service windows:

```sql
AND CURRENT_TIMESTAMP() BETWEEN TIMESTAMP(service_start_time) AND TIMESTAMP(service_end_time)
```

## BOM Explosion Logic for Menu Items

When retrieving assembly instructions for a menu item (80*), the system:

1. **Explodes the BOM** recursively until reaching non-packaged items
2. **Finds overlapping versions** - Gets the BOM line version that overlaps with the effective time of the parent item
3. **Resolves multi-version conflicts** - If multiple sub-component versions are effective, compares start time with now to get the active version
4. **Includes customization items** - Also explodes:
   - Mandatory choice items
   - Optional addition items
   - Dish Preference items
   - Extra option items
5. **Deduplicates** - Each packaged item appears only once in the assembly table

## UI Display Fields

The assembly instructions card displays:
- **Document Name** - Instruction name
- **Document Type** - Assembly document type
- **Status** - Color-coded chips (Draft, Pending Update, Active)
- **Last Updated** - Timestamp of last modification

For menu items, the assembly table shows:
- **Item Type** - Object type (packaged item, etc.)
- **Item Name** - Display name
- **Item Version** - Version identifier
- **Document Type** - Links to assembly detail page
- **Action** - Preview/print functionality

## Related Documentation

- [line-build.md](line-build.md) - Kitchen prep before assembly
- [recipes-procedures.md](recipes-procedures.md) - Cooking procedures
- [../core/bom-components.md](../core/bom-components.md) - Component ingredients

---

## Code References (Java Codebase)

> **Codebase**: `master-data-management-2`
> **Validated**: 2026-01-28

### Domain Models

- **AssemblyInstruction**: `backend/domain-library/src/main/java/app/internalrecipe/item/pouching/AssemblyInstruction.java`
  - Embedded in ItemVersion.assemblyInstructions (List<AssemblyInstruction>)
  - Key fields: `status`, `documentType`, `coldPouchType`, `conceptIds`, `name`, `bomLines`
  - Packaging: `bagItemVersionIds`, `filmItemVersionId`, `mapGasType`
  - Nested classes: `BomLine`, `ExplodedBomLine`, `Tool`, `AssemblyBuildInformation`, `AssemblyBuild`

- **AssemblyInstruction.BomLine**: BOM line in assembly context
  - Fields: `itemNumber`, `itemVersionId`, `quantity`, `unit`, `preparationIds`, `containers`, `modifications`

- **AssemblyInstruction.AssemblyBuildInformation**: Build steps with images
  - Fields: `combinedImageKeys`, `assemblyBuilds` (list of step/image/description)

- **AssemblyInstructionHistory**: `backend/domain-library/src/main/java/app/internalrecipe/item/pouching/AssemblyInstructionHistory.java`
  - Audit trail for assembly instruction changes

### Enums

- **AsseemblyDocumentType**: `backend/domain-library/src/main/java/app/internalrecipe/item/pouching/AsseemblyDocumentType.java`
  - Values: `COLD_POUCH_ROP`, `ASSEMBLY_BUILD`, `KITTING`, etc.
  - Note: Class name has typo "Asseembly" (two 'e's)

- **AssemblyColdPouchType**: `backend/domain-library/src/main/java/app/internalrecipe/item/pouching/AssemblyColdPouchType.java`
  - Values: `WITH_RETHERM_ROP`, `WO_RETHERM_ROP`

- **AssemblyStatusType**: `backend/domain-library/src/main/java/app/internalrecipe/item/pouching/AssemblyStatusType.java`
  - Values: `ACTIVE`, `DRAFT`, `PENDING_UPDATE`

- **AssemblyInstructionMapGasType**: `backend/domain-library/src/main/java/app/internalrecipe/item/pouching/AssemblyInstructionMapGasType.java`
  - MAP gas types for packaging

- **AssemblyInstructionContainer**: `backend/domain-library/src/main/java/app/internalrecipe/item/pouching/AssemblyInstructionContainer.java`
  - Container specifications

- **AssemblyInstructionModification**: `backend/domain-library/src/main/java/app/internalrecipe/item/pouching/AssemblyInstructionModification.java`
  - Assembly modifications

- **PouchingLabel**: `backend/domain-library/src/main/java/app/internalrecipe/item/pouching/PouchingLabel.java`
  - Label information for packaging

### Service Layer

- **BOItemBomHeaderPouchingService**: `backend/internal-recipe-service/src/main/java/app/internalrecipe/item/service/bomheader/assembly/BOItemBomHeaderPouchingService.java`
  - Core assembly instruction operations

- **BOItemBomHeaderPouchingGetService**: `backend/internal-recipe-service/src/main/java/app/internalrecipe/item/service/bomheader/assembly/BOItemBomHeaderPouchingGetService.java`
  - Query assembly instructions

- **BOItemBomHeaderPouchingUpdateService**: `backend/internal-recipe-service/src/main/java/app/internalrecipe/item/service/bomheader/assembly/BOItemBomHeaderPouchingUpdateService.java`
  - Update assembly instructions

- **BOItemBOMHeaderPouchingCheckService**: `backend/internal-recipe-service/src/main/java/app/internalrecipe/item/service/bomheader/assembly/BOItemBOMHeaderPouchingCheckService.java`
  - Validation for assembly instructions

- **BOItemBomHeaderAssemblyHistoryService**: `backend/internal-recipe-service/src/main/java/app/internalrecipe/item/service/bomheader/assembly/BOItemBomHeaderAssemblyHistoryService.java`
  - Assembly history management

- **BOItemKittingInstructionHistoryService**: `backend/internal-recipe-service/src/main/java/app/internalrecipe/item/service/kittinginstruction/BOItemKittingInstructionHistoryService.java`
  - Kitting instruction history

- **ItemAssemblyInstructionPDFService**: `backend/master-data-file-service/src/main/java/app/file/pdf/service/ItemAssemblyInstructionPDFService.java`
  - PDF export for assembly instructions

### @Deprecated Fields

No @Deprecated annotations found in assembly instruction domain classes.
