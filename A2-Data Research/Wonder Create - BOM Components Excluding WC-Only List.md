---
title: Wonder Create - BOM Components Excluding WC-Only List
date: 2026-05-21
updated: 2026-05-21
project: Wonder Create
tags: [cookbook, line-build, bom, global-appliance-config, data-research]
source: BigQuery (wonder-dw-prod-brd, wonder-recipe-prod)
---

# Wonder Create - BOM Components Excluding WC-Only List

## 查询背景

与 [[Wonder Create - Cookbook Line Build Report (Global Config Appliances)]] 使用相同的 menu item 范围（4 品牌、non-dormant、active final version、有 line build），以及相同的 appliance 过滤（TURBO_OVEN、FRYER、PIZZA_CONVEYOR_OVEN、CLAMSHELL），但 **component 匹配逻辑不同**：

- **报告 1**: 只找 line build 步骤中映射了 Confluence 页面 80 个 cookbook # 的组件
- **本报告**: 找出 line build COOK 步骤中映射的 **所有** component item，然后 **排除** Confluence 页面中 "Cookbook numbers in WC, not on the IK list" 表里的 26 个 item

### 排除的 WC-Only 列表

来自 [[WC Ingredient Validation vs Cookbook List 2026-05-08#Cookbook-numbers-in-WC,-not-on-the-IK-list]]:

```
4000243, 4000258, 4000259, 4000263, 4000265, 4000281, 4000285, 4000304,
4000387, 4000541, 4000544, 4000568, 4000658, 4000824, 4000826, 4000834,
4000837, 4000863, 4000864, 4000865, 4000867, 4000869, 4000872,
7000026, 7000029, 7000040
```

## 查询参数

| 参数 | 值 |
|------|-----|
| **Component 范围** | Line build 步骤中所有 mapped item（不限 cookbook 清单），排除 WC-only 26 个 |
| **品牌** | Royal Greens, Limesalt, Yasas, Hanu Poke |
| **Menu Item 筛选** | `object_type=MENU`, `effective=true`, `deleted=false`, `item_status!=DORMANT`, `version_status=FINAL` |
| **Activity** | `COOK` |
| **Appliances** | `TURBO_OVEN`, `FRYER`, `PIZZA_CONVEYOR_OVEN`, `CLAMSHELL` |
| **匹配方式** | 直接 (`step_related_item` / `proc_related_item`)、Customization Option 解析 |
| **数据源** | `wonder-dw-prod-brd.master_data.item_versions`, `wonder-recipe-prod.recipe_v2.effective_items`, `wonder-recipe-prod.mongo_batch_recipe_v2.global_appliance_settings` |

## 结果总览

| 指标 | 数值 |
|------|------|
| 匹配的 Component Items | **7 个**（排除 WC-only 后） |
| 匹配的 Menu Items | **36 个** |
| 总组合行数 | **100 行**（含版本/config/restaurant 不同组合） |
| 命中的 Appliance | TURBO_OVEN（83 行）、FRYER（17 行） |

## 按 Appliance 分析

### TURBO_OVEN — 83 行，4 个组件

| Component # | WC Name | 关联 Menu Items | 使用品牌 | 匹配方式 |
|-------------|---------|----------------|---------|---------|
| 4000330 | Mexican Three Cheese | 6 | Limesalt | CUSTOMIZATION |
| 4000380 | Roasted Cauliflower | 18 | Yasas | CUSTOMIZATION |
| 4000384 | Beef Souvlaki | 24 | Yasas | CUSTOMIZATION |
| 4000411 | Spiced Sweet Potatoes | 17 | Yasas | CUSTOMIZATION |

**Config**: 全部 `100/90 475°F` (UUID: `a2ce42da`)

### FRYER — 17 行，3 个组件

| Component # | WC Name | 关联 Menu Items | 使用品牌 | 匹配方式 |
|-------------|---------|----------------|---------|---------|
| 4000053 | Fries, French, Fridge Friendly, 5/16" (Buyout) HC | 3 | Limesalt, Yasas, Bellies | DIRECT |
| 4000709 | Chicken Tender | 1 | Bellies | DIRECT |
| 4000991 | Falafel | 2 | Yasas | DIRECT |

**Config**: `350°F`（大部分）、`325°F`（Falafel Side 特定 HDR）

---

## 与报告 1 的关键差异

### 被排除的 WC-Only 组件（在报告 1 中有但本报告排除）

| Component # | WC Name | 报告 1 行数 | 排除原因 |
|-------------|---------|------------|---------|
| 4000281 | Moruno Spiced Cauliflower | 6 | WC-only, not on IK list |
| 4000872 | Guacamole | 13 | WC-only, not on IK list |

### 新发现的组件（不在 80 个 cookbook 清单中）

| Component # | WC Name | 关联 Menu Items 数 | Appliance | 说明 |
|-------------|---------|-------------------|-----------|------|
| 4000380 | Roasted Cauliflower | 18 | TURBO_OVEN | Yasas 主要组件 |
| 4000384 | Beef Souvlaki | 24 | TURBO_OVEN | Yasas 主要蛋白质组件 |
| 4000411 | Spiced Sweet Potatoes | 17 | TURBO_OVEN | Yasas 主要组件 |
| 4000053 | Fries | 3 | FRYER | 跨品牌使用 |
| 4000709 | Chicken Tender | 1 | FRYER | Bellies 品牌 |
| 4000991 | Falafel | 2 | FRYER | Yasas 品牌 |

---

## Menu Items 列表

### Limesalt — TURBO_OVEN

| Menu # | Menu Name | Version | Component Items |
|--------|-----------|---------|-----------------|
| 8005007 | Quesadilla (BYO), Limesalt | 43 | 4000330 |
| 8010902 | Cheesesteak Quesadilla (BYO), Limesalt | 19 | 4000330 |
| 8010985 | Cheesesteak Quesadilla, Limesalt PRESET | 19 | 4000330 |
| 8011570 | Quesadilla (BYO), Limesalt (Jasmine Rice Pilot) | 1 | 4000330 |
| 8011576 | Cheesesteak Quesadilla (BYO), Limesalt (Jasmine Rice Pilot) | 1 | 4000330 |
| 8011610 | Cheesesteak Quesadilla, Jasmine Rice Pilot | 1 | 4000330 |

### Limesalt — FRYER

| Menu # | Menu Name | Component | Config |
|--------|-----------|-----------|--------|
| 8010867 | Mexican Fries, Limesalt | 4000053 (Fries) | 350°F |

### Yasas — TURBO_OVEN（主要用量）

| Menu # | Menu Name | Component Items |
|--------|-----------|-----------------|
| 8007402 | Sandwich (BYO), Yasas | 4000380, 4000384, 4000411 |
| 8007403 | Bowl (BYO), Yasas | 4000380, 4000384, 4000411 |
| 8010686 | Spicy Pepper & Feta Sandwich PRESET, Yasas BYO | 4000380, 4000384, 4000411 |
| 8010687 | Beef Souvlaki & Tzatziki Sandwich PRESET, Yasas BYO | 4000380, 4000384, 4000411 |
| 8010688 | Chicken Souvlaki & Avocado Sandwich PRESET, Yasas BYO | 4000380, 4000384, 4000411 |
| 8010689 | Spiced Sweet Potato & Kalamata Sandwich PRESET, Yasas BYO | 4000380, 4000384, 4000411 |
| 8010690 | Spicy Cauliflower & Avocado Sandwich PRESET, Yasas BYO | 4000380, 4000384, 4000411 |
| 8010716 | Beef Souvlaki & Kalamata Salad PRESET, Yasas BYO | 4000380, 4000384, 4000411 |
| 8010717 | Cauliflower & Chickpea Grain Bowl PRESET, Yasas BYO | 4000380, 4000384, 4000411 |
| 8010718 | Spiced Sweet Potato & Feta Salad PRESET, Yasas BYO | 4000380, 4000384, 4000411 |
| 8010719 | Spicy Cauliflower & Feta Salad PRESET, Yasas BYO | 4000380, 4000384, 4000411 |
| 8010720 | Zesty Chicken Souvlaki & Rice Bowl PRESET, Yasas BYO | 4000380, 4000384, 4000411 |
| 8010904 | Bowl (BYO), Yasas (Rice Pilot) | 4000384, 4000411 |
| 8010911 | Beef Souvlaki & Kalamata Salad PRESET, Yasas BYO (RICE PILOT) | 4000384, 4000411 |
| 8010912 | Cauliflower & Chickpea Grain Bowl PRESET, Yasas BYO (RICE PILOT) | 4000384, 4000411 |
| 8010913 | Spiced Sweet Potato & Feta Salad PRESET, Yasas BYO (RICE PILOT) | 4000384, 4000411 |
| 8010914 | Spicy Cauliflower & Feta Salad PRESET, Yasas BYO (RICE PILOT) | 4000384, 4000411 |
| 8010915 | Zesty Chicken Souvlaki & Rice Bowl PRESET, Yasas BYO (RICE PILOT) | 4000384, 4000411 |
| 8011566 | Bowl (BYO), Yasas (Jasmine Rice Pilot) | 4000380, 4000384 |
| 8011605 | Spiced Sweet Potato & Feta Salad, Jasmine Rice Pilot | 4000380, 4000384 |
| 8011606 | Spicy Cauliflower & Feta Salad, Jasmine Rice Pilot | 4000380, 4000384 |
| 8011607 | Cauliflower & Chickpea Grain Bowl, Jasmine Rice Pilot | 4000380, 4000384 |
| 8011608 | Zesty Chicken Souvlaki & Rice Bowl, Jasmine Rice Pilot | 4000380, 4000384 |
| 8011609 | Beef Souvlaki & Kalamata Salad, Jasmine Rice Pilot | 4000380, 4000384 |

### Yasas — FRYER

| Menu # | Menu Name | Component | Config |
|--------|-----------|-----------|--------|
| 8011417 | Mediterranean Fries, Yasas | 4000053 (Fries) | 350°F |
| 8011652 | Falafel Side, Yasas | 4000991 (Falafel) | 325°F / 350°F |
| 8011785 | Falafel Souvlaki, Yasas | 4000991 (Falafel) | 350°F |

### Bellies — FRYER

| Menu # | Menu Name | Component | Config |
|--------|-----------|-----------|--------|
| 8010062 | French Fries, Bellies | 4000053 (Fries) | 350°F |
| 8009955 | Chicken Tenders, Bellies | 4000709 (Chicken Tender) | 350°F |

> **注意**: "Bellies" 是 Royal Greens 和 Hanu Poke 共有的品牌名（部分 menu item 的 brand_names 为 "Hanu Poke, Limesalt, Royal Greens, Yasas"）

---

## 关键发现

### 1. TURBO_OVEN 组件集中在 Yasas

排除 WC-only 后，Yasas 的 TURBO_OVEN 组件数量最多（**Beef Souvlaki 24 个 menu item、Roasted Cauliflower 18、Spiced Sweet Potatoes 17**），远超 Limesalt（仅 Mexican Three Cheese 6 个）。

### 2. 新增 6 个组件不在原始 cookbook 清单中

这些组件在 80 个 cookbook 验证清单之外，但确实出现在 line build 的 COOK 步骤中。包括 FRYER 的 3 个直接映射组件。

### 3. FRYER 使用 DIRECT mapping（不同于 TURBO_OVEN 的 customization）

FRYER 子步骤直接引用 `step_related_item`。配置有 `350°F`（默认）和 `325°F`（Falafel Side 特定 HDR）。

### 4. 部分 Menu Item 有特定 HDR 限制

French Fries Bellies、Mexican Fries Limesalt、Chicken Tenders Bellies 等有多个不同 HDR 的 line build 变体，不只是 "All"。

### 5. Brand "Bellies" 跨品牌共享

"Bellies" 作为 brand_name 显示为 "Hanu Poke, Limesalt, Royal Greens, Yasas" — 说明 FRYER 的 Bellies 产品是 4 个品牌共享的。

---

## 查询 SQL

```sql
-- 完整查询见 .claude/tmp/all_components_excluding_wc_only.sql
-- 原始结果 JSON 见 .claude/tmp/all_components_excluding_wc_only_results.json
```

## 相关链接

- [[Wonder Create - Cookbook Line Build Report (Global Config Appliances)]] — 另一份报告（80 个 cookbook # 匹配）
- [[WC Ingredient Validation vs Cookbook List 2026-05-08#Cookbook-numbers-in-WC,-not-on-the-IK-list]] — 被排除的 WC-Only 列表
- [[line-build.md]] — Line Build 领域文档
- [[customization.md]] — Customization 领域文档
