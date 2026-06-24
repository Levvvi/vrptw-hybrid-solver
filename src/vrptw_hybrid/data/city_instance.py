"""City-road VRPTW instance artifact helpers."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from vrptw_hybrid.core.models import Customer, VehicleSpec, VRPTWInstance


def with_network_matrices(
    instance: VRPTWInstance,
    *,
    distance_matrix_m: NDArray[np.float64],
    time_matrix_min: NDArray[np.float64],
    graphml_cache_path: str | Path,
    matrix_cache_path: str | Path,
    place_name: str,
    network_type: str,
    horizon_min: float,
    service_time_min: float,
) -> VRPTWInstance:
    """Return a city instance that uses road-network matrices in solver units."""

    depot = replace(
        instance.depot,
        ready_time=0.0,
        due_time=horizon_min,
        service_time=0.0,
    )
    customers = tuple(
        replace(
            customer,
            ready_time=0.0,
            due_time=horizon_min,
            service_time=service_time_min,
        )
        for customer in instance.customers
    )
    metadata = {
        **instance.metadata,
        "format": "synthetic_city_osm",
        "coordinate_system": "lat_lon",
        "place_name": place_name,
        "network_type": network_type,
        "distance_matrix_type": "network_shortest_path",
        "distance_unit": "meters",
        "time_matrix_type": "speed_proxy_shortest_path",
        "time_unit": "minutes",
        "graphml_cache_path": str(graphml_cache_path),
        "matrix_cache_path": str(matrix_cache_path),
        "traffic_time_note": "travel time is a road-network shortest-path proxy",
    }
    return VRPTWInstance(
        name=instance.name,
        depot=depot,
        customers=customers,
        vehicle=instance.vehicle,
        distance_matrix=distance_matrix_m,
        time_matrix=time_matrix_min,
        metadata=metadata,
    )


def save_city_instance_json(
    instance: VRPTWInstance,
    path: str | Path,
    *,
    city_id: str,
    place_name: str,
    graphml_cache_path: str | Path,
    matrix_cache_path: str | Path,
) -> Path:
    """Save a city instance artifact that can reconstruct the solver instance."""

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    artifact = city_instance_to_dict(
        instance,
        city_id=city_id,
        place_name=place_name,
        graphml_cache_path=graphml_cache_path,
        matrix_cache_path=matrix_cache_path,
    )
    output_path.write_text(
        json.dumps(artifact, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return output_path


def load_city_instance_json(path: str | Path) -> VRPTWInstance:
    """Load a city instance saved by save_city_instance_json."""

    input_path = Path(path)
    data = json.loads(input_path.read_text(encoding="utf-8"))
    depot = _customer_from_dict(data["depot"])
    customers = tuple(_customer_from_dict(row) for row in data["customers"])
    vehicles = data["vehicles"]
    distance = np.asarray(data["distance_matrix"]["values"], dtype=float)
    time = np.asarray(data["time_matrix"]["values"], dtype=float)
    metadata = dict(data.get("metadata", {}))
    metadata.update(
        {
            "city_id": data["city_id"],
            "place_name": data["place_name"],
            "coordinate_system": data["coordinate_system"],
            "graph_node_ids": [
                data["depot"]["nearest_node"],
                *(row["nearest_node"] for row in data["customers"]),
            ],
        }
    )
    return VRPTWInstance(
        name=str(data["city_id"]),
        depot=depot,
        customers=customers,
        vehicle=VehicleSpec(
            count=int(vehicles["count"]),
            capacity=int(vehicles["capacity"]),
            fixed_cost=float(vehicles.get("fixed_cost", 0.0)),
        ),
        distance_matrix=distance,
        time_matrix=time,
        metadata=metadata,
    )


def city_instance_to_dict(
    instance: VRPTWInstance,
    *,
    city_id: str,
    place_name: str,
    graphml_cache_path: str | Path,
    matrix_cache_path: str | Path,
) -> dict[str, Any]:
    """Return a JSON-serializable city artifact."""

    graph_node_ids = _graph_node_ids(instance)
    seed = instance.metadata.get("seed")
    network_type = instance.metadata.get("network_type", "drive")
    return {
        "city_id": city_id,
        "place_name": place_name,
        "coordinate_system": "lat_lon",
        "network_type": network_type,
        "seed": seed,
        "depot": _customer_to_city_dict(instance.depot, graph_node_ids[0]),
        "customers": [
            _customer_to_city_dict(customer, node_id)
            for customer, node_id in zip(instance.customers, graph_node_ids[1:], strict=True)
        ],
        "vehicles": {
            "count": instance.vehicle.count,
            "capacity": instance.vehicle.capacity,
            "fixed_cost": instance.vehicle.fixed_cost,
        },
        "distance_matrix": {
            "type": "network_shortest_path",
            "unit": "meters",
            "source": str(matrix_cache_path),
            "values": instance.distance_matrix.tolist(),
        },
        "time_matrix": {
            "type": "speed_proxy_shortest_path",
            "unit": "minutes",
            "source": str(matrix_cache_path),
            "values": instance.time_matrix.tolist(),
        },
        "metadata": dict(instance.metadata),
        "network_cache": str(graphml_cache_path),
        "notes": [
            "Coordinates are real latitude/longitude points sampled from the OSM road network.",
            "Distances are shortest-path road-network distances in meters.",
            "Travel times are proxy values derived from OSM edge lengths and speed assumptions.",
        ],
    }


def _graph_node_ids(instance: VRPTWInstance) -> list[Any]:
    node_ids = instance.metadata.get("graph_node_ids")
    if not isinstance(node_ids, list | tuple) or len(node_ids) != instance.node_count:
        raise ValueError("city instance metadata must include one graph_node_id per node")
    return list(node_ids)


def _customer_to_city_dict(customer: Customer, nearest_node: Any) -> dict[str, Any]:
    return {
        "id": customer.id,
        "lat": customer.lat,
        "lon": customer.lon,
        "x": customer.x,
        "y": customer.y,
        "demand": customer.demand,
        "ready_time": customer.ready_time,
        "due_time": customer.due_time,
        "service_time": customer.service_time,
        "nearest_node": str(nearest_node),
    }


def _customer_from_dict(data: dict[str, Any]) -> Customer:
    return Customer(
        id=int(data["id"]),
        x=float(data.get("x", data["lon"])),
        y=float(data.get("y", data["lat"])),
        demand=int(data["demand"]),
        ready_time=float(data["ready_time"]),
        due_time=float(data["due_time"]),
        service_time=float(data["service_time"]),
        lat=float(data["lat"]),
        lon=float(data["lon"]),
    )
