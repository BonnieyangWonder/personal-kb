# Business Requirements Document Compilation

Compile scattered requirements discussions from Jira tickets and Confluence pages into a structured business requirements document. The document serves as a business requirement traceability baseline for subsequent feature development.

## Language

**All document content must be in English**, regardless of the source material language. Source pages may be mixed Chinese/English, but the final output document is English-only.

## Output Directory

**`Z01-Resource/CB-business/` is the dedicated directory for all Cookbook-related business requirements documents.** All biz-req output goes here unless the user specifies a different target directory.

## When to Use

- User provides a Jira ticket + several Confluence reference page links
- User asks to write a business requirements document for a Cookbook feature
- Business requirements change over time and the document needs continuous iteration
- Default output location: `Z01-Resource/CB-business/`

## Workflow

### Step 1: Resource Collection

Starting from the user-provided entry links, **exhaustively collect** all related materials:

1. **Jira ticket**: Fetch issue content via Atlassian MCP tools. If no Jira scope is available, infer from Confluence page mentions and references.
2. **Confluence pages**: Fetch each page body in markdown format via `getConfluencePage` for text extraction.
3. **Footer comments**: `getConfluencePageFooterComments` (with replies). These often contain stakeholder alignment and design decision discussions.
4. **Inline comments**: `getConfluencePageInlineComments` (with replies). These often contain questions and clarifications on specific attribute values or table entries.
5. **Child pages**: `getConfluencePageDescendants`. Child pages may contain more granular specifications.
6. **Referenced pages**: Links from @mentions in body text, smartlinks, and pages mentioned in comments — fetch them if relevant to the topic.
7. **External resources**: Google Sheets, Figma links, etc. — fetch if publicly accessible.

### Inaccessible Resources (CRITICAL)

**After completing resource collection, you MUST explicitly report every resource that could not be accessed.** This is a hard requirement — do not silently skip failed fetches.

Access failures include:
- Jira tickets that return 404 or authentication errors
- Confluence pages that return 404 or permission errors
- Slack links that require login / can't be fetched
- Google Docs/Sheets links that are private
- Figma links behind authentication
- Any URL that WebFetch cannot retrieve
- Footer/inline comments that fail to load

Format the warning clearly before proceeding to Step 2:
```
⚠ Unable to access the following resources:
- <url1> — <reason (e.g., Confluence page not found)>
- <url2> — <reason (e.g., Slack login required)>
- <url3> — <reason (e.g., comment fetch failed)>

The compiled document will note these as unverified references.
```

**Do NOT proceed to Step 2 (Resource Analysis) until the user has seen this list.** If all resources are accessible, explicitly state: "✅ All referenced resources successfully accessed."

### Step 2: Resource Analysis

Perform three layers of analysis on collected materials:

1. **Distinguish proposals vs. final decisions**: Page body content may be early drafts. Discussions in comments often contain key decision turning points. Map the timeline: who proposed what → who objected/revised → what was the final conclusion. Record rejected proposals as well (provides context for "why not").
2. **Identify cross-page related concepts**: The same business concept may appear across multiple pages with different framing (e.g., IK Eligible defined at component level in one page, associated with step level in another). Connect them to form a complete picture.
3. **Extract business rules, filter technical details**: Focus on what & why, not specific API endpoints or database fields. Technical details only retained at the "solution overview" level.

### Step 3: Document Structure

Organize in the following order (flexibly adapt to specific topic):

| Section | Content |
|---|---|
| **Business Background** | Why this feature is needed, related project context |
| **Concept Definitions & Enum Values** | Definition, allowed values, and meaning of each core attribute |
| **Configuration Level** | At which level each attribute is configured (menu item / component / sub-step) and why |
| **Interaction Rules** | Dependencies and constraints between attributes |
| **Solution Design** | What each system does (overview level, not functional spec) |
| **Design Decision Records** | Key decision outcomes, decision makers, dates, rejected proposals and reasons |
| **Data Flow** | How data flows between systems |
| **Configuration Matrix** | Complete configuration reference for all known scenarios |
| **Timeline & Dependencies** | Milestones, upstream/downstream dependencies |
| **Open Questions** | Pending items and future iteration directions |
| **Reference Pages** | URL matrix of all source pages |

### Step 4: Validation

1. **Self-check**: Cross-reference every claim against source materials. Every claim must have a source.
2. **Common pitfalls to watch**:
   - Which level a concept applies at (component vs. step vs. menu item)
   - Correct data flow direction (who queries whom, who pushes to whom)
   - Precise meaning of "default" (system fallback vs. configuration-level inheritance)
   - Enum value names and counts match source materials
3. **Annotate sources**: Key decisions should note who decided, which page/comment, and date.

### Step 5: Iteration

1. Submit to stakeholder for review
2. Revise iteratively based on feedback until accurate
3. Bump `updated` date on every edit
4. The document is a living document — iterate as business requirements evolve

### Step 6: Update Existing Documents

**When updating an existing business document, do NOT modify it directly.** Instead:

1. List the proposed changes, showing **before → after** comparisons
2. Submit for user review
3. Only execute edits after user confirms

## Output

A markdown document placed in `Z01-Resource/CB-business/` (the dedicated Cookbook business requirements directory), with complete frontmatter, wikilink references, and a source page URL matrix. All content in English.
