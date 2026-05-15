# Sequencing Algorithm Logic - Reference Documentation

## Purpose

This folder contains **reference documentation** about how Wonder's kitchen sequencing algorithms make decisions. These files explain the internal logic, optimization objectives, and decision-making processes.

## Code Location (KDS Repository)

The actual sequencing code lives in the KDS repository (available as a submodule at `/wonder/kds`):

- **Algorithm Implementation**: `wonder/kds/tool/cooking-optimization-library/`
  - Core sequencing logic and optimization algorithms
  - ThreeStageWrapper implementations
  - CP-SAT solver integration
  - Simulation and scoring logic

- **Backend Service**: `wonder/kds/backend/cooking-optimization-service/`
  - Execution pipeline for running optimizations
  - Result processing and transformation
  - Database persistence (saves to BigQuery tables: `hdr_kitchen_order_sequencing_optimizer`, `optimizer_batch`, `sequencing_contexts`)
  - API endpoints for triggering optimizations

**When to reference the code**: When documentation in this folder isn't sufficient, or when you need to understand implementation-specific details.

## When to Read These Files

**Read these files when:**
- User asks "Why did the sequencing algorithm choose this batch grouping?"
- User asks "How does the holdback strategy work?"
- User asks "What optimization objectives does the algorithm use?"
- User wants to understand the decision-making process for a specific order
- Debugging algorithm behavior (not data queries)

**Don't read these files when:**
- User wants to query sequencing data (use main SKILL.md instead)
- User wants to analyze performance metrics
- User wants to check expo sit times or customer promise adherence
- User wants to debug data quality issues

## Files in This Folder

### `three-stage-wrapper-logic.md`
Documents the ThreeStageWrapperV2 family of sequencing algorithms:
- Three-stage simulation approach
- How the wrapper coordinates pods and batch groups
- Holdback strategy logic
- Optimization objectives and scoring

**When to use**: Most HDRs use ThreeStageWrapperV2. Read this when investigating algorithm decisions at production sites.

### `ortools-cpsat-logic.md`
Documents the ORTools CP-SAT constraint programming approach:
- Constraint satisfaction problem formulation
- Decision variables and constraints
- Objective function weights
- How the solver finds optimal solutions

**When to use**: Some experimental sites or future implementations may use CP-SAT. Read this when investigating constraint-based optimization decisions.

## Quick Reference

**For data queries and analysis**: Return to main skill files:
- `../SKILL.md` - Overview and when to use the skill
- `../schema-reference.md` - Table schemas and field definitions
- `../common-pitfalls.md` - Query mistakes to avoid
- `../query-patterns.md` - Common analysis patterns

**For algorithm decisions**: Read the appropriate file in this folder based on which algorithm implementation is being used.

---

**Note**: These files are intentionally separated to keep the main skill focused on the 95% use case (querying and analyzing data). Algorithm logic is important but needed less frequently.
