---
title: Delete Variant 需求分析
type: ra
status: draft
created: 2026-07-14
updated: 2026-07-14
ticket_key: MD-18276
ticket_url: https://wonder.atlassian.net/browse/MD-18276
related_analyses: []
---

# Delete Variant 需求分析

## 背景

CDT team 提出需要在 Test Kitchen 中实现"Delete Variant"功能，用于清理无用的 draft variants，防止意外发布。

**Ticket**: [MD-18276](https://wonder.atlassian.net/browse/MD-18276)

---

## 现状分析

### 1. Variant 的生命周期和数据特性

#### Variant 是纯 R&D 沙箱阶段数据
- Variant 不会 sync 到 ERP（[[Variant-Test Kitchen/Variant List.md]]）
- Variant 不会 sync 到 OG（系统库存）
- Variant 不会进入任何 downstream system
- Variant 是 Menu Item/Recipe 的测试版本，只存在于 Test Kitchen 中

#### 当前 Variant 的 Actions
[[Variant-Test Kitchen/Variant List.md]] 第69-70行：
- Edit（编辑 variant 名称/描述）
- Duplicate（复制 variant）
- Compare（比较 variant）
- Move to Draft Version（转化为 normal version 的 draft）
- **❌ 无 Delete 选项**

### 2. 现有的数据保护机制

#### Move to Draft 时的校验
[[Variant-Test Kitchen/Variant List.md]] "Move to Draft" 部分第6条：
```
验证 variant 的 component/BOM/customization 中是否有：
- deleted item
- dormant item  
- variant item

如果有，显示错误："Unable to move the variant to draft. 
Please remove the following delete/dormant/variant sub item from the main variant."
```

#### Publish Version 时的校验
[[02Common Features/Publish Version.md]] 第17条：
```
检查是否有任何 sub item 在 BOM/Component/customization/line build 中被 deleted/dormant
如果有，显示错误："The following item(s) are currently dormant or deleted. 
Please either remove them or change their status to 'Active'."
```

**结论**: 即使 variant 中包含被删除的 item，后续流程也会捕获这个问题

---

## 需求理解

### 为什么需要 Delete Variant？

1. **清理 R&D 阶段的废弃数据** — 用户在 Test Kitchen 中创建了多个 variants 进行测试，最终只有少数被 move to draft，其他成为无用数据
2. **防止界面混乱** — Variant List 中积累大量旧的、无用的 test cases
3. **简化数据维护** — R&D 阶段的试验应该可以被清理

### 用户期望

- 快速删除无用的 draft variants
- 不要求复杂的 parent usage 校验（已经在 move to draft/publish 时校验了）
- 删除即清空，不需要恢复机制

---

## 设计决策 + 风险评估

### 决策 1️⃣: 删除 Variant 时**不校验** Parent Usage

#### 理由
1. **数据隔离**: Variant 是纯 R&D 沙箱，不进入 downstream
2. **后续防护充分**: Move to Draft 和 Publish 都有校验
3. **用户体验**: 删除时不加 usage 校验可以简化流程

#### 风险及缓解措施
| 风险 | 影响 | 缓解措施 |
|------|------|--------|
| 用户删除了被 parent variant 使用的 variant | Parent variant 无法 move to draft | 在 variant 列表显示警告文案；错误消息指向被引用的 parent |
| 删除后无法恢复 | 数据丢失 | UI 二次确认对话；记录删除日志便于审计 |

---

## 其他风险及考虑事项

### 已验证的风险（CB-full-feature 中找到）

#### 1. Preset Menu Item 的特殊处理
**文档**: [[Variant-Test Kitchen/Variant List.md]] 第3、7条  
**现象**: 
- 无法为有 linked preset item 的 menu item 创建 variant
- 无法为有 linked preset item 的 menu item move to draft

**对 Delete Variant 的影响**: 
- ✅ 低风险 — 这个限制在创建/move 时已生效
- 建议：Delete 时不需要特殊处理

#### 2. Byproduct Item 的级联关系
**文档**: [[Create New Variant.md]] Component 卡片对比表

**现象**:
- 创建 variant 时 **不继承** linked byproduct item
- Move to draft 时 **保留或继承** linked byproduct 关系

**对 Delete Variant 的影响**:
- ✅ 低风险 — Byproduct 关系在 output section，variant 中通常没有自定义配置
- 建议：删除 variant 时 byproduct 关系会自动清理

#### 3. Benchtop Recipe 的 Commercialize 阻塞
**文档**: [[Variant-Test Kitchen/Variant List.md]] Move to Draft 第10条注

**现象**:
```
"Since any deleted/dormant child item in the component tree of benchtop item, 
user cannot commercialize to recipe, we could only add this validation 
at 1st layer of component/BOM/customization of variant."
```

**对 Delete Variant 的影响**:
- ⚠️ 中等风险 — 如果某个 benchtop variant 在 component 中使用了 variant item，删除后无法 commercialize
- **但**: 这个风险在 commercialize 时会被捕获，不是致命的
- 建议：在错误提示中明确说明原因

#### 4. Concept 数据的丢失
**文档**: [[Create New Variant.md]] Item Information 卡片

**现象**:
- Menu item variant 可以有自己的 concept 设置
- 其他 item type 的 variant 隐藏 concept 字段

**对 Delete Variant 的影响**:
- ⚠️ 中等风险 — Menu item variant 的 concept 配置会完全丢失
- **用户可能期望**: 有某种 concept 配置的版本历史
- 建议：
  - Delete 前检查是否有自定义 concept
  - 如果有，在确认对话中提示："This variant has custom concept settings. They will be deleted."

#### 5. Dormant 与 Delete 的语义
**问题**: Variant 本身能否被 dormant，还是只能 delete？

**建议决策**:
- ✅ Variant **只支持 Delete**，**不支持 Dormant**
- 理由: Variant 本身没有 status 字段（已在 [[Variant-Test Kitchen/Variant List.md]] 第7条确认）

#### 6. Bulk Move 后的孤立 Variant
**文档**: [[Variant-Test Kitchen/Variant List.md]] Bulk Move to Draft

**现象**:
- Parent variant 包含 child variants 时，bulk move 会递归处理
- Child variant 被 move to draft 后，parent variant 中的引用也会更新

**对 Delete Variant 的影响**:
- ✅ 低风险 — Bulk move 的级联逻辑已处理好
- 建议：Delete 时也应考虑递归删除的可能性
  - **简单方案**: 删除 parent variant，child variants 不自动删除（避免意外级联删除）
  - **提示**: 如果 parent variant 被删除，任何引用它的 child 会在 move to draft 时报错

---

## 实现建议

### 最小可行版本（Mode 1）

```
DELETE Variant 功能需求：

1. UI
   ✅ 在 Variant List 的 Actions 中添加 "Delete" 按钮
   ✅ 点击后显示确认对话框，内容包括：
      - "Deleting this variant cannot be undone"
      - 如果该 variant 有自定义 concept（menu item only），提示：
        "This variant has custom concept settings. They will be deleted."
      - Actions: Cancel, Delete

2. 业务逻辑
   ✅ 直接删除 variant 及其所有 data（不检查 parent usage）
   ✅ 不需要检查 sub item 的 usage（后续 move to draft/publish 会校验）
   ✅ 删除后刷新列表

3. 错误处理 + 提示
   ✅ 成功: "Successfully deleted the variant. {variant_name}"
   ✅ 失败: 显示具体错误（如权限问题）

4. 权限
   ✅ 需要 "Edit Variant" 权限（与 Edit/Duplicate 相同）

5. 日志
   ✅ 记录到 variant 所属 item 的 Change History（或单独的 audit log）
      "Variant {variant_name} deleted by {user} at {timestamp}"
```

### 可选增强（未来迭代）

```
1. Soft Delete
   - 不是硬删除，而是标记为 deleted
   - 允许在一定时间内恢复
   - 实现复杂度提高

2. Batch Delete
   - 支持选择多个 variant 后批量删除
   - 需要额外的 UI 选择框逻辑

3. Delete 前的 Usage Preview
   - 显示 "This variant is referenced by X parent variants"
   - 只是展示，不阻止删除
   - 帮助用户更有信心地删除
```

---

## 跨域检查清单

| 系统 | 影响范围 | 检查结果 |
|------|--------|--------|
| **ERP** | Variant 数据不 sync | ✅ 无影响 |
| **OG（库存）** | Variant 数据不 sync | ✅ 无影响 |
| **Pantry/KDS** | Variant 数据不进入生产系统 | ✅ 无影响 |
| **SCC（供应链目录）** | Variant 数据被排除 | ✅ 无影响 |
| **Merch（商品化系统）** | 需要验证是否存储 variant 引用 | ⚠️ 建议代码验证 |

---

## 参考链接

### CB-full-feature 相关页面
- [[Variant-Test Kitchen/Variant List.md]] — Variant 主要功能定义
- [[Variant-Test Kitchen/Create New Variant.md]] — Variant 创建时的数据处理
- [[Variant-Test Kitchen/Variant Details.md]] — Variant 详情页面规范
- [[02Common Features/Publish Version.md]] — Publish 时的校验机制
- [[02Common Features/Delete Item.md]] — Item 删除时的 usage 校验逻辑
- [[02Common Features/Delete Version.md]] — Version 删除时的校验逻辑

### 相关 Ticket
- **MD-18276** — Delete Variant 需求（本次分析）

### 相关概念
- [[Cookbook Item Taxonomy]] — Item 类型定义（如 menu item、recipe 等）

---

## 结论

**Delete Variant 功能是可行的，且设计合理**:

1. ✅ **不需要校验 parent usage** — 后续 move to draft/publish 的校验已足够
2. ✅ **无 downstream 系统影响** — Variant 是纯 R&D 数据
3. ⚠️ **需要注意的细节**:
   - Menu item variant 的 concept 配置会丢失
   - 需要在 UI 中清晰提示"删除不可恢复"
   - 记录删除日志便于审计

**建议优先级**: High — 这是清理无用 R&D 数据的必要功能，实现复杂度低，风险可控。

---

## 附录：讨论记录

### 核心讨论点

**Q: 删除 variant 时是否需要检查 parent usage？**

**答**（已验证）:
- Variant 不进入 ERP/OG 等 downstream system
- Move to Draft 和 Publish 时已有完整校验
- 删除不检查 usage 不会破坏系统完整性
- 让用户自行责任管理 R&D 阶段数据，符合"快速清理"的目的

**Q: 是否还有其他隐藏的依赖关系？**

**答**（已扫描 CB-full-feature）:
- ✅ Preset item：无影响（preset 无法链接到 variant item）
- ✅ Byproduct item：无影响（variant 中 byproduct 自动清理）
- ✅ Benchtop recipe：风险已在 commercialize 时被捕获
- ⚠️ Concept 配置：Menu item variant 会丢失，需提示用户

---

**Status**: Ready for implementation discussion  
**Next Steps**: 
- [ ] 与 CDT team 确认 implementation scope
- [ ] 与 product 确认 UI/UX 文案
- [ ] 确认是否需要权限控制或日志记录
