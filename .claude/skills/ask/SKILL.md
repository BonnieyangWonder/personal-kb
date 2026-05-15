---
name: ask
description: >
  Open-ended Q&A against the knowledge base. Uses INDEX.base as the vault Bases wiki index,
  Obsidian CLI (properties, search, tags, backlinks) to traverse the same graph the Base
  shows in Obsidian, SCHEMA.md for taxonomy, then reads and synthesizes with citations.
  Use when the user asks questions about vault content like "what is X", "why did we decide Y",
  "explain Z", "what do my notes say about", "summarize what I know about", or any question
  that should be answered from accumulated knowledge rather than general training data.
---

# /ask — Knowledge Q&A

You are a knowledge assistant. Your job is to answer questions by navigating the vault's knowledge graph, reading relevant pages, and synthesizing evidence-based answers — always citing sources with wikilinks.

## Parameters

- **question** (required): The question to answer.
- **output** (optional): Save the answer as a note at this path.

## Process

### Step 1: Understand the Question

Identify the key concepts, entities, and intent in the user's question.

### Step 2: Locate Relevant Pages

**Do not delegate this workflow to a generic exploration subagent.** Run the Obsidian CLI steps yourself so searches merge and nothing is skipped.

#### 2a — Wiki index: `INDEX.base` (Bases)

If `INDEX.base` exists, read it first:

```bash
obsidian read file="INDEX.base"
```

**What this is:** The vault's **Obsidian Bases wiki index**. In the app, this file drives a **live, query-backed table** of notes with rich metadata (paths, tags, dates, backlinks, and any columns you add). The bytes on disk are the Base definition (views, filters, formulas); Obsidian **evaluates** that definition into the dynamic index you see in the UI.

**How to use it as an agent:** Parse the definition to learn **which paths and property filters** define "compiled knowledge" in this vault. Then run CLI commands that query the **same scope** — do not treat the YAML as meaningless "config" or assume the vault has no index when you do not see note titles in the read output.

#### 2b — List agent-maintained pages (same scope the Base should cover)

Enumerate compiled pages by v2 frontmatter `type` (high-speed retrieval, same notes the Base is meant to index):

```bash
obsidian properties type=entity
obsidian properties type=concept
obsidian properties type=comparison
obsidian properties type=query
```

Use paths and titles from this output as candidates. When helpful, add **`obsidian tags`**, **`obsidian backlinks file="..."`**, or other list commands from `obsidian help` to exploit metadata associations the Base surfaces as columns.

#### 2c — Taxonomy and conventions

Read `SCHEMA.md` when you need the tag taxonomy, domain rules, or agent directory conventions:

```bash
obsidian read file="SCHEMA.md"
```

If the question or `SCHEMA.md` points at specific tags, run targeted searches for those tags in addition to plain terms.

#### 2d — Search by key concepts

For each key concept in the question:

```bash
obsidian search "<key concept>"
```

Combine and deduplicate results across queries.

#### 2e — User and source notes outside agent directories

Answers may live in raw notes (e.g. reports, dailies, `Projects/`) that are **not** under `entities/`, `concepts/`, `comparisons/`, or `queries/`. After agent-scope passes, run broader searches (filename keywords, dates, or tags) until you have checked plausible locations or confirmed the vault has no matching note.

### Step 3: Read Relevant Pages

For each promising result, read the full content:

```bash
obsidian read file="entities/some-page.md"
```

Prioritize:

- Agent pages in `entities/`, `concepts/`, `comparisons/`, `queries/`
- Pages with matching tags or domain
- Pages with `status: reviewed` (over `draft`)
- Recent pages (higher `updated` date)

Also read user source notes when the question requires original context.

### Step 4: Synthesize Answer

Combine evidence from all relevant pages into a clear, structured answer:

- **Direct answer first** — address the question directly
- **Supporting evidence** — cite specific pages with wikilinks and brief quotes
- **Context** — explain how the evidence connects
- **Uncertainties** — flag gaps where the vault doesn't have enough information

Every claim must be backed by at least one vault note. Do not use general knowledge to answer — ground everything in the vault.

### Step 5: Present Answer

```markdown
## Answer

<Direct answer to the question>

## Evidence

- **[[Page A]]**: "<relevant quote>"
- **[[Page B]]**: "<relevant quote>"
- **[[Page C]]**: "<relevant quote>"

## Context

<Brief paragraph connecting the evidence and explaining the bigger picture>

## Gaps

<What the vault doesn't cover that would help answer more completely>

## Related Questions

- Consider exploring: "..."
- Run `/trace topic="X"` to see how this evolved
- Run `/connect from="A" to="B"` to understand the relationship
- If the vault lacks pages for key entities or concepts, run `/cook` to compile knowledge from source notes
```

### Step 6: Save (Optional)

At the end of your answer, ask:

> "Would you like me to save this as a note?"

If the user confirms, save the answer with frontmatter:

```yaml
---
title: "Answer: <topic>"
date: <today>
tags: [qa, <topic>]
---
```

Use `obsidian create` to save. Ask the user where they'd like it saved.

## Key Principles

- **Evidence-based**: Every answer must cite vault notes. No general knowledge answers.
- **Direct first**: Answer the question before providing supporting detail.
- **Acknowledge gaps**: If the vault doesn't have enough information, say so.
- **Respect scope**: Only answer based on vault content, not external knowledge.
- **Save on request**: Always offer to save the answer as a note for future reference.
- **Bases + CLI:** The wiki index is **`INDEX.base`** in Obsidian; discovery via CLI is **`obsidian properties`** (by `type` and other fields), **`obsidian search`**, and related commands — not a duplicate markdown index file.
