# WC — BYO Customization Configuration Consistency 分析

**项目**: WC (Wonder Create)
**品牌范围**: Royal Greens、Limesalt、Yasas、Hanu Poke
**分析对象**: 设置了 Max Options 的 customization，在 `custom_type`、`max_choices`、`min_choices`、`free_choices` 四个维度上，主 menu item 与其 preset menu item 的配置是否一致
**数据源**: `wonder-recipe-prod.recipe_v2`（`item_versions` / `menus` / `concepts`）

## 0. 方法论与过滤条件

### 0.1 "现在 menu item"（忽略 dormant / expired / draft）的过滤条件

数据库里没有字面的 "EXPIRED" 状态字段，`item_status` 只有 `ACTIVE` / `DORMANT` / `R&D`，`version_status` 只有 `FINAL` / `SCHEDULED` / `DRAFT`。按 Cookbook 数据模型的标准口径，"忽略 dormant / expired / draft" 对应：

| 用户口径 | 对应过滤条件 |
|---|---|
| 忽略 dormant | `item_status != 'DORMANT'` |
| 忽略 expired（已被新版本取代的历史版本） | `effective = true`（`item_versions` 保留全部历史版本，`effective=true` 只保留当前生效版本） |
| 忽略 draft | `version_status = 'FINAL'` |
| （额外补充）"现在"在售 | `sold_status = 'FOR_SALE'` |

同时叠加 `deleted = false`、`object_type = 'MENU'`。

### 0.2 品牌 → Menu Item 关联方式

按 playbook 强制要求，**不使用** `concept_ids LIKE '%id%'` 做品牌关联（会导致共享 menu 跨品牌污染）。改为：找到 `concept_ids` 数组长度为 1（品牌专属）且状态为 `ACTIVE` 的 menu，取其 `items[]` 列表：

| 品牌 | 品牌专属 ACTIVE Menu | Menu 内 item 数 |
|---|---|---|
| Royal Greens | Bowlder Menu；Royal Greens Super Salad Station [ACTIVE] 01.06.2025 | 247 |
| Yasas | Yasas [ACTIVE] 2.19.2024 | 41 |
| Hanu Poke | Hanu Poke [ACTIVE] 1.10.2025 | 16 |
| Limesalt | Limesalt [ACTIVE] 2.19.2024 | 34 |

去重后共 **240** 个 distinct item_number。

**⚠️ 数据说明（Hanu Poke）**：Hanu Poke 专属 menu 里只有 2 个 item（Edamame 8007334、8008070），customization 很少。但实际的 Hanu Poke BYO Poke Bowl（item 8010473，名称为 "BYO Poke Bowl, **Hanu Poke** BOWLDER"）被挂在 **Royal Greens** 的 "Bowlder Menu"（该 menu `concept_ids` 只含 Royal Greens 一个 concept）下，属于共享的 "Bowlder" 建模平台。按本报告的品牌判定方法（menu 的 concept 归属），8010473 被计入 Royal Greens；但从命名看它实际服务于 Hanu Poke 品类。本报告在下方数据中如实按 menu 归属标注为 Royal Greens，并在此处单独标注这个特例，供参考判断。

### 0.3 Customization 字段口径

`item_customization` JSON 里，"Max options" 对应字段是 `options[].max_choices`（不是文档里旧命名的 `max_options`）。经检查，**134 个（当前有效/非 dormant/FINAL/FOR_SALE）menu item 拥有 customization**，其中共 889 个 customization option，仅 25 个 `max_choices` 为空 —— 即 **864 个 option（97%）设置了 Max options**。

**⚠️ 关键纠偏**：这 134 个 item 里，有 **108 个本身就是 preset item**（自己也被直接挂载在 menu 的 items[] 列表里作为可单独下单的商品，例如 "Greek Salad, Royal Greens PRESET"）。若不剔除，会把 preset 错当成"主 menu item"重复计入。剔除后，**真正的主 menu item（`preset_item_version_info IS NULL`）只有 26 个**，其中 **16 个**至少有 1 个 customization 设置了 Max options。

---

## 1. 主 Menu Item 的 Customization + Max Options 数据（16 个主 item，共 71 条 customization 记录）

| Brand | Menu Item (item_number) | Customization (Option) | Type | Custom Type | Min | Max | Free Choices |
|---|---|---|---|---|---|---|---|
| Limesalt | Burrito (BYO), Limesalt (8004637) | Add Extra Protein | MANDATORY_CHOICE | SINGLE_SELECT | 1 | 1 | — |
| Limesalt | Burrito (BYO), Limesalt (8004637) | Choose Your Beans | MANDATORY_CHOICE | SINGLE_SELECT | 1 | 1 | — |
| Limesalt | Burrito (BYO), Limesalt (8004637) | Choose Your Protein | MANDATORY_CHOICE | SINGLE_SELECT | 1 | 1 | — |
| Limesalt | Burrito (BYO), Limesalt (8004637) | Choose Your Rice | MANDATORY_CHOICE | SINGLE_SELECT | 1 | 1 | — |
| Limesalt | Burrito (BYO), Limesalt (8004637) | Choose Your Toppings | OPTIONAL_ADDITION | MULTI_SELECT | 0 | 10 | — |
| Limesalt | Bowl (BYO), Limesalt (8004638) | Add Extra Protein | MANDATORY_CHOICE | SINGLE_SELECT | 1 | 1 | — |
| Limesalt | Bowl (BYO), Limesalt (8004638) | Choose Your Beans | MANDATORY_CHOICE | SINGLE_SELECT | 1 | 1 | — |
| Limesalt | Bowl (BYO), Limesalt (8004638) | Choose Your Protein | MANDATORY_CHOICE | SINGLE_SELECT | 1 | 1 | — |
| Limesalt | Bowl (BYO), Limesalt (8004638) | Choose Your Rice | MANDATORY_CHOICE | SINGLE_SELECT | 1 | 1 | — |
| Limesalt | Bowl (BYO), Limesalt (8004638) | Choose Your Toppings | OPTIONAL_ADDITION | MULTI_SELECT | 0 | 10 | — |
| Limesalt | Taco (BYO), Limesalt (8005005) | Choose Your Protein | MANDATORY_CHOICE | SINGLE_SELECT | 1 | 1 | — |
| Limesalt | Taco (BYO), Limesalt (8005005) | Choose Your Toppings | OPTIONAL_ADDITION | MULTI_SELECT | 0 | 5 | — |
| Limesalt | Taco (BYO), Limesalt (8005005) | Choose Your Tortilla | MANDATORY_CHOICE | SINGLE_SELECT | 1 | 1 | — |
| Limesalt | Salad (BYO), Limesalt (8005006) | Add Extra Protein | MANDATORY_CHOICE | SINGLE_SELECT | 1 | 1 | — |
| Limesalt | Salad (BYO), Limesalt (8005006) | Choose Your Beans | MANDATORY_CHOICE | SINGLE_SELECT | 1 | 1 | — |
| Limesalt | Salad (BYO), Limesalt (8005006) | Choose Your Dressing | MANDATORY_CHOICE | SINGLE_SELECT | 1 | 1 | — |
| Limesalt | Salad (BYO), Limesalt (8005006) | Choose Your Protein | MANDATORY_CHOICE | SINGLE_SELECT | 1 | 1 | — |
| Limesalt | Salad (BYO), Limesalt (8005006) | Choose Your Rice | MANDATORY_CHOICE | SINGLE_SELECT | 1 | 1 | — |
| Limesalt | Salad (BYO), Limesalt (8005006) | Choose Your Toppings | OPTIONAL_ADDITION | MULTI_SELECT | 0 | 10 | — |
| Limesalt | Quesadilla (BYO), Limesalt (8005007) | Choose Your Protein | MANDATORY_CHOICE | SINGLE_SELECT | 1 | 1 | — |
| Limesalt | Quesadilla (BYO), Limesalt (8005007) | Choose Your Sides | OPTIONAL_ADDITION | MULTI_SELECT | 0 | 3 | — |
| Royal Greens | Crispy Leaf & Feta Salad, The Mainstay (8000326) | Dressing (Served on Side) | MANDATORY_CHOICE | MULTI_SELECT | 1 | 2 | — |
| Royal Greens | Antipasto Salad, Di Fara 3.0 (8006372) | Dressing (Served on Side) | MANDATORY_CHOICE | MULTI_SELECT | 1 | 2 | — |
| Royal Greens | Chopped Salad, BF 3.0 (8006900) | Dressing (Served on Side) | MANDATORY_CHOICE | MULTI_SELECT | 1 | 2 | — |
| Royal Greens | Kale, Citrus & Blue Cheese Salad, BF (8009278) | Dressing (Served on Side) | MANDATORY_CHOICE | MULTI_SELECT | 1 | 2 | — |
| Royal Greens | BYO Greens Bowl, Royal Greens BOWLDER- Primary ID (8010459) | 2 Dressings (Served on Side) | MANDATORY_CHOICE | MULTI_SELECT | 2 | 2 | — |
| Royal Greens | BYO Greens Bowl, Royal Greens BOWLDER- Primary ID (8010459) | Base | MANDATORY_CHOICE | PARTIAL_SELECT | 1 | 1 | — |
| Royal Greens | BYO Greens Bowl, Royal Greens BOWLDER- Primary ID (8010459) | Cheese | OPTIONAL_ADDITION | MULTI_SELECT | 0 | 2 | — |
| Royal Greens | BYO Greens Bowl, Royal Greens BOWLDER- Primary ID (8010459) | Crunchy Toppings | OPTIONAL_ADDITION | MULTI_SELECT | 0 | 3 | — |
| Royal Greens | BYO Greens Bowl, Royal Greens BOWLDER- Primary ID (8010459) | Premium Toppings | OPTIONAL_ADDITION | MULTI_SELECT | 0 | 8 | — |
| Royal Greens | BYO Greens Bowl, Royal Greens BOWLDER- Primary ID (8010459) | Protein (Served Chilled) | MANDATORY_CHOICE | MULTI_SELECT | 1 | 2 | — |
| Royal Greens | BYO Greens Bowl, Royal Greens BOWLDER- Primary ID (8010459) | Side of Pita | MANDATORY_CHOICE | SINGLE_SELECT | 1 | 1 | — |
| Royal Greens | BYO Greens Bowl, Royal Greens BOWLDER- Primary ID (8010459) | Toppings | OPTIONAL_ADDITION | MULTI_SELECT | 0 | 6 | — |
| Royal Greens | BYO Poke Bowl, Hanu Poke BOWLDER (8010473) | Choose Your Base | MANDATORY_CHOICE | SINGLE_SELECT | 1 | 1 | — |
| Royal Greens | BYO Poke Bowl, Hanu Poke BOWLDER (8010473) | Choose Your Protein | MANDATORY_CHOICE | PARTIAL_SELECT | 1 | 1 | — |
| Royal Greens | BYO Poke Bowl, Hanu Poke BOWLDER (8010473) | Choose Your Sauce | MANDATORY_CHOICE | SINGLE_SELECT | 1 | 1 | — |
| Royal Greens | BYO Poke Bowl, Hanu Poke BOWLDER (8010473) | Crunchy Toppings | OPTIONAL_ADDITION | MULTI_SELECT | 0 | 3 | — |
| Royal Greens | BYO Poke Bowl, Hanu Poke BOWLDER (8010473) | Extra Sauce | OPTIONAL_ADDITION | SINGLE_SELECT | 0 | 1 | — |
| Royal Greens | BYO Poke Bowl, Hanu Poke BOWLDER (8010473) | Include Poke Marinade | MANDATORY_CHOICE | SINGLE_SELECT | 1 | 1 | — |
| Royal Greens | BYO Poke Bowl, Hanu Poke BOWLDER (8010473) | Vegetable Toppings | OPTIONAL_ADDITION | MULTI_SELECT | 0 | 8 | — |
| Royal Greens | BYO Greens Bowl, Royal Greens BOWLDER- Abridged Rail ID (8010492) | 2 Dressings (Served on Side) | MANDATORY_CHOICE | MULTI_SELECT | 2 | 2 | — |
| Royal Greens | BYO Greens Bowl, Royal Greens BOWLDER- Abridged Rail ID (8010492) | Base | MANDATORY_CHOICE | PARTIAL_SELECT | 1 | 1 | — |
| Royal Greens | BYO Greens Bowl, Royal Greens BOWLDER- Abridged Rail ID (8010492) | Cheese | OPTIONAL_ADDITION | MULTI_SELECT | 0 | 2 | — |
| Royal Greens | BYO Greens Bowl, Royal Greens BOWLDER- Abridged Rail ID (8010492) | Crunchy Toppings | OPTIONAL_ADDITION | MULTI_SELECT | 0 | 3 | — |
| Royal Greens | BYO Greens Bowl, Royal Greens BOWLDER- Abridged Rail ID (8010492) | Premium Toppings | OPTIONAL_ADDITION | MULTI_SELECT | 0 | 6 | — |
| Royal Greens | BYO Greens Bowl, Royal Greens BOWLDER- Abridged Rail ID (8010492) | Protein (Served Chilled) | MANDATORY_CHOICE | MULTI_SELECT | 1 | 2 | — |
| Royal Greens | BYO Greens Bowl, Royal Greens BOWLDER- Abridged Rail ID (8010492) | Side of Pita | MANDATORY_CHOICE | SINGLE_SELECT | 1 | 1 | — |
| Royal Greens | BYO Greens Bowl, Royal Greens BOWLDER- Abridged Rail ID (8010492) | Toppings | OPTIONAL_ADDITION | MULTI_SELECT | 0 | 6 | — |
| Royal Greens | BYO Greens Bowl, Royal Greens BOWLDER - Primary ID (C&C Pilot) (8011814) | 2 Dressings (Served on Side) | MANDATORY_CHOICE | MULTI_SELECT | 2 | 2 | — |
| Royal Greens | BYO Greens Bowl, Royal Greens BOWLDER - Primary ID (C&C Pilot) (8011814) | Base | MANDATORY_CHOICE | PARTIAL_SELECT | 1 | 1 | — |
| Royal Greens | BYO Greens Bowl, Royal Greens BOWLDER - Primary ID (C&C Pilot) (8011814) | Cheese | OPTIONAL_ADDITION | MULTI_SELECT | 0 | 2 | — |
| Royal Greens | BYO Greens Bowl, Royal Greens BOWLDER - Primary ID (C&C Pilot) (8011814) | Crunchy Toppings | OPTIONAL_ADDITION | MULTI_SELECT | 0 | 3 | — |
| Royal Greens | BYO Greens Bowl, Royal Greens BOWLDER - Primary ID (C&C Pilot) (8011814) | Premium Toppings | OPTIONAL_ADDITION | MULTI_SELECT | 0 | 8 | — |
| Royal Greens | BYO Greens Bowl, Royal Greens BOWLDER - Primary ID (C&C Pilot) (8011814) | Protein (Served Chilled) | MANDATORY_CHOICE | MULTI_SELECT | 1 | 2 | — |
| Royal Greens | BYO Greens Bowl, Royal Greens BOWLDER - Primary ID (C&C Pilot) (8011814) | Side of Pita | MANDATORY_CHOICE | SINGLE_SELECT | 1 | 1 | — |
| Royal Greens | BYO Greens Bowl, Royal Greens BOWLDER - Primary ID (C&C Pilot) (8011814) | Toppings | OPTIONAL_ADDITION | MULTI_SELECT | 0 | 6 | — |
| Yasas | Wrap (BYO), Yasas (8007402) | Add Extra Dressing | OPTIONAL_ADDITION | None | 0 | 1 | — |
| Yasas | Wrap (BYO), Yasas (8007402) | Choose Your Main | MANDATORY_CHOICE | MULTI_SELECT | 1 | 2 | — |
| Yasas | Wrap (BYO), Yasas (8007402) | Choose Your Spreads | OPTIONAL_ADDITION | MULTI_SELECT | 0 | 3 | — |
| Yasas | Wrap (BYO), Yasas (8007402) | Choose Your Toppings | OPTIONAL_ADDITION | MULTI_SELECT | 0 | 5 | — |
| Yasas | Bowl (BYO), Yasas (8007403) | Add Extra Dressing | OPTIONAL_ADDITION | None | 0 | 1 | — |
| Yasas | Bowl (BYO), Yasas (8007403) | Choose Your Base | MANDATORY_CHOICE | PARTIAL_SELECT | 1 | 1 | — |
| Yasas | Bowl (BYO), Yasas (8007403) | Choose Your Main | MANDATORY_CHOICE | MULTI_SELECT | 1 | 2 | — |
| Yasas | Bowl (BYO), Yasas (8007403) | Choose Your Spreads | OPTIONAL_ADDITION | MULTI_SELECT | 0 | 3 | — |
| Yasas | Bowl (BYO), Yasas (8007403) | Choose Your Toppings | OPTIONAL_ADDITION | MULTI_SELECT | 0 | 9 | — |
| Yasas | Bowl (BYO), Yasas (8007403) | Dressings (Served on Side) | MANDATORY_CHOICE | SINGLE_SELECT | 1 | 1 | — |
| Yasas | Bowl (BYO), Yasas (8007403) | Include Side of Pita | MANDATORY_CHOICE | SINGLE_SELECT | 1 | 1 | — |
| Yasas | Wrap (BYO), Yasas (C&C Pilot) (8011818) | Choose Dressing (Served on Side) | MANDATORY_CHOICE | SINGLE_SELECT | 1 | 1 | — |
| Yasas | Wrap (BYO), Yasas (C&C Pilot) (8011818) | Choose Your Main | MANDATORY_CHOICE | MULTI_SELECT | 1 | 2 | — |
| Yasas | Wrap (BYO), Yasas (C&C Pilot) (8011818) | Choose Your Spreads | OPTIONAL_ADDITION | MULTI_SELECT | 0 | 3 | — |
| Yasas | Wrap (BYO), Yasas (C&C Pilot) (8011818) | Choose Your Toppings | OPTIONAL_ADDITION | MULTI_SELECT | 0 | 5 | — |

**Free Choices**：以上 71 条记录中 `free_choices`（`freemium`）均为空（该品牌范围内主 item 层面尚未使用免费选择数量的设置）。

---

## 2. 主 Menu Item vs. 其 Preset 的设置差异分析

### 2.1 匹配方式说明

Preset 自己的 `item_versions.item_customization` 里，每个 option 的 `id` 是 preset 创建时新生成的 UUID，**与主 item 的 option id 不同**，不能直接按 `option_id` 做跨表 join。

**补充核实**：`item_versions` 表上还有一个已废弃字段 `item_customization_presets`（挂在**主 item** 记录上，非 preset 自己的记录），里面按 **主 item 自己的 option_id** 记录了每个 preset（按名称）具体选中了哪些 `option_value`。这是目前能找到的、唯一一张记录"主 item option ↔ preset"关联关系的结构。核实结果：

- 覆盖率有限：8 个 BYO 主 item 中，只有 **5 个**（8007402、8007403、8010459、8010473、8010492）该字段有数据；较新的 3 个（8004638 Limesalt Bowl、8011814 / 8011818 两个 C&C Pilot 版本）该字段为空，说明这批是在该字段停用之后创建的。
- 关联到的 option 身份（按 option_id 反查主 item 当前的 option 名称）与本报告用 **option 名称匹配**的方式**完全一致**（如 "Base"、"Toppings"、"2 Dressings (Served on Side)" 等），仅 8010473 一个 option（旧 id `701bd7c4-...`）在当前 option 集合里找不到对应项，推测是历史上被拆分/改名后留下的失效引用（该主 item 目前有 "Choose Your Sauce" + "Extra Sauce" 两个独立 option，早期可能是合并成一个）。
- **关键限制**：`item_customization_presets` 只记录了每个 preset 选中的 `option_value`（是否选中/是否 in_eligible/default_portion），**不包含** `custom_type` / `max_choices` / `min_choices` / `freemium` 这些设置本身 —— 这些设置只存在于**每个 preset 自己的** `item_versions.item_customization` 里。

**结论**：`item_customization_presets` 证实了本报告"按 option 名称匹配"的关联关系是对的（两种方法在能交叉验证的范围内 100% 一致），但它无法替代本节的差异对比——因为它不携带 Max/Min/Custom Type/Free Choices 这些数值。因此下方差异对比仍然是：**主 item 的 option（来自主 item 自己的 item_customization）× 同名的 preset option（来自 preset 自己的 item_customization）**逐项比较。Preset 数据同样过滤 `effective=true`、`deleted=false`、`item_status != DORMANT`、`version_status = FINAL`、`sold_status = FOR_SALE`。

### 2.2 覆盖范围

在 16 个"有 Max options 设置"的主 item 中，只有 **8 个是 BYO 类型、且真的有 preset**（其余 8 个是固定菜品，没有 preset 概念）：

- Limesalt: Bowl (BYO) 8004638
- Royal Greens: BYO Greens Bowl ×3 个版本（8010459 / 8010492 / 8011814），BYO Poke Bowl 8010473
- Yasas: Wrap (BYO) 8007402 / 8011818，Bowl (BYO) 8007403

这 8 个主 item 共对应 **111 个有效 preset**。

### 2.3 总体不一致占比

对每个（主 item 的 customization option × 其 preset）配对，比较 `custom_type`、`max_choices`、`min_choices`、`freemium` 四个字段：

> **总对比 804 对，其中 102 对至少有 1 个字段不一致 → 不一致占比 12.7%**

按字段拆分（一对里可能同时命中多个字段）：

| 字段 | 不一致次数（在 102 个不一致对中） |
|---|---|
| `min_choices` | 45 |
| `max_choices` | 40 |
| `custom_type` | 35 |
| `freemium` | 1 |

### 2.4 按主 Item 拆分

| Brand | 主 Menu Item | Presets 数 | 对比的 (Option×Preset) 对数 | 不一致数 | 不一致占比 |
|---|---|---|---|---|---|
| Limesalt | Bowl (BYO), Limesalt (8004638) | 8 | 40 | 0 | 0.0% |
| Royal Greens | BYO Greens Bowl, Royal Greens BOWLDER- Primary ID (8010459) | 27 | 216 | 25 | 11.6% |
| Royal Greens | BYO Poke Bowl, Hanu Poke BOWLDER (8010473) | 5 | 35 | 0 | 0.0% |
| Royal Greens | BYO Greens Bowl, Royal Greens BOWLDER- Abridged Rail ID (8010492) | 24 | 192 | 39 | 20.3% |
| Royal Greens | BYO Greens Bowl, Royal Greens BOWLDER - Primary ID (C&C Pilot) (8011814) | 25 | 200 | 1 | 0.5% |
| Yasas | Wrap (BYO), Yasas (8007402) | 8 | 32 | 14 | 43.8% |
| Yasas | Bowl (BYO), Yasas (8007403) | 11 | 77 | 20 | 26.0% |
| Yasas | Wrap (BYO), Yasas (C&C Pilot) (8011818) | 3 | 12 | 3 | 25.0% |

**观察**：
- Limesalt 的 Bowl (BYO) 及 Royal Greens 的 BYO Poke Bowl（8010473）**100% 一致**（0 处差异）——preset 完全继承主 item 设置，未做任何覆盖。
- Yasas 的两个 Wrap/Bowl BYO 差异比例最高（26%–44%），几乎所有 preset 都把 `custom_type` 从 `MULTI_SELECT`/`PARTIAL_SELECT` 改为 `SINGLE_SELECT`（因为 preset 已经预先锁定了具体的单一选项组合，不再需要多选）。
- Royal Greens 的两个 "BYO Greens Bowl" 主版本（8010459 / 8010492）有 20%+ 的差异，主要是 "2 Dressings (Served on Side)" 的 `min_choices` 从 2 降为 1（绝大多数 preset 只强制选 1 个酱料而非 2 个）。

### 2.5 差异明细（逐个主 item / customization / preset）


#### Royal Greens | BYO Greens Bowl, Royal Greens BOWLDER- Primary ID (8010459)

**2 Dressings (Served on Side)** — 主 item: custom_type=MULTI_SELECT, min=2, max=2, free=None

| Preset | 不一致字段 |
|---|---|
| Greek Salad, Royal Greens PRESET (8010664) | min_choices: 2 → 1 |
| Buffalo Salad, Royal Greens PRESET (8010872) | min_choices: 2 → 1 |
| Royal Caesar Salad, Royal Greens PRESET (8010668) | min_choices: 2 → 1 |
| Royal Roots Bowl, Royal Greens PRESET (8010669) | min_choices: 2 → 1 |
| Tostada Bowl,  Royal Greens PRESET (8010671) | min_choices: 2 → 1 |
| Marc Murphy's Crispy Leaf & Feta Salad, Royal Greens PRESET (8010672) | min_choices: 2 → 1 |
| Bobby Flay's Citrus & Blue Cheese Salad, Royal Greens PRESET (8010676) | min_choices: 2 → 1 |
| Spicy Salmon Sashimi Salad, Royal Greens PRESET (8010873) | min_choices: 2 → 1 |
| Avocado Green Goddess Salad, Royal Greens PRESET (8011534) | min_choices: 2 → 1 |
| Spicy Southwest Salad, Royal Greens PRESET (8011536) | min_choices: 2 → 1 |
| Harvest Bowl, Royal Greens PRESET (8010662) | min_choices: 2 → 1 |
| Mandarin Crunch Salad, Royal Greens PRESET (8010666) | min_choices: 2 → 1 |
| Beet & Goat Cheese Salad, Royal Greens PRESET (8010673) | min_choices: 2 → 1 |
| Crispy Rice Bowl, Royal Greens PRESET (8011533) | min_choices: 2 → 1 |
| Blue Cheese & Pecan Salad, Royal Greens PRESET (8010674) | min_choices: 2 → 1 |
| Di Fara's Antipasto Salad, Royal Greens PRESET (8010677) | min_choices: 2 → 1 |
| Maydan's Fattoush Salad, Royal Greens PRESET (8010678) | min_choices: 2 → 1 |
| Cobb Salad, Royal Greens PRESET (8010661) | min_choices: 2 → 1 |
| Pesto Parm Bowl, Royal Greens PRESET (8010663) | max_choices: 2 → 3; min_choices: 2 → 1 |
| Miso Avocado Bowl, Royal Greens PRESET (8010665) | min_choices: 2 → 1 |
| Thai Peanut Salad, Royal Greens PRESET (8010670) | min_choices: 2 → 1 |
| Strawberry Pecan Salad, Royal Greens PRESET (8010859) | min_choices: 2 → 1 |
| Avocado Green Goddess Bowl PRESET (8011535) | min_choices: 2 → 1 |
| Baked by Melissa's Sesame Soba Salad, Royal Greens PRESET (8011537) | min_choices: 2 → 1 |

**Protein (Served Chilled)** — 主 item: custom_type=MULTI_SELECT, min=1, max=2, free=None

| Preset | 不一致字段 |
|---|---|
| Marc Murphy's Crispy Leaf & Feta Salad, Royal Greens PRESET (8010672) | freemium: None → 1 |


#### Royal Greens | BYO Greens Bowl, Royal Greens BOWLDER- Abridged Rail ID (8010492)

**2 Dressings (Served on Side)** — 主 item: custom_type=MULTI_SELECT, min=2, max=2, free=None

| Preset | 不一致字段 |
|---|---|
| Greek  Salad, Royal Greens AB PRESET (8010702) | min_choices: 2 → 1 |
| Blue Cheese & Pecan Salad, Royal Greens AB PRESET (8010711) | min_choices: 2 → 1 |
| Bobby Flay's Citrus & Blue Cheese Salad, Royal Greens AB PRESET (8010713) | min_choices: 2 → 1 |
| Harvest Bowl, Royal Greens AB PRESET (8010700) | min_choices: 2 → 1 |
| Pesto Parm Bowl, Royal Greens AB PRESET (8010701) | max_choices: 2 → 3; min_choices: 2 → 1 |
| Mandarin Crunch Salad, Royal Greens AB PRESET (8010704) | min_choices: 2 → 1 |
| Strawberry Pecan Salad, Royal Greens AB PRESET (8010862) | min_choices: 2 → 1 |
| Avocado Green Goddess Bowl, Royal Greens AB PRESET (8011558) | min_choices: 2 → 1 |
| Crispy Rice Bowl, Royal Greens AB PRESET (8011560) | min_choices: 2 → 1 |
| Maydan's Fattoush Salad, Royal Greens AB PRESET (8010714) | min_choices: 2 → 1 |
| Baked by Melissa's Sesame Soba Salad, Royal Greens AB PRESET (8011559) | min_choices: 2 → 1 |
| Thai Peanut Salad, Royal Greens AB PRESET (8010708) | min_choices: 2 → 1 |
| Spicy Salmon Sashimi Salad, Royal Greens AB PRESET (8010876) | min_choices: 2 → 1 |
| Avocado Green Goddess Salad, Royal Greens AB PRESET (8011557) | min_choices: 2 → 1 |
| Cobb Salad, Royal Greens AB PRESET (8010699) | min_choices: 2 → 1 |
| Royal Caesar Salad, Royal Greens AB PRESET (8010706) | min_choices: 2 → 1 |
| Buffalo Salad, Royal Greens AB PRESET (8010875) | min_choices: 2 → 1 |
| Miso Avocado Bowl, Royal Greens AB PRESET (8010703) | min_choices: 2 → 1 |
| Royal Roots Bowl, Royal Greens AB PRESET (8010707) | min_choices: 2 → 1 |
| Marc Murphy's Crispy Leaf & Feta Salad, Royal Greens AB PRESET (8010709) | min_choices: 2 → 1 |
| Beet & Goat Cheese Salad, Royal Greens AB PRESET (8010710) | min_choices: 2 → 1 |

**Cheese** — 主 item: custom_type=MULTI_SELECT, min=0, max=2, free=None

| Preset | 不一致字段 |
|---|---|
| Maydan's Fattoush Salad, Royal Greens AB PRESET (8010714) | custom_type: MULTI_SELECT → SINGLE_SELECT |

**Crunchy Toppings** — 主 item: custom_type=MULTI_SELECT, min=0, max=3, free=None

| Preset | 不一致字段 |
|---|---|
| Greek  Salad, Royal Greens AB PRESET (8010702) | max_choices: 3 → 2 |
| Blue Cheese & Pecan Salad, Royal Greens AB PRESET (8010711) | max_choices: 3 → 2 |
| Bobby Flay's Citrus & Blue Cheese Salad, Royal Greens AB PRESET (8010713) | max_choices: 3 → 2 |
| Harvest Bowl, Royal Greens AB PRESET (8010700) | max_choices: 3 → 2 |
| Pesto Parm Bowl, Royal Greens AB PRESET (8010701) | max_choices: 3 → 2 |
| Mandarin Crunch Salad, Royal Greens AB PRESET (8010704) | max_choices: 3 → 2 |
| Strawberry Pecan Salad, Royal Greens AB PRESET (8010862) | max_choices: 3 → 2 |
| Maydan's Fattoush Salad, Royal Greens AB PRESET (8010714) | max_choices: 3 → 2 |
| Thai Peanut Salad, Royal Greens AB PRESET (8010708) | max_choices: 3 → 2 |
| Spicy Salmon Sashimi Salad, Royal Greens AB PRESET (8010876) | max_choices: 3 → 2 |
| Cobb Salad, Royal Greens AB PRESET (8010699) | max_choices: 3 → 2 |
| Royal Caesar Salad, Royal Greens AB PRESET (8010706) | max_choices: 3 → 2 |
| Buffalo Salad, Royal Greens AB PRESET (8010875) | max_choices: 3 → 2 |
| Miso Avocado Bowl, Royal Greens AB PRESET (8010703) | max_choices: 3 → 2 |
| Royal Roots Bowl, Royal Greens AB PRESET (8010707) | max_choices: 3 → 2 |
| Marc Murphy's Crispy Leaf & Feta Salad, Royal Greens AB PRESET (8010709) | max_choices: 3 → 2 |
| Beet & Goat Cheese Salad, Royal Greens AB PRESET (8010710) | max_choices: 3 → 2 |


#### Royal Greens | BYO Greens Bowl, Royal Greens BOWLDER - Primary ID (C&C Pilot) (8011814)

**2 Dressings (Served on Side)** — 主 item: custom_type=MULTI_SELECT, min=2, max=2, free=None

| Preset | 不一致字段 |
|---|---|
| Pesto Parm Bowl, Royal Greens PRESET (C&C Pilot) (8011892) | max_choices: 2 → 3 |


#### Yasas | Wrap (BYO), Yasas (8007402)

**Choose Your Main** — 主 item: custom_type=MULTI_SELECT, min=1, max=2, free=None

| Preset | 不一致字段 |
|---|---|
| Beef Souvlaki & Tzatziki Sandwich PRESET, Yasas BYO (8010687) | custom_type: MULTI_SELECT → SINGLE_SELECT; max_choices: 2 → 1 |
| Spicy Cauliflower & Avocado Sandwich PRESET, Yasas BYO (8010690) | custom_type: MULTI_SELECT → SINGLE_SELECT; max_choices: 2 → 1 |
| Spiced Sweet Potato & Kalamata Sandwich PRESET, Yasas BYO (8010689) | custom_type: MULTI_SELECT → SINGLE_SELECT; max_choices: 2 → 1 |
| Chicken Souvlaki & Avocado Sandwich PRESET, Yasas BYO (8010688) | custom_type: MULTI_SELECT → SINGLE_SELECT; max_choices: 2 → 1 |

**Choose Your Spreads** — 主 item: custom_type=MULTI_SELECT, min=0, max=3, free=None

| Preset | 不一致字段 |
|---|---|
| Beef Souvlaki & Tzatziki Sandwich PRESET, Yasas BYO (8010687) | custom_type: MULTI_SELECT → SINGLE_SELECT |
| Spicy Cauliflower & Avocado Sandwich PRESET, Yasas BYO (8010690) | custom_type: MULTI_SELECT → SINGLE_SELECT |
| Za'atar Carrots & Broccoli Wrap PRESET (8011651) | custom_type: MULTI_SELECT → SINGLE_SELECT |
| Spiced Sweet Potato & Kalamata Sandwich PRESET, Yasas BYO (8010689) | custom_type: MULTI_SELECT → SINGLE_SELECT |
| Chicken Souvlaki & Avocado Sandwich PRESET, Yasas BYO (8010688) | custom_type: MULTI_SELECT → SINGLE_SELECT |

**Choose Your Toppings** — 主 item: custom_type=MULTI_SELECT, min=0, max=5, free=None

| Preset | 不一致字段 |
|---|---|
| Beef Souvlaki & Tzatziki Sandwich PRESET, Yasas BYO (8010687) | custom_type: MULTI_SELECT → SINGLE_SELECT |
| Spicy Cauliflower & Avocado Sandwich PRESET, Yasas BYO (8010690) | custom_type: MULTI_SELECT → SINGLE_SELECT; max_choices: 5 → 4 |
| Za'atar Carrots & Broccoli Wrap PRESET (8011651) | custom_type: MULTI_SELECT → SINGLE_SELECT |
| Spiced Sweet Potato & Kalamata Sandwich PRESET, Yasas BYO (8010689) | custom_type: MULTI_SELECT → SINGLE_SELECT; max_choices: 5 → 4 |
| Chicken Souvlaki & Avocado Sandwich PRESET, Yasas BYO (8010688) | custom_type: MULTI_SELECT → SINGLE_SELECT; max_choices: 5 → 4 |


#### Yasas | Bowl (BYO), Yasas (8007403)

**Choose Your Base** — 主 item: custom_type=PARTIAL_SELECT, min=1, max=1, free=None

| Preset | 不一致字段 |
|---|---|
| Spiced Sweet Potato & Feta Salad PRESET, Yasas BYO (8010718) | custom_type: PARTIAL_SELECT → SINGLE_SELECT |
| Spicy Cauliflower & Feta Salad PRESET, Yasas BYO (8010719) | custom_type: PARTIAL_SELECT → SINGLE_SELECT |
| Zesty Chicken Souvlaki & Rice Bowl PRESET, Yasas BYO (8010720) | custom_type: PARTIAL_SELECT → SINGLE_SELECT |
| Beef Souvlaki & Kalamata Salad PRESET, Yasas BYO (8010716) | custom_type: PARTIAL_SELECT → SINGLE_SELECT |
| Cauliflower & Chickpea Grain Bowl PRESET, Yasas BYO (8010717) | custom_type: PARTIAL_SELECT → SINGLE_SELECT |

**Choose Your Main** — 主 item: custom_type=MULTI_SELECT, min=1, max=2, free=None

| Preset | 不一致字段 |
|---|---|
| Spiced Sweet Potato & Feta Salad PRESET, Yasas BYO (8010718) | custom_type: MULTI_SELECT → SINGLE_SELECT; max_choices: 2 → 1 |
| Spicy Cauliflower & Feta Salad PRESET, Yasas BYO (8010719) | custom_type: MULTI_SELECT → SINGLE_SELECT; max_choices: 2 → 1 |
| Zesty Chicken Souvlaki & Rice Bowl PRESET, Yasas BYO (8010720) | custom_type: MULTI_SELECT → SINGLE_SELECT; max_choices: 2 → 1 |
| Beef Souvlaki & Kalamata Salad PRESET, Yasas BYO (8010716) | custom_type: MULTI_SELECT → SINGLE_SELECT; max_choices: 2 → 1 |
| Cauliflower & Chickpea Grain Bowl PRESET, Yasas BYO (8010717) | custom_type: MULTI_SELECT → SINGLE_SELECT; max_choices: 2 → 1 |

**Choose Your Spreads** — 主 item: custom_type=MULTI_SELECT, min=0, max=3, free=None

| Preset | 不一致字段 |
|---|---|
| Spiced Sweet Potato & Feta Salad PRESET, Yasas BYO (8010718) | custom_type: MULTI_SELECT → SINGLE_SELECT |
| Spicy Cauliflower & Feta Salad PRESET, Yasas BYO (8010719) | custom_type: MULTI_SELECT → SINGLE_SELECT |
| Zesty Chicken Souvlaki & Rice Bowl PRESET, Yasas BYO (8010720) | custom_type: MULTI_SELECT → SINGLE_SELECT |
| Beef Souvlaki & Kalamata Salad PRESET, Yasas BYO (8010716) | custom_type: MULTI_SELECT → SINGLE_SELECT |
| Cauliflower & Chickpea Grain Bowl PRESET, Yasas BYO (8010717) | custom_type: MULTI_SELECT → SINGLE_SELECT |

**Choose Your Toppings** — 主 item: custom_type=MULTI_SELECT, min=0, max=9, free=None

| Preset | 不一致字段 |
|---|---|
| Spiced Sweet Potato & Feta Salad PRESET, Yasas BYO (8010718) | custom_type: MULTI_SELECT → SINGLE_SELECT; max_choices: 9 → 4 |
| Spicy Cauliflower & Feta Salad PRESET, Yasas BYO (8010719) | custom_type: MULTI_SELECT → SINGLE_SELECT; max_choices: 9 → 4 |
| Zesty Chicken Souvlaki & Rice Bowl PRESET, Yasas BYO (8010720) | custom_type: MULTI_SELECT → SINGLE_SELECT; max_choices: 9 → 4 |
| Beef Souvlaki & Kalamata Salad PRESET, Yasas BYO (8010716) | custom_type: MULTI_SELECT → SINGLE_SELECT; max_choices: 9 → 4 |
| Cauliflower & Chickpea Grain Bowl PRESET, Yasas BYO (8010717) | custom_type: MULTI_SELECT → SINGLE_SELECT; max_choices: 9 → 4 |


#### Yasas | Wrap (BYO), Yasas (C&C Pilot) (8011818)

**Choose Dressing (Served on Side)** — 主 item: custom_type=SINGLE_SELECT, min=1, max=1, free=None

| Preset | 不一致字段 |
|---|---|
| Za'atar Carrots & Broccoli Pita (C&C Pilot) (8011879) | max_choices: 1 → None |
| Harissa Chicken Crunch Sandwich (C&C Pilot) (8011876) | max_choices: 1 → None |
| Grilled Steak & Feta Sandwich (C&C Pilot) (8011878) | max_choices: 1 → None |


---

## 3. 数据口径与已知局限

1. `deleted` 字段在 `menus` 表中不存在（`INFORMATION_SCHEMA` 确认），品牌 menu 判定改用 `status = 'ACTIVE'` + `concept_count = 1`。
2. "Expired" 无独立字段，用 `effective = true` 近似代表"未被历史版本取代"。
3. Free Choices（`freemium`）在本品牌范围内，主 item 层面全部未设置；仅在 1 个 preset（Marc Murphy's Crispy Leaf & Feta Salad, Royal Greens PRESET）上被单独设置为 1（主 item 该项为空）。
4. 只统计了主 item 的 customization option 与"存在同名 option"的 preset 之间的差异；若 preset 引入了主 item 没有的全新 option（本次未发现此类情况），或某个 preset 缺失了主 item 里的某个 option，未计入本次对比范围。
5. Hanu Poke 的 BYO Poke Bowl（8010473）因 menu 归属被计入 Royal Greens，见 §0.2 特别说明。
6. `item_versions.item_customization_presets`（已废弃字段，挂在主 item 记录上）为 5/8 个主 item 提供了权威的 option_id 级"主 item option ↔ preset"关联记录，交叉验证了 §2.1 的按名称匹配方法；但该字段不含 `custom_type`/`max_choices`/`min_choices`/`freemium`，无法替代本报告的差异对比，详见 §2.1。
