# P2_VIS_01B_REPORT.md

Date: 2026-06-23

## A. Goal

VIS-01B implements a small real city road-network demo:

OSMnx/NetworkX road graph -> synthetic city orders -> network shortest-path
distance/time matrices -> VRPTW solve -> GeoJSON -> Folium HTML -> Streamlit
display.

This is a curated visualization demo, not a large-scale benchmark.

## B. City And Area

| Field | Value |
| --- | --- |
| City id | `berlin_mitte_30` |
| Place label | `Mitte, Berlin, Germany` |
| Network type | `drive` |
| Bounding box | north `52.5320`, south `52.5100`, east `13.4200`, west `13.3700` |
| Orders | 30 synthetic orders sampled from OSM graph nodes |
| Seed | 42 |
| Vehicles | 6 available |
| Vehicle capacity | 35 |
| Service time | 5 minutes |

The bbox keeps the demo small and repeatable while still using real
latitude/longitude coordinates and OSM road geometry.

## C. OSM Data Source

The road graph is reused from the existing local OSM cache:

- GraphML cache: `cache/osm/berlin_mitte_drive.graphml`
- Cache policy: ignored by git; reused for this VIS-01B run, with no OSM
  re-download
- Distance matrix cache: `cache/distance_matrices/berlin_mitte_30_seed42.npz`
- Network processing: largest strongly connected component is used for route
  reachability.

The cache directories are intentionally not committed.

## D. City Instance Generation

Config:

- `configs/city_demo_berlin_mitte.yaml`

Curated city instance:

- `reports/demo/city/city_instance_berlin_mitte_30.json`

The instance artifact records:

- `coordinate_system = lat_lon`
- depot and customer lat/lon
- nearest OSM graph node for every stop
- vehicle count and capacity
- network shortest-path distance matrix in meters
- proxy travel-time matrix in minutes

The generated customer time windows are wide hard windows for demo robustness.
They are still checked by the standard VRPTW checker.

## E. Distance Matrix

Distance is computed as shortest-path road distance on the OSM graph.

Travel time is a proxy:

- OSM edge lengths are combined with simple speed assumptions by road type.
- The solver time matrix is converted to minutes.
- This is not measured travel-time data and should not be described as observed travel
  time.

## F. Solvers

The city demo runs:

- `greedy`
- `ortools_routing`
- `alns_roulette`
- `alns_mosade`

CP-SAT is not used for this city demo.

## G. Summary Results

Source:

- `reports/demo/city/city_summary.csv`

| Solver | Feasible | Vehicles | Distance m | Runtime sec | Status |
| --- | --- | ---: | ---: | ---: | --- |
| `greedy` | true | 3 | 32309.954 | 0.197 | `FEASIBLE` |
| `ortools_routing` | true | 3 | 22701.994 | 60.010 | `SOLUTION_FOUND` |
| `alns_roulette` | true | 3 | 23956.684 | 6.214 | `FEASIBLE` |
| `alns_mosade` | true | 3 | 23956.684 | 6.256 | `FEASIBLE` |

In this single curated city demo, MOSADE-inspired selection does not demonstrate
a clear advantage over roulette selection. OR-Tools Routing produced the lowest
observed distance under the configured 60-second budget.

## H. Folium Demo Artifacts

Curated artifacts:

- `reports/demo/city/city_solution_greedy_seed0.json`
- `reports/demo/city/city_solution_ortools_routing_seed0.json`
- `reports/demo/city/city_solution_alns_roulette_seed0.json`
- `reports/demo/city/city_solution_alns_mosade_seed0.json`
- `reports/demo/city/city_routes_greedy_seed0.geojson`
- `reports/demo/city/city_routes_ortools_routing_seed0.geojson`
- `reports/demo/city/city_routes_alns_roulette_seed0.geojson`
- `reports/demo/city/city_routes_alns_mosade_seed0.geojson`
- `reports/demo/city/city_map_greedy_seed0.html`
- `reports/demo/city/city_map_ortools_routing_seed0.html`
- `reports/demo/city/city_map_alns_roulette_seed0.html`
- `reports/demo/city/city_map_alns_mosade_seed0.html`

The Folium maps use real lat/lon and OpenStreetMap tiles. This is separate from
VIS-01A benchmark x-y visualization.

## I. Streamlit Command

Start the app with:

```powershell
Set-Location <repo-root>
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process
.\.venv311\Scripts\Activate.ps1
streamlit run apps/streamlit_app.py
```

Use the `City road demo` mode to view the Berlin Mitte artifacts.

## J. Limitations

- This is a 30-order curated visualization demo.
- Travel time is a road-network shortest-path proxy, not measured travel-time data.
- The synthetic order set is generated from OSM graph nodes, not from real order
  history.
- This demo does not support a better-than-baseline claim for MOSADE-inspired selection.
- Results should not be extrapolated to production routing or large-scale city
  operations.
- OSM cache and distance-matrix cache are local ignored artifacts.

## K. Next Steps

Recommended priority:

1. `DOC-01`: package the project narrative and README/demo instructions.
2. `REL-01`: prepare a clean submission-ready repository snapshot.
3. `ABL-02`: diagnose why MOSADE-inspired selection is not outperforming
   roulette/uniform in the current experimental settings.
