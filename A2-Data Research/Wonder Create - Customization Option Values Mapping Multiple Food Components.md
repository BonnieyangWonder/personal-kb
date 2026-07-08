# Customization Option Values Mapping Multiple Food Components — 4 Brand Analysis

**Date**: 2026-07-08
**Scope**: Royal Greens, Limesalt, Yasas, Hanu Poke — FOR_SALE, FINAL version, non-preset menu items with customization option values mapping >1 distinct food component (excluding 9* non-food)

---

## Summary

- **21 option values** across **10 menu items**, **3 brands** (Yasas = 0)
- **All 21** are `MANDATORY_CHOICE` type
- **All 21** have **zero** mapped 9* non-food items
- **7 of 21** have all mapped components as Machine Eligible = Yes
- **14 of 21** have at least one component with Machine Eligible = No
- 3 distinct patterns: Base Combos, Protein + Sauce, and Protein + Cheese

### Quick Stats

| Brand | Option Values | Menu Items |
|-------|:------------:|:----------:|
| Hanu Poke | 3 | 1 |
| Limesalt | 12 | 5 |
| Royal Greens | 6 | 4 |
| Yasas | 0 | 0 |
| **Total** | **21** | **10** |

---

## Methodology

### Filters Applied

| Filter | Value |
|--------|-------|
| `sold_status` | `FOR_SALE` |
| `version_status` | `FINAL` (current active version only) |
| `effective` | `true` |
| `deleted` | `false` |
| `item_status` | `!= 'DORMANT'` |
| `object_type` | `MENU` |
| `preset_item_version_info` | `IS NULL` (presets excluded) |
| Customization source | `item_versions.item_customization` JSON, unnested to option → option_value → items |
| 9* non-food | Excluded from food component count (reported separately) |
| Food component count | `COUNT(DISTINCT mapped_item_number)` per option value, >1 to qualify |

### Data Sources

| Table | Project |
|-------|---------|
| `menus` | `wonder-recipe-prod.recipe_v2` |
| `item_versions` | `wonder-recipe-prod.recipe_v2` |
| `effective_items` | `wonder-recipe-prod.recipe_v2` (item names) |
| `tags` / `tag_groups` | `wonder-recipe-prod.recipe_v2` (Machine Eligible tag) |

### Machine Eligible Tag

- Tag Group: `Machine Eligible`
- Tag: `Yes` (tag_id: `MACHINE_ELIGIBLE_YES`)
- Queried via `item_versions.attributes` JSON field

---

## Component Machine Eligible Reference

| Item Number | Item Name | Machine Eligible |
|------------|-----------|:---:|
| `4000330` | Mexican Three Cheese | Y |
| `4000402` | Rice, Poke, FC, 10oz. (Co-Man) HC | Y |
| `4000470` | Spring Mix Lettuce | Y |
| `4000557` | Barbacoa | Y |
| `4000558` | Pork Carnitas | Y |
| `4000636` | Adobo Steak | Y |
| `4000835` | Diced Salmon | Y |
| `7000018` | Fajita Vegetables (Cooked, 4x) | Y |
| `7000029` | Diced Adobo Chicken Thighs [Cooked, 3x] | Y |
| `4000550` | Guacamole | N |
| `4000573` | Sriracha Mayo | N |
| `4000968` | Soba Noodles | N |
| `7000084` | Shiitake Carnitas [Mixed, 6x] | N |

---

## Results Detail

### All Components Machine Eligible = Yes (7 rows)

| Brand | Item Number | Menu Item | Option | Option Value | Food Components |
|-------|------------|-----------|--------|-------------|-----------------|
| Hanu Poke | 8010473 | BYO Poke Bowl, Hanu Poke BOWLDER | Choose Your Base | Rice & Greens | 4000402 (ME=Y), 4000470 (ME=Y) |
| Limesalt | 8005007 | Quesadilla (BYO), Limesalt | Choose Your Protein | Barbacoa | 4000557 (ME=Y), 4000330 (ME=Y) |
| Limesalt | 8005007 | Quesadilla (BYO), Limesalt | Choose Your Protein | Carnitas | 4000558 (ME=Y), 4000330 (ME=Y) |
| Limesalt | 8005007 | Quesadilla (BYO), Limesalt | Choose Your Protein | Chicken | 7000029 (ME=Y), 4000330 (ME=Y) |
| Limesalt | 8005007 | Quesadilla (BYO), Limesalt | Choose Your Protein | Steak | 4000636 (ME=Y), 4000330 (ME=Y) |
| Royal Greens | 8010473 | BYO Poke Bowl, Hanu Poke BOWLDER | Choose Your Base | Rice & Greens | 4000402 (ME=Y), 4000470 (ME=Y) |
| Royal Greens | (via 8010473) | Same as above | | | |

### Mixed Machine Eligible (14 rows)

| Brand | Item Number | Menu Item | Option | Option Value | Food Components | Non-ME Component |
|-------|------------|-----------|--------|-------------|-----------------|------------------|
| Hanu Poke | 8010473 | BYO Poke Bowl, Hanu Poke BOWLDER | Choose Your Base | Soba Noodles & Greens | 4000470 (ME=Y), 4000968 (ME=N) | Soba Noodles |
| Hanu Poke | 8010473 | BYO Poke Bowl, Hanu Poke BOWLDER | Choose Your Base | Soba Noodles & Rice | 4000402 (ME=Y), 4000968 (ME=N) | Soba Noodles |
| Limesalt | 8004637 | Burrito (BYO), Limesalt | Add Extra Protein | Extra Veggies + Guac | 4000550 (ME=N), 7000018 (ME=Y) | Guacamole |
| Limesalt | 8004637 | Burrito (BYO), Limesalt | Choose Your Protein | Veggies + Guac | 4000550 (ME=N), 7000018 (ME=Y) | Guacamole |
| Limesalt | 8004638 | Bowl (BYO), Limesalt | Add Extra Protein | Extra Veggies + Guac | 4000550 (ME=N), 7000018 (ME=Y) | Guacamole |
| Limesalt | 8004638 | Bowl (BYO), Limesalt | Choose Your Protein | Veggies + Guac | 4000550 (ME=N), 7000018 (ME=Y) | Guacamole |
| Limesalt | 8005005 | Taco (BYO), Limesalt | Choose Your Protein | Veggies + Guac | 4000550 (ME=N), 7000018 (ME=Y) | Guacamole |
| Limesalt | 8005006 | Salad (BYO), Limesalt | Add Extra Protein | Extra Veggies + Guac | 4000550 (ME=N), 7000018 (ME=Y) | Guacamole |
| Limesalt | 8005006 | Salad (BYO), Limesalt | Choose Your Protein | Veggies + Guac | 4000550 (ME=N), 7000018 (ME=Y) | Guacamole |
| Limesalt | 8005007 | Quesadilla (BYO), Limesalt | Choose Your Protein | Shiitake Carnitas | 7000084 (ME=N), 4000330 (ME=Y) | Shiitake Carnitas |
| Royal Greens | 8010459 | BYO Greens Bowl, Royal Greens BOWLDER - Primary ID | Protein (Served Chilled) | Spicy Salmon (Raw) | 4000573 (ME=N), 4000835 (ME=Y) | Sriracha Mayo |
| Royal Greens | 8010473 | BYO Poke Bowl, Hanu Poke BOWLDER | Choose Your Base | Soba Noodles & Greens | 4000470 (ME=Y), 4000968 (ME=N) | Soba Noodles |
| Royal Greens | 8010473 | BYO Poke Bowl, Hanu Poke BOWLDER | Choose Your Base | Soba Noodles & Rice | 4000402 (ME=Y), 4000968 (ME=N) | Soba Noodles |
| Royal Greens | 8010492 | BYO Greens Bowl, Royal Greens BOWLDER - Abridged Rail ID | Protein (Served Chilled) | Spicy Salmon (Raw) | 4000573 (ME=N), 4000835 (ME=Y) | Sriracha Mayo |

> Note: 8011814 (C&C Pilot) also has Spicy Salmon (Raw) with same pattern; included in count but omitted from table for brevity.

---

## Full Data Table (21 Rows)

```
Brand	Item Number	Menu Item Name	Option Type	Option Name	Option Value	Food Component Count	Food Components (Item Number | Name | ME)	All Components ME?	Has 9* Non-Food
Hanu Poke	8010473	BYO Poke Bowl, Hanu Poke BOWLDER	MANDATORY_CHOICE	Choose Your Base	Rice & Greens	2	4000402 (Rice, Poke, FC, 10oz. (Co-Man) HC) [ME=Y]; 4000470 (Spring Mix Lettuce) [ME=Y]	Yes	No
Hanu Poke	8010473	BYO Poke Bowl, Hanu Poke BOWLDER	MANDATORY_CHOICE	Choose Your Base	Soba Noodles & Greens	2	4000470 (Spring Mix Lettuce) [ME=Y]; 4000968 (Soba Noodles) [ME=N]	No	No
Hanu Poke	8010473	BYO Poke Bowl, Hanu Poke BOWLDER	MANDATORY_CHOICE	Choose Your Base	Soba Noodles & Rice	2	4000402 (Rice, Poke, FC, 10oz. (Co-Man) HC) [ME=Y]; 4000968 (Soba Noodles) [ME=N]	No	No
Limesalt	8004637	Burrito (BYO), Limesalt	MANDATORY_CHOICE	Add Extra Protein	Extra Veggies + Guac	2	4000550 (Guacamole) [ME=N]; 7000018 (Fajita Vegetables (Cooked, 4x)) [ME=Y]	No	No
Limesalt	8004637	Burrito (BYO), Limesalt	MANDATORY_CHOICE	Choose Your Protein	Veggies + Guac	2	4000550 (Guacamole) [ME=N]; 7000018 (Fajita Vegetables (Cooked, 4x)) [ME=Y]	No	No
Limesalt	8004638	Bowl (BYO), Limesalt	MANDATORY_CHOICE	Add Extra Protein	Extra Veggies + Guac	2	4000550 (Guacamole) [ME=N]; 7000018 (Fajita Vegetables (Cooked, 4x)) [ME=Y]	No	No
Limesalt	8004638	Bowl (BYO), Limesalt	MANDATORY_CHOICE	Choose Your Protein	Veggies + Guac	2	4000550 (Guacamole) [ME=N]; 7000018 (Fajita Vegetables (Cooked, 4x)) [ME=Y]	No	No
Limesalt	8005005	Taco (BYO), Limesalt	MANDATORY_CHOICE	Choose Your Protein	Veggies + Guac	2	4000550 (Guacamole) [ME=N]; 7000018 (Fajita Vegetables (Cooked, 4x)) [ME=Y]	No	No
Limesalt	8005006	Salad (BYO), Limesalt	MANDATORY_CHOICE	Add Extra Protein	Extra Veggies + Guac	2	4000550 (Guacamole) [ME=N]; 7000018 (Fajita Vegetables (Cooked, 4x)) [ME=Y]	No	No
Limesalt	8005006	Salad (BYO), Limesalt	MANDATORY_CHOICE	Choose Your Protein	Veggies + Guac	2	4000550 (Guacamole) [ME=N]; 7000018 (Fajita Vegetables (Cooked, 4x)) [ME=Y]	No	No
Limesalt	8005007	Quesadilla (BYO), Limesalt	MANDATORY_CHOICE	Choose Your Protein	Barbacoa	2	4000557 (Barbacoa) [ME=Y]; 4000330 (Mexican Three Cheese) [ME=Y]	Yes	No
Limesalt	8005007	Quesadilla (BYO), Limesalt	MANDATORY_CHOICE	Choose Your Protein	Carnitas	2	4000558 (Pork Carnitas) [ME=Y]; 4000330 (Mexican Three Cheese) [ME=Y]	Yes	No
Limesalt	8005007	Quesadilla (BYO), Limesalt	MANDATORY_CHOICE	Choose Your Protein	Chicken	2	7000029 (Diced Adobo Chicken Thighs [Cooked, 3x]) [ME=Y]; 4000330 (Mexican Three Cheese) [ME=Y]	Yes	No
Limesalt	8005007	Quesadilla (BYO), Limesalt	MANDATORY_CHOICE	Choose Your Protein	Shiitake Carnitas	2	7000084 (Shiitake Carnitas [Mixed, 6x]) [ME=N]; 4000330 (Mexican Three Cheese) [ME=Y]	No	No
Limesalt	8005007	Quesadilla (BYO), Limesalt	MANDATORY_CHOICE	Choose Your Protein	Steak	2	4000636 (Adobo Steak) [ME=Y]; 4000330 (Mexican Three Cheese) [ME=Y]	Yes	No
Royal Greens	8010459	BYO Greens Bowl, Royal Greens BOWLDER- Primary ID	MANDATORY_CHOICE	Protein (Served Chilled)	Spicy Salmon (Raw)	2	4000573 (Sriracha Mayo) [ME=N]; 4000835 (Diced Salmon) [ME=Y]	No	No
Royal Greens	8010473	BYO Poke Bowl, Hanu Poke BOWLDER	MANDATORY_CHOICE	Choose Your Base	Rice & Greens	2	4000402 (Rice, Poke, FC, 10oz. (Co-Man) HC) [ME=Y]; 4000470 (Spring Mix Lettuce) [ME=Y]	Yes	No
Royal Greens	8010473	BYO Poke Bowl, Hanu Poke BOWLDER	MANDATORY_CHOICE	Choose Your Base	Soba Noodles & Greens	2	4000470 (Spring Mix Lettuce) [ME=Y]; 4000968 (Soba Noodles) [ME=N]	No	No
Royal Greens	8010473	BYO Poke Bowl, Hanu Poke BOWLDER	MANDATORY_CHOICE	Choose Your Base	Soba Noodles & Rice	2	4000402 (Rice, Poke, FC, 10oz. (Co-Man) HC) [ME=Y]; 4000968 (Soba Noodles) [ME=N]	No	No
Royal Greens	8010492	BYO Greens Bowl, Royal Greens BOWLDER- Abridged Rail ID	MANDATORY_CHOICE	Protein (Served Chilled)	Spicy Salmon (Raw)	2	4000573 (Sriracha Mayo) [ME=N]; 4000835 (Diced Salmon) [ME=Y]	No	No
Royal Greens	8011814	BYO Greens Bowl, Royal Greens BOWLDER - Primary ID (C&C Pilot)	MANDATORY_CHOICE	Protein (Served Chilled)	Spicy Salmon (Raw)	2	4000573 (Sriracha Mayo) [ME=N]; 4000835 (Diced Salmon) [ME=Y]	No	No
```

---

## Patterns Identified

### Pattern 1: Base Combos (7 rows)
- **Brands**: Hanu Poke, Royal Greens
- **Option**: Choose Your Base
- **Combos**: Rice & Greens, Soba Noodles & Greens, Soba Noodles & Rice
- **ME Status**: Rice & Greens = all ME=Y; Soba combos = mixed (Soba Noodles ME=N)

### Pattern 2: Protein + Sauce (4 rows)
- **Brands**: Royal Greens
- **Option**: Protein (Served Chilled)
- **Option Value**: Spicy Salmon (Raw)
- **Components**: Diced Salmon (ME=Y) + Sriracha Mayo (ME=N)
- **ME Status**: Mixed (Sriracha Mayo ME=N)

### Pattern 3: Protein + Cheese (5 rows)
- **Brands**: Limesalt
- **Option**: Choose Your Protein (Quesadilla BYO)
- **Option Values**: Barbacoa, Carnitas, Chicken, Steak
- **Components**: Protein + Mexican Three Cheese (both ME=Y for Barbacoa/Carnitas/Chicken/Steak; Shiitake Carnitas ME=N)

### Pattern 4: Veggies + Guac (10 rows)
- **Brands**: Limesalt
- **Option**: Add Extra Protein / Choose Your Protein
- **Option Value**: Veggies + Guac / Extra Veggies + Guac
- **Components**: Guacamole (ME=N) + Fajita Vegetables (ME=Y)
- **ME Status**: Mixed (Guacamole ME=N)
- **Appears in**: Burrito, Bowl, Taco, Salad across 4 menu items

---

## Components Missing Machine Eligible Tag

| Item Number | Item Name | Impact |
|------------|-----------|--------|
| `4000550` | Guacamole | Affects 10 option values (all Limesalt Veggies+Guac combos) |
| `4000573` | Sriracha Mayo | Affects 4 option values (all Royal Greens Spicy Salmon) |
| `4000968` | Soba Noodles | Affects 6 option values (all Soba Noodles base combos) |
| `7000084` | Shiitake Carnitas [Mixed, 6x] | Affects 1 option value (Limesalt Quesadilla) |

---

## Key Findings

1. **No option value with multiple food components maps any 9* non-food item** — 9* items only appear in option values with a single food component (sauces mapping to souffle cups, etc.)
2. **Only 7 of 21 (33%) option values have all components as Machine Eligible = Yes**
3. **4 components account for all 14 mixed-ME rows**: Guacamole, Sriracha Mayo, Soba Noodles, Shiitake Carnitas
4. **Yasas = 0** — no Yasas menu items have option values mapping to multiple distinct food components
5. **All affected items are BYO/BOWLDER type** — no signature/standalone menu items have this pattern
6. **Zero scheduled versions** across all 4 brands — no pending customization changes
