# Line Build Multi-Version & Multi-Usage Toggles Analysis

**目的**：评估 Cookbook Line Build 中 **"Is Multi-usage qty Item"** 和 **"Multi versions vs options"** 两个 toggle 是否可以下线，改用常规（单条）line build 配置替代。

**数据来源**：`secure-recipe-prod.recipe_v2.item_line_builds` / `item_versions` / `effective_items`，essential filter 统一为 `deleted=false AND item_status!='DORMANT' AND effective=true`（对比案例除外，见第三节）。

**范围**：全菜单当前 `sold_status IN ('FOR_SALE','SCHEDULED')`、`version_status IN ('FINAL','SCHEDULED')`、非preset的menu item中，两个toggle各自=true的全部item（Is Multi-usage 4个，Multi versions 12个）。

---

## 结论摘要

| 功能                                     | 结论         | 依据                                                                                                                                   |
| -------------------------------------- | ---------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| **Multi versions vs options**（12个item） | **可以整体去掉** | 8个"熟度"item：常规单条line build + step级`mapping_option`已被证实能表达同样的cook time/step数量差异（有已发布过的真实case）。4个"芝士"item：3个分支line build内容逐字段完全相同，本就冗余。 |
| **Is Multi-usage qty Item**（4个item）    | **不能整体去掉** | 2个Di Fara披萨item：topping用量按选中总数分级（8oz→6oz→4oz），是聚合/计数逻辑，常规配置和Task都表达不了。2个Smash Burger item：2个档位内容完全相同，属于冗余配置，这2个可以去掉。                 |

---

## 最终建议

1. **Multi versions vs options**：12个item全部建议下线该toggle，统一迁移为"1条line build + 多个step在同一序号下按option value分流"（技术可行性验证见第三节3.4）。
2. **Is Multi-usage qty Item**：
   - 8011482 / 8011483（Smash Burger）：直接关闭toggle，退回常规单line build。
   - 8006447 / 8010990（Di Fara Pizza）：保留能力，但建议长期用BOM/recipe层的"数量随选中数变化的公式字段"取代目前"手工配N条line build×餐厅覆盖"的方式，从数据模型上根治，而不是简单回退到常规单line build（常规配置解决不了这个聚合逻辑）。
3. 建议在全菜单范围（不止这16个item）按"绑定的option类型是否为MANDATORY_CHOICE/DISH_PREFERENCE + 各分支cook_time/appliance/step数量是否相同"这个规则做一次全量筛查，识别出所有类似"芝士case"的冗余配置，评估下线两个toggle后的实际收益面。

---

## 一、Multi versions vs options — 详细数据

### 1.1 12个item绑定的option / customization type / option value

| Item Number | 名称 | Option Name | Customization Type | Option Values |
|---|---|---|---|---|
| 8005708 | Sirloin 10 oz, The Mainstay | Choose Your Temperature | `DISH_PREFERENCE` | Rare / Medium Rare / Medium / Medium Well / Well Done |
| 8006910 | Spice Rubbed Filet Mignon, BF 3.0 | Choose Your Temperature | `DISH_PREFERENCE` | Rare / Medium Rare / Medium / Medium Well / Well Done |
| 8006911 | Spice Rubbed NY Strip, BF 3.0 | Choose Your Temperature | `DISH_PREFERENCE` | Rare / Medium Rare / Medium / Medium Well / Well Done |
| 8006912 | Spice Rubbed Ribeye, BF 3.0 | Choose Your Temperature | `DISH_PREFERENCE` | Rare / Medium Rare / Medium / Medium Well / Well Done |
| 8007958 | Steak Pepperonata, Alanza | Choose Your Temperature | `DISH_PREFERENCE` | Rare / Medium Rare / Medium / Medium Well / Well Done |
| 8008463 | NY Strip 12oz, The Mainstay | Choose Your Temperature | `DISH_PREFERENCE` | Rare / Medium Rare / Medium / Medium Well / Well Done |
| 8009920 | Sirloin for Steak Frites, The Mainstay | Choose Your Temperature | `DISH_PREFERENCE` | Rare / Medium Rare / Medium / Medium Well / Well Done |
| 8011706 | Steak with Arugula Salad, Alanza | Choose Your Temperature | `DISH_PREFERENCE` | Rare / Medium Rare / Medium / Medium Well / Well Done |
| 8011526 | Double KBBQ Beef Burger, Korean LTO | Choose Your Cheese | `MANDATORY_CHOICE` | American Cheese / No Cheese / Sharp Cheddar Cheese |
| 8011820 | Double KBBQ Beef Burger, Korean LTO (Pilot) | Choose Your Cheese | `MANDATORY_CHOICE` | American Cheese / No Cheese / Sharp Cheddar Cheese |
| 8011821 | Single KBBQ Beef Burger, Korean LTO (Pilot) | Choose Your Cheese | `MANDATORY_CHOICE` | American Cheese / No Cheese / Sharp Cheddar Cheese |
| 8011822 | Single KBBQ Beef Burger, Korean LTO | Choose Your Cheese | `MANDATORY_CHOICE` | American Cheese / No Cheese / Sharp Cheddar Cheese |

### 1.2 Line Build 逐值数据 — "Choose Your Temperature" 组（8个item，真实需求）

每个 option value 对应一条独立 line build，`step_count` = 该line build的procedure step数量，`cook_steps_summary` = `活动/设备/时长` 的去重列表：

| Item | Option Value | Step Count | Cook Steps Summary（activity/appliance/time） |
|---|---|---|---|
| 8005708 | Rare | 4 | COOK/TURBO_OVEN/03:00; COOK/WATER_BATH/03:00; GARNISH; COMPLETE |
| 8005708 | Medium Rare | 4 | COOK/TURBO_OVEN/04:00; COOK/WATER_BATH/03:00; GARNISH; COMPLETE |
| 8005708 | Medium | 4 | COOK/TURBO_OVEN/05:00; COOK/WATER_BATH/03:00; GARNISH; COMPLETE |
| 8005708 | Medium Well | 5 | COOK/TURBO_OVEN/05:00; COOK/WATER_BATH/03:00; COOK/WATER_BATH/05:00; GARNISH; COMPLETE |
| 8005708 | Well Done | 5 | COOK/TURBO_OVEN/06:00; COOK/WATER_BATH/03:00; COOK/WATER_BATH/08:00; GARNISH; COMPLETE |
| 8006910 | Rare | 6 | COOK/MICROWAVE/01:00; COOK/TURBO_OVEN/05:00; GARNISH; VEND; COMPLETE |
| 8006910 | Medium Rare | 6 | COOK/MICROWAVE/01:00; COOK/TURBO_OVEN/06:00; GARNISH; VEND; COMPLETE |
| 8006910 | Medium | 6 | COOK/MICROWAVE/01:00; COOK/TURBO_OVEN/07:00; VEND; COMPLETE; GARNISH |
| 8006910 | Medium Well | 7 | COOK/MICROWAVE/01:00; COOK/WATER_BATH/08:00; COOK/TURBO_OVEN/08:00; GARNISH; VEND; COMPLETE |
| 8006910 | Well Done | 7 | COOK/MICROWAVE/01:00; COOK/WATER_BATH/10:00; COOK/TURBO_OVEN/08:00; GARNISH; VEND; COMPLETE |
| 8006911 | Rare | 6 | COOK/MICROWAVE/01:00; COOK/TURBO_OVEN/04:00; GARNISH; VEND; COMPLETE |
| 8006911 | Medium Rare | 6 | COOK/MICROWAVE/01:00; COOK/TURBO_OVEN/05:00; GARNISH; VEND; COMPLETE |
| 8006911 | Medium | 6 | COOK/MICROWAVE/01:00; COOK/TURBO_OVEN/06:00; GARNISH; VEND; COMPLETE |
| 8006911 | Medium Well | 7 | COOK/MICROWAVE/01:00; COOK/WATER_BATH/06:00; COOK/TURBO_OVEN/06:00; GARNISH; VEND; COMPLETE |
| 8006911 | Well Done | 7 | COOK/MICROWAVE/01:00; COOK/WATER_BATH/10:00; COOK/TURBO_OVEN/06:00; GARNISH; VEND; COMPLETE |
| 8006912 | Rare | 6 | COOK/MICROWAVE/01:00; COOK/TURBO_OVEN/04:00; GARNISH; VEND; COMPLETE |
| 8006912 | Medium Rare | 6 | COOK/MICROWAVE/01:00; COOK/TURBO_OVEN/05:00; GARNISH; VEND; COMPLETE |
| 8006912 | Medium | 6 | COOK/MICROWAVE/01:00; COOK/TURBO_OVEN/06:00; GARNISH; VEND; COMPLETE |
| 8006912 | Medium Well | 7 | COOK/MICROWAVE/01:00; COOK/WATER_BATH/06:00; COOK/TURBO_OVEN/06:00; GARNISH; VEND; COMPLETE |
| 8006912 | Well Done | 7 | COOK/MICROWAVE/01:00; COOK/WATER_BATH/10:00; COOK/TURBO_OVEN/06:00; GARNISH; VEND; COMPLETE |
| 8007958 | Rare | 4 | COOK/TURBO_OVEN/03:00; COOK/WATER_BATH/05:00; GARNISH; COMPLETE |
| 8007958 | Medium Rare | 4 | COOK/TURBO_OVEN/04:00; COOK/WATER_BATH/05:00; GARNISH; COMPLETE |
| 8007958 | Medium | 4 | COOK/TURBO_OVEN/05:00; COOK/WATER_BATH/05:00; GARNISH; COMPLETE |
| 8007958 | Medium Well | 5 | COOK/TURBO_OVEN/05:00; COOK/WATER_BATH/05:00; COOK/WATER_BATH/05:00; GARNISH; COMPLETE |
| 8007958 | Well Done | 5 | COOK/TURBO_OVEN/06:00; COOK/WATER_BATH/05:00; COOK/WATER_BATH/08:00; GARNISH; COMPLETE |
| 8008463 | Rare | 4 | COOK/TURBO_OVEN/03:00; COOK/WATER_BATH/03:00; GARNISH; COMPLETE |
| 8008463 | Medium Rare | 4 | COOK/TURBO_OVEN/04:00; COOK/WATER_BATH/03:00; GARNISH; COMPLETE |
| 8008463 | Medium | 4 | COOK/TURBO_OVEN/05:00; COOK/WATER_BATH/03:00; GARNISH; COMPLETE |
| 8008463 | Medium Well | 5 | COOK/TURBO_OVEN/05:00; COOK/WATER_BATH/03:00; COOK/WATER_BATH/05:00; GARNISH; COMPLETE |
| 8008463 | Well Done | 5 | COOK/TURBO_OVEN/06:00; COOK/WATER_BATH/03:00; COOK/WATER_BATH/08:00; GARNISH; COMPLETE |
| 8009920 | Rare | 3 | COOK/TURBO_OVEN/03:00; GARNISH; COMPLETE |
| 8009920 | Medium Rare | 3 | COOK/TURBO_OVEN/04:00; GARNISH; COMPLETE |
| 8009920 | Medium | 3 | COOK/TURBO_OVEN/05:00; GARNISH; COMPLETE |
| 8009920 | Medium Well | 4 | COOK/TURBO_OVEN/05:00; COOK/WATER_BATH/05:00; GARNISH; COMPLETE |
| 8009920 | Well Done | 4 | COOK/TURBO_OVEN/06:00; COOK/WATER_BATH/08:00; GARNISH; COMPLETE |
| 8011706 | Rare | 3 | COOK/TURBO_OVEN/03:00; GARNISH; COMPLETE |
| 8011706 | Medium Rare | 3 | COOK/TURBO_OVEN/04:00; GARNISH; COMPLETE |
| 8011706 | Medium | 3 | COOK/TURBO_OVEN/05:00; GARNISH; COMPLETE |
| 8011706 | Medium Well | 4 | COOK/TURBO_OVEN/05:00; COOK/WATER_BATH/05:00; GARNISH; COMPLETE |
| 8011706 | Well Done | 4 | COOK/TURBO_OVEN/06:00; COOK/WATER_BATH/08:00; GARNISH; COMPLETE |

**规律**：所有8个item一致——cook time随熟度递增，Medium Well/Well Done比Rare/Medium Rare/Medium多1个水浴预煮/复煮step（`step_count`+1），温度越高水浴时间也越长。这是**同一块肉的procedure本身在变**，不是另外做的独立部件。

### 1.3 Line Build 逐值数据 — "Choose Your Cheese" 组（4个item，冗余配置）

| Item | Option Value | Step Count | Cook Steps Summary |
|---|---|---|---|
| 8011526 | American Cheese | 17 | COOK/TURBO_OVEN/01:00; COOK/TURBO_OVEN/02:30; GARNISH; VEND; COMPLETE |
| 8011526 | No Cheese | 17 | COOK/TURBO_OVEN/01:00; COOK/TURBO_OVEN/02:30; GARNISH; VEND; COMPLETE |
| 8011526 | Sharp Cheddar Cheese | 17 | COOK/TURBO_OVEN/01:00; COOK/TURBO_OVEN/02:30; GARNISH; VEND; COMPLETE |
| 8011820 | American Cheese | 17 | COOK/TURBO_OVEN/01:00; COOK/CLAMSHELL/00:43; GARNISH; VEND; COMPLETE |
| 8011820 | No Cheese | 17 | COOK/TURBO_OVEN/01:00; COOK/CLAMSHELL/00:43; GARNISH; VEND; COMPLETE |
| 8011820 | Sharp Cheddar Cheese | 17 | COOK/TURBO_OVEN/01:00; COOK/CLAMSHELL/00:43; GARNISH; VEND; COMPLETE |
| 8011821 | American Cheese | 17 | COOK/TURBO_OVEN/01:00; COOK/CLAMSHELL/00:43; GARNISH; VEND; COMPLETE |
| 8011821 | No Cheese | 17 | COOK/TURBO_OVEN/01:00; COOK/CLAMSHELL/00:43; GARNISH; VEND; COMPLETE |
| 8011821 | Sharp Cheddar Cheese | 17 | COOK/TURBO_OVEN/01:00; COOK/CLAMSHELL/00:43; GARNISH; VEND; COMPLETE |
| 8011822 | American Cheese | 17 | COOK/TURBO_OVEN/01:00; COOK/TURBO_OVEN/02:30; GARNISH; VEND; COMPLETE |
| 8011822 | No Cheese | 17 | COOK/TURBO_OVEN/01:00; COOK/TURBO_OVEN/02:30; GARNISH; VEND; COMPLETE |
| 8011822 | Sharp Cheddar Cheese | 17 | COOK/TURBO_OVEN/01:00; COOK/TURBO_OVEN/02:30; GARNISH; VEND; COMPLETE |

**规律**：4个item、每个item的3个cheese分支，`step_count`和`cook_steps_summary`逐字段完全一致——3条line build唯一的差异是某个sub-step里"Sliced Cheddar"/"Sliced American"这一行文字（或No Cheese时不出现这行）。实测明细见8011822案例：

```
American Cheese分支 step1 sub-step: "POST: (1 ea) Sliced American - each Patty"
Sharp Cheddar分支  step1 sub-step: "POST: (1 ea) Sliced Cheddar - each Patty"
No Cheese分支      step1: 无对应sub-step（跳过这一行）
```

这跟同一批item自己常规line build里已经在用的"Special Sauce"/"Bun"（`(4pt) Special Sauce - each Bun` vs `No Special Sauce`；`-BOTTOM BUN-` vs `No Bun`）是同一种sub-step级互斥映射，无需为此另开一整条line build。

### 1.4 反证：系统里已有"常规line build + step级mapping_option"实现同款熟度分支的真实case

以下4个item **未开启** Multi versions toggle（`is_multiple_version=false`），但在**同一条line build里**用step级`mapping_option`绑定"Choose Your Temperature"，同样做到了cook time和step数量随熟度变化：

| Item | 名称 | version_status | line_build_status | 现状 |
|---|---|---|---|---|
| 8000755 | Grilled Tuna Steak, BF | FINAL | LINE_BUILD_CREATED | DORMANT（品牌已停) |
| 8000882 | Spiced Ribeye, Maydan | FINAL | PENDING_UPDATE(与本模式无关的其他警告) | DORMANT |
| 8001565 | Filet Mignon w/ Salad, Mullen | FINAL | LINE_BUILD_CREATED | DORMANT |
| 8001885 | Simply Grilled NY Strip, Symon | FINAL | LINE_BUILD_CREATED | DORMANT |

以8000882为例（同一条line build内部）：

| Step Order | Appliance | Rare | Medium Rare | Medium | Medium Well | Well |
|---|---|---|---|---|---|---|
| 2 | WATER_BATH | *(无此step)* | *(无此step)* | *(无此step)* | 06:00 | 10:00 |
| 4 | TURBO_OVEN | 02:00 | 02:30 | 03:00 | 03:00 | 03:00 |
| 5 | TURBO_OVEN | 02:00 | 02:30 | 03:00 | 03:00 | 03:00 |

`version_status=FINAL`、3/4个`line_build_status=LINE_BUILD_CREATED`（通过全部校验），证明这个配法**技术上完全可行、且真实发布过**——现在DORMANT是因为Maydan/Mullen/Symon这些品牌概念下线了，跟配置方式本身无关。**这直接证明"Choose Your Temperature"这8个item当初选择Multi Version toggle并非技术必需**，只是配置者选择了CDT里更直接的那条路径。

---

## 二、Is Multi-usage qty Item — 详细数据

### 2.1 4个item绑定的option / customization type

| Item Number | 名称 | Option Name | Customization Type | 档位含义 |
|---|---|---|---|---|
| 8006447 | Regular Round Pizza (BYO), Di Fara 3.0 | Choose Your Toppings | `OPTIONAL_ADDITION` | `apply_option_value_amount_from` = 已选topping总数的起始档位 |
| 8010990 | Regular Round Pizza (BYO), Di Fara 3.0 (Pilot) | Choose Your Toppings | `OPTIONAL_ADDITION` | 同上 |
| 8011482 | Single Smash Burger, BRFC | Addition | `OPTIONAL_ADDITION` | 同上（按已选加料数分档，档位0/1） |
| 8011483 | Double Smash Burger, BRFC | Addition | `OPTIONAL_ADDITION` | 同上 |

Di Fara披萨"Choose Your Toppings"当前可选值（`item_customization`里现行的7个）：Crumbled Sausage / Kalamata Olives / Meatballs / Mushrooms / Pepperoni / Peppers / Red Onions。

> 注：line build里还发现了 Broccoli Rabe、Sweet Sausage 两个topping的用量sub-step，但这两个值**已不在当前customization option的选项列表里**——是历史遗留的line build配置未随选项调整同步清理，属于额外发现的数据质量问题，不是本次分析的核心结论,但可作为后续清理的线索。

### 2.2 Di Fara Pizza（8006447）—— topping用量按选中总数分级的原始数据

取每个档位下同一topping的sub-step文本（已去重/标准化oz数）：

| Topping | 档位0(基准/0个) | 档位1(选1个) | 档位2(选2个) | 档位3(选3个+) |
|---|---|---|---|---|
| Pepperoni | 3oz | 8oz（或30片） | 6oz（或25片） | 4oz（或18片） |
| Mushrooms | 6oz | 8oz | 6oz | 4oz |
| Crumbled Sausage | — | 8oz | 6oz | 4oz |
| Kalamata Olives | — | 8oz | 6oz | 4oz |
| Red Onions | 4oz | 8oz | 6oz | 3-4oz |
| Bell Peppers(Peppers) | — | 8oz/4oz | 6oz/4oz | 3-4oz |
| Broccoli Rabe* | — | 8oz | 6oz | 4oz |
| Meatballs | 6oz | 6-8oz | 6oz | 4oz |
| Sweet Sausage* | 3oz | 8oz/20个 | 6oz/18个 | 3-4oz/18个 |

（*Broccoli Rabe / Sweet Sausage 为line build里的历史遗留值，见2.1注释）

**规律**：同一个topping，选择的topping总数越多，单个topping的用量越少——这是"这个topping自己的量，取决于顾客总共选了几个topping"的聚合逻辑，不是"选了A就做A"的单值分支，常规的per-option-value的task/step映射无法表达（无法让某个topping的step知道同一订单里还选了几个别的topping）。18个line build里只有3-4个是真正的用量档位，其余是餐厅专属覆盖的重复拷贝（不同`restaurant_id`），不是这个功能本身需要那么多档。

### 2.3 Smash Burger（8011482/8011483）—— 冗余配置的实测证据

`apply_option_value_amount_from`档位0 vs 档位1，逐step比对：

| Step | 内容 | 档位0 | 档位1 |
|---|---|---|---|
| 1（GARNISH） | Toast Bun | TOAST: Burger Bun / Martin's Roll | 完全相同 |
| 2（GARNISH） | 包材 | Small Foil - Small Clamshell | 完全相同 |
| 3（GARNISH） | Special Sauce | (4pt) Special Sauce - each Bun / No Special Sauce | 完全相同 |
| 4（GARNISH） | Bun/Pickles/Lettuce/Tomato/Addition | Bottom Bun, (3ea)Pickles, Shredded Lettuce, (1ea)Slice Tomato, Pickled Peppers/(2ea)Bacon | 完全相同 |
| 5-6（COOK） | Patty | CLAMSHELL 00:43, -SINGLE AMERICAN-/-SINGLE PLAIN-, (1ea)Burger Patty, POST:(3 Shakes)Salt | 完全相同 |
| 7（COMPLETE） | Place in Bag | 完全相同 | 完全相同 |

两个档位除了内部line build ID不同外，**没有发现任何用量、appliance、cook time上的差异**——这2个item开启这个toggle没有实际起作用,退回单条常规line build结果完全一致。

---

## 附录A：引用的产品文档

- [[Z01-Resource/CB-full-feature/Line Build/Multi usage Configuration.md]] — Is Multi-usage qty Item 原始需求
- [[Z01-Resource/CB-full-feature/Line Build/Different Option Values.md]] — Multi versions vs options 原始需求
- [[Z01-Resource/CB-full-feature/Line Build/Line Build Page.md]] — Line Build 校验规则、两个toggle互斥关系
- [[Z01-Resource/CB-bigquery/tables/secure-recipe-prod/recipe_v2/item_line_builds.md]] — 表结构
- [[Z01-Resource/CB-bigquery/playbooks/line-build.md]] — 查询方法论

## 附录B：核心SQL

```sql
-- 找出is_multiple_usage/is_multiple_version=true的当前menu item(含FOR_SALE+SCHEDULED)
SELECT DISTINCT
  iv.item_number, iv.name, iv.item_status, iv.version_status, iv.sold_status, iv.effective
FROM `secure-recipe-prod.recipe_v2.item_line_builds` ilb
JOIN `secure-recipe-prod.recipe_v2.item_versions` iv
  ON ilb.item_version_id = iv._id
WHERE ilb.is_multiple_usage = true        -- 或 ilb.is_multiple_version = true
  AND iv.deleted = false
  AND iv.item_status != 'DORMANT'
  AND iv.object_type = 'MENU'
  AND iv.sold_status IN ('FOR_SALE', 'SCHEDULED')
  AND iv.version_status IN ('FINAL', 'SCHEDULED')
  AND iv.preset_item_version_info IS NULL
ORDER BY iv.item_number;

-- 解析option/option value的人类可读名称（customization type）
SELECT
  iv.item_number,
  JSON_VALUE(opt, "$.id") AS option_id,
  JSON_VALUE(opt, "$.name") AS option_name,
  JSON_VALUE(opt, "$.type") AS option_type,
  JSON_VALUE(opt_val, "$.id") AS option_value_id,
  JSON_VALUE(opt_val, "$.name") AS option_value_name
FROM `secure-recipe-prod.recipe_v2.item_versions` iv,
  UNNEST(JSON_EXTRACT_ARRAY(iv.item_customization, "$.options")) AS opt,
  UNNEST(JSON_EXTRACT_ARRAY(opt, "$.option_values")) AS opt_val
WHERE iv.deleted = false AND iv.effective = true;

-- 验证"同line build、同step_order、不同option value、cook_time是否不同"（regular line build是否已支持该模式）
SELECT ilb.item_number, ilb.line_build_id, ilb.procedures_step_order,
  ilb.procedures_option_value_name, ilb.procedures_appliance, ilb.cooking_time,
  COUNT(DISTINCT ilb.cooking_time) OVER (PARTITION BY ilb.line_build_id, ilb.procedures_step_order) AS distinct_cooktime_at_same_step
FROM `secure-recipe-prod.recipe_v2.item_line_builds` ilb
JOIN `secure-recipe-prod.recipe_v2.item_versions` iv ON ilb.item_version_id = iv._id
WHERE ilb.is_multiple_version = false
  AND ilb.procedures_option_name = "Choose Your Temperature"
  AND ilb.procedures_activity = "COOK"
  AND iv.deleted = false AND iv.effective = true AND iv.object_type = "MENU";
```

---

*生成时间：2026-08-07 | 数据来源：secure-recipe-prod.recipe_v2 | 分析人：Bonnie + Claudian*
