import numpy as np
import pytest

from vrptw_hybrid.core.models import (
    Customer,
    Route,
    RouteStop,
    Solution,
    VehicleSpec,
    VRPTWInstance,
)


def make_customers() -> tuple[Customer, ...]:
    return (
        Customer(id=1, x=1.0, y=0.0, demand=2, ready_time=0.0, due_time=20.0, service_time=1.0),
        Customer(id=2, x=2.0, y=0.0, demand=2, ready_time=0.0, due_time=20.0, service_time=1.0),
        Customer(id=3, x=3.0, y=0.0, demand=2, ready_time=0.0, due_time=20.0, service_time=1.0),
    )


def test_construct_vrptw_instance_with_three_customers() -> None:
    depot = Customer(id=0, x=0.0, y=0.0, demand=0, ready_time=0.0, due_time=100.0, service_time=0.0)
    matrix = np.zeros((4, 4))

    instance = VRPTWInstance(
        name="mini",
        depot=depot,
        customers=make_customers(),
        vehicle=VehicleSpec(capacity=10, count=2),
        distance_matrix=matrix,
        time_matrix=matrix,
        metadata={"source": "unit-test"},
    )

    assert instance.node_count == 4
    assert instance.nodes[0] == depot
    assert instance.customer_ids == (1, 2, 3)
    assert instance.metadata == {"source": "unit-test"}


def test_vrptw_instance_rejects_bad_distance_matrix_shape() -> None:
    depot = Customer(id=0, x=0.0, y=0.0, demand=0, ready_time=0.0, due_time=100.0, service_time=0.0)
    bad_distance = np.zeros((3, 3))
    time_matrix = np.zeros((4, 4))

    with pytest.raises(ValueError, match=r"distance_matrix must be shape \(4, 4\)"):
        VRPTWInstance(
            name="mini",
            depot=depot,
            customers=make_customers(),
            vehicle=VehicleSpec(capacity=10, count=2),
            distance_matrix=bad_distance,
            time_matrix=time_matrix,
            metadata={},
        )


def test_vrptw_instance_rejects_duplicate_customer_ids() -> None:
    depot = Customer(id=0, x=0.0, y=0.0, demand=0, ready_time=0.0, due_time=100.0, service_time=0.0)
    customers = (
        Customer(id=1, x=1.0, y=0.0, demand=1, ready_time=0.0, due_time=20.0, service_time=1.0),
        Customer(id=1, x=2.0, y=0.0, demand=1, ready_time=0.0, due_time=20.0, service_time=1.0),
    )
    matrix = np.zeros((3, 3))

    with pytest.raises(ValueError, match="Customer ids must be unique"):
        VRPTWInstance(
            name="duplicate",
            depot=depot,
            customers=customers,
            vehicle=VehicleSpec(capacity=10, count=2),
            distance_matrix=matrix,
            time_matrix=matrix,
            metadata={},
        )


def test_route_and_solution_models_are_constructible() -> None:
    stop = RouteStop(
        customer_id=1,
        arrival_time=3.0,
        start_service_time=4.0,
        departure_time=5.0,
        load_after=2,
    )
    route = Route(vehicle_id=0, stops=(stop,), distance=10.5, duration=15.0, load=2)

    solution = Solution(
        instance_name="mini",
        solver_name="unit",
        routes=(route,),
        objective=100010.5,
        vehicles_used=1,
        total_distance=10.5,
        total_duration=15.0,
        feasible=True,
        runtime_sec=0.01,
        metadata={"status": "ok"},
    )

    assert solution.routes == (route,)
    assert solution.metadata["status"] == "ok"


def test_invalid_time_window_is_rejected() -> None:
    with pytest.raises(ValueError, match="ready_time cannot exceed due_time"):
        Customer(
            id=9,
            x=0.0,
            y=0.0,
            demand=1,
            ready_time=10.0,
            due_time=5.0,
            service_time=1.0,
        )
