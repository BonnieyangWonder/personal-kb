# HDR-Insights Tool

**Interactive HTML dashboard for deep-dive analysis of individual Wonder order sequencing performance.**

**⚡ Auto-Generate**: When users ask for "HDR-insights", "hdr insights", "order details", "show me order X", or "why did order X perform poorly", immediately run this tool to generate and open the interactive HTML report.

## Purpose

HDR-Insights generates a comprehensive, interactive HTML report for analyzing **one specific order** showing:

- **Order Summary**: Timing, channel, status, O2E performance metrics
- **Order Items**: All menu items with categories and quantities
- **Timeline Scrubber**: Navigate through ALL sequencing runs for the order with Previous/Next controls
- **Interactive Charts**: Visualize score trends (expo sit time, customer promise) across all runs
- **Target Order Details**: Item-level scores, holdback strategies, estimated wait times
- **Kitchen Context**: Other orders in the same sequencing run with rankings
- **Kitchen State (Pods)**: Real-time pod/appliance state with cooking items, queued items, and timers
- **Batch Groups**: Complete batch group assignments with human-readable pod codes
- **Performance Comparison**: See how the target order ranked vs all other orders (percentile)

**Key Feature**: Timeline scrubbing allows you to see how sequencing predictions changed over time as the order was re-optimized every 30+ seconds.

## Usage

```bash
# From wonder-sequencing skill directory:
python3 hdr-insights-tool/hdr_insights.py <order_number_or_id>
```

**Example:**
```bash
python3 hdr-insights-tool/hdr_insights.py 6187677
```

**Output:** Interactive HTML file saved to `outputs/hdr-insights-{order_number}-{timestamp}.html`

## What It Shows

### Order Summary Dashboard
- Order ID and number (with shortened display)
- Status, channel, dining option
- **O2E Time**: Actual order-to-eat duration
- **SLA Difference**: Negative = early, positive = late
- **Expo Wait Time**: How long order sat at expo
- **Placement Time**: When order was created (ET)

### Order Items Table
Complete list of menu items with:
- Item name
- Category (entree, side, dessert, etc.)
- Quantity

### Timeline Scrubber (Core Feature)

Navigate through every sequencing run:
- **Controls**: Previous/Next buttons to move between runs
- **Run Counter**: "Run X of Y" display
- **Timestamp**: When each sequencing run completed
- **Interactive Chart**: Click chart points to jump to specific runs
- **Line Charts**:
  - Avg Expo Score trend over time
  - Avg Customer Promise Score trend over time
  - Current run highlighted in orange

### Per-Run Details

For each sequencing run, view:

#### 🎯 Target Order Items
Each item shows:
- **Menu item name** with colored score badges
- **Expo Sit Time Score**: Absolute value of expo wait time
  - **CRITICAL**: Sign is meaningless - both +5 and -5 = 5 minutes of wait
  - Color-coded: Green (<3), Yellow (3-7), Red (>7)
  - Always displayed as |score| throughout the tool
- **Customer Promise Score**: Minutes early (+) or late (-) vs promise time
  - Color thresholds:
    - **Red**: >8 mins early OR >10 mins late
    - **Yellow**: 0-8 mins early
    - **Green**: 0-10 mins late (acceptable window)
- **Holdback Strategy**: Which strategy was applied (e.g., "BUFFER", "DELAY_START")

#### 🏢 Sequencing Run Context (Collapsible)
Shows **item-level data** (not order-level aggregation) for all items in the sequencing run:
- **Run Statistics**: Avg expo score, avg CP score across all items
- **Target Order Rank**: Percentile showing how this order performed vs others (e.g., "GOOD (72.5%)")
- **Interactive Sortable Table**: All items with expo, CP, and holdback columns
  - **Sort Options**: "Expo Score (worst first)" or "Customer Promise Score (worst first)"
  - **Multi-level Sorting**: Primary → Secondary → Tertiary (e.g., expo → cp → holdback)
  - **Target Highlighting**: Target order items highlighted in blue for easy identification

#### 🏭 Kitchen State - Pods (Collapsible)
Real-time kitchen state organized by pod with **collapsible sections**:

**Pod Header Features:**
- **Collapsible**: Click to expand/collapse individual pods
- **Status Icons**: 🔥 (has cooking items) or ⏳ (only queued items)
- **Target Indicator**: 🎯 shown if pod contains target order items
- **Filtering**: Expo pods (Expo_Pod_X) are automatically hidden

**For Each Pod:**
- **🔥 Cooking Section**: Items currently being prepared
  - **Grouped by batch_id** with orange borders
  - Menu item name with state badge (COOKING)
  - Order number (target order items highlighted in blue)
  - **Resource type**: e.g., "FRYER", "WATER_BATH", "PRESS" (not appliance codes)
  - **All workflow steps**: Multiple steps for same item shown together indented
  - Batch ID header for each batch group

- **⏳ Queued Section**: Items waiting to cook
  - **Grouped by batch groups** from BigQuery with purple borders
  - Groups sorted by priority (execution order)
  - Menu item name with state badge (QUEUED)
  - Order number (target order items highlighted in blue)
  - Resource type assignment
  - Group ID and Priority shown in header

**Human-Readable Codes**: Pod names extracted from kitchen context (e.g., "Cold_Pod_1A", "Hot_Pod_2B") instead of showing UUIDs.

## Technical Implementation

### Data Sources

**Primary Tables:**
```
wonder-dw-prod-brd.orders.hdr_orders                                    # Order metrics
wonder-dw-prod-brd.orders.order_items                                   # Item details
wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing_optimizer        # Sequencing scores
wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing_optimizer_batch  # Batch groups
wonder-raw-prod.mongo_batch_cooking_optimization.sequencing_contexts    # Kitchen state JSON
```

### Critical Implementation Details

#### 1. Kitchen Context Lookup

**CRITICAL**: Use `context_id` (not `_id`) to fetch kitchen context:

```python
# CORRECT - Use context_id from optimizer table
context_id = run['items'][0].get('context_id')
kitchen_context_raw = all_kitchen_contexts.get(context_id)
```

**Why**: The optimizer table has two fields:
- `_id`: Sequencing run identifier
- `context_id`: Links to sequencing_contexts table `_id`

#### 2. Kitchen Context JSON Structure

**CRITICAL**: The `kitchen_context` field is a **list** containing workflow items (NOT direct menu item assignments).

**Actual Structure:**
```json
[
  {
    "super_pod": {
      "id": "uuid",
      "code": "Super_Pod_A",
      "pods": [
        {
          "id": "uuid",
          "code": "Cold_Pod_1A",
          "pod_type": "COLD",
          "appliances": [
            {
              "id": "uuid",
              "code": "Press_A",
              "type": "PRESS"
            }
          ]
        }
      ]
    },
    "items": [
      {
        "id": "item_workflow_uuid",
        "order_id": "uuid",
        "pod_id": "uuid",
        "steps": [
          {
            "status": "IN_PROGRESS",
            "resource_type": "FRYER",
            "step_order": 1,
            "batch_id": "uuid",
            "timer_remaining_secs": 180
          },
          {
            "status": "INCOMPLETE",
            "resource_type": "WATER_BATH",
            "step_order": 2,
            "batch_id": "uuid"
          }
        ]
      }
    ]
  }
]
```

**Key Differences from Original Documentation:**
- Items do NOT contain `menu_item_name` or `order_number` directly
- Items do NOT have a simple `state` field - instead they have `steps` array
- Each step has `status` ("IN_PROGRESS" = cooking, "INCOMPLETE" = queued)
- Items reference `order_id` (not order_number)

**Extraction Pattern:**
1. Parse `super_pod` for pod/appliance code mappings: `super_pod['pods'][i]['code']`
2. Parse `items` list for kitchen state by pod
3. **JOIN with optimizer data** to get menu_item_name and order_number by item_id
4. Process workflow `steps` to determine cooking/queued state
5. Map UUIDs to human-readable codes using extracted mappings

**Joining Kitchen Context with Menu Details:**
```python
def parse_kitchen_context(kitchen_context, item_mapping):
    """
    item_mapping: dict of {item_id: {'menu_item_name': str, 'order_number': str}}
    Built from optimizer table: SELECT item_id, menu_item_name, order_number FROM optimizer WHERE _id = run_id
    """
    for context_item in kitchen_context:
        for item in context_item.get('items', []):
            item_id = item.get('id')
            # Lookup menu details
            menu_details = item_mapping.get(item_id, {})
            menu_item_name = menu_details.get('menu_item_name', f'Item {item_id[:8]}...')
            order_number = menu_details.get('order_number', 'Unknown')

            # Process workflow steps
            for step in item.get('steps', []):
                step_status = step.get('status')  # IN_PROGRESS or INCOMPLETE
                resource_type = step.get('resource_type')  # FRYER, WATER_BATH, etc.
```

#### 3. CSV Field Size Limits

Kitchen context JSON can exceed 130KB. Increase CSV parser limits:

```python
import csv
csv.field_size_limit(10000000)  # 10MB limit
```

#### 4. Batch Query Optimization

Fetch data in batches (20 run_ids at a time) instead of sequentially:

```python
# Fetch ALL context/batch data for multiple runs at once
run_ids = [run['run_id'] for run in runs_data]
all_context_data = get_all_context_data(run_ids)  # Batch of 20
all_batch_data = get_all_batch_data(run_ids)      # Batch of 20
all_kitchen_contexts = get_all_kitchen_contexts(context_ids)  # Batch of 20
```

**Performance**: Reduces 100+ sequential queries to ~6 batch queries for 50 runs.

#### 5. Data Availability

- **Batch Data**: Started populating mid-December 2025. Earlier orders won't have batch group data.
- **Kitchen Context**: Available for recent orders (Dec 20+). Older orders may have `null`.
- **Fallback**: Tool gracefully handles missing data with empty sections.

### Key Join Patterns

**Merge optimizer and batch tables:**
```sql
SELECT batch.*, i_s.*
FROM hdr_kitchen_order_sequencing_optimizer_batch batch
LEFT JOIN hdr_kitchen_order_sequencing_optimizer i_s
  ON batch._id = i_s._id AND batch.item_id = i_s.item_id
WHERE i_s.order_id = '<target_order_id>'
```

**Fetch kitchen context:**
```sql
SELECT _id as context_id, kitchen_context
FROM sequencing_contexts
WHERE _id IN ('<context_id_1>', '<context_id_2>', ...)
```

**Critical**: Join on BOTH `_id` AND `item_id` when merging batch/optimizer tables.

## HTML Features

### Interactive Elements
- **Collapsible Sections**: Click headers to expand/collapse (Kitchen Context, Batch Groups, Pods)
- **Timeline Navigation**: Previous/Next buttons with keyboard shortcuts potential
- **Chart Interaction**: Click chart points to jump to specific runs
- **Color Coding**:
  - **Expo scores**: Always use absolute value |score|
    - Green: <3 mins, Yellow: 3-7 mins, Red: >7 mins
  - **CP scores**: Sign matters (+ = early, - = late)
    - Red: >8 mins early OR >10 mins late
    - Yellow: 0-8 mins early
    - Green: 0-10 mins late
  - **State badges**: Orange (cooking), Gray (queued), Green (complete)

### Responsive Design
- Grid layouts adapt to screen size
- Tables scroll horizontally if needed
- Charts resize with window

### Dependencies
- **Chart.js 4.4.0**: Loaded from CDN for timeline charts
- **No other external dependencies**: Pure HTML/CSS/JavaScript

## Dependencies

- Python 3.x (standard library only)
- `bq` CLI tool (Google Cloud BigQuery)
- Access to `wonder-dw-prod-brd` and `wonder-raw-prod` BigQuery projects

**No external Python packages required.**

## Example Workflow

```bash
# Generate report for order 6187677
python3 hdr_insights.py 6187677

# Output:
✓ Generated: outputs/hdr-insights-6187677-2025-12-23-1410.html

# Open in browser to explore:
# - Timeline: 48 sequencing runs
# - Click through runs to see how predictions changed
# - View kitchen state at each optimization cycle
# - See batch group assignments with human-readable pod codes
# - Compare target order performance vs other orders in same run
```

## Console Output

The tool prints minimal output:
```
✓ Generated: /path/to/outputs/hdr-insights-6187677-2025-12-23-1410.html
```

**No verbose console logging** - all analysis is in the HTML report.

## File Output

**Naming Pattern**: `hdr-insights-{order_number}-{YYYY-MM-DD-HHMM}.html`

**File Size**: Typically 2-3 MB for orders with 40-50 sequencing runs and full kitchen context.

**Location**: `outputs/` directory (gitignored)

## Common Use Cases

### 1. "Why did this order perform poorly?"
- Open HTML report
- Check O2E time and expo wait in summary
- Look at expo sit time scores (high = problem)
- Check customer promise scores (negative = late)
- View percentile ranking vs other orders
- Examine kitchen state at time of sequencing

### 2. "How did sequencing predictions change?"
- Use timeline scrubber to navigate between runs
- Watch expo scores trend over time in chart
- Compare early runs vs final runs
- Identify when predictions stabilized

### 3. "What was the kitchen doing when this order was sequenced?"
- Navigate to specific sequencing run
- Expand "Kitchen State - Pods" section
- See what items were cooking, queued, with timers
- Understand kitchen load and constraints

### 4. "Which pod was this item assigned to?"
- Expand "Kitchen State - Pods" section
- Look for pods with 🎯 icon (contains target order items)
- Check queued section for batch group assignments
- See human-readable pod code (e.g., "Hot_Pod_1A") and batch priority

## Future Enhancements

Planned additions:
- **Export to PDF**: Generate printable reports
- **Compare Multiple Orders**: Side-by-side comparison
- **HDR Benchmarking**: Compare order vs HDR averages
- **Alert Highlighting**: Auto-flag anomalies (high expo, late CP)
- **Filter Controls**: Show/hide specific sections
- **Search**: Find specific items or orders in context

## Troubleshooting

### "No sequencing data found"
- Order may be too old (pre-sequencing deployment)
- Check order_number is correct
- Verify order has `order_id` in sequencing tables

### "Kitchen state is null"
- Kitchen context started populating Dec 20, 2025
- Older orders won't have pod state details
- Batch groups and scores will still work

### "Batch data not available"
- Batch table started populating mid-December 2025
- Earlier orders only have optimizer table data
- Tool gracefully shows "No batch groups" message

### Large File Size
- Kitchen context JSON can be several MB
- 40-50 sequencing runs with full context = ~2-3 MB HTML
- This is normal and loads quickly in modern browsers
