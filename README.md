# Hybrid VRPTW Solver for Urban Delivery

A portfolio-grade Vehicle Routing Problem with Time Windows (VRPTW) project that
connects exact validation, adaptive ALNS, OR-Tools baselines, statistical
analysis, and Streamlit/Folium map visualization into one interview-ready
engineering story.

The core idea is not to write another standalone routing solver. The project is
designed to demonstrate the full trade-off chain:

```text
business problem -> mathematical model -> exact validation -> heuristic search
-> adaptive operator selection -> baseline comparison -> statistical evaluation
-> map visualization -> resume evidence
```

The personal differentiator is the MOSADE-inspired adaptive mechanism: strategy
selection ideas from evolutionary optimization are migrated into ALNS
destroy/repair operator selection for an industrial routing problem.

## Why VRPTW

Urban delivery teams must decide which vehicle visits which customers, in what
order, while respecting vehicle capacity, customer time windows, service times,
and depot operating hours. A cheap route that arrives late is infeasible; a
feasible route that uses too many vehicles is expensive. VRPTW is a compact way
to model this operational tension.

This repository treats VRPTW as an engineering problem:

- small instances are solved or checked with an exact CP-SAT formulation;
- larger instances use greedy construction plus ALNS local search;
- OR-Tools Routing is used as an external baseline;
- Solomon best-known-solution fields are used where verified;
- experiments produce CSV summaries, statistical tests, and report figures;
- map layers turn routes into depot/customer markers and vehicle polylines.

## Model Summary

Given depot `0`, customers `1..n`, vehicles `k`, demand `q_i`, service time
`s_i`, capacity `Q`, travel time `t_ij`, and distance `d_ij`, the solver seeks
routes that:

- start and end at the depot;
- visit each customer exactly once;
- keep each route load within vehicle capacity;
- arrive within each customer's time window `[a_i, b_i]`, allowing waiting;
- minimize a weighted objective dominated by vehicle count, then travel cost.

In implementation, the objective uses a large vehicle weight so that reducing
vehicles is prioritized before shaving route distance, matching common Solomon
benchmark reporting.

## Solver Strategy

| Layer | Role | Implementation |
| --- | --- | --- |
| Greedy insertion | Fast feasible initial solution and demo fallback | `src/vrptw_hybrid/solvers/greedy.py` |
| CP-SAT exact | Small-instance validation and correctness anchor | `src/vrptw_hybrid/solvers/exact_cp_sat.py` |
| OR-Tools Routing | Industry baseline for comparison | `src/vrptw_hybrid/solvers/ortools_routing.py` |
| ALNS | Scalable heuristic search for larger cases | `src/vrptw_hybrid/solvers/alns/` |
| Adaptive selector | MOSADE-inspired operator selection | `src/vrptw_hybrid/solvers/alns/selectors.py` |

The ALNS loop starts from a greedy solution, repeatedly removes customers with a
destroy operator, reinserts them with a repair operator, accepts improving
candidates, and records convergence metadata. Candidate caching and
nearest-neighbor filtering keep repair evaluation practical as instances grow.

## Adaptive Selector

Uniform ALNS samples destroy and repair operators evenly. Roulette ALNS updates
independent operator weights by segment-level rewards. The MOSADE-inspired
selector goes one step further: it treats a `(destroy, repair)` pair as the
strategy, assigns rewards for accepted moves and new best solutions, and keeps a
memory of recent pair performance.

```mermaid
flowchart LR
    A["Current solution"] --> B["Choose destroy|repair pair"]
    B --> C["Destroy customers"]
    C --> D["Repair route plan"]
    D --> E["Evaluate feasibility and cost"]
    E --> F["Accept if improved"]
    F --> G["Reward pair"]
    G --> B
```

That pair-level view is useful because a destroy operator can be weak with one
repair operator and strong with another. The selector stores this interaction
instead of assuming the two choices are independent.

## Experiment Protocol

Recommended experiment dimensions:

- instances: Solomon subsets first, then synthetic city instances with optional
  OSM road-network matrices;
- solvers: `greedy`, `ortools_routing`, `alns_uniform`, `alns_mosade`;
- seeds: at least 3 for heuristic comparisons once runtime allows;
- budgets: fixed `time_limit_sec` and `max_iterations` per instance class;
- metrics: feasible flag, objective, vehicles used, total distance, total
  duration, runtime, BKS vehicle/distance gaps when available;
- reporting: convergence curves, cost/runtime scatter, gap boxplots, operator
  probability plots, pair heatmaps, Wilcoxon/Holm statistical summaries.

The batch runner writes results under `data/results/`. README or resume claims
about percentage improvement, 500/1000-customer scaling, or BKS gaps must only
be filled after a real CSV exists.

## Results

No benchmark improvement numbers are claimed yet.

| Claim | Evidence file | Status |
| --- | --- | --- |
| Vehicle reduction vs OR-Tools | TODO: `data/results/.../runs_*.csv` | TODO |
| Distance reduction vs OR-Tools | TODO: `data/results/.../runs_*.csv` | TODO |
| Runtime on 500/1000-customer scaling | TODO: `data/results/scaling_*.csv` | TODO |
| Solomon BKS gap summary | TODO: verified result CSV with BKS fields | TODO |

## Quick Start

Create an editable development install and run the test suite:

```bash
python -m pip install -e ".[dev]"
pytest -q
```

Check the CLI and solve the mini Solomon fixture:

```bash
vrptw info --config configs/solomon_small.yaml
vrptw solve --instance tests/fixtures/mini_solomon.txt --solver greedy --config configs/solomon_small.yaml --seed 42 --time-limit 3 --max-iterations 10
vrptw solve --instance tests/fixtures/mini_solomon.txt --solver alns_uniform --config configs/solomon_small.yaml --seed 42 --time-limit 3 --max-iterations 10
```

Run a small batch experiment:

```bash
vrptw batch --config configs/solomon_small.yaml --output data/results/solomon_small
```

Generate report figures from the latest CSV in that output directory:

```powershell
$runsCsv = Get-ChildItem data/results/solomon_small/runs_*.csv | Sort-Object LastWriteTime -Descending | Select-Object -First 1
python scripts/make_report_figures.py --runs-csv $runsCsv.FullName --output-dir data/results/figures
```

## Demo

Install visualization dependencies and launch the Streamlit app:

```bash
python -m pip install -e ".[dev,vis]"
streamlit run apps/streamlit_app.py
```

The demo supports:

- selecting a mini Solomon instance;
- running `greedy`, `ortools_routing`, `alns_uniform`, or `alns_mosade`;
- setting seed, time limit, and ALNS iterations;
- loading a precomputed solution JSON for a fast interview path;
- viewing metrics, a Folium route map, route table, convergence curve, operator
  probabilities, and download buttons for solution JSON and metrics CSV.

Demo screenshot/GIF: TODO after capturing the Streamlit page with a generated
solution.

## Project Structure

```text
apps/
  streamlit_app.py              Streamlit + Folium demo
configs/
  solomon_small.yaml            Small reproducible experiment config
docs/
  modeling.md                   VRPTW formulation and business meaning
  algorithm_alns.md             ALNS search loop and operators
  adaptive_selector.md          Adaptive selector notes
  experiment_protocol.md        Reproducible benchmark protocol
  statistical_tests.md          Statistical testing notes
scripts/
  make_report_figures.py        SVG figure generation from result CSV/JSON
  profile_alns.py               ALNS profiling helper
  run_scaling.py                Scaling experiment launcher
src/vrptw_hybrid/
  core/                         Data models, feasibility, metrics, solution I/O
  data/                         Solomon parser, BKS table, OSM/synthetic data
  experiments/                  Batch runner, statistics, plots, scaling
  solvers/                      Greedy, CP-SAT, OR-Tools, ALNS
  visualization/                GeoJSON export and Folium rendering
tests/
  fixtures/mini_solomon.txt     Fast smoke/demo instance
```

## Limitations

- The project solves static VRPTW instances; it is not a real-time dispatch or
  live re-optimization system.
- Road-network travel times use cached OSM graph data and simplified speed
  assumptions; live traffic is out of scope.
- CP-SAT exact validation is intended for small instances and can be sensitive
  to the installed OR-Tools native runtime.
- COPT/MILP integration is optional and not required for the main demo path.
- Visualization dependencies are kept in the `vis` extra to keep solver tests
  lightweight.

## Interview Talk Track

1. Start from the business constraint: delivery routes must balance vehicle
   count, distance, capacity, and time-window feasibility.
2. Explain the mathematical model: binary arc decisions, service start times,
   capacity accumulation, time-window bounds, and depot return.
3. Justify exact vs heuristic: exact models are valuable for small-instance
   validation, but heuristic ALNS is the practical path for larger routing.
4. Explain adaptive ALNS: destroy/repair pairs are treated like strategies;
   rewards update pair probabilities from recent search performance.
5. Explain validation: exact checks on small cases, OR-Tools baseline, Solomon
   BKS gaps where verified, repeated seeds, statistical summaries, and map
   inspection.

Resume bullet template, to fill only after real CSV evidence exists:

```text
Implemented a hybrid VRPTW solver with CP-SAT validation, OR-Tools baseline,
and MOSADE-inspired adaptive ALNS; on <instance set>, reduced vehicles by TODO,
distance by TODO%, and produced a Streamlit/Folium route visualization demo.
```
