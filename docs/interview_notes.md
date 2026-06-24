# Interview Notes

## 30-Second Introduction

I built a VRPTW portfolio project that connects the full chain from business
constraints to modeling, solving, evaluation, and visualization. Small instances
use CP-SAT as a correctness anchor, medium instances compare OR-Tools Routing,
greedy construction, and ALNS variants, and the final demo includes both a
benchmark route viewer and a Berlin Mitte OSM road-network map.

The important part is not that one heuristic wins everywhere. It is that every
claim is backed by CSVs, checker output, statistical summaries, and visual
artifacts.

## 2-Minute Technical Story

The business problem is urban delivery with hard time windows: each customer
must be visited once, vehicles have capacity limits, service takes time, and
routes must return to the depot. I model that as VRPTW with a vehicle-first,
distance-second objective convention.

I implemented a shared instance model, solution model, and feasibility checker.
The checker validates customer coverage, capacity, time-window service starts,
travel-time consistency, depot return, and route count. That checker is used
across solvers and experiments.

For solving, I use several layers. CP-SAT is used for small validation; OR-Tools
Routing is the external baseline; greedy construction gives quick feasible
solutions; ALNS variants handle heuristic search. The ALNS code supports uniform
selection, roulette weighting, and a MOSADE-inspired selector that tracks
destroy/repair pairs.

The experiments are intentionally evidence-driven. RUN-01 verifies that outputs
land as CSV/JSON. RUN-02 audits UNKNOWN and provenance rules. ABL-01 tests the
selector mechanism. EXP-02 runs 90 rows across Solomon 100 and
Gehring-Homberger 200 selected instances. VIS-01A visualizes benchmark x-y
routes, and VIS-01B visualizes a small Berlin Mitte road-network demo.

## Business -> Model -> Solve -> Evaluate -> Visualize

1. Business: delivery routes must balance vehicle count, distance, capacity, and
   delivery time windows.
2. Model: nodes, depot, demand, service time, travel matrix, time windows, and
   vehicle capacity.
3. Solve: CP-SAT for small checks, OR-Tools Routing as a baseline, ALNS for
   heuristic variants.
4. Evaluate: feasible rate, vehicles, distance, runtime, objective, convergence,
   and paired exploratory tests.
5. Visualize: benchmark x-y route viewer and Berlin Mitte Folium road-map demo.

## Why Not Pure Exact Optimization

Exact formulations are valuable because they expose modeling errors and provide
small-instance validation. They become expensive as customer count and vehicle
route decisions grow. In this project, CP-SAT is deliberately scoped to mini and
small validation. The medium comparison uses OR-Tools Routing and ALNS variants.

## Why CP-SAT Is Only A Small Anchor

CP-SAT gives useful correctness pressure on small cases, but it is not presented
as a medium benchmark baseline. Earlier small experiments include UNKNOWN rows
under time limits, and those are not counted as optimal or successful. That is
why EXP-02 excludes CP-SAT.

## OR-Tools Routing: Strong But Budget-Limited

In EXP-02, OR-Tools Routing returned strong solutions when it found one. Under
the fixed 60-second budget, its feasible rate was 0.5 on the selected medium
suite. ALNS variants reached 1.0 feasible rate. The honest phrasing is:

> OR-Tools Routing was strongest on feasible paired rows, but not consistently
> available under the fixed budget.

## MOSADE Did Not Win

This is a useful interview point, not a failure to hide. I migrated the idea of
adaptive strategy selection into ALNS destroy/repair pair selection, instrumented
operator probabilities and rewards, and ran an ablation. The result was that the
MOSADE-inspired selector did not outperform uniform or roulette in the current
settings.

Good phrasing:

> The mechanism is implemented and explainable, but the current evidence does
> not support a superiority claim. The next technical step is ABL-02: reward
> scaling, pair-memory diagnosis, and selector parameter tuning.

## VIS-01A vs VIS-01B

VIS-01A is a benchmark route viewer. It uses Solomon and Gehring-Homberger x-y
coordinates and must not be described as a real map.

VIS-01B is a city road demo. It uses a Berlin Mitte OSM driving graph, synthetic
orders sampled from road-network nodes, road shortest-path distances, GeoJSON,
and Folium HTML.

## City Demo Travel-Time Caveat

The Berlin Mitte demo uses road-network shortest paths and a travel-time proxy
from edge lengths and speed assumptions. It is not based on observed traffic
measurements. Phrase it as a visualization and integration demo.

## Defensive Answers To Likely Follow-Ups

Q: Why did MOSADE not beat simpler selectors?

A: The current reward scale and problem slice may not give the pair-memory
mechanism enough signal. I kept the negative result because the point of the
project is an evidence-backed engineering workflow, not forcing a success story.

Q: Why keep OR-Tools if ALNS is the project focus?

A: It gives a serious external baseline. Where OR-Tools returns a solution it is
very strong, which keeps the comparison honest.

Q: Why use a weighted objective?

A: The benchmark convention prioritizes vehicle count before distance. The code
reports objective, vehicles, distance, and runtime separately so objective is
not confused with distance.

Q: Are the city routes real delivery routes?

A: They are synthetic orders on a real OSM road network. The map is useful for
demonstration, but it is not a production dispatch or measured travel-time
system.

Q: What would you do next?

A: First package the repository for release. Then ABL-02 to diagnose selector
behavior. After that, broader experiments only if the medium-scale evidence is
stable.
