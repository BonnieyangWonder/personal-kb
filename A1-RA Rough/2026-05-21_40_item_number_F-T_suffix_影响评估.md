---
title: "40 Item Number F/T Suffix 方案变更影响评估"
date: 2026-05-21
type: analysis
tags: [cookbook, scc, supply-chain, frozen-thawed]
domain: supply-chain
status: draft
sources:
  - "https://wonder.atlassian.net/wiki/spaces/~712020735951bb19ca4030aef4f98504f0b3da/pages/5145231396/Cookbook+Frozen+Thawed+40+Hot+Hold+PRD"
  - "https://wonder.atlassian.net/wiki/spaces/FP1/pages/5122555921/WSKU+Frozen+Thawed+Split"
---

## 背景

Cookbook Frozen/Thawed 40* 方案原计划：frozen 和 thawed 状态使用**两个不同的 40* item number**（如 400001 ↔ 400008），彼此通过 sibling linkage 关联。

新需求变更为：**同一个 base item number**，frozen state 后缀 **F**，thawed state 后缀 **T**（如 400001F / 400001T）。

本文档评估此变更对现有系统的影响。

## 需求变更对比

| 维度 | 原方案 (PRD) | 新方案 |
|------|-------------|--------|
| Item Number | 两个不同号码，如 400001 ↔ 400008 | 同一基础号，如 400001F / 400001T |
| 状态标识 | state field (frozen / thawed) | state field + item number 编码状态 |
| 关联方式 | sibling linkage field | 共享 base number，天然关联 |
| 新建互补状态 | 生成新 item number | 生成同 base + 相反 suffix |

## 影响分析

### 🔴 一、与 SCC Contract 冲突（阻断级）

**SCC 现有设计**（[WSKU Frozen/Thawed Split](https://wonder.atlassian.net/wiki/spaces/FP1/pages/5122555921)）：

- Frozen HDR SKU: `4000555F`
- Thawed HDR SKU: `4000555` — **没有 T 后缀**，base number 即代表 thawed

新需求要求 thawed 加 T 后缀 `400001T`，与 SCC 预期 `400001` **不匹配**。

**可选方案：**

| 选项 | 描述 | 影响面 |
|------|------|--------|
| A: SCC 接受 T 后缀 | SCC 数据模型、全部下游改造 | Forecast, Ladle, VDC, Work Orders |
| B: Cookbook 对外去 T | 内部 `400001T` → 给 SCC 发 `400001` | 增加转换层，需确保映射不丢失 |
| **C: Cookbook 对齐 SCC** | F 后缀 = frozen，无后缀 = thawed | Cookbook 内部调整最小 |

> ⚠️ **建议**：需要立即与 SCC team（Brandon / Sadhana）对齐。SCC 的 WSKU Split 文档已锁定 `4000555` = thawed，变更 SCC 的成本远高于 Cookbook 内部调整。

---

### 🔴 二、存量 40* Item Rename / Migration（高风险）

**PRD 原方案**：新建 frozen 40* 与已有 thawed 40* 做 sibling link，**已有 item number 不变，零风险**。

**新方案**：已有 40* 需加后缀。如 `400002`（thawed）→ 改为 `400002T`。

**风险点**：
- `400002` 已被大量 menu item BOM、fulfillment option、PCS 引用
- Item number rename = **全量引用更新**，任何一个遗漏都导致生产事故
- 菜单显示错误、库存匹配失败、订单出错

> ⚠️ **建议**：存量 thawed item 保持原号码不加 T，仅新创建的 frozen/thawed pair 使用新格式。避免全量数据迁移。

---

### 🟡 三、Item Number 唯一性逻辑

| 场景 | 原方案 | 新方案 |
|------|--------|--------|
| 唯一键 | `item_number` 全局唯一 | `(base_number, state)` 联合唯一 |
| 无 state 的 40* 能否存在？ | 可以，state 可选 | **不行**，会与 `400001F` / `400001T` 冲突 |
| 只有 frozen 的 standalone | 独立号码 `400001` | `400001F`，但 base `400001` 被占用 |

**矛盾**：PRD 允许 draft 时 state 为空，且 ambient 物品无需区分 frozen/thawed。新方案的 item number 格式**强制要求所有 40* 必须有一个 state**。

---

### 🟡 四、Item Number 生成逻辑

**原方案**：auto-increment，简单直接。

**新方案需支持**：

- 新建 standalone 40* → 分配 base number + state suffix
- 从已有 Generate complementary → 相同 base + 相反 suffix
- 校验 base number 冲突：`400001` 不允许与 `400001F` / `400001T` 共存
- 搜索 "400001" 需返回 `400001F` 和 `400001T`

---

### 🟡 五、Menu Item / HDR Recipe BOM

- BOM 组件引用从 `400001` 变为 `400001F` / `400001T`
- 存量 BOM 若 rename，需全量更新引用
- 搜索组件时需展示 state icon 和 F/T 标识
- "同一 menu item 不能同时使用 pairing 两状态"的校验逻辑不变

---

### 🟡 六、Pantry

来自 [PRD Open Questions #2](https://wonder.atlassian.net/wiki/spaces/~712020735951bb19ca4030aef4f98504f0b3da/pages/5145231396/Cookbook+Frozen+Thawed+40+Hot+Hold+PRD)：

- Pantry 通过 42 item number 获取 hot hold 信息
- Pantry hard code 的 "cook from frozen" 列表需更新引用
- 42 层的 F suffix 和 40 层的 F/T suffix 对齐后，Pantry 更容易做状态判断

---

### 🟢 七、KDS

PRD 已明确：KDS 不受影响（hot hold info 通过 42 item number 传递，KDS 无变更）。

---

### 🟡 八、Dormant / Delete 逻辑

- 共享 base number 使 pairing 关系更清晰
- 校验消息、warning message 中的 item number 格式需更新
- 逻辑本身不变：post-publish pairing 必须同进退

---

### 🟢 九、其他影响较小的模块

| 模块 | 影响 | 说明 |
|------|------|------|
| Hot Hold 配置 | 无变化 | 每个 state 独立配置，不依赖 item number 格式 |
| State 字段 | 保留 | Item number 编码了状态，但显式 state field 仍需保留（用于查询/过滤） |
| 变更日志 | 需更新 | state 字段变更记录 |
| 报表/分析 | 中等 | 按 item number 分组的报表需适配 |

---

## 影响矩阵总览

| 系统/模块 | 影响等级 | 关键变更 |
|-----------|---------|---------|
| **SCC Contract** | 🔴 阻断 | SCC 用 `4000555`（无T），Cookbook 新方案用 `4000555T`，必须对齐 |
| **存量 40* Migration** | 🔴 高风险 | 已有 item 加后缀 = 全量引用更新，建议只对新 pair 使用 |
| **Item Number 生成** | 🟡 中等 | 从 auto-increment 改为 base+suffix 联合生成 |
| **Item Number 唯一性** | 🟡 中等 | 唯一键从单字段变为复合字段 |
| **Menu Item BOM** | 🟡 中等 | 存量 BOM 引用格式变更 |
| **搜索/查询** | 🟡 中等 | 搜 "400001" 需返回 F 和 T 两个结果 |
| **Pantry** | 🟡 中等 | hard code 引用更新 |
| **PCS / Fulfillment** | 🟡 中等 | linkage 引用格式变更 |
| **报表 / 分析** | 🟡 中等 | group by item number 需适配 |
| **KDS** | 🟢 低 | 不受影响 |
| **Dormant / Delete** | 🟢 低 | 逻辑不变，消息格式微调 |
| **Hot Hold 配置** | 🟢 低 | 每个 state 独立配置 |

---

## 建议 & 待决策事项

1. **🔴 优先**：与 SCC team（Brandon / Sadhana）对齐 Contract 格式
   - 确认 SCC 能否接受 T 后缀，或统一用 SCC 规范（F 后缀 + thawed 无后缀）
   - 这是**阻断级问题**，必须在开发前解决

2. **🔴 优先**：存量 40* 不 rename
   - 已有 thawed item 保持原号码，仅新创建的 frozen/thawed pair 使用新格式
   - 避免全量数据迁移的极端风险

3. **🟡 需明确**：是否允许无 state / 无 suffix 的 40* 存在
   - 如果所有 40* 必须有 state，draft 阶段的空白如何处理？
   - Ambient 物品的 state 如何归类？

4. **🟡 需明确**：Generate complementary 时，base number 如何分配
   - 从已有 40* 的 base number 衍生
   - 还是新分配 base number 再建立关联？

---

*分析基于：*
- [Cookbook: Frozen/Thawed 40* & Hot Hold PRD](https://wonder.atlassian.net/wiki/spaces/~712020735951bb19ca4030aef4f98504f0b3da/pages/5145231396)
- [WSKU Frozen/Thawed Split](https://wonder.atlassian.net/wiki/spaces/FP1/pages/5122555921)
