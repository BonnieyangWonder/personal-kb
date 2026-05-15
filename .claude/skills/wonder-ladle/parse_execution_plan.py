#!/usr/bin/env python3
"""
Parse text-formatted Protocol Buffer execution plan into pandas DataFrame
"""

import pandas as pd
import re
from datetime import date

def parse_execution_plan(filepath):
    """Parse the .txt.pb file into a list of dictionaries"""
    items = []
    current_item = {}
    in_item = False
    in_delivery_date = False

    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()

            # Start of item block
            if line == 'items {':
                in_item = True
                current_item = {}
                continue

            # End of item block
            if line == '}' and in_item and not in_delivery_date:
                # Add the item if it has required fields
                if current_item:
                    items.append(current_item.copy())
                in_item = False
                current_item = {}
                continue

            if not in_item:
                continue

            # Parse delivery_date nested block
            if line == 'delivery_date {':
                in_delivery_date = True
                continue

            if line == '}' and in_delivery_date:
                in_delivery_date = False
                continue

            # Parse fields inside delivery_date
            if in_delivery_date:
                if line.startswith('year:'):
                    current_item['delivery_year'] = int(line.split(':')[1].strip())
                elif line.startswith('month:'):
                    current_item['delivery_month'] = int(line.split(':')[1].strip())
                elif line.startswith('day:'):
                    current_item['delivery_day'] = int(line.split(':')[1].strip())
                continue

            # Parse regular fields
            if line.startswith('vendor_sku:'):
                # Extract quoted value
                match = re.search(r'"([^"]+)"', line)
                if match:
                    current_item['vendor_sku'] = match.group(1)

            elif line.startswith('uom:'):
                current_item['uom'] = line.split(':')[1].strip()

            elif line.startswith('supplier_node_id:'):
                match = re.search(r'"([^"]+)"', line)
                if match:
                    current_item['supplier_node_id'] = match.group(1)

            elif line.startswith('receiver_node_id:'):
                match = re.search(r'"([^"]+)"', line)
                if match:
                    current_item['receiver_node_id'] = match.group(1)

            elif line.startswith('scheduled_order_id:'):
                match = re.search(r'"([^"]+)"', line)
                if match:
                    current_item['scheduled_order_id'] = match.group(1)

            elif line.startswith('ideal_quantity:'):
                current_item['ideal_quantity'] = int(line.split(':')[1].strip())

            elif line.startswith('allocated_quantity:'):
                current_item['allocated_quantity'] = int(line.split(':')[1].strip())

    # Convert to DataFrame
    df = pd.DataFrame(items)

    # Create delivery_date column
    if 'delivery_year' in df.columns:
        df['delivery_date'] = pd.to_datetime(
            df[['delivery_year', 'delivery_month', 'delivery_day']].rename(
                columns={'delivery_year': 'year', 'delivery_month': 'month', 'delivery_day': 'day'}
            )
        )

    # Fill missing quantities with 0
    if 'ideal_quantity' in df.columns:
        df['ideal_quantity'] = df['ideal_quantity'].fillna(0).astype(int)
    else:
        df['ideal_quantity'] = 0

    if 'allocated_quantity' in df.columns:
        df['allocated_quantity'] = df['allocated_quantity'].fillna(0).astype(int)
    else:
        df['allocated_quantity'] = 0

    return df


if __name__ == '__main__':
    print("Parsing execution plan...")
    df = parse_execution_plan('temp/43a6af7d-bacf-481e-8a2e-e1bf40ce6200.txt.pb')

    print(f"\nLoaded {len(df):,} items")
    print(f"\nDataFrame shape: {df.shape}")
    print(f"\nColumns: {df.columns.tolist()}")
    print(f"\nFirst few rows:")
    print(df.head())

    print(f"\nData types:")
    print(df.dtypes)

    print(f"\nBasic stats:")
    print(df.describe())

    # Answer the test question
    print("\n" + "="*80)
    print("TEST QUERY")
    print("="*80)
    print("Question: How many of item 8803374 did we order where")
    print("  supplier is 6651623c-c67e-4b17-a368-66a74e2206bf")
    print("  receiver is 46d337b4-7f61-4338-979a-5ee8d8e0071f")
    print()

    result = df[
        (df['vendor_sku'] == '8803374') &
        (df['supplier_node_id'] == '6651623c-c67e-4b17-a368-66a74e2206bf') &
        (df['receiver_node_id'] == '46d337b4-7f61-4338-979a-5ee8d8e0071f')
    ]

    print(f"Matching records: {len(result)}")

    if len(result) > 0:
        total_ideal = result['ideal_quantity'].sum()
        total_allocated = result['allocated_quantity'].sum()

        print(f"Total ideal quantity: {total_ideal}")
        print(f"Total allocated quantity: {total_allocated}")
        print(f"\nDetails of matching records:")
        print(result[['vendor_sku', 'supplier_node_id', 'receiver_node_id',
                      'delivery_date', 'ideal_quantity', 'allocated_quantity']])
    else:
        print("No matching records found!")

    # Save to CSV for future queries
    csv_path = 'temp/execution_plan.csv'
    df.to_csv(csv_path, index=False)
    print(f"\n\nDataFrame saved to: {csv_path}")
