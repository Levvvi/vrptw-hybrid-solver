"""Visualization helpers for VRPTW solutions."""

from vrptw_hybrid.visualization.folium_map import (
    FoliumMapError,
    render_solution_map,
    save_solution_map_html,
)
from vrptw_hybrid.visualization.geojson import (
    points_feature_collection,
    routes_feature_collection,
    save_geojson,
    solution_geojson,
)
from vrptw_hybrid.visualization.route_artifacts import (
    RouteArtifactError,
    artifact_route_table_rows,
    build_benchmark_route_artifact,
    load_route_artifact,
    save_route_artifact,
    select_run_row,
)

__all__ = [
    "FoliumMapError",
    "RouteArtifactError",
    "artifact_route_table_rows",
    "build_benchmark_route_artifact",
    "load_route_artifact",
    "points_feature_collection",
    "render_solution_map",
    "routes_feature_collection",
    "save_geojson",
    "save_route_artifact",
    "save_solution_map_html",
    "select_run_row",
    "solution_geojson",
]
