#!/usr/bin/env python3
"""
OTR Insights Tool - Generate interactive HTML reports for On-Time Rate analysis.

Usage:
    python3 otr_insights.py <hdr_name>           # HDR-level analysis
    python3 otr_insights.py <order_number>       # Order-level deep dive
    python3 otr_insights.py --network            # Network-wide WBR summary

Examples:
    python3 otr_insights.py "Yardley"
    python3 otr_insights.py 6187677
    python3 otr_insights.py --network --weeks 4
"""

import subprocess
import json
import csv
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Increase CSV field size limit for large JSON fields
csv.field_size_limit(10000000)

# Constants
PROJECT_ID = "wonder-dw-prod-brd"
DEFAULT_WEEKS = 6
OUTPUT_DIR = Path(__file__).parent / "outputs"


def run_bq_query(query: str) -> list[dict]:
    """Execute BigQuery query and return results as list of dicts."""
    cmd = [
        "bq", "query",
        "--use_legacy_sql=false",
        f"--project_id={PROJECT_ID}",
        "--format=json",
        "--max_rows=10000",
        query
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    # Check if we got valid JSON output (success even if stderr has warnings)
    output = result.stdout.strip()
    if output.startswith('[') or output.startswith('{'):
        # Valid JSON - ignore any stderr warnings (SSL, etc.)
        pass
    elif result.returncode != 0 or not output:
        # Real error - show relevant stderr (filter noise)
        stderr_lines = [l for l in result.stderr.split('\n') 
                        if l.strip() 
                        and 'PermissionError' not in l 
                        and 'bootstrapping' not in l 
                        and 'load_verify_locations' not in l
                        and 'Traceback' not in l
                        and 'File "' not in l
                        and 'import ' not in l
                        and 'from ' not in l]
        if stderr_lines:
            print(f"BigQuery Error: {chr(10).join(stderr_lines[:5])}", file=sys.stderr)
        return []
    
    try:
        return json.loads(result.stdout) if result.stdout.strip() else []
    except json.JSONDecodeError:
        print(f"JSON Parse Error: {result.stdout[:500]}", file=sys.stderr)
        return []


def get_hdr_metrics(hdr_name: str, weeks: int = DEFAULT_WEEKS) -> dict:
    """Get comprehensive HDR-level metrics."""
    
    query = f"""
    WITH weekly_metrics AS (
      SELECT
        FORMAT_DATE('%F', DATE_TRUNC(o.service_date_et, WEEK(MONDAY))) AS service_week,
        h.hdr_name,
        h.hdr_id,
        h.population_type,
        h.hdr_class,
        h.design_type,
        COALESCE(h.calendar_weeks_from_friends_family_start, h.calendar_weeks_from_opening_date) AS weeks_open,
        
        -- Volume
        COUNT(DISTINCT o.order_id) AS total_orders,
        COUNT(DISTINCT CASE WHEN o.order_channel IN ('APP','WEB','IN_PERSON') THEN o.order_id END) AS orders_1p,
        COUNT(DISTINCT CASE WHEN o.dining_option = 'DELIVERY' AND o.order_channel IN ('APP','WEB','IN_PERSON') THEN o.order_id END) AS orders_1p_delivery,
        COUNT(DISTINCT CASE WHEN o.dining_option = 'PICKUP' AND o.order_channel IN ('APP','WEB','IN_PERSON') THEN o.order_id END) AS orders_1p_pickup,
        
        -- OTR Metrics using imperfect_orders.on_time_issue (correct method)
        -- 1P OTR: All 1P orders
        ROUND((1 - SAFE_DIVIDE(
          COUNT(DISTINCT CASE WHEN o.order_channel IN ('APP','WEB','IN_PERSON') AND io.on_time_issue THEN o.order_id END),
          COUNT(DISTINCT CASE WHEN o.order_channel IN ('APP','WEB','IN_PERSON') THEN o.order_id END)
        )) * 100, 1) AS otr_1p,
        -- Delivery OTR
        ROUND((1 - SAFE_DIVIDE(
          COUNT(DISTINCT CASE WHEN o.dining_option = 'DELIVERY' AND o.order_channel IN ('APP','WEB','IN_PERSON') AND io.on_time_issue THEN o.order_id END),
          COUNT(DISTINCT CASE WHEN o.dining_option = 'DELIVERY' AND o.order_channel IN ('APP','WEB','IN_PERSON') THEN o.order_id END)
        )) * 100, 1) AS otr_1p_delivery,
        -- Pickup OTR
        ROUND((1 - SAFE_DIVIDE(
          COUNT(DISTINCT CASE WHEN o.dining_option = 'PICKUP' AND o.order_channel IN ('APP','WEB','IN_PERSON') AND io.on_time_issue THEN o.order_id END),
          COUNT(DISTINCT CASE WHEN o.dining_option = 'PICKUP' AND o.order_channel IN ('APP','WEB','IN_PERSON') THEN o.order_id END)
        )) * 100, 1) AS otr_1p_pickup,
        -- OTR No Earlies (using delivery_sla_difference for this specific cut)
        ROUND(AVG(CASE WHEN o.order_channel IN ('APP','WEB','IN_PERSON')
          AND o.delivery_sla_difference <= 0.99 THEN 1 ELSE 0 END) * 100, 1) AS otr_1p_no_earlies,
        -- Kitchen OTR (ready_for_pickup_sla_difference <= 2)
        ROUND(AVG(CASE WHEN o.ready_for_pickup_sla_difference <= 2 THEN 1 ELSE 0 END) * 100, 1) AS kitchen_otr,
        
        -- Timing Metrics
        ROUND(AVG(o.ticket_time_mins), 1) AS avg_ticket_time,
        ROUND(AVG(o.actual_pickup_waiting_duration_mins), 1) AS avg_expo_wait,
        ROUND(AVG(o.courier_response_time_mins), 1) AS avg_courier_response,
        ROUND(AVG(o.kitchen_handoff_time_mins), 1) AS avg_handoff,
        ROUND(AVG(o.actual_transit_mins), 1) AS avg_transit,
        
        -- Variance from Expected
        ROUND(AVG(o.actual_queue_mins - o.estimated_queue_mins), 1) AS queue_variance,
        ROUND(AVG(o.actual_cook_duration_mins - o.estimated_cook_duration_mins), 1) AS cook_variance,
        ROUND(AVG(o.actual_packaging_bagging_mins - o.estimated_packaging_bagging_mins), 1) AS pack_variance,
        
        -- Miss Categories
        COUNT(DISTINCT CASE WHEN o.delivery_sla_difference > 0.99 THEN o.order_id END) AS late_orders,
        COUNT(DISTINCT CASE WHEN o.delivery_sla_difference < -8.99 THEN o.order_id END) AS early_orders,
        
        -- Profile Detection (Delivery only)
        ROUND(AVG(CASE WHEN o.dining_option = 'DELIVERY' 
          AND o.courier_response_time_mins <= 5 AND o.kitchen_handoff_time_mins > 8 
          THEN 1 ELSE 0 END) * 100, 1) AS pct_profile_a,
        ROUND(AVG(CASE WHEN o.dining_option = 'DELIVERY'
          AND o.courier_response_time_mins > 15 AND o.kitchen_handoff_time_mins <= 5 
          THEN 1 ELSE 0 END) * 100, 1) AS pct_profile_b,
        
        -- Force Complete Metrics (from imperfect_kitchen_items)
        ROUND(AVG(CASE WHEN iki.has_force_progression = 1 THEN 1 ELSE 0 END) * 100, 1) AS pct_force_complete,
        ROUND(AVG(CASE WHEN iki.has_premature_force_complete = 1 THEN 1 ELSE 0 END) * 100, 1) AS pct_premature_fc,
        ROUND(AVG(CASE WHEN iki.has_critical_force_complete = 1 THEN 1 ELSE 0 END) * 100, 1) AS pct_critical_fc,
        
        -- Force Complete + Slow Handoff (Fake Bump Signal)
        ROUND(AVG(CASE WHEN o.dining_option = 'DELIVERY' 
          AND iki.has_force_progression = 1 
          AND o.kitchen_handoff_time_mins > 5 
          THEN 1 ELSE 0 END) * 100, 1) AS pct_fc_slow_handoff,
          
        -- Handoff Time for Force Complete vs Non-Force Complete orders
        ROUND(AVG(CASE WHEN iki.has_force_progression = 1 THEN o.kitchen_handoff_time_mins END), 1) AS avg_handoff_fc_orders,
        ROUND(AVG(CASE WHEN iki.has_force_progression = 0 OR iki.has_force_progression IS NULL THEN o.kitchen_handoff_time_mins END), 1) AS avg_handoff_non_fc_orders
          
      FROM `wonder-dw-prod-brd.orders.hdr_orders` o
      JOIN `wonder-dw-prod-brd.dw.dim_hdrs` h ON o.hdr_id = h.hdr_id
      LEFT JOIN `wonder-dw-prod-brd.orders.imperfect_orders` io ON o.order_id = io.order_id
      LEFT JOIN (
        SELECT order_id, 
          MAX(has_force_progression) AS has_force_progression,
          MAX(has_premature_force_complete) AS has_premature_force_complete,
          MAX(has_critical_force_complete) AS has_critical_force_complete
        FROM `wonder-dw-prod-brd.orders.imperfect_kitchen_items`
        GROUP BY order_id
      ) iki ON o.order_id = iki.order_id
      WHERE o.order_status = 'COMPLETE'
        AND o.brand_category = 'WONDER_HDR'
        AND (o.order_business_type <> 'WONDER_SPOT' OR o.order_business_type IS NULL)
        AND (o.order_business_type <> '3P_PLATFORM_CORPORATE' OR o.order_business_type IS NULL)
        AND o.service_date_et >= DATE_TRUNC(DATE_SUB(CURRENT_DATE('America/New_York'), INTERVAL {weeks + 1} WEEK), WEEK(MONDAY))
        AND o.service_date_et < DATE_TRUNC(CURRENT_DATE('America/New_York'), WEEK(MONDAY))
        AND LOWER(h.hdr_name) LIKE LOWER('%{hdr_name}%')
      GROUP BY 1, 2, 3, 4, 5, 6, 7
    )
    SELECT * FROM weekly_metrics
    ORDER BY service_week DESC
    """
    
    return run_bq_query(query)


def get_late_order_error_decomposition(hdr_name: str, weeks: int = 2) -> list[dict]:
    """Get error decomposition for late orders by pickup scenario - reveals TRUE root cause."""
    
    query = f"""
    WITH late_orders AS (
      SELECT
        o.order_id,
        -- Pickup Scenario
        CASE 
          WHEN o.kitchen_handoff_time_mins <= 5 AND o.courier_response_time_mins <= 5 
            THEN 'Both Fast'
          WHEN o.kitchen_handoff_time_mins > 5 AND o.courier_response_time_mins <= 5 
            THEN 'Ops Fault (Slow Handoff)'
          WHEN o.kitchen_handoff_time_mins <= 5 AND o.courier_response_time_mins > 5 
            THEN 'Courier Late'
          ELSE 'Both Slow'
        END AS pickup_scenario,
        -- Error decomposition: Actual - Estimated (negative = late)
        COALESCE(o.estimated_queue_mins, 0) - COALESCE(o.actual_queue_mins, 0) AS queue_error,
        COALESCE(o.estimated_cook_duration_mins, 0) - COALESCE(o.actual_cook_duration_mins, 0) AS cook_error,
        COALESCE(o.estimated_pickup_waiting_duration_mins, 0) - COALESCE(o.actual_pickup_waiting_duration_mins, 0) AS pickup_error,
        COALESCE(o.estimated_transit_mins, 0) - COALESCE(o.actual_transit_mins, 0) AS transit_error,
        -- Total
        COALESCE(o.estimated_o2e_mins, 0) - COALESCE(o.actual_o2e_mins, 0) AS total_error
      FROM `wonder-dw-prod-brd.orders.hdr_orders` o
      JOIN `wonder-dw-prod-brd.dw.dim_hdrs` h ON o.hdr_id = h.hdr_id
      LEFT JOIN `wonder-dw-prod-brd.orders.imperfect_orders` io ON o.order_id = io.order_id
      WHERE o.order_status = 'COMPLETE'
        AND o.brand_category = 'WONDER_HDR'
        AND o.dining_option = 'DELIVERY'
        AND (o.order_business_type <> 'WONDER_SPOT' OR o.order_business_type IS NULL)
        AND o.service_date_et >= DATE_SUB(CURRENT_DATE('America/New_York'), INTERVAL {weeks} WEEK)
        AND o.service_date_et < CURRENT_DATE('America/New_York')
        AND LOWER(h.hdr_name) LIKE LOWER('%{hdr_name}%')
        AND io.on_time_issue = TRUE  -- Only late orders
    )
    SELECT
      pickup_scenario,
      COUNT(*) AS late_orders,
      ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 1) AS pct_of_late,
      -- Error decomposition (negative = late)
      ROUND(AVG(queue_error), 1) AS avg_queue_error,
      ROUND(AVG(cook_error), 1) AS avg_cook_error,
      ROUND(AVG(queue_error + cook_error), 1) AS avg_kitchen_error,
      ROUND(AVG(pickup_error), 1) AS avg_pickup_error,
      ROUND(AVG(transit_error), 1) AS avg_transit_error,
      ROUND(AVG(total_error), 1) AS avg_total_error,
      -- % attribution (of total lateness)
      ROUND(ABS(AVG(queue_error + cook_error)) * 100.0 / NULLIF(ABS(AVG(total_error)), 0), 0) AS pct_kitchen_driver,
      ROUND(ABS(AVG(transit_error)) * 100.0 / NULLIF(ABS(AVG(total_error)), 0), 0) AS pct_transit_driver
    FROM late_orders
    GROUP BY 1
    ORDER BY late_orders DESC
    """
    
    return run_bq_query(query)


def get_hdr_scenario_breakdown(hdr_name: str, weeks: int = DEFAULT_WEEKS) -> list[dict]:
    """Get kitchen handoff scenario breakdown for an HDR."""
    
    query = f"""
    SELECT
      FORMAT_DATE('%F', DATE_TRUNC(o.service_date_et, WEEK(MONDAY))) AS service_week,
      h.hdr_name,
      CASE 
        WHEN o.ready_for_pickup_sla_difference > 2 AND o.courier_response_time_mins <= 5 
          THEN 'A. Kitchen LATE, Courier Waits'
        WHEN o.ready_for_pickup_sla_difference <= 2 AND o.courier_response_time_mins > 5 
          THEN 'B. Kitchen FAST, Food Waits'
        WHEN o.ready_for_pickup_sla_difference > 2 AND o.courier_response_time_mins > 5 
          THEN 'C. Compounding Failure'
        ELSE 'D. Ideal State'
      END AS scenario,
      COUNT(DISTINCT o.order_id) AS orders,
      ROUND(AVG(CASE WHEN o.delivery_sla_difference BETWEEN -8.99 AND 0.99 THEN 1 ELSE 0 END) * 100, 1) AS otr,
      ROUND(AVG(o.actual_pickup_waiting_duration_mins), 1) AS avg_sit_time,
      ROUND(AVG(o.courier_response_time_mins), 1) AS avg_courier_response,
      ROUND(AVG(o.kitchen_handoff_time_mins), 1) AS avg_handoff
    FROM `wonder-dw-prod-brd.orders.hdr_orders` o
    JOIN `wonder-dw-prod-brd.dw.dim_hdrs` h ON o.hdr_id = h.hdr_id
    WHERE o.order_status = 'COMPLETE'
      AND o.brand_category = 'WONDER_HDR'
      AND o.dining_option = 'DELIVERY'
      AND o.order_channel IN ('APP', 'WEB', 'IN_PERSON')
      AND (o.order_business_type <> 'WONDER_SPOT' OR o.order_business_type IS NULL)
      AND o.service_date_et >= DATE_TRUNC(DATE_SUB(CURRENT_DATE('America/New_York'), INTERVAL {weeks + 1} WEEK), WEEK(MONDAY))
      AND o.service_date_et < DATE_TRUNC(CURRENT_DATE('America/New_York'), WEEK(MONDAY))
      AND LOWER(h.hdr_name) LIKE LOWER('%{hdr_name}%')
    GROUP BY 1, 2, 3
    ORDER BY service_week DESC, scenario
    """
    
    return run_bq_query(query)


def get_production_variance_by_pod(hdr_name: str, weeks: int = 2) -> list[dict]:
    """Get production variance analysis by pod type and restaurant for an HDR."""
    
    query = f"""
    WITH item_metrics AS (
      SELECT
        h.hdr_name,
        ki.pod_type,
        r.restaurant_name,
        ki.order_id,
        ki.menu_item_name,
        ki.expected_step_time / 60.0 AS expected_cook_mins,
        ki.actual_production_time_min,
        ki.actual_production_time_min - (ki.expected_step_time / 60.0) AS production_variance,
        iki.has_longer_than_expected_production_time,
        iki.has_shorter_than_expected_production_time,
        io.on_time_issue
      FROM `wonder-dw-prod-brd.orders.hdr_kitchen_order_item` ki
      JOIN `wonder-dw-prod-brd.orders.hdr_orders` o ON ki.order_id = o.order_id
      JOIN `wonder-dw-prod-brd.dw.dim_hdrs` h ON o.hdr_id = h.hdr_id
      LEFT JOIN `wonder-dw-prod-brd.dw.dim_restaurants` r ON ki.restaurant_id = r.restaurant_id
      LEFT JOIN `wonder-dw-prod-brd.orders.imperfect_kitchen_items` iki 
        ON ki.order_id = iki.order_id AND ki.id = iki.id
      LEFT JOIN `wonder-dw-prod-brd.orders.imperfect_orders` io ON o.order_id = io.order_id
      WHERE o.order_status = 'COMPLETE'
        AND o.brand_category = 'WONDER_HDR'
        AND ki.order_status = 'COMPLETED'
        AND (o.order_business_type <> 'WONDER_SPOT' OR o.order_business_type IS NULL)
        AND o.service_date_et >= DATE_SUB(CURRENT_DATE('America/New_York'), INTERVAL {weeks} WEEK)
        AND o.service_date_et < CURRENT_DATE('America/New_York')
        AND LOWER(h.hdr_name) LIKE LOWER('%{hdr_name}%')
        AND ki.actual_production_time_min IS NOT NULL
        AND ki.expected_step_time > 0
    )
    SELECT
      pod_type,
      restaurant_name,
      COUNT(*) AS item_count,
      COUNT(DISTINCT order_id) AS order_count,
      
      -- Production Time Metrics
      ROUND(AVG(expected_cook_mins), 1) AS avg_expected_cook,
      ROUND(AVG(actual_production_time_min), 1) AS avg_actual_cook,
      ROUND(AVG(production_variance), 1) AS avg_variance,
      
      -- % Over/Under Expected
      ROUND(AVG(CASE WHEN has_longer_than_expected_production_time = 1 THEN 1 ELSE 0 END) * 100, 1) AS pct_over_expected,
      ROUND(AVG(CASE WHEN has_shorter_than_expected_production_time = 1 THEN 1 ELSE 0 END) * 100, 1) AS pct_under_expected,
      
      -- OTR Impact (orders with this pod/restaurant)
      ROUND((1 - SAFE_DIVIDE(
        COUNT(DISTINCT CASE WHEN on_time_issue THEN order_id END),
        COUNT(DISTINCT order_id)
      )) * 100, 1) AS otr_pct,
      
      -- Variance when late vs on-time
      ROUND(AVG(CASE WHEN on_time_issue THEN production_variance END), 1) AS variance_when_late,
      ROUND(AVG(CASE WHEN NOT on_time_issue OR on_time_issue IS NULL THEN production_variance END), 1) AS variance_when_ontime
      
    FROM item_metrics
    WHERE pod_type IS NOT NULL
    GROUP BY 1, 2
    HAVING COUNT(*) >= 20
    ORDER BY avg_variance DESC, pct_over_expected DESC
    """
    
    return run_bq_query(query)


def get_reason_code_breakdown(hdr_name: str, weeks: int = 2) -> list[dict]:
    """Get reason code breakdown for all orders, late orders, and kitchen late orders."""
    
    query = f"""
    WITH order_flags AS (
      SELECT
        o.order_id,
        io.on_time_issue,
        o.ready_for_pickup_sla_difference,
        -- Basic flags
        MAX(iki.has_longer_than_expected_production_time) AS has_long_production,
        MAX(iki.has_shorter_than_expected_production_time) AS has_short_production,
        MAX(iki.has_long_queue) AS has_long_queue,
        MAX(iki.has_long_pending_packaging) AS has_long_pending_packaging,
        MAX(iki.has_force_progression) AS has_force_complete,
        MAX(iki.has_premature_force_complete) AS has_premature_fc,
        MAX(iki.has_critical_force_complete) AS has_critical_fc,
        -- Sequencer flags
        MAX(iki.has_bad_interaction) AS has_bad_interaction,
        MAX(iki.has_trickling_violation) AS has_trickling,
        MAX(iki.has_double_delay) AS has_double_delay,
        MAX(iki.has_reset) AS has_reset,
        -- Hot hold flags
        MAX(iki.has_missing_pouch) AS has_missing_pouch,
        MAX(iki.has_surprise_pouch) AS has_surprise_pouch,
        -- Other
        MAX(CASE WHEN ki.hot_hold_item_a_la_minute_fl = 1 THEN 1 ELSE 0 END) AS has_alm_item,
        MAX(CASE WHEN ki.delay_duration_mins > 0 THEN 1 ELSE 0 END) AS has_sequencer_delay,
        MAX(iki.has_missing_signal) AS has_missing_signal,
        MAX(iki.has_kds_remake) AS has_kds_remake,
        MAX(iki.has_bump) AS has_bump
      FROM `wonder-dw-prod-brd.orders.hdr_orders` o
      JOIN `wonder-dw-prod-brd.dw.dim_hdrs` h ON o.hdr_id = h.hdr_id
      LEFT JOIN `wonder-dw-prod-brd.orders.imperfect_orders` io ON o.order_id = io.order_id
      LEFT JOIN `wonder-dw-prod-brd.orders.imperfect_kitchen_items` iki ON o.order_id = iki.order_id
      LEFT JOIN `wonder-dw-prod-brd.orders.hdr_kitchen_order_item` ki ON o.order_id = ki.order_id
      WHERE o.order_status = 'COMPLETE'
        AND o.brand_category = 'WONDER_HDR'
        AND (o.order_business_type <> 'WONDER_SPOT' OR o.order_business_type IS NULL)
        AND o.service_date_et >= DATE_SUB(CURRENT_DATE('America/New_York'), INTERVAL {weeks} WEEK)
        AND o.service_date_et < CURRENT_DATE('America/New_York')
        AND LOWER(h.hdr_name) LIKE LOWER('%{hdr_name}%')
      GROUP BY 1, 2, 3
    )
    SELECT
      'All Orders' AS segment,
      COUNT(*) AS orders,
      ROUND(AVG(CASE WHEN has_long_production = 1 THEN 1 ELSE 0 END) * 100, 1) AS pct_long_production,
      ROUND(AVG(CASE WHEN has_long_queue = 1 THEN 1 ELSE 0 END) * 100, 1) AS pct_long_queue,
      ROUND(AVG(CASE WHEN has_long_pending_packaging = 1 THEN 1 ELSE 0 END) * 100, 1) AS pct_long_pending_packaging,
      ROUND(AVG(CASE WHEN has_force_complete = 1 THEN 1 ELSE 0 END) * 100, 1) AS pct_force_complete,
      ROUND(AVG(CASE WHEN has_premature_fc = 1 THEN 1 ELSE 0 END) * 100, 1) AS pct_premature_fc,
      ROUND(AVG(CASE WHEN has_critical_fc = 1 THEN 1 ELSE 0 END) * 100, 1) AS pct_critical_fc,
      ROUND(AVG(CASE WHEN has_bad_interaction = 1 THEN 1 ELSE 0 END) * 100, 1) AS pct_bad_interaction,
      ROUND(AVG(CASE WHEN has_trickling = 1 THEN 1 ELSE 0 END) * 100, 1) AS pct_trickling,
      ROUND(AVG(CASE WHEN has_double_delay = 1 THEN 1 ELSE 0 END) * 100, 1) AS pct_double_delay,
      ROUND(AVG(CASE WHEN has_alm_item = 1 THEN 1 ELSE 0 END) * 100, 1) AS pct_alm,
      ROUND(AVG(CASE WHEN has_sequencer_delay = 1 THEN 1 ELSE 0 END) * 100, 1) AS pct_sequencer_delay,
      ROUND(AVG(CASE WHEN has_missing_pouch = 1 THEN 1 ELSE 0 END) * 100, 1) AS pct_missing_pouch,
      ROUND(AVG(CASE WHEN has_surprise_pouch = 1 THEN 1 ELSE 0 END) * 100, 1) AS pct_surprise_pouch,
      ROUND(AVG(CASE WHEN has_kds_remake = 1 THEN 1 ELSE 0 END) * 100, 1) AS pct_kds_remake,
      ROUND(AVG(CASE WHEN has_bump = 1 THEN 1 ELSE 0 END) * 100, 1) AS pct_bump
    FROM order_flags
    
    UNION ALL
    
    SELECT
      'Late Orders' AS segment,
      COUNT(*) AS orders,
      ROUND(AVG(CASE WHEN has_long_production = 1 THEN 1 ELSE 0 END) * 100, 1) AS pct_long_production,
      ROUND(AVG(CASE WHEN has_long_queue = 1 THEN 1 ELSE 0 END) * 100, 1) AS pct_long_queue,
      ROUND(AVG(CASE WHEN has_long_pending_packaging = 1 THEN 1 ELSE 0 END) * 100, 1) AS pct_long_pending_packaging,
      ROUND(AVG(CASE WHEN has_force_complete = 1 THEN 1 ELSE 0 END) * 100, 1) AS pct_force_complete,
      ROUND(AVG(CASE WHEN has_premature_fc = 1 THEN 1 ELSE 0 END) * 100, 1) AS pct_premature_fc,
      ROUND(AVG(CASE WHEN has_critical_fc = 1 THEN 1 ELSE 0 END) * 100, 1) AS pct_critical_fc,
      ROUND(AVG(CASE WHEN has_bad_interaction = 1 THEN 1 ELSE 0 END) * 100, 1) AS pct_bad_interaction,
      ROUND(AVG(CASE WHEN has_trickling = 1 THEN 1 ELSE 0 END) * 100, 1) AS pct_trickling,
      ROUND(AVG(CASE WHEN has_double_delay = 1 THEN 1 ELSE 0 END) * 100, 1) AS pct_double_delay,
      ROUND(AVG(CASE WHEN has_alm_item = 1 THEN 1 ELSE 0 END) * 100, 1) AS pct_alm,
      ROUND(AVG(CASE WHEN has_sequencer_delay = 1 THEN 1 ELSE 0 END) * 100, 1) AS pct_sequencer_delay,
      ROUND(AVG(CASE WHEN has_missing_pouch = 1 THEN 1 ELSE 0 END) * 100, 1) AS pct_missing_pouch,
      ROUND(AVG(CASE WHEN has_surprise_pouch = 1 THEN 1 ELSE 0 END) * 100, 1) AS pct_surprise_pouch,
      ROUND(AVG(CASE WHEN has_kds_remake = 1 THEN 1 ELSE 0 END) * 100, 1) AS pct_kds_remake,
      ROUND(AVG(CASE WHEN has_bump = 1 THEN 1 ELSE 0 END) * 100, 1) AS pct_bump
    FROM order_flags
    WHERE on_time_issue = TRUE
    
    UNION ALL
    
    SELECT
      'Kitchen Late (>2m)' AS segment,
      COUNT(*) AS orders,
      ROUND(AVG(CASE WHEN has_long_production = 1 THEN 1 ELSE 0 END) * 100, 1) AS pct_long_production,
      ROUND(AVG(CASE WHEN has_long_queue = 1 THEN 1 ELSE 0 END) * 100, 1) AS pct_long_queue,
      ROUND(AVG(CASE WHEN has_long_pending_packaging = 1 THEN 1 ELSE 0 END) * 100, 1) AS pct_long_pending_packaging,
      ROUND(AVG(CASE WHEN has_force_complete = 1 THEN 1 ELSE 0 END) * 100, 1) AS pct_force_complete,
      ROUND(AVG(CASE WHEN has_premature_fc = 1 THEN 1 ELSE 0 END) * 100, 1) AS pct_premature_fc,
      ROUND(AVG(CASE WHEN has_critical_fc = 1 THEN 1 ELSE 0 END) * 100, 1) AS pct_critical_fc,
      ROUND(AVG(CASE WHEN has_bad_interaction = 1 THEN 1 ELSE 0 END) * 100, 1) AS pct_bad_interaction,
      ROUND(AVG(CASE WHEN has_trickling = 1 THEN 1 ELSE 0 END) * 100, 1) AS pct_trickling,
      ROUND(AVG(CASE WHEN has_double_delay = 1 THEN 1 ELSE 0 END) * 100, 1) AS pct_double_delay,
      ROUND(AVG(CASE WHEN has_alm_item = 1 THEN 1 ELSE 0 END) * 100, 1) AS pct_alm,
      ROUND(AVG(CASE WHEN has_sequencer_delay = 1 THEN 1 ELSE 0 END) * 100, 1) AS pct_sequencer_delay,
      ROUND(AVG(CASE WHEN has_missing_pouch = 1 THEN 1 ELSE 0 END) * 100, 1) AS pct_missing_pouch,
      ROUND(AVG(CASE WHEN has_surprise_pouch = 1 THEN 1 ELSE 0 END) * 100, 1) AS pct_surprise_pouch,
      ROUND(AVG(CASE WHEN has_kds_remake = 1 THEN 1 ELSE 0 END) * 100, 1) AS pct_kds_remake,
      ROUND(AVG(CASE WHEN has_bump = 1 THEN 1 ELSE 0 END) * 100, 1) AS pct_bump
    FROM order_flags
    WHERE ready_for_pickup_sla_difference > 2
    """
    
    return run_bq_query(query)


def get_late_order_ranked_reasons(hdr_name: str, weeks: int = 2) -> list[dict]:
    """Get ranked reason codes for late orders - descending by frequency."""
    
    query = f"""
    WITH order_flags AS (
      SELECT
        o.order_id,
        io.on_time_issue,
        o.ready_for_pickup_sla_difference,
        o.ticket_time_mins,
        o.actual_queue_mins,
        o.actual_cook_duration_mins,
        o.actual_packaging_bagging_mins,
        o.courier_response_time_mins,
        o.kitchen_handoff_time_mins,
        -- Expo wait and cook time variance for sequencer validation
        MAX(iki.last_item_expo_wait_time_gt_2) AS last_item_expo_wait_gt_2,
        (MAX(ki.expected_step_time) - MIN(ki.expected_step_time)) / 60.0 AS cook_time_range,
        -- All flags
        MAX(iki.has_longer_than_expected_production_time) AS has_long_production,
        MAX(iki.has_long_queue) AS has_long_queue,
        MAX(iki.has_long_pending_packaging) AS has_long_pending_packaging,
        MAX(iki.has_force_progression) AS has_force_complete,
        MAX(iki.has_premature_force_complete) AS has_premature_fc,
        MAX(iki.has_critical_force_complete) AS has_critical_fc,
        MAX(iki.has_bad_interaction) AS has_bad_interaction,
        MAX(iki.has_trickling_violation) AS has_trickling,
        MAX(iki.has_double_delay) AS has_double_delay,
        MAX(CASE WHEN ki.hot_hold_item_a_la_minute_fl = 1 THEN 1 ELSE 0 END) AS has_alm_item,
        MAX(CASE WHEN ki.delay_duration_mins > 0 THEN 1 ELSE 0 END) AS has_sequencer_delay,
        MAX(iki.has_missing_pouch) AS has_missing_pouch,
        MAX(iki.has_surprise_pouch) AS has_surprise_pouch,
        MAX(iki.has_kds_remake) AS has_kds_remake,
        MAX(iki.has_bump) AS has_bump,
        MAX(iki.has_reset) AS has_reset,
        MAX(iki.has_missing_signal) AS has_missing_signal
      FROM `wonder-dw-prod-brd.orders.hdr_orders` o
      JOIN `wonder-dw-prod-brd.dw.dim_hdrs` h ON o.hdr_id = h.hdr_id
      LEFT JOIN `wonder-dw-prod-brd.orders.imperfect_orders` io ON o.order_id = io.order_id
      LEFT JOIN `wonder-dw-prod-brd.orders.imperfect_kitchen_items` iki ON o.order_id = iki.order_id
      LEFT JOIN `wonder-dw-prod-brd.orders.hdr_kitchen_order_item` ki ON o.order_id = ki.order_id
      WHERE o.order_status = 'COMPLETE'
        AND o.brand_category = 'WONDER_HDR'
        AND (o.order_business_type <> 'WONDER_SPOT' OR o.order_business_type IS NULL)
        AND o.service_date_et >= DATE_SUB(CURRENT_DATE('America/New_York'), INTERVAL {weeks} WEEK)
        AND o.service_date_et < CURRENT_DATE('America/New_York')
        AND LOWER(h.hdr_name) LIKE LOWER('%{hdr_name}%')
      GROUP BY 1, 2, 3, 4, 5, 6, 7, 8, 9
    ),
    -- Add sequencer overhold flag: expo wait > cook time variance means sequencer is the problem
    order_flags_with_sequencer AS (
      SELECT *,
        -- Sequencer is only flagged as issue if expo wait exceeds cook time variance
        CASE WHEN last_item_expo_wait_gt_2 = 1 
             AND (has_bad_interaction = 1 OR has_trickling = 1 OR has_double_delay = 1)
             AND COALESCE(cook_time_range, 0) < 2  -- Low complexity order shouldn't have sequencer issues
             THEN 1 ELSE 0 END AS sequencer_actual_issue
      FROM order_flags
    ),
    late_orders AS (
      SELECT * FROM order_flags_with_sequencer WHERE on_time_issue = TRUE
    ),
    kitchen_late AS (
      SELECT * FROM order_flags_with_sequencer WHERE ready_for_pickup_sla_difference > 2
    ),
    -- Unpivot reason codes for late orders
    reason_counts AS (
      SELECT 'Long Production (Actual > Expected + 3m)' AS reason_code, 
        'Kitchen Ops' AS owner, 'Ops' AS category,
        SUM(has_long_production) AS late_count,
        (SELECT SUM(has_long_production) FROM order_flags_with_sequencer) AS all_count,
        (SELECT SUM(has_long_production) FROM kitchen_late) AS kitchen_late_count,
        COUNT(*) AS total_late,
        (SELECT COUNT(*) FROM order_flags_with_sequencer) AS total_all,
        (SELECT COUNT(*) FROM kitchen_late) AS total_kitchen_late,
        ROUND(AVG(CASE WHEN has_long_production = 1 THEN ticket_time_mins END), 1) AS avg_ticket_when_issue,
        ROUND(AVG(CASE WHEN has_long_production = 0 THEN ticket_time_mins END), 1) AS avg_ticket_no_issue
      FROM late_orders
      
      UNION ALL SELECT 'Long Queue (>= 5 min in queue)' AS reason_code,
        'Capacity/Ops' AS owner, 'Capacity' AS category,
        SUM(has_long_queue), (SELECT SUM(has_long_queue) FROM order_flags_with_sequencer),
        (SELECT SUM(has_long_queue) FROM kitchen_late),
        COUNT(*), (SELECT COUNT(*) FROM order_flags_with_sequencer), (SELECT COUNT(*) FROM kitchen_late),
        ROUND(AVG(CASE WHEN has_long_queue = 1 THEN actual_queue_mins END), 1),
        ROUND(AVG(CASE WHEN has_long_queue = 0 THEN actual_queue_mins END), 1)
      FROM late_orders
      
      UNION ALL SELECT 'Long Pending Packaging (>= 5 min at expo)' AS reason_code,
        'Expo/Ops' AS owner, 'Ops' AS category,
        SUM(has_long_pending_packaging), (SELECT SUM(has_long_pending_packaging) FROM order_flags_with_sequencer),
        (SELECT SUM(has_long_pending_packaging) FROM kitchen_late),
        COUNT(*), (SELECT COUNT(*) FROM order_flags_with_sequencer), (SELECT COUNT(*) FROM kitchen_late),
        NULL, NULL
      FROM late_orders
      
      UNION ALL SELECT 'Force Complete (Any)' AS reason_code,
        'Training' AS owner, 'Workflow' AS category,
        SUM(has_force_complete), (SELECT SUM(has_force_complete) FROM order_flags_with_sequencer),
        (SELECT SUM(has_force_complete) FROM kitchen_late),
        COUNT(*), (SELECT COUNT(*) FROM order_flags_with_sequencer), (SELECT COUNT(*) FROM kitchen_late),
        ROUND(AVG(CASE WHEN has_force_complete = 1 THEN kitchen_handoff_time_mins END), 1),
        ROUND(AVG(CASE WHEN has_force_complete = 0 THEN kitchen_handoff_time_mins END), 1)
      FROM late_orders
      
      UNION ALL SELECT 'Premature Force Complete' AS reason_code,
        'Training' AS owner, 'Workflow' AS category,
        SUM(has_premature_fc), (SELECT SUM(has_premature_fc) FROM order_flags_with_sequencer),
        (SELECT SUM(has_premature_fc) FROM kitchen_late),
        COUNT(*), (SELECT COUNT(*) FROM order_flags_with_sequencer), (SELECT COUNT(*) FROM kitchen_late),
        NULL, NULL
      FROM late_orders
      
      UNION ALL SELECT 'Critical Force Complete (Very Early)' AS reason_code,
        'Training' AS owner, 'Workflow' AS category,
        SUM(has_critical_fc), (SELECT SUM(has_critical_fc) FROM order_flags_with_sequencer),
        (SELECT SUM(has_critical_fc) FROM kitchen_late),
        COUNT(*), (SELECT COUNT(*) FROM order_flags_with_sequencer), (SELECT COUNT(*) FROM kitchen_late),
        NULL, NULL
      FROM late_orders
      
      -- Sequencer Actual Issue: Only flag if expo wait > cook time variance on low-complexity orders
      UNION ALL SELECT '⚠️ Sequencer Issue (Expo Wait > Variance)' AS reason_code,
        'Sequencer/Product' AS owner, 'Sequencer' AS category,
        SUM(sequencer_actual_issue), (SELECT SUM(sequencer_actual_issue) FROM order_flags_with_sequencer),
        (SELECT SUM(sequencer_actual_issue) FROM kitchen_late),
        COUNT(*), (SELECT COUNT(*) FROM order_flags_with_sequencer), (SELECT COUNT(*) FROM kitchen_late),
        NULL, NULL
      FROM late_orders
      
      UNION ALL SELECT 'Bad Interaction (Sequencer flag)' AS reason_code,
        'Sequencer/Product' AS owner, 'Sequencer' AS category,
        SUM(has_bad_interaction), (SELECT SUM(has_bad_interaction) FROM order_flags_with_sequencer),
        (SELECT SUM(has_bad_interaction) FROM kitchen_late),
        COUNT(*), (SELECT COUNT(*) FROM order_flags_with_sequencer), (SELECT COUNT(*) FROM kitchen_late),
        NULL, NULL
      FROM late_orders
      
      UNION ALL SELECT 'Trickling Violation (FIFO broken)' AS reason_code,
        'Sequencer/Product' AS owner, 'Sequencer' AS category,
        SUM(has_trickling), (SELECT SUM(has_trickling) FROM order_flags_with_sequencer),
        (SELECT SUM(has_trickling) FROM kitchen_late),
        COUNT(*), (SELECT COUNT(*) FROM order_flags_with_sequencer), (SELECT COUNT(*) FROM kitchen_late),
        NULL, NULL
      FROM late_orders
      
      UNION ALL SELECT 'Double Delay' AS reason_code,
        'Sequencer/Product' AS owner, 'Sequencer' AS category,
        SUM(has_double_delay), (SELECT SUM(has_double_delay) FROM order_flags_with_sequencer),
        (SELECT SUM(has_double_delay) FROM kitchen_late),
        COUNT(*), (SELECT COUNT(*) FROM order_flags_with_sequencer), (SELECT COUNT(*) FROM kitchen_late),
        NULL, NULL
      FROM late_orders
      
      UNION ALL SELECT 'A La Minute Item' AS reason_code,
        'Menu/Culinary' AS owner, 'Menu' AS category,
        SUM(has_alm_item), (SELECT SUM(has_alm_item) FROM order_flags_with_sequencer),
        (SELECT SUM(has_alm_item) FROM kitchen_late),
        COUNT(*), (SELECT COUNT(*) FROM order_flags_with_sequencer), (SELECT COUNT(*) FROM kitchen_late),
        NULL, NULL
      FROM late_orders
      
      UNION ALL SELECT 'Sequencer Delay Applied' AS reason_code,
        'Sequencer/Product' AS owner, 'Sequencer' AS category,
        SUM(has_sequencer_delay), (SELECT SUM(has_sequencer_delay) FROM order_flags_with_sequencer),
        (SELECT SUM(has_sequencer_delay) FROM kitchen_late),
        COUNT(*), (SELECT COUNT(*) FROM order_flags_with_sequencer), (SELECT COUNT(*) FROM kitchen_late),
        NULL, NULL
      FROM late_orders
      
      UNION ALL SELECT 'Missing Pouch (Hot Hold)' AS reason_code,
        'Inventory/Ops' AS owner, 'HotHold' AS category,
        SUM(has_missing_pouch), (SELECT SUM(has_missing_pouch) FROM order_flags_with_sequencer),
        (SELECT SUM(has_missing_pouch) FROM kitchen_late),
        COUNT(*), (SELECT COUNT(*) FROM order_flags_with_sequencer), (SELECT COUNT(*) FROM kitchen_late),
        NULL, NULL
      FROM late_orders
      
      UNION ALL SELECT 'Surprise Pouch (Hot Hold)' AS reason_code,
        'Inventory/Ops' AS owner, 'HotHold' AS category,
        SUM(has_surprise_pouch), (SELECT SUM(has_surprise_pouch) FROM order_flags_with_sequencer),
        (SELECT SUM(has_surprise_pouch) FROM kitchen_late),
        COUNT(*), (SELECT COUNT(*) FROM order_flags_with_sequencer), (SELECT COUNT(*) FROM kitchen_late),
        NULL, NULL
      FROM late_orders
      
      UNION ALL SELECT 'KDS Remake' AS reason_code,
        'Kitchen Ops' AS owner, 'Ops' AS category,
        SUM(has_kds_remake), (SELECT SUM(has_kds_remake) FROM order_flags_with_sequencer),
        (SELECT SUM(has_kds_remake) FROM kitchen_late),
        COUNT(*), (SELECT COUNT(*) FROM order_flags_with_sequencer), (SELECT COUNT(*) FROM kitchen_late),
        NULL, NULL
      FROM late_orders
      
      UNION ALL SELECT 'Item Bumped Back' AS reason_code,
        'Kitchen Ops' AS owner, 'Ops' AS category,
        SUM(has_bump), (SELECT SUM(has_bump) FROM order_flags_with_sequencer),
        (SELECT SUM(has_bump) FROM kitchen_late),
        COUNT(*), (SELECT COUNT(*) FROM order_flags_with_sequencer), (SELECT COUNT(*) FROM kitchen_late),
        NULL, NULL
      FROM late_orders
      
      UNION ALL SELECT 'Timer Reset' AS reason_code,
        'Kitchen Ops' AS owner, 'Ops' AS category,
        SUM(has_reset), (SELECT SUM(has_reset) FROM order_flags_with_sequencer),
        (SELECT SUM(has_reset) FROM kitchen_late),
        COUNT(*), (SELECT COUNT(*) FROM order_flags_with_sequencer), (SELECT COUNT(*) FROM kitchen_late),
        NULL, NULL
      FROM late_orders
      
      UNION ALL SELECT 'Missing Signal (Tracking failure)' AS reason_code,
        'KDS/Tech' AS owner, 'Tech' AS category,
        SUM(has_missing_signal), (SELECT SUM(has_missing_signal) FROM order_flags_with_sequencer),
        (SELECT SUM(has_missing_signal) FROM kitchen_late),
        COUNT(*), (SELECT COUNT(*) FROM order_flags_with_sequencer), (SELECT COUNT(*) FROM kitchen_late),
        NULL, NULL
      FROM late_orders
    )
    SELECT
      reason_code,
      owner,
      category,
      late_count,
      total_late,
      ROUND(SAFE_DIVIDE(late_count, total_late) * 100, 1) AS pct_of_late,
      all_count,
      total_all,
      ROUND(SAFE_DIVIDE(all_count, total_all) * 100, 1) AS pct_of_all,
      ROUND(SAFE_DIVIDE(late_count, total_late) * 100 - SAFE_DIVIDE(all_count, total_all) * 100, 1) AS enrichment,
      kitchen_late_count,
      total_kitchen_late,
      ROUND(SAFE_DIVIDE(kitchen_late_count, total_kitchen_late) * 100, 1) AS pct_of_kitchen_late,
      avg_ticket_when_issue,
      avg_ticket_no_issue
    FROM reason_counts
    WHERE late_count > 0
    ORDER BY pct_of_late DESC
    """
    
    return run_bq_query(query)


def get_network_summary(weeks: int = DEFAULT_WEEKS) -> list[dict]:
    """Get network-wide weekly summary."""
    
    query = f"""
    SELECT
      FORMAT_DATE('%F', DATE_TRUNC(o.service_date_et, WEEK(MONDAY))) AS service_week,
      h.population_type,
      
      -- Volume
      COUNT(DISTINCT o.order_id) AS total_orders,
      COUNT(DISTINCT CASE WHEN o.order_channel IN ('APP','WEB','IN_PERSON') THEN o.order_id END) AS orders_1p,
      COUNT(DISTINCT CASE WHEN o.dining_option = 'DELIVERY' THEN o.order_id END) AS delivery_orders,
      COUNT(DISTINCT CASE WHEN o.dining_option = 'PICKUP' THEN o.order_id END) AS pickup_orders,
      
      -- OTR using imperfect_orders.on_time_issue (correct method)
      ROUND((1 - SAFE_DIVIDE(
        COUNT(DISTINCT CASE WHEN o.order_channel IN ('APP','WEB','IN_PERSON') AND io.on_time_issue THEN o.order_id END),
        COUNT(DISTINCT CASE WHEN o.order_channel IN ('APP','WEB','IN_PERSON') THEN o.order_id END)
      )) * 100, 1) AS otr_1p,
      ROUND((1 - SAFE_DIVIDE(
        COUNT(DISTINCT CASE WHEN o.dining_option = 'DELIVERY' AND o.order_channel IN ('APP','WEB','IN_PERSON') AND io.on_time_issue THEN o.order_id END),
        COUNT(DISTINCT CASE WHEN o.dining_option = 'DELIVERY' AND o.order_channel IN ('APP','WEB','IN_PERSON') THEN o.order_id END)
      )) * 100, 1) AS otr_delivery,
      ROUND((1 - SAFE_DIVIDE(
        COUNT(DISTINCT CASE WHEN o.dining_option = 'PICKUP' AND o.order_channel IN ('APP','WEB','IN_PERSON') AND io.on_time_issue THEN o.order_id END),
        COUNT(DISTINCT CASE WHEN o.dining_option = 'PICKUP' AND o.order_channel IN ('APP','WEB','IN_PERSON') THEN o.order_id END)
      )) * 100, 1) AS otr_pickup,
      ROUND(AVG(CASE WHEN o.ready_for_pickup_sla_difference <= 2 THEN 1 ELSE 0 END) * 100, 1) AS kitchen_otr,
      
      -- Timing
      ROUND(AVG(o.ticket_time_mins), 1) AS avg_ticket_time,
      ROUND(AVG(o.actual_pickup_waiting_duration_mins), 1) AS avg_expo_wait,
      ROUND(AVG(o.courier_response_time_mins), 1) AS avg_courier_response,
      ROUND(AVG(o.kitchen_handoff_time_mins), 1) AS avg_handoff
      
    FROM `wonder-dw-prod-brd.orders.hdr_orders` o
    JOIN `wonder-dw-prod-brd.dw.dim_hdrs` h ON o.hdr_id = h.hdr_id
    LEFT JOIN `wonder-dw-prod-brd.orders.imperfect_orders` io ON o.order_id = io.order_id
    WHERE o.order_status = 'COMPLETE'
      AND o.brand_category = 'WONDER_HDR'
      AND (o.order_business_type <> 'WONDER_SPOT' OR o.order_business_type IS NULL)
      AND (o.order_business_type <> '3P_PLATFORM_CORPORATE' OR o.order_business_type IS NULL)
      AND o.service_date_et >= DATE_TRUNC(DATE_SUB(CURRENT_DATE('America/New_York'), INTERVAL {weeks + 1} WEEK), WEEK(MONDAY))
      AND o.service_date_et < DATE_TRUNC(CURRENT_DATE('America/New_York'), WEEK(MONDAY))
    GROUP BY 1, 2
    ORDER BY service_week DESC, population_type
    """
    
    return run_bq_query(query)


def get_problem_locations(weeks: int = 2) -> dict:
    """Identify Profile A and Profile B locations."""
    
    # Profile A: Ops Failures (fast courier, slow handoff)
    profile_a_query = f"""
    SELECT
      h.hdr_name,
      h.population_type,
      COUNT(DISTINCT o.order_id) AS orders,
      ROUND(AVG(o.courier_response_time_mins), 1) AS avg_courier_response,
      ROUND(AVG(o.kitchen_handoff_time_mins), 1) AS avg_handoff,
      ROUND(AVG(o.kitchen_handoff_time_mins) - AVG(o.courier_response_time_mins), 1) AS ops_gap,
      ROUND(AVG(CASE WHEN o.delivery_sla_difference BETWEEN -8.99 AND 0.99 THEN 1 ELSE 0 END) * 100, 1) AS otr
    FROM `wonder-dw-prod-brd.orders.hdr_orders` o
    JOIN `wonder-dw-prod-brd.dw.dim_hdrs` h ON o.hdr_id = h.hdr_id
    WHERE o.order_status = 'COMPLETE'
      AND o.brand_category = 'WONDER_HDR'
      AND o.dining_option = 'DELIVERY'
      AND o.order_channel IN ('APP', 'WEB', 'IN_PERSON')
      AND (o.order_business_type <> 'WONDER_SPOT' OR o.order_business_type IS NULL)
      AND o.service_date_et >= DATE_SUB(CURRENT_DATE('America/New_York'), INTERVAL {weeks} WEEK)
      AND o.service_date_et < CURRENT_DATE('America/New_York')
    GROUP BY 1, 2
    HAVING AVG(o.courier_response_time_mins) <= 5 AND AVG(o.kitchen_handoff_time_mins) > 6
    ORDER BY ops_gap DESC
    LIMIT 10
    """
    
    # Profile B: Logistics Failures (fast handoff, slow courier)
    profile_b_query = f"""
    SELECT
      h.hdr_name,
      h.population_type,
      COUNT(DISTINCT o.order_id) AS orders,
      ROUND(AVG(o.courier_response_time_mins), 1) AS avg_courier_response,
      ROUND(AVG(o.kitchen_handoff_time_mins), 1) AS avg_handoff,
      ROUND(AVG(o.courier_response_time_mins) - AVG(o.kitchen_handoff_time_mins), 1) AS logistics_gap,
      ROUND(AVG(CASE WHEN o.delivery_sla_difference BETWEEN -8.99 AND 0.99 THEN 1 ELSE 0 END) * 100, 1) AS otr
    FROM `wonder-dw-prod-brd.orders.hdr_orders` o
    JOIN `wonder-dw-prod-brd.dw.dim_hdrs` h ON o.hdr_id = h.hdr_id
    WHERE o.order_status = 'COMPLETE'
      AND o.brand_category = 'WONDER_HDR'
      AND o.dining_option = 'DELIVERY'
      AND o.order_channel IN ('APP', 'WEB', 'IN_PERSON')
      AND (o.order_business_type <> 'WONDER_SPOT' OR o.order_business_type IS NULL)
      AND o.service_date_et >= DATE_SUB(CURRENT_DATE('America/New_York'), INTERVAL {weeks} WEEK)
      AND o.service_date_et < CURRENT_DATE('America/New_York')
    GROUP BY 1, 2
    HAVING AVG(o.courier_response_time_mins) > 12 AND AVG(o.kitchen_handoff_time_mins) <= 5
    ORDER BY logistics_gap DESC
    LIMIT 10
    """
    
    return {
        'profile_a': run_bq_query(profile_a_query),
        'profile_b': run_bq_query(profile_b_query)
    }


def get_order_details(order_number: str) -> dict:
    """Get detailed order-level analysis."""
    
    query = f"""
    SELECT
      o.order_id,
      o.order_number,
      h.hdr_name,
      h.population_type,
      h.hdr_class,
      o.service_date_et,
      o.dining_option,
      o.order_channel,
      o.order_status,
      
      -- SLA
      ROUND(o.delivery_sla_difference, 2) AS delivery_sla_diff,
      ROUND(o.ready_for_pickup_sla_difference, 2) AS kitchen_sla_diff,
      CASE 
        WHEN o.delivery_sla_difference BETWEEN -8.99 AND 0.99 THEN 'ON_TIME'
        WHEN o.delivery_sla_difference < -8.99 THEN 'EARLY'
        ELSE 'LATE'
      END AS otr_status,
      
      -- Timing
      ROUND(o.ticket_time_mins, 1) AS ticket_time,
      ROUND(o.actual_pickup_waiting_duration_mins, 1) AS expo_wait,
      ROUND(o.courier_response_time_mins, 1) AS courier_response,
      ROUND(o.kitchen_handoff_time_mins, 1) AS handoff,
      ROUND(o.actual_transit_mins, 1) AS transit,
      ROUND(o.actual_o2e_mins, 1) AS o2e,
      
      -- Estimated
      ROUND(o.estimated_queue_mins, 1) AS est_queue,
      ROUND(o.estimated_cook_duration_mins, 1) AS est_cook,
      ROUND(o.estimated_packaging_bagging_mins, 1) AS est_pack,
      
      -- Actual
      ROUND(o.actual_queue_mins, 1) AS actual_queue,
      ROUND(o.actual_cook_duration_mins, 1) AS actual_cook,
      ROUND(o.actual_packaging_bagging_mins, 1) AS actual_pack,
      
      -- Variance
      ROUND(o.actual_queue_mins - o.estimated_queue_mins, 1) AS queue_var,
      ROUND(o.actual_cook_duration_mins - o.estimated_cook_duration_mins, 1) AS cook_var,
      ROUND(o.actual_packaging_bagging_mins - o.estimated_packaging_bagging_mins, 1) AS pack_var,
      
      -- Items
      o.items_per_check
      
    FROM `wonder-dw-prod-brd.orders.hdr_orders` o
    JOIN `wonder-dw-prod-brd.dw.dim_hdrs` h ON o.hdr_id = h.hdr_id
    WHERE o.order_number = '{order_number}'
       OR o.order_id = '{order_number}'
    """
    
    results = run_bq_query(query)
    return results[0] if results else None


def get_order_imperfections(order_id: str) -> list[dict]:
    """Get imperfect kitchen items for an order."""
    
    query = f"""
    SELECT
      menu_item_name,
      has_kds_remake,
      has_bump,
      has_force_progression,
      has_premature_force_complete,
      has_critical_force_complete,
      has_long_queue,
      has_long_pending_packaging,
      has_shorter_than_expected_production_time,
      has_longer_than_expected_production_time,
      has_bad_interaction,
      has_double_delay,
      has_trickling_violation,
      has_missing_pouch,
      has_surprise_pouch,
      force_complete_severity_tier
    FROM `wonder-dw-prod-brd.orders.imperfect_kitchen_items`
    WHERE order_id = '{order_id}'
    """
    
    return run_bq_query(query)


def generate_html_report(data: dict, report_type: str) -> str:
    """Generate the HTML report."""
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OTR Insights - {data.get('title', 'Report')}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        :root {{
            --pesto: #00462A;
            --romaine: #078F45;
            --snap-pea: #6FD172;
            --cucumber: #CCF4CD;
            --feta: #FAF5EE;
            --popsicle: #37BC96;
            --marmalade: #FF5600;
            --couscous: #FED026;
            --pomodoro: #E2003F;
            --butternut: #FF9846;
            
            --bg-primary: var(--pesto);
            --bg-secondary: #003D25;
            --bg-tertiary: #005535;
            --text-primary: var(--feta);
            --text-secondary: var(--cucumber);
            --border-color: var(--romaine);
        }}
        
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        
        body {{
            font-family: 'SF Mono', 'Fira Code', monospace;
            background: var(--bg-primary);
            color: var(--text-primary);
            line-height: 1.6;
            padding: 2rem;
        }}
        
        .container {{ max-width: 1400px; margin: 0 auto; }}
        
        header {{
            text-align: center;
            padding-bottom: 1.5rem;
            border-bottom: 2px solid var(--border-color);
            margin-bottom: 2rem;
        }}
        
        h1 {{
            font-size: 2rem;
            background: linear-gradient(135deg, var(--snap-pea), var(--popsicle));
            -webkit-background-clip: text;
            background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        
        .subtitle {{ color: var(--text-secondary); font-size: 0.9rem; }}
        .generated {{ color: var(--text-secondary); font-size: 0.8rem; margin-top: 0.5rem; }}
        
        .section {{
            background: var(--bg-secondary);
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
            border: 1px solid var(--border-color);
        }}
        
        .section-title {{
            font-size: 1.1rem;
            color: var(--snap-pea);
            margin-bottom: 1rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}
        
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 1rem;
        }}
        
        .metric {{
            background: var(--bg-tertiary);
            padding: 1rem;
            border-radius: 8px;
            text-align: center;
        }}
        
        .metric-value {{
            font-size: 1.8rem;
            font-weight: 700;
            color: var(--popsicle);
        }}
        
        .metric-value.good {{ color: var(--snap-pea); }}
        .metric-value.warning {{ color: var(--butternut); }}
        .metric-value.critical {{ color: var(--pomodoro); }}
        
        .metric-label {{
            font-size: 0.75rem;
            color: var(--text-secondary);
            text-transform: uppercase;
            margin-top: 0.25rem;
        }}
        
        .metric-delta {{
            font-size: 0.85rem;
            margin-top: 0.25rem;
        }}
        
        .delta-positive {{ color: var(--snap-pea); }}
        .delta-negative {{ color: var(--pomodoro); }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.85rem;
        }}
        
        th, td {{
            padding: 0.75rem;
            text-align: left;
            border-bottom: 1px solid var(--border-color);
        }}
        
        th {{
            color: var(--text-secondary);
            font-weight: 500;
            text-transform: uppercase;
            font-size: 0.75rem;
        }}
        
        tr:hover {{ background: var(--bg-tertiary); }}
        
        .rec-block {{
            padding: 1rem;
            border-radius: 8px;
            margin-bottom: 1rem;
            border-left: 4px solid;
        }}
        
        .rec-critical {{
            background: rgba(226, 0, 63, 0.1);
            border-color: var(--pomodoro);
        }}
        
        .rec-warning {{
            background: rgba(255, 152, 70, 0.1);
            border-color: var(--butternut);
        }}
        
        .rec-success {{
            background: rgba(111, 209, 114, 0.1);
            border-color: var(--snap-pea);
        }}
        
        .rec-info {{
            background: rgba(55, 188, 150, 0.1);
            border-color: var(--popsicle);
        }}
        
        .rec-block h4 {{ margin-bottom: 0.5rem; }}
        
        .rec-action {{
            background: var(--bg-tertiary);
            padding: 0.5rem;
            border-radius: 4px;
            margin-top: 0.5rem;
        }}
        
        .chart-container {{
            height: 300px;
            margin: 1rem 0;
        }}
        
        .badge {{
            display: inline-block;
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: 600;
        }}
        
        .badge-good {{ background: var(--snap-pea); color: var(--pesto); }}
        .badge-warning {{ background: var(--butternut); color: var(--pesto); }}
        .badge-critical {{ background: var(--pomodoro); color: white; }}
        
        .two-col {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1.5rem;
        }}
        
        @media (max-width: 768px) {{
            .two-col {{ grid-template-columns: 1fr; }}
        }}
        
        .collapsible {{
            cursor: pointer;
            user-select: none;
        }}
        
        .collapsible::after {{
            content: ' ▼';
            font-size: 0.8rem;
        }}
        
        .collapsible.collapsed::after {{
            content: ' ▶';
        }}
        
        .collapse-content {{
            overflow: hidden;
            transition: max-height 0.3s ease;
        }}
        
        .collapse-content.collapsed {{
            max-height: 0;
            padding: 0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📊 OTR Insights Report</h1>
            <p class="subtitle">{data.get('title', 'Analysis')}</p>
            <p class="generated">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M ET')}</p>
        </header>
        
        {data.get('content', '')}
    </div>
    
    <script>
        // Collapsible sections
        document.querySelectorAll('.collapsible').forEach(el => {{
            el.addEventListener('click', () => {{
                el.classList.toggle('collapsed');
                const content = el.nextElementSibling;
                if (content) content.classList.toggle('collapsed');
            }});
        }});
    </script>
</body>
</html>"""
    
    return html


def generate_hdr_report(hdr_name: str, weeks: int) -> str:
    """Generate HDR-level report."""
    
    print(f"Fetching data for HDR: {hdr_name}...")
    
    metrics = get_hdr_metrics(hdr_name, weeks)
    scenarios = get_hdr_scenario_breakdown(hdr_name, weeks)
    production_variance = get_production_variance_by_pod(hdr_name, 2)  # Last 2 weeks
    reason_codes = get_reason_code_breakdown(hdr_name, 2)
    ranked_reasons = get_late_order_ranked_reasons(hdr_name, 2)  # Ranked reasons for late orders
    error_decomp = get_late_order_error_decomposition(hdr_name, 2)  # Error decomposition by pickup scenario
    
    if not metrics:
        return f"No data found for HDR matching '{hdr_name}'"
    
    # Get the most recent week's data
    current = metrics[0] if metrics else {}
    prev = metrics[1] if len(metrics) > 1 else {}
    
    # Calculate WoW changes
    def calc_delta(curr_val, prev_val):
        if curr_val is None or prev_val is None:
            return None
        try:
            return float(curr_val) - float(prev_val)
        except:
            return None
    
    otr_delta = calc_delta(current.get('otr_1p'), prev.get('otr_1p'))
    kitchen_delta = calc_delta(current.get('kitchen_otr'), prev.get('kitchen_otr'))
    ticket_delta = calc_delta(current.get('avg_ticket_time'), prev.get('avg_ticket_time'))
    
    # Build content
    content = f"""
    <!-- Executive Summary -->
    <div class="section">
        <h2 class="section-title">📈 Executive Summary - {current.get('hdr_name', hdr_name)}</h2>
        <div class="metrics-grid">
            <div class="metric">
                <div class="metric-value {'good' if float(current.get('otr_1p', 0)) >= 90 else 'warning' if float(current.get('otr_1p', 0)) >= 85 else 'critical'}">{current.get('otr_1p', 'N/A')}%</div>
                <div class="metric-label">1P OTR</div>
                {f'<div class="metric-delta {"delta-positive" if otr_delta and otr_delta > 0 else "delta-negative"}">{otr_delta:+.1f} pts WoW</div>' if otr_delta else ''}
            </div>
            <div class="metric">
                <div class="metric-value">{current.get('kitchen_otr', 'N/A')}%</div>
                <div class="metric-label">Kitchen OTR</div>
                {f'<div class="metric-delta {"delta-positive" if kitchen_delta and kitchen_delta > 0 else "delta-negative"}">{kitchen_delta:+.1f} pts WoW</div>' if kitchen_delta else ''}
            </div>
            <div class="metric">
                <div class="metric-value">{current.get('avg_ticket_time', 'N/A')}m</div>
                <div class="metric-label">Avg Ticket Time</div>
                {f'<div class="metric-delta {"delta-negative" if ticket_delta and ticket_delta > 0 else "delta-positive"}">{ticket_delta:+.1f}m WoW</div>' if ticket_delta else ''}
            </div>
            <div class="metric">
                <div class="metric-value">{current.get('orders_1p', 'N/A')}</div>
                <div class="metric-label">1P Orders</div>
            </div>
            <div class="metric">
                <div class="metric-value">{current.get('otr_1p_delivery', 'N/A')}%</div>
                <div class="metric-label">Delivery OTR</div>
            </div>
            <div class="metric">
                <div class="metric-value">{current.get('otr_1p_pickup', 'N/A')}%</div>
                <div class="metric-label">Pickup OTR</div>
            </div>
        </div>
        
        <div style="margin-top: 1rem; color: var(--text-secondary); font-size: 0.85rem;">
            <strong>Context:</strong> {current.get('population_type', 'N/A')} | Class: {current.get('hdr_class', 'N/A')} | {current.get('weeks_open', 'N/A')} weeks open
        </div>
    </div>
    """
    
    # Recommendations based on data
    content += """<div class="section"><h2 class="section-title">💡 Recommendations</h2>"""
    
    handoff = float(current.get('avg_handoff', 0) or 0)
    courier = float(current.get('avg_courier_response', 0) or 0)
    profile_a_pct = float(current.get('pct_profile_a', 0) or 0)
    profile_b_pct = float(current.get('pct_profile_b', 0) or 0)
    
    # Force Complete metrics
    pct_fc = float(current.get('pct_force_complete', 0) or 0)
    pct_premature_fc = float(current.get('pct_premature_fc', 0) or 0)
    pct_critical_fc = float(current.get('pct_critical_fc', 0) or 0)
    pct_fc_slow_handoff = float(current.get('pct_fc_slow_handoff', 0) or 0)
    handoff_fc = float(current.get('avg_handoff_fc_orders', 0) or 0)
    handoff_non_fc = float(current.get('avg_handoff_non_fc_orders', 0) or 0)
    handoff_gap = handoff_fc - handoff_non_fc if handoff_fc and handoff_non_fc else 0
    
    if profile_a_pct > 10:
        # Check if force complete is contributing to Profile A
        fc_context = ""
        if pct_fc > 15 and handoff_gap > 2:
            fc_context = f" <strong>Force Complete Correlation:</strong> {pct_fc:.1f}% of orders have force complete, and FC orders have {handoff_gap:.1f}m LONGER handoff than non-FC orders. This strongly suggests fake bumping."
        content += f"""
        <div class="rec-block rec-critical">
            <h4>🔴 Profile A: Ops Failure Detected ({profile_a_pct:.1f}% of delivery orders)</h4>
            <p>Drivers arrive quickly ({courier:.1f}m) but food sits in-store for {handoff:.1f}m. This suggests expo bottleneck or "fake bumping".{fc_context}</p>
            <div class="rec-action">⚡ <strong>Action:</strong> Audit KDS procedures. Stop pre-bumping. Review expo station staffing.</div>
        </div>
        """
    
    if profile_b_pct > 5:
        content += f"""
        <div class="rec-block rec-warning">
            <h4>🟠 Profile B: Logistics Failure Detected ({profile_b_pct:.1f}% of delivery orders)</h4>
            <p>Kitchen is fast (handoff {handoff:.1f}m) but drivers take {courier:.1f}m to arrive. Food is sitting ready with no courier.</p>
            <div class="rec-action">⚡ <strong>Action:</strong> Review courier incentives. Adjust dispatch radius for this zone.</div>
        </div>
        """
    
    # Force Complete Analysis (independent of Profile A/B)
    if pct_fc > 20 or pct_premature_fc > 10 or pct_critical_fc > 5:
        severity = "critical" if pct_critical_fc > 5 else "warning"
        content += f"""
        <div class="rec-block rec-{severity}">
            <h4>{'🔴' if severity == 'critical' else '🟠'} High Force Complete Rate</h4>
            <p>
                <strong>{pct_fc:.1f}%</strong> of orders have force complete 
                ({pct_premature_fc:.1f}% premature, {pct_critical_fc:.1f}% critical).
            </p>
            <p>
                <strong>Handoff Impact:</strong> FC orders avg {handoff_fc:.1f}m handoff vs {handoff_non_fc:.1f}m for non-FC 
                (gap: <span class="{'delta-negative' if handoff_gap > 2 else ''}">{handoff_gap:+.1f}m</span>)
            </p>
            <div class="rec-action">⚡ <strong>Action:</strong> {'URGENT: ' if severity == 'critical' else ''}Review KDS training. Staff may be bumping orders before food is ready to meet make-time targets.</div>
        </div>
        """
    elif pct_fc_slow_handoff > 5:
        content += f"""
        <div class="rec-block rec-warning">
            <h4>🟠 Force Complete + Slow Handoff Pattern</h4>
            <p>{pct_fc_slow_handoff:.1f}% of delivery orders have BOTH force complete AND slow handoff (>5m). This is a fake bump signal.</p>
            <div class="rec-action">⚡ <strong>Action:</strong> Audit specific orders with FC + slow handoff to identify culprits.</div>
        </div>
        """
    
    kitchen_otr = float(current.get('kitchen_otr', 100))
    customer_otr = float(current.get('otr_1p', 100))
    
    if kitchen_otr > 60 and customer_otr < 85:
        content += f"""
        <div class="rec-block rec-info">
            <h4>📊 Kitchen is Performing, Delivery Execution Failing</h4>
            <p>Kitchen OTR ({kitchen_otr:.1f}%) is solid, but Customer OTR ({customer_otr:.1f}%) is lagging. The gap is in post-kitchen execution (handoff + logistics).</p>
            <div class="rec-action">⚡ <strong>Action:</strong> Focus on sit time reduction, not kitchen speed.</div>
        </div>
        """
    elif kitchen_otr < 55:
        content += f"""
        <div class="rec-block rec-critical">
            <h4>🔴 Kitchen Speed Issue</h4>
            <p>Kitchen OTR at {kitchen_otr:.1f}% indicates the kitchen is the primary bottleneck.</p>
            <div class="rec-action">⚡ <strong>Action:</strong> Review ticket time breakdown. Check queue and cook variances.</div>
        </div>
        """
    
    has_issues = (profile_a_pct > 10 or profile_b_pct > 5 or kitchen_otr < 55 or customer_otr < 85 
                  or pct_fc > 20 or pct_premature_fc > 10 or pct_critical_fc > 5 or pct_fc_slow_handoff > 5)
    if not has_issues:
        content += """
        <div class="rec-block rec-success">
            <h4>✅ No Critical Issues Detected</h4>
            <p>This HDR is performing within acceptable parameters. Continue monitoring.</p>
        </div>
        """
    
    content += "</div>"
    
    # Force Complete Details Section
    content += f"""
    <div class="section">
        <h2 class="section-title collapsible">🔧 Force Complete Analysis</h2>
        <div class="collapse-content">
            <div class="metrics-grid">
                <div class="metric">
                    <div class="metric-value {'critical' if pct_fc > 25 else 'warning' if pct_fc > 15 else ''}">{pct_fc:.1f}%</div>
                    <div class="metric-label">Any Force Complete</div>
                </div>
                <div class="metric">
                    <div class="metric-value {'warning' if pct_premature_fc > 10 else ''}">{pct_premature_fc:.1f}%</div>
                    <div class="metric-label">Premature FC</div>
                </div>
                <div class="metric">
                    <div class="metric-value {'critical' if pct_critical_fc > 5 else ''}">{pct_critical_fc:.1f}%</div>
                    <div class="metric-label">Critical FC</div>
                </div>
                <div class="metric">
                    <div class="metric-value {'critical' if pct_fc_slow_handoff > 10 else 'warning' if pct_fc_slow_handoff > 5 else ''}">{pct_fc_slow_handoff:.1f}%</div>
                    <div class="metric-label">FC + Slow Handoff</div>
                </div>
            </div>
            
            <div style="margin-top: 1.5rem;">
                <h4 style="color: var(--snap-pea); margin-bottom: 1rem;">Handoff Time: FC vs Non-FC Orders</h4>
                <table>
                    <tr><th>Order Type</th><th>Avg Handoff</th><th>Impact</th></tr>
                    <tr>
                        <td>Force Complete Orders</td>
                        <td class="{'delta-negative' if handoff_fc > 5 else ''}">{handoff_fc:.1f}m</td>
                        <td rowspan="2" style="text-align: center; font-size: 1.2rem; {'color: var(--pomodoro)' if handoff_gap > 3 else ''}">
                            {'+' if handoff_gap > 0 else ''}{handoff_gap:.1f}m gap
                        </td>
                    </tr>
                    <tr>
                        <td>Non-Force Complete Orders</td>
                        <td>{handoff_non_fc:.1f}m</td>
                    </tr>
                </table>
                <p style="margin-top: 1rem; font-size: 0.85rem; color: var(--text-secondary);">
                    <strong>Interpretation:</strong> 
                    {'A large positive gap suggests FC orders are "fake bumped" - marked ready before food is actually complete.' if handoff_gap > 2 else 'Handoff times are similar regardless of FC status - FC is likely due to system/workflow issues, not fake bumping.'}
                </p>
            </div>
        </div>
    </div>
    """
    
    # Production Variance by Pod/Restaurant Section
    if production_variance:
        content += """
    <div class="section">
        <h2 class="section-title collapsible">🍳 Production Variance by Pod & Restaurant</h2>
        <div class="collapse-content">
            <p style="margin-bottom: 1rem; color: var(--text-secondary);">
                Which pods/restaurants are running over expected cook time and impacting OTR?
            </p>
            <table>
                <tr>
                    <th>Pod Type</th>
                    <th>Restaurant</th>
                    <th>Items</th>
                    <th>Expected</th>
                    <th>Actual</th>
                    <th>Variance</th>
                    <th>% Over</th>
                    <th>OTR</th>
                    <th>Var (Late)</th>
                </tr>
        """
        for pv in production_variance[:15]:  # Top 15 problem areas
            variance = float(pv.get('avg_variance', 0) or 0)
            pct_over = float(pv.get('pct_over_expected', 0) or 0)
            otr = float(pv.get('otr_pct', 0) or 0)
            var_late = float(pv.get('variance_when_late', 0) or 0)
            
            variance_class = 'delta-negative' if variance > 2 else 'delta-positive' if variance < -1 else ''
            otr_class = 'critical' if otr < 80 else 'warning' if otr < 90 else ''
            
            content += f"""
                <tr>
                    <td><strong>{pv.get('pod_type', 'N/A')}</strong></td>
                    <td>{pv.get('restaurant_name', 'N/A')[:25]}</td>
                    <td>{pv.get('item_count', 'N/A')}</td>
                    <td>{pv.get('avg_expected_cook', 'N/A')}m</td>
                    <td>{pv.get('avg_actual_cook', 'N/A')}m</td>
                    <td class="{variance_class}">{variance:+.1f}m</td>
                    <td class="{'delta-negative' if pct_over > 40 else ''}">{pct_over:.0f}%</td>
                    <td class="{otr_class}">{otr:.0f}%</td>
                    <td class="{'delta-negative' if var_late > 3 else ''}">{var_late:+.1f}m</td>
                </tr>
            """
        
        content += """
            </table>
            <p style="margin-top: 1rem; font-size: 0.85rem; color: var(--text-secondary);">
                <strong>Columns:</strong> Variance = Actual - Expected (positive = over). % Over = orders exceeding expected + 3min. 
                Var (Late) = avg variance for late orders only.
            </p>
        """
        
        # Identify worst offenders
        worst = [p for p in production_variance if float(p.get('avg_variance', 0) or 0) > 2 and float(p.get('pct_over_expected', 0) or 0) > 40]
        if worst:
            content += """
            <div class="rec-block rec-warning" style="margin-top: 1rem;">
                <h4>🔴 Production Variance Hotspots</h4>
                <p>These pod/restaurant combinations are consistently running over expected:</p>
                <ul style="margin-top: 0.5rem;">
            """
            for w in worst[:5]:
                content += f"""<li><strong>{w.get('pod_type')}</strong> / {w.get('restaurant_name', 'N/A')[:20]}: {float(w.get('avg_variance', 0)):+.1f}m avg variance, {w.get('pct_over_expected')}% over expected</li>"""
            content += """
                </ul>
                <div class="rec-action">⚡ <strong>Action:</strong> Review recipe timing for these items. Check equipment/staffing at these pods.</div>
            </div>
            """
        
        content += "</div></div>"
    
    # Reason Code Breakdown Section - Comprehensive
    if reason_codes:
        all_orders = next((r for r in reason_codes if r.get('segment') == 'All Orders'), {})
        late_orders = next((r for r in reason_codes if r.get('segment') == 'Late Orders'), {})
        kitchen_late = next((r for r in reason_codes if r.get('segment') == 'Kitchen Late (>2m)'), {})
        
        content += f"""
    <div class="section">
        <h2 class="section-title collapsible">📋 Reason Code Attribution (Summary)</h2>
        <div class="collapse-content">
            <p style="margin-bottom: 1rem; color: var(--text-secondary);">
                Comparing reason code prevalence across All Orders, Late Orders, and Kitchen Late orders.
            </p>
            <table>
                <tr>
                    <th>Reason Code</th>
                    <th>All Orders</th>
                    <th>Late Orders</th>
                    <th>Kitchen Late</th>
                    <th>Enrichment</th>
                    <th>Owner</th>
                </tr>
        """
        
        reason_codes_list = [
            ('Long Production', 'pct_long_production', 'Kitchen Ops'),
            ('Long Queue', 'pct_long_queue', 'Capacity'),
            ('Long Pending Packaging', 'pct_long_pending_packaging', 'Expo/Ops'),
            ('Force Complete (Any)', 'pct_force_complete', 'Training'),
            ('Premature Force Complete', 'pct_premature_fc', 'Training'),
            ('Critical Force Complete', 'pct_critical_fc', 'Training'),
            ('Bad Interaction', 'pct_bad_interaction', 'Sequencer'),
            ('Trickling', 'pct_trickling', 'Sequencer'),
            ('Double Delay', 'pct_double_delay', 'Sequencer'),
            ('ALM Items', 'pct_alm', 'Menu'),
            ('Sequencer Delay', 'pct_sequencer_delay', 'Sequencer'),
            ('Missing Pouch', 'pct_missing_pouch', 'Inventory'),
            ('Surprise Pouch', 'pct_surprise_pouch', 'Inventory'),
            ('KDS Remake', 'pct_kds_remake', 'Kitchen Ops'),
            ('Item Bumped', 'pct_bump', 'Kitchen Ops'),
        ]
        
        for name, field, owner in reason_codes_list:
            all_val = float(all_orders.get(field, 0) or 0)
            late_val = float(late_orders.get(field, 0) or 0)
            kitchen_late_val = float(kitchen_late.get(field, 0) or 0)
            enrichment = late_val - all_val
            
            enrich_class = 'delta-negative' if enrichment > 10 else 'delta-positive' if enrichment < 0 else ''
            late_class = 'delta-negative' if late_val > all_val + 15 else ''
            kitchen_class = 'delta-negative' if kitchen_late_val > late_val + 10 else ''
            
            content += f"""
                <tr>
                    <td><strong>{name}</strong></td>
                    <td>{all_val:.0f}%</td>
                    <td class="{late_class}">{late_val:.0f}%</td>
                    <td class="{kitchen_class}">{kitchen_late_val:.0f}%</td>
                    <td class="{enrich_class}">{enrichment:+.0f} pts</td>
                    <td style="font-size: 0.8rem; color: var(--text-secondary);">{owner}</td>
                </tr>
            """
        
        content += f"""
            </table>
            <p style="margin-top: 1rem; font-size: 0.85rem; color: var(--text-secondary);">
                <strong>Enrichment</strong> = Late % - All %. High positive = strongly predicts lateness. 
                <strong>Kitchen Late</strong> = Orders where ready_for_pickup was >2 min late.
            </p>
            <div style="margin-top: 1rem; display: flex; gap: 1rem; flex-wrap: wrap;">
                <div style="padding: 0.5rem 1rem; background: rgba(0,0,0,0.2); border-radius: 5px;">
                    <strong>All Orders:</strong> {int(all_orders.get('orders', 0) or 0):,}
                </div>
                <div style="padding: 0.5rem 1rem; background: rgba(255,86,0,0.2); border-radius: 5px;">
                    <strong>Late Orders:</strong> {int(late_orders.get('orders', 0) or 0):,}
                </div>
                <div style="padding: 0.5rem 1rem; background: rgba(226,0,63,0.2); border-radius: 5px;">
                    <strong>Kitchen Late:</strong> {int(kitchen_late.get('orders', 0) or 0):,}
                </div>
            </div>
        </div>
    </div>
        """
    
    # Ranked Late Order Reasons Section - The main recommendations
    if ranked_reasons:
        content += """
    <div class="section">
        <h2 class="section-title">🔴 Late Order Reasons (Ranked by Impact)</h2>
        <p style="margin-bottom: 1rem; color: var(--text-secondary);">
            All late orders broken down by reason code, sorted by frequency. Focus on the top items for maximum impact.
        </p>
        <table>
            <tr>
                <th>#</th>
                <th>Reason Code</th>
                <th>Late Orders</th>
                <th>% of Late</th>
                <th>% of All</th>
                <th>Enrichment</th>
                <th>Kitchen Late %</th>
                <th>Owner</th>
            </tr>
        """
        
        for i, r in enumerate(ranked_reasons, 1):
            pct_late = float(r.get('pct_of_late', 0) or 0)
            pct_all = float(r.get('pct_of_all', 0) or 0)
            enrichment = float(r.get('enrichment', 0) or 0)
            pct_kitchen = float(r.get('pct_of_kitchen_late', 0) or 0)
            late_count = int(r.get('late_count', 0) or 0)
            
            # Color coding
            rank_class = 'critical' if i <= 3 else 'warning' if i <= 6 else ''
            enrich_class = 'delta-negative' if enrichment > 10 else 'delta-positive' if enrichment < 0 else ''
            
            content += f"""
            <tr>
                <td><strong class="{rank_class}">{i}</strong></td>
                <td><strong>{r.get('reason_code', 'N/A')}</strong></td>
                <td>{late_count:,}</td>
                <td class="{rank_class}">{pct_late:.0f}%</td>
                <td>{pct_all:.0f}%</td>
                <td class="{enrich_class}">{enrichment:+.0f} pts</td>
                <td>{pct_kitchen:.0f}%</td>
                <td style="font-size: 0.8rem; color: var(--snap-pea);">{r.get('owner', 'N/A')}</td>
            </tr>
            """
        
        content += """
        </table>
        <p style="margin-top: 1rem; font-size: 0.85rem; color: var(--text-secondary);">
            <strong>% of Late</strong> = What % of all late orders have this issue. 
            <strong>Enrichment</strong> = How much more common this is in late orders vs all orders.
            <strong>Kitchen Late %</strong> = Prevalence specifically in orders where kitchen missed target by >2 min.
        </p>
    </div>
        """
        
        # Generate Comprehensive Recommendations based on ranked reasons
        content += """
    <div class="section">
        <h2 class="section-title">📝 Actionable Recommendations</h2>
        <p style="margin-bottom: 1rem; color: var(--text-secondary);">
            Based on the late order analysis, here are prioritized recommendations:
        </p>
        """
        
        # Build recommendations from top reasons
        recommendations = []
        
        for i, r in enumerate(ranked_reasons[:8]):  # Top 8 reasons
            reason = r.get('reason_code', '')
            pct_late = float(r.get('pct_of_late', 0) or 0)
            pct_kitchen = float(r.get('pct_of_kitchen_late', 0) or 0)
            owner = r.get('owner', '')
            category = r.get('category', '')
            
            if pct_late < 5:  # Skip if <5% of late orders
                continue
            
            rec = {
                'priority': i + 1,
                'issue': reason,
                'pct_late': pct_late,
                'owner': owner,
                'category': category,
                'action': '',
                'urgency': 'high' if i < 3 else 'medium' if i < 6 else 'low'
            }
            
            # Generate action based on reason
            if 'Long Production' in reason:
                rec['action'] = 'Review recipe timing accuracy. Audit cook stations with highest variance. Check equipment calibration.'
            elif 'Long Queue' in reason:
                rec['action'] = 'Assess staffing during peak hours. Review capacity vs volume. Consider sequencer holdback tuning.'
            elif 'Long Pending Packaging' in reason:
                rec['action'] = 'Audit expo station efficiency. Check bagging workflow. Ensure packaging materials are pre-staged.'
            elif 'Critical Force Complete' in reason or 'Premature Force' in reason:
                rec['action'] = 'Immediate training intervention. Audit KDS behaviors. Review force complete reasons with management.'
            elif 'Force Complete' in reason:
                rec['action'] = 'Review workflow bottlenecks causing force completes. Train staff on proper timing before bumping orders.'
            # Sequencer Actual Issue - only flag when expo wait > cook time variance
            elif 'Sequencer Issue (Expo Wait' in reason:
                rec['action'] = '⚠️ ACTIONABLE: Sequencer is over-holding items beyond what cook time variance justifies. Review holdback logic and release timing. Algorithm tuning needed.'
            # Bad Interaction flag - may not be actionable, depends on context
            elif 'Bad Interaction' in reason:
                rec['action'] = 'Flag present but may be expected for complex orders. Only actionable if expo wait > cook time range. Check hot hold inventory sync.'
            elif 'Trickling' in reason:
                rec['action'] = 'FIFO violation detected. May be expected for staggered cook times. Investigate if causing actual expo wait issues.'
            elif 'Double Delay' in reason:
                rec['action'] = 'Multiple delays applied. Review if delays are appropriate for order complexity or indicate systemic issue.'
            elif 'ALM' in reason or 'A La Minute' in reason:
                rec['action'] = 'A La Minute items naturally require last-minute cooking. Not inherently an issue unless causing excessive expo wait.'
            elif 'Missing Pouch' in reason:
                rec['action'] = 'Audit hot hold inventory management. Review par levels. Check inventory sync frequency.'
            elif 'Surprise Pouch' in reason:
                rec['action'] = 'Investigate unexpected hot hold items. May indicate system/inventory mismatch.'
            elif 'KDS Remake' in reason:
                rec['action'] = 'Audit quality issues causing remakes. Review training on first-time-right execution.'
            elif 'Bumped' in reason:
                rec['action'] = 'Review why items are being bumped back. May indicate upstream quality or workflow issues.'
            elif 'Sequencer Delay' in reason:
                rec['action'] = 'Expected for complex orders. Sequencer holdback is helping coordinate items. Only investigate if expo wait > cook time variance.'
            elif 'Reset' in reason:
                rec['action'] = 'Investigate timer resets. May indicate inaccurate cook times or workflow issues.'
            else:
                rec['action'] = 'Investigate root cause with operations team.'
            
            recommendations.append(rec)
        
        # Render recommendations
        for rec in recommendations:
            urgency_color = 'var(--pomodoro)' if rec['urgency'] == 'high' else 'var(--marmalade)' if rec['urgency'] == 'medium' else 'var(--snap-pea)'
            urgency_label = '🔴 HIGH' if rec['urgency'] == 'high' else '🟠 MEDIUM' if rec['urgency'] == 'medium' else '🟢 LOW'
            
            content += f"""
        <div class="rec-block {'rec-critical' if rec['urgency'] == 'high' else 'rec-warning' if rec['urgency'] == 'medium' else 'rec-info'}" style="margin-bottom: 1rem;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                <h4 style="margin: 0;">#{rec['priority']}: {rec['issue']}</h4>
                <span style="color: {urgency_color}; font-weight: bold;">{urgency_label}</span>
            </div>
            <p style="margin: 0.5rem 0;"><strong>{rec['pct_late']:.0f}%</strong> of late orders have this issue.</p>
            <div class="rec-action">⚡ <strong>Action:</strong> {rec['action']}</div>
            <div style="margin-top: 0.5rem; font-size: 0.8rem; color: var(--text-secondary);">Owner: <strong>{rec['owner']}</strong></div>
        </div>
            """
        
        content += "</div>"
    
    # Scenario Breakdown
    if scenarios:
        current_week_scenarios = [s for s in scenarios if s.get('service_week') == current.get('service_week')]
        if current_week_scenarios:
            content += """
            <div class="section">
                <h2 class="section-title collapsible">🎯 Delivery Scenario Breakdown</h2>
                <div class="collapse-content">
                    <table>
                        <tr>
                            <th>Scenario</th>
                            <th>Orders</th>
                            <th>OTR</th>
                            <th>Avg Sit Time</th>
                            <th>Courier Response</th>
                            <th>Handoff</th>
                        </tr>
            """
            for s in current_week_scenarios:
                otr_val = float(s.get('otr', 0))
                badge_class = 'good' if otr_val >= 90 else 'warning' if otr_val >= 80 else 'critical'
                content += f"""
                <tr>
                    <td>{s.get('scenario', 'N/A')}</td>
                    <td>{s.get('orders', 'N/A')}</td>
                    <td><span class="badge badge-{badge_class}">{s.get('otr', 'N/A')}%</span></td>
                    <td>{s.get('avg_sit_time', 'N/A')}m</td>
                    <td>{s.get('avg_courier_response', 'N/A')}m</td>
                    <td>{s.get('avg_handoff', 'N/A')}m</td>
                </tr>
                """
            content += "</table></div></div>"
    
    # Error Decomposition for Late Orders - Reveals TRUE root cause
    if error_decomp:
        content += """
    <div class="section">
        <h2 class="section-title collapsible">⚠️ Late Order Error Decomposition (TRUE Root Cause)</h2>
        <div class="collapse-content">
            <div class="rec-block rec-warning" style="margin-bottom: 1rem;">
                <h4>⚠️ CRITICAL: "Fast Handoff" ≠ "Kitchen On-Time"</h4>
                <p>The pickup scenario only measures pickup efficiency, NOT whether kitchen was on schedule. 
                "Both Fast" orders often have 10+ min of kitchen delay already baked in!</p>
            </div>
            <table>
                <tr>
                    <th>Pickup Scenario</th>
                    <th>Late Orders</th>
                    <th>% of Late</th>
                    <th>Kitchen Error<br/>(Queue+Cook)</th>
                    <th>Pickup Error</th>
                    <th>Transit Error</th>
                    <th>Total Error</th>
                    <th>Kitchen %</th>
                    <th>Transit %</th>
                </tr>
        """
        for ed in error_decomp:
            kitchen_err = float(ed.get('avg_kitchen_error', 0) or 0)
            transit_err = float(ed.get('avg_transit_error', 0) or 0)
            pickup_err = float(ed.get('avg_pickup_error', 0) or 0)
            total_err = float(ed.get('avg_total_error', 0) or 0)
            pct_kitchen = float(ed.get('pct_kitchen_driver', 0) or 0)
            pct_transit = float(ed.get('pct_transit_driver', 0) or 0)
            
            # Highlight which is the bigger driver
            kitchen_class = 'delta-negative' if pct_kitchen > 50 else ''
            transit_class = 'delta-negative' if pct_transit > 50 else ''
            
            content += f"""
                <tr>
                    <td><strong>{ed.get('pickup_scenario', 'N/A')}</strong></td>
                    <td>{int(ed.get('late_orders', 0) or 0):,}</td>
                    <td>{ed.get('pct_of_late', 0)}%</td>
                    <td class="{kitchen_class}">{kitchen_err:+.1f}m</td>
                    <td>{pickup_err:+.1f}m</td>
                    <td>{transit_err:+.1f}m</td>
                    <td><strong>{total_err:+.1f}m</strong></td>
                    <td class="{kitchen_class}"><strong>{pct_kitchen:.0f}%</strong></td>
                    <td class="{transit_class}"><strong>{pct_transit:.0f}%</strong></td>
                </tr>
            """
        
        # Find "Both Fast" row and provide insight
        both_fast = next((e for e in error_decomp if 'Both Fast' in str(e.get('pickup_scenario', ''))), None)
        if both_fast:
            bf_kitchen = float(both_fast.get('pct_kitchen_driver', 0) or 0)
            bf_transit = float(both_fast.get('pct_transit_driver', 0) or 0)
            bf_kitchen_err = float(both_fast.get('avg_kitchen_error', 0) or 0)
            bf_late = int(both_fast.get('late_orders', 0) or 0)
            bf_pct = float(both_fast.get('pct_of_late', 0) or 0)
            
            content += f"""
            </table>
            <div class="rec-block rec-critical" style="margin-top: 1rem;">
                <h4>🔍 "Both Fast" Orders Are NOT Transit-Only Issues</h4>
                <p>For the {bf_pct:.0f}% of late orders ({bf_late:,}) with "Both Fast" pickup:</p>
                <ul style="margin: 0.5rem 0;">
                    <li><strong>Kitchen (Queue + Cook) = {bf_kitchen:.0f}%</strong> of total lateness ({bf_kitchen_err:+.1f}m)</li>
                    <li><strong>Transit = {bf_transit:.0f}%</strong> of total lateness</li>
                </ul>
                <p style="margin-top: 0.5rem;">
                    <strong>❌ WRONG:</strong> "Both Fast = Kitchen doing fine, must be transit"<br/>
                    <strong>✅ CORRECT:</strong> "Both Fast = Handoff was efficient, but kitchen was ALREADY late, and transit added more"
                </p>
            </div>
            """
        else:
            content += "</table>"
        
        content += "</div></div>"
    
    # Weekly Trend
    content += """
    <div class="section">
        <h2 class="section-title collapsible">📅 Weekly Trend</h2>
        <div class="collapse-content">
            <div class="chart-container">
                <canvas id="trendChart"></canvas>
            </div>
            <table>
                <tr>
                    <th>Week</th>
                    <th>Orders</th>
                    <th>1P OTR</th>
                    <th>Kitchen OTR</th>
                    <th>Ticket Time</th>
                    <th>Expo Wait</th>
                    <th>Handoff</th>
                </tr>
    """
    
    chart_labels = []
    chart_otr = []
    chart_kitchen = []
    
    for m in metrics[:weeks]:
        chart_labels.append(m.get('service_week', ''))
        chart_otr.append(float(m.get('otr_1p', 0) or 0))
        chart_kitchen.append(float(m.get('kitchen_otr', 0) or 0))
        
        content += f"""
        <tr>
            <td>{m.get('service_week', 'N/A')}</td>
            <td>{m.get('orders_1p', 'N/A')}</td>
            <td>{m.get('otr_1p', 'N/A')}%</td>
            <td>{m.get('kitchen_otr', 'N/A')}%</td>
            <td>{m.get('avg_ticket_time', 'N/A')}m</td>
            <td>{m.get('avg_expo_wait', 'N/A')}m</td>
            <td>{m.get('avg_handoff', 'N/A')}m</td>
        </tr>
        """
    
    content += f"""
            </table>
        </div>
    </div>
    
    <script>
        const ctx = document.getElementById('trendChart').getContext('2d');
        new Chart(ctx, {{
            type: 'line',
            data: {{
                labels: {json.dumps(list(reversed(chart_labels)))},
                datasets: [
                    {{
                        label: '1P OTR',
                        data: {json.dumps(list(reversed(chart_otr)))},
                        borderColor: '#6FD172',
                        backgroundColor: 'rgba(111, 209, 114, 0.1)',
                        tension: 0.3,
                        fill: true
                    }},
                    {{
                        label: 'Kitchen OTR',
                        data: {json.dumps(list(reversed(chart_kitchen)))},
                        borderColor: '#37BC96',
                        backgroundColor: 'rgba(55, 188, 150, 0.1)',
                        tension: 0.3,
                        fill: true
                    }}
                ]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{ labels: {{ color: '#FAF5EE' }} }}
                }},
                scales: {{
                    y: {{
                        min: 40,
                        max: 100,
                        ticks: {{ color: '#CCF4CD' }},
                        grid: {{ color: 'rgba(7, 143, 69, 0.3)' }}
                    }},
                    x: {{
                        ticks: {{ color: '#CCF4CD' }},
                        grid: {{ color: 'rgba(7, 143, 69, 0.3)' }}
                    }}
                }}
            }}
        }});
    </script>
    """
    
    # Timing Breakdown
    content += f"""
    <div class="section">
        <h2 class="section-title collapsible">⏱️ Timing Breakdown (Current Week)</h2>
        <div class="collapse-content">
            <div class="two-col">
                <div>
                    <h4 style="color: var(--snap-pea); margin-bottom: 1rem;">Kitchen Stages</h4>
                    <table>
                        <tr><th>Stage</th><th>Variance from Expected</th></tr>
                        <tr><td>Queue</td><td class="{'delta-negative' if float(current.get('queue_variance', 0) or 0) > 1 else 'delta-positive'}">{current.get('queue_variance', 'N/A')}m</td></tr>
                        <tr><td>Cook</td><td class="{'delta-negative' if float(current.get('cook_variance', 0) or 0) > 1 else 'delta-positive'}">{current.get('cook_variance', 'N/A')}m</td></tr>
                        <tr><td>Pack/Bag</td><td class="{'delta-negative' if float(current.get('pack_variance', 0) or 0) > 1 else 'delta-positive'}">{current.get('pack_variance', 'N/A')}m</td></tr>
                    </table>
                </div>
                <div>
                    <h4 style="color: var(--snap-pea); margin-bottom: 1rem;">Post-Kitchen Stages</h4>
                    <table>
                        <tr><th>Stage</th><th>Avg Time</th></tr>
                        <tr><td>Expo Wait</td><td>{current.get('avg_expo_wait', 'N/A')}m</td></tr>
                        <tr><td>Courier Response</td><td>{current.get('avg_courier_response', 'N/A')}m</td></tr>
                        <tr><td>Kitchen Handoff</td><td>{current.get('avg_handoff', 'N/A')}m</td></tr>
                        <tr><td>Transit</td><td>{current.get('avg_transit', 'N/A')}m</td></tr>
                    </table>
                </div>
            </div>
        </div>
    </div>
    """
    
    return generate_html_report({
        'title': f"{current.get('hdr_name', hdr_name)} - {current.get('service_week', 'Recent')}",
        'content': content
    }, 'hdr')


def generate_network_report(weeks: int) -> str:
    """Generate network-wide WBR report."""
    
    print("Fetching network-wide data...")
    
    summary = get_network_summary(weeks)
    problems = get_problem_locations(2)
    
    if not summary:
        return "No network data found"
    
    # Aggregate by week (combine population types)
    weekly_totals = {}
    for row in summary:
        week = row.get('service_week')
        if week not in weekly_totals:
            weekly_totals[week] = {
                'orders_1p': 0, 'delivery_orders': 0, 'pickup_orders': 0,
                'otr_sum': 0, 'delivery_otr_sum': 0, 'pickup_otr_sum': 0,
                'kitchen_otr_sum': 0, 'ticket_sum': 0, 'count': 0
            }
        wt = weekly_totals[week]
        wt['orders_1p'] += int(row.get('orders_1p', 0) or 0)
        wt['delivery_orders'] += int(row.get('delivery_orders', 0) or 0)
        wt['pickup_orders'] += int(row.get('pickup_orders', 0) or 0)
        wt['otr_sum'] += float(row.get('otr_1p', 0) or 0)
        wt['delivery_otr_sum'] += float(row.get('otr_delivery', 0) or 0)
        wt['pickup_otr_sum'] += float(row.get('otr_pickup', 0) or 0)
        wt['kitchen_otr_sum'] += float(row.get('kitchen_otr', 0) or 0)
        wt['ticket_sum'] += float(row.get('avg_ticket_time', 0) or 0)
        wt['count'] += 1
    
    weeks_sorted = sorted(weekly_totals.keys(), reverse=True)
    current_week = weeks_sorted[0] if weeks_sorted else None
    prev_week = weeks_sorted[1] if len(weeks_sorted) > 1 else None
    
    curr = weekly_totals.get(current_week, {})
    prev = weekly_totals.get(prev_week, {})
    
    curr_otr = curr['otr_sum'] / curr['count'] if curr.get('count') else 0
    prev_otr = prev['otr_sum'] / prev['count'] if prev.get('count') else 0
    otr_delta = curr_otr - prev_otr
    
    content = f"""
    <div class="section">
        <h2 class="section-title">📊 Network Executive Summary</h2>
        <p style="margin-bottom: 1rem; color: var(--text-secondary);">Week of {current_week}</p>
        
        <div class="metrics-grid">
            <div class="metric">
                <div class="metric-value {'good' if curr_otr >= 90 else 'warning' if curr_otr >= 85 else 'critical'}">{curr_otr:.1f}%</div>
                <div class="metric-label">Network OTR (1P)</div>
                <div class="metric-delta {'delta-positive' if otr_delta > 0 else 'delta-negative'}">{otr_delta:+.1f} pts WoW</div>
            </div>
            <div class="metric">
                <div class="metric-value">{curr['delivery_otr_sum']/curr['count']:.1f}%</div>
                <div class="metric-label">Delivery OTR</div>
            </div>
            <div class="metric">
                <div class="metric-value">{curr['pickup_otr_sum']/curr['count']:.1f}%</div>
                <div class="metric-label">Pickup OTR</div>
            </div>
            <div class="metric">
                <div class="metric-value">{curr['kitchen_otr_sum']/curr['count']:.1f}%</div>
                <div class="metric-label">Kitchen OTR</div>
            </div>
            <div class="metric">
                <div class="metric-value">{curr.get('orders_1p', 0):,}</div>
                <div class="metric-label">1P Orders</div>
            </div>
            <div class="metric">
                <div class="metric-value">{curr['ticket_sum']/curr['count']:.1f}m</div>
                <div class="metric-label">Avg Ticket Time</div>
            </div>
        </div>
    </div>
    """
    
    # Profile A Locations
    if problems.get('profile_a'):
        content += """
        <div class="section">
            <h2 class="section-title">🔴 Profile A: Ops Failures (Fast Drivers, Slow Handoff)</h2>
            <p style="margin-bottom: 1rem; color: var(--text-secondary);">These locations have quick driver arrival but slow in-store handoff. Likely expo bottleneck or "fake bumping".</p>
            <table>
                <tr><th>HDR</th><th>Population</th><th>Orders</th><th>Courier Response</th><th>Handoff</th><th>Ops Gap</th><th>OTR</th></tr>
        """
        for loc in problems['profile_a']:
            content += f"""
            <tr>
                <td><strong>{loc.get('hdr_name', 'N/A')}</strong></td>
                <td>{loc.get('population_type', 'N/A')}</td>
                <td>{loc.get('orders', 'N/A')}</td>
                <td class="delta-positive">{loc.get('avg_courier_response', 'N/A')}m</td>
                <td class="delta-negative">{loc.get('avg_handoff', 'N/A')}m</td>
                <td class="delta-negative">+{loc.get('ops_gap', 'N/A')}m</td>
                <td>{loc.get('otr', 'N/A')}%</td>
            </tr>
            """
        content += """
            </table>
            <div class="rec-action" style="margin-top: 1rem;">⚡ <strong>Action:</strong> Audit KDS procedures. Stop pre-bumping. Focus on expo station flow.</div>
        </div>
        """
    
    # Profile B Locations
    if problems.get('profile_b'):
        content += """
        <div class="section">
            <h2 class="section-title">🟠 Profile B: Logistics Failures (Fast Kitchen, Slow Drivers)</h2>
            <p style="margin-bottom: 1rem; color: var(--text-secondary);">These locations have fast kitchen execution but drivers take too long to arrive.</p>
            <table>
                <tr><th>HDR</th><th>Population</th><th>Orders</th><th>Courier Response</th><th>Handoff</th><th>Logistics Gap</th><th>OTR</th></tr>
        """
        for loc in problems['profile_b']:
            content += f"""
            <tr>
                <td><strong>{loc.get('hdr_name', 'N/A')}</strong></td>
                <td>{loc.get('population_type', 'N/A')}</td>
                <td>{loc.get('orders', 'N/A')}</td>
                <td class="delta-negative">{loc.get('avg_courier_response', 'N/A')}m</td>
                <td class="delta-positive">{loc.get('avg_handoff', 'N/A')}m</td>
                <td class="delta-negative">+{loc.get('logistics_gap', 'N/A')}m</td>
                <td>{loc.get('otr', 'N/A')}%</td>
            </tr>
            """
        content += """
            </table>
            <div class="rec-action" style="margin-top: 1rem;">⚡ <strong>Action:</strong> Review courier incentives. Adjust dispatch radius for these zones.</div>
        </div>
        """
    
    # Weekly Breakdown by Population Type
    content += """
    <div class="section">
        <h2 class="section-title collapsible">📅 Weekly Breakdown by Population Type</h2>
        <div class="collapse-content">
            <table>
                <tr><th>Week</th><th>Population</th><th>1P Orders</th><th>OTR</th><th>Delivery OTR</th><th>Pickup OTR</th><th>Kitchen OTR</th></tr>
    """
    
    for row in summary[:24]:  # Last 4 weeks * ~6 population types
        otr_val = float(row.get('otr_1p', 0) or 0)
        badge_class = 'good' if otr_val >= 90 else 'warning' if otr_val >= 85 else 'critical'
        content += f"""
        <tr>
            <td>{row.get('service_week', 'N/A')}</td>
            <td>{row.get('population_type', 'N/A')}</td>
            <td>{row.get('orders_1p', 'N/A')}</td>
            <td><span class="badge badge-{badge_class}">{row.get('otr_1p', 'N/A')}%</span></td>
            <td>{row.get('otr_delivery', 'N/A')}%</td>
            <td>{row.get('otr_pickup', 'N/A')}%</td>
            <td>{row.get('kitchen_otr', 'N/A')}%</td>
        </tr>
        """
    
    content += "</table></div></div>"
    
    return generate_html_report({
        'title': f"Network WBR Summary - {current_week}",
        'content': content
    }, 'network')


def generate_order_report(order_number: str) -> str:
    """Generate order-level deep dive report."""
    
    print(f"Fetching data for order: {order_number}...")
    
    order = get_order_details(order_number)
    
    if not order:
        return f"No order found for '{order_number}'"
    
    imperfections = get_order_imperfections(order.get('order_id', ''))
    
    # Determine OTR status styling
    sla_diff = float(order.get('delivery_sla_diff', 0) or 0)
    status = order.get('otr_status', 'UNKNOWN')
    status_class = 'good' if status == 'ON_TIME' else 'warning' if status == 'EARLY' else 'critical'
    
    content = f"""
    <div class="section">
        <h2 class="section-title">🎯 Order Details</h2>
        <div class="metrics-grid">
            <div class="metric">
                <div class="metric-value {status_class}">{status}</div>
                <div class="metric-label">OTR Status</div>
                <div class="metric-delta">{sla_diff:+.1f} mins</div>
            </div>
            <div class="metric">
                <div class="metric-value">{order.get('o2e', 'N/A')}m</div>
                <div class="metric-label">O2E Time</div>
            </div>
            <div class="metric">
                <div class="metric-value">{order.get('ticket_time', 'N/A')}m</div>
                <div class="metric-label">Ticket Time</div>
            </div>
            <div class="metric">
                <div class="metric-value">{order.get('expo_wait', 'N/A')}m</div>
                <div class="metric-label">Expo Wait</div>
            </div>
            <div class="metric">
                <div class="metric-value">{order.get('items_per_check', 'N/A')}</div>
                <div class="metric-label">Items</div>
            </div>
        </div>
        
        <div style="margin-top: 1.5rem;">
            <table>
                <tr><th>Field</th><th>Value</th></tr>
                <tr><td>Order Number</td><td><strong>{order.get('order_number', 'N/A')}</strong></td></tr>
                <tr><td>HDR</td><td>{order.get('hdr_name', 'N/A')}</td></tr>
                <tr><td>Date</td><td>{order.get('service_date_et', 'N/A')}</td></tr>
                <tr><td>Dining Option</td><td>{order.get('dining_option', 'N/A')}</td></tr>
                <tr><td>Channel</td><td>{order.get('order_channel', 'N/A')}</td></tr>
                <tr><td>Population Type</td><td>{order.get('population_type', 'N/A')}</td></tr>
                <tr><td>HDR Class</td><td>{order.get('hdr_class', 'N/A')}</td></tr>
            </table>
        </div>
    </div>
    """
    
    # Timing Breakdown
    content += f"""
    <div class="section">
        <h2 class="section-title">⏱️ Timing Breakdown</h2>
        <div class="two-col">
            <div>
                <h4 style="color: var(--snap-pea); margin-bottom: 1rem;">Kitchen Stages</h4>
                <table>
                    <tr><th>Stage</th><th>Actual</th><th>Expected</th><th>Variance</th></tr>
                    <tr>
                        <td>Queue</td>
                        <td>{order.get('actual_queue', 'N/A')}m</td>
                        <td>{order.get('est_queue', 'N/A')}m</td>
                        <td class="{'delta-negative' if float(order.get('queue_var', 0) or 0) > 1 else 'delta-positive'}">{order.get('queue_var', 'N/A')}m</td>
                    </tr>
                    <tr>
                        <td>Cook</td>
                        <td>{order.get('actual_cook', 'N/A')}m</td>
                        <td>{order.get('est_cook', 'N/A')}m</td>
                        <td class="{'delta-negative' if float(order.get('cook_var', 0) or 0) > 1 else 'delta-positive'}">{order.get('cook_var', 'N/A')}m</td>
                    </tr>
                    <tr>
                        <td>Pack/Bag</td>
                        <td>{order.get('actual_pack', 'N/A')}m</td>
                        <td>{order.get('est_pack', 'N/A')}m</td>
                        <td class="{'delta-negative' if float(order.get('pack_var', 0) or 0) > 1 else 'delta-positive'}">{order.get('pack_var', 'N/A')}m</td>
                    </tr>
                </table>
            </div>
            <div>
                <h4 style="color: var(--snap-pea); margin-bottom: 1rem;">Post-Kitchen</h4>
                <table>
                    <tr><th>Stage</th><th>Time</th></tr>
                    <tr><td>Expo Wait</td><td>{order.get('expo_wait', 'N/A')}m</td></tr>
                    <tr><td>Courier Response</td><td>{order.get('courier_response', 'N/A')}m</td></tr>
                    <tr><td>Handoff</td><td>{order.get('handoff', 'N/A')}m</td></tr>
                    <tr><td>Transit</td><td>{order.get('transit', 'N/A')}m</td></tr>
                </table>
            </div>
        </div>
    </div>
    """
    
    # Root Cause Analysis
    content += """<div class="section"><h2 class="section-title">🔍 Root Cause Analysis</h2>"""
    
    if status == 'LATE':
        kitchen_sla = float(order.get('kitchen_sla_diff', 0) or 0)
        courier = float(order.get('courier_response', 0) or 0)
        handoff = float(order.get('handoff', 0) or 0)
        
        if kitchen_sla > 5 and handoff <= 5 and courier <= 5:
            content += """
            <div class="rec-block rec-critical">
                <h4>🔴 OPS: Kitchen Slow</h4>
                <p>Kitchen was significantly late, but handoff and courier were fast. The delay originated in the kitchen.</p>
                <div class="rec-action">⚡ Check queue time, cook duration, and complexity.</div>
            </div>
            """
        elif courier <= 5 and handoff > 8:
            content += """
            <div class="rec-block rec-critical">
                <h4>🔴 OPS: Slow Handoff (Possible Fake Bump)</h4>
                <p>Driver arrived quickly but waited a long time for food. Order may have been bumped prematurely.</p>
                <div class="rec-action">⚡ Review expo procedures at this location.</div>
            </div>
            """
        elif kitchen_sla <= 2 and courier > 10:
            content += """
            <div class="rec-block rec-warning">
                <h4>🟠 LOGISTICS: Driver Shortage</h4>
                <p>Kitchen was on time, but no driver arrived for over 10 minutes. Food sat ready.</p>
                <div class="rec-action">⚡ Review courier incentives for this zone.</div>
            </div>
            """
        elif kitchen_sla > 2 and courier > 5:
            content += """
            <div class="rec-block rec-critical">
                <h4>🔴 COMPOUNDING: Both Ops & Logistics Failed</h4>
                <p>Kitchen was late AND courier was slow. Multiple failures compounded.</p>
            </div>
            """
        else:
            content += """
            <div class="rec-block rec-info">
                <h4>⚪ Root cause unclear</h4>
                <p>No clear single bottleneck identified. Review individual timing stages.</p>
            </div>
            """
    elif status == 'EARLY':
        content += """
        <div class="rec-block rec-warning">
            <h4>🟡 ETA Over-Prediction</h4>
            <p>Order arrived significantly early. The ETA system over-estimated the delivery time.</p>
            <div class="rec-action">ℹ️ This affects customer experience but not as severely as late orders.</div>
        </div>
        """
    else:
        content += """
        <div class="rec-block rec-success">
            <h4>✅ On Time</h4>
            <p>This order was delivered within the acceptable window.</p>
        </div>
        """
    
    content += "</div>"
    
    # Imperfections
    if imperfections:
        content += """
        <div class="section">
            <h2 class="section-title collapsible">⚠️ Item Imperfections</h2>
            <div class="collapse-content">
                <table>
                    <tr><th>Item</th><th>Issues</th><th>Severity</th></tr>
        """
        for item in imperfections:
            issues = []
            if item.get('has_force_progression') == 1:
                issues.append('Force Complete')
            if item.get('has_long_queue') == 1:
                issues.append('Long Queue')
            if item.get('has_longer_than_expected_production_time') == 1:
                issues.append('Slow Production')
            if item.get('has_bad_interaction') == 1:
                issues.append('Sequencer Issue')
            if item.get('has_trickling_violation') == 1:
                issues.append('Trickling')
            if item.get('has_missing_pouch') == 1:
                issues.append('Missing Pouch')
            
            severity = item.get('force_complete_severity_tier', 'N/A')
            
            if issues:
                content += f"""
                <tr>
                    <td>{item.get('menu_item_name', 'Unknown')}</td>
                    <td>{', '.join(issues)}</td>
                    <td>{severity}</td>
                </tr>
                """
        content += "</table></div></div>"
    
    return generate_html_report({
        'title': f"Order {order.get('order_number', order_number)} - {order.get('hdr_name', 'Unknown')}",
        'content': content
    }, 'order')


def main():
    """Main entry point."""
    
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    # Parse arguments
    arg = sys.argv[1]
    weeks = DEFAULT_WEEKS
    
    # Check for --weeks flag
    if '--weeks' in sys.argv:
        weeks_idx = sys.argv.index('--weeks')
        if weeks_idx + 1 < len(sys.argv):
            try:
                weeks = int(sys.argv[weeks_idx + 1])
            except ValueError:
                pass
    
    # Create output directory
    OUTPUT_DIR.mkdir(exist_ok=True)
    
    # Generate report based on input
    if arg == '--network':
        html = generate_network_report(weeks)
        filename = f"otr-network-{datetime.now().strftime('%Y-%m-%d-%H%M')}.html"
    elif arg.isdigit() and len(arg) >= 6:
        # Likely an order number
        html = generate_order_report(arg)
        filename = f"otr-order-{arg}-{datetime.now().strftime('%Y-%m-%d-%H%M')}.html"
    else:
        # Assume HDR name
        html = generate_hdr_report(arg, weeks)
        safe_name = arg.lower().replace(' ', '-')[:20]
        filename = f"otr-hdr-{safe_name}-{datetime.now().strftime('%Y-%m-%d-%H%M')}.html"
    
    # Write output
    output_path = OUTPUT_DIR / filename
    with open(output_path, 'w') as f:
        f.write(html)
    
    print(f"✓ Generated: {output_path}")
    
    # Try to open in browser (suppress stderr from macOS osascript)
    try:
        import webbrowser
        import subprocess
        # Use subprocess to suppress stderr from osascript on macOS
        subprocess.run(
            ['open', str(output_path.absolute())],
            stderr=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL
        )
    except:
        pass


if __name__ == "__main__":
    main()

