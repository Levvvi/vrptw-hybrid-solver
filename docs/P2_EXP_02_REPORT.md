# P2-EXP-02 Medium Heuristic Comparison Report

Date: 2026-06-23

## A. Objective

EXP-02 extends the earlier C101-only experiments to C/R/RC distributions and a
larger benchmark scale. The goal is to compare greedy construction, OR-Tools
Routing, and ALNS selector variants on:

- Solomon 100-customer instances.
- Gehring & Homberger 200-customer extended benchmark instances.

CP-SAT is intentionally excluded from EXP-02. It remains a mini/25-customer
validation anchor, not a 100/200-customer baseline.

## B. Data Sources

Data source details, download URLs, checksums, and objective notes are recorded
in `docs/data_sources.md`.

Solomon 100-customer instances were downloaded from:

- `https://www.sintef.no/projectweb/top/vrptw/100-customers/`
- `https://www.sintef.no/globalassets/project/top/vrptw/solomon/solomon-100.zip`

Gehring & Homberger 200-customer extended benchmark instances were downloaded
from:

- `https://www.sintef.no/projectweb/top/vrptw/200-customers/`
- `https://www.sintef.no/globalassets/project/top/vrptw/homberger/200/homberger_200_customer_instances.zip`

Raw benchmark archives and extracted files are kept under `data/raw/benchmark/`
and are intentionally ignored by git.

## C. Benchmark Scope

Solomon 100 and Gehring & Homberger 200 are different benchmark families. The
200-customer files are not "Solomon 200"; they are extended benchmark instances
from Gehring & Homberger.

Instances:

| instance | family | customers | source file |
| --- | --- | ---: | --- |
| `c101_100` | Solomon 100 | 100 | `data/raw/benchmark/solomon_100/In/c101.txt` |
| `r101_100` | Solomon 100 | 100 | `data/raw/benchmark/solomon_100/In/r101.txt` |
| `rc101_100` | Solomon 100 | 100 | `data/raw/benchmark/solomon_100/In/rc101.txt` |
| `gh_c1_2_1_200` | Gehring & Homberger 200 | 200 | `data/raw/benchmark/homberger_200/C1_2_1.TXT` |
| `gh_r1_2_1_200` | Gehring & Homberger 200 | 200 | `data/raw/benchmark/homberger_200/R1_2_1.TXT` |
| `gh_rc1_2_1_200` | Gehring & Homberger 200 | 200 | `data/raw/benchmark/homberger_200/RC1_2_1.TXT` |

## D. Objective Convention

The benchmark objective hierarchy is:

1. Minimize vehicles.
2. Minimize total distance.

The project also reports `objective` / `cost`, an internal vehicle-weighted
optimization objective. That value is not route distance. External comparisons
should read vehicles, distance, runtime, feasible rate, and objective together.

## E. Configuration

Config: `configs/experiment_medium.yaml`

Solvers:

- `greedy`
- `ortools_routing`
- `alns_uniform`
- `alns_roulette`
- `alns_mosade`

Seeds: `0, 1, 2`

Budgets:

- OR-Tools Routing time limit: 60 seconds.
- ALNS time limit: 60 seconds.
- ALNS max iterations: 500.

Planned and executed runs:

- `6 instances * 5 solvers * 3 seeds = 90`

## F. Output Files

Working outputs:

- `data/results/experiments/runs_medium.csv`
- `data/results/experiments/summary_medium.csv`
- `data/results/experiments/stat_tests_medium.csv`
- `data/results/experiments/solutions/medium/*.json`
- `data/results/experiments/convergence/medium/*.csv`

Curated commit-friendly outputs:

- `reports/results/runs_medium.csv`
- `reports/results/summary_medium.csv`
- `reports/results/stat_tests_medium.csv`

Figures:

- `reports/figures/medium_solver_cost.png`
- `reports/figures/medium_solver_runtime.png`
- `reports/figures/medium_feasible_rate.png`
- `reports/figures/medium_convergence.png`
- `reports/figures/figure_sources.md`

## G. Feasibility And Aggregate Results

The batch completed with 90 rows and 0 pipeline error rows. Feasibility is
reported separately because OR-Tools Routing did not find a solution for every
instance within the 60-second limit.

| solver | valid runs | feasible rate | mean vehicles | mean distance | mean runtime sec |
| --- | ---: | ---: | ---: | ---: | ---: |
| `alns_uniform` | 18 | 1.000 | 18.556 | 3076.988 | 40.643 |
| `alns_roulette` | 18 | 1.000 | 18.667 | 3056.841 | 40.349 |
| `alns_mosade` | 18 | 1.000 | 18.667 | 3067.615 | 40.592 |
| `greedy` | 18 | 1.000 | 19.167 | 3530.322 | 28.744 |
| `ortools_routing` | 9 | 0.500 | 17.000 | 2403.523 | 60.009 |

OR-Tools Routing returned `NO_SOLUTION` for `r101_100`, `rc101_100`, and
`gh_r1_2_1_200` across all three seeds. These rows are not included in mean
distance or paired distance comparisons.

## H. Best Observed Gap

`runs_medium.csv` includes derived best-observed fields:

- `best_observed_vehicles`
- `best_observed_distance`
- `best_observed_objective`
- `vehicle_gap_to_best_observed`
- `distance_gap_to_best_observed_pct`
- `objective_gap_to_best_observed_pct`

The best-observed comparison is exploratory and internal to this run. It is not
a replacement for verified BKS tables, especially for Gehring & Homberger 200.

Mean objective gap to best observed:

| solver | mean objective gap pct |
| --- | ---: |
| `ortools_routing` | 0.000 |
| `alns_uniform` | 1.862 |
| `alns_roulette` | 2.417 |
| `alns_mosade` | 2.418 |
| `greedy` | 5.371 |

## I. Statistical Comparisons

Paired tests use the `distance` metric and only feasible rows with solutions.
They are exploratory because the sample size is small.

Key comparisons:

| comparison | paired n | mean diff A-B | relative diff pct | Holm p | better mean distance |
| --- | ---: | ---: | ---: | ---: | --- |
| `alns_mosade` vs `alns_uniform` | 18 | -9.372 | -0.305 | 1.000 | `alns_mosade` |
| `alns_mosade` vs `alns_roulette` | 18 | 10.775 | 0.352 | 1.000 | `alns_roulette` |
| `alns_mosade` vs `ortools_routing` | 9 | 410.542 | 17.081 | 0.166 | `ortools_routing` |
| `alns_uniform` vs `ortools_routing` | 9 | 344.026 | 14.313 | 0.166 | `ortools_routing` |

No MOSADE comparison is significant after Holm correction. The only significant
distance improvements in this run are ALNS variants over greedy.

## J. Interpretation

MOSADE-inspired selection is still not proven better. In this broader EXP-02
run:

- MOSADE had a slightly lower mean distance than uniform, but not significantly.
- MOSADE was worse than roulette by mean distance.
- MOSADE was worse than uniform by vehicle-weighted objective.
- The result does not support a claim of stable MOSADE superiority.

OR-Tools Routing is a strong baseline where it returns a solution. On its 9
feasible paired rows, it has lower mean distance than the ALNS variants. However,
it only produced feasible solutions for half of the 18 OR-Tools runs under the
60-second limit, so the honest conclusion is "strong but not consistently
available under this budget."

ALNS is much stronger than greedy and has 100% feasible rate on this selected
medium suite.

## K. Limitations

- This is still a small exploratory medium-scale experiment: 6 instances and 3 seeds.
- No 400/600/800/1000-customer instances were run.
- No CP-SAT large-scale baseline is included.
- Gehring & Homberger 200 BKS values are not included.
- OR-Tools no-solution rows are excluded from distance means and paired tests.
- Results should not be described as production-scale or very-large-scale evidence.

## L. Next Step

Recommended next step: VIS-01, using real EXP-02 solution JSON to build a
Streamlit/Folium map demo.

Secondary next steps:

- ABL-02 mechanism diagnosis, because MOSADE is still not robustly better than
  uniform or roulette.
- Tune MOSADE reward scaling and pair-memory parameters before scaling further.
- If selector behavior improves, run a later EXP-03 with 400/600 customers; do
  not jump to 1000 before the 200-customer story is stable.
