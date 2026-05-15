# wonder-ladle (Under Construction)

This skill provides tools and knowledge for working with Wonder's Ladle system - the purchase planning and execution plan generation service.

## Status

⚠️ **Under Construction** - This skill is being developed and is not yet production-ready.

## Current Tools

### parse_execution_plan.py
Parses text-formatted Protocol Buffer execution plan files (.txt.pb) into pandas DataFrames for analysis.

**Usage:**
```bash
python3 parse_execution_plan.py
```

**Features:**
- Parses 500K+ line execution plan files
- Converts to CSV for efficient querying
- Handles nested delivery_date structures
- Extracts: vendor_sku, supplier_node_id, receiver_node_id, quantities, dates

**Output:** Creates `execution_plan.csv` with all parsed items

### debug_query.py
Debugging utility to inspect parsed execution plan data and troubleshoot queries.

**Usage:**
```bash
python3 debug_query.py
```

## Execution Plan Structure

Execution plans are Protocol Buffer files containing:
- `run_data`: Metadata (UUID, timestamp)
- `items[]`: Array of planned orders/shipments
  - `vendor_sku`: Product identifier
  - `uom`: Unit of measure
  - `delivery_date`: Year/month/day structure
  - `supplier_node_id`: Source location UUID
  - `receiver_node_id`: Destination location UUID
  - `ideal_quantity`: Optimal order quantity
  - `allocated_quantity`: Actual allocated quantity
  - `scheduled_order_id`: Order identifier hash

## Data Access

Execution plans are stored in Azure Blob Storage:
- **Storage Account:** rfprodv2ladlestorage
- **Container:** execution-plans
- **Formats:** `.pb` (binary), `.txt.pb` (text), `.xlsx` (some exports)

**Download latest:**
```bash
az storage blob list \
  --account-name rfprodv2ladlestorage \
  --container-name execution-plans \
  --auth-mode login \
  --query "[?ends_with(name, '.txt.pb')] | sort_by(@, &properties.lastModified) | [-1]"
```

## TODO

- [ ] Create SKILL.md with complete skill documentation
- [ ] Document schema reference for execution plans
- [ ] Add common-pitfalls.md for query patterns
- [ ] Document relationship with POMS (purchase orders)
- [ ] Add query examples and use cases
- [ ] Understand Ladle's role in supply chain workflow
