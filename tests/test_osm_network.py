from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

import vrptw_hybrid.data.osm_network as osm_network
from vrptw_hybrid.data.osm_network import (
    OSMNetworkError,
    add_travel_time,
    load_drive_network,
    nearest_graph_nodes,
    network_distance_time_matrix,
    osm_cache_path,
)


class FakeGraph:
    def __init__(self) -> None:
        self.edge_rows: list[tuple[str, str, int, dict[str, Any]]] = []

    def add_edge(self, u: str, v: str, key: int, **data: Any) -> None:
        self.edge_rows.append((u, v, key, data))

    def copy(self) -> FakeGraph:
        copied = FakeGraph()
        copied.edge_rows = deepcopy(self.edge_rows)
        return copied

    def edges(self, *, keys: bool = False, data: bool = False) -> list[tuple[Any, ...]]:
        if keys and data:
            return [(u, v, key, row) for u, v, key, row in self.edge_rows]
        if data:
            return [(u, v, row) for u, v, _key, row in self.edge_rows]
        return [(u, v) for u, v, _key, _row in self.edge_rows]

    def number_of_edges(self) -> int:
        return len(self.edge_rows)

    def nodes(self, data: bool = False) -> list[Any]:
        nodes = {
            "1": {"x": 0.0, "y": 0.0},
            "2": {"x": 1.0, "y": 0.0},
            "3": {"x": 2.0, "y": 0.0},
            "4": {"x": 10.0, "y": 10.0},
        }
        if data:
            return list(nodes.items())
        return list(nodes)


def make_graph() -> FakeGraph:
    graph = FakeGraph()
    graph.add_edge("1", "2", key=0, length=1000.0, highway="residential")
    graph.add_edge("2", "1", key=0, length=1000.0, speed_kph=50.0)
    return graph


def make_path_graph() -> FakeGraph:
    graph = FakeGraph()
    graph.add_edge("1", "2", key=0, length=10.0, travel_time=5.0)
    graph.add_edge("2", "3", key=0, length=7.0, travel_time=4.0)
    graph.add_edge("1", "3", key=0, length=25.0, travel_time=20.0)
    graph.add_edge("2", "1", key=0, length=10.0, travel_time=5.0)
    graph.add_edge("3", "2", key=0, length=7.0, travel_time=4.0)
    graph.add_edge("3", "1", key=0, length=25.0, travel_time=20.0)
    return graph


def make_one_way_graph() -> FakeGraph:
    graph = FakeGraph()
    graph.add_edge("1", "2", key=0, length=10.0, travel_time=5.0)
    graph.add_edge("2", "3", key=0, length=7.0, travel_time=4.0)
    return graph


def test_osm_cache_path_uses_place_slug(tmp_path: Path) -> None:
    path = osm_cache_path(place="New York, USA", cache_dir=tmp_path)

    assert path == tmp_path / "new_york_usa.graphml"


def test_add_travel_time_uses_speed_or_highway_default() -> None:
    graph = add_travel_time(make_graph())
    edges = list(graph.edges(keys=True, data=True))
    edge_default = edges[0][3]
    edge_explicit = edges[1][3]

    assert edge_default["speed_kph"] == 25.0
    assert edge_default["travel_time"] == pytest.approx(144.0)
    assert edge_explicit["speed_kph"] == 50.0
    assert edge_explicit["travel_time"] == pytest.approx(72.0)


def test_load_drive_network_uses_existing_cache_without_osmnx(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cache_path = osm_cache_path(place="Cache City", cache_dir=tmp_path)
    cache_path.write_text("<graphml />", encoding="utf-8")
    monkeypatch.setattr(osm_network, "_read_graphml", lambda path: make_graph())

    graph = load_drive_network(place="Cache City", cache_dir=tmp_path)

    assert graph.number_of_edges() == 2
    for _u, _v, data in graph.edges(data=True):
        assert "travel_time" in data


def test_load_drive_network_without_cache_has_clear_error(tmp_path: Path) -> None:
    with pytest.raises(OSMNetworkError, match=r"OSMnx is required|Failed to download"):
        load_drive_network(place="Missing City", cache_dir=tmp_path)


def test_nearest_graph_nodes_uses_lat_lon_points() -> None:
    nearest = nearest_graph_nodes(make_path_graph(), [(0.0, 0.1), (0.0, 1.8)])

    assert nearest == ("1", "3")


def test_network_distance_time_matrix_uses_shortest_paths() -> None:
    distance_matrix, time_matrix = network_distance_time_matrix(
        make_path_graph(),
        ("1", "2", "3"),
    )

    assert distance_matrix.shape == (3, 3)
    assert distance_matrix[0, 2] == pytest.approx(17.0)
    assert time_matrix[0, 2] == pytest.approx(9.0)


def test_network_distance_time_matrix_handles_unreachable_large_m() -> None:
    distance_matrix, time_matrix = network_distance_time_matrix(
        make_one_way_graph(),
        ("3", "1"),
        unreachable="large_m",
        large_m=999.0,
    )

    assert distance_matrix[0, 1] == 999.0
    assert time_matrix[0, 1] == 999.0


def test_network_distance_time_matrix_raises_for_unreachable() -> None:
    with pytest.raises(OSMNetworkError, match="no path"):
        network_distance_time_matrix(make_one_way_graph(), ("3", "1"))


def test_network_distance_time_matrix_uses_npz_cache(tmp_path: Path) -> None:
    cache_path = tmp_path / "matrix_cache.npz"

    first_distance, _first_time = network_distance_time_matrix(
        make_path_graph(),
        ("1", "2"),
        cache_path=cache_path,
    )
    cached_distance, _cached_time = network_distance_time_matrix(
        make_path_graph(),
        ("1", "2"),
        cache_path=cache_path,
    )

    assert cache_path.exists()
    assert cached_distance.tolist() == first_distance.tolist()
