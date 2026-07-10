---
date: 2026-07-06
status: in-progress
type: concept
tags:
  - cookbook
  - skill-design
  - requirements-analysis
---

# Cookbook RA Skill 设计讨论

> **状态：Q1 已回复，等待 Bonnie 回复 Q2-5 + 一个追问**
> 下次继续时：打开这个笔记，说"继续讨论 RA skill"

## 背景

为 Wonder Cookbook 系统设计一个需求分析（RA）专用 skill，目标是提高需求分析的效率、准确性，提供合理高效正确的解决方案。

## 已完成的分析

### 现有资源
- **wonder-cookbook skill**：覆盖 18 个 domain doc + schema reference + 70+ 表
- **数据源**：4 BigQuery datasets，标准 query pattern 已建立
- **RA 输出路径**：`A1-RA Rough/YYYY-MM-DD_<Topic>_<描述>.md`（注：笔记曾误写 A2-RA Rough，实际用的是 A1；vault 规则 report-paths.md 也写的是 A2，需要在 skill 定稿时统一）
- **关联系统 skills**：Pantry / Orders / Sequencing / Supply Chain / Kitchen Ops
- **现有 RA 范例**：[[2026-05-25_Gluten-Free_标签系统推断改人工指定_需求分析]]（结构完整，可作为模板参考）

### Skill 结构参考
- `wonder-cookbook/SKILL.md`：YAML frontmatter + 主文件 + 子目录
- `create-jira-ticket.md`：单文件 skill，含完整工作流

## Q1 回复：典型需求场景（已确认）

Bonnie 给出两大类，不限于此：

| 类别 | 定义 | 驱动力 | 示例 |
|------|------|--------|------|
| **A. 业务规则/能力调整** | 校验逻辑、数据维护规则、新增字段、新增 feature、API 变更 | 通常由下游系统需求驱动（Cookbook 是 Wonder 平台 item 基础数据 source 及维护平台） | Gluten-Free 案例；新增字段支持某下游 API |
| **B. Item 类型属性管理** | 9 种 object_type（见 [[Cookbook Item Taxonomy]]）各自的通用/专属属性变更，及配套业务管理流程 | 通常由产品/业务流程需求驱动 | 新增某 type 专属属性；调整某属性的校验/审批流程 |

**关联发现**：知识库里没有统一的"属性总表"。属性/业务规则文档分散在：
- `Z01-Resource/CB-business/core/item-and-object-type.md`（基础属性 + object_type 规则）
- `Z01-Resource/CB-business/features/*.md`（按 feature 领域切分：customization / item-cost / line-build / menu-price / nutrition-allergens / sold-status / version-publish / wonder-create）

**设计影响**：涉及属性变更的需求，skill 需要先判断"这个属性属于哪个 feature 领域"，再去对应文档交叉定位，而不能假设有单一属性索引可查。

**待追问**：是否已有内部文档/Confluence 系统性列出"每个 object_type 的完整属性清单"？还是目前就是分散在各 feature 文档里，需要 skill 自己动态拼装？

**待讨论**：A 类常需要"下游影响分析"（谁在用这个字段/API），B 类常需要"跨 type 一致性分析"（这个属性在其他 type 里怎么处理，会不会打破通用规则）。skill 是否要针对两类走不同分析框架，而非一套模板套所有需求？

## 待 Bonnie 回复的问题（Q2-5）

### 2. 期望的 RA 输出格式
- A: 严格按 Gluten-Free 模板（Background → System Analysis → Solution → Impact → Cross-team → Roadmap → Decisions → Risk）
- B: 简化版（适合中小需求）
- C: 多档模式（快速分析 vs 完整 RA）—— 助手建议此项

### 3. 分析深度
- 是否自动跑 BigQuery 做数据影响分析？
- 还是主要做逻辑推理 + 方案设计？

### 4. Skill 边界
- RA 结束是否自动提议创建 Jira ticket？
- 是否自动加载跨系统子 skill 的知识？

### 5. 命名和触发
- `/ra`？
- `/cookbook-ra`？—— 助手建议此项（避免与其他领域 RA 冲突）
- 其他？

---

## 已有确定项

| 项目 | 决定 |
|------|------|
| 领域知识 | 复用 wonder-cookbook skill |
| 数据源 | 4 BigQuery datasets |
| 输出路径 | `A1-RA Rough/`（待统一 vault 规则里的 A2 拼写） |
| 关联系统 | Pantry/Orders/Sequencing/Supply Chain/Kitchen Ops |
| 语言 | 中英混合（按需求方来源决定） |
| 需求场景分类 | A. 业务规则/能力调整　B. Item 类型属性管理 |
