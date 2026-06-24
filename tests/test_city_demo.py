from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import numpy as np
from scripts import generate_city_demo

from vrptw_hybrid.core.checker import check_solution
from vrptw_hybrid.data.city_instance import (
    load_city_instance_json,
    save_city_instance_json,
)
from vrptw_hybrid.solvers.greedy import solve_greedy


class FakeCityGraph:
    def __init__(self, node_count: int = 8) -> None:
        self._nodes = {
            index: {"x": 13.37 + index * 0.001, "y": 52.51 + index * 0.001}
            for index in range(node_count)
        }
        self._edges: list[tuple[int, int, dict[str, Any]]] = []
        for source in self._nodes:
            for target in self._nodes:
                if source == target:
                    continue
                distance = abs(target - source) * 100.0 + 50.0
                self._edges.append(
                    (
                        source,
                        target,
                        {"length": distance, "travel_time": distance / 500.0 * 60.0},
                    )
                )

    def nodes(self, data: bool = False) -> list[Any]:
        if data:
            return list(self._nodes.items())
        return list(self._nodes)

    def edges(self, data: bool = False) -> list[tuple[Any, ...]]:
        if data:
            return list(self._edges)
        return [(source, target) for source, target, _row in self._edges]

    def copy(self) -> FakeCityGraph:
        return self


def city_config(tmp_path: Path) -> dict[str, Any]:
    return {
        "city": {
            "city_id": "unit_city_3",
            "place_name": "Unit City",
            "network_type": "drive",
            "graph_cache_path": tmp_path / "unit.graphml",
            "distance_matrix_cache_path": tmp_path / "matrix.npz",
        },
        "generation": {
            "order_count": 3,
            "seed": 3,
            "vehicle_count": 2,
            "vehicle_capacity": 10,
            "demand_min": 1,
            "demand_max": 2,
            "service_time_min": 1.0,
            "horizon_min": 200.0,
        },
        "solvers": ["greedy"],
        "solver": {"time_limit_sec": 1, "max_iterations": 2},
        "time_limits": {"ortools_routing": 1, "alns": 1},
        "objective": {"vehicle_weight": 100000.0},
        "alns": {},
        "outputs": {
            "city_dir": tmp_path,
            "instance_json": tmp_path / "city_instance.json",
            "summary_csv": tmp_path / "city_summary.csv",
        },
    }


def test_build_city_instance_uses_network_matrices_and_checker(tmp_path: Path) -> None:
    instance = generate_city_demo.build_city_instance(city_config(tmp_path), FakeCityGraph())
    solution = solve_greedy(instance, seed=7)
    report = check_solution(solution, instance)

    assert instance.metadata["coordinate_system"] == "lat_lon"
    assert instance.metadata["distance_matrix_type"] == "network_shortest_path"
    assert instance.metadata["time_unit"] == "minutes"
    assert instance.distance_matrix.shape == (4, 4)
    assert np.max(instance.distance_matrix) > 0
    assert report.feasible


def test_city_instance_json_round_trips(tmp_path: Path) -> None:
    config = city_config(tmp_path)
    instance = generate_city_demo.build_city_instance(config, FakeCityGraph())
    path = tmp_path / "city_instance.json"

    save_city_instance_json(
        instance,
        path,
        city_id="unit_city_3",
        place_name="Unit City",
        graphml_cache_path=tmp_path / "unit.graphml",
        matrix_cache_path=tmp_path / "matrix.npz",
    )
    loaded = load_city_instance_json(path)
    raw = json.loads(path.read_text(encoding="utf-8"))

    assert raw["coordinate_system"] == "lat_lon"
    assert raw["network_type"] == "drive"
    assert raw["seed"] == 3
    assert raw["distance_matrix"]["type"] == "network_shortest_path"
    assert raw["distance_matrix"]["source"].endswith("matrix.npz")
    assert loaded.name == instance.name
    assert loaded.node_count == instance.node_count


def test_generate_city_demo_with_mock_graph_writes_curated_artifacts(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
city:
  city_id: unit_city_3
  place_name: Unit City
  network_type: drive
  graph_cache_path: {graph_cache_path}
  distance_matrix_cache_path: {matrix_cache_path}
generation:
  order_count: 3
  seed: 3
  vehicle_count: 2
  vehicle_capacity: 10
  demand_min: 1
  demand_max: 2
  service_time_min: 1.0
  horizon_min: 200.0
solvers: [greedy]
solver:
  time_limit_sec: 1
  max_iterations: 2
time_limits:
  ortools_routing: 1
  alns: 1
objective:
  vehicle_weight: 100000.0
alns: {{}}
outputs:
  city_dir: {city_dir}
  instance_json: {instance_json}
  summary_csv: {summary_csv}
        """.format(
            city_dir=(tmp_path / "city").as_posix(),
            graph_cache_path=(tmp_path / "unit.graphml").as_posix(),
            instance_json=(tmp_path / "city" / "city_instance.json").as_posix(),
            matrix_cache_path=(tmp_path / "matrix.npz").as_posix(),
            summary_csv=(tmp_path / "city" / "city_summary.csv").as_posix(),
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        generate_city_demo,
        "_load_or_download_graph",
        lambda _config: FakeCityGraph(),
    )

    outputs = generate_city_demo.generate_city_demo(config_path)
    rows = list(csv.DictReader(outputs["summary_csv"].open("r", encoding="utf-8")))

    assert outputs["instance_json"].exists()
    assert rows[0]["solver"] == "greedy"
    assert rows[0]["pipeline_status"] == "ok"
    assert Path(rows[0]["geojson"]).exists()
    assert Path(rows[0]["map_html"]).exists()
