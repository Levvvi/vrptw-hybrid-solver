import csv
import json
from pathlib import Path

from vrptw_hybrid.core.models import Route, RouteStop, Solution
from vrptw_hybrid.core.solution_io import (
    load_solution_json,
    save_metrics_csv,
    save_solution_json,
    solution_from_dict,
    solution_to_dict,
)


def make_solution() -> Solution:
    route = Route(
        vehicle_id=0,
        stops=(
            RouteStop(
                customer_id=1,
                arrival_time=5.0,
                start_service_time=5.0,
                departure_time=6.0,
                load_after=2,
            ),
        ),
        distance=10.0,
        duration=11.0,
        load=2,
    )
    return Solution(
        instance_name="mini",
        solver_name="unit",
        routes=(route,),
        objective=100010.0,
        vehicles_used=1,
        total_distance=10.0,
        total_duration=11.0,
        feasible=True,
        runtime_sec=0.01,
        metadata={"seed": 42, "git_commit": "abc123"},
    )


def test_solution_dict_round_trip() -> None:
    solution = make_solution()

    restored = solution_from_dict(solution_to_dict(solution))

    assert restored == solution
    assert restored.metadata["seed"] == 42


def test_solution_json_round_trip(tmp_path: Path) -> None:
    solution = make_solution()
    output_path = tmp_path / "solution.json"

    save_solution_json(solution, output_path)
    restored = load_solution_json(output_path)

    assert restored == solution
    text = output_path.read_text(encoding="utf-8")
    assert "\n" in text
    parsed = json.loads(text)
    assert parsed["instance_name"] == "mini"
    assert parsed["metadata"]["seed"] == 42


def test_save_metrics_csv_writes_header_and_rows(tmp_path: Path) -> None:
    output_path = tmp_path / "metrics.csv"
    rows = [
        {"instance": "mini", "solver": "greedy", "vehicles_used": 1, "total_distance": 10.0},
        {"instance": "mini", "solver": "alns", "vehicles_used": 1, "total_distance": 9.5},
    ]

    save_metrics_csv(rows, output_path)

    with output_path.open("r", encoding="utf-8", newline="") as file:
        loaded_rows = list(csv.DictReader(file))

    assert loaded_rows == [
        {"instance": "mini", "solver": "greedy", "vehicles_used": "1", "total_distance": "10.0"},
        {"instance": "mini", "solver": "alns", "vehicles_used": "1", "total_distance": "9.5"},
    ]
