"""Route evaluation and insertion helpers for ALNS repair operators."""

from __future__ import annotations

from dataclasses import dataclass

from vrptw_hybrid.core.models import Route, RouteStop, VRPTWInstance


@dataclass(frozen=True, slots=True)
class InsertionResult:
    feasible: bool
    route: Route | None
    violations: tuple[str, ...]
    distance: float
    duration: float
    load: int


def evaluate_route(
    route_customer_ids: tuple[int, ...],
    instance: VRPTWInstance,
    *,
    vehicle_id: int = 0,
    tol: float = 1e-6,
) -> InsertionResult:
    """Evaluate one route sequence using earliest-start scheduling."""

    if tol < 0:
        raise ValueError("tol must be non-negative")

    customer_by_id = {customer.id: customer for customer in instance.customers}
    index_by_id = {node.id: index for index, node in enumerate(instance.nodes)}
    violations: list[str] = []
    stops: list[RouteStop] = []
    previous_id = instance.depot.id
    previous_departure = instance.depot.ready_time
    distance = 0.0
    load = 0

    for position, customer_id in enumerate(route_customer_ids):
        customer = customer_by_id.get(customer_id)
        if customer is None:
            return InsertionResult(
                feasible=False,
                route=None,
                violations=(f"position {position}: unknown customer id {customer_id}",),
                distance=distance,
                duration=0.0,
                load=load,
            )

        from_index = index_by_id[previous_id]
        to_index = index_by_id[customer_id]
        travel_time = float(instance.time_matrix[from_index, to_index])
        arrival_time = previous_departure + travel_time
        start_service_time = max(arrival_time, customer.ready_time)
        departure_time = start_service_time + customer.service_time
        distance += float(instance.distance_matrix[from_index, to_index])
        load += customer.demand

        if load > instance.vehicle.capacity:
            violations.append(
                f"position {position}: capacity exceeded ({load} > {instance.vehicle.capacity})"
            )
        if start_service_time > customer.due_time + tol:
            violations.append(
                f"position {position}: customer {customer_id} time window violated "
                f"({start_service_time} > {customer.due_time})"
            )

        stops.append(
            RouteStop(
                customer_id=customer_id,
                arrival_time=arrival_time,
                start_service_time=start_service_time,
                departure_time=departure_time,
                load_after=load,
            )
        )
        previous_id = customer_id
        previous_departure = departure_time

    final_from_index = index_by_id[previous_id]
    depot_index = index_by_id[instance.depot.id]
    return_time = previous_departure + float(instance.time_matrix[final_from_index, depot_index])
    distance += float(instance.distance_matrix[final_from_index, depot_index])
    if return_time > instance.depot.due_time + tol:
        violations.append(
            f"return to depot time window violated ({return_time} > {instance.depot.due_time})"
        )

    duration = return_time - instance.depot.ready_time
    route = Route(
        vehicle_id=vehicle_id,
        stops=tuple(stops),
        distance=distance,
        duration=duration,
        load=load,
    )
    return InsertionResult(
        feasible=not violations,
        route=route,
        violations=tuple(violations),
        distance=distance,
        duration=duration,
        load=load,
    )


def is_feasible_insertion(
    route_customer_ids: tuple[int, ...],
    customer_id: int,
    position: int,
    instance: VRPTWInstance,
) -> bool:
    """Return whether inserting a customer at position keeps the route feasible."""

    return _evaluate_insertion(route_customer_ids, customer_id, position, instance).feasible


def insertion_delta_cost(
    route_customer_ids: tuple[int, ...],
    customer_id: int,
    position: int,
    instance: VRPTWInstance,
) -> float | None:
    """Return distance delta for a feasible insertion, otherwise None."""

    base = evaluate_route(route_customer_ids, instance)
    inserted = _evaluate_insertion(route_customer_ids, customer_id, position, instance)
    if not inserted.feasible:
        return None
    return inserted.distance - base.distance


def _evaluate_insertion(
    route_customer_ids: tuple[int, ...],
    customer_id: int,
    position: int,
    instance: VRPTWInstance,
) -> InsertionResult:
    if position < 0 or position > len(route_customer_ids):
        raise ValueError("position must be within the route insertion range")
    inserted_ids = (
        *route_customer_ids[:position],
        customer_id,
        *route_customer_ids[position:],
    )
    return evaluate_route(inserted_ids, instance)
