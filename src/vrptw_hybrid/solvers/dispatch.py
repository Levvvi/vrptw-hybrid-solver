"""Solver dispatch helpers shared by CLI and experiment runner."""

from __future__ import annotations

from typing import Any

from vrptw_hybrid.core.models import Solution, VRPTWInstance
from vrptw_hybrid.solvers.alns.operator_filters import (
    filter_destroy_operators,
    filter_repair_operators,
)
from vrptw_hybrid.solvers.alns.solver import ALNSSolver
from vrptw_hybrid.solvers.exact_cp_sat import CPSATRuntimeError, CPSATVRPTWSolver
from vrptw_hybrid.solvers.greedy import GreedySolver
from vrptw_hybrid.solvers.ortools_routing import ORToolsRoutingSolver


class SolverDispatchError(ValueError):
    """Raised when a solver run cannot be configured or executed."""


def run_solver_from_config(
    *,
    solver_name: str,
    instance: VRPTWInstance,
    config: dict[str, Any],
    seed: int | None,
    time_limit: float | None = None,
    max_iterations: int | None = None,
) -> Solution:
    """Run one configured solver on an instance."""

    solver_key = solver_name.lower()
    solver_config = config.get("solver", {})
    objective_config = config.get("objective", {})
    if not isinstance(solver_config, dict):
        solver_config = {}
    if not isinstance(objective_config, dict):
        objective_config = {}

    vehicle_weight = float(objective_config.get("vehicle_weight", 100000.0))
    default_time_limit = float(solver_config.get("time_limit_sec", 60.0))
    effective_time_limit = default_time_limit if time_limit is None else time_limit
    effective_max_iterations = int(solver_config.get("max_iterations", 1000))
    if max_iterations is not None:
        effective_max_iterations = max_iterations
    alns_config = _mapping(config.get("alns", {}))
    ablation_config = _mapping(config.get("ablation", {}))
    ablation_name = str(ablation_config.get("name", "default"))
    selector_name = str(alns_config.get("selector", "uniform"))
    segment_length = int(alns_config.get("segment_length", 100))
    reaction_factor = float(alns_config.get("reaction_factor", 0.2))
    exploration_floor = float(alns_config.get("exploration_floor", 0.05))
    temperature = float(alns_config.get("temperature", 1.0))
    decay = float(alns_config.get("decay", 0.8))
    memory_size = int(alns_config.get("memory_size", 50))
    candidate_neighbor_size = int(alns_config.get("candidate_neighbor_size", 0) or 0)
    use_pair_memory = _bool_config(
        alns_config.get("use_pair_memory", True),
        "alns.use_pair_memory",
    )
    use_diversity_bonus = _bool_config(
        alns_config.get("use_diversity_bonus", True),
        "alns.use_diversity_bonus",
    )

    if solver_key == "greedy":
        return _with_ablation(
            GreedySolver(vehicle_weight=vehicle_weight, seed=seed).solve(instance, seed=seed),
            ablation_name,
        )
    if solver_key in {
        "alns",
        "alns_uniform",
        "alns_roulette",
        "alns_mosade",
        "alns_mosade_adaptive",
    }:
        try:
            destroy_operators = filter_destroy_operators(
                enabled_names=_optional_name_list(
                    alns_config.get("enabled_destroy_operators"),
                    "alns.enabled_destroy_operators",
                ),
                disabled_names=_optional_name_list(
                    alns_config.get("disabled_destroy_operators"),
                    "alns.disabled_destroy_operators",
                ),
            )
            repair_operators = filter_repair_operators(
                enabled_names=_optional_name_list(
                    alns_config.get("enabled_repair_operators"),
                    "alns.enabled_repair_operators",
                ),
                disabled_names=_optional_name_list(
                    alns_config.get("disabled_repair_operators"),
                    "alns.disabled_repair_operators",
                ),
            )
        except ValueError as exc:
            raise SolverDispatchError(str(exc)) from exc

        effective_selector_name = _selector_name_from_solver_alias(solver_key, selector_name)
        return _with_ablation(
            ALNSSolver(
                max_iterations=effective_max_iterations,
                time_limit_sec=effective_time_limit,
                vehicle_weight=vehicle_weight,
                seed=seed,
                destroy_operators=destroy_operators,
                repair_operators=repair_operators,
                selector_name=effective_selector_name,
                segment_length=segment_length,
                reaction_factor=reaction_factor,
                exploration_floor=exploration_floor,
                temperature=temperature,
                decay=decay,
                memory_size=memory_size,
                use_pair_memory=use_pair_memory,
                use_diversity_bonus=use_diversity_bonus,
                ablation_name=ablation_name,
                candidate_neighbor_size=candidate_neighbor_size,
            ).solve(instance, seed=seed),
            ablation_name,
        )
    if solver_key in {"ortools", "ortools_routing"}:
        return _with_ablation(
            ORToolsRoutingSolver(
                time_limit_sec=effective_time_limit,
                vehicle_weight=vehicle_weight,
            ).solve(instance, seed=seed),
            ablation_name,
        )
    if solver_key in {"cp_sat", "exact_cp_sat"}:
        try:
            return _with_ablation(
                CPSATVRPTWSolver(
                    time_limit_sec=effective_time_limit,
                    vehicle_weight=vehicle_weight,
                ).solve(instance, seed=seed),
                ablation_name,
            )
        except CPSATRuntimeError as exc:
            raise SolverDispatchError(str(exc)) from exc
    raise SolverDispatchError(f"Unknown solver: {solver_name}")


def _mapping(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _optional_name_list(value: object, field_name: str) -> tuple[str, ...] | None:
    if value is None:
        return None
    if isinstance(value, str):
        return (value,)
    if isinstance(value, list | tuple):
        return tuple(str(item) for item in value)
    raise SolverDispatchError(f"{field_name} must be a string or list of strings")


def _bool_config(value: object, field_name: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    raise SolverDispatchError(f"{field_name} must be a boolean")


def _selector_name_from_solver_alias(solver_key: str, configured_selector: str) -> str:
    if solver_key == "alns_uniform":
        return "uniform"
    if solver_key == "alns_roulette":
        return "roulette"
    if solver_key in {"alns_mosade", "alns_mosade_adaptive"}:
        return "mosade"
    return configured_selector


def _with_ablation(solution: Solution, ablation_name: str) -> Solution:
    return Solution(
        instance_name=solution.instance_name,
        solver_name=solution.solver_name,
        routes=solution.routes,
        objective=solution.objective,
        vehicles_used=solution.vehicles_used,
        total_distance=solution.total_distance,
        total_duration=solution.total_duration,
        feasible=solution.feasible,
        runtime_sec=solution.runtime_sec,
        metadata={**solution.metadata, "ablation": ablation_name},
    )
