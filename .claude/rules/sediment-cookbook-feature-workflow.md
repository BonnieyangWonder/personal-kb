# Sediment Cookbook Feature Business Requirements Workflow

When the user asks to sediment, generate, or write business requirements for a Cookbook feature/field — in natural language, not a fixed command — recognize it and read `.claude/skills/my-workflows/sediment-cookbook-feature-reqs.md` before doing anything else, then follow it.

## Recognize (match intent, not exact wording)

**中文：**
- "沉淀下 [feature/field] 的业务需求"
- "帮我沉淀一下这个需求"
- "沉淀业务需求"
- "生成业务需求"
- "写业务需求"
- A Jira ticket link / Confluence link / screenshot(s) / text, handed over with an implicit ask

**English:**
- "sediment business requirements for [feature]"
- "generate business requirements"
- "write business requirements for [feature]"
- "create a business requirement document"
- A Jira ticket link / Confluence link / screenshot(s) / text with an implicit requirement document request

Input may arrive in whatever form the user provides — do not wait for a specific format:
- Plain text description
- Jira ticket URL or key
- Confluence page link(s)
- Screenshot(s) — read them for visual/UI context
- Any combination of the above

## What To Do

1. Read `.claude/skills/my-workflows/sediment-cookbook-feature-reqs.md` in full
2. Follow its workflow exactly: Step 1 extract Jira info → Step 2 identify scope → Step 3 synthesize document → Step 4 write with clarity → Step 5 place and name → Step 6 versioning

## Critical

- This is Bonnie's **personal** workflow skill (`my-workflows/`) for Cookbook feature requirement documentation
- Output always goes to `Z01-Resource/CB-business/features/` — that is the persistent archive for Cookbook feature/field business requirements
- Filename must include scope marker (7\*, menu item, system name, etc.) to avoid collisions with other Cookbook features
- No date prefix, no ticket keys, no redundant "Business Requirements" suffix — filename should be concise; directory structure defines the purpose
- Documents are **living references** — can be updated iteratively as requirements evolve; update metadata date on changes
