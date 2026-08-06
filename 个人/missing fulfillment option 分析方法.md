---
type: methodology
status: reviewed
created: 2026-08-06
updated: 2026-08-06
tags:
  - cookbook
  - 40-model
  - fulfillment-option
  - wsku
  - data-analysis
  - 个人
---

# missing fulfillment option 分析方法

> 分析一批 Cookbook 40\* item（HDR Consumable Item），判断"背后是否有可用 fulfillment option"，排除掉表面异常、实际业务上正常的噪音，找出真正需要跟进的数据缺口。首次实践于 2026-08-06，对象是 83 个 Ess-a-Bagel / Happy Tuna 相关 40 item，逐轮和 Bonnie 对齐规则后收敛。对应 skill：[[.claude/skills/my-workflows/check-40-item-fulfillment.md]]。

## 适用场景

- 批量检查一组 40 item 是否有可用的库存履约（fulfillment）配置
- 常见触发：SCC cutover 迁移排查、40/40F frozen-thawed 补齐核查、品牌共享组件的数据健康检查

## 背景知识

- **40 Model**：40\* = HDR Consumable Item（消费端表示），41\* = 传统 WSKU（订货端表示，legacy），42\*/W42\* = SCC 迁移后的新 WSKU。一个 40 可以链接多个 41/42，同一时刻只有一个 "active for ordering"。
- **40F 冷冻态命名规则**：冷冻态 40 item = thawed 版本编号 + "F" 后缀（如 4001125 ↔ 4001125F）。**不是所有 40 都需要 40F**——纯常温/冷藏零售品天然没有冷冻态，属正常，不是数据缺失。
- **SCC cutover 状态**：`wonder_sku_items.scc_source` 标记该 WSKU 是否已迁移到 SCC。`scc_source=true` 且有 42\* item = 已 cutover；`scc_source=NULL` 且只有 41\* item = 未 cutover，仍走 legacy 通道。
- **Concept ≠ Brand**：40/menu item 上的 `concept_ids` 存的是"概念/门店陈列"标识（如 "Wonder Café"），要通过 `concepts.brand_ids` 再解析一层才是真正的商业品牌（如 "Grab & Go"）——两者不能直接用名字字符串比较。

## 判定逻辑（决策树）

```
40 item
 │
 ├─ Step 1【品牌判断】
 │   1. 取 40 item 自己的 concept_ids（已经是从 menu item 继承汇总的字段，一般不需要再下钻到具体 menu item）
 │   2. 每个 concept_id → concepts.brand_ids → dim_restaurant_brands.restaurant_brand_name，解析成品牌名集合
 │   3. 特例豁免：若品牌集合同时含 Ess-a-Bagel 和 Grab & Go（即 concept_ids 同时有 Ess-a-Bagel + Wonder Café），
 │      按 Ess-a-Bagel 处理（Bonnie 业务侧既定豁免——Wonder Café 只是共享转售渠道，不是独立运营品牌）
 │   4. 处理后品牌集合 ⊆ 允许名单（默认 {Happy Tuna, Ess-a-Bagel}）？
 │       ├─ 是 → ✅ 正常，忽略
 │       └─ 否 → 进入 Step 2
 │
 └─ Step 2【Fulfillment 可用性判断】（下列 4 条命中任意 1 条即正常）
     ①  有对应 40F，且 40F 名下 ≥1 个"可用"的 42 item
     ②  40 本身（thawed）名下 ≥1 个"可用"的 42 item
     ③  该 40 未 cutover 到 SCC（scc_source=NULL 且查无 42 item），但有 ≥1 个"可用"的 41 item
     ④  以上都不满足 → 🚩 异常，需要跟进（例如建 ticket 要求 SCC/CDT 补配 fulfillment option）
```

**"可用"的精确定义**（41/42 通用）：
- `wonder_sku_items.deleted = false` 且 `item_status != 'DORMANT'`
- 且关联的 `wonder_sku_to_fulfillment_options.deleted = false` 且 `status = 'ACTIVE'`（该字段另外两个取值 `INACTIVE_BY_USER` / `INACTIVE_BY_SYSTEM` 都不算可用）

**关键提醒**：判断"40 名下有哪些 42/41"时，务必用 `consumable_item_number` 去数据库里查**全部**关联记录，不要只信任外部给的单一映射——同一个 40（或 40F）可能挂多个 42/41，有的 dormant、有的不是，只看外部给的那一条容易漏判（把已经 dormant/无效的当成唯一真相，或者漏掉真正在用的那条）。

## 数据源 & 关键字段

| 数据 | 表 | 关键字段 |
|---|---|---|
| 40 item 基本信息、状态 | `secure-recipe-prod.recipe_v2.item_versions` / `effective_items` | `item_number`, `name`, `item_state`(THAWED/FROZEN), `item_status`, `deleted`, `effective` |
| 40 item 的 concept | 同上 | `concept_ids`（JSON 数组，系统计算，继承自 menu item） |
| concept → brand | `wonder-recipe-prod.recipe_v2.concepts` | `_id`, `name`, `brand_ids`（JSON 数组） |
| brand_id → brand 名 | `wonder-dw-prod-brd.dw.dim_restaurant_brands` | `restaurant_brand_id`, `restaurant_brand_name`, `archived` |
| 40 item 实际被哪些 menu item 消费（BOM 路径，仅在需要下钻时用）| `secure-recipe-prod.recipe_v2.item_versions.bom_header`（嵌套 JSON）| `UNNEST(JSON_EXTRACT_ARRAY(bom_header,'$.bom_lines'))` → `$.item_number` |
| 40 item 被哪些 menu item 当作 customization 选项 | `secure-recipe-prod.recipe_v2.item_versions.item_customization`（嵌套 JSON，**不要用** `item_customizations_flattened`，会笛卡尔积）| `options[].option_values[].items[].item_number` |
| 40/40F 名下的 41\*/42\* WSKU | `wonder-raw-prod.mysql_batch_product_catalog.wonder_sku_items` | `item_number`, `consumable_item_number`(关联 40), `item_status`, `deleted`, `scc_source` |
| WSKU 是否有 fulfillment option | `wonder-raw-prod.mysql_batch_product_catalog.wonder_sku_to_fulfillment_options` | `wonder_sku_item_number`, `fulfillment_option_id`, `status`(ACTIVE/INACTIVE_BY_USER/INACTIVE_BY_SYSTEM), `deleted` |

## SQL 查询范式

### 1. 40 item → concept_ids → brand 名（Step 1，批量）

```sql
WITH item_list AS (
  SELECT item40 FROM UNNEST(['40011XX', '40012XX']) AS item40
),
base AS (
  SELECT il.item40, iv.name, iv.concept_ids
  FROM item_list il
  LEFT JOIN `secure-recipe-prod.recipe_v2.item_versions` iv
    ON iv.item_number = il.item40 AND iv.effective = true AND iv.deleted = false
)
SELECT
  b.item40, b.name,
  STRING_AGG(DISTINCT brd.restaurant_brand_name, ', ') AS brands
FROM base b
LEFT JOIN UNNEST(JSON_EXTRACT_ARRAY(b.concept_ids)) AS cid
LEFT JOIN `wonder-recipe-prod.recipe_v2.concepts` c ON c._id = TRIM(cid, '"')
LEFT JOIN UNNEST(JSON_EXTRACT_ARRAY(c.brand_ids)) AS bid
LEFT JOIN `wonder-dw-prod-brd.dw.dim_restaurant_brands` brd ON brd.restaurant_brand_id = TRIM(bid, '"')
GROUP BY b.item40, b.name;
```

拿到 `brands` 后套用"Ess-a-Bagel + Grab & Go 同时出现 → 按 Ess-a-Bagel"豁免，再判断剩余集合是否 ⊆ 允许名单。

### 2. 40F 是否存在

```sql
SELECT il.item40, CONCAT(il.item40,'F') AS item40F,
       ei.item_number IS NOT NULL AS f_exists, ei.item_status AS f_status
FROM item_list il
LEFT JOIN `secure-recipe-prod.recipe_v2.effective_items` ei
  ON ei.item_number = CONCAT(il.item40, 'F') AND ei.deleted = false;
```

### 3. 40/40F 名下全部 42（或 41）item 及 fulfillment 状态（Step 2，务必用 consumable_item_number 反查全集）

```sql
SELECT
  s.consumable_item_number AS parent_40,
  s.item_number AS wsku,
  s.item_status,
  s.scc_source,
  fo.status AS fulfillment_status
FROM `wonder-raw-prod.mysql_batch_product_catalog.wonder_sku_items` s
LEFT JOIN `wonder-raw-prod.mysql_batch_product_catalog.wonder_sku_to_fulfillment_options` fo
  ON fo.wonder_sku_item_number = s.item_number AND fo.deleted = false
WHERE s.consumable_item_number IN ('40011XX', '40011XXF')  -- thawed + frozen 都要查
  AND s.deleted = false
ORDER BY parent_40, item_status, wsku;
```

拿到结果后按"可用"定义（见上）过滤，判断每个 parent_40 名下是否 ≥1 条可用。

### 4.（较少用）下钻到具体 menu item 的 concept——仅在怀疑 item 级汇总的 concept_ids 掩盖了"单独出现"情况时才需要

```sql
-- BOM 路径
SELECT DISTINCT JSON_VALUE(bom_line,'$.item_number') AS component_40,
       m.item_number AS parent_item_number, m.concept_ids AS parent_concept_ids
FROM `secure-recipe-prod.recipe_v2.item_versions` m,
UNNEST(JSON_EXTRACT_ARRAY(m.bom_header, '$.bom_lines')) AS bom_line
WHERE m.effective = true AND m.deleted = false
  AND JSON_VALUE(bom_line, '$.item_number') IN ('40011XX');

-- customization 路径（优先用嵌套 JSON，不要用 flattened 表）
SELECT DISTINCT JSON_VALUE(opt_item, '$.item_number') AS component_40,
       iv.item_number AS parent_item_number, iv.concept_ids AS parent_concept_ids,
       iv.sold_status, iv.version_status
FROM `secure-recipe-prod.recipe_v2.item_versions` iv,
  UNNEST(JSON_EXTRACT_ARRAY(iv.item_customization, '$.options')) AS opt,
  UNNEST(JSON_EXTRACT_ARRAY(opt, '$.option_values')) AS opt_val,
  UNNEST(JSON_EXTRACT_ARRAY(opt_val, '$.items')) AS opt_item
WHERE iv.effective = true AND iv.deleted = false
  AND JSON_VALUE(opt_item, '$.item_number') IN ('40011XX');
```

## 关键方法论坑点

1. **Concept ≠ Brand**：不能直接拿 concept 名字去和品牌白名单做字符串匹配，必须经过 `concepts.brand_ids → dim_restaurant_brands` 解析。
2. **不要只信任外部给的单一"40→42"映射**：同一个 40（或 40F）名下可能挂多个 42/41，必须用 `consumable_item_number` 反查全集，且要看 `item_status`（排除 DORMANT）和 fulfillment `status`（只有 ACTIVE 算数，INACTIVE_BY_USER/INACTIVE_BY_SYSTEM 都不算）。
3. **判断"是否已 cutover 到 SCC"看 `scc_source` 字段，不能只看"有没有 42 item"**——已 cutover 但 42 没配 fulfillment、旧 41 又都 dormant 了的情况，不适用"未 cutover→看 41 兜底"这条规则，只能算真异常。
4. **customization 查询用 `item_customization` 嵌套 JSON 直接 UNNEST，不要用 `item_customizations_flattened` 表**——后者对 option-value 级别分析会产生笛卡尔积（详见 [[Z01-Resource/CB-bigquery/playbooks/data-research-patterns.md]]）。
5. **BigQuery billing project 选择**：`secure-recipe-prod` / `wonder-recipe-prod` / `wonder-raw-prod` / `wonder-dw-prod-brd` 各自用自己的 project 做 billing project 来查询即可跨库 JOIN，不需要额外配置。

## 参数化配置（每次分析可能要调整的地方）

| 参数 | 当前取值 | 说明 |
|---|---|---|
| 允许品牌名单 | `{Happy Tuna, Ess-a-Bagel}` | 相对固定，Bonnie 需要时会指定调整 |
| Concept 豁免映射 | `Wonder Café(concept) → Grab & Go(brand)`，与 Ess-a-Bagel 同时出现时豁免 | 目前唯一已知的豁免案例，未来遇到新的类似情况需要重新和 Bonnie 确认 |

## 案例参考：2026-08-06 分析（83 个 Ess-a-Bagel/Happy Tuna 相关 40 item）

- 61 个仅 Ess-a-Bagel(+Wonder Café) 使用 → Step 1 正常
- 21 个被其他品牌使用但有 40F → 其中 18 个 40F 的 42 有可用 fulfillment（Step 2① 正常），3 个初判缺口
- 3 个初判缺口复核后：2 个（4000557 Barbacoa、4000683 Flame Roasted Corn Kernels）未 cutover 到 SCC 但 41 有可用 fulfillment（Step 2③ 正常救回）；1 个（4000280 Sesame General Sauce）本身 thawed 侧还有一个非 dormant 的 42（4200397）有可用 fulfillment（Step 2② 正常救回）
- **最终异常：仅 1 个 —— 4000667 Fried Chicken**（已 cutover 到 SCC，唯一的 42 无 fulfillment，仅有的 2 个 41 备用项均已 dormant，无路可用）
