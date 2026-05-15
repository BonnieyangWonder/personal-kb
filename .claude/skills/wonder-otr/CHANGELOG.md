# Wonder OTR Skill Changelog

## 2026-01-14c: Terminology Correction - "Holdback" vs "Delay"

### Changes Made

Replaced "sequencer delay" terminology with "sequencer holdback" throughout the skill for consistency and accuracy:

1. **SKILL.md**
   - Updated "The Hot Hold Problem" section to use "holdback" instead of "delay"
   - Changed "Sequencer-Caused Delay" to "Sequencer Holdback" in root cause tables
   - Updated impact quantification table column header from "Seq Delay" to "Seq Holdback"
   - Changed all references to `delay_duration` to `delay_duration_mins` (the actual field name)

2. **common-pitfalls.md**
   - Updated Pitfall #23 title and content to use "holdback" terminology
   - Changed "sequencer adds delay" to "sequencer holds back items"
   - Updated proof examples to use "holdback" instead of "delay"

### Rationale

"Holdback" is the correct technical term for the sequencer's intentional timing strategy (`delay_duration_mins` field). "Delay" has negative connotations and is a buzzword that implies unintentional slowness. The sequencer is **intentionally holding back** items for coordination purposes, not causing accidental delays.

---

## 2026-01-14b: Added Cross-References to wonder-sequencing Skill

### Changes Made

Added cross-references to the `wonder-sequencing` skill for sequencer-related analysis:

1. **SKILL.md**
   - Added "Related Skills" section explaining when to use wonder-sequencing
   - Added cross-reference in "Queue Time Analysis: Sequencer Holdback vs Capacity"
   - Added cross-reference in "Bad Interaction Bucket: Hot Hold vs A La Minute"

2. **common-pitfalls.md**
   - Added cross-reference in Pitfall #23 (Sequencer's Hot Hold Assumption)

### Purpose

This enables Claude to automatically discover and chain to the wonder-sequencing skill when:
- Analyzing why items are held back
- Understanding ThreeStageWrapper algorithm decisions
- Investigating batch group assignments
- Deep-diving sequencer performance metrics
- Analyzing item-level sequencing scores

The wonder-otr skill focuses on **OTR outcomes and RCA**. The wonder-sequencing skill focuses on **how the sequencer makes decisions**.

---

## 2026-01-14: Context-Aware Threshold Update

### Problem Identified
- **Courier Response** and **Kitchen Handoff** thresholds were incorrectly set at 5 minutes
- Fixed thresholds don't account for segment differences (Urban vs Suburban, Mature vs NSO)
- Severity assessments were misleading across different HDR classes and population types

### Changes Made

#### 1. Corrected Target Thresholds
- **Before:** Courier Response "Fast" = ≤ 5 mins, Handoff "Fast" = ≤ 5 mins
- **After:** Courier Response "Target" = ≤ 2 mins, Handoff "Target" = ≤ 2 mins
- These are FIXED targets that apply universally

#### 2. Introduced Percentile-Based Severity Assessment
- Added guidance to use rolling 6-week percentile-based thresholds
- Segment by `hdr_class` and `population_type` for context-aware severity
- Severity levels: TARGET → NORMAL → ELEVATED → HIGH → CRITICAL

#### 3. Clarified When to Use Fixed vs Percentile
| Use Case | Threshold Type | Reason |
|----------|----------------|--------|
| Kitchen "On Time" (≤2 mins) | **Fixed** | Universal target |
| Courier/Handoff Target (≤2 mins) | **Fixed** | Aspirational goal |
| Courier/Handoff Severity | **Percentile** | Accounts for segment baselines |
| `imperfect_kitchen_items` flags | **Fixed** | Process compliance definitions |

#### 4. Added New Common Pitfall
- **Pitfall #24:** Using Fixed Thresholds for Severity Assessment Across All Segments
- Explains why fixed thresholds fail and how to implement percentile-based approach
- Includes complete SQL example for segment-level benchmarking

### Files Modified

1. **schema-reference.md**
   - Split "RCA Thresholds Reference" into "Fixed Thresholds" and "Context-Aware Thresholds"
   - Added comprehensive SQL example for percentile-based severity classification
   - Documented exception for `imperfect_kitchen_items` flags

2. **common-pitfalls.md**
   - Updated Pitfall #18 (Hardcoding Threshold Values Inconsistently)
   - Added new Pitfall #24 (Using Fixed Thresholds for Severity Assessment)
   - Added cross-references to schema-reference.md

3. **SKILL.md**
   - Updated "Kitchen Handoff Scenarios" thresholds from 5 mins to 2 mins
   - Updated scenario SQL CASE statements to use 2-minute thresholds
   - Updated "Removing Arbitrary Thresholds" section to recommend 6-week percentile approach
   - Added cross-references to detailed guidance

4. **hdr-insights/README.md**
   - Updated threshold table to reflect 2-minute targets
   - Added note about fixed vs percentile usage
   - Updated Profile A/B trigger thresholds

### Impact

**Before:**
```sql
-- Urban Mature store with 4-min courier response flagged as "slow"
-- Suburban NSO store with 4-min courier response also flagged as "slow"
-- Misleading: Urban is actually slow, NSO is performing at segment norm
```

**After:**
```sql
-- Urban Mature: 4 mins vs P50=3 mins → ELEVATED severity (appropriate)
-- Suburban NSO: 4 mins vs P50=7 mins → NORMAL severity (appropriate)
-- Context-aware assessment drives correct interventions
```

### Migration Guide

For existing queries using fixed 5-minute thresholds:

1. **Scenario Classification:** Update to 2-minute targets
2. **Severity Assessment:** Replace fixed thresholds with percentile-based approach
3. **Historical Analysis:** Recalculate baselines using 6-week rolling window
4. **Reporting:** Add segment context (hdr_class, population_type) to all severity reports

### Related Documentation

- [schema-reference.md#context-aware-thresholds](schema-reference.md#context-aware-thresholds-percentile-based)
- [common-pitfalls.md#pitfall-24](common-pitfalls.md#pitfall-24-using-fixed-thresholds-for-severity-assessment-across-all-segments)
