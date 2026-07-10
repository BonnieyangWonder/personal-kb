---
date: 2026-07-06
status: done
type: concept
tags:
  - cookbook
  - skill-design
  - requirements-analysis
---

# Cookbook RA Skill 设计讨论

> **状态：✅ 设计讨论完成，skill 已创建**
> - Skill 内容：`.claude/skills/my-workflows/cookbook-ra.md`
> - 触发规则：`.claude/rules/cookbook-ra-workflow.md`（已手动加入 CLAUDE.md 的 Knowlery 管理区块——**注意**：这个区块看起来由 Knowlery Obsidian 插件自动维护，本地没装 knowlery CLI 无法验证/触发正规注册流程，手动加的这行如果之后被插件重新生成时覆盖掉，需要重新加回 `.claude/CLAUDE.md`）
> - 剩余未解决的小缺口（低优先级，见资源清单 E 部分）：团队/owner 联系人图谱、后端代码库访问、wonder-ladle 知识空白
> - 下次要用：直接说"分析下 XX 需求"或"ra 分析" + 提供 ticket/链接/截图即可触发

## 背景

为 Wonder Cookbook 系统设计一个需求分析（RA）专用 skill，目标是提高需求分析的效率、准确性，提供合理高效正确的解决方案。

## 资源清单（Stage 0 扫描该查的清单本体）

这份清单是"触发式升级"流程里 Stage 0 固定扫描环节要对照的资源registry，未来会变成 RA skill 文件的 Resources 章节。

### A. Cookbook 领域知识——三层，从粗到细

| 层 | 位置 | 定位 | 何时用 |
|---|------|------|--------|
| **wonder-cookbook skill** | `.claude/skills/wonder-cookbook/` | 数据/查询层打包入口：18 个 domain 文档 + schema-reference + common-pitfalls，已用 Java 代码库验证字段映射（120+ domain model、60+ service class、100+ API endpoint 已关联） | 需要 SQL 模式、字段语义、代码引用时——优先激活这个 skill，效率最高 |
| **CB-business** | `Z01-Resource/CB-business/` | 业务规则/产品逻辑层：core/（通用概念）+ features/（具体字段计算逻辑）+ 2 篇跨系统分析。自带 Trigger Topics 路由表 | 需要理解字段计算逻辑/规则边界 |
| **CB-full-feature** | `Z01-Resource/CB-full-feature/` | UI/功能点粒度详情，Confluence "Cookbook Full Features Detail Requirements" 空间完整镜像（179 页，2026-06-12 抓取）。惰性加载——从索引页找具体页面 | 需要知道 UI 上具体配置/校验逻辑。**注意：抓取时间点之后的内容可能滞后，见下方 Jira 缺口条目** |

**重要发现**：`.claude/skills/wonder-cookbook/{core,domains,cross-system,reference}/` 和 `Z01-Resource/CB-bigquery/` 文件名几乎一一对应，是同一份知识的两种呈现形式。调用 wonder-cookbook skill 通常已足够，不需要重复翻 CB-bigquery 原始文件夹。

### B. 跨系统 skills（需求涉及 Cookbook 以外系统时按需加载）

| Skill | 覆盖范围 |
|---|------|
| wonder-pantry | HDR 库存：waste、slacking、hot holding、menu availability |
| wonder-orders | 订单/销售数据：channel performance、order-to-eat |
| wonder-otr | On-Time Rate 绩效 + Root Cause Analysis |
| wonder-sporklift | 仓储（ShipHero 3PL）：库存流水、lot/batch、PO fulfillment |
| wonder-supply-chain | POMS 采购订单系统 |
| wonder-menu-availability | 门店级菜单可用性（active_menu_v2） |
| wonder-command-center | 订单拆分 Splitter 规则引擎 |
| wonder-sequencing | 厨房排序优化 |
| wonder-kitchen-ops | Batching eligibility |
| ⚠️ wonder-ladle | WIP，基本是空的——但 F/T suffix 案例证实 Ladle 是真实下游系统之一，已知缺口 |

### C. 活数据源

- **BigQuery**（4 datasets, 70+ 表）——验证实际影响面
- **Jira / Confluence**（`mcp-atlassian`，已确认连接）——原始需求常从这里发起
- **⚠️ 未归档的近期 Jira ticket（新发现的重要缺口）**：
  - **范围**：MD 项目，Cookbook Board（board_id=846）。**检查点：已归档至 Sprint 7**（Bonnie 直接确认，非文件推断）——未归档范围是 `MD 2026 Sprint 8` 起到当前 `MD 2026 Sprint 14`（2026-06-29~07-13，进行中）
  - **规模**：已确认 100+ 张 ticket（分页未翻完，估计大几百张）
  - **内容主题高度集中于一个进行中的项目：SCC（Supply Chain Catalog）迁移**——WSKU/40\\*/41\\*/88\\* item 与 SCC 的同步、sold status 调整、fulfillment option/PCS 变更（如 MD-17694 "SCC migration main workflow"）
  - **与案例库的联系**：[[2026-05-21_40_item_number_F-T_suffix_影响评估]] 正是这个 SCC 迁移项目里的一环，证实这是正在进行、规模不小的真实项目，不是孤立历史案例
  - **查询方式（JQL）**：`project = MD AND sprint in ("MD 2026 Sprint <检查点+1>", ..., "<当前 sprint>")`。**检查点必须用 sprint 号维护，不能用日期**——CB-full-feature 是按 ticket/sprint 增量归档（Bonnie 有空就处理之前 sprint 的内容），归档节奏不规律，文件更新日期反映不出真实进度。检查点是 Bonnie 手动维护的状态（当前 = Sprint 7），skill 不应尝试从文件日期自动推断，每次 RA 前直接问 Bonnie 当前检查点即可
  - **实践含义**：任何涉及 WSKU/40\\*/41\\*/SCC/fulfillment option/PCS 的新需求，Stage 0 必须查这批 ticket——CB-full-feature/CB-business 对这个领域的"现状"很可能已经过时

### D. 关键发现：RA 是需求生命线的中间环节，不是孤立 skill

```
新需求出现（业务语言 / Jira ticket）
   ↓
【RA skill，设计中】分析现状 + 提方案 + 识别风险 → A1-RA Rough/*.md
   ↓ 需要落地开发
create-jira-ticket → Jira
   ↓ 开发完成后正式归档
biz-req → CB-business/*.md   和/或   archive-jira-to-cb → CB-full-feature/*.md
```

- **biz-req**（`.claude/skills/my-workflows/biz-req.md`）：把已讨论/已定案的需求从 Jira/Confluence 整理成 `CB-business/` 的正式业务需求文档。事后归档整理，非事前分析。资源抓取模式值得借鉴：ticket + Confluence 正文 + footer comments + inline comments + child pages + 引用页。
- **archive-jira-to-cb**（`.claude/skills/my-workflows/archive-jira-to-cb.md`）：把已完成 ticket 归档进 CB-full-feature UI 文档树。也是事后动作。上面发现的 SCC 迁移 ticket 堆积，正是这个 workflow 的待办积压。
- **create-jira-ticket**：RA 分析完成后落地开发用。

### E. 已确认的缺口

1. **团队/owner 联系人图谱**：vault 里没有，只存在于 Confluence"Cookbook system overview"页面。
2. **后端代码库访问**：Gluten-Free RA 附录列了具体 Java 类路径，但当前会话没有被授予代码仓库 external directory 权限。**待 Bonnie 确认**：以后做 RA 时会给代码仓库路径作为 external directory 吗？
3. **wonder-ladle**：已知下游系统，但目前无可用知识。
4. **未归档 Jira ticket 积压**（见 C）：检查点 = Sprint 7，Sprint 8 起未归档，SCC 迁移主题，100+ 张未同步进 CB-full-feature。**优先级：低**——对当前需求分析影响不大，先记录，后续再完善（比如要不要在 CB-full-feature 里显式记录检查点）。

**待 Bonnie 确认**：
1. 这份资源清单是否完整？
2. 代码库访问问题怎么处理？

（SCC 迁移 ticket 积压的处理方式已确认：Bonnie 自己按节奏用 archive-jira-to-cb 增量归档，不是紧急项，RA 时按当前检查点活查即可，不需要额外安排批量归档时间。）

## 方法论：触发式升级（Stage 0 扫描 → 信号触发 → 决定深度）

不预先分类需求类型，而是让 skill 永远从同一个轻量扫描动作开始（对照上面的资源清单），扫描中发现的具体信号决定是否升级到模式 2。

### 证据：3 个真实案例的"表面 vs 实际"对比

| 案例 | 表面看起来像 | 实际展开后 |
|------|-------------|-----------|
| [[2026-05-25_Gluten-Free_标签系统推断改人工指定_需求分析]] | 模式 1（改一个字段的来源） | 模式 2：食品安全合规、法律风险、8 个团队协调、分阶段 rollout、回滚方案 |
| [[2026-05-21_40_item_number_F-T_suffix_影响评估]] | 模式 1（技术命名方案决定） | 模式 2：撞上 SCC 团队 contract 的阻断级冲突、存量数据 rename 生产风险、唯一性逻辑根本矛盾。**现已知这是更大的 SCC 迁移项目的一部分** |
| [[2026-06-24_Wonder_Create_BYO_Customization_Analysis]] | 模式 1（数据分析找规律） | 模式 2：反向挖掘规律、设计全新自动分类规则引擎，关联更大 epic（MD-18146） |

**结论**：复杂度是分析过程中才暴露的，不是需求文本自带的属性。已放弃"按需求措辞自动判断模式"的旧假设。

**已知升级信号（待 Bonnie 补充/确认）：**

| 触发信号 | 案例证据 |
|---------|---------|
| 触及其他团队已依赖的 contract/边界 | F/T suffix 撞上 SCC 的 `4000555=thawed` 假设 |
| 违反现有系统的不变量/假设 | item_number 唯一性变化；系统推断→人工指定打破无人在环假设 |
| 需要对存量生产数据做结构性变更 | F/T suffix 的 item number rename = 全量引用更新风险 |
| 涉及合规/法律/食品安全等非纯技术风险 | Gluten-Free 过敏原声明风险 |
| 没有现成模式可以照搬，需要设计新机制 | BYO 的 Material Category 自动分类规则 |
| 需要跨 3+ 团队协调 | Gluten-Free 涉及 8 个团队 |

**提议的 skill 流程：**

```
Stage 0 · 固定扫描（对照资源清单，成本低）
  → 定位涉及的 feature/object_type/跨系统 skill
  → 查有没有类似机制的现有实现
  → 查有没有其他系统/团队对这个字段有依赖或 contract（含近期未归档 ticket）
  → 查是否涉及存量生产数据

  触发任一升级信号？
  否 → 模式 1 输出：现状 + 改动点 + 核对清单
  是 → 模式 2 输出：方案设计 + 跨团队矩阵 + 风险 + 路线图
```

**关键设计点**：判断不是一次性的。模式 1 分析过程中如果挖出升级信号，skill 要主动说明并升级，而不是被最初判断锁死。

## 核心指导方向（Bonnie 原话，仍然有效）

| 模式 | Skill 该表现出的能力 | 分析目标 |
|------|----------------------|---------|
| **模式 1 — 效率模式** | 基于现有逻辑 + 需求来源方情况做分析 | 更高效、更完善、没有遗漏 |
| **模式 2 — 专家模式** | 表现专业产品专家能力：基于对 cookbook 整体业务的理解 + 现有 feature，分析需求、提出解决方案、识别风险点 | 给出方案 + 风险识别，而非仅罗列现状 |

**Bonnie 提供的模式 2 业务语言案例（尚未验证，作为未来测试样本）：**
1. "餐厅 cook dish 时需要支持 timer" —— 已知 line-build.md 有 cook time / step time 等既有概念，需判断差距
2. "App 引入第三方合作，需要 cookbook 配合让第三方菜品上架" —— vault 中无任何相关文档，真实知识空白

## Q1 回复：典型需求场景 / 内容轴 A-B 分类（已确认）

| 类别 | 定义 | 驱动力 | 示例 |
|------|------|--------|------|
| **A. 业务规则/能力调整** | 校验逻辑、数据维护规则、新增字段、新增 feature、API 变更 | 通常由下游系统需求驱动 | Gluten-Free；F/T suffix |
| **B. Item 类型属性管理** | 9 种 object_type（见 [[Cookbook Item Taxonomy]]）各自的通用/专属属性变更 | 通常由产品/业务流程需求驱动 | BYO Customization 分类规则 |

内容分类轴（A/B）决定去哪些知识源找资料；复杂度轴（模式1/2）决定分析深度，由触发式升级机制判断。

## RA 输出规范（已确认）

- **位置**：`A1-RA Rough/`（注：vault 规则 report-paths.md 写的是 A2，需要在 skill 定稿时统一）
- **命名**：`YYYY-MM-DD_<Topic>_<描述>.md`；**若分析基于具体 Jira ticket，文件名必须包含 ticket number**——提议格式 `YYYY-MM-DD_<TICKET-KEY>_<Topic>_<描述>.md`（例：`2026-07-10_MD-17701_Timer支持_需求分析.md`，ticket key 放在日期后、Topic 前，方便按 ticket 扫描/搜索）。**待 Bonnie 确认这个位置是否OK，或者你想放在别的地方（比如放最后）**
- **必须包含 Reference Linkage 章节**：相关 Jira ticket 链接、Confluence 页面链接、相关的其他 RA 文档/CB-business/CB-full-feature 页面 wikilink——跟 vault 全局的 citation-required 规则保持一致
- **不衔接 biz-req / archive-jira-to-cb**：RA 只产出分析报告本身，不写入/更新 CB-full-feature 或 CB-business（理由见上方 Q4）

### 真实 RA 案例库（3 篇，用于校验 skill 设计）
  - [[2026-05-25_Gluten-Free_标签系统推断改人工指定_需求分析]]
  - [[2026-05-21_40_item_number_F-T_suffix_影响评估]]
  - [[2026-06-24_Wonder_Create_BYO_Customization_Analysis]]

## 待 Bonnie 回复的问题

### 3. 分析深度（已确认）
默认做数据影响分析——RA 时自动跑 BigQuery 验证实际影响面（"多少 item/多少 HDR 受影响"），不是只做逻辑推理 + 方案设计。

### 4. Skill 边界
- RA 结束是否自动提议创建 Jira ticket？——**待确认**
- 是否自动加载跨系统子 skill 的知识？——**已确认**：自动加载，Stage 0 判断到相关就直接查，不停下来问；涉及多个系统时开头提一句涉及哪些系统即可
- 是否要衔接 biz-req / archive-jira-to-cb？——**已确认：不衔接**。RA 只负责产出分析报告，不更新 CB-full-feature / CB-business。**CB-full-feature 只记录已进入开发/已上线的 feature**——RA 阶段的分析还没到那个成熟度，不属于它的范围。后续要不要归档，是 Bonnie 自己另外手动决定、触发 biz-req/archive-jira-to-cb 的事，跟 RA skill 无关

### 5. 命名和触发
- `/ra`？
- `/cookbook-ra`？—— 助手建议此项
- 其他？

---

## 已有确定项

| 项目 | 决定 |
|------|------|
| **核心指导方向** | 模式 1（效率）+ 模式 2（专家方案+风险）双模式，按需求复杂度区分 |
| **判断机制** | 触发式升级（Stage 0 扫描 + trigger 列表），非预先分类 |
| **资源清单** | 已盘点完成（见上，含未归档 Jira ticket 缺口），待 Bonnie 确认完整性 + 代码库访问问题 |
| **RA 定位** | 需求生命线中间环节，但**不自动衔接**：RA 只产出报告，biz-req/archive-jira-to-cb 是 Bonnie 后续手动触发的独立步骤 |
| **分析深度** | 默认做数据影响分析（自动跑 BigQuery），不只是逻辑推理 |
| **跨系统知识加载** | 自动加载，不停下来问；涉及多系统时开头提一句涉及哪些系统 |
| **RA 输出规范** | 位置 `A1-RA Rough/`；命名含 ticket number（若基于具体 ticket，位置待确认）；必须含 Reference Linkage 章节；不写入 CB-full-feature/CB-business |
| 领域知识 | wonder-cookbook skill（含 CB-bigquery 等效内容）+ CB-business + CB-full-feature |
| 数据源 | 4 BigQuery datasets + Jira/Confluence（mcp-atlassian）+ MD 2026 Sprint 8 起未归档 ticket（检查点=Sprint 7，SCC 迁移主题） |
| 输出路径 | `A1-RA Rough/`（待统一 vault 规则里的 A2 拼写） |
| 关联系统 | Pantry/Orders/Sequencing/Supply Chain/Kitchen Ops/Sporklift/Command Center/Menu Availability/OTR（Ladle 缺口待补） |
| 语言 | 中英混合（按需求方来源决定） |
| 内容分类轴 | A. 业务规则/能力调整　B. Item 类型属性管理 |
