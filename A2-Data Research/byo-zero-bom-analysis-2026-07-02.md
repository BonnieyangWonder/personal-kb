---
title: "BYO Menu Items with Zero Required BOM — Royal Greens, Limesalt, Yasas, Hanu Poke"
date: 2026-07-02
created: 2026-07-02
updated: 2026-07-02
type: query
tags:
  - cookbook
  - recipe-management
  - bigquery
domain: cookbook
status: active
description: "Analysis of salad/bowl/wrap menu items across 4 brands that have zero required BOM components and rely entirely on customization options."
author: bonnie
---

## Query Context

**Question**: 查找 Royal Greens、Limesalt、Yasas、Hanu Poke 四个 brand 中，BOM 里没有 `manage_inventory = true` 的 component，且 customization option 最多的 salad/bowl/wrap 类 menu item（排除 PRESET）。

**Date**: 2026-07-02

**Datasets**:
- `wonder-recipe-prod.recipe_v2.concepts` / `menus`
- `secure-recipe-prod.recipe_v2.item_versions` / `bom_headers` / `bom_lines` / `effective_items`

---

## Key Findings

### 🥗 Salad & Bowl: Top 10 BYO Items (0 Required BOM, 非 PRESET)

All top 10 items share a common pattern: BOM consists entirely of packaging materials (containers, lids, sleeves, souffle cups) with `manage_inventory = false`. All actual food ingredients are provided through `item_customization` options.

#### Tier 1: Royal Greens BYO Greens Bowl — Primary ID（85 Option Values）

| # | Item Number | Name | Status | Brands | Options | Total OV |
|---|-------------|------|--------|--------|---------|----------|
| 1 | `8010459` | BYO Greens Bowl, Royal Greens BOWLDER- Primary ID | `FOR_SALE` | All 4 | 8 | **85** |
| 2 | `8011814` | BYO Greens Bowl, Royal Greens BOWLDER - Primary ID (C&C Pilot) | `FOR_SALE` | All 4 | 8 | **85** |

**8 Customization Options**:

| Option | Type | Display | OV Count |
|--------|------|---------|----------|
| Toppings | `OPTIONAL_ADDITION` | Featured | 23 |
| 2 Dressings (Served on Side) | `MANDATORY_CHOICE` | Featured | 22 |
| Crunchy Toppings | `OPTIONAL_ADDITION` | Featured | 12 |
| Premium Toppings | `OPTIONAL_ADDITION` | Featured | 8 |
| Base | `MANDATORY_CHOICE` | Featured | 6 |
| Protein (Served Chilled) | `MANDATORY_CHOICE` | Featured | 6 |
| Cheese | `OPTIONAL_ADDITION` | Featured | 6 |
| Side of Pita | `MANDATORY_CHOICE` | Featured | 2 |

**BOM (全部 manage_inventory = false)**:
- Bowl, 48oz, Natural, Round, Pulp (`9000041`)
- Lid, 32 & 48oz Pulp Bowl, PET, Dome (`9001727`)
- Souffle Cup, 2oz, PP (`9002138`)
- Lid, 2oz Souffle Cup, PET (`9002139`)
- Royal Greens Wrap Sleeves 13 7/8" (`9003669`)

#### Tier 2: Royal Greens BYO Greens Bowl — Abridged Rail ID（80 Option Values）

| # | Item Number | Name | Status | Brands | Options | Total OV |
|---|-------------|------|--------|--------|---------|----------|
| 3 | `8010492` | BYO Greens Bowl, Royal Greens BOWLDER- Abridged Rail ID | `FOR_SALE` | All 4 | 8 | **80** |
| 4 | `8011815` | BYO Greens Bowl, Royal Greens BOWLDER - Abridged Rail ID (C&C Pilot) | `NOT_SOLD` | All 4 | 8 | 80 |

**vs Primary ID 差异**：Toppings 20 (↓3)、Premium Toppings 7 (↓1)、Cheese 5 (↓1)

#### Tier 3: Cook & Chill Rice + Veg Pilot Bowls/Salads（48 Option Values）

| # | Item Number | Name | Status | Brands |
|---|-------------|------|--------|--------|
| 5 | `8011855` | Harissa Chicken Crunch Bowl | `FOR_SALE` | Limesalt, Yasas |
| 6 | `8011856` | Grilled Chicken & Avocado Bowl | `FOR_SALE` | Limesalt, Yasas |
| 7 | `8011857` | Greek Salad w/ Grilled Chicken | `FOR_SALE` | Limesalt, Yasas |
| 8 | `8011858` | Grilled Steak & Feta Bowl | `FOR_SALE` | Limesalt, Yasas |
| 9 | `8011859` | Falafel Bowl | `FOR_SALE` | Limesalt, Yasas |
| 10 | `8011860` | Za'atar Carrots & Broccoli Bowl | `FOR_SALE` | Limesalt, Yasas |

**8 Customization Options**（结构不同于 Royal Greens）:

| Option | Type | Display | OV Count |
|--------|------|---------|----------|
| Choose Your Toppings | `OPTIONAL_ADDITION` | Featured | 14 |
| Dressings (Served on Side) | `MANDATORY_CHOICE` | Featured | 8 |
| Add Extra Dressing | `OPTIONAL_ADDITION` | In-Drawer | 7 |
| Choose Your Spreads | `OPTIONAL_ADDITION` | Featured | 6 |
| Choose Your Grain | `MANDATORY_CHOICE` | Featured | 4 |
| Choose Your Main | `MANDATORY_CHOICE` | Featured | 4 |
| Choose Your Greens | `MANDATORY_CHOICE` | Featured | 3 |
| Include Side of Pita | `MANDATORY_CHOICE` | Featured | 2 |

---

### 🌯 Wrap: No Items Match Criteria

These 4 brands have **zero** non-PRESET wrap items with 0 required BOM. The 2 BYO wrap items both have **Naan Bread** (`4000367`) as a `manage_inventory = true` BOM component:

| Item Number | Name | Status | Required BOM |
|-------------|------|--------|-------------|
| `8007402` | Wrap (BYO), Yasas | `FOR_SALE` | Naan Bread (`4000367`) |
| `8011818` | Wrap (BYO), Yasas (C&C Pilot) | `FOR_SALE` | Naan Bread (`4000367`) |

**Why Wrap ≠ Bowl**: Bowl 的承载物是包装材料（`manage_inventory = false`），Wrap 的饼皮（Naan Bread）是食材，必须计入 required inventory。

Wrap BYO items have **5 customization options** — fewer than bowl equivalents.

---

### 🌯 Brand-Specific BYO Bowls（未进入 Top 10 但值得关注）

| Brand | Item Number | Name | Options | Total OV |
|-------|-------------|------|---------|----------|
| Yasas | `8007403` | Bowl (BYO), Yasas | 7 | 46 |
| Hanu Poke | `8010473` | BYO Poke Bowl, Hanu Poke BOWLDER | 7 | 40 |
| Limesalt | `8004638` | Bowl (BYO), Limesalt | 5 | 33 |

---

## Summary

1. **Royal Greens BYO Greens Bowl** is the most customization-rich, with 85 option values across 8 customization categories — all ingredients delivered via customization, BOM contains only packaging
2. **Cook & Chill Pilot** bowls/salads use a different option taxonomy (Grain/Main/Greens/Spreads vs the Toppings/Crunchy/Premium model)
3. **Wrap items fundamentally differ** from bowls: the wrap bread (Naan) is a required BOM component, so no wrap achieves "0 required BOM + pure customization"
4. **Hanu Poke BYO Poke Bowl** has unique poke-specific options (Poke Marinade, Choose Your Sauce) not found in other brands

---

## Query Reference

### Salad/Bowl/Wrap Query (Non-PRESET)

```sql
-- Key filters:
-- 1. 4 brand concept IDs via menus
-- 2. item_versions: effective=true, deleted=false, object_type='MENU', item_customization IS NOT NULL
-- 3. Name LIKE '%salad%' OR '%bowl%' OR '%wrap%', NOT LIKE '%preset%'
-- 4. Exclude items where bom_headers+bom_lines has manage_inventory=true
-- 5. Rank by SUM of all option_values across customization options
```

### BOM Required Check

```sql
-- Items with required BOM:
SELECT DISTINCT bh.item_number
FROM `secure-recipe-prod.recipe_v2.bom_headers` bh
INNER JOIN `secure-recipe-prod.recipe_v2.bom_lines` bl
  ON bh.item_number = bl.bom_header_item_number
  AND CURRENT_TIMESTAMP() BETWEEN TIMESTAMP(bl.service_start_time) AND TIMESTAMP(bl.service_end_time)
WHERE bh.is_active = true AND bl.manage_inventory = true
```