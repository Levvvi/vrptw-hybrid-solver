"""Shared runtime context for ALNS operators."""

from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter
from typing import Any

from vrptw_hybrid.core.models import VRPTWInstance
from vrptw_hybrid.solvers.alns.route_eval import InsertionResult, evaluate_route


@dataclass(slots=True)
class ALNSProfiler:
    """Small counter/timer profiler for ALNS smoke runs."""

    counters: dict[str, int] = field(default_factory=dict)
    timings_sec: dict[str, float] = field(default_factory=dict)

    def count(self, name: str, value: int = 1) -> None:
        self.counters[name] = self.counters.get(name, 0) + value

    def add_time(self, name: str, elapsed_sec: float) -> None:
        self.timings_sec[name] = self.timings_sec.get(name, 0.0) + elapsed_sec

    def snapshot(self) -> dict[str, Any]:
        return {
            "counters": dict(sorted(self.counters.items())),
            "timings_sec": {
                key: round(value, 6) for key, value in sorted(self.timings_sec.items())
            },
        }


@dataclass(frozen=True, slots=True)
class NearestNeighborCache:
    """Customer nearest-neighbor lookup built from the instance distance matrix."""

    neighbors_by_customer: dict[int, tuple[int, ...]]

    @classmethod
    def build(cls, instance: VRPTWInstance) -> NearestNeighborCache:
        index_by_id = {node.id: index for index, node in enumerate(instance.nodes)}
        neighbors_by_customer: dict[int, tuple[int, ...]] = {}
        customer_ids = tuple(customer.id for customer in instance.customers)
        for customer_id in customer_ids:
            customer_index = index_by_id[customer_id]
            ordered = sorted(
                (other_id for other_id in customer_ids if other_id != customer_id),
                key=lambda other_id: (
                    float(instance.distance_matrix[customer_index, index_by_id[other_id]]),
                    other_id,
                ),
            )
            neighbors_by_customer[customer_id] = tuple(ordered)
        return cls(neighbors_by_customer)

    def nearest(self, customer_id: int, limit: int | None = None) -> tuple[int, ...]:
        neighbors = self.neighbors_by_customer.get(customer_id, ())
        if limit is None or limit <= 0:
            return neighbors
        return neighbors[:limit]


@dataclass(slots=True)
class RouteEvaluationCache:
    """Memoize immutable route evaluations by customer sequence and vehicle id."""

    _cache: dict[tuple[tuple[int, ...], int], InsertionResult] = field(default_factory=dict)

    def evaluate(
        self,
        route_customer_ids: tuple[int, ...],
        instance: VRPTWInstance,
        *,
        vehicle_id: int = 0,
        profiler: ALNSProfiler | None = None,
    ) -> InsertionResult:
        key = (tuple(route_customer_ids), vehicle_id)
        if key in self._cache:
            if profiler is not None:
                profiler.count("route_eval_cache_hits")
            return self._cache[key]

        if profiler is not None:
            profiler.count("route_eval_cache_misses")
        result = evaluate_route(route_customer_ids, instance, vehicle_id=vehicle_id)
        self._cache[key] = result
        return result

    def snapshot(self) -> dict[str, int]:
        return {"entries": len(self._cache)}


@dataclass(slots=True)
class ALNSContext:
    """Shared caches and tuning knobs for one ALNS solve."""

    nearest_neighbors: NearestNeighborCache
    route_cache: RouteEvaluationCache
    profiler: ALNSProfiler
    candidate_neighbor_size: int | None = None

    @classmethod
    def from_instance(
        cls,
        instance: VRPTWInstance,
        *,
        candidate_neighbor_size: int | None = None,
    ) -> ALNSContext:
        normalized_neighbor_size = candidate_neighbor_size
        if normalized_neighbor_size is not None and normalized_neighbor_size <= 0:
            normalized_neighbor_size = None
        return cls(
            nearest_neighbors=NearestNeighborCache.build(instance),
            route_cache=RouteEvaluationCache(),
            profiler=ALNSProfiler(),
            candidate_neighbor_size=normalized_neighbor_size,
        )

    def time_block(self, name: str) -> _ProfileTimer:
        return _ProfileTimer(self.profiler, name)

    def snapshot(self) -> dict[str, Any]:
        return {
            "candidate_neighbor_size": self.candidate_neighbor_size,
            "route_cache": self.route_cache.snapshot(),
            **self.profiler.snapshot(),
        }


@dataclass(slots=True)
class _ProfileTimer:
    profiler: ALNSProfiler
    name: str
    start_time: float = 0.0

    def __enter__(self) -> None:
        self.start_time = perf_counter()

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.profiler.add_time(self.name, perf_counter() - self.start_time)
