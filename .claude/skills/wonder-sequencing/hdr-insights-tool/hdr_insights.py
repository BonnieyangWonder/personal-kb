#!/usr/bin/env python3
"""
HDR-Insights: Generate interactive HTML report for order sequencing analysis
"""

import subprocess
import sys
import csv
import json
from io import StringIO
from datetime import datetime

def run_bq_query(query):
    """Run BigQuery query and return results as list of dicts"""
    cmd = ['bq', 'query', '--use_legacy_sql=false', '--format=csv', '--max_rows=100000', query]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        # Increase field size limit for large JSON fields (like kitchen_context)
        csv.field_size_limit(10000000)  # 10MB limit
        reader = csv.DictReader(StringIO(result.stdout))
        return list(reader)
    except subprocess.CalledProcessError as e:
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
      o.order_level_expo_wait_time_mins
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

def get_all_sequencing_runs(order_id):
    """Fetch ALL sequencing runs for the order (for timeline scrubbing)"""
    query = f"""
    SELECT
      _id,
      context_id,
      item_id,
      order_id,
      order_number,
      menu_item_name,
      expo_sit_time_score,
      customer_promise_score,
      estimated_item_expo_wait_time_mins,
      estimated_order_level_expo_time_mins,
      hold_back_strategy_v2,
      estimated_hold_back_time,
      DATETIME(TIMESTAMP(created_time), 'America/New_York') as created_time_et,
      TIMESTAMP(created_time) as created_time_ts,
      DATETIME(t_s, 'America/New_York') as t_s_et,
      DATETIME(t_i, 'America/New_York') as t_i_et,
      DATETIME(t_o, 'America/New_York') as t_o_et,
      DATETIME(t_cp, 'America/New_York') as t_cp_et
    FROM `wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing_optimizer`
    WHERE order_id = '{order_id}'
    ORDER BY created_time ASC
    """
    return run_bq_query(query)

def get_context_ids_from_runs(runs_data):
    """Extract unique context_ids from runs data"""
    context_ids = set()
    for run in runs_data:
        for item in run.get('items', []):
            ctx_id = item.get('context_id')
            if ctx_id:
                context_ids.add(ctx_id)
    return list(context_ids)

def get_sequencing_context(run_id):
    """Fetch all orders/items in the same sequencing run"""
    query = f"""
    SELECT
      i_s._id as run_id,
      i_s.order_id,
      i_s.order_number,
      i_s.item_id,
      i_s.menu_item_name,
      i_s.expo_sit_time_score,
      i_s.customer_promise_score,
      i_s.estimated_item_expo_wait_time_mins,
      i_s.hold_back_strategy_v2
    FROM `wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing_optimizer` i_s
    WHERE i_s._id = '{run_id}'
    ORDER BY i_s.expo_sit_time_score DESC
    LIMIT 500
    """
    return run_bq_query(query)

def get_batch_groups(run_id):
    """Fetch batch group data for a run"""
    query = f"""
    SELECT
      batch.group_id,
      batch.pod_id,
      batch.group_priority as priority,
      i_s.item_id,
      i_s.order_id,
      i_s.order_number,
      i_s.menu_item_name,
      i_s.expo_sit_time_score,
      i_s.customer_promise_score,
      i_s.estimated_hold_back_time
    FROM `wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing_optimizer_batch` batch
    LEFT JOIN `wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing_optimizer` i_s
      ON batch._id = i_s._id AND batch.item_id = i_s.item_id
    WHERE batch._id = '{run_id}'
    ORDER BY batch.group_priority, i_s.order_number
    LIMIT 1000
    """
    return run_bq_query(query)

def organize_runs_data(all_seq_data, target_order_number):
    """Organize sequencing data by run"""
    runs = {}
    for row in all_seq_data:
        run_id = row['_id']
        if run_id not in runs:
            runs[run_id] = {
                'timestamp': row['created_time_et'],
                'timestamp_ts': row['created_time_ts'],
                'items': []
            }
        runs[run_id]['items'].append(row)

    # Sort by timestamp and convert to list
    sorted_runs = sorted(runs.items(), key=lambda x: x[1]['timestamp'])

    # Build runsData structure
    runs_data = []
    for idx, (run_id, run_data) in enumerate(sorted_runs):
        target_items = [item for item in run_data['items'] if item['order_number'] == target_order_number]

        if not target_items:
            continue

        expo_scores = [safe_float(item['expo_sit_time_score']) for item in target_items if item.get('expo_sit_time_score')]
        cp_scores = [safe_float(item['customer_promise_score']) for item in target_items if item.get('customer_promise_score')]

        runs_data.append({
            'index': idx,
            'run_id': run_id,
            'timestamp': run_data['timestamp'],
            'timestamp_ts': run_data['timestamp_ts'],
            'max_expo_score': max(expo_scores) if expo_scores else 0,
            'max_cp_score': max(cp_scores) if cp_scores else 0,
            'avg_expo_score': sum(expo_scores) / len(expo_scores) if expo_scores else 0,
            'avg_cp_score': sum(cp_scores) / len(cp_scores) if cp_scores else 0,
            'num_items': len(target_items),
            'items': target_items
        })

    return runs_data

def get_all_context_data(run_ids):
    """Fetch context data for multiple runs at once"""
    if not run_ids or len(run_ids) == 0:
        return {}

    # Split into batches of 20 to avoid query size limits
    batch_size = 20
    all_context = {}

    for i in range(0, len(run_ids), batch_size):
        batch_ids = run_ids[i:i+batch_size]
        ids_str = "', '".join(batch_ids)

        query = f"""
        SELECT
          i_s._id as run_id,
          i_s.order_id,
          i_s.order_number,
          i_s.item_id,
          i_s.menu_item_name,
          i_s.expo_sit_time_score,
          i_s.customer_promise_score,
          i_s.estimated_item_expo_wait_time_mins,
          i_s.hold_back_strategy_v2
        FROM `wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing_optimizer` i_s
        WHERE i_s._id IN ('{ids_str}')
        ORDER BY i_s._id, i_s.expo_sit_time_score DESC
        """

        results = run_bq_query(query)
        if results:
            for row in results:
                rid = row['run_id']
                if rid not in all_context:
                    all_context[rid] = []
                all_context[rid].append(row)

    return all_context

def get_all_batch_data(run_ids):
    """Fetch batch data for multiple runs at once"""
    if not run_ids or len(run_ids) == 0:
        return {}

    # Split into batches of 20 to avoid query size limits
    batch_size = 20
    all_batches = {}

    for i in range(0, len(run_ids), batch_size):
        batch_ids = run_ids[i:i+batch_size]
        ids_str = "', '".join(batch_ids)

        query = f"""
        SELECT
          batch._id as run_id,
          batch.group_id,
          batch.pod_id,
          batch.group_priority as priority,
          i_s.item_id,
          i_s.order_id,
          i_s.order_number,
          i_s.menu_item_name,
          i_s.expo_sit_time_score,
          i_s.customer_promise_score,
          i_s.estimated_hold_back_time
        FROM `wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing_optimizer_batch` batch
        LEFT JOIN `wonder-dw-prod-brd.orders.hdr_kitchen_order_sequencing_optimizer` i_s
          ON batch._id = i_s._id AND batch.item_id = i_s.item_id
        WHERE batch._id IN ('{ids_str}')
        ORDER BY batch._id, batch.group_priority, i_s.order_number
        """

        results = run_bq_query(query)
        if results:
            for row in results:
                rid = row['run_id']
                if rid not in all_batches:
                    all_batches[rid] = []
                all_batches[rid].append(row)

    return all_batches

def get_all_kitchen_contexts(context_ids):
    """Fetch kitchen context (pod state) for multiple context_ids at once"""
    if not context_ids or len(context_ids) == 0:
        return {}

    # Split into batches of 20 to avoid query size limits
    batch_size = 20
    all_contexts = {}

    for i in range(0, len(context_ids), batch_size):
        batch_ids = context_ids[i:i+batch_size]
        ids_str = "', '".join(batch_ids)

        query = f"""
        SELECT
          _id as context_id,
          kitchen_context
        FROM `wonder-raw-prod.mongo_batch_cooking_optimization.sequencing_contexts`
        WHERE _id IN ('{ids_str}')
        """

        results = run_bq_query(query)
        if results:
            for row in results:
                ctx_id = row['context_id']
                try:
                    kitchen_context = json.loads(row['kitchen_context']) if row.get('kitchen_context') else None
                    if kitchen_context:
                        all_contexts[ctx_id] = kitchen_context
                except (json.JSONDecodeError, TypeError):
                    all_contexts[ctx_id] = None

    return all_contexts

def extract_code_mappings(kitchen_context):
    """Extract ID-to-code mappings from kitchen context"""
    mappings = {
        'pods': {},
        'super_pods': {},
        'appliances': {}
    }

    if not kitchen_context:
        return mappings

    # kitchen_context is a list where each element has a 'super_pod' key
    context_list = kitchen_context if isinstance(kitchen_context, list) else []

    for context_item in context_list:
        if not isinstance(context_item, dict):
            continue

        # Get the super_pod object from this context item
        super_pod = context_item.get('super_pod', {})
        if not isinstance(super_pod, dict):
            continue

        # Extract super pod mapping
        super_pod_id = super_pod.get('id')
        super_pod_code = super_pod.get('code')
        if super_pod_id and super_pod_code:
            mappings['super_pods'][super_pod_id] = super_pod_code

        # Extract pod codes
        pods = super_pod.get('pods', [])
        for pod in pods:
            if isinstance(pod, dict):
                pod_id = pod.get('id')
                code = pod.get('code')
                if pod_id and code:
                    mappings['pods'][pod_id] = code

                # Extract appliance codes from this pod
                appliances = pod.get('appliances', [])
                for appliance in appliances:
                    if isinstance(appliance, dict):
                        appliance_id = appliance.get('id')
                        appliance_code = appliance.get('code')
                        if appliance_id and appliance_code:
                            mappings['appliances'][appliance_id] = appliance_code

    return mappings

def parse_kitchen_context(kitchen_context, item_mapping):
    """Parse kitchen context and enrich with menu item details from optimizer data"""
    if not kitchen_context:
        return None

    pods_data = {}

    # kitchen_context is a list where each element has 'super_pod' and 'items'
    context_list = kitchen_context if isinstance(kitchen_context, list) else []

    for context_item in context_list:
        if not isinstance(context_item, dict):
            continue

        # Get super pod info
        super_pod = context_item.get('super_pod', {})
        super_pod_code = super_pod.get('code', 'Unknown Super Pod')

        # Get workflow items (these have steps, not direct pod assignments)
        workflow_items = context_item.get('items', [])

        # Parse workflow items and their steps
        for workflow_item in workflow_items:
            if not isinstance(workflow_item, dict):
                continue

            item_id = workflow_item.get('id')
            order_id = workflow_item.get('order_id')
            item_status = workflow_item.get('status')

            # Join with optimizer data to get menu details
            menu_details = item_mapping.get(item_id, {})
            menu_item_name = menu_details.get('menu_item_name', f'Item {item_id[:8] if item_id else "Unknown"}...')
            order_number = menu_details.get('order_number', 'Unknown')

            # Process steps - group by pod first, then collect all steps for this item per pod
            steps = workflow_item.get('steps', [])
            item_steps_by_pod = {}

            for step in steps:
                if not isinstance(step, dict):
                    continue

                step_status = step.get('status')
                # Only show IN_PROGRESS and INCOMPLETE steps (active work)
                if step_status in ['IN_PROGRESS', 'INCOMPLETE']:
                    pod_id = step.get('pod_id')

                    if pod_id not in item_steps_by_pod:
                        item_steps_by_pod[pod_id] = []

                    # Map step status to display state
                    display_state = 'COOKING' if step_status == 'IN_PROGRESS' else 'QUEUED'

                    item_steps_by_pod[pod_id].append({
                        'step_status': display_state,
                        'resource_type': step.get('resource_type', 'UNKNOWN'),
                        'step_order': step.get('step_order'),
                        'batch_id': step.get('batch_id'),
                        'started_time': step.get('started_time'),
                        'actionable_time': step.get('actionable_time')
                    })

            # Add grouped steps to pods_data
            for pod_id, pod_steps in item_steps_by_pod.items():
                if pod_id not in pods_data:
                    pods_data[pod_id] = {
                        'pod_id': pod_id,
                        'super_pod_code': super_pod_code,
                        'items': []
                    }

                # Determine overall state (cooking if any step is cooking, else queued)
                overall_state = 'COOKING' if any(s['step_status'] == 'COOKING' for s in pod_steps) else 'QUEUED'
                # Get batch_id from first step with one
                batch_id = next((s['batch_id'] for s in pod_steps if s.get('batch_id')), None)

                pods_data[pod_id]['items'].append({
                    'item_id': item_id,
                    'order_id': order_id,
                    'order_number': order_number,
                    'menu_item_name': menu_item_name,
                    'state': overall_state,
                    'batch_id': batch_id,
                    'steps': pod_steps  # Array of steps for this item in this pod
                })

    return pods_data if pods_data else None

def generate_html(order, items, runs_data, order_identifier):
    """Generate comprehensive HTML report"""

    # Fetch ALL context and batch data at once (much faster!)
    run_ids = [run['run_id'] for run in runs_data]
    all_context_data = get_all_context_data(run_ids)
    all_batch_data = get_all_batch_data(run_ids)

    # Extract context_ids from runs (needed for kitchen context lookup)
    context_ids = get_context_ids_from_runs(runs_data)
    all_kitchen_contexts = get_all_kitchen_contexts(context_ids)

    # Prepare context data for each run
    for run in runs_data:
        context_data = all_context_data.get(run['run_id'], [])

        if context_data:
            # Calculate run statistics
            all_expo = [safe_float(item['expo_sit_time_score']) for item in context_data if item.get('expo_sit_time_score')]
            all_cp = [safe_float(item['customer_promise_score']) for item in context_data if item.get('customer_promise_score')]

            unique_orders = list(set(item['order_number'] for item in context_data))

            # Calculate percentile for target order (expo is absolute value metric - lower is better)
            target_avg_expo = abs(run['avg_expo_score'])
            worse_count = sum(1 for score in all_expo if abs(score) > target_avg_expo)
            percentile = (worse_count / len(all_expo) * 100) if all_expo else 0

            run['context'] = {
                'total_orders': len(unique_orders),
                'run_avg_expo': sum(all_expo) / len(all_expo) if all_expo else 0,
                'run_avg_cp': sum(all_cp) / len(all_cp) if all_cp else 0,
                'run_min_expo': min(all_expo) if all_expo else 0,
                'run_max_expo': max(all_expo) if all_expo else 0,
                'run_min_cp': min(all_cp) if all_cp else 0,
                'run_max_cp': max(all_cp) if all_cp else 0,
                'expo_percentile': percentile
            }

            # Store all context items for sorting/display
            run['all_context_items'] = context_data
        else:
            run['context'] = None
            run['all_context_items'] = []

        # Get batch groups from pre-fetched data
        batch_data = all_batch_data.get(run['run_id'], [])
        if batch_data:
            batch_groups = {}
            for row in batch_data:
                gid = row['group_id']
                if gid not in batch_groups:
                    batch_groups[gid] = {
                        'group_id': gid,
                        'pod_id': row['pod_id'],
                        'priority': row['priority'],
                        'items': []
                    }
                batch_groups[gid]['items'].append(row)
            run['batch_groups'] = batch_groups
        else:
            run['batch_groups'] = {}

        # Parse kitchen context (pod state) with item mapping for joins
        # Get context_id from the first item in this run
        context_id = run['items'][0].get('context_id') if run['items'] else None
        kitchen_context_raw = all_kitchen_contexts.get(context_id) if context_id else None

        if kitchen_context_raw:
            # Create item_id to menu details mapping from context_data
            item_mapping = {}
            if context_data:
                for item in context_data:
                    item_id = item.get('item_id')
                    if item_id:
                        item_mapping[item_id] = {
                            'menu_item_name': item.get('menu_item_name'),
                            'order_number': item.get('order_number'),
                            'order_id': item.get('order_id')
                        }

            run['kitchen_state'] = parse_kitchen_context(kitchen_context_raw, item_mapping)
            # Extract code mappings for human-readable names (kitchen_context_raw can be list or dict)
            run['code_mappings'] = extract_code_mappings(kitchen_context_raw)
        else:
            run['kitchen_state'] = None
            run['code_mappings'] = {'pods': {}, 'super_pods': {}, 'appliances': {}}

    # Generate HTML
    timestamp = datetime.now().strftime("%Y-%m-%d-%H%M")
    output_file = f"/Users/efox/Documents/GitHub/salmon-of-knowledge/outputs/hdr-insights-{order['order_number']}-{timestamp}.html"

    o2e = safe_float(order.get('actual_o2e_mins'))
    sla_diff = safe_float(order.get('delivery_sla_difference'))
    expo_wait = safe_float(order.get('order_level_expo_wait_time_mins'))

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>HDR-Insights: Order {order['order_number']}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0"></script>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f5f5;
        }}
        .container {{
            max-width: 1600px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #333;
            border-bottom: 3px solid #4CAF50;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #333;
            margin-top: 30px;
        }}
        h3 {{
            color: #555;
            margin-top: 20px;
            margin-bottom: 10px;
        }}
        .order-summary {{
            background: #f9f9f9;
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
            border-left: 4px solid #4CAF50;
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
            border: 2px solid #4CAF50;
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
            background: #4CAF50;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-weight: 500;
        }}
        .nav-button:hover {{
            background: #45a049;
        }}
        .nav-button:disabled {{
            background: #ccc;
            cursor: not-allowed;
        }}
        .run-indicator {{
            font-size: 16px;
            font-weight: bold;
            color: #333;
        }}
        .items-section {{
            margin-top: 20px;
        }}
        .item-card {{
            background: #f0f8ff;
            border: 2px solid #2196F3;
            border-radius: 8px;
            padding: 15px;
            margin: 15px 0;
        }}
        .item-header {{
            font-weight: bold;
            font-size: 16px;
            color: #1976D2;
            margin-bottom: 10px;
        }}
        .score-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
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
        .rank-badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-weight: bold;
            font-size: 12px;
        }}
        .rank-good {{
            background: #4CAF50;
            color: white;
        }}
        .rank-medium {{
            background: #FF9800;
            color: white;
        }}
        .rank-poor {{
            background: #f44336;
            color: white;
        }}
        .kitchen-section {{
            background: #fff9f0;
            border: 2px solid #FF9800;
            border-radius: 8px;
            padding: 15px;
            margin: 15px 0;
        }}
        .kitchen-header {{
            font-weight: bold;
            font-size: 16px;
            color: #F57C00;
            margin-bottom: 10px;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .kitchen-header:hover {{
            color: #E65100;
        }}
        .expand-icon {{
            font-size: 20px;
            transition: transform 0.3s;
        }}
        .expand-icon.expanded {{
            transform: rotate(180deg);
        }}
        .collapsible-content {{
            max-height: 0;
            overflow: hidden;
            transition: max-height 0.3s ease-out;
        }}
        .collapsible-content.expanded {{
            max-height: none;
            overflow-y: auto;
            max-height: 80vh;
        }}
        .other-order {{
            background: white;
            padding: 10px;
            margin: 10px 0;
            border-radius: 4px;
            border-left: 3px solid #FF9800;
        }}
        .other-order-header {{
            font-weight: bold;
            color: #F57C00;
            margin-bottom: 5px;
        }}
        .batch-group {{
            background: white;
            padding: 10px;
            margin: 10px 0;
            border-radius: 4px;
            border-left: 3px solid #4CAF50;
        }}
        .batch-group-header {{
            font-weight: bold;
            color: #2E7D32;
            margin-bottom: 8px;
            font-size: 14px;
        }}
        .items-table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
        }}
        .items-table th {{
            background: #f5f5f5;
            padding: 10px;
            text-align: left;
            font-size: 12px;
            color: #666;
            border-bottom: 2px solid #ddd;
        }}
        .items-table td {{
            padding: 10px;
            border-bottom: 1px solid #eee;
            font-size: 13px;
        }}
        .score-positive {{
            color: #4CAF50;
            font-weight: bold;
        }}
        .score-negative {{
            color: #f44336;
            font-weight: bold;
        }}
        .score-neutral {{
            color: #666;
        }}
        .pod-section {{
            background: #f0f4ff;
            border: 2px solid #3F51B5;
            border-radius: 8px;
            padding: 15px;
            margin: 15px 0;
        }}
        .pod-header {{
            font-weight: bold;
            font-size: 16px;
            color: #1976D2;
            margin-bottom: 10px;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .pod-header:hover {{
            color: #0D47A1;
        }}
        .pod-item {{
            background: white;
            padding: 10px;
            margin: 8px 0;
            border-radius: 4px;
            border-left: 3px solid #3F51B5;
        }}
        .pod-item-header {{
            font-weight: bold;
            color: #1976D2;
            margin-bottom: 5px;
            font-size: 14px;
        }}
        .pod-item-detail {{
            font-size: 12px;
            color: #555;
            padding: 2px 0;
        }}
        .state-badge {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 10px;
            font-size: 11px;
            font-weight: bold;
            margin-left: 8px;
        }}
        .state-cooking {{
            background: #FF9800;
            color: white;
        }}
        .state-queued {{
            background: #9E9E9E;
            color: white;
        }}
        .state-complete {{
            background: #4CAF50;
            color: white;
        }}
        .timer-badge {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 10px;
            font-size: 11px;
            background: #FFC107;
            color: #333;
            font-weight: bold;
            margin-left: 8px;
        }}
        .target-order-row {{
            background-color: #e3f2fd !important;
            border-left: 4px solid #2196F3 !important;
            font-weight: 500;
        }}
        .target-order-row:hover {{
            background-color: #bbdefb !important;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🔍 HDR-Insights: Order {order['order_number']}</h1>

        <div class="order-summary">
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
                <div class="metric-label">Dining Option</div>
                <div class="metric-value">{order.get('dining_option', 'N/A')}</div>
            </div>
            <div class="metric">
                <div class="metric-label">O2E Time</div>
                <div class="metric-value">{o2e:.1f} min</div>
            </div>
            <div class="metric">
                <div class="metric-label">SLA Difference</div>
                <div class="metric-value">{sla_diff:.1f} min</div>
            </div>
            <div class="metric">
                <div class="metric-label">Expo Wait</div>
                <div class="metric-value">{expo_wait:.1f} min</div>
            </div>
            <div class="metric">
                <div class="metric-label">Placed At</div>
                <div class="metric-value">{order.get('order_placed_et', 'N/A')[:16]}</div>
            </div>
        </div>

        <h2>📦 Order Items ({len(items)})</h2>
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

        <h2>📊 Sequencing Timeline Scrubber</h2>
        <div class="timeline-scrubber">
            <div class="scrubber-header">
                <div class="scrubber-title">Run <span id="currentRunIndex">1</span> of {len(runs_data)}</div>
                <div class="scrubber-controls">
                    <button class="nav-button" onclick="changeRun(-1)" id="prevBtn">◀ Previous</button>
                    <span class="run-indicator" id="runTimestamp"></span>
                    <button class="nav-button" onclick="changeRun(1)" id="nextBtn">Next ▶</button>
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

        function getRankBadge(percentile) {{
            if (percentile >= 70) return '<span class="rank-badge rank-good">GOOD (' + percentile.toFixed(1) + '%)</span>';
            if (percentile >= 30) return '<span class="rank-badge rank-medium">MEDIUM (' + percentile.toFixed(1) + '%)</span>';
            return '<span class="rank-badge rank-poor">POOR (' + percentile.toFixed(1) + '%)</span>';
        }}

        function toggleCollapsible(id) {{
            const content = document.getElementById(id);
            const icon = document.getElementById(id + '-icon');
            content.classList.toggle('expanded');
            icon.classList.toggle('expanded');
        }}

        function updateRun(index) {{
            currentRunIndex = index;
            const run = runsData[index];

            document.getElementById('currentRunIndex').textContent = index + 1;
            document.getElementById('runTimestamp').textContent = run.timestamp.substring(0, 19);

            document.getElementById('prevBtn').disabled = (index === 0);
            document.getElementById('nextBtn').disabled = (index === runsData.length - 1);

            let html = '<div class="items-section">';

            // Target order items
            html += '<h3>🎯 Target Order Items</h3>';
            run.items.forEach((item, idx) => {{
                const expoScore = parseFloat(item.expo_sit_time_score) || 0;
                const cpScore = parseFloat(item.customer_promise_score) || 0;
                const absExpoScore = Math.abs(expoScore);
                const expoClass = absExpoScore > 7 ? 'score-negative' : absExpoScore > 3 ? 'score-neutral' : 'score-positive';
                // CP: Red if >8 early or >10 late, Yellow if 0-8 early, Green if 0-10 late
                const cpClass = (cpScore > 8 || cpScore < -10) ? 'score-negative' :
                               (cpScore > 0 && cpScore <= 8) ? 'score-neutral' :
                               'score-positive';

                html += `
                <div class="item-card">
                    <div class="item-header">${{item.menu_item_name}}</div>
                    <div class="score-grid">
                        <div class="score-item">
                            <div class="score-label">Expo Sit Time</div>
                            <div class="score-value ${{expoClass}}">${{absExpoScore.toFixed(2)}} min</div>
                        </div>
                        <div class="score-item">
                            <div class="score-label">Customer Promise</div>
                            <div class="score-value ${{cpClass}}">${{cpScore > 0 ? '+' : ''}}${{cpScore.toFixed(2)}} min</div>
                        </div>
                        <div class="score-item">
                            <div class="score-label">Holdback Strategy</div>
                            <div class="score-value">${{item.hold_back_strategy_v2 || 'None'}}</div>
                        </div>
                        <div class="score-item">
                            <div class="score-label">Holdback Time</div>
                            <div class="score-value">${{parseFloat(item.estimated_hold_back_time || 0).toFixed(1)}} min</div>
                        </div>
                    </div>
                </div>`;
            }});

            // Item Time Estimates Section
            html += `
            <div class="kitchen-section" style="background: #f0fff0; border-color: #2E7D32;">
                <div class="kitchen-header" onclick="toggleCollapsible('time-estimates-${{index}}')" style="color: #2E7D32;">
                    <span>⏱️ Item Time Estimates</span>
                    <span class="expand-icon" id="time-estimates-${{index}}-icon">▼</span>
                </div>
                <div class="collapsible-content" id="time-estimates-${{index}}">
                    <div style="font-size: 12px; color: #666; margin-bottom: 10px; padding: 8px; background: #e8f5e9; border-radius: 4px;">
                        <strong>Legend:</strong> t_s = Simulated Start | t_i = Item Done | t_o = Order Done | t_cp = Customer Promise<br/>
                        <strong>Derived:</strong> Queue Time = (t_s - run_time) - Holdback | Holdback = intentional delay | Cook Time = t_i - t_s
                    </div>
                    <table class="items-table">
                        <thead>
                            <tr>
                                <th>Item</th>
                                <th>t_s (Start)</th>
                                <th>t_i (Item Done)</th>
                                <th>t_o (Order Done)</th>
                                <th>t_cp (Promise)</th>
                                <th>Queue Time</th>
                                <th>Holdback</th>
                                <th>Cook Time</th>
                            </tr>
                        </thead>
                        <tbody>`;

            run.items.forEach(item => {{
                const formatTime = (t) => t ? t.substring(11, 19) : 'N/A';

                // Calculate derived times
                const runTimestamp = run.timestamp; // Format: "2025-01-29 18:05:23"
                const t_s = item.t_s_et;
                const t_i = item.t_i_et;
                const holdbackMins = Math.max(0, parseFloat(item.estimated_hold_back_time || 0));

                let queueTime = 'N/A';
                let cookTime = 'N/A';
                let holdbackDisplay = holdbackMins.toFixed(1) + ' min';

                // Parse timestamps and calculate differences
                if (t_s && runTimestamp) {{
                    try {{
                        const runDate = new Date(runTimestamp.replace(' ', 'T'));
                        const startDate = new Date(t_s.replace(' ', 'T'));
                        const totalWaitMins = (startDate - runDate) / 60000;
                        // Queue time = total wait minus intentional holdback (floor at 0)
                        const queueMins = Math.max(0, totalWaitMins - holdbackMins);
                        queueTime = queueMins.toFixed(1) + ' min';
                    }} catch (e) {{}}
                }}

                if (t_s && t_i) {{
                    try {{
                        const startDate = new Date(t_s.replace(' ', 'T'));
                        const doneDate = new Date(t_i.replace(' ', 'T'));
                        const cookMins = (doneDate - startDate) / 60000;
                        cookTime = cookMins.toFixed(1) + ' min';
                    }} catch (e) {{}}
                }}

                html += `
                            <tr>
                                <td>${{item.menu_item_name}}</td>
                                <td>${{formatTime(item.t_s_et)}}</td>
                                <td>${{formatTime(item.t_i_et)}}</td>
                                <td>${{formatTime(item.t_o_et)}}</td>
                                <td style="font-weight: bold; color: #1976D2;">${{formatTime(item.t_cp_et)}}</td>
                                <td style="color: #F57C00;">${{queueTime}}</td>
                                <td style="color: #4CAF50;">${{holdbackDisplay}}</td>
                                <td style="color: #9C27B0;">${{cookTime}}</td>
                            </tr>`;
            }});

            html += `
                        </tbody>
                    </table>
                </div>
            </div>`;

            // Context information
            if (run.context) {{
                const ctx = run.context;
                const allContextItems = run.all_context_items || [];

                html += `
                <div class="kitchen-section">
                    <div class="kitchen-header" onclick="toggleCollapsible('context-${{index}}')">
                        <span>🏢 Sequencing Run Context (${{allContextItems.length}} items from ${{ctx.total_orders}} orders)</span>
                        <span class="expand-icon" id="context-${{index}}-icon">▼</span>
                    </div>
                    <div class="collapsible-content" id="context-${{index}}">
                        <div class="score-grid">
                            <div class="score-item">
                                <div class="score-label">Run Avg Expo Score (absolute)</div>
                                <div class="score-value">${{Math.abs(ctx.run_avg_expo).toFixed(2)}}</div>
                            </div>
                            <div class="score-item">
                                <div class="score-label">Run Avg CP Score</div>
                                <div class="score-value">${{ctx.run_avg_cp.toFixed(2)}}</div>
                            </div>
                            <div class="score-item">
                                <div class="score-label">Target Order Rank</div>
                                <div class="score-value">${{getRankBadge(ctx.expo_percentile)}}</div>
                            </div>
                        </div>

                        <div style="margin: 15px 0; display: flex; align-items: center;">
                            <label for="context-sort-${{index}}" style="font-weight: bold; margin-right: 10px;">Sort by:</label>
                            <select id="context-sort-${{index}}" onchange="sortContextItems(${{index}})" style="padding: 5px 10px; border: 1px solid #ccc; border-radius: 4px; font-size: 14px;">
                                <option value="expo">Expo Score (worst first)</option>
                                <option value="cp">Customer Promise Score (worst first)</option>
                            </select>
                        </div>

                        <div id="context-items-${{index}}"></div>
                    </div>
                </div>`;
            }}

            // Kitchen State (Pod Details)
            if (run.kitchen_state && Object.keys(run.kitchen_state).length > 0) {{
                const codeMaps = run.code_mappings || {{pods: {{}}, super_pods: {{}}, appliances: {{}}}};

                html += `
                <div class="pod-section">
                    <div class="pod-header" onclick="toggleCollapsible('pods-${{index}}')">
                        <span>🏭 Kitchen State - Pods (${{Object.keys(run.kitchen_state).length}} pods)</span>
                        <span class="expand-icon" id="pods-${{index}}-icon">▼</span>
                    </div>
                    <div class="collapsible-content" id="pods-${{index}}">`;

                const targetOrderNumber = run.items[0].order_number;

                Object.values(run.kitchen_state).forEach((pod, podIdx) => {{
                    // Skip Expo pods
                    const podCode = codeMaps.pods[pod.pod_id] || pod.pod_id.substring(0, 8) + '...';
                    if (podCode.includes('Expo')) {{
                        return;  // Skip this pod
                    }}

                    const cookingItems = pod.items.filter(item => item.state && item.state.toLowerCase().includes('cook'));
                    const queuedItems = pod.items.filter(item => item.state && item.state.toLowerCase().includes('queue'));

                    const superPodCode = pod.super_pod_code || 'Unknown Super Pod';

                    // Determine pod status for icon
                    const statusIcon = cookingItems.length > 0 ? '🔥' : (queuedItems.length > 0 ? '⏳' : '');

                    // Check if pod has target order items
                    const hasTargetOrder = pod.items.some(item => item.order_number === targetOrderNumber);
                    const targetIcon = hasTargetOrder ? ' 🎯' : '';

                    const podSectionId = 'pod-' + index + '-' + podIdx;

                    html += `
                    <div style="background: white; padding: 12px; margin: 12px 0; border-radius: 6px; border: 1px solid #3F51B5;">
                        <div class="pod-header" onclick="toggleCollapsible('${{podSectionId}}')" style="cursor: pointer; display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <div style="font-weight: bold; font-size: 15px; color: #1976D2;">
                                    📍 Pod: ${{podCode}} ${{statusIcon}}${{targetIcon}}
                                </div>
                                <div style="font-size: 12px; color: #666;">
                                    Super Pod: ${{superPodCode}} | ${{pod.items.length}} items
                                </div>
                            </div>
                            <span class="expand-icon" id="${{podSectionId}}-icon">▼</span>
                        </div>
                        <div class="collapsible-content" id="${{podSectionId}}">`;

                    // Helper function to render cooking items grouped by batch_id
                    function renderCookingItems(items) {{
                        if (items.length === 0) return;

                        html += `<div style="margin: 8px 0;"><strong>🔥 Cooking (${{items.length}}):</strong></div>`;

                        // Group items by batch_id
                        const batches = {{}};
                        const noBatch = [];

                        items.forEach(item => {{
                            if (item.batch_id) {{
                                if (!batches[item.batch_id]) {{
                                    batches[item.batch_id] = [];
                                }}
                                batches[item.batch_id].push(item);
                            }} else {{
                                noBatch.push(item);
                            }}
                        }});

                        // Render batched items
                        Object.entries(batches).forEach(([batchId, batchItems]) => {{
                            html += `<div style="margin-left: 10px; margin-top: 10px; border-left: 3px solid #FF9800; padding-left: 10px;">
                                <div style="font-size: 12px; color: #F57C00; font-weight: bold; margin-bottom: 5px;">Batch: ${{batchId.substring(0, 8)}}...</div>`;

                            batchItems.forEach(item => {{
                                const isTargetOrder = item.order_number === targetOrderNumber;
                                const highlightClass = isTargetOrder ? 'target-order-row' : '';
                                html += `<div class="pod-item ${{highlightClass}}" style="margin-bottom: 8px;">
                                    <div class="pod-item-header">
                                        ${{item.menu_item_name || 'Unknown Item'}}
                                        <span class="state-badge state-cooking">${{item.state}}</span>
                                    </div>
                                    <div class="pod-item-detail">Order: ${{item.order_number || 'Unknown'}}</div>`;

                                // Show all steps for this item
                                if (item.steps && item.steps.length > 0) {{
                                    item.steps.forEach(step => {{
                                        html += `<div class="pod-item-detail" style="margin-left: 15px;">
                                            • Step ${{step.step_order}}: ${{step.resource_type}} (${{step.step_status}})
                                        </div>`;
                                    }});
                                }}

                                html += `</div>`;
                            }});

                            html += `</div>`;
                        }});

                        // Render non-batched items
                        if (noBatch.length > 0) {{
                            noBatch.forEach(item => {{
                                const isTargetOrder = item.order_number === targetOrderNumber;
                                const highlightClass = isTargetOrder ? 'target-order-row' : '';
                                html += `<div class="pod-item ${{highlightClass}}" style="margin-top: 8px;">
                                    <div class="pod-item-header">
                                        ${{item.menu_item_name || 'Unknown Item'}}
                                        <span class="state-badge state-cooking">${{item.state}}</span>
                                    </div>
                                    <div class="pod-item-detail">Order: ${{item.order_number || 'Unknown'}}</div>`;

                                // Show all steps for this item
                                if (item.steps && item.steps.length > 0) {{
                                    item.steps.forEach(step => {{
                                        html += `<div class="pod-item-detail" style="margin-left: 15px;">
                                            • Step ${{step.step_order}}: ${{step.resource_type}} (${{step.step_status}})
                                        </div>`;
                                    }});
                                }}

                                html += `</div>`;
                            }});
                        }}
                    }}

                    // Helper function to render queued items grouped by batch group
                    function renderQueuedItemsByBatchGroup(items) {{
                        if (items.length === 0) return;

                        html += `<div style="margin: 8px 0; margin-top: 15px;"><strong>⏳ Queued (${{items.length}}):</strong></div>`;

                        // Get batch groups for this pod from run data
                        const batchGroups = run.batch_groups || {{}};
                        const podBatchGroups = Object.values(batchGroups).filter(g => g.pod_id === pod.pod_id);

                        if (podBatchGroups.length > 0) {{
                            // Sort groups by priority
                            podBatchGroups.sort((a, b) => (a.priority || 0) - (b.priority || 0));

                            // Create item_id to item mapping for quick lookup
                            const itemMap = {{}};
                            items.forEach(item => {{
                                itemMap[item.item_id] = item;
                            }});

                            // Render each batch group
                            podBatchGroups.forEach(group => {{
                                // Find queued items that belong to this group
                                const groupItems = [];
                                if (group.items && group.items.length > 0) {{
                                    group.items.forEach(bgItem => {{
                                        const queuedItem = itemMap[bgItem.item_id];
                                        if (queuedItem) {{
                                            groupItems.push(queuedItem);
                                        }}
                                    }});
                                }}

                                if (groupItems.length > 0) {{
                                    const podCode = codeMaps.pods[group.pod_id] || group.pod_id.substring(0, 8) + '...';
                                    const groupIdShort = group.group_id.substring(0, 8);

                                    html += `<div style="margin-left: 10px; margin-top: 10px; border-left: 3px solid #9C27B0; padding-left: 10px;">
                                        <div style="font-size: 12px; color: #7B1FA2; font-weight: bold; margin-bottom: 5px;">
                                            Group ${{groupIdShort}} (Priority ${{group.priority}}) - Pod: ${{podCode}}
                                        </div>`;

                                    groupItems.forEach(item => {{
                                        const isTargetOrder = item.order_number === targetOrderNumber;
                                        const highlightClass = isTargetOrder ? 'target-order-row' : '';
                                        html += `<div class="pod-item ${{highlightClass}}" style="margin-bottom: 8px;">
                                            <div class="pod-item-header">
                                                ${{item.menu_item_name || 'Unknown Item'}}
                                                <span class="state-badge state-queued">${{item.state}}</span>
                                            </div>
                                            <div class="pod-item-detail">Order: ${{item.order_number || 'Unknown'}}</div>`;

                                        // Show all steps for this item
                                        if (item.steps && item.steps.length > 0) {{
                                            item.steps.forEach(step => {{
                                                html += `<div class="pod-item-detail" style="margin-left: 15px;">
                                                    • Step ${{step.step_order}}: ${{step.resource_type}} (${{step.step_status}})
                                                </div>`;
                                            }});
                                        }}

                                        html += `</div>`;
                                    }});

                                    html += `</div>`;
                                }}
                            }});
                        }} else {{
                            // Fallback: show items without grouping if no batch groups available
                            items.forEach(item => {{
                                const isTargetOrder = item.order_number === targetOrderNumber;
                                const highlightClass = isTargetOrder ? 'target-order-row' : '';
                                html += `<div class="pod-item ${{highlightClass}}" style="margin-top: 8px;">
                                    <div class="pod-item-header">
                                        ${{item.menu_item_name || 'Unknown Item'}}
                                        <span class="state-badge state-queued">${{item.state}}</span>
                                    </div>
                                    <div class="pod-item-detail">Order: ${{item.order_number || 'Unknown'}}</div>`;

                                // Show all steps for this item
                                if (item.steps && item.steps.length > 0) {{
                                    item.steps.forEach(step => {{
                                        html += `<div class="pod-item-detail" style="margin-left: 15px;">
                                            • Step ${{step.step_order}}: ${{step.resource_type}} (${{step.step_status}})
                                        </div>`;
                                    }});
                                }}

                                html += `</div>`;
                            }});
                        }}
                    }}

                    // Render cooking items grouped by batch_id
                    renderCookingItems(cookingItems);

                    // Render queued items grouped by batch group
                    renderQueuedItemsByBatchGroup(queuedItems);

                    html += `</div></div>`;  // Close collapsible-content and pod div
                }});

                html += `</div></div>`;
            }}

            html += '</div>';
            document.getElementById('runDetails').innerHTML = html;

            // Initialize context items sorting if context exists
            if (run.context && run.all_context_items && run.all_context_items.length > 0) {{
                sortContextItems(index);
            }}
        }}

        function sortContextItems(runIndex) {{
            const run = runsData[runIndex];
            const sortBy = document.getElementById('context-sort-' + runIndex).value;
            const items = [...run.all_context_items]; // Clone array
            const targetOrderNumber = run.items[0].order_number;

            if (sortBy === 'expo') {{
                // Primary: Expo score (absolute, descending - worst first)
                // Secondary: CP score badness
                // Tertiary: Holdback strategy
                items.sort((a, b) => {{
                    const aExpo = Math.abs(parseFloat(a.expo_sit_time_score) || 0);
                    const bExpo = Math.abs(parseFloat(b.expo_sit_time_score) || 0);
                    if (bExpo !== aExpo) return bExpo - aExpo;

                    const aCP = parseFloat(a.customer_promise_score) || 0;
                    const bCP = parseFloat(b.customer_promise_score) || 0;
                    const aBad = aCP > 8 ? (aCP - 8) : (aCP < -10 ? (Math.abs(aCP) - 10) : 0);
                    const bBad = bCP > 8 ? (bCP - 8) : (bCP < -10 ? (Math.abs(bCP) - 10) : 0);
                    if (bBad !== aBad) return bBad - aBad;

                    const aHold = a.hold_back_strategy_v2 || 'ZZZ';
                    const bHold = b.hold_back_strategy_v2 || 'ZZZ';
                    return aHold.localeCompare(bHold);
                }});
            }} else {{
                // Primary: CP score badness
                // Secondary: Expo score
                // Tertiary: Holdback strategy
                items.sort((a, b) => {{
                    const aCP = parseFloat(a.customer_promise_score) || 0;
                    const bCP = parseFloat(b.customer_promise_score) || 0;
                    const aBad = aCP > 8 ? (aCP - 8) : (aCP < -10 ? (Math.abs(aCP) - 10) : 0);
                    const bBad = bCP > 8 ? (bCP - 8) : (bCP < -10 ? (Math.abs(bCP) - 10) : 0);
                    if (bBad !== aBad) return bBad - aBad;

                    const aExpo = Math.abs(parseFloat(a.expo_sit_time_score) || 0);
                    const bExpo = Math.abs(parseFloat(b.expo_sit_time_score) || 0);
                    if (bExpo !== aExpo) return bExpo - aExpo;

                    const aHold = a.hold_back_strategy_v2 || 'ZZZ';
                    const bHold = b.hold_back_strategy_v2 || 'ZZZ';
                    return aHold.localeCompare(bHold);
                }});
            }}

            // Render items table with target order highlighting
            let html = '<table class="items-table"><thead><tr><th>Order</th><th>Item</th><th>Expo Score</th><th>CP Score</th><th>Holdback</th></tr></thead><tbody>';
            items.forEach(item => {{
                const expo = parseFloat(item.expo_sit_time_score) || 0;
                const cp = parseFloat(item.customer_promise_score) || 0;
                const absExpo = Math.abs(expo);
                const expoClass = absExpo > 7 ? 'score-negative' : absExpo > 3 ? 'score-neutral' : 'score-positive';
                const cpClass = (cp > 8 || cp < -10) ? 'score-negative' :
                               (cp > 0 && cp <= 8) ? 'score-neutral' :
                               'score-positive';
                const isTargetOrder = item.order_number === targetOrderNumber;
                const rowClass = isTargetOrder ? 'target-order-row' : '';

                html += `<tr class="${{rowClass}}">
                    <td>${{item.order_number}}</td>
                    <td>${{item.menu_item_name}}</td>
                    <td class="${{expoClass}}">${{absExpo.toFixed(1)}}</td>
                    <td class="${{cpClass}}">${{cp > 0 ? '+' : ''}}${{cp.toFixed(1)}}</td>
                    <td>${{item.hold_back_strategy_v2 || 'None'}}</td>
                </tr>`;
            }});
            html += '</tbody></table>';

            document.getElementById('context-items-' + runIndex).innerHTML = html;
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
                        label: 'Avg Expo Score (absolute)',
                        data: runsData.map(r => Math.abs(r.avg_expo_score)),
                        borderColor: '#2196F3',
                        backgroundColor: 'rgba(33, 150, 243, 0.1)',
                        tension: 0.4,
                        pointRadius: function(context) {{
                            return context.dataIndex === currentRunIndex ? 8 : 4;
                        }},
                        pointHoverRadius: function(context) {{
                            return context.dataIndex === currentRunIndex ? 10 : 6;
                        }},
                        pointBackgroundColor: function(context) {{
                            return context.dataIndex === currentRunIndex ? '#FF5722' : '#2196F3';
                        }},
                        pointBorderColor: function(context) {{
                            return context.dataIndex === currentRunIndex ? '#FF5722' : '#2196F3';
                        }},
                        pointBorderWidth: function(context) {{
                            return context.dataIndex === currentRunIndex ? 3 : 2;
                        }}
                    }},
                    {{
                        label: 'Avg Customer Promise Score',
                        data: runsData.map(r => r.avg_cp_score),
                        borderColor: '#4CAF50',
                        backgroundColor: 'rgba(76, 175, 80, 0.1)',
                        tension: 0.4,
                        pointRadius: function(context) {{
                            return context.dataIndex === currentRunIndex ? 8 : 4;
                        }},
                        pointHoverRadius: function(context) {{
                            return context.dataIndex === currentRunIndex ? 10 : 6;
                        }},
                        pointBackgroundColor: function(context) {{
                            return context.dataIndex === currentRunIndex ? '#FF5722' : '#4CAF50';
                        }},
                        pointBorderColor: function(context) {{
                            return context.dataIndex === currentRunIndex ? '#FF5722' : '#4CAF50';
                        }},
                        pointBorderWidth: function(context) {{
                            return context.dataIndex === currentRunIndex ? 3 : 2;
                        }}
                    }}
                ]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: true,
                plugins: {{
                    legend: {{
                        display: true,
                        position: 'top'
                    }},
                    tooltip: {{
                        mode: 'index',
                        intersect: false
                    }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: false,
                        title: {{
                            display: true,
                            text: 'Score (minutes)'
                        }}
                    }},
                    x: {{
                        title: {{
                            display: true,
                            text: 'Sequencing Run'
                        }}
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
            timelineChart.data.datasets.forEach(dataset => {{
                dataset.pointRadius = dataset.pointRadius;
                dataset.pointBackgroundColor = dataset.pointBackgroundColor;
            }});
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
    # Fetch order
    order_list = get_order_details(order_identifier)
    if not order_list or len(order_list) == 0:
        print(f"ERROR: Order not found: {order_identifier}")
        return None
    order = order_list[0]

    # Fetch items
    items = get_order_items(order['order_id'])
    if not items:
        print(f"ERROR: No items found for order {order_identifier}")
        return None

    # Fetch all sequencing runs
    all_seq_data = get_all_sequencing_runs(order['order_id'])
    if not all_seq_data:
        print(f"ERROR: No sequencing data found for order {order_identifier}")
        return None

    # Organize runs
    runs_data = organize_runs_data(all_seq_data, order['order_number'])

    if not runs_data:
        print(f"ERROR: Could not organize sequencing runs for order {order_identifier}")
        return None

    # Generate HTML
    output_file = generate_html(order, items, runs_data, order_identifier)

    print(f"✓ Generated: {output_file}")
    return output_file

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 hdr_insights.py <order_number_or_id>")
        print("Example: python3 hdr_insights.py 6187677")
        sys.exit(1)

    order_identifier = sys.argv[1]
    analyze_order(order_identifier)
