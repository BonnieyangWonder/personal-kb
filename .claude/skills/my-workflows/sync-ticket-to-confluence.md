# Atlassian JIRA + Confluence Sync Command

将 JIRA Ticket 信息同步到 Confluence 页面的标准流程。

## 输入

- JIRA Ticket Key（如：MD-17493）
- 目标 Confluence Space
- 目标页面标题（可选，默认使用 JIRA Summary）

## 输出

创建/更新 Confluence 页面，包含：

1. **Ticket 基本信息**
   - Key、标题、类型、状态、优先级
   - Reporter、Assignee
   - 创建/更新时间

2. **需求描述**
   - 完整的 Description（保留格式）
   - 子任务列表

3. **技术实现要点**（自动提取）
   - Context/背景
   - 新模型设计
   - 依赖关系
   - 实施计划
   - 范围边界（In/Out of Scope）

4. **关联信息**
   - 父级 Epic
   - 相关子任务
   - 链接的 PR/Build（如有）

## 执行步骤

1. 从 JIRA REST API 获取 ticket 完整信息
2. 格式化内容为 Confluence Wiki 格式
3. 检查目标 Confluence 页面是否存在
   - 存在 → 更新
   - 不存在 → 创建新页面
4. 包含相关截图（从 JIRA 附件）

## API 端点

- JIRA: `https://wonder.atlassian.net/rest/api/2/issue/{ticketKey}`
- Confluence: `https://wonder.atlassian.net/wiki/rest/api/`

## 认证

使用环境变量存储的 API Token（已配置）
