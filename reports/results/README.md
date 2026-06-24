# Curated RUN-01 Results

These CSV files are the small, reproducible evidence tables copied from the
ignored `data/results/` working output directory.

Source files:

- `solver_matrix.csv` from `data/results/smoke/solver_matrix.csv`
- `runs_small.csv` from `data/results/experiments/runs_small.csv`
- `summary_small.csv` from `data/results/experiments/summary_small.csv`
- `stat_tests_small.csv` from `data/results/experiments/stat_tests_small.csv`
- `ablation_selectors.csv` from `data/results/experiments/ablation_selectors.csv`
- `ablation_selectors_summary.csv` from `data/results/experiments/ablation_selectors_summary.csv`
- `ablation_selectors_stat_tests.csv` from `data/results/experiments/ablation_selectors_stat_tests.csv`

Scope:

- exploratory small-scale experiment only;
- mini Solomon, C101 25-customer, and C101 50-customer slices;
- seeds 0, 1, 2 for the small batch;
- CP-SAT is time-limited and has `UNKNOWN` rows for `c101_50`;
- no 100/200/1000-customer conclusion should be inferred from these files.
- selector ablation is ALNS-only and compares `alns_uniform`, `alns_roulette`,
  and `alns_mosade` on the currently available C101/mini instances.
