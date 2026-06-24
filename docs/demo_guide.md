# Demo Guide

## A. Streamlit Startup

From the repository root:

```powershell
python -m pip install -e ".[dev,vis]"
streamlit run apps/streamlit_app.py
```

## B. Benchmark Viewer

Mode: `Benchmark curated demo`

Inputs:

- `reports/demo/artifacts/*.json`
- `reports/demo/png/*.png`
- `reports/demo/html/*.html`
- selected solution JSON under `reports/demo/solutions/`

This viewer shows Solomon and Gehring-Homberger benchmark x-y coordinates. It
does not use map tiles and should not be described as a real city map.

## C. City Road Demo

Mode: `City road demo`

Inputs:

- `reports/demo/city/city_summary.csv`
- `reports/demo/city/city_instance_berlin_mitte_30.json`
- `reports/demo/city/city_solution_*_seed0.json`
- `reports/demo/city/city_routes_*_seed0.geojson`
- `reports/demo/city/city_map_*_seed0.html`

This demo shows Berlin Mitte routes on Folium using OSM road geometry. Travel
time is a shortest-path proxy from edge lengths and speed assumptions.

## D. CLI Example

Generate or refresh a benchmark route artifact:

```powershell
vrptw plot --benchmark `
  --run-csv reports/results/runs_medium.csv `
  --instance c101_100 `
  --solver alns_roulette `
  --seed 0 `
  --output-png reports/demo/png/c101_100_alns_roulette_seed0.png `
  --output-artifact reports/demo/artifacts/c101_100_alns_roulette_seed0.json
```

Generate the curated city demo from existing cache:

```powershell
python scripts/generate_city_demo.py --config configs/city_demo_berlin_mitte.yaml
```

The city script reuses `cache/osm` and `cache/distance_matrices` when present.
Those cache files are intentionally ignored by git.

## E. FAQ

Why is `cache/` ignored?

It contains local OSM GraphML and matrix caches. They are useful locally but not
small, stable source artifacts.

Why is `data/results/` ignored?

It contains raw experiment output, solution JSON, and convergence traces. The
commit-friendly subset is copied to `reports/`.

Why are some OR-Tools benchmark rows no-solution?

EXP-02 used a fixed 60-second budget. OR-Tools Routing is strong when it returns
a solution, but it did not solve every selected medium instance within that
budget.

Why not claim MOSADE improved the solver?

ABL-01 and EXP-02 do not support that claim. The selector is implemented and
instrumented, but current results do not show stable improvement.

Why is the city demo not a measured travel-time demo?

It uses OSM road geometry and a shortest-path proxy. It does not use observed
traffic measurements or dispatch telemetry.
