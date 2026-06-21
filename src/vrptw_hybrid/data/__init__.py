"""Data loading and instance generation helpers."""

from vrptw_hybrid.data.distance_matrix import (
    euclidean_distance_matrix,
    round_matrix,
    scale_to_int,
)
from vrptw_hybrid.data.osm_network import OSMNetworkError, add_travel_time, load_drive_network
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
    "euclidean_distance_matrix",
    "generate_city_vrptw_instance",
    "get_solomon_bks",
    "load_drive_network",
    "parse_solomon",
    "round_matrix",
    "save_instance_json",
    "scale_to_int",
]
