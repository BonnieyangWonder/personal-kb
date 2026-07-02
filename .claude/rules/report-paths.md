# Report Paths

When the user asks to create a report or save analysis results, place the file in the correct directory:

| User Says | Directory |
|-----------|-----------|
| "data research", "data research报告", "放到data research" | `A2-Data Research/` |
| "RA rough", "RA rough报告", "放到RA rough", "需求分析" | `A2-RA Rough/` |

**Naming Convention** (follow existing pattern in each directory):
- Data Research: `Wonder Create - <Topic>.md` or `<topic>-<date>.md`
- RA Rough: `YYYY-MM-DD_<Topic>_<描述>.md`

**Do NOT**:
- Create reports in `queries/` when user says "data research" or "RA rough"
- Use `obsidian create` for these reports (they go in A2- directories, not agent-managed knowledge dirs)
- Create anywhere else unless the user explicitly names a different location
