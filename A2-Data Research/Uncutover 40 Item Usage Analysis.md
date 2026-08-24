# Uncutover 40 Item Usage Analysis

**问题**：`~/Downloads/Uncutover 40s.xlsx` 里三个批次的 40\* HDR Consumable Item（`for salescheduled 40` 11 个、`B2B 88` 42 个、`Not sold 40` 405 个，均按 item number 去重），分别被哪些 menu item 或 7\* HDR recipe item 通过 BOM 或 customization 引用？「Not sold 40」批次里如果命中的是 7\* HDR recipe item，再反查这个 HDR recipe item 本身又被谁用。

**范围**：只统计 `item_status != 'DORMANT'`（non-dormant）、`version_status != 'EXPIRED'`（非过期版本）、`preset_item_version_info IS NULL`（排除 preset item，判断标准是数据库字段而非 item name 里是否带 "preset" 字样）的 menu item / HDR recipe item 用法。

---

## 结论

1. **for sale & scheduled 40**（11 个，本身是 FOR_SALE/SCHEDULED 状态）：**全部 11 个都有有效用法**，共 61 条用法记录，落在 **30 个去重后的 menu item** 上，**0 个 HDR recipe item**。用法最集中的是 4000636（Adobo Steak，20 条：3 BOM + 17 customization）和 4000833（Spiced Tofu，18 条：1 BOM + 17 customization）。
2. **B2B 88**（42 个，B2B/Wonder Works 内部用途）：**41/42 有有效用法**，共 48 条用法记录，落在 **47 个去重后的 menu item** 上，全部走 BOM 路径，全部 `sold_status = NOT_SOLD`。**唯一没有用法的是 4001177**。其中 15 条用法来自还在 `DRAFT`/`R&D` 状态的测试品项（如 "Wonder Works EGAM"、"AREAS"、"(COPY)" 系列）——因为本次过滤条件只排除 DORMANT/EXPIRED/preset，不排除 DRAFT，所以这些草稿也算"有用法"；这一点和之前 [[40 Item SCC Cutover Status]] 报告里 B2B 段落（额外排除了 DRAFT，得到 30/42）的口径不同，见下方"与既有报告的口径差异"。
3. **Not sold 40**（405 个，数量最大的一批）：**只有 163/405（约 40%）有有效用法**，共 336 条用法记录，落在 **174 个去重后的 usage item 上（167 个 menu item + 7 个 HDR recipe item）**。**242 个（约 60%）完全查不到任何非 dormant/过期/preset 的用法**，是本批里最值得关注的清理候选（明细见下文，也写入了 Excel 的 `Not sold 40 usages` sheet便于核对，零用法的项在该 sheet 里不会出现任何行）。
4. **Not sold 40 → 7 个 HDR recipe item 的反查**：这 7 个 HDR recipe item（7000017/7000019/7000024/7000025/7000026/7000120/7000132）本身又被谁用——**6/7 有下游用法**（15 条记录，全部落在 8 个去重后的 menu item 上，**没有再出现 HDR recipe → HDR recipe 的嵌套用法**），**7000026（BBQ Brisket Burnt Ends (Cooked) Limesalt HDR）完全查不到任何用法**。命中的用法里有 10/15 条还处于 `DRAFT`/`R&D`（"BOWLDER"/"Rice Pilot" 测试品项），只有 5 条是 `FINAL`/`ACTIVE`。

---

> [!warning] ⚠️ 与既有报告的口径差异 —— 两份报告数字对不上不是错误
> vault 里已有一份 [[40 Item SCC Cutover Status]] 报告，其中"B2B 关联 40 Item"章节分析的**是同一批 `B2B 88`**（42 个，41 个重叠 + 1 个新增 4001177）。
>
> | | 本报告 | [[40 Item SCC Cutover Status]] |
> |---|---|---|
> | 过滤条件 | non-dormant + 非过期版本 + 非 preset（**不排除 DRAFT**） | non-dormant + 非过期版本 + 非 preset + **额外排除 `version_status = 'DRAFT'`** |
> | 结论 | **41 有效 / 1 无效** | **30 有效 / 12 无效** |
>
> 差别的 11 个（B2B 88 里那些还处于 `DRAFT`/`R&D` 的 "Wonder Works EGAM"/"AREAS"/"(COPY)" 测试品项）就是被"排除 DRAFT"这条额外条件筛掉的。**两份报告的原始查询结果并不矛盾**，纯粹是过滤条件不同——以后再看到这两个数字对不上，先检查是不是这个原因，不用怀疑数据本身有问题。按自己的目的（要不要把还在测试阶段的草稿品项算作"有效用法"）选用对应口径。

---

## Excel 交付物

在 `~/Downloads/Uncutover 40s.xlsx` 里新增了 4 个 sheet（原 3 个原始 sheet 保持不变）：

| Sheet | 对应源 sheet / 数据 | 行数 |
|---|---|---|
| `for sale & scheduled 40 usages` | `for salescheduled 40`（11 个 40 item） | 61 |
| `B2B 88 usages` | `B2B 88`（42 个 40 item） | 48 |
| `Not sold 40 usages` | `Not sold 40`（405 个 40 item） | 336 |
| `Not sold 40 hdr recipe usages` | 反查 `Not sold 40 usages` 里命中的 7 个 HDR recipe item | 15 |

列结构统一为：`usage item number, usage item name, 40 item number（或 hdr recipe item number）, item status, sold status, version, version status, used in BOM/customization, customization type, customization name, option name`。

---

## 详细数据

### 1. for sale & scheduled 40（11 个）

| 40 item | 名称 | 40 自身状态 | BOM 用法数 | customization 用法数 | 涉及 menu item 数 |
|---|---|---|---|---|---|
| 4000052 | Lemon Chess Pie Slice | FOR_SALE | 1 | 0 | 1 |
| 4000060 | Banana Chocolate Hazelnut Pudding, Magnolia | FOR_SALE | 1 | 0 | 1 |
| 4000374 | Pepperonata | FOR_SALE | 2 | 0 | 2 |
| 4000380 | Roasted Cauliflower | FOR_SALE | 2 | 4 | 5 |
| 4000384 | Beef Souvlaki | FOR_SALE | 1 | 6 | 5 |
| 4000636 | Adobo Steak | FOR_SALE | 3 | 17 | 13 |
| 4000642 | Braised Collard Greens | SCHEDULED | 1 | 0 | 1 |
| 4000654 | Mozzarella Provolone Blend | FOR_SALE | 1 | 0 | 1 |
| 4000832 | Vodka Sauce (Pouch) | FOR_SALE | 3 | 0 | 3 |
| 4000833 | Spiced Tofu | FOR_SALE | 1 | 17 | 12 |
| 4000862 | Grilled Scallion Dressing | FOR_SALE | 1 | 0 | 1 |

全部 11 个都有用法，无零用法项。明细见 Excel `for sale & scheduled 40 usages` sheet。

### 2. B2B 88（42 个）

**41 个有用法，1 个（4001177）无任何用法。** 41 个有用法的清单（40 item → menu item → item # → 用法 → sold_status / version_status / item_status）：

| 40 item | Menu Item | Item # | 用法 | sold_status | version_status | item_status |
|---|---|---|---|---|---|---|
| 4000298 | Classic Fried Chicken Sandwich, Wonder Works | 8010099 | BOM | NOT_SOLD | DRAFT | R&D |
| 4000298 | Buffalo Chicken Sandwich, Wonder Works | 8010101 | BOM | NOT_SOLD | DRAFT | R&D |
| 4000298 | Classic Fried Chicken Sandwich, The Booth (October) | 8011025 | BOM | NOT_SOLD | FINAL | ACTIVE |
| 4000604 | White Cheddar Mac & Cheese, Wonder Works | 8004847 | BOM | NOT_SOLD | FINAL | ACTIVE |
| 4000614 | Pork and Napa Cabbage Potsticker, Wonder Works | 8008673 | BOM | NOT_SOLD | FINAL | ACTIVE |
| 4000749 | Roasted Brussels Sprouts, Wonder Works | 8005799 | BOM | NOT_SOLD | FINAL | ACTIVE |
| 4000750 | Rigatoni Bolognese, Wonder Works | 8005314 | BOM | NOT_SOLD | FINAL | ACTIVE |
| 4000751 | Roasted Red Bliss Potatoes, Wonder Works | 8005312 | BOM | NOT_SOLD | FINAL | ACTIVE |
| 4000752 | Pulled Pork, Wonder Works | 8006157 | BOM | NOT_SOLD | FINAL | ACTIVE |
| 4000753 | Cheesesteak, Wonder Works EGAM | 8010192 | BOM | NOT_SOLD | DRAFT | R&D |
| 4000778 | Crispy Chicken Wings, Wonder Works | 8005792 | BOM | NOT_SOLD | FINAL | ACTIVE |
| 4000779 | Chicken Parmigiana, Wonder Works | 8005797 | BOM | NOT_SOLD | FINAL | ACTIVE |
| 4000780 | Seared Sirloin, Wonder Works | 8007494 | BOM | NOT_SOLD | FINAL | ACTIVE |
| 4000781 | NY Strip Steak, Wonder Works | 8005789 | BOM | NOT_SOLD | FINAL | ACTIVE |
| 4000784 | Bacon, Egg, & Cheese Sandwich, Wonder Works | 8008978 | BOM | NOT_SOLD | FINAL | ACTIVE |
| 4000785 | Vegetarian Breakfast Sandwich, Wonder Works | 8008882 | BOM | NOT_SOLD | FINAL | ACTIVE |
| 4000791 | Cavatappi Alfredo, Wonder Works | 8005315 | BOM | NOT_SOLD | FINAL | ACTIVE |
| 4000791 | Cavatappi Alfredo, Wonder Works EGAM | 8010195 | BOM | NOT_SOLD | DRAFT | R&D |
| 4000791 | Chicken Alfredo, Wonder Works (COPY) | 8010424 | BOM | NOT_SOLD | DRAFT | R&D |
| 4000792 | Fries, Wonder Works | 8005788 | BOM | NOT_SOLD | FINAL | ACTIVE |
| 4000793 | Half Roasted Chicken, Wonder Works | 8005790 | BOM | NOT_SOLD | FINAL | ACTIVE |
| 4000794 | Chicken Tenders, Wonder Works | 8004845 | BOM | NOT_SOLD | FINAL | ACTIVE |
| 4000795 | Rigatoni Red Sauce, Wonder Works | 8005316 | BOM | NOT_SOLD | FINAL | ACTIVE |
| 4000796 | Roasted Carrots, Wonder Works | 8005310 | BOM | NOT_SOLD | FINAL | ACTIVE |
| 4000797 | Penne alla Vodka, Wonder Works | 8005313 | BOM | NOT_SOLD | FINAL | ACTIVE |
| 4000797 | Penne alla Vodka, Wonder Works EGAM | 8010193 | BOM | NOT_SOLD | DRAFT | R&D |
| 4000798 | Cheese Quesadilla, Wonder Works | 8005794 | BOM | NOT_SOLD | FINAL | ACTIVE |
| 4000799 | Churros, Wonder Works | 8006159 | BOM | NOT_SOLD | FINAL | ACTIVE |
| 4000800 | Salmon Tranche, Wonder Works | 8006207 | BOM | NOT_SOLD | FINAL | ACTIVE |
| 4000801 | Smash Burger, Wonder Works | 8005798 | BOM | NOT_SOLD | FINAL | ACTIVE |
| 4000802 | Vegetable Potsticker, Wonder Works | 8008505 | BOM | NOT_SOLD | FINAL | ACTIVE |
| 4000879 | Cornbread, Wonder Works | 8011474 | BOM | NOT_SOLD | FINAL | ACTIVE |
| 4000880 | Biscuits, Wonder Works | 8011475 | BOM | NOT_SOLD | FINAL | ACTIVE |
| 4000882 | Half Bone-in Chicken, Wonder Works | 8011476 | BOM | NOT_SOLD | FINAL | ACTIVE |
| 4000924 / 4000925 | Cheesesteak, Wonder Works | 8004842 | BOM | NOT_SOLD | FINAL | ACTIVE |
| 4000934 | Meatball Ricotta Round Pizza 16" (Di Fara), Wonder Works | 8004517 | BOM | NOT_SOLD | DRAFT | R&D |
| 4000952 | Mini Garlic Bread, Wonder Works / Wonder Works EGAM | 8010098 / 8010191 | BOM | NOT_SOLD | DRAFT | R&D |
| 4000955 | Chicken Cordon Blue, Wonder Works AREAS / (COPY) | 8010334 / 8010413 | BOM | NOT_SOLD | DRAFT | R&D |
| 4000956 | Roasted Pork Sandwich, Wonder Works AREAS | 8010407 | BOM | NOT_SOLD | DRAFT | R&D |
| 4000957 | Mozzarella Sticks, Wonder Works AREAS | 8010406 | BOM | NOT_SOLD | DRAFT | R&D |
| 4000958 | Arancini, Wonder Works AREAS | 8010330 | BOM | NOT_SOLD | DRAFT | R&D |
| 4000959 | Simple Salad, Wonder Works AREAS | 8010329 | BOM | NOT_SOLD | DRAFT | R&D |
| 4000960 | Meatball Sandwich, Wonder Works AREAS | 8010335 | BOM | NOT_SOLD | DRAFT | R&D |
| 4000961 | Chicken Tenders, Wonder Works AREAS | 8010337 | BOM | NOT_SOLD | DRAFT | R&D |
| 4000963 | The Marco, Wonder Works AREAS | 8010340 | BOM | NOT_SOLD | DRAFT | R&D |

**4001177**：BOM 和 customization 路径在任何状态下都查无引用，是这批里唯一"完全无人使用"的 40 item。

### 3. Not sold 40（405 个）

- 163 个有效用法 / 242 个零用法，336 条用法记录，落在 174 个去重后的 usage item 上（167 menu item + 7 HDR recipe item）。
- 明细已写入 Excel `Not sold 40 usages` sheet（336 行）；数量太大不在此处逐条列出。
- 命中的 7 个 HDR recipe item：`7000017`（Cilantro-Lime White Rice）、`7000019`（Fresh Pico de Gallo）、`7000024`（White Rice Cooked）、`7000025`（Brown Rice Cooked）、`7000026`（BBQ Brisket Burnt Ends Cooked）、`7000120`（Tejas Pickles）、`7000132`（Bacon Pieces Cooked）——这 7 个的反查结果见第 4 节。

**242 个零用法的 40 item number**（non-dormant + 非过期版本 + 非 preset 条件下查无任何 menu item / HDR recipe item 用法，清理候选）：

4000047, 4000049, 4000056, 4000057, 4000058, 4000078, 4000081, 4000082, 4000084, 4000085, 4000088, 4000089, 4000090, 4000096, 4000097, 4000098, 4000099, 4000100, 4000101, 4000113, 4000122, 4000123, 4000129, 4000131, 4000132, 4000137, 4000233, 4000234, 4000236, 4000237, 4000239, 4000240, 4000244, 4000250, 4000251, 4000254, 4000255, 4000257, 4000261, 4000262, 4000269, 4000277, 4000278, 4000283, 4000287, 4000288, 4000291, 4000295, 4000297, 4000299, 4000302, 4000305, 4000306, 4000308, 4000311, 4000314, 4000321, 4000322, 4000327, 4000331, 4000333, 4000335, 4000336, 4000338, 4000340, 4000350, 4000360, 4000366, 4000370, 4000373, 4000375, 4000387, 4000388, 4000389, 4000390, 4000393, 4000394, 4000396, 4000401, 4000403, 4000422, 4000448, 4000449, 4000461, 4000465, 4000477, 4000483, 4000486, 4000487, 4000488, 4000492, 4000498, 4000499, 4000502, 4000508, 4000511, 4000512, 4000514, 4000537, 4000539, 4000551, 4000566, 4000569, 4000570, 4000576, 4000578, 4000579, 4000581, 4000582, 4000583, 4000584, 4000586, 4000587, 4000589, 4000590, 4000591, 4000594, 4000595, 4000598, 4000600, 4000601, 4000605, 4000607, 4000610, 4000615, 4000619, 4000621, 4000627, 4000638, 4000639, 4000640, 4000643, 4000645, 4000656, 4000657, 4000662, 4000668, 4000673, 4000674, 4000676, 4000681, 4000687, 4000700, 4000705, 4000710, 4000718, 4000733, 4000735, 4000739, 4000786, 4000787, 4000788, 4000789, 4000790, 4000822, 4000825, 4000830, 4000866, 4000871, 4000874, 4000881, 4000884, 4000886, 4000887, 4000888, 4000889, 4000890, 4000896, 4000909, 4000914, 4000915, 4000917, 4000920, 4000922, 4000923, 4000927, 4000930, 4000932, 4000933, 4000937, 4000938, 4000941, 4000943, 4000944, 4000945, 4000946, 4000947, 4000948, 4000949, 4000950, 4000964, 4000973, 4000974, 4000975, 4000978, 4000980, 4000984, 4000989, 4000995, 4001005, 4001014, 4001016, 4001100, 4001102, 4001163, 4001169, 4001178, 4001180, 4001183, 4001184, 4001185, 4001186, 4001187, 4001188, 4001189, 4001192, 4001193, 4001200, 4001202, 4001206, 4001207, 4001222, 4001225, 4001229, 4001243, 4001246, 4001248, 4001249, 4001252, 4001258, 4001260, 4001261, 4001262, 4001263, 4001271, 4001272, 4001273, 4001296, 4001298, 4001299, 4001310, 4001311

### 4. Not sold 40 → HDR recipe item 反查（7 个）

以上第 3 节命中的 7 个 HDR recipe item，反过来查谁用了它们（同样 non-dormant + 非过期版本 + 非 preset）：

| HDR recipe item | 名称 | 用法数 | 用法类型 | 涉及 menu item |
|---|---|---|---|---|
| 7000017 | Cilantro-Lime White Rice [BOWLDER Limesalt TEST] | 1 | customization | Bowl (BYO), Limesalt [BOWLDER 700* TEST ID] (8010568) |
| 7000019 | Fresh Pico de Gallo (FC Mexican) [BOWLDER Limesalt TEST] | 2 | customization | Bowl (BYO), Limesalt [BOWLDER 700* TEST ID] (8010568) |
| 7000024 | White Rice (Cooked) [Rice Cooker, 21x] | 5 | customization | Bowl (BYO), Yasas (Rice Pilot) (8010904)；Burrito (BYO), Limesalt (Rice Pilot) (8010916)；Bowl (BYO), Limesalt (Rice Pilot) (8010917)；Taco (BYO), Limesalt (Rice Pilot) (8010918) |
| 7000025 | Brown Rice (Cooked) [Rice Cooker, 21x] | 4 | customization | Burrito (BYO), Limesalt (Rice Pilot) (8010916)；Bowl (BYO), Limesalt (Rice Pilot) (8010917)；Taco (BYO), Limesalt (Rice Pilot) (8010918)；Custom Rice Bowl, Mighty Quinn's (8012211) |
| 7000026 | BBQ Brisket Burnt Ends (Cooked) Limesalt HDR | **0** | — | **无任何用法** |
| 7000120 | Tejas Pickles | 1 | BOM | Tejas Pickle Mix, Tejas Revamp (8012368) |
| 7000132 | Bacon Pieces (Cooked, 1/2 Batch) | 2 | BOM + customization | Loaded Baby Potatoes, The Mainstay (8012004) |

- 15 条记录全部落在 **8 个去重后的 menu item** 上，**没有出现 HDR recipe → HDR recipe 的二次嵌套用法**。
- 10/15 条命中还处于 `DRAFT`/`R&D`（BOWLDER / Rice Pilot 系列测试品项），只有 5 条是 `FINAL`/`ACTIVE`（7000024、7000025 各 1 条对应 8010904/8010916/8010917/8010918 中的 FINAL 记录）。
- **7000026** 在 BOM 和 customization 路径下都查无引用，是这批 HDR recipe item 里唯一"完全无人使用"的。

---

## 方法与查询

数据源：`secure-recipe-prod.recipe_v2.item_versions`（`bom_header` 和 `item_customization` 均为 JSON 字段）。

统一过滤条件：

```sql
WHERE iv.effective = true
  AND iv.deleted = false
  AND iv.item_status != 'DORMANT'
  AND iv.version_status != 'EXPIRED'
  AND iv.object_type IN ('MENU','HDR_RECIPE')
  AND iv.preset_item_version_info IS NULL
```

BOM + customization 用法 UNION 查询（`{id_list}` 替换为目标 40\*/7\* item number 列表）：

```sql
WITH bom_usage AS (
  SELECT
    JSON_VALUE(bom_line, '$.item_number') AS src_item_number,
    iv.item_number AS usage_item_number,
    iv.name AS usage_item_name,
    iv.item_status, iv.sold_status, iv.version_id AS version, iv.version_status,
    'BOM' AS used_in,
    CAST(NULL AS STRING) AS customization_type,
    CAST(NULL AS STRING) AS customization_name,
    CAST(NULL AS STRING) AS option_name
  FROM `secure-recipe-prod.recipe_v2.item_versions` iv,
  UNNEST(JSON_EXTRACT_ARRAY(iv.bom_header, '$.bom_lines')) AS bom_line
  WHERE iv.effective = true AND iv.deleted = false
    AND iv.item_status != 'DORMANT' AND iv.version_status != 'EXPIRED'
    AND iv.object_type IN ('MENU','HDR_RECIPE')
    AND iv.preset_item_version_info IS NULL
    AND JSON_VALUE(bom_line, '$.item_number') IN ({id_list})
),
cust_usage AS (
  SELECT
    JSON_VALUE(opt_item, '$.item_number') AS src_item_number,
    iv.item_number AS usage_item_number,
    iv.name AS usage_item_name,
    iv.item_status, iv.sold_status, iv.version_id AS version, iv.version_status,
    'customization' AS used_in,
    JSON_VALUE(opt, '$.type') AS customization_type,
    JSON_VALUE(opt, '$.name') AS customization_name,
    JSON_VALUE(opt_val, '$.name') AS option_name
  FROM `secure-recipe-prod.recipe_v2.item_versions` iv,
  UNNEST(JSON_EXTRACT_ARRAY(iv.item_customization, '$.options')) AS opt,
  UNNEST(JSON_EXTRACT_ARRAY(opt, '$.option_values')) AS opt_val,
  UNNEST(JSON_EXTRACT_ARRAY(opt_val, '$.items')) AS opt_item
  WHERE iv.effective = true AND iv.deleted = false
    AND iv.item_status != 'DORMANT' AND iv.version_status != 'EXPIRED'
    AND iv.object_type IN ('MENU','HDR_RECIPE')
    AND iv.preset_item_version_info IS NULL
    AND JSON_VALUE(opt_item, '$.item_number') IN ({id_list})
)
SELECT * FROM bom_usage
UNION DISTINCT
SELECT * FROM cust_usage
ORDER BY src_item_number, usage_item_number, used_in;
```

第 4 节的 HDR recipe 反查，`{id_list}` 替换为第 3 节命中的 7 个 HDR recipe item number（`7000017,7000019,7000024,7000025,7000026,7000120,7000132`），查询结构完全相同。

对象类型确认（去重后 usage item 的 `object_type` 分布，用于确认"menu item 数"与"hdr recipe item 数"）：

```sql
SELECT object_type, COUNT(DISTINCT item_number) AS cnt
FROM `secure-recipe-prod.recipe_v2.item_versions`
WHERE effective = true AND deleted = false AND item_number IN ({usage_item_ids})
GROUP BY object_type;
```

---

## 备注

- `Not sold 40` 原始 sheet 里有 7 条 40 item number 带后缀 "F"（如 `4000052F`、`4001183F`），代表同一 40 item 的冷冻（FZN）变体标注，查询时已 strip 掉非数字字符还原为纯数字 item number 处理。
- 只读 BigQuery 分析，未修改任何 Cookbook 数据；Excel 文件仅新增 sheet，原有 3 个 sheet 内容未改动。

---
*生成时间：2026-08-24 | 数据源：`~/Downloads/Uncutover 40s.xlsx` + `secure-recipe-prod.recipe_v2.item_versions`*
