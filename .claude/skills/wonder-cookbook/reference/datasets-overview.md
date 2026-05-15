# Datasets Overview - Cookbook Data Sources

Cookbook data spans **4 BigQuery datasets** with **70+ tables**. Understanding which dataset to query is critical for finding the right data.

---

## Dataset Summary

| Dataset | Purpose | Tables | Access |
|---------|---------|--------|--------|
| `secure-recipe-prod.recipe_v2` | Sensitive item/recipe data | 13 | Primary queries |
| `wonder-recipe-prod.recipe_v2` | Non-sensitive item data | 21 | Public attributes |
| `wonder-recipe-prod.mongo_batch_recipe_v2` | Mappings & reference data | 40+ | Lookups, conversions |
| `wonder-raw-prod.mysql_batch_product_catalog` | Product catalog | 8 | SKU/fulfillment mappings |

---

## secure-recipe-prod.recipe_v2 (Sensitive Data)

**Primary dataset** for item and recipe queries. Contains sensitive pricing and cost data.

| Table | Description | Key Fields |
|-------|-------------|------------|
| `item_versions` | **Main table** - All item data with nested JSON | item_number, name, bom_header, effective, deleted |
| `effective_items` | Pre-filtered view (effective=true) | item_number, name, object_type |
| `bom_headers` | Bill of Materials headers | item_number, is_active, item_version_id |
| `bom_lines` | BOM line items (tree structure) | bom_header_item_number, bom_line_item_number, manage_inventory |
| `item_line_builds` | Line build instructions | item_number, procedures_*, cooking_time |
| `recipes` | Recipe data | item_number, instructions |
| `recipes_procedures` | Procedures for recipes | recipe_id, procedure_name |
| `recipes_procedure_steps` | Procedure steps | procedure_id, step_order |
| `assembly_instruction` | Assembly instructions | item_number, notes |
| `ingredients` | Ingredient data | item_number, ingredient_list |
| `components` | Recipe/ingredient composition | parent_item, child_item |
| `all_item_version_customization_nutrition` | Nutrition with customizations | item_number, calories_k_cal, is_preset |
| `concept_restaurant_ids` | Concept to restaurant mappings | concept_id, restaurant_id |

---

## wonder-recipe-prod.recipe_v2 (Non-Sensitive Data)

Non-sensitive item attributes and reference data.

| Table | Description |
|-------|-------------|
| `item_versions` | Item version data (subset of secure) |
| `effective_items` | Currently effective items |
| `allergens` | Allergen data |
| `assembly_instruction` | Assembly instructions |
| `assembly_instruction_histories` | Historical assembly instructions |
| `attributes` | Item attributes |
| `concepts` | Restaurant concepts |
| `food_nutrition_facts` | Nutrition facts data |
| `ingredients` | Ingredient data |
| `item_customization` | Item customization options |
| `item_customizations_flattened` | Flattened customization data |
| `kitchen_locations` | Kitchen location data |
| `kitchen_sub_locations` | Kitchen sub-location data |
| `menus` | Menu data |
| `preparations` | Preparation instructions |
| `recipes` | Recipe data |
| `smallwares` | Smallwares/equipment data |
| `tag_groups` | Tag group definitions |
| `tags` | Tag data |
| `units` | Unit of measure data |
| `vendor_items` | Vendor item data |
| `vendor_items_v2` | Vendor product catalog (v2) |

---

## wonder-recipe-prod.mongo_batch_recipe_v2 (Mappings & Reference)

Reference data, mappings, and sync logs. Use for lookups and conversions.

| Table | Description |
|-------|-------------|
| `units` | Unit of measure definitions |
| `unit_conversions` | Unit conversion data |
| `vendors` | Vendor data |
| `vendor_v2` | Vendor data (v2) |
| `vendor_items` | Vendor item mappings |
| `vendor_items_v2` | Vendor items (v2) |
| `vendor_items_v3` | Vendor items (v3) |
| `vendor_item_units` | Vendor item unit mappings |
| `concepts` | Restaurant concepts |
| `routes` | Route data |
| `route_mappings` | Route mapping data |
| `location_mappings` | Route/facility location mappings |
| `facilities` | Facility data |
| `menus` | Menu data |
| `items` | Items data |
| `item_lists` | Item list data |
| `kitchen_locations` | Kitchen location data |
| `kitchen_sub_locations` | Kitchen sub-location data |
| `preparations` | Preparation instructions |
| `tag_groups` | Tag group definitions |
| `tags` | Tag data |
| `appliance_programs` | Appliance program settings |
| `global_appliance_settings` | Global appliance settings |
| `chef_package_rules` | Chef package rules |
| `comments` | Comments data |
| `erp_item_fields` | ERP item field mappings |
| `filter_codes` | Filter code definitions |
| `inventory_consumable_items` | Inventory consumable items |
| `inventory_item_conversions` | Inventory item conversion data |
| `item_product_coverage_groups` | Product coverage groups |
| `item_version_change_logs` | Item version change history |
| `materials_taxonomies` | Materials taxonomy data |
| `raw_materials_taxonomies` | Raw materials taxonomy |
| `expanded_item_version_customization_costs` | Customization cost data |
| `transfer_cost_change_log` | Transfer cost change history |
| `truck_item_extend_information` | Truck item extended info |
| `spork_bulk_get_recipes` | Spork recipes bulk data |
| `spork_bulk_get_recipe_details` | Spork recipe details |
| `spork_bulk_get_assembly_and_kitting_instructions` | Spork assembly/kitting |
| `spork_get_by_id_item_recipes` | Spork item recipes by ID |
| `sync_api_to_spork_logs` | API to Spork sync logs |

---

## wonder-raw-prod.mysql_batch_product_catalog (Product Catalog)

Product catalog and SKU fulfillment mappings.

| Table | Description |
|-------|-------------|
| `wonder_items` | Wonder items data |
| `wonder_sku_items` | Wonder SKU items |
| `wonder_sku_fulfillment_options` | SKU fulfillment options |
| `wonder_sku_to_fulfillment_options` | SKU to fulfillment option mappings |
| `internal_fulfillment_items` | Internal fulfillment items |
| `ordergrid_items` | Order grid items |
| `pack_relationships` | Pack relationship data |
| `scheduled_40_module_switch_plan` | Scheduled module switch plan |

---

## Agent Logs (wonder-recipe-prod.mongo_batch_recipe_agent)

Agent conversation and invocation logs (for debugging Recipe Agent).

| Table | Description |
|-------|-------------|
| `agent_conversation_logs` | Agent conversation log data |
| `agent_invocation_logs` | Agent invocation log data |
| `agent_session_logs` | Agent session log data |

---

## Which Dataset to Use?

| Use Case | Dataset | Table |
|----------|---------|-------|
| Item lookup by number/name | `secure-recipe-prod.recipe_v2` | `item_versions` or `effective_items` |
| BOM/recipe components | `secure-recipe-prod.recipe_v2` | `item_versions` (nested JSON) |
| Line build instructions | `secure-recipe-prod.recipe_v2` | `item_line_builds` |
| Nutrition data | `secure-recipe-prod.recipe_v2` | `all_item_version_customization_nutrition` |
| Unit conversions | `wonder-recipe-prod.mongo_batch_recipe_v2` | `unit_conversions` |
| Vendor information | `wonder-recipe-prod.mongo_batch_recipe_v2` | `vendor_items_v3` |
| SKU to fulfillment | `wonder-raw-prod.mysql_batch_product_catalog` | `wonder_sku_to_fulfillment_options` |
| Allergens | `wonder-recipe-prod.recipe_v2` | `allergens` |
| Customization options | `wonder-recipe-prod.recipe_v2` | `item_customizations_flattened` |

---

## Cross-Dataset Joins

When joining across datasets, always:
1. Use fully qualified table names with backticks
2. CAST item_number to STRING for joins
3. Include `deleted = false` on item tables

```sql
-- Example: Join item data to product catalog
SELECT
  iv.item_number,
  iv.name,
  wsi.sku
FROM `secure-recipe-prod.recipe_v2.item_versions` iv
LEFT JOIN `wonder-raw-prod.mysql_batch_product_catalog.wonder_sku_items` wsi
  ON CAST(iv.item_number AS STRING) = CAST(wsi.item_number AS STRING)
WHERE iv.effective = true
  AND iv.deleted = false;
```

---

## Configuration Tables (Reference Data)

Cookbook uses several configuration tables for reference data that appears throughout recipes and menu items. These tables are managed via the Cookbook back-office UI.

### Allergens

Allergen configuration for labeling and app display. Data is stored in:
- `wonder-recipe-prod.recipe_v2.allergens`

| Field | Description |
|-------|-------------|
| name | Allergen name (e.g., "Soy", "Fish", "Tree Nuts") |
| code | Allergen code identifier |
| is_visible | Whether visible in mobile app |
| display_name | Display name on app |
| abbreviation | Short code (alphabetic, unique) |
| sub_types | Detailed allergen sub-types for labeling |

**Key Allergen Types:**
- **Major 9 Allergens**: Soy, Milk/Dairy, Fish, Eggs, Peanuts, Sesame, Wheat, Tree Nuts, Shellfish (all visible in app)
- **Fish Sub-types**: Anchovy, Salmon, Tuna, Cod, Sea Bass, etc. (used in ingredient labels)
- **Tree Nuts Sub-types**: Almond, Cashew, Hazelnut, Pecan, Pine Nut, Pistachio, Walnut
- **Shellfish Sub-types**: Crab, Lobster, Shrimp, plus Clam, Scallop, Squid, Octopus (some label-only)
- **Hidden Allergens**: Mustard, Celery, Crustaceans, Lupin, Molluscs, Sulphites (not visible in app)

### Dietary Tags

Dietary preference tags for menu item classification. Data is stored in:
- `wonder-recipe-prod.recipe_v2.tags` (with tag_group = dietary)
- `wonder-recipe-prod.mongo_batch_recipe_v2.tags`
- `wonder-recipe-prod.mongo_batch_recipe_v2.tag_groups`

| Field | Description |
|-------|-------------|
| name | Dietary tag name (e.g., "Vegetarian", "Vegan", "Gluten-Free") |
| abbreviation | Short code (uppercase, unique) |

Dietary tags are user-defined and appear in:
- Menu item creation/editing in Cookbook
- Mobile app dietary preference filters
- Restaurant/menu item tags in customer-facing UI

### Preparations

Preparation methods that describe how ingredients are processed. Data is stored in:
- `wonder-recipe-prod.recipe_v2.preparations`
- `wonder-recipe-prod.mongo_batch_recipe_v2.preparations`

| Field | Description |
|-------|-------------|
| name | Preparation name (e.g., "Diced", "Julienne", "Trim End") |
| type | Either "Process" (physical transformation) or "Reference" (informational) |
| is_active | Active flag (new preparations default to active) |
| usages | Count of recipe components using this preparation |
| created_time | Creation timestamp |
| last_updated_time | Last update timestamp |

**Preparation Types:**
- **Process**: Physical transformation applied to ingredient (e.g., "Dice", "Slice", "Trim End")
- **Reference**: Informational notation (e.g., size specifications, notes)

Preparations appear in component names like: `Carrot, Large [Trim End; Dice]`

### Kitchen Locations

Kitchen station/location configuration for recipe instructions. Data is stored in:
- `wonder-recipe-prod.recipe_v2.kitchen_locations`
- `wonder-recipe-prod.recipe_v2.kitchen_sub_locations`
- `wonder-recipe-prod.mongo_batch_recipe_v2.kitchen_locations`
- `wonder-recipe-prod.mongo_batch_recipe_v2.kitchen_sub_locations`

| Field | Description |
|-------|-------------|
| name | Location name (e.g., "Grill", "Sauté", "Prep") |
| sub_locations | Nested sub-location data |

Kitchen locations are used in:
- Recipe step assignments
- Line build instructions
- Kitchen workflow organization

---

## Related Documentation

- [../schema-reference.md](../schema-reference.md) - Detailed field schemas
- [../core/item-master.md](../core/item-master.md) - Item master queries
