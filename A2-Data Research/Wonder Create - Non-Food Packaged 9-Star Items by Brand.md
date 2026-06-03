---
title: Wonder Create - Non-Food Packaged 9-Star Items by Brand
date: 2026-06-03
updated: 2026-06-03
project: Wonder Create
tags: [cookbook, non-food, packaging, data-research]
source: BigQuery (master_data + wonder-recipe-prod)
---

# Wonder Create - Non-Food Packaged 9-Star Items by Brand

## 查询背景

Wonder Create 新建 item 时需要知道各 brand 下已有的 non-food packaged item（9\* 开头），以便复用现有包装物料而非重复创建。本次调查覆盖 **6 个 brand**（Hanu Poke、Bellies、Limesalt、El Diez、Yasas、Royal Greens）下所有 FOR_SALE menu item 中用到的 9\* component 和 customization option value。

**HSide Concept** 未在 Cookbook 系统中找到（已搜索 concepts 和 menus 表的各种拼写变体）。

## 数据范围

| 维度 | 说明 |
|------|------|
| **数据源** | `wonder-dw-prod-brd.master_data.item_versions`（`bom_header` JSON → BOM components）+ `wonder-recipe-prod.recipe_v2.item_customizations_flattened`（customization option values） |
| **Brand 筛选** | 通过 concept → brand-specific menu（concept_count=1）→ menu items 链路，避免 commissary multi-concept menu 的跨品牌污染 |
| **Menu Item 筛选** | `sold_status = 'FOR_SALE'`, `object_type IN ('MENU', 'RECIPE')`, `deleted = false` |
| **9\* 来源** | (1) `bom_header.bom_lines[].item_number`（完整 BOM 级 component）; (2) `item_customizations_flattened.option_values[].items[].item_number`（customization option value） |
| **sub_type 覆盖** | 不限制 sub_type，GUEST_PACKAGING 和 INTERNAL_PACKAGING 均纳入 |
| **排除** | label / tamper evident 贴纸标签类; Sleeve / Wrap Sleeve 纸套类 |

> **v6 更新**: 新增 **Royal Greens**（Royal Greens Super Salad Station [ACTIVE] 01.06.2025，140 items），6 brand 完整覆盖。

> **v5 更新**: 发现 `wonder-dw-prod-brd.master_data.item_versions` 的 `bom_header` JSON 列包含完整 BOM（含 packaging components），弥补了 `wonder-recipe-prod` 中 `guest_packaging_items` 覆盖率极低的问题。

## ⚠️ 方法修正记录

**初版查询存在严重 bug**：通过 concept → menus（LIKE '%concept_id%'）→ menu items 的链路，会将 commissary 大菜单中**所有品牌的 item 都算给目标 brand**。

**修正方案**：只使用 **concept_count = 1 的 brand 专属 menu**：

| Brand | Menu Name | Menu ID | Status |
|-------|-----------|---------|--------|
| Hanu Poke | Hanu Poke [ACTIVE] 1.10.2025 | ae48489e-1a67-477a-bedf-1b17d9a79ed5 | ACTIVE |
| Bellies | Bellies [Active Menu] 7.18.24 | 707d1f80-8157-456d-9013-d5dca1c97d18 | ACTIVE |
| Limesalt | Limesalt [ACTIVE] 2.19.2024 | 7c4d18c3-3d61-4016-97fb-a23c15f3b258 | ACTIVE |
| Yasas | Yasas [ACTIVE] 2.19.2024 | 94ec50e9-2bb1-43e3-bb77-95a46c603103 | ACTIVE |
| El Diez | El Diez Mexican Bowls | ca5cf454-adba-4709-8c19-8b70cc24f495 | R&D |
| Royal Greens | Royal Greens Super Salad Station [ACTIVE] 01.06.2025 | 47999e6b-6aa7-430e-8b72-707cb1ba081e | ACTIVE |

## 各 Brand FOR_SALE Menu Item 数量

| Brand | FOR_SALE Items | 数据来源 |
|-------|---------------|---------|
| Hanu Poke | 13 | BOM + Customization |
| Bellies | 14 | BOM + Customization |
| Limesalt | 31 | BOM + Customization |
| Yasas | 22 | BOM + Customization |
| El Diez | 8 | BOM + Customization |
| **Royal Greens** | **47** | BOM + Customization |

---

# 9\* Non-Food Packaging Item 分类汇总

> 数据来源：BOM（`master_data.item_versions.bom_header.bom_lines`）+ Customization（`item_customizations_flattened`）。已排除 label 和 sleeve 类。

---

## 一、Container + Lid 配对

### 1.1 盒子 / 碗 + 盖子

| #   | 容器                                                               | 盖子                                                                        | 使用 Brand（Menu Items）                                      |
| --- | ---------------------------------------------------------------- | ------------------------------------------------------------------------- | --------------------------------------------------------- |
| 1   | **9000033** Container, 8.5x6.25", 28oz, Natural, Rectangle, Pulp | **9000034** Lid, Container, 8.5x6.25", 28oz, Clear, Rectangle, PP Plastic | Limesalt (10), El Diez (1)                                |
| 2   | **9002087** Bowl, White, Round, Paper, 16oz                      | **9002088** Lid, Clear, PP, 16oz White Round Bowl                         | Hanu Poke (2)                                             |
| 3   | **9002624** Bowl, 16oz, Bellies                                  | **9002626** Lid, 16 Oz, Bowl, Bellies                                     | Bellies (5)                                               |
| 4   | **9000061** Bowl, 32oz, Natural, Round, Pulp                     | **9001727** Lid, 32 & 48oz Pulp Bowl, PET, Dome                           | Limesalt (1), Yasas (7), Royal Greens (34, CUSTOMIZATION) |
| 5   | **9000726** Bowl, 8oz, Clear, Round, PET Plastic                 | **9000305** Lid, Bowl, 5.5", 8/12/16oz, Clear, Round, Flat, Plastic       | Hanu Poke (1)                                             |
| 6   | **9001638** Pulp Plus 36 oz Rectangle Container PFAs Free        | **9001639** Flat Pulp Lid for Pulp Plus Container                         | Limesalt (2)                                              |
| 7   | **9003663** CONT RECT 36 OZ PULP PLUS                            | **9003662** LID FLAT CLR F/ PULP RECT CONTAINER FOR 30/36oz               | Limesalt (2)                                              |
| 8   | **9000041** Bowl, 48oz, Natural, Round, Pulp                     | **9001727** Lid, 32 & 48oz Pulp Bowl, PET, Dome                           | **Royal Greens (47)**                                     |

> **注意**: 9000061 (32oz) 和 9000041 (48oz) 共用同一个盖子 9001727（Lid, 32 & 48oz Pulp Bowl, PET, Dome）。Royal Greens 的 BOM 主容器为 48oz（9000041+9001727），但 32oz 碗（9000061）也在 customization 中作为备选 bowl size 出现。

### 1.2 Souffle Cup + Lid

| # | 杯子 | 盖子 | 使用 Brand（Menu Items） |
|---|------|------|------------------------|
| 9 | **9002138** Souffle Cup, 2oz, PP | **9002139** Lid, 2oz Souffle Cup, PET | Hanu Poke (9), Bellies (2), Limesalt (4), El Diez (1), Yasas (15), **Royal Greens (46)** |
| 10 | **9002140** Souffle Cup, 4oz, PP | **9002141** Lid, 4oz Souffle Cup, PET | Limesalt (10), El Diez (6), Yasas (6), **Royal Greens (1)** |

---

## 二、自带盖子的组合容器 (Container & Lid as one item)

| # | Item Number | Name | 使用 Brand（Menu Items） |
|---|------------|------|------------------------|
| 1 | **9001868** | Bowl and Lid, Kraft, Round, Paper, 40oz | Hanu Poke (9) |
| 2 | **9000664** | Container & Lid, 4.5", 16oz, Deli, Black, Round, PP Plastic | Hanu Poke (1), Limesalt (1) |
| 3 | **9000831** | Cup & Lid, 8oz, Soup, Kraft | Limesalt (4) |
| 4 | **9002623** | Clamshell, Bellies | Bellies (5) |
| 5 | **9000624** | Box, 5.7x5x3.25", Clamshell, Brown, Kraft | Limesalt (1), Yasas (1) |
| 6 | **9000270** | Tray & Lid, 7", 24oz, Black-Gold, Round, Aluminum-Plastic | Yasas (1) |

> Royal Greens 未使用自带盖子的组合容器。

---

## 三、袋子类 (Bags)

| #   | Item Number | Name                                       | 使用 Brand（Menu Items）  |
| --- | ----------- | ------------------------------------------ | --------------------- |
| 1   | **9001961** | Bag, White, Paper, 1#, Window              | Limesalt (8)          |
| 2   | **9001889** | Bag, Yasas, Greasepaper, 6x7               | Yasas (8)             |
| 3   | **9000727** | Bag, 6.75 x 6.5", Sandwich, Natural, Kraft | Limesalt (1)          |
| 4   | **9001888** | Bag, Royal Greens, Greasepaper, 6x7        | **Royal Greens (42)** |

---

## 四、其他包装物 (纸、锡纸、勺子、标记牌、独立碗等)

| #   | Item Number | Name                                      | 使用 Brand（Menu Items）   |
| --- | ----------- | ----------------------------------------- | ---------------------- |
| 1   | **9000260** | Sheet, 14x16", Foil, Insulated, Honeycomb | Bellies (2), Yasas (5) |
| 2   | **9001506** | 18x18 Foil Paper                          | Limesalt (2)           |

> Royal Greens 未使用此分类中的包装物。

### 9000260 深度分析：Foil Sheet 的真实使用场景

9000260（Sheet, 14x16", Foil, Insulated, Honeycomb）是一种保温隔热箔纸，出现在 2 个 brand 共 7 个 FOR_SALE menu item 中。它**不单独承担主容器角色**，而是作为手持食品的包裹层。

#### 使用的 Menu Items

| Brand | Item # | Name | Type |
|-------|--------|------|------|
| Bellies | 8009954 | Cheese Burger, Bellies | MENU |
| Bellies | 8010061 | Burger, Bellies | MENU |
| Yasas | 8007402 | Wrap (BYO), Yasas | MENU |
| Yasas | 8011648 | Harissa Chicken Crunch Sandwich | MENU |
| Yasas | 8011649 | Grilled Chicken & Avocado Sandwich | MENU |
| Yasas | 8011650 | Grilled Steak & Feta Sandwich | MENU |
| Yasas | 8011651 | Za'atar Carrots & Broccoli Pita | MENU |

**规律**：全是手持类 item（burger / sandwich / wrap / pita），无一例外。

#### 与 9000260 配套使用的其他 9\* Container

| Brand | 配套 9\* Container | 特点 | 来源 |
|-------|-------------------|------|------|
| **Bellies** | **9002623** Clamshell, Bellies | 品牌定制翻盖盒（自带盖子），分类二 | BOM |
| **Yasas** | **9002138+9002139** Souffle Cup 2oz + Lid | 酱料杯（分类 1.2），注意：**无 rigid container** | CUSTOMIZATION |

> **关键差异**：Bellies 用 Clamshell 作为主容器 + Foil 包裹保温；Yasas 的 sandwich/wrap/pita **仅靠 Foil Sheet 包裹**，没有任何碗/盒/翻盖类 outer container，仅附加 2oz Souffle Cup 用于配酱。

两个品牌均额外使用了 label（已排除）：Bellies 使用 9002320 Gluten Free Substitution Label，Yasas 使用 9001846 Tamper Evident Label。

> **Wonder Create 启示**：如果新 brand 要做 wrap/sandwich 类手持 item，9000260 是已验证的 foil wrap 方案。但需注意 Yasas 模式（纯 foil wrap + sauce cup）vs Bellies 模式（clamshell + foil wrap）对 outer container 的不同需求。

---

## 已排除项目

### Label / Tamper Evident 类

| Item # | Name | 出现 Brand | Menu Items |
|--------|------|-----------|------------|
| 9001478 | Label, Limesalt, Chicken, 1.5 Round | Limesalt (17), El Diez (1) | 18 |
| 9001479 | Label, Limesalt, Steak, 1.5 Round | Limesalt (17), El Diez (1) | 18 |
| 9001481 | Label, Limesalt, Spiced Tofu, 1.5 Round | Limesalt | 17 |
| 9001482 | Label, Limesalt, Barbacoa, 1.5 Round | Limesalt | 17 |
| 9001483 | Label, Limesalt, Carnitas, 1.5 Round | Limesalt (17), El Diez (1) | 18 |
| 9001484 | Label, Limesalt, Cheese, 1.5 Round | Limesalt | 2 |
| 9001485 | Label, Limesalt, Veggie, 1.5 Round | Limesalt | 16 |
| 9001637 | Label, DiFara, Tamper Evident, 1x3 | **Royal Greens** | **1** |
| 9001748 | Label, Limesalt, Tamper Evident, 1x3 | Limesalt | 2 |
| 9001846 | Label, Yasas, Tamper Evident, 1x3 | Yasas | 5 |
| 9002320 | Label, Gluten Free Substitution, 1.5" Round | Bellies | 2 |

### Sleeve / Wrap Sleeve 类

| Item # | Name | 出现 Brand | Menu Items |
|--------|------|-----------|------------|
| 9003667 | Mainstay Wrap Sleeves 13 7/8" | **Royal Greens** | **1** |
| 9003669 | Royal Greens Wrap Sleeves 13 7/8" | **Royal Greens** | **42** |
| 9003671 | Limesalt Wrap Sleeves 13 7/8" | Limesalt | 17 |
| 9003674 | Hanu Poke Wrap Sleeves 13 7/8" | Hanu Poke | 13 |
| 9003677 | Bobby Flay Wrap Sleeves 13 7/8" | **Royal Greens** | **3** |
| 9003681 | Yasas Wrap Sleeves 13 7/8" | Yasas | 7 |
| 9003688 | El Diez Wrap Sleeves 13 7/8" | El Diez | 1 |

---

## Brand × Packaging Type 交叉汇总

| Brand | Box/Bowl + Lid | Souffle Cup 2oz | Souffle Cup 4oz | 自带盖子 | 袋子 | 其他 | 合计（unique items） |
|-------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Hanu Poke | 9002087+88, 9000726+0305 | 9002138+39 | — | 9001868, 9000664 | — | — | 8 |
| Bellies | 9002624+26 | 9002138+39 | — | 9002623 | — | 9000260 | 6 |
| Limesalt | 9000033+34, 9000061+1727, 9001638+39, 9003663+62 | 9002138+39 | 9002140+41 | 9000664, 9000831, 9000624 | 9001961, 9000727 | 9001506 | 17 |
| Yasas | 9000061+1727 | 9002138+39 | 9002140+41 | 9000270, 9000624 | 9001889 | 9000260 | 10 |
| El Diez | 9000033+34 | 9002138+39 | 9002140+41 | — | — | — | 6 |
| **Royal Greens** | **9000041+1727**, 9000061+1727 (cust) | **9002138+39** | 9002140+41 | — | **9001888** | — | **9** |

---

## 关键发现

### 1. 2oz Souffle Cup 是唯一真正的全品牌通用包装（6/6 brand）

**9002138 + 9002139** (Souffle Cup, 2oz, PP + Lid) 出现在**全部 6 个 brand**（Hanu Poke 9、Bellies 2、Limesalt 4、El Diez 1、Yasas 15、Royal Greens 46），用于 sauce / modifier cup。作为 Wonder Create 通用 modifier cup 包装的首选，**是所有品牌之间唯一没有例外的通用组件**。

### 2. 4oz Souffle Cup 覆盖 4/6 brand

**9002140 + 9002141** (Souffle Cup, 4oz) 在 4 个 brand 使用（Limesalt 10、El Diez 6、Yasas 6、Royal Greens 1），Hanu Poke 和 Bellies 未使用。

### 3. 9001727 Dome Lid 是 3 个 brand 的共享盖子（跨 32oz/48oz 两种碗）

**9001727** Lid, 32 & 48oz Pulp Bowl, PET, Dome 同时覆盖 32oz 碗（9000061）和 48oz 碗（9000041），在 **Limesalt、Yasas、Royal Greens** 三个品牌使用。Royal Greens 以 48oz 碗（9000041）为主、customization 备选 32oz（9000061）。

### 4. Royal Greens 是最大的 packaging 消费品牌

| 指标 | Royal Greens | 其他 5 brand 合计 |
|------|:---:|:---:|
| FOR_SALE Items | 47 | 88 |
| 使用 48oz Bowl 的 items | 47 | 0 |
| 使用 2oz Souffle Cup 的 items | 46 | 31 |
| 使用 Greasepaper Bag 的 items | 42 | — |
| 主力容器 | 9000041+9001727 (48oz 碗) | 品牌定制居多 |

Royal Greens 的 packaging 策略以 **48oz 圆形 pulp 碗 + dome 盖 + 2oz souffle cup + greasepaper 袋** 四件套为核心，覆盖其 47 个 FOR_SALE salad item。

### 5. 各品牌主包装差异大，几乎全是品牌定制

| Brand | 主容器 | 特点 |
|-------|--------|------|
| Hanu Poke | 9001868 Bowl+Lid 40oz Kraft (9 items) | 品牌主容器是 40oz 纸碗，自带盖子 |
| Bellies | 9002623 Clamshell (5 items) + 9002624 Bowl 16oz (5 items) | 全部 Bellies 品牌定制 |
| Limesalt | 9000033+9000034 Container 28oz 矩形 Pulp (10 items) | 矩形 pulp 容器为主，包装种类最多 |
| Yasas | 9000061 Bowl 32oz Pulp + 9001727 Dome Lid (7 items) | 32oz 圆形 pulp 碗 + dome 盖 |
| El Diez | 9000033+9000034 (1 item，R&D) | 与 Limesalt 共用 28oz 矩形容器 |
| **Royal Greens** | **9000041 Bowl 48oz Pulp + 9001727 Dome Lid (47 items)** | **48oz 圆形 pulp 碗，容量最大；搭配 greasepaper 袋** |

### 6. 可用于 Wonder Create 的通用包装推荐

| 优先级 | 包装 | 理由 |
|--------|------|------|
| **高** | 9002138+9002139 Souffle Cup 2oz | **唯一 6/6 brand 通用**，用于酱料/ modifier 杯 |
| **高** | 9002140+9002141 Souffle Cup 4oz | 4/6 brand 通用，用于较大份配菜 |
| **中** | 9001727 Lid 32&48oz Dome | 3/6 brand 共享盖子，跨 32oz/48oz 两种碗 |
| **中** | 9000041 Bowl 48oz + 9001727 | Royal Greens 专用但用量极大（47 items），salad 类 brand 参考 |
| **中** | 9000061 Bowl 32oz + 9001727 | 3/6 brand 使用，圆形 pulp 碗通用性较好 |
| **中** | 9000033+9000034 Container 28oz 矩形 Pulp | Limesalt + El Diez 共用，矩形 pulp 容器较通用 |
| **低** | 品牌定制容器（9001868、9002623/4/6、9000624 等） | 仅单个品牌使用，不适合跨品牌复用 |

### 7. 数据完整性验证

通过与 `master_data.item_versions.bom_header.bom_lines`（BOM JSON）对比验证，`wonder-recipe-prod` 中的 `guest_packaging_items` 数据严重不完整：
- BOM JSON 包含大量 `guest_packaging_items` 中没有的 9\* item
- 例如 Bellies 在 `guest_packaging_items` 中为 0，但 BOM JSON 中包含 6 个 9\* item

---

## 修订历史

| 版本 | 日期 | 说明 |
|------|------|------|
| v1 (初版) | 2026-06-03 | 使用 concept → menus (LIKE) 链路，存在 commissary menu 跨品牌污染 bug |
| v2 (修正) | 2026-06-03 | 改用 concept_count=1 brand-specific menu；修正 9001467 归属 |
| v3 (验证) | 2026-06-03 | 修正 customization 查询 JSON 嵌套 unnest |
| v4 (重构) | 2026-06-03 | 按 packaging 类型分类重组 |
| v5 (BOM 完整版) | 2026-06-03 | 发现 `master_data.item_versions.bom_header` JSON 含完整 BOM；数据量从 9 个 unique item 暴增至 27 个；覆盖 5 brand |
| **v6 (6-Brand 最终版)** | 2026-06-03 | **新增 Royal Greens**（47 FOR_SALE items）；6 brand 完整覆盖；更新所有分类表和 key findings |

---

## 查询 SQL（v6 最终版 - 6 Brand）

```sql
-- COMPLETE: BOM (master_data.item_versions.bom_header) + Customization
-- 6 brands: Hanu Poke, Bellies, Limesalt, Yasas, El Diez, Royal Greens
WITH brand_menus AS (
  SELECT * FROM UNNEST([
    STRUCT("Hanu Poke" AS brand, "ae48489e-1a67-477a-bedf-1b17d9a79ed5" AS menu_id),
    STRUCT("Bellies" AS brand, "707d1f80-8157-456d-9013-d5dca1c97d18" AS menu_id),
    STRUCT("Limesalt" AS brand, "7c4d18c3-3d61-4016-97fb-a23c15f3b258" AS menu_id),
    STRUCT("Yasas" AS brand, "94ec50e9-2bb1-43e3-bb77-95a46c603103" AS menu_id),
    STRUCT("El Diez" AS brand, "ca5cf454-adba-4709-8c19-8b70cc24f495" AS menu_id),
    STRUCT("Royal Greens" AS brand, "47999e6b-6aa7-430e-8b72-707cb1ba081e" AS menu_id)
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
    JSON_VALUE(bom_line, "$.item_number") AS comp_item_number, "BOM" AS source
  FROM for_sale_items fsi
  JOIN `wonder-dw-prod-brd.master_data.item_versions` iv
    ON fsi.item_number = iv.item_number
    AND iv.effective = true AND iv.deleted = false AND iv.item_status != "DORMANT",
  UNNEST(JSON_EXTRACT_ARRAY(iv.bom_header, "$.bom_lines")) AS bom_line
  WHERE JSON_VALUE(bom_line, "$.item_number") IS NOT NULL
    AND STARTS_WITH(JSON_VALUE(bom_line, "$.item_number"), "9")
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
)
SELECT a.comp_item_number,
  ei.name AS comp_item_name,
  ei.object_sub_type AS comp_sub_type,
  a.brand,
  COUNT(DISTINCT a.menu_item_number) AS menu_item_count,
  STRING_AGG(DISTINCT a.source ORDER BY a.source) AS sources
FROM all_9x a
LEFT JOIN `wonder-recipe-prod.recipe_v2.effective_items` ei
  ON a.comp_item_number = CAST(ei.item_number AS STRING) AND ei.deleted = false
GROUP BY a.comp_item_number, ei.name, ei.object_sub_type, a.brand
ORDER BY a.comp_item_number, a.brand
```

## 相关链接

- [[Wonder Create - BOM Components Excluding All 80 Cookbook Items]]
- [[packaged-skus.md]] — Packaged SKUs 领域文档
- [[customization.md]] — Customization 领域文档
- [[item-master.md]] — Item Master（9\* = NON_FOOD 说明）
