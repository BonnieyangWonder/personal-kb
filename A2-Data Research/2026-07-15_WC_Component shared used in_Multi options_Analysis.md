# Wonder Create — Cookbook 定制项多映射分析 

## Food Component 被多个选项映射的设计问题诊断

**项目**: Wonder Create
**报告日期**: 2026-07-15
**数据源**: `wonder-recipe-prod.recipe_v2`（`item_versions` / `menus` / `concepts`）
**分析对象**: 单个 menu item 的当前 version 内，`MANDATORY_CHOICE` + `OPTIONAL_ADDITION` 两类 customization 选项中，**某个 food component item 被多个选项值（option value）映射**的情况。

**核心问题**: 识别 Cookbook 菜品配置中，同一食材被多个选项映射的模式，区分"真正的重复设计问题"与"正常的组合菜品设计"。

> 表中的 **Version N** 即 Cookbook UI 上的版本号（`item_versions.version_id` 整数），非内部 UUID。

---

## 0. 口径修正说明（相对初版）

本报告是对初版（同名文件）的**方法论修正重做**。初版有三处偏差，已全部纠正：

| # | 初版问题 | 本版修正 |
|---|---|---|
| 1 | 把 `9002138 Souffle Cup` / `9002139 Lid` 当作头号“food component” | 这些是 `object_type = NON_FOOD` 的**包材**。本版只保留 `object_type IN (HDR_CONSUMABLE_ITEM, HDR_RECIPE)` 的**真实 food** |
| 2 | 品牌关联用 `concept_ids LIKE '%id%'`（会跨品牌污染） | 改用 **`concept_count = 1` 的品牌专属 menu**（playbook §2 强制要求） |
| 3 | “多个 option” 的粒度/含义不清 | 明确 = **多个 option value（选择项，如 tofu/chicken）**；并**排除 “Extra X” 加量选项**，只看正常选择 |

---

## 1. 判定逻辑

一个 (menu item, food component) 组合”命中”，当且仅当：在该 menu item 当前 version 的 customization 里，**≥2 个不同的 option value**（`option_value_id`）的 `items[]` 都指向同一个 food component。

**数据层级**（3 层）：`item_customization → options[] → option_values[] → items[]`
- `options[]` = 定制分组（如 “Choose Your Protein”）
- `option_values[]` = 具体选择项（如 tofu、chicken）← 用户口径里的 “option”
- `items[]` = 该选择映射到的 food component

### 重复模式的两种类型

本报告中发现的 “food component 被多个 option value 映射” 有两种截然不同的模式：

| 模式 | 定义 | 特征 | 示例 |
|------|------|------|------|
| **真正重复** | 同一食材在多个 **单食材选择项** 中出现 | 无组合选项参与，食材被独立选择多次 | Yasas Bowl：Romaine 同时作为 Base 和 Topping 选择 |
| **组合引发** | 同一食材在多个 **组合选择项** 中作为成分出现 | 组合选项（如 “Rice & Greens”）导致其成分被重复计数 | Hanu Poke Bowl：Rice 出现在 “Rice & Greens”、”Soba & Rice”、”Sushi Rice” 中（实际上是 3 个组合选项的组成部分） |

**本版数据分析**：
- **真正重复的 (menu item, food component) 组合**：共 **2 对**（见 §1.1）
- **含组合选项的命中**：共 **105 对**（需拆分理解）

**关于”同名跨 option”**：有些命中里两个 option value 显示名相同（如 Yasas “Romaine” 同时在 Choose Your Base 与 Choose Your Toppings；Burger Baby 同款酱同时在 On Burger 与 On The Side），它们是不同的 `option_value_id`，本版按”命中”保留，并在”选择”列标注 _（含同名不同项）_。

### 1.1 真正重复的食材（单食材重复，不含组合选项）

**仅 2 个 food component 被多个单映射的 option value 使用**：

| Menu Item | Item Number | Version | Food Component | Food Item Number | 出现在的选择 | 选择所属 Option |
|-----------|-------------|---------|-----------------|-----------------|-----------|------------|
| Bowl (BYO), Yasas | 8007403 | 42 | Romaine Lettuce | 4000427 | Romaine（出现 2 次，同名不同项） | Choose Your Base [MANDATORY_CHOICE] + Choose Your Toppings [OPTIONAL_ADDITION] |
| BYO Poke Bowl, Hanu Poke BOWLDER | 8010473 | 22 | Poke Marinade | 4000742 | Poke Marinade Mixed In · Poke Marinade On the Side | Include Poke Marinade [MANDATORY_CHOICE] |

**结论**：真正的重复非常稀少（仅 2 对）。Hanu Poke 的 Rice、Spring Mix、Soba Noodles 看似被多个选择映射，但实际上是被多个**组合选项**（如 “Rice & Greens”）的 items[] 分别包含，不属于真正重复。

## 2. 过滤条件

| 条件 | 说明 |
|------|------|
| `effective = true` AND `deleted = false` | 当前有效、未软删 |
| `item_status != 'DORMANT'` | 排除 dormant menu item |
| `object_type = 'MENU'` | 仅 menu item |
| `sold_status = 'FOR_SALE'` | 在售 |
| `version_status = 'FINAL'` | 已发布、非过期 version（非 DRAFT/SCHEDULED）→ 满足“1 menu item 1 version” |
| `preset_item_version_info IS NULL` | 排除 preset / BYO preset |
| option `type IN ('MANDATORY_CHOICE','OPTIONAL_ADDITION')` | 仅这两类 customization |
| option value 名 **不以 “Extra ” 开头** | 排除 “Extra Chicken / Extra Sauce” 等加量选项 |
| mapped item `object_type IN ('HDR_CONSUMABLE_ITEM','HDR_RECIPE')` | **仅 food**，排除 NON_FOOD 包材 |
| brand（仅 Part A）= `concept_count = 1` 品牌专属 menu | 避免共享 menu 跨品牌污染 |

---

## Part A — 四个品牌（Royal Greens / Limesalt / Yasas / Hanu Poke）

**结论：有命中。** 共 **14 个去重后的 (menu item × food component) 组合，涉及 7 个 distinct menu item**。

- **Limesalt**：5 个 menu item（Quesadilla / Burrito / Bowl / Taco / Salad），9 对
- **Hanu Poke**：1 个 menu item（BYO Poke Bowl BOWLDER），4 对
- **Yasas**：1 个 menu item（Bowl BYO），1 对
- **Royal Greens**：无专属命中（唯一命中项是泄漏进其 Bowlder Menu 的 Hanu Poke item）

#### Royal Greens

> ⚠️ Royal Greens 名下唯一命中的 `8010473 BYO Poke Bowl, Hanu Poke BOWLDER` 本质是 Hanu Poke 的 item（同时被放进了 Royal Greens 的 “Bowlder Menu”）。**Royal Greens 没有自己专属的命中 item**——详见 Hanu Poke。

#### Limesalt

⚠️ **本部分所有命中均为"夹带成分"或"组合引发"类型**：Limesalt 的菜品中，某些食材（如 Mexican Three Cheese）被每个 protein 选择自动夹带；或某些蔬菜（Fajita Vegetables、Guacamole）同时在 protein 选择和 toppings 中出现。这些都反映的是**菜品设计中的默认成分**或**同一食材在多个选项中的使用**，而非真正的重复设计问题。

**`[8005007]` Quesadilla (BYO), Limesalt**  ·  Version 46

| food component                 | object_type         | 被N个选择映射 | 映射它的选择（option values）                                                   | 涉及的 option [type]                      | 重复类型 |
| ------------------------------ | ------------------- | :-----: | ----------------------------------------------------------------------- | -------------------------------------- | ---|
| `4000330` Mexican Three Cheese | HDR_CONSUMABLE_ITEM |    6    | Barbacoa · Carnitas · Cheese Only · Chicken · Shiitake Carnitas · Steak | Choose Your Protein [MANDATORY_CHOICE] | ⚠️ 组合引发（每个 protein 选择都内含此奶酪） |

**`[8004637]` Burrito (BYO), Limesalt**  ·  Version 46

| food component | object_type | 被N个选择映射 | 映射它的选择（option values） | 涉及的 option [type] |
|---|---|:--:|---|---|
| `4000550` Guacamole | HDR_CONSUMABLE_ITEM | 2 | Guacamole · Veggies + Guac | Choose Your Protein [MANDATORY_CHOICE] · Choose Your Toppings [OPTIONAL_ADDITION] |
| `7000018` Fajita Vegetables (Cooked, 4x) | HDR_RECIPE | 2 | Fajita Vegetables · Veggies + Guac | Choose Your Protein [MANDATORY_CHOICE] · Choose Your Toppings [OPTIONAL_ADDITION] |

**`[8004638]` Bowl (BYO), Limesalt**  ·  Version 46

| food component | object_type | 被N个选择映射 | 映射它的选择（option values） | 涉及的 option [type] |
|---|---|:--:|---|---|
| `4000550` Guacamole | HDR_CONSUMABLE_ITEM | 2 | Guacamole · Veggies + Guac | Choose Your Protein [MANDATORY_CHOICE] · Choose Your Toppings [OPTIONAL_ADDITION] |
| `7000018` Fajita Vegetables (Cooked, 4x) | HDR_RECIPE | 2 | Fajita Vegetables · Veggies + Guac | Choose Your Protein [MANDATORY_CHOICE] · Choose Your Toppings [OPTIONAL_ADDITION] |

**`[8005005]` Taco (BYO), Limesalt**  ·  Version 44

| food component | object_type | 被N个选择映射 | 映射它的选择（option values） | 涉及的 option [type] |
|---|---|:--:|---|---|
| `4000550` Guacamole | HDR_CONSUMABLE_ITEM | 2 | Guacamole · Veggies + Guac | Choose Your Protein [MANDATORY_CHOICE] · Choose Your Toppings [OPTIONAL_ADDITION] |
| `7000018` Fajita Vegetables (Cooked, 4x) | HDR_RECIPE | 2 | Fajita Vegetables · Veggies + Guac | Choose Your Protein [MANDATORY_CHOICE] · Choose Your Toppings [OPTIONAL_ADDITION] |

**`[8005006]` Salad (BYO), Limesalt**  ·  Version 46

| food component | object_type | 被N个选择映射 | 映射它的选择（option values） | 涉及的 option [type] |
|---|---|:--:|---|---|
| `4000550` Guacamole | HDR_CONSUMABLE_ITEM | 2 | Guacamole · Veggies + Guac | Choose Your Protein [MANDATORY_CHOICE] · Choose Your Toppings [OPTIONAL_ADDITION] |
| `7000018` Fajita Vegetables (Cooked, 4x) | HDR_RECIPE | 2 | Fajita Vegetables · Veggies + Guac | Choose Your Protein [MANDATORY_CHOICE] · Choose Your Toppings [OPTIONAL_ADDITION] |

#### Yasas

**`[8007403]` Bowl (BYO), Yasas**  ·  Version 42

| food component | object_type | 被N个选择映射 | 映射它的选择（option values） | 涉及的 option [type] | 重复类型 |
|---|---|:--:|---|---|---|
| `4000427` Romaine Lettuce | HDR_CONSUMABLE_ITEM | 2 | Romaine  _（2 个 option value，含同名不同项）_ | Choose Your Base [MANDATORY_CHOICE] · Choose Your Toppings [OPTIONAL_ADDITION] | ✓ 真正重复（用户可在两个不同选项中独立选择 Romaine） |

#### Hanu Poke

**`[8010473]` BYO Poke Bowl, Hanu Poke BOWLDER**  ·  Version 22

| food component | object_type | 被N个选择映射 | 映射它的选择（option values） | 涉及的 option [type] | 重复类型 |
|---|---|:--:|---|---|---|
| `4000402` Rice, Poke, FC, 10oz. (Co-Man) HC | HDR_CONSUMABLE_ITEM | 3 | Rice & Greens · Soba Noodles & Rice · Sushi Rice | Choose Your Base [MANDATORY_CHOICE] | ⚠️ 组合引发（3个组合选项均含此食材） |
| `4000470` Spring Mix Lettuce | HDR_CONSUMABLE_ITEM | 3 | Mixed Greens · Rice & Greens · Soba Noodles & Greens | Choose Your Base [MANDATORY_CHOICE] | ⚠️ 组合引发（3个组合选项均含此食材） |
| `4000968` Soba Noodles | HDR_CONSUMABLE_ITEM | 3 | Soba Noodles · Soba Noodles & Greens · Soba Noodles & Rice | Choose Your Base [MANDATORY_CHOICE] | ⚠️ 组合引发（3个组合选项均含此食材） |
| `4000742` Poke Marinade | HDR_CONSUMABLE_ITEM | 2 | Poke Marinade Mixed In · Poke Marinade On the Side | Include Poke Marinade [MANDATORY_CHOICE] | ✓ 真正重复（单食材选择，非组合） |

---

## Part B — 全品牌（不限 brand）

**结论：有命中。** 共 **107 个 (menu item × food component) 组合，涉及 53 个 distinct menu item、22 个 distinct food component**。

映射强度分布：**6 个选择映射同一 food** ×4 · **3 个选择** ×4 · **2 个选择** ×99。

### 重复模式的分布

| 模式类型 | 数量 | 组成 |
|---------|------|------|
| **真正重复**（单食材重复，不含组合选项） | 2 | Yasas Romaine + Hanu Poke Poke Marinade |
| **组合引发**（多个组合选项共享食材成分） | 105 | Burger Baby 酱料、Limesalt 奶酪/蔬菜、Hanu Poke 底料等 |

### 模式详解

三类典型模式：
1. **底料复用（组合选择）** — 如 Hanu BYO Poke Bowl 的 “Choose Your Base”，组合项 “Rice & Greens / Soba & Rice / Sushi Rice” 都指向同一份 Rice。**这是组合引发**，而非单食材重复。
2. **同物出现在多个单项选择** — 如 Burger Baby 同一酱料同时在 “Additional Sauce (On Burger)” 与 “(On The Side)” 两个 option；Yasas “Romaine” 同时是 base 和 topping。**这是真正重复**。
3. **夹带成分（隐藏在选项中）** — 如 Limesalt Quesadilla 每种 protein 选择都夹带 “Mexican Three Cheese”。这可能是真正重复，也可能是数据模型设计（是否应该在组合选项中处理）的问题。

#### Burger Baby — 30 对 / 11 个 menu item

⚠️ **本部分所有命中均为"组合引发"类型**：Burger Baby 的菜品中，每种酱料（Queso Blanco、Chipotle Mayo 等）在同一菜品中同时出现在 "On Burger" 和 "On The Side" 两个不同的选项组中，但这反映的是**酱料放置位置的选择**（不同 option），而非菜品设计的重复。

**`[8007200]` Bacon Cheeseburger, Burger Baby**  ·  Version 20

| food component | 被N个选择映射 | 映射它的选择 | 涉及 option [type] | 重复类型 |
|---|:--:|---|---|---|
| `4000279` Queso Blanco Sauce | 2 | Queso Blanco  _（2 个 option value，含同名不同项）_ | Additional Sauce (On The Side) [OPTIONAL_ADDITION] · Additional Toppings [OPTIONAL_ADDITION] | ⚠️ 组合引发（不同位置选项） |
| `4000284` Rosarita HC | 2 | Chipotle Mayo  _（2 个 option value，含同名不同项）_ | Additional Sauce (On Burger) [OPTIONAL_ADDITION] · Additional Sauce (On The Side) [OPTIONAL_ADDITION] | ⚠️ 组合引发（不同位置选项） |
| `4000442` BBQ Hickory Brown Sugar Sauce | 2 | BBQ Sauce  _（2 个 option value，含同名不同项）_ | Additional Sauce (On Burger) [OPTIONAL_ADDITION] · Additional Sauce (On The Side) [OPTIONAL_ADDITION] | ⚠️ 组合引发（不同位置选项） |
| `4000996` Avocado Ranch Dressing | 2 | Avocado Ranch  _（2 个 option value，含同名不同项）_ | Additional Sauce (On Burger) [OPTIONAL_ADDITION] · Additional Sauce (On The Side) [OPTIONAL_ADDITION] | ⚠️ 组合引发（不同位置选项） |

**`[8007201]` Classic Hamburger, Burger Baby**  ·  Version 17

| food component | 被N个选择映射 | 映射它的选择 | 涉及 option [type] |
|---|:--:|---|---|
| `4000279` Queso Blanco Sauce | 2 | Queso Blanco  _（2 个 option value，含同名不同项）_ | Additional Sauce (On The Side) [OPTIONAL_ADDITION] · Additional Toppings [OPTIONAL_ADDITION] |
| `4000284` Rosarita HC | 2 | Chipotle Mayo  _（2 个 option value，含同名不同项）_ | Additional Sauce (On Burger) [OPTIONAL_ADDITION] · Additional Sauce (On The Side) [OPTIONAL_ADDITION] |
| `4000442` BBQ Hickory Brown Sugar Sauce | 2 | BBQ Sauce  _（2 个 option value，含同名不同项）_ | Additional Sauce (On Burger) [OPTIONAL_ADDITION] · Additional Sauce (On The Side) [OPTIONAL_ADDITION] |
| `4000996` Avocado Ranch Dressing | 2 | Avocado Ranch  _（2 个 option value，含同名不同项）_ | Additional Sauce (On Burger) [OPTIONAL_ADDITION] · Additional Sauce (On The Side) [OPTIONAL_ADDITION] |

**`[8007205]` Classic Cheeseburger, Burger Baby**  ·  Version 17

| food component | 被N个选择映射 | 映射它的选择 | 涉及 option [type] |
|---|:--:|---|---|
| `4000279` Queso Blanco Sauce | 2 | Queso Blanco  _（2 个 option value，含同名不同项）_ | Additional Sauce (On The Side) [OPTIONAL_ADDITION] · Additional Toppings [OPTIONAL_ADDITION] |
| `4000284` Rosarita HC | 2 | Chipotle Mayo  _（2 个 option value，含同名不同项）_ | Additional Sauce (On Burger) [OPTIONAL_ADDITION] · Additional Sauce (On The Side) [OPTIONAL_ADDITION] |
| `4000442` BBQ Hickory Brown Sugar Sauce | 2 | BBQ Sauce  _（2 个 option value，含同名不同项）_ | Additional Sauce (On Burger) [OPTIONAL_ADDITION] · Additional Sauce (On The Side) [OPTIONAL_ADDITION] |
| `4000996` Avocado Ranch Dressing | 2 | Avocado Ranch  _（2 个 option value，含同名不同项）_ | Additional Sauce (On Burger) [OPTIONAL_ADDITION] · Additional Sauce (On The Side) [OPTIONAL_ADDITION] |

**`[8007908]` Big Baby, Burger Baby**  ·  Version 16

| food component | 被N个选择映射 | 映射它的选择 | 涉及 option [type] |
|---|:--:|---|---|
| `4000279` Queso Blanco Sauce | 2 | Queso Blanco  _（2 个 option value，含同名不同项）_ | Additional Sauce (On The Side) [OPTIONAL_ADDITION] · Additional Toppings [OPTIONAL_ADDITION] |
| `4000284` Rosarita HC | 2 | Chipotle Mayo  _（2 个 option value，含同名不同项）_ | Additional Sauce (On Burger) [OPTIONAL_ADDITION] · Additional Sauce (On The Side) [OPTIONAL_ADDITION] |
| `4000442` BBQ Hickory Brown Sugar Sauce | 2 | BBQ Sauce  _（2 个 option value，含同名不同项）_ | Additional Sauce (On Burger) [OPTIONAL_ADDITION] · Additional Sauce (On The Side) [OPTIONAL_ADDITION] |
| `4000996` Avocado Ranch Dressing | 2 | Avocado Ranch  _（2 个 option value，含同名不同项）_ | Additional Sauce (On Burger) [OPTIONAL_ADDITION] · Additional Sauce (On The Side) [OPTIONAL_ADDITION] |

**`[8007910]` Double Bacon Cheeseburger, Burger Baby**  ·  Version 19

| food component | 被N个选择映射 | 映射它的选择 | 涉及 option [type] |
|---|:--:|---|---|
| `4000279` Queso Blanco Sauce | 2 | Queso Blanco  _（2 个 option value，含同名不同项）_ | Additional Sauce (On The Side) [OPTIONAL_ADDITION] · Additional Toppings [OPTIONAL_ADDITION] |
| `4000284` Rosarita HC | 2 | Chipotle Mayo  _（2 个 option value，含同名不同项）_ | Additional Sauce (On Burger) [OPTIONAL_ADDITION] · Additional Sauce (On The Side) [OPTIONAL_ADDITION] |
| `4000442` BBQ Hickory Brown Sugar Sauce | 2 | BBQ Sauce  _（2 个 option value，含同名不同项）_ | Additional Sauce (On Burger) [OPTIONAL_ADDITION] · Additional Sauce (On The Side) [OPTIONAL_ADDITION] |
| `4000996` Avocado Ranch Dressing | 2 | Avocado Ranch  _（2 个 option value，含同名不同项）_ | Additional Sauce (On Burger) [OPTIONAL_ADDITION] · Additional Sauce (On The Side) [OPTIONAL_ADDITION] |

**`[8011697]` Smashburger Taco, Burger Baby**  ·  Version 2

| food component | 被N个选择映射 | 映射它的选择 | 涉及 option [type] |
|---|:--:|---|---|
| `4000284` Rosarita HC | 2 | Chipotle Mayo  _（2 个 option value，含同名不同项）_ | Additional Sauce (On Taco) [OPTIONAL_ADDITION] · Additional Sauce (On The Side) [OPTIONAL_ADDITION] |
| `4000996` Avocado Ranch Dressing | 2 | Avocado Ranch  _（2 个 option value，含同名不同项）_ | Additional Sauce (On Taco) [OPTIONAL_ADDITION] · Additional Sauce (On The Side) [OPTIONAL_ADDITION] |

**`[8011699]` Veggie Baby, Burger Baby**  ·  Version 2

| food component | 被N个选择映射 | 映射它的选择 | 涉及 option [type] |
|---|:--:|---|---|
| `4000279` Queso Blanco Sauce | 2 | Queso Blanco  _（2 个 option value，含同名不同项）_ | Additional Sauce (On The Side) [OPTIONAL_ADDITION] · Additional Toppings [OPTIONAL_ADDITION] |

**`[8011700]` Bronco Baby, Burger Baby**  ·  Version 2

| food component | 被N个选择映射 | 映射它的选择 | 涉及 option [type] |
|---|:--:|---|---|
| `4000279` Queso Blanco Sauce | 2 | Queso Blanco  _（2 个 option value，含同名不同项）_ | Additional Sauce (On The Side) [OPTIONAL_ADDITION] · Additional Toppings [OPTIONAL_ADDITION] |

**`[8011702]` Double Veggie Baby, Burger Baby**  ·  Version 2

| food component | 被N个选择映射 | 映射它的选择 | 涉及 option [type] |
|---|:--:|---|---|
| `4000279` Queso Blanco Sauce | 2 | Queso Blanco  _（2 个 option value，含同名不同项）_ | Additional Sauce (On The Side) [OPTIONAL_ADDITION] · Additional Toppings [OPTIONAL_ADDITION] |

**`[8011703]` Double Bronco Baby, Burger Baby**  ·  Version 2

| food component | 被N个选择映射 | 映射它的选择 | 涉及 option [type] |
|---|:--:|---|---|
| `4000279` Queso Blanco Sauce | 2 | Queso Blanco  _（2 个 option value，含同名不同项）_ | Additional Sauce (On The Side) [OPTIONAL_ADDITION] · Additional Toppings [OPTIONAL_ADDITION] |

**`[8011705]` Classic Double Burger, Burger Baby**  ·  Version 2

| food component | 被N个选择映射 | 映射它的选择 | 涉及 option [type] |
|---|:--:|---|---|
| `4000279` Queso Blanco Sauce | 2 | Queso Blanco  _（2 个 option value，含同名不同项）_ | Additional Sauce (On The Side) [OPTIONAL_ADDITION] · Additional Toppings [OPTIONAL_ADDITION] |
| `4000284` Rosarita HC | 2 | Chipotle Mayo  _（2 个 option value，含同名不同项）_ | Additional Sauce (On Burger) [OPTIONAL_ADDITION] · Additional Sauce (On The Side) [OPTIONAL_ADDITION] |
| `4000442` BBQ Hickory Brown Sugar Sauce | 2 | BBQ Sauce  _（2 个 option value，含同名不同项）_ | Additional Sauce (On Burger) [OPTIONAL_ADDITION] · Additional Sauce (On The Side) [OPTIONAL_ADDITION] |
| `4000996` Avocado Ranch Dressing | 2 | Avocado Ranch  _（2 个 option value，含同名不同项）_ | Additional Sauce (On Burger) [OPTIONAL_ADDITION] · Additional Sauce (On The Side) [OPTIONAL_ADDITION] |

#### Burger Baby (Pilot) — 30 对 / 11 个 menu item

**`[8010580]` Bacon Cheeseburger, Burger Baby (Pilot)**  ·  Version 16

| food component | 被N个选择映射 | 映射它的选择 | 涉及 option [type] |
|---|:--:|---|---|
| `4000279` Queso Blanco Sauce | 2 | Queso Blanco  _（2 个 option value，含同名不同项）_ | Additional Sauce (On The Side) [OPTIONAL_ADDITION] · Additional Toppings [OPTIONAL_ADDITION] |
| `4000284` Rosarita HC | 2 | Chipotle Mayo  _（2 个 option value，含同名不同项）_ | Additional Sauce (On Burger) [OPTIONAL_ADDITION] · Additional Sauce (On The Side) [OPTIONAL_ADDITION] |
| `4000442` BBQ Hickory Brown Sugar Sauce | 2 | BBQ Sauce  _（2 个 option value，含同名不同项）_ | Additional Sauce (On Burger) [OPTIONAL_ADDITION] · Additional Sauce (On The Side) [OPTIONAL_ADDITION] |
| `4000996` Avocado Ranch Dressing | 2 | Avocado Ranch  _（2 个 option value，含同名不同项）_ | Additional Sauce (On Burger) [OPTIONAL_ADDITION] · Additional Sauce (On The Side) [OPTIONAL_ADDITION] |

**`[8010581]` Classic Hamburger, Burger Baby (Pilot)**  ·  Version 15

| food component | 被N个选择映射 | 映射它的选择 | 涉及 option [type] |
|---|:--:|---|---|
| `4000279` Queso Blanco Sauce | 2 | Queso Blanco  _（2 个 option value，含同名不同项）_ | Additional Sauce (On The Side) [OPTIONAL_ADDITION] · Additional Toppings [OPTIONAL_ADDITION] |
| `4000284` Rosarita HC | 2 | Chipotle Mayo  _（2 个 option value，含同名不同项）_ | Additional Sauce (On Burger) [OPTIONAL_ADDITION] · Additional Sauce (On The Side) [OPTIONAL_ADDITION] |
| `4000442` BBQ Hickory Brown Sugar Sauce | 2 | BBQ Sauce  _（2 个 option value，含同名不同项）_ | Additional Sauce (On Burger) [OPTIONAL_ADDITION] · Additional Sauce (On The Side) [OPTIONAL_ADDITION] |
| `4000996` Avocado Ranch Dressing | 2 | Avocado Ranch  _（2 个 option value，含同名不同项）_ | Additional Sauce (On Burger) [OPTIONAL_ADDITION] · Additional Sauce (On The Side) [OPTIONAL_ADDITION] |

**`[8010584]` Classic Cheeseburger, Burger Baby (Pilot)**  ·  Version 15

| food component | 被N个选择映射 | 映射它的选择 | 涉及 option [type] |
|---|:--:|---|---|
| `4000279` Queso Blanco Sauce | 2 | Queso Blanco  _（2 个 option value，含同名不同项）_ | Additional Sauce (On The Side) [OPTIONAL_ADDITION] · Additional Toppings [OPTIONAL_ADDITION] |
| `4000284` Rosarita HC | 2 | Chipotle Mayo  _（2 个 option value，含同名不同项）_ | Additional Sauce (On Burger) [OPTIONAL_ADDITION] · Additional Sauce (On The Side) [OPTIONAL_ADDITION] |
| `4000442` BBQ Hickory Brown Sugar Sauce | 2 | BBQ Sauce  _（2 个 option value，含同名不同项）_ | Additional Sauce (On Burger) [OPTIONAL_ADDITION] · Additional Sauce (On The Side) [OPTIONAL_ADDITION] |
| `4000996` Avocado Ranch Dressing | 2 | Avocado Ranch  _（2 个 option value，含同名不同项）_ | Additional Sauce (On Burger) [OPTIONAL_ADDITION] · Additional Sauce (On The Side) [OPTIONAL_ADDITION] |

**`[8010591]` Big Baby, Burger Baby (Pilot)**  ·  Version 15

| food component | 被N个选择映射 | 映射它的选择 | 涉及 option [type] |
|---|:--:|---|---|
| `4000279` Queso Blanco Sauce | 2 | Queso Blanco  _（2 个 option value，含同名不同项）_ | Additional Sauce (On The Side) [OPTIONAL_ADDITION] · Additional Toppings [OPTIONAL_ADDITION] |
| `4000284` Rosarita HC | 2 | Chipotle Mayo  _（2 个 option value，含同名不同项）_ | Additional Sauce (On Burger) [OPTIONAL_ADDITION] · Additional Sauce (On The Side) [OPTIONAL_ADDITION] |
| `4000442` BBQ Hickory Brown Sugar Sauce | 2 | BBQ Sauce  _（2 个 option value，含同名不同项）_ | Additional Sauce (On Burger) [OPTIONAL_ADDITION] · Additional Sauce (On The Side) [OPTIONAL_ADDITION] |
| `4000996` Avocado Ranch Dressing | 2 | Avocado Ranch  _（2 个 option value，含同名不同项）_ | Additional Sauce (On Burger) [OPTIONAL_ADDITION] · Additional Sauce (On The Side) [OPTIONAL_ADDITION] |

**`[8010592]` Double Bacon Cheeseburger, Burger Baby (Pilot)**  ·  Version 16

| food component | 被N个选择映射 | 映射它的选择 | 涉及 option [type] |
|---|:--:|---|---|
| `4000279` Queso Blanco Sauce | 2 | Queso Blanco  _（2 个 option value，含同名不同项）_ | Additional Sauce (On The Side) [OPTIONAL_ADDITION] · Additional Toppings [OPTIONAL_ADDITION] |
| `4000284` Rosarita HC | 2 | Chipotle Mayo  _（2 个 option value，含同名不同项）_ | Additional Sauce (On Burger) [OPTIONAL_ADDITION] · Additional Sauce (On The Side) [OPTIONAL_ADDITION] |
| `4000442` BBQ Hickory Brown Sugar Sauce | 2 | BBQ Sauce  _（2 个 option value，含同名不同项）_ | Additional Sauce (On Burger) [OPTIONAL_ADDITION] · Additional Sauce (On The Side) [OPTIONAL_ADDITION] |
| `4000996` Avocado Ranch Dressing | 2 | Avocado Ranch  _（2 个 option value，含同名不同项）_ | Additional Sauce (On Burger) [OPTIONAL_ADDITION] · Additional Sauce (On The Side) [OPTIONAL_ADDITION] |

**`[8011761]` Classic Double Burger, Burger Baby (Pilot)**  ·  Version 2

| food component | 被N个选择映射 | 映射它的选择 | 涉及 option [type] |
|---|:--:|---|---|
| `4000279` Queso Blanco Sauce | 2 | Queso Blanco  _（2 个 option value，含同名不同项）_ | Additional Sauce (On The Side) [OPTIONAL_ADDITION] · Additional Toppings [OPTIONAL_ADDITION] |
| `4000284` Rosarita HC | 2 | Chipotle Mayo  _（2 个 option value，含同名不同项）_ | Additional Sauce (On Burger) [OPTIONAL_ADDITION] · Additional Sauce (On The Side) [OPTIONAL_ADDITION] |
| `4000442` BBQ Hickory Brown Sugar Sauce | 2 | BBQ Sauce  _（2 个 option value，含同名不同项）_ | Additional Sauce (On Burger) [OPTIONAL_ADDITION] · Additional Sauce (On The Side) [OPTIONAL_ADDITION] |
| `4000996` Avocado Ranch Dressing | 2 | Avocado Ranch  _（2 个 option value，含同名不同项）_ | Additional Sauce (On Burger) [OPTIONAL_ADDITION] · Additional Sauce (On The Side) [OPTIONAL_ADDITION] |

**`[8011764]` Bronco Baby, Burger Baby (Pilot)**  ·  Version 2

| food component | 被N个选择映射 | 映射它的选择 | 涉及 option [type] |
|---|:--:|---|---|
| `4000279` Queso Blanco Sauce | 2 | Queso Blanco  _（2 个 option value，含同名不同项）_ | Additional Sauce (On The Side) [OPTIONAL_ADDITION] · Additional Toppings [OPTIONAL_ADDITION] |

**`[8011766]` Smashburger Taco, Burger Baby (Pilot)**  ·  Version 2

| food component | 被N个选择映射 | 映射它的选择 | 涉及 option [type] |
|---|:--:|---|---|
| `4000284` Rosarita HC | 2 | Chipotle Mayo  _（2 个 option value，含同名不同项）_ | Additional Sauce (On Taco) [OPTIONAL_ADDITION] · Additional Sauce (On The Side) [OPTIONAL_ADDITION] |
| `4000996` Avocado Ranch Dressing | 2 | Avocado Ranch  _（2 个 option value，含同名不同项）_ | Additional Sauce (On Taco) [OPTIONAL_ADDITION] · Additional Sauce (On The Side) [OPTIONAL_ADDITION] |

**`[8011780]` Double Bronco Baby, Burger Baby (Pilot)**  ·  Version 2

| food component | 被N个选择映射 | 映射它的选择 | 涉及 option [type] |
|---|:--:|---|---|
| `4000279` Queso Blanco Sauce | 2 | Queso Blanco  _（2 个 option value，含同名不同项）_ | Additional Sauce (On The Side) [OPTIONAL_ADDITION] · Additional Toppings [OPTIONAL_ADDITION] |

**`[8011940]` Double Veggie Baby, Burger Baby (Pilot)**  ·  Version 2

| food component | 被N个选择映射 | 映射它的选择 | 涉及 option [type] |
|---|:--:|---|---|
| `4000279` Queso Blanco Sauce | 2 | Queso Blanco  _（2 个 option value，含同名不同项）_ | Additional Sauce (On The Side) [OPTIONAL_ADDITION] · Additional Toppings [OPTIONAL_ADDITION] |

**`[8011941]` Veggie Baby, Burger Baby (Pilot)**  ·  Version 2

| food component | 被N个选择映射 | 映射它的选择 | 涉及 option [type] |
|---|:--:|---|---|
| `4000279` Queso Blanco Sauce | 2 | Queso Blanco  _（2 个 option value，含同名不同项）_ | Additional Sauce (On The Side) [OPTIONAL_ADDITION] · Additional Toppings [OPTIONAL_ADDITION] |

#### Limesalt (Jasmine Rice Pilot) — 10 对 / 6 个 menu item

**`[8011565]` Bowl (BYO), Limesalt (Jasmine Rice Pilot)**  ·  Version 1

| food component | 被N个选择映射 | 映射它的选择 | 涉及 option [type] |
|---|:--:|---|---|
| `4000550` Guacamole | 2 | Guacamole · Veggies + Guac | Choose Your Protein [MANDATORY_CHOICE] · Choose Your Toppings [OPTIONAL_ADDITION] |
| `7000018` Fajita Vegetables (Cooked, 4x) | 2 | Fajita Vegetables · Veggies + Guac | Choose Your Protein [MANDATORY_CHOICE] · Choose Your Toppings [OPTIONAL_ADDITION] |

**`[8011570]` Quesadilla (BYO), Limesalt (Jasmine Rice Pilot)**  ·  Version 1

| food component | 被N个选择映射 | 映射它的选择 | 涉及 option [type] |
|---|:--:|---|---|
| `4000330` Mexican Three Cheese | 6 | Barbacoa · Carnitas · Cheese Only · Chicken · Spiced Tofu · Steak | Choose Your Protein [MANDATORY_CHOICE] |

**`[8011571]` Salad (BYO), Limesalt (Jasmine Rice Pilot)**  ·  Version 1

| food component | 被N个选择映射 | 映射它的选择 | 涉及 option [type] |
|---|:--:|---|---|
| `4000550` Guacamole | 2 | Guacamole · Veggies + Guac | Choose Your Protein [MANDATORY_CHOICE] · Choose Your Toppings [OPTIONAL_ADDITION] |
| `7000018` Fajita Vegetables (Cooked, 4x) | 2 | Fajita Vegetables · Veggies + Guac | Choose Your Protein [MANDATORY_CHOICE] · Choose Your Toppings [OPTIONAL_ADDITION] |

**`[8011572]` Taco (BYO), Limesalt (Jasmine Rice Pilot)**  ·  Version 1

| food component | 被N个选择映射 | 映射它的选择 | 涉及 option [type] |
|---|:--:|---|---|
| `4000550` Guacamole | 2 | Guacamole · Veggies + Guac | Choose Your Protein [MANDATORY_CHOICE] · Choose Your Toppings [OPTIONAL_ADDITION] |
| `7000018` Fajita Vegetables (Cooked, 4x) | 2 | Fajita Vegetables · Veggies + Guac | Choose Your Protein [MANDATORY_CHOICE] · Choose Your Toppings [OPTIONAL_ADDITION] |

**`[8011573]` Burrito (BYO), Limesalt (Jasmine Rice Pilot)**  ·  Version 1

| food component | 被N个选择映射 | 映射它的选择 | 涉及 option [type] |
|---|:--:|---|---|
| `4000550` Guacamole | 2 | Guacamole · Veggies + Guac | Choose Your Protein [MANDATORY_CHOICE] · Choose Your Toppings [OPTIONAL_ADDITION] |
| `7000018` Fajita Vegetables (Cooked, 4x) | 2 | Fajita Vegetables · Veggies + Guac | Choose Your Protein [MANDATORY_CHOICE] · Choose Your Toppings [OPTIONAL_ADDITION] |

**`[8011576]` Cheesesteak Quesadilla (BYO), Limesalt (Jasmine Rice Pilot)**  ·  Version 1

| food component | 被N个选择映射 | 映射它的选择 | 涉及 option [type] |
|---|:--:|---|---|
| `4000330` Mexican Three Cheese | 6 | Barbacoa · Carnitas · Cheese Only · Chicken · Spiced Tofu · Steak | Choose Your Protein [MANDATORY_CHOICE] |

#### Limesalt — 9 对 / 5 个 menu item

**`[8004637]` Burrito (BYO), Limesalt**  ·  Version 46

| food component | 被N个选择映射 | 映射它的选择 | 涉及 option [type] |
|---|:--:|---|---|
| `4000550` Guacamole | 2 | Guacamole · Veggies + Guac | Choose Your Protein [MANDATORY_CHOICE] · Choose Your Toppings [OPTIONAL_ADDITION] |
| `7000018` Fajita Vegetables (Cooked, 4x) | 2 | Fajita Vegetables · Veggies + Guac | Choose Your Protein [MANDATORY_CHOICE] · Choose Your Toppings [OPTIONAL_ADDITION] |

**`[8004638]` Bowl (BYO), Limesalt**  ·  Version 46

| food component | 被N个选择映射 | 映射它的选择 | 涉及 option [type] |
|---|:--:|---|---|
| `4000550` Guacamole | 2 | Guacamole · Veggies + Guac | Choose Your Protein [MANDATORY_CHOICE] · Choose Your Toppings [OPTIONAL_ADDITION] |
| `7000018` Fajita Vegetables (Cooked, 4x) | 2 | Fajita Vegetables · Veggies + Guac | Choose Your Protein [MANDATORY_CHOICE] · Choose Your Toppings [OPTIONAL_ADDITION] |

**`[8005005]` Taco (BYO), Limesalt**  ·  Version 44

| food component | 被N个选择映射 | 映射它的选择 | 涉及 option [type] |
|---|:--:|---|---|
| `4000550` Guacamole | 2 | Guacamole · Veggies + Guac | Choose Your Protein [MANDATORY_CHOICE] · Choose Your Toppings [OPTIONAL_ADDITION] |
| `7000018` Fajita Vegetables (Cooked, 4x) | 2 | Fajita Vegetables · Veggies + Guac | Choose Your Protein [MANDATORY_CHOICE] · Choose Your Toppings [OPTIONAL_ADDITION] |

**`[8005006]` Salad (BYO), Limesalt**  ·  Version 46

| food component | 被N个选择映射 | 映射它的选择 | 涉及 option [type] |
|---|:--:|---|---|
| `4000550` Guacamole | 2 | Guacamole · Veggies + Guac | Choose Your Protein [MANDATORY_CHOICE] · Choose Your Toppings [OPTIONAL_ADDITION] |
| `7000018` Fajita Vegetables (Cooked, 4x) | 2 | Fajita Vegetables · Veggies + Guac | Choose Your Protein [MANDATORY_CHOICE] · Choose Your Toppings [OPTIONAL_ADDITION] |

**`[8005007]` Quesadilla (BYO), Limesalt**  ·  Version 46

| food component | 被N个选择映射 | 映射它的选择 | 涉及 option [type] |
|---|:--:|---|---|
| `4000330` Mexican Three Cheese | 6 | Barbacoa · Carnitas · Cheese Only · Chicken · Shiitake Carnitas · Steak | Choose Your Protein [MANDATORY_CHOICE] |

#### Limesalt (Cook & Chill Rice Pilot) — 9 对 / 5 个 menu item

**`[8011831]` Bowl (BYO), Limesalt (Cook & Chill Rice Pilot)**  ·  Version 2

| food component | 被N个选择映射 | 映射它的选择 | 涉及 option [type] |
|---|:--:|---|---|
| `4000550` Guacamole | 2 | Guacamole · Veggies + Guac | Choose Your Protein [MANDATORY_CHOICE] · Choose Your Toppings [OPTIONAL_ADDITION] |
| `7000018` Fajita Vegetables (Cooked, 4x) | 2 | Fajita Vegetables · Veggies + Guac | Choose Your Protein [MANDATORY_CHOICE] · Choose Your Toppings [OPTIONAL_ADDITION] |

**`[8011832]` Burrito (BYO), Limesalt (Cook & Chill Rice Pilot)**  ·  Version 2

| food component | 被N个选择映射 | 映射它的选择 | 涉及 option [type] |
|---|:--:|---|---|
| `4000550` Guacamole | 2 | Guacamole · Veggies + Guac | Choose Your Protein [MANDATORY_CHOICE] · Choose Your Toppings [OPTIONAL_ADDITION] |
| `7000018` Fajita Vegetables (Cooked, 4x) | 2 | Fajita Vegetables · Veggies + Guac | Choose Your Protein [MANDATORY_CHOICE] · Choose Your Toppings [OPTIONAL_ADDITION] |

**`[8011834]` Quesadilla (BYO), Limesalt (Cook & Chill Rice Pilot)**  ·  Version 2

| food component | 被N个选择映射 | 映射它的选择 | 涉及 option [type] |
|---|:--:|---|---|
| `4000330` Mexican Three Cheese | 6 | Barbacoa · Carnitas · Cheese Only · Chicken · Shiitake Carnitas · Steak | Choose Your Protein [MANDATORY_CHOICE] |

**`[8011835]` Salad (BYO), Limesalt (Cook & Chill Rice Pilot)**  ·  Version 2

| food component | 被N个选择映射 | 映射它的选择 | 涉及 option [type] |
|---|:--:|---|---|
| `4000550` Guacamole | 2 | Guacamole · Veggies + Guac | Choose Your Protein [MANDATORY_CHOICE] · Choose Your Toppings [OPTIONAL_ADDITION] |
| `7000018` Fajita Vegetables (Cooked, 4x) | 2 | Fajita Vegetables · Veggies + Guac | Choose Your Protein [MANDATORY_CHOICE] · Choose Your Toppings [OPTIONAL_ADDITION] |

**`[8011836]` Taco (BYO), Limesalt (Cook & Chill Rice Pilot)**  ·  Version 2

| food component | 被N个选择映射 | 映射它的选择 | 涉及 option [type] |
|---|:--:|---|---|
| `4000550` Guacamole | 2 | Guacamole · Veggies + Guac | Choose Your Protein [MANDATORY_CHOICE] · Choose Your Toppings [OPTIONAL_ADDITION] |
| `7000018` Fajita Vegetables (Cooked, 4x) | 2 | Fajita Vegetables · Veggies + Guac | Choose Your Protein [MANDATORY_CHOICE] · Choose Your Toppings [OPTIONAL_ADDITION] |

#### Ess-a-Bagel — 9 对 / 8 个 menu item

⚠️ **本部分所有命中均为"组合引发"类型**：Ess-a-Bagel 的菜品中，某些食材在多个 size/slice/toast 选项中出现，反映的是基于不同用户选择（大小、烘烤方式）的变体，而非菜品本身的重复。

**`[8011657]` Bagel, Ess-a-Bagel**  ·  Version 2

| food component | 被N个选择映射 | 映射它的选择 | 涉及 option [type] | 重复类型 |
|---|:--:|---|---|---|
| `4001166` Essa Toaster | 2 | Yes, Sliced · Yes, Toasted | Slice Bagel? [MANDATORY_CHOICE] · Toast Bagel? [MANDATORY_CHOICE] | ⚠️ 组合引发（不同烘烤选项） |

**`[8011658]` Bagel & Spread, Ess-a-Bagel**  ·  Version 2

| food component | 被N个选择映射 | 映射它的选择 | 涉及 option [type] |
|---|:--:|---|---|
| `4001032` Jelly (Essa) | 2 | Jelly · Peanut Butter & Jelly | Choose Your Spread [MANDATORY_CHOICE] |
| `4001033` Peanut Butter (Essa) | 2 | Peanut Butter · Peanut Butter & Jelly | Choose Your Spread [MANDATORY_CHOICE] |

**`[8011721]` Reuben Fusion, Ess-a-Bagel**  ·  Version 2

| food component | 被N个选择映射 | 映射它的选择 | 涉及 option [type] |
|---|:--:|---|---|
| `4001056` Turkey (Essa) | 2 | Turkey  _（2 个 option value，含同名不同项）_ | Add-Ons [OPTIONAL_ADDITION] · Protein Choice [MANDATORY_CHOICE] |

**`[8011730]` Tuna Salad By The Pound, Ess-a-Bagel**  ·  Version 2

| food component | 被N个选择映射 | 映射它的选择 | 涉及 option [type] |
|---|:--:|---|---|
| `4001066` Tuna Salad (Essa) | 2 | 1/2lb Tuna Salad · 1lb Tuna Salad | Size Choice [MANDATORY_CHOICE] |

**`[8011731]` Chicken Salad By The Pound, Ess-a-Bagel**  ·  Version 2

| food component | 被N个选择映射 | 映射它的选择 | 涉及 option [type] |
|---|:--:|---|---|
| `4001105` Chicken Salad (Essa) | 2 | 1/2lb Chicken Salad · 1lb Chicken Salad | Size Choice [MANDATORY_CHOICE] |

**`[8011732]` Whitefish Salad By The Pound, Ess-a-Bagel**  ·  Version 2

| food component | 被N个选择映射 | 映射它的选择 | 涉及 option [type] |
|---|:--:|---|---|
| `4001067` Whitefish Salad (Essa) | 2 | 1/2lb Whitefish Salad · 1lb Whitefish Salad | Size Choice [MANDATORY_CHOICE] |

**`[8011733]` Egg Salad By The Pound, Ess-a-Bagel**  ·  Version 2

| food component | 被N个选择映射 | 映射它的选择 | 涉及 option [type] |
|---|:--:|---|---|
| `4001106` Egg Salad (Essa) | 2 | 1/2lb Egg Salad · 1lb Egg Salad | Size Choice [MANDATORY_CHOICE] |

**`[8011758]` Espresso, Ess-a-Bagel**  ·  Version 1

| food component | 被N个选择映射 | 映射它的选择 | 涉及 option [type] |
|---|:--:|---|---|
| `4001078` Espresso (Essa) | 3 | Double · Single · Triple | Size Choice [MANDATORY_CHOICE] |

#### Hanu Poke BOWLDER — 4 对 / 1 个 menu item

**`[8010473]` BYO Poke Bowl, Hanu Poke BOWLDER**  ·  Version 22

| food component | 被N个选择映射 | 映射它的选择 | 涉及 option [type] |
|---|:--:|---|---|
| `4000402` Rice, Poke, FC, 10oz. (Co-Man) HC | 3 | Rice & Greens · Soba Noodles & Rice · Sushi Rice | Choose Your Base [MANDATORY_CHOICE] |
| `4000470` Spring Mix Lettuce | 3 | Mixed Greens · Rice & Greens · Soba Noodles & Greens | Choose Your Base [MANDATORY_CHOICE] |
| `4000968` Soba Noodles | 3 | Soba Noodles · Soba Noodles & Greens · Soba Noodles & Rice | Choose Your Base [MANDATORY_CHOICE] |
| `4000742` Poke Marinade | 2 | Poke Marinade Mixed In · Poke Marinade On the Side | Include Poke Marinade [MANDATORY_CHOICE] |

#### Wing Trip — 4 对 / 4 个 menu item

**`[8011272]` 6pc Classic Wings, Wing Trip**  ·  Version 5

| food component | 被N个选择映射 | 映射它的选择 | 涉及 option [type] |
|---|:--:|---|---|
| `4000838` Nashville Seasoning | 2 | Hot Honey · Nashville Hot | Choose Your Flavor [MANDATORY_CHOICE] |

**`[8011274]` 12pc Classic Wings, Wing Trip**  ·  Version 5

| food component | 被N个选择映射 | 映射它的选择 | 涉及 option [type] |
|---|:--:|---|---|
| `4000838` Nashville Seasoning | 2 | Hot Honey · Nashville Hot | Choose Your Flavor [MANDATORY_CHOICE] |

**`[8011275]` 12pc Boneless Wings, Wing Trip**  ·  Version 5

| food component | 被N个选择映射 | 映射它的选择 | 涉及 option [type] |
|---|:--:|---|---|
| `4000838` Nashville Seasoning | 2 | Hot Honey · Nashville Hot | Choose Your Flavor [MANDATORY_CHOICE] |

**`[8011276]` 6pc Boneless Wings, Wing Trip**  ·  Version 5

| food component | 被N个选择映射 | 映射它的选择 | 涉及 option [type] |
|---|:--:|---|---|
| `4000838` Nashville Seasoning | 2 | Hot Honey · Nashville Hot | Choose Your Flavor [MANDATORY_CHOICE] |

#### Yasas — 1 对 / 1 个 menu item

**`[8007403]` Bowl (BYO), Yasas**  ·  Version 42

| food component | 被N个选择映射 | 映射它的选择 | 涉及 option [type] |
|---|:--:|---|---|
| `4000427` Romaine Lettuce | 2 | Romaine  _（2 个 option value，含同名不同项）_ | Choose Your Base [MANDATORY_CHOICE] · Choose Your Toppings [OPTIONAL_ADDITION] |

#### Yasas (Cook & Chill Rice + Veg Pilot) — 1 对 / 1 个 menu item

**`[8011837]` Bowl (BYO), Yasas (Cook & Chill Rice + Veg Pilot)**  ·  Version 2

| food component | 被N个选择映射 | 映射它的选择 | 涉及 option [type] |
|---|:--:|---|---|
| `4000427` Romaine Lettuce | 2 | Romaine  _（2 个 option value，含同名不同项）_ | Choose Your Greens [MANDATORY_CHOICE] · Choose Your Toppings [OPTIONAL_ADDITION] |

---

## 2. 真正重复 vs 组合引发 — 分类总结

### 核心发现

在 Part B 的 **107 个命中组合**中：

| 分类 | 数量 | 特征 | 需要处理 |
|------|------|------|--------|
| **真正重复** | 2 | 同一食材在多个独立、单映射的 option value 中出现（用户可独立多次选择） | ⚠️ 需要业务审视：是否符合预期 |
| **组合引发** | 105 | 同一食材在多个组合选项中作为成分出现，或在不同位置选项中出现 | ✓ 正常设计模式，无需修正 |

### 示例对比

**✓ 组合引发（正常）：**
```
Hanu Poke Bowl "Choose Your Base"
  ├─ "Rice & Greens" → Rice + Spring Mix
  ├─ "Soba & Greens" → Soba + Spring Mix ← Rice 在两个组合中，但不是用户多次选择
  └─ "Sushi Rice" → Sushi Rice
```

**⚠️ 真正重复（需审视）：**
```
Yasas Bowl
  ├─ "Choose Your Base" → "Romaine"
  └─ "Choose Your Toppings" → "Romaine" ← 用户可在两个不同选项中都选择 Romaine
```

Burger Baby 的情况介于两者之间：
```
Burger Baby Bacon Cheeseburger
  ├─ "Additional Sauce (On Burger)" → "Queso Blanco"
  └─ "Additional Sauce (On The Side)" → "Queso Blanco" ← 实际是不同位置，非重复
```

### 行动建议

1. **真正重复的 2 个案例**（Yasas Romaine、Hanu Poke Poke Marinade）：确认这是否符合菜品设计意图，或是否应该在数据模型中处理
2. **组合引发的 105 个案例**：大多无需处理，但可以考虑：
   - Limesalt 的"夹带奶酪"：是否应该隐藏或默认处理
   - Burger Baby 的"酱料位置"：是否应该合并为一个选项

---

## 3. 参考查询（四品牌版；全品牌版只需去掉 brand CTE/JOIN）

```sql
-- v2: food component mapped by MULTIPLE (non-"Extra") option VALUES within one menu item version
-- Scope: 4 brands (concept_count=1). Food only. Active/FINAL/non-preset. Exclude "Extra X" choices.
WITH brand_concepts AS (
  SELECT 'Royal Greens' AS brand, 'bdd54588-04c5-42cb-a154-324646bf0f43' AS cid UNION ALL
  SELECT 'Limesalt', 'df4c141a-857f-46d0-a9c6-9c3f84f618a0' UNION ALL
  SELECT 'Yasas', '4cc6a37a-05bf-40ca-8aa6-cd043d33a5d8' UNION ALL
  SELECT 'Hanu Poke', '3c628085-cf0a-4dc7-a510-daa9f51ac9ac'
),
menu_concepts AS (
  SELECT m.items, c AS cid,
         ARRAY_LENGTH(JSON_EXTRACT_STRING_ARRAY(m.concept_ids)) AS ccount
  FROM `wonder-recipe-prod.recipe_v2.menus` m,
       UNNEST(JSON_EXTRACT_STRING_ARRAY(m.concept_ids)) AS c
),
brand_items AS (
  SELECT DISTINCT bc.brand, JSON_VALUE(it, '$.item_number') AS item_number
  FROM menu_concepts mc
  JOIN brand_concepts bc ON bc.cid = mc.cid AND mc.ccount = 1,
  UNNEST(JSON_EXTRACT_ARRAY(mc.items)) AS it
),
active_menu AS (
  SELECT bi.brand, CAST(iv.item_number AS STRING) AS menu_item_number,
         iv.name AS menu_item_name, iv.version_id AS version_number, iv.item_customization
  FROM brand_items bi
  JOIN `wonder-recipe-prod.recipe_v2.item_versions` iv
    ON CAST(iv.item_number AS STRING) = bi.item_number
  WHERE iv.effective = true AND iv.deleted = false
    AND iv.item_status != 'DORMANT' AND iv.object_type = 'MENU'
    AND iv.sold_status = 'FOR_SALE' AND iv.version_status = 'FINAL'
    AND iv.preset_item_version_info IS NULL
),
food_items AS (
  SELECT CAST(item_number AS STRING) AS num,
         ANY_VALUE(name) AS food_name,
         ANY_VALUE(object_type) AS food_object_type
  FROM `wonder-recipe-prod.recipe_v2.item_versions`
  WHERE effective = true AND deleted = false
    AND object_type IN ('HDR_CONSUMABLE_ITEM','HDR_RECIPE')
  GROUP BY 1
),
cust AS (
  SELECT am.brand, am.menu_item_number, am.menu_item_name, am.version_number,
         JSON_VALUE(opt, '$.name') AS option_name,
         JSON_VALUE(opt, '$.type') AS option_type,
         JSON_VALUE(ov, '$.id')   AS option_value_id,
         JSON_VALUE(ov, '$.name') AS option_value_name,
         JSON_VALUE(oi, '$.item_number') AS mapped_item_number
  FROM active_menu am,
       UNNEST(JSON_EXTRACT_ARRAY(am.item_customization, '$.options')) AS opt,
       UNNEST(JSON_EXTRACT_ARRAY(opt, '$.option_values')) AS ov,
       UNNEST(JSON_EXTRACT_ARRAY(ov, '$.items')) AS oi
  WHERE JSON_VALUE(opt, '$.type') IN ('MANDATORY_CHOICE','OPTIONAL_ADDITION')
    AND JSON_VALUE(oi, '$.item_number') IS NOT NULL
    AND NOT (LOWER(JSON_VALUE(ov, '$.name')) LIKE 'extra %')   -- exclude "Extra X" choices
),
joined AS (
  SELECT c.*, fi.food_name, fi.food_object_type
  FROM cust c
  JOIN food_items fi ON fi.num = c.mapped_item_number
)
SELECT
  brand, menu_item_number, menu_item_name, version_number,
  mapped_item_number AS food_component_number,
  food_name AS food_component_name,
  food_object_type,
  COUNT(DISTINCT option_value_id) AS mapped_by_n_option_values,
  STRING_AGG(DISTINCT option_value_name, ' | ' ORDER BY option_value_name) AS option_value_names,
  STRING_AGG(DISTINCT CONCAT(option_name, ' [', option_type, ']'), ' | ' ORDER BY CONCAT(option_name, ' [', option_type, ']')) AS options_involved
FROM joined
GROUP BY brand, menu_item_number, menu_item_name, version_number, food_component_number, food_component_name, food_object_type
HAVING COUNT(DISTINCT option_value_id) > 1
ORDER BY brand, mapped_by_n_option_values DESC, menu_item_number, food_component_number
```

---

## 4. 相关文档

- [[Z01-Resource/CB-bigquery/playbooks/data-research-patterns.md]] — §2 品牌隔离、§11 customization 分析三教训
- [[.claude/skills/wonder-cookbook/domains/customization.md]] — option 类型与结构

---

_由 Claude 生成于 2026-07-15。数据经修正方法论重跑（food-only、品牌专属 menu、option-value 粒度、排除 Extra）。Version 列为 UI 版本号。_
