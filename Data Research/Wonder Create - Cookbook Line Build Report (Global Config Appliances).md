---
title: Wonder Create - Cookbook Line Build 分析报告 (Global Config Appliances)
date: 2026-05-21
updated: 2026-05-21
project: Wonder Create
tags: [cookbook, line-build, global-appliance-config, data-research]
source: BigQuery (wonder-dw-prod-brd, wonder-recipe-prod)
---

# Wonder Create - Cookbook Line Build 分析报告

## 查询背景

将 Confluence 页面 [[WC Ingredient Validation vs Cookbook List 2026-05-08]] 中的 cookbook component items 与 4 个品牌（Royal Greens、Limesalt、Yasas、Hanu Poke）的 menu item line build 进行交叉比对，筛选出 `activity=COOK` 且 appliance 为 **需要 Global Appliance Config 的设备类型**（TURBO_OVEN、FRYER、PIZZA_CONVEYOR_OVEN、CLAMSHELL）的子步骤。

## 查询参数

| 参数 | 值 |
|------|-----|
| **Cookbook Items** | 80 个（去重后） |
| **品牌** | Royal Greens, Limesalt, Yasas, Hanu Poke |
| **Menu Item 筛选** | `object_type=MENU`, `effective=true`, `deleted=false`, `item_status!=DORMANT`, `version_status=FINAL` |
| **Activity** | `COOK` |
| **Appliances** | `TURBO_OVEN`, `FRYER`, `PIZZA_CONVEYOR_OVEN`, `CLAMSHELL` |
| **匹配方式** | 直接 (`related_item_number`)、标题匹配、Customization Option 解析 |
| **数据源** | `wonder-dw-prod-brd.master_data.item_versions`, `wonder-recipe-prod.recipe_v2.effective_items`, `wonder-recipe-prod.mongo_batch_recipe_v2.global_appliance_settings` |

## 结果总览

| 指标 | 数值 |
|------|------|
| 匹配的 Component Items | **5 个** |
| 匹配的 Menu Items | **54 个** |
| 总组合行数 | **100 行** |
| 匹配方式 | 全部通过 Customization Option 解析 |
| 命中的 Appliance | 仅 `TURBO_OVEN`（其他无匹配） |
| Global Appliance Config | 全部 `100/90 475°F` (UUID: `a2ce42da`) |
| Restaurant Scope | 全部 `All` |

## 按 Appliance 分析

### TURBO_OVEN — 命中 100 行

| Cookbook # | WC Name | 关联 Menu Items 数 | 使用品牌 |
|------------|---------|-------------------|---------|
| 4000636 | Adobo Steak | 48 | Limesalt |
| 4000550 | Guacamole Spread | 27 | Limesalt |
| 4000872 | Guacamole | 13 | Limesalt |
| 4000281 | Moruno Spiced Cauliflower | 6 | Yasas |
| 4000330 | Mexican Three Cheese | 6 | Limesalt |

**Config 格式**: `{percent_time}/{wind_speed} {temperature}°F` → e.g. `100/90 475°F`

### FRYER — 无匹配

FRYER 子步骤使用 **直接 `step_related_item` 映射**（非 customization），但引用的组件为：
- 4000053 (Fries)
- 4000709 (Breaded Chicken Tender)
- 4000991 (Falafel)

这些均不在 80 个 cookbook 验证清单中。

### PIZZA_CONVEYOR_OVEN — 无匹配

在这 4 个品牌的 COOK 活动中未使用。

**Config 格式示例**: `Oven 4, 575°F, 40/50, 4:45`

### CLAMSHELL — 无匹配

在这 4 个品牌的 COOK 活动中未使用。

**Config 格式示例**: `Top: 450°F, Bottom: 450°F, Gap: 308mm`

## Menu Items 列表

### Limesalt 系列 (Limesalt, 94 rows)

| Menu # | Menu Name | Version | Component Items |
|--------|-----------|---------|-----------------|
| 8004637 | Burrito (BYO), Limesalt | 43 | 4000636, 4000550 |
| 8004638 | Bowl (BYO), Limesalt | 43 | 4000636, 4000550 |
| 8005005 | Taco (BYO), Limesalt | 41 | 4000636, 4000550 |
| 8005006 | Salad (BYO), Limesalt | 43 | 4000636, 4000550 |
| 8005007 | Quesadilla (BYO), Limesalt | 43 | 4000636, 4000330, 4000550 |
| 8010850 | Brown Rice Fajita Bowl, PRESET | 43 | 4000636, 4000550 |
| 8010851 | White Rice Fajita Bowl, PRESET | 43 | 4000636, 4000550 |
| 8010853 | Ranchero Bowl, PRESET | 43 | 4000636, 4000550 |
| 8010854 | Campesino Bowl, PRESET | 43 | 4000636, 4000550 |
| 8010855 | Sabroso Bowl, PRESET | 43 | 4000636, 4000550 |
| 8010856 | Essentials Bowl, PRESET | 43 | 4000636, 4000550 |
| 8010857 | Picante Bowl, PRESET | 43 | 4000636, 4000550 |
| 8010858 | Basics Bowl, PRESET | 43 | 4000636, 4000550 |
| 8010902 | Cheesesteak Quesadilla (BYO), Limesalt | 19 | 4000636, 4000330 |
| 8010907 | BBQ Brisket Burrito, PRESET | 43 | 4000636, 4000550 |
| 8010908 | BBQ Brisket Bowl, PRESET | 43 | 4000636, 4000550 |
| 8010909 | BBQ Brisket Taco, PRESET | 41 | 4000636, 4000550 |
| 8010985 | Cheesesteak Quesadilla, Limesalt PRESET | 19 | 4000636, 4000330 |

#### Limesalt Rice Pilot 系列

| Menu # | Menu Name | Version | Component Items |
|--------|-----------|---------|-----------------|
| 8010916 | Burrito (BYO), Limesalt (Rice Pilot) | 7 | 4000636, 4000872 |
| 8010917 | Bowl (BYO), Limesalt (Rice Pilot) | 7 | 4000636, 4000872 |
| 8010918 | Taco (BYO), Limesalt (Rice Pilot) | 7 | 4000636, 4000872 |
| 8010921 | Cheesesteak Quesadilla (BYO), Limesalt (Rice Pilot) | 6 | 4000636 |
| 8010922 | Brown Rice Fajita Bowl (RICE PILOT) PRESET | 7 | 4000636, 4000872 |
| 8010923 | White Rice Fajita Bowl (RICE PILOT) PRESET | 7 | 4000636, 4000872 |
| 8010924 | Ranchero Bowl (RICE PILOT) PRESET | 7 | 4000636, 4000872 |
| 8010925 | Campesino Bowl (RICE PILOT) PRESET | 7 | 4000636, 4000872 |
| 8010926 | Sabroso Bowl (RICE PILOT) PRESET | 7 | 4000636, 4000872 |
| 8010927 | Essentials Bowl (RICE PILOT) PRESET | 7 | 4000636, 4000872 |
| 8010928 | Picante Bowl (RICE PILOT) PRESET | 7 | 4000636, 4000872 |
| 8010929 | Basics Bowl (RICE PILOT) PRESET | 7 | 4000636, 4000872 |
| 8010935 | BBQ Brisket Burrito (RICE PILOT) PRESET | 7 | 4000636, 4000872 |
| 8010936 | BBQ Brisket Bowl (RICE PILOT) PRESET | 7 | 4000636, 4000872 |
| 8010937 | BBQ Brisket Taco (RICE PILOT) PRESET | 7 | 4000636, 4000872 |

#### Limesalt Jasmine Rice Pilot 系列

| Menu # | Menu Name | Version | Component Items |
|--------|-----------|---------|-----------------|
| 8011565 | Bowl (BYO), Limesalt (Jasmine Rice Pilot) | 1 | 4000636, 4000550 |
| 8011570 | Quesadilla (BYO), Limesalt (Jasmine Rice Pilot) | 1 | 4000330, 4000636 |
| 8011571 | Salad (BYO), Limesalt (Jasmine Rice Pilot) | 1 | 4000636, 4000550 |
| 8011572 | Taco (BYO), Limesalt (Jasmine Rice Pilot) | 1 | 4000636, 4000550 |
| 8011573 | Burrito (BYO), Limesalt (Jasmine Rice Pilot) | 1 | 4000636, 4000550 |
| 8011576 | Cheesesteak Quesadilla (BYO), Limesalt (Jasmine Rice Pilot) | 1 | 4000330, 4000636 |
| 8011591 | Sabroso Bowl, Jasmine Rice Pilot | 1 | 4000636, 4000550 |
| 8011592 | Brown Rice Fajita Bowl, Jasmine Rice Pilot | 1 | 4000636, 4000550 |
| 8011593 | Essentials Bowl, Jasmine Rice Preset | 1 | 4000636, 4000550 |
| 8011594 | Picante Bowl, Jasmine Rice Pilot | 1 | 4000636, 4000550 |
| 8011595 | Ranchero Bowl, Jasmine Rice Pilot | 1 | 4000636, 4000550 |
| 8011596 | Basics Bowl, Jasmine Rice Pilot | 1 | 4000636, 4000550 |
| 8011597 | Campesino Bowl, Jasmine Rice Pilot | 1 | 4000636, 4000550 |
| 8011599 | White Rice Fajita Bowl, Jasmine Rice Pilot | 1 | 4000636, 4000550 |
| 8011610 | Cheesesteak Quesadilla, Jasmine Rice Pilot | 1 | 4000330, 4000636 |

### Yasas Rice Pilot 系列 (Yasas, 6 rows)

| Menu # | Menu Name | Version | Component Items |
|--------|-----------|---------|-----------------|
| 8010904 | Bowl (BYO), Yasas (Rice Pilot) | 7 | 4000281 |
| 8010911 | Beef Souvlaki & Kalamata Salad PRESET, Yasas BYO (RICE PILOT) | 7 | 4000281 |
| 8010912 | Cauliflower & Chickpea Grain Bowl PRESET, Yasas BYO (RICE PILOT) | 7 | 4000281 |
| 8010913 | Spiced Sweet Potato & Feta Salad PRESET, Yasas BYO (RICE PILOT) | 7 | 4000281 |
| 8010914 | Spicy Cauliflower & Feta Salad PRESET, Yasas BYO (RICE PILOT) | 7 | 4000281 |
| 8010915 | Zesty Chicken Souvlaki & Rice Bowl PRESET, Yasas BYO (RICE PILOT) | 7 | 4000281 |

## 关键发现

### 1. 仅 TURBO_OVEN 有匹配结果

| Appliance | COOK 步骤总数 | 匹配行数 | 原因 |
|-----------|-------------|---------|------|
| TURBO_OVEN | 6,529 | 100 | 通过 Customization Option 解析命中 |
| FRYER | 390 | 0 | 使用 direct mapping，但组件不在 cookbook 清单中 |
| PIZZA_CONVEYOR_OVEN | 0 | 0 | 4 个品牌未使用 |
| CLAMSHELL | 0 | 0 | 4 个品牌未使用 |

### 2. 全部匹配通过 Customization Option 解析

所有 TURBO_OVEN 的 COOK 子步骤使用 `related_customization_option`（UUID 引用），**无任何直接 `related_item_number` 映射**。组件 → 菜单项的关联通过 menu item 的 `item_customization.options[].option_values[].items[].item_number` 间接解析。

### 3. 品牌分布

- **Limesalt** — 94 行，5 个组件，覆盖全部产品系列（BYO、PRESET、Rice Pilot、Jasmine Rice Pilot）
- **Yasas** — 6 行，仅 Moruno Spiced Cauliflower，限定在 Rice Pilot 系列
- **Royal Greens** — 无匹配
- **Hanu Poke** — 无匹配

### 4. Global Appliance Config — 仅 TURBO_OVEN 有数据

| Appliance | Config UUID | Config 值 |
|-----------|-------------|-----------|
| TURBO_OVEN | `a2ce42da` | `100/90 475°F` |
| FRYER | — | 无匹配，无对应数据 |
| PIZZA_CONVEYOR_OVEN | — | 未使用 |
| CLAMSHELL | — | 未使用 |

### 5. Restaurant Scope 全部为 All

无针对特定 HDR 的例外 line build。

## 查询 SQL

```sql
-- 完整查询见 .claude/tmp/turbo_oven_query.sql
-- 原始结果 JSON (.claude/tmp/turbo_oven_results.json) 包含字段:
-- component_item_number, component_item_name, menu_item_number, menu_item_name,
-- menu_item_version, activity, appliance, global_appliance_config,
-- line_build_apply_to_restaurant, match_type, brand_names
```

## 相关链接

- [[WC Ingredient Validation vs Cookbook List 2026-05-08]] — 原始 Cookbook 列表
- [[line-build.md]] — Line Build 领域文档
- [[customization.md]] — Customization 领域文档
