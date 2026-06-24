# P2-VIS-01A Benchmark Route Viewer Report

Date: 2026-06-23

## A. Goal

VIS-01A adds a benchmark route viewer for EXP-02 results. It uses real
`runs_medium.csv` rows, solution JSON, and source benchmark instances to display
Solomon / Gehring & Homberger routes in two-dimensional benchmark coordinates.

This is not a real city road map.

## B. Data Source

Primary EXP-02 inputs:

- `reports/results/runs_medium.csv`
- `reports/results/summary_medium.csv`
- `reports/results/stat_tests_medium.csv`
- `data/results/experiments/solutions/medium/*.json`
- `data/raw/benchmark/...`

For public/demo use, a small curated subset was copied into:

- `reports/demo/artifacts/*.json`
- `reports/demo/png/*.png`
- `reports/demo/html/*.html`
- `reports/demo/solutions/*.json`

The curated demo artifacts are self-contained for plotting because they include
depot, customer coordinates, route sequences, and route points.

## C. Benchmark Viewer vs City Map

Benchmark route viewer:

- Coordinates are Solomon/GH benchmark `x/y`.
- Route lines are depot/customer/depot polylines in benchmark space.
- No map tiles are used.
- The route plot explicitly states that coordinates are not latitude/longitude.

City road demo:

- Requires real `lat/lon`, OSM graph data, and graph-following route geometry.
- Deferred to VIS-01B.

## D. Curated Demo Runs

VIS-01A generated these curated runs:

| instance | solver | seed | purpose |
| --- | --- | ---: | --- |
| `c101_100` | `alns_roulette` | 0 | Solomon C route demo |
| `r101_100` | `alns_roulette` | 0 | Solomon R route demo |
| `rc101_100` | `alns_roulette` | 0 | Solomon RC route demo |
| `gh_c1_2_1_200` | `alns_uniform` | 0 | GH C route demo |
| `gh_r1_2_1_200` | `alns_roulette` | 0 | GH R route demo |
| `gh_rc1_2_1_200` | `alns_roulette` | 0 | GH RC route demo |
| `gh_rc1_2_1_200` | `ortools_routing` | 0 | OR-Tools feasible route demo |
| `r101_100` | `ortools_routing` | 0 | OR-Tools `NO_SOLUTION` status demo |

MOSADE is intentionally not used as the curated default because EXP-02 does not
show that it is superior to uniform or roulette selection.

## E. Streamlit

Start command:

```powershell
Set-Location <repo-root>
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process
.\.venv311\Scripts\Activate.ps1
streamlit run apps/streamlit_app.py
```

Supported modes:

- `Curated demo`: default, reads `reports/demo/artifacts/*.json`.
- `Full local experiment`: reads `reports/results/runs_medium.csv`, then pairs
  a selected row with `source_file` and `solution_json`.

The full local mode shows a friendly error if the selected row points to ignored
local files under `data/results/` or `data/raw/` that are not present.

## F. CLI Plot

Example:

```powershell
vrptw plot --benchmark `
  --run-csv reports/results/runs_medium.csv `
  --instance c101_100 `
  --solver alns_roulette `
  --seed 0 `
  --output-png reports/demo/png/c101_100_alns_roulette_seed0.png `
  --output-artifact reports/demo/artifacts/c101_100_alns_roulette_seed0.json `
  --output-html reports/demo/html/c101_100_alns_roulette_seed0.html
```

The command selects one run row, builds a benchmark route artifact, and writes a
PNG route plot. If the selected row is `NO_SOLUTION`, it writes a status artifact
and status figure instead of failing.

## G. NO_SOLUTION Handling

OR-Tools Routing has a 0.5 feasible rate in EXP-02. The viewer does not hide
that:

- Curated demo includes `r101_100 / ortools_routing / seed 0` as a no-solution example.
- `NO_SOLUTION` artifacts have `feasible=false`, `has_solution=false`, and `routes=[]`.
- Streamlit displays: `No route available for this run. Solver status = NO_SOLUTION under the configured time budget.`

## H. Current Limits

- Benchmark `x/y` coordinates are not real road-network locations.
- Routes are not real driving paths.
- VIS-01A does not use Folium map tiles.
- MOSADE is not described as outperforming baselines.
- OR-Tools Routing is shown as strong when feasible but not consistently
  available under the 60-second EXP-02 budget.

## I. Next Step

Proceed to VIS-01B only after preparing:

- a small city instance with real lat/lon,
- an OSM GraphML cache or documented download path,
- a solved city solution JSON,
- and a Streamlit mode that clearly separates city road routes from benchmark
  x-y routes.
