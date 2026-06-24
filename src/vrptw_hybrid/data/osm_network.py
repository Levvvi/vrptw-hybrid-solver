"""OpenStreetMap road-network loading and caching helpers."""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime
from heapq import heappop, heappush
from itertools import pairwise
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

DEFAULT_OSM_CACHE_DIR = Path("data/raw/osm")
LOGGER = logging.getLogger(__name__)
DEFAULT_SPEED_KPH_BY_HIGHWAY = {
    "motorway": 90.0,
    "trunk": 70.0,
    "primary": 55.0,
    "secondary": 45.0,
    "tertiary": 35.0,
    "residential": 25.0,
    "unclassified": 25.0,
    "service": 15.0,
}


class OSMNetworkError(RuntimeError):
    """Raised when OSM network retrieval or caching fails."""


def download_graph(
    *,
    place_name: str | None = None,
    network_type: str = "drive",
    cache_path: str | Path,
    bbox: tuple[float, float, float, float] | None = None,
    use_cache: bool = True,
) -> Any:
    """Load a GraphML cache or download an OSM graph and save it."""

    path = Path(cache_path)
    if use_cache and path.exists():
        LOGGER.info("loading OSM GraphML cache path=%s", path)
        return load_graphml(path)

    if (place_name is None) == (bbox is None):
        raise ValueError("provide exactly one of place_name or bbox")

    osmnx = _import_osmnx()
    created_at = datetime.now(UTC).isoformat()
    LOGGER.info(
        "downloading OSM graph source=%s network_type=%s cache_path=%s created_at=%s",
        place_name or bbox,
        network_type,
        path,
        created_at,
    )
    try:
        if bbox is not None:
            graph = osmnx.graph_from_bbox(
                _bbox_for_osmnx(bbox),
                network_type=network_type,
            )
        else:
            graph = osmnx.graph_from_place(place_name, network_type=network_type)
    except Exception as exc:
        raise OSMNetworkError(
            "Failed to download OSM network. Provide a cached GraphML file "
            f"at {path} or check the place/bbox and network connection."
        ) from exc

    graph = _largest_component(add_travel_time(graph), strongly=True)
    save_graphml(graph, path)
    return graph


def load_graphml(path: str | Path) -> Any:
    """Load a cached GraphML road network and enrich travel-time fields."""

    input_path = Path(path)
    if not input_path.exists():
        raise OSMNetworkError(f"GraphML cache not found: {input_path}")
    LOGGER.info("loading GraphML path=%s", input_path)
    return _largest_component(add_travel_time(_read_graphml(input_path)), strongly=True)


def save_graphml(graph: Any, path: str | Path) -> Path:
    """Save a graph as GraphML and return the output path."""

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        osmnx = _import_osmnx()
        osmnx.save_graphml(graph, output_path)
    except Exception as exc:
        raise OSMNetworkError(f"Failed to save GraphML cache: {output_path}") from exc
    LOGGER.info("saved GraphML cache path=%s", output_path)
    return output_path


def nearest_graph_nodes(
    graph: Any,
    lat_lon_points: list[tuple[float, float]] | tuple[tuple[float, float], ...],
) -> tuple[Any, ...]:
    """Return nearest graph node ids for ``(lat, lon)`` points."""

    nodes = [
        (node_id, float(data["y"]), float(data["x"]))
        for node_id, data in graph.nodes(data=True)
        if "x" in data and "y" in data
    ]
    if not nodes:
        raise OSMNetworkError("graph contains no nodes with x/y coordinates")

    nearest: list[Any] = []
    for lat, lon in lat_lon_points:
        node_id, _node_lat, _node_lon = min(
            nodes,
            key=lambda item: (item[1] - lat) ** 2 + (item[2] - lon) ** 2,
        )
        nearest.append(node_id)
    return tuple(nearest)


def nearest_nodes_for_orders(
    graph: Any,
    depot: Any,
    customers: list[Any] | tuple[Any, ...],
) -> tuple[Any, ...]:
    """Return nearest graph nodes for a depot and customers with lat/lon fields."""

    orders = (depot, *tuple(customers))
    points = tuple(_lat_lon_from_order(order) for order in orders)
    return nearest_graph_nodes(graph, points)


def network_distance_time_matrix(
    graph: Any,
    node_ids: tuple[Any, ...] | list[Any],
    *,
    distance_weight: str = "length",
    time_weight: str = "travel_time",
    unreachable: str = "raise",
    large_m: float = 1e9,
    cache_path: str | Path | None = None,
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Return shortest-path distance and time matrices for graph node ids."""

    if cache_path is not None:
        path = Path(cache_path)
        if path.exists():
            loaded = np.load(path)
            return loaded["distance_matrix"], loaded["time_matrix"]

    node_tuple = tuple(node_ids)
    distance_matrix = _shortest_path_matrix(
        graph,
        node_tuple,
        weight=distance_weight,
        unreachable=unreachable,
        large_m=large_m,
    )
    time_matrix = _shortest_path_matrix(
        graph,
        node_tuple,
        weight=time_weight,
        unreachable=unreachable,
        large_m=large_m,
    )
    if cache_path is not None:
        path = Path(cache_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        np.savez(path, distance_matrix=distance_matrix, time_matrix=time_matrix)
    return distance_matrix, time_matrix


def build_network_distance_matrix(
    graph: Any,
    node_ids: tuple[Any, ...] | list[Any],
    *,
    weight: str = "length",
    cache_path: str | Path | None = None,
) -> NDArray[np.float64]:
    """Return a shortest-path matrix for one graph edge weight."""

    if weight == "length":
        distance_matrix, _time_matrix = network_distance_time_matrix(
            graph,
            node_ids,
            cache_path=cache_path,
        )
        return distance_matrix
    if weight == "travel_time":
        _distance_matrix, time_matrix = network_distance_time_matrix(
            graph,
            node_ids,
            cache_path=cache_path,
        )
        return time_matrix
    return _shortest_path_matrix(
        graph,
        tuple(node_ids),
        weight=weight,
        unreachable="raise",
        large_m=1e9,
    )


def build_shortest_path_geometry(
    graph: Any,
    route_node_sequence: list[Any] | tuple[Any, ...],
    *,
    weight: str = "length",
) -> list[tuple[float, float]]:
    """Return lon/lat coordinates for shortest paths between route nodes."""

    node_ids = tuple(route_node_sequence)
    if not node_ids:
        return []
    if len(node_ids) == 1:
        return [_node_coordinate(graph, node_ids[0])]

    edge_lookup = _edge_lookup(graph, weight=weight)
    adjacency = _adjacency_from_edge_lookup(edge_lookup, weight=weight)
    coordinates: list[tuple[float, float]] = []
    for source, target in pairwise(node_ids):
        path = _dijkstra_path(adjacency, source, target)
        segment = _path_geometry(graph, path, edge_lookup)
        _extend_without_duplicate(coordinates, segment)
    return coordinates


def shortest_path_nodes(
    graph: Any,
    origin_node: Any,
    dest_node: Any,
    *,
    weight: str = "length",
) -> list[Any]:
    """Return shortest-path graph nodes between two OSM nodes."""

    edge_lookup = _edge_lookup(graph, weight=weight)
    adjacency = _adjacency_from_edge_lookup(edge_lookup, weight=weight)
    return _dijkstra_path(adjacency, origin_node, dest_node)


def shortest_path_geometry(
    graph: Any,
    node_path: list[Any] | tuple[Any, ...],
) -> list[tuple[float, float]]:
    """Return lon/lat geometry coordinates for a graph node path."""

    return _path_geometry(graph, list(node_path), _edge_lookup(graph, weight="length"))


def load_drive_network(
    *,
    place: str | None = None,
    bbox: tuple[float, float, float, float] | None = None,
    cache_dir: str | Path = DEFAULT_OSM_CACHE_DIR,
    cache_name: str | None = None,
    use_cache: bool = True,
) -> Any:
    """Load a driving network from GraphML cache or OSMnx."""

    if (place is None) == (bbox is None):
        raise ValueError("provide exactly one of place or bbox")

    cache_path = osm_cache_path(
        place=place,
        bbox=bbox,
        cache_dir=cache_dir,
        cache_name=cache_name,
    )
    if use_cache and cache_path.exists():
        graph = _read_graphml(cache_path)
        return _largest_component(add_travel_time(graph), strongly=True)

    osmnx = _import_osmnx()
    try:
        if place is not None:
            graph = osmnx.graph_from_place(place, network_type="drive")
        else:
            graph = osmnx.graph_from_bbox(_bbox_for_osmnx(bbox), network_type="drive")
    except Exception as exc:
        raise OSMNetworkError(
            "Failed to download OSM driving network. Provide a cached GraphML file "
            f"at {cache_path} or check the place/bbox and network connection."
        ) from exc

    graph = _largest_component(add_travel_time(graph), strongly=True)
    if use_cache:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        save_graphml(graph, cache_path)
    return graph


def osm_cache_path(
    *,
    place: str | None = None,
    bbox: tuple[float, float, float, float] | None = None,
    cache_dir: str | Path = DEFAULT_OSM_CACHE_DIR,
    cache_name: str | None = None,
) -> Path:
    """Return the GraphML cache path for a place or bbox."""

    name = cache_name or (_slugify(place) if place is not None else _bbox_slug(bbox))
    return Path(cache_dir) / f"{name}.graphml"


def add_travel_time(
    graph: Any,
    *,
    default_speed_kph_by_highway: dict[str, float] | None = None,
) -> Any:
    """Return a copy of graph with edge speed_kph and travel_time seconds."""

    speeds = default_speed_kph_by_highway or DEFAULT_SPEED_KPH_BY_HIGHWAY
    enriched = graph.copy()
    for _u, _v, _key, data in enriched.edges(keys=True, data=True):
        length_m = float(data.get("length", 0.0))
        data["length"] = length_m
        speed_kph = _edge_speed_kph(data, speeds)
        data["speed_kph"] = speed_kph
        data["travel_time"] = length_m / (speed_kph * 1000.0 / 3600.0) if speed_kph > 0 else 0.0
    return enriched


def _edge_speed_kph(data: dict[str, Any], speeds: dict[str, float]) -> float:
    explicit_speed = _speed_value(data.get("speed_kph"))
    if explicit_speed is not None:
        return explicit_speed
    maxspeed = _speed_value(data.get("maxspeed"))
    if maxspeed is not None:
        return maxspeed

    highway_value = data.get("highway", "residential")
    highway_types = highway_value if isinstance(highway_value, list) else [highway_value]
    for highway_type in highway_types:
        speed = speeds.get(str(highway_type))
        if speed is not None:
            return speed
    return speeds["residential"]


def _shortest_path_matrix(
    graph: Any,
    node_ids: tuple[Any, ...],
    *,
    weight: str,
    unreachable: str,
    large_m: float,
) -> NDArray[np.float64]:
    if unreachable not in {"raise", "large_m"}:
        raise ValueError("unreachable must be 'raise' or 'large_m'")
    adjacency = _weighted_adjacency(graph, weight)
    matrix = np.zeros((len(node_ids), len(node_ids)), dtype=float)
    for row_index, source in enumerate(node_ids):
        distances = _dijkstra(adjacency, source)
        for col_index, target in enumerate(node_ids):
            if source == target:
                matrix[row_index, col_index] = 0.0
            elif target in distances:
                matrix[row_index, col_index] = distances[target]
            elif unreachable == "large_m":
                matrix[row_index, col_index] = large_m
            else:
                raise OSMNetworkError(
                    f"no path between graph nodes {source!r} and {target!r}"
                )
    return matrix


def _weighted_adjacency(graph: Any, weight: str) -> dict[Any, list[tuple[Any, float]]]:
    adjacency: dict[Any, list[tuple[Any, float]]] = {}
    for edge in graph.edges(data=True):
        source, target, data = _normalize_edge(edge)
        value = data.get(weight)
        if value is None:
            raise OSMNetworkError(f"edge {source!r}->{target!r} missing weight {weight!r}")
        adjacency.setdefault(source, []).append((target, float(value)))
        adjacency.setdefault(target, adjacency.get(target, []))
    return adjacency


def _lat_lon_from_order(order: Any) -> tuple[float, float]:
    lat = getattr(order, "lat", None)
    lon = getattr(order, "lon", None)
    if lat is None and isinstance(order, dict):
        lat = order.get("lat")
    if lon is None and isinstance(order, dict):
        lon = order.get("lon")
    if lat is None or lon is None:
        raise OSMNetworkError("order is missing lat/lon coordinates")
    return (float(lat), float(lon))


def _edge_lookup(graph: Any, *, weight: str) -> dict[tuple[Any, Any], dict[str, Any]]:
    lookup: dict[tuple[Any, Any], dict[str, Any]] = {}
    for edge in graph.edges(data=True):
        source, target, data = _normalize_edge(edge)
        candidate = dict(data)
        previous = lookup.get((source, target))
        if previous is None or _edge_weight(candidate, weight) < _edge_weight(previous, weight):
            lookup[(source, target)] = candidate
    return lookup


def _adjacency_from_edge_lookup(
    edge_lookup: dict[tuple[Any, Any], dict[str, Any]],
    *,
    weight: str,
) -> dict[Any, list[tuple[Any, float]]]:
    adjacency: dict[Any, list[tuple[Any, float]]] = {}
    for (source, target), data in edge_lookup.items():
        adjacency.setdefault(source, []).append((target, _edge_weight(data, weight)))
        adjacency.setdefault(target, adjacency.get(target, []))
    return adjacency


def _dijkstra_path(
    adjacency: dict[Any, list[tuple[Any, float]]],
    source: Any,
    target: Any,
) -> list[Any]:
    if source == target:
        return [source]

    distances: dict[Any, float] = {source: 0.0}
    predecessors: dict[Any, Any] = {}
    counter = 0
    heap: list[tuple[float, int, Any]] = [(0.0, counter, source)]
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
    raise OSMNetworkError(f"no path between graph nodes {source!r} and {target!r}")


def _reconstruct_path(predecessors: dict[Any, Any], source: Any, target: Any) -> list[Any]:
    path = [target]
    while path[-1] != source:
        path.append(predecessors[path[-1]])
    path.reverse()
    return path


def _path_geometry(
    graph: Any,
    node_path: list[Any],
    edge_lookup: dict[tuple[Any, Any], dict[str, Any]],
) -> list[tuple[float, float]]:
    if len(node_path) == 1:
        return [_node_coordinate(graph, node_path[0])]

    coordinates: list[tuple[float, float]] = []
    for source, target in pairwise(node_path):
        edge_data = edge_lookup[(source, target)]
        segment = _geometry_coordinates(edge_data.get("geometry"))
        if not segment:
            segment = [_node_coordinate(graph, source), _node_coordinate(graph, target)]
        _extend_without_duplicate(coordinates, segment)
    return coordinates


def _geometry_coordinates(geometry: Any) -> list[tuple[float, float]]:
    if geometry is None:
        return []
    raw_coordinates = getattr(geometry, "coords", geometry)
    coordinates: list[tuple[float, float]] = []
    for item in raw_coordinates:
        if len(item) < 2:
            continue
        coordinates.append((float(item[0]), float(item[1])))
    return coordinates


def _node_coordinate(graph: Any, node_id: Any) -> tuple[float, float]:
    for current_node_id, data in graph.nodes(data=True):
        if current_node_id == node_id:
            return (float(data["x"]), float(data["y"]))
    raise OSMNetworkError(f"graph node {node_id!r} is missing x/y coordinates")


def _extend_without_duplicate(
    coordinates: list[tuple[float, float]],
    segment_coordinates: list[tuple[float, float]],
) -> None:
    for coordinate in segment_coordinates:
        if not coordinates or coordinates[-1] != coordinate:
            coordinates.append(coordinate)


def _edge_weight(edge_data: dict[str, Any], weight: str) -> float:
    value = edge_data.get(weight, edge_data.get("length", 1.0))
    return float(value)


def _normalize_edge(edge: tuple[Any, ...]) -> tuple[Any, Any, dict[str, Any]]:
    if len(edge) == 3:
        source, target, data = edge
        return source, target, dict(data)
    if len(edge) == 4:
        source, target, _key, data = edge
        return source, target, dict(data)
    raise OSMNetworkError(f"unsupported edge tuple shape: {edge!r}")


def _dijkstra(
    adjacency: dict[Any, list[tuple[Any, float]]],
    source: Any,
) -> dict[Any, float]:
    distances: dict[Any, float] = {source: 0.0}
    counter = 0
    heap: list[tuple[float, int, Any]] = [(0.0, counter, source)]
    while heap:
        current_distance, _order, node = heappop(heap)
        if current_distance > distances[node]:
            continue
        for neighbor, edge_weight in adjacency.get(node, []):
            candidate = current_distance + edge_weight
            if candidate < distances.get(neighbor, float("inf")):
                distances[neighbor] = candidate
                counter += 1
                heappush(heap, (candidate, counter, neighbor))
    return distances


def _speed_value(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, list | tuple):
        for item in value:
            parsed = _speed_value(item)
            if parsed is not None:
                return parsed
        return None
    match = re.search(r"\d+(\.\d+)?", str(value))
    if match is None:
        return None
    parsed = float(match.group(0))
    if "mph" in str(value).lower():
        return parsed * 1.609344
    return parsed


def _read_graphml(path: Path) -> Any:
    try:
        import networkx as nx
    except ImportError as exc:
        raise OSMNetworkError(
            "NetworkX is required to read cached GraphML networks."
        ) from exc
    try:
        return nx.read_graphml(path, force_multigraph=True)
    except Exception as exc:
        raise OSMNetworkError(f"Failed to read cached GraphML network: {path}") from exc


def _import_osmnx() -> Any:
    try:
        import osmnx as ox
    except ImportError as exc:
        raise OSMNetworkError(
            "OSMnx is required to download or save OSM networks. Install the vis "
            "extra or provide an existing GraphML cache."
        ) from exc
    return ox


def _largest_component(graph: Any, *, strongly: bool) -> Any:
    try:
        osmnx = _import_osmnx()
        return osmnx.truncate.largest_component(graph, strongly=strongly)
    except Exception:
        return graph


def _bbox_for_osmnx(
    bbox: tuple[float, float, float, float] | None,
) -> tuple[float, float, float, float]:
    if bbox is None:
        raise ValueError("bbox is required")
    north, south, east, west = bbox
    return west, south, east, north


def _bbox_slug(bbox: tuple[float, float, float, float] | None) -> str:
    if bbox is None:
        raise ValueError("bbox is required when place is not provided")
    north, south, east, west = bbox
    return f"bbox_n{north:.5f}_s{south:.5f}_e{east:.5f}_w{west:.5f}".replace(".", "p")


def _slugify(value: str | None) -> str:
    if value is None:
        raise ValueError("place is required")
    normalized = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip().lower()).strip("_")
    return normalized or "osm_place"
