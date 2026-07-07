---
name: audit
description: >
  Scan agent-maintained directories for health issues: orphan pages, broken wikilinks,
  stale content, frontmatter violations, tag taxonomy drift, oversized pages. Use this
  skill whenever the user wants to audit knowledge base quality, check for broken links,
  find stale or orphan pages, or says anything like "check my wiki", "are there any issues",
  "audit the knowledge base", "find broken links", or "what needs fixing".
---

# /audit — Knowledge Health Check

Scan the four agent-maintained directories (`entities/`, `concepts/`, `comparisons/`, `queries/`)
for structural issues.

**Use the deterministic tools first** — they compute several categories exactly:

```bash
obsidian orphans          # category 1: files with no incoming links
obsidian unresolved       # category 2: broken wikilinks, with counts
obsidian deadends         # bonus signal: files with no outgoing links
obsidian knowlery:stale   # categories 3 and 7 (or: knowlery stale / node .knowlery/bin/query.mjs --stale)
```

Filter tool output to the four agent directories. Fall back to manual traversal only
when none of the tools is available.

## Scan Categories

### 1. Orphan Pages
Pages with no inbound wikilinks from any other note — from `obsidian orphans`.
- Severity: **warning** for new pages (< 7 days old), **info** for older

### 2. Broken Wikilinks
Wikilinks in agent pages that point to non-existent targets — from `obsidian unresolved`.
- Severity: **warning**

### 3. Stale Content
Compiled pages whose cited sources changed after the page was last written — the
`Stale pages` section of the staleness report.
- Severity: **info**

### 4. Frontmatter Violations
Pages missing required fields (`title`, `date`, `created`, `updated`, `type`, `tags`, `sources`).
- Severity: **warning** for missing required fields

### 5. Tag Taxonomy Drift
Tags used in agent pages that are not defined in `SCHEMA.md`.
- Severity: **info**

### 6. Oversized Pages
Pages exceeding ~200 lines — candidates for splitting.
- Severity: **info**

### 7. Dangling Sources
Agent pages whose `sources` cite notes that no longer exist — the `Dangling sources`
section of the staleness report.
- Severity: **warning**

## Report Format

Group findings by severity:

```
Health check complete. Found 3 issues:

Warnings (2):
• [[broken-link-page]] — broken wikilink to [[nonexistent]]
• [[orphan-page]] — no inbound links (created 30 days ago)

Info (1):
• [[large-concept]] — 340 lines, consider splitting into sub-topics
```

Offer concrete fixes for each issue. Ask before making changes.
