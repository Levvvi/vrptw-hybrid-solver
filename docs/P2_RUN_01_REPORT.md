# P2-RUN-01 Report

Date: 2026-06-22

## A. Environment Readiness

Current local environment is Install Ready for the core Python workflow:

- Python: `<repo-root>\.venv311\Scripts\python.exe`
- Python version: 3.11.9
- OR-Tools: 9.15.6755
- VC++ Runtime x64: `v14.51.36247.00`
- `pip check`: pass
- CP-SAT smoke: `status= CpSolverStatus.OPTIMAL x= 1`
- `pytest`: `150 passed, 1 skipped`
- `ruff`: pass
- `mypy`: pass
- `vrptw info`: pass

## B. Solver Smoke Matrix

Evidence:

- `data/results/smoke/solver_matrix.csv`
- `reports/results/solver_matrix.csv`
- `data/results/smoke/solutions/*.json`

| solver | feasible | vehicles | distance | objective | runtime_sec | status |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| greedy | True | 2 | 180.000 | 200180.000 | 0.003 | FEASIBLE |
| ortools_routing | True | 2 | 140.000 | 200140.000 | 3.011 | SOLUTION_FOUND |
| cp_sat | True | 2 | 150.000 | 200150.000 | 3.017 | FEASIBLE |
| alns_uniform | True | 2 | 140.000 | 200140.000 | 0.017 | FEASIBLE |
| alns_mosade | True | 2 | 140.000 | 200140.000 | 0.016 | FEASIBLE |

Every smoke solution was rechecked with `check_solution`; distance and objective were recomputed before entering the matrix.

## C. Small Batch Status

Small batch completed and wrote 45 rows:

- `data/results/experiments/runs_small.csv`
- `reports/results/runs_small.csv`
- 45 solution JSON files under `data/results/experiments/solutions/`
- 18 ALNS convergence CSV files under `data/results/experiments/convergence/`

There are no `pipeline_status=error` failed rows. In `runs_small.csv`, `status`
records solver status and `pipeline_status` records execution success or error.
There are 3 infeasible/no-solution-returned rows:

| instance | solver | seeds | status |
| --- | --- | --- | --- |
| c101_50 | cp_sat | 0, 1, 2 | UNKNOWN |

This means the small experiment is complete, but not fully green for CP-SAT on
50 customers within the 30 second limit. `UNKNOWN` means CP-SAT did not prove or
return a feasible solution within the time budget. It does not mean the instance
is infeasible, and it does not mean optimality was proven.

## C1. Experiment Configuration

Config file: `configs/experiment_small.yaml`

Instances:

- `mini_solomon`: `tests/fixtures/mini_solomon.txt`
- `c101_25`: `data/raw/solomon/C101_25.txt`
- `c101_50`: `data/raw/solomon/C101_100.txt`, `limit_customers: 50`

Solvers:

- `greedy`
- `ortools_routing`
- `cp_sat`
- `alns_uniform`
- `alns_mosade`

Seeds:

- `0`
- `1`
- `2`

Time limits:

- `cp_sat`: 30 seconds
- `ortools_routing`: 10 seconds
- ALNS variants: 10 seconds

ALNS maximum iterations:

- 100

Solomon data sources used for local, ignored raw files:

- `data/raw/solomon/C101_25.txt`: https://raw.githubusercontent.com/mck-/Open-VRP/master/test-cases/Solomon-25/C101.txt
- `data/raw/solomon/C101_100.txt`: https://raw.githubusercontent.com/jonzhaocn/VRPTW-ACO-python/master/solomon-100/c101.txt

## D. Small Batch Summary

Evidence: `data/results/experiments/summary_small.csv`
Curated copy: `reports/results/summary_small.csv`

| solver | runs | valid_runs | feasible_rate | mean_distance | mean_runtime_sec | mean_objective |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| alns_mosade | 9 | 9 | 1.000 | 245.137 | 0.942 | 333578.470 |
| alns_uniform | 9 | 9 | 1.000 | 245.508 | 0.800 | 333578.842 |
| cp_sat | 9 | 6 | 0.667 | 190.380 | 25.034 | 250190.380 |
| greedy | 9 | 9 | 1.000 | 275.469 | 0.191 | 333608.803 |
| ortools_routing | 9 | 9 | 1.000 | 231.687 | 10.003 | 333565.020 |

CP-SAT summary excludes the 3 infeasible `c101_50` rows from valid metric means.

## E. Selector Result

Evidence: `data/results/experiments/stat_tests_small.csv`
Curated copy: `reports/results/stat_tests_small.csv`

`alns_mosade` is slightly better than `alns_uniform` on mean objective in this exploratory small-scale run:

- paired_n: 9
- mean objective difference, `alns_mosade - alns_uniform`: -0.371
- Holm-adjusted p-value: 1.000
- reject at 0.05: False

This is an exploratory small-scale experiment. The difference is not
statistically significant and should not be presented as a proven improvement.

`ortools_routing` is better than `alns_mosade` on mean objective in this run:

- paired_n: 9
- mean objective difference, `alns_mosade - ortools_routing`: 13.450
- Holm-adjusted p-value: 0.899
- reject at 0.05: False

## F. CP-SAT Interpretation

CP-SAT is currently valid as a small-scale exact or feasibility-validation anchor, not as a blanket proof of optimality for all small experiments.

- Mini smoke: feasible, status `FEASIBLE`.
- C101_25 batch rows: feasible within the 30 second limit.
- C101_50 batch rows: `UNKNOWN` within the 30 second limit.

Do not claim CP-SAT optimality unless `status=OPTIMAL` or a valid optimality gap/bound is reported.
Do not treat `UNKNOWN` as infeasible; it is a time-limited no-solution-returned
state for this run.

## G. Generated Files

CSV:

- `data/results/smoke/solver_matrix.csv`
- `data/results/experiments/runs_small.csv`
- `data/results/experiments/summary_small.csv`
- `data/results/experiments/stat_tests_small.csv`
- `data/results/experiments/convergence/*.csv`

JSON:

- `data/results/smoke/solutions/*.json`
- `data/results/experiments/solutions/*.json`

Figures:

- `reports/figures/solver_cost_comparison.png`
- `reports/figures/solver_runtime_comparison.png`
- `reports/figures/alns_convergence.png`
- `reports/figures/selector_ablation.png`
- `reports/figures/convergence.svg`
- `reports/figures/cost_runtime.svg`
- `reports/figures/gap_boxplot.svg`
- `reports/figures/operator_probabilities.svg`
- `reports/figures/pair_heatmap.svg`
- `reports/figures/figure_sources.md`

Docs/config:

- `docs/environment.md`
- `configs/experiment_small.yaml`
- `configs/repro_check.yaml`

Curated, commit-friendly CSV copies:

- `reports/results/solver_matrix.csv`
- `reports/results/runs_small.csv`
- `reports/results/summary_small.csv`
- `reports/results/stat_tests_small.csv`
- `reports/results/README.md`

## H. Next Stage

Recommended next step is not yet Solomon 100/200 with CP-SAT included. First choose one of these paths:

1. Scope CP-SAT to mini and <=25 customer exact validation, then proceed to selector ablation and Solomon 100/200 for heuristic and OR-Tools comparisons.
2. Continue improving the CP-SAT formulation or add a separate feasibility-check mode before requiring C101_50 CP-SAT rows to be feasible.

The heuristic/OR-Tools side is ready for the next selector ablation round. The exact CP-SAT side should remain explicitly limited in interview claims.

This RUN-01 result must not be extrapolated to Solomon 100/200 or very-large-scale
settings. Larger-scale claims require separate result CSV evidence.
