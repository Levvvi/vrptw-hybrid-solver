import numpy as np
import pytest

from vrptw_hybrid.core.models import (
    Customer,
    Route,
    RouteStop,
    VehicleSpec,
    VRPTWInstance,
)
from vrptw_hybrid.core.objective import composite_objective, compute_route_distance


def make_instance() -> VRPTWInstance:
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
    return VRPTWInstance(
        name="objective-mini",
        depot=depot,
        customers=customers,
        vehicle=VehicleSpec(capacity=10, count=2),
        distance_matrix=matrix,
        time_matrix=matrix,
        metadata={},
    )


def test_compute_route_distance_includes_return_to_depot() -> None:
    route = Route(
        vehicle_id=0,
        stops=(
            RouteStop(1, 5.0, 5.0, 6.0, 2),
            RouteStop(2, 11.0, 11.0, 12.0, 5),
        ),
        distance=0.0,
        duration=22.0,
        load=5,
    )

    assert compute_route_distance(route, make_instance()) == pytest.approx(20.0)


def test_compute_route_distance_rejects_unknown_customer() -> None:
    route = Route(
        vehicle_id=0,
        stops=(RouteStop(99, 5.0, 5.0, 6.0, 0),),
        distance=0.0,
        duration=0.0,
        load=0,
    )

    with pytest.raises(ValueError, match="Unknown customer id"):
        compute_route_distance(route, make_instance())


def test_composite_objective_prioritizes_vehicle_count() -> None:
    assert composite_objective(vehicles_used=2, total_distance=123.4, vehicle_weight=100000.0) == (
        200123.4
    )


def test_composite_objective_rejects_negative_values() -> None:
    with pytest.raises(ValueError, match="vehicles_used must be non-negative"):
        composite_objective(-1, 0.0, 100000.0)
