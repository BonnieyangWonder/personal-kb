# OTR Insights Tool

**Interactive HTML dashboard for deep-dive OTR (On-Time Rate) analysis.**

**⚡ Auto-Generate**: When users ask for "OTR insights", "show me HDR X performance", "why was order X late", or "generate WBR summary", immediately run this tool to generate and open the interactive HTML report.

## Purpose

OTR-Insights generates comprehensive, interactive HTML reports for analyzing:

- **HDR-level metrics**: Weekly OTR trends, scenario breakdowns, timing analysis
- **Order-level deep dives**: Individual order root cause analysis
- **Network WBR summaries**: Executive-level weekly business review

## Usage

```bash
# From wonder-otr skill directory:
cd .claude/skills/wonder-otr/hdr-insights

# HDR-level analysis
python3 otr_insights.py "Yardley"
python3 otr_insights.py "West Chester" --weeks 8

# Order-level deep dive
python3 otr_insights.py 6187677

# Network-wide WBR summary
python3 otr_insights.py --network
python3 otr_insights.py --network --weeks 4
```

**Output:** Interactive HTML file saved to `outputs/otr-{type}-{name}-{timestamp}.html` and auto-opened in browser.

## What It Shows

### HDR-Level Report

#### Executive Summary
- **1P OTR**: With WoW change (green/red delta)
- **Kitchen OTR**: Process-level OTR
- **Delivery OTR / Pickup OTR**: Channel breakdown
- **Avg Ticket Time**: With WoW change
- **Orders**: Volume for the week
- **Context**: Population type, HDR class, weeks open

#### Recommendations (Auto-Generated)
Based on the data, the tool automatically identifies:

| Issue Detected | Recommendation |
|----------------|----------------|
| **Profile A** (>10% of orders) | Audit KDS procedures. Stop pre-bumping. |
| **Profile B** (>5% of orders) | Review courier incentives. Adjust dispatch radius. |
| **Kitchen OTR < 55%** | Kitchen speed issue - review ticket time breakdown |
| **High Kitchen OTR, Low Customer OTR** | Focus on sit time reduction, not kitchen speed |

#### Delivery Scenario Breakdown
- **A. Kitchen LATE, Courier Waits**: Kitchen slow, driver waiting
- **B. Kitchen FAST, Food Waits**: Kitchen fast, driver shortage
- **C. Compounding Failure**: Both failed
- **D. Ideal State**: Both on time

Shows OTR, sit time, courier response, and handoff for each scenario.

#### Weekly Trend Chart
Interactive Chart.js line chart showing:
- 1P OTR trend over 6 weeks
- Kitchen OTR trend over 6 weeks

#### Timing Breakdown
Two-column layout showing:
- **Kitchen Stages**: Queue, Cook, Pack/Bag variances from expected
- **Post-Kitchen**: Expo wait, courier response, handoff, transit

### Order-Level Report

#### Order Summary
- **OTR Status**: ON_TIME / EARLY / LATE with badge
- **SLA Difference**: Minutes early/late
- **O2E Time**: Total order-to-eat
- **Ticket Time**: Kitchen execution
- **Expo Wait**: Post-kitchen wait
- **Items**: Count of items in order

#### Order Details Table
- Order number, HDR, date, dining option, channel
- Population type, HDR class

#### Timing Breakdown
- Actual vs Expected vs Variance for Queue, Cook, Pack/Bag
- Post-kitchen timings: Expo, Courier, Handoff, Transit

#### Root Cause Analysis (Auto-Generated)
For **LATE** orders, automatically diagnoses:

| Pattern | Diagnosis |
|---------|-----------|
| Kitchen SLA > 5m, fast handoff/courier | **OPS: Kitchen Slow** |
| Fast courier, slow handoff (> 8m) | **OPS: Slow Handoff (Fake Bump)** |
| Kitchen on time, slow courier (> 10m) | **LOGISTICS: Driver Shortage** |
| Kitchen late AND courier slow | **COMPOUNDING: Both Failed** |

For **EARLY** orders:
- Diagnoses as ETA over-prediction

#### Item Imperfections
Lists any imperfect kitchen items with:
- Force complete flags
- Long queue issues
- Sequencer problems
- Missing pouch issues
- Severity tier

### Network WBR Report

#### Executive Summary
- **Network OTR (1P)**: With WoW delta
- **Delivery OTR / Pickup OTR / Kitchen OTR**
- **Total 1P Orders**
- **Avg Ticket Time**

#### Profile A Locations
Top 10 HDRs with ops failures:
- Fast courier response (≤5m) but slow handoff (>6m)
- Shows ops gap, OTR, population type

#### Profile B Locations
Top 10 HDRs with logistics failures:
- Fast handoff (≤5m) but slow courier (>12m)
- Shows logistics gap, OTR, population type

#### Weekly Breakdown by Population Type
Table showing OTR metrics segmented by:
- Urban / Suburban / Big Box
- Delivery OTR, Pickup OTR, Kitchen OTR

## Technical Details

### Data Sources

```
wonder-dw-prod-brd.orders.hdr_orders                    # Core order metrics
wonder-dw-prod-brd.dw.dim_hdrs                          # HDR attributes
wonder-dw-prod-brd.orders.imperfect_kitchen_items       # Item-level issues
```

### Key Metrics Calculated

| Metric | Definition |
|--------|------------|
| **1P OTR** | Orders with SLA diff between -8.99 and +0.99 mins |
| **Kitchen OTR** | Orders with ready_for_pickup_sla_difference ≤ 2 mins |
| **Profile A %** | % with courier ≤5m AND handoff >8m |
| **Profile B %** | % with courier >15m AND handoff ≤5m |
| **Ops Gap** | handoff - courier_response (positive = ops problem) |

### Thresholds

| Threshold | Value | Used For |
|-----------|-------|----------|
| Kitchen "On Time" | ≤ 2 mins | Kitchen OTR calculation |
| Courier "Fast" | ≤ 5 mins | Profile detection |
| Handoff "Fast" | ≤ 5 mins | Profile detection |
| Profile A trigger | Courier ≤5m, Handoff >8m | Ops failure detection |
| Profile B trigger | Courier >12-15m, Handoff ≤5m | Logistics failure detection |

## Dependencies

- Python 3.x (standard library only)
- `bq` CLI tool (Google Cloud BigQuery)
- Access to `wonder-dw-prod-brd` BigQuery project
- Chart.js 4.4.0 (loaded from CDN)

**No external Python packages required.**

## Example Workflow

```bash
# 1. Deep dive on a specific HDR
python3 otr_insights.py "Yardley"
# Output: outputs/otr-hdr-yardley-2026-01-12-1430.html
# Opens in browser with full analysis + recommendations

# 2. Investigate a specific order
python3 otr_insights.py 6187677
# Output: outputs/otr-order-6187677-2026-01-12-1432.html
# Shows exact timing breakdown + root cause

# 3. Generate WBR summary for leadership
python3 otr_insights.py --network
# Output: outputs/otr-network-2026-01-12-1435.html
# Executive summary with Profile A/B locations
```

## File Output

**Naming Pattern:**
- HDR: `otr-hdr-{name}-{YYYY-MM-DD-HHMM}.html`
- Order: `otr-order-{number}-{YYYY-MM-DD-HHMM}.html`
- Network: `otr-network-{YYYY-MM-DD-HHMM}.html`

**Location:** `outputs/` directory (gitignored)

## Common Use Cases

### 1. "Why is this HDR performing poorly?"
```bash
python3 otr_insights.py "Yardley"
```
Check:
- Profile A/B percentages
- Scenario breakdown (where are orders failing?)
- Timing variances (queue? cook? handoff?)

### 2. "Why was this order late?"
```bash
python3 otr_insights.py 6187677
```
Check:
- Root cause diagnosis (auto-generated)
- Which stage had the biggest variance
- Any imperfect item flags

### 3. "Prepare the weekly WBR"
```bash
python3 otr_insights.py --network --weeks 4
```
Get:
- Network OTR with WoW delta
- Profile A locations (ops failures to audit)
- Profile B locations (logistics issues)
- Breakdown by population type

### 4. "Compare two HDRs"
```bash
python3 otr_insights.py "Yardley"
python3 otr_insights.py "Green Brook"
```
Open both reports side-by-side and compare:
- Where are the timing differences?
- Different profiles (A vs B)?
- Different scenario distributions?

## Troubleshooting

### "No data found for HDR"
- Check HDR name spelling
- HDR name matching is case-insensitive and uses LIKE
- Try partial name: `"Yard"` instead of `"Yardley"`

### "No order found"
- Use the order_number (e.g., `6187677`), not the full UUID
- Order must be within last 90 days
- Order must be COMPLETE status

### "BigQuery Error"
- Ensure `bq` CLI is installed and authenticated
- Run `gcloud auth application-default login` if needed
- Check project access to `wonder-dw-prod-brd`

### Charts not rendering
- Requires internet connection for Chart.js CDN
- Check browser console for errors
- Try refreshing the page

## Integration with wonder-otr Skill

This tool implements the analysis frameworks documented in `SKILL.md`:

- **Kitchen Handoff Scenarios** (A/B/C/D)
- **Profile A/B Detection**
- **Sit Time Decomposition** (Courier Response vs Handoff)
- **Root Cause Attribution**
- **Dual OTR Framework** (Customer vs Kitchen)

The auto-generated recommendations follow the same thresholds and logic patterns.
