## 结论

对同一批 **210 个去重后的 40\* HDR Consumable Item**（原始粘贴 239 个，含重复）做 SCC cutover 状态核查：

- **100%（210/210）尚未 cutover 到 SCC**：无论是 40 本身（thawed）还是对应的 40F（冷冻态），名下都**查无任何 42\* item**，且所有关联的 41\* WSKU 的 `scc_source` 全部为 `NULL`。这批 item 目前**全部**仍走 legacy 41 通道。
- **100%（210/210）在 legacy 41 通道上仍有 ≥1 个"可用"的 41 item**（`item_status != DORMANT` 且关联的 `wonder_sku_to_fulfillment_options.status = 'ACTIVE'`）。按 [[个人/missing fulfillment option 分析方法]] 的判定逻辑 Step 2③（"未 cutover 到 SCC，但有可用 41 兜底"），**这批 item 单独看都不构成 fulfillment 缺口**。
- **但与本次会话前一步的"是否被有效消费"核查交叉后**：这 210 个 uncutover item 里，只有 **9 个（4.3%）** 真正被当前 `sold_status ∈ {FOR_SALE, SCHEDULED}`、非 draft、非 dormant 的 menu item（BOM 路径）实际使用；**201 个（95.7%）没有任何有效销售路径在消费它们**——既未 cutover，也没有活跃 menu item 在用，是"双重休眠"状态，比单纯"未 cutover"更值得关注（是否该直接 dormant / 清理，而不是排队等 SCC 迁移）。
- 9 个被使用的 item 对应的 menu item 名称中均**不含 B2B / Wonder Works**。

## 背景与范围

本报告的 210 个 40 item 与前一步"是否被 menu item / 7\* HDR recipe 的 BOM/customization 使用"核查用的是同一批清单（Bonnie 直接粘贴的批次，已去重）。这里补充的新维度是：**SCC cutover 状态**（是否已迁移到新的 42\* WSKU 体系）。

术语说明（详见 [[个人/missing fulfillment option 分析方法]]）：
- `scc_source = true`（无论落在 41\* 还是 42\* 记录上）= 已 cutover 到 SCC
- `scc_source = NULL` 且查无 42\* item = 未 cutover（uncutover），仍完全依赖 legacy 41 通道

## 详细数据

### Cutover 状态汇总

| 维度 | 数量 | 占比 |
|---|---|---|
| 检查的 40 item（去重后） | 210 | 100% |
| Uncutover（无 42\*，`scc_source` 全 NULL） | 210 | 100% |
| Cutover（至少一条记录 `scc_source = true`） | 0 | 0% |
| 有 ≥1 个"可用"41 item 兜底（非 dormant + fulfillment ACTIVE） | 210 | 100% |
| 无任何可用 41（真异常，需要跟进） | 0 | 0% |

### 与"活跃消费"交叉后的四象限

| 象限 | 数量 | 说明 |
|---|---|---|
| Uncutover + 被活跃 menu item 使用 | 9 | 正常运转中，但仍排队等 SCC cutover |
| **Uncutover + 无活跃 menu item 使用** | **201** | **双重休眠——建议评估是否可以直接跳过 cutover、走 dormant/清理流程** |
| Cutover + 被活跃 menu item 使用 | 0 | — |
| Cutover + 无活跃 menu item 使用 | 0 | — |

被活跃 menu item 使用的 9 个 item（均无 B2B / Wonder Works 标记）：

| 40 item | 使用它的 Menu Item | sold_status | version_status |
|---|---|---|---|
| 4000060 | Banana Hazelnut Chocolate Pudding, Desserts (8010006) | FOR_SALE | FINAL |
| 4000374 | Steak Pepperonata, Alanza (8007958) / Pork Chop Pepperonata, Alanza (8007956) | FOR_SALE | FINAL |
| 4000380 | Cabo Cauliflower & Hummus Wrap (8012112) / Bowl (8012107), Opa Cantina | FOR_SALE | FINAL |
| 4000384 | Beef Souvlaki Street Wrap, Cantina Zorba (8012119) | FOR_SALE | FINAL |
| 4000636 | Chiang Mai Chili Steak Bowl (8012099) / The Acropolis Asada Bowl (8012104) / Wrap (8012109), Siam Crunch / Opa Cantina | FOR_SALE | FINAL |
| 4000654, 4000832 | Vodka Bacon Pizza, Detroit Brick LTO (8011319) | FOR_SALE | FINAL |
| 4000833 | Spiced Tofu & Hummus Wrap, Cantina Zorba (8012120) | FOR_SALE | FINAL |
| 4000862 | Bangkok Charred Scallion Chicken Bowl, Siam Crunch (8012102) | FOR_SALE | FINAL |

其余 **201 个**"uncutover 且无活跃消费"的 40 item：

4000059, 4000074, 4000097, 4000113, 4000138, 4000139, 4000153, 4000154, 4000155, 4000156, 4000157, 4000158, 4000159, 4000160, 4000161, 4000162, 4000163, 4000164, 4000165, 4000166, 4000167, 4000168, 4000169, 4000170, 4000171, 4000172, 4000173, 4000174, 4000175, 4000176, 4000177, 4000178, 4000179, 4000180, 4000181, 4000182, 4000183, 4000184, 4000185, 4000186, 4000187, 4000241, 4000257, 4000258, 4000259, 4000262, 4000263, 4000265, 4000266, 4000267, 4000281, 4000285, 4000289, 4000290, 4000298, 4000304, 4000308, 4000333, 4000346, 4000347, 4000348, 4000349, 4000389, 4000392, 4000401, 4000403, 4000411, 4000421, 4000443, 4000444, 4000448, 4000482, 4000491, 4000492, 4000497, 4000503, 4000520, 4000532, 4000541, 4000544, 4000547, 4000549, 4000569, 4000581, 4000587, 4000592, 4000596, 4000604, 4000606, 4000614, 4000624, 4000625, 4000627, 4000628, 4000641, 4000656, 4000668, 4000672, 4000679, 4000681, 4000687, 4000688, 4000695, 4000743, 4000744, 4000747, 4000749, 4000750, 4000751, 4000752, 4000753, 4000754, 4000755, 4000756, 4000758, 4000759, 4000760, 4000761, 4000762, 4000763, 4000764, 4000765, 4000766, 4000767, 4000768, 4000769, 4000770, 4000771, 4000772, 4000773, 4000774, 4000775, 4000776, 4000777, 4000778, 4000779, 4000780, 4000781, 4000782, 4000783, 4000784, 4000785, 4000791, 4000792, 4000793, 4000794, 4000795, 4000796, 4000797, 4000798, 4000799, 4000800, 4000801, 4000802, 4000813, 4000824, 4000826, 4000834, 4000837, 4000863, 4000864, 4000865, 4000867, 4000869, 4000872, 4000879, 4000880, 4000882, 4000885, 4000892, 4000913, 4000924, 4000925, 4000928, 4000929, 4000931, 4000934, 4000935, 4000936, 4000937, 4000939, 4000940, 4000941, 4000942, 4000945, 4000947, 4000948, 4000951, 4000952, 4000953, 4000955, 4000956, 4000957, 4000958, 4000959, 4000960, 4000961, 4000962, 4000963, 4001009, 4001010

### WSKU 状态明细（41\* 侧）

- 240 条 41\* WSKU 记录关联到这 210 个 40 item（含 40F 反查），未发现任何 42\* 记录。
- `item_status` 分布：206 个 40 item 名下全部 41 均为 `ACTIVE`；1 个同时有 `ACTIVE` + `R&D`；3 个同时有 `ACTIVE` + `DORMANT`（但都至少还有一个非 dormant 的）。
- 关联 `wonder_sku_to_fulfillment_options`：210 个 40 item 均能找到至少一条 `status = 'ACTIVE'` 的 fulfillment 记录，未发现"无可用 fulfillment"的真异常。

## 方法与查询

数据源：
- `secure-recipe-prod.recipe_v2.item_versions`（BOM `bom_header`、customization `item_customization` JSON，及 `sold_status`/`version_status`/`item_status`）——用于前一步的"活跃消费"核查
- `wonder-raw-prod.mysql_batch_product_catalog.wonder_sku_items`（`consumable_item_number`, `item_number`, `item_status`, `scc_source`, `deleted`）——本次 cutover 核查主表
- `wonder-raw-prod.mysql_batch_product_catalog.wonder_sku_to_fulfillment_options`（`wonder_sku_item_number`, `status`, `deleted`）——判断 41 是否"可用"

关键查询（40 + 40F 反查全部关联 WSKU）：

```sql
WITH item_list AS (
  SELECT item40 FROM UNNEST(['4000059','4000060', ... ]) AS item40
),
targets AS (
  SELECT item40 AS base_40, item40 AS lookup_item FROM item_list
  UNION ALL
  SELECT item40 AS base_40, CONCAT(item40, 'F') AS lookup_item FROM item_list
)
SELECT
  t.base_40,
  s.consumable_item_number AS matched_consumable,
  s.item_number AS wsku_item_number,
  s.item_status,
  s.deleted,
  s.scc_source
FROM targets t
JOIN `wonder-raw-prod.mysql_batch_product_catalog.wonder_sku_items` s
  ON s.consumable_item_number = t.lookup_item
WHERE s.deleted = false
ORDER BY t.base_40, s.item_number;
```

可用 fulfillment 判断：

```sql
SELECT
  s.consumable_item_number AS base_40,
  s.item_number AS wsku_item_number,
  s.item_status,
  fo.status AS fulfillment_status,
  fo.deleted AS fo_deleted
FROM `wonder-raw-prod.mysql_batch_product_catalog.wonder_sku_items` s
LEFT JOIN `wonder-raw-prod.mysql_batch_product_catalog.wonder_sku_to_fulfillment_options` fo
  ON fo.wonder_sku_item_number = s.item_number AND fo.deleted = false
WHERE s.deleted = false
  AND s.consumable_item_number IN ('4000059','4000060', ... );
```

对照的"活跃消费"核查方法与结论见本次会话上一轮的分析（menu item / 7\* HDR recipe 的 BOM + customization 查询，过滤 `sold_status IN ('FOR_SALE','SCHEDULED')`、`version_status != 'DRAFT'`、`item_status != 'DORMANT'`）。

---
*生成时间：2026-08-21 | 只读 BigQuery 分析，未修改任何 Cookbook/SCC 数据*
