from pathlib import Path

import numpy as np
import pytest

from vrptw_hybrid.core.checker import check_solution
from vrptw_hybrid.core.models import Customer, VehicleSpec, VRPTWInstance
from vrptw_hybrid.data.solomon import parse_solomon
from vrptw_hybrid.solvers.exact_cp_sat import (
    CPSATRuntimeError,
    CPSATVRPTWSolver,
    is_cp_sat_runtime_available,
    solve_cp_sat,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "mini_solomon.txt"


def test_cp_sat_solves_mini_solomon_8_customers() -> None:
    if not is_cp_sat_runtime_available():
        pytest.skip("Installed OR-Tools CP-SAT runtime fails smoke test")
    instance = parse_solomon(FIXTURE, limit_customers=8)

    solution = solve_cp_sat(instance, time_limit_sec=10, scale_factor=10)
    report = check_solution(solution, instance)

    assert solution.feasible
    assert report.feasible
    assert solution.vehicles_used <= instance.vehicle.count
    assert sorted(
        stop.customer_id for route in solution.routes for stop in route.stops
    ) == list(instance.customer_ids)
    assert solution.metadata["status"] in {"OPTIMAL", "FEASIBLE"}
    assert solution.metadata["feasibility_violations"] == []


def test_cp_sat_returns_infeasible_solution_when_capacity_is_impossible() -> None:
    if not is_cp_sat_runtime_available():
        pytest.skip("Installed OR-Tools CP-SAT runtime fails smoke test")
    depot = Customer(id=0, x=0.0, y=0.0, demand=0, ready_time=0.0, due_time=100.0, service_time=0.0)
    customers = (
        Customer(id=1, x=1.0, y=0.0, demand=5, ready_time=0.0, due_time=100.0, service_time=0.0),
    )
    matrix = np.array([[0.0, 1.0], [1.0, 0.0]])
    instance = VRPTWInstance(
        name="cp-sat-infeasible",
        depot=depot,
        customers=customers,
        vehicle=VehicleSpec(capacity=4, count=1),
        distance_matrix=matrix,
        time_matrix=matrix,
        metadata={},
    )

    solution = solve_cp_sat(instance, time_limit_sec=2, scale_factor=10)

    assert not solution.feasible
    assert solution.routes == ()
    assert solution.metadata["status"] == "INFEASIBLE"


def test_cp_sat_rejects_invalid_parameters() -> None:
    with pytest.raises(ValueError, match="time_limit_sec must be positive"):
        CPSATVRPTWSolver(time_limit_sec=0)


def test_cp_sat_runtime_failure_is_controlled() -> None:
    if is_cp_sat_runtime_available():
        pytest.skip("Runtime is available; controlled failure path is not active")
    instance = parse_solomon(FIXTURE, limit_customers=2)

    with pytest.raises(CPSATRuntimeError, match="failed a subprocess smoke test"):
        solve_cp_sat(instance, time_limit_sec=2, scale_factor=10)
