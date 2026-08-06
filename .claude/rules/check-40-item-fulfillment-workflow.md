# Check 40 Item Fulfillment Workflow

When the user asks whether a batch of Cookbook 40\* items has a usable fulfillment option behind it — in natural language, not a fixed command — recognize it and read `.claude/skills/my-workflows/check-40-item-fulfillment.md` before doing anything else, then follow it.

## Recognize (match intent, not exact wording)

Don't wait for the exact phrase "fulfillment option" or a fully-formed sentence. Recognize the intent from much shorter or looser phrasings too, as long as it's clearly about whether 40\* items have fulfillment configured.

**中文（从完整到简短都要识别）：**
- "查一下这些40 item有没有fulfillment option"
- "这批40 item背后有没有可用的fulfillment"
- "40 item fulfillment异常排查/核查/检查"
- "查下这些40有没有fulfillment"
- "这些40有问题吗" / "这些40正常吗"（当上下文已经在聊fulfillment / 42 / 41 / SCC cutover时）
- 直接甩一批40\*编号，隐含"看看这些有没有fulfillment"的诉求，不解释太多

**English (short forms count too):**
- "check if these 40 items have a fulfillment option"
- "audit these 40 items for fulfillment gaps"
- "do these 40 items have fulfillment"
- A pasted list of 40\* item numbers with an implicit "check these" ask, in a fulfillment/42/41/SCC-cutover context

Input may be a plain list of item numbers, a list with an attached (possibly stale) 40→42 mapping, or just a couple of item numbers typed inline — don't require a specific format before recognizing the trigger.

## What To Do

1. Read `.claude/skills/my-workflows/check-40-item-fulfillment.md` in full before doing anything else
2. Follow its steps exactly: Step 0 scope the batch → Step 1 brand check → Step 2 fulfillment availability check → Step 3 report results

## Critical

- This is Bonnie's **personal** workflow skill (`my-workflows/`), read-only against BigQuery — never modify Cookbook/SCC data to test a finding.
- The allowed-brand list and the Wonder Café → Grab & Go exemption are defined in [[个人/missing fulfillment option 分析方法]] — don't hardcode a different list or invent new exemptions; if a batch surfaces a brand/concept combination not already covered there, ask Bonnie rather than guessing.
- Default to reporting results in-chat. Do not create a persistent report note unless Bonnie explicitly asks to save/archive it.
