---
title: Cookbook Wonder Create
date: 2026-05-29
created: 2026-06-01
updated: 2026-06-01
type: concept
domain: cookbook
tags:
  - cookbook
  - product-development
status: active
description: Fully-automated menu item creation for influencer virtual restaurants — AI line build generation, publish pipeline, component eligibility, and Machine Eligible flags.
sources:
  - Z01-Resource/CB-business/features/wonder-create.md
author: bonnie
---

# Cookbook Wonder Create

Wonder Create (WC) lets influencers and celebrities design virtual restaurant dishes through an AI chatbot. Cookbook receives creation requests from the WC Orchestration Service and turns them into fully-published, kitchen-ready MENU items — no manual CDT/CE involvement.

WC items are standard 80\* MENU items, identified by a `wonder_create_external_id` field. They run on existing IKC speedline infrastructure using only already-available ingredient pools.

## Creation Flow

### Phase 1 — Influencer design (outside Cookbook)
Influencer uses AI chatbot to name their brand and select components from `wc_available_items` BQ view.

### Phase 2 — Validate (read-only)
`POST /wonder-create/validate` — checks all validation rules, returns flat error list. No writes.

### Phase 3 — Publish (writes to Cookbook)
`POST /wonder-create/publish` pipeline:
1. Idempotency check (`request_task_id`)
2. Validate (abort on any failure)
3. Brand upsert (brand + concept 1:1)
4. Item upsert (80\* MENU with BOM)
5. Defaults applied (package SKUs, service location = "No Selection")
6. Nutrition calculated
7. Publish with `ignoreCheck=true` — bypasses standard human checklist
8. Line Build Agent triggered asynchronously

## Component Eligibility

Components must be:
- `HDR_CONSUMABLE_ITEM` (40\*), `HDR_RECIPE` (70\*), or `NON_FOOD` (90\*)
- Have `WONDER_CREATE: ELIGIBLE` attribute tag
- Not dormant; published FINAL version with valid service window

**Not eligible**: Regular MENU (80\*), INGREDIENT (50\*).

## Two Key Flags (Don't Confuse)

| Flag | Attribute | Meaning |
|------|-----------|---------|
| **WC Eligible** | `WONDER_CREATE: ELIGIBLE` | Can be used in WC menus at all |
| **Machine Eligible** | `MACHINE_ELIGIBLE_YES` | Can be processed by IK machine at garnish step |

An item can have one, both, or neither.

## Auto Line Build Generation

Two-part process runs asynchronously after publish:

1. **Skeleton** (code): Builds structure: GARNISH placeholder → COOK per cooked component → GARNISH assembly → COMPLETE
2. **LLM fill**: Gemini Flash fills in appliance, cook time, batch limit, step time, parking spot, sub-step titles. Uses most frequent historical cook method per component.

**Fallback**: Rule-based defaults if LLM fails after 2 retries. Scheduled job runs every 10 min.

WC line builds use: IK Step (for IK-eligible) + GARNISH (for non-IK) + COMPLETE. No thermal COOK steps.

## Key Differences from Regular Items

- Bypasses standard publish checklist via `ignoreCheck=true`
- No CE manual review — fully automated
- No customization support in MVP
- Updates to live items are scheduled for "tomorrow at NY midnight" (not immediate)
- Component changes trigger line build regeneration

## Related

- [[Cookbook]] — system overview
- [[Cookbook Line Build]] — activity types and KDS station roles
- [[Cookbook Version Publish]] — how standard publish differs
- [[Cookbook 40-41 Model]] — 40\* items are primary WC component type
- [[Z01-Resource/CB-business/features/wonder-create.md]] — full reference
