from pathlib import Path
from typing import Any

from vrptw_hybrid.data.synthetic import (
    CityGenerationConfig,
    generate_city_vrptw_instance,
    save_instance_json,
)


class FakeNodeGraph:
    def __init__(self, node_count: int = 30) -> None:
        self._nodes = {
            index: {"x": float(index), "y": float(index * 2)}
            for index in range(node_count)
        }

    def nodes(self, data: bool = False) -> list[Any]:
        if data:
            return list(self._nodes.items())
        return list(self._nodes)


def test_city_generator_is_seed_reproducible() -> None:
    graph = FakeNodeGraph()
    config = CityGenerationConfig(customer_count=5, seed=7, name="city_test")

    first = generate_city_vrptw_instance(graph, config)
    second = generate_city_vrptw_instance(graph, config)

    assert first.name == "city_test"
    assert [customer.demand for customer in first.customers] == [
        customer.demand for customer in second.customers
    ]
    assert first.metadata["graph_node_ids"] == second.metadata["graph_node_ids"]
    assert first.distance_matrix.tolist() == second.distance_matrix.tolist()


def test_city_generator_respects_time_windows_and_capacity() -> None:
    config = CityGenerationConfig(
        customer_count=10,
        vehicle_capacity=8,
        demand_min=1,
        demand_max=3,
        time_window_width=60.0,
        seed=11,
    )

    instance = generate_city_vrptw_instance(FakeNodeGraph(), config)

    assert instance.node_count == 11
    assert instance.vehicle.capacity == 8
    assert all(customer.demand <= instance.vehicle.capacity for customer in instance.customers)
    assert all(customer.ready_time <= customer.due_time for customer in instance.customers)
    assert all(customer.lat is not None and customer.lon is not None for customer in instance.nodes)


def test_save_mini_city_20_demo_json(tmp_path: Path) -> None:
    instance = generate_city_vrptw_instance(
        FakeNodeGraph(node_count=25),
        CityGenerationConfig(customer_count=20, seed=5, name="mini_city_20"),
    )
    output_path = tmp_path / "mini_city_20.json"

    saved_path = save_instance_json(instance, output_path)
    text = saved_path.read_text(encoding="utf-8")

    assert saved_path == output_path
    assert '"name": "mini_city_20"' in text
    assert '"customer_count": 20' in text
