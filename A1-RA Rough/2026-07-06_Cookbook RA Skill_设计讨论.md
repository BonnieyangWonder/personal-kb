---
date: 2026-07-06
updated: 2026-07-13
status: active
type: concept
tags:
  - cookbook
  - skill-design
  - requirements-analysis
---

# Cookbook RA Skill 设计讨论

> **持续更新的设计文档，不是操作手册。** 记录"为什么这样设计"；skill 具体怎么运作，以下面两个文件为准，冲突时它们优先：
> - Skill 内容：`.claude/skills/my-workflows/cookbook-ra.md`
> - 触发规则：`.claude/rules/cookbook-ra-workflow.md`
>
> 继续迭代时：打开这个笔记，说"继续完善 RA skill"，并说明是哪次实际使用中发现的问题。

## 设计目标

按需求复杂度/明确度分两种输出深度，不是按需求内容类型分：

| 模式 | Skill 该表现出的能力 | 分析目标 |
|------|----------------------|---------|
| **模式 1 — 效率模式** | 基于现有逻辑 + 需求来源方情况做分析 | 更高效、更完善、没有遗漏 |
| **模式 2 — 专家模式** | 表现专业产品专家能力：基于对 cookbook 整体业务的理解 + 现有 feature，分析需求、提出解决方案、识别风险点 | 给出方案 + 风险识别，而非仅罗列现状 |

## 当前设计一览

详细规则都在 skill 文件里，这里只做索引：

| 决策项 | 结论 | 详见 |
|--------|------|------|
| 判断机制 | **触发式升级**——不预先分类需求难度，固定跑 Stage 0 扫描，出现 6 个信号中任一个才升级到模式 2 | skill Step 3 |
| 资源清单 | 三层 Cookbook 知识（wonder-cookbook skill / CB-business / CB-full-feature）+ 9 个跨系统 skill + BigQuery + Jira/Confluence | skill Step 0 |
| 跨系统知识加载 | 自动加载，不停下来问；涉及多系统时开头提一句 | skill Step 0 |
| 分析深度 | 强制跑 BigQuery 做数据影响分析 | skill Step 2 |
| Skill 边界 | 不提议建 ticket；不写入 CB-full-feature/CB-business（那是 Bonnie 手动触发 biz-req / archive-jira-to-cb 的事） | skill Step 5 |
| 输出规范 | 存 `A1-RA Rough/`；文件名不用日期，有 ticket 就把 ticket 号放最前面；必须有 Reference Linkage | skill Output |
| 存放位置 | 个人目录 `.claude/skills/my-workflows/`，非团队 `wonder-*` skill | — |
| 触发方式 | 自然语言识别意图，不用固定命令 | rule 文件 |

## 设计依据

vault 里 3 个真实 RA 案例，"表面看起来"和"实际展开后"完全不对应：

| 案例 | 表面看起来像 | 实际展开后 |
|------|-------------|-----------|
| [[2026-05-25_Gluten-Free_标签系统推断改人工指定_需求分析]] | 模式 1（改一个字段的来源） | 模式 2：食品安全合规、法律风险、8 个团队协调、分阶段 rollout、回滚方案 |
| [[2026-05-21_40_item_number_F-T_suffix_影响评估]] | 模式 1（技术命名方案决定） | 模式 2：撞上 SCC 团队 contract 的阻断级冲突、存量数据 rename 生产风险、唯一性逻辑根本矛盾。后来发现是更大的 SCC 迁移项目的一部分 |
| [[2026-06-24_Wonder_Create_BYO_Customization_Analysis]] | 模式 1（数据分析找规律） | 模式 2：反向挖掘规律、设计全新自动分类规则引擎，关联更大 epic |

三个案例全部从"听起来简单"变成"实际专家级"——**复杂度是分析过程中才暴露的，不是需求文本自带的属性**。这是放弃"按需求措辞判断模式"、改用 Stage 0 扫描 + 信号触发升级的核心依据（信号列表见 skill Step 3）。

## 已知缺口（低优先级）

1. **团队/owner 联系人图谱**——vault 里没有，只在 Confluence"Cookbook system overview"页面
2. **后端代码库访问**——当前无代码仓库权限，字段级细节需标注"待代码验证"
3. **wonder-ladle**——已知是下游系统之一，但目前无可用知识
4. **SCC 迁移 ticket 积压**——检查点 = Sprint 7，之后的 ticket 还没归档进 CB-full-feature，涉及 WSKU/40\*/41\*/fulfillment option 的需求要留意

## 待观察 / 下次讨论

- 6 个升级信号 + A/B 内容分类轴是从 3 个案例反推的，只验证过一轮——用几次真实 RA 后回来看够不够全（案例复盘机制会持续产出新证据，见下）
- 模式 1 目前还没有真实案例出现过（3 个参考案例全升级到模式 2）——如果长期不出现，可能说明"值得写 RA 的需求"本身很少简单
- 知识陈旧的风险不止 CB-full-feature：wonder-cookbook skill 的 domain 文档标注"Last Validated: 2026-01-28"，已半年没验证——要不要把"领域文档最后验证时间"也纳入 Stage 0
- CLAUDE.md 里手动加的 `cookbook-ra-workflow.md` import 行还没验证过插件重新生成时会不会保留——如果"分析下 XX 需求"哪天不触发了，先查这一行还在不在
- 两个业务语言案例还没真正跑过 RA，可作为下一批测试样本：支持 timer（已有 cook time/step time 概念，需判断差距）、第三方合作上架（vault 里完全空白，模式 2 的真实压力测试）
- 自然语言触发灵不灵、会不会跟别的 skill 误判，也待观察

## 案例复盘记录（从已归档 ticket 反推分析能力）

每次 `archive-jira-to-cb`（见其 Step 6）归档完一张 ticket 后，把它当 RA skill 的回溯测试样本：用专业判断反推这个需求真正该怎么分析（不设固定维度），跟 `cookbook-ra.md` 当前框架对比，把有价值的发现记在这里。**只积累证据，不直接改 skill 文件**——Bonnie 定期回顾，决定要不要据此更新。

目前还没有真实条目。

**记录格式：**

```
### [TICKET-KEY] <ticket 标题> —— 复盘于 YYYY-MM-DD

**这个需求真正需要覆盖的分析要点**（自由展开，不限类别/数量）：


**对比 cookbook-ra 框架的发现**：
- 现有框架覆盖到了：
- 现有框架没覆盖 / 覆盖不好：

**建议**（是否需要更新 skill，由 Bonnie 决定）：
```

## 版本记录

| 日期 | 变更 |
|------|------|
| 2026-07-06 | 首次讨论 |
| 2026-07-06 ~ 07-10 | 定下触发式升级方法论、资源清单、输出规范、skill 边界；创建 `cookbook-ra.md` + `cookbook-ra-workflow.md`；`archive-jira-to-cb.md` 加 Step 6 建立案例复盘机制 |
| 2026-07-13 | 精简重写：去掉讨论过程中已解决、无持续参考价值的细节，只留有价值的依据、缺口和待观察项 |

## 真实案例库（校验样本）

- [[2026-05-25_Gluten-Free_标签系统推断改人工指定_需求分析]]
- [[2026-05-21_40_item_number_F-T_suffix_影响评估]]
- [[2026-06-24_Wonder_Create_BYO_Customization_Analysis]]
