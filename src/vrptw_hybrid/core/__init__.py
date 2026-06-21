"""Core VRPTW domain models and shared computations."""

from vrptw_hybrid.core.checker import FeasibilityReport, check_solution
from vrptw_hybrid.core.metrics import compute_solution_metrics, gap_percent
from vrptw_hybrid.core.models import (
    Customer,
    Route,
    RouteStop,
    Solution,
    VehicleSpec,
    VRPTWInstance,
    validate_square_matrix,
)
from vrptw_hybrid.core.objective import composite_objective, compute_route_distance
from vrptw_hybrid.core.solution_io import (
    load_solution_json,
    save_metrics_csv,
    save_solution_json,
    solution_from_dict,
    solution_to_dict,
)

__all__ = [
    "Customer",
    "FeasibilityReport",
    "Route",
    "RouteStop",
    "Solution",
    "VRPTWInstance",
    "VehicleSpec",
    "check_solution",
    "composite_objective",
    "compute_route_distance",
    "compute_solution_metrics",
    "gap_percent",
    "load_solution_json",
    "save_metrics_csv",
    "save_solution_json",
    "solution_from_dict",
    "solution_to_dict",
    "validate_square_matrix",
]
