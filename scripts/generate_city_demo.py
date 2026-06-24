"""Generate the curated Berlin Mitte city road-network demo artifacts."""

# ruff: noqa: E402

from __future__ import annotations

import argparse
import csv
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

import yaml

from vrptw_hybrid.core.checker import check_solution
from vrptw_hybrid.core.models import Solution, VRPTWInstance
from vrptw_hybrid.core.solution_io import save_solution_json
from vrptw_hybrid.data.city_instance import save_city_instance_json, with_network_matrices
from vrptw_hybrid.data.osm_network import (
    OSMNetworkError,
    download_graph,
    network_distance_time_matrix,
)
from vrptw_hybrid.data.synthetic import CityGenerationConfig, generate_city_vrptw_instance
from vrptw_hybrid.solvers.dispatch import run_solver_from_config
from vrptw_hybrid.visualization.folium_map import save_solution_map_html
from vrptw_hybrid.visualization.geojson import save_geojson, solution_geojson

CITY_MAP_CAPTION = (
    "Road-network shortest path based on OSM data; travel time is a proxy unless "
    "a calibrated speed model is enabled."
)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/city_demo_berlin_mitte.yaml"),
        help="City demo YAML config.",
    )
    args = parser.parse_args(argv)
    generate_city_demo(args.config)
    return 0


def generate_city_demo(config_path: str | Path) -> dict[str, Path]:
    """Generate city instance, solutions, GeoJSON, Folium maps, and summary CSV."""

    config_file = _repo_path(config_path)
    config = _load_yaml(config_file)
    graph = _load_or_download_graph(config)
    instance = build_city_instance(config, graph)
    outputs = _outputs(config)
    city = config["city"]
    city_dir = outputs["city_dir"]
    city_dir.mkdir(parents=True, exist_ok=True)

    instance_path = _repo_path(outputs["instance_json"])
    save_city_instance_json(
        instance,
        instance_path,
        city_id=str(city["city_id"]),
        place_name=str(city["place_name"]),
        graphml_cache_path=_relative_path(_network_cache_path(city)),
        matrix_cache_path=Path(str(instance.metadata["matrix_cache_path"])),
    )

    rows: list[dict[str, Any]] = []
    for solver_name in config["solvers"]:
        rows.append(_run_solver_and_save(config, instance, graph, str(solver_name), city_dir))

    summary_path = _repo_path(outputs["summary_csv"])
    _write_summary(rows, summary_path)
    return {
        "instance_json": instance_path,
        "summary_csv": summary_path,
        "city_dir": city_dir,
    }


def build_city_instance(config: dict[str, Any], graph: Any) -> VRPTWInstance:
    """Build a reproducible city instance and replace Euclidean matrices."""

    city = config["city"]
    generation = config["generation"]
    base_seed = int(generation["seed"])
    last_error: Exception | None = None
    for attempt in range(10):
        seed = base_seed + attempt
        synthetic = generate_city_vrptw_instance(
            graph,
            CityGenerationConfig(
                customer_count=int(generation["order_count"]),
                vehicle_count=int(generation["vehicle_count"]),
                vehicle_capacity=int(generation["vehicle_capacity"]),
                demand_min=int(generation["demand_min"]),
                demand_max=int(generation["demand_max"]),
                service_time=float(generation["service_time_min"]),
                time_window_width=float(generation["horizon_min"]),
                horizon=float(generation["horizon_min"]),
                seed=seed,
                name=str(city["city_id"]),
            ),
        )
        node_ids = tuple(synthetic.metadata["graph_node_ids"])
        matrix_cache_path = _matrix_cache_path(city, seed=seed, base_seed=base_seed)
        try:
            distance_matrix_m, time_matrix_sec = network_distance_time_matrix(
                graph,
                node_ids,
                cache_path=matrix_cache_path,
            )
        except OSMNetworkError as exc:
            last_error = exc
            continue
        time_matrix_min = time_matrix_sec / 60.0
        return with_network_matrices(
            synthetic,
            distance_matrix_m=distance_matrix_m,
            time_matrix_min=time_matrix_min,
            graphml_cache_path=_relative_path(_network_cache_path(city)),
            matrix_cache_path=_relative_path(matrix_cache_path),
            place_name=str(city["place_name"]),
            network_type=str(city["network_type"]),
            horizon_min=float(generation["horizon_min"]),
            service_time_min=float(generation["service_time_min"]),
        )
    raise OSMNetworkError("failed to sample mutually reachable city nodes") from last_error


def _run_solver_and_save(
    config: dict[str, Any],
    instance: VRPTWInstance,
    graph: Any,
    solver_name: str,
    city_dir: Path,
) -> dict[str, Any]:
    seed = int(config["generation"]["seed"])
    solution_path = city_dir / f"city_solution_{solver_name}_seed0.json"
    geojson_path = city_dir / f"city_routes_{solver_name}_seed0.geojson"
    map_path = city_dir / f"city_map_{solver_name}_seed0.html"
    try:
        solution = run_solver_from_config(
            solver_name=solver_name,
            instance=instance,
            config=config,
            seed=seed,
            time_limit=_solver_time_limit(config, solver_name),
            max_iterations=int(config["solver"]["max_iterations"]),
        )
        solution = _with_city_metadata(solution, solver_name=solver_name, config=config)
        report = check_solution(solution, instance)
        if solution.feasible != report.feasible:
            solution = Solution(
                instance_name=solution.instance_name,
                solver_name=solution.solver_name,
                routes=solution.routes,
                objective=solution.objective,
                vehicles_used=solution.vehicles_used,
                total_distance=solution.total_distance,
                total_duration=solution.total_duration,
                feasible=report.feasible,
                runtime_sec=solution.runtime_sec,
                metadata={**solution.metadata, "feasibility_violations": list(report.violations)},
            )
        solution = _compact_city_solution(solution)
        save_solution_json(solution, solution_path)
        bundle = solution_geojson(instance, solution, graph=graph, weight="length")
        save_geojson(_combined_feature_collection(bundle), geojson_path)
        save_solution_map_html(
            instance,
            solution,
            map_path,
            graph=graph,
            geojson_bundle=bundle,
            weight="length",
            vehicle_layers=True,
            caption=CITY_MAP_CAPTION,
        )
        return _summary_row(
            solver_name=solver_name,
            solution=solution,
            report_violations=list(report.violations),
            solution_path=solution_path,
            geojson_path=geojson_path,
            map_path=map_path,
        )
    except Exception as exc:
        return {
            "solver": solver_name,
            "seed": 0,
            "pipeline_status": "error",
            "status": "ERROR",
            "feasible": False,
            "has_solution": False,
            "vehicles": 0,
            "distance_m": "",
            "duration_min": "",
            "objective": "",
            "runtime_sec": "",
            "solution_json": "",
            "geojson": "",
            "map_html": "",
            "error": str(exc),
        }


def _with_city_metadata(
    solution: Solution,
    *,
    solver_name: str,
    config: dict[str, Any],
) -> Solution:
    city = config["city"]
    return Solution(
        instance_name=solution.instance_name,
        solver_name=solver_name,
        routes=solution.routes,
        objective=solution.objective,
        vehicles_used=solution.vehicles_used,
        total_distance=solution.total_distance,
        total_duration=solution.total_duration,
        feasible=solution.feasible,
        runtime_sec=solution.runtime_sec,
        metadata={
            **solution.metadata,
            "solver_alias": solver_name,
            "city_id": city["city_id"],
            "place_name": city["place_name"],
            "coordinate_system": "lat_lon",
            "distance_unit": "meters",
            "time_unit": "minutes",
            "travel_time_note": "road-network shortest-path proxy",
        },
    )


def _compact_city_solution(solution: Solution) -> Solution:
    """Drop heavy ALNS histories from curated city solution JSON artifacts."""

    metadata = dict(solution.metadata)
    selector = metadata.get("selector")
    kept_metadata = {
        key: value
        for key, value in metadata.items()
        if key
        in {
            "ablation",
            "best_iteration",
            "city_id",
            "coordinate_system",
            "destroy_fraction",
            "distance_unit",
            "feasibility_violations",
            "first_solution_strategy",
            "iterations",
            "local_search_metaheuristic",
            "max_iterations",
            "place_name",
            "scale_factor",
            "seed",
            "selector",
            "solver_alias",
            "status",
            "time_limit_sec",
            "time_unit",
            "travel_time_note",
        }
    }
    if isinstance(selector, dict):
        kept_metadata["selector"] = selector
    kept_metadata["curated_metadata_note"] = "full ALNS history omitted from city demo JSON"
    return Solution(
        instance_name=solution.instance_name,
        solver_name=solution.solver_name,
        routes=solution.routes,
        objective=solution.objective,
        vehicles_used=solution.vehicles_used,
        total_distance=solution.total_distance,
        total_duration=solution.total_duration,
        feasible=solution.feasible,
        runtime_sec=solution.runtime_sec,
        metadata=kept_metadata,
    )


def _summary_row(
    *,
    solver_name: str,
    solution: Solution,
    report_violations: list[str],
    solution_path: Path,
    geojson_path: Path,
    map_path: Path,
) -> dict[str, Any]:
    status = str(solution.metadata.get("status", "FEASIBLE" if solution.feasible else "FAILED"))
    has_solution = bool(solution.routes)
    return {
        "city_id": solution.metadata.get("city_id", solution.instance_name),
        "solver": solver_name,
        "seed": 0,
        "pipeline_status": "ok",
        "status": status,
        "feasible": solution.feasible,
        "has_solution": has_solution,
        "vehicles": solution.vehicles_used,
        "distance_m": solution.total_distance if has_solution else "",
        "duration_min": solution.total_duration if has_solution else "",
        "objective": solution.objective if has_solution else "",
        "runtime_sec": solution.runtime_sec,
        "solution_json": _relative_path(solution_path),
        "geojson": _relative_path(geojson_path),
        "map_html": _relative_path(map_path),
        "checker_feasible": not report_violations,
        "violations": "; ".join(report_violations),
        "error": "",
    }


def _load_or_download_graph(config: dict[str, Any]) -> Any:
    city = config["city"]
    cache_path = _network_cache_path(city)
    bbox_config = city.get("bbox")
    bbox = None
    if isinstance(bbox_config, dict):
        bbox = (
            float(bbox_config["north"]),
            float(bbox_config["south"]),
            float(bbox_config["east"]),
            float(bbox_config["west"]),
        )
    try:
        return download_graph(
            place_name=None if bbox is not None else str(city["place_name"]),
            bbox=bbox,
            network_type=str(city.get("network_type", "drive")),
            cache_path=cache_path,
        )
    except OSMNetworkError:
        raise


def _solver_time_limit(config: dict[str, Any], solver_name: str) -> float:
    if solver_name == "ortools_routing":
        return float(config["time_limits"]["ortools_routing"])
    if solver_name.startswith("alns"):
        return float(config["time_limits"]["alns"])
    return float(config["solver"]["time_limit_sec"])


def _matrix_cache_path(city: dict[str, Any], *, seed: int, base_seed: int) -> Path:
    path = _distance_matrix_cache_path(city)
    if seed == base_seed:
        return path
    return path.with_name(f"{path.stem}_seed{seed}{path.suffix}")


def _network_cache_path(city: dict[str, Any]) -> Path:
    return _repo_path(_required_city_path(city, "network_cache", "graph_cache_path"))


def _distance_matrix_cache_path(city: dict[str, Any]) -> Path:
    return _repo_path(
        _required_city_path(city, "distance_matrix_cache", "distance_matrix_cache_path")
    )


def _required_city_path(city: dict[str, Any], preferred_key: str, fallback_key: str) -> Any:
    value = city.get(preferred_key, city.get(fallback_key))
    if value is None:
        raise KeyError(f"city.{preferred_key} is required")
    return value


def _combined_feature_collection(bundle: dict[str, Any]) -> dict[str, Any]:
    points = bundle.get("points", {}).get("features", [])
    routes = bundle.get("routes", {}).get("features", [])
    return {
        "type": "FeatureCollection",
        "features": [*points, *routes],
    }


def _write_summary(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Config root must be a mapping: {path}")
    data.setdefault("metadata", {})
    data["metadata"]["generated_at"] = datetime.now(UTC).isoformat()
    return data


def _outputs(config: dict[str, Any]) -> dict[str, Path]:
    outputs = config["outputs"]
    normalized = dict(outputs)
    if "city_dir" not in normalized and "demo_dir" in normalized:
        normalized["city_dir"] = normalized["demo_dir"]
    return {key: _repo_path(value) for key, value in normalized.items()}


def _repo_path(path_value: str | Path) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        return path
    return REPO_ROOT / path


def _relative_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT.resolve()))
    except ValueError:
        return str(path)


if __name__ == "__main__":
    raise SystemExit(main())
