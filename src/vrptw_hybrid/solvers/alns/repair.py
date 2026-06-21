"""Repair operators for Adaptive Large Neighborhood Search."""

from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import dataclass

from vrptw_hybrid.core.models import VRPTWInstance
from vrptw_hybrid.solvers.alns.context import ALNSContext
from vrptw_hybrid.solvers.alns.route_eval import InsertionResult, evaluate_route
from vrptw_hybrid.solvers.alns.state import ALNSState

RepairFunction = Callable[[ALNSState, VRPTWInstance, random.Random, ALNSContext | None], ALNSState]


@dataclass(frozen=True, slots=True)
class RepairOperator:
    name: str
    function: RepairFunction

    def __call__(
        self,
        state: ALNSState,
        instance: VRPTWInstance,
        rng: random.Random,
        context: ALNSContext | None = None,
    ) -> ALNSState:
        return self.function(state, instance, rng, context)


@dataclass(frozen=True, slots=True)
class _InsertionCandidate:
    customer_id: int
    route_index: int | None
    position: int
    route_ids: tuple[int, ...]
    delta_cost: float
    score: float


def greedy_cheapest_insertion(
    state: ALNSState,
    instance: VRPTWInstance,
    rng: random.Random,
    context: ALNSContext | None = None,
) -> ALNSState:
    """Insert each unassigned customer at the cheapest feasible position."""

    return _repair_loop(
        state,
        instance,
        rng,
        _select_cheapest,
        "greedy_cheapest_insertion",
        context,
    )


def regret_2_insertion(
    state: ALNSState,
    instance: VRPTWInstance,
    rng: random.Random,
    context: ALNSContext | None = None,
) -> ALNSState:
    """Regret-2 insertion repair."""

    return _repair_loop(
        state,
        instance,
        rng,
        lambda candidates: _select_regret(candidates, regret_k=2),
        "regret_2_insertion",
        context,
    )


def regret_3_insertion(
    state: ALNSState,
    instance: VRPTWInstance,
    rng: random.Random,
    context: ALNSContext | None = None,
) -> ALNSState:
    """Regret-3 insertion repair."""

    return _repair_loop(
        state,
        instance,
        rng,
        lambda candidates: _select_regret(candidates, regret_k=3),
        "regret_3_insertion",
        context,
    )


def time_window_priority_insertion(
    state: ALNSState,
    instance: VRPTWInstance,
    rng: random.Random,
    context: ALNSContext | None = None,
) -> ALNSState:
    """Insert tight-window customers first, using cheapest feasible positions."""

    return _repair_loop(
        state,
        instance,
        rng,
        lambda candidates: _select_time_window_priority(candidates, instance),
        "time_window_priority_insertion",
        context,
    )


def noise_insertion(
    state: ALNSState,
    instance: VRPTWInstance,
    rng: random.Random,
    context: ALNSContext | None = None,
) -> ALNSState:
    """Cheapest insertion with small random noise added to candidate scores."""

    return _repair_loop(
        state,
        instance,
        rng,
        lambda candidates: _select_noise(candidates, rng),
        "noise_insertion",
        context,
    )


REPAIR_OPERATORS = (
    RepairOperator("greedy_cheapest_insertion", greedy_cheapest_insertion),
    RepairOperator("regret_2_insertion", regret_2_insertion),
    RepairOperator("regret_3_insertion", regret_3_insertion),
    RepairOperator("time_window_priority_insertion", time_window_priority_insertion),
    RepairOperator("noise_insertion", noise_insertion),
)


def _repair_loop(
    state: ALNSState,
    instance: VRPTWInstance,
    rng: random.Random,
    selector: Callable[[list[_InsertionCandidate]], _InsertionCandidate | None],
    operator_name: str,
    context: ALNSContext | None,
) -> ALNSState:
    repaired = state.copy_with(
        feasible=False,
        metadata={**state.metadata, "last_repair": operator_name, "inserted_customers": []},
    )

    while repaired.unassigned:
        candidates = _generate_candidates(repaired, instance, context=context)
        if not candidates and context is not None and context.candidate_neighbor_size is not None:
            context.profiler.count("repair_unrestricted_fallbacks")
            candidates = _generate_candidates(repaired, instance, context=None)
        selected = selector(candidates)
        if selected is None:
            return _finalize_repair(repaired, instance, operator_name)
        repaired = _apply_insertion(repaired, selected)

    return _finalize_repair(repaired, instance, operator_name)


def _generate_candidates(
    state: ALNSState,
    instance: VRPTWInstance,
    *,
    context: ALNSContext | None,
) -> list[_InsertionCandidate]:
    candidates: list[_InsertionCandidate] = []
    for customer_id in sorted(state.unassigned):
        route_indexes = _candidate_route_indexes(customer_id, state, context)
        if context is not None:
            context.profiler.count("repair_customers_considered")
            context.profiler.count("repair_candidate_routes_considered", len(route_indexes))
        for route_index in route_indexes:
            route_ids = state.routes[route_index]
            for position in range(len(route_ids) + 1):
                if context is not None:
                    context.profiler.count("repair_candidate_positions_evaluated")
                delta = _insertion_delta_cost(
                    route_ids,
                    customer_id,
                    position,
                    instance,
                    route_index=route_index,
                    context=context,
                )
                if delta is None:
                    continue
                if context is not None:
                    context.profiler.count("repair_candidates_feasible")
                candidate_ids = (
                    *route_ids[:position],
                    customer_id,
                    *route_ids[position:],
                )
                candidates.append(
                    _InsertionCandidate(
                        customer_id=customer_id,
                        route_index=route_index,
                        position=position,
                        route_ids=candidate_ids,
                        delta_cost=delta,
                        score=delta,
                    )
                )

        if len(state.routes) < instance.vehicle.count:
            result = _evaluate_route(
                (customer_id,),
                instance,
                vehicle_id=len(state.routes),
                context=context,
            )
            if result.feasible:
                if context is not None:
                    context.profiler.count("repair_new_route_candidates_feasible")
                candidates.append(
                    _InsertionCandidate(
                        customer_id=customer_id,
                        route_index=None,
                        position=0,
                        route_ids=(customer_id,),
                        delta_cost=result.distance,
                        score=result.distance,
                    )
                )
    return candidates


def _candidate_route_indexes(
    customer_id: int,
    state: ALNSState,
    context: ALNSContext | None,
) -> tuple[int, ...]:
    if context is None or context.candidate_neighbor_size is None:
        return tuple(range(len(state.routes)))

    neighbor_ids = set(
        context.nearest_neighbors.nearest(customer_id, context.candidate_neighbor_size)
    )
    route_indexes = tuple(
        route_index
        for route_index, route_ids in enumerate(state.routes)
        if any(route_customer_id in neighbor_ids for route_customer_id in route_ids)
    )
    if route_indexes:
        context.profiler.count("repair_restricted_route_sets")
        return route_indexes
    return tuple(range(len(state.routes)))


def _insertion_delta_cost(
    route_customer_ids: tuple[int, ...],
    customer_id: int,
    position: int,
    instance: VRPTWInstance,
    *,
    route_index: int,
    context: ALNSContext | None,
) -> float | None:
    if position < 0 or position > len(route_customer_ids):
        raise ValueError("position must be within the route insertion range")
    inserted_ids = (
        *route_customer_ids[:position],
        customer_id,
        *route_customer_ids[position:],
    )
    base = _evaluate_route(
        route_customer_ids,
        instance,
        vehicle_id=route_index,
        context=context,
    )
    inserted = _evaluate_route(
        inserted_ids,
        instance,
        vehicle_id=route_index,
        context=context,
    )
    if not inserted.feasible:
        return None
    return inserted.distance - base.distance


def _evaluate_route(
    route_customer_ids: tuple[int, ...],
    instance: VRPTWInstance,
    *,
    vehicle_id: int,
    context: ALNSContext | None,
) -> InsertionResult:
    if context is None:
        return evaluate_route(route_customer_ids, instance, vehicle_id=vehicle_id)
    return context.route_cache.evaluate(
        route_customer_ids,
        instance,
        vehicle_id=vehicle_id,
        profiler=context.profiler,
    )


def _select_cheapest(candidates: list[_InsertionCandidate]) -> _InsertionCandidate | None:
    if not candidates:
        return None
    return min(
        candidates,
        key=lambda candidate: (
            candidate.score,
            candidate.customer_id,
            candidate.route_index is None,
            -1 if candidate.route_index is None else candidate.route_index,
            candidate.position,
        ),
    )


def _select_regret(
    candidates: list[_InsertionCandidate],
    *,
    regret_k: int,
) -> _InsertionCandidate | None:
    if not candidates:
        return None
    by_customer: dict[int, list[_InsertionCandidate]] = {}
    for candidate in candidates:
        by_customer.setdefault(candidate.customer_id, []).append(candidate)

    regret_choices: list[tuple[float, float, int, _InsertionCandidate]] = []
    for customer_id, customer_candidates in by_customer.items():
        ordered = sorted(customer_candidates, key=lambda candidate: candidate.delta_cost)
        best = ordered[0]
        if len(ordered) >= regret_k:
            regret = ordered[regret_k - 1].delta_cost - best.delta_cost
        else:
            regret = float("inf")
        regret_choices.append((regret, best.delta_cost, customer_id, best))

    return max(regret_choices, key=lambda item: (item[0], -item[1], -item[2]))[3]


def _select_time_window_priority(
    candidates: list[_InsertionCandidate],
    instance: VRPTWInstance,
) -> _InsertionCandidate | None:
    if not candidates:
        return None
    customer_by_id = {customer.id: customer for customer in instance.customers}
    return min(
        candidates,
        key=lambda candidate: (
            customer_by_id[candidate.customer_id].due_time
            - customer_by_id[candidate.customer_id].ready_time,
            customer_by_id[candidate.customer_id].due_time,
            candidate.delta_cost,
            candidate.customer_id,
        ),
    )


def _select_noise(
    candidates: list[_InsertionCandidate],
    rng: random.Random,
) -> _InsertionCandidate | None:
    if not candidates:
        return None
    max_delta = max((candidate.delta_cost for candidate in candidates), default=0.0)
    noise_scale = max(1.0, max_delta) * 0.05
    noisy = [
        (
            candidate.delta_cost + rng.uniform(0.0, noise_scale),
            candidate.customer_id,
            candidate,
        )
        for candidate in candidates
    ]
    return min(noisy, key=lambda item: (item[0], item[1]))[2]


def _apply_insertion(state: ALNSState, candidate: _InsertionCandidate) -> ALNSState:
    routes = list(state.routes)
    if candidate.route_index is None:
        routes.append(candidate.route_ids)
    else:
        routes[candidate.route_index] = candidate.route_ids

    inserted_customers = list(state.metadata.get("inserted_customers", []))
    inserted_customers.append(candidate.customer_id)
    return state.copy_with(
        routes=tuple(routes),
        unassigned=state.unassigned - {candidate.customer_id},
        cost=float("inf"),
        feasible=False,
        metadata={
            **state.metadata,
            "inserted_customers": inserted_customers,
        },
    )


def _finalize_repair(
    state: ALNSState,
    instance: VRPTWInstance,
    operator_name: str,
) -> ALNSState:
    solution = state.to_solution(instance, solver_name=operator_name)
    return state.copy_with(
        cost=solution.objective if solution.feasible else float("inf"),
        feasible=solution.feasible,
        metadata={
            **state.metadata,
            "last_repair": operator_name,
            "remaining_unassigned": sorted(state.unassigned),
            "feasibility_violations": solution.metadata["feasibility_violations"],
        },
    )
