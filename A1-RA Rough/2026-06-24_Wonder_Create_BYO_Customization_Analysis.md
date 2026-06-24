---
title: Wonder Create BYO Customization — 规律分析与自动分类方案
date: 2026-06-24
created: 2026-06-24
updated: 2026-06-24
type: analysis
tags:
  - cookbook
  - product-development
  - recipe-management
domain: cookbook
status: draft
description: 分析 4 个品牌（Royal Greens, Limesalt, Yasas, Hanu Poke）的 BYO customization 结构，找到 component → customization group 的自动归集规则。
sources:
  - https://wonder.atlassian.net/wiki/spaces/~63331686234d44d406d22f29/pages/5386993881
references:
  - "[[MD-18146]]"
---

## 背景

Wonder Create MVP Phase 2 需求（[[MD-18146]]）：将 Wonder Create 从静态 1:1 Cookbook item 升级为支持 BYO 定制化的模式。核心挑战之一是如何**自动将不同 preset 里的 component 归集到 Master BYO item 的一组 customization 下面**。

本报告分析 4 个品牌（Royal Greens、Limesalt、Yasas、Hanu Poke）的现有 BYO 定制化数据，找到分类规律。

---

## 一、10 个唯一 BYO Menu Item 的 Customization 结构

> 查询范围：`item_versions`，过滤 `effective=true, deleted=false, item_status!=DORMANT, version_status!=DRAFT, object_type=MENU`。Preset 项已排除。

### Limesalt 家族（墨西哥风格，6 项）

| Item # | Format | Sold | MANDATORY_CHOICE | OPTIONAL_ADDITION |
|--------|--------|------|-----------------|------------------|
| 8004637 | Burrito | ✅ | Protein(7) Beans(3) Rice(3) ExtraProtein(7) | Toppings(13) |
| 8004638 | Bowl | ✅ | Protein(7) Beans(3) Rice(3) ExtraProtein(7) | Toppings(13) |
| 8005005 | Taco | ✅ | Protein(7) Tortilla(2) | Toppings(17) |
| 8005006 | Salad | ✅ | Protein(7) Beans(3) Rice(3) **Dressing(3)** ExtraProtein(7) | Toppings(12) |
| 8005007 | Quesadilla | ✅ | Protein(6) | FajitaVeg(1) Sides(14) |
| 8010902 | Cheesesteak Quesadilla | ❌ | Protein(6) | FajitaVeg(1) Sides(14) |

**Limesalt "Choose Your Protein" 选项（7个，6个 BYO 项完全一致）：**
- Barbacoa (4000557)、Carnitas (4000558)、Chicken (7000029)
- Shiitake Carnitas (7000084)、Steak (4000636)
- Veggies + Guac (4000550 + 7000018)、No Protein (NULL)

**Limesalt "Choose Your Toppings" 选项（12-17个）：**
- 包含 Cilantro、Corn Salsa、Fajita Vegetables、Guacamole、Pickled Jalapeños、Pico de Gallo、Queso Blanco、Shredded Cheese、Sour Cream 等

### Yasas 家族（地中海风格，4 项）

| Item # | Format | Sold | MANDATORY_CHOICE | OPTIONAL_ADDITION |
|--------|--------|------|-----------------|------------------|
| 8007402 | Wrap | ✅ | Main(4) Dressing(8) | Toppings(14) Spreads(6) ExtraDressing(7) |
| 8007403 | Bowl | ✅ | **Base(5)** Main(4) Dressing(8) **Pita(2)** | Toppings(14) Spreads(6) ExtraDressing(7) |
| 8011818 | Wrap (C&C) | ✅ | Main(4) Dressing(8) | Toppings(14) Spreads(6) ExtraDressing(7) |
| 8010904 | Bowl (Rice Pilot) | ❌ | Base(6) Protein(5) Dressing(5) Pita(2) | Toppings(9) Spreads(5) ExtraDressing(4) ExtraProtein(4) |

**Yasas "Choose Your Main" 选项（4个）：**
- Chicken Souvlaki (7000031)、Steak Souvlaki (7000069)
- Za'atar Roasted Carrots (7000045)、No Protein (NULL)

**Yasas "Choose Dressing" 选项（8个）：**
- Garlic Red Wine Vinaigrette、Green Goddess、Harissa、Lemon Vinaigrette
- Pomegranate Vinaigrette、Tahini Yogurt、Zhug、No Dressing

**Yasas "Choose Your Spreads" 选项（6个）：**
- Eggplant (4000451)、Harissa Dip (4000990)、Hummus (4000476)
- Red Pepper & Feta Spread (4000463)、Toum (4000326)、Tzatziki (4000479)

---

## 二、观察到的规律

### 规律 1：同家族内 Customization Group 完全一致
Bowl、Burrito、Salad、Taco 共享相同的 "Choose Your Protein"、"Choose Your Toppings"。只是不同 format 会增删某些 group（如 Salad 多 Dressing，Taco 少 Beans/Rice 多 Tortilla）。

### 规律 2：同品牌内 Option Values 完全相同
Limesalt 的 "Choose Your Protein" 在所有 6 个 BYO item 里都是相同的 7 个选项。这说明 **option values 是在品牌级别定义的，而非 per-item**。

### 规律 3：MANDATORY vs OPTIONAL 的边界固定

| 类别 | Type | 举例 |
|------|------|------|
| 蛋白质、基底、酱料、主食 | MANDATORY_CHOICE, FEATURED | Choose Your Protein / Base / Dressing |
| 配料、抹酱、加倍 | OPTIONAL_ADDITION, FEATURED | Choose Your Toppings / Spreads |
| 额外酱料、额外蛋白质 | OPTIONAL_ADDITION, IN_DRAWER | Add Extra Dressing / Extra Protein |

### 规律 4：每个 MANDATORY group 都有 "No X" 选项
"Choose Your Protein" → "No Protein"（item_number = NULL），确保用户可以不选。

### 规律 5：Option Value item_number 可能有多个
如 "Extra Veggies + Guac" 映射到 2 个 item（4000550 + 7000018），Quesadilla 的 Protein 选项里 Cheese 被包含在每个 option 中。

---

## 三、Component 自动分类方案

### 3.1 Cookbook 的分类体系

Cookbook 有两层 item 层级，分类路径不同：

| Item 类型 | 前缀 | 分类方式 | 举例 |
|----------|------|---------|------|
| 食材/原料 | 40\*/50\* | 直接取 `Material Category` tag | Chicken Thigh → Protein |
| HDR 配方 | 70\* | 追踪 BOM → 取 required 子组件的 Material Category | Chicken Souvlaki → 子组件 Chicken Thigh → Protein |

**Tag Group**: `Material Category` (`e47e87cf-8e2c-45e7-97c8-2eccd2a12f1d`)

**相关 tag values**（仅列出食品相关）:

| Material Category | 含义 |
|-------------------|------|
| Protein | 蛋白质（鸡肉、牛肉等） |
| Seafood | 海鲜 |
| Vegetables | 蔬菜 |
| Fruit | 水果 |
| Dairy | 乳制品 |
| Sauces/Spreads | 酱料/抹酱 |
| Dry | 干货（米、豆类、谷物等） |
| Pickles/Peppers/Olives | 腌制品 |
| Bakery | 烘焙（面饼、面包） |
| Prepared Food/Buyout | 半成品/采购品 |
| Asian Specialty | 亚洲特色 |

**验证案例** — 70* recipe 的 BOM 子组件分类：

| HDR Recipe | BOM 子组件 | Material Category |
|-----------|-----------|-------------------|
| 7000029 Chicken Souvlaki | 4000328 Diced Chicken Thigh | **Protein** |
| 7000069 Steak Souvlaki | 4000384 Beef Souvlaki | **Protein** |
| 7000040 Supergreens Mix | 4000428 Kale + 4000474 Romaine | **Vegetables** |
| 7000045 Za'atar Roasted Carrots | → 子组件 Carrots | Vegetables |

### 3.2 Material Category → Customization Group 映射规则

```
Material Category                        →  Customization Group           Type
──────────────────────────────────────────────────────────────────────────────────
Protein, Seafood, Prepared Food/Buyout*  →  "Choose Your Protein/Main"   MANDATORY_CHOICE
Dry (rice, grain)                        →  "Choose Your Base/Rice"      MANDATORY_CHOICE
Sauces/Spreads (dressing)               →  "Choose Dressing"             MANDATORY_CHOICE
Vegetables, Fruit, Pickles, Dry(beans)   →  "Choose Your Toppings"       OPTIONAL_ADDITION
Sauces/Spreads (dip/hummus/tzatziki)    →  "Choose Your Spreads"         OPTIONAL_ADDITION
Dairy (cheese)                           →  "Cheese" / Toppings          OPTIONAL_ADDITION
Bakery (tortilla, pita)                  →  "Choose Your Tortilla/Side"   MANDATORY_CHOICE
```

> *Prepared Food/Buyout 需结合 `Material Sub-Category` 判断：Beef/Pork/Chicken → Protein；Dressing → Sauce

### 3.3 边界情况：Sauce vs Spread 的区分

`Sauces/Spreads` 下同时包含 dressing（如 Lime Chipotle Vinaigrette）和抹酱（如 Hummus）。区分方式：
- `Material Sub-Category = "Dressing"` → "Choose Dressing"
- 其他 Sauces/Spreads → "Choose Your Spreads"

---

## 四、完整自动化流程

```
Input: Brand 下 N 个 signature dish 的 BOM components
         │
         ▼
Step 1 ─ 对每个 component 分辨 item 类型
  ├── 40*/50* ingredients
  │     └── 直接查 effective_items.attributes → Material Category tag
  └── 70* HDR recipes
        └── 查 BOM required 子组件 → 取子组件的 Material Category
         │
         ▼
Step 2 ─ Material Category → Customization Group 映射（见 3.2 规则表）
         │
         ▼
Step 3 ─ 同 Group 内去重合并 → Option Values
         每个 option value = {
           name, item_number, usage_quantity, default_price
         }
         │
         ▼
Step 4 ─ 每个 MANDATORY group 追加 "No X" option（item_number=NULL）
         │
         ▼
Step 5 ─ 为每个 signature dish 创建 Preset
         在其默认食材对应的 option value 上标记 is_default=true
         │
         ▼
Output: 1 个 Master BYO item + N 个 Presets
```

### Ola Cocina 示例

```
Master BYO: Bowl (BYO), Ola Cocina
│
├── MANDATORY: Choose Your Base (union of {Brown Rice, White Rice, Romaine})
├── MANDATORY: Choose Your Protein (union of {Chicken, Tuna, Salmon, Barbacoa, Tofu})
├── MANDATORY: Choose Your Dressing (union of {Lime Chipotle, Salsa Verde, Garlic Red Wine Vinaigrette})
├── OPTIONAL: Choose Your Toppings (union of 9 topping items)
│
├── Preset: Pollo Al Pastor Bowl  → Chicken + Brown Rice + Lime Chipotle = default
├── Preset: Baja Poke-Ceviche     → Tuna + Brown Rice + Lime Chipotle = default
├── Preset: Cabo Salmon           → Salmon + White Rice + Lime Chipotle = default
├── Preset: Luau Barbacoa         → Barbacoa + Brown Rice + Salsa Verde = default
└── Preset: Tulum Tofu            → Tofu + Romaine + Garlic Red Wine Vinaigrette = default
```

---

## 五、待确认的开放问题

1. **Sauce vs Spread 的细分规则**：Material Sub-Category = "Dressing" 是否足以区分所有场景？需要更多数据验证
2. **Wonder Create signature dish 的 BOM 结构**：是否遵循同样的 40\*/50\*/70\* 前缀规范？需要抽样验证
3. **Customization Group 模板选择**：新品牌如何决定用 Limesalt 模板还是 Yasas 模板？由 cuisine type 决定还是由 BOM 成分决定？
4. **multi-item option value 处理**：如 Quesadilla "Choose Your Protein" 中每个 option 都绑定 4000330 (Cheese)，这种隐式绑定如何自动化？
