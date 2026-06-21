"""Feasibility checks for VRPTW solver outputs."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from vrptw_hybrid.core.models import Customer, RouteStop, Solution, VRPTWInstance


@dataclass(frozen=True, slots=True)
class FeasibilityReport:
    feasible: bool
    violations: tuple[str, ...]


def check_solution(
    solution: Solution,
    instance: VRPTWInstance,
    *,
    tol: float = 1e-6,
) -> FeasibilityReport:
    """Check a solver solution against core VRPTW feasibility constraints."""

    if tol < 0:
        raise ValueError("tol must be non-negative")

    violations: list[str] = []
    node_by_id = {node.id: node for node in instance.nodes}
    index_by_id = {node.id: index for index, node in enumerate(instance.nodes)}
    customer_ids = set(instance.customer_ids)
    visit_counts: Counter[int] = Counter()

    _check_vehicle_counts(solution, instance, violations)

    for route_index, route in enumerate(solution.routes):
        current_load = 0
        previous_id = instance.depot.id
        previous_departure = instance.depot.ready_time

        for stop_index, stop in enumerate(route.stops):
            context = f"route {route_index} stop {stop_index} customer {stop.customer_id}"
            if stop.customer_id == instance.depot.id:
                violations.append(f"{context}: depot cannot be visited as a customer")
                continue
            if stop.customer_id not in customer_ids:
                violations.append(f"{context}: unknown customer id")
                continue

            customer = node_by_id[stop.customer_id]
            visit_counts[stop.customer_id] += 1
            current_load += customer.demand

            if current_load > instance.vehicle.capacity:
                violations.append(
                    f"route {route_index}: capacity exceeded "
                    f"({current_load} > {instance.vehicle.capacity})"
                )
            if stop.load_after != current_load:
                violations.append(
                    f"{context}: load_after {stop.load_after} does not match "
                    f"expected load {current_load}"
                )

            _check_stop_times(
                stop_context=context,
                stop=stop,
                customer=customer,
                tol=tol,
                violations=violations,
            )
            _check_travel_time(
                instance=instance,
                previous_id=previous_id,
                previous_departure=previous_departure,
                current_id=stop.customer_id,
                arrival_time=stop.arrival_time,
                context=context,
                tol=tol,
                violations=violations,
                index_by_id=index_by_id,
            )

            previous_id = stop.customer_id
            previous_departure = stop.departure_time

        if current_load != route.load:
            violations.append(
                f"route {route_index}: route load {route.load} does not match "
                f"expected load {current_load}"
            )
        _check_return_to_depot(
            instance=instance,
            route_index=route_index,
            previous_id=previous_id,
            previous_departure=previous_departure,
            tol=tol,
            violations=violations,
            index_by_id=index_by_id,
        )

    _check_customer_coverage(instance, visit_counts, violations)
    return FeasibilityReport(feasible=not violations, violations=tuple(violations))


def _check_vehicle_counts(
    solution: Solution,
    instance: VRPTWInstance,
    violations: list[str],
) -> None:
    non_empty_routes = sum(1 for route in solution.routes if route.stops)
    if len(solution.routes) > instance.vehicle.count:
        violations.append(
            f"route count {len(solution.routes)} exceeds available vehicles "
            f"{instance.vehicle.count}"
        )
    if solution.vehicles_used > instance.vehicle.count:
        violations.append(
            f"vehicles_used {solution.vehicles_used} exceeds available vehicles "
            f"{instance.vehicle.count}"
        )
    if solution.vehicles_used != non_empty_routes:
        violations.append(
            f"vehicles_used {solution.vehicles_used} does not match non-empty routes "
            f"{non_empty_routes}"
        )


def _check_stop_times(
    *,
    stop_context: str,
    stop: RouteStop,
    customer: Customer,
    tol: float,
    violations: list[str],
) -> None:
    if stop.start_service_time + tol < stop.arrival_time:
        violations.append(f"{stop_context}: service starts before arrival")
    if stop.departure_time + tol < stop.start_service_time + customer.service_time:
        violations.append(f"{stop_context}: departure does not include service time")
    if (
        stop.start_service_time < customer.ready_time - tol
        or stop.start_service_time > customer.due_time + tol
    ):
        violations.append(
            f"{stop_context}: service start {stop.start_service_time} violates time window "
            f"[{customer.ready_time}, {customer.due_time}]"
        )


def _check_travel_time(
    *,
    instance: VRPTWInstance,
    previous_id: int,
    previous_departure: float,
    current_id: int,
    arrival_time: float,
    context: str,
    tol: float,
    violations: list[str],
    index_by_id: dict[int, int],
) -> None:
    previous_index = index_by_id[previous_id]
    current_index = index_by_id[current_id]
    travel_time = float(instance.time_matrix[previous_index, current_index])
    earliest_arrival = previous_departure + travel_time
    if arrival_time + tol < earliest_arrival:
        violations.append(
            f"{context}: arrival {arrival_time} is earlier than travel-time "
            f"minimum {earliest_arrival}"
        )


def _check_return_to_depot(
    *,
    instance: VRPTWInstance,
    route_index: int,
    previous_id: int,
    previous_departure: float,
    tol: float,
    violations: list[str],
    index_by_id: dict[int, int],
) -> None:
    previous_index = index_by_id[previous_id]
    depot_index = index_by_id[instance.depot.id]
    return_time = previous_departure + float(instance.time_matrix[previous_index, depot_index])
    if return_time > instance.depot.due_time + tol:
        violations.append(
            f"route {route_index}: return to depot at {return_time} violates depot due time "
            f"{instance.depot.due_time}"
        )


def _check_customer_coverage(
    instance: VRPTWInstance,
    visit_counts: Counter[int],
    violations: list[str],
) -> None:
    for customer_id in instance.customer_ids:
        count = visit_counts[customer_id]
        if count == 0:
            violations.append(f"customer {customer_id} was not visited")
        elif count > 1:
            violations.append(f"customer {customer_id} was visited {count} times")
