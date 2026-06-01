---
title: Cookbook Line Build
date: 2026-05-29
created: 2026-06-01
updated: 2026-06-01
type: concept
domain: cookbook
tags:
  - cookbook
  - kitchen-operations
status: active
description: Kitchen execution blueprints for menu items — 4-level hierarchy, activity types, KDS station roles, appliance config, hot hold, and IK Step.
sources:
  - Z01-Resource/CB-business/features/line-build.md
  - Z01-Resource/CB-bigquery/schema-reference.md
author: bonnie
---

# Cookbook Line Build

A line build is the **kitchen execution blueprint** for a menu item. It tells the Kitchen Display System (KDS) what to do: which station, what equipment, how long, and in what sequence.

## Four-Level Hierarchy

| Level | Name | Business Meaning |
|-------|------|-----------------|
| 1 | **LineBuild** | Complete operational flow for one item (or option scope) |
| 2 | **Task** | Named parallel workflow (one per cooking path) |
| 3 | **Step (Procedure)** | Single kitchen action: one activity type, one appliance, one set of timing |
| 4 | **Sub-step (ProcedureStep)** | Specific instruction mapped to one BOM ingredient or customization option |

An item can have **multiple line builds**, each scoped by **restaurant** and/or **customization option value**.

## Activity Types and KDS Stations

| Activity | KDS Station | What it does |
|----------|------------|-------------|
| **COOK** | Hot Pod | Active cooking (turbo oven, fryer, etc.). Requires appliance + cook time > 0. |
| **GARNISH** | Cold Pod | Cold assembly, pressing, toasting. No appliance. Cook time = 0. |
| **COMPLETE** | Expo | Final check, packaging, handoff. Must be last non-Vend step. |
| **VEND** | Vending pod | Dispense pre-packaged component. |
| **IK Step** | Intelligent Kitchen | Route IK-eligible components to the IK machine. |

## Key Configuration Rules

**COOK**: Appliance required. Cook time > 0. Batch limit required. Four appliances need Global Appliance Config: Turbo Oven, Fryer Basket, Pizza Conveyor Oven, Clamshell Griddle.

**COMPLETE**: At least one required. Must be last (Vend after is OK). Requires Parking Spot (AMBIENT or WARM).

**Hot Hold (HH)**: Alternative mode for batch-cooked items held warm. Specifies retherm appliance/time, holding appliance/time, batch limit, parking spot.

## IK Step (Intelligent Kitchen)

Instead of mapping to specific appliance slots, IK Step maps **all IK-eligible components** to sub-steps. At runtime, KDS checks which components are loaded in the IK machine:

- Loaded → dispatched to IK machine
- Not loaded → fall back to GARNISH (Cold Pod)

One line build covers all restaurant variants without per-location configs.

## Line Build Status

| Status | Meaning |
|--------|---------|
| **None** | No line build configured |
| **Line Build Created** | Active and valid |
| **Pending Update** | Unresolved mapping warnings (usually from BOM changes) |

Pending Update is a **warning** — the item can still be served.

## BQ Table: `item_line_builds`

Key fields: `item_number`, `procedures_appliance`, `procedures_activity`, `procedures_cooking_phase`, `cooking_time`, `step_time`, `resting_time`, `hold_time`, `is_hot_hold_eligible_selected`, `show_hot_hold`, `restaurant_id`.

Always filter service windows: `CURRENT_TIMESTAMP() BETWEEN TIMESTAMP(service_start_time) AND TIMESTAMP(service_end_time)`.

## Related

- [[Cookbook]] — system overview
- [[Cookbook BOM Structure]] — BOM changes trigger "Pending Update"
- [[Cookbook Customization]] — conditional sub-steps
- [[Cookbook Wonder Create]] — AI-generated line builds
- [[Z01-Resource/CB-business/features/line-build.md]] — full reference
