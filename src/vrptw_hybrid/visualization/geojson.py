"""GeoJSON export helpers for map-based VRPTW visualization."""

from __future__ import annotations

import json
from heapq import heappop, heappush
from itertools import pairwise
from pathlib import Path
from typing import Any

from vrptw_hybrid.core.models import Customer, Route, Solution, VRPTWInstance

Coordinate = tuple[float, float]
NodeId = Any


def points_feature_collection(instance: VRPTWInstance) -> dict[str, Any]:
    """Return depot and customer points as a GeoJSON FeatureCollection."""

    features = [_point_feature(instance.depot, role="depot")]
    features.extend(_point_feature(customer, role="customer") for customer in instance.customers)
    return {"type": "FeatureCollection", "features": features}


def routes_feature_collection(
    instance: VRPTWInstance,
    solution: Solution,
    graph: Any | None = None,
    *,
    weight: str = "length",
) -> dict[str, Any]:
    """Return solution routes as GeoJSON LineString features."""

    customer_by_id = {customer.id: customer for customer in instance.customers}
    graph_node_by_customer_id = _graph_node_mapping(instance)
    features = [
        _route_feature(
            instance=instance,
            solution=solution,
            route=route,
            route_index=route_index,
            customer_by_id=customer_by_id,
            graph=graph,
            graph_node_by_customer_id=graph_node_by_customer_id,
            weight=weight,
        )
        for route_index, route in enumerate(solution.routes)
    ]
    return {"type": "FeatureCollection", "features": features}


def solution_geojson(
    instance: VRPTWInstance,
    solution: Solution,
    graph: Any | None = None,
    *,
    weight: str = "length",
) -> dict[str, Any]:
    """Return named point and route FeatureCollections for a VRPTW solution."""

    return {
        "points": points_feature_collection(instance),
        "routes": routes_feature_collection(instance, solution, graph, weight=weight),
    }


def save_geojson(collection: dict[str, Any], path: str | Path) -> Path:
    """Write a GeoJSON-compatible mapping to disk and return the output path."""

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(collection, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return output_path


def _point_feature(customer: Customer, *, role: str) -> dict[str, Any]:
    demand = int(customer.demand)
    ready_time = float(customer.ready_time)
    due_time = float(customer.due_time)
    service_time = float(customer.service_time)
    properties: dict[str, Any] = {
        "type": role,
        "id": customer.id,
        "demand": demand,
        "ready_time": ready_time,
        "due_time": due_time,
        "service_time": service_time,
        "popup": _popup_text(customer, role=role),
    }
    if role == "customer":
        properties["customer_id"] = customer.id
    return {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": list(_customer_coordinate(customer)),
        },
        "properties": properties,
    }


def _popup_text(customer: Customer, *, role: str) -> str:
    label = "Depot" if role == "depot" else f"Customer {customer.id}"
    return (
        f"{label}<br>"
        f"demand: {customer.demand}<br>"
        f"time window: [{customer.ready_time:g}, {customer.due_time:g}]<br>"
        f"service: {customer.service_time:g}"
    )


def _route_feature(
    *,
    instance: VRPTWInstance,
    solution: Solution,
    route: Route,
    route_index: int,
    customer_by_id: dict[int, Customer],
    graph: Any | None,
    graph_node_by_customer_id: dict[int, NodeId],
    weight: str,
) -> dict[str, Any]:
    customer_ids = [stop.customer_id for stop in route.stops]
    coordinates = _route_coordinates(
        instance=instance,
        route=route,
        customer_by_id=customer_by_id,
        graph=graph,
        graph_node_by_customer_id=graph_node_by_customer_id,
        weight=weight,
    )
    return {
        "type": "Feature",
        "geometry": {
            "type": "LineString",
            "coordinates": [list(coordinate) for coordinate in coordinates],
        },
        "properties": {
            "route_id": route_index,
            "vehicle_id": route.vehicle_id,
            "solver": solution.solver_name,
            "feasible": solution.feasible,
            "sequence": customer_ids,
            "customer_ids": customer_ids,
            "distance_m": float(route.distance),
            "distance": float(route.distance),
            "duration": float(route.duration),
            "load": route.load,
            "popup": (
                f"Vehicle {route.vehicle_id}<br>"
                f"customers: {', '.join(str(customer_id) for customer_id in customer_ids)}<br>"
                f"distance_m: {route.distance:g}<br>"
                f"duration_min: {route.duration:g}"
            ),
        },
    }


def _route_coordinates(
    *,
    instance: VRPTWInstance,
    route: Route,
    customer_by_id: dict[int, Customer],
    graph: Any | None,
    graph_node_by_customer_id: dict[int, NodeId],
    weight: str,
) -> list[Coordinate]:
    if graph is None or not graph_node_by_customer_id:
        return _straight_route_coordinates(instance, route, customer_by_id)

    stop_customer_ids = [stop.customer_id for stop in route.stops]
    graph_node_ids = [graph_node_by_customer_id.get(instance.depot.id)]
    graph_node_ids.extend(
        graph_node_by_customer_id.get(customer_id) for customer_id in stop_customer_ids
    )
    graph_node_ids.append(graph_node_by_customer_id.get(instance.depot.id))

    if any(node_id is None for node_id in graph_node_ids):
        return _straight_route_coordinates(instance, route, customer_by_id)

    node_ids = [node_id for node_id in graph_node_ids if node_id is not None]
    edge_lookup = _edge_lookup(graph, weight=weight)
    adjacency = _adjacency_from_edges(edge_lookup, weight=weight)
    coordinates: list[Coordinate] = []
    try:
        for source, target in pairwise(node_ids):
            node_path = _shortest_node_path(adjacency, source, target)
            segment_coordinates = _path_coordinates(graph, node_path, edge_lookup)
            _extend_without_duplicate(coordinates, segment_coordinates)
    except (KeyError, ValueError):
        return _straight_route_coordinates(instance, route, customer_by_id)

    if len(coordinates) < 2:
        return _straight_route_coordinates(instance, route, customer_by_id)
    return coordinates


def _straight_route_coordinates(
    instance: VRPTWInstance,
    route: Route,
    customer_by_id: dict[int, Customer],
) -> list[Coordinate]:
    coordinates = [_customer_coordinate(instance.depot)]
    for stop in route.stops:
        customer = customer_by_id[stop.customer_id]
        coordinates.append(_customer_coordinate(customer))
    coordinates.append(_customer_coordinate(instance.depot))
    return coordinates


def _graph_node_mapping(instance: VRPTWInstance) -> dict[int, NodeId]:
    graph_node_ids = instance.metadata.get("graph_node_ids")
    if not isinstance(graph_node_ids, list | tuple):
        return {}
    if len(graph_node_ids) != instance.node_count:
        return {}

    mapping: dict[int, NodeId] = {instance.depot.id: graph_node_ids[0]}
    for customer, graph_node_id in zip(instance.customers, graph_node_ids[1:], strict=True):
        mapping[customer.id] = graph_node_id
    return mapping


def _customer_coordinate(customer: Customer) -> Coordinate:
    lon = customer.lon if customer.lon is not None else customer.x
    lat = customer.lat if customer.lat is not None else customer.y
    return (float(lon), float(lat))


def _edge_lookup(
    graph: Any,
    *,
    weight: str,
) -> dict[tuple[NodeId, NodeId], dict[str, Any]]:
    lookup: dict[tuple[NodeId, NodeId], dict[str, Any]] = {}
    for edge in graph.edges(data=True):
        source, target, data = _normalize_edge(edge)
        candidate = dict(data)
        previous = lookup.get((source, target))
        if previous is None or _edge_weight(candidate, weight) < _edge_weight(previous, weight):
            lookup[(source, target)] = candidate
    return lookup


def _normalize_edge(edge: tuple[Any, ...]) -> tuple[NodeId, NodeId, dict[str, Any]]:
    if len(edge) == 3:
        source, target, data = edge
        return source, target, dict(data)
    if len(edge) == 4:
        source, target, _key, data = edge
        return source, target, dict(data)
    raise ValueError(f"unsupported edge tuple shape: {edge!r}")


def _edge_weight(edge_data: dict[str, Any], weight: str) -> float:
    value = edge_data.get(weight, edge_data.get("length", 1.0))
    return float(value)


def _adjacency_from_edges(
    edge_lookup: dict[tuple[NodeId, NodeId], dict[str, Any]],
    *,
    weight: str,
) -> dict[NodeId, list[tuple[NodeId, float]]]:
    adjacency: dict[NodeId, list[tuple[NodeId, float]]] = {}
    for (source, target), data in edge_lookup.items():
        adjacency.setdefault(source, []).append((target, _edge_weight(data, weight)))
        adjacency.setdefault(target, adjacency.get(target, []))
    return adjacency


def _shortest_node_path(
    adjacency: dict[NodeId, list[tuple[NodeId, float]]],
    source: NodeId,
    target: NodeId,
) -> list[NodeId]:
    if source == target:
        return [source]

    distances: dict[NodeId, float] = {source: 0.0}
    predecessors: dict[NodeId, NodeId] = {}
    counter = 0
    heap: list[tuple[float, int, NodeId]] = [(0.0, counter, source)]
    while heap:
        current_distance, _order, node = heappop(heap)
        if node == target:
            return _reconstruct_path(predecessors, source, target)
        if current_distance > distances[node]:
            continue
        for neighbor, edge_weight in adjacency.get(node, []):
            candidate = current_distance + edge_weight
            if candidate < distances.get(neighbor, float("inf")):
                distances[neighbor] = candidate
                predecessors[neighbor] = node
                counter += 1
                heappush(heap, (candidate, counter, neighbor))
    raise ValueError(f"no path between graph nodes {source!r} and {target!r}")


def _reconstruct_path(
    predecessors: dict[NodeId, NodeId],
    source: NodeId,
    target: NodeId,
) -> list[NodeId]:
    path = [target]
    while path[-1] != source:
        path.append(predecessors[path[-1]])
    path.reverse()
    return path


def _path_coordinates(
    graph: Any,
    node_path: list[NodeId],
    edge_lookup: dict[tuple[NodeId, NodeId], dict[str, Any]],
) -> list[Coordinate]:
    if len(node_path) == 1:
        return [_node_coordinate(graph, node_path[0])]

    coordinates: list[Coordinate] = []
    for source, target in pairwise(node_path):
        edge_data = edge_lookup[(source, target)]
        segment_coordinates = _edge_coordinates(graph, source, target, edge_data)
        _extend_without_duplicate(coordinates, segment_coordinates)
    return coordinates


def _edge_coordinates(
    graph: Any,
    source: NodeId,
    target: NodeId,
    edge_data: dict[str, Any],
) -> list[Coordinate]:
    geometry = edge_data.get("geometry")
    geometry_coordinates = _geometry_coordinates(geometry)
    if geometry_coordinates:
        return geometry_coordinates
    return [_node_coordinate(graph, source), _node_coordinate(graph, target)]


def _geometry_coordinates(geometry: Any) -> list[Coordinate]:
    if geometry is None:
        return []
    raw_coordinates = getattr(geometry, "coords", geometry)
    coordinates: list[Coordinate] = []
    for item in raw_coordinates:
        if len(item) < 2:
            continue
        lon, lat = item[0], item[1]
        coordinates.append((float(lon), float(lat)))
    return coordinates


def _node_coordinate(graph: Any, node_id: NodeId) -> Coordinate:
    for current_node_id, data in graph.nodes(data=True):
        if current_node_id == node_id:
            return (float(data["x"]), float(data["y"]))
    raise KeyError(f"graph node {node_id!r} is missing x/y coordinates")


def _extend_without_duplicate(
    coordinates: list[Coordinate],
    segment_coordinates: list[Coordinate],
) -> None:
    for coordinate in segment_coordinates:
        if not coordinates or coordinates[-1] != coordinate:
            coordinates.append(coordinate)
