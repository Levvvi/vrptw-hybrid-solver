"""Greedy insertion solver for constructing initial VRPTW solutions."""

from __future__ import annotations

import random
from dataclasses import dataclass
from time import perf_counter

from vrptw_hybrid.core.checker import check_solution
from vrptw_hybrid.core.models import Route, RouteStop, Solution, VRPTWInstance
from vrptw_hybrid.core.objective import composite_objective


class GreedyConstructionError(RuntimeError):
    """Raised when greedy construction cannot produce a feasible complete solution."""


@dataclass(frozen=True, slots=True)
class _InsertionCandidate:
    customer_id: int
    route_index: int | None
    insert_position: int
    route_ids: tuple[int, ...]
    route: Route
    score: float


class GreedySolver:
    """Minimum-delta insertion heuristic for VRPTW initial solutions."""

    def __init__(
        self,
        *,
        vehicle_weight: float = 100000.0,
        deterministic: bool = True,
        seed: int | None = None,
    ) -> None:
        self.vehicle_weight = vehicle_weight
        self.deterministic = deterministic
        self.seed = seed
        self._rng = random.Random(seed)

    def solve(self, instance: VRPTWInstance) -> Solution:
        """Construct a feasible solution by repeatedly inserting one customer."""

        start_time = perf_counter()
        route_ids: list[tuple[int, ...]] = []
        route_objects: list[Route] = []
        unassigned = set(instance.customer_ids)

        while unassigned:
            candidate = self._choose_candidate(
                instance=instance,
                route_ids=route_ids,
                route_objects=route_objects,
                unassigned=unassigned,
            )
            if candidate.route_index is None:
                route_ids.append(candidate.route_ids)
                route_objects.append(candidate.route)
            else:
                route_ids[candidate.route_index] = candidate.route_ids
                route_objects[candidate.route_index] = candidate.route
            unassigned.remove(candidate.customer_id)

        runtime_sec = perf_counter() - start_time
        vehicles_used = len(route_objects)
        total_distance = sum(route.distance for route in route_objects)
        total_duration = sum(route.duration for route in route_objects)
        solution = Solution(
            instance_name=instance.name,
            solver_name="greedy",
            routes=tuple(route_objects),
            objective=composite_objective(
                vehicles_used=vehicles_used,
                total_distance=total_distance,
                vehicle_weight=self.vehicle_weight,
            ),
            vehicles_used=vehicles_used,
            total_distance=total_distance,
            total_duration=total_duration,
            feasible=False,
            runtime_sec=runtime_sec,
            metadata={
                "strategy": "minimum_delta_insertion",
                "deterministic": self.deterministic,
                "seed": self.seed,
            },
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
            feasible=report.feasible,
            runtime_sec=solution.runtime_sec,
            metadata={
                **solution.metadata,
                "feasibility_violations": list(report.violations),
            },
        )

    def _choose_candidate(
        self,
        *,
        instance: VRPTWInstance,
        route_ids: list[tuple[int, ...]],
        route_objects: list[Route],
        unassigned: set[int],
    ) -> _InsertionCandidate:
        candidates = self._generate_candidates(
            instance=instance,
            route_ids=route_ids,
            route_objects=route_objects,
            unassigned=unassigned,
        )
        if not candidates:
            unresolved = ", ".join(str(customer_id) for customer_id in sorted(unassigned))
            raise GreedyConstructionError(
                "Greedy construction could not insert remaining customers: "
                f"{unresolved}. Increase vehicle count/capacity or relax time windows."
            )

        ordered = sorted(
            candidates,
            key=lambda candidate: (
                candidate.score,
                instance.nodes[_index_by_customer_id(instance)[candidate.customer_id]].due_time,
                candidate.customer_id,
                candidate.route_index is None,
                -1 if candidate.route_index is None else candidate.route_index,
                candidate.insert_position,
            ),
        )
        if self.deterministic:
            return ordered[0]

        best_score = ordered[0].score
        tied = [candidate for candidate in ordered if abs(candidate.score - best_score) <= 1e-9]
        return self._rng.choice(tied)

    def _generate_candidates(
        self,
        *,
        instance: VRPTWInstance,
        route_ids: list[tuple[int, ...]],
        route_objects: list[Route],
        unassigned: set[int],
    ) -> list[_InsertionCandidate]:
        candidates: list[_InsertionCandidate] = []
        for customer_id in sorted(unassigned):
            for route_index, ids in enumerate(route_ids):
                old_distance = route_objects[route_index].distance
                for insert_position in range(len(ids) + 1):
                    candidate_ids = (
                        *ids[:insert_position],
                        customer_id,
                        *ids[insert_position:],
                    )
                    route = _build_route(instance, route_index, candidate_ids)
                    if route is None:
                        continue
                    score = route.distance - old_distance
                    candidates.append(
                        _InsertionCandidate(
                            customer_id=customer_id,
                            route_index=route_index,
                            insert_position=insert_position,
                            route_ids=candidate_ids,
                            route=route,
                            score=score,
                        )
                    )

            if len(route_ids) < instance.vehicle.count:
                route_index = len(route_ids)
                candidate_ids = (customer_id,)
                route = _build_route(instance, route_index, candidate_ids)
                if route is None:
                    continue
                candidates.append(
                    _InsertionCandidate(
                        customer_id=customer_id,
                        route_index=None,
                        insert_position=0,
                        route_ids=candidate_ids,
                        route=route,
                        score=self.vehicle_weight + route.distance,
                    )
                )
        return candidates


def solve_greedy(
    instance: VRPTWInstance,
    *,
    vehicle_weight: float = 100000.0,
    deterministic: bool = True,
    seed: int | None = None,
) -> Solution:
    """Convenience wrapper around :class:`GreedySolver`."""

    return GreedySolver(
        vehicle_weight=vehicle_weight,
        deterministic=deterministic,
        seed=seed,
    ).solve(instance)


def _build_route(
    instance: VRPTWInstance,
    vehicle_id: int,
    customer_ids: tuple[int, ...],
) -> Route | None:
    index_by_id = _index_by_customer_id(instance)
    customer_by_id = {customer.id: customer for customer in instance.customers}
    stops: list[RouteStop] = []
    load = 0
    previous_id = instance.depot.id
    previous_departure = instance.depot.ready_time

    for customer_id in customer_ids:
        customer = customer_by_id[customer_id]
        previous_index = index_by_id[previous_id]
        current_index = index_by_id[customer_id]
        travel_time = float(instance.time_matrix[previous_index, current_index])
        arrival_time = previous_departure + travel_time
        start_service_time = max(arrival_time, customer.ready_time)
        if start_service_time > customer.due_time:
            return None
        departure_time = start_service_time + customer.service_time
        load += customer.demand
        if load > instance.vehicle.capacity:
            return None
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

    previous_index = index_by_id[previous_id]
    depot_index = index_by_id[instance.depot.id]
    return_time = previous_departure + float(instance.time_matrix[previous_index, depot_index])
    if return_time > instance.depot.due_time:
        return None

    return Route(
        vehicle_id=vehicle_id,
        stops=tuple(stops),
        distance=_route_distance(instance, customer_ids),
        duration=return_time - instance.depot.ready_time,
        load=load,
    )


def _route_distance(instance: VRPTWInstance, customer_ids: tuple[int, ...]) -> float:
    index_by_id = _index_by_customer_id(instance)
    previous_id = instance.depot.id
    distance = 0.0
    for customer_id in customer_ids:
        from_index = index_by_id[previous_id]
        to_index = index_by_id[customer_id]
        distance += float(instance.distance_matrix[from_index, to_index])
        previous_id = customer_id
    final_from_index = index_by_id[previous_id]
    depot_index = index_by_id[instance.depot.id]
    distance += float(instance.distance_matrix[final_from_index, depot_index])
    return distance


def _index_by_customer_id(instance: VRPTWInstance) -> dict[int, int]:
    return {node.id: index for index, node in enumerate(instance.nodes)}
