---
title: IK Dish Type & IK Plating Rule - Business Requirements
date: 2026-05-08
created: 2026-05-22
updated: 2026-05-22
type: concept
domain: Cookbook
status: active
tags:
  - cookbook
  - ik
  - plating-rule
  - dish-type
  - line-build
  - kds
sources:
  - https://wonder.atlassian.net/browse/MD-17927
  - https://wonder.atlassian.net/wiki/spaces/SR/pages/4916084781
  - https://wonder.atlassian.net/wiki/spaces/RT/pages/5051580475
  - https://wonder.atlassian.net/wiki/spaces/RT/pages/4990074883
  - https://wonder.atlassian.net/wiki/spaces/SR/pages/4917067798
  - https://wonder.atlassian.net/wiki/spaces/SR/pages/5116362975
  - https://wonder.atlassian.net/wiki/spaces/~712020a23d399f56f34b208584dc6e78d90758/pages/4298440989
  - https://wonder.atlassian.net/wiki/spaces/SR/pages/5217583107
  - https://wonder.atlassian.net/wiki/spaces/RT/pages/5238849564
  - https://wonder.atlassian.net/wiki/spaces/~712020a23d399f56f34b208584dc6e78d90758/pages/5244518402
---

# IK Dish Type & IK Plating Rule — Business Requirements

## 1. Business Background

Wonder 正在将 Infinite Kitchen（IK）自动化设备集成到 hybrid pod 厨房流程中。IK 设备需要知道两个关键信息来正确完成出餐：

1. **用什么容器（碗型）** → **IK Dish Type**
2. **食材如何摆放（摆盘方式）** → **IK Plating Rule**

这两个属性需要在 Cookbook 中配置，并随订单数据传递给 IK 设备和 KDS。

IK 设备当前需要支持 6 种包装类型（Dish Type）和 5 种摆盘规则（Plating Rule），且这些配置需要灵活应对不同菜单项、不同 HDR 的差异化需求。

### 关联项目背景

- **Wonder Create**: 让 Influencer 可以自由创建菜单项，需要 Cookbook 自动生成 line build（默认所有 IK Eligible 组件聚合到 IK step）
- **IK Eligible 组件标记**: 已在 component item 层面标记 `IK Eligible=true/false`，标记为 true 的组件会聚合到 line build 的 IK step 中
- **KDS 路由逻辑**: KDS 将 IK step 中实际 loaded 在 HDR IK 中的组件发送给 IK 设备，未 loaded 的则路由到 cold pod 做 garnish

---

## 2. IK Dish Type（碗型/容器类型）

### 2.1 定义

IK Dish Type 指 IK 设备在处理订单时需要请求放置的容器类型。不同的菜单项可能需要不同大小和形状的容器。

### 2.2 属性值（枚举）

| IK Dish Type | 描述 |
|---|---|
| `48oz Bowl` | 48oz 圆形碗，用于大份沙拉（如 Royal Greens） |
| `32oz Bowl` | 32oz 圆形碗，用于常规 bowl（如 Yasas、Hanu Poke） |
| `30oz Oval Metal Bowl` | 30oz 椭圆形金属碗，用于特定 bowl 类型 |
| `Bellies Bowl` | Bellies 品牌专用碗（如 Bellies Chicken and Rice） |
| `8oz Cup` | 8oz 小杯，用于 side items（如白米饭、豆类、salsa） |
| `Reusable Bowl` | 可重复使用碗，用于 burrito、quesadilla、taco 等非碗类食品的 IK 处理 |

### 2.3 配置层级

**在 Menu Item 级别配置**（最终设计决策）。

- 不在 component item 级别配置
- 一个 menu item 只有一个 IK Dish Type
- IK Dish Type 可能与最终包装不同（例如 quesadilla 用 Reusable Bowl 在 IK 中处理，但最终包装在矩形 pulp bowl 中）

### 2.4 示例

| Menu Item | IK Dish Type | 说明 |
|---|---|---|
| Royal Greens Cobb Salad | 48oz Bowl | 大份沙拉 |
| Yasas Bowl | 32oz Bowl | 常规 bowl |
| Hanu Poke Bowl | 32oz Bowl | Poke bowl |
| Limesalt Bowl | 30oz Oval Metal Bowl | 椭圆碗 |
| Bellies Chicken and Rice | Bellies Bowl | Bellies 品牌碗 |
| Limesalt Burrito | Reusable Bowl | 非碗类，IK 处理完后转移到最终包装 |
| Limesalt Tacos | Reusable Bowl | 同上 |
| Limesalt Quesadilla | Reusable Bowl | 同上 |
| Side white rice / brown rice / poke rice | 8oz Cup | Side 小份 |
| Side corn salsa / pico | Reusable Bowl (8oz Cup at FS) | 特殊：IK 处理用 reusable bowl，但最终打包在 FS 的 4oz cup |

---

## 3. IK Plating Rule（摆盘规则）

### 3.1 定义

IK Plating Rule 定义食材在容器中如何排列摆放。这直接影响 IK 设备的 dispensing 行为（单圈/双圈、食材落点位置等）。

### 3.2 属性值（枚举）

| IK Plating Rule | 描述 | 适用场景 |
|---|---|---|
| `Layering` | 分层摆放，所有食材按顺序叠放 | 默认规则，适用于大多数 bowl 类型 |
| `Center` | 居中摆放，所有食材放在碗中央 | burrito、taco、quesadilla 等在 reusable bowl 中处理；side items |
| `Straight` | 直线排列 | 特定 bowl（如 Limesalt oval bowl）；非分层场景 |
| `Prelap Center` | 预跑圈后居中摆放 | Double Lap (Action Needed)：先收集特定食材（如 Soba Noodles），跑完一圈后居中摆放，再跑第二圈收集其余食材 |
| `Prelap Poke Press` | 预跑圈后 Poke Press 摆盘 | Double Lap (Action Needed) + TM 按压：先收集 Poke Rice + Furikake，居中摆放后停在 FS 让 TM 按压，再跑第二圈 |

### 3.3 IK Plating Rule 与 Double Lap 的关系

```
Prelap Center       → Double Lap (No Action Needed)：碗在 FS 不停止
                       例：Royal Greens + Soba Noodles
Prelap Poke Press   → Double Lap (Action Needed)：碗在 FS 停止，TM 按压后继续
                       例：Hanu Poke Bowl with Poke Rice + Furikake
```

`Center` / `Layering` / `Straight` → Standard Single Lap（标准单圈）

### 3.4 配置层级

**最终决策：在 Menu Item 级别配置默认值，支持 Sub-Step 级别覆盖**。

- **Menu Item 级别**：设置该 menu item 的默认 IK Plating Rule，所有子步骤继承此默认值
- **Sub-Step 级别**：可针对特定子步骤覆盖默认值（例如某个 component/customization 需要特殊摆盘方式）

### 3.5 配置设计的演进

| 方案 | 提出时间 | 状态 |
|---|---|---|
| Component Item 级别配置 IK Plating Rule | 2026-05-08 (Bonnie 提出) | ❌ 被否决 |
| Menu Item 级别默认 + Sub-Step 级别覆盖 | 2026-05-08 (Charlie Fox) / 2026-05-12 (Evan Fox 确认) | ✅ 采纳 |

**Component 级别方案被否决的原因**（Charlie Fox, 2026-05-08）：
- 不能假设同一个 component 在所有使用场景中有相同的 plating rule
- 也不能假设同一 component 在特定 dish type 下总是相同 plating rule
- 配置会过于复杂

### 3.6 示例

#### 示例 1：Royal Greens Cobb Salad 定制加 Soba Noodles

```
Menu Item Level:
  IK Dish Type: 48oz Bowl
  IK Plating Rule: Layering (默认)

Sub-Step Level Override:
  Sub-Step: "Choose your Base → Soba Noodles"
  IK Plating Rule: Prelap Center (覆盖)
  → IK 先跑一圈收集 Soba Noodles 居中摆放，再跑第二圈收集其余食材
```

#### 示例 2：Hanu Poke Bowl with Poke Rice

```
Menu Item Level:
  IK Dish Type: 32oz Bowl
  IK Plating Rule: Layering (默认)

Sub-Step Level Override:
  Sub-Step: "Choose your Base → Sushi Rice (Poke Rice)"
  IK Plating Rule: Prelap Poke Press (覆盖)
  
  Sub-Step: "Crunchy Toppings → Furikake"
  IK Plating Rule: Prelap Poke Press (覆盖)
  → IK 先跑一圈收集 Poke Rice + Furikake，居中摆放后停在 FS，TM 按压确认，再跑第二圈
```

#### 示例 3：Limesalt Burrito

```
Menu Item Level:
  IK Dish Type: Reusable Bowl
  IK Plating Rule: Center
  → IK 单圈收集所有食材并居中摆放
```

---

## 4. 与 IK Eligible 的交互规则

> **来源：MD-17927 (Bonnie Yang 的业务需求)**

### 4.1 核心逻辑

`IK Eligible` 是触发 IK 对比逻辑的开关：
- **IK Eligible = true** 的 step → KDS 会比较 sub-step 的 component 是否在 HDR 的 IK 中被 loaded
- 如果 IK loaded → 发送给 IK 处理
- 如果 IK 未 loaded → KDS 将其作为 garnish step 发送到 cold pod

### 4.2 Plating Rule 的必填性规则

| Step 的 IK Eligible | Plating Rule 要求 | 原因 |
|---|---|---|
| `true` | **必填**（如果 sub-step 映射了 item/customization） | IK 需要知道如何摆盘这些食材 |
| `false` | **可选**（可为 null） | 该 step 不走 IK，但保留灵活性 |

### 4.3 设计灵活性考量

- **不阻止**为 `IK Eligible=false` 的 sub-step 设置 plating rule
  - 更灵活，KDS 中不会因为非 IK step 携带 plating rule 而出问题
- 不做 `IK Eligible` true → false 时的自动清除
  - 目标是有越来越多的 HDR 使用 IK 设备 → 限制没有意义
  - Cookbook 返回 line build 中存在的任何配置给 KDS
  - KDS 是否会消费 plating rule 值由 `IK Eligible` flag 决定
- 如果将来需要 enforcement：在 `IK Eligible` 从 true 改为 false 时做 validation + auto-clear

---

## 5. 解决方案设计

### 5.1 Cookbook 侧

1. **Menu Item 新增属性 `IK Dish Type`**
   - 枚举值：48oz Bowl / 32oz Bowl / 30oz Oval Metal Bowl / Bellies Bowl / 8oz Cup / Reusable Bowl
   - 在 menu item 创建/编辑页面可配置

2. **Menu Item 新增属性 `IK Plating Rule`（默认值）**
   - 枚举值：Layering / Center / Straight / Prelap Center / Prelap Poke Press
   - 作为该 menu item 所有 IK sub-step 的默认 plating rule

3. **Line Build Sub-Step 新增属性 `IK Plating Rule`（可覆盖）**
   - 默认继承 menu item 级别的 IK Plating Rule
   - CE/用户可手动修改任意 sub-step 的 plating rule
   - 不受 component item 的 plating rule 配置影响
   - 如果 sub-step 属于 `IK Eligible=true` 的 step 且映射了 component/customization → plating rule 必填
   - 如果 sub-step 属于 `IK Eligible=false` 的 step → plating rule 可选

4. **Cookbook 返回给 KDS 的数据**
   - 返回所有 line build 中已配置的 IK Dish Type 和 IK Plating Rule
   - 不根据 IK Eligible 过滤 — 全部透传

### 5.2 KDS 侧

1. **消费 IK Dish Type**：发送给 IK（在 `POST /orders` API 的 `dish_type` 字段）
2. **消费 IK Plating Rule**：
   - 只消费 `IK Eligible=true` 的 step 中 sub-step 的 plating rule
   - 如 `IK Eligible=false` → 忽略 plating rule
3. **IK order API** 中的数据结构：
   - Line item 级别：`dish_type`、`plating_rule`
   - Ingredient 级别：`plating_rule`

### 5.3 IK 设备侧

1. 根据 `dish_type` 选择请求 TM 放置的容器类型
2. 根据 `plating_rule` 决定：
   - 单圈还是双圈（Double Lap）
   - 是否需要在 FS（Finishing Station）停止并等待 TM 交互
   - 食材在容器中的排列方式（居中/分层/直线）

---

## 6. 关键设计决策记录

| # | 决策 | 结论 | 决策人 | 日期 |
|---|---|---|---|---|
| 1 | IK Dish Type 配置在哪一层 | **Menu Item 级别** | Bonnie / Evan Fox | 2026-05-12 |
| 2 | IK Plating Rule 配置在哪一层 | **Menu Item 默认 + Sub-Step 覆盖** (不在 Component 级别) | Charlie Fox / Evan Fox | 2026-05-12 |
| 3 | IK Eligible=false 时 plating rule 是否必填 | **可选**（不强制清除） | Bonnie Yang | MD-17927 |
| 4 | IK Eligible true→false 是否自动清除 plating rule | **不清除** | Bonnie Yang | MD-17927 |
| 5 | Cookbook 是否需要按 IK Eligible 过滤 plating rule | **不过滤**，全量透传给 KDS | Bonnie Yang | MD-17927 |
| 6 | 是否需要在 Component Item 层支持多 Plating Rule 配置 | **不需要**，简化方案 | Charlie Fox / Evan Fox | 2026-05-12 |

---

## 7. 关联系统与数据流

```
Cookbook
  ├── Menu Item: IK Dish Type, IK Plating Rule (default)
  └── Line Build Sub-Step: IK Plating Rule (override)
       │
       ▼
KDS (Kitchen Display System)
  ├── 获取 IK Eligible 组件的 IK loaded 状态
  ├── IK Eligible=true → 发送给 IK (含 plating rule)
  └── IK Eligible=false / 未被 IK loaded → 发送给 cold pod (忽略 plating rule)
       │
       ▼
IK (Infinite Kitchen)
  ├── POST /orders: 接收 dish_type, plating_rule, ingredients
  ├── BPS: 提示 TM 放置对应 dish type
  └── 执行对应的 plating rule (单圈/双圈/摆盘方式)
       │
       ▼
Finishing Station (FS)
  ├── Bowl Chit: 打印 QR code, order item info, packaging type, ingredients
  └── FSO Chit: 仅 FS 食材的 chit
```

---

## 8. Plating Rule → IK Journey 映射

| Plating Rule | IK Journey | TM 交互 |
|---|---|---|
| `Layering` | Standard Single Lap | 无 |
| `Center` | Standard Single Lap | 无 |
| `Straight` | Standard Single Lap | 无 |
| `Prelap Center` | Double Lap (No Action Needed) | FS 不停止 |
| `Prelap Poke Press` | Double Lap (Action Needed) | FS 停止，TM 按压确认 |

---

## 9. 菜单项配置矩阵（完整参考）

| Dish Type | Food Item | IK Plating Rule (Menu Item) | Sub-Step Override |
|---|---|---|---|
| 48oz Bowl | Royal Greens Bowls | Layering | — |
| 48oz Bowl | Royal Greens + Soba Noodles | Layering | Soba Noodles: Prelap Center |
| 32oz Bowl | Yasas Bowls | Layering | — |
| Reusable Bowl | Yasas Sandwiches | Center | — |
| 32oz Bowl | Hanu Poke Bowls (with Poke Rice) | Layering | Sushi Rice + Furikake: Prelap Poke Press |
| 32oz Bowl | Hanu Poke Bowls (Double Greens, no rice) | Layering | — (no override → single lap) |
| 30oz Oval | Limesalt Bowls | Straight | — |
| Reusable Bowl | Limesalt Burritos | Center | — |
| Reusable Bowl | Limesalt Tacos | Layering | — |
| Reusable Bowl | Limesalt Quesadilla | Layering | — |
| 8oz Cup | Side white/brown/poke rice | Center | — |
| Reusable Bowl | Side corn salsa / pico | Center | (特殊：FS 放入 4oz cup) |
| Bellies Bowl | Bellies Chicken and Rice | Layering | — |
| 32oz Bowl | Side salads (various) | Layering | — |
| 48oz Bowl (default) | New unconfigured items | Layering | — |

---

## 10. 时间线

| 里程碑 | 目标日期 |
|---|---|
| Cookbook IK Dish Type & Plating Rule 开发完成 | ~2026-05-25 (6/1 前 1 周) |
| KDS 端数据透传 | 2026-06-01 |
| 首次 integration test (IK simulator) | 2026-06-01 |
| IK lab 全量测试 | 2026-06-15 |
| MTE 软启动 (Limesalt + Yasas) | 2026-08-10 |
| 全面 launch | 2026 年 9 月 |

---

## 11. 依赖项

- **Cookbook**: 完成 IK Eligible 组件标记 + IK Step 在 line build 中的支持（已完成，2026-03）
- **KDS**: IK order dispatch API (`POST /orders`) — `dish_type` 和 `plating_rule` 字段已定义
- **HDR Portal**: 支持 IK pod type 配置（`ik_code`）
- **IK 设备**: BPS 更新支持 6 种 dish type 的 pre-placement；支持所有 plating rule 对应的 journey

---

## 12. 未解决问题 / 后续迭代

1. **Dish Type 与 Plating Rule 的 cross-validation**: 是否需要在 Cookbook 中做数据录入校验（如某些 plating rule 不适用于某些 dish type）？
   - 当前决策：MVP 阶段不做限制，IK 侧自行处理不兼容情况
   - 长期：可能需要上游保护
2. **IK Dish Type 与最终 Packaging Type 的关系**: Chit 上应显示 packaging type 还是 IK Dish Type？
   - MVP: 显示 packaging type
   - 未来: 如果两者不同时才显示 packaging type
3. **Component Item 级别 plating rule 配置**: 当前被否决，如果后续运营数据的模式显示需要，可能重新考虑
4. **基于食材数量自动切换 Dish Type**: Wonder Create 可能需要根据食材数量自动推荐 dish type

---

## 13. 参考页面链接

| 页面 | 链接 |
|---|---|
| **Jira: MD-17927** (IK Dish Type & Plating Rule 主需求) | [MD-17927](https://wonder.atlassian.net/browse/MD-17927) |
| **Changing Plating Rules Based on Order Item type** (业务需求 & 示例) | [Confluence](https://wonder.atlassian.net/wiki/spaces/SR/pages/4916084781) |
| **IK Eligible Component Configured in Line Build** (IK Eligible 配置方案) | [Confluence](https://wonder.atlassian.net/wiki/spaces/RT/pages/5051580475) |
| **[WIP] IK Integration** (技术集成 & API 定义) | [Confluence](https://wonder.atlassian.net/wiki/spaces/RT/pages/4990074883) |
| **Double Laps for IK Bowls** (Double Lap journey 需求) | [Confluence](https://wonder.atlassian.net/wiki/spaces/SR/pages/4917067798) |
| **Pre-Placing Dishes for Wonder IK** (Dish Type pre-placement) | [Confluence](https://wonder.atlassian.net/wiki/spaces/SR/pages/5116362975) |
| **[WIP] IK integration at hybrid pods PRD** (整体 PRD) | [Confluence](https://wonder.atlassian.net/wiki/spaces/~712020a23d399f56f34b208584dc6e78d90758/pages/4298440989) |
| **Chit Updates - MVP** (Chit 设计) | [Confluence](https://wonder.atlassian.net/wiki/spaces/SR/pages/5217583107) |
| **XM NY Weekly Planning 2026-5-12** (周计划) | [Confluence](https://wonder.atlassian.net/wiki/spaces/RT/pages/5238849564) |
| **6/15 Integration Test** (集成测试场景) | [Confluence](https://wonder.atlassian.net/wiki/spaces/~712020a23d399f56f34b208584dc6e78d90758/pages/5244518402) |
| **Plating Rules Matrix** (Google Sheet) | [Google Sheets](https://docs.google.com/spreadsheets/d/1W2xdmpeZWBDvkZTFOdCSjFiFrDzvlkIfImOwdltLr-k/edit) |
| **Reusable Bowl / "For Here" in the IK** | [Confluence](https://wonder.atlassian.net/wiki/spaces/SR/pages/4916969522) |
