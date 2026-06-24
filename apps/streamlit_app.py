"""Streamlit demo for the VRPTW hybrid solver."""

# ruff: noqa: E402

from __future__ import annotations

import csv
import json
import sys
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from vrptw_hybrid.core.models import Solution, VRPTWInstance
from vrptw_hybrid.core.solution_io import (
    load_solution_json,
    solution_to_dict,
    solution_to_metrics_row,
)
from vrptw_hybrid.data.solomon import parse_solomon
from vrptw_hybrid.solvers.dispatch import run_solver_from_config
from vrptw_hybrid.utils.config import load_config
from vrptw_hybrid.visualization.benchmark_plot import plot_benchmark_routes_matplotlib
from vrptw_hybrid.visualization.folium_map import FoliumMapError, render_solution_map
from vrptw_hybrid.visualization.route_artifacts import (
    artifact_route_table_rows,
    build_benchmark_route_artifact,
    load_route_artifact,
)


@dataclass(frozen=True, slots=True)
class DemoInstance:
    label: str
    path: Path
    limit_customers: int | None = None


DEFAULT_CONFIG_PATH = REPO_ROOT / "configs" / "solomon_small.yaml"
CURATED_ARTIFACT_DIR = REPO_ROOT / "reports" / "demo" / "artifacts"
CURATED_PNG_DIR = REPO_ROOT / "reports" / "demo" / "png"
LOCAL_RUNS_CSV = REPO_ROOT / "reports" / "results" / "runs_medium.csv"
CACHE_PLOT_DIR = REPO_ROOT / "cache" / "streamlit_benchmark_plots"
CITY_DEMO_DIR = REPO_ROOT / "reports" / "demo" / "city"
CITY_SUMMARY_CSV = CITY_DEMO_DIR / "city_summary.csv"
CITY_INSTANCE_JSON = CITY_DEMO_DIR / "city_instance_berlin_mitte_30.json"
DEMO_INSTANCES = {
    "mini_solomon_8": DemoInstance(
        label="Mini Solomon 8",
        path=REPO_ROOT / "tests" / "fixtures" / "mini_solomon.txt",
        limit_customers=8,
    ),
    "mini_solomon_10": DemoInstance(
        label="Mini Solomon 10",
        path=REPO_ROOT / "tests" / "fixtures" / "mini_solomon.txt",
        limit_customers=10,
    ),
}
SOLVER_OPTIONS = ("greedy", "ortools_routing", "alns_uniform", "alns_mosade")


def load_demo_instance(instance_key: str) -> VRPTWInstance:
    """Load one configured demo instance."""

    spec = DEMO_INSTANCES[instance_key]
    return parse_solomon(spec.path, limit_customers=spec.limit_customers)


def run_demo_solver(
    instance: VRPTWInstance,
    *,
    solver_name: str,
    seed: int,
    time_limit: float,
    max_iterations: int,
    config_path: str | Path = DEFAULT_CONFIG_PATH,
) -> Solution:
    """Run a supported demo solver through the shared dispatch layer."""

    config = load_config(config_path)
    return run_solver_from_config(
        solver_name=solver_name,
        instance=instance,
        config=config,
        seed=seed,
        time_limit=time_limit,
        max_iterations=max_iterations,
    )


def load_precomputed_solution(path: str | Path) -> Solution:
    """Load a precomputed solution JSON for a fast demo path."""

    return load_solution_json(path)


def route_table_rows(solution: Solution) -> list[dict[str, Any]]:
    """Return one table row per route stop."""

    rows: list[dict[str, Any]] = []
    for route in solution.routes:
        for position, stop in enumerate(route.stops, start=1):
            rows.append(
                {
                    "vehicle_id": route.vehicle_id,
                    "stop": position,
                    "customer_id": stop.customer_id,
                    "arrival_time": stop.arrival_time,
                    "start_service_time": stop.start_service_time,
                    "departure_time": stop.departure_time,
                    "load_after": stop.load_after,
                    "route_distance": route.distance,
                    "route_duration": route.duration,
                    "route_load": route.load,
                }
            )
    return rows


def convergence_rows(solution: Solution) -> list[dict[str, float | int]]:
    """Return ALNS convergence rows from solution metadata."""

    history = solution.metadata.get("history", [])
    if not isinstance(history, list):
        return []

    rows: list[dict[str, float | int]] = []
    for entry in history:
        if not isinstance(entry, dict):
            continue
        iteration = entry.get("iteration")
        if not isinstance(iteration, int):
            continue
        rows.append(
            {
                "iteration": iteration,
                "best_cost": _finite_float(entry.get("best_cost")),
                "current_cost": _finite_float(entry.get("current_cost")),
                "candidate_cost": _finite_float(entry.get("candidate_cost")),
            }
        )
    return rows


def operator_probability_rows(solution: Solution) -> list[dict[str, Any]]:
    """Return selector probability rows for display in the demo."""

    selector = _selector_snapshot(solution)
    rows: list[dict[str, Any]] = []
    rows.extend(
        _probability_rows(
            selector.get("destroy_probabilities", {}),
            probability_type="destroy",
        )
    )
    rows.extend(
        _probability_rows(
            selector.get("repair_probabilities", {}),
            probability_type="repair",
        )
    )
    rows.extend(
        _probability_rows(
            selector.get("pair_probabilities", {}),
            probability_type="destroy|repair",
        )
    )
    return rows


def solution_download_json(solution: Solution) -> str:
    """Return a JSON string suitable for Streamlit download_button."""

    return json.dumps(solution_to_dict(solution), indent=2, sort_keys=True) + "\n"


def metrics_csv(solution: Solution) -> str:
    """Return a one-row metrics CSV for Streamlit download_button."""

    row = solution_to_metrics_row(solution)
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=list(row))
    writer.writeheader()
    writer.writerow(row)
    return output.getvalue()


def load_curated_route_artifacts(
    artifact_dir: str | Path = CURATED_ARTIFACT_DIR,
) -> list[dict[str, Any]]:
    """Load curated benchmark route artifacts for public demo mode."""

    directory = Path(artifact_dir)
    if not directory.exists():
        return []
    artifacts = [load_route_artifact(path) for path in sorted(directory.glob("*.json"))]
    return sorted(artifacts, key=artifact_label)


def load_medium_run_rows(runs_csv: str | Path = LOCAL_RUNS_CSV) -> list[dict[str, Any]]:
    """Load EXP-02 run rows for full local experiment mode."""

    path = Path(runs_csv)
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as file:
        return [dict(row) for row in csv.DictReader(file)]


def load_city_summary_rows(summary_csv: str | Path = CITY_SUMMARY_CSV) -> list[dict[str, Any]]:
    """Load curated city road-demo summary rows."""

    path = Path(summary_csv)
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as file:
        return [dict(row) for row in csv.DictReader(file)]


def load_city_instance_artifact(path: str | Path = CITY_INSTANCE_JSON) -> dict[str, Any]:
    """Load the curated city instance artifact."""

    input_path = Path(path)
    if not input_path.exists():
        return {}
    return json.loads(input_path.read_text(encoding="utf-8"))


def filter_display_rows(
    rows: list[dict[str, Any]],
    *,
    feasible_only: bool,
    include_no_solution: bool,
) -> list[dict[str, Any]]:
    """Filter run rows for sidebar selection."""

    filtered: list[dict[str, Any]] = []
    for row in rows:
        has_solution = _truthy(row.get("has_solution"))
        feasible = _truthy(row.get("feasible"))
        no_solution = str(row.get("status", "")) == "NO_SOLUTION"
        if no_solution and include_no_solution:
            filtered.append(row)
            continue
        if feasible_only and not (feasible and has_solution):
            continue
        if not include_no_solution and no_solution:
            continue
        filtered.append(row)
    return filtered


def filter_display_artifacts(
    artifacts: list[dict[str, Any]],
    *,
    feasible_only: bool,
    include_no_solution: bool,
) -> list[dict[str, Any]]:
    """Filter artifacts for sidebar selection."""

    filtered: list[dict[str, Any]] = []
    for artifact in artifacts:
        no_solution = str(artifact.get("status", "")) == "NO_SOLUTION"
        has_solution = _truthy(artifact.get("has_solution"))
        feasible = _truthy(artifact.get("feasible"))
        if no_solution and include_no_solution:
            filtered.append(artifact)
            continue
        if feasible_only and not (feasible and has_solution):
            continue
        if not include_no_solution and no_solution:
            continue
        filtered.append(artifact)
    return filtered


def build_artifact_from_run_row(row: dict[str, Any]) -> dict[str, Any]:
    """Build an artifact from one local experiment run row."""

    source_file = _repo_path(row["source_file"])
    solution_json = _repo_path(row["solution_json"])
    return build_benchmark_route_artifact(source_file, solution_json, row)


def artifact_label(artifact: dict[str, Any]) -> str:
    """Return a concise label for a route artifact."""

    return (
        f"{artifact.get('instance')} / {artifact.get('solver')} / seed "
        f"{artifact.get('seed')} / {artifact.get('status')}"
    )


def run_row_label(row: dict[str, Any]) -> str:
    """Return a concise label for an EXP-02 row."""

    return (
        f"{row.get('instance')} / {row.get('solver')} / seed "
        f"{row.get('seed')} / {row.get('status')}"
    )


def city_run_label(row: dict[str, Any]) -> str:
    """Return a concise label for a city demo solver row."""

    return (
        f"{row.get('solver')} / seed {row.get('seed')} / "
        f"{row.get('status')} / feasible={row.get('feasible')}"
    )


def route_table_rows_from_artifact(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    """Return route table rows for Streamlit display."""

    return artifact_route_table_rows(artifact)


def city_route_table_rows(
    solution: Solution,
    city_artifact: dict[str, Any],
) -> list[dict[str, Any]]:
    """Return city route rows with lat/lon and customer time-window fields."""

    customers = {
        int(customer["id"]): customer
        for customer in city_artifact.get("customers", [])
        if isinstance(customer, dict) and "id" in customer
    }
    rows: list[dict[str, Any]] = []
    for route in solution.routes:
        for sequence_order, stop in enumerate(route.stops, start=1):
            customer = customers.get(stop.customer_id, {})
            rows.append(
                {
                    "vehicle_id": route.vehicle_id,
                    "sequence_order": sequence_order,
                    "customer_id": stop.customer_id,
                    "lat": customer.get("lat"),
                    "lon": customer.get("lon"),
                    "demand": customer.get("demand"),
                    "ready_time": customer.get("ready_time"),
                    "due_time": customer.get("due_time"),
                    "arrival_time": stop.arrival_time,
                    "start_service_time": stop.start_service_time,
                    "load_after": stop.load_after,
                }
            )
    return rows


def solver_comparison_rows(
    instance_name: str,
    runs_csv: str | Path = LOCAL_RUNS_CSV,
) -> list[dict[str, Any]]:
    """Return per-solver rows for the selected instance from the medium runs CSV."""

    rows = [
        row
        for row in load_medium_run_rows(runs_csv)
        if str(row.get("instance", "")) == str(instance_name)
    ]
    rows.sort(key=lambda row: (str(row.get("solver", "")), str(row.get("seed", ""))))
    return [
        {
            "solver": row.get("solver"),
            "seed": row.get("seed"),
            "status": row.get("status"),
            "feasible": row.get("feasible"),
            "has_solution": row.get("has_solution"),
            "vehicles": row.get("vehicles"),
            "distance": row.get("distance"),
            "objective": row.get("objective"),
            "runtime_sec": row.get("runtime_sec"),
        }
        for row in rows
    ]


def main() -> None:
    """Run the Streamlit app."""

    st = _import_streamlit()
    pd = _import_pandas()

    st.set_page_config(page_title="VRPTW Hybrid Demo", layout="wide")
    st.title("VRPTW Hybrid Demo")

    mode = st.sidebar.radio(
        "Mode",
        options=("Benchmark curated demo", "Benchmark full local experiment", "City road demo"),
        index=0,
    )
    if mode == "City road demo":
        _render_city_road_demo(st, pd)
        return

    st.warning(
        "Solomon/GH benchmark coordinates are synthetic x-y coordinates, "
        "not real latitude/longitude."
    )
    feasible_only = bool(st.sidebar.checkbox("Feasible only", value=True))
    include_no_solution = bool(st.sidebar.checkbox("Include NO_SOLUTION", value=False))

    artifact: dict[str, Any]
    if mode == "Benchmark curated demo":
        artifacts = filter_display_artifacts(
            load_curated_route_artifacts(),
            feasible_only=feasible_only,
            include_no_solution=include_no_solution,
        )
        if not artifacts:
            st.error("No curated benchmark route artifacts found in reports/demo/artifacts.")
            st.stop()
        selected_artifact = st.sidebar.selectbox(
            "Run",
            options=artifacts,
            format_func=artifact_label,
        )
        artifact = dict(selected_artifact)
    else:
        rows = filter_display_rows(
            load_medium_run_rows(),
            feasible_only=feasible_only,
            include_no_solution=include_no_solution,
        )
        if not rows:
            st.error("No matching local EXP-02 rows found in reports/results/runs_medium.csv.")
            st.stop()
        selected_row = st.sidebar.selectbox("Run", options=rows, format_func=run_row_label)
        try:
            artifact = build_artifact_from_run_row(dict(selected_row))
        except FileNotFoundError as exc:
            st.error(
                "The selected local run references files that are not present. "
                "Use curated demo mode or restore data/results and data/raw locally."
            )
            st.code(str(exc))
            st.stop()

    _render_artifact_metrics(st, artifact)
    _render_benchmark_plot(st, artifact)
    _render_artifact_tables(st, pd, artifact)
    _render_solver_comparison(st, pd, artifact)


def _render_city_road_demo(st: Any, pd: Any) -> None:
    st.info(
        "City road demo uses real latitude/longitude and OSM road-network shortest paths. "
        "Travel time is a proxy derived from edge lengths and speed assumptions, not "
        "real-time traffic."
    )
    rows = load_city_summary_rows()
    if not rows:
        st.error("No curated city demo summary found in reports/demo/city/city_summary.csv.")
        st.stop()
    selected = st.sidebar.selectbox("Solver", options=rows, format_func=city_run_label)
    row = dict(selected)
    _render_city_metrics(st, row)

    map_path = _repo_path(row.get("map_html", ""))
    st.subheader("Folium Road Map")
    if map_path.exists():
        st.components.v1.html(map_path.read_text(encoding="utf-8"), height=720, scrolling=True)
    else:
        st.warning(f"Map HTML not found: {map_path}")

    city_artifact = load_city_instance_artifact()
    st.subheader("City Instance")
    if city_artifact:
        st.caption(
            "Coordinates are real lat/lon sampled from the OSM road graph; "
            "distance is network shortest path in meters."
        )
        customer_rows = city_artifact.get("customers", [])
        st.dataframe(pd.DataFrame(customer_rows), hide_index=True, use_container_width=True)
    else:
        st.warning("City instance artifact is missing.")

    st.subheader("Route Table")
    solution_path = _repo_path(row.get("solution_json", ""))
    if not solution_path.exists():
        st.info("No solution JSON is available for this solver row.")
    else:
        solution = load_precomputed_solution(solution_path)
        route_rows = city_route_table_rows(solution, city_artifact)
        if route_rows:
            st.dataframe(pd.DataFrame(route_rows), hide_index=True, use_container_width=True)
        else:
            st.info("No route available for this run under the configured time budget.")

    st.subheader("City Solver Summary")
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)


def _render_city_metrics(st: Any, row: dict[str, Any]) -> None:
    columns = st.columns(6)
    columns[0].metric("Feasible", str(row.get("feasible")))
    columns[1].metric("Vehicles", _display_value(row.get("vehicles")))
    columns[2].metric("Distance m", _display_value(row.get("distance_m")))
    columns[3].metric("Runtime", f"{_display_value(row.get('runtime_sec'))}s")
    columns[4].metric("Status", str(row.get("status")))
    columns[5].metric("Pipeline", str(row.get("pipeline_status")))


def _render_metrics(st: Any, solution: Solution) -> None:
    columns = st.columns(5)
    columns[0].metric("Vehicles", solution.vehicles_used)
    columns[1].metric("Distance", f"{solution.total_distance:.2f}")
    columns[2].metric("Duration", f"{solution.total_duration:.2f}")
    columns[3].metric("Objective", f"{solution.objective:.2f}")
    columns[4].metric("Runtime", f"{solution.runtime_sec:.2f}s")


def _render_artifact_metrics(st: Any, artifact: dict[str, Any]) -> None:
    columns = st.columns(7)
    columns[0].metric("Feasible", str(artifact.get("feasible")))
    columns[1].metric("Has Solution", str(artifact.get("has_solution")))
    columns[2].metric("Status", str(artifact.get("status")))
    columns[3].metric("Vehicles", _display_value(artifact.get("vehicles")))
    columns[4].metric("Distance", _display_value(artifact.get("distance")))
    columns[5].metric("Objective", _display_value(artifact.get("objective")))
    columns[6].metric("Runtime", f"{_display_value(artifact.get('runtime_sec'))}s")


def _render_benchmark_plot(st: Any, artifact: dict[str, Any]) -> None:
    st.subheader("Benchmark Route Plot")
    if not _truthy(artifact.get("has_solution")):
        st.info(
            "No route available for this run. Solver status = "
            f"{artifact.get('status')} under the configured time budget."
        )
        return
    path = _artifact_png_path(artifact)
    if not path.exists():
        plot_benchmark_routes_matplotlib(artifact, path)
    st.image(str(path), use_container_width=True)


def _render_artifact_tables(st: Any, pd: Any, artifact: dict[str, Any]) -> None:
    st.subheader("Routes")
    rows = route_table_rows_from_artifact(artifact)
    if rows:
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
    else:
        st.info("No route stops to display for this run.")


def _render_solver_comparison(st: Any, pd: Any, artifact: dict[str, Any]) -> None:
    st.subheader("Same-instance Solver Rows")
    rows = solver_comparison_rows(str(artifact.get("instance", "")))
    if rows:
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
    else:
        st.info("No same-instance comparison rows available.")


def _render_map(st: Any, instance: VRPTWInstance, solution: Solution) -> None:
    st.subheader("Map")
    try:
        map_object = render_solution_map(instance, solution)
    except FoliumMapError as exc:
        st.warning(str(exc))
        return
    _display_folium_map(st, map_object)


def _display_folium_map(st: Any, map_object: Any) -> None:
    try:
        from streamlit_folium import st_folium
    except ImportError:
        html = map_object._repr_html_()
        st.components.v1.html(html, height=620, scrolling=True)
        return
    st_folium(map_object, height=620, use_container_width=True)


def _render_tables(st: Any, pd: Any, solution: Solution) -> None:
    route_rows = route_table_rows(solution)
    st.subheader("Routes")
    if route_rows:
        st.dataframe(pd.DataFrame(route_rows), hide_index=True, use_container_width=True)
    else:
        st.info("No route stops to display.")

    convergence = convergence_rows(solution)
    st.subheader("Convergence")
    if convergence:
        convergence_frame = pd.DataFrame(convergence).set_index("iteration")
        st.line_chart(convergence_frame[["best_cost", "current_cost"]])
    else:
        st.info("No convergence history for this solver.")

    probabilities = operator_probability_rows(solution)
    st.subheader("Operator Probabilities")
    if probabilities:
        st.dataframe(pd.DataFrame(probabilities), hide_index=True, use_container_width=True)
    else:
        st.info("No operator probability snapshot for this solver.")


def _render_downloads(st: Any, solution: Solution) -> None:
    left, right = st.columns(2)
    base_name = f"{solution.instance_name}_{solution.solver_name}".replace(" ", "_")
    left.download_button(
        "Solution JSON",
        data=solution_download_json(solution),
        file_name=f"{base_name}.json",
        mime="application/json",
    )
    right.download_button(
        "Metrics CSV",
        data=metrics_csv(solution),
        file_name=f"{base_name}_metrics.csv",
        mime="text/csv",
    )


def _selector_snapshot(solution: Solution) -> dict[str, Any]:
    selector = solution.metadata.get("selector")
    if isinstance(selector, dict):
        return selector

    history = solution.metadata.get("history", [])
    if isinstance(history, list):
        for entry in reversed(history):
            if isinstance(entry, dict) and isinstance(entry.get("selector_snapshot"), dict):
                return dict(entry["selector_snapshot"])
    return {}


def _probability_rows(
    probabilities: Any,
    *,
    probability_type: str,
) -> list[dict[str, Any]]:
    if not isinstance(probabilities, dict):
        return []
    return [
        {
            "type": probability_type,
            "operator": str(operator),
            "probability": float(probability),
        }
        for operator, probability in probabilities.items()
    ]


def _finite_float(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    if number == float("inf"):
        return 0.0
    return number


def _artifact_png_path(artifact: dict[str, Any]) -> Path:
    stem = (
        f"{artifact.get('instance')}_{artifact.get('solver')}_seed{artifact.get('seed')}"
    ).replace(" ", "_")
    curated_path = CURATED_PNG_DIR / f"{stem}.png"
    if curated_path.exists():
        return curated_path
    return CACHE_PLOT_DIR / f"{stem}.png"


def _repo_path(path_value: str | Path) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        return path
    return REPO_ROOT / path


def _display_value(value: Any) -> str:
    if value is None or value == "":
        return "NA"
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return str(value)


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _import_streamlit() -> Any:
    try:
        import streamlit as st
    except ImportError as exc:
        raise RuntimeError(
            "Streamlit is required for the demo app. Install with: "
            'pip install -e ".[vis]"'
        ) from exc
    return st


def _import_pandas() -> Any:
    try:
        import pandas as pd
    except ImportError as exc:
        raise RuntimeError("pandas is required for the demo app.") from exc
    return pd


if __name__ == "__main__":
    main()
