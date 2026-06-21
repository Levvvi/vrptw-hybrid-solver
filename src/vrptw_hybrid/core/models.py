"""Unified data models for VRPTW instances and solver outputs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
from numpy.typing import NDArray

FloatMatrix = NDArray[np.float64]


@dataclass(frozen=True, slots=True)
class Customer:
    id: int
    x: float
    y: float
    demand: int
    ready_time: float
    due_time: float
    service_time: float
    lat: float | None = None
    lon: float | None = None

    def __post_init__(self) -> None:
        if self.demand < 0:
            raise ValueError(f"Customer {self.id} demand must be non-negative")
        if self.ready_time > self.due_time:
            raise ValueError(f"Customer {self.id} ready_time cannot exceed due_time")
        if self.service_time < 0:
            raise ValueError(f"Customer {self.id} service_time must be non-negative")


@dataclass(frozen=True, slots=True)
class VehicleSpec:
    capacity: int
    count: int
    fixed_cost: float = 0.0

    def __post_init__(self) -> None:
        if self.capacity <= 0:
            raise ValueError("Vehicle capacity must be positive")
        if self.count < 0:
            raise ValueError("Vehicle count must be non-negative")
        if self.fixed_cost < 0:
            raise ValueError("Vehicle fixed_cost must be non-negative")


@dataclass(frozen=True, slots=True)
class VRPTWInstance:
    name: str
    depot: Customer
    customers: tuple[Customer, ...]
    vehicle: VehicleSpec
    distance_matrix: FloatMatrix
    time_matrix: FloatMatrix
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        customers = tuple(self.customers)
        object.__setattr__(self, "customers", customers)
        object.__setattr__(self, "metadata", dict(self.metadata))

        customer_ids = [customer.id for customer in customers]
        if self.depot.id in customer_ids:
            raise ValueError("Depot id must not appear in customers")
        if len(customer_ids) != len(set(customer_ids)):
            raise ValueError("Customer ids must be unique")

        expected_size = len(customers) + 1
        distance_matrix = np.asarray(self.distance_matrix, dtype=float)
        time_matrix = np.asarray(self.time_matrix, dtype=float)
        validate_square_matrix(distance_matrix, expected_size, "distance_matrix")
        validate_square_matrix(time_matrix, expected_size, "time_matrix")

        object.__setattr__(self, "distance_matrix", distance_matrix)
        object.__setattr__(self, "time_matrix", time_matrix)

    @property
    def node_count(self) -> int:
        return len(self.customers) + 1

    @property
    def nodes(self) -> tuple[Customer, ...]:
        return (self.depot, *self.customers)

    @property
    def customer_ids(self) -> tuple[int, ...]:
        return tuple(customer.id for customer in self.customers)


@dataclass(frozen=True, slots=True)
class RouteStop:
    customer_id: int
    arrival_time: float
    start_service_time: float
    departure_time: float
    load_after: int

    def __post_init__(self) -> None:
        if self.arrival_time < 0:
            raise ValueError("RouteStop arrival_time must be non-negative")
        if self.start_service_time < self.arrival_time:
            raise ValueError("RouteStop start_service_time cannot precede arrival_time")
        if self.departure_time < self.start_service_time:
            raise ValueError("RouteStop departure_time cannot precede start_service_time")
        if self.load_after < 0:
            raise ValueError("RouteStop load_after must be non-negative")


@dataclass(frozen=True, slots=True)
class Route:
    vehicle_id: int
    stops: tuple[RouteStop, ...]
    distance: float
    duration: float
    load: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "stops", tuple(self.stops))
        if self.vehicle_id < 0:
            raise ValueError("Route vehicle_id must be non-negative")
        if self.distance < 0:
            raise ValueError("Route distance must be non-negative")
        if self.duration < 0:
            raise ValueError("Route duration must be non-negative")
        if self.load < 0:
            raise ValueError("Route load must be non-negative")


@dataclass(frozen=True, slots=True)
class Solution:
    instance_name: str
    solver_name: str
    routes: tuple[Route, ...]
    objective: float
    vehicles_used: int
    total_distance: float
    total_duration: float
    feasible: bool
    runtime_sec: float
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "routes", tuple(self.routes))
        object.__setattr__(self, "metadata", dict(self.metadata))
        if self.vehicles_used < 0:
            raise ValueError("Solution vehicles_used must be non-negative")
        if self.total_distance < 0:
            raise ValueError("Solution total_distance must be non-negative")
        if self.total_duration < 0:
            raise ValueError("Solution total_duration must be non-negative")
        if self.runtime_sec < 0:
            raise ValueError("Solution runtime_sec must be non-negative")


def validate_square_matrix(matrix: NDArray[Any], expected_size: int, name: str) -> None:
    if matrix.ndim != 2:
        raise ValueError(f"{name} must be a 2D matrix")
    expected_shape = (expected_size, expected_size)
    if matrix.shape != expected_shape:
        raise ValueError(f"{name} must be shape {expected_shape}, got {matrix.shape}")
    if not np.isfinite(matrix).all():
        raise ValueError(f"{name} must contain only finite values")
