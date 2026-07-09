# Gluten-Free 标签从"系统自动推断"改为"人工指定"——需求分析

> **日期**: 2026-05-25
> **状态**: Draft
> **来源**: Bonnie Yang（需求提出方）
> **关联文档**: [Confluence - Nutritions](https://wonder.atlassian.net/wiki/spaces/RT/pages/3965977174/Nutritions)

---

## 1. 需求背景

### 1.1 问题描述

当前系统中，**Gluten-Free** 饮食标志是系统根据 BOM（物料清单）中的过敏原数据**自动推断**的：只要 BOM 树及所有 mandatory choice 选项中不包含 gluten 过敏原，系统就自动为该菜品标记 "Gluten-Free"。

这种做法存在严重的食品安全和法律风险：

> 即使从数据角度确实没有 gluten 过敏原，也不能系统性地声称菜品是 "Gluten-Free"。因为食品生产中普遍存在交叉污染（cross-contamination），即使是微量 gluten 对 Celiac 患者也是极其危险的。**"Gluten-Free" 声明需要严格验证零残留，必须人工指定，不能系统推断。**

### 1.2 已发现的案例

- **Ess-a-Bagels**：已通过 "Hide nutrition info" toggle 临时解决
- 可能存在更多未被发现的类似案例

### 1.3 与 Vegan/Vegetarian 的本质区别

需求方明确指出：**"It would seem like we could apply a similar treatment as our Vegan/Vegetarian logic, but it's meaningfully different here."**

| 维度 | Vegan/Vegetarian | Gluten-Free |
|------|-----------------|-------------|
| **计算依赖** | 组件上的 **Vegan/Vegetarian tag**（人工在组件层面打过标） | Gluten 过敏原的**缺失**（纯机器推断） |
| **人在回路** | ✅ 有——每个 ingredient 被人工标记为 Vegan/Vegetarian | ❌ 无——没有人工确认环节 |
| **推理方向** | 正向——"有人确认过每个组件符合标准" | 反向——"没检测到就是安全的" |
| **风险等级** | 饮食偏好错误 → 客户不满意 | 过敏原声明错误 → 医疗紧急 / 诉讼 |
| **建议处理** | 保持系统计算（组件 tag → 向上汇总） | **纯人工指定**（需食品安全审核） |

---

## 2. 现有系统分析

### 2.1 当前 Gluten-Free 计算逻辑

**数据源**: `secure-recipe-prod.recipe_v2.all_item_version_customization_nutrition`

| 字段 | 说明 |
|------|------|
| `opv_allergens` | 从 BOM 树汇总的过敏原（JSON array），Gluten 包含在内 |
| `opv_collected_dietary_tags` | 饮食标签（JSON array），包含 Vegan、Vegetarian、Gluten-Free 等 |

**当前计算规则**（来自 `DietaryFlagEnum`）：

| 标志 | 条件 |
|------|------|
| **Gluten Free** | BOM 及所有 eligible mandatory choice 选项中均无 gluten 过敏原 → 自动标记 |
| **Gluten Free Optional** | 非 Gluten Free，但 gluten 可通过 customization 移除 |

**计算引擎**（Java 代码路径）：
- `BOItemCustomizationNutritionCalculateServiceV3`
  - `backend/internal-recipe-service/.../nutrition/`
- `BOItemRecipeNutritionCalculateService`
  - `backend/recipe-service-v2/.../`

### 2.2 涉及的数据表

| 表 | 作用 |
|----|------|
| `secure-recipe-prod.recipe_v2.all_item_version_customization_nutrition` | 营养数据，含 `opv_collected_dietary_tags` |
| `secure-recipe-prod.recipe_v2.effective_items` | 当前有效 item |
| `wonder-recipe-prod.recipe_v2.allergens` | 过敏原配置 |
| `wonder-recipe-prod.recipe_v2.tags` / `tag_groups` | 饮食标签定义 |

### 2.3 Gluten 在过敏原体系中的位置

Gluten 属于 **Additional Allergens**（非 Big 9），**不在 App 上直接展示**：

- 在成分标签层面追踪
- 用于系统自动推断 Gluten-Free 标志
- 但不同于 Milk/Eggs/Peanuts 等 Big 9 在 App UI 上显示为过敏原标签

---

## 3. 需求目标

### 3.1 核心目标

**将 Gluten-Free 标签从系统自动推断改为人工指定**，确保：

1. 不再根据"BOM 中无 gluten 过敏原"自动生成 Gluten-Free 标签
2. Gluten-Free 标签只能由授权人员经食品安全审核后手动设置
3. 已存在的系统自动生成的 Gluten-Free 标签需要批量清除
4. `GLUTEN_FREE_OPTIONAL` 的处理需要单独评估

### 3.2 非目标

- 不改变过敏原（allergen）的汇总计算逻辑
- 不改变 Vegan/Vegetarian 的计算逻辑
- 不改变 nutrition data 的计算公式

---

## 4. 系统变更方案

### 4.1 后端服务层（Cookbook / master-data-management-2）

#### A. 营养计算引擎——跳过 Gluten-Free 自动推断

| 服务类 | 变更 |
|--------|------|
| `BOItemCustomizationNutritionCalculateServiceV3` | **关键变更**：在 dietary flag 计算中，跳过 `GLUTEN_FREE` / `GLUTEN_FREE_OPTIONAL` 的自动赋值 |
| `BOItemRecipeNutritionCalculateService` | 同上，食谱层计算 |
| `BOItemCustomizationNutritionService` | 确保 nutrition 保存流程不再写入自动生成的 Gluten-Free flag |

**关键设计细节**：当触发营养重新计算时（component usage 变更、BOM 变更等）：
- ✅ VEGAN / VEGETARIAN → 继续自动重算
- ❌ GLUTEN_FREE → **保持不变**（因为是人工指定的，不受 BOM 变更影响）

#### B. Domain Model——新增人工指定支持

`DietaryFlagEnum` 当前定义：
```java
public enum DietaryFlagEnum {
    VEGAN, VEGETARIAN, GLUTEN_FREE, GLUTEN_FREE_OPTIONAL
}
```

建议引入 flag 来源区分（决策点 2）：
```java
public enum DietaryFlagSource {
    SYSTEM_CALCULATED,  // VEGAN, VEGETARIAN
    MANUALLY_ASSIGNED   // GLUTEN_FREE
}
```

或更简洁方案：在 `ItemVersion` 上增加独立的 `manuallyAssignedDietaryFlags` 字段。

#### C. API 层——新增手动标记端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/bo/item/:itemNumber/nutrition/gluten-free-flag` | PUT | 手动设置/取消 Gluten-Free |
| `/bo/item/:itemNumber/nutrition/gluten-free-flag/history` | GET | 查询设置历史（审计） |

**权限控制**：只有食品安全团队或 Admin 角色可操作。

### 4.2 Cookbook UI 层

#### Nutrition 面板改造

1. **Gluten-Free 开关**：从"只读（系统计算）"改为"手动勾选"
2. **权限控制**：非授权用户不可见/不可操作
3. **审计追踪**：记录操作人、时间、变更
4. **警告提示**：
   > ⚠️ "Gluten-Free" 声明需要严格验证零交叉污染风险。仅当经过食品安全团队确认后才能勾选。
5. **状态指示**：区分"已审核 Gluten-Free" vs "未审核" vs "不适用"

### 4.3 数据层

#### A. 数据清理

```sql
-- 影响范围评估
SELECT COUNT(DISTINCT n.item_number) as affected_items
FROM `secure-recipe-prod.recipe_v2.all_item_version_customization_nutrition` n
JOIN `secure-recipe-prod.recipe_v2.effective_items` ei
  ON n.item_number = CAST(ei.item_number AS STRING)
WHERE ei.object_type = 'MENU'
  AND ei.item_status = 'ACTIVE'
  AND ei.deleted = false
  AND n.is_preset = 'true'
  AND (n.opv_collected_dietary_tags LIKE '%Gluten%'
       OR n.opv_collected_dietary_tags LIKE '%gluten%');
```

#### B. 存储方案（待决策）

| 方案 | 改动量 | 优缺点 |
|------|--------|--------|
| **A. 复用现有字段**，清空 Gluten 相关 tag 后手工加回 | 中 | 简单但不够清晰 |
| **B. 新增独立字段** `manually_assigned_dietary_tags` | 大 | 最干净，但 schema 变更影响大 |
| **C. 在 tag value 中加来源前缀** | 中 | 解析复杂度增加 |

---

## 5. 下游影响分析

### 5.1 Customer-Facing App（Wonder App / Marketplace）

| 功能 | 影响 |
|------|------|
| **Dietary preference filter** | 用户筛选 "Gluten-Free" 时，只有人工审核过的菜品会显示 |
| **菜单项详情页** | Gluten-Free badge 仅在人工标记后显示 |
| **标签清除后过渡期** | 原本显示 Gluten-Free 的菜品不再显示该标签 |

**过渡期降级策略（待决策点 3）**：
- 方案 A：不显示任何标签（默认）
- 方案 B：显示 "Dietary info under review"
- 方案 C：仅对已验证菜品的集合不做变动，其他全部移除

### 5.2 Menu Availability (`active_menu_v2`)

- 确认 `active_menu_v2` 是否携带 dietary tags
- 确认数据同步链路及影响范围

### 5.3 其他可能受影响的系统

- OrderGrid (`ordergrid_items`)
- 第三方配送平台（DoorDash / Uber Eats）
- Nutrition PDF 导出
- Marketing / Merchandising 系统

---

## 6. 跨团队协调矩阵

| 团队 | 职责 | 交付物 |
|------|------|--------|
| **Cookbook / MDM** | 后端逻辑修改、API 改造、UI 改造 | Gluten-Free 手动标记功能 |
| **食品安全 (Food Safety)** | 定义审核标准、逐项审核菜品 | 审核通过的菜品清单 |
| **Ops** | "Hide nutrition info" 临时方案、执行手工标记 | 紧急案例修复 |
| **数据平台 (Data Platform)** | 数据备份、清理脚本、影响分析、监控 | 数据迁移脚本、影响报告 |
| **Marketplace / App** | Dietary filter 逻辑确认、UI 适配 | App 端兼容 |
| **Menu Management** | 确认 menu availability 数据流 | active_menu_v2 兼容 |
| **QA** | 端到端测试 | 测试用例、回归测试 |
| **法务 / 合规** | 审查 Gluten-Free 声明策略 | 合规确认 |

---

## 7. 实施路线图

### Phase 1 — 紧急止血（Week 1）

- [ ] 数据团队运行影响分析，确定受影响的菜品数量
- [ ] Ops 对已知问题菜品使用 "Hide nutrition info" toggle
- [ ] 食品安全团队梳理"确实 Gluten-Free"的菜品清单
- [ ] 全量备份 `opv_collected_dietary_tags`

### Phase 2 — 代码变更（Week 2-3）

- [ ] Cookbook 后端：修改 `BOItemCustomizationNutritionCalculateServiceV3`，移除 Gluten-Free 自动计算
- [ ] Cookbook 后端：新增 Gluten-Free 手动标记 API + 权限控制
- [ ] Cookbook UI：Nutrition 面板增加 Gluten-Free 手动开关
- [ ] 单元测试 + 集成测试
- [ ] dev/uat 环境验证

### Phase 3 — 数据清理 + 灰度（Week 4）

- [ ] Prod 运行数据清理脚本，批量清除 Gluten-Free 标签
- [ ] 食品安全团队在 Cookbook UI 中手工加回已验证菜品的标签
- [ ] App 团队确认 dietary filter 行为正常
- [ ] 灰度发布，少量 HDR 验证

### Phase 4 — 全量 + 监控（Week 5+）

- [ ] 全量发布
- [ ] 监控：App dietary filter 使用率变化、客户反馈
- [ ] 建立 Gluten-Free 标签审核 SOP
- [ ] 季度审核机制

---

## 8. 关键决策点

需要跨团队对齐：

1. **GLUTEN_FREE_OPTIONAL 的处理**：保留系统计算 or 也改为人工指定？

2. **人工标记的存储位置**：复用 `opv_collected_dietary_tags` or 新增独立字段？

3. **App 端过渡期降级策略**：标签清除后、审核加回前，App 展示什么？

4. **审核流程**：一键设置 or 需要审批工作流（提交 → Manager 审批 → 生效）？

---

## 9. 风险与回滚

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| 短期内大量菜品失去 Gluten-Free 标签 | 用户可筛选的 Gluten-Free 菜品骤减 | Phase 3 灰度验证 + 食品安全团队优先审核热销菜品 |
| App 端 dietary filter 行为异常 | 用户体验降级 | 提前与 App 团队对齐，充分测试 |
| 人工审核瓶颈 | 标签恢复速度慢 | 建立优先级（按销量排序），分批审核 |
| 数据清理遗漏 | 部分菜品仍显示错误标签 | 清理前后对比报告 + 自动化监控 |

**回滚方案**：
- 从备份恢复 `opv_collected_dietary_tags`
- 恢复自动计算逻辑
- 回滚 UI 变更

---

## 10. 附录

### A. 相关代码路径

| 组件 | 路径 |
|------|------|
| DietaryFlagEnum | `backend/domain-library/.../innerclassview/DietaryFlagEnum.java` |
| DietaryTag | `backend/domain-library/.../innerclassview/DietaryTag.java` |
| DietaryTagInfo | `backend/domain-library/.../innerclassview/DietaryTagInfo.java` |
| ItemCustomizationNutrition | `backend/domain-library/.../customization/ItemCustomizationNutrition.java` |
| NutritionCalculateServiceV3 | `backend/internal-recipe-service/.../nutrition/BOItemCustomizationNutritionCalculateServiceV3.java` |
| RecipeNutritionCalculateService | `backend/recipe-service-v2/.../BOItemRecipeNutritionCalculateService.java` |

### B. 相关数据表

| 表 | Dataset |
|----|---------|
| `all_item_version_customization_nutrition` | `secure-recipe-prod.recipe_v2` |
| `effective_items` | `secure-recipe-prod.recipe_v2` |
| `item_versions` | `secure-recipe-prod.recipe_v2` |
| `allergens` | `wonder-recipe-prod.recipe_v2` |
| `tags` / `tag_groups` | `wonder-recipe-prod.recipe_v2` |

### C. 参考文档

- [Confluence - Nutritions](https://wonder.atlassian.net/wiki/spaces/RT/pages/3965977174/Nutritions)
- Cookbook 知识库：`nutrition.md`、`customization.md`、`tags-categorization.md`
