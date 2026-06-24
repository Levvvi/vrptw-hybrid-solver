# Claim Registry

This registry maps public claims to evidence files. Use it as the source for
README, resume, and interview wording.

| Public claim | Evidence | Source file | Notes / caveat |
| --- | --- | --- | --- |
| The project has a passing local quality gate. | `187 passed, 1 skipped`; ruff and mypy pass | `docs/P2_DOC_01_REPORT.md` | Latest DOC-01 gate. |
| RUN-01 produced real small-scale result files. | Small runs, summary, stats, figures, and solution artifacts exist | `docs/P2_RUN_01_REPORT.md`, `reports/results/summary_small.csv` | CP-SAT is time-limited. |
| RUN-02 audited result provenance and UNKNOWN handling. | UNKNOWN rows are not treated as feasible or optimal | `docs/P2_RUN_02_AUDIT.md` | Small-scale experiment is exploratory. |
| MOSADE-inspired selector did not outperform uniform/roulette in ABL-01. | Mean objective was slightly worse; Holm p-values were 1.000 | `docs/P2_ABL_01_REPORT.md`, `reports/results/ablation_selectors_summary.csv` | Do not claim MOSADE superiority. |
| ABL-01 produced selector convergence/probability logs. | 45 convergence CSV files and selector weight figure | `docs/P2_ABL_01_REPORT.md`, `reports/figures/selector_weight_evolution.png` | Mechanism is demonstrable even without performance win. |
| EXP-02 ran 90 medium benchmark rows. | 6 instances x 5 solvers x 3 seeds | `docs/P2_EXP_02_REPORT.md`, `reports/results/runs_medium.csv` | Solomon 100 plus Gehring-Homberger 200 selected instances. |
| EXP-02 had 0 pipeline error rows. | `pipeline_error_runs = 0` in summaries | `reports/results/summary_medium.csv` | Solver no-solution is tracked separately. |
| OR-Tools Routing feasible rate was 0.5 under 60s in EXP-02. | `feasible_rate = 0.5` | `reports/results/summary_medium.csv` | Strong when feasible, not consistently available under budget. |
| ALNS variants reached 1.0 feasible rate in EXP-02. | `feasible_rate = 1.0` for uniform, roulette, MOSADE | `reports/results/summary_medium.csv` | Selected medium suite only. |
| OR-Tools Routing had lower mean distance where it found solutions. | `distance_mean = 2403.523` over feasible OR-Tools rows | `reports/results/summary_medium.csv`, `docs/P2_EXP_02_REPORT.md` | Infeasible/no-solution rows excluded from distance mean. |
| VIS-01A benchmark viewer uses Solomon/GH x-y coordinates. | Route artifacts declare `coordinate_system = benchmark_xy` and `is_real_map = false` | `docs/P2_VIS_01A_REPORT.md`, `reports/demo/artifacts/` | Do not describe as a real map. |
| VIS-01B city demo uses Berlin Mitte OSM road geometry. | City instance and Folium artifacts under `reports/demo/city` | `docs/P2_VIS_01B_REPORT.md`, `reports/demo/city/city_instance_berlin_mitte_30.json` | Uses synthetic orders on OSM graph. |
| VIS-01B uses shortest-path proxy travel times. | Report and city artifact notes | `docs/P2_VIS_01B_REPORT.md`, `reports/demo/city/city_instance_berlin_mitte_30.json` | Not measured travel-time data. |
| VIS-01B greedy result. | Feasible, 3 vehicles, 32309.954 m, 0.200 s | `reports/demo/city/city_summary.csv` | Demo only. |
| VIS-01B OR-Tools result. | Feasible, 3 vehicles, 22701.994 m, 60.010 s | `reports/demo/city/city_summary.csv` | 60s budget. |
| VIS-01B ALNS roulette result. | Feasible, 3 vehicles, 23956.684 m, 6.214 s | `reports/demo/city/city_summary.csv` | Demo only. |
| VIS-01B ALNS MOSADE result. | Feasible, 3 vehicles, 23956.684 m, 6.256 s | `reports/demo/city/city_summary.csv` | Not better than roulette here. |
