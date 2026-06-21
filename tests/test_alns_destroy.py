import random

import numpy as np
import pytest

from vrptw_hybrid.core.models import Customer, VehicleSpec, VRPTWInstance
from vrptw_hybrid.solvers.alns.destroy import (
    DESTROY_OPERATORS,
    random_removal,
    route_removal,
    shaw_related_removal,
    time_window_tight_removal,
    worst_distance_removal,
)
from vrptw_hybrid.solvers.alns.state import ALNSState


def make_instance() -> VRPTWInstance:
    depot = Customer(id=0, x=0.0, y=0.0, demand=0, ready_time=0.0, due_time=100.0, service_time=0.0)
    customers = (
        Customer(id=1, x=1.0, y=0.0, demand=1, ready_time=0.0, due_time=100.0, service_time=0.0),
        Customer(id=2, x=2.0, y=0.0, demand=2, ready_time=0.0, due_time=5.0, service_time=0.0),
        Customer(id=3, x=3.0, y=0.0, demand=1, ready_time=0.0, due_time=100.0, service_time=0.0),
        Customer(id=4, x=4.0, y=0.0, demand=1, ready_time=9.0, due_time=10.0, service_time=0.0),
    )
    matrix = np.array(
        [
            [0.0, 1.0, 10.0, 1.0, 4.0],
            [1.0, 0.0, 10.0, 1.0, 3.0],
            [10.0, 10.0, 0.0, 10.0, 2.0],
            [1.0, 1.0, 10.0, 0.0, 1.0],
            [4.0, 3.0, 2.0, 1.0, 0.0],
        ]
    )
    return VRPTWInstance(
        name="destroy-mini",
        depot=depot,
        customers=customers,
        vehicle=VehicleSpec(capacity=10, count=2),
        distance_matrix=matrix,
        time_matrix=matrix,
        metadata={},
    )


def make_state() -> ALNSState:
    return ALNSState(
        routes=((1, 2, 3), (4,)),
        unassigned=frozenset(),
        cost=100.0,
        feasible=True,
        metadata={"tag": "original"},
    )


def test_destroy_operator_registry_has_names() -> None:
    assert {operator.name for operator in DESTROY_OPERATORS} == {
        "random_removal",
        "worst_distance_removal",
        "shaw_related_removal",
        "route_removal",
        "time_window_tight_removal",
    }


def test_random_removal_removes_q_without_mutating_original() -> None:
    state = make_state()

    destroyed = random_removal(state, make_instance(), random.Random(7), q=2)

    assert len(destroyed.unassigned) == 2
    assert state.routes == ((1, 2, 3), (4,))
    assert state.unassigned == frozenset()
    assert destroyed.metadata["last_destroy"] == "random_removal"
    assert destroyed.cost == float("inf")


def test_worst_distance_removal_removes_largest_detour_customer() -> None:
    destroyed = worst_distance_removal(make_state(), make_instance(), random.Random(1), q=1)

    assert destroyed.unassigned == frozenset({2})
    assert destroyed.routes == ((1, 3), (4,))


def test_shaw_related_removal_removes_requested_count() -> None:
    destroyed = shaw_related_removal(make_state(), make_instance(), random.Random(3), q=2)

    assert len(destroyed.unassigned) == 2
    assert destroyed.metadata["last_destroy"] == "shaw_related_removal"


def test_route_removal_removes_short_route() -> None:
    destroyed = route_removal(make_state(), make_instance(), random.Random(1), q=1)

    assert destroyed.unassigned == frozenset({4})
    assert destroyed.routes == ((1, 2, 3),)


def test_time_window_tight_removal_removes_tightest_customer() -> None:
    destroyed = time_window_tight_removal(make_state(), make_instance(), random.Random(1), q=1)

    assert destroyed.unassigned == frozenset({4})


def test_negative_q_is_rejected() -> None:
    with pytest.raises(ValueError, match="q must be non-negative"):
        random_removal(make_state(), make_instance(), random.Random(1), q=-1)
