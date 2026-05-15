# Three-Stage Wrapper Logic Reference

This document details the business logic for the ThreeStageWrapperV2 family of sequencing algorithms. These wrappers use a simulation-based approach with iterative refinement.

**Source Files**:
- `ThreeStageWrapperV2.java` - Base three-stage algorithm
- `ThreeStageIterWrapperV2.java` - Iterative refinement variant
- `ThreeStageIterHoldbackLNSWrapperV2.java` - Iterative with Local Neighborhood Search
- `SequencingWrapperHelpers.java` - Shared simulation and scoring functions
- `HoldBackCalculatorV2.java` - Holdback time calculations
- `ScoreEvaluationHelpers.java` - Scoring weights and evaluation

## Algorithm Overview

The three-stage approach uses progressive simulation and refinement:
1. **Stage 1 (Item-level)**: Compute individual item scores independently
2. **Stage 2 (Order-level)**: Simulate each order with items from Stage 1
3. **Stage 3 (Sequence-level)**: Simulate entire kitchen sequence
4. **Refinement**: Adjust holdback times based on results, repeat as needed

**Key Principle**: Each stage uses output from the previous stage as input, progressively refining the schedule from item → order → full sequence.

## Core Data Structures

### SimulationInput
Contains all items to be sequenced with their cooking steps, timing requirements, and customer promises.

**Key Fields**:
- `items()`: List of `SimulationInputItem` (menu items to cook)
- `currentTime()`: Current time when sequencing runs
- `orderIds()`: Distinct order IDs in this input
- `unlimitedInventoryEnabled()`: Whether hot-hold optimization is active

### ItemScore
Represents scoring and timing predictions for a single menu item.

**Key Fields**:
- `id`: Item identifier
- `tS`: Simulated start time
- `tI`: Item finish time (when this item completes cooking)
- `tO`: Order finish time (when entire order is ready at expo)
- `tF`: Order items finish (when all items in order complete)
- `tCP`: Customer promise time (target completion from ETA service)
- `expoSitTimeScore`: Predicted expo wait time in seconds (negative = early, positive = late)
- `customerPromiseScore`: Predicted vs promise in seconds (negative = early, positive = late)
- `estimatedHoldBackTime`: Minutes to delay item from immediate preparation
- `holdBackStrategyV2`: Strategy applied (EXPO_THRESHOLD, CUSTOMER_PROMISE, etc.)
- `isCorporateOrder`: Corporate/catering order flag
- `inPersonSource`: Kiosk or other in-person source

### KitchenSequenceScores
Container for item scores, separating in-progress orders (bucket2) from new orders (bucket3).

**Structure**:
- `bucket2Scores`: Map<String, ItemScore> for items in orders that have started cooking
- `bucket3Scores`: Map<String, ItemScore> for items in orders not yet started
- `combinedScores()`: All scores merged together

## ThreeStageWrapperV2

### Algorithm Steps

**Step 1: Item-Level Simulation**
```
itemScores = computeItemScoresV2(input, settings)
```
- Simulates each item independently
- Ignores other items and orders
- Provides baseline timing estimates
- Returns `KitchenSequenceScores` with initial predictions

**Step 2: Order-Level Simulation**
```
orderScores = computeOrderScoresV2(input, itemScores, settings)
```
- Simulates each order as a unit
- Uses itemScores from Step 1 as input
- Accounts for coordination between items in same order
- Updates scores with order-level constraints

**Step 3: Sequence-Level Simulation (Initial)**
```
sequenceScores = computeSequenceScoresV2(input, orderScores, settings, Boolean.FALSE)
```
- Simulates entire kitchen with all orders
- Uses orderScores from Step 2 as input
- `Boolean.FALSE` = intermediate simulation (no final adjustments)
- Accounts for resource contention across all items

**Step 4: Holdback Adjustment**
```
amendedHoldbackTimes = amendHoldbackTimes(input.items(), sequenceScores, settings)
updatedOrderScores = orderScores.withUpdatedHoldbackTimes(amendedHoldbackTimes)
```
- Calculates optimal holdback times based on sequence simulation
- Combines expo and promise considerations
- Updates order scores with new holdback times

**Step 5: Final Sequence Simulation**
```
finalSequenceScores = computeSequenceScoresV2(input, updatedOrderScores, settings, Boolean.TRUE)
finalSequence = computeSequence(input, updatedOrderScores, settings, "V2")
```
- Re-simulates with adjusted holdback times
- `Boolean.TRUE` = final simulation (apply all adjustments)
- Builds `OptimizedKitchenSequence` output with batch groups

**Step 6: Output Preparation**
```
finalSequence.updateWithResultantScores(...)
finalSequence.addItemIdSequence()
finalSequence.wrapperName = "ThreeStageWrapperV2"
```
- Attaches final scores to output
- Generates item sequence ordering
- Labels with wrapper name for tracking

### Iteration Estimate
```
itemCount + orderCount + 2
```
- Used for time budgeting and progress tracking
- Each item is simulated, each order is simulated, plus 2 sequence-level simulations

## ThreeStageIterWrapperV2

### Additional Parameters
- `availableIterations`: Maximum iterations allowed (default: 25)
- `earlyStoppageIterations`: Stop if no improvement for N iterations (default: 10)

### Algorithm Differences from Base

**Steps 1-5**: Same as ThreeStageWrapperV2 (initial three-stage simulation + holdback adjustment)

**Step 6: Iterative Refinement Loop**
```
while (!complete && iterationCount < availableIterations):
    currentAmendedHoldbackTimes = amendHoldbackTimes(input.items(), currentSequenceScores, settings)

    if no change in holdback times:
        break  // Converged

    currentOrderScores = currentOrderScores.withUpdatedHoldbackTimes(currentAmendedHoldbackTimes)
    currentSequenceScores = computeSequenceScoresV2(input, currentOrderScores, settings, Boolean.TRUE)
    currentSequenceScore = getSequenceScore(currentSequenceScores.combinedScores(), input)

    if currentSequenceScore < bestSequenceScore:
        bestSequenceScore = currentSequenceScore
        bestSequenceScores = currentSequenceScores
        bestUpdatedOrderScores = currentOrderScores
        lastUpdatedIteration = iterationCount
    elif iterationCount - lastUpdatedIteration >= earlyStoppageIterations:
        complete = true  // Early stopping - no improvement

    iterationCount += 1
```

**Convergence Criteria**:
1. Holdback times stop changing (optimal found)
2. No improvement for `earlyStoppageIterations` consecutive iterations
3. Reach `availableIterations` limit

**Key Insight**: Holdback adjustments can trigger cascading effects. Holding back one item may free up resources, allowing other items to start earlier, which changes their holdback needs. Iteration finds the fixed point.

### Iteration Estimate
```
availableIterations
```
- Returns the full iteration budget since exact count depends on convergence

## ThreeStageIterHoldbackLNSWrapperV2

### Additional Parameters
Same as ThreeStageIterWrapperV2 plus uses remaining iteration budget for LNS

### Algorithm Phases

**Phase 1: Three-Stage Iteration** (Same as ThreeStageIterWrapperV2)
- Runs the full iterative refinement
- Tracks best solution found
- Stores in `threeStageIteration` result
- Iteration count: `itemCount + orderCount + 2 + iterCount`

**Phase 2: Local Neighborhood Search (LNS)**
```
remainingIterations = availableIterations - getBaseIterationEstimate(input) - iterationCount

if remainingIterations > 0 and itemCount > 1:
    LNSIteration = getLNSAdjustedIteration(threeStageIteration, input, settings, remainingIterations)
```
- Uses remaining iteration budget for sequence order optimization
- **LNS Strategy**: Try swapping adjacent items in the sequence
- Evaluates each swap to find better orderings
- Keeps holdback times from Phase 1 fixed during swaps
- `itemCount > 1` requirement avoids LNS for single-item sequences

**Phase 3: Holdback Refinement on LNS Result**
```
bestHoldbackAdjIteration = getRefinedHoldbackAdjustment(LNSIteration, input, settings)
```
- Takes LNS-optimized sequence
- Re-evaluates holdback times for the new ordering
- May adjust holdback for individual items based on new neighbors

**Phase 4: Final Simulation**
```
optimizedSequence = runSimulationForSequence(
    input, settings,
    bestHoldbackAdjIteration.itemPriorities(),
    bestHoldbackAdjIteration.holdbackAdj()
)
```
- Runs kitchen simulation with best sequence and refined holdback
- Generates batch groups for KDS display
- Returns final `OptimizedKitchenSequence`

### Key Differences from ThreeStageIterWrapperV2
1. **LNS adds sequence order optimization**: Iter only adjusts holdback; LNS also reorders items
2. **Two-level optimization**: Iter (holdback) → LNS (order) → Holdback refinement
3. **Higher quality**: Can find better solutions but uses more iterations
4. **Adaptive budget**: Uses whatever iterations remain after convergence

### Iteration Estimate
```
availableIterations
```
- Dynamically allocates between phases based on convergence speed

## Holdback Calculation Logic

### Holdback Types

**Expo Holdback** (`calculateExpoHoldbackTime`):
```
if expoSitTimeScore > settings.maxExpoSitSeconds():
    holdback = expoSitTimeScore - settings.maxExpoSitSeconds()
```
- Delays item to avoid exceeding expo sit time threshold
- `maxExpoSitSeconds` changed from 420s (7 min) to 180s (3 min) on 2025-11-24
- Example: Item would sit 5 minutes at expo → hold back 2 minutes (5min - 3min)

**Promise Holdback** (`calculatePromiseHoldbackTime`):
```
if isCorporateOrder or isKioskOrder:
    // Only hold back if we're late (negative score)
    holdback = min(0, customerPromiseScore - maxCustomerPromiseEarlySeconds)
else:
    // Hold back if too early or too late
    holdback = customerPromiseScore - maxCustomerPromiseEarlySeconds
```
- Prevents finishing too early (wasted kitchen capacity)
- `maxCustomerPromiseEarlySeconds`: Grace period before promise time
- **Corporate/Kiosk exemption**: These orders start immediately even if early (customer is waiting)

### Holdback Amendment Logic

**Per-Item Calculation**:
```
expoHoldback = calculateExpoHoldbackTime(itemScore, settings)
promiseHoldback = calculatePromiseHoldbackTime(itemScore, settings)
```

**Order-Level Coordination**:
```
for each order:
    calculate sumExpoHoldbackTimes for all items
    calculate sumPromiseHoldbackTimes for all items

    minExpo = min(sumExpoHoldbackTimes)
    adjSumExpoHoldbackTimes = sumExpoHoldbackTimes - minExpo  // Normalize to minimum

    finalOrderHoldbackTimes = max(adjSumExpoHoldbackTimes, sumPromiseHoldbackTimes)
```

**Key Insight**: Items in the same order coordinate holdback. If one item needs to be held back, others in the same order are held back proportionally to keep the order synchronized.

## Scoring System

### Scoring Weights
```
scoring6 (current):
- 20: Expo Sit Time Score weight
- 20: Early Customer Promise Score weight
- 100: Late Customer Promise Score weight
- 10: Throughput/Makespan Score weight
```

**Interpretation**: Being late is 5x worse than being early (100 vs 20). Expo sit time and lateness are equally weighted (20, 100).

### Score Components

**Expo Sit Time Score** (`expoSitTimeScore` field):
- Measured in seconds
- Positive value: Item sits at expo waiting for other items
- Negative value: Item not yet finished when other items are ready
- Per-order maximum: Only the longest wait per order counts
- **Goal**: Minimize maximum expo wait per order

**Customer Promise Score** (`customerPromiseScore` field):
- Measured in seconds relative to promise time
- Positive value: Order finishes after promise (LATE - bad)
- Negative value: Order finishes before promise (EARLY - wasteful)
- **Goal**: Finish close to promise time, never late

**Sequence Score Calculation** (`getSequenceScore`):
```
expoCost = profitMargin * costPerExpoSecond * totalExpoTime
cpEarlyCost = profitMargin * costPerEarlySecond * totalEarlyTime
cpLateCost = profitMargin * costPerLateSecond * totalLateTime
laborCost = costPerLaborSecond * sequenceCompletionTime

totalScore = expoCost + cpEarlyCost + cpLateCost + laborCost
```

- Lower score is better (represents estimated cost)
- Profit margin factor: Impacts on CLTV (customer lifetime value)
- Labor cost: Incentivizes completing sequences faster

## Simulation Process

### Kitchen Simulation Flow
1. **Resource Initialization**: Set up appliances (grills, fryers, ovens, etc.) and chef resources
2. **Priority Scheduling**: Determine order in which items enter simulation based on scores
3. **Step Scheduling**: For each item, schedule each cooking step on appropriate resources
4. **Batching**: Group compatible items together on shared appliances
5. **Holdback Application**: Delay items according to holdback strategy
6. **Timeline Generation**: Compute actual start/finish times with resource constraints
7. **Score Calculation**: Evaluate expo waits, promise adherence, and throughput

### Item Priority Scheduling
Items are prioritized using `SEGMENT_COMPARATOR` (see ScoreEvaluationHelpers):
1. Remakes (highest priority)
2. Items incurring sit time (already waiting)
3. Customer promise score (piecewise)
4. In-person orders (kiosk - customer waiting)
5. Fast pass orders
6. Customer promise score (linear)
7. Expo sit time score
8. Batch size limits
9. Bucket 3 item count
10. Cooking priority

### Batching Strategy
- Items using the same appliance can batch together
- Batch eligibility based on cooking activity, appliance, and timing
- Batch groups displayed one at a time on KDS screens
- V2/V3 batching strategies progressively refine groupings

## Key Algorithm Behaviors

### Convergence
- **Fast convergence**: Most sequences converge in 3-5 iterations
- **Oscillation prevention**: Early stopping after 10 iterations without improvement
- **Fixed point**: Holdback times stabilize when no item benefits from adjustment

### Known Bugs and Edge Cases

**Bug: Late orders with holdback**
- **Issue**: Orders with `customerPromiseScore < -10` should not have `estimatedHoldBackTime > 0`
- **Impact**: Late orders being delayed further (making them even later)
- **Detection**: `WHERE customerPromiseScore < -10 AND estimatedHoldBackTime > 0`

**Edge Case: Excessive delays**
- **Issue**: Items sequenced 30+ or 60+ minutes before start time
- **Cause**: Cascading holdback or resource contention
- **Detection**: `WHERE TIMESTAMP_DIFF(created_time, t_s, SECOND) > 1800`

## Algorithm Selection Guide

**Use ThreeStageWrapperV2 when**:
- Fast response needed (< 1 second)
- Simple kitchen with few items (< 20 items)
- Baseline solution acceptable

**Use ThreeStageIterWrapperV2 when**:
- Moderate complexity (20-50 items)
- Time budget allows (2-5 seconds)
- Need better holdback optimization

**Use ThreeStageIterHoldbackLNSWrapperV2 when**:
- Complex kitchen (50+ items)
- Time budget allows (5-15 seconds)
- Need best possible solution quality
- Currently **most common in production**

## Related Files

- **SKILL.md**: Query patterns for sequencing tables
- **schema-reference.md**: Table schemas and field descriptions
- **ortools-cpsat-logic.md**: Alternative constraint programming approach
- **Source code**: `/kds/tool/cooking-optimization-library/src/main/java/app/optimization/sequencing/`
