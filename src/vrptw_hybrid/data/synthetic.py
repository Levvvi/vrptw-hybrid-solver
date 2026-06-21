"""Synthetic city VRPTW instance generation from graph nodes."""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from vrptw_hybrid.core.models import Customer, VehicleSpec, VRPTWInstance
from vrptw_hybrid.data.distance_matrix import euclidean_distance_matrix


@dataclass(frozen=True, slots=True)
class CityGenerationConfig:
    customer_count: int = 20
    vehicle_count: int = 5
    vehicle_capacity: int = 30
    demand_min: int = 1
    demand_max: int = 5
    service_time: float = 5.0
    time_window_width: float = 120.0
    horizon: float = 480.0
    seed: int = 42
    name: str = "synthetic_city"


def generate_city_vrptw_instance(
    graph: Any,
    config: CityGenerationConfig | None = None,
) -> VRPTWInstance:
    """Generate a reproducible city-style VRPTW instance from graph node coordinates."""

    cfg = config or CityGenerationConfig()
    _validate_config(cfg)
    nodes = _graph_nodes_with_coordinates(graph)
    if len(nodes) < cfg.customer_count + 1:
        raise ValueError("graph does not contain enough coordinate-bearing nodes")

    rng = random.Random(cfg.seed)
    sampled_nodes = rng.sample(nodes, cfg.customer_count + 1)
    depot_node = sampled_nodes[0]
    customer_nodes = sampled_nodes[1:]
    depot = Customer(
        id=0,
        x=depot_node.lon,
        y=depot_node.lat,
        demand=0,
        ready_time=0.0,
        due_time=cfg.horizon + cfg.time_window_width,
        service_time=0.0,
        lat=depot_node.lat,
        lon=depot_node.lon,
    )
    customers = tuple(
        _customer_from_node(index, node, cfg, rng)
        for index, node in enumerate(customer_nodes, start=1)
    )
    points = [(node.x, node.y) for node in (depot, *customers)]
    matrix = euclidean_distance_matrix(points)
    return VRPTWInstance(
        name=cfg.name,
        depot=depot,
        customers=customers,
        vehicle=VehicleSpec(capacity=cfg.vehicle_capacity, count=cfg.vehicle_count),
        distance_matrix=matrix,
        time_matrix=matrix.copy(),
        metadata={
            "format": "synthetic_city",
            "seed": cfg.seed,
            "customer_count": cfg.customer_count,
            "graph_node_ids": [depot_node.node_id, *(node.node_id for node in customer_nodes)],
        },
    )


def save_instance_json(instance: VRPTWInstance, path: str | Path) -> Path:
    """Save a VRPTWInstance as JSON for demos or fixtures."""

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(instance_to_dict(instance), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return output_path


def instance_to_dict(instance: VRPTWInstance) -> dict[str, Any]:
    """Convert a VRPTWInstance to a JSON-serializable dictionary."""

    return {
        "name": instance.name,
        "depot": _customer_to_dict(instance.depot),
        "customers": [_customer_to_dict(customer) for customer in instance.customers],
        "vehicle": {
            "capacity": instance.vehicle.capacity,
            "count": instance.vehicle.count,
            "fixed_cost": instance.vehicle.fixed_cost,
        },
        "distance_matrix": instance.distance_matrix.tolist(),
        "time_matrix": instance.time_matrix.tolist(),
        "metadata": dict(instance.metadata),
    }


@dataclass(frozen=True, slots=True)
class _GraphNode:
    node_id: Any
    lat: float
    lon: float


def _customer_from_node(
    customer_id: int,
    node: _GraphNode,
    cfg: CityGenerationConfig,
    rng: random.Random,
) -> Customer:
    ready_latest = max(0.0, cfg.horizon - cfg.time_window_width)
    ready_time = rng.uniform(0.0, ready_latest)
    return Customer(
        id=customer_id,
        x=node.lon,
        y=node.lat,
        demand=rng.randint(cfg.demand_min, cfg.demand_max),
        ready_time=ready_time,
        due_time=ready_time + cfg.time_window_width,
        service_time=cfg.service_time,
        lat=node.lat,
        lon=node.lon,
    )


def _graph_nodes_with_coordinates(graph: Any) -> list[_GraphNode]:
    nodes: list[_GraphNode] = []
    for node_id, data in graph.nodes(data=True):
        if "x" not in data or "y" not in data:
            continue
        nodes.append(_GraphNode(node_id=node_id, lon=float(data["x"]), lat=float(data["y"])))
    return nodes


def _validate_config(cfg: CityGenerationConfig) -> None:
    if cfg.customer_count <= 0:
        raise ValueError("customer_count must be positive")
    if cfg.vehicle_count <= 0:
        raise ValueError("vehicle_count must be positive")
    if cfg.vehicle_capacity <= 0:
        raise ValueError("vehicle_capacity must be positive")
    if cfg.demand_min < 0 or cfg.demand_max < cfg.demand_min:
        raise ValueError("demand range is invalid")
    if cfg.demand_max > cfg.vehicle_capacity:
        raise ValueError("demand_max must not exceed vehicle_capacity")
    if cfg.service_time < 0:
        raise ValueError("service_time must be non-negative")
    if cfg.time_window_width <= 0:
        raise ValueError("time_window_width must be positive")
    if cfg.horizon <= 0:
        raise ValueError("horizon must be positive")


def _customer_to_dict(customer: Customer) -> dict[str, Any]:
    return {
        "id": customer.id,
        "x": customer.x,
        "y": customer.y,
        "demand": customer.demand,
        "ready_time": customer.ready_time,
        "due_time": customer.due_time,
        "service_time": customer.service_time,
        "lat": customer.lat,
        "lon": customer.lon,
    }
