---
title: 我的 Skills 清单
created: 2026-07-17
updated: 2026-08-17
tags: [meta, skills, index, 个人]
---

# 我的 Skills 清单

> 一份 skill 总览:**有哪些、在哪、个人还是团队、各自做什么**。
> 专治「分不清哪个是我自己的 skill」。手动维护，最后更新 2026-08-17。

## 🚀 快速找 Skill

**我要…** → **用这个 Skill**

- 分析 Cookbook 需求 → **cookbook-ra**（📋 RA 分析）
- 把 ticket 功能归档 → **archive-jira-to-cb**（📦 归档功能）
- 生成业务需求文档 → **biz-req** 或 **sediment-cookbook-feature-reqs**（📄 业务需求）
- 建 Jira ticket → **create-jira-ticket**（🎫 建 Ticket）
- 同步 Jira 到 Confluence → **sync-ticket-to-confluence**（🔄 同步到 Confluence）
- 同步 Sprint ticket 清单 → **sync-sprint-tickets-to-obsidian**（🔗 同步 Sprint 清单）
- 检查 40* item → **check-40-item-fulfillment**（✅ 检查 Item）
- 创建周会议程 → **xm-ny-weekly-planning**（📅 周会议程）
- 查 Cookbook 数据 → **wonder-cookbook**（🍳 菜单配方）
- 查 OTR 绩效 → **wonder-otr**（⏱️ 准时绩效）
- 查其他业务数据 → 看下方**🔵 团队 Skills**表

## 一眼分类(位置 = 归属)

| 归属 | 位置 | 谁维护 |
|---|---|---|
| 🟢 **个人 skill** | `.claude/skills/my-workflows/` | 我自己(Bonnie) |
| 🔵 **团队 skill** | `.claude/skills/wonder-*/` | 团队共享(domain 知识) |
| 📚 **知识库 / 资源** | `Z01-Resource/CB-*/` | 我维护的 Cookbook 知识库(被个人 workflow 读写,本身不是 workflow) |
| ⚙️ **系统 / 框架 skill** | `.claude/skills/`(其余) | Knowlery / Obsidian / agent 内置 |

**判断口诀**:在 `my-workflows/` 里 = 我的;`wonder-` 开头 = 团队;`Z01-Resource/CB-` = 我的知识库(不是 workflow)。

---

## 🟢 个人 Skills —— `.claude/skills/my-workflows/`

| 一眼看出 | Skill | 文件 | 做什么 |
|---|---|---|---|
| 📋 RA 分析 | **cookbook-ra** | `cookbook-ra.md` | 分析 Cookbook 需求 → 数据影响分析 → 生成 RA 报告。触发:「分析下 XX 需求」「RA 一下」 |
| 📦 归档功能 | **archive-jira-to-cb** | `archive-jira-to-cb.md` | 把 Jira ticket 需求归档进 CB-full-feature（已上线功能文档）。触发:「把 ticket 归档到 RA」 |
| 📄 业务需求 | **biz-req** | `biz-req.md` | 编译 Jira/Confluence 需求为业务需求文档，写进 CB-business |
| 🔄 同步到 Confluence | **sync-ticket-to-confluence** | `sync-ticket-to-confluence.md` | 对比 Jira ticket vs Confluence 页面，给出 diff，确认后更新 Confluence（英文） |
| 🎫 建 Ticket | **create-jira-ticket** | `create-jira-ticket.md` | 建 Jira ticket（MD 项目、Story）。⚠️ 注意：顶层有同名文件 `.claude/skills/create-jira-ticket.md`，规则用的是**顶层**那份 |
| 📅 周会议程 | **xm-ny-weekly-planning** | `xm-ny-weekly-planning.md` | 建当周「XM NY Weekly Planning」Confluence 页面（RT 空间）。⚙️ **每周一 15:00 自动运行**，也可手动触发 |
| 🏗️ 业务需求 | **sediment-cookbook-feature-reqs** | `sediment-cookbook-feature-reqs.md` | 沉淀 Cookbook 功能/字段的业务需求文档到 CB-business/features 存档库。触发:「沉淀业务需求」+[链接/图片/文字] |
| ✅ 检查 Item | **check-40-item-fulfillment** | `check-40-item-fulfillment.md` | 批量检查 40* item 背后是否有可用 fulfillment option。按 concept→brand 排除正常项，查 40F/40/41 兜底路径。触发:「查一下这些40有没有fulfillment」或直接甩编号 |
| 🔗 同步 Sprint 清单 | **sync-sprint-tickets-to-obsidian** | `sync-sprint-tickets-to-obsidian.md` | 从 Jira 拉取 Sprint ticket，自动更新 [[个人/ticket 归档]]。**保留你的"是否归档"标记不覆盖**。触发:「把 Sprint 16 同步到 ticket 归档」 |

---

## 🔵 团队 Skills —— `.claude/skills/wonder-<name>/`

| 一眼看出 | Skill | 做什么 |
|---|---|---|
| 🍳 菜单配方 | **wonder-cookbook** | Cookbook recipe/BOM 系统：菜品配方、组件结构、菜单可用性逻辑 |
| 📦 拆单逻辑 | **wonder-command-center** | Command Center 拆单系统：分析 item 为什么被分到某个 order |
| 👨‍🍳 厨房运营 | **wonder-kitchen-ops** | 厨房作业：batching 资格、fryer batching、BOM↔linebuild↔sequencing 关系 |
| 📋 菜单可用性 | **wonder-menu-availability** | HDR 菜单可用性：active_menu_v2（现行）/ active_menu（旧版） |
| 📊 订单销售 | **wonder-orders** | 订单/销售数据：hdr_orders、order_items、满意度、渠道、准时率 |
| ⏱️ 准时绩效 | **wonder-otr** | On-Time Rate 绩效 + 根因分析，生成分层报告。触发:「generate WBR summary」 |
| 📦 门店库存 | **wonder-pantry** | HDR 库存管理：waste、盘点、库存移动、slacking、hot holding、可用性 |
| 🔀 厨房排序 | **wonder-sequencing** | Sequencing optimizer：批次分组、holdback、排序逻辑 |
| 🏭 3PL 仓储 | **wonder-sporklift** | Sporklift 仓储系统：ShipHero 库存台账、PO 履约、批次、效期 |
| 📮 采购系统 | **wonder-supply-chain** | POMS 采购订单：PO、采购计划、shipments、表结构 schema |
| ⚠️ 缺口 | **wonder-ladle** | **WIP / 空** —— 已知缺口，涉及 Ladle 时请明确说明 |

---

## 📚 知识库 / 资源 —— `Z01-Resource/CB-*/`

> 这些是**知识库**,不是 workflow;被上面的个人 workflow(尤其 `cookbook-ra`)读写。

| 目录 | 内容 |
|---|---|
| **CB-bigquery** | BigQuery 参考:`datasets/`、`tables/`、`playbooks/`、`metrics/`、`queries/`。有自己的 `SKILL.md`,内容≈ `wonder-cookbook` 的 BQ 层。含专门的 `playbooks/wonder-create.md` |
| **CB-business** | 业务规则、字段计算逻辑(`biz-req` 的输出目标) |
| **CB-full-feature** | 已上线功能的详细需求文档,镜像 Confluence 空间 RT(`archive-jira-to-cb` 的输出目标)。⚠️ 只反映已 ship 且已手动归档到的部分,非实时镜像 |

---

## ⚙️ 系统 / 框架 Skills —— `.claude/skills/`(其余)

非我为业务自建,属 Knowlery / Obsidian / agent 框架:

- **Knowlery 知识流**:`cook`(消化笔记成知识页)、`ask`(带引用回答)、`explore`(找关联/时间线)、`challenge`(压力测试观点)、`ideas`(生成想法)、`audit`(vault 体检)、`organize`(目录重整) —— 详见 [[KNOWLEDGE]]
- **Knowlery 工具**:`knowlery-cli`、`knowlery-mcp`(命令行 / MCP 操作知识库)
- **Obsidian 工具**:`obsidian-cli`、`obsidian-bases`、`obsidian-markdown`、`json-canvas`、`vault-conventions`
- **其它**:`search-company-knowledge`(搜 Confluence/Jira/内部文档 —— 找 MD-18063 用的就是它)、`defuddle`(抓网页正文为干净 markdown)
- **顶层 `.md`**:`atlassian-jira.md`、`atlassian-confluence.md`(参考文档)、`create-jira-ticket.md`(见个人区备注)

> 另有一批 Claude Code **全局内置** skill(`code-review`、`verify`、`deep-research`、`dataviz`、`run`、`security-review` 等),非本 vault 维护,按需自动触发,不在此清单重点范围。

---

## 备注

- **create-jira-ticket 有两份**:`.claude/skills/create-jira-ticket.md`(顶层,规则实际调用)与 `my-workflows/create-jira-ticket.md`(个人区)。若要改建单规范,认准顶层那份。
- 规则文件在 `.claude/rules/`(如 `ticket-workflow`、`cookbook-ra-workflow`、`archive-ticket-instruction`),负责把自然语言触发词路由到上面对应的个人 skill。
