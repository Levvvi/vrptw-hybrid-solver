# P2-CHECKPOINT-01

Date: 2026-06-23

## A. Quality Gates

All commands were run under `.venv311`.

- Python version: 3.11.9
- Python executable: `<repo-root>\.venv311\Scripts\python.exe`
- `python -m pip check`: pass
- `python -m pytest -q`: `154 passed, 1 skipped, 3 warnings`
- `python -m ruff check .`: pass
- `python -m mypy src`: pass
- `vrptw info`: pass

## B. RUN-01 / RUN-02 / ABL-01 Status

RUN-01 is complete:

- Environment fixed and documented.
- Solver smoke matrix: 5/5 feasible.
- Small batch: 45 rows, 0 pipeline errors.
- CP-SAT on `c101_50` remains `UNKNOWN` and is not claimed as feasible or optimal.

RUN-02 is complete:

- Result schema and UNKNOWN handling audited.
- `status` means solver status.
- `pipeline_status` means execution success or error.
- Curated result strategy implemented under `reports/results/`.

ABL-01 is complete:

- Selector-only ALNS ablation finished.
- 45 rows: 3 instances * 3 selectors * 5 seeds.
- 0 pipeline errors.
- 100% feasible rate for all three selectors.
- Figures and curated CSVs generated.

## C. ABL-01 Real Conclusion

MOSADE-inspired selector did not outperform uniform or roulette in this
exploratory ablation.

Mean objective:

| selector | mean objective | mean distance | mean runtime sec |
| --- | ---: | ---: | ---: |
| `alns_uniform` | 333577.014 | 243.680 | 1.783 |
| `alns_roulette` | 333581.071 | 247.737 | 1.643 |
| `alns_mosade` | 333584.548 | 251.215 | 1.734 |

Holm-adjusted p-values:

- `alns_mosade` vs `alns_uniform`: 1.000
- `alns_mosade` vs `alns_roulette`: 1.000
- `alns_roulette` vs `alns_uniform`: 1.000

The correct wording is: MOSADE-inspired selection is implemented and
instrumented, but this C101-only small ablation does not show a stable advantage.

Objective note:

`objective` is the internal optimization objective and includes vehicle-count
weighting. It can be much larger than route distance. External comparisons
should report vehicles, distance, and runtime alongside objective; objective
should not be described as travel distance.

## D. Files Recommended For Commit

Source and tests:

- `.gitignore`
- `src/vrptw_hybrid/cli.py`
- `src/vrptw_hybrid/core/solution_io.py`
- `src/vrptw_hybrid/experiments/__init__.py`
- `src/vrptw_hybrid/experiments/plots.py`
- `src/vrptw_hybrid/experiments/runner.py`
- `src/vrptw_hybrid/experiments/statistics.py`
- `src/vrptw_hybrid/solvers/alns/solver.py`
- `src/vrptw_hybrid/solvers/exact_cp_sat.py`
- `src/vrptw_hybrid/solvers/ortools_routing.py`
- `tests/test_cli.py`
- `tests/test_experiment_runner.py`
- `tests/test_selectors.py`
- `tests/test_solution_io.py`

Configs:

- `configs/experiment_small.yaml`
- `configs/repro_check.yaml`
- `configs/ablation_selectors.yaml`

Docs:

- `docs/environment.md`
- `docs/P2_INSTALL_AUDIT.md`
- `docs/P2_RUN_01_REPORT.md`
- `docs/P2_RUN_02_AUDIT.md`
- `docs/P2_ABL_01_REPORT.md`
- `docs/P2_CHECKPOINT_01.md`
- `docs/P2_VRPTW_Codex_Workorders.md`

Curated results and figures:

- `reports/results/*`
- `reports/figures/*`

## E. Files That Must Stay Ignored

Do not commit:

- `.venv311/`
- `.ai-bridge/`
- `cache/`
- `.pytest_cache/`
- `.mypy_cache/`
- `.ruff_cache/`
- `data/raw/*`
- `data/results/*`

Confirmed ignore evidence:

- `.gitignore:2` ignores `.venv*/`
- `.gitignore:3` ignores `.ai-bridge/`
- `.gitignore:4` ignores `cache/`
- `.gitignore:24` ignores `data/raw/*`
- `.gitignore:28` ignores `data/results/*`

## F. Suggested Commit Split

1. `feat: add reproducible VRPTW experiment pipeline`

   Include source, tests, configs, `.gitignore`, and report-generation logic.

2. `docs: add small-scale experiment and ablation reports`

   Include docs, curated CSVs under `reports/results/`, and generated figures
   under `reports/figures/`.

Do not commit yet unless explicitly requested.
