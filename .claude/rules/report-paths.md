# Report Paths

When the user asks to create a report or save analysis results, place the file in the correct directory **based on the nature of the report, not just exact keyword match**:

| Report Nature | Trigger Phrases | Directory |
|---------------|-----------------|-----------|
| **数据分析报告** — query results, data findings, metrics, SQL analysis, trend reports | "数据分析报告", "数据报告", "data research", "数据research", "data分析", "查询报告", "query result", "放data research" | `A2-Data Research/` |
| **RA 分析** — 需求分析, requirements analysis, rough/incomplete analysis, 初步评估 | "RA", "RA分析", "RA rough", "ra分析报告", "需求分析", "初步分析", "放RA rough" | `A2-RA Rough/` |

**Decision Rule**: If the user describes the output as a report about data/queries/findings → Data Research. If they describe it as an RA/requirements/rough assessment → RA Rough.

**Naming Convention** (follow existing pattern in each directory):
- Data Research — general rule for **every** report in this directory, regardless of topic or project: **no date prefix**. Keep the filename short and clearly distinguishable from other reports already in the folder. If the report is an analysis for a specific project, **abbreviate the project name** and use it as the filename prefix: `<ProjectAbbrev> - <Topic>.md` (e.g. Wonder Create → `WC - <Topic>.md`). If the report isn't tied to a specific project, use `<Topic>.md` directly. Keep `<Topic>` itself short but descriptive enough to tell reports apart — e.g. when the core finding is a consistency/mismatch check between two configs (any project, not just WC), phrase the topic as `<Object> Configuration Consistency` (e.g. `WC - BYO Customization Configuration Consistency.md`).
- RA Rough: `YYYY-MM-DD_<Topic>_<描述>.md` (this directory keeps its own date-prefixed convention — it does not follow the Data Research naming rule above)

**Structure Convention** (结论先写 — applies to every report in either directory):
- Lead with the conclusion: the first section after the title must state the bottom-line answer/findings/recommendation — not the background, scope, or methodology. A reader should get the answer from the first section alone, without scrolling.
- Everything else (background/scope, methodology, detailed data tables, SQL/query appendix) follows the conclusion, in that order.
- This applies regardless of report length or how many sub-questions it answers — if the request had multiple parts, the conclusion section states the answer to each part before any of them gets elaborated on.

**Do NOT**:
- Create reports in `queries/` or other knowledge directories when user wants data research or RA rough
- Use `obsidian create` for these reports (they go in A2- directories, not agent-managed knowledge dirs)
