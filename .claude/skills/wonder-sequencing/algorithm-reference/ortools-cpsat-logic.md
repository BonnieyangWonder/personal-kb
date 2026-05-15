# OR-Tools CP-SAT Wrapper Logic Reference

This document details the business logic for the ORToolsCPSATV2 sequencing algorithm. This wrapper uses Google OR-Tools' CP-SAT (Constraint Programming with SAT solver) for optimization.

**Source Files**:
- `ORToolsCPSATV2.java` - Main CP-SAT wrapper (1496 lines)
- `ORToolsCPSATHelpers.java` - Helper functions for model building
- `domain/ORToolsCPSATTypes.java` - Type definitions for CP-SAT

## Algorithm Overview

**Approach**: Mathematical optimization using constraint programming rather than simulation-based heuristics.

**Key Differences from ThreeStage**:
- **Declarative**: Define constraints and objective, solver finds optimal solution
- **Exact (within time limit)**: Explores solution space systematically
- **Warm-start capable**: Uses ThreeStageIterWrapperV2 solution as starting point
- **Time-bound**: Runs for fixed duration (default: 15 seconds)
- **Deterministic**: Single-threaded with fixed random seed for reproducibility

### Optimization Strategy
```
1. Generate base solution using ThreeStageIterWrapperV2
2. Build constraint programming model
3. Add warm-start hints from base solution
4. Solve with OR-Tools CP-SAT solver
5. Compare solver solution to base solution
6. Return better solution
```

**Fallback Safety**: If CP-SAT fails or produces worse solution, return base solution.

## Core Components

### Time Scaling
```
TIME_SCALE = 15  // Scale down all times by factor of 15
```
- **Purpose**: Reduces variable domains for faster solving
- **Example**: 300 seconds → 20 scaled units
- **Application**: All time values (start, end, duration) are scaled
- **Precision tradeoff**: 15-second granularity (acceptable for kitchen scheduling)

### Solver Parameters
```
maxTimeInSeconds: 15.0 (default)
numSearchWorkers: 1 (single-threaded for determinism)
randomSeed: 1 (fixed seed)
logSearchProgress: true (if debug enabled)
```

### Model Variables

**For each cooking step** (not completed or in-progress):

**COR (Coordination) Variables** - Represent the step as a whole
- `corStartVar`: When step begins (scaled time)
- `corEndVar`: When step completes (scaled time)
- `corIntervalVar`: Interval representing the step duration
- Groups by `podId` for no-overlap constraints

**Appliance Variables** - Represent the appliance usage portion
- `appStartVar`: When appliance usage begins (may be after COR start for labor-first steps)
- `appEndVar`: When appliance usage completes
- `appIntervalVar`: Interval for appliance usage only
- Groups by `applianceId` for resource constraints

**Key Insight**: Splitting COR and appliance allows modeling labor-first steps (e.g., prep 30s, then grill 60s). COR includes both labor and appliance time; appliance interval is just the appliance portion.

## Algorithm Phases

### Phase 1: Generate Base Solution
```
baseWrapper = new ThreeStageIterWrapperV2(settings, 25, 10)
baseSolution = baseWrapper.computeOptimizedKitchenSequence(input)
```
- Uses simulation-based algorithm for initial solution
- Provides warm-start hints to CP-SAT
- Fallback if CP-SAT fails to find better solution
- **Iteration budget**: 25 iterations, early stop after 10 without improvement

### Phase 2: Build Solver Context
```
ctx = buildSolverContext(input)
```

**Context Contents**:
- `itemIdToIndex`: Map item IDs to integer indices (CP-SAT uses integers)
- `itemIndexToId`: Reverse mapping for result extraction
- `orderIdToItemIds`: Group items by order for objective calculation
- `applianceMaps`: Index maps for appliances and appliance types
- `orderInfoList`: Customer promise times and order metadata
- `startedSegments`: Items/steps already in progress (fixed times)
- `resourceAvailability`: Available inventory quantities
- `itemFixedEndTimes`: Completion times for in-progress items
- `horizon`: Maximum time bound for variables
- `unlimitedInventory`: Hot-hold optimization flag

**Started Segments**: Items that have begun cooking are excluded from optimization. Their completion times are fixed and used in async objective penalty.

### Phase 3: Create Model Variables
```
vars = createStepVariables(input, ctx, model)
```

**For each unfinished step**:
1. Calculate `StepTiming` (labor time, cook time, hot-hold adjustment)
2. Create COR interval: `[corStartVar, corEndVar)` with duration `laborTime + cookTime`
3. Create appliance interval: `[appStartVar, appEndVar)` with duration `cookTime`
4. Link appliance start to COR: `appStartVar >= corStartVar + laborTime`
5. Link appliance end to COR: `corEndVar == appEndVar`

**Hot-Hold Optimization** (when `unlimitedInventory` enabled):
- Cook time → 0 for hot-hold eligible steps
- Appliance interval becomes optional (0 duration)
- Labor time unchanged
- **Effect**: Speeds up preparation by using pre-cooked inventory

**Human-Only Resources** (e.g., plating):
- No appliance variable created
- Only COR variable needed
- Represents pure labor activities

### Phase 4: Add Constraints

#### No-Overlap Constraints (COR)
```
for each pod:
    model.addNoOverlap(corIntervalsByPod[pod])
```
- Ensures one step at a time per pod
- **Pod**: Virtual grouping of appliances (typically one employee)
- **Effect**: Prevents chef from working on two items simultaneously

#### Dependency Constraints
```
for each item:
    for each step pair (prev, curr):
        model.addGreaterOrEqual(currCOR.startVar, prevCOR.endVar)
```
- Enforces cooking step ordering within an item
- Example: Can't grill before prepping
- **Intra-item dependencies**: Steps of same item must execute in order

#### Batching Constraints
```
for each batch eligibility group:
    create batch group presence variables
    enforce: if items batch together, they overlap on appliance
    enforce: batch size limits
```

**Batch Eligibility Groups**: Items that can batch together based on:
- Same appliance type (e.g., all grill steps)
- Compatible cooking activity (e.g., all "grill" operations)
- Similar duration (within batching tolerance)

**Batch Benefits**:
- Shared appliance time (multiple items cook simultaneously)
- Reduced total makespan
- Efficient resource utilization

**Batching Logic**:
- If items are in same batch group AND both assigned to batch:
  - Appliance intervals must overlap
  - Total batch size ≤ batch limit (e.g., 6 patties on grill)
- Items can opt-out of batching (independent execution)

### Phase 5: Add Objective Function
```
makespanVar = model.newIntVar(0, horizon, "makespan")
model.addMaxEquality(makespanVar, allCOREndVars)

objective = buildObjective(itemScores, orderInfo, makespanVar, fixedEndTimes)
model.minimize(objective)
```

**Objective Components**:

1. **Async Penalty** (order-level):
```
for each order:
    itemEndTimes = max(corEndVar for items in order, fixedEndTimes for started items)
    asyncPenalty = ASYNC_COST * (max(itemEndTimes) - min(itemEndTimes))
```
- Penalizes items in same order finishing at different times
- Forces order synchronization at expo
- **Goal**: All items in order ready simultaneously

2. **Target Miss Early Penalty** (order-level):
```
for each order:
    orderFinishTime = max(itemEndTimes)
    earlyAmount = max(0, TARGET_WINDOW_SCALED - (customerPromise - orderFinishTime))
    earlyPenalty = TARGET_MISS_EARLY_COST * earlyAmount
```
- Penalizes finishing too early (before target window)
- Target window: 10 minutes grace period before promise
- **Goal**: Don't finish more than 10 minutes early

3. **Target Miss Late Penalty** (order-level):
```
for each order:
    orderFinishTime = max(itemEndTimes)
    lateAmount = max(0, orderFinishTime - customerPromise)
    latePenalty = TARGET_MISS_LATE_COST * lateAmount
```
- Penalizes finishing after promise time
- **Goal**: Never be late

4. **Makespan Penalty**:
```
makespanPenalty = MAKESPAN_COST * makespanVar
```
- Penalizes longer sequences
- Incentivizes completing all work faster
- **Goal**: Minimize total time to finish all orders

**Scoring Weights** (from `getScoringWeights()`):
```
ASYNC_COST = 20
TARGET_MISS_EARLY_COST = 20
TARGET_MISS_LATE_COST = 100
MAKESPAN_COST = 10
```

**Interpretation**: Being late is 5x worse than being early (100 vs 20). Order synchronization and lateness equally weighted (20, 100).

### Phase 6: Add Warm-Start Hints
```
for each item in baseSolution:
    for each step:
        model.addHint(corStartVar, baseStartTime)
        model.addHint(corEndVar, baseEndTime)
```
- Provides solver with good starting solution
- **Not a constraint**: Solver can deviate if it finds better solution
- **Benefit**: Faster convergence, explores near-optimal regions first

### Phase 7: Solve Model
```
solver = new CpSolver()
solver.setMaxTimeInSeconds(maxTimeInSeconds)
solver.setNumSearchWorkers(1)
solver.setRandomSeed(1)

status = solver.solve(model)
```

**Solver Status**:
- `OPTIMAL`: Proven optimal solution found (rare within time limit)
- `FEASIBLE`: Valid solution found, may not be optimal
- `INFEASIBLE`: No solution exists satisfying all constraints
- `UNKNOWN`: Timeout or resource limit before finding solution

**Determinism**: Single worker + fixed seed ensures same solution every run (critical for testing and debugging).

### Phase 8: Extract and Compare Solutions
```
if status == OPTIMAL or status == FEASIBLE:
    solverSolution = buildOptimizedSequence(input, ctx, solver, status, vars)
    baseScore = getSequenceScore(baseSolution)
    solverScore = getSequenceScore(solverSolution)
    return solverScore <= baseScore ? solverSolution : baseSolution
else:
    return baseSolution
```

**Solution Extraction**:
1. Read start/end times from solved variables
2. Unscale times (multiply by `TIME_SCALE`)
3. Build `OptimizedKitchenSequence` with batch groups
4. Calculate item scores for comparison

**Safety**: Always compare and return better solution. CP-SAT occasionally produces worse solutions due to modeling approximations.

## Constraint Modeling Techniques

### Interval Variables
```
intervalVar = model.newIntervalVar(startVar, duration, endVar, "name")
```
- Represents a task with start, duration, and end
- Built-in OR-Tools abstraction
- **Constraint**: `end = start + duration` enforced automatically

### No-Overlap Constraints
```
model.addNoOverlap(intervalVars)
```
- Ensures intervals don't overlap on shared resource
- Classic scheduling constraint
- **Use cases**: Pods (one step at a time), appliances (capacity constraints)

### Optional Intervals
```
presenceVar = model.newBoolVar("presence")
intervalVar = model.newOptionalIntervalVar(start, duration, end, presenceVar, "name")
```
- Interval only active if `presenceVar == true`
- **Use cases**: Batching (item may or may not join batch), hot-hold (appliance optional)

### Conditional Constraints
```
model.addImplication(conditionVar, constraint)
```
- Constraint only enforced if `conditionVar == true`
- **Use cases**: "If items batch together, then they must overlap"

## Key Modeling Decisions

### Why Split COR and Appliance?
- **Labor-first steps**: Prep work before appliance (e.g., 30s prep, then 60s grill)
- **Batching flexibility**: Multiple items share appliance simultaneously
- **Accurate timing**: Separates human time from appliance time

### Why Scale Time?
- **Variable domains**: Smaller domains = faster solving
- **Integer precision**: Avoids floating-point in constraints
- **Search efficiency**: CP-SAT works best with bounded integer variables

### Why Warm-Start?
- **Time-bound solving**: 15 seconds isn't enough to explore full solution space
- **Local search bias**: Starting near good solution finds improvements faster
- **Hybrid approach**: Combines heuristic (ThreeStage) with exact method (CP-SAT)

### Why Single-Threaded?
- **Determinism**: Same input → same output (essential for debugging)
- **Reproducibility**: Production runs match development runs
- **Testing**: Can write assertions about exact solutions

## Horizon Calculation

```
horizon = calculateHorizon(input, startedSegments, unlimitedInventory)
```

**Purpose**: Upper bound on all time variables to constrain search space.

**Calculation**:
1. Sum all step times for all items
2. Add buffer for resource contention
3. Account for customer promise times
4. Scale down by `TIME_SCALE`

**Tradeoff**: Too small → infeasible model; Too large → slow solving.

## Performance Characteristics

### Typical Performance
- **Small kitchens** (< 20 items): 2-5 seconds, often finds optimal
- **Medium kitchens** (20-50 items): 5-15 seconds, finds good feasible solutions
- **Large kitchens** (50+ items): 15 seconds (timeout), returns best found or base solution

### When CP-SAT Excels
- **Complex batching opportunities**: Finds non-obvious batch combinations
- **Tight timing constraints**: Optimally schedules with minimal slack
- **Multi-objective tradeoffs**: Balances async, target, makespan systematically

### When CP-SAT Struggles
- **Very large problems**: Exponential search space
- **Conflicting constraints**: May timeout before finding feasible solution
- **Highly variable step times**: Large horizons slow down search

## Advantages vs ThreeStage

**Pros**:
- **Systematic exploration**: Doesn't rely on heuristics
- **Optimal batching**: Finds best batch combinations
- **Provable bounds**: Can certify solution quality (if optimal status)
- **No iteration needed**: Single solve (vs multiple iterations)

**Cons**:
- **Time requirement**: Needs 15+ seconds (vs 1-5 seconds for ThreeStage)
- **Modeling complexity**: Approximations in constraint formulation
- **Failure modes**: Can timeout with no solution
- **Less predictable**: Solving time varies with problem structure

## Production Usage

**Current Status**: ORToolsCPSATV2 is **not** the primary production wrapper. ThreeStageIterHoldbackLNSWrapperV2 is most commonly used.

**Use Cases**:
- **Research**: Exploring optimal solutions
- **Benchmarking**: Evaluating ThreeStage quality
- **Complex scenarios**: High-value situations where 15s latency acceptable

**Future Direction**: May become primary as solver performance improves and time budgets increase.

## Debugging and Validation

### Model Validation
```
validationError = model.validate()
if (!validationError.isEmpty()):
    LOGGER.warn("Model validation error: {}", validationError)
    return baseSolution
```
- Checks for constraint conflicts
- Ensures variable domains are valid
- **Safety**: Returns base solution on validation failure

### Logging Solution
```
if LOGGER.isDebugEnabled():
    printSolution(solver, makespanVar, vars, ctx)
```
- Prints variable assignments
- Shows which items batch together
- Displays timing for each step
- **Enable with**: Debug logging level

### Common Issues

**Infeasible Model**:
- **Cause**: Contradictory constraints (e.g., impossible promise times)
- **Fix**: Review horizon calculation, check input validity
- **Mitigation**: Base solution fallback

**Timeout Without Solution**:
- **Cause**: Problem too large or complex
- **Fix**: Increase `maxTimeInSeconds` or simplify constraints
- **Mitigation**: Base solution fallback

**Worse Than Base**:
- **Cause**: Modeling approximations or objective mismatch
- **Fix**: Review objective weights, check score calculation
- **Mitigation**: Comparison logic returns base solution

## Related Files

- **three-stage-wrapper-logic.md**: Alternative simulation-based approach
- **SKILL.md**: Query patterns for sequencing tables
- **schema-reference.md**: Table schemas and field descriptions
- **Source code**: `/kds/tool/cooking-optimization-library/src/main/java/app/optimization/sequencing/ORToolsCPSATV2.java`
