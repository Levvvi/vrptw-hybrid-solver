"""OpenStreetMap road-network loading and caching helpers."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

DEFAULT_OSM_CACHE_DIR = Path("data/raw/osm")
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
        return add_travel_time(graph)

    osmnx = _import_osmnx()
    try:
        if place is not None:
            graph = osmnx.graph_from_place(place, network_type="drive")
        else:
            north, south, east, west = _bbox_for_osmnx(bbox)
            graph = osmnx.graph_from_bbox(
                north,
                south,
                east,
                west,
                network_type="drive",
            )
    except Exception as exc:
        raise OSMNetworkError(
            "Failed to download OSM driving network. Provide a cached GraphML file "
            f"at {cache_path} or check the place/bbox and network connection."
        ) from exc

    graph = add_travel_time(graph)
    if use_cache:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        osmnx.save_graphml(graph, cache_path)
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


def _bbox_for_osmnx(
    bbox: tuple[float, float, float, float] | None,
) -> tuple[float, float, float, float]:
    if bbox is None:
        raise ValueError("bbox is required")
    north, south, east, west = bbox
    return north, south, east, west


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
