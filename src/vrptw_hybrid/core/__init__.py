"""Core VRPTW domain models and shared computations."""

from vrptw_hybrid.core.checker import FeasibilityReport, check_solution
from vrptw_hybrid.core.models import (
    Customer,
    Route,
    RouteStop,
    Solution,
    VehicleSpec,
    VRPTWInstance,
    validate_square_matrix,
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
    "validate_square_matrix",
]
