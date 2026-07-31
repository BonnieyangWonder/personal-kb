---
title: 我的 Skills 清单
created: 2026-07-17
updated: 2026-07-31
tags: [meta, skills, index, 个人]
---

# 我的 Skills 清单

> 一份 skill 总览:**有哪些、在哪、个人还是团队、各自做什么**。
> 专治「分不清哪个是我自己的 skill」。手动维护,最后更新 2026-07-20。

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

| Skill | 文件 | 做什么 |
|---|---|---|
| **cookbook-ra** | `cookbook-ra.md` | Cookbook 需求分析(RA):分析需求 → data impact 分析 → 出 RA 报告(到 `A1-RA Rough/`)。会自动编排调用 `wonder-*` 团队 skill。触发:「分析下 XX 需求」「RA 一下」 |
| **archive-jira-to-cb** | `archive-jira-to-cb.md` | 把 Jira ticket 需求归档进 `Z01-Resource/CB-full-feature/`(已上线功能文档)。触发:「把 ticket 归档到 RA」 |
| **biz-req** | `biz-req.md` | 把 Jira + Confluence 需求编译成业务需求文档,写进 `Z01-Resource/CB-business/` |
| **sync-ticket-to-confluence** | `sync-ticket-to-confluence.md` | 对比 Jira ticket 与已有 Confluence 页面,给出 diff,确认后更新 Confluence(英文) |
| **create-jira-ticket** | `create-jira-ticket.md` | 建 Jira ticket(MD 项目、Story)。⚠️ 顶层另有一份同名 `.claude/skills/create-jira-ticket.md`,`ticket-workflow` 规则实际用的是**顶层**那份 |
| **xm-ny-weekly-planning** | `xm-ny-weekly-planning.md` | 建当周「XM NY Weekly Planning」Confluence 页面(空间 RT,父页面"2026"),正文标题 `Topics`,comment 里艾特 Pratik Busi / Jakob Lewei / Lisa Li / Bonnie。触发:「创建本周的 meeting agenda」「XM NY weekly planning for this week」。⚙️ **已注册 macOS LaunchAgent 每周一 15:00 自动跑**(无需开口),脚本 + 日志在 `~/.xm-ny-weekly-planning/`(`run.log`)。**如果自动没成功,直接说触发词手动建就行** |
| **sediment-cookbook-feature-reqs** | `sediment-cookbook-feature-reqs.md` | 沉淀 Cookbook 系统功能/字段的业务需求文档。从 Jira ticket 提取需求 → 组织标准化文档 → 放进 `Z01-Resource/CB-business/features/`(持久化的功能业务需求档案库)。触发:「沉淀业务需求」「生成业务需求」「写业务需求」+[链接/图片/文字]。输出文件名简洁清晰,含范围标记(如 `7*`)避免重名 |

---

## 🔵 团队 Skills —— `.claude/skills/wonder-<name>/`

| Skill | 做什么 |
|---|---|
| **wonder-cookbook** | Cookbook recipe / BOM 系统:菜品配方、必选 vs 可选组件、菜单可用性逻辑 |
| **wonder-command-center** | Command Center 拆单(Splitter):为什么某 item 被分到某个 order |
| **wonder-kitchen-ops** | 厨房运营:batching 资格、fryer batching、BOM↔linebuild↔sequencing 关系 |
| **wonder-menu-availability** | HDR 菜单可用性(`active_menu_v2` 现行 / `active_menu` 旧版) |
| **wonder-orders** | 订单 / 销售数据(`hdr_orders`、`order_items`、满意度、渠道、准时率) |
| **wonder-otr** | On-Time Rate 绩效 + 根因分析,出分层领导层报告。触发:「generate WBR summary」「weekly OTR report」 |
| **wonder-pantry** | 门店(HDR)库存:waste、盘点、库存移动、slacking、hot holding、可用性 |
| **wonder-sequencing** | 厨房排序系统(sequencing optimizer、batch group、holdback) |
| **wonder-sporklift** | Sporklift 仓储(ShipHero 3PL 库存台账、快照、PO 履约、批次/效期) |
| **wonder-supply-chain** | POMS 采购订单系统(PO、采购计划、shipments;含表结构 schema) |
| **wonder-ladle** | ⚠️ WIP / 空 —— 已知缺口,涉及 Ladle 时需明确说明,别静默跳过 |

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
