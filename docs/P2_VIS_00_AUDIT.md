# P2-VIS-00 Audit

Date: 2026-06-23

## A. Quality Gates

Commands were run under `<repo-root>\.venv311\Scripts\python.exe`.

| Gate | Result |
| --- | --- |
| Python | `3.11.9` |
| `python -m pip check` | pass |
| `python -m pytest -q` | `167 passed, 1 skipped, 3 warnings` |
| `python -m ruff check .` | pass |
| `python -m mypy src` | pass |
| `vrptw info` | pass |

## B. EXP-02 Result Files

Audited files:

- `docs/P2_EXP_02_REPORT.md`
- `configs/experiment_medium.yaml`
- `reports/results/runs_medium.csv`
- `reports/results/summary_medium.csv`
- `reports/results/stat_tests_medium.csv`
- `reports/figures/figure_sources.md`
- `reports/figures/medium_solver_cost.png`
- `reports/figures/medium_solver_runtime.png`
- `reports/figures/medium_feasible_rate.png`
- `reports/figures/medium_convergence.png`

CSV status:

| file | rows | notes |
| --- | ---: | --- |
| `reports/results/runs_medium.csv` | 90 | 6 instances * 5 solvers * 3 seeds |
| `reports/results/summary_medium.csv` | 5 | one row per solver |
| `reports/results/stat_tests_medium.csv` | 10 | paired solver comparisons |

`runs_medium.csv` includes the visualization-critical columns:

- `instance`, `solver`, `seed`
- `feasible`, `status`, `pipeline_status`, `has_solution`
- `vehicles`, `distance`, `objective`, `cost`, `runtime_sec`
- `source_file`
- `solution_json`
- `convergence_csv`

Expected blanks are present:

- `iterations`, `best_iteration`, `selector`, and `convergence_csv` are blank for non-ALNS solvers.
- BKS fields are blank where no verified reference exists.
- `gap`, `lower_bound`, and `best_bound` are blank because EXP-02 did not use exact solvers.
- Best-observed fields are blank for OR-Tools no-solution rows.

EXP-02 solvers:

- `greedy`
- `ortools_routing`
- `alns_uniform`
- `alns_roulette`
- `alns_mosade`

EXP-02 instances:

- Solomon 100: `c101_100`, `r101_100`, `rc101_100`
- Gehring & Homberger 200: `gh_c1_2_1_200`, `gh_r1_2_1_200`, `gh_rc1_2_1_200`

Aggregate results:

| solver | feasible rate | mean vehicles | mean distance | mean runtime sec |
| --- | ---: | ---: | ---: | ---: |
| `alns_uniform` | 1.000 | 18.556 | 3076.988 | 40.643 |
| `alns_roulette` | 1.000 | 18.667 | 3056.841 | 40.349 |
| `alns_mosade` | 1.000 | 18.667 | 3067.615 | 40.592 |
| `greedy` | 1.000 | 19.167 | 3530.322 | 28.744 |
| `ortools_routing` | 0.500 | 17.000 | 2403.523 | 60.009 |

OR-Tools Routing `NO_SOLUTION` rows:

| instance | seeds | status |
| --- | --- | --- |
| `r101_100` | `0, 1, 2` | `NO_SOLUTION` |
| `rc101_100` | `0, 1, 2` | `NO_SOLUTION` |
| `gh_r1_2_1_200` | `0, 1, 2` | `NO_SOLUTION` |

Report wording audit:

- `docs/P2_EXP_02_REPORT.md` distinguishes Solomon 100 from Gehring & Homberger 200.
- It states that CP-SAT is not a 100/200 baseline.
- It states that MOSADE is not proven better.
- It states that OR-Tools has a 50% feasible rate under the 60-second budget.
- It avoids production-scale and very-large-scale claims.

## C. Solution JSON Audit

Search roots:

- `data/results/`
- `reports/`
- `outputs/`
- `artifacts/`

EXP-02 solution files are under:

- `data/results/experiments/solutions/medium/*.json`

Findings:

| item | result |
| --- | --- |
| EXP-02 run rows | 90 |
| rows with existing `solution_json` path | 90 |
| feasible rows with route stops | 81 |
| OR-Tools no-solution rows | 9 |
| missing `source_file` paths | 0 |
| invalid customer references in feasible routes | 0 |

The solution JSON schema is uniform:

- `instance_name`
- `solver_name`
- `feasible`
- `vehicles_used`
- `total_distance`
- `total_duration`
- `objective`
- `runtime_sec`
- `routes`
- `metadata`

Each route contains:

- `vehicle_id`
- `stops`
- `distance`
- `duration`
- `load`

Each stop contains:

- `customer_id`
- `arrival_time`
- `start_service_time`
- `departure_time`
- `load_after`

Important caveat:

- The solution JSON itself does not store `source_file`, top-level `seed`, or top-level `instance` alias.
- Those fields are available from `reports/results/runs_medium.csv`.
- VIS-01A should load a selected row from `runs_medium.csv`, parse `source_file`, then load `solution_json`.

OR-Tools `NO_SOLUTION` handling:

- The 9 `NO_SOLUTION` rows do have JSON files, but those files contain empty `routes` and `feasible=false`.
- They are status artifacts, not route visualization candidates.
- VIS-01A should filter selectable solution rows with `pipeline_status == ok`, `feasible == true`, and `has_solution == true`.

Coordinate linkage:

- Feasible route customer ids can be mapped back to the parsed benchmark instance.
- Example: `c101_100__alns_uniform__seed0.json` maps customer `20` to `x=30.0`, `y=50.0` from `data/raw/benchmark/solomon_100/In/c101.txt`.

## D. Visualization Module Audit

Modules:

- `src/vrptw_hybrid/visualization/geojson.py`
- `src/vrptw_hybrid/visualization/folium_map.py`
- `apps/streamlit_app.py`

Import smoke:

- `apps.streamlit_app`: pass
- `vrptw_hybrid.visualization.folium_map`: pass
- `vrptw_hybrid.visualization.geojson`: pass

Current capabilities:

- `solution_geojson(instance, solution)` can produce point and route FeatureCollections.
- Without an OSM graph, route geometry is straight-line depot/customer/depot coordinates.
- With graph metadata and a graph object, it can build graph-following route coordinates.
- `render_solution_map(instance, solution)` can render a Folium map from a `VRPTWInstance` and `Solution`.
- The Folium popups include route customer ids, distance, duration, load, time windows, and service times.

Benchmark route viewer status:

- Data is sufficient for a benchmark x-y route viewer.
- Existing GeoJSON uses `x/y` as `lon/lat` fallback. For Solomon/GH benchmark files this is acceptable only as benchmark coordinate visualization.
- The UI must clearly avoid calling these coordinates real city geography.
- A pure Plotly/matplotlib x-y viewer may be semantically cleaner than an OpenStreetMap tile for benchmark data.

Current Streamlit app limitations:

- It is currently a mini fixture demo with hard-coded `DEMO_INSTANCES`.
- It can load a precomputed solution JSON, but the displayed instance still comes from the sidebar mini fixture.
- That means it cannot safely show EXP-02 routes until it can pair a selected `runs_medium.csv` row with its matching `source_file`.
- It does not currently read `reports/results/runs_medium.csv`.
- It does not currently filter out OR-Tools `NO_SOLUTION` rows.

Fake data / hard-coded data:

- The app uses mini fixture choices for the current demo.
- Tests use fake Folium objects for unit testing only.
- EXP-02 result files and solution JSON are real run artifacts.

## E. VIS-01A Benchmark Route Viewer

VIS-01A can be done immediately.

Recommended data flow:

1. Read `reports/results/runs_medium.csv`.
2. Filter to `pipeline_status == ok`, `feasible == true`, `has_solution == true`.
3. Let the user choose instance, solver, seed, or a best-observed row.
4. Parse `source_file` with `parse_solomon`.
5. Load `solution_json` with `load_solution_json`.
6. Render benchmark x-y routes with depot, customers, route order, vehicles, distance, objective, runtime, and status.
7. Explicitly label the view as benchmark coordinates, not a real city map.
8. Show OR-Tools `NO_SOLUTION` rows in a disabled or separate status table so the 50% feasible rate remains visible.

Good default VIS-01A candidates:

- `c101_100 / alns_uniform / seed 0`
- `r101_100 / alns_uniform / seed 0`
- `gh_c1_2_1_200 / ortools_routing / seed 0`
- `gh_rc1_2_1_200 / ortools_routing / seed 0`

Do not present MOSADE as the default "best" selector. EXP-02 does not support
that claim.

## F. VIS-01B City Road Demo

VIS-01B is not ready as a direct continuation of EXP-02.

Existing pieces:

- `src/vrptw_hybrid/data/osm_network.py` can load/cache OSM driving networks.
- `src/vrptw_hybrid/data/synthetic.py` can generate city-style VRPTW instances from graph nodes with `lat/lon` and `graph_node_ids`.
- `visualization.geojson` can use graph paths when a graph and graph-node mapping are present.

Missing for a real city road demo:

- A committed or reproducible small city configuration.
- A cached OSM GraphML file or documented download step.
- A city instance loader for saved JSON.
- A solved city solution JSON.
- A Streamlit path that distinguishes real `lat/lon` city routes from benchmark x-y routes.

VIS-01B should be a separate task after VIS-01A.

## G. Minimal Fix Plan If Solution JSON Were Missing

No fix is needed for EXP-02 route JSON: the runner already saved all 90 solution
JSON paths.

If future runs lack route JSON, the minimal fix is:

1. Ensure batch configs set `experiment.solution_dir`.
2. Ensure `runner.run_batch()` calls `save_solution_json()` for every solver result.
3. Store `solution_json` and `source_file` in the run CSV.
4. Filter route viewers by `feasible` and `has_solution`.

## H. Recommended Next Work Order

Proceed with `P2-VIS-01A Benchmark Route Viewer`.

Scope:

- Update `apps/streamlit_app.py` to support a "Precomputed EXP-02 results" mode.
- Read `reports/results/runs_medium.csv`.
- Filter feasible rows and separately show OR-Tools no-solution rows.
- Load matching `source_file` and `solution_json`.
- Render benchmark x-y routes without claiming real city geography.
- Add tests for row filtering, instance/solution pairing, and route table generation.

Defer `P2-VIS-01B City Road Demo` until after a small city dataset and solution
pipeline are prepared.

## I. Commit / Ignore Guidance

Suggested commit candidates:

- `docs/P2_VIS_00_AUDIT.md`
- Existing EXP-02 docs/configs/scripts/tests/results/figures intended for portfolio review.
- `reports/results/*.csv`
- `reports/figures/*.png`

Must remain ignored:

- `.venv/`
- `.venv311/`
- `.ai-bridge/`
- `cache/`
- `data/raw/*`
- `data/results/*`
