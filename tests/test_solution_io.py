import csv
import json
from pathlib import Path

from vrptw_hybrid.core.models import Route, RouteStop, Solution
from vrptw_hybrid.core.solution_io import (
    load_solution_json,
    save_convergence_csv,
    save_metrics_csv,
    save_solution_json,
    solution_from_dict,
    solution_to_dict,
    solution_to_metrics_row,
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


def test_solution_to_metrics_row_includes_ablation_for_csv(tmp_path: Path) -> None:
    solution = make_solution()
    solution = Solution(
        instance_name=solution.instance_name,
        solver_name="alns",
        routes=solution.routes,
        objective=solution.objective,
        vehicles_used=solution.vehicles_used,
        total_distance=solution.total_distance,
        total_duration=solution.total_duration,
        feasible=solution.feasible,
        runtime_sec=solution.runtime_sec,
        metadata={
            **solution.metadata,
            "ablation": "alns_mosade_no_shaw_destroy",
            "iterations": 7,
            "best_iteration": 3,
        },
    )
    output_path = tmp_path / "metrics.csv"

    row = solution_to_metrics_row(solution)
    save_metrics_csv([row], output_path)

    with output_path.open("r", encoding="utf-8", newline="") as file:
        loaded_row = next(csv.DictReader(file))

    assert row["ablation"] == "alns_mosade_no_shaw_destroy"
    assert loaded_row["ablation"] == "alns_mosade_no_shaw_destroy"
    assert loaded_row["iterations"] == "7"


def test_save_convergence_csv_writes_alns_history(tmp_path: Path) -> None:
    solution = make_solution()
    solution = Solution(
        instance_name=solution.instance_name,
        solver_name="alns_mosade",
        routes=solution.routes,
        objective=solution.objective,
        vehicles_used=solution.vehicles_used,
        total_distance=solution.total_distance,
        total_duration=solution.total_duration,
        feasible=solution.feasible,
        runtime_sec=solution.runtime_sec,
        metadata={
            **solution.metadata,
            "history": [
                {
                    "iteration": 1,
                    "current_cost": 100.0,
                    "candidate_cost": 95.0,
                    "best_cost": 95.0,
                    "delta_cost": -5.0,
                    "reward": 3.0,
                    "accepted": True,
                    "new_best": True,
                    "destroy": "random_removal",
                    "destroy_operator": "random_removal",
                    "repair": "greedy_insertion",
                    "repair_operator": "greedy_insertion",
                    "selector_snapshot": {
                        "name": "mosade_inspired",
                        "pair_probabilities": {"random_removal|greedy_insertion": 0.7},
                        "pair_credit": {"random_removal|greedy_insertion": 2.5},
                    },
                }
            ],
        },
    )
    output_path = tmp_path / "convergence.csv"

    save_convergence_csv(solution, output_path)

    with output_path.open("r", encoding="utf-8", newline="") as file:
        row = next(csv.DictReader(file))

    assert row["solver"] == "alns_mosade"
    assert row["iteration"] == "1"
    assert row["best_objective"] == "95.0"
    assert row["reward"] == "3.0"
    assert row["destroy_operator"] == "random_removal"
    assert row["repair_operator"] == "greedy_insertion"
    assert row["selector"] == "mosade_inspired"
    assert row["selected_pair_probability"] == "0.7"
    assert row["selected_pair_credit"] == "2.5"
    assert "mosade_inspired" in row["selector_snapshot"]
