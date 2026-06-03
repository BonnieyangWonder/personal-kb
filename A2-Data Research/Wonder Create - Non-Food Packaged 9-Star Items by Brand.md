---
title: Wonder Create - Non-Food Packaged 9-Star Items by Brand
date: 2026-06-03
updated: 2026-06-03
project: Wonder Create
tags: [cookbook, non-food, packaging, data-research]
source: BigQuery (wonder-recipe-prod)
---

# Wonder Create - Non-Food Packaged 9-Star Items by Brand

## 查询背景

Wonder Create 新建 item 时需要知道各 brand 下已有的 non-food packaged item（9\* 开头），以便复用现有包装物料而非重复创建。本次调查覆盖 **5 个 brand**（Hanu Poke、Bellies、Limesalt、El Diez、Yasas）下所有 FOR_SALE menu item 中用到的 9\* component 和 customization option value。

**HSide Concept** 未在 Cookbook 系统中找到（已搜索 concepts 和 menus 表的各种拼写变体）。

## 数据范围

| 维度 | 说明 |
|------|------|
| **数据源** | `wonder-recipe-prod.recipe_v2`（concepts、menus、effective_items、item_versions、item_customizations_flattened） |
| **Brand 筛选** | 通过 concept → brand-specific menu（concept_count=1）→ menu items 链路，避免 commissary multi-concept menu 的跨品牌污染 |
| **Menu Item 筛选** | `sold_status = 'FOR_SALE'`, `object_type IN ('MENU', 'RECIPE')`, `deleted = false` |
| **9\* 来源** | (1) `guest_packaging_items`（BOM 级别 component）; (2) `item_customizations_flattened.option_values[].items[].item_number`（customization option value） |
| **sub_type 覆盖** | 不限制 sub_type，GUEST_PACKAGING 和 INTERNAL_PACKAGING 均纳入 |
| **排除** | label 类 9\*（非打包盒/袋子的贴纸标签）; Sleeve / 纸套类 |

> **注意**: `secure-recipe-prod.recipe_v2` 无访问权限，无法直接查询 `bom_headers` / `bom_lines` / `bom_header` JSON。通过 `guest_packaging_items` 字段 + `item_customizations_flattened` 表覆盖了 BOM component 和 customization option 两个维度的 9\* 使用情况。

## ⚠️ 方法修正记录

**初版查询存在严重 bug**：通过 concept → menus（LIKE '%concept_id%'）→ menu items 的链路，会将 commissary 大菜单（如 "Pitco Items"、"DORA-3528" 等 30+ concept 的菜单）中**所有品牌的 item 都算给目标 brand**。

例如：9001467 (Oval Bowl WC) 被错误地标记为 "Hanu Poke 18 个 menu item 使用"，实际上它是 Yasas 专属的，在 Hanu Poke [ACTIVE] menu 中的使用量为 0。

**修正方案**：只使用 **concept_count = 1 的 brand 专属 menu**：

| Brand | Menu Name | Menu ID | Status | Concept Count |
|-------|-----------|---------|--------|---------------|
| Hanu Poke | Hanu Poke [ACTIVE] 1.10.2025 | ae48489e-1a67-477a-bedf-1b17d9a79ed5 | ACTIVE | 1 |
| Bellies | Bellies [Active Menu] 7.18.24 | 707d1f80-8157-456d-9013-d5dca1c97d18 | ACTIVE | 1 |
| Limesalt | Limesalt [ACTIVE] 2.19.2024 | 7c4d18c3-3d61-4016-97fb-a23c15f3b258 | ACTIVE | 1 |
| Yasas | Yasas [ACTIVE] 2.19.2024 | 94ec50e9-2bb1-43e3-bb77-95a46c603103 | ACTIVE | 1 |
| El Diez | El Diez Mexican Bowls | ca5cf454-adba-4709-8c19-8b70cc24f495 | R&D | 1 |

> **注意**: 存在 concept_count=2 的 menu（如 "BOWLDER- RG + Poke + Partner Salads Launch Menu"）包含 Hanu Poke concept，但其中的 item（如 "Kale and Romaine Caesar Salad, BF 3.0"）是 Bobby Flay 的 partner salad，并非 Hanu Poke item。此类 menu 已从 brand-specific 结果中排除。

## 各 Brand FOR_SALE Menu Item 数量

| Brand | Brand Menu | FOR_SALE Items | 有 guest_packaging_items | 有 customization 9\* |
|-------|-----------|---------------|-------------------------|---------------------|
| Hanu Poke | Hanu Poke [ACTIVE] | 13 | 0 | 9 |
| Bellies | Bellies [Active Menu] | 14 | 0 | 2 (label only) |
| Limesalt | Limesalt [ACTIVE] | 31 | 0 | 25 |
| Yasas | Yasas [ACTIVE] | 22 | 8 | 12 |
| El Diez | El Diez Mexican Bowls | 8 | 0 | 4 |

> El Diez 目前处于 R&D 状态，尚未上线。

---

# 9\* Non-Food Packaging Item 分类汇总

> 数据来源：BOM（`guest_packaging_items`）+ Customization（`item_customizations_flattened`）。已排除 label 类和 sleeve/纸套类。

---

## 一、Container + Lid 配对

### 1.1 盒子 / 碗 + 盖子

| # | 容器 | 盖子 | 使用 Brand | Menu Items |
|---|------|------|-----------|------------|
| 1 | **9001467** Bowl, Pulp Container, 32oz, Oval (WC) | **9001468** Lid, Pulp Container, 32oz, Oval, Pulp (WC) | Yasas（BOM） | 7 |

> 9001467/9001468 仅在 Yasas 的 `guest_packaging_items` 中出现。Hanu Poke、Bellies、Limesalt、El Diez 的 brand menu 均无 BOM 级 guest_packaging_items 数据，因此无法从 wonder-recipe-prod 确定其主包装容器。

### 1.2 Souffle Cup + Lid

| # | 杯子 | 盖子 | 使用 Brand | Menu Items |
|---|------|------|-----------|------------|
| 2 | **9002138** Souffle Cup, 2oz, PP | **9002139** Lid, 2oz Souffle Cup, PET | Hanu Poke（9）、Limesalt（4）、El Diez（1）、Yasas（12） | **26** |
| 3 | **9002140** Souffle Cup, 4oz, PP | **9002141** Lid, 4oz Souffle Cup, PET | Limesalt（4）、El Diez（1） | 5 |

> Souffle Cup 系列均来自 customization option value（`item_customizations_flattened`），作为 modifier cup 用于酱料/配菜。**2oz Souffle Cup 是唯一跨 4 个 brand 使用的通用包装。**

---

## 二、自带盖子的组合容器 (Container & Lid as one item)

| # | Item Number | Name | Sub Type | 使用 Brand | Menu Items |
|---|------------|------|----------|-----------|------------|
| 1 | **9000831** | Cup & Lid, 8oz, Soup, Kraft | GUEST_PACKAGING | Limesalt（CUSTOMIZATION） | 2 |

> 9000831 是杯+盖一体的 8oz 汤碗，仅在 Limesalt 的 customization option 中使用。

---

## 三、袋子类 (Bags)

| # | Item Number | Name | Sub Type | 使用 Brand | Menu Items |
|---|------------|------|----------|-----------|------------|
| 1 | **9001516** | 6x6.5 Greaseproof Paper Bag (PFAS FREE) | GUEST_PACKAGING | Yasas（BOM） | 1 |
| 2 | **9001889** | Bag, Yasas, Greasepaper, 6x7 | GUEST_PACKAGING | Yasas（CUSTOMIZATION） | 7 |

> 9001516 用于 Mini Pita, Yasas（8005299）；9001889 是 Yasas 品牌定制纸袋，出现在 customization 中，覆盖 7 个 menu item。

---

## 四、其他包装物 (纸、锡纸、勺子、标记牌、独立碗等)

> **在当前数据范围内，5 个 brand 的 FOR_SALE menu item 未发现此类 9\* item（已排除 label 和 sleeve）。**

---

## 已排除的 Label 类

> 以下 9\* item 经确认为贴纸标签（非打包盒/袋子），已在上述分类中排除。

| Item # | Name | 出现 Brand | Menu Items |
|--------|------|-----------|------------|
| 9001478 | Label, Limesalt, Chicken, 1.5 Round | Limesalt (17), El Diez (1) | 18 |
| 9001479 | Label, Limesalt, Steak, 1.5 Round | Limesalt (17), El Diez (1) | 18 |
| 9001481 | Label, Limesalt, Spiced Tofu, 1.5 Round | Limesalt | 17 |
| 9001482 | Label, Limesalt, Barbacoa, 1.5 Round | Limesalt | 17 |
| 9001483 | Label, Limesalt, Carnitas, 1.5 Round | Limesalt (17), El Diez (1) | 18 |
| 9001484 | Label, Limesalt, Cheese, 1.5 Round | Limesalt | 2 |
| 9001485 | Label, Limesalt, Veggie, 1.5 Round | Limesalt | 16 |
| 9002320 | Label, Gluten Free Substitution, 1.5" Round | Bellies | 2 |

---

## Brand × Packaging Type 交叉汇总

| Brand | Box/Bowl + Lid | Souffle Cup 2oz | Souffle Cup 4oz | Cup & Lid 一体 | 袋子 | 合计 |
|-------|:---:|:---:|:---:|:---:|:---:|:---:|
| Hanu Poke | — | 9002138+39 | — | — | — | 2 |
| Bellies | — | — | — | — | — | 0 |
| Limesalt | — | 9002138+39 | 9002140+41 | 9000831 | — | 5 |
| Yasas | 9001467+68 | 9002138+39 | — | — | 9001516, 9001889 | 6 |
| El Diez | — | 9002138+39 | 9002140+41 | — | — | 4 |
| **Unique Item 数** | 2 | 2 | 2 | 1 | 2 | **9** |

---

## 关键发现

### 1. 2oz Souffle Cup 是唯一的跨品牌通用包装

**9002138 + 9002139** (Souffle Cup, 2oz, PP + Lid) 是唯一出现在 4 个 brand（Hanu Poke、Limesalt、El Diez、Yasas）的 9\* non-food item。作为 Wonder Create 的通用 modifier cup 包装，这是最直接的复用选择。

### 2. Guest Packaging Item 覆盖率极低

只有 **Yasas** 的 8 个 FOR_SALE menu item 在 `guest_packaging_items` 中有数据。Hanu Poke、Bellies、Limesalt、El Diez 的 brand-specific menu 均无 guest_packaging_items。这意味着绝大多数品牌的主包装（container、lid、bag）不在 wonder-recipe-prod 的 `item_versions.guest_packaging_items` 中维护。

### 3. 9\* Item 主要来源是 Customization Option

除 Yasas 的 9001467/9001468/9001516 来自 BOM（guest_packaging_items）外，其余所有 9\* item 均来自 `item_customizations_flattened`。Souffle Cup 系列作为 modifier cup 出现在各品牌的 customization options 中。

### 4. 9001467 Oval Bowl (WC) 是 Yasas 专属

Oval Bowl 32oz WC 及盖子仅在 Yasas brand-specific menu 中使用（7 个 menu item），其他 4 个 brand 均未使用。

### 5. Bellies 无 Cookbook 层面的 Non-Food Packaging

Bellies 是 burger 类 brand，其 14 个 FOR_SALE item 在 Cookbook 中没有 guest_packaging_items，customization 中也无有效的非 label 9\* item。其包装物料可能通过 88\* packaged item 或其他系统管理。

### 6. El Diez 处于 R&D 阶段

El Diez 仅有一个 R&D status 的 menu（"El Diez Mexican Bowls"），8 个 FOR_SALE item，使用了 2 种 Souffle Cup + Limesalt label（customization 共享），无独立 packaging。

### 7. ⚠️ Cookbook 中的 Non-Food Packaging 数据严重不完整

**这是本次调查最重要的发现。** 大部分品牌的实际包装物料（container、lid、bag、sleeve、marker、foil 等）并未通过 `guest_packaging_items` 或 `item_customizations_flattened` 覆盖。这些数据可能在：

- `secure-recipe-prod.recipe_v2`（**无访问权限**，含 `bom_headers`/`bom_lines`/`bom_header` JSON）— 这是最可能包含完整 BOM 级 packaging 数据的来源
- 88\* packaged item 的内部 BOM（9\* 作为 88\* 的子 component）
- 独立于 Cookbook 的 packaging/供应链系统

**这意味着：本报告列出的 9 个 non-food item 只是 Cookbook 中显式记录的冰山一角，并非这些品牌实际使用的全部包装物料。**

---

## 修订历史

| 版本 | 日期 | 说明 |
|------|------|------|
| v1 (初版) | 2026-06-03 | 使用 concept → menus (LIKE) 链路，存在 commissary menu 跨品牌污染 bug |
| v2 (修正) | 2026-06-03 | 改用 concept_count=1 brand-specific menu；修正 9001467 归属 |
| v3 (验证) | 2026-06-03 | 修正 customization 查询（JSON_EXTRACT_ARRAY 嵌套 unnest）；修复 Limesalt 计数（6→5）；补充完整 label 列表和 menu item 使用量 |
| v4 (重构) | 2026-06-03 | 按 packaging 类型分类重组：Container+Lid 配对 / 一体组合容器 / 袋子 / 其他；增加 Brand×Packaging Type 交叉汇总表 |

---

## 查询 SQL（v4）

```sql
-- Comprehensive: BOM + Customization 9* items across 5 brands
-- Uses concept_count=1 brand-specific menus only
-- NO sub_type filter — includes GUEST_PACKAGING, INTERNAL_PACKAGING, etc.
WITH brand_menus AS (
  SELECT * FROM UNNEST([
    STRUCT("Hanu Poke" AS brand, "ae48489e-1a67-477a-bedf-1b17d9a79ed5" AS menu_id),
    STRUCT("Bellies" AS brand, "707d1f80-8157-456d-9013-d5dca1c97d18" AS menu_id),
    STRUCT("Limesalt" AS brand, "7c4d18c3-3d61-4016-97fb-a23c15f3b258" AS menu_id),
    STRUCT("Yasas" AS brand, "94ec50e9-2bb1-43e3-bb77-95a46c603103" AS menu_id),
    STRUCT("El Diez" AS brand, "ca5cf454-adba-4709-8c19-8b70cc24f495" AS menu_id)
  ])
),
brand_menu_items AS (
  SELECT DISTINCT bm.brand,
    CAST(JSON_VALUE(mi, "$.item_number") AS STRING) AS item_number
  FROM brand_menus bm
  JOIN `wonder-recipe-prod.recipe_v2.menus` m ON bm.menu_id = m._id,
  UNNEST(JSON_EXTRACT_ARRAY(m.items)) AS mi
),
for_sale_items AS (
  SELECT DISTINCT bmi.brand, bmi.item_number,
    ei.name AS item_name, ei.object_type
  FROM brand_menu_items bmi
  JOIN `wonder-recipe-prod.recipe_v2.effective_items` ei
    ON bmi.item_number = CAST(ei.item_number AS STRING) AND ei.deleted = false
  WHERE ei.sold_status = "FOR_SALE" AND ei.object_type IN ("MENU", "RECIPE")
),
bom_9x AS (
  SELECT DISTINCT fsi.brand, fsi.item_number AS menu_item_number,
    JSON_VALUE(gp, "$.item_number") AS comp_item_number, "BOM" AS source
  FROM for_sale_items fsi
  JOIN `wonder-recipe-prod.recipe_v2.item_versions` iv
    ON fsi.item_number = iv.item_number
    AND iv.effective = true AND iv.deleted = false AND iv.item_status != "DORMANT",
  UNNEST(JSON_EXTRACT_ARRAY(iv.guest_packaging_items)) AS gp
  WHERE JSON_VALUE(gp, "$.item_number") IS NOT NULL
    AND JSON_VALUE(gp, "$.item_number") != ""
    AND STARTS_WITH(JSON_VALUE(gp, "$.item_number"), "9")
),
cust_9x AS (
  SELECT DISTINCT fsi.brand, fsi.item_number AS menu_item_number,
    JSON_VALUE(item, "$.item_number") AS comp_item_number, "CUSTOMIZATION" AS source
  FROM for_sale_items fsi
  JOIN `wonder-recipe-prod.recipe_v2.item_customizations_flattened` icf
    ON fsi.item_number = icf.item_number,
  UNNEST(JSON_EXTRACT_ARRAY(icf.option_values)) AS ov,
  UNNEST(JSON_EXTRACT_ARRAY(ov, "$.items")) AS item
  WHERE JSON_VALUE(item, "$.item_number") IS NOT NULL
    AND STARTS_WITH(JSON_VALUE(item, "$.item_number"), "9")
),
all_9x AS (
  SELECT * FROM bom_9x UNION DISTINCT SELECT * FROM cust_9x
),
with_details AS (
  SELECT a.*, ei.name AS comp_name, ei.object_sub_type
  FROM all_9x a
  LEFT JOIN `wonder-recipe-prod.recipe_v2.effective_items` ei
    ON a.comp_item_number = CAST(ei.item_number AS STRING) AND ei.deleted = false
)
SELECT comp_item_number, MAX(comp_name) AS comp_name,
  MAX(object_sub_type) AS object_sub_type, brand,
  COUNT(DISTINCT menu_item_number) AS menu_item_count,
  STRING_AGG(DISTINCT source ORDER BY source) AS sources
FROM with_details
GROUP BY comp_item_number, brand
ORDER BY brand, comp_item_number
```

## 相关链接

- [[Wonder Create - BOM Components Excluding All 80 Cookbook Items]]
- [[packaged-skus.md]] — Packaged SKUs 领域文档
- [[customization.md]] — Customization 领域文档
- [[item-master.md]] — Item Master（9\* = NON_FOOD 说明）
