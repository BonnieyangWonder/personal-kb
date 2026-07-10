# Archive Ticket Instruction

When the user says any of these phrases to archive a Jira ticket to CB-Full-Feature:

**中文：**
- "把 ticket 归档到 RA"
- "把 [TICKET-KEY] 归档到 RA"
- 例: "把 MD-17640 归档到 RA"

**English:**
- "Archive ticket to RA"
- "Archive [TICKET-KEY] to RA"
- Example: "Archive MD-17640 to RA"

**User will also provide:**
- Jira ticket URL (e.g., https://wonder.atlassian.net/browse/MD-17640)

## What To Do

1. **Immediately recognize** this means: invoke the `archive-jira-to-cb` skill
2. **Target directory is ALWAYS**: `Z01-Resource/CB-full-feature/`
3. **Note**: "RA" is just shorthand/nickname — the actual destination is always CB-full-feature

## Workflow

1. Extract ticket key from the URL
2. Call `archive-jira-to-cb` skill with the ticket key
3. Follow the skill's full process:
   - Read Jira ticket completely
   - Read ALL CB-full-feature documentation pages
   - Analyze mapping
   - Present plan for user approval
   - Execute changes after approval

## Common Variations

The user may say it in different ways — all mean the same thing:
- "把 ticket 归档到 RA" (Chinese)
- "archive ticket to RA" (English)
- With or without ticket number in the phrase itself
- Always followed by ticket URL

**The key indicator**: "归档到 RA" or "archive to RA" = use archive-jira-to-cb skill, target CB-full-feature

## Critical

- Do NOT interpret "RA" as the "A2-RA Rough" directory
- Always use `Z01-Resource/CB-full-feature/` as the target
- This is a shorthand instruction pattern, not a variable directory path
