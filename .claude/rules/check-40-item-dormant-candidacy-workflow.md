# Check 40 Item / Menu Item Dormant Candidacy Workflow

When the user asks whether a batch of Cookbook 40\* items (or the menu items that use them) can be marked dormant — in natural language, not a fixed command — recognize it and read `.claude/skills/my-workflows/check-40-item-dormant-candidacy.md` before doing anything else, then follow it.

## Recognize (match intent, not exact wording)

Don't wait for a fully-formed sentence. Recognize the intent from shorter or looser phrasings too, as long as it's clearly about whether 40\* items or their consuming menu items are safe to dormant.

**中文（从完整到简短都要识别）：**
- "查下这个 Excel 里的 40 item 有没有被 menu item 用"
- "帮我看看这批 40 item 能不能 dormant"
- "这些 menu item 是否可以 dormant"
- "这批 40 item 的用法核查一下"
- "查一下有没有 menu item 或 hdr recipe 在用这些 40 item"
- 直接给一个本地 Excel 文件路径 + 一批 40 item/menu item 编号，隐含"看看谁在用、能不能下线"的诉求，不解释太多

**English (short forms count too):**
- "check which menu items use these 40 items"
- "can these 40 items be marked dormant"
- "audit this batch for dormant candidacy"
- "find no-usage 40 items in this file"
- A local Excel file path + a batch of 40/menu item numbers with an implicit "check usage, can we dormant these" ask

Input is normally a local Excel workbook (outside the vault, e.g. `~/Downloads/...`) with one or more sheets listing 40\* item numbers. May also be a follow-up on a workbook already being worked on in the current session (e.g. "add a sheet for X", "check for updates", "did anyone edit these recently") — recognize continuations of this workflow, not just the initial trigger.

## What To Do

1. Read `.claude/skills/my-workflows/check-40-item-dormant-candidacy.md` in full before doing anything else
2. Follow its steps: Step 0 scope the batch (watch the "F" suffix trap) → Step 1 usage query (BOM + customization, non-dormant/non-expired/non-preset) → Step 2 build/update Excel usage sheets → Step 3 dedupe into a Dormant Confirmation sheet → Step 4 recency check (human edits, excluding unreliable `is_system_action`) → Step 5 interpret without auto-classifying → Step 6 report

## Critical

- This is Bonnie's **personal** workflow skill (`my-workflows/`), read-only against BigQuery — never modify Cookbook data to test a finding.
- The only file this workflow writes to is the local Excel workbook (adding/updating sheets and cells) — never touch vault notes as part of it, and never overwrite Bonnie's own manual edits to that workbook (column reorders, added notes columns, manual annotations) without being asked.
- Never strip non-numeric characters from a 40\* item number when scoping the batch — see the skill file's Step 0 and [[Z01-Resource/CB-bigquery/playbooks/data-research-patterns.md]] §13.1 for why.
- Never treat `item_version_change_logs.is_system_action = false` as sufficient proof of a human edit on its own — see the skill file's Step 4 and playbook §14.
- Never auto-classify an item as dormant-safe or dormant-unsafe from status fields (`R&D`/`DRAFT`) alone — always leave the final call to a human (skill file's Step 5).
- Default to reporting results in-chat. Do not create a persistent report note unless Bonnie explicitly asks to save/archive it (then follow `report-paths.md`).
