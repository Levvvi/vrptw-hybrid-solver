"""Data loading and instance generation helpers."""

from vrptw_hybrid.data.city_instance import (
    city_instance_to_dict,
    load_city_instance_json,
    save_city_instance_json,
    with_network_matrices,
)
from vrptw_hybrid.data.distance_matrix import (
    euclidean_distance_matrix,
    round_matrix,
    scale_to_int,
)
from vrptw_hybrid.data.osm_network import (
    OSMNetworkError,
    add_travel_time,
    build_network_distance_matrix,
    build_shortest_path_geometry,
    download_graph,
    load_drive_network,
    load_graphml,
    nearest_graph_nodes,
    nearest_nodes_for_orders,
    network_distance_time_matrix,
    save_graphml,
    shortest_path_geometry,
    shortest_path_nodes,
)
from vrptw_hybrid.data.solomon import SolomonParseError, parse_solomon
from vrptw_hybrid.data.solomon_bks import SolomonBKS, bks_gap_fields, get_solomon_bks
from vrptw_hybrid.data.synthetic import (
    CityGenerationConfig,
    generate_city_vrptw_instance,
    save_instance_json,
)

__all__ = [
    "CityGenerationConfig",
    "OSMNetworkError",
    "SolomonBKS",
    "SolomonParseError",
    "add_travel_time",
    "bks_gap_fields",
    "build_network_distance_matrix",
    "build_shortest_path_geometry",
    "city_instance_to_dict",
    "download_graph",
    "euclidean_distance_matrix",
    "generate_city_vrptw_instance",
    "get_solomon_bks",
    "load_city_instance_json",
    "load_drive_network",
    "load_graphml",
    "nearest_graph_nodes",
    "nearest_nodes_for_orders",
    "network_distance_time_matrix",
    "parse_solomon",
    "round_matrix",
    "save_city_instance_json",
    "save_graphml",
    "save_instance_json",
    "scale_to_int",
    "shortest_path_geometry",
    "shortest_path_nodes",
    "with_network_matrices",
]
