from __future__ import annotations

from typing import Any

import numpy as np

from vrptw_hybrid.core.models import (
    Customer,
    Route,
    RouteStop,
    Solution,
    VehicleSpec,
    VRPTWInstance,
)
from vrptw_hybrid.visualization.geojson import (
    points_feature_collection,
    routes_feature_collection,
    solution_geojson,
)


class FakeGraph:
    def __init__(self) -> None:
        self._nodes = {
            "depot": {"x": 0.0, "y": 0.0},
            "c1": {"x": 1.0, "y": 0.0},
            "c2": {"x": 2.0, "y": 0.0},
        }
        self._edges: list[tuple[str, str, dict[str, Any]]] = []

    def add_edge(self, source: str, target: str, **data: Any) -> None:
        self._edges.append((source, target, data))

    def nodes(self, data: bool = False) -> list[Any]:
        if data:
            return list(self._nodes.items())
        return list(self._nodes)

    def edges(self, data: bool = False) -> list[tuple[Any, ...]]:
        if data:
            return [(source, target, row) for source, target, row in self._edges]
        return [(source, target) for source, target, _row in self._edges]


def make_instance() -> VRPTWInstance:
    depot = Customer(
        id=0,
        x=0.0,
        y=0.0,
        demand=0,
        ready_time=0.0,
        due_time=100.0,
        service_time=0.0,
        lat=0.0,
        lon=0.0,
    )
    customers = (
        Customer(
            id=1,
            x=1.0,
            y=0.0,
            demand=3,
            ready_time=5.0,
            due_time=30.0,
            service_time=2.0,
            lat=0.0,
            lon=1.0,
        ),
        Customer(
            id=2,
            x=2.0,
            y=0.0,
            demand=4,
            ready_time=10.0,
            due_time=45.0,
            service_time=2.0,
            lat=0.0,
            lon=2.0,
        ),
    )
    matrix = np.array(
        [
            [0.0, 10.0, 20.0],
            [10.0, 0.0, 8.0],
            [20.0, 8.0, 0.0],
        ],
        dtype=float,
    )
    return VRPTWInstance(
        name="geojson_test",
        depot=depot,
        customers=customers,
        vehicle=VehicleSpec(capacity=10, count=1),
        distance_matrix=matrix,
        time_matrix=matrix,
        metadata={"graph_node_ids": ["depot", "c1", "c2"]},
    )


def make_solution() -> Solution:
    route = Route(
        vehicle_id=7,
        stops=(
            RouteStop(
                customer_id=1,
                arrival_time=10.0,
                start_service_time=10.0,
                departure_time=12.0,
                load_after=3,
            ),
            RouteStop(
                customer_id=2,
                arrival_time=20.0,
                start_service_time=20.0,
                departure_time=22.0,
                load_after=7,
            ),
        ),
        distance=27.0,
        duration=24.0,
        load=7,
    )
    return Solution(
        instance_name="geojson_test",
        solver_name="unit",
        routes=(route,),
        objective=27.0,
        vehicles_used=1,
        total_distance=27.0,
        total_duration=24.0,
        feasible=True,
        runtime_sec=0.01,
    )


def make_graph() -> FakeGraph:
    graph = FakeGraph()
    graph.add_edge(
        "depot",
        "c1",
        length=10.0,
        geometry=[(0.0, 0.0), (0.5, 0.1), (1.0, 0.0)],
    )
    graph.add_edge("c1", "c2", length=8.0)
    graph.add_edge("c2", "depot", length=9.0)
    return graph


def test_points_feature_collection_contains_customer_popup_fields() -> None:
    points = points_feature_collection(make_instance())

    assert points["type"] == "FeatureCollection"
    assert len(points["features"]) == 3
    assert points["features"][0]["geometry"]["coordinates"] == [0.0, 0.0]
    customer_properties = points["features"][1]["properties"]
    assert customer_properties["customer_id"] == 1
    assert "demand: 3" in customer_properties["popup"]
    assert "time window: [5, 30]" in customer_properties["popup"]


def test_routes_feature_collection_uses_edge_geometry_and_vehicle_id() -> None:
    routes = routes_feature_collection(make_instance(), make_solution(), make_graph())

    assert routes["type"] == "FeatureCollection"
    assert len(routes["features"]) == 1
    route = routes["features"][0]
    assert route["properties"]["vehicle_id"] == 7
    assert route["geometry"]["type"] == "LineString"
    assert route["geometry"]["coordinates"] == [
        [0.0, 0.0],
        [0.5, 0.1],
        [1.0, 0.0],
        [2.0, 0.0],
        [0.0, 0.0],
    ]


def test_solution_geojson_returns_folium_readable_collections() -> None:
    bundle = solution_geojson(make_instance(), make_solution(), make_graph())

    assert bundle["points"]["type"] == "FeatureCollection"
    assert bundle["routes"]["type"] == "FeatureCollection"
