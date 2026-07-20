---
type: analysis
status: in-progress
created: 2026-07-20
updated: 2026-07-20
tags:
  - cookbook
  - ik-eligible
  - ticket-analysis
---

# IK Eligible Checkbox 相关Tickets分析

**分析时间**: 2026-07-20  
**范围**: Sprint 8 - Sprint 15  
**总计**: 16个保留的tickets (已过滤掉4个重复的前端tickets)

---

## 📊 功能分类总览

### 1. IK Plating Rules配置 (3个)
- **MD-17927** ✅ IK Plating Rules configuration on menu item (保留-后端核心)
- **MD-18170** ✅ Auto-select default IK plating rule when step marked as IK eligible (独立功能)
- ~~MD-17936~~ ❌ UI - IK Plating Rules configuration on menu item (过滤-重复)

### 2. IK Component机器eligible属性 (3个)
- **MD-18130** ✅ IK Support-Component machine eligibility warning and IK step ordering constraint (保留-后端核心) **[已更新]**
- **MD-18115** ✅ IK Support-Side Component in Specific Dish Type (独立功能)
- ~~MD-18149~~ ❌ UI - IK Support-Component machine eligibility warning and IK step ordering constraint (过滤-重复)

### 3. Portion Conversion配置 (5个)
- **MD-18167** ✅ Configure Minimal Serving Portion Conversion at Component Level (保留-后端核心)
- **MD-18271** ✅ Minimal Serving Portion Conversion API support (API层面)
- **MD-18224** ✅ Menu item/non food item detail page: Don't display 'portion conversion' pop up (UI细节)
- **MD-18226** ✅ CLONE - Menu item/non food item detail page: Remove validation of 'Portion Conversion missing' (UI细节)
- ~~MD-18174~~ ❌ UI - Configure IK Portion Conversion at Component Level (过滤-重复)

### 4. Machine Eligible属性Tab转换验证 (3个)
- **MD-18219** ✅ Prevent from Tab Machine/Wonder Eligible Attribute to Published Item without Portion Conversion (保留-后端核心)
- **MD-18217** ✅ Disable Deletion from Machine Eligible/Wonder Eligible Component (独立功能)
- ~~MD-18284~~ ❌ UI - Prevent from Tab Machine/Wonder Eligible Attribute to Published Item without Portion Conversion (过滤-重复)

### 5. IK Line Build支持 (2个)
- **MD-17693** ✅ UI - IK Support - IK Eligible Line Build (前端)
- **MD-17818** ✅ [Wonder Create] Build General Line Build Agent (ships before WC flow) (后端agent)

### 6. 其他功能 (4个)
- **MD-17880** ✅ Map items as machine eligible for IK project (后端映射)
- **MD-17756** ✅ Send a topic/message to HDR if an ingredient is removed from "Machine Eligible" attribute (后端通知)
- **MD-18104** ✅ Remove Hot Holding Exclusion Logic From Vend Step in Cookbook (逻辑调整)
- **MD-18199** ✅ Add Unit Conversion ea→g for 7\* (HDR Recipe) Items (数据转换)

---

## 🗑️ 过滤掉的Tickets（前端/后端重复对）

| 过滤掉 | 对应保留 | 功能模块 | 理由 |
|--------|---------|---------|------|
| **MD-17936** | MD-17927 | IK Plating Rules配置 | 完全重复，功能描述相同 |
| **MD-18149** | MD-18130 | Component机器eligible & step ordering | 完全重复，功能描述相同 |
| **MD-18174** | MD-18167 | Portion Conversion配置 | 重复功能，MD-18167描述更完整 |
| **MD-18284** | MD-18219 | Machine Eligible属性转换验证 | 完全重复，功能描述相同 |

---

## ✅ 更新进度追踪

### 已完成更新 (2026-07-20) - 5个
- ✅ **MD-17690** - [已更新] (之前的4个外的tickets之一)
- ✅ **MD-17820** - [已更新] (之前的4个外的tickets之一)
- ✅ **MD-17947** - [已更新] (之前的4个外的tickets之一)
- ✅ **MD-17982** - [已更新] (之前的4个外的tickets之一)
- ✅ **MD-18130** - IK Support-Component machine eligibility warning and IK step ordering constraint

### 待更新 (共11个)
- [ ] **MD-17693** - UI - IK Support - IK Eligible Line Build
- [ ] **MD-17756** - Send a topic/message to HDR if an ingredient is removed from "Machine Eligible" attribute
- [ ] **MD-17818** - [Wonder Create] Build General Line Build Agent (ships before WC flow)
- [ ] **MD-17880** - Map items as machine eligible for IK project
- [ ] **MD-17927** - IK Plating Rules configuration on menu item
- [ ] **MD-18104** - Remove Hot Holding Exclusion Logic From Vend Step in Cookbook
- [ ] **MD-18115** - IK Support-Side Component in Specific Dish Type
- [ ] **MD-18167** - Configure Minimal Serving Portion Conversion at Component Level
- [ ] **MD-18170** - Auto-select default IK plating rule when step marked as IK eligible
- [ ] **MD-18217** - Disable Deletion from Machine Eligible/Wonder Eligible Component
- [ ] **MD-18219** - Prevent from Tab Machine/Wonder Eligible Attribute to Published Item without Portion Conversion
- [ ] **MD-18224** - Menu item/non food item detail page: Don't display 'portion conversion' pop up
- [ ] **MD-18226** - CLONE - Menu item/non food item detail page: Remove validation of 'Portion Conversion missing'
- [ ] **MD-18271** - Minimal Serving Portion Conversion API support

---

## 📌 关键发现

1. **前后端拆分**: 共4对tickets采用了前端(UI -)和后端分开建票的模式，建议关闭重复的前端tickets
2. **主要功能线**:
   - IK Plating Rules配置 (后端配置 + 前端UI展示)
   - Machine Eligible属性管理 (属性定义、验证、删除限制)
   - Portion Conversion配置 (数据映射 + API + UI调整)
   - Line Build支持 (通用agent + IK-specific UI)

3. **依赖关系**: Portion Conversion相关的多个tickets可能存在先后依赖关系
   - MD-18167 (后端配置) → MD-18271 (API) 和 MD-18224/MD-18226 (UI)
   - MD-18219 (验证) → MD-18224/MD-18226 (UI展示)

---

## 📝 注释
- 本分析基于Sprint 8-15范围内的"ik eligible checkbox"相关tickets
- 已排除所有Bug类tickets
- 保留的16个tickets都是Done或In UAT状态
- 下次更新时可参考待更新列表逐个处理
