# XM NY Weekly Planning Workflow

When the user asks to set up the weekly XM NY meeting agenda page — in natural language, not a fixed command — recognize it and read `.claude/skills/my-workflows/xm-ny-weekly-planning.md` before doing anything else, then follow it.

## Recognize (match intent, not exact wording)

**中文：**
- "创建本周的 meeting agenda"
- "建一下这周的 weekly planning page"
- "这周的 XM NY weekly planning"

**English:**
- "create this week's meeting agenda"
- "set up the weekly planning page"
- "XM NY weekly planning for this week"

Usually asked once a week (often Monday), but recognize the intent on whatever day it's asked — don't require the word "Monday" to be present.

## What To Do

1. Read `.claude/skills/my-workflows/xm-ny-weekly-planning.md` in full
2. Follow its steps exactly: compute the title date (page-creation date **+ 1 day**) → create the page under space RT (parent `4675175482`) → post the footer comment with real, storage-format mentions of the recurring attendees

## Critical

- Title date is the page-creation date **plus one day** — this direction was corrected once already; do not default to "the day before."
- Mentions in the footer comment MUST use the Confluence storage-format `<ac:link><ri:user ri:account-id="..." /></ac:link>` macro. Plain markdown `@name` or `[~id]` renders as dead text, not a real mention — this failed once already in practice.
- Default attendees (Pratik Busi, Jakob Lewei, Lisa Li) are listed with pre-resolved account IDs in the skill file — reuse them, don't re-search unless the user changes the attendee list.
- Do not write Obsidian vault notes as part of this workflow — it only touches Confluence.
