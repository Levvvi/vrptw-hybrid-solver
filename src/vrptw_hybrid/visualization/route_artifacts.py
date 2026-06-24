"""Build portable benchmark route artifacts from experiment solution outputs."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pandas as pd

from vrptw_hybrid.core.models import Customer, Route, RouteStop, Solution, VRPTWInstance
from vrptw_hybrid.core.solution_io import load_solution_json
from vrptw_hybrid.data.solomon import parse_solomon

BENCHMARK_NOTES = [
    "Benchmark x-y coordinates are not latitude/longitude.",
    "This artifact is not a real road-network route.",
]


class RouteArtifactError(ValueError):
    """Raised when a benchmark route artifact cannot be created."""


def load_run_table(runs_csv: str | Path) -> pd.DataFrame:
    """Load an experiment runs CSV as a pandas DataFrame."""

    path = Path(runs_csv)
    if not path.exists():
        raise FileNotFoundError(f"runs CSV not found: {path}")
    return pd.read_csv(path)


def load_solution(solution_json: str | Path) -> Solution:
    """Load a solution JSON produced by the batch runner."""

    return load_solution_json(solution_json)


def load_instance_coordinates(source_file: str | Path) -> dict[int, dict[str, Any]]:
    """Return depot/customer coordinates keyed by customer id."""

    instance = parse_solomon(source_file)
    return {
        node.id: _node_payload(
            node,
            kind="depot" if node.id == instance.depot.id else "customer",
        )
        for node in instance.nodes
    }


def select_run_row(
    runs_csv: str | Path,
    *,
    instance: str,
    solver: str,
    seed: int,
) -> dict[str, Any]:
    """Select a unique run row by instance, solver, and seed."""

    table = load_run_table(runs_csv)
    matches = table[
        (table["instance"].astype(str) == str(instance))
        & (table["solver"].astype(str) == str(solver))
        & (table["seed"].astype(int) == int(seed))
    ]
    if matches.empty:
        raise RouteArtifactError(
            f"no run row found for instance={instance!r} solver={solver!r} seed={seed!r}"
        )
    if len(matches) > 1:
        raise RouteArtifactError(
            f"multiple run rows found for instance={instance!r} solver={solver!r} seed={seed!r}"
        )
    return _row_to_dict(matches.iloc[0].to_dict())


def build_benchmark_route_artifact(
    source_file: str | Path,
    solution_json: str | Path,
    run_row: Mapping[str, Any],
) -> dict[str, Any]:
    """Build a portable x-y route artifact from one experiment run row."""

    source_path = Path(source_file)
    solution_path = Path(solution_json)
    if not source_path.exists():
        raise FileNotFoundError(f"source instance not found: {source_path}")
    if not solution_path.exists():
        raise FileNotFoundError(f"solution JSON not found: {solution_path}")

    row = _row_to_dict(run_row)
    instance = parse_solomon(source_path)
    solution = load_solution(solution_path)
    customer_by_id = {customer.id: customer for customer in instance.customers}
    has_solution = _bool(row.get("has_solution")) and bool(solution.routes)
    feasible = _bool(row.get("feasible")) and bool(solution.feasible)

    return {
        "schema_version": "benchmark_route_artifact_v1",
        "benchmark_family": _benchmark_family(source_path, instance),
        "coordinate_system": "benchmark_xy",
        "is_real_map": False,
        "source_file": str(source_path),
        "solution_json": str(solution_path),
        "instance": str(row.get("instance", solution.instance_name)),
        "source_instance_name": solution.instance_name,
        "solver": str(row.get("solver", solution.solver_name)),
        "seed": _optional_int(row.get("seed")),
        "status": str(row.get("status", solution.metadata.get("status", ""))),
        "pipeline_status": str(row.get("pipeline_status", "")),
        "feasible": feasible,
        "has_solution": has_solution,
        "vehicles": _optional_float(row.get("vehicles", solution.vehicles_used)),
        "distance": _optional_float(row.get("distance", solution.total_distance)),
        "objective": _optional_float(row.get("objective", solution.objective)),
        "runtime_sec": _optional_float(row.get("runtime_sec", solution.runtime_sec)),
        "depot": _node_payload(instance.depot, kind="depot"),
        "customers": [_node_payload(customer, kind="customer") for customer in instance.customers],
        "routes": _routes_payload(solution.routes, instance.depot, customer_by_id)
        if has_solution and feasible
        else [],
        "notes": list(BENCHMARK_NOTES),
    }


def save_route_artifact(artifact: Mapping[str, Any], output_json: str | Path) -> Path:
    """Save a benchmark route artifact as JSON."""

    path = Path(output_json)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(dict(artifact), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def artifact_route_table_rows(artifact: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Return a flat customer-stop table from an artifact."""

    rows: list[dict[str, Any]] = []
    for route in _list_of_mappings(artifact.get("routes")):
        vehicle_id = route.get("vehicle_id")
        for position, point in enumerate(_list_of_mappings(route.get("points")), start=1):
            if point.get("kind") != "customer":
                continue
            rows.append(
                {
                    "vehicle_id": vehicle_id,
                    "sequence_order": position - 1,
                    "customer_id": point.get("id"),
                    "x": point.get("x"),
                    "y": point.get("y"),
                    "demand": point.get("demand"),
                    "ready_time": point.get("ready_time"),
                    "due_time": point.get("due_time"),
                    "service_time": point.get("service_time"),
                    "arrival_time": point.get("arrival_time"),
                    "start_service_time": point.get("start_service_time"),
                    "departure_time": point.get("departure_time"),
                    "load_after": point.get("load_after"),
                }
            )
    return rows


def load_route_artifact(path: str | Path) -> dict[str, Any]:
    """Load a saved benchmark route artifact."""

    artifact_path = Path(path)
    with artifact_path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, dict):
        raise RouteArtifactError(f"artifact JSON root must be an object: {artifact_path}")
    return data


def _routes_payload(
    routes: tuple[Route, ...],
    depot: Customer,
    customer_by_id: dict[int, Customer],
) -> list[dict[str, Any]]:
    return [
        {
            "vehicle_id": route.vehicle_id,
            "customer_sequence": [stop.customer_id for stop in route.stops],
            "distance": route.distance,
            "duration": route.duration,
            "load": route.load,
            "points": _route_points(route, depot, customer_by_id),
        }
        for route in routes
    ]


def _route_points(
    route: Route,
    depot: Customer,
    customer_by_id: dict[int, Customer],
) -> list[dict[str, Any]]:
    points = [_node_payload(depot, kind="depot")]
    for stop in route.stops:
        customer = customer_by_id[stop.customer_id]
        points.append(_stop_payload(customer, stop))
    points.append(_node_payload(depot, kind="depot"))
    return points


def _node_payload(customer: Customer, *, kind: str) -> dict[str, Any]:
    return {
        "id": customer.id,
        "x": float(customer.x),
        "y": float(customer.y),
        "kind": kind,
        "demand": customer.demand,
        "ready_time": float(customer.ready_time),
        "due_time": float(customer.due_time),
        "service_time": float(customer.service_time),
    }


def _stop_payload(customer: Customer, stop: RouteStop) -> dict[str, Any]:
    payload = _node_payload(customer, kind="customer")
    payload.update(
        {
            "arrival_time": float(stop.arrival_time),
            "start_service_time": float(stop.start_service_time),
            "departure_time": float(stop.departure_time),
            "load_after": int(stop.load_after),
        }
    )
    return payload


def _benchmark_family(path: Path, instance: VRPTWInstance) -> str:
    normalized = f"{path.as_posix()} {instance.name}".lower()
    if "homberger" in normalized or "_2_" in instance.name.lower():
        return "Gehring-Homberger"
    return "Solomon"


def _row_to_dict(row: Mapping[str, Any]) -> dict[str, Any]:
    return {str(key): _clean_scalar(value) for key, value in row.items()}


def _clean_scalar(value: Any) -> Any:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except TypeError:
        return value
    if hasattr(value, "item"):
        try:
            return value.item()
        except ValueError:
            return value
    return value


def _optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return number


def _optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _list_of_mappings(value: Any) -> list[Mapping[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, Mapping)]
