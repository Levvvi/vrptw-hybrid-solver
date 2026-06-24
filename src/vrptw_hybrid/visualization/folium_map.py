"""Folium rendering helpers for VRPTW solution maps."""

from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Any

from vrptw_hybrid.core.models import Solution, VRPTWInstance
from vrptw_hybrid.visualization.geojson import solution_geojson

ROUTE_COLORS = [
    "#2563eb",
    "#dc2626",
    "#16a34a",
    "#9333ea",
    "#ea580c",
    "#0891b2",
    "#be123c",
    "#4d7c0f",
]


class FoliumMapError(RuntimeError):
    """Raised when Folium rendering cannot be completed."""


def render_solution_map(
    instance: VRPTWInstance,
    solution: Solution,
    graph: Any | None = None,
    *,
    geojson_bundle: dict[str, Any] | None = None,
    weight: str = "length",
    tiles: str = "OpenStreetMap",
    zoom_start: int = 12,
    vehicle_layers: bool = False,
    caption: str | None = None,
) -> Any:
    """Return a Folium map containing depot, customers, and solution routes."""

    folium = _import_folium()
    bundle = geojson_bundle or solution_geojson(instance, solution, graph, weight=weight)
    points = _features(bundle["points"])
    routes = _features(bundle["routes"])

    map_object = folium.Map(
        location=list(_map_center(points)),
        zoom_start=zoom_start,
        tiles=tiles,
        control_scale=True,
    )

    route_group = folium.FeatureGroup(name="Routes", show=True).add_to(map_object)
    depot_group = folium.FeatureGroup(name="Depot", show=True).add_to(map_object)
    customer_group = folium.FeatureGroup(name="Customers", show=True).add_to(map_object)

    stop_index = _route_stop_index(solution)
    _add_route_layers(folium, map_object, route_group, routes, vehicle_layers=vehicle_layers)
    _add_point_layers(folium, depot_group, customer_group, points, stop_index)
    _add_caption(folium, map_object, caption)
    _fit_points(map_object, points)
    folium.LayerControl(collapsed=False).add_to(map_object)
    return map_object


def save_solution_map_html(
    instance: VRPTWInstance,
    solution: Solution,
    output_path: str | Path,
    graph: Any | None = None,
    *,
    geojson_bundle: dict[str, Any] | None = None,
    weight: str = "length",
    tiles: str = "OpenStreetMap",
    zoom_start: int = 12,
    vehicle_layers: bool = False,
    caption: str | None = None,
) -> Path:
    """Render a solution map and save it as an HTML file."""

    map_object = render_solution_map(
        instance,
        solution,
        graph,
        geojson_bundle=geojson_bundle,
        weight=weight,
        tiles=tiles,
        zoom_start=zoom_start,
        vehicle_layers=vehicle_layers,
        caption=caption,
    )
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    map_object.save(str(path))
    return path


def _import_folium() -> Any:
    try:
        import folium
    except ImportError as exc:
        raise FoliumMapError(
            "Folium is required for map rendering. Install the visualization extra "
            'with: pip install -e ".[vis]"'
        ) from exc
    return folium


def _features(collection: dict[str, Any]) -> list[dict[str, Any]]:
    features = collection.get("features", [])
    return [feature for feature in features if isinstance(feature, dict)]


def _map_center(points: list[dict[str, Any]]) -> tuple[float, float]:
    locations = [_lat_lon(feature["geometry"]["coordinates"]) for feature in points]
    if not locations:
        return (0.0, 0.0)
    lat = sum(location[0] for location in locations) / len(locations)
    lon = sum(location[1] for location in locations) / len(locations)
    return (lat, lon)


def _fit_points(map_object: Any, points: list[dict[str, Any]]) -> None:
    locations = [_lat_lon(feature["geometry"]["coordinates"]) for feature in points]
    if len(locations) < 2:
        return
    min_lat = min(location[0] for location in locations)
    max_lat = max(location[0] for location in locations)
    min_lon = min(location[1] for location in locations)
    max_lon = max(location[1] for location in locations)
    fit_bounds = getattr(map_object, "fit_bounds", None)
    if callable(fit_bounds):
        fit_bounds([[min_lat, min_lon], [max_lat, max_lon]])


def _add_route_layers(
    folium: Any,
    map_object: Any,
    route_group: Any,
    routes: list[dict[str, Any]],
    *,
    vehicle_layers: bool,
) -> None:
    for index, feature in enumerate(routes):
        coordinates = feature["geometry"].get("coordinates", [])
        locations = [_lat_lon(coordinate) for coordinate in coordinates]
        if len(locations) < 2:
            continue
        properties = feature.get("properties", {})
        vehicle_id = properties.get("vehicle_id", index)
        parent = route_group
        if vehicle_layers:
            parent = folium.FeatureGroup(name=f"Vehicle {vehicle_id}", show=True).add_to(
                map_object
            )
        folium.PolyLine(
            locations=locations,
            color=_route_color(index),
            weight=4,
            opacity=0.85,
            tooltip=f"Vehicle {vehicle_id}",
            popup=folium.Popup(_route_popup_html(properties), max_width=320),
        ).add_to(parent)


def _add_caption(folium: Any, map_object: Any, caption: str | None) -> None:
    if not caption:
        return
    get_root = getattr(map_object, "get_root", None)
    element_factory = getattr(folium, "Element", None)
    if not callable(get_root) or element_factory is None:
        return
    html = (
        '<div style="position: fixed; top: 12px; left: 50px; z-index: 9999; '
        'background: white; padding: 8px 10px; border: 1px solid #555; '
        'border-radius: 4px; font-size: 13px; max-width: 420px;">'
        f"{escape(caption)}"
        "</div>"
    )
    get_root().html.add_child(element_factory(html))


def _add_point_layers(
    folium: Any,
    depot_group: Any,
    customer_group: Any,
    points: list[dict[str, Any]],
    stop_index: dict[int, dict[str, Any]],
) -> None:
    for feature in points:
        properties = feature.get("properties", {})
        location = _lat_lon(feature["geometry"]["coordinates"])
        role = str(properties.get("type", "customer"))
        if role == "depot":
            folium.Marker(
                location=location,
                tooltip="Depot",
                popup=folium.Popup(_point_popup_html(properties, stop_index), max_width=320),
                icon=folium.Icon(color="red", icon="home", prefix="fa"),
            ).add_to(depot_group)
        else:
            customer_id = properties.get("customer_id", properties.get("id"))
            folium.CircleMarker(
                location=location,
                radius=5,
                color="#111827",
                weight=1,
                fill=True,
                fill_color="#f59e0b",
                fill_opacity=0.9,
                tooltip=f"Customer {customer_id}",
                popup=folium.Popup(_point_popup_html(properties, stop_index), max_width=320),
            ).add_to(customer_group)


def _route_stop_index(solution: Solution) -> dict[int, dict[str, Any]]:
    index: dict[int, dict[str, Any]] = {}
    for route in solution.routes:
        for sequence_order, stop in enumerate(route.stops, start=1):
            index[stop.customer_id] = {
                "vehicle_id": route.vehicle_id,
                "sequence_order": sequence_order,
                "arrival_time": stop.arrival_time,
                "start_service_time": stop.start_service_time,
                "departure_time": stop.departure_time,
                "load_after": stop.load_after,
            }
    return index


def _route_popup_html(properties: dict[str, Any]) -> str:
    vehicle_id = properties.get("vehicle_id", "")
    customer_ids = ", ".join(str(customer_id) for customer_id in properties.get("customer_ids", []))
    rows = [
        f"<strong>Vehicle {escape(str(vehicle_id))}</strong>",
        f"customers: {escape(customer_ids)}",
        f"distance: {_format_number(properties.get('distance'))}",
        f"duration: {_format_number(properties.get('duration'))}",
        f"load: {escape(str(properties.get('load', '')))}",
    ]
    return "<br>".join(rows)


def _point_popup_html(
    properties: dict[str, Any],
    stop_index: dict[int, dict[str, Any]],
) -> str:
    role = str(properties.get("type", "customer"))
    customer_id = properties.get("customer_id", properties.get("id", ""))
    if role == "depot":
        title = "Depot"
    else:
        title = f"Customer {customer_id}"

    rows = [
        f"<strong>{escape(title)}</strong>",
        f"demand: {escape(str(properties.get('demand', '')))}",
        (
            "time window: "
            f"[{_format_number(properties.get('ready_time'))}, "
            f"{_format_number(properties.get('due_time'))}]"
        ),
    ]

    if isinstance(customer_id, int) and customer_id in stop_index:
        stop = stop_index[customer_id]
        rows.extend(
            [
                f"vehicle: {escape(str(stop['vehicle_id']))}",
                f"sequence: {escape(str(stop['sequence_order']))}",
                f"arrival: {_format_number(stop['arrival_time'])}",
                f"service start: {_format_number(stop['start_service_time'])}",
                f"departure: {_format_number(stop['departure_time'])}",
                f"load after: {escape(str(stop['load_after']))}",
            ]
        )
    return "<br>".join(rows)


def _lat_lon(coordinate: list[Any] | tuple[Any, ...]) -> list[float]:
    lon, lat = coordinate[0], coordinate[1]
    return [float(lat), float(lon)]


def _route_color(index: int) -> str:
    return ROUTE_COLORS[index % len(ROUTE_COLORS)]


def _format_number(value: Any) -> str:
    if value is None:
        return ""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return escape(str(value))
    return escape(f"{number:g}")
