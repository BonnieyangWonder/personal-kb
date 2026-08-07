# Line Build Same-HDR Duplicate Audit

**问题**：1个menu item在同1个HDR（物理location）里，是否存在多条line build？排除 `is_multiple_usage=true`（Is Multi-usage qty）和 `is_multiple_version=true`（Multi versions vs options）两个已知合法场景后再看。

**范围**：menu item取 `sold_status IN ('FOR_SALE','SCHEDULED')`、`version_status != 'DRAFT'`、`item_status != 'DORMANT'`、`service_end_time > now()`、`deleted=false`、`object_type='MENU'`。

---

## 结论

**1. 排除5个已确认从HDR删除的ghost restaurant后：0个case，问题已完全解释清楚。**
第一轮按 `restaurant_id` 直接当HDR分组，结论是0；纠正为按真实物理HDR（`restaurant_id → hdr_id`）分组后，实际查出6个item在Upper East Side这一个HDR上有2条不同line build。深挖后发现这6个case全部由同一批数据脏源头造成——5个已经从HDR删除/解绑的"ghost" restaurant，名下还挂着状态为`LINE_BUILD_CREATED`的孤儿line build。**把这5个restaurant的line build记录排除掉之后重新检查，同HDR多line build的case清零**（9746条line build记录归集到4563组item×HDR，无一组>1条），说明这不是普遍性问题，只是这一批遗留脏数据造成的。

**2. 需要清理：11个menu item、15条(item版本×line build)记录，全部关联到这5个已删除的restaurant。清理动作统一是"从对应line build的Apply to Restaurants名单里摘除这几个restaurant_id"，不是删除整条line build——因为这15条line build目前都还同时被30~212个其他正常在用的restaurant共用。**

**3. 附带发现一个流程性gap，建议单独跟进**：HDR侧删除/解绑restaurant，目前看不会触发Cookbook这边同步清理对应restaurant_id下的line build配置。这批5个只是这次顺带查到的，同样的孤儿数据大概率会随着HDR以后每次删除restaurant持续产生，建议作为根因流程问题上报，而不是当一次性清理处理。

**清理清单**（详见下文完整表格）：

| Restaurant（已确认HDR删除） | 涉及item数 | Line build记录数 |
|---|---|---|
| DO NOT USE!!! Alanza Upper East Side | 10 | 11 |
| DNU Wing Trip Downtown Brooklyn Corporate | 2 | 2 |
| JBird Westfield | 2 | 2 |
| Royal Greens Westfield TEMP | 1 | 1 |
| Estelle & Jeanie's Westfield | 1 | 1 |
| **合计（去重后item数）** | **11** | **15** |

---

## 背景与方法论

### 一个关键纠正：restaurant_id ≠ HDR

`item_line_builds.restaurant_id` 对应的是"品牌在某个location的实例"（如 "Alanza Pizza Upper East Side"），不是物理HDR本身。1个HDR可以同时承载几十个不同品牌的restaurant。要判断"是否在同一个HDR"，必须先把 `restaurant_id` 解析成真正的 `hdr_id`：

- **主路径（约96%覆盖）**：`wonder-dw-prod-brd.forecast.active_service_calendar_v2`，直接给出 `restaurant_id ↔ hdr_id` 的精确映射
- **兜底路径（约4%，多为新开/未发布的restaurant）**：`wonder-dw-prod-brd.dw.dim_hdrs` 的 `hdr_name`/`hdr_code`（如 `HDR_UES` ↔ "Upper East Side"）与 `dim_restaurants.restaurant_name` 做文本匹配
- 剩余4条（2个restaurant_id，"Chai Pani Nevins"/"Table No. 1 Nevins"）两种方式都解析不出HDR，人工核实这两个在所有相关item上用的都是同一条line build，不影响结论

排查中还发现 `wonder-dw-prod-brd.dw.dim_hdr_restaurants` 表看起来像现成的restaurant→HDR桥表，但实测里面大部分restaurant_id对应了多个hdr_id（不符合"1个restaurant对应1个HDR"的预期），数据可信度存疑，本次分析没有采用。

### 5个ghost restaurant的确认信息

| Restaurant | restaurant_id | publish_status (Merch Tool) | 最近更新时间 |
|---|---|---|---|
| DO NOT USE!!! Alanza Upper East Side | `bb44c9c5-a7f3-4338-94e7-2f14192c2998` | UNPUBLISHED | 2026-07-30 |
| DNU Wing Trip Downtown Brooklyn Corporate | `1172532f-9c2a-4ea8-9a36-b3fa6dc5570f` | UNPUBLISHED | 2026-07-31 |
| JBird Westfield | `639649b1-6b9c-4e12-8946-36283a151218` | UNPUBLISHED | 2024-11-18 |
| Royal Greens Westfield TEMP | `dbbb3879-8a1e-416e-ac4f-e2b813dca692` | UNPUBLISHED | 2026-07-31 |
| Estelle & Jeanie's Westfield | `a690a153-3e4b-4d36-a9ac-a84e296360a5` | UNPUBLISHED | 2024-11-18 |

Bonnie直接在HDR系统核实过，这5个restaurant确实已经从HDR删除/解绑。`publish_status`字段由Merch Tool管理（`dim_hdr_restaurants.restaurant_name`字段说明明确标注"as configured in Merch tool"），跟HDR侧的解绑动作是两个系统各自的状态，未必同步更新时间戳——因此上面的"最近更新时间"只反映Merch Tool这边的记录，不代表HDR解绑的确切时间。

**覆盖度提醒**：本次识别ghost restaurant用的代理指标是Merch Tool的`publish_status=UNPUBLISHED`，跟"HDR侧已删除"不是同一件事、也未必完全同步——不排除还有restaurant在HDR侧已删除、但Merch Tool这边`publish_status`仍显示PUBLISHED，本次方法会漏掉这类case。如果能拿到HDR系统自己的完整删除名单，值得再反查一轮。

---

## 结论1详情：排除ghost restaurant后的同HDR检查

| 指标 | 数值 |
|---|---|
| 符合条件的menu item（对象层） | 845个item / 1233个item版本 |
| 有line build配置的符合条件item | 248个item / 333个item版本 |
| 全部line build记录（排除两个toggle后） | 9767条 |
| 其中归属5个ghost restaurant、被排除 | 17条 |
| 成功归集到物理HDR的记录 | 9746条（4条"Nevins"未解析，已人工确认无影响） |
| 归集出的 (item版本 × HDR) 组合 | 4563组 |
| **>1条line build的组合数** | **0** |

---

## 结论2详情：完整清理清单

以下15条记录，动作统一为「保留line build，把标注的ghost restaurant_id从其Apply to Restaurants名单中移除」：

| item_number | 名称 | item_version_id | line_build_id | 需摘除的restaurant | 该line build其他在用restaurant数 |
|---|---|---|---|---|---|
| 8006354 | Parmesan Potatoes, Walnut Lane | `c8e2e860-a2fc-4ba7-99a0-e329d015ab7f` | `ac238d1a-9bbc-4323-9221-a97f3669b42d` | JBird Westfield, DO NOT USE!!! Alanza Upper East Side | 30 |
| 8007812 | Soda, Prebiotic, Strawberry Lemon, Poppi | `5296162b-fb9a-4af3-a4e7-9dc19640a352` | `058994e8-9962-4d3f-8a8d-68808e46f0b8` | Royal Greens Westfield TEMP, JBird Westfield, Estelle & Jeanie's Westfield | 30 |
| 8008516 | French Fries, Wing Trip | `67e62dfc-c79f-4a38-9bc8-0cdf665cbcab` | `25a7c399-d649-4402-84e4-5af208993e17` | DO NOT USE!!! Alanza Upper East Side | 49 |
| 8009955 | Chicken Tenders, Bellies | `c74d0815-6904-41eb-b8ee-ee6ae33358f1` | `91e4735d-60cb-4f87-b785-b421f744837c` | DNU Wing Trip Downtown Brooklyn Corporate | 170 |
| 8009955 | Chicken Tenders, Bellies（同item，另一条line build） | `c74d0815-6904-41eb-b8ee-ee6ae33358f1` | `daec5dd2-8335-45a0-855a-6858b0626e7c` | DO NOT USE!!! Alanza Upper East Side | 156 |
| 8010062 | French Fries, Bellies | `1e8eb83d-8ca9-47f8-a812-f4e3d470fb93` | `b217ffc7-7ddb-403d-bd25-6cec9ad7426e` | DNU Wing Trip Downtown Brooklyn Corporate | 148 |
| 8010062 | French Fries, Bellies（同item，另一条line build） | `1e8eb83d-8ca9-47f8-a812-f4e3d470fb93` | `d2476fe6-a549-45b8-9f9c-8b38160c1c83` | DO NOT USE!!! Alanza Upper East Side | 36 |
| 8010386 | Chinese Green Beans, Kin House 2.0（FINAL版本） | `24494212-124d-4eed-a146-a0a76b29bc95` | `7165180c-a80f-409f-819b-2beb2eda7455` | DO NOT USE!!! Alanza Upper East Side | 39 |
| 8010386 | Chinese Green Beans, Kin House 2.0（SCHEDULED版本） | `eaab4ef8-0d0c-4481-9016-fcff94be71d9` | `7165180c-a80f-409f-819b-2beb2eda7455` | DO NOT USE!!! Alanza Upper East Side | 39 |
| 8010431 | Pizza Vodka 12", Alanza Pizza | `fcf9aed0-a484-4d13-93e6-3bbdab877a4a` | `5b31c3ce-638a-4daf-81c9-828463d13973` | DO NOT USE!!! Alanza Upper East Side | 164 |
| 8010435 | Pizza Tartufo & Funghi 12", Alanza Pizza | `e3042a1f-d52b-48ba-beab-ea7f4dde6868` | `3fa8b7b9-0089-421f-ac01-91cfae013d58` | DO NOT USE!!! Alanza Upper East Side | 204 |
| 8010437 | Pizza Piccante 12", Alanza Pizza | `73787529-6392-411b-90d7-6a62b1de1be1` | `c1f67c9e-3f6e-4041-bf0a-13546009fa94` | DO NOT USE!!! Alanza Upper East Side | 164 |
| 8010438 | Pizza Pepperoni 12", Alanza Pizza | `42cef21b-4c9a-4fc3-b4cf-dbec6c7ebf24` | `08466aa8-9f6f-418a-acf3-4368059e6172` | DO NOT USE!!! Alanza Upper East Side | 206 |
| 8010439 | Pizza Classica 12", Alanza Pizza | `7e8cf114-a0af-4ba6-a8c8-a12255058e22` | `f237ae61-23ea-4bef-b9dc-94ad1e86fb23` | DO NOT USE!!! Alanza Upper East Side | 212 |

其中前6个item（8008516、8010431、8010435、8010437、8010438、8010439）原本就是本次分析最先查到的"同HDR 2条line build内容已经不同"的case——现役restaurant（Alanza Pizza/Alanza/Detroit Brick Pizza Co./Best of Wonder的Upper East Side实例）已经切换到新的line build，ghost restaurant手里还攥着旧版本。其余5个item目前恰好和现役内容一致，暂时没有出餐风险，但同样是需要摘除的脏数据。

---

## 建议

1. **清理**：按上表把5个restaurant_id从对应15条line build的Apply to Restaurants名单中移除，不要整条删除line build（都还有几十到两百多个其他restaurant在正常用）。
2. **根因**：把"HDR删除/解绑restaurant时，Cookbook没有联动清理该restaurant_id下的line build"作为流程gap上报，推动系统层面的清理机制，而不是仅做这一次性修复。
3. **覆盖度**：如果能拿到HDR系统自己的完整"已删除restaurant"名单，建议再反查一轮——本次是用Merch Tool `publish_status=UNPUBLISHED`做代理指标筛出来的5个，可能不是HDR侧已删除restaurant的完整集合。

---

## 附录：核心SQL

```sql
-- Step 1: 符合条件的menu item版本
WITH qualifying_items AS (
  SELECT iv.item_number, iv._id AS item_version_id, iv.name
  FROM `secure-recipe-prod.recipe_v2.item_versions` iv
  WHERE iv.object_type = 'MENU'
    AND iv.deleted = false
    AND iv.item_status != 'DORMANT'
    AND iv.version_status != 'DRAFT'
    AND iv.sold_status IN ('FOR_SALE', 'SCHEDULED')
    AND iv.service_end_time > CURRENT_DATETIME()
),
-- Step 2: 排除两个toggle=true的line build，且要有具体restaurant_id
lb AS (
  SELECT DISTINCT ilb.item_version_id, ilb.restaurant_id, ilb.line_build_id
  FROM `secure-recipe-prod.recipe_v2.item_line_builds` ilb
  WHERE ilb.restaurant_id IS NOT NULL
    AND COALESCE(ilb.is_multiple_usage, false) = false
    AND COALESCE(ilb.is_multiple_version, false) = false
)
SELECT q.item_number, q.name, q.item_version_id, lb.restaurant_id, lb.line_build_id, dr.restaurant_name
FROM qualifying_items q
JOIN lb ON q.item_version_id = lb.item_version_id
LEFT JOIN `wonder-dw-prod-brd.dw.dim_restaurants` dr ON lb.restaurant_id = dr.restaurant_id;

-- Step 3: restaurant_id → hdr_id 精确映射（约96%覆盖）
SELECT DISTINCT restaurant_id, hdr_id
FROM `wonder-dw-prod-brd.forecast.active_service_calendar_v2`;

-- Step 4: 剩余未解析的，用 dim_hdrs 的 hdr_name/hdr_code 对 restaurant_name 做文本匹配兜底
-- （见正文方法论部分，逻辑在Python里做，非纯SQL）

-- Step 5: 排除5个ghost restaurant，按 (item_version_id, hdr_id) 分组数 line_build_id
-- HAVING COUNT(DISTINCT line_build_id) > 1  → 本次结果为空
```

---

## 关联笔记

- [[A2-Data Research/Line Build Multi-Version & Multi-Usage Toggles Analysis.md]] —— 同期对 `is_multiple_usage`/`is_multiple_version` 两个toggle本身是否可以下线的分析，本报告排除的两个toggle条件与该报告口径一致

---

*生成时间：2026-08-07 | 数据来源：secure-recipe-prod.recipe_v2、wonder-dw-prod-brd.dw、wonder-dw-prod-brd.forecast | 分析人：Bonnie + Claudian*
