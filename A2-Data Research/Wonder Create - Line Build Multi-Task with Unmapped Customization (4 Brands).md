# Line Build Multi-Task with Unmapped Customization Options — 4 Brand Analysis

**Date**: 2026-07-15
**Project**: Wonder Create
**Scope**: Royal Greens, Limesalt, Yasas, Hanu Poke — menu items whose **line build has multiple tasks (≥2)** AND **≥2 tasks are NOT mapped to any customization option**. Filters: `sold_status IN ('FOR_SALE','SCHEDULED')`, non-expired service window, `item_status != 'DORMANT'`, presets excluded.

---

## Summary

| Metric | Value |
|--------|-------|
| Qualifying menu items (**≥2 tasks, ≥2 unmapped**) | **3** |
| Brands affected | Yasas (2), Royal Greens / Hanu Poke (1) |
| Brand items in scope (FOR_SALE/SCHEDULED + filters + has line build) | 66 |
| — of which SCHEDULED | **0** (all 66 are FOR_SALE) |
| Multi-task items (≥2 tasks) | 17 |
| Items with exactly 1 unmapped task (excluded) | 14 |
| Items with ≥2 unmapped tasks (**match**) | **3** |

### Result

| Brand | Item # | Name | sold / version | Total tasks | Unmapped tasks (no customization) |
|-------|--------|------|----------------|:-----------:|-----------------------------------|
| **Yasas** | `8007402` | Wrap (BYO), Yasas | FOR_SALE / FINAL | 9 | `Default`, `Dressing` |
| **Yasas** | `8011818` | Wrap (BYO), Yasas (C&C Pilot) | FOR_SALE / FINAL | 9 | `Default`, `Dressing` |
| **Royal Greens / Hanu Poke** | `8009943` | Caesar Salad, Bellies | FOR_SALE / FINAL | 2 | `Default`, `Lemon Caesar Dressing` |

---

## Task-Level Breakdown

### `8007402` Wrap (BYO), Yasas — 9 tasks (2 unmapped)

| Task | Mapped to customization? |
|------|--------------------------|
| Default | ❌ **unmapped** |
| Dressing | ❌ **unmapped** |
| Extra Green Goddess | ✅ mapped |
| Extra Harissa Dressing | ✅ mapped |
| Extra Lemon Vinaigrette | ✅ mapped |
| Extra Pomegranate Vinaigrette | ✅ mapped |
| Extra Roasted Garlic Red Wine Vinaigrette | ✅ mapped |
| Extra Tahini Yogurt | ✅ mapped |
| Extra Zhug | ✅ mapped |

### `8011818` Wrap (BYO), Yasas (C&C Pilot) — 9 tasks (2 unmapped)

Identical task structure to `8007402`: unmapped = `Default`, `Dressing`; the other 7 are "Extra …" sauce tasks each mapped to a customization option value.

### `8009943` Caesar Salad, Bellies — 2 tasks (both unmapped)

| Task | Mapped to customization? |
|------|--------------------------|
| Default | ❌ **unmapped** |
| Lemon Caesar Dressing | ❌ **unmapped** |

> ⚠️ **Name note**: this item is named "Bellies" (partner-brand recipe) but is sold under the **`BOWLDER- RG + Poke + Partner Salads Launch Menu`** (concepts = Royal Greens + Hanu Poke only, ACTIVE). By menu membership it belongs to RG / Hanu Poke; recipe origin is the partner brand Bellies. Include/exclude is a business judgment call.

---

## Convergence Funnel

| Step | Count |
|------|-------|
| Clean-menu items attributed to the 4 brands | 364 |
| + in scope: `sold_status IN ('FOR_SALE','SCHEDULED')`, non-expired, non-dormant, non-preset, has line build | 66 |
| + line build has multiple tasks (≥2) | 17 |
| + ≥2 tasks with no mapped customization option | **3** ✅ |

The remaining 14 multi-task items each have exactly **1** unmapped task — almost always the base `Default` task — so they fail the ≥2 threshold.

---

## Methodology

| Filter / Rule | Value |
|---------------|-------|
| `object_type` | `MENU` |
| `sold_status` | `IN ('FOR_SALE','SCHEDULED')` |
| `version_status` / `effective` | not constrained (relaxed so SCHEDULED versions can qualify; here 0 SCHEDULED exist) |
| Non-expired | `service_end_time > CURRENT_DATETIME()` |
| `item_status` | `!= 'DORMANT'` |
| `deleted` | `false` |
| `preset_item_version_info` | `IS NULL` (presets excluded) |
| Has line build | `item_line_build IS NOT NULL` |
| "Multiple tasks" | task count per line build ≥ 2 |
| "≥2 unmapped" | ≥2 tasks where `task.customization_option IS NULL` |

### "1个以上" interpreted as **≥2**

Every multi-task item has at least the base `Default` task unmapped, so a "≥1 unmapped" filter is trivially satisfied by all 17 multi-task items. The meaningful (and confirmed) threshold is **≥2 unmapped tasks**.

### Unmapped-task detection

In the `item_line_build` JSON, each task carries an optional `customization_option` object (`{option_id, option_value_id}`). A task is **unmapped** (a base/always-run task) when this field is null:

```
JSON_EXTRACT(task, '$.customization_option') IS NULL
   OR TO_JSON_STRING(JSON_EXTRACT(task, '$.customization_option')) = 'null'
```

### Data sources

| Data | Source | Note |
|------|--------|------|
| Line build (tasks + customization mapping) | `secure-recipe-prod.recipe_v2.item_versions.item_line_build` | **Only** table with this field; `wonder-recipe-prod.item_versions` lacks it |
| Menus / concepts | `wonder-recipe-prod.recipe_v2.menus` / `concepts` | `concept_ids` & `items` are JSON strings |

### Brand membership — "clean menu" method

To avoid cross-contamination from shared multi-brand menus (e.g. "Pitco Items" = 6 concepts, "Beverages" = 33 concepts), an item is attributed to a brand only via **clean menus** — menus whose *every* `concept_id` is one of the 4 targets. Items appearing **only** in shared multi-brand menus are not captured (a known scope limitation).

| Brand | Concept ID |
|-------|-----------|
| Hanu Poke | `3c628085-cf0a-4dc7-a510-daa9f51ac9ac` |
| Limesalt | `df4c141a-857f-46d0-a9c6-9c3f84f618a0` |
| Royal Greens | `bdd54588-04c5-42cb-a154-324646bf0f43` |
| Yasas | `4cc6a37a-05bf-40ca-8aa6-cd043d33a5d8` |

---

## Caveats

1. **"1个以上" = ≥2 unmapped tasks** (confirmed). The ≥1 reading returns all 17 multi-task items and is not meaningful.
2. **`8009943 Caesar Salad, Bellies`** — partner-brand recipe sold under the RG + Hanu Poke Bowlder menu; brand attribution is by menu membership.
3. **SCHEDULED** — 0 of these brands' line-build items are `sold_status = 'SCHEDULED'`, so "or scheduled" adds nothing here (but was applied).
4. **Clean-menu scoping** — items present only in shared multi-brand menus are excluded to prevent mis-attribution.

---

## Query Reference

```sql
WITH target_concepts AS (
  SELECT * FROM UNNEST([
    STRUCT('3c628085-cf0a-4dc7-a510-daa9f51ac9ac' AS cid, 'Hanu Poke' AS bname),
    STRUCT('df4c141a-857f-46d0-a9c6-9c3f84f618a0', 'Limesalt'),
    STRUCT('bdd54588-04c5-42cb-a154-324646bf0f43', 'Royal Greens'),
    STRUCT('4cc6a37a-05bf-40ca-8aa6-cd043d33a5d8', 'Yasas')])
),
menu_parsed AS (
  SELECT m._id AS menu_id,
    ARRAY(SELECT JSON_VALUE(x) FROM UNNEST(JSON_EXTRACT_ARRAY(m.concept_ids)) x) AS concepts,
    m.items
  FROM `wonder-recipe-prod.recipe_v2.menus` m
),
clean_menus AS (   -- menus whose EVERY concept is one of the 4 targets (no contamination)
  SELECT * FROM menu_parsed
  WHERE ARRAY_LENGTH(concepts) >= 1
    AND NOT EXISTS (SELECT 1 FROM UNNEST(concepts) cc
                    WHERE cc NOT IN (SELECT cid FROM target_concepts))
),
brand_items AS (
  SELECT item_number, STRING_AGG(DISTINCT bname, ' / ' ORDER BY bname) AS brands
  FROM (
    SELECT DISTINCT JSON_VALUE(item, '$.item_number') AS item_number, tc.bname
    FROM clean_menus cm, UNNEST(JSON_EXTRACT_ARRAY(cm.items)) AS item
    JOIN UNNEST(cm.concepts) cn ON TRUE
    JOIN target_concepts tc ON tc.cid = cn
  ) GROUP BY item_number
),
iv AS (
  SELECT iv.item_number, iv.name, iv.item_line_build, iv.version_id, iv.sold_status, iv.version_status
  FROM `secure-recipe-prod.recipe_v2.item_versions` iv
  WHERE iv.object_type = 'MENU' AND iv.item_line_build IS NOT NULL
    AND iv.deleted = false AND iv.item_status != 'DORMANT'
    AND iv.sold_status IN ('FOR_SALE','SCHEDULED')
    AND iv.preset_item_version_info IS NULL
    AND iv.service_end_time > CURRENT_DATETIME()
    AND iv.item_number IN (SELECT item_number FROM brand_items)
),
lb AS (
  SELECT iv.item_number, iv.name, iv.version_id, iv.sold_status, iv.version_status, l, lb_idx
  FROM iv, UNNEST(JSON_EXTRACT_ARRAY(iv.item_line_build, '$.line_builds')) l WITH OFFSET lb_idx
),
lb_task_detail AS (
  SELECT lb.item_number, lb.name, lb.version_id, lb.sold_status, lb.version_status, lb.lb_idx,
    JSON_VALUE(tt, '$.name') AS task_name,
    (JSON_EXTRACT(tt, '$.customization_option') IS NULL
       OR TO_JSON_STRING(JSON_EXTRACT(tt, '$.customization_option')) = 'null') AS is_unmapped
  FROM lb, UNNEST(JSON_EXTRACT_ARRAY(lb.l, '$.tasks')) tt
),
lb_summary AS (
  SELECT item_number, name, version_id, sold_status, version_status, lb_idx,
    COUNT(*) AS task_count,
    COUNTIF(is_unmapped) AS unmapped_task_count,
    ARRAY_AGG(IF(is_unmapped, task_name, NULL) IGNORE NULLS ORDER BY task_name) AS unmapped_tasks
  FROM lb_task_detail
  GROUP BY item_number, name, version_id, sold_status, version_status, lb_idx
),
ranked AS (   -- pick, per item, the line build with the most unmapped tasks
  SELECT *, ROW_NUMBER() OVER (PARTITION BY item_number
                               ORDER BY unmapped_task_count DESC, task_count DESC) AS rn
  FROM lb_summary
)
SELECT bi.brands, r.item_number, r.name, r.sold_status, r.version_status,
  r.task_count, r.unmapped_task_count,
  ARRAY_TO_STRING(r.unmapped_tasks, ' | ') AS unmapped_task_names
FROM ranked r
JOIN brand_items bi ON bi.item_number = r.item_number
WHERE r.rn = 1 AND r.unmapped_task_count >= 2   -- multiple tasks AND >1 (≥2) unmapped
ORDER BY r.unmapped_task_count DESC, r.task_count DESC, bi.brands, r.item_number;
```

---

## Related

- [[A2-Data Research/byo-zero-bom-analysis-2026-07-02.md]] — same 4 brands, BYO zero-required-BOM analysis
- [[A2-Data Research/Wonder Create - Customization Option Values Mapping Multiple Food Components.md]] — same 4 brands, customization option-value mapping
- [[A2-Data Research/Wonder Create Component - Cookbook Line Build Report (Global Config Appliances).md]] — line build (appliance config) analysis
