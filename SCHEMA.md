# Knowledge Schema

Knowledge taxonomy and conventions for this vault.

## Knowledge Domains

_No domains defined yet. The agent adds domains here as knowledge pages are created._

## Tag Taxonomy

Tags follow these conventions:
- 2-5 tags per page, alphabetically sorted
- Tags should be singular (use `#project` not `#projects`)
- New tags should be added here first before use

### Current Tags

| Tag | Usage | Description |
|-----|-------|-------------|

_No tags defined yet. The agent adds tags here as knowledge pages are created._

## Domain Taxonomy

| Domain | Description |
|--------|-------------|

_No domains defined yet. The agent adds domains here as knowledge pages are created._

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
