# Atlassian Confluence Skill

## 概述

用于创建、读取、更新 Confluence 页面的 Skill。

## 认证

使用 Basic Auth（API Token）：
- Email: bonnieyang@xm.wonder.com
- Token: 已配置在 mcp.json

## API 端点

```
https://wonder.atlassian.net/wiki/rest/api/
```

## 支持的操作

### 1. 获取页面

```bash
GET /rest/api/content/{pageId}
```

查询参数：
- `expand` - body.storage, version, history

### 2. 搜索页面

```bash
GET /rest/api/content/search
```

CQL 示例：
- `space=MD AND title~"Guide"`
- `type=page AND text~"keyword"`

### 3. 创建页面

```bash
POST /rest/api/content
```

Body:
```json
{
  "type": "page",
  "title": "Page Title",
  "space": { "key": "SPACE_KEY" },
  "body": {
    "storage": {
      "value": "<p>Content in Wiki markup</p>",
      "representation": "storage"
    }
  }
}
```

### 4. 更新页面

```bash
PUT /rest/api/content/{pageId}
```

需要包含当前版本号进行乐观锁更新。

### 5. 获取子页面

```bash
GET /rest/api/content/{pageId}/child/page
```

## Wiki 标记语法

### 标题
```
h1. Heading 1
h2. Heading 2
h3. Heading 3
```

### 列表
```
- Bullet item
* Also bullet
# Numbered item
```

### 代码块
```
{bcode:language}
code here
{code}
```

### 表格
```
||Header 1||Header 2||
|Cell 1|Cell 2|
```

### 链接
```
[Link Text|http://url.com]
[Page Title|PageId]
```

### 图片
```
!image-xxx.png|width=600!
```

## 常用场景

### 从 JIRA Ticket 创建文档
1. 获取 JIRA Ticket 信息
2. 格式化为 Confluence Wiki 格式
3. 创建/更新目标页面

### 文档同步
- 自动更新开发文档
- 同步 Sprint 总结
- 维护变更日志

### 知识库查询
- 按 Space 搜索
- 按标签过滤
- 获取页面历史
