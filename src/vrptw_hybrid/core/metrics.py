"""Solution-level metrics and comparison helpers."""

from __future__ import annotations

from typing import TypeAlias

from vrptw_hybrid.core.models import Solution, VRPTWInstance
from vrptw_hybrid.core.objective import composite_objective, compute_route_distance

MetricValue: TypeAlias = bool | int | float


def compute_solution_metrics(
    solution: Solution,
    instance: VRPTWInstance,
    *,
    vehicle_weight: float = 100000.0,
) -> dict[str, MetricValue]:
    """Compute canonical metrics from a solution and its instance."""

    vehicles_used = sum(1 for route in solution.routes if route.stops)
    total_distance = sum(compute_route_distance(route, instance) for route in solution.routes)
    total_duration = sum(route.duration for route in solution.routes)
    return {
        "vehicles_used": vehicles_used,
        "total_distance": total_distance,
        "total_duration": total_duration,
        "composite_objective": composite_objective(
            vehicles_used=vehicles_used,
            total_distance=total_distance,
            vehicle_weight=vehicle_weight,
        ),
        "feasible": solution.feasible,
        "runtime_sec": solution.runtime_sec,
    }


def gap_percent(value: float, reference: float | None) -> float | None:
    """Return percentage gap to a reference value, or None when undefined."""

    if reference is None or reference == 0:
        return None
    return (value - reference) / abs(reference) * 100.0
