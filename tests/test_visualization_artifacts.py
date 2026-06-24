from pathlib import Path

from vrptw_hybrid.core.models import Solution
from vrptw_hybrid.core.solution_io import save_solution_json
from vrptw_hybrid.data.solomon import parse_solomon
from vrptw_hybrid.solvers.greedy import solve_greedy
from vrptw_hybrid.visualization.route_artifacts import (
    artifact_route_table_rows,
    build_benchmark_route_artifact,
    load_instance_coordinates,
    load_route_artifact,
    save_route_artifact,
)

FIXTURE = Path("tests/fixtures/mini_solomon.txt")


def test_feasible_solution_builds_benchmark_route_artifact(tmp_path: Path) -> None:
    instance = parse_solomon(FIXTURE, limit_customers=8)
    solution = solve_greedy(instance, seed=42)
    solution_path = tmp_path / "solution.json"
    save_solution_json(solution, solution_path)
    row = _run_row(solution_path, feasible=True, has_solution=True)

    artifact = build_benchmark_route_artifact(FIXTURE, solution_path, row)

    assert artifact["coordinate_system"] == "benchmark_xy"
    assert artifact["is_real_map"] is False
    assert artifact["benchmark_family"] == "Solomon"
    assert artifact["feasible"] is True
    assert artifact["has_solution"] is True
    assert artifact["routes"]
    visited = [
        customer_id
        for route in artifact["routes"]
        for customer_id in route["customer_sequence"]
    ]
    assert sorted(visited) == sorted(instance.customer_ids)
    first_route = artifact["routes"][0]
    assert first_route["points"][0]["kind"] == "depot"
    assert first_route["points"][-1]["kind"] == "depot"
    assert artifact_route_table_rows(artifact)


def test_no_solution_artifact_has_empty_routes_and_saves(tmp_path: Path) -> None:
    no_solution = Solution(
        instance_name="MINI_C101",
        solver_name="ortools_routing",
        routes=(),
        objective=0.0,
        vehicles_used=0,
        total_distance=0.0,
        total_duration=0.0,
        feasible=False,
        runtime_sec=1.0,
        metadata={"status": "NO_SOLUTION"},
    )
    solution_path = tmp_path / "no_solution.json"
    save_solution_json(no_solution, solution_path)
    row = _run_row(solution_path, feasible=False, has_solution=False, status="NO_SOLUTION")

    artifact = build_benchmark_route_artifact(FIXTURE, solution_path, row)
    saved_path = save_route_artifact(artifact, tmp_path / "artifact.json")
    loaded = load_route_artifact(saved_path)

    assert artifact["feasible"] is False
    assert artifact["has_solution"] is False
    assert artifact["routes"] == []
    assert loaded["status"] == "NO_SOLUTION"
    assert artifact_route_table_rows(artifact) == []


def test_load_instance_coordinates_returns_depot_and_customers() -> None:
    coordinates = load_instance_coordinates(FIXTURE)

    assert coordinates[0]["kind"] == "depot"
    assert coordinates[1]["kind"] == "customer"
    assert {"x", "y", "demand", "ready_time", "due_time"}.issubset(coordinates[1])


def _run_row(
    solution_path: Path,
    *,
    feasible: bool,
    has_solution: bool,
    status: str = "FEASIBLE",
) -> dict[str, object]:
    return {
        "instance": "mini_solomon",
        "solver": "greedy",
        "seed": 42,
        "status": status,
        "pipeline_status": "ok",
        "feasible": feasible,
        "has_solution": has_solution,
        "vehicles": 1,
        "distance": 10.0,
        "objective": 100010.0,
        "runtime_sec": 0.01,
        "solution_json": str(solution_path),
        "source_file": str(FIXTURE),
    }
