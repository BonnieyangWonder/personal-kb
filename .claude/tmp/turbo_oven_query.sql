WITH
-- Target cookbook item numbers from the Confluence page
target_items AS (
  SELECT item_num FROM UNNEST([
    '4000064','4000075','4000104','4000117','4000118','4000242','4000243',
    '4000258','4000259','4000263','4000265','4000276','4000279','4000281',
    '4000285','4000304','4000316','4000323','4000330','4000337','4000367',
    '4000381','4000383','4000387','4000402','4000406','4000414','4000415',
    '4000416','4000421','4000428','4000430','4000436','4000440','4000451',
    '4000467','4000474','4000495','4000534','4000541','4000542','4000544',
    '4000550','4000552','4000558','4000568','4000572','4000573','4000636',
    '4000644','4000651','4000655','4000656','4000658','4000661','4000823',
    '4000824','4000826','4000834','4000837','4000843','4000848','4000850',
    '4000853','4000856','4000860','4000862','4000863','4000864','4000865',
    '4000866','4000867','4000869','4000872','4000873','7000026','7000029',
    '7000031','7000034','7000040'
  ]) AS item_num
),

-- Brand concept mapping for 4 brands
brand_concepts AS (
  SELECT DISTINCT item_number
  FROM `wonder-dw-prod-brd.master_data.recipe_concept_mapping`
  WHERE LOWER(concept_name) IN ('royal greens', 'limesalt', 'yasas', 'hanu poke')
),

-- Active menu items (non-dormant, effective, final version) with line builds
menu_items AS (
  SELECT
    iv.item_number,
    iv.item_name,
    iv.item_version_number,
    iv.item_version_uuid,
    iv.item_line_build,
    iv.item_customization
  FROM `wonder-dw-prod-brd.master_data.item_versions` iv
  JOIN brand_concepts bc ON iv.item_number = bc.item_number
  WHERE iv.object_type = 'MENU'
    AND iv.effective = TRUE
    AND iv.deleted = FALSE
    AND iv.item_status != 'DORMANT'
    AND iv.version_status = 'FINAL'
    AND iv.item_line_build IS NOT NULL
),

-- Extract procedures: only COOK with TURBO_OVEN
lb_procedures AS (
  SELECT
    mi.item_number,
    mi.item_name,
    mi.item_version_number,
    mi.item_version_uuid,
    mi.item_customization,
    -- Line build level: restaurant scope
    JSON_EXTRACT(lb, '$.restaurant_ids') AS restaurant_ids,
    JSON_EXTRACT_SCALAR(lb, '$.id') AS line_build_id,
    -- Task level
    JSON_EXTRACT_SCALAR(t, '$.name') AS task_name,
    JSON_EXTRACT(t, '$.customization_option') AS task_customization_option,
    -- Procedure level
    p,
    SAFE_CAST(JSON_EXTRACT_SCALAR(p, '$.order') AS INT64) AS proc_order,
    JSON_EXTRACT_SCALAR(p, '$.activity') AS activity,
    JSON_EXTRACT_SCALAR(p, '$.appliance') AS appliance,
    JSON_EXTRACT_SCALAR(p, '$.appliance_config_id') AS appliance_config_id,
    JSON_EXTRACT_SCALAR(p, '$.related_item_number') AS proc_related_item,
    JSON_EXTRACT(p, '$.customization_option') AS proc_customization_option
  FROM menu_items mi,
    UNNEST(JSON_EXTRACT_ARRAY(mi.item_line_build, '$.line_builds')) AS lb,
    UNNEST(JSON_EXTRACT_ARRAY(lb, '$.tasks')) AS t,
    UNNEST(JSON_EXTRACT_ARRAY(t, '$.procedures')) AS p
  WHERE JSON_EXTRACT_SCALAR(p, '$.activity') = 'COOK'
    AND JSON_EXTRACT_SCALAR(p, '$.appliance') = 'TURBO_OVEN'
),

-- Extract sub-steps
lb_substeps AS (
  SELECT
    lp.*,
    ps,
    SAFE_CAST(JSON_EXTRACT_SCALAR(ps, '$.order') AS INT64) AS step_order,
    JSON_EXTRACT_SCALAR(ps, '$.title') AS step_title,
    JSON_EXTRACT_SCALAR(ps, '$.related_item_number') AS step_related_item,
    JSON_EXTRACT(ps, '$.related_customization_option') AS step_related_customization_option
  FROM lb_procedures lp,
    UNNEST(JSON_EXTRACT_ARRAY(lp.p, '$.procedure_steps')) AS ps
),

-- Extract customization option value -> item_number mapping
-- Structure: options[].option_values[].items[].item_number
cust_option_values AS (
  SELECT
    iv.item_number AS menu_item_number,
    JSON_EXTRACT_SCALAR(opt_val, '$.id') AS option_value_id,
    JSON_EXTRACT_SCALAR(opt_val_item, '$.item_number') AS mapped_item_number
  FROM (
    SELECT DISTINCT item_number, item_customization
    FROM menu_items
    WHERE item_customization IS NOT NULL
      AND item_customization != ''
  ) iv,
    UNNEST(JSON_EXTRACT_ARRAY(iv.item_customization, '$.options')) AS opt,
    UNNEST(JSON_EXTRACT_ARRAY(opt, '$.option_values')) AS opt_val,
    UNNEST(JSON_EXTRACT_ARRAY(opt_val, '$.items')) AS opt_val_item
  WHERE JSON_EXTRACT_SCALAR(opt_val, '$.id') IS NOT NULL
    AND JSON_EXTRACT_SCALAR(opt_val_item, '$.item_number') IS NOT NULL
),

-- MATCH TYPE 1: Direct matches (step_related_item IN target_items)
direct_matches AS (
  SELECT DISTINCT
    ls.*,
    ls.step_related_item AS matched_item_number,
    'DIRECT' AS match_type
  FROM lb_substeps ls
  JOIN target_items ti ON ti.item_num = ls.step_related_item
  WHERE ls.step_related_item IS NOT NULL
),

-- MATCH TYPE 2: Title matches (step_title contains target item number)
title_matches AS (
  SELECT DISTINCT
    ls.*,
    ti.item_num AS matched_item_number,
    'TITLE' AS match_type
  FROM lb_substeps ls
  CROSS JOIN target_items ti
  WHERE ls.step_related_item IS NULL
    AND ls.step_title LIKE CONCAT('%', ti.item_num, '%')
),

-- MATCH TYPE 3: Indirect via customization option
-- Resolve step/procedure option_value_id -> customization option item_number -> target
indirect_matches AS (
  SELECT DISTINCT
    ls.*,
    cov.mapped_item_number AS matched_item_number,
    'CUSTOMIZATION' AS match_type
  FROM lb_substeps ls
  JOIN cust_option_values cov
    ON cov.menu_item_number = ls.item_number
    AND (
      JSON_EXTRACT_SCALAR(ls.step_related_customization_option, '$.option_value_id') = cov.option_value_id
      OR
      JSON_EXTRACT_SCALAR(ls.proc_customization_option, '$.option_value_id') = cov.option_value_id
    )
  JOIN target_items ti ON ti.item_num = cov.mapped_item_number
  WHERE ls.step_related_item IS NULL
),

-- Combine all matches
all_matches AS (
  SELECT * FROM direct_matches
  UNION ALL
  SELECT * FROM title_matches
  UNION ALL
  SELECT * FROM indirect_matches
),

-- Deduplicate
deduped AS (
  SELECT
    matched_item_number,
    item_number AS menu_item_number,
    item_name AS menu_item_name,
    item_version_number,
    activity,
    appliance,
    appliance_config_id,
    restaurant_ids,
    ANY_VALUE(task_name) AS task_name,
    ANY_VALUE(match_type) AS match_type
  FROM all_matches
  GROUP BY matched_item_number, menu_item_number, item_name, item_version_number,
           activity, appliance, appliance_config_id, restaurant_ids
)

-- Final output
SELECT
  d.matched_item_number AS component_item_number,
  ei.name AS component_item_name,
  d.menu_item_number,
  d.menu_item_name,
  d.item_version_number AS menu_item_version,
  d.activity,
  d.appliance,
  -- Format Global Appliance Config: "{percent_time}/{wind_speed} {temperature}°F"
  CASE
    WHEN gas.turbo_oven_config IS NOT NULL THEN
      CONCAT(
        JSON_EXTRACT_SCALAR(
          JSON_EXTRACT_ARRAY(gas.turbo_oven_config, '$.wind_speed_steps')[SAFE_OFFSET(0)],
          '$.percent_time'
        ),
        '/',
        JSON_EXTRACT_SCALAR(
          JSON_EXTRACT_ARRAY(gas.turbo_oven_config, '$.wind_speed_steps')[SAFE_OFFSET(0)],
          '$.wind_speed'
        ),
        ' ',
        JSON_EXTRACT_SCALAR(gas.turbo_oven_config, '$.temperature'),
        '°F'
      )
    ELSE NULL
  END AS global_appliance_config,
  -- Restaurant scope: NULL/empty = "All", otherwise show HDR UUIDs
  CASE
    WHEN d.restaurant_ids IS NULL THEN 'All'
    WHEN JSON_EXTRACT_SCALAR(d.restaurant_ids, '$[0]') IS NULL THEN 'All'
    ELSE TO_JSON_STRING(d.restaurant_ids)
  END AS line_build_apply_to_restaurant,
  d.match_type
FROM deduped d
LEFT JOIN `wonder-recipe-prod.recipe_v2.effective_items` ei
  ON d.matched_item_number = ei.item_number
  AND ei.deleted = FALSE
LEFT JOIN `wonder-recipe-prod.mongo_batch_recipe_v2.global_appliance_settings` gas
  ON d.appliance_config_id = gas._id
ORDER BY d.matched_item_number, d.menu_item_number;
