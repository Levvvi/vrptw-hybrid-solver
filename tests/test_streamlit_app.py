from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

from vrptw_hybrid.core.solution_io import save_solution_json


def load_streamlit_app_module() -> Any:
    app_path = Path(__file__).resolve().parents[1] / "apps" / "streamlit_app.py"
    spec = importlib.util.spec_from_file_location("streamlit_app_under_test", app_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import Streamlit app from {app_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


streamlit_app = load_streamlit_app_module()


def test_load_demo_instance_uses_mini_fixture() -> None:
    instance = streamlit_app.load_demo_instance("mini_solomon_8")

    assert instance.name == "MINI_C101"
    assert instance.node_count == 9


def test_run_demo_solver_runs_greedy_small() -> None:
    instance = streamlit_app.load_demo_instance("mini_solomon_8")

    solution = streamlit_app.run_demo_solver(
        instance,
        solver_name="greedy",
        seed=42,
        time_limit=1.0,
        max_iterations=2,
    )

    assert solution.feasible
    assert solution.vehicles_used > 0
    assert streamlit_app.route_table_rows(solution)


def test_run_demo_solver_runs_alns_small_and_exports_curves() -> None:
    instance = streamlit_app.load_demo_instance("mini_solomon_8")

    solution = streamlit_app.run_demo_solver(
        instance,
        solver_name="alns_uniform",
        seed=42,
        time_limit=1.0,
        max_iterations=2,
    )

    assert solution.feasible
    assert streamlit_app.convergence_rows(solution)
    assert streamlit_app.operator_probability_rows(solution)


def test_precomputed_solution_json_round_trips(tmp_path: Path) -> None:
    instance = streamlit_app.load_demo_instance("mini_solomon_8")
    solution = streamlit_app.run_demo_solver(
        instance,
        solver_name="greedy",
        seed=7,
        time_limit=1.0,
        max_iterations=1,
    )
    path = tmp_path / "solution.json"
    save_solution_json(solution, path)

    loaded = streamlit_app.load_precomputed_solution(path)
    download_json = streamlit_app.solution_download_json(loaded)
    metrics = streamlit_app.metrics_csv(loaded)

    assert loaded.instance_name == solution.instance_name
    assert json.loads(download_json)["solver_name"] == solution.solver_name
    assert "vehicles_used" in metrics


def test_curated_route_artifacts_load_if_present() -> None:
    artifacts = streamlit_app.load_curated_route_artifacts()

    assert artifacts
    assert all(artifact["coordinate_system"] == "benchmark_xy" for artifact in artifacts)
    assert all(artifact["is_real_map"] is False for artifact in artifacts)


def test_artifact_route_table_rows_ignore_no_solution() -> None:
    no_solution = {
        "instance": "r101_100",
        "solver": "ortools_routing",
        "seed": 0,
        "status": "NO_SOLUTION",
        "feasible": False,
        "has_solution": False,
        "routes": [],
    }

    assert streamlit_app.route_table_rows_from_artifact(no_solution) == []


def test_medium_run_rows_can_filter_no_solution() -> None:
    rows = [
        {"feasible": "True", "has_solution": "True", "status": "FEASIBLE"},
        {"feasible": "False", "has_solution": "False", "status": "NO_SOLUTION"},
    ]

    feasible = streamlit_app.filter_display_rows(
        rows,
        feasible_only=True,
        include_no_solution=False,
    )
    with_no_solution = streamlit_app.filter_display_rows(
        rows,
        feasible_only=True,
        include_no_solution=True,
    )

    assert len(feasible) == 1
    assert len(with_no_solution) == 2


def test_city_summary_and_route_rows_load_from_curated_artifacts(tmp_path: Path) -> None:
    summary = tmp_path / "city_summary.csv"
    summary.write_text(
        "solver,seed,status,feasible,solution_json,map_html\n"
        "greedy,0,FEASIBLE,True,solution.json,map.html\n",
        encoding="utf-8",
    )
    city_instance = {
        "customers": [
            {
                "id": 1,
                "lat": 52.51,
                "lon": 13.37,
                "demand": 2,
                "ready_time": 0,
                "due_time": 100,
            }
        ]
    }
    solution = streamlit_app.run_demo_solver(
        streamlit_app.load_demo_instance("mini_solomon_8"),
        solver_name="greedy",
        seed=7,
        time_limit=1.0,
        max_iterations=1,
    )

    rows = streamlit_app.load_city_summary_rows(summary)
    route_rows = streamlit_app.city_route_table_rows(solution, city_instance)

    assert rows[0]["solver"] == "greedy"
    assert route_rows
    assert {"vehicle_id", "sequence_order", "customer_id"}.issubset(route_rows[0])
