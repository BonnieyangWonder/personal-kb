---
title: Wonder Create - BOM Components Excluding Cookbook List
date: 2026-05-21
updated: 2026-05-22
project: Wonder Create
tags: [cookbook, line-build, bom, global-appliance-config, data-research]
source: BigQuery (wonder-dw-prod-brd, wonder-recipe-prod)
---

# Wonder Create - BOM Components Excluding Cookbook List

## 查询背景

与 [[Wonder Create - Cookbook Line Build Report (Global Config Appliances)]] 使用相同的 menu item 范围（4 品牌、non-dormant、active final version、有 line build），以及相同的 appliance 过滤（TURBO_OVEN、FRYER、PIZZA_CONVEYOR_OVEN、CLAMSHELL），但 **component 匹配逻辑不同**：

- **报告 1**: 只找 line build 步骤中映射了 Confluence 页面全部 80 个 cookbook # 的组件
- **本报告**: 找出 line build COOK 步骤中映射的 **所有** component item，然后 **排除** Confluence 页面中全部的 80 个 cookbook # item

### 排除列表

排除 [[WC Ingredient Validation vs Cookbook List 2026-05-08]] 页面中列出的**全部 80 个 cookbook #**（涵盖页面中所有 5 张表），包括但不限于 "Cookbook numbers in WC, not on the IK list" 的 26 个。

## 查询参数

| 参数 | 值 |
|------|-----|
| **Component 范围** | Line build 步骤中所有 mapped item，排除 80 个 cookbook # |
| **品牌** | Royal Greens, Limesalt, Yasas, Hanu Poke |
| **Menu Item 筛选** | `object_type=MENU`, `effective=true`, `deleted=false`, `item_status!=DORMANT`, `version_status=FINAL` |
| **Activity** | `COOK` |
| **Appliances** | `TURBO_OVEN`, `FRYER`, `PIZZA_CONVEYOR_OVEN`, `CLAMSHELL` |
| **匹配方式** | 直接 (`step_related_item` / `proc_related_item`)、Customization Option 解析 |
| **数据源** | `wonder-dw-prod-brd.master_data.item_versions`, `wonder-recipe-prod.recipe_v2.effective_items`, `wonder-recipe-prod.mongo_batch_recipe_v2.global_appliance_settings` |

## 结果总览

| 指标 | 数值 |
|------|------|
| 匹配的 Component Items | **6 个**（排除 80 个 cookbook # 后） |
| 匹配的 Menu Items | **30 个** |
| 总组合行数 | **100 行**（含版本/config/restaurant 不同组合） |
| 命中的 Appliance | TURBO_OVEN（83 行）、FRYER（17 行） |

## 按 Appliance 分析

### TURBO_OVEN — 83 行，3 个组件

| Component # | WC Name | 关联 Menu Items | 使用品牌 | 匹配方式 |
|-------------|---------|----------------|---------|---------|
| 4000380 | Roasted Cauliflower | 18 | Yasas | CUSTOMIZATION |
| 4000384 | Beef Souvlaki | 24 | Yasas | CUSTOMIZATION |
| 4000411 | Spiced Sweet Potatoes | 23 | Yasas | CUSTOMIZATION |

**Config**: 全部 `100/90 475°F` (UUID: `a2ce42da`)

> **注意**: 排除全部 80 个 cookbook # 后，Limesalt 品牌的 TURBO_OVEN 组件（4000330 Mexican Three Cheese、4000636 Adobo Steak、4000550 Guacamole Spread、4000872 Guacamole、4000281 Moruno Spiced Cauliflower）均被排除。TURBO_OVEN 组件完全集中在 Yasas 品牌。

### FRYER — 17 行，3 个组件

| Component # | WC Name | 关联 Menu Items | 使用品牌 | 匹配方式 |
|-------------|---------|----------------|---------|---------|
| 4000053 | Fries, French, Fridge Friendly, 5/16" (Buyout) HC | 3 | Limesalt, Yasas, Bellies | DIRECT |
| 4000709 | Chicken Tender | 1 | Bellies | DIRECT |
| 4000991 | Falafel | 2 | Yasas | DIRECT |

**Config**: `350°F`（大部分）、`325°F`（Falafel Side 特定 HDR）

---

## Menu Items 列表

### Yasas — TURBO_OVEN（主要用量）

#### 标准系列 (v30/v40)

| Menu # | Menu Name | Version | Component Items |
|--------|-----------|---------|-----------------|
| 8007402 | Sandwich (BYO), Yasas | 30 | 4000380, 4000384, 4000411 |
| 8007403 | Bowl (BYO), Yasas | 40 | 4000380, 4000384, 4000411 |
| 8010686 | Spicy Pepper & Feta Sandwich PRESET, Yasas BYO | 30 | 4000380, 4000384, 4000411 |
| 8010687 | Beef Souvlaki & Tzatziki Sandwich PRESET, Yasas BYO | 30 | 4000380, 4000384, 4000411 |
| 8010688 | Chicken Souvlaki & Avocado Sandwich PRESET, Yasas BYO | 30 | 4000380, 4000384, 4000411 |
| 8010689 | Spiced Sweet Potato & Kalamata Sandwich PRESET, Yasas BYO | 30 | 4000380, 4000384, 4000411 |
| 8010690 | Spicy Cauliflower & Avocado Sandwich PRESET, Yasas BYO | 30 | 4000380, 4000384, 4000411 |
| 8010716 | Beef Souvlaki & Kalamata Salad PRESET, Yasas BYO | 40 | 4000380, 4000384, 4000411 |
| 8010717 | Cauliflower & Chickpea Grain Bowl PRESET, Yasas BYO | 40 | 4000380, 4000384, 4000411 |
| 8010718 | Spiced Sweet Potato & Feta Salad PRESET, Yasas BYO | 40 | 4000380, 4000384, 4000411 |
| 8010719 | Spicy Cauliflower & Feta Salad PRESET, Yasas BYO | 40 | 4000380, 4000384, 4000411 |
| 8010720 | Zesty Chicken Souvlaki & Rice Bowl PRESET, Yasas BYO | 40 | 4000380, 4000384, 4000411 |

#### Rice Pilot 系列 (v7)

| Menu # | Menu Name | Version | Component Items |
|--------|-----------|---------|-----------------|
| 8010904 | Bowl (BYO), Yasas (Rice Pilot) | 7 | 4000384, 4000411 |
| 8010911 | Beef Souvlaki & Kalamata Salad PRESET, Yasas BYO (RICE PILOT) | 7 | 4000384, 4000411 |
| 8010912 | Cauliflower & Chickpea Grain Bowl PRESET, Yasas BYO (RICE PILOT) | 7 | 4000384, 4000411 |
| 8010913 | Spiced Sweet Potato & Feta Salad PRESET, Yasas BYO (RICE PILOT) | 7 | 4000384, 4000411 |
| 8010914 | Spicy Cauliflower & Feta Salad PRESET, Yasas BYO (RICE PILOT) | 7 | 4000384, 4000411 |
| 8010915 | Zesty Chicken Souvlaki & Rice Bowl PRESET, Yasas BYO (RICE PILOT) | 7 | 4000384, 4000411 |

#### Jasmine Rice Pilot 系列 (v1)

| Menu # | Menu Name | Version | Component Items |
|--------|-----------|---------|-----------------|
| 8011566 | Bowl (BYO), Yasas (Jasmine Rice Pilot) | 1 | 4000380, 4000384, 4000411 |
| 8011605 | Spiced Sweet Potato & Feta Salad, Jasmine Rice Pilot | 1 | 4000380, 4000384 |
| 8011606 | Spicy Cauliflower & Feta Salad, Jasmine Rice Pilot | 1 | 4000380, 4000384 |
| 8011607 | Cauliflower & Chickpea Grain Bowl, Jasmine Rice Pilot | 1 | 4000380, 4000384 |
| 8011608 | Zesty Chicken Souvlaki & Rice Bowl, Jasmine Rice Pilot | 1 | 4000380, 4000384 |
| 8011609 | Beef Souvlaki & Kalamata Salad, Jasmine Rice Pilot | 1 | 4000380, 4000384 |

### FRYER — 各品牌

#### Bellies（跨品牌共享）

| Menu # | Menu Name | Component | Config |
|--------|-----------|-----------|--------|
| 8010062 | French Fries, Bellies | 4000053 (Fries) | 350°F |
| 8009955 | Chicken Tenders, Bellies | 4000709 (Chicken Tender) | 350°F |

> **注意**: "Bellies" 品牌名显示为 "Hanu Poke, Limesalt, Royal Greens, Yasas"，即 4 个品牌共享。

#### Limesalt

| Menu # | Menu Name | Component | Config |
|--------|-----------|-----------|--------|
| 8010867 | Mexican Fries, Limesalt | 4000053 (Fries) | 350°F |

#### Yasas

| Menu # | Menu Name | Component | Config |
|--------|-----------|-----------|--------|
| 8011417 | Mediterranean Fries, Yasas | 4000053 (Fries) | 350°F |
| 8011652 | Falafel Side, Yasas | 4000991 (Falafel) | 325°F / 350°F |
| 8011785 | Falafel Souvlaki, Yasas | 4000991 (Falafel) | 350°F |

---

## 与报告 1 的关键差异

### 被排除的 Cookbook 组件（在报告 1 中有但本报告排除）

报告 1 中的 5 个 cookbook 组件全部被排除：

| Component # | WC Name | 报告 1 行数 | 排除原因 |
|-------------|---------|------------|---------|
| 4000636 | Adobo Steak | 48 | 在 80 个 cookbook 清单中 |
| 4000550 | Guacamole Spread | 27 | 在 80 个 cookbook 清单中 |
| 4000872 | Guacamole | 13 | 在 80 个 cookbook 清单中 |
| 4000281 | Moruno Spiced Cauliflower | 6 | 在 80 个 cookbook 清单中 |
| 4000330 | Mexican Three Cheese | 6 | 在 80 个 cookbook 清单中 |

### 新发现的组件（不在 80 个 cookbook 清单中）

| Component # | WC Name | 关联 Menu Items 数 | Appliance | 说明 |
|-------------|---------|-------------------|-----------|------|
| 4000380 | Roasted Cauliflower | 18 | TURBO_OVEN | Yasas 主要蔬菜组件 |
| 4000384 | Beef Souvlaki | 24 | TURBO_OVEN | Yasas 最大用量蛋白质组件 |
| 4000411 | Spiced Sweet Potatoes | 23 | TURBO_OVEN | Yasas 主要组件 |
| 4000053 | Fries | 3 | FRYER | 跨品牌使用 |
| 4000709 | Chicken Tender | 1 | FRYER | Bellies 品牌 |
| 4000991 | Falafel | 2 | FRYER | Yasas 品牌 |

---

## 关键发现

### 1. TURBO_OVEN 组件 100% 集中在 Yasas

排除全部 80 个 cookbook # 后，**Limesalt 没有任何 TURBO_OVEN 组件**保留（所有 Limesalt TURBO_OVEN 组件均属于 cookbook 清单）。TURBO_OVEN 成为 Yasas 专属的 appliance 类别。

### 2. Beef Souvlaki 是最大用量组件

**4000384 (Beef Souvlaki)** 关联 24 个 menu items，覆盖 Yasas 标准系列（12）、Rice Pilot（6）、Jasmine Rice Pilot（6）全部三个产品系列。

### 3. FRYER 使用 DIRECT mapping（不同于 TURBO_OVEN 的 customization）

FRYER 子步骤直接引用 `step_related_item`，不经过 customization option。配置有 350°F（默认）和 325°F（Falafel Side 特定 HDR）。

### 4. 部分 Menu Item 有特定 HDR 限制

French Fries Bellies、Mexican Fries Limesalt、Chicken Tenders Bellies 等有多个不同 HDR 的 line build 变体（每个 HDR group 有独立 line build），不只是 "All"。

### 5. Spiced Sweet Potatoes 在 Rice Pilot 系列中替代了 Moruno Spiced Cauliflower

Rice Pilot 系列（8010904、8010911-8010915）中，4000411 (Spiced Sweet Potatoes) 出现在所有 6 个 menu item 的 COOK 步骤中。而报告 1 中同一系列匹配的是 4000281 (Moruno Spiced Cauliflower，cookbook item)。两者可能共用 TURBO_OVEN 的 customization option 映射。

### 6. 6 个新组件不在 cookbook 验证清单中

这些组件在 80 个 cookbook 验证清单之外，但确实出现在 line build 的 COOK 步骤中。如果这些组件需要 Global Appliance Config 管理，则需要被纳入 Wonder Create 的范围。

---

## 查询 SQL

```sql
-- 完整查询见 .claude/tmp/all_components_excluding_wc_only.sql
-- 原始结果 JSON 见 .claude/tmp/all_components_excluding_80_results.json
```

## 相关链接

- [[Wonder Create - Cookbook Line Build Report (Global Config Appliances)]] — 报告 1（80 个 cookbook # 匹配）
- [[WC Ingredient Validation vs Cookbook List 2026-05-08]] — 原始 Cookbook 列表
- [[line-build.md]] — Line Build 领域文档
- [[customization.md]] — Customization 领域文档
