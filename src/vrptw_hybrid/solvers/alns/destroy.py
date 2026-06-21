"""Destroy operators for Adaptive Large Neighborhood Search."""

from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import dataclass

from vrptw_hybrid.core.models import VRPTWInstance
from vrptw_hybrid.solvers.alns.state import ALNSState

DestroyFunction = Callable[[ALNSState, VRPTWInstance, random.Random, int], ALNSState]


@dataclass(frozen=True, slots=True)
class DestroyOperator:
    name: str
    function: DestroyFunction

    def __call__(
        self,
        state: ALNSState,
        instance: VRPTWInstance,
        rng: random.Random,
        q: int,
    ) -> ALNSState:
        return self.function(state, instance, rng, q)


def random_removal(
    state: ALNSState,
    instance: VRPTWInstance,
    rng: random.Random,
    q: int,
) -> ALNSState:
    """Remove q assigned customers uniformly at random."""

    assigned = _assigned_customers(state)
    removed = set(rng.sample(assigned, k=min(_valid_q(q), len(assigned))))
    return _remove_customers(state, removed, "random_removal")


def worst_distance_removal(
    state: ALNSState,
    instance: VRPTWInstance,
    rng: random.Random,
    q: int,
) -> ALNSState:
    """Remove customers with the largest marginal distance contribution."""

    contributions = []
    index_by_id = {node.id: index for index, node in enumerate(instance.nodes)}
    for route in state.routes:
        padded = (instance.depot.id, *route, instance.depot.id)
        for position, customer_id in enumerate(route, start=1):
            previous_id = padded[position - 1]
            next_id = padded[position + 1]
            contribution = (
                float(instance.distance_matrix[index_by_id[previous_id], index_by_id[customer_id]])
                + float(instance.distance_matrix[index_by_id[customer_id], index_by_id[next_id]])
                - float(instance.distance_matrix[index_by_id[previous_id], index_by_id[next_id]])
            )
            contributions.append((contribution, customer_id))

    ordered = sorted(contributions, key=lambda item: (-item[0], item[1]))
    removed = {customer_id for _contribution, customer_id in ordered[: _valid_q(q)]}
    return _remove_customers(state, removed, "worst_distance_removal")


def shaw_related_removal(
    state: ALNSState,
    instance: VRPTWInstance,
    rng: random.Random,
    q: int,
) -> ALNSState:
    """Remove one random seed customer and its most related neighbors."""

    assigned = _assigned_customers(state)
    if not assigned or q <= 0:
        return _remove_customers(state, set(), "shaw_related_removal")

    seed_customer_id = rng.choice(assigned)
    related = sorted(
        (customer_id for customer_id in assigned if customer_id != seed_customer_id),
        key=lambda customer_id: _relatedness(instance, seed_customer_id, customer_id),
    )
    removed = {seed_customer_id, *related[: max(0, min(q, len(assigned)) - 1)]}
    return _remove_customers(state, removed, "shaw_related_removal")


def route_removal(
    state: ALNSState,
    instance: VRPTWInstance,
    rng: random.Random,
    q: int,
) -> ALNSState:
    """Remove a whole short route, using randomness for ties."""

    non_empty_routes = [route for route in state.routes if route]
    if not non_empty_routes or q <= 0:
        return _remove_customers(state, set(), "route_removal")

    min_length = min(len(route) for route in non_empty_routes)
    shortest_routes = [route for route in non_empty_routes if len(route) == min_length]
    removed = set(rng.choice(shortest_routes))
    return _remove_customers(state, removed, "route_removal")


def time_window_tight_removal(
    state: ALNSState,
    instance: VRPTWInstance,
    rng: random.Random,
    q: int,
) -> ALNSState:
    """Remove customers with the tightest time windows."""

    customer_by_id = {customer.id: customer for customer in instance.customers}
    assigned = _assigned_customers(state)
    ordered = sorted(
        assigned,
        key=lambda customer_id: (
            customer_by_id[customer_id].due_time - customer_by_id[customer_id].ready_time,
            customer_by_id[customer_id].due_time,
            customer_id,
        ),
    )
    return _remove_customers(state, set(ordered[: _valid_q(q)]), "time_window_tight_removal")


DESTROY_OPERATORS = (
    DestroyOperator("random_removal", random_removal),
    DestroyOperator("worst_distance_removal", worst_distance_removal),
    DestroyOperator("shaw_related_removal", shaw_related_removal),
    DestroyOperator("route_removal", route_removal),
    DestroyOperator("time_window_tight_removal", time_window_tight_removal),
)


def _assigned_customers(state: ALNSState) -> list[int]:
    return [customer_id for route in state.routes for customer_id in route]


def _remove_customers(state: ALNSState, removed: set[int], operator_name: str) -> ALNSState:
    if not removed:
        return state.copy_with(
            feasible=False,
            metadata={**state.metadata, "last_destroy": operator_name, "removed_customers": []},
        )

    new_routes = tuple(
        tuple(customer_id for customer_id in route if customer_id not in removed)
        for route in state.routes
    )
    new_routes = tuple(route for route in new_routes if route)
    return state.copy_with(
        routes=new_routes,
        unassigned=state.unassigned | removed,
        cost=float("inf"),
        feasible=False,
        metadata={
            **state.metadata,
            "last_destroy": operator_name,
            "removed_customers": sorted(removed),
        },
    )


def _relatedness(instance: VRPTWInstance, first_customer_id: int, second_customer_id: int) -> float:
    index_by_id = {node.id: index for index, node in enumerate(instance.nodes)}
    customer_by_id = {customer.id: customer for customer in instance.customers}
    first = customer_by_id[first_customer_id]
    second = customer_by_id[second_customer_id]
    first_index = index_by_id[first_customer_id]
    second_index = index_by_id[second_customer_id]
    distance = float(instance.distance_matrix[first_index, second_index])
    ready_gap = abs(first.ready_time - second.ready_time)
    due_gap = abs(first.due_time - second.due_time)
    demand_gap = abs(first.demand - second.demand)
    return distance + ready_gap + due_gap + demand_gap


def _valid_q(q: int) -> int:
    if q < 0:
        raise ValueError("q must be non-negative")
    return q
