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
from vrptw_hybrid.visualization.folium_map import FoliumMapError, render_solution_map


@dataclass(frozen=True, slots=True)
class DemoInstance:
    label: str
    path: Path
    limit_customers: int | None = None


DEFAULT_CONFIG_PATH = REPO_ROOT / "configs" / "solomon_small.yaml"
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


def main() -> None:
    """Run the Streamlit app."""

    st = _import_streamlit()
    pd = _import_pandas()

    st.set_page_config(page_title="VRPTW Hybrid Demo", layout="wide")
    st.title("VRPTW Hybrid Demo")

    instance_key = st.sidebar.selectbox(
        "Instance",
        options=list(DEMO_INSTANCES),
        format_func=lambda key: DEMO_INSTANCES[key].label,
    )
    solver_name = st.sidebar.selectbox("Solver", options=SOLVER_OPTIONS, index=0)
    seed = int(st.sidebar.number_input("Seed", min_value=0, value=42, step=1))
    time_limit = float(st.sidebar.slider("Time limit (sec)", 1, 30, 3))
    max_iterations = int(st.sidebar.slider("Max iterations", 1, 500, 30))
    use_precomputed = bool(st.sidebar.checkbox("Use precomputed JSON", value=False))
    precomputed_path = st.sidebar.text_input("Precomputed solution JSON", value="")
    run_clicked = st.sidebar.button("Run solver", type="primary")

    instance = load_demo_instance(str(instance_key))
    state_key = "vrptw_demo_solution"
    should_run = run_clicked or state_key not in st.session_state

    if should_run:
        try:
            with st.spinner("Solving VRPTW instance..."):
                if use_precomputed and precomputed_path.strip():
                    solution = load_precomputed_solution(precomputed_path.strip())
                else:
                    solution = run_demo_solver(
                        instance,
                        solver_name=str(solver_name),
                        seed=seed,
                        time_limit=time_limit,
                        max_iterations=max_iterations,
                    )
        except Exception as exc:
            st.error(str(exc))
            st.stop()
        st.session_state[state_key] = solution
    else:
        solution = st.session_state[state_key]

    _render_metrics(st, solution)
    _render_map(st, instance, solution)
    _render_tables(st, pd, solution)
    _render_downloads(st, solution)


def _render_metrics(st: Any, solution: Solution) -> None:
    columns = st.columns(5)
    columns[0].metric("Vehicles", solution.vehicles_used)
    columns[1].metric("Distance", f"{solution.total_distance:.2f}")
    columns[2].metric("Duration", f"{solution.total_duration:.2f}")
    columns[3].metric("Objective", f"{solution.objective:.2f}")
    columns[4].metric("Runtime", f"{solution.runtime_sec:.2f}s")


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
