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

> **状态：等待 Bonnie 提供 5 个问题的回复**
> 下次继续时：打开这个笔记，说"继续讨论 RA skill"

## 背景

为 Wonder Cookbook 系统设计一个需求分析（RA）专用 skill，目标是提高需求分析的效率、准确性，提供合理高效正确的解决方案。

## 已完成的分析

### 现有资源
- **wonder-cookbook skill**：覆盖 18 个 domain doc + schema reference + 70+ 表
- **数据源**：4 BigQuery datasets，标准 query pattern 已建立
- **RA 输出路径**：`A2-RA Rough/YYYY-MM-DD_<Topic>_<描述>.md`
- **关联系统 skills**：Pantry / Orders / Sequencing / Supply Chain / Kitchen Ops
- **现有 RA 范例**：[[2026-05-25_Gluten-Free_标签系统推断改人工指定_需求分析]]（结构完整，可作为模板参考）

### Skill 结构参考
- `wonder-cookbook/SKILL.md`：YAML frontmatter + 主文件 + 子目录
- `create-jira-ticket.md`：单文件 skill，含完整工作流

## 待 Bonnie 回复的 5 个问题

### 1. 典型需求场景（最重要）
日常收到的需求类型？例如：
- 字段从自动计算改人工指定
- 新增 item 类型/分类标签
- BOM 结构变更影响分析
- 业务规则调整
- 跨系统数据对齐
- 其他？

### 2. 期望的 RA 输出格式
- A: 严格按 Gluten-Free 模板（Background → System Analysis → Solution → Impact → Cross-team → Roadmap → Decisions → Risk）
- B: 简化版（适合中小需求）
- C: 多档模式（快速分析 vs 完整 RA）

### 3. 分析深度
- 是否自动跑 BigQuery 做数据影响分析？
- 还是主要做逻辑推理 + 方案设计？

### 4. Skill 边界
- RA 结束是否自动提议创建 Jira ticket？
- 是否自动加载跨系统子 skill 的知识？

### 5. 命名和触发
- `/ra`？
- `/cookbook-ra`？
- 其他？

---

## 已有确定项

| 项目 | 决定 |
|------|------|
| 领域知识 | 复用 wonder-cookbook skill |
| 数据源 | 4 BigQuery datasets |
| 输出路径 | `A2-RA Rough/` |
| 关联系统 | Pantry/Orders/Sequencing/Supply Chain/Kitchen Ops |
| 语言 | 中英混合（按需求方来源决定） |
