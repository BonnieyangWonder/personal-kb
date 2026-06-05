---
title: Wonder Create - Packaging Types Analysis
date: 2026-06-05
updated: 2026-06-05
project: Wonder Create
tags: [cookbook, non-food, packaging, data-research]
source: BigQuery (master_data + wonder-recipe-prod)
---

# Wonder Create - Packaging Types Analysis

## 调研背景

Wonder Create 新建 item 时，CE 需要选择合适的包装物料。本报告调研 Cookbook 系统中 9\* non-food packaging item 的材质类型、属性维度和配对关系，供 CE 选择包装时参考。

数据范围沿用 [[Wonder Create - Non-Food Packaged 9-Star Items by Brand]] 的 6 brand（Hanu Poke、Bellies、Limesalt、El Diez、Yasas、Royal Greens），并向全系统扩展。

## 数据来源

| 维度 | 说明 |
|------|------|
| **Item 基础信息** | `master_data.item_versions`（item_name, object_sub_type, item_status） |
| **属性体系** | `master_data.item_attributes`（Material Category, Material Sub-Category, Packaged Size, NONFOODITEMSTATUS） |
| **BOM 关联** | `master_data.item_versions.bom_header.bom_lines`（bowl-lid 配对关系） |
| **属性粒度问题** | Material Sub-Category 在 Bowl 层级仅到 `Bowl`，不区分 Pulp/PET/PP/Paper。材质信息需从 item_name 中提取 |

---

## 一、Bowl 材质类型

### 1.1 现有属性体系

系统中 Bowl 类 item 的 `Material Sub-Category` 统一为 `Bowl`，没有材质细分。可用于筛选的属性维度：

| 属性 | Bowl 可选项 |
|------|-----------|
| Material Category | `Guest Packaging` |
| Material Sub-Category | `Bowl` |
| Packaged Size | `XS`, `S`, `M`, `L`, `XL` |
| NONFOODITEMSTATUS | `ACTIVE` |

### 1.2 从 Item Name 提取的材质分类

通过分析 item name 的命名规则，Bowl 实际包含以下材质：

| Item # | Name | 材质 | 容量 | 颜色 | Size |
|--------|------|------|------|------|:---:|
| 9000041 | Bowl, 48oz, Natural, Round, Pulp | Pulp | 48oz | Natural | M |
| 9000061 | Bowl, 32oz, Natural, Round, Pulp | Pulp | 32oz | Natural | L |
| 9000170 | Bowl, 48oz, Clear, Round, PET Plastic | PET | 48oz | Clear | — |
| 9000263 | Bowl, 12oz, Clear, Round, PET Plastic | PET | 12oz | Clear | — |
| 9000636 | Bowl, 32oz, Clear, Round, Shallow, Plastic | Plastic | 32oz | Clear | M |
| 9000726 | Bowl, 8oz, Clear, Round, PET Plastic | PET | 8oz | Clear | S |
| 9000893 | Bowl, 24oz, Clear, Round, Shallow, Plastic | Plastic | 24oz | Clear | — |
| 9002087 | Bowl, White, Round, Paper, 16oz | Paper | 16oz | White | S |
| 9002254 | Bowl, 24oz, Black, Round, PP Plastic | PP | 24oz | Black | M |
| 9002398 | Choice 4 oz. Round Kraft PE-Lined… | Kraft | 4oz | Kraft | — |

> 9000204 (8oz Black PP, INTERNAL_PACKAGING, NONFOODITEMSTATUS=INACTIVE) 和 9000665 (Bowl & Lid 42oz Noodle Black, 组合容器) 未列入。

### 1.3 材质归类建议

系统中材质信息不在结构化属性中，CE 需要按 item name 关键词识别。建议将 Bowl 材质归为两大类：

| 类型 | 覆盖材质 | 外观特征 | 代表 Item |
|------|----------|----------|-----------|
| **Fiber（纤维基）** | Pulp, Paper, Kraft | 不透明、自然质感、环保可降解 | 9000041, 9000061, 9002087, 9002398 |
| **Plastic（塑料）** | PET, PP, Plastic | 透明或着色、硬质 | 9000170, 9000636, 9000726, 9000263, 9000893, 9002254 |

**归类理由**：
- Pulp 和 Paper 都是植物纤维基材料，制造工艺不同但 CE 关心的维度（环保感知、不透明外观）一致
- PET 和 PP 都是石油基塑料，系统命名不统一（有的写 "PET Plastic"，有的只写 "Plastic"），进一步细分在系统中不可靠
- CE 的核心决策是「纸质的还是塑料的」，而非纸浆模压 vs 纸板、PET vs PP

### 1.4 48oz / 32oz Bowl 选项

| 容量 | Fiber | Plastic |
|:---:|-------|---------|
| **48oz** | 9000041 Bowl, 48oz, Natural, Round, Pulp | 9000170 Bowl, 48oz, Clear, Round, PET Plastic |
| **32oz** | 9000061 Bowl, 32oz, Natural, Round, Pulp | 9000636 Bowl, 32oz, Clear, Round, Shallow, Plastic |

---

## 二、Bowl × Lid 配对

### 2.1 覆盖 32oz/48oz 的 Lid 清单

| Item # | Name | 盖型 | 材质 |
|--------|------|:---:|------|
| 9001727 | Lid, 32 & 48oz Pulp Bowl, PET, Dome | Dome | PET |
| 9000042 | Lid, Bowl, 24, 32, 48oz, Clear, Round, PP Plastic | Flat | PP |
| 9000171 | Lid, Bowl, 24, 32, 48oz, Clear, Round, Flat, PET Plastic | Flat | PET |
| 9000503 | Lid, Bowl, 24, 32, 48oz, Clear, Round, Dome, PET Plastic | Dome | PET |

### 2.2 实际 BOM 配对数据

查询所有菜单 item 的 BOM，确认 bowl 和 lid 的实际使用关系：

| Bowl | 材质组 | 主 Lid | 盖型 | 菜单数 | 次选 Lid | 菜单数 |
|------|:---:|--------|:---:|:---:|------|:---:|
| 9000041 (48oz Pulp) | Fiber | **9001727** Dome PET | Dome | 183 | 9000042 Flat PP | 6 |
| 9000061 (32oz Pulp) | Fiber | **9001727** Dome PET | Dome | 46 | **9000042** Flat PP | 47 |
| 9000170 (48oz PET) | Plastic | **9000171** Flat PET | Flat | 18 | 9000503 Dome PET | 3 |
| 9000636 (32oz Plastic) | Plastic | **9000171** Flat PET | Flat | 46 | 9000503 Dome PET | 10 |

### 2.3 配对规律

| 材质组 | 推荐 Lid | 盖型 | 原因 |
|:---:|------|:---:|------|
| **Fiber** | 9001727 | Dome | Pulp 碗较深，需 Dome 拱起空间；名称明确标注 "Pulp Bowl" |
| **Plastic** | 9000171 | Flat | 透明塑料碗通常较浅（含 Shallow 型号），平盖即可；9000170 和 9000171 号段连续，为配套创建 |

### 2.4 CE 选择对照表

| 容量 | 材质组 | Bowl | Lid | 盖型 |
|:---:|:---:|------|------|:---:|
| 48oz | Fiber | 9000041 | 9001727 | Dome |
| 48oz | Plastic | 9000170 | 9000171 | Flat |
| 32oz | Fiber | 9000061 | 9001727 / 9000042 | Dome / Flat |
| 32oz | Plastic | 9000636 | 9000171 | Flat |

---

## 三、Wrap / Sandwich 类纸包装

### 3.1 6 Brand 中已验证的 Wrap 包装

从 [[Wonder Create - Non-Food Packaged 9-Star Items by Brand]] 文档确认，Bellies（burger）和 Yasas（wrap/sandwich/pita）使用了以下纸/箔类包装：

| Item # | Name | Material Sub-Cat | Size | 使用 Brand | 菜单数 |
|--------|------|:---:|:---:|-----------|:---:|
| **9000260** | Sheet, 14x16", Foil, Insulated, Honeycomb | Foil | M | Bellies, Yasas | 8 |
| **9001889** | Bag, Yasas, Greasepaper, 6x7 | Bag-Foil | S | Yasas | 1 |
| **9001506** | 18x18 Foil Paper | Foil | L | Limesalt | 2 |

**使用模式**：

| 模式 | 代表 Brand | 包装组合 | 适用场景 |
|------|-----------|----------|----------|
| **Clamshell + Foil Wrap** | Bellies | 9002623 Clamshell + 9000260 Foil Sheet | Burger 类，需要 rigid outer container |
| **纯 Foil Wrap + Sauce Cup** | Yasas | 9000260 Foil Sheet + 9002138 Souffle Cup | Wrap/Sandwich 类，无 rigid 外容器 |

### 3.2 系统中所有可用于 Wrap/Sandwich 的纸/箔类 9\* Item

按 Material Sub-Category 分类：

#### Bag-Deli（纸袋）

| Item # | Name | Size | 特征 |
|--------|------|:---:|------|
| 9000068 | Bag, 9x10", Flatbread | — | Flatbread 专用 |
| **9000727** | Bag, 6.75 x 6.5", Sandwich, Natural, Kraft | S | 三明治牛皮纸袋 |
| **9001961** | Bag, White, Paper, 1#, Window | S | 白色带窗纸袋 |
| 9002211 | Bag, Tape Strip, Celery & Carrots, Wing Trip | S | 带胶条，品牌定制 |

#### Bag-Foil（箔纸袋 / Greasepaper 袋）

| Item # | Name | Size | 品牌/用途 |
|--------|------|:---:|-----------|
| 9001249 | Bag, 5.25x3.5x12", Insulated, White, Foil | S | 保温箔袋 |
| **9001622** | Foil Insulator Sandwich Bag | L | 三明治保温箔袋（未被 6 brand 使用，通用型） |
| 9001887 | Bag, Chios, Greasepaper, 6x7 | S | Chios |
| 9001888 | Bag, Royal Greens, Greasepaper, 6x7 | — | Royal Greens |
| 9001889 | Bag, Yasas, Greasepaper, 6x7 | S | Yasas |
| 9001890 | Bag, Maydan, Greasepaper, 9x10 | S | Maydan |
| 9001947 | Bag, Greasepaper, Burger Baby | — | Burger Baby |
| 9001948 | Bag, Greasepaper, Fred's, Hoagie | L | Hoagie 三明治 |
| 9001949 | Bag, Greasepaper, Limesalt, Burrito | — | Limesalt |
| 9001950 | Bag, Greasepaper, Alanza, Garlic Bread | M | Alanza |
| 9001951 | Bag, Greasepaper, Tejas, Proteins | L | Tejas |
| 9001952 | Bag, Foil Paper, Yasas, Spanakopita | S | Yasas |
| 9001953 | Bag, Foil Paper, Mr.D's | S | Mr.D's |
| 9001954 | Bag, Foil Paper, Chai Pani, Naan | — | Chai Pani |

#### Foil（箔纸/片）

| Item # | Name | Size | 特征 |
|--------|------|:---:|------|
| 9000137 | Sheet, 12x10.75", Silver, Foil, Aluminum | — | 铝箔片 |
| **9000260** | Sheet, 14x16", Foil, Insulated, Honeycomb | M | 保温蜂窝箔纸（**最常用**） |
| 9000350 | Sheet, 18", Silver, Foil, Aluminum | — | 铝箔片（INTERNAL_PACKAGING） |
| **9001506** | 18x18 Foil Paper | L | 大号箔纸 |

#### Paper（纸）

| Item # | Name | 特征 |
|--------|------|------|
| 9000013 | Paper, 6x10.75", Small, Deli, Parchment | 小号油纸 |
| 9000019 | Paper, 12x10.75", Large, Deli, Parchment | 大号油纸 |
| 9000357 | Paper, 16x24", White, Rectangle, Parchment, Silicone | 硅油纸 |
| 9001003 | Paper, 18"x700', 40lb, Butcher, White, Roll, Premium | 屠宰纸卷（R&D） |
| 9001623 | 18" x 700' 40# Pink / Peach Butcher Paper Roll | 粉色屠宰纸卷 |
| 9001734 | 18x18 Freezer Paper | 冷冻纸 |

#### Greasepaper（防油纸）

| Item # | Name | 品牌/用途 |
|--------|------|-----------|
| 9000833 | Paper, 5x6.5", Grease, Tejas | Tejas |
| 9001258 | Paper, Custom, Jota, Greaseproof | Jota |
| 9002096 | Greasepaper, Wing Trip, 9x9 | Wing Trip |
| 9002256 | Greasepaper, Chai Pani, 9x9 | Chai Pani |
| 9002274 | Greasepaper, Streetbird, 5x6.5 | Streetbird |

### 3.3 CE 可选包装特征维度

根据 `item_attributes` 表，CE 选择包装时可用的筛选维度：

| 属性维度 | Wrap/Sandwich 相关可选值 | 说明 |
|----------|------------------------|------|
| **Material Category** | `Guest Packaging`, `Internal Packaging`, `Smallwares & Supplies` | 一级分类 |
| **Material Sub-Category** | `Foil`, `Bag-Foil`, `Bag-Deli`, `Paper`, `Greasepaper`, `Film`, `Box-ToGo`, `Clamshell` | 二级材质细分 |
| **Packaged Size** | `XS`, `S`, `M`, `L`, `XL` | 标准化尺寸标签 |
| **NONFOODITEMSTATUS** | `ACTIVE` | 务必筛选 ACTIVE |

### 3.4 通用 Wrap 包装推荐（非品牌定制）

| 优先级 | Item | 类型 | Size | 理由 |
|:---:|------|------|:---:|------|
| **高** | 9000260 | Foil Sheet (Insulated Honeycomb) | M | 唯一被 2+ brand 验证，burger/wrap/pita 全覆盖 |
| **高** | 9000727 | Sandwich Kraft Bag | S | 三明治牛皮纸袋，通用型 |
| **中** | 9001622 | Foil Insulator Sandwich Bag | L | 三明治保温箔袋，虽未被 6 brand 使用但是通用型 |
| **中** | 9001506 | 18x18 Foil Paper | L | 大号箔纸，Limesalt 已验证 |
| **中** | 9001961 | White Paper Bag #1 Window | S | 白色带窗纸袋，Limesalt 已验证 |
| **低** | 品牌 Greasepaper 袋（9001887-1954） | Bag-Foil | S/M/L | 品牌定制，新品牌需评估是否复用或新建 |

---

## 四、属性体系总结

### 4.1 系统现有属性维度

| Attribute | 可选值数量 | 说明 |
|-----------|:---:|------|
| Material Category | 6 | Guest Packaging, Internal Packaging, Smallwares & Supplies, Facilities, Marketing, Sanitation |
| Material Sub-Category | 50+ | Bowl, Lid, Foil, Bag-Deli, Bag-Foil, Paper, Greasepaper, Clamshell, Container-pulp, Sleeves-branded, 等 |
| Packaged Size | 5 | XS, S, M, L, XL |
| NONFOODITEMSTATUS | 2 | ACTIVE, INACTIVE |

### 4.2 属性体系局限

- **Material Sub-Category 粒度不够**：Bowl 层级不区分材质（Pulp/PET/PP/Paper 全部归类为 `Bowl`），CE 无法通过属性筛选材质
- **材质信息仅存在于 item name**：需依赖命名规范提取关键词
- **命名规范不统一**：有的写 "PET Plastic"，有的只写 "Plastic"
- **跨品牌包装复用度低**：Bag-Foil 类 15 个 item 中有 12 个是品牌定制，通用型仅 9001249、9001622

### 4.3 CE 选择包装的建议流程

1. **选包装形态**：Material Sub-Category → Bowl / Clamshell / Container-pulp / Box-ToGo
2. **选材质类型**：从 item name 关键词识别 → Fiber (Pulp/Paper/Kraft) vs Plastic (PET/PP)
3. **选容量**：从 item name 提取 oz 数
4. **选 Lid**：按 Bowl-Lid 配对表匹配（Fiber→Dome, Plastic→Flat）
5. **选辅助包装**（wrap/sandwich 类）：Foil Sheet / Bag-Deli / Bag-Foil
6. **确认状态**：NONFOODITEMSTATUS = ACTIVE

---

## 相关链接

- [[Wonder Create - Non-Food Packaged 9-Star Items by Brand]] — 6 Brand 9\* 包装使用详情
- [[Wonder Create - BOM Components Excluding All 80 Cookbook Items]]
- [[packaged-skus.md]] — Packaged SKUs 领域文档
- [[item-master.md]] — Item Master（9\* = NON_FOOD 说明）
