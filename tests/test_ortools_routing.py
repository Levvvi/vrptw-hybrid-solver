from pathlib import Path

import numpy as np
import pytest

from vrptw_hybrid.core.checker import check_solution
from vrptw_hybrid.core.models import Customer, VehicleSpec, VRPTWInstance
from vrptw_hybrid.data.solomon import parse_solomon
from vrptw_hybrid.solvers.ortools_routing import ORToolsRoutingSolver, solve_ortools_routing

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "mini_solomon.txt"


def test_ortools_routing_solves_mini_instance() -> None:
    instance = parse_solomon(FIXTURE)

    solution = solve_ortools_routing(instance, time_limit_sec=3, scale_factor=10)
    report = check_solution(solution, instance)

    assert solution.feasible
    assert report.feasible
    assert solution.solver_name == "ortools_routing"
    assert solution.metadata["status"] == "SOLUTION_FOUND"
    assert solution.metadata["first_solution_strategy"] == "PATH_CHEAPEST_ARC"
    assert sorted(
        stop.customer_id for route in solution.routes for stop in route.stops
    ) == list(instance.customer_ids)


def test_ortools_routing_returns_no_solution_for_impossible_capacity() -> None:
    depot = Customer(id=0, x=0.0, y=0.0, demand=0, ready_time=0.0, due_time=100.0, service_time=0.0)
    customers = (
        Customer(id=1, x=1.0, y=0.0, demand=5, ready_time=0.0, due_time=100.0, service_time=0.0),
    )
    matrix = np.array([[0.0, 1.0], [1.0, 0.0]])
    instance = VRPTWInstance(
        name="routing-infeasible",
        depot=depot,
        customers=customers,
        vehicle=VehicleSpec(capacity=4, count=1),
        distance_matrix=matrix,
        time_matrix=matrix,
        metadata={},
    )

    solution = solve_ortools_routing(instance, time_limit_sec=1, scale_factor=10)

    assert not solution.feasible
    assert solution.routes == ()
    assert solution.metadata["status"] == "NO_SOLUTION"


def test_ortools_routing_rejects_unknown_strategy() -> None:
    instance = parse_solomon(FIXTURE, limit_customers=2)
    solver = ORToolsRoutingSolver(first_solution_strategy="NOT_A_STRATEGY", time_limit_sec=1)

    with pytest.raises(ValueError, match="Unknown OR-Tools enum value"):
        solver.solve(instance)
