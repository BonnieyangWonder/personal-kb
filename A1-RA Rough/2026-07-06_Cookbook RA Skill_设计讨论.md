---
date: 2026-07-06
updated: 2026-07-10
status: active
type: concept
tags:
  - cookbook
  - skill-design
  - requirements-analysis
---

# Cookbook RA Skill 设计讨论

> **这是一份持续更新的设计文档，不是一次性定稿。** Skill 上线使用后，会根据实际做 RA 时踩到的问题持续修订这份文档和 skill 本身，直到 RA skill 的行为摸索清楚、稳定下来为止。
>
> **这份文档记录"为什么这样设计"，不是操作手册**——skill 具体怎么运作，权威来源是下面两个文件，两边如果有冲突以它们为准：
> - Skill 内容：`.claude/skills/my-workflows/cookbook-ra.md`
> - 触发规则：`.claude/rules/cookbook-ra-workflow.md`
>
> 下次要继续迭代时：打开这个笔记，说"继续完善 RA skill"，并说清楚是哪次实际使用中发现的问题。

## 设计目标

按需求复杂度/明确度分两种输出深度，不是按需求内容类型分：

| 模式 | Skill 该表现出的能力 | 分析目标 |
|------|----------------------|---------|
| **模式 1 — 效率模式** | 基于现有逻辑 + 需求来源方情况做分析 | 更高效、更完善、没有遗漏 |
| **模式 2 — 专家模式** | 表现专业产品专家能力：基于对 cookbook 整体业务的理解 + 现有 feature，分析需求、提出解决方案、识别风险点 | 给出方案 + 风险识别，而非仅罗列现状 |

## 当前设计一览

详细规则都写在 skill 文件里，这里只做索引，避免两处维护同一份内容：

| 决策项 | 结论 | 详见 |
|--------|------|------|
| 判断机制 | **触发式升级**——不预先分类需求难度，固定跑一次 Stage 0 扫描，扫描中出现 6 个信号里任一个才升级到模式 2 | skill Step 3 |
| 资源清单 | 三层 Cookbook 知识（wonder-cookbook skill / CB-business / CB-full-feature）+ 9 个跨系统 skill + BigQuery + Jira/Confluence | skill Step 0 |
| 跨系统知识加载 | 自动加载，不停下来问；涉及多系统时开头提一句涉及哪些系统 | skill Step 0 |
| 分析深度 | 强制跑 BigQuery 做数据影响分析，不只是逻辑推理 | skill Step 2 |
| Skill 边界 | 不提议建 Jira ticket；不写入/更新 CB-full-feature 或 CB-business（那是 Bonnie 自己另外手动触发 biz-req / archive-jira-to-cb 的事） | skill Step 5 |
| 输出规范 | 存 `A1-RA Rough/`；文件名不用日期，有 ticket 就把 ticket 号放最前面；必须有 Reference Linkage 章节 | skill Output |
| 存放位置 | Bonnie 个人工作目录 `.claude/skills/my-workflows/`，不是团队共享的 `wonder-*` skill | — |
| 触发方式 | 自然语言识别意图（"分析下 XX 需求"/"ra 分析"+ ticket/链接/截图），不用死板的固定命令 | rule 文件 |

## 设计依据（为什么这样决定）

### 为什么不预先分类需求难度

vault 里 3 个真实 RA 案例，"表面看起来"和"实际展开后"完全不对应：

| 案例 | 表面看起来像 | 实际展开后 |
|------|-------------|-----------|
| [[2026-05-25_Gluten-Free_标签系统推断改人工指定_需求分析]] | 模式 1（改一个字段的来源） | 模式 2：食品安全合规、法律风险、8 个团队协调、分阶段 rollout、回滚方案 |
| [[2026-05-21_40_item_number_F-T_suffix_影响评估]] | 模式 1（技术命名方案决定） | 模式 2：撞上 SCC 团队 contract 的阻断级冲突、存量数据 rename 生产风险、唯一性逻辑根本矛盾。后来发现这是更大的 SCC 迁移项目的一部分 |
| [[2026-06-24_Wonder_Create_BYO_Customization_Analysis]] | 模式 1（数据分析找规律） | 模式 2：反向挖掘规律、设计全新自动分类规则引擎，关联更大 epic（MD-18146） |

三个案例全部从"听起来简单"变成"实际专家级"。**结论：复杂度是分析过程中才暴露的，不是需求文本自带的属性**——所以放弃了"按需求措辞自动判断模式"的最初想法，改成 Stage 0 固定扫描 + 信号触发升级（信号列表见 skill Step 3）。这套信号本身也是从这 3 个案例反推出来的，还只验证过一轮，用几次真实 RA 之后应该回来检查够不够全。

### 为什么 ticket 归档检查点用 sprint 号、不用日期

CB-full-feature 不是整体同步的，是 Bonnie 按 sprint 有空就手动增量归档，节奏不规律，文件更新日期反映不出真实进度。所以检查点必须是 Bonnie 直接给的 sprint 号（当前 = Sprint 7），skill 不应该尝试从文件日期自动推断。这条本身对需求分析影响不大，优先级低，先记着。

## 已知缺口（低优先级，暂不处理）

1. **团队/owner 联系人图谱**——vault 里没有，只在 Confluence"Cookbook system overview"页面
2. **后端代码库访问**——当前没有代码仓库的 external directory 权限，字段级细节可能需要标注"待代码验证"
3. **wonder-ladle**——已知是下游系统之一，但 skill 目前是空的，没有可用知识
4. **SCC 迁移 ticket 积压**——检查点 = Sprint 7，Sprint 8 起的 ticket 还没归档进 CB-full-feature，涉及 WSKU/40\*/41\*/fulfillment option 的需求要留意

## 待实践验证的假设

这些是设计时的最佳猜测，还没被真实用例验证过，用几次之后回来对照：

- 6 个升级信号够不够全，会不会漏掉某类真实场景
- Bonnie 提过的两个业务语言案例还没真正跑过 RA，可以作为下一批测试样本：
  - "餐厅 cook dish 时需要支持 timer"——已知 line-build.md 有 cook time/step time 概念，需判断这次需求和现有概念的差距
  - "App 引入第三方合作，需要 cookbook 配合让第三方菜品上架"——vault 里完全没有相关文档，是真实知识空白，会是模式 2 的一次真实压力测试
- 自然语言触发是否真的够灵敏，会不会漏判或误判成别的 skill

## 下次讨论的灵感 / 待展开的点

- **模式 1 在实践中会不会真的出现？** 目前 3 个参考案例全部从"看起来简单"升级成模式 2，还没见过真正停在模式 1 的真实样本。用一段时间后如果模式 1 一直不出现，值得讨论：是不是"值得写 RA 报告的需求"本身很少简单，模式 1 覆盖的其实主要是根本不需要写 RA 的微小改动？
- **知识陈旧的风险不止 CB-full-feature 一层。** wonder-cookbook skill 的 18 个 domain 文档标注"Last Validated: 2026-01-28"，到现在已经快半年——跟 CB-full-feature 的归档滞后是同一类问题（知识来源落后于真实系统状态），只是这次只深挖了 ticket 积压这一个来源。下次可以讨论要不要把"领域文档最后验证时间"也纳入 Stage 0 的检查范围。
- **CLAUDE.md 里 Knowlery 管理区块的手动改动还没完全验证过。** 之前手动加了 `cookbook-ra-workflow.md` 的 import 行，理论上风险很低（`archive-ticket-instruction.md` 的存在证明这套机制认 `.claude/rules/` 文件夹里的文件），但没有直接验证过插件重新生成时会不会保留。如果哪天"分析下 XX 需求"忽然不触发了，先去 `.claude/CLAUDE.md` 检查这一行还在不在，不在就加回去。
- **升级信号和内容分类轴会持续增长，不是一次性定案。** 新增的"归档后反推分析能力"机制（见下）会不断产出新证据，6 个升级信号和 A/B 两个内容轴大概率需要定期回来扩充/重新归类。

## 案例复盘记录（从已归档 ticket 反推分析能力）

每次 `archive-jira-to-cb` skill 执行完归档后（见该 skill 文件 Step 6），会把这个 ticket 当作 RA skill 的回溯测试样本：反推这个需求本该怎么分析，跟当前 `cookbook-ra.md` 的框架对比，把有价值的发现记在这里。**这里只积累证据，不直接改 skill 文件**——Bonnie 定期回顾这份记录，决定要不要据此更新 RA skill。

**反推分析时不局限于固定几个维度**（不是只看现有功能/影响点/关联功能/风险/分析维度这几项）——按这个具体 ticket 的实际情况，用专业判断带出真正相关的分析角度，跟 RA skill 本身"不预先分类、让复杂度自己浮现"的哲学保持一致。

目前还没有真实条目——下次执行完 `archive-jira-to-cb` 后，第一条记录会加在这里。

**每条记录用这个结构（分析内容本身自由展开，不是填空）：**

```
### [TICKET-KEY] <ticket 标题> —— 复盘于 YYYY-MM-DD

**这个需求真正需要覆盖的分析要点**（按实际情况展开，不限定类别/数量）：


**对比 cookbook-ra 框架的发现**：
- 现有框架覆盖到了：
- 现有框架没覆盖 / 覆盖不好：

**建议**（是否需要更新 skill，由 Bonnie 决定）：
```

## 版本记录

| 日期 | 变更 |
|------|------|
| 2026-07-06 | 首次讨论，定下背景和待确认问题清单 |
| 2026-07-06 ~ 2026-07-10 | 确定触发式升级方法论、完整资源清单（含未归档 ticket 缺口）、输出规范、skill 边界；创建 `cookbook-ra.md` + `cookbook-ra-workflow.md` 并接入 CLAUDE.md |
| 2026-07-10 | 精简重写本文档：去掉已经沉淀进 skill 文件的操作细节，只留设计依据、缺口、待验证假设，标记为持续更新的设计日志 |
| 2026-07-10 | 新增"下次讨论的灵感"和"案例复盘记录"两个章节；在 `archive-jira-to-cb.md` 里加了 Step 6，让归档后自动反推分析能力、沉淀到这份笔记 |
| 2026-07-10 | 复盘机制去掉固定 5 维度的框架，改成按具体 ticket 用专业判断自由展开——跟 RA skill 本身不预先分类的哲学保持一致 |

## 真实案例库（校验样本）

- [[2026-05-25_Gluten-Free_标签系统推断改人工指定_需求分析]]
- [[2026-05-21_40_item_number_F-T_suffix_影响评估]]
- [[2026-06-24_Wonder_Create_BYO_Customization_Analysis]]
