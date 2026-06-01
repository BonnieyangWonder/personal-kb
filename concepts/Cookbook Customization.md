---
title: Cookbook Customization
date: 2026-05-29
created: 2026-06-01
updated: 2026-06-01
type: concept
domain: cookbook
tags:
  - cookbook
  - recipe-management
status: active
description: Customer choice system for Wonder menu items — option types, selection modes, pricing, BOM mapping, presets, and availability impact.
sources:
  - Z01-Resource/CB-business/features/customization.md
author: bonnie
---

# Cookbook Customization

Customization allows Wonder customers to personalize dishes — choosing proteins, adding toppings, requesting sauce on the side, or removing ingredients. A single BYO menu item can produce thousands of order variants.

Data flows to: **Wonder App** (customer display), **KDS** (kitchen execution), **Pantry** (availability calculation).

## Two Type Systems

Customization has **two independent properties**:

### Option Type — What category of choice?

| Option Type | Inventory Impact | Usage Qty | Pricing |
|-------------|-----------------|-----------|----------|
| **Mandatory Choice** | Yes | Required | Yes |
| **Optional Addition** | Yes | Required | Yes |
| **Extra Request** | Yes | Required | Yes |
| **Dish Preference** | No | No | Yes |
| **Optional Subtraction** | No | No | Never |
| **On the Side** | No | No | Never |

"If no BOM (`noBom=true`): only Mandatory Choice, Dish Preference, and Optional Addition available."

### Selection Mode — How does the customer pick?

| Mode | Behavior |
|------|----------|
| **Single-select** (default) | Each option picked at most once |
| **Multi-select** | Same option can be picked multiple times (max required) |
| **Partial-select** | Two different options at half-portion each (max must = 1) |

## Pricing and Free Choices

- **BQ field name is `price`** — NOT `default_price`. `$.default_price` returns NULL.
- **Free Choices**: First N selections are free; beyond N, charged at unit price.
- Free Choices ≥ min selections and ≤ max selections required.

## Display: Featured vs In-Drawer

| Display | Types Allowed |
|---------|--------------|
| **Featured** (visible immediately) | Mandatory Choice (forced), Optional Addition, Dish Preference |
| **In-Drawer** (inside "Customize") | Optional Subtraction, On the Side, Extra Request (forced) |

## BOM Mapping

| Option Type | Mapping Required | Multi-item |
|-------------|-----------------|------------|
| Mandatory Choice | Yes | Yes |
| Optional Addition | Yes | Yes |
| Extra Request | Yes | Yes |
| Optional Subtraction | Yes | Yes |
| On the Side | Yes | One item only |
| Dish Preference | Optional | One item only |

**Outside-BOM mapping** (MD-17334): Dish Preference, On the Side, and Optional Subtraction can now map to items outside the BOM tree.

## Presets

A preset is an **independent 80\* menu item** with its own item number, version lifecycle, and nutrition. Not just a saved selection — a first-class item in all downstream systems.

Each preset can independently vary: min/max selections, free choices count, selection mode, ineligible options, default portions.

Use `preset_item_version_info` in BQ. The older `item_customization_presets` is deprecated.

## Availability Impact

Only Mandatory Choice, Optional Addition, and Extra Request affect availability:

- **Single-select**: Ranked-option algorithm (highest-stock option first)
- **Multi-select**: `floor(sum of all option quantities ÷ min)`
- **Partial-select**: `floor(sum ÷ min)` with 0.5 rounding

If a Mandatory Choice has a "None" option, it's treated as unlimited.

## Related

- [[Cookbook]] — system overview
- [[Cookbook BOM Structure]] — how customizations interact with BOM
- [[Cookbook Line Build]] — conditional sub-steps tied to customizations
- [[Z01-Resource/CB-business/features/customization.md]] — full reference
