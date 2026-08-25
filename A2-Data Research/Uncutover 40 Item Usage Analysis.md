# Uncutover 40 Item Usage Analysis

**问题**：`~/Downloads/Uncutover 40s.xlsx` 里三个批次的 40\* HDR Consumable Item（`for salescheduled 40` 11 个、`B2B 88` 42 个、`Not sold 40` 405 个 → 修正后 408 个，均按 item number 去重），分别被哪些 menu item 或 7\* HDR recipe item 通过 BOM 或 customization 引用？「Not sold 40」批次里如果命中的是 7\* HDR recipe item，再反查这个 HDR recipe item 本身又被谁用。后续在此基础上追加了：跨批次去重的 menu item "能否 dormant" 确认清单、40 item 零用法清单、以及针对这两份清单的最近 90 天人工编辑核查。

**范围**：只统计 `item_status != 'DORMANT'`（non-dormant）、`version_status != 'EXPIRED'`（非过期版本）、`preset_item_version_info IS NULL`（排除 preset item，判断标准是数据库字段而非 item name 里是否带 "preset" 字样）的 menu item / HDR recipe item 用法。

---

## 结论

1. **for sale & scheduled 40**（11 个，本身是 FOR_SALE/SCHEDULED 状态）：**全部 11 个都有有效用法**，共 61 条用法记录，落在 **30 个去重后的 menu item** 上，**0 个 HDR recipe item**。用法最集中的是 4000636（Adobo Steak，20 条：3 BOM + 17 customization）和 4000833（Spiced Tofu，18 条：1 BOM + 17 customization）。
2. **B2B 88**（原始 42 个，B2B/Wonder Works 内部用途）：**41/42 有有效用法，1 个（4001177）完全无用法**。`B2B 88 usages` sheet 后续又并入了 37 个 **Wonder Works 品牌**的 menu item（这些原本是通过其他 40 item 从 "Not sold 40" 批次里查出来的，因为品牌是 Wonder Works 才移到这个 sheet ——详见下方"数据质量修正与后续调整"），所以该 sheet 现在合计 **90 条用法记录，78 个去重后的 menu item，涉及 67 个不同的 40 item**（其中 26 个不属于原始 42 个 B2B 88 批次）。若只看原始 42 个批次本身：41/42 有效，全部走 BOM 路径，全部 `sold_status = NOT_SOLD`。其中有部分用法来自还在 `DRAFT`/`R&D` 状态的测试品项（如 "Wonder Works EGAM"、"AREAS"、"(COPY)" 系列）——因为本次过滤条件只排除 DORMANT/EXPIRED/preset，不排除 DRAFT，所以这些草稿也算"有用法"；这一点和之前 [[40 Item SCC Cutover Status]] 报告里 B2B 段落（额外排除了 DRAFT）的口径不同，见下方"与既有报告的口径差异"。
3. **Not sold 40**（原始 405 个，数据质量修正后为 **408 个** —— 见下方专门章节）：**165/408（约 40%）有有效用法**，共 345 条用法记录，落在 **177 个去重后的 usage item 上（170 个 menu item + 7 个 HDR recipe item）**。**243 个（约 60%）完全查不到任何非 dormant/过期/preset 的用法**，是本批里最值得关注的清理候选。
4. **Not sold 40 → 7 个 HDR recipe item 的反查**：这 7 个 HDR recipe item（7000017/7000019/7000024/7000025/7000026/7000120/7000132）本身又被谁用——**6/7 有下游用法**（15 条记录，全部落在 8 个去重后的 menu item 上，**没有再出现 HDR recipe → HDR recipe 的嵌套用法**），**7000026（BBQ Brisket Burnt Ends (Cooked) Limesalt HDR）完全查不到任何用法**。命中的用法里有 10/15 条还处于 `DRAFT`/`R&D`，只有 5 条是 `FINAL`/`ACTIVE`。
5. **`Menu／7 Dormant Confirmation` 汇总确认清单**（原名 `Menu Item Dormant Confirmation`；跨 `for sale & scheduled 40 usages` + `Not sold 40 usages` + `Not sold 40 hdr recipe usages` 三个 sheet，按 item number 去重，不含 B2B 88）：**159 个去重后的 item（152 个 menu item + 7 个 7\* HDR recipe item，两者已合并进同一张确认清单，第一列改名为 `menu item/7*`）**，105 个 `ACTIVE` + 54 个 `R&D`。补充了最近 90 天人工编辑核查：**89/159（约 56%）在最近 90 天内被人工编辑过**，其中 8 个标注为 "Wonder Create item"（通过 Wonder Create 工具批量创建发布，而非纯手工编辑）。两个原本判定"已从 Cookbook 彻底删除"的 item（8012010、8012021，"TO DELETE" 命名）已由 Bonnie 从清单里手动移除，不再需要走确认流程。
6. **`B2B 88 Dormant Confirmation` 确认清单**：镜像 `B2B 88 usages` sheet 去重后的 **78 个 menu item**，格式与上面一致，独立于 `Menu／7 Dormant Confirmation` 之外，供业务方专门确认 Wonder Works/B2B 相关品项。
7. **`No usage 40 items` 零用法清单**：跨 `B2B 88`（1 个）+ `Not sold 40`（原 243 个）合计原本 244 个 40 item 完全无用法；**其中 29 个 40 item 自身的 `40 item status` 已经是 `DORMANT`（已经下线，不需要再走"能否 dormant"确认）**，Bonnie 复核后已从清单里删除这 29 条，清单收敛到 **215 个**（189 `ACTIVE` + 26 `R&D`）。剩余 215 个里 **21 个（约 10%）** 有人工编辑记录，但多为属性清理/草稿信息更新，真正"发布新版本"级别的编辑很少——整体仍是相对安全的清理候选池。

---

> [!warning] ⚠️ 与既有报告的口径差异 —— 两份报告数字对不上不是错误
> vault 里已有一份 [[40 Item SCC Cutover Status]] 报告，其中"B2B 关联 40 Item"章节分析的**是同一批原始 `B2B 88`**（42 个，41 个重叠 + 1 个新增 4001177）。
>
> | | 本报告 | [[40 Item SCC Cutover Status]] |
> |---|---|---|
> | 过滤条件 | non-dormant + 非过期版本 + 非 preset（**不排除 DRAFT**） | non-dormant + 非过期版本 + 非 preset + **额外排除 `version_status = 'DRAFT'`** |
> | 结论（原始 42 个批次） | **41 有效 / 1 无效** | **30 有效 / 12 无效** |
>
> 差别的 11 个（B2B 88 里那些还处于 `DRAFT`/`R&D` 的 "Wonder Works EGAM"/"AREAS"/"(COPY)" 测试品项）就是被"排除 DRAFT"这条额外条件筛掉的。**两份报告的原始查询结果并不矛盾**，纯粹是过滤条件不同——以后再看到这两个数字对不上，先检查是不是这个原因，不用怀疑数据本身有问题。按自己的目的（要不要把还在测试阶段的草稿品项算作"有效用法"）选用对应口径。

---

## ⚠️ 数据质量修正记录（"F" 后缀 item number 的坑）

分析过程中发现：`Not sold 40` 原始 sheet 里有 7 个 40 item number 带后缀 "F"（如 `4001271F`）。**最初错误地把 "F" 当成注释性标记，用正则去掉后缀做了归一化**——但复查发现 **"F" 是 item number 的真实组成部分，代表冷冻（FZN）变体，是一个完全独立、真实存在的 Cookbook item**，不能剥离。已按修正后的正确身份重新核查并更新了受影响的 sheet：

| item number | 问题 | 修正结果 |
|---|---|---|
| `4001260` | 之前误当作裸数字查询，实际该裸数字对应的是**另一个完全不相关的真实 item**（"Fried Shrimp (U21/25)"，SCHEDULED） | 更正为 `4001260F`（"Fried Shrimp (U21/25) [FZN]"），无用法 |
| `4001271` | 裸数字**根本不存在** | 更正为 `4001271F`（"Salmon, IQF [FZN]"），无用法 |
| `4001299` | 裸数字根本不存在；且真实的 `4001299F` **其实有用法**（原来被误判为无用法） | 从零用法清单移除，改为记入 `Not sold 40 usages`（6 条用法：3 BOM + 3 customization，Mighty Quinn's 系列 R&D 草稿） |
| `4001183F`、`4001286F`、`4001296F` | 归一化时被当作各自裸数字兄弟（`4001183`/`4001286`/`4001296`，两者都是真实存在的独立 item）的"重复项"丢弃，**从未被纳入任何用法核查** | 补查后：`4001183F`、`4001296F` 无用法（新增进零用法清单）；`4001286F` 有用法（3 条 BOM，同样是 Mighty Quinn's/Tejas Revamp 系列 R&D 草稿，涉及 5 个去重后 menu item，已计入结论 §5 的 152 个数字里） |

**净影响**：`Not sold 40` 批次范围从 405 → **408**（新发现 3 个此前完全漏查的真实 item）；`Not sold 40 usages` 336 → **345** 行；零用法清单 243 → **244**（B2B 88 的 4001177 单独占 1 个）；`Menu Item Dormant Confirmation` 新增/更新了因这次修正而浮现的 5 个 Mighty Quinn's/Tejas Revamp menu item。

这个坑（以及后面 §"方法与查询"提到的 `is_system_action` 不可靠问题）已经沉淀进 [[Z01-Resource/CB-bigquery/playbooks/data-research-patterns.md]] §13–14，供以后所有 Cookbook 数据分析任务复用，不用重新踩坑。

---

## Excel 交付物

`~/Downloads/Uncutover 40s.xlsx` 现在共 **10 个 sheet**（原始 3 个 `for salescheduled 40` / `B2B 88` / `Not sold 40` 保持不变，新增 7 个）：

| Sheet | 内容 | 当前行数 |
|---|---|---|
| `for sale & scheduled 40 usages` | `for salescheduled 40`（11 个 40 item）的 BOM/customization 用法明细 | 61 |
| `B2B 88 usages` | `B2B 88`（42 个）+ 后续并入的 37 个 Wonder Works menu item 的用法明细 | 90 |
| `Not sold 40 usages` | `Not sold 40`（修正后 408 个）的用法明细 | 345 |
| `Not sold 40 hdr recipe usages` | 反查 `Not sold 40 usages` 命中的 7 个 HDR recipe item | 15（+ Bonnie 手动加的 1 条备注行） |
| `Menu／7 Dormant Confirmation` | 跨批次去重后的 menu item + 7\* HDR recipe item 待确认清单（原 `Menu Item Dormant Confirmation`，后并入了原 `HDR Recipe Dormant Confirmation` 的 7 行并删除了那个独立 sheet），含 90 天编辑核查 | 159 |
| `B2B 88 Dormant Confirmation` | `B2B 88 usages` 去重后的 menu item 待确认清单 | 78 |
| `No usage 40 items` | 跨 `B2B 88` + `Not sold 40` 的零用法 40 item 清单，含 90 天编辑核查（已剔除 29 个自身已是 `DORMANT` 的记录） | 215 |

用法明细类 sheet 列结构统一为：`40 item number（或 hdr recipe item number）, usage item number, usage item name, item status, sold status, version, version status, used in BOM/customization, customization type, customization name, option name`。

确认清单类 sheet（`Menu／7 Dormant Confirmation` / `B2B 88 Dormant Confirmation`）列结构：`menu item/7*`（`Menu／7 Dormant Confirmation` 专属，`B2B 88 Dormant Confirmation` 仍是 `menu item number`）`, menu item name, item status, sold status, version, version status, referenced 40/hdr recipe item(s), source sheet(s), [Note,] edited in last 90 days?, last edited by, last edited date, last edit detail (within 90 days), confirm OK to dormant?, comments`。`confirm OK to dormant?` 和 `comments` 留空，供业务方手动确认。`referenced 40/hdr recipe item(s)` 对 menu item 行表示"这个 menu item 用了哪些 40/7\* item"，对 7\* HDR recipe item 行则表示"这个 7\* item 自己用了哪些 `Not sold 40` 的 40 item"——两种含义的方向不同，读的时候按行的 item 类型区分。

`No usage 40 items` 列结构：`40 item number, 40 item name, 40 item status, 40 sold status, 40 version status, source batch, edited in last 90 days?, last edited by, last edited date, last edit detail (within 90 days)`。

> 注：Bonnie 已手动编辑过这个文件多次（调整过用法明细 sheet 的列顺序、给 `Not sold 40 hdr recipe usages` 加了一列 "Bonnie Noted" 并写了备注、移除了两个已确认删除的 menu item、把 `HDR Recipe Dormant Confirmation` 并入 `Menu Item Dormant Confirmation` 并改名改列名、删除了 `No usage 40 items` 里 29 条自身已 DORMANT 的记录），本报告的行数/列结构以当前文件实际状态为准。

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

### 2. B2B 88（原始 42 个）

**41 个有用法，1 个（4001177）无任何用法。** 明细见 Excel `B2B 88 usages` sheet（该 sheet 现在还包含后续并入的 37 个 Wonder Works menu item，见"数据质量修正与后续调整"背景说明）。有用法的 41 个里，多数是 `sold_status=NOT_SOLD, version_status=FINAL, item_status=ACTIVE` 的正式 Wonder Works 品项（如 White Cheddar Mac & Cheese、Pulled Pork、Crispy Chicken Wings 等），另有约 15 条用法来自还在 `DRAFT`/`R&D` 的测试变体（"EGAM"/"AREAS"/"(COPY)" 系列）。

**4001177**：BOM 和 customization 路径在任何状态下都查无引用，是原始 42 个批次里唯一"完全无人使用"的 40 item。

### 3. Not sold 40（修正后 408 个）

- 165 个有效用法 / 243 个零用法，345 条用法记录，落在 177 个去重后的 usage item 上（170 menu item + 7 HDR recipe item）。这 243 个零用法里，后续有 29 个因为自身 `item_status` 已经是 `DORMANT`，被从"待确认清单"里移除（见下方清单），`No usage 40 items` sheet 里实际显示 214 个 `Not sold 40` 来源的记录。
- 明细已写入 Excel `Not sold 40 usages` sheet（345 行）；数量太大不在此处逐条列出。
- 命中的 7 个 HDR recipe item：`7000017`（Cilantro-Lime White Rice）、`7000019`（Fresh Pico de Gallo）、`7000024`（White Rice Cooked）、`7000025`（Brown Rice Cooked）、`7000026`（BBQ Brisket Burnt Ends Cooked）、`7000120`（Tejas Pickles）、`7000132`（Bacon Pieces Cooked）——这 7 个的反查结果见第 4 节。

**215 个零用法 40 item number 待确认清单**（跨 `Not sold 40` 214 个 + `B2B 88` 的 4001177，non-dormant + 非过期版本 + 非 preset 条件下查无任何 menu item / HDR recipe item 用法，清理候选。含修正后的 `4001183F`/`4001260F`/`4001271F`，`4001183` 裸数字兄弟也独立无用法）：

4000047, 4000049, 4000056, 4000057, 4000058, 4000078, 4000081, 4000082, 4000084, 4000085, 4000088, 4000089, 4000090, 4000096, 4000097, 4000098, 4000099, 4000100, 4000101, 4000113, 4000122, 4000123, 4000129, 4000131, 4000132, 4000137, 4000233, 4000234, 4000236, 4000237, 4000239, 4000240, 4000244, 4000250, 4000251, 4000254, 4000255, 4000257, 4000261, 4000262, 4000269, 4000277, 4000278, 4000283, 4000287, 4000288, 4000291, 4000295, 4000297, 4000299, 4000302, 4000305, 4000306, 4000308, 4000311, 4000314, 4000321, 4000322, 4000327, 4000331, 4000333, 4000335, 4000336, 4000338, 4000340, 4000350, 4000360, 4000366, 4000370, 4000373, 4000375, 4000387, 4000388, 4000389, 4000390, 4000393, 4000394, 4000396, 4000401, 4000403, 4000422, 4000448, 4000449, 4000461, 4000465, 4000477, 4000483, 4000486, 4000487, 4000488, 4000492, 4000498, 4000499, 4000502, 4000508, 4000511, 4000512, 4000514, 4000537, 4000539, 4000551, 4000566, 4000569, 4000570, 4000576, 4000578, 4000579, 4000581, 4000582, 4000583, 4000584, 4000586, 4000587, 4000589, 4000590, 4000591, 4000594, 4000595, 4000598, 4000600, 4000601, 4000605, 4000607, 4000610, 4000615, 4000619, 4000621, 4000627, 4000638, 4000639, 4000640, 4000643, 4000645, 4000656, 4000657, 4000662, 4000668, 4000673, 4000674, 4000676, 4000681, 4000687, 4000700, 4000718, 4000733, 4000735, 4000786, 4000787, 4000788, 4000789, 4000790, 4000822, 4000830, 4000866, 4000871, 4000881, 4000884, 4000886, 4000887, 4000888, 4000889, 4000890, 4000896, 4000909, 4000914, 4000915, 4000917, 4000920, 4000927, 4000930, 4000932, 4000933, 4000937, 4000938, 4000941, 4000943, 4000944, 4000945, 4000946, 4000947, 4000948, 4000949, 4000950, 4000964, 4000974, 4001014, 4001016, 4001177, 4001180, 4001183, 4001183F, 4001184, 4001185, 4001186, 4001187, 4001188, 4001189, 4001192, 4001193, 4001202, 4001206, 4001207, 4001222, 4001229, 4001246, 4001248, 4001252, 4001258, 4001260F, 4001263, 4001272, 4001273, 4001298, 4001310, 4001311

**另外 29 个 40 item number 因为自身 `40 item status` 已经是 `DORMANT`，已被 Bonnie 从确认清单里删除（这些不需要再走"能否 dormant"流程，因为已经 dormant 了）**：

4000705, 4000710, 4000739, 4000825, 4000874, 4000922, 4000923, 4000973, 4000975, 4000978, 4000980, 4000984, 4000989, 4000995, 4001005, 4001100, 4001102, 4001163, 4001169, 4001178, 4001200, 4001225, 4001243, 4001249, 4001261, 4001262, 4001271F, 4001296, 4001296F

> 以上清单已是 Bonnie 复核后剔除 29 个自身 `40 item status = DORMANT` 记录之后的 **215 个**（原始零用法数是 243；243 − 29 + 1 个 B2B 88 的 4001177 = 215，见下方"数据质量修正记录"之后的清单收敛说明）。

其中 21 个（约 10%）在最近 90 天内有人工编辑记录（详见 `No usage 40 items` sheet 的 `edited in last 90 days?` 等列），多为属性清理（`Updated: Attributes`）或系统营养重算触发，真正"发布新版本"级别的很少（如 4001272/4001273/4001310/4001311 这几个 `ACTIVE`/`FINAL` 状态的例外）。

### 4. Not sold 40 → HDR recipe item 反查（7 个，明细现已并入 `Menu／7 Dormant Confirmation` sheet）

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
- 10/15 条命中还处于 `DRAFT`/`R&D`（BOWLDER / Rice Pilot 系列测试品项），只有 5 条是 `FINAL`/`ACTIVE`。
- **7000026** 在 BOM 和 customization 路径下都查无引用，是这批 HDR recipe item 里唯一"完全无人使用"的。
- Bonnie 后来在 `Not sold 40 hdr recipe usages` sheet 里手动给 `7000132` 加了一条 "no usage" 备注行（与上面查到的 2 条真实用法记录并存）——保留原样未做改动，如果这条备注实际指向的是 7000026 而非 7000132 的笔误，需要 Bonnie 自己确认。
- 这 7 个 item 本身"是否可以 dormant"的确认，连同它们各自引用了哪些 `Not sold 40` 40 item，现在统一记录在第 5 节的 `Menu／7 Dormant Confirmation` sheet 里（不再单独建 `HDR Recipe Dormant Confirmation` sheet）。

### 5. Menu／7 Dormant Confirmation（159 个去重后的 item：152 menu item + 7 个 7\* HDR recipe item）

原名 `Menu Item Dormant Confirmation`，第一列已改名为 `menu item/7*`。汇总来源：`for sale & scheduled 40 usages` + `Not sold 40 usages`（其中 7 个 HDR recipe item 本身，即第 4 节命中的那 7 个，作为独立行并入本表而非当作 menu item）+ `Not sold 40 hdr recipe usages`，按 item number 去重。

- **item status 分布**：105 个 `ACTIVE`，54 个 `R&D`。
- **最近 90 天人工编辑核查**：89/159（约 56%）有人工编辑记录（判定口径见"方法与查询"）。编辑类型分布里，`Updated: Line Build`（19）、`Published: This Version`（8）、`Edited: Component`（8）、`Updated: BOM Line`（4）等实质性内容改动加起来将近 40 个，说明相当一部分不是简单的元数据调整，而是真的在维护配方——建议这部分优先找对应编辑人核实，不要因为"无用法的 40 item 关联到它"就直接建议 dormant。
- **8 个标注为 "Wonder Create item"**（Note 列，均为 menu item）：这 8 个 menu item 的最近编辑记录归属 "Wonder Create" 这个批量创作工具账号（而非具体人名），但 `New`/`Edited: Component`/`Published: This Version` 这类动作说明是真实通过工具发布的正式菜品（Chiang Mai Chili Steak Bowl 等），不是自动化系统噪音，标注出来是提醒"最近编辑=Wonder Create"和"最近编辑=SCC_SYNC 自动重算"含义不同，不能一概而论。
- **2 个已彻底删除的 item**（8012010、8012021，均命名带 "TO DELETE"）：查证时发现它们已经从 `item_versions` 里完全消失（不是标记删除，是查无记录），Bonnie 已手动将其从清单移除，不再占用确认流程。
- 因"F 后缀"数据质量修正，新增/更新了 5 个 Mighty Quinn's/Tejas Revamp 系列的 R&D 草稿 menu item（8012141、8012203、8012210 为新增，8012143、8012147 为更新引用）——这 5 个是否可以 dormant，因为都是内部测试草稿且最近仍有人工编辑（Ben Whritenour），**需要业务方明确确认，不能仅凭 R&D/DRAFT 状态判断**（是历史遗留测试数据、还是正在推进的新品测试，无法单纯从状态字段区分）。
- 7 个 7\* HDR recipe item 的详情（名称、引用的 `Not sold 40` item、90天编辑）见第 4 节表格，数据已原样并入本 sheet，未重新核查。

### 6. B2B 88 Dormant Confirmation（78 个去重后的 menu item）

数据源：`B2B 88 usages` sheet（含原始 42 个 B2B 88 批次 + 后续并入的 37 个 Wonder Works menu item）去重后的结果，格式与 `Menu／7 Dormant Confirmation` 一致但独立成表，方便业务方专门针对 Wonder Works/B2B 品项做确认。

### 7. No usage 40 items（215 个，原 244 个）

见第 3 节的完整清单。**29 个自身 `40 item status = DORMANT` 的记录已被移除**（清单见第 3 节末尾），因为这些 40 item 本来就已经下线，不需要再走"能否 dormant"的确认流程。剩余 215 个（189 `ACTIVE` + 26 `R&D`）里有 21 个最近 90 天有人工编辑记录，但详情显示多为草稿信息整理、属性标签更新或系统营养重算触发（`Updated: Attributes`、`Recalculated: Nutrition`），真正代表"仍在积极推进上线"的很少——整体上这批仍是相对安全的清理候选池，个别有 `Published: This Version` 记录的（4001272/4001273/4001310/4001311）建议单独确认。

---

## 方法与查询

数据源：`secure-recipe-prod.recipe_v2.item_versions`（`bom_header` 和 `item_customization` 均为 JSON 字段）；90 天人工编辑核查用 `wonder-recipe-prod.mongo_batch_recipe_v2.item_version_change_logs`。

统一过滤条件（用法查询）：

```sql
WHERE iv.effective = true
  AND iv.deleted = false
  AND iv.item_status != 'DORMANT'
  AND iv.version_status != 'EXPIRED'
  AND iv.object_type IN ('MENU','HDR_RECIPE')
  AND iv.preset_item_version_info IS NULL
```

BOM + customization 用法 UNION 查询（`{id_list}` 替换为目标 40\*/7\* item number 列表，**必须用完整字符串，包括任何字母后缀，不要正则去除**——见"数据质量修正记录"）：

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

HDR recipe 反查（第 4 节），`{id_list}` 替换为第 3 节命中的 7 个 HDR recipe item number，查询结构完全相同。

对象类型确认（去重后 usage item 的 `object_type` 分布，用于确认"menu item 数"与"hdr recipe item 数"）：

```sql
SELECT object_type, COUNT(DISTINCT item_number) AS cnt
FROM `secure-recipe-prod.recipe_v2.item_versions`
WHERE effective = true AND deleted = false AND item_number IN ({usage_item_ids})
GROUP BY object_type;
```

90 天人工编辑核查（第 5/7 节）：

```sql
SELECT created_by, is_system_action, COUNT(*) AS cnt
FROM `wonder-recipe-prod.mongo_batch_recipe_v2.item_version_change_logs`
WHERE item_number IN ({id_list})
  AND TIMESTAMP(created_time) >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 90 DAY)
GROUP BY created_by, is_system_action
ORDER BY cnt DESC;
```

**`is_system_action = false` 不能单独作为"是人工编辑"的判断依据**——实测 `SCC_SYNC`（营养重算同步服务）、`Wonder Create`（批量创作工具）这两个明显的系统/工具账号，这个字段都标的是 `false`。正确做法：先按 `created_by` 分组核查，排除 `recipe system%`（含 `Recipe System (MD-xxxxx)`）、`SCC_SYNC`、`Wonder Create`、纯 ticket key 格式（`^MD-[0-9]+$`）之后剩下的才算人工编辑。详见 [[Z01-Resource/CB-bigquery/playbooks/data-research-patterns.md]] §14。

---

## 备注

- 只读 BigQuery 分析，未修改任何 Cookbook 数据。
- Excel 文件除新增/更新上述 sheet 外，未改动原有 3 个原始 sheet 的内容；Bonnie 对文件的手动编辑（列顺序、备注列、删除已确认无效的行、合并/改名 sheet、删除已 DORMANT 记录）均已在本次更新中保留，未被覆盖。
- 这次分析沉淀出的两个通用坑（40\* "F" 后缀陷阱、`is_system_action` 不可靠）已写入 [[Z01-Resource/CB-bigquery/playbooks/data-research-patterns.md]] §13–14 和 [[.claude/skills/wonder-cookbook/domains/hdr-consumables.md]]，并沉淀成了一个可复用的个人 skill：`.claude/skills/my-workflows/check-40-item-dormant-candidacy.md`。
- Excel 从最初的 3 个原始 sheet 逐步演进到目前 **10 个 sheet**（含合并/精简后的结果）：`HDR Recipe Dormant Confirmation` 曾短暂作为独立 sheet 存在，后按 Bonnie 要求并入 `Menu Item Dormant Confirmation` 并整体改名为 `Menu／7 Dormant Confirmation`（Excel 的 sheet 名不允许 `/` 和 `*` 字符，用全角斜杠 `／` 替代、并去掉了 `*`，列头本身仍保留真实的 `menu item/7*`）。

---
*生成时间：2026-08-24 | 更新时间：2026-08-25（补充 Dormant Confirmation / No usage 清单、90天编辑核查、F 后缀数据质量修正、HDR Recipe Dormant Confirmation 并入 Menu／7 Dormant Confirmation、No usage 40 items 剔除已 DORMANT 记录）| 数据源：`~/Downloads/Uncutover 40s.xlsx` + `secure-recipe-prod.recipe_v2.item_versions` + `wonder-recipe-prod.mongo_batch_recipe_v2.item_version_change_logs`*
