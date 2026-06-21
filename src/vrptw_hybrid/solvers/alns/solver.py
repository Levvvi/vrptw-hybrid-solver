"""Basic ALNS solver with uniform random operator selection."""

from __future__ import annotations

import random
from collections.abc import Mapping
from time import perf_counter
from typing import Any

from vrptw_hybrid.core.models import Solution, VRPTWInstance
from vrptw_hybrid.solvers.alns.acceptance import AlwaysBetterAcceptance
from vrptw_hybrid.solvers.alns.destroy import DESTROY_OPERATORS, DestroyOperator
from vrptw_hybrid.solvers.alns.repair import REPAIR_OPERATORS, RepairOperator
from vrptw_hybrid.solvers.alns.selectors import (
    MOSADEInspiredSelector,
    OperatorEvent,
    OperatorSelector,
    RouletteWheelSelector,
    UniformSelector,
)
from vrptw_hybrid.solvers.alns.state import ALNSState
from vrptw_hybrid.solvers.base import BaseSolver
from vrptw_hybrid.solvers.greedy import solve_greedy


class ALNSSolver(BaseSolver):
    """Initial ALNS implementation using uniform random operator selection."""

    def __init__(
        self,
        *,
        max_iterations: int = 1000,
        time_limit_sec: float | None = None,
        destroy_fraction: float = 0.2,
        vehicle_weight: float = 100000.0,
        seed: int | None = None,
        destroy_operators: tuple[DestroyOperator, ...] = DESTROY_OPERATORS,
        repair_operators: tuple[RepairOperator, ...] = REPAIR_OPERATORS,
        selector: OperatorSelector | None = None,
        selector_name: str = "uniform",
        segment_length: int = 100,
        reaction_factor: float = 0.2,
        exploration_floor: float = 0.05,
        temperature: float = 1.0,
        decay: float = 0.8,
        memory_size: int = 50,
        use_pair_memory: bool = True,
        use_diversity_bonus: bool = True,
        ablation_name: str = "default",
    ) -> None:
        if max_iterations < 0:
            raise ValueError("max_iterations must be non-negative")
        if time_limit_sec is not None and time_limit_sec <= 0:
            raise ValueError("time_limit_sec must be positive when provided")
        if not 0 < destroy_fraction <= 1:
            raise ValueError("destroy_fraction must be in (0, 1]")
        if not destroy_operators:
            raise ValueError("at least one destroy operator is required")
        if not repair_operators:
            raise ValueError("at least one repair operator is required")

        self.max_iterations = max_iterations
        self.time_limit_sec = time_limit_sec
        self.destroy_fraction = destroy_fraction
        self.vehicle_weight = vehicle_weight
        self.seed = seed
        self.destroy_operators = destroy_operators
        self.repair_operators = repair_operators
        self.ablation_name = ablation_name
        self.selector = selector or _make_selector(
            selector_name=selector_name,
            destroy_operators=destroy_operators,
            repair_operators=repair_operators,
            segment_length=segment_length,
            reaction_factor=reaction_factor,
            exploration_floor=exploration_floor,
            temperature=temperature,
            decay=decay,
            memory_size=memory_size,
            use_pair_memory=use_pair_memory,
            use_diversity_bonus=use_diversity_bonus,
        )
        self.acceptance = AlwaysBetterAcceptance()

    def solve(
        self,
        instance: VRPTWInstance,
        config: Mapping[str, Any] | None = None,
        seed: int | None = None,
    ) -> Solution:
        """Run a basic ALNS search and return the best Solution found."""

        effective_seed = self.seed if seed is None else seed
        rng = random.Random(effective_seed)
        start_time = perf_counter()
        initial_solution = solve_greedy(
            instance,
            vehicle_weight=self.vehicle_weight,
            deterministic=True,
            seed=effective_seed,
        )
        current = ALNSState.from_solution(initial_solution)
        best = current
        best_iteration = 0
        history: list[dict[str, Any]] = []
        no_improvement_iterations = 0
        q = (
            max(1, round(len(instance.customers) * self.destroy_fraction))
            if instance.customers
            else 0
        )

        for iteration in range(1, self.max_iterations + 1):
            elapsed = perf_counter() - start_time
            if self.time_limit_sec is not None and elapsed >= self.time_limit_sec:
                break
            if q == 0:
                break

            destroy_operator = self.selector.select_destroy(rng)
            repair_operator = self.selector.select_repair(rng)
            destroyed = destroy_operator(current, instance, rng, q)
            candidate = repair_operator(destroyed, instance, rng)
            candidate_solution = candidate.to_solution(
                instance,
                solver_name="alns_candidate",
                vehicle_weight=self.vehicle_weight,
                runtime_sec=elapsed,
            )
            candidate_cost = (
                candidate_solution.objective if candidate_solution.feasible else float("inf")
            )
            accepted = (
                candidate_solution.feasible
                and self.acceptance.accept(current.cost, candidate_cost, rng)
            )
            new_best = candidate_solution.feasible and candidate_cost < best.cost
            delta_cost = (
                candidate_cost - current.cost if candidate_solution.feasible else float("inf")
            )
            event = OperatorEvent(
                destroy_name=destroy_operator.name,
                repair_name=repair_operator.name,
                accepted=accepted,
                new_best=new_best,
                delta_cost=delta_cost,
                feasible=candidate_solution.feasible,
            )
            self.selector.update(event)

            if accepted:
                current = candidate.copy_with(cost=candidate_cost, feasible=True)
            if new_best:
                best = candidate.copy_with(cost=candidate_cost, feasible=True)
                best_iteration = iteration
                no_improvement_iterations = 0
            else:
                no_improvement_iterations += 1

            history.append(
                {
                    "iteration": iteration,
                    "destroy": destroy_operator.name,
                    "repair": repair_operator.name,
                    "candidate_cost": candidate_cost,
                    "current_cost": current.cost,
                    "best_cost": best.cost,
                    "delta_cost": delta_cost,
                    "accepted": accepted,
                    "new_best": new_best,
                    "feasible": candidate_solution.feasible,
                    "no_improvement_iterations": no_improvement_iterations,
                    "selector_snapshot": self.selector.snapshot(),
                }
            )

        runtime_sec = perf_counter() - start_time
        best_solution = best.to_solution(
            instance,
            solver_name="alns",
            vehicle_weight=self.vehicle_weight,
            runtime_sec=runtime_sec,
        )
        return Solution(
            instance_name=best_solution.instance_name,
            solver_name=best_solution.solver_name,
            routes=best_solution.routes,
            objective=best_solution.objective,
            vehicles_used=best_solution.vehicles_used,
            total_distance=best_solution.total_distance,
            total_duration=best_solution.total_duration,
            feasible=best_solution.feasible,
            runtime_sec=best_solution.runtime_sec,
            metadata={
                **best_solution.metadata,
                "seed": effective_seed,
                "iterations": len(history),
                "max_iterations": self.max_iterations,
                "best_iteration": best_iteration,
                "history": history,
                "selector": self.selector.snapshot(),
                "destroy_fraction": self.destroy_fraction,
                "ablation": self.ablation_name,
                "destroy_operators": [operator.name for operator in self.destroy_operators],
                "repair_operators": [operator.name for operator in self.repair_operators],
            },
        )


def solve_alns(
    instance: VRPTWInstance,
    *,
    max_iterations: int = 1000,
    time_limit_sec: float | None = None,
    destroy_fraction: float = 0.2,
    vehicle_weight: float = 100000.0,
    seed: int | None = None,
    selector_name: str = "uniform",
    temperature: float = 1.0,
    decay: float = 0.8,
    memory_size: int = 50,
    use_pair_memory: bool = True,
    use_diversity_bonus: bool = True,
    ablation_name: str = "default",
) -> Solution:
    """Convenience wrapper around :class:`ALNSSolver`."""

    return ALNSSolver(
        max_iterations=max_iterations,
        time_limit_sec=time_limit_sec,
        destroy_fraction=destroy_fraction,
        vehicle_weight=vehicle_weight,
        seed=seed,
        selector_name=selector_name,
        temperature=temperature,
        decay=decay,
        memory_size=memory_size,
        use_pair_memory=use_pair_memory,
        use_diversity_bonus=use_diversity_bonus,
        ablation_name=ablation_name,
    ).solve(instance)


def _make_selector(
    *,
    selector_name: str,
    destroy_operators: tuple[DestroyOperator, ...],
    repair_operators: tuple[RepairOperator, ...],
    segment_length: int,
    reaction_factor: float,
    exploration_floor: float,
    temperature: float,
    decay: float,
    memory_size: int,
    use_pair_memory: bool,
    use_diversity_bonus: bool,
) -> OperatorSelector:
    selector_key = selector_name.lower()
    if selector_key in {"uniform", "uniform_random"}:
        return UniformSelector(destroy_operators, repair_operators)
    if selector_key in {"roulette", "roulette_wheel"}:
        return RouletteWheelSelector(
            destroy_operators,
            repair_operators,
            segment_length=segment_length,
            reaction_factor=reaction_factor,
            exploration_floor=exploration_floor,
        )
    if selector_key in {"mosade", "mosade_inspired", "adaptive"}:
        return MOSADEInspiredSelector(
            destroy_operators,
            repair_operators,
            temperature=temperature,
            decay=decay,
            memory_size=memory_size,
            exploration_floor=exploration_floor,
            use_pair_memory=use_pair_memory,
            use_diversity_bonus=use_diversity_bonus,
        )
    raise ValueError(f"Unknown ALNS selector: {selector_name}")
