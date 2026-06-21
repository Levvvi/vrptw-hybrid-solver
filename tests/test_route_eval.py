import numpy as np
import pytest

from vrptw_hybrid.core.models import Customer, VehicleSpec, VRPTWInstance
from vrptw_hybrid.solvers.alns.route_eval import (
    evaluate_route,
    insertion_delta_cost,
    is_feasible_insertion,
)


def make_instance(capacity: int = 10, tight_customer_2: bool = False) -> VRPTWInstance:
    depot = Customer(id=0, x=0.0, y=0.0, demand=0, ready_time=0.0, due_time=100.0, service_time=0.0)
    customer_2_due = 1.0 if tight_customer_2 else 100.0
    customers = (
        Customer(id=1, x=1.0, y=0.0, demand=2, ready_time=0.0, due_time=100.0, service_time=0.0),
        Customer(
            id=2,
            x=2.0,
            y=0.0,
            demand=3,
            ready_time=0.0,
            due_time=customer_2_due,
            service_time=0.0,
        ),
        Customer(id=3, x=3.0, y=0.0, demand=2, ready_time=0.0, due_time=100.0, service_time=0.0),
    )
    matrix = np.array(
        [
            [0.0, 1.0, 2.0, 3.0],
            [1.0, 0.0, 1.0, 2.0],
            [2.0, 1.0, 0.0, 1.0],
            [3.0, 2.0, 1.0, 0.0],
        ]
    )
    return VRPTWInstance(
        name="route-eval",
        depot=depot,
        customers=customers,
        vehicle=VehicleSpec(capacity=capacity, count=2),
        distance_matrix=matrix,
        time_matrix=matrix,
        metadata={},
    )


def test_evaluate_route_returns_schedule_and_distance() -> None:
    result = evaluate_route((1, 2), make_instance())

    assert result.feasible
    assert result.route is not None
    assert result.distance == pytest.approx(4.0)
    assert result.duration == pytest.approx(4.0)
    assert result.load == 5
    assert [stop.customer_id for stop in result.route.stops] == [1, 2]
    assert result.route.stops[1].arrival_time == pytest.approx(2.0)


def test_feasible_end_insertion() -> None:
    instance = make_instance()

    assert is_feasible_insertion((1,), 2, 1, instance)
    assert insertion_delta_cost((1,), 2, 1, instance) == pytest.approx(2.0)


def test_feasible_middle_insertion() -> None:
    instance = make_instance()

    assert is_feasible_insertion((1, 3), 2, 1, instance)
    assert insertion_delta_cost((1, 3), 2, 1, instance) == pytest.approx(0.0)


def test_capacity_infeasible_insertion_returns_none_delta() -> None:
    instance = make_instance(capacity=4)

    assert not is_feasible_insertion((1,), 2, 1, instance)
    assert insertion_delta_cost((1,), 2, 1, instance) is None


def test_time_window_infeasible_insertion_returns_violation() -> None:
    instance = make_instance(tight_customer_2=True)

    result = evaluate_route((1, 2), instance)

    assert not result.feasible
    assert "time window violated" in "\n".join(result.violations)


def test_invalid_insertion_position_is_rejected() -> None:
    with pytest.raises(ValueError, match="position must be within"):
        is_feasible_insertion((1,), 2, 2, make_instance())
