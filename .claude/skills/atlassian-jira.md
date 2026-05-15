# Atlassian JIRA Skill

## 概述

用于查询、分析和管理 JIRA Tickets 的 Skill。

## 认证

使用 Basic Auth（API Token）：
- Email: bonnieyang@xm.wonder.com
- Token: 已配置在 mcp.json

## API 端点

```
https://wonder.atlassian.net/rest/api/2/
```

## 支持的操作

### 1. 查询 Ticket

```bash
GET /rest/api/2/issue/{ticketKey}
```

Fields 参数：
- `summary` - 标题
- `status` - 状态
- `assignee` - 经办人
- `reporter` - 报告人
- `description` - 描述
- `created` - 创建时间
- `updated` - 更新时间
- `priority` - 优先级
- `issuetype` - 问题类型
- `labels` - 标签
- `parent` - 父级
- `subtasks` - 子任务
- `comment` - 评论

### 2. 搜索 Tickets

```bash
GET /rest/api/2/search?jql={jqlQuery}
```

常用 JQL 示例：
- `project = MD AND status = "To Do"` - 查询 MD 项目下所有 To Do
- `assignee = currentUser() AND status != Done` - 我的任务
- `created >= -7d` - 最近 7 天创建的

### 3. 更新 Ticket

```bash
PUT /rest/api/2/issue/{ticketKey}
```

可更新字段：
- `summary`
- `description`
- `assignee`
- `status`
- `priority`

### 4. 添加评论

```bash
POST /rest/api/2/issue/{ticketKey}/comment
```

## 常用场景

### Ticket 分析
1. 获取基本信息（类型、状态、优先级、人员）
2. 解析描述内容（Context、Requirements、AC、Dependencies）
3. 提取关键信息（技术方案、时间节点、范围边界）
4. 生成总结

### 批量操作
- 按 Epic 查询所有子任务
- 按 Sprint 导出任务列表
- 批量更新状态/分配人

## 项目 Key

- MD = Main Dashboard / Product Catalog
- ENG = Engineering
- QA = Quality Assurance
