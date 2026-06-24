# P2-RUN-02 Audit

Date: 2026-06-22

## A. Quality Gates

All commands were run under `.venv311`.

- Python: `<repo-root>\.venv311\Scripts\python.exe`
- Python version: 3.11.9
- `python -m pip check`: pass
- `python -m pytest -q`: `150 passed, 1 skipped, 3 warnings`
- `python -m ruff check .`: pass
- `python -m mypy src`: pass
- `vrptw info`: pass

## B. RUN-01 File Audit

Required files exist and were read:

| file | status | content check |
| --- | --- | --- |
| `docs/environment.md` | exists | environment and quality gate evidence present |
| `configs/experiment_small.yaml` | exists | 3 instances, 5 solvers, 3 seeds |
| `docs/P2_RUN_01_REPORT.md` | exists | updated with limits and UNKNOWN wording |
| `data/results/smoke/solver_matrix.csv` | exists | 5 rows |
| `data/results/experiments/runs_small.csv` | exists | 45 rows |
| `data/results/experiments/summary_small.csv` | exists | 5 rows |
| `data/results/experiments/stat_tests_small.csv` | exists | 10 rows |
| `reports/figures/*.png` | exists | 4 non-empty PNG files |

Curated commit-friendly copies exist under `reports/results/`.

## C. CSV Schema Audit

Both `solver_matrix.csv` and `runs_small.csv` now contain all required columns:

- `solver`
- `instance`
- `seed`
- `feasible`
- `vehicles`
- `distance`
- `objective`
- `runtime_sec`
- `status`

They also contain the recommended reproducibility columns:

- `time_limit_sec`
- `gap`
- `lower_bound`
- `best_bound`
- `has_solution`
- `error`
- `route_count`
- `customer_count`
- `source_file`
- `config_file`
- `created_at`

Empty fields are intentional where no evidence exists:

- `gap` and `lower_bound` are blank because no reliable optimality gap was computed.
- `best_bound` is populated only where solver metadata provided it.
- `convergence_csv` is blank for non-ALNS solvers.
- BKS distance gap fields are blank where no verified matching BKS comparison exists.

`status` now means solver status, while `pipeline_status` means whether the batch command itself completed or errored.

## D. CP-SAT UNKNOWN Handling

`runs_small.csv` has exactly three `c101_50 + cp_sat` rows:

| seed | status | pipeline_status | feasible | has_solution |
| ---: | --- | --- | --- | --- |
| 0 | UNKNOWN | ok | False | False |
| 1 | UNKNOWN | ok | False | False |
| 2 | UNKNOWN | ok | False | False |

This is correct:

- `UNKNOWN` is not written as `OPTIMAL`.
- `UNKNOWN` is not described as infeasible.
- `UNKNOWN` rows are excluded from valid metric means because `feasible=False`.
- `summary_small.csv` reports `cp_sat` as `runs=9`, `valid_runs=6`, `feasible_rate=0.6667`.
- `stat_tests_small.csv` uses `paired_n=6` for `cp_sat` vs `alns_mosade`, so the `c101_50` UNKNOWN rows are not used in that paired comparison.

`docs/P2_RUN_01_REPORT.md` now explicitly states that the experiment is exploratory, CP-SAT is time-limited, UNKNOWN is neither infeasibility nor optimality, and small results must not be extrapolated to very-large-scale claims.

## E. Reproducibility Check

Dry run:

```powershell
vrptw batch --config configs\experiment_small.yaml --dry-run
```

Result:

- planned runs: 45

Minimal reproduction run:

```powershell
vrptw batch --config configs\repro_check.yaml
```

Generated:

- `data/results/repro_check/runs_repro_check.csv`
- `data/results/repro_check/solutions/*.json`
- `data/results/repro_check/convergence/*.csv`

Reproduction result:

- rows: 5
- pipeline error rows: 0
- solution JSON files: 5
- convergence CSV files: 2

This validates that the result pipeline can regenerate files without overwriting RUN-01.

## F. Figure Reproducibility

Figures were regenerated with:

```powershell
vrptw plot --results data\results\experiments\runs_small.csv --output reports\figures
```

The plot command now writes:

- `reports/figures/figure_sources.md`

This manifest records the input CSV, the CLI command, and generated output paths. The PNG files are non-empty:

- `solver_cost_comparison.png`
- `solver_runtime_comparison.png`
- `alns_convergence.png`
- `selector_ablation.png`

No hand-made figure is required for RUN-01.

## G. Gitignore And Result Submission Strategy

Current `.gitignore` correctly ignores:

- `.venv/`
- `.venv*/`
- `.ai-bridge/`
- `cache/`
- `__pycache__/`
- `.pytest_cache/`
- `.mypy_cache/`
- `.ruff_cache/`
- `data/raw/*`
- `data/results/*`

Recommended and implemented strategy: Strategy A.

Keep `data/results/*` ignored as the working output area. Commit curated small-scale evidence under:

- `reports/results/solver_matrix.csv`
- `reports/results/runs_small.csv`
- `reports/results/summary_small.csv`
- `reports/results/stat_tests_small.csv`
- `reports/results/README.md`
- `reports/figures/*.png`
- `reports/figures/figure_sources.md`

This avoids committing large future raw experiment output while still making small reproducible evidence visible.

## H. Files Fixed Or Added

Code:

- `src/vrptw_hybrid/cli.py`
- `src/vrptw_hybrid/core/solution_io.py`
- `src/vrptw_hybrid/experiments/__init__.py`
- `src/vrptw_hybrid/experiments/plots.py`
- `src/vrptw_hybrid/experiments/runner.py`
- `src/vrptw_hybrid/experiments/statistics.py`
- `src/vrptw_hybrid/solvers/exact_cp_sat.py`
- `src/vrptw_hybrid/solvers/ortools_routing.py`

Tests:

- `tests/test_cli.py`
- `tests/test_experiment_runner.py`
- `tests/test_solution_io.py`

Configs/docs/results:

- `.gitignore`
- `configs/experiment_small.yaml`
- `configs/repro_check.yaml`
- `docs/environment.md`
- `docs/P2_RUN_01_REPORT.md`
- `docs/P2_RUN_02_AUDIT.md`
- `reports/results/*`
- `reports/figures/*`

## I. Claims Not Ready For README Or Resume

Do not claim:

- CP-SAT proved optimality for the small experiment.
- CP-SAT proved C101_50 infeasible.
- MOSADE is statistically significantly better than uniform ALNS.
- ALNS beats OR-Tools on this small batch.
- Any Solomon 100/200 result.
- Any 500/1000-customer scaling result.
- Any production runtime or industrial cost saving percentage.

Allowed wording:

- The environment is Install Ready for core Python experiments.
- The solver matrix is feasible on mini Solomon.
- The small batch is an exploratory experiment with transparent UNKNOWN CP-SAT rows.
- MOSADE is slightly better than uniform ALNS in mean objective on this slice, but not statistically significant.

## J. Next Stage Recommendation

Recommended next stage: ABL-01, then EXP-02.

Order:

1. ABL-01: selector ablation with `alns_uniform`, `alns_roulette`, and `alns_mosade`, excluding CP-SAT from larger heuristic-only comparisons.
2. EXP-02: Solomon 100/200 heuristic and OR-Tools batch with fixed budgets.
3. VIS-01: Streamlit/Folium demo wired to curated precomputed solution JSON.

CP-SAT should remain scoped to mini and 25-customer validation unless the exact formulation is further improved.
