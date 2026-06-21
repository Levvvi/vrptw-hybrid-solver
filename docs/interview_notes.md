# Interview Notes

This document turns the project into an interview narrative. It follows the
intended arc:

```text
constraints as math -> exact vs heuristic trade-off -> adaptive mechanism
-> validation and evidence -> demo
```

No performance numbers are filled in here until they are backed by result CSVs.

## 30-Second Pitch

I built a hybrid VRPTW project for urban delivery routing. It models vehicle
capacity, customer time windows, service times, and depot return; uses CP-SAT
for small-instance validation; uses greedy construction and ALNS for larger
instances; compares against an OR-Tools baseline; and exposes convergence,
operator-selection metadata, statistics, and a Streamlit/Folium map demo. The
differentiating part is that I transferred MOSADE-style adaptive strategy
selection into ALNS destroy/repair operator selection.

## 2-Minute Technical Walkthrough

1. Business problem: a dispatcher needs feasible routes that use few vehicles,
   travel short distances, and arrive inside customer time windows.
2. Mathematical model: customers are nodes, vehicles are routes, arc decisions
   represent travel, and service start times enforce time-window feasibility.
3. Exact validation: on small instances, CP-SAT helps verify that the objective
   and constraints are encoded correctly.
4. Heuristic solving: for larger cases, exact search becomes expensive, so the
   project uses greedy insertion to get a feasible solution and ALNS to improve
   it.
5. Adaptive mechanism: ALNS chooses destroy/repair operators online. The
   MOSADE-inspired selector treats each destroy/repair pair as a strategy and
   updates pair probabilities from accepted moves and new best solutions.
6. Evaluation: the batch runner records cost, vehicles, distance, runtime,
   feasibility, BKS gaps where verified, convergence history, and selector
   snapshots.
7. Demo: Streamlit shows metrics, a Folium route map, route tables,
   convergence curves, operator probabilities, and downloadable JSON/CSV.

## Mathematical Model Talk Track

The core decision is whether vehicle `k` travels from node `i` to node `j`.
That is the binary arc variable `x_ijk`. Then each customer has a service start
time `T_i` and a load state `L_i`.

Use this framing:

- visit constraint: every customer appears exactly once;
- flow constraint: if a vehicle enters a customer, it must leave that customer;
- capacity constraint: cumulative demand cannot exceed vehicle capacity;
- time-window constraint: service must start between `ready_time` and
  `due_time`; early arrival becomes waiting;
- objective: prioritize fewer vehicles, then lower distance.

Interview wording:

```text
I separate feasibility from cost. A route is only valid if the decoder can walk
through the sequence, compute arrival/start/departure times, and keep both time
windows and capacity satisfied. Only then do I compare vehicle count and travel
distance.
```

## Why Not Use Only Exact Optimization

Exact methods are valuable because they catch modeling mistakes and can certify
small cases. But VRPTW has combinatorial route assignment and sequencing, and
time windows make feasibility tightly coupled with order. As the number of
customers grows, exact search can spend the budget proving optimality rather
than giving a good operational answer.

Interview wording:

```text
I use exact optimization as a correctness anchor, not as the only production
strategy. That is the engineering trade-off: exact methods validate the model
on small cases; ALNS gives controllable runtime and useful solutions on larger
cases.
```

## Adaptive Operator Selection Talk Track

Plain ALNS needs to choose a destroy operator and a repair operator every
iteration. Uniform selection ignores feedback. Roulette selection can adapt
independent operator weights. My MOSADE-inspired version adapts the pair:

```text
strategy = destroy_operator | repair_operator
```

Why pair-level matters:

- the value of a destroy operator depends on how the removed customers are
  repaired;
- a related-customer destroy can be strong with regret insertion but weaker
  with another repair operator;
- pair statistics reveal interactions that independent weights hide.

Reward explanation:

```text
new best solution: strong reward
accepted improving solution: medium reward
feasible exploratory solution: small reward
rarely sampled pair: small diversity bonus
```

Interview wording:

```text
The adaptive selector is deliberately modest. I am not claiming a new global
optimizer. I am taking a proven idea, online strategy selection, and moving it
to the ALNS operator layer where the strategy is a destroy/repair pair.
```

## Gap, Convergence, Ablation, Statistics

How to discuss evidence before final benchmark numbers:

- Gap: "The code can compute BKS gap fields when the BKS entry is verified; I
  leave unknown values blank rather than inventing targets."
- Convergence: "ALNS stores `best_cost` by iteration, so I can show whether
  improvements happen early, late, or not at all under a fixed budget."
- Ablation: "Uniform, roulette, and MOSADE-inspired selectors share the same
  solver shell. That isolates the effect of operator selection."
- Statistics: "The analysis aligns rows by instance and seed, then uses paired
  comparisons. I only fill resume percentages after the matched CSV supports
  them."

When results are available, fill this sentence:

```text
On <instance set> with <seed count> seeds and <time budget>, <solver> reduced
<metric> by <X> versus <baseline>, with evidence in <runs csv>.
```

## Demo Flow

1. Open Streamlit.
2. Select `Mini Solomon 8`.
3. Run `greedy` to show a fast feasible baseline.
4. Run `alns_uniform` or `alns_mosade` to show convergence and route metadata.
5. Point at map layers: depot, customers, route polylines, and popups with time
   windows and arrival times.
6. Download solution JSON to show route details are not only visual.

## Follow-Up Questions

**How do you know the solution is feasible?**  
Each route is decoded stop by stop. The checker validates customer coverage,
duplicates, capacity, arrival/service times, and depot return.

**Why OR-Tools if you already implemented solvers?**  
OR-Tools is a credible external baseline. It helps separate "my heuristic
works" from "my heuristic beats a trivial implementation."

**What is the risk in the adaptive selector?**  
It can overfit to early lucky rewards. The exploration floor and sliding memory
reduce that risk, and ablations compare it against uniform and roulette
selection.

**Why not claim MOSADE fully?**  
Because the project transfers one idea, adaptive strategy selection. It is
more accurate and more defensible to call it MOSADE-inspired.

**What would you improve next?**  
Run larger Solomon and synthetic-city batches, add more acceptance criteria,
test richer road-network travel times, and fill the resume numbers only after
the CSV and statistical summaries support them.
