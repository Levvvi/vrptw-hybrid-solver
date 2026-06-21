import numpy as np
import pytest

from vrptw_hybrid.core.metrics import compute_solution_metrics, gap_percent
from vrptw_hybrid.core.models import (
    Customer,
    Route,
    RouteStop,
    Solution,
    VehicleSpec,
    VRPTWInstance,
)


def make_solution_and_instance() -> tuple[Solution, VRPTWInstance]:
    depot = Customer(id=0, x=0.0, y=0.0, demand=0, ready_time=0.0, due_time=100.0, service_time=0.0)
    customers = (
        Customer(id=1, x=3.0, y=4.0, demand=2, ready_time=0.0, due_time=50.0, service_time=1.0),
        Customer(id=2, x=6.0, y=8.0, demand=3, ready_time=0.0, due_time=60.0, service_time=1.0),
    )
    matrix = np.array(
        [
            [0.0, 5.0, 10.0],
            [5.0, 0.0, 5.0],
            [10.0, 5.0, 0.0],
        ]
    )
    instance = VRPTWInstance(
        name="metrics-mini",
        depot=depot,
        customers=customers,
        vehicle=VehicleSpec(capacity=10, count=2),
        distance_matrix=matrix,
        time_matrix=matrix,
        metadata={},
    )
    route = Route(
        vehicle_id=0,
        stops=(
            RouteStop(1, 5.0, 5.0, 6.0, 2),
            RouteStop(2, 11.0, 11.0, 12.0, 5),
        ),
        distance=999.0,
        duration=22.0,
        load=5,
    )
    solution = Solution(
        instance_name="metrics-mini",
        solver_name="unit",
        routes=(route,),
        objective=0.0,
        vehicles_used=1,
        total_distance=999.0,
        total_duration=22.0,
        feasible=True,
        runtime_sec=0.5,
        metadata={},
    )
    return solution, instance


def test_compute_solution_metrics_uses_instance_distance_matrix() -> None:
    solution, instance = make_solution_and_instance()

    metrics = compute_solution_metrics(solution, instance, vehicle_weight=100000.0)

    assert metrics["vehicles_used"] == 1
    assert metrics["total_distance"] == pytest.approx(20.0)
    assert metrics["total_duration"] == pytest.approx(22.0)
    assert metrics["composite_objective"] == pytest.approx(100020.0)
    assert metrics["feasible"] is True
    assert metrics["runtime_sec"] == pytest.approx(0.5)


def test_gap_percent_handles_reference_values() -> None:
    assert gap_percent(110.0, 100.0) == pytest.approx(10.0)
    assert gap_percent(90.0, 100.0) == pytest.approx(-10.0)
    assert gap_percent(10.0, None) is None
    assert gap_percent(10.0, 0.0) is None
