#!/usr/bin/env python3
"""Debug the query - check what values exist"""

import pandas as pd

# Load the CSV we just created
df = pd.read_csv('temp/execution_plan.csv')

print("Debugging the query...")
print("="*80)

# Check if the vendor_sku exists
sku = '8803374'
supplier = '6651623c-c67e-4b17-a368-66a74e2206bf'
receiver = '46d337b4-7f61-4338-979a-5ee8d8e0071f'

print(f"\n1. Does vendor_sku '{sku}' exist?")
sku_matches = df[df['vendor_sku'] == sku]
print(f"   Found {len(sku_matches)} records with this SKU")
if len(sku_matches) > 0:
    print(f"   Suppliers for this SKU: {sku_matches['supplier_node_id'].unique()[:5]}")
    print(f"   Receivers for this SKU: {sku_matches['receiver_node_id'].unique()[:5]}")

print(f"\n2. Does supplier_node_id '{supplier}' exist?")
supplier_matches = df[df['supplier_node_id'] == supplier]
print(f"   Found {len(supplier_matches)} records with this supplier")
if len(supplier_matches) > 0:
    print(f"   SKUs from this supplier: {supplier_matches['vendor_sku'].unique()[:10]}")

print(f"\n3. Does receiver_node_id '{receiver}' exist?")
receiver_matches = df[df['receiver_node_id'] == receiver]
print(f"   Found {len(receiver_matches)} records with this receiver")
if len(receiver_matches) > 0:
    print(f"   SKUs to this receiver: {receiver_matches['vendor_sku'].unique()[:10]}")

# Check combinations
print(f"\n4. SKU + Supplier combination:")
sku_supplier = df[(df['vendor_sku'] == sku) & (df['supplier_node_id'] == supplier)]
print(f"   Found {len(sku_supplier)} records")

print(f"\n5. SKU + Receiver combination:")
sku_receiver = df[(df['vendor_sku'] == sku) & (df['receiver_node_id'] == receiver)]
print(f"   Found {len(sku_receiver)} records")

print(f"\n6. Supplier + Receiver combination:")
supplier_receiver = df[(df['supplier_node_id'] == supplier) & (df['receiver_node_id'] == receiver)]
print(f"   Found {len(supplier_receiver)} records")

# Show overall stats
print(f"\n" + "="*80)
print("Overall dataset stats:")
print(f"  Total records: {len(df):,}")
print(f"  Unique SKUs: {df['vendor_sku'].nunique():,}")
print(f"  Unique suppliers: {df['supplier_node_id'].nunique():,}")
print(f"  Unique receivers: {df['receiver_node_id'].nunique():,}")

# Show some sample SKUs
print(f"\n  Sample SKUs: {df['vendor_sku'].unique()[:10]}")
