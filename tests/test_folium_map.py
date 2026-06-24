from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np
import pytest

from vrptw_hybrid.core.models import (
    Customer,
    Route,
    RouteStop,
    Solution,
    VehicleSpec,
    VRPTWInstance,
)
from vrptw_hybrid.visualization import folium_map
from vrptw_hybrid.visualization.folium_map import (
    render_solution_map,
    save_solution_map_html,
)


class FakeElement:
    def __init__(
        self,
        kind: str,
        registry: list[FakeElement],
        *args: Any,
        **kwargs: Any,
    ) -> None:
        self.kind = kind
        self.args = args
        self.kwargs = kwargs
        self.children: list[FakeElement] = []
        registry.append(self)

    def add_to(self, parent: FakeElement) -> FakeElement:
        parent.children.append(self)
        return self

    def fit_bounds(self, bounds: list[list[float]]) -> None:
        self.kwargs["fit_bounds"] = bounds

    def save(self, path: str) -> None:
        Path(path).write_text("<html><body>fake folium map</body></html>", encoding="utf-8")


def make_fake_folium() -> tuple[SimpleNamespace, list[FakeElement]]:
    registry: list[FakeElement] = []

    def factory(kind: str) -> Any:
        def create(*args: Any, **kwargs: Any) -> FakeElement:
            return FakeElement(kind, registry, *args, **kwargs)

        return create

    fake = SimpleNamespace(
        Map=factory("Map"),
        FeatureGroup=factory("FeatureGroup"),
        Marker=factory("Marker"),
        CircleMarker=factory("CircleMarker"),
        PolyLine=factory("PolyLine"),
        Popup=factory("Popup"),
        Icon=factory("Icon"),
        LayerControl=factory("LayerControl"),
    )
    return fake, registry


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
    customer = Customer(
        id=1,
        x=1.0,
        y=1.0,
        demand=2,
        ready_time=5.0,
        due_time=35.0,
        service_time=3.0,
        lat=1.0,
        lon=1.0,
    )
    matrix = np.array([[0.0, 10.0], [10.0, 0.0]], dtype=float)
    return VRPTWInstance(
        name="folium_test",
        depot=depot,
        customers=(customer,),
        vehicle=VehicleSpec(capacity=10, count=1),
        distance_matrix=matrix,
        time_matrix=matrix,
    )


def make_solution() -> Solution:
    route = Route(
        vehicle_id=2,
        stops=(
            RouteStop(
                customer_id=1,
                arrival_time=10.0,
                start_service_time=12.0,
                departure_time=15.0,
                load_after=2,
            ),
        ),
        distance=20.0,
        duration=18.0,
        load=2,
    )
    return Solution(
        instance_name="folium_test",
        solver_name="unit",
        routes=(route,),
        objective=20.0,
        vehicles_used=1,
        total_distance=20.0,
        total_duration=18.0,
        feasible=True,
        runtime_sec=0.01,
    )


def install_fake_folium(
    monkeypatch: pytest.MonkeyPatch,
) -> list[FakeElement]:
    fake, registry = make_fake_folium()
    monkeypatch.setattr(folium_map, "_import_folium", lambda: fake)
    return registry


def test_render_solution_map_adds_routes_markers_popups_and_layers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry = install_fake_folium(monkeypatch)

    map_object = render_solution_map(make_instance(), make_solution())

    assert map_object.kind == "Map"
    feature_group_names = [
        element.kwargs["name"] for element in registry if element.kind == "FeatureGroup"
    ]
    assert feature_group_names == ["Routes", "Depot", "Customers"]
    assert any(element.kind == "LayerControl" for element in registry)

    polyline = next(element for element in registry if element.kind == "PolyLine")
    assert polyline.kwargs["locations"] == [[0.0, 0.0], [1.0, 1.0], [0.0, 0.0]]
    assert polyline.kwargs["tooltip"] == "Vehicle 2"

    popup_texts = [
        str(element.args[0]) for element in registry if element.kind == "Popup" and element.args
    ]
    assert any(
        "Customer 1" in text and "sequence: 1" in text and "arrival: 10" in text
        for text in popup_texts
    )
    assert any("time window: [5, 35]" in text for text in popup_texts)


def test_save_solution_map_html_writes_nonempty_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_folium(monkeypatch)
    output_path = tmp_path / "solution_map.html"

    saved_path = save_solution_map_html(make_instance(), make_solution(), output_path)

    assert saved_path == output_path
    assert output_path.exists()
    assert output_path.stat().st_size > 0


def test_render_solution_map_can_create_vehicle_layers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry = install_fake_folium(monkeypatch)

    render_solution_map(make_instance(), make_solution(), vehicle_layers=True)

    feature_group_names = [
        element.kwargs["name"] for element in registry if element.kind == "FeatureGroup"
    ]
    assert "Vehicle 2" in feature_group_names
