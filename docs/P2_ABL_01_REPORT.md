# P2-ABL-01 Selector Ablation Report

Date: 2026-06-22

## A. Objective

This ablation tests whether the MOSADE-inspired ALNS selector provides a stable
benefit over uniform random selection and roulette-wheel selection.

This is an exploratory selector ablation, not a final claim of superiority.

## B. Configuration

Config: `configs/ablation_selectors.yaml`

Available local Solomon data only includes C101 plus the mini fixture. R101 and
RC101 files were not present locally, so they were not fabricated or included.

Instances:

- `mini_solomon`: `tests/fixtures/mini_solomon.txt`
- `c101_25`: `data/raw/solomon/C101_25.txt`
- `c101_50`: `data/raw/solomon/C101_100.txt`, `limit_customers: 50`

Selectors / solvers:

- `alns_uniform`
- `alns_roulette`
- `alns_mosade`

Seeds:

- `0, 1, 2, 3, 4`

Budget:

- ALNS time limit: 30 seconds
- ALNS max iterations: 300
- CP-SAT, greedy, and OR-Tools were intentionally excluded from ABL-01.

Planned and executed runs:

- `3 instances * 3 selectors * 5 seeds = 45`

## C. Data Files

Working output:

- `data/results/experiments/ablation_selectors.csv`
- `data/results/experiments/ablation_selectors_summary.csv`
- `data/results/experiments/ablation_selectors_stat_tests.csv`
- `data/results/experiments/solutions/selectors/*.json`
- `data/results/experiments/convergence/selectors/*.csv`

Curated commit-friendly copies:

- `reports/results/ablation_selectors.csv`
- `reports/results/ablation_selectors_summary.csv`
- `reports/results/ablation_selectors_stat_tests.csv`

Figures:

- `reports/figures/selector_ablation_cost.png`
- `reports/figures/selector_ablation_runtime.png`
- `reports/figures/selector_ablation_convergence.png`
- `reports/figures/selector_weight_evolution.png`
- `reports/figures/figure_sources.md`

## D. Feasibility

All ABL-01 runs completed without pipeline errors.

| selector | runs | feasible runs | feasible rate |
| --- | ---: | ---: | ---: |
| alns_uniform | 15 | 15 | 1.000 |
| alns_roulette | 15 | 15 | 1.000 |
| alns_mosade | 15 | 15 | 1.000 |

No UNKNOWN or missing-solution rows were included in selector metrics.

## E. Distance And Runtime

`objective` is the internal optimization objective. It includes vehicle-count
weighting and may be much larger than route distance. External comparisons
should report vehicles, distance, and runtime alongside objective; objective
should not be described as travel distance.

| selector | mean distance | median distance | mean runtime sec | mean objective |
| --- | ---: | ---: | ---: | ---: |
| alns_uniform | 243.680 | 250.667 | 1.783 | 333577.014 |
| alns_roulette | 247.737 | 254.010 | 1.643 | 333581.071 |
| alns_mosade | 251.215 | 250.667 | 1.734 | 333584.548 |

By instance mean distance:

| instance | uniform | roulette | mosade |
| --- | ---: | ---: | ---: |
| mini_solomon | 140.000 | 140.000 | 140.000 |
| c101_25 | 227.794 | 239.965 | 250.399 |
| c101_50 | 363.247 | 363.247 | 363.247 |

In this run, the only meaningful distance separation happened on `c101_25`;
`mini_solomon` and `c101_50` tied across selectors.

## F. Statistical Tests

Metric: objective / `cost`. Lower is better.

| comparison | paired_n | mean diff A-B | relative mean diff pct | median diff | Holm p | better mean |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| alns_mosade vs alns_uniform | 15 | 7.535 | 0.0023 | 0.000 | 1.000 | alns_uniform |
| alns_mosade vs alns_roulette | 15 | 3.478 | 0.0010 | 0.000 | 1.000 | alns_roulette |
| alns_roulette vs alns_uniform | 15 | 4.057 | 0.0012 | 0.000 | 1.000 | alns_uniform |

No comparison is statistically significant at 0.05 after Holm correction.

## G. Convergence And Selector Logs

ABL-01 wrote 45 convergence CSV files with 13,500 total rows. Each convergence
row includes:

- `iteration`
- `best_objective`
- `current_objective`
- `destroy_operator`
- `repair_operator`
- `selector`
- `reward`
- selected operator probability, weight, or pair credit where applicable
- raw `selector_snapshot` JSON

This is sufficient to explain the adaptive selector mechanism in the demo:

- uniform selector keeps flat probabilities;
- roulette selector records independent destroy/repair weights;
- MOSADE-inspired selector records pair-level probabilities and credits.

`selector_weight_evolution.png` visualizes probability concentration over time.

## H. Interpretation

MOSADE-inspired ALNS did not outperform uniform or roulette in this exploratory
ablation. The observed mean objective was slightly worse than both baselines:

- vs uniform: +7.535 objective units on average
- vs roulette: +3.478 objective units on average

Because median differences are zero and Holm-adjusted p-values are 1.000, this
run does not support a claim that MOSADE-inspired selection is better.

The honest interview interpretation is:

> I implemented the MOSADE-inspired selector and instrumented its pair-level
> probabilities, but in the current small C101-only ablation it does not yet
> show a stable advantage over simpler selectors.

## I. Limitations

- Current ablation uses only mini/C101 data because R101 and RC101 are not
  present locally.
- The sample is small: 3 instances and 5 seeds.
- The experiment reaches only 25/50 customer slices plus the mini fixture.
- CP-SAT does not participate in ABL-01.
- No 100/200/1000-customer conclusion should be inferred.
- This is not a production-scale runtime result.

## J. Next Step

Proceed to EXP-02, but treat selector results carefully:

1. Add or download R101/RC101 before claiming robustness across Solomon classes.
2. Run heuristic-only Solomon 100/200 comparisons with `alns_uniform`,
   `alns_roulette`, `alns_mosade`, and `ortools_routing`.
3. Consider tuning MOSADE parameters before re-running ablation:
   `temperature`, `decay`, `memory_size`, `exploration_floor`, and pair reward
   scaling.
4. Keep CP-SAT scoped to mini and 25-customer validation unless the exact model
   is improved.
