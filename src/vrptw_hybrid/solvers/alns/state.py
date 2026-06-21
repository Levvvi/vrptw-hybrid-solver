"""Mutable-search state representation for ALNS."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, replace
from typing import Any

from vrptw_hybrid.core.checker import check_solution
from vrptw_hybrid.core.models import Route, RouteStop, Solution, VRPTWInstance
from vrptw_hybrid.core.objective import composite_objective


@dataclass(frozen=True, slots=True)
class ALNSState:
    routes: tuple[tuple[int, ...], ...]
    unassigned: frozenset[int]
    cost: float
    feasible: bool
    metadata: dict[str, Any]

    def __post_init__(self) -> None:
        object.__setattr__(self, "routes", tuple(tuple(route) for route in self.routes))
        object.__setattr__(self, "unassigned", frozenset(self.unassigned))
        object.__setattr__(self, "metadata", deepcopy(self.metadata))

    @classmethod
    def from_solution(cls, solution: Solution) -> ALNSState:
        """Create an ALNS state from a complete or partial Solution."""

        route_customer_ids = tuple(
            tuple(stop.customer_id for stop in route.stops) for route in solution.routes
        )
        return cls(
            routes=route_customer_ids,
            unassigned=frozenset(solution.metadata.get("unassigned", ())),
            cost=solution.objective,
            feasible=solution.feasible,
            metadata={
                "source_solver": solution.solver_name,
                "instance_name": solution.instance_name,
                **deepcopy(solution.metadata),
            },
        )

    def copy_with(
        self,
        *,
        routes: tuple[tuple[int, ...], ...] | None = None,
        unassigned: frozenset[int] | set[int] | tuple[int, ...] | None = None,
        cost: float | None = None,
        feasible: bool | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ALNSState:
        """Return a safe modified copy without sharing mutable metadata."""

        return replace(
            self,
            routes=self.routes if routes is None else routes,
            unassigned=self.unassigned if unassigned is None else frozenset(unassigned),
            cost=self.cost if cost is None else cost,
            feasible=self.feasible if feasible is None else feasible,
            metadata=deepcopy(self.metadata if metadata is None else metadata),
        )

    def to_solution(
        self,
        instance: VRPTWInstance,
        *,
        solver_name: str = "alns_state",
        vehicle_weight: float = 100000.0,
        runtime_sec: float = 0.0,
    ) -> Solution:
        """Convert state routes back to a unified Solution object."""

        routes = tuple(
            _build_route(instance, vehicle_id, route)
            for vehicle_id, route in enumerate(self.routes)
        )
        vehicles_used = sum(1 for route in routes if route.stops)
        total_distance = sum(route.distance for route in routes)
        total_duration = sum(route.duration for route in routes)
        metadata = {
            **deepcopy(self.metadata),
            "unassigned": sorted(self.unassigned),
            "state_cost": self.cost,
        }
        solution = Solution(
            instance_name=instance.name,
            solver_name=solver_name,
            routes=routes,
            objective=composite_objective(vehicles_used, total_distance, vehicle_weight),
            vehicles_used=vehicles_used,
            total_distance=total_distance,
            total_duration=total_duration,
            feasible=False,
            runtime_sec=runtime_sec,
            metadata=metadata,
        )
        report = check_solution(solution, instance)
        return Solution(
            instance_name=solution.instance_name,
            solver_name=solution.solver_name,
            routes=solution.routes,
            objective=solution.objective,
            vehicles_used=solution.vehicles_used,
            total_distance=solution.total_distance,
            total_duration=solution.total_duration,
            feasible=report.feasible and not self.unassigned,
            runtime_sec=solution.runtime_sec,
            metadata={
                **solution.metadata,
                "feasibility_violations": list(report.violations),
            },
        )


def _build_route(instance: VRPTWInstance, vehicle_id: int, customer_ids: tuple[int, ...]) -> Route:
    index_by_id = {node.id: index for index, node in enumerate(instance.nodes)}
    customer_by_id = {customer.id: customer for customer in instance.customers}
    previous_id = instance.depot.id
    previous_departure = instance.depot.ready_time
    stops: list[RouteStop] = []
    distance = 0.0
    load = 0

    for customer_id in customer_ids:
        customer = customer_by_id[customer_id]
        from_index = index_by_id[previous_id]
        to_index = index_by_id[customer_id]
        arrival_time = previous_departure + float(instance.time_matrix[from_index, to_index])
        start_service_time = max(arrival_time, customer.ready_time)
        departure_time = start_service_time + customer.service_time
        distance += float(instance.distance_matrix[from_index, to_index])
        load += customer.demand
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
    return Route(
        vehicle_id=vehicle_id,
        stops=tuple(stops),
        distance=distance,
        duration=return_time - instance.depot.ready_time,
        load=load,
    )
