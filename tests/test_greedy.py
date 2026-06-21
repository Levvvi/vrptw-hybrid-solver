from pathlib import Path

import numpy as np
import pytest

from vrptw_hybrid.core.checker import check_solution
from vrptw_hybrid.core.models import Customer, Solution, VehicleSpec, VRPTWInstance
from vrptw_hybrid.data.solomon import parse_solomon
from vrptw_hybrid.solvers.greedy import GreedyConstructionError, GreedySolver, solve_greedy

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "mini_solomon.txt"


def route_signature(solution: Solution) -> tuple[tuple[int, ...], ...]:
    return tuple(tuple(stop.customer_id for stop in route.stops) for route in solution.routes)


def test_greedy_solves_mini_solomon_with_checker() -> None:
    instance = parse_solomon(FIXTURE)

    solution = solve_greedy(instance, seed=42)
    report = check_solution(solution, instance)

    assert solution.feasible
    assert report.feasible
    assert solution.vehicles_used <= instance.vehicle.count
    assert sorted(
        stop.customer_id for route in solution.routes for stop in route.stops
    ) == list(instance.customer_ids)
    assert solution.metadata["strategy"] == "minimum_delta_insertion"
    assert solution.metadata["feasibility_violations"] == []


def test_greedy_deterministic_mode_is_repeatable() -> None:
    instance = parse_solomon(FIXTURE, limit_customers=8)
    solver = GreedySolver(seed=123, deterministic=True)

    first = solver.solve(instance)
    second = solver.solve(instance)

    assert route_signature(first) == route_signature(second)
    assert first.objective == pytest.approx(second.objective)


def test_greedy_raises_controlled_error_when_vehicle_capacity_is_impossible() -> None:
    depot = Customer(id=0, x=0.0, y=0.0, demand=0, ready_time=0.0, due_time=100.0, service_time=0.0)
    customers = (
        Customer(id=1, x=1.0, y=0.0, demand=5, ready_time=0.0, due_time=100.0, service_time=0.0),
    )
    matrix = np.array([[0.0, 1.0], [1.0, 0.0]])
    instance = VRPTWInstance(
        name="capacity-impossible",
        depot=depot,
        customers=customers,
        vehicle=VehicleSpec(capacity=4, count=1),
        distance_matrix=matrix,
        time_matrix=matrix,
        metadata={},
    )

    with pytest.raises(GreedyConstructionError, match="could not insert remaining customers"):
        solve_greedy(instance)


def test_greedy_handles_empty_instance() -> None:
    depot = Customer(id=0, x=0.0, y=0.0, demand=0, ready_time=0.0, due_time=100.0, service_time=0.0)
    matrix = np.array([[0.0]])
    instance = VRPTWInstance(
        name="empty",
        depot=depot,
        customers=(),
        vehicle=VehicleSpec(capacity=4, count=1),
        distance_matrix=matrix,
        time_matrix=matrix,
        metadata={},
    )

    solution = solve_greedy(instance)

    assert solution.feasible
    assert solution.routes == ()
    assert solution.objective == pytest.approx(0.0)
