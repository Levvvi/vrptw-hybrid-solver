"""Run a small ALNS profiling smoke test."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from vrptw_hybrid.core.models import Solution
from vrptw_hybrid.data.solomon import parse_solomon
from vrptw_hybrid.solvers.alns.operator_filters import (
    filter_destroy_operators,
    filter_repair_operators,
)
from vrptw_hybrid.solvers.alns.solver import ALNSSolver
from vrptw_hybrid.utils.config import load_config


def main() -> None:
    parser = argparse.ArgumentParser(description="Profile ALNS on one Solomon instance.")
    parser.add_argument("--instance", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=Path("configs/default.yaml"))
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--max-iterations", type=int, default=None)
    parser.add_argument("--time-limit", type=float, default=None)
    parser.add_argument("--limit-customers", type=int, default=None)
    args = parser.parse_args()

    config = load_config(args.config)
    solution = _run_profile(config, args)
    summary = {
        "instance": solution.instance_name,
        "solver": solution.solver_name,
        "ablation": solution.metadata.get("ablation"),
        "seed": solution.metadata.get("seed"),
        "feasible": solution.feasible,
        "objective": solution.objective,
        "vehicles_used": solution.vehicles_used,
        "total_distance": solution.total_distance,
        "runtime_sec": solution.runtime_sec,
        "iterations": solution.metadata.get("iterations"),
        "candidate_neighbor_size": solution.metadata.get("candidate_neighbor_size"),
        "profiler": solution.metadata.get("profiler", {}),
    }
    print(json.dumps(summary, indent=2, sort_keys=True))


def _run_profile(config: dict[str, Any], args: argparse.Namespace) -> Solution:
    instance = parse_solomon(args.instance, limit_customers=args.limit_customers)
    solver_config = config.get("solver", {})
    objective_config = config.get("objective", {})
    alns_config = config.get("alns", {})
    ablation_config = config.get("ablation", {})
    if not isinstance(solver_config, dict):
        solver_config = {}
    if not isinstance(objective_config, dict):
        objective_config = {}
    if not isinstance(alns_config, dict):
        alns_config = {}
    if not isinstance(ablation_config, dict):
        ablation_config = {}

    solver = ALNSSolver(
        max_iterations=args.max_iterations
        if args.max_iterations is not None
        else int(solver_config.get("max_iterations", 1000)),
        time_limit_sec=args.time_limit
        if args.time_limit is not None
        else float(solver_config.get("time_limit_sec", 60.0)),
        vehicle_weight=float(objective_config.get("vehicle_weight", 100000.0)),
        seed=args.seed if args.seed is not None else int(config.get("seed", 42)),
        destroy_operators=filter_destroy_operators(
            enabled_names=_optional_names(alns_config.get("enabled_destroy_operators")),
            disabled_names=_optional_names(alns_config.get("disabled_destroy_operators")),
        ),
        repair_operators=filter_repair_operators(
            enabled_names=_optional_names(alns_config.get("enabled_repair_operators")),
            disabled_names=_optional_names(alns_config.get("disabled_repair_operators")),
        ),
        selector_name=str(alns_config.get("selector", "uniform")),
        segment_length=int(alns_config.get("segment_length", 100)),
        reaction_factor=float(alns_config.get("reaction_factor", 0.2)),
        exploration_floor=float(alns_config.get("exploration_floor", 0.05)),
        temperature=float(alns_config.get("temperature", 1.0)),
        decay=float(alns_config.get("decay", 0.8)),
        memory_size=int(alns_config.get("memory_size", 50)),
        use_pair_memory=_bool_config(alns_config.get("use_pair_memory", True)),
        use_diversity_bonus=_bool_config(alns_config.get("use_diversity_bonus", True)),
        ablation_name=str(ablation_config.get("name", "default")),
        candidate_neighbor_size=int(alns_config.get("candidate_neighbor_size", 0) or 0),
    )
    return solver.solve(instance)


def _optional_names(value: object) -> tuple[str, ...] | None:
    if value is None:
        return None
    if isinstance(value, str):
        return (value,)
    if isinstance(value, list | tuple):
        return tuple(str(item) for item in value)
    raise TypeError("operator filters must be strings or lists of strings")


def _bool_config(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    raise TypeError("boolean config values must be booleans")


if __name__ == "__main__":
    main()
