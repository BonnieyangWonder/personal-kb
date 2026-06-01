# Knowledge Schema

Knowledge taxonomy and conventions for this vault.

## Knowledge Domains

| Domain | Description |
|--------|-------------|
| `cookbook` | Wonder's Cookbook recipe and BOM management system

## Tag Taxonomy

Tags follow these conventions:
- 2-5 tags per page, alphabetically sorted
- Tags should be singular (use `#project` not `#projects`)
- New tags should be added here first before use

### Current Tags

| Tag | Usage | Description |
|-----|-------|-------------|
| `bigquery` | 1 page | BigQuery SQL patterns and data warehousing |
| `cookbook` | 11 pages | Wonder's Cookbook recipe/BOM management system |
| `item-lifecycle` | 4 pages | Item status transitions and version workflows |
| `kitchen-operations` | 2 pages | Kitchen execution, line build, and station operations |
| `product-development` | 1 page | R&D workflows and automated item creation |
| `recipe-management` | 4 pages | BOM structure, recipe components, and customization

## Domain Taxonomy

| Domain | Description |
|--------|-------------|
| `cookbook` | Wonder's Cookbook recipe and BOM management system — item taxonomy, BOM structure, lifecycle, query patterns, and feature-level business rules.

## Agent Page Conventions

| Directory | Purpose |
|-----------|---------|
| `entities/` | Concrete, named things (people, organizations, products, systems) |
| `concepts/` | Abstract ideas (methods, rules, decisions, processes) |
| `comparisons/` | Side-by-side analyses of options |
| `queries/` | User-question-driven answers worth keeping |

## Frontmatter Schema

See the /cook skill specification for the complete frontmatter schema. Key required fields:

- `title` — concise one-line summary
- `date` — primary temporal anchor (ISO 8601)
- `created` — page creation date
- `updated` — last content change date (bump on every edit)
- `type` — one of: entity, concept, comparison, query
- `tags` — 2-5 tags from this taxonomy, alphabetically sorted
- `sources` — relative paths to contributing notes

## Page Thresholds

- Create a page when: entity/concept appears in 2+ notes OR is central subject of one note
- Split a page when: it exceeds ~200 lines
- Do NOT create pages for: passing mentions, minor details, out-of-domain topics

## Custom Fields

| Field | Type | Description |
|-------|------|-------------|
| `status` | text | Page status (active, draft, archived) |
| `domain` | text | Knowledge domain |
| `description` | text | Short description/summary |
| `references` | list | Related wikilink references |
| `author` | text | Content author |
