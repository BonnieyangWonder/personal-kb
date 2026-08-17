# Add Requirement Dependency Workflow

When the user mentions adding or recording a requirement dependency or relationship — in natural language, not a fixed command — recognize it and read `.claude/skills/my-workflows/add-requirement-dependency.md` before doing anything else, then follow it.

## Recognize (match intent, not exact wording)

Don't wait for the exact phrase or a fully-formed sentence. Recognize the intent from various phrasings too, as long as it's clearly about recording requirement relationships or dependencies.

**中文（从完整到简短都要识别）：**
- "补充需求关联"
- "补充关联需求"
- "发现了一个需求关联"
- "有个新的关联需求"
- "需求关联补充"
- "加一个关联到清单里"
- "记录一个需求关联"
- "这个需求还有关联..."
- 直接说出需求信息，暗含"这个 XX 还要考虑 YY" 的关联诉求，无需完整表述

**English (short forms count too):**
- "add a requirement dependency"
- "record a new association"
- "capture this requirement relationship"
- "log a dependency"
- A description of a requirement with implicit dependencies mentioned

Input may be partial info, keywords, or full descriptions — do not require a specific format before recognizing the trigger.

## What To Do

1. Read `.claude/skills/my-workflows/add-requirement-dependency.md` in full before doing anything else
2. Follow its steps exactly: Step 0 collect info → Step 1 edit checklist → Step 2 verify and reflect → Step 3 update

## Critical

- This is Bonnie's **personal** workflow skill (`my-workflows/`), used to maintain [[个人/需求关联清单.md]]
- Default to adding to the checklist directly (do not ask for confirmation unless genuinely unclear)
- The checklist uses a **table format**; when adding rows, follow the existing column structure and Markdown conventions
- Do not modify or override existing entries without explicit permission
