# Partial-Select Salad/Bowl BYO Menu Items — Machine Eligible Report

**Date**: 2026-07-01
**Scope**: FOR_SALE salad/bowl parent BYO menu items with PARTIAL_SELECT customization (presets excluded)

---

## Summary

共 **8 个主 BYO menu item**，均采用 `MANDATORY_CHOICE` + `PARTIAL_SELECT` 定制化模式，**没有**任何一个 menu item 的所有 mapped component 都是 machine eligible。

---

## Results Detail

### ✅ Machine Eligible = YES（28 条）

| Menu Item Number | Menu Item Name | Customization | Option | Mapped Component | Component Name |
|-----------------|----------------|--------------|--------|-----------------|----------------|
| 8010459 | BYO Greens Bowl, Royal Greens BOWLDER - Primary ID | Base | Crispy Leaf | 4000471 | Crispy Leaf Lettuce |
| | | | Grains | 4000381 | Grain Mix |
| | | | Romaine | 4000474 | Chopped Romaine Lettuce |
| | | | Shredded Kale | 4000428 | Curly Kale Lettuce |
| | | | Spring Mix | 4000470 | Spring Mix Lettuce |
| 8010492 | BYO Greens Bowl, Royal Greens BOWLDER - Abridged Rail ID | Base | Crispy Leaf | 4000471 | Crispy Leaf Lettuce |
| | | | Grains | 4000381 | Grain Mix |
| | | | Romaine | 4000474 | Chopped Romaine Lettuce |
| | | | Shredded Kale | 4000428 | Curly Kale Lettuce |
| | | | Spring Mix | 4000470 | Spring Mix Lettuce |
| 8011814 | BYO Greens Bowl, Royal Greens BOWLDER - Primary ID (C&C Pilot) | Base | Crispy Leaf | 4000471 | Crispy Leaf Lettuce |
| | | | Grains | 4000381 | Grain Mix |
| | | | Romaine | 4000474 | Chopped Romaine Lettuce |
| | | | Shredded Kale | 4000428 | Curly Kale Lettuce |
| | | | Spring Mix | 4000470 | Spring Mix Lettuce |
| 8010473 | BYO Poke Bowl, Hanu Poke BOWLDER | Choose Your Protein | Salmon | 4000835 | Diced Salmon |
| | | | Tofu | 4000574 | Tofu [THAW] |
| | | | Tuna | 4000827 | Diced Tuna |
| 8011363 | BYO, Pop Salad | Base | Romaine | 4000474 | Chopped Romaine Lettuce |
| | | | Shredded Kale | 4000428 | Curly Kale Lettuce |
| | | | Spring Mix | 4000470 | Spring Mix Lettuce |
| 8011816 | BYO, Pop Salad (C&C Pilot) | Base | Romaine | 4000474 | Chopped Romaine Lettuce |
| | | | Shredded Kale | 4000428 | Curly Kale Lettuce |
| | | | Spring Mix | 4000470 | Spring Mix Lettuce |
| 8007403 | Bowl (BYO), Yasas | Choose Your Base | Lentils & Bulgur | 4000850 | Lentil Bulgur Mix (Co-Man) |
| | | | Romaine | 4000427 | Romaine Lettuce |
| 8011837 | Bowl (BYO), Yasas (C&C Pilot) | Choose Your Greens | Romaine | 4000427 | Romaine Lettuce |

### ❌ Machine Eligible = NO（14 条）

| Menu Item | Customization | Option | Mapped Component | Component Name | Notes |
|-----------|--------------|--------|-----------------|----------------|-------|
| 8010459 | Base | Soba Noodles | 4000968 | Soba Noodles | Missing ME tag |
| 8010492 | Base | Soba Noodles | 4000968 | Soba Noodles | Same as above |
| 8011814 | Base | Soba Noodles | 4000968 | Soba Noodles | Same as above |
| 8010473 | Choose Your Protein | Chilled Shrimp | 4000644 | Roasted Shrimp | Missing ME tag |
| 8011363 | Base | Romaine | 9000041 | Bowl, 48oz, Natural, Round, Pulp | Non-food packaging — likely by design |
| | Base | Shredded Kale | 9000041 | Same as above | Non-food packaging |
| | Base | Spring Mix | 9000041 | Same as above | Non-food packaging |
| 8011816 | Base | Romaine | 9000041 | Bowl, 48oz, Natural, Round, Pulp | Non-food packaging |
| | Base | Shredded Kale | 9000041 | Same as above | Non-food packaging |
| | Base | Spring Mix | 9000041 | Same as above | Non-food packaging |
| 8007403 | Choose Your Base | Brown Rice | 7000079 | Brown Jasmine Rice (Cooked) [Rice Cooker, 10x] | Missing ME tag |
| | Choose Your Base | Jasmine Rice | 7000078 | White Jasmine Rice (Cooked) [Rice Cooker, 12x] | Missing ME tag |
| | Choose Your Base | Supergreens Mix | 7000040 | Supergreens Mix [1x Deep, 6" Half Hotel] | Missing ME tag |
| 8011837 | Choose Your Greens | Supergreens Mix | 7000040 | Supergreens Mix [1x Deep, 6" Half Hotel] | Missing ME tag |

---

## Per-Item Summary

| Menu Item Number | Menu Item | ME / Total | Non-ME Components |
|-----------------|-----------|------------|-------------------|
| 8010459 | BYO Greens Bowl, Royal Greens BOWLDER - Primary ID | 5 / 6 | 4000968 (Soba Noodles) |
| 8010492 | BYO Greens Bowl, Royal Greens BOWLDER - Abridged Rail ID | 5 / 6 | 4000968 (Soba Noodles) |
| 8011814 | BYO Greens Bowl, Royal Greens BOWLDER - Primary ID (C&C Pilot) | 5 / 6 | 4000968 (Soba Noodles) |
| 8010473 | BYO Poke Bowl, Hanu Poke BOWLDER | 3 / 4 | 4000644 (Roasted Shrimp) |
| 8011363 | BYO, Pop Salad | 3 / 6 | 9000041 ×3 (packaging, can ignore) |
| 8011816 | BYO, Pop Salad (C&C Pilot) | 3 / 6 | 9000041 ×3 (packaging, can ignore) |
| 8007403 | Bowl (BYO), Yasas | 2 / 5 | 7000079, 7000078, 7000040 |
| 8011837 | Bowl (BYO), Yasas (C&C Pilot) | 1 / 2 | 7000040 |

---

## Non-ME Component Analysis

| Component | Name | Type | Affected BYOs | Action |
|-----------|------|------|---------------|--------|
| 4000968 | Soba Noodles | HDR_CONSUMABLE | Royal Greens BOWLDER (×3) | Add ME tag |
| 4000644 | Roasted Shrimp | HDR_CONSUMABLE | Hanu Poke BOWLDER | Add ME tag |
| 7000079 | Brown Jasmine Rice (Cooked) | HDR_RECIPE | Yasas Bowl | Add ME tag or substitute |
| 7000078 | White Jasmine Rice (Cooked) | HDR_RECIPE | Yasas Bowl | Add ME tag or substitute |
| 7000040 | Supergreens Mix | HDR_RECIPE | Yasas Bowl (×2) | Add ME tag or substitute |
| 9000041 | Bowl, 48oz, Natural, Round, Pulp | NON_FOOD | Pop Salad (×2) | Non-food — can ignore |

> **Note on Pop Salad**: Each green option has TWO mapped items — one food component (4000xxx, ME=YES) and one packaging item (9000041, ME=NO). This is a food+packaging pair pattern. The 9000041 entries are non-food packaging and likely don't need ME tag.

---

## Key Observations

1. **No BYO menu item has 100% ME coverage** — all have at least one non-ME mapped component
2. **Royal Greens BOWLDER** is closest at 5/6 — only Soba Noodles (`4000968`) missing ME tag
3. **Yasas** has the biggest gap — rice items (7000078, 7000079) and Supergreens Mix (7000040) are HDR_RECIPE types (7* prefix), which may need a different approach to mark as ME
4. **Hanu Poke** is 3/4 — only Chilled Shrimp (`4000644`) missing ME tag
5. All customizations are `MANDATORY_CHOICE` type — customer must pick one option
6. All items have `max_options = 1` per Partial-select rules, allowing half portions of two options (50%+50%)

---

## Excluded

- **~100 preset items** excluded — presets inherit customization from parent BYO items
- Preset naming pattern: "..., Royal Greens PRESET", "..., Hanu Poke PRESET" etc.

---

## SQL Query

```sql
WITH partial_select_items AS (
  SELECT DISTINCT
    iv.item_number,
    iv.name,
    JSON_VALUE(opt, "$.type") AS customization_type,
    JSON_VALUE(opt, "$.name") AS customization_name,
    opt AS option_raw
  FROM `secure-recipe-prod.recipe_v2.item_versions` iv,
    UNNEST(JSON_EXTRACT_ARRAY(iv.item_customization, "$.options")) AS opt
  WHERE iv.effective = true
    AND iv.deleted = false
    AND iv.item_status != "DORMANT"
    AND iv.sold_status = "FOR_SALE"
    AND iv.object_type = "MENU"
    AND JSON_VALUE(opt, "$.custom_type") = "PARTIAL_SELECT"
    AND (LOWER(iv.name) LIKE "%salad%" OR LOWER(iv.name) LIKE "%bowl%")
    AND iv.preset_item_version_info IS NULL
),
mapped_items AS (
  SELECT
    psi.item_number AS menu_item_number,
    psi.name AS menu_item_name,
    psi.customization_type,
    psi.customization_name,
    JSON_VALUE(ov, "$.name") AS option_value_name,
    JSON_VALUE(item, "$.item_number") AS mapped_component_number
  FROM partial_select_items psi,
    UNNEST(JSON_EXTRACT_ARRAY(psi.option_raw, "$.option_values")) AS ov,
    UNNEST(JSON_EXTRACT_ARRAY(ov, "$.items")) AS item
  WHERE JSON_EXTRACT_ARRAY(ov, "$.items") IS NOT NULL
),
machine_eligible_items AS (
  SELECT DISTINCT iv.item_number
  FROM `secure-recipe-prod.recipe_v2.item_versions` iv,
    UNNEST(JSON_EXTRACT_ARRAY(iv.attributes)) AS attr
  WHERE iv.effective = true
    AND iv.deleted = false
    AND JSON_VALUE(attr, "$.tag_id") = "MACHINE_ELIGIBLE_YES"
)
SELECT
  mi.menu_item_number,
  mi.menu_item_name,
  mi.customization_type,
  mi.customization_name,
  mi.option_value_name,
  mi.mapped_component_number,
  ei.name AS component_name,
  CASE WHEN me.item_number IS NOT NULL THEN "YES" ELSE "NO" END AS machine_eligible
FROM mapped_items mi
LEFT JOIN machine_eligible_items me ON mi.mapped_component_number = me.item_number
LEFT JOIN `secure-recipe-prod.recipe_v2.effective_items` ei
  ON mi.mapped_component_number = CAST(ei.item_number AS STRING)
  AND ei.deleted = false
ORDER BY machine_eligible DESC, mi.menu_item_name, mi.option_value_name;
```
