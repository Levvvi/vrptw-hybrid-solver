import random
from pathlib import Path

import numpy as np

from vrptw_hybrid.core.checker import check_solution
from vrptw_hybrid.core.models import Customer, VehicleSpec, VRPTWInstance
from vrptw_hybrid.data.solomon import parse_solomon
from vrptw_hybrid.solvers.alns.destroy import random_removal
from vrptw_hybrid.solvers.alns.repair import (
    REPAIR_OPERATORS,
    greedy_cheapest_insertion,
    noise_insertion,
    regret_2_insertion,
    regret_3_insertion,
    time_window_priority_insertion,
)
from vrptw_hybrid.solvers.alns.state import ALNSState
from vrptw_hybrid.solvers.greedy import solve_greedy

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "mini_solomon.txt"


def state_signature(state: ALNSState) -> tuple[tuple[int, ...], ...]:
    return state.routes


def test_repair_operator_registry_has_names() -> None:
    assert {operator.name for operator in REPAIR_OPERATORS} == {
        "greedy_cheapest_insertion",
        "regret_2_insertion",
        "regret_3_insertion",
        "time_window_priority_insertion",
        "noise_insertion",
    }


def destroyed_mini_state(q: int = 2) -> tuple[VRPTWInstance, ALNSState]:
    instance = parse_solomon(FIXTURE, limit_customers=8)
    solution = solve_greedy(instance, seed=42)
    state = ALNSState.from_solution(solution)
    destroyed = random_removal(state, instance, random.Random(2), q=q)
    return instance, destroyed


def test_greedy_cheapest_repair_restores_feasible_mini_state() -> None:
    instance, destroyed = destroyed_mini_state(q=2)

    repaired = greedy_cheapest_insertion(destroyed, instance, random.Random(1))
    solution = repaired.to_solution(instance)
    report = check_solution(solution, instance)

    assert repaired.unassigned == frozenset()
    assert repaired.feasible
    assert report.feasible
    assert sorted(customer_id for route in repaired.routes for customer_id in route) == list(
        instance.customer_ids
    )
    assert destroyed.unassigned


def test_regret_repairs_restore_feasible_state() -> None:
    instance, destroyed = destroyed_mini_state(q=3)

    repaired_2 = regret_2_insertion(destroyed, instance, random.Random(1))
    repaired_3 = regret_3_insertion(destroyed, instance, random.Random(1))

    assert repaired_2.unassigned == frozenset()
    assert repaired_2.feasible
    assert repaired_3.unassigned == frozenset()
    assert repaired_3.feasible


def test_time_window_priority_inserts_tight_customer_first() -> None:
    instance = make_priority_instance()
    state = ALNSState(
        routes=((1,),),
        unassigned=frozenset({2, 3}),
        cost=float("inf"),
        feasible=False,
        metadata={},
    )

    repaired = time_window_priority_insertion(state, instance, random.Random(1))

    assert repaired.metadata["inserted_customers"][0] == 2
    assert repaired.unassigned == frozenset()
    assert repaired.feasible


def test_noise_insertion_is_seed_reproducible() -> None:
    instance, destroyed = destroyed_mini_state(q=3)

    first = noise_insertion(destroyed, instance, random.Random(7))
    second = noise_insertion(destroyed, instance, random.Random(7))

    assert state_signature(first) == state_signature(second)


def test_repair_records_infeasible_when_vehicle_capacity_blocks_insertion() -> None:
    depot = Customer(id=0, x=0.0, y=0.0, demand=0, ready_time=0.0, due_time=100.0, service_time=0.0)
    customers = (
        Customer(id=1, x=1.0, y=0.0, demand=1, ready_time=0.0, due_time=100.0, service_time=0.0),
        Customer(id=2, x=2.0, y=0.0, demand=1, ready_time=0.0, due_time=100.0, service_time=0.0),
    )
    matrix = np.array(
        [
            [0.0, 1.0, 2.0],
            [1.0, 0.0, 1.0],
            [2.0, 1.0, 0.0],
        ]
    )
    instance = VRPTWInstance(
        name="repair-blocked",
        depot=depot,
        customers=customers,
        vehicle=VehicleSpec(capacity=1, count=1),
        distance_matrix=matrix,
        time_matrix=matrix,
        metadata={},
    )
    state = ALNSState(
        routes=((1,),),
        unassigned=frozenset({2}),
        cost=float("inf"),
        feasible=False,
        metadata={},
    )

    repaired = greedy_cheapest_insertion(state, instance, random.Random(1))

    assert repaired.unassigned == frozenset({2})
    assert not repaired.feasible
    assert repaired.metadata["remaining_unassigned"] == [2]


def make_priority_instance() -> VRPTWInstance:
    depot = Customer(id=0, x=0.0, y=0.0, demand=0, ready_time=0.0, due_time=100.0, service_time=0.0)
    customers = (
        Customer(id=1, x=1.0, y=0.0, demand=1, ready_time=0.0, due_time=100.0, service_time=0.0),
        Customer(id=2, x=2.0, y=0.0, demand=1, ready_time=9.0, due_time=10.0, service_time=0.0),
        Customer(id=3, x=3.0, y=0.0, demand=1, ready_time=0.0, due_time=100.0, service_time=0.0),
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
        name="priority",
        depot=depot,
        customers=customers,
        vehicle=VehicleSpec(capacity=10, count=2),
        distance_matrix=matrix,
        time_matrix=matrix,
        metadata={},
    )
