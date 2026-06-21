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
