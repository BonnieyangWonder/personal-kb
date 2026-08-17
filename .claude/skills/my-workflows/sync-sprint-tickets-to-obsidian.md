# Sync Jira Sprint Tickets to Obsidian

从 Jira MD Board 拉取指定 Sprint 的所有 ticket，自动更新 Obsidian ticket 归档文档中的表格，同时保留用户已有的手动标记（如"是否归档"列）。

## 输入

- **Sprint 编号或名称**（例如：`Sprint 16` / `MD 2026 Sprint 16` / `16`）
- **（可选）Obsidian 文档路径**（默认指向 `个人/ticket 归档.md`）

## 功能

1. **从 Jira 拉取** — 调用 MCP 工具 `jira_get_sprint_issues`，获取指定 Sprint 的所有 ticket（不含 Sub-task 和已取消项）
2. **生成 Markdown 表格** — 按照现有格式（# | Ticket | 标题 | 状态 | 链接 | 是否归档）整理数据
3. **智能合并** — 对比现有文档：
   - 新 ticket → 追加行
   - 已有 ticket 状态变化 → 更新状态列
   - **保留已有的"是否归档"标记** — 不覆盖用户手动标记
   - 已移出 Sprint 的 ticket → 挪到"已移出 Sprint"分区
4. **更新统计** — 更新 Sprint 统计行（工作项总数、状态分布、已归档数）
5. **版本记录** — Markdown 文件加上"最后更新日期"和"同步于 Jira 实时状态"注记

## Workflow

### Phase 1: 获取 Sprint 信息

1. 从用户输入解析 Sprint 编号（支持多种格式：`16` / `Sprint 16` / `MD 2026 Sprint 16`）
2. 调用 MCP 工具 `jira_get_sprints_from_board` 查询 MD Board（Board 10）的所有 Sprint
3. 匹配指定 Sprint，获取 Sprint ID

### Phase 2: 拉取 Ticket 清单

1. 调用 MCP 工具 `jira_get_sprint_issues`，传入 Sprint ID，获取完整 ticket 列表
2. 字段提取：
   - `key` — Ticket 编号（如 MD-18084）
   - `summary` — 标题
   - `status.name` — 状态（Done / In QA / To Do 等）
   - `created` / `updated` — 创建/更新时间
   - 过滤掉 Sub-task（`type.name != "Sub-task"`）和已取消的（`status != "Cancelled"`）

### Phase 3: 读取现有文档

1. 打开 `个人/ticket 归档.md`
2. 定位到对应 Sprint 的表格（按标题 `## MD XXXX Sprint XX` 找）
3. 解析现有表格：
   - 读取所有现有行
   - 提取"是否归档"列的标记（保留这些数据）
   - 记录当前行顺序和数据

### Phase 4: 数据对比 & 合并

**匹配规则**：同一 Ticket 编号视为同一行（例 MD-18084）

对每一张 ticket：
1. **如果在现有表格中** → 更新状态列，保留"是否归档"列的原值
2. **如果是新 ticket** → 追加到表尾，"是否归档"列留空
3. **如果 ticket 已从 Sprint 移出**（Jira 状态为 backlog 等）→ 移到"已移出 Sprint"分区

### Phase 5: 生成更新内容

按照现有格式重新生成表格 Markdown：

```markdown
| # | Ticket | 标题 | 状态 | 链接 | 是否归档 |
|---|--------|------|------|------|------|
| 1 | MD-18084 | ... | In QA | https://... | 是 |
...
```

更新统计行：
- **总工作项数**：X 个（来自 Jira 实时数据，不含 Sub-task 与已取消项）
- **状态分布**：Done X 个 / In QA X 个 / ...
- **已归档**：X 个

更新顶部时间戳：
```
**MD 2026 Sprint 16**：27 Jul - 10 Aug 2026（进行中/已结束，XX 个工作项，已按 Jira 实时状态同步于 YYYY-MM-DD）
```

### Phase 6: 写入文档

1. 调用 `obsidian write` 或直接编辑文件，替换对应 Sprint 的表格部分
2. 保留其他 Sprint 的内容不变
3. 更新 frontmatter 的 `updated` 日期

## 认证 & API

### MCP 工具（首选）

```
mcp__atlassian__jira_get_sprints_from_board    # 查询 Sprint 列表
mcp__atlassian__jira_get_sprint_issues         # 拉取 Sprint 的 Ticket
```

### 参数

- Board ID：`10`（MD Board）
- 字段列表：`summary`, `status`, `created`, `updated`, `issuetype`
- 过滤：`issuetype.name != 'Sub-task' AND status != 'Cancelled'`

## 处理特殊情况

| 情况 | 处理方式 |
|-----|--------|
| 找不到指定 Sprint | 报错：列出所有可用 Sprint，要求用户确认 |
| Jira 连接失败（401/403） | 报错：⚠ 无法连接 Jira，检查认证 |
| ticket 状态为已完成但仍在 Sprint | 保留在表格中，不移出 |
| ticket 从 Sprint 中被手动移除 | 移到"已移出 Sprint"分区 |
| 用户的"是否归档"标记冲突 | 始终保留用户数据，不覆盖 |

## 使用示例

**用户说：**
> "把 Sprint 16 的 ticket 同步到我的 ticket 归档"
> "更新一下 Sprint 16 的清单"
> "sync sprint 16"

**系统执行流程：**
1. 解析 Sprint 16
2. 从 Jira 拉取所有 ticket
3. 对比现有文档
4. 生成更新（保留 archive 标记）
5. 写入文件
6. 返回摘要："`✅ 已更新 21 个 ticket，其中 4 个标记为已归档`"

## 触发规则

识别用户意图（不需完整句子）：

**中文：**
- "把 Sprint 16 同步到 ticket 归档"
- "同步 Sprint 16"
- "更新一下 Sprint 16 的清单"
- "拉一下最新的 Sprint ticket"

**English:**
- "sync sprint 16 to ticket archive"
- "update sprint 16 tickets"
- "pull latest sprint tickets"

## 注意事项

- **保留用户数据** — "是否归档"列永不覆盖
- **增量更新** — 只改变有变化的部分（状态、新增 ticket）
- **时间戳** — 每次同步更新文档的"最后同步于 YYYY-MM-DD"
- **不涉及其他 Sprint** — 只更新指定 Sprint，其他 Sprint 保持原样
