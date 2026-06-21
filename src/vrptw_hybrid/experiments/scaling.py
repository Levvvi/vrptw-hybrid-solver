"""Scaling experiment helpers for synthetic and Solomon-sized VRPTW runs."""

from __future__ import annotations

import random
from dataclasses import dataclass
from math import ceil
from pathlib import Path
from time import perf_counter
from typing import Any

from vrptw_hybrid.core.models import Customer, VehicleSpec, VRPTWInstance
from vrptw_hybrid.core.solution_io import save_metrics_csv
from vrptw_hybrid.data.distance_matrix import euclidean_distance_matrix
from vrptw_hybrid.data.solomon import parse_solomon
from vrptw_hybrid.solvers.dispatch import run_solver_from_config


@dataclass(frozen=True, slots=True)
class ScalingResult:
    csv_path: Path
    rows: tuple[dict[str, Any], ...]


def generate_synthetic_instance(
    size: int,
    *,
    seed: int = 42,
) -> VRPTWInstance:
    """Generate a reproducible synthetic VRPTW instance for scaling smoke tests."""

    if size <= 0:
        raise ValueError("size must be positive")
    rng = random.Random(seed + size)
    depot = Customer(
        id=0,
        x=50.0,
        y=50.0,
        demand=0,
        ready_time=0.0,
        due_time=100000.0,
        service_time=0.0,
    )
    customers = tuple(
        Customer(
            id=customer_id,
            x=rng.uniform(0.0, 100.0),
            y=rng.uniform(0.0, 100.0),
            demand=rng.randint(1, 5),
            ready_time=0.0,
            due_time=100000.0,
            service_time=1.0,
        )
        for customer_id in range(1, size + 1)
    )
    capacity = 50
    total_demand = sum(customer.demand for customer in customers)
    vehicle_count = max(1, ceil(total_demand / capacity) + 5)
    points = [(node.x, node.y) for node in (depot, *customers)]
    matrix = euclidean_distance_matrix(points)
    return VRPTWInstance(
        name=f"SYNTHETIC_{size}",
        depot=depot,
        customers=customers,
        vehicle=VehicleSpec(capacity=capacity, count=vehicle_count),
        distance_matrix=matrix,
        time_matrix=matrix.copy(),
        metadata={"format": "synthetic_scaling", "size": size, "seed": seed},
    )


def run_scaling_experiment(
    *,
    sizes: tuple[int, ...],
    solvers: tuple[str, ...],
    output_csv: str | Path,
    seed: int = 42,
    max_iterations: int = 20,
    small_time_limit_sec: float = 30.0,
    large_time_limit_sec: float = 120.0,
    large_threshold: int = 500,
    instance_template: str | None = None,
) -> ScalingResult:
    """Run a scaling smoke experiment and write one CSV row per size/solver."""

    rows: list[dict[str, Any]] = []
    for size in sizes:
        instance = _load_or_generate_instance(size, seed, instance_template)
        time_limit = large_time_limit_sec if size >= large_threshold else small_time_limit_sec
        for solver in solvers:
            rows.append(
                _run_one_scaling_case(
                    instance=instance,
                    size=size,
                    solver=solver,
                    seed=seed,
                    max_iterations=max_iterations,
                    time_limit=time_limit,
                )
            )
    csv_path = save_metrics_csv(rows, output_csv)
    return ScalingResult(csv_path=csv_path, rows=tuple(rows))


def _run_one_scaling_case(
    *,
    instance: VRPTWInstance,
    size: int,
    solver: str,
    seed: int,
    max_iterations: int,
    time_limit: float,
) -> dict[str, Any]:
    base_row = {
        "scale": size,
        "instance": instance.name,
        "solver": solver,
        "seed": seed,
        "time_limit_sec": time_limit,
        "max_iterations": max_iterations,
    }
    config = _scaling_config(max_iterations=max_iterations)
    start_time = perf_counter()
    try:
        solution = run_solver_from_config(
            solver_name=solver,
            instance=instance,
            config=config,
            seed=seed,
            time_limit=time_limit,
            max_iterations=max_iterations,
        )
        elapsed = perf_counter() - start_time
        status = "timeout" if elapsed >= time_limit else "ok"
        return {
            **base_row,
            "vehicles": solution.vehicles_used,
            "distance": solution.total_distance,
            "cost": solution.objective,
            "runtime_sec": solution.runtime_sec,
            "feasible": solution.feasible,
            "status": status,
            "error": "",
        }
    except Exception as exc:
        return {
            **base_row,
            "vehicles": "",
            "distance": "",
            "cost": "",
            "runtime_sec": perf_counter() - start_time,
            "feasible": False,
            "status": "error",
            "error": str(exc),
        }


def _load_or_generate_instance(
    size: int,
    seed: int,
    instance_template: str | None,
) -> VRPTWInstance:
    if instance_template:
        path = Path(instance_template.format(size=size))
        return parse_solomon(path, limit_customers=size)
    return generate_synthetic_instance(size, seed=seed)


def _scaling_config(*, max_iterations: int) -> dict[str, Any]:
    return {
        "ablation": {"name": "scaling"},
        "objective": {"vehicle_weight": 100000.0},
        "solver": {
            "time_limit_sec": 60.0,
            "max_iterations": max_iterations,
        },
        "alns": {
            "selector": "mosade",
            "segment_length": 10,
            "reaction_factor": 0.3,
            "exploration_floor": 0.05,
            "temperature": 1.0,
            "decay": 0.8,
            "memory_size": 50,
            "candidate_neighbor_size": 25,
            "use_pair_memory": True,
            "use_diversity_bonus": True,
            "disabled_destroy_operators": [],
            "disabled_repair_operators": [],
        },
    }
