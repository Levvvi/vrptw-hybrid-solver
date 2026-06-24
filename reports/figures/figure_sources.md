# Figure Sources

- Command: `vrptw plot --results data\results\experiments\runs_small.csv --output reports\figures`
- Primary input CSV: `data\results\experiments\runs_small.csv`
- Solution JSON paths are read from the `solution_json` column.
- ALNS convergence data is read from solution metadata and convergence-capable runs.

## Outputs

- `reports\figures\convergence.svg`
- `reports\figures\cost_runtime.svg`
- `reports\figures\gap_boxplot.svg`
- `reports\figures\operator_probabilities.svg`
- `reports\figures\pair_heatmap.svg`
- `reports\figures\solver_cost_comparison.png`
- `reports\figures\solver_runtime_comparison.png`
- `reports\figures\alns_convergence.png`
- `reports\figures\selector_ablation.png`

## P2-ABL-01 Selector Ablation

- Primary input CSV: `data/results/experiments/ablation_selectors.csv`
- Summary CSV: `data/results/experiments/ablation_selectors_summary.csv`
- Statistical tests CSV: `data/results/experiments/ablation_selectors_stat_tests.csv`
- Convergence source: `data/results/experiments/convergence/selectors/*.csv`
- Generated figures:
  - `reports/figures/selector_ablation_cost.png`
  - `reports/figures/selector_ablation_runtime.png`
  - `reports/figures/selector_ablation_convergence.png`
  - `reports/figures/selector_weight_evolution.png`

## P2-EXP-02 Medium Heuristic Comparison

- Command: `python scripts/generate_medium_assets.py`
- Primary input CSV: `data/results/experiments/runs_medium.csv`
- Summary CSV: `data/results/experiments/summary_medium.csv`
- Statistical tests CSV: `data/results/experiments/stat_tests_medium.csv`
- Convergence source: `data/results/experiments/convergence/medium/*.csv`
- Generated figures:
  - `reports/figures/medium_solver_cost.png`
  - `reports/figures/medium_solver_runtime.png`
  - `reports/figures/medium_feasible_rate.png`
  - `reports/figures/medium_convergence.png`

## P2-VIS-01A Benchmark Route Demo

- Command: `python scripts/generate_demo_artifacts.py`
- Primary input CSV: `reports/results/runs_medium.csv`
- Source solution JSON: selected rows from `data/results/experiments/solutions/medium/*.json`
- Generated artifacts:
  - `reports/demo/artifacts/*.json`
  - `reports/demo/png/*.png`
  - `reports/demo/html/*.html`
  - `reports/demo/solutions/*.json`
