# Cookbook RA Workflow

When the user asks for a Cookbook requirements analysis — in natural language, not a fixed command — recognize it and read `.claude/skills/my-workflows/cookbook-ra.md` before doing anything else, then follow it.

## Recognize (match intent, not exact wording)

**中文：**
- "分析下 XX 需求"
- "帮我分析一下这个需求"
- "RA 一下" / "ra 分析"
- A Jira ticket link / Confluence link / screenshot(s), handed over with an implicit ask like "cookbook 要怎么支持这个"

**English:**
- "requirements analysis for X"
- "analyze this requirement"
- "what would it take to support X"
- A Jira ticket link / Confluence link / screenshot(s) with an implicit ask for how Cookbook should support it

Input may be plain text, a ticket/Confluence link, one or more screenshots, or any mix — do not wait for a specific format before recognizing the trigger.

## What To Do

1. Read `.claude/skills/my-workflows/cookbook-ra.md` in full
2. Follow its workflow exactly: Step 0 resource scan → Step 1 understand the ask → Step 2 data impact analysis (always) → Step 3 escalation check (decides Mode 1 vs Mode 2 output) → Step 4 write the report → Step 5 boundaries

## Critical

- This is Bonnie's **personal** workflow skill (`my-workflows/`), not one of the shared `wonder-*` team domain skills — it orchestrates across them but is not itself one.
- Do not propose creating a Jira ticket at the end of the analysis.
- Do not write into `CB-full-feature` or `CB-business` — those are updated separately, later, by Bonnie's own manual `archive-jira-to-cb` / `biz-req` workflows, never automatically from RA.
- Output goes to `A1-RA Rough/`, filename has no date; ticket key first if the analysis is ticket-based (see the skill file for the exact naming pattern).
