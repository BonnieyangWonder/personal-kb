#!/usr/bin/env python3
"""
HDR-Insights (Raw): Generate interactive HTML report for order sequencing analysis
using RAW mongo tables instead of BRD tables.

Use this for HDRs that don't have data in the BRD optimizer table.
"""

import subprocess
import sys
import csv
import json
from io import StringIO
from datetime import datetime, timedelta

def run_bq_query(query, debug=False):
    """Run BigQuery query and return results as list of dicts"""
    cmd = ['bq', 'query', '--use_legacy_sql=false', '--format=csv', '--max_rows=100000', query]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if debug:
            print(f"  Return code: {result.returncode}")
            print(f"  Query stdout length: {len(result.stdout)}")
            print(f"  Query stdout preview: {result.stdout[:300]}")
            if result.stderr:
                print(f"  Query stderr: {result.stderr[:500]}")
        # Check for query errors in stdout (bq sometimes puts errors there)
        if result.stdout.startswith('Error in query') or 'Error processing job' in result.stdout:
            print(f"Query error in stdout: {result.stdout[:500]}")
            return None
        # Return code 1 might be OK if we got output (bq sometimes reports warnings as rc=1)
        if result.returncode != 0 and not result.stdout.strip():
            print(f"Query error: {result.stderr}")
            return None
        csv.field_size_limit(10000000)
        reader = csv.DictReader(StringIO(result.stdout))
        rows = list(reader)
        if debug:
            print(f"  Parsed {len(rows)} rows")
        return rows
    except Exception as e:
        print(f"Exception: {e}")
        return None

def safe_float(val, default=0.0):
    """Safely convert value to float"""
    try:
        return float(val) if val and val != '' else default
    except (ValueError, TypeError):
        return default

def get_order_details(order_identifier):
    """Fetch order details"""
    query = f"""
    SELECT
      o.order_id,
      o.order_number,
      o.hdr_id,
      o.order_status,
      o.order_channel,
      o.dining_option,
      o.item_count,
      DATETIME(o.order_placed_date_utc, 'America/New_York') as order_placed_et,
      DATETIME(o.actual_delivery_time_utc, 'America/New_York') as actual_delivery_et,
      o.actual_o2e_mins,
      o.delivery_sla_difference,
      o.order_level_expo_wait_time_mins,
      o.order_placed_date_utc
    FROM `wonder-dw-prod-brd.orders.hdr_orders` o
    WHERE o.order_number = '{order_identifier}' OR o.order_id = '{order_identifier}'
    LIMIT 1
    """
    return run_bq_query(query)

def get_order_items(order_id):
    """Fetch items for the order"""
    query = f"""
    SELECT
      oi.order_item_id,
      oi.menu_item_name,
      oi.menu_item_category_name,
      oi.order_quantity
    FROM `wonder-dw-prod-brd.orders.order_items` oi
    WHERE oi.order_id = '{order_id}'
    """
    return run_bq_query(query)

def get_hdr_name(hdr_id):
    """Get HDR name from command_center.nodes"""
    query = f"""
    SELECT facility_name
    FROM `wonder-dw-prod-brd.command_center.nodes`
    WHERE facility_id = '{hdr_id}'
    LIMIT 1
    """
    result = run_bq_query(query)
    return result[0]['facility_name'] if result else 'Unknown HDR'

def get_sequencing_data_from_raw(order_id, hdr_id, order_placed_utc):
    """
    Fetch sequencing data from raw mongo tables.

    This joins:
    - sequencing_contexts (has item_id -> order_id mapping in kitchen_context JSON)
    - optimized_sequences (has item scores in item_scores JSON)
    """
    # Parse order placed time and create a search window (order placed to +3 hours)
    # Format: 2026-01-09 22:40:28
    order_time = order_placed_utc.strip().replace(' ', 'T')
    print(f"  Order time for query: {order_time}")

    query = f"""
    WITH order_item_mapping AS (
      -- Extract item_id -> order_id mapping from kitchen_context
      SELECT DISTINCT
        ctx._id as context_id,
        JSON_EXTRACT_SCALAR(item, "$.id") as item_id,
        JSON_EXTRACT_SCALAR(item, "$.order_id") as order_id
      FROM `wonder-raw-prod.mongo_batch_cooking_optimization.sequencing_contexts` ctx,
      UNNEST(JSON_EXTRACT_ARRAY(kitchen_context)) as super_pod,
      UNNEST(JSON_EXTRACT_ARRAY(super_pod, "$.items")) as item
      WHERE ctx.hdr_id = '{hdr_id}'
        AND ctx.created_time >= DATETIME_SUB(DATETIME('{order_time}'), INTERVAL 5 MINUTE)
        AND ctx.created_time <= DATETIME_ADD(DATETIME('{order_time}'), INTERVAL 3 HOUR)
        AND JSON_EXTRACT_SCALAR(item, "$.order_id") = '{order_id}'
    ),
    item_scores AS (
      -- Extract scores from optimized_sequences
      SELECT
        opt._id,
        opt.context_id,
        opt.created_time,
        JSON_EXTRACT_SCALAR(score, "$.item_id") as item_id,
        CAST(JSON_EXTRACT_SCALAR(score, "$.expo_sit_time_score") AS FLOAT64) / 60.0 as expo_sit_time_score,
        CAST(JSON_EXTRACT_SCALAR(score, "$.customer_promise_score") AS FLOAT64) / 60.0 as customer_promise_score,
        CAST(JSON_EXTRACT_SCALAR(score, "$.estimated_hold_back_time") AS FLOAT64) / 60.0 as estimated_hold_back_time,
        JSON_EXTRACT_SCALAR(score, "$.t_s") as t_s,
        JSON_EXTRACT_SCALAR(score, "$.t_i") as t_i,
        JSON_EXTRACT_SCALAR(score, "$.t_o") as t_o,
        JSON_EXTRACT_SCALAR(score, "$.t_cp") as t_cp
      FROM `wonder-raw-prod.mongo_batch_cooking_optimization.optimized_sequences` opt,
      UNNEST(JSON_EXTRACT_ARRAY(item_scores)) as score
      WHERE opt.hdr_id = '{hdr_id}'
        AND opt.created_time >= DATETIME_SUB(DATETIME('{order_time}'), INTERVAL 5 MINUTE)
        AND opt.created_time <= DATETIME_ADD(DATETIME('{order_time}'), INTERVAL 3 HOUR)
    )
    SELECT
      s._id,
      s.context_id,
      DATETIME(TIMESTAMP(s.created_time), 'America/New_York') as created_time_et,
      s.created_time as created_time_ts,
      s.item_id,
      oi.order_id,
      s.expo_sit_time_score,
      s.customer_promise_score,
      s.estimated_hold_back_time,
      s.t_s,
      s.t_i,
      s.t_o,
      s.t_cp
    FROM item_scores s
    JOIN order_item_mapping oi ON s.context_id = oi.context_id AND s.item_id = oi.item_id
    ORDER BY s.created_time ASC, s.item_id
    """
    return run_bq_query(query, debug=True)

def get_menu_item_names(order_id):
    """Get menu item names for order items"""
    query = f"""
    SELECT
      oi.order_item_id,
      oi.menu_item_name
    FROM `wonder-dw-prod-brd.orders.order_items` oi
    WHERE oi.order_id = '{order_id}'
    """
    result = run_bq_query(query)
    # Create a mapping - we'll use item_id from sequencing, but we need to match somehow
    # For now, return the list of menu items
    return result

def organize_runs_data(all_seq_data, order_id, menu_items):
    """Organize sequencing data by run"""
    # Create a simple item index -> name mapping
    item_names = {item['order_item_id']: item['menu_item_name'] for item in menu_items} if menu_items else {}

    runs = {}
    for row in all_seq_data:
        run_id = row['_id']
        if run_id not in runs:
            runs[run_id] = {
                'timestamp': row['created_time_et'],
                'timestamp_ts': row['created_time_ts'],
                'items': []
            }

        # Add menu item name (use item_id suffix for now since we can't directly map)
        row['menu_item_name'] = f"Item {row['item_id'][:8]}..."
        row['order_number'] = 'Target Order'  # We know all items are from our target order
        runs[run_id]['items'].append(row)

    # Sort by timestamp and convert to list
    sorted_runs = sorted(runs.items(), key=lambda x: x[1]['timestamp'])

    runs_data = []
    for idx, (run_id, run_data) in enumerate(sorted_runs):
        items = run_data['items']

        if not items:
            continue

        expo_scores = [safe_float(item['expo_sit_time_score']) for item in items]
        cp_scores = [safe_float(item['customer_promise_score']) for item in items]

        runs_data.append({
            'index': idx,
            'run_id': run_id,
            'timestamp': run_data['timestamp'],
            'timestamp_ts': run_data['timestamp_ts'],
            'max_expo_score': max(expo_scores) if expo_scores else 0,
            'max_cp_score': max(cp_scores) if cp_scores else 0,
            'avg_expo_score': sum(expo_scores) / len(expo_scores) if expo_scores else 0,
            'avg_cp_score': sum(cp_scores) / len(cp_scores) if cp_scores else 0,
            'num_items': len(items),
            'items': items
        })

    return runs_data

def generate_html(order, items, runs_data, hdr_name):
    """Generate HTML report"""
    timestamp = datetime.now().strftime("%Y-%m-%d-%H%M")
    output_file = f"/Users/efox/Documents/GitHub/salmon-of-knowledge/outputs/hdr-insights-raw-{order['order_number']}-{timestamp}.html"

    o2e = safe_float(order.get('actual_o2e_mins'))
    sla_diff = safe_float(order.get('delivery_sla_difference'))
    expo_wait = safe_float(order.get('order_level_expo_wait_time_mins'))

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>HDR-Insights (Raw): Order {order['order_number']}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0"></script>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f5f5;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #333;
            border-bottom: 3px solid #FF9800;
            padding-bottom: 10px;
        }}
        .raw-badge {{
            background: #FF9800;
            color: white;
            padding: 4px 12px;
            border-radius: 4px;
            font-size: 14px;
            margin-left: 10px;
        }}
        h2 {{ color: #333; margin-top: 30px; }}
        .order-summary {{
            background: #fff3e0;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
        }}
        .metric {{
            padding: 10px;
            background: white;
            border-radius: 4px;
            border-left: 4px solid #FF9800;
        }}
        .metric-label {{
            font-size: 12px;
            color: #666;
            font-weight: 500;
        }}
        .metric-value {{
            font-size: 18px;
            font-weight: bold;
            color: #333;
            margin-top: 5px;
        }}
        .chart-container {{
            margin: 30px 0;
            padding: 20px;
            background: #fafafa;
            border-radius: 5px;
        }}
        .timeline-scrubber {{
            background: white;
            border: 2px solid #FF9800;
            border-radius: 8px;
            padding: 20px;
            margin: 20px 0;
        }}
        .scrubber-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }}
        .scrubber-title {{
            font-size: 18px;
            font-weight: bold;
            color: #333;
        }}
        .scrubber-controls {{
            display: flex;
            gap: 10px;
            align-items: center;
        }}
        .nav-button {{
            padding: 8px 16px;
            background: #FF9800;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-weight: 500;
        }}
        .nav-button:hover {{ background: #F57C00; }}
        .nav-button:disabled {{ background: #ccc; cursor: not-allowed; }}
        .run-indicator {{
            font-size: 16px;
            font-weight: bold;
            color: #333;
        }}
        .item-card {{
            background: #fff3e0;
            border: 2px solid #FF9800;
            border-radius: 8px;
            padding: 15px;
            margin: 15px 0;
        }}
        .item-header {{
            font-weight: bold;
            font-size: 16px;
            color: #E65100;
            margin-bottom: 10px;
        }}
        .score-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 10px;
            margin-top: 10px;
        }}
        .score-item {{
            background: white;
            padding: 8px;
            border-radius: 4px;
            font-size: 13px;
        }}
        .score-label {{
            font-size: 11px;
            color: #666;
            margin-bottom: 3px;
        }}
        .score-value {{
            font-weight: bold;
            font-size: 15px;
        }}
        .score-positive {{ color: #4CAF50; }}
        .score-negative {{ color: #f44336; }}
        .score-neutral {{ color: #666; }}
        .items-table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
        }}
        .items-table th {{
            background: #fff3e0;
            padding: 10px;
            text-align: left;
            font-size: 12px;
            color: #666;
            border-bottom: 2px solid #FF9800;
        }}
        .items-table td {{
            padding: 10px;
            border-bottom: 1px solid #eee;
            font-size: 13px;
        }}
        .note-box {{
            background: #e3f2fd;
            border: 1px solid #2196F3;
            border-radius: 4px;
            padding: 15px;
            margin: 20px 0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>HDR-Insights: Order {order['order_number']} <span class="raw-badge">RAW DATA</span></h1>

        <div class="note-box">
            <strong>Note:</strong> This report uses RAW mongo tables because <strong>{hdr_name}</strong> HDR
            does not have data in the BRD optimizer table. Some features (like menu item names, kitchen state visualization)
            may be limited.
        </div>

        <div class="order-summary">
            <div class="metric">
                <div class="metric-label">HDR</div>
                <div class="metric-value">{hdr_name}</div>
            </div>
            <div class="metric">
                <div class="metric-label">Order ID</div>
                <div class="metric-value">{order['order_id'][:8]}...</div>
            </div>
            <div class="metric">
                <div class="metric-label">Status</div>
                <div class="metric-value">{order.get('order_status', 'N/A')}</div>
            </div>
            <div class="metric">
                <div class="metric-label">Channel</div>
                <div class="metric-value">{order.get('order_channel', 'N/A')}</div>
            </div>
            <div class="metric">
                <div class="metric-label">O2E Time</div>
                <div class="metric-value">{o2e:.1f} min</div>
            </div>
            <div class="metric">
                <div class="metric-label">SLA Difference</div>
                <div class="metric-value">{sla_diff:+.1f} min</div>
            </div>
            <div class="metric">
                <div class="metric-label">Expo Wait</div>
                <div class="metric-value">{expo_wait:.1f} min</div>
            </div>
            <div class="metric">
                <div class="metric-label">Placed At (ET)</div>
                <div class="metric-value">{order.get('order_placed_et', 'N/A')[:16]}</div>
            </div>
        </div>

        <h2>Order Items ({len(items)})</h2>
        <table class="items-table">
            <thead>
                <tr>
                    <th>Item Name</th>
                    <th>Category</th>
                    <th>Quantity</th>
                </tr>
            </thead>
            <tbody>
"""

    for item in items:
        html += f"""                <tr>
                    <td>{item['menu_item_name']}</td>
                    <td>{item.get('menu_item_category_name', 'N/A')}</td>
                    <td>{item['order_quantity']}</td>
                </tr>
"""

    html += f"""            </tbody>
        </table>

        <h2>Sequencing Timeline ({len(runs_data)} runs)</h2>
        <div class="timeline-scrubber">
            <div class="scrubber-header">
                <div class="scrubber-title">Run <span id="currentRunIndex">1</span> of {len(runs_data)}</div>
                <div class="scrubber-controls">
                    <button class="nav-button" onclick="changeRun(-1)" id="prevBtn">Prev</button>
                    <span class="run-indicator" id="runTimestamp"></span>
                    <button class="nav-button" onclick="changeRun(1)" id="nextBtn">Next</button>
                </div>
            </div>

            <div class="chart-container">
                <canvas id="timelineChart" height="80"></canvas>
            </div>

            <div id="runDetails"></div>
        </div>

    </div>

    <script>
        const runsData = {json.dumps(runs_data, indent=2)};
        let currentRunIndex = 0;

        function updateRun(index) {{
            currentRunIndex = index;
            const run = runsData[index];

            document.getElementById('currentRunIndex').textContent = index + 1;
            document.getElementById('runTimestamp').textContent = run.timestamp.substring(0, 19);

            document.getElementById('prevBtn').disabled = (index === 0);
            document.getElementById('nextBtn').disabled = (index === runsData.length - 1);

            let html = '<div style="margin-top: 20px;">';
            html += '<h3>Items in this Run (' + run.items.length + ')</h3>';

            run.items.forEach((item, idx) => {{
                const expoScore = Math.abs(parseFloat(item.expo_sit_time_score) || 0);
                const cpScore = parseFloat(item.customer_promise_score) || 0;
                const holdback = parseFloat(item.estimated_hold_back_time) || 0;

                const expoClass = expoScore > 7 ? 'score-negative' : expoScore > 3 ? 'score-neutral' : 'score-positive';
                const cpClass = (cpScore > 8 || cpScore < -10) ? 'score-negative' :
                               (cpScore > 0 && cpScore <= 8) ? 'score-neutral' : 'score-positive';

                html += `
                <div class="item-card">
                    <div class="item-header">Item ${{idx + 1}}: ${{item.item_id.substring(0, 8)}}...</div>
                    <div class="score-grid">
                        <div class="score-item">
                            <div class="score-label">Expo Sit Time (abs)</div>
                            <div class="score-value ${{expoClass}}">${{expoScore.toFixed(1)}} min</div>
                        </div>
                        <div class="score-item">
                            <div class="score-label">Customer Promise</div>
                            <div class="score-value ${{cpClass}}">${{cpScore > 0 ? '+' : ''}}${{cpScore.toFixed(1)}} min</div>
                        </div>
                        <div class="score-item">
                            <div class="score-label">Holdback Time</div>
                            <div class="score-value">${{holdback.toFixed(1)}} min</div>
                        </div>
                        <div class="score-item">
                            <div class="score-label">Start Time (t_s)</div>
                            <div class="score-value" style="font-size: 12px;">${{item.t_s ? item.t_s.substring(11, 19) : 'N/A'}}</div>
                        </div>
                    </div>
                </div>`;
            }});

            html += '</div>';

            // Summary stats
            html += `
            <div style="margin-top: 20px; padding: 15px; background: #f5f5f5; border-radius: 8px;">
                <strong>Run Summary:</strong>
                Avg Expo: ${{Math.abs(run.avg_expo_score).toFixed(2)}} min |
                Avg CP: ${{run.avg_cp_score.toFixed(2)}} min |
                Max Expo: ${{Math.abs(run.max_expo_score).toFixed(2)}} min
            </div>`;

            document.getElementById('runDetails').innerHTML = html;
        }}

        function changeRun(delta) {{
            const newIndex = currentRunIndex + delta;
            if (newIndex >= 0 && newIndex < runsData.length) {{
                updateRun(newIndex);
                updateChart();
            }}
        }}

        // Initialize chart
        const ctx = document.getElementById('timelineChart').getContext('2d');
        const timelineChart = new Chart(ctx, {{
            type: 'line',
            data: {{
                labels: runsData.map((r, i) => `Run ${{i + 1}}`),
                datasets: [
                    {{
                        label: 'Avg Expo Score (absolute, min)',
                        data: runsData.map(r => Math.abs(r.avg_expo_score)),
                        borderColor: '#2196F3',
                        backgroundColor: 'rgba(33, 150, 243, 0.1)',
                        tension: 0.4,
                        pointRadius: 4,
                        pointBackgroundColor: function(context) {{
                            return context.dataIndex === currentRunIndex ? '#FF5722' : '#2196F3';
                        }}
                    }},
                    {{
                        label: 'Avg Customer Promise (min)',
                        data: runsData.map(r => r.avg_cp_score),
                        borderColor: '#4CAF50',
                        backgroundColor: 'rgba(76, 175, 80, 0.1)',
                        tension: 0.4,
                        pointRadius: 4,
                        pointBackgroundColor: function(context) {{
                            return context.dataIndex === currentRunIndex ? '#FF5722' : '#4CAF50';
                        }}
                    }}
                ]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: true,
                plugins: {{
                    legend: {{ display: true, position: 'top' }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: false,
                        title: {{ display: true, text: 'Score (minutes)' }}
                    }}
                }},
                onClick: (event, elements) => {{
                    if (elements.length > 0) {{
                        updateRun(elements[0].index);
                        updateChart();
                    }}
                }}
            }}
        }});

        function updateChart() {{
            timelineChart.update();
        }}

        // Initialize first run
        updateRun(0);
    </script>
</body>
</html>"""

    with open(output_file, 'w') as f:
        f.write(html)

    return output_file

def analyze_order(order_identifier):
    """Main analysis function"""
    print(f"Fetching order {order_identifier}...")

    # Fetch order
    order_list = get_order_details(order_identifier)
    if not order_list or len(order_list) == 0:
        print(f"ERROR: Order not found: {order_identifier}")
        return None
    order = order_list[0]

    print(f"  Order ID: {order['order_id']}")
    print(f"  HDR ID: {order['hdr_id']}")

    # Get HDR name
    hdr_name = get_hdr_name(order['hdr_id'])
    print(f"  HDR: {hdr_name}")

    # Fetch items
    items = get_order_items(order['order_id'])
    if not items:
        print(f"ERROR: No items found for order {order_identifier}")
        return None
    print(f"  Items: {len(items)}")

    # Fetch sequencing data from RAW tables
    print(f"Querying raw sequencing data...")
    raw_seq_data = get_sequencing_data_from_raw(
        order['order_id'],
        order['hdr_id'],
        order['order_placed_date_utc']
    )

    if not raw_seq_data:
        print(f"ERROR: No sequencing data found in raw tables for order {order_identifier}")
        return None

    print(f"  Found {len(raw_seq_data)} sequencing records")

    # Get menu items for name mapping
    menu_items = get_menu_item_names(order['order_id'])

    # Organize runs
    runs_data = organize_runs_data(raw_seq_data, order['order_id'], menu_items)

    if not runs_data:
        print(f"ERROR: Could not organize sequencing runs for order {order_identifier}")
        return None

    print(f"  Organized into {len(runs_data)} sequencing runs")

    # Generate HTML
    output_file = generate_html(order, items, runs_data, hdr_name)

    print(f"Generated: {output_file}")
    return output_file

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 hdr_insights_raw.py <order_number_or_id>")
        print("Example: python3 hdr_insights_raw.py 6475434")
        print("")
        print("Use this for HDRs that don't have data in the BRD optimizer table.")
        sys.exit(1)

    order_identifier = sys.argv[1]
    analyze_order(order_identifier)
