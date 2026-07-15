---
name: wonder-cookbook
description: Expert knowledge of Wonder's Cookbook recipe and BOM (Bill of Materials) system. Use when analyzing menu item recipes, component items/ingredients, required vs optional component items, and menu availability logic.
allowed-tools: Read, Grep, Glob
---

# wonder-cookbook

Cookbook is Wonder's recipe management system that defines the Bill of Materials (BOM) for all menu items. It specifies which component ingredients are required vs optional, tracks recipe evolution over time through service windows, and determines menu item availability logic.

## Quick Start

**Databases**: 4 datasets, 70+ tables (see [reference/datasets-overview.md](reference/datasets-overview.md))
- Primary: `secure-recipe-prod.recipe_v2`

**Most Important Tables**:
- `item_versions` - All item data with nested BOM JSON
- `effective_items` - Pre-filtered current items (most queried)
- `item_line_builds` - Kitchen prep assignments

---

## Essential Filter (ALWAYS USE)

**CRITICAL**: Always include `deleted = false` to exclude soft-deleted items:

```sql
WHERE effective = true
  AND deleted = false
  AND item_status != 'DORMANT'
```

Even when using `effective_items`, you MUST include `deleted = false`.

---

## Primary BOM Query Pattern (Nested JSON)

The **recommended** pattern uses nested JSON in `item_versions`:

```sql
SELECT
  m.item_number,
  m.name,
  JSON_VALUE(bom_line, '$.item_number') AS component_item,
  SAFE_CAST(JSON_EXTRACT_SCALAR(bom_line, '$.quantity') AS FLOAT64) AS quantity,
  JSON_VALUE(bom_line, '$.uom') AS uom
FROM `secure-recipe-prod.recipe_v2.item_versions` m,
UNNEST(JSON_EXTRACT_ARRAY(m.bom_header, '$.bom_lines')) AS bom_line
WHERE m.effective = true
  AND m.deleted = false
  AND m.item_status != 'DORMANT'
  AND m.item_number = '8009068';
```

## Alternative: Separate BOM Tables

Use `bom_headers`/`bom_lines` for cross-item analysis:

```sql
SELECT DISTINCT
  bh.item_number as menu_item_id,
  ei.name as menu_item_name,
  bl.bom_line_item_number as component_id,
  ei_comp.name as component_name,
  bl.manage_inventory as is_required
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
  AND bh.item_number = '8009068'
  AND CURRENT_TIMESTAMP() BETWEEN TIMESTAMP(bl.service_start_time) AND TIMESTAMP(bl.service_end_time)
ORDER BY bl.manage_inventory DESC, component_id;
```

## Domain Index

### Core Concepts (Start Here)

| Document | Purpose |
|----------|---------|
| [core/bom-components.md](core/bom-components.md) | BOM headers/lines, nested JSON pattern, required vs optional |
| [core/item-master.md](core/item-master.md) | `item_versions` vs `effective_items`, item number prefixes |
| [core/service-windows.md](core/service-windows.md) | Recipe versioning, time-based filtering |
| [core/tags-categorization.md](core/tags-categorization.md) | Tags, tag groups, item categorization via attributes |

### Functional Domains

| Document | Purpose |
|----------|---------|
| [domains/recipes-procedures.md](domains/recipes-procedures.md) | Cooking instructions, procedure steps |
| [domains/line-build.md](domains/line-build.md) | Kitchen prep lines, appliances, activity types |
| [domains/assembly-instructions.md](domains/assembly-instructions.md) | Assembly after cooking |
| [domains/nutrition.md](domains/nutrition.md) | Nutrition facts, allergens |
| [domains/customization.md](domains/customization.md) | Customer choices (MANDATORY_CHOICE, OPTIONAL_ADDITION) |
| [domains/packaged-skus.md](domains/packaged-skus.md) | Pre-packaged 88*/7* components + **9\* containers / IK dish type ↔ packaging** (same concept; incl. Wonder Create auto-assign, MD-18063), service location, smallware tools |
| [domains/hdr-consumables.md](domains/hdr-consumables.md) | HDR consumables (40*) and WSKUs (41*), the "40 Model" |
| [domains/cost-pricing.md](domains/cost-pricing.md) | Item costs, menu prices, margins |
| [domains/units-of-measure.md](domains/units-of-measure.md) | UOM fields, conversions across contexts |
| [domains/food-science.md](domains/food-science.md) | Shelf life, storage requirements |
| [domains/vendor-items.md](domains/vendor-items.md) | External vendor SKU linkage, OG sync |
| [domains/logistics.md](domains/logistics.md) | Storage, receiving info, space management |
| [domains/menu-management.md](domains/menu-management.md) | Menu collections, concept associations, recipe exports |
| [domains/benchtop-recipe.md](domains/benchtop-recipe.md) | R&D/test kitchen recipes, commercialization workflow |

### Cross-System Integration

| Document | Purpose |
|----------|---------|
| [cross-system/pantry-integration.md](cross-system/pantry-integration.md) | Check component stock levels |
| [cross-system/orders-integration.md](cross-system/orders-integration.md) | Menu item sales analysis |
| [cross-system/supply-chain-integration.md](cross-system/supply-chain-integration.md) | POMS purchase orders, fill rates |
| [cross-system/vendor-catalog-service.md](cross-system/vendor-catalog-service.md) | Real-time vendor product data (Kafka events) |

### Reference

| Document | Purpose |
|----------|---------|
| [reference/datasets-overview.md](reference/datasets-overview.md) | 4 datasets, 70+ tables overview |
| [schema-reference.md](schema-reference.md) | Complete table schemas |
| [common-pitfalls.md](common-pitfalls.md) | Common mistakes to avoid |
| ⭐ **Data Research Patterns** → `Z01-Resource/CB-bigquery/playbooks/data-research-patterns.md` | **MUST read for EVERY data analysis task** — data source selection, brand filtering, BOM+customization UNION, 9* packaging methodology, deep analysis patterns, AND 3 critical customization pitfalls (option_value grouping level, FOR_SALE/FINAL/preset filters, item_versions JSON vs flatten table) |

## Key Concepts

### Required vs Optional Components

**THE KEY FIELD**: `bom_lines.manage_inventory`

| Value | Impact | Examples |
|-------|--------|----------|
| `true` | **REQUIRED** - Menu item unavailable if out of stock | Proteins, signature sauces |
| `false` | **OPTIONAL** - Doesn't affect availability | Packaging, garnishes |

### Service Windows

Recipes evolve over time. Always filter to current recipe:

```sql
AND CURRENT_TIMESTAMP() BETWEEN TIMESTAMP(bl.service_start_time) AND TIMESTAMP(bl.service_end_time)
```

### Table Selection

| Need | Use |
|------|-----|
| Current item lookup | `effective_items` (pre-filtered, fastest) |
| Historical analysis | `item_versions` (full history) |
| Recipe components | `bom_headers` + `bom_lines` |

## Common Tasks

**"What ingredients are in this menu item?"** → [core/bom-components.md](core/bom-components.md)

**"Why is this item showing out of stock?"** → Check required components: [cross-system/pantry-integration.md](cross-system/pantry-integration.md)

**"What's been ordered for this component?"** → [cross-system/supply-chain-integration.md](cross-system/supply-chain-integration.md)

**"What's the shelf life?"** → [domains/food-science.md](domains/food-science.md)

**"How is this item cooked?"** → [domains/line-build.md](domains/line-build.md) + [domains/recipes-procedures.md](domains/recipes-procedures.md)

**"What's the nutrition info?"** → [domains/nutrition.md](domains/nutrition.md)

**"What customization options exist?"** → [domains/customization.md](domains/customization.md)

**"What's the cost/margin?"** → [domains/cost-pricing.md](domains/cost-pricing.md)

**"How do units convert?"** → [domains/units-of-measure.md](domains/units-of-measure.md)

**"How has this recipe changed?"** → [core/service-windows.md](core/service-windows.md)

**"What tags/categories does this item have?"** → [core/tags-categorization.md](core/tags-categorization.md)

**"Which vendor SKUs are linked to this ingredient?"** → [domains/vendor-items.md](domains/vendor-items.md)

**"What are the storage/logistics requirements?"** → [domains/logistics.md](domains/logistics.md)

**"What packaged items (88*/7*) are in this menu item?"** → [domains/packaged-skus.md](domains/packaged-skus.md)

**"What IK dish type does an item get?" / "How is packaging assigned?"** → [domains/packaged-skus.md](domains/packaged-skus.md) (§ IK Dish Type) — note: **"IK dish type" = "packaging"** (same concept, 9* container)

**"How does Wonder Create / WC assign packaging or dish type to its menu items?"** → [domains/packaged-skus.md](domains/packaged-skus.md) (§ IK Dish Type) — auto-inferred from green count / weight (MD-18063); search **"packaging"** not "dish type"

**"What dish type do BYO / zero-BOM bowls get?"** → [domains/packaged-skus.md](domains/packaged-skus.md) (§ IK Dish Type) — NOT in the BOM; inferred from Green components + total weight

**"What 9* non-food packaging/container items are used by these brands?"** → ⭐ **Read `Z01-Resource/CB-bigquery/playbooks/data-research-patterns.md` FIRST** — then [domains/packaged-skus.md](domains/packaged-skus.md)

**"Find which brands use X packaging" / "Compare packaging across brands"** → ⭐ **Read `Z01-Resource/CB-bigquery/playbooks/data-research-patterns.md` FIRST**

**"Analyze data across brands/menus" / "Cross-dataset research"** → ⭐ **Read `Z01-Resource/CB-bigquery/playbooks/data-research-patterns.md` FIRST**

**"What are the 40*/41* consumables and WSKUs?"** → [domains/hdr-consumables.md](domains/hdr-consumables.md)

**"Which tables should I use?"** → [reference/datasets-overview.md](reference/datasets-overview.md)

**"What menus contain this item?"** → [domains/menu-management.md](domains/menu-management.md)

**"What items are in this menu?"** → [domains/menu-management.md](domains/menu-management.md)

**"What are benchtop recipes?"** → [domains/benchtop-recipe.md](domains/benchtop-recipe.md)

**"How do I commercialize a benchtop item?"** → [domains/benchtop-recipe.md](domains/benchtop-recipe.md)

## Critical Rules

1. **Always include `deleted = false`** - even on `effective_items`
2. **Prefer nested JSON BOM pattern** for single-item lookups
3. **Always filter service windows** for current recipes (separate BOM tables)
4. **Prefer `effective_items`** over `item_versions` for current items
5. **Filter `bom_headers.is_active = true`** to exclude archived BOMs
6. **Use LEFT JOIN** for item metadata (not all components have metadata)
7. **CAST item_number to STRING** when joining across tables
8. **Check `manage_inventory`** when analyzing availability blockers
9. **Use item_number prefix** to identify object type (80*=menu, 50*=ingredient)

---

## Validation Status

**Last Validated**: 2026-01-28
**Codebase**: `master-data-management-2`
**Status**: Fully validated with code references

All 18 domain documentation files include a "Code References (Java Codebase)" section that maps BigQuery schemas to Java domain models, services, and API endpoints. This enables Claude to assist with both data analysis AND programming tasks.

### Validated Domains

| Category | Count | Domains |
|----------|-------|---------|
| Core | 4 | BOM Components, Item Master, Service Windows, Tags & Categorization |
| Functional | 14 | Recipes & Procedures, Line Build, Assembly Instructions, Nutrition, Customization, Packaged SKUs, HDR Consumables, Cost & Pricing, Units of Measure, Food Science, Vendor Items, Logistics, Menu Management, Benchtop Recipe |

### @Deprecated Fields

~55+ @Deprecated annotations identified across the codebase. Each domain's documentation includes a "@Deprecated Field Summary" table documenting fields that may affect queries. Key areas:

- **Food Science**: 8 deprecated shelf-life fields (migration from days to minutes)
- **Vendor Items**: Deprecated `Vendor` class (use `VendorV2`)
- **Recipe**: 5 deprecated fields (relocated to ItemVersion level)
- **NewObjectType**: 2 deprecated values (`COMMON_STOCK_TOTE`, `MOBILE_SF`)

### Code Reference Coverage

| Metric | Count |
|--------|-------|
| Domain models documented | 120+ |
| Service classes referenced | 60+ |
| API endpoints documented | 100+ |
| MongoDB collections identified | 25+ |

### Maintenance Notes

- Re-validate after major MDM releases
- Update @Deprecated summaries when fields are removed
- Check for new domains added to Cookbook
