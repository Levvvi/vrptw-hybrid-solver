"""Objective helpers for VRPTW solutions."""

from __future__ import annotations

from vrptw_hybrid.core.models import Route, VRPTWInstance


def compute_route_distance(route: Route, instance: VRPTWInstance) -> float:
    """Compute depot-to-depot route distance from the instance matrix."""

    index_by_id = {node.id: index for index, node in enumerate(instance.nodes)}
    previous_id = instance.depot.id
    distance = 0.0

    for stop in route.stops:
        if stop.customer_id not in index_by_id:
            raise ValueError(f"Unknown customer id in route: {stop.customer_id}")
        distance += _distance_between(instance, index_by_id, previous_id, stop.customer_id)
        previous_id = stop.customer_id

    distance += _distance_between(instance, index_by_id, previous_id, instance.depot.id)
    return distance


def composite_objective(
    vehicles_used: int,
    total_distance: float,
    vehicle_weight: float,
) -> float:
    """Compute a vehicle-prioritized composite VRPTW objective."""

    if vehicles_used < 0:
        raise ValueError("vehicles_used must be non-negative")
    if total_distance < 0:
        raise ValueError("total_distance must be non-negative")
    if vehicle_weight < 0:
        raise ValueError("vehicle_weight must be non-negative")
    return vehicle_weight * vehicles_used + total_distance


def _distance_between(
    instance: VRPTWInstance,
    index_by_id: dict[int, int],
    from_id: int,
    to_id: int,
) -> float:
    from_index = index_by_id[from_id]
    to_index = index_by_id[to_id]
    return float(instance.distance_matrix[from_index, to_index])
