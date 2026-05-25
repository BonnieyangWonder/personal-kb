---
title: IK Dish Type & IK Plating Rule
date: 2026-05-08
created: 2026-05-22
updated: 2026-05-25
type: concept
domain: Cookbook
status: active
tags:
  - cookbook
  - ik
  - plating-rule
  - dish-type
  - line-build
  - kds
sources:
  - https://wonder.atlassian.net/browse/MD-17927
  - https://wonder.atlassian.net/wiki/spaces/SR/pages/4916084781
  - https://wonder.atlassian.net/wiki/spaces/RT/pages/5051580475
  - https://wonder.atlassian.net/wiki/spaces/RT/pages/4990074883
  - https://wonder.atlassian.net/wiki/spaces/SR/pages/4917067798
  - https://wonder.atlassian.net/wiki/spaces/SR/pages/5116362975
  - https://wonder.atlassian.net/wiki/spaces/~712020a23d399f56f34b208584dc6e78d90758/pages/4298440989
  - https://wonder.atlassian.net/wiki/spaces/SR/pages/5217583107
  - https://wonder.atlassian.net/wiki/spaces/RT/pages/5238849564
  - https://wonder.atlassian.net/wiki/spaces/~712020a23d399f56f34b208584dc6e78d90758/pages/5244518402
---

# IK Dish Type & IK Plating Rule

## 1. Business Background

Wonder is integrating Infinite Kitchen (IK) automation equipment into its hybrid pod kitchen workflows. The IK equipment needs two key pieces of information to correctly assemble orders:

1. **Which container (dish/bowl type) to use** → **IK Dish Type**
2. **How to arrange ingredients in that container** → **IK Plating Rule**

These two attributes are configured in Cookbook as item master data. When an order is placed via the consumer app/site, KDS receives the order and fetches the corresponding menu item data (including IK Dish Type and IK Plating Rule) from Cookbook, then routes the relevant information to the IK equipment.

The IK equipment currently needs to support 6 packaging types (Dish Types) and 5 plating rules. These configurations must flexibly accommodate different menu items and different HDR-specific requirements.

### Related Project Context

- **Wonder Create**: Enables influencers to freely create menu items; requires Cookbook to auto-generate line builds (defaulting to aggregating all IK Eligible components into an IK step)
- **IK Eligible Component Flagging**: Already in place at the component item level (`IK Eligible=true/false`). Components marked `true` are aggregated into the IK step in the line build.
- **KDS Routing Logic**: KDS sends IK step components that are actually loaded in the HDR's IK to the IK equipment; unloaded components are routed to the cold pod as garnish steps.

---

## 2. IK Dish Type

### 2.1 Definition

IK Dish Type specifies the container type that the IK equipment should request the Team Member to place. Different menu items may require containers of different sizes and shapes.

### 2.2 Enum Values

| IK Dish Type | Description |
|---|---|
| `48oz Bowl` | 48oz round bowl, used for large salads (e.g., Royal Greens) |
| `32oz Bowl` | 32oz round bowl, used for standard bowls (e.g., Yasas, Hanu Poke) |
| `30oz Oval Metal Bowl` | 30oz oval metal bowl, used for specific bowl types |
| `Bellies Bowl` | Bellies-branded bowl (e.g., Bellies Chicken and Rice) |
| `8oz Cup` | 8oz small cup, used for side items (e.g., white rice, beans, salsa) |
| `Reusable Bowl` | Reusable bowl, used for non-bowl items processed through IK (e.g., burritos, quesadillas, tacos) |

### 2.3 Configuration Level

**Configured at the Menu Item level** (final design decision).

- NOT configured at the component item level
- One menu item has exactly one IK Dish Type
- IK Dish Type may differ from the final packaging (e.g., a quesadilla is processed in a Reusable Bowl in the IK, but is ultimately packaged in a rectangular pulp bowl)

### 2.4 Examples

| Menu Item | IK Dish Type | Notes |
|---|---|---|
| Royal Greens Cobb Salad | 48oz Bowl | Large salad |
| Yasas Bowl | 32oz Bowl | Standard bowl |
| Hanu Poke Bowl | 32oz Bowl | Poke bowl |
| Limesalt Bowl | 30oz Oval Metal Bowl | Oval bowl |
| Bellies Chicken and Rice | Bellies Bowl | Bellies branded |
| Limesalt Burrito | Reusable Bowl | Non-bowl; transferred to final packaging after IK |
| Limesalt Tacos | Reusable Bowl | Same as above |
| Limesalt Quesadilla | Reusable Bowl | Same as above |
| Side white rice / brown rice / poke rice | 8oz Cup | Small side portion |
| Side corn salsa / pico | Reusable Bowl (8oz Cup at FS) | Special: IK processes in reusable bowl, but final packaging at FS uses a 4oz cup |

---

## 3. IK Plating Rule

### 3.1 Definition

IK Plating Rule defines how ingredients should be arranged and dispensed into the container. This directly affects the IK equipment's dispensing behavior (single lap vs. double lap, ingredient drop positioning, etc.).

### 3.2 Enum Values

| IK Plating Rule | Description | Use Case |
|---|---|---|
| `Layering` | Layered placement — all ingredients dispensed in sequence, stacked | Default rule; applicable to most bowl types |
| `Center` | Center placement — all ingredients placed in the center of the dish | Burritos, tacos, quesadillas processed in reusable bowls; side items |
| `Straight` | Straight-line arrangement | Specific bowls (e.g., Limesalt oval bowl); non-layering scenarios |
| `Prelap Center` | Pre-lap followed by center placement | Double Lap (No Action Needed, no FS stop): first collects specific ingredients (e.g., Soba Noodles), centers them after one lap, then runs a second lap for remaining ingredients |
| `Prelap Poke Press` | Pre-lap followed by Poke Press placement | Double Lap (Action Needed) + TM press: first collects Poke Rice + Furikake, centers them, stops at FS for TM to press down, then runs a second lap |

### 3.3 Relationship Between IK Plating Rule and Double Lap

```
Prelap Center       → Double Lap (No Action Needed): Bowl passes through FS without stopping
                       Example: Royal Greens + Soba Noodles
Prelap Poke Press   → Double Lap (Action Needed): Bowl stops at FS, TM presses down, then continues
                       Example: Hanu Poke Bowl with Poke Rice + Furikake
```

`Center` / `Layering` / `Straight` → Standard Single Lap

### 3.4 Configuration Level

**Final decision: Configured at the Menu Item level as a default, with Sub-Step level overrides.**

- **Menu Item level**: Sets the default IK Plating Rule for the menu item. All sub-steps inherit this default.
- **Sub-Step level**: Allows overriding the default for specific sub-steps (e.g., when a particular component/customization requires a different plating method).

### 3.5 Configuration Design Evolution

| Proposal | Proposed | Status |
|---|---|---|
| Configure IK Plating Rule at Component Item level | 2026-05-08 (Bonnie Yang) | ❌ Rejected |
| Menu Item level default + Sub-Step level override | 2026-05-08 (Charlie Fox) / 2026-05-12 (Evan Fox confirmed) | ✅ Accepted |

**Reason the Component-level approach was rejected** (Charlie Fox, 2026-05-08):
- Cannot assume the same component uses the same plating rule in all usage contexts
- Cannot assume the same component always uses the same plating rule even within a specific dish type
- Configuration would become overly complex

### 3.6 Examples

#### Example 1: Royal Greens Cobb Salad customized with Soba Noodles

```
Menu Item Level:
  IK Dish Type: 48oz Bowl
  IK Plating Rule: Layering (default)

Sub-Step Level Override:
  Sub-Step: "Choose your Base → Soba Noodles"
  IK Plating Rule: Prelap Center (override)
  → IK runs first lap collecting Soba Noodles and centers them,
    then runs second lap collecting the remaining ingredients
```

#### Example 2: Hanu Poke Bowl with Poke Rice

```
Menu Item Level:
  IK Dish Type: 32oz Bowl
  IK Plating Rule: Layering (default)

Sub-Step Level Override:
  Sub-Step: "Choose your Base → Sushi Rice (Poke Rice)"
  IK Plating Rule: Prelap Poke Press (override)

  Sub-Step: "Crunchy Toppings → Furikake"
  IK Plating Rule: Prelap Poke Press (override)
  → IK runs first lap collecting Poke Rice + Furikake, centers them,
    stops at FS for TM to press down and confirm, then runs second lap
```

#### Example 3: Limesalt Burrito

```
Menu Item Level:
  IK Dish Type: Reusable Bowl
  IK Plating Rule: Center
  → IK runs a single lap collecting all ingredients and centers them
```

---

## 4. Interaction Rules with IK Eligible

> **Source: MD-17927 (Bonnie Yang's business requirements)**

### 4.1 Core Logic

`IK Eligible` acts as the trigger for IK comparison logic:
- Steps with **IK Eligible = true** → KDS compares the sub-step's component against what is actually loaded in the HDR's IK
  - If loaded in IK → sent to IK for processing
  - If not loaded in IK → KDS routes it as a garnish step to the cold pod
- Steps with **IK Eligible = false** → KDS does not perform the IK comparison

### 4.2 Plating Rule Required vs Optional

| Step's IK Eligible | Plating Rule Requirement | Rationale |
|---|---|---|
| `true` | **Required** (when the sub-step maps to an item/customization) | The IK needs to know how to plate these ingredients |
| `false` | **Optional** (can be null) | The step does not go through IK, but flexibility is preserved |

### 4.3 Design Flexibility Considerations

- **Do NOT prevent** setting a plating rule on sub-steps where `IK Eligible=false`
  - More flexible; non-IK steps carrying a plating rule do not cause issues in KDS
- **Do NOT auto-clear** plating rules when changing `IK Eligible` from true → false
  - The goal is to have more and more HDRs using IK equipment → such limitations are unnecessary
  - Cookbook returns whatever configuration exists in the line build to KDS
  - Whether KDS consumes the plating rule value is determined by the `IK Eligible` flag
- If enforcement is needed in the future: add validation and auto-clear when `IK Eligible` changes from true → false

---

## 5. Solution Design

### 5.1 Cookbook Side

1. **New Menu Item attribute: `IK Dish Type`**
   - Enum: 48oz Bowl / 32oz Bowl / 30oz Oval Metal Bowl / Bellies Bowl / 8oz Cup / Reusable Bowl
   - Configurable on the menu item create/edit page

2. **New Menu Item attribute: `IK Plating Rule` (default)**
   - Enum: Layering / Center / Straight / Prelap Center / Prelap Poke Press
   - Serves as the default plating rule for all IK sub-steps of this menu item

3. **New Line Build Sub-Step attribute: `IK Plating Rule` (overrideable)**
   - Defaults to inheriting the menu item-level IK Plating Rule
   - CE/user can manually modify the plating rule for any sub-step
   - Not influenced by component item-level plating rule configuration
   - If the sub-step belongs to an `IK Eligible=true` step and maps to a component/customization → plating rule is required
   - If the sub-step belongs to an `IK Eligible=false` step → plating rule is optional

4. **Data served to KDS when queried**
   - When KDS fetches a menu item's line build from Cookbook, all configured IK Dish Type and IK Plating Rule values are returned
   - No filtering based on IK Eligible — Cookbook returns whatever is configured

### 5.2 KDS Side

1. **Consuming IK Dish Type**: Sends to IK (in the `dish_type` field of the `POST /orders` API)
2. **Consuming IK Plating Rule**:
   - Only consumes plating rules from sub-steps in `IK Eligible=true` steps
   - If `IK Eligible=false` → ignores the plating rule
3. **IK order API data structure**:
   - Line item level: `dish_type`, `plating_rule`
   - Ingredient level: `plating_rule`

### 5.3 IK Equipment Side

1. Uses `dish_type` to determine which container type to request the TM to place
2. Uses `plating_rule` to determine:
   - Single lap vs. Double Lap
   - Whether to stop at the Finishing Station (FS) and wait for TM interaction
   - How to arrange ingredients in the container (center / layered / straight)

---

## 6. Key Design Decision Records

| # | Decision | Outcome | Decided By | Date |
|---|---|---|---|---|
| 1 | Which level to configure IK Dish Type | **Menu Item level** | Bonnie Yang / Evan Fox | 2026-05-12 |
| 2 | Which level to configure IK Plating Rule | **Menu Item default + Sub-Step override** (NOT Component level) | Charlie Fox / Evan Fox | 2026-05-12 |
| 3 | Is plating rule required when IK Eligible=false | **Optional** (no forced clearing) | Bonnie Yang | MD-17927 |
| 4 | Auto-clear plating rule when IK Eligible changes true→false | **Do NOT auto-clear** | Bonnie Yang | MD-17927 |
| 5 | Should Cookbook filter plating rule by IK Eligible | **No filtering**, pass through everything to KDS | Bonnie Yang | MD-17927 |
| 6 | Support multiple plating rule configs at Component Item level | **No**, simplified approach | Charlie Fox / Evan Fox | 2026-05-12 |

---

## 7. System Context & Data Flow

```
Consumer App / Site
  │
  │ (order placed: contains menu items, customizations)
  ▼
KDS (Kitchen Display System)
  │
  │ (fetches menu item line build, IK Dish Type, IK Plating Rule)
  ▼
Cookbook
  ├── Menu Item: IK Dish Type, IK Plating Rule (default)
  └── Line Build Sub-Step: IK Plating Rule (override)

KDS (after fetching from Cookbook)
  ├── Retrieves IK loaded status for IK Eligible components
  ├── IK Eligible=true → sends to IK (with plating rule)
  └── IK Eligible=false / not IK-loaded → sends to cold pod (ignores plating rule)
       │
       ▼
IK (Infinite Kitchen)
  ├── POST /orders: receives dish_type, plating_rule, ingredients
  ├── BPS: prompts TM to place the corresponding dish type
  └── Executes the specified plating rule (single/double lap, placement style)
       │
       ▼
Finishing Station (FS)
  ├── Bowl Chit: prints QR code, order item info, packaging type, ingredients
  └── FSO Chit: chit for FS-only items
```

---

## 8. Plating Rule → IK Journey Mapping

| Plating Rule | IK Journey | TM Interaction |
|---|---|---|
| `Layering` | Standard Single Lap | None |
| `Center` | Standard Single Lap | None |
| `Straight` | Standard Single Lap | None |
| `Prelap Center` | Double Lap (No Action Needed) | FS pass-through, no stop |
| `Prelap Poke Press` | Double Lap (Action Needed) | FS stops, TM presses to confirm |

---

## 9. Menu Item Configuration Matrix (Full Reference)

| Dish Type | Food Item | IK Plating Rule (Menu Item) | Sub-Step Override |
|---|---|---|---|
| 48oz Bowl | Royal Greens Bowls | Layering | — |
| 48oz Bowl | Royal Greens + Soba Noodles | Layering | Soba Noodles: Prelap Center |
| 32oz Bowl | Yasas Bowls | Layering | — |
| Reusable Bowl | Yasas Sandwiches | Center | — |
| 32oz Bowl | Hanu Poke Bowls (with Poke Rice) | Layering | Sushi Rice + Furikake: Prelap Poke Press |
| 32oz Bowl | Hanu Poke Bowls (Double Greens, no rice) | Layering | — (no override → single lap) |
| 30oz Oval | Limesalt Bowls | Straight | — |
| Reusable Bowl | Limesalt Burritos | Center | — |
| Reusable Bowl | Limesalt Tacos | Layering | — |
| Reusable Bowl | Limesalt Quesadilla | Layering | — |
| 8oz Cup | Side white/brown/poke rice | Center | — |
| Reusable Bowl | Side corn salsa / pico | Center | (Special: transferred to 4oz cup at FS) |
| Bellies Bowl | Bellies Chicken and Rice | Layering | — |
| 32oz Bowl | Side salads (various) | Layering | — |
| 48oz Bowl (default) | New unconfigured items | Layering | — |

---

## 10. Timeline

| Milestone | Target Date |
|---|---|
| Cookbook IK Dish Type & Plating Rule development complete | ~2026-05-25 (1 week before 6/1) |
| KDS data passthrough | 2026-06-01 |
| First integration test (IK simulator) | 2026-06-01 |
| IK lab full test | 2026-06-15 |
| MTE soft launch (Limesalt + Yasas) | 2026-08-10 |
| Full launch | September 2026 |

---

## 11. Dependencies

- **Cookbook**: IK Eligible component flagging + IK Step support in line build (completed, 2026-03)
- **KDS**: IK order dispatch API (`POST /orders`) — `dish_type` and `plating_rule` fields are already defined
- **HDR Portal**: Must support IK pod type configuration (`ik_code`)
- **IK Equipment**: BPS updates to support pre-placement of all 6 dish types; support for all plating rule journeys

---

## 12. Open Questions / Future Iterations

1. **Cross-validation between Dish Type and Plating Rule**: Should Cookbook enforce data entry validation (e.g., certain plating rules are incompatible with certain dish types)?
   - Current decision: No restriction for MVP; IK handles incompatible cases on its own
   - Long term: Upstream protection may be needed
2. **IK Dish Type vs Final Packaging Type on Chits**: Should the chit show the packaging type or the IK Dish Type?
   - MVP: Show packaging type
   - Future: Only show packaging type when it differs from IK Dish Type
3. **Component Item-level plating rule configuration**: Currently rejected. May be reconsidered if operational data patterns indicate a need.
4. **Auto-switching Dish Type based on ingredient count**: Wonder Create may need automatic dish type recommendations based on the number of ingredients.

---

## 13. Reference Pages

| Page | Link |
|---|---|
| **Jira: MD-17927** (IK Dish Type & Plating Rule primary requirement) | [MD-17927](https://wonder.atlassian.net/browse/MD-17927) |
| **Changing Plating Rules Based on Order Item type** (business requirements & examples) | [Confluence](https://wonder.atlassian.net/wiki/spaces/SR/pages/4916084781) |
| **IK Eligible Component Configured in Line Build** (IK Eligible configuration approach) | [Confluence](https://wonder.atlassian.net/wiki/spaces/RT/pages/5051580475) |
| **[WIP] IK Integration** (technical integration & API definitions) | [Confluence](https://wonder.atlassian.net/wiki/spaces/RT/pages/4990074883) |
| **Double Laps for IK Bowls** (Double Lap journey requirements) | [Confluence](https://wonder.atlassian.net/wiki/spaces/SR/pages/4917067798) |
| **Pre-Placing Dishes for Wonder IK** (Dish Type pre-placement) | [Confluence](https://wonder.atlassian.net/wiki/spaces/SR/pages/5116362975) |
| **[WIP] IK integration at hybrid pods PRD** (overall PRD) | [Confluence](https://wonder.atlassian.net/wiki/spaces/~712020a23d399f56f34b208584dc6e78d90758/pages/4298440989) |
| **Chit Updates - MVP** (Chit design) | [Confluence](https://wonder.atlassian.net/wiki/spaces/SR/pages/5217583107) |
| **XM NY Weekly Planning 2026-5-12** (weekly planning) | [Confluence](https://wonder.atlassian.net/wiki/spaces/RT/pages/5238849564) |
| **6/15 Integration Test** (integration test scenarios) | [Confluence](https://wonder.atlassian.net/wiki/spaces/~712020a23d399f56f34b208584dc6e78d90758/pages/5244518402) |
| **Plating Rules Matrix** (Google Sheet) | [Google Sheets](https://docs.google.com/spreadsheets/d/1W2xdmpeZWBDvkZTFOdCSjFiFrDzvlkIfImOwdltLr-k/edit) |
| **Reusable Bowl / "For Here" in the IK** | [Confluence](https://wonder.atlassian.net/wiki/spaces/SR/pages/4916969522) |
