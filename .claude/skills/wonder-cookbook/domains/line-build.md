# Line Build - Kitchen Prep Line Assignments

The line build system defines how items are prepared in the kitchen, including which cooking line, appliance, and phase each step belongs to. This is critical for kitchen operations and KDS (Kitchen Display System) sequencing.

Line builds are **only applicable to truck items** (items prepared on Wonder trucks/HDRs). They define the complete cooking workflow from prep through completion.

---

## Essential Filter (ALWAYS USE)

When joining to item tables, always include:

```sql
WHERE effective = true
  AND deleted = false
  AND item_status != 'DORMANT'
```

---

## Line Build Status

Each line build has a status indicating its readiness:

| Status | Description |
|--------|-------------|
| `None` | No line build exists for this truck item version |
| `Line Build Created` | Line build exists and is valid |
| `Pending Update` | Line build exists but has warnings requiring attention |

When warnings exist (e.g., BOM changes affecting line build), status changes to `Pending Update`.

---

## Line Build Hierarchy

Line builds follow a hierarchical structure:

```
Line Build (per item version)
├── Apply to Restaurants (All or specific HDRs)
├── Apply to Options (customization variants)
└── Tasks (parallel cooking workflows)
    └── Steps (ordered actions within task)
        └── Sub-Steps (detailed instructions per step)
```

### Multi-Task Line Builds

A menu item can have **multiple parallel tasks** within a single line build. Tasks enable:
- Component-based cooking (different proteins cooked separately)
- Customization-driven workflows (sauce trio only if selected)
- Parallel prep paths that converge at expo

**Task Properties:**
- `task_name` - Required, up to 100 characters (e.g., "Flatbread", "Chicken Kebab", "Sauce Trio")
- `mapping_option` - Optional customization option that triggers this task

**Important:** No step dependencies across parallel tasks. Dependencies exist only within individual tasks.

---

## Activity Types

The `procedures_activity` field indicates what type of action is performed:

| Activity | Description | Use Case | Required Fields |
|----------|-------------|----------|-----------------|
| `COOK` | Active cooking action | Frying, grilling, baking | Appliance required, cook time > 0 |
| `GARNISH` | Assembly/garnishing | Adding toppings, plating | Step time > 0, no appliance |
| `COMPLETE` | Completion/finishing | Final packaging, handoff | Must be last step, parking spot required |
| `VEND` | Vending/dispensing | Packaged items from ambient storage | Mapping item required, parking spot required |

> **Deprecated**: The `PACKAGE` and `BAG` activities are deprecated. They may appear in historical data but should not be used in new line builds.

**Activity-Specific Rules:**

- **COOK**: Must have appliance selected; step time > cook time
- **GARNISH**: No appliance; cook time and resting time = 0
- **COMPLETE**: Must be last step; exactly one complete step per task (unless customization variants)
- **VEND**: Only shows BOM items (excluding hot hold eligible items) and customization options; requires parking spot (Ambient or Warm)

---

## Core Table

### item_line_builds

Kitchen prep line assignments with timing and equipment details.

```sql
-- Key identification fields
item_version_id          STRING    -- Version UUID
item_number              STRING    -- Item ID
service_start_time       DATETIME  -- Service window start
service_end_time         DATETIME  -- Service window end
line_build_id            STRING    -- Unique line build identifier
status                   STRING    -- Line build status
restaurant_id            STRING    -- Associated HDR/restaurant

-- Procedure fields
procedures_step_order    INTEGER   -- Order of this step
procedures_cooking_phase STRING    -- Cooking phase (see below)
procedures_appliance     STRING    -- Equipment used (see below)
procedures_activity      STRING    -- Activity description
procedures_batch_limit   STRING    -- Batch limit
procedures_holding_location STRING -- Where item is held

-- Timing fields
step_time                STRING    -- Total step time
cooking_time             STRING    -- Active cooking time
resting_time             STRING    -- Resting/cooling time
hold_time                STRING    -- Hold time before service

-- Hot hold eligibility
is_hot_hold_eligible_selected BOOLEAN -- Can be held hot
show_hot_hold            BOOLEAN   -- Display hot hold option

-- Sub-steps (nested detail)
sub_steps_order          STRING    -- Sub-step ordering
sub_steps_title          STRING    -- Sub-step title
sub_steps_related_item_number STRING -- Related item if any
```

## Cooking Phases

| Phase | Description |
|-------|-------------|
| `PRE_ROUTE_PREP` | Preparation before routing/assignment |
| `PRE_ORDER_PREP` | Preparation before order received |
| `PRE_COOKING` | Prep work before cooking starts |
| `COOKING` | Active cooking phase |
| `POST_COOKING` | Assembly/finishing after cooking |

> **Note**: The `HOT_HOLD` and `A_LA_MINUTE` values do not exist in the current cooking phase enum. Hot hold functionality is managed through the hot hold eligible flags and appliance configurations, not as a cooking phase.

---

## Appliances

Appliances available by activity type:

### COOK Activity Appliances

| Appliance | Use Case | Global Config Required |
|-----------|----------|------------------------|
| `TURBO_OVEN` | Rapid convection heating | Yes - `{percent}/{windspeed} {temp}` (e.g., "100/90 475°F") |
| `FRYER` | Deep frying | Yes - temperature (325°F, 350°F) |
| `PIZZA_CONVEYOR_OVEN` | Pizza baking | Yes - belt speed config |
| `CLAMSHELL` | Grilling burgers, sandwiches | Yes - top/bottom plate temps |
| `WATER_BATH` | Sous vide/re-thermalization | No |
| `FRIDGE` | Refrigerated storage | No |
| `PRESS` | Panini/flatbread pressing | No |
| `C_VAP` / `C-VAP` | Controlled vapor cooking | No - but has Max Hold Time |
| `HOT_BOX` | Hot holding | No |
| `MICROWAVE` | Reheating | No |
| `PITCO` | Commercial fryer | No |
| `RICE_COOKER` | Rice preparation | No |
| `STEAM_TABLE` | Steam heating | No - but has Max Hold Time |
| `TOASTER` | Toasting | No |

### Global Appliance Config

For `TURBO_OVEN`, `FRYER`, `PIZZA_CONVEYOR_OVEN`, and `CLAMSHELL`, a global appliance config is **required**:

```
Turbo Oven: "100/90 475°F" (percent time/windspeed temperature)
Fryer: "325°F" or "350°F"
Pizza Conveyor: Conveyor setting
Clamshell: "Top: 450F, Bottom: 450F, Gap: 308mm"
```

---

## Parking Spots

For COMPLETE and VEND activities, a parking spot is required:

| Parking Spot | Description |
|--------------|-------------|
| `AMBIENT` | Room temperature holding |
| `WARM` | Heated holding |

---

## Step Structure

Each step within a task contains:

### Step-Level Fields

| Field | Description | Required |
|-------|-------------|----------|
| `step_order` | Integer 1-99, determines sequence | Yes |
| `step` | Display step number (can match order) | Yes |
| `mapping_option` | Customization option this step applies to | No |
| `activity` | COOK, GARNISH, COMPLETE, VEND, PACKAGE | Yes |
| `appliance` | Equipment used (COOK activity only) | For COOK |
| `step_time` | Total time for step (minutes:seconds) | Yes if COOK/GARNISH |
| `cook_time` | Active cooking time | For COOK |
| `resting_time` | Resting/cooling time | No |
| `max_hold_time` | Maximum hold time (for COOK with certain appliances) | No |
| `batch_limit` | Max items per batch (>=1 for COOK) | For COOK |
| `step_dependency` | Comma-separated list of prerequisite steps | No |
| `parking_spot` | AMBIENT or WARM (for COMPLETE/VEND) | For COMPLETE/VEND |

### Step Dependencies

- Format: comma-separated step orders (e.g., "1, 2, 3")
- Dependencies must be steps with order less than current step
- No cyclical dependencies allowed (1→2→1 invalid)
- No redundant dependencies (if 2 depends on 1, and 3 depends on 2, then 3 shouldn't also list 1)

### Sub-Step Fields

Each step contains one or more sub-steps with:

| Field | Description |
|-------|-------------|
| `sub_steps_order` | Order within the step |
| `sub_steps_title` | Instruction title (required) |
| `mapping_option_item` | BOM item or customization option this applies to |
| `text_color` | Visual highlight (Green, Beet, Orange, Grape, Violet, Juniper) |
| `is_cooking_eligible` | Whether this sub-step represents a cooked component |
| `kds_portion` | Use KDS portion conversion for display |
| `hot_hold_eligible_step` | Can this step use hot hold instruction |

---

## Hot Hold System

Hot hold allows pre-cooking items and holding them warm, then re-thermalizing when ordered.

### Hot Hold Eligible Step

A step can be marked as "Hot Hold eligible" when:
1. Activity = COOK
2. Sub-step mapped to a hot hold eligible item (packaged item with HH instructions)
3. Or sub-step mapped to customization option whose related item is HH eligible

### Hot Hold vs A La Minute Views

- **A La Minute View**: Default cooking instructions (make when ordered)
- **Hot Hold View**: Retherm → Hold workflow for pre-cooked items

When a step has a hot hold eligible sub-step, users can toggle between A La Minute and Hot Hold views.

### Hot Hold Step Display

When showing Hot Hold instructions:
- Activity-Appliance: `Retherm-{appliance}, Holding-{appliance}`
- Time: `Step time: {labor + retherm}, Retherm time: {retherm}, Hold time: {hold}`
- Parameters: `Cooking Phase: Hot Hold, Batch Limit: {limit}, Parking Spot`

---

## Apply To: Restaurants and Options

Line builds can be scoped to specific restaurants and/or customization options.

### Apply to Restaurants

| Value | Behavior |
|-------|----------|
| `All` | Default line build for all restaurants |
| Specific HDRs | Exception line build for named restaurants |

### Apply to Option/Option Value

When "Multi versions vs options" toggle is enabled:
- Create different line builds per customization selection
- Example: Different line build for "White Rice" vs "Brown Rice" choice

### Combinations

Line builds can combine restaurant and option scoping:
- Line Build 1: Restaurant A, Choose Rice = White Rice
- Line Build 2: Restaurant A, Choose Rice = Brown Rice
- Line Build 3: Restaurant B, Choose Rice = White Rice

---

## Customization Mapping

Steps and sub-steps can map to customization options:

| Option Type | Mapping Format |
|-------------|----------------|
| Mandatory Choice | `Option Name - Option Value` |
| Optional Addition | `Option Name - Option Value` |
| Dish Preference | `Option Name - Option Value` |
| Extra Request | `Option Name - Option Value` |
| On the Side | `Option Value on the side` / `Option Value NOT on the side` |
| Optional Subtraction | `Keep {item}` / `No {item}` |

**Note:** "Normal" and "Keep" customization options are removed from step-level mapping. Use BOM line items instead.

---

## Query Patterns

### Get Line Build for a Menu Item

```sql
SELECT
  ilb.item_number,
  ei.name as item_name,
  ilb.procedures_step_order,
  ilb.procedures_cooking_phase,
  ilb.procedures_appliance,
  ilb.procedures_activity,
  ilb.cooking_time,
  ilb.hold_time
FROM `secure-recipe-prod.recipe_v2.item_line_builds` ilb
LEFT JOIN `secure-recipe-prod.recipe_v2.effective_items` ei
  ON ilb.item_number = CAST(ei.item_number AS STRING)
  AND ei.deleted = false
WHERE ilb.item_number = '8009068'
  AND CURRENT_TIMESTAMP() BETWEEN TIMESTAMP(ilb.service_start_time) AND TIMESTAMP(ilb.service_end_time)
ORDER BY ilb.procedures_step_order;
```

### Find Items by Appliance

```sql
SELECT DISTINCT
  ilb.item_number,
  ei.name as item_name,
  ilb.procedures_appliance,
  ilb.cooking_time
FROM `secure-recipe-prod.recipe_v2.item_line_builds` ilb
LEFT JOIN `secure-recipe-prod.recipe_v2.effective_items` ei
  ON ilb.item_number = CAST(ei.item_number AS STRING)
  AND ei.deleted = false
WHERE ilb.procedures_appliance = 'FRYER'
  AND ei.object_type = 'MENU'
  AND ei.item_status = 'ACTIVE'
  AND CURRENT_TIMESTAMP() BETWEEN TIMESTAMP(ilb.service_start_time) AND TIMESTAMP(ilb.service_end_time)
ORDER BY ei.name;
```

### Analyze Cooking Phase Distribution

```sql
SELECT
  ilb.procedures_cooking_phase,
  COUNT(DISTINCT ilb.item_number) as item_count
FROM `secure-recipe-prod.recipe_v2.item_line_builds` ilb
WHERE CURRENT_TIMESTAMP() BETWEEN TIMESTAMP(ilb.service_start_time) AND TIMESTAMP(ilb.service_end_time)
  AND ilb.procedures_cooking_phase IS NOT NULL
GROUP BY ilb.procedures_cooking_phase
ORDER BY item_count DESC;
```

### Find Hot-Hold Eligible Items

```sql
SELECT DISTINCT
  ilb.item_number,
  ei.name as item_name,
  ilb.hold_time
FROM `secure-recipe-prod.recipe_v2.item_line_builds` ilb
LEFT JOIN `secure-recipe-prod.recipe_v2.effective_items` ei
  ON ilb.item_number = CAST(ei.item_number AS STRING)
  AND ei.deleted = false
WHERE ilb.is_hot_hold_eligible_selected = true
  AND ei.object_type = 'MENU'
  AND ei.item_status = 'ACTIVE'
  AND CURRENT_TIMESTAMP() BETWEEN TIMESTAMP(ilb.service_start_time) AND TIMESTAMP(ilb.service_end_time)
ORDER BY ei.name;
```

### Line Build by Restaurant

```sql
SELECT
  ilb.restaurant_id,
  ilb.item_number,
  ei.name as item_name,
  ilb.procedures_appliance
FROM `secure-recipe-prod.recipe_v2.item_line_builds` ilb
LEFT JOIN `secure-recipe-prod.recipe_v2.effective_items` ei
  ON ilb.item_number = CAST(ei.item_number AS STRING)
  AND ei.deleted = false
WHERE ilb.restaurant_id IS NOT NULL
  AND CURRENT_TIMESTAMP() BETWEEN TIMESTAMP(ilb.service_start_time) AND TIMESTAMP(ilb.service_end_time)
ORDER BY ilb.restaurant_id, ei.name
LIMIT 100;
```

### Find Items by Activity Type

```sql
SELECT DISTINCT
  ilb.item_number,
  ei.name as item_name,
  ilb.procedures_activity,
  ilb.procedures_appliance
FROM `secure-recipe-prod.recipe_v2.item_line_builds` ilb
LEFT JOIN `secure-recipe-prod.recipe_v2.effective_items` ei
  ON ilb.item_number = CAST(ei.item_number AS STRING)
  AND ei.deleted = false
WHERE ilb.procedures_activity = 'COOK'  -- or VEND, GARNISH, COMPLETE
  AND ei.object_type = 'MENU'
  AND CURRENT_TIMESTAMP() BETWEEN TIMESTAMP(ilb.service_start_time) AND TIMESTAMP(ilb.service_end_time)
ORDER BY ei.name;
```

### Find Items with Turbo Oven and Appliance Config

```sql
SELECT DISTINCT
  ilb.item_number,
  ei.name as item_name,
  ilb.procedures_appliance,
  ilb.cooking_time
FROM `secure-recipe-prod.recipe_v2.item_line_builds` ilb
LEFT JOIN `secure-recipe-prod.recipe_v2.effective_items` ei
  ON ilb.item_number = CAST(ei.item_number AS STRING)
  AND ei.deleted = false
WHERE ilb.procedures_appliance = 'TURBO_OVEN'
  AND ei.object_type = 'MENU'
  AND ei.item_status = 'ACTIVE'
  AND CURRENT_TIMESTAMP() BETWEEN TIMESTAMP(ilb.service_start_time) AND TIMESTAMP(ilb.service_end_time)
ORDER BY ei.name;
```

### Analyze Multi-Step Line Builds

```sql
SELECT
  ilb.item_number,
  ei.name as item_name,
  COUNT(DISTINCT ilb.procedures_step_order) as step_count,
  ARRAY_AGG(DISTINCT ilb.procedures_activity) as activities,
  ARRAY_AGG(DISTINCT ilb.procedures_appliance IGNORE NULLS) as appliances
FROM `secure-recipe-prod.recipe_v2.item_line_builds` ilb
LEFT JOIN `secure-recipe-prod.recipe_v2.effective_items` ei
  ON ilb.item_number = CAST(ei.item_number AS STRING)
  AND ei.deleted = false
WHERE ei.object_type = 'MENU'
  AND ei.item_status = 'ACTIVE'
  AND CURRENT_TIMESTAMP() BETWEEN TIMESTAMP(ilb.service_start_time) AND TIMESTAMP(ilb.service_end_time)
GROUP BY ilb.item_number, ei.name
HAVING COUNT(DISTINCT ilb.procedures_step_order) > 3
ORDER BY step_count DESC;
```

## Advanced Query Patterns

### Extract Full Line Build Details from Nested JSON

The most comprehensive way to extract line build data is from the nested `item_line_build` JSON in `item_versions`:

```sql
WITH iv_base AS (
  SELECT
    item_number,
    name,
    sold_status,
    version_status,
    item_line_build,
    version_id,
    effective
  FROM `secure-recipe-prod.recipe_v2.item_versions`
  WHERE object_type = 'MENU'
    AND item_line_build IS NOT NULL
    AND effective = true
    AND item_status != 'DORMANT'
    AND deleted = false
),
line_build AS (
  SELECT iv_base.*, lb
  FROM iv_base,
  UNNEST(JSON_EXTRACT_ARRAY(iv_base.item_line_build, '$.line_builds')) AS lb
),
lb_task AS (
  SELECT
    line_build.*,
    t,
    JSON_EXTRACT(t, '$.customization_option') AS t_rc,
    JSON_EXTRACT_SCALAR(t, '$.name') AS t_name
  FROM line_build,
  UNNEST(JSON_EXTRACT_ARRAY(line_build.lb, '$.tasks')) AS t
),
lb_procedure AS (
  SELECT
    lb_task.*,
    p,
    JSON_VALUE(p, '$.related_item_number') AS p_ri,
    JSON_EXTRACT(p, '$.customization_option') AS p_rc,
    SAFE_CAST(JSON_VALUE(p, '$.order') AS INT64) AS p_order,
    JSON_VALUE(p, '$.activity') AS activity
  FROM lb_task,
  UNNEST(JSON_EXTRACT_ARRAY(lb_task.t, '$.procedures')) AS p
),
lb_ps AS (
  SELECT
    lb_procedure.*,
    ps,
    JSON_VALUE(ps, '$.related_item_number') AS ps_ri,
    JSON_EXTRACT(ps, '$.related_customization_option') AS ps_rc,
    SAFE_CAST(JSON_VALUE(ps, '$.order') AS INT64) AS ps_order
  FROM lb_procedure,
  UNNEST(JSON_EXTRACT_ARRAY(lb_procedure.p, '$.procedure_steps')) AS ps
)
SELECT
  item_number,
  name,
  sold_status,
  version_status,
  version_id,
  effective,
  t_name AS task_name,
  p_order AS procedure_order,
  activity,
  t_rc AS task_related_customization,
  p_ri AS procedure_related_item,
  p_rc AS procedure_related_customization,
  ps_ri AS procedure_step_related_item,
  ps_rc AS procedure_step_related_customization
FROM lb_ps
WHERE effective = true
ORDER BY version_id, p_order, ps_order;
```

### Find VEND and COMPLETE Activities with Mappings

Find all line builds that have VEND or COMPLETE activities with mapped customizations or related items:

```sql
WITH iv_base AS (
  SELECT item_number, name, sold_status, version_status, item_line_build, version_id, effective
  FROM `secure-recipe-prod.recipe_v2.item_versions`
  WHERE object_type = 'MENU'
    AND item_line_build IS NOT NULL
    AND effective = true
    AND item_status != 'DORMANT'
    AND deleted = false
),
line_build AS (
  SELECT iv_base.*, lb
  FROM iv_base,
  UNNEST(JSON_EXTRACT_ARRAY(iv_base.item_line_build, '$.line_builds')) AS lb
),
lb_task AS (
  SELECT line_build.*, t,
    JSON_EXTRACT(t, '$.customization_option') AS t_rc,
    JSON_EXTRACT_SCALAR(t, '$.name') AS t_name
  FROM line_build,
  UNNEST(JSON_EXTRACT_ARRAY(line_build.lb, '$.tasks')) AS t
),
lb_procedure AS (
  SELECT lb_task.*, p,
    JSON_EXTRACT(p, '$.related_item_number') AS p_ri,
    JSON_EXTRACT(p, '$.customization_option') AS p_rc,
    SAFE_CAST(JSON_EXTRACT(p, '$.order') AS INT64) AS p_order,
    JSON_EXTRACT(p, '$.activity') AS activity
  FROM lb_task,
  UNNEST(JSON_EXTRACT_ARRAY(lb_task.t, '$.procedures')) AS p
),
lb_ps AS (
  SELECT lb_procedure.*, ps,
    JSON_EXTRACT(ps, '$.related_item_number') AS ps_ri,
    JSON_EXTRACT(ps, '$.related_customization_option') AS ps_rc,
    SAFE_CAST(JSON_EXTRACT(ps, '$.order') AS INT64) AS ps_order
  FROM lb_procedure,
  UNNEST(JSON_EXTRACT_ARRAY(lb_procedure.p, '$.procedure_steps')) AS ps
)
SELECT
  item_number, name, sold_status, version_status, version_id,
  t_name AS task_name, p_order, activity,
  t_rc AS task_related_customization,
  p_ri AS procedure_related_item,
  p_rc AS procedure_related_customization,
  ps_ri AS p_step_related_item,
  ps_rc AS p_step_related_customization
FROM lb_ps
WHERE effective = true
  AND activity IN ('"VEND"', '"COMPLETE"')
  AND (t_rc IS NOT NULL OR p_ri IS NOT NULL OR p_rc IS NOT NULL OR ps_ri IS NOT NULL OR ps_rc IS NOT NULL)
ORDER BY version_id, p_order, ps_order;
```

### Find Menu Items with Multiple Tasks

Identify menu items that have complex line builds with 2+ parallel tasks:

```sql
WITH iv_base AS (
  SELECT item_number, item_line_build, object_type, version_id, effective
  FROM `secure-recipe-prod.recipe_v2.item_versions`
  WHERE object_type = 'MENU'
    AND item_line_build IS NOT NULL
    AND effective = true
    AND item_status != 'DORMANT'
    AND deleted = false
),
line_build AS (
  SELECT iv_base.*, lb
  FROM iv_base,
  UNNEST(JSON_EXTRACT_ARRAY(iv_base.item_line_build, '$.line_builds')) AS lb
),
lb_task AS (
  SELECT
    item_number,
    version_id,
    object_type,
    JSON_EXTRACT(t, '$.id') AS t_id,
    JSON_EXTRACT_SCALAR(t, '$.name') AS t_name
  FROM line_build,
  UNNEST(JSON_EXTRACT_ARRAY(line_build.lb, '$.tasks')) AS t
)
SELECT item_number, version_id, object_type, COUNT(*) AS task_count
FROM lb_task
GROUP BY item_number, version_id, object_type
HAVING COUNT(*) >= 2;
```

### Get All Related Items in Line Build

Extract all related items from line builds, resolving customization mappings:

```sql
WITH iv_base AS (
  SELECT item_number, name, item_line_build, version_id, effective
  FROM `secure-recipe-prod.recipe_v2.item_versions`
  WHERE object_type = 'MENU'
    AND item_status != 'DORMANT'
    AND version_status = 'FINAL'
    AND deleted = false
    AND sold_status = 'FOR_SALE'
    AND item_line_build IS NOT NULL
),
line_build AS (
  SELECT iv_base.*, lb
  FROM iv_base,
  UNNEST(JSON_EXTRACT_ARRAY(iv_base.item_line_build, '$.line_builds')) AS lb
),
lb_task AS (
  SELECT line_build.*, t,
    JSON_EXTRACT(t, '$.customization_option') AS t_rc,
    JSON_EXTRACT_SCALAR(t, '$.name') AS t_name
  FROM line_build,
  UNNEST(JSON_EXTRACT_ARRAY(line_build.lb, '$.tasks')) AS t
),
lb_procedure AS (
  SELECT lb_task.*, p,
    JSON_EXTRACT_SCALAR(p, '$.related_item_number') AS p_ri,
    JSON_EXTRACT(p, '$.customization_option') AS p_rc,
    SAFE_CAST(JSON_EXTRACT(p, '$.order') AS INT64) AS p_order,
    JSON_EXTRACT_SCALAR(p, '$.activity') AS activity
  FROM lb_task,
  UNNEST(JSON_EXTRACT_ARRAY(lb_task.t, '$.procedures')) AS p
),
lb_ps AS (
  SELECT lb_procedure.*, ps,
    JSON_EXTRACT_SCALAR(ps, '$.related_item_number') AS ps_ri,
    JSON_EXTRACT(ps, '$.related_customization_option') AS ps_rc,
    SAFE_CAST(JSON_EXTRACT(ps, '$.order') AS INT64) AS ps_order
  FROM lb_procedure,
  UNNEST(JSON_EXTRACT_ARRAY(lb_procedure.p, '$.procedure_steps')) AS ps
),
customization AS (
  SELECT
    iv.item_number AS parent_item_number,
    JSON_VALUE(customization_option_value_raw, '$.id') AS c_opt_id,
    JSON_VALUE(customization_option_value_item_raw, '$.item_number') AS child_item_number
  FROM `secure-recipe-prod.recipe_v2.item_versions` iv,
    UNNEST(JSON_EXTRACT_ARRAY(iv.item_customization, '$.options')) AS customization_options_raw,
    UNNEST(JSON_EXTRACT_ARRAY(customization_options_raw, '$.option_values')) AS customization_option_value_raw,
    UNNEST(JSON_EXTRACT_ARRAY(customization_option_value_raw, '$.items')) AS customization_option_value_item_raw
  WHERE item_status != 'DORMANT'
    AND deleted = false
    AND object_type = 'MENU'
    AND effective = true
    AND JSON_VALUE(customization_options_raw, '$.type') IN ('MANDATORY_CHOICE', 'OPTIONAL_ADDITION')
),
lb_extracted AS (
  SELECT
    item_number AS menu_item_number,
    name AS menu_item_name,
    t_name,
    activity,
    COALESCE(p_ri, ps_ri) AS related_item,
    JSON_EXTRACT_SCALAR(COALESCE(ps_rc, p_rc), '$.option_value_id') AS rc_opt_id
  FROM lb_ps
  WHERE effective = true
  ORDER BY version_id, p_order, ps_order
)
SELECT
  l.menu_item_number,
  l.menu_item_name,
  l.t_name,
  l.activity,
  COALESCE(l.related_item, c.child_item_number) AS line_build_related_item_number,
  COALESCE(i.name, i2.name) AS line_build_related_item_name
FROM lb_extracted l
LEFT JOIN customization c ON l.rc_opt_id = c.c_opt_id
LEFT JOIN `secure-recipe-prod.recipe_v2.item_versions` i ON i.item_number = l.related_item AND i.effective = true
LEFT JOIN `secure-recipe-prod.recipe_v2.item_versions` i2 ON i2.item_number = c.child_item_number AND i2.effective = true
WHERE COALESCE(l.related_item, c.child_item_number) IS NOT NULL;
```

### KDS Portion Validation: Find Missing Conversions

Find line build steps where KDS portion is selected but the mapped item doesn't have KDS portion conversions defined:

```sql
WITH iv_base AS (
  SELECT item_number, name, version_id, service_start_time, service_end_time, item_line_build
  FROM `secure-recipe-prod.recipe_v2.item_versions`
  WHERE object_type = 'MENU'
    AND item_line_build IS NOT NULL
    AND deleted = false
    AND item_status != 'DORMANT'
    AND service_end_time > CURRENT_DATETIME()
),
line_build AS (
  SELECT iv_base.*, lb, (lb_index+1) AS line_build_index
  FROM iv_base,
  UNNEST(JSON_EXTRACT_ARRAY(iv_base.item_line_build, '$.line_builds')) AS lb WITH OFFSET AS lb_index
),
lb_task AS (
  SELECT line_build.*, t, JSON_VALUE(t, '$.name') AS task_name
  FROM line_build,
  UNNEST(JSON_EXTRACT_ARRAY(line_build.lb, '$.tasks')) AS t
),
lb_procedure AS (
  SELECT lb_task.item_number, lb_task.name, lb_task.version_id,
    lb_task.service_start_time, lb_task.service_end_time, lb_task.line_build_index,
    lb_task.task_name, p,
    JSON_VALUE(p, '$.activity') AS activity,
    SAFE_CAST(JSON_VALUE(p, '$.order') AS INT64) AS procedure_order
  FROM lb_task,
  UNNEST(JSON_EXTRACT_ARRAY(lb_task.t, '$.procedures')) AS p
),
lb_ps AS (
  SELECT lb_procedure.*, ps,
    SAFE_CAST(JSON_VALUE(ps, '$.order') AS INT64) AS step_order,
    JSON_VALUE(ps, '$.title') AS step_title,
    JSON_VALUE(ps, '$.cook_readable_item_number') AS cook_readable_item_number
  FROM lb_procedure,
  UNNEST(JSON_EXTRACT_ARRAY(lb_procedure.p, '$.procedure_steps')) AS ps
  WHERE JSON_VALUE(ps, '$.is_cook_readable_qty_selected') = 'true'
),
cook_readable_items AS (
  SELECT item_number, name, kds_portion_conversions
  FROM `secure-recipe-prod.recipe_v2.item_versions`
  WHERE deleted = false AND effective = true
)
SELECT DISTINCT
  lb_ps.item_number AS menu_item_number,
  lb_ps.name AS menu_item_name,
  lb_ps.version_id AS menu_item_version_id,
  lb_ps.service_start_time,
  lb_ps.service_end_time,
  lb_ps.line_build_index,
  lb_ps.task_name,
  lb_ps.activity,
  lb_ps.procedure_order,
  lb_ps.step_order,
  lb_ps.step_title,
  lb_ps.cook_readable_item_number,
  cri.name AS cook_readable_item_name,
  cri.kds_portion_conversions
FROM lb_ps
LEFT JOIN cook_readable_items cri
  ON lb_ps.cook_readable_item_number = cri.item_number
WHERE cri.kds_portion_conversions IS NULL
  OR JSON_EXTRACT_ARRAY(cri.kds_portion_conversions) IS NULL
  OR ARRAY_LENGTH(JSON_EXTRACT_ARRAY(cri.kds_portion_conversions)) = 0
ORDER BY lb_ps.item_number, lb_ps.version_id, lb_ps.line_build_index, lb_ps.procedure_order, lb_ps.step_order;
```

### Find 88* Items Used by KDS Portion

Find which menu items reference specific 88* packaged items in KDS portion fields:

```sql
WITH line_build_data AS (
  SELECT
    iv.item_number,
    iv.name,
    iv.version_id,
    iv.version_status,
    iv.effective,
    JSON_VALUE(ps, '$.cook_readable_item_number') AS cook_readable_item_number
  FROM `secure-recipe-prod.recipe_v2.item_versions` iv,
    UNNEST(JSON_EXTRACT_ARRAY(iv.item_line_build, '$.line_builds')) AS lb,
    UNNEST(JSON_EXTRACT_ARRAY(lb, '$.tasks')) AS t,
    UNNEST(JSON_EXTRACT_ARRAY(t, '$.procedures')) AS p,
    UNNEST(JSON_EXTRACT_ARRAY(p, '$.procedure_steps')) AS ps
  WHERE iv.item_line_build IS NOT NULL
    AND iv.service_end_time > CURRENT_DATETIME()
    AND iv.deleted = false
    AND iv.item_status <> 'DORMANT'
)
SELECT DISTINCT
  item_number,
  name,
  version_id,
  version_status,
  effective,
  cook_readable_item_number
FROM line_build_data
WHERE cook_readable_item_number LIKE '88%'  -- Filter for 88* packaged items
ORDER BY item_number, cook_readable_item_number;
```

---

## Audit Table

For tracking line build changes over time:

```sql
-- Line build change history
SELECT *
FROM `secure-recipe-prod.mongo_batch_recipe_v2.item_line_build_histories`
WHERE item_number = '8009068'
ORDER BY updated_time DESC
LIMIT 10;
```

---

## Validation Rules

Line builds have extensive validation at multiple levels.

### Line Build Level Validations

| Rule | Error Message |
|------|---------------|
| Duplicate task mapping | "Unable to save. Cannot map the same option to multiple tasks." |
| Missing Apply to Option value | "Please set apply to option/option values" |
| Duplicate line build exists | "This Line Build has already existed" |

### Task Level Validations

| Rule | Error Message |
|------|---------------|
| Task mapping conflicts with line build | "The following task is conflict with the line build: task {name}" |
| Task step conflicts with task option | "The following sub-step/step is conflict with the task: step # in task {name}" |
| Duplicate VEND mapping in task | Cannot map same BOM item/option to multiple VEND steps in same task |

### Step Level Validations

**Complete Step Rules:**
| Rule | Error Message |
|------|---------------|
| No complete step | "Must have at least one Complete step: task {name}" |
| Complete not last step | "The complete step must be the last step except Bag Steps: {task name}" |
| Duplicate complete step order | "Complete step order must be unique: task {name}" |
| Same option value on multiple completes | "Duplicated complete step" |

**Step Order Rules:**
| Rule | Error Message |
|------|---------------|
| Duplicate step order (different options) | "Duplicate step order: step #, step # in {task name}" |
| Cyclical dependency | "Step dependency should be in format of '1, 2, 3'" |
| Dependency on later step | Step order must be greater than all dependencies |

**Activity-Specific Rules:**
| Activity | Validation |
|----------|------------|
| COOK | Appliance required; step time > cook time; cook time > 0; batch limit >= 1 |
| GARNISH | Step time > 0; cook time = 0; resting time = 0 |
| COMPLETE | Parking spot required; must have sub-step with title |
| VEND | Mapping item required; parking spot required |

### Sub-Step Level Validations

| Rule | Error Message |
|------|---------------|
| Option conflicts with step | "Option value(s) of sub step(s) is conflict with the Option Value of its step" |
| Missing mapping option when step has one | "Sub step (in step #) is missing mapping option" |
| KDS Portion missing conversion | "Missing KDS Portion Conversion, please uncheck it or revise it on component item {number}" |

### Hot Hold Validations (Warnings)

| Scenario | Warning |
|----------|---------|
| HH item missing HH eligible step | "The following hot hold item/customization option is missing Hot Hold eligible step" |
| Multiple HH eligible steps for same item | "The following HH item/customization option has multi Hot Hold eligible steps" |
| First cook step not HH eligible | "The first cook step of the following hot hold item(s) is not Hot Hold eligible" |
| Appliance mismatch with HH retherm | "The hot holding eligible component has no supported appliance" |

---

## Service Window Filtering

Line builds use service windows like other Cookbook tables:

```sql
AND CURRENT_TIMESTAMP() BETWEEN TIMESTAMP(service_start_time) AND TIMESTAMP(service_end_time)
```

---

## T-Shirt Sizing

Line builds support T-shirt sizing for menu items, introduced in August 2025.

---

## Integration with Sequencing

Line build data informs kitchen sequencing. See the **wonder-sequencing** skill for:
- How line builds affect sequence planning
- Batch group assignments
- Kitchen context analysis

---

## Integration with KDS

Line build data is sent to the Kitchen Display System (KDS) via API, including:
- Cooking instructions per step
- Customization-driven step visibility
- Hot hold instructions when applicable
- KDS portion quantities for ingredients
- Mapping item/option information for chef guidance

---

## Deprecation Notes

### Deprecated Activities

> **Deprecated**: The `PACKAGE` and `BAG` activities are deprecated. They may appear in historical data but should not be used in new line builds.

When querying historical data, you may encounter these values:

```sql
-- Filter out deprecated activities for current analysis
WHERE procedures_activity NOT IN ('PACKAGE', 'BAG')
```

### Non-Existent Enum Values

The following values documented in older references do **NOT** exist in the current codebase:

| Category | Non-Existent Values | Notes |
|----------|---------------------|-------|
| Appliances | `RETHERM`, `HOLDING` | Hot hold uses existing appliances with HH configuration |
| Cooking Phases | `HOT_HOLD`, `A_LA_MINUTE` | Hot hold is managed via flags, not phases |

### Appliance Naming

> **Note**: The appliance is named `CLAMSHELL` in the codebase, not `CLAMSHELL_GRIDDLE`. Queries should use `CLAMSHELL`.

```sql
-- Correct
WHERE procedures_appliance = 'CLAMSHELL'

-- Incorrect (may not match)
WHERE procedures_appliance = 'CLAMSHELL_GRIDDLE'
```

---

## Related Documentation

- [recipes-procedures.md](recipes-procedures.md) - Detailed cooking instructions
- [assembly-instructions.md](assembly-instructions.md) - Assembly after cooking
- [../core/service-windows.md](../core/service-windows.md) - Recipe versioning

---

## Code References (Java Codebase)

> **Codebase**: `master-data-management-2`
> **Validated**: 2026-01-28

### Domain Models

- **ItemLineBuild**: `backend/domain-library/src/main/java/app/internalrecipe/item/linebuild/ItemLineBuild.java`
  - Embedded in ItemVersion.itemLineBuild field
  - Key fields: `isMultipleUsage`, `isMultipleVersion`, `lineBuilds`, `status`, `pendingUpdateInfoList`
  - Nested classes: `LineBuild`, `Task`, `Procedure`, `ProcedureStep`, `CustomizationOption`

- **ItemLineBuild.LineBuild**: Line build configuration
  - Fields: `id`, `restaurantIds`, `applyOptionId`, `applyOptionValueIds`, `tasks`

- **ItemLineBuild.Task**: Parallel cooking workflow
  - Fields: `id`, `name`, `customizationOption`, `procedures`

- **ItemLineBuild.Procedure**: Individual step in task
  - Fields: `order`, `activity`, `appliance`, `cookingPhase`, `batchLimit`, `applianceConfigId`, `parkingSpot`, `procedureSteps`
  - Timing: `cookingUsageSeconds`, `restingUsageSeconds`, `holdUsageSeconds`, `stepUsageSeconds`

- **ItemLineBuild.ProcedureStep**: Sub-step detail
  - Fields: `order`, `title`, `relatedItemNumber`, `isHotHoldEligibleSelected`, `isCookReadableQtySelected`, `textColor`

- **ItemLineBuildHistory**: `backend/domain-library/src/main/java/app/internalrecipe/item/linebuild/ItemLineBuildHistory.java`
  - MongoDB Collection: `item_line_build_histories`
  - Audit trail for line build changes

### Enums

- **LineBuildProcedureActivity**: `backend/domain-library/src/main/java/app/internalrecipe/item/linebuild/LineBuildProcedureActivity.java`
  - Active: `COOK`, `GARNISH`, `COMPLETE`, `VEND`
  - **@Deprecated (6)**: `PACKAGE`, `BAG`, `ADD_MIX`, `RESTING`, `HOLD`, `THERMAL_HOLDING`

- **LineBuildProcedureAppliance**: `backend/domain-library/src/main/java/app/internalrecipe/item/linebuild/LineBuildProcedureAppliance.java`
  - Active: `TURBO_OVEN`, `WATER_BATH`, `FRIDGE`, `HOT_BOX`, `FRYER`, `PRESS`, `TOASTER`, `STEAM_TABLE`, `C_VAP`, `PITCO`, `CLAMSHELL`, `PIZZA_CONVEYOR_OVEN`, `RICE_COOKER`, `MICROWAVE`
  - **@Deprecated (8)**: `PASTA_COOKER`, `PIZZA_OVEN` (since 2024 Sprint 2), `ALTO_SHAAM`, `CARTER_HOFFMAN`, `COFFEE_MAKER`, `ESPRESSO_MACHINE`, `BLENDER`, `COMBI_OVEN`

- **LineBuildProcedureCookingPhase**: `backend/domain-library/src/main/java/app/internalrecipe/item/linebuild/LineBuildProcedureCookingPhase.java`
  - Values: `PRE_ROUTE_PREP`, `PRE_ORDER_PREP`, `PRE_COOKING`, `COOKING`, `POST_COOKING`

- **ParkingSpot**: `backend/domain-library/src/main/java/app/internalrecipe/item/linebuild/ParkingSpot.java`
  - Values: `AMBIENT`, `WARM`

- **ItemLineBuildStatus**: `backend/domain-library/src/main/java/app/internalrecipe/item/linebuild/ItemLineBuildStatus.java`
  - Values: `NONE`, `LINE_BUILD_CREATED`, `PENDING_UPDATE`

### Service Layer

- **BOItemLineBuildService**: `backend/internal-recipe-service/src/main/java/app/internalrecipe/item/service/BOItemLineBuildService.java`
  - Core line build CRUD operations

- **BOItemLineBuildErrorCheckServiceV2**: `backend/internal-recipe-service/src/main/java/app/internalrecipe/item/service/BOItemLineBuildErrorCheckServiceV2.java`
  - Validation logic for line build rules

- **BOItemLineBuildProcedureHotHoldService**: `backend/internal-recipe-service/src/main/java/app/internalrecipe/item/service/BOItemLineBuildProcedureHotHoldService.java`
  - Hot hold workflow management

- **BOCheckAndAlertItemLineBuildService**: `backend/internal-recipe-service/src/main/java/app/internalrecipe/item/service/BOCheckAndAlertItemLineBuildService.java`
  - Validation alerts and warnings

- **BulkItemLineBuildStructureService**: `backend/recipe-service-v2/src/main/java/app/recipev2/item/service/BulkItemLineBuildStructureService.java`
  - Bulk operations for line builds

### API Endpoints

- **BOItemLineBuildWebService**: `backend/internal-recipe-service-interface/src/main/java/app/internalrecipe/api/BOItemLineBuildWebService.java`
  - Line build CRUD endpoints

### @Deprecated Summary

| Category | Deprecated Values | Notes |
|----------|-------------------|-------|
| Activities | `PACKAGE`, `BAG`, `ADD_MIX`, `RESTING`, `HOLD`, `THERMAL_HOLDING` | Use `COOK`, `GARNISH`, `COMPLETE`, `VEND` |
| Appliances | `PASTA_COOKER`, `PIZZA_OVEN`, `ALTO_SHAAM`, `CARTER_HOFFMAN`, `COFFEE_MAKER`, `ESPRESSO_MACHINE`, `BLENDER`, `COMBI_OVEN` | Removed from HDR kitchens |
