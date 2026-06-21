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
    "validate_square_matrix",
]
