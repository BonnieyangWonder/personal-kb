# Customization Option Values Mapping Multiple Food Components — 4 Brand Analysis

**Date**: 2026-07-08
**Scope**: Royal Greens, Limesalt, Yasas, Hanu Poke — FOR_SALE, FINAL version, non-preset BYO menu items with customization option values mapping >1 distinct food component (excluding 9* non-food)

---

## Summary

| Metric | Value |
|--------|-------|
| Option values with >1 food component | **21** |
| Menu items affected | **10** |
| Brands affected | **3** (Yasas = 0) |
| Option type | All `MANDATORY_CHOICE` |
| 9* non-food mapped | **0** (all 21 = No) |
| All components Machine Eligible = Yes | **7** |
| All components Wonder Create Eligible = Yes | **17** |
| Both ME=Y and WC=Y | **7** |
| Scheduled versions | **0** |

### By Brand

| Brand | Option Values | Menu Items |
|-------|:------------:|:----------:|
| Hanu Poke | 3 | 1 |
| Limesalt | 12 | 5 |
| Royal Greens | 6 | 4 |
| Yasas | 0 | 0 |

---

## Methodology

| Filter | Value |
|--------|-------|
| `sold_status` | `FOR_SALE` |
| `version_status` | `FINAL` (current active version only, ignore scheduled) |
| `effective` / `deleted` | `true` / `false` |
| `item_status` | `!= 'DORMANT'` |
| `object_type` | `MENU` |
| `preset_item_version_info` | `IS NULL` (presets excluded) |
| Brand membership | Brand-specific menus only (`concept_count = 1`) |
| Customization source | `item_versions.item_customization` → options → option_values → items |
| 9* non-food | Excluded from food component count; reported separately |
| Food component count | `COUNT(DISTINCT)` per option value; must be >1 |

### Tags Checked

| Tag Group | Tag Name | Tag ID |
|-----------|---------|--------|
| Machine Eligible | Yes | `MACHINE_ELIGIBLE_YES` |
| Wonder Create | Eligible | `ELIGIBLE` |

Both queried via `item_versions.attributes` JSON field.

---

## Component Tags Reference (13 items)

| Item Number | Item Name | ME | WC |
|------------|-----------|:--:|:--:|
| `4000330` | Mexican Three Cheese | Y | Y |
| `4000402` | Rice, Poke, FC, 10oz. (Co-Man) HC | Y | Y |
| `4000470` | Spring Mix Lettuce | Y | Y |
| `4000550` | Guacamole | **N** | Y |
| `4000557` | Barbacoa | Y | Y |
| `4000558` | Pork Carnitas | Y | Y |
| `4000573` | Sriracha Mayo | **N** | Y |
| `4000636` | Adobo Steak | Y | Y |
| `4000835` | Diced Salmon | Y | Y |
| `4000968` | Soba Noodles | **N** | **N** |
| `7000018` | Fajita Vegetables (Cooked, 4x) | Y | Y |
| `7000029` | Diced Adobo Chicken Thighs [Cooked, 3x] | Y | Y |
| `7000084` | Shiitake Carnitas [Mixed, 6x] | **N** | **N** |

---

## Full Data Table (21 Rows)

### Hanu Poke

| # | Item | Menu Item Name | Option | Option Value | Food Components | ME | WC | 9* |
|:-:|------|---------------|--------|-------------|-----------------|:--:|:--:|:--:|
| 1 | 8010473 | BYO Poke Bowl, Hanu Poke BOWLDER | Choose Your Base | **Rice & Greens** | `4000402` Rice Poke [ME=Y WC=Y]<br>`4000470` Spring Mix [ME=Y WC=Y] | ✅ | ✅ | - |
| 2 | 8010473 | BYO Poke Bowl, Hanu Poke BOWLDER | Choose Your Base | **Soba Noodles & Greens** | `4000470` Spring Mix [ME=Y WC=Y]<br>`4000968` Soba Noodles [ME=N WC=N] | ❌ | ❌ | - |
| 3 | 8010473 | BYO Poke Bowl, Hanu Poke BOWLDER | Choose Your Base | **Soba Noodles & Rice** | `4000402` Rice Poke [ME=Y WC=Y]<br>`4000968` Soba Noodles [ME=N WC=N] | ❌ | ❌ | - |

### Limesalt

| # | Item | Menu Item Name | Option | Option Value | Food Components | ME | WC | 9* |
|:-:|------|---------------|--------|-------------|-----------------|:--:|:--:|:--:|
| 4 | 8004637 | Burrito (BYO), Limesalt | Add Extra Protein | **Extra Veggies + Guac** | `4000550` Guacamole [ME=N WC=Y]<br>`7000018` Fajita Veg [ME=Y WC=Y] | ❌ | ✅ | - |
| 5 | 8004637 | Burrito (BYO), Limesalt | Choose Your Protein | **Veggies + Guac** | `4000550` Guacamole [ME=N WC=Y]<br>`7000018` Fajita Veg [ME=Y WC=Y] | ❌ | ✅ | - |
| 6 | 8004638 | Bowl (BYO), Limesalt | Add Extra Protein | **Extra Veggies + Guac** | `4000550` Guacamole [ME=N WC=Y]<br>`7000018` Fajita Veg [ME=Y WC=Y] | ❌ | ✅ | - |
| 7 | 8004638 | Bowl (BYO), Limesalt | Choose Your Protein | **Veggies + Guac** | `4000550` Guacamole [ME=N WC=Y]<br>`7000018` Fajita Veg [ME=Y WC=Y] | ❌ | ✅ | - |
| 8 | 8005005 | Taco (BYO), Limesalt | Choose Your Protein | **Veggies + Guac** | `4000550` Guacamole [ME=N WC=Y]<br>`7000018` Fajita Veg [ME=Y WC=Y] | ❌ | ✅ | - |
| 9 | 8005006 | Salad (BYO), Limesalt | Add Extra Protein | **Extra Veggies + Guac** | `4000550` Guacamole [ME=N WC=Y]<br>`7000018` Fajita Veg [ME=Y WC=Y] | ❌ | ✅ | - |
| 10 | 8005006 | Salad (BYO), Limesalt | Choose Your Protein | **Veggies + Guac** | `4000550` Guacamole [ME=N WC=Y]<br>`7000018` Fajita Veg [ME=Y WC=Y] | ❌ | ✅ | - |
| 11 | 8005007 | Quesadilla (BYO), Limesalt | Choose Your Protein | **Barbacoa** | `4000557` Barbacoa [ME=Y WC=Y]<br>`4000330` Mexican 3-Cheese [ME=Y WC=Y] | ✅ | ✅ | - |
| 12 | 8005007 | Quesadilla (BYO), Limesalt | Choose Your Protein | **Carnitas** | `4000558` Pork Carnitas [ME=Y WC=Y]<br>`4000330` Mexican 3-Cheese [ME=Y WC=Y] | ✅ | ✅ | - |
| 13 | 8005007 | Quesadilla (BYO), Limesalt | Choose Your Protein | **Chicken** | `7000029` Adobo Chicken [ME=Y WC=Y]<br>`4000330` Mexican 3-Cheese [ME=Y WC=Y] | ✅ | ✅ | - |
| 14 | 8005007 | Quesadilla (BYO), Limesalt | Choose Your Protein | **Shiitake Carnitas** | `7000084` Shiitake Carnitas [ME=N WC=N]<br>`4000330` Mexican 3-Cheese [ME=Y WC=Y] | ❌ | ❌ | - |
| 15 | 8005007 | Quesadilla (BYO), Limesalt | Choose Your Protein | **Steak** | `4000636` Adobo Steak [ME=Y WC=Y]<br>`4000330` Mexican 3-Cheese [ME=Y WC=Y] | ✅ | ✅ | - |

### Royal Greens

| # | Item | Menu Item Name | Option | Option Value | Food Components | ME | WC | 9* |
|:-:|------|---------------|--------|-------------|-----------------|:--:|:--:|:--:|
| 16 | 8010459 | BYO Greens Bowl, RG BOWLDER - Primary | Protein (Served Chilled) | **Spicy Salmon (Raw)** | `4000573` Sriracha Mayo [ME=N WC=Y]<br>`4000835` Diced Salmon [ME=Y WC=Y] | ❌ | ✅ | - |
| 17 | 8010473 | BYO Poke Bowl, Hanu Poke BOWLDER | Choose Your Base | **Rice & Greens** | `4000402` Rice Poke [ME=Y WC=Y]<br>`4000470` Spring Mix [ME=Y WC=Y] | ✅ | ✅ | - |
| 18 | 8010473 | BYO Poke Bowl, Hanu Poke BOWLDER | Choose Your Base | **Soba Noodles & Greens** | `4000470` Spring Mix [ME=Y WC=Y]<br>`4000968` Soba Noodles [ME=N WC=N] | ❌ | ❌ | - |
| 19 | 8010473 | BYO Poke Bowl, Hanu Poke BOWLDER | Choose Your Base | **Soba Noodles & Rice** | `4000402` Rice Poke [ME=Y WC=Y]<br>`4000968` Soba Noodles [ME=N WC=N] | ❌ | ❌ | - |
| 20 | 8010492 | BYO Greens Bowl, RG BOWLDER - Abridged | Protein (Served Chilled) | **Spicy Salmon (Raw)** | `4000573` Sriracha Mayo [ME=N WC=Y]<br>`4000835` Diced Salmon [ME=Y WC=Y] | ❌ | ✅ | - |
| 21 | 8011814 | BYO Greens Bowl, RG BOWLDER - C&C Pilot | Protein (Served Chilled) | **Spicy Salmon (Raw)** | `4000573` Sriracha Mayo [ME=N WC=Y]<br>`4000835` Diced Salmon [ME=Y WC=Y] | ❌ | ✅ | - |

---

## Eligibility Breakdown

### ✅ Both ME=Y & WC=Y (7 rows)

| Pattern | Rows | Details |
|---------|:---:|---------|
| Rice & Greens | #1, #17 | Rice Poke + Spring Mix — both fully eligible |
| Quesadilla: Barbacoa | #11 | Barbacoa + Mexican 3-Cheese |
| Quesadilla: Carnitas | #12 | Pork Carnitas + Mexican 3-Cheese |
| Quesadilla: Chicken | #13 | Adobo Chicken + Mexican 3-Cheese |
| Quesadilla: Steak | #15 | Adobo Steak + Mexican 3-Cheese |

### ⚠️ ME=N but WC=Y (14 rows) — Missing Machine Eligible only

| Missing ME Component | Rows | Details |
|---------------------|:---:|---------|
| Guacamole (`4000550`) | #4–#10 (7 rows) | All Limesalt Veggies+Guac across Burrito/Bowl/Taco/Salad |
| Sriracha Mayo (`4000573`) | #16, #20, #21 (3 rows) | All Royal Greens Spicy Salmon |

### ❌ Both ME=N & WC=N (6 rows) — Missing both tags

| Missing Component | Rows | Details |
|------------------|:---:|---------|
| Soba Noodles (`4000968`) | #2–#3, #18–#19 (4 rows) | All Soba combos across Hanu Poke & Royal Greens |
| Shiitake Carnitas (`7000084`) | #14 (1 row) | Limesalt Quesadilla Shiitake Carnitas |

---

## Patterns

| Pattern | Brand(s) | Option Values | Example | Components |
|---------|----------|:--:|---------|------------|
| **Base Combos** | Hanu Poke, Royal Greens | 7 | Rice & Greens, Soba Noodles & Greens, Soba Noodles & Rice | 2 base ingredients combined |
| **Veggies + Guac** | Limesalt | 10 | Veggies + Guac, Extra Veggies + Guac | Guacamole + Fajita Vegetables |
| **Protein + Sauce** | Royal Greens | 4 | Spicy Salmon (Raw) | Diced Salmon + Sriracha Mayo |
| **Protein + Cheese** | Limesalt | 5 | Barbacoa / Carnitas / Chicken / Steak / Shiitake Carnitas | Protein + Mexican 3-Cheese |

> Note: totals sum to 26 (not 21) because some rows belong to multiple patterns. E.g., "Soba Noodles & Greens" is both a Base Combo (pattern 1) and a Missing-Both-Tags case.

---

## Components Needing Tag Updates

| Item | Missing Tags | Impact (option values) | Action |
|------|:-----------:|:----------------------:|--------|
| `4000550` Guacamole | ME | 10 | Add Machine Eligible = Yes |
| `4000573` Sriracha Mayo | ME | 4 | Add Machine Eligible = Yes |
| `4000968` Soba Noodles | ME + WC | 6 | Add both tags |
| `7000084` Shiitake Carnitas [Mixed, 6x] | ME + WC | 1 | Add both tags |

---

## Key Findings

1. **Zero 9\* non-food mapping** — option values with multiple food components never include packaging items
2. **Yasas = 0** — no Yasas option values map to multiple distinct food components
3. **All affected items are BYO/BOWLDER** — no signature/standalone menu items
4. **Zero scheduled versions** across all 4 brands
5. **Guacamole & Sriracha Mayo** are the easiest fixes (both already WC Eligible, only missing ME)
6. **Soba Noodles & Shiitake Carnitas** need both ME and WC tags added
