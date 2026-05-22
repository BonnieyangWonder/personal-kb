---
title: Wonder Create - 7* HDR Recipe Components 在 Line Build 中的 40* 映射分析
date: 2026-05-21
updated: 2026-05-22
project: Wonder Create
tags: [cookbook, line-build, hdr-recipe, 40-model, data-research]
source: BigQuery (wonder-dw-prod-brd)
---
- [ ] 
# Wonder Create - 7* HDR Recipe Components 在 Line Build 中的 40* 映射分析

## 查询背景

查找所有 menu item（非 DORMANT、非过期、已发布版本），满足以下条件：

1. **Component 或 Customization Option** 中 mapping item 是 **7\* HDR Recipe** 项
2. **Line Build** 中有 sub step mapping 的 **40\*** 是该 7* item 的 BOM component

→ 即：Line Build 的 sub-step 直接引用了 7* 内部的 40* 子组件，跨过了 7* 抽象层。

## 查询参数

| 参数 | 值 |
|------|-----|
| **Menu Item 筛选** | `object_type=MENU`, `effective=true`, `deleted=false`, `item_status!=DORMANT`, `version_status IN (FINAL, PUBLISHED)`, 未过期 |
| **7\* 来源** | BOM component lines (`LIKE '7%'`) 或 Customization option values (`LIKE '7%'`) |
| **数据源** | `wonder-dw-prod-brd.master_data.item_versions` |
| **日期** | 2026-05-21 |

## 结果总览

| 指标 | 数值 |
|------|------|
| 匹配的 Menu Items | **14 个** |
| 总组合行数 | **25 行** |
| 涉及的 7\* Items | **8 个** |
| 涉及的 40\* Items | **7 个** |
| FOR_SALE | 21 行（11 items） |
| NOT_SOLD | 4 行（2 items） |
| 品牌 | Dabba, BRFC, Bellies |

## 涉及的 7\* HDR Recipe Items

| 7\* Item | Name | 中文名称 | 关联 Menu Items 数 | 关联 40* |
|----------|------|----------|-------------------|----------|
| 7000051 | Tandoori Chicken Thigh [Marinated, 3x] | 坦都里鸡腿 [腌制, 3x] | 6 | 4000693 (Tandoori Chicken Thigh) |
| 7000052 | Tandoori Paneer [Marinated, 3x] | 坦都里印度奶酪 [腌制, 3x] | 2 | 4000694 (Paneer (Diced)) |
| 7000062 | Chicken Tender, BRFC | 鸡柳 (BRFC) | 3 | 4000902 (Raw Chicken Tender) |
| 7000059 | Chicken Thigh, BRFC | 鸡腿肉 (BRFC) | 1 | 4000899 (Raw Chicken Thigh) |
| 7000060 | Chicken Drumstick, BRFC | 鸡锤 (BRFC) | 1 | 4000900 (Raw Chicken Drumstick) |
| 7000058 | Chicken Breast, BRFC | 鸡胸肉 (BRFC) | 1 | 4000898 (Raw Chicken Breast) |
| 7000061 | Chicken Whole Wing, BRFC | 全鸡翅 (BRFC) | 1 | 4000901 (Raw Chicken Whole Wing) |
| 7000029 | Diced Adobo Chicken Thigh [Cooked, 3x] | 阿斗波鸡腿肉丁 [熟制, 3x] | 1 | 4000319 (Adobo Marinade Sauce) |

## 详细结果

### Dabba 品牌 — TURBO_OVEN

| Menu Item | 中文名称 | Ver | Sold | 7* | LB ID | Activity | 40* | Appliance |
|-----------|----------|-----|------|----|-------|----------|-----|-----------|
| 8011293 Saag Paneer | 印度菠菜奶酪 | 4 | FOR_SALE | 7000052 Tandoori Paneer | a15607ea | COOK | 4000694 Paneer (Diced) | TURBO_OVEN |
| 8011298 Chicken Tikka Roll | 鸡肉提卡卷 | 7 | FOR_SALE | 7000051 Tandoori Chicken Thigh | d0d5e753 | COOK | 4000693 Tandoori Chicken Thigh | TURBO_OVEN |
| 8011303 Chicken Vindaloo | 鸡肉文达卢 | 4 | FOR_SALE | 7000051 Tandoori Chicken Thigh | 30eb5ce3 | COOK | 4000693 Tandoori Chicken Thigh | TURBO_OVEN |
| 8011304 Chicken Tikka Masala | 鸡肉提卡玛莎拉 | 5 | FOR_SALE | 7000051 Tandoori Chicken Thigh | f8a97aef | COOK | 4000693 Tandoori Chicken Thigh | TURBO_OVEN |
| 8011305 Butter Chicken | 黄油鸡 | 4 | FOR_SALE | 7000051 Tandoori Chicken Thigh | b891183a | COOK | 4000693 Tandoori Chicken Thigh | TURBO_OVEN |
| 8011308 Paneer Tikka Masala | 印度奶酪提卡玛莎拉 | 4 | FOR_SALE | 7000052 Tandoori Paneer | 6ad5a45e | COOK | 4000694 Paneer (Diced) | TURBO_OVEN |
| 8011674 Chicken Toastie | 鸡肉吐司 | 1 | NOT_SOLD | 7000051 Tandoori Chicken Thigh | f0a3eb5c | GARNISH | 4000693 Tandoori Chicken Thigh | — |
| 8011675 Chicken Tikka Masala Pizza | 鸡肉提卡玛莎拉披萨 | 1 | NOT_SOLD | 7000051 Tandoori Chicken Thigh | 0ccf2d81 | GARNISH | 4000693 Tandoori Chicken Thigh | — |
| 8011675 Chicken Tikka Masala Pizza | 鸡肉提卡玛莎拉披萨 | 1 | NOT_SOLD | 7000051 Tandoori Chicken Thigh | 34ba53c3 | GARNISH | 4000693 Tandoori Chicken Thigh | — |

### BRFC 品牌 — FRYER

| Menu Item | 中文名称 | Ver | Sold | 7* | LB ID | Activity | 40* | Appliance |
|-----------|----------|-----|------|----|-------|----------|-----|-----------|
| 8011487 Hot & Sweet Tender Dog | 甜辣鸡柳热狗 | 4 | FOR_SALE | 7000062 Chicken Tender, BRFC | fbcb7290 | COOK | 4000902 Raw Chicken Tender | FRYER |
| 8011510 Tender Supreme (3pc) | 至尊鸡柳 3块 | 2 | FOR_SALE | 7000062 Chicken Tender, BRFC | a0eb3814 | GARNISH | 4000902 Raw Chicken Tender | — |
| 8011510 Tender Supreme (3pc) | 至尊鸡柳 3块 | 2 | FOR_SALE | 7000062 Chicken Tender, BRFC | a58c9be9 | GARNISH | 4000902 Raw Chicken Tender | — |
| 8011511 2 Piece White (Breast+Wing) | 两块白肉 鸡胸+鸡翅 | 3 | FOR_SALE | 7000058 Chicken Breast, BRFC | 77adc5a6 | GARNISH | 4000898 Raw Chicken Breast | — |
| 8011511 2 Piece White (Breast+Wing) | 两块白肉 鸡胸+鸡翅 | 3 | FOR_SALE | 7000058 Chicken Breast, BRFC | 9a13cda2 | GARNISH | 4000898 Raw Chicken Breast | — |
| 8011511 2 Piece White (Breast+Wing) | 两块白肉 鸡胸+鸡翅 | 3 | FOR_SALE | 7000061 Chicken Whole Wing, BRFC | 77adc5a6 | GARNISH | 4000901 Raw Chicken Whole Wing | — |
| 8011511 2 Piece White (Breast+Wing) | 两块白肉 鸡胸+鸡翅 | 3 | FOR_SALE | 7000061 Chicken Whole Wing, BRFC | 9a13cda2 | GARNISH | 4000901 Raw Chicken Whole Wing | — |
| 8011512 2 Piece Dark (Thigh+Drum) | 两块深肉 鸡腿+鸡锤 | 2 | FOR_SALE | 7000059 Chicken Thigh, BRFC | 688b1d0f | COOK | 4000899 Raw Chicken Thigh | FRYER |
| 8011512 2 Piece Dark (Thigh+Drum) | 两块深肉 鸡腿+鸡锤 | 2 | FOR_SALE | 7000059 Chicken Thigh, BRFC | 688b1d0f | GARNISH | 4000899 Raw Chicken Thigh | — |
| 8011512 2 Piece Dark (Thigh+Drum) | 两块深肉 鸡腿+鸡锤 | 2 | FOR_SALE | 7000059 Chicken Thigh, BRFC | c74bb8dc | COOK | 4000899 Raw Chicken Thigh | FRYER |
| 8011512 2 Piece Dark (Thigh+Drum) | 两块深肉 鸡腿+鸡锤 | 2 | FOR_SALE | 7000059 Chicken Thigh, BRFC | c74bb8dc | GARNISH | 4000899 Raw Chicken Thigh | — |
| 8011512 2 Piece Dark (Thigh+Drum) | 两块深肉 鸡腿+鸡锤 | 2 | FOR_SALE | 7000060 Chicken Drumstick, BRFC | 688b1d0f | GARNISH | 4000900 Raw Chicken Drumstick | — |
| 8011512 2 Piece Dark (Thigh+Drum) | 两块深肉 鸡腿+鸡锤 | 2 | FOR_SALE | 7000060 Chicken Drumstick, BRFC | c74bb8dc | GARNISH | 4000900 Raw Chicken Drumstick | — |
| 8011517 Royal Tenders (12pc) | 皇家鸡柳 12块 | 2 | FOR_SALE | 7000062 Chicken Tender, BRFC | 44099426 | COOK | 4000902 Raw Chicken Tender | FRYER |
| 8011517 Royal Tenders (12pc) | 皇家鸡柳 12块 | 2 | FOR_SALE | 7000062 Chicken Tender, BRFC | 76c32d96 | COOK | 4000902 Raw Chicken Tender | FRYER |

### Bellies 品牌 — TURBO_OVEN

| Menu Item | 中文名称 | Ver | Sold | 7* | LB ID | Activity | 40* | Appliance |
|-----------|----------|-----|------|----|-------|----------|-----|-----------|
| 8011217 Kids Chicken Bowl, Bellies | 儿童鸡肉碗 | 3 | FOR_SALE | 7000029 Diced Adobo Chicken Thigh | b876ecce | COOK | 4000319 Adobo Marinade Sauce | TURBO_OVEN |

## 按 Activity × Appliance 交叉分析

| Activity | Appliance | 行数 | 解释 |
|----------|-----------|------|------|
| COOK | TURBO_OVEN | 7 | Dabba tandoori 系列 + Bellies adobo |
| COOK | FRYER | 5 | BRFC 炸鸡系列 |
| GARNISH | NULL | 13 | 组装/摆盘步骤，无需烹饪设备 |

## 中英文名称对照

### 40\* Consumable Items

| 40\* Item | English Name | 中文名称 |
|-----------|-------------|----------|
| 4000319 | Adobo Marinade Sauce | 阿斗波腌料酱 |
| 4000693 | Tandoori Chicken Thigh | 坦都里鸡腿肉 |
| 4000694 | Paneer (Diced) | 印度奶酪 (切丁) |
| 4000898 | Raw Chicken Breast | 生鸡胸肉 |
| 4000899 | Raw Chicken Thigh | 生鸡腿肉 |
| 4000900 | Raw Chicken Drumstick | 生鸡锤 |
| 4000901 | Raw Chicken Whole Wing | 生全鸡翅 |
| 4000902 | Raw Chicken Tender | 生鸡柳 |

### 7\* HDR Recipe Items

| 7\* Item | English Name | 中文名称 |
|----------|-------------|----------|
| 7000029 | Diced Adobo Chicken Thighs [Cooked, 3x] | 阿斗波鸡腿肉丁 [熟制, 3x] |
| 7000051 | Tandoori Chicken Thigh [Marinated, 3x] | 坦都里鸡腿 [腌制, 3x] |
| 7000052 | Tandoori Paneer [Marinated, 3x] | 坦都里印度奶酪 [腌制, 3x] |
| 7000058 | Chicken Breast, BRFC | 鸡胸肉 (BRFC) |
| 7000059 | Chicken Thigh, BRFC | 鸡腿肉 (BRFC) |
| 7000060 | Chicken Drumstick, BRFC | 鸡锤 (BRFC) |
| 7000061 | Chicken Whole Wing, BRFC | 全鸡翅 (BRFC) |
| 7000062 | Chicken Tender, BRFC | 鸡柳 (BRFC) |

### Menu Items (80\*)

| Menu Item | English Name | 中文名称 | Brand |
|-----------|-------------|----------|-------|
| 8011217 | Kids Chicken Bowl, Bellies | 儿童鸡肉碗 | Bellies |
| 8011293 | Saag Paneer, Dabba | 印度菠菜奶酪 | Dabba |
| 8011298 | Chicken Tikka Roll, Dabba | 鸡肉提卡卷 | Dabba |
| 8011303 | Chicken Vindaloo, Dabba | 鸡肉文达卢 | Dabba |
| 8011304 | Chicken Tikka Masala, Dabba | 鸡肉提卡玛莎拉 | Dabba |
| 8011305 | Butter Chicken, Dabba | 黄油鸡 | Dabba |
| 8011308 | Paneer Tikka Masala, Dabba | 印度奶酪提卡玛莎拉 | Dabba |
| 8011487 | Hot & Sweet Tender Dog, BRFC | 甜辣鸡柳热狗 | BRFC |
| 8011510 | Tender Supreme (3pc), BRFC | 至尊鸡柳 3块 | BRFC |
| 8011511 | 2 Piece White (Breast+Wing), BRFC | 两块白肉 鸡胸+鸡翅 | BRFC |
| 8011512 | 2 Piece Dark (Thigh+Drum), BRFC | 两块深肉 鸡腿+鸡锤 | BRFC |
| 8011517 | Royal Tenders (12pc), BRFC | 皇家鸡柳 12块 | BRFC |
| 8011674 | Chicken Toastie, Dabba | 鸡肉吐司 | Dabba |
| 8011675 | Chicken Tikka Masala Pizza, Dabba | 鸡肉提卡玛莎拉披萨 | Dabba |

## 关键发现

1. **所有 COOK 步骤都有 appliance，所有 GARNISH 步骤都没有** — 符合预期，GARNISH 无需烹饪设备。

2. **BRFC 的 2 Piece 系列最复杂**：
   - `8011511` (2 Piece White) 有 2 个 line build variant，每个同时引用 7000058 (Breast) 和 7000061 (Wing)
   - `8011512` (2 Piece Dark) 同样 2 个 variant，同时有 COOK (FRYER) 和 GARNISH 步骤，引用 7000059 (Thigh) 和 7000060 (Drumstick)

3. **7000051 (Tandoori Chicken Thigh) 是最多 menu items 使用的 7\***：被 6 个 Dabba menu items 引用。

4. **NOT_SOLD 的两个 item** (`8011674`, `8011675`) 都是 version 1 的 Dabba 新品（Pizza/Toastie），可能还在测试阶段。

5. **映射关系本质**：这些 sub-step 都直接 map 了 40\* 而非 7\*，意味着 line build 跨过了 7\* HDR Recipe 的抽象层，直接引用了 7\* 内部的 consumable 子组件。

## SQL 查询

```sql
WITH
active_menu AS (
  SELECT item_number, item_name, item_version_number, sold_status,
    bom_header, item_customization, item_line_build
  FROM wonder-dw-prod-brd.master_data.item_versions
  WHERE effective = true AND deleted = false AND item_status != 'DORMANT'
    AND object_type = 'MENU'
    AND version_status IN ('FINAL', 'PUBLISHED')
    AND (item_version_effective_end_time_utc IS NULL OR CURRENT_DATETIME() < item_version_effective_end_time_utc)
    AND item_line_build IS NOT NULL
),
menu_bom_7 AS (
  SELECT item_number, item_name, item_version_number, sold_status, item_line_build,
    JSON_VALUE(bl, '$.item_number') AS star7
  FROM active_menu, UNNEST(JSON_EXTRACT_ARRAY(bom_header, '$.bom_lines')) AS bl
  WHERE JSON_VALUE(bl, '$.item_number') LIKE '7%'
),
menu_cust_7 AS (
  SELECT item_number, item_name, item_version_number, sold_status, item_line_build,
    JSON_VALUE(ov, '$.item_number') AS star7
  FROM active_menu, UNNEST(JSON_EXTRACT_ARRAY(item_customization, '$.options')) AS o,
    UNNEST(JSON_EXTRACT_ARRAY(o, '$.option_values')) AS ov
  WHERE JSON_VALUE(ov, '$.item_number') LIKE '7%'
),
menu_7 AS (SELECT * FROM menu_bom_7 UNION DISTINCT SELECT * FROM menu_cust_7),
star7_bom AS (
  SELECT item_number AS star7, item_name AS star7_name,
    JSON_VALUE(bl, '$.item_number') AS comp40
  FROM wonder-dw-prod-brd.master_data.item_versions, UNNEST(JSON_EXTRACT_ARRAY(bom_header, '$.bom_lines')) AS bl
  WHERE effective = true AND deleted = false AND item_status != 'DORMANT'
    AND object_type = 'HDR_RECIPE' AND item_number LIKE '7%'
    AND JSON_VALUE(bl, '$.item_number') LIKE '40%'
),
item40_name AS (
  SELECT item_number, item_name
  FROM wonder-dw-prod-brd.master_data.item_versions
  WHERE effective = true AND deleted = false AND item_status != 'DORMANT'
    AND item_number LIKE '40%'
  QUALIFY ROW_NUMBER() OVER (PARTITION BY item_number ORDER BY item_version_number DESC) = 1
),
lb_substeps AS (
  SELECT m7.item_number, m7.item_name, m7.item_version_number, m7.sold_status, m7.star7,
    JSON_VALUE(lb, '$.id') AS line_build_id,
    JSON_VALUE(p, '$.activity') AS activity,
    JSON_VALUE(p, '$.title') AS step_title,
    JSON_VALUE(p, '$.appliance') AS appliance,
    JSON_VALUE(ps, '$.title') AS ps_title,
    JSON_VALUE(ps, '$.related_item_number') AS ps_related_item
  FROM menu_7 m7,
    UNNEST(JSON_EXTRACT_ARRAY(m7.item_line_build, '$.line_builds')) AS lb,
    UNNEST(JSON_EXTRACT_ARRAY(lb, '$.tasks')) AS t,
    UNNEST(JSON_EXTRACT_ARRAY(t, '$.procedures')) AS p,
    UNNEST(JSON_EXTRACT_ARRAY(p, '$.procedure_steps')) AS ps
  WHERE JSON_VALUE(ps, '$.related_item_number') LIKE '40%'
)
SELECT DISTINCT
  lbs.item_number AS menu_item_number, lbs.item_name AS menu_item_name,
  lbs.item_version_number AS version, lbs.sold_status,
  lbs.star7 AS star7_item_number, b.star7_name AS star7_item_name,
  lbs.line_build_id, lbs.activity AS activity_type,
  lbs.step_title,
  lbs.ps_title AS ingredient_step_title,
  lbs.ps_related_item AS ref_40_item,
  i40.item_name AS ref_40_item_name,
  lbs.appliance
FROM lb_substeps lbs
JOIN star7_bom b ON lbs.star7 = b.star7 AND lbs.ps_related_item = b.comp40
LEFT JOIN item40_name i40 ON lbs.ps_related_item = i40.item_number
ORDER BY menu_item_number, star7_item_number, line_build_id;
```
