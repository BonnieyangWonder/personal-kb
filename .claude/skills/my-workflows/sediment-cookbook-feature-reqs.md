# Sediment Cookbook Feature / Field Business Requirements

Compile Cookbook system feature or field requirements from Jira tickets into structured, durable business requirement documents. These documents serve as the canonical reference for why a feature/field exists and what business problems it solves.

Output directory: `Z01-Resource/CB-business/features/` — a persistent archive of Cookbook system features/fields and their underlying business drivers.

## When to Use

Trigger on natural language requesting a business requirements document for a Cookbook feature or field:

**中文**:
- "帮我给 [feature/field] 写个业务需求报告"
- "把 [ticket] 的需求沉淀成文档"
- "[功能] 的业务需求是什么"

**English**:
- "write business requirements for [feature/field]"
- "sediment requirements from [ticket] into a document"
- "what's the business case for [feature]"

Input may include:
- Jira ticket URL or key (primary source)
- Confluence page links (supporting context)
- Field names or feature module names
- Brief description of scope

---

## Workflow

### Step 1: Extract Jira Ticket Information

1. **Fetch the Jira ticket** using `mcp__mcp-atlassian__jira_get_issue` with `fields='*all'`
2. **Extract core sections** from ticket description:
   - **Background**: Context, existing gaps, related initiatives
   - **Request**: What fields/features to add, technical specifications
   - **Business Logic**: Definitions, business rules, constraints
   - **Data Sourcing**: How values are derived (manual, automatic, AI-extracted, etc.)
   - **Integration Points**: Downstream consumers, API contracts, webhooks
3. **Parse examples**: Instance 1, Instance 2, etc. — these are concrete test cases; extract exact values and reasoning
4. **Identify References**: Links to related tickets (HD*, CB*, etc.), design docs (Figma, Confluence), and pilot projects

### Step 2: Identify Scope and Impact

Determine the **scope marker** for the feature/field:

- **7\* scope**: If the feature applies to 7-star items (prep procedures, components, recipes), mark as `7*`
- **Menu item scope**: If it applies at menu item level, note as such
- **System-wide**: If it touches cross-system data or integrations, note impact span
- **System/Level marker**: If not 7\*, include system name and configuration level in output filename

**Rule**: Use scope markers in the output filename to disambiguate from other Cookbook features with similar names:
- ✅ `Cook & Chill 7*.md` — clearly marks as 7-star focused
- ✅ `Menu Item Pricing Structure.md` — clear scope
- ❌ `Cook Chill.md` — too vague, collides with other cook/chill logic elsewhere
- ❌ `Cook & Chill Support Business Requirements.md` — redundant; filename should be concise, structure defines "business requirements"

### Step 3: Synthesize Business Requirements Document

**Filename convention**: `<Feature Name> <Scope Marker>.md`
- No date prefix (these are durable references, not time-stamped reports)
- No "Business Requirements" suffix (redundant with directory)
- Scope marker (e.g., `7*`) if needed for disambiguation
- Example: `Cook & Chill 7*.md`, `Multi-Item Ordering.md`

**Document structure** (flexible, adapt to feature specifics):

| Section | Content |
|---------|---------|
| **Header Metadata** | Source Ticket, Status, Scope |
| **Executive Summary** | Problem statement, fields/features introduced, business value |
| **Business Context** | Why needed, related projects, gaps being solved |
| **Feature / Field Definitions** | Name, data type, optionality, scope, definition, examples, instances |
| **Data Sourcing Strategy** | How values are derived (manual entry, auto-extraction, AI, etc.) |
| **Product Requirements** | MVP scope, data model changes, database schema, UI display, API updates |
| **Business Impact** | Benefits for operations, compliance, efficiency, scalability |
| **Technical Specifications** | Optional/required, constraints, validation rules, extensibility paths |
| **Dependencies & Integration** | Upstream/downstream systems, stakeholders, API consumers |
| **Success Criteria** | Measurable targets for adoption, accuracy, coverage |
| **Reference Tickets** | Links to related Jira tickets, pilot projects, design docs |
| **Appendix** | Detailed instance examples with step-by-step derivations |

### Step 4: Write with Clarity and Precision

**Tone**: Professional, reference-grade. Speak to product managers, engineers, compliance, and kitchen operations equally.

**Key principles**:
1. **Every claim backed by source**: If citing a business rule or value, note where it came from (ticket, comment, Confluence page)
2. **Concrete examples over abstractions**: Use Instance 1, Instance 2 patterns from source tickets; readers trust examples more than prose
3. **Define all terms**: Readers may be unfamiliar with internal terminology — define "7-star item", "prep procedure", "bulk prep" on first mention
4. **Table-driven where possible**: Constraints, field specs, stakeholder roles — tables compress information density and improve scannability
5. **Wikilinks for cross-refs**: Link to [[other features]] in features/, [[related tickets]], and [[external references]]

### Step 5: Placement and Naming

**Directory**: `Z01-Resource/CB-business/features/`

**Filename format**:
- `<Feature Name> <Scope Marker>.md` for features with clear scope boundaries
- `<System>-<Feature Name>.md` for cross-system features (rare in CB-business/)
- **No dates, no ticket keys, no redundant suffixes**

**Examples**:
- ✅ `Cook & Chill 7*.md`
- ✅ `Prep Procedure Instructions.md`
- ✅ `Component Yield Scaling.md`
- ❌ `MD-18172-Cook-And-Chill-Business-Requirements.md` — too long, redundant
- ❌ `2026-07-31_Cook_Chill_Needs.md` — dated, too informal

### Step 6: Document Versioning and Iteration

**First draft**: Create with high confidence based on Jira ticket analysis.

**Updates**: Features evolve; when requirements change:
1. Update the same file (no new files for iterations)
2. Bump the metadata `updated` date
3. Preserve change history inline with brief dated notes or comments

**Living document**: These are canonical references — keep them accurate and current as Cookbook evolves.

---

## Quality Checklist

Before finalizing, verify:

- ✅ **Scoped correctly**: Feature name includes scope marker (7\*, menu item, system name) to avoid naming collisions
- ✅ **Self-contained**: Reader understands the feature without external context lookups
- ✅ **Terminology defined**: First mention of domain terms includes definition
- ✅ **Examples concrete**: Instance 1 / Instance 2 extracted directly from ticket; values and reasoning explicit
- ✅ **All links verified**: Jira tickets, Confluence pages, Figma links are accessible and current
- ✅ **Business value clear**: Why this feature matters; who benefits; what problems it solves
- ✅ **Integration points mapped**: Downstream consumers (KOM, KDS, other systems) identified
- ✅ **Success criteria measurable**: Targets for accuracy, adoption, coverage are quantified

---

## Example Workflow

**User says**: "帮我给这个ticket里的'Cook Time'和'Chilling Target Temperature'的写个业务需求报告，放到cb-business"

**Process**:
1. Extract ticket MD-18172 via Jira MCP
2. Read sections: Background (Cook & Chill pilot needs), Request (two new fields), Examples (Instance 1/2), References (HDR-10589, pilot tickets)
3. Determine scope: Features are for 7-star item prep procedures → mark as `7*`
4. Synthesize document with: Executive Summary (why needed for KOM), Field Definitions (Cook Time in seconds, Chilling Target Temp in °F with examples), Data Sourcing (AI extraction from instructions), Product Requirements (API updates, webhooks), Business Impact (food safety, efficiency), Success Criteria (accuracy targets, adoption)
5. Save as `Cook & Chill 7*.md` in `Z01-Resource/CB-business/features/`
6. Output: Durable reference for why these fields exist and what they enable

---

## Why This Matters

Cookbook system changes fast. Features ship, get integrated, evolve. Without durable business requirement docs:
- New team members don't know *why* a field exists
- Product decisions become tribal knowledge
- Integration points are rediscovered (and sometimes missed)
- Compliance and food safety logic gets fragmented across comments and code

`Z01-Resource/CB-business/features/` is the single source of truth for "why does Cookbook have this field/feature?" — a living textbook that compounds in value over time.
