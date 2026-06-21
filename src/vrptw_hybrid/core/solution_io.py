"""Serialization helpers for solutions and experiment metrics."""

from __future__ import annotations

import csv
import json
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from vrptw_hybrid.core.models import Route, RouteStop, Solution


def solution_to_dict(solution: Solution) -> dict[str, Any]:
    """Convert a Solution into a JSON-serializable dictionary."""

    return {
        "instance_name": solution.instance_name,
        "solver_name": solution.solver_name,
        "routes": [
            {
                "vehicle_id": route.vehicle_id,
                "stops": [
                    {
                        "customer_id": stop.customer_id,
                        "arrival_time": stop.arrival_time,
                        "start_service_time": stop.start_service_time,
                        "departure_time": stop.departure_time,
                        "load_after": stop.load_after,
                    }
                    for stop in route.stops
                ],
                "distance": route.distance,
                "duration": route.duration,
                "load": route.load,
            }
            for route in solution.routes
        ],
        "objective": solution.objective,
        "vehicles_used": solution.vehicles_used,
        "total_distance": solution.total_distance,
        "total_duration": solution.total_duration,
        "feasible": solution.feasible,
        "runtime_sec": solution.runtime_sec,
        "metadata": dict(solution.metadata),
    }


def solution_from_dict(data: Mapping[str, Any]) -> Solution:
    """Build a Solution from a dictionary produced by solution_to_dict."""

    routes = tuple(_route_from_dict(route_data) for route_data in data["routes"])
    return Solution(
        instance_name=str(data["instance_name"]),
        solver_name=str(data["solver_name"]),
        routes=routes,
        objective=float(data["objective"]),
        vehicles_used=int(data["vehicles_used"]),
        total_distance=float(data["total_distance"]),
        total_duration=float(data["total_duration"]),
        feasible=bool(data["feasible"]),
        runtime_sec=float(data["runtime_sec"]),
        metadata=dict(data.get("metadata", {})),
    )


def save_solution_json(solution: Solution, path: str | Path, *, indent: int = 2) -> Path:
    """Save a Solution as human-readable JSON and return the output path."""

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file:
        json.dump(solution_to_dict(solution), file, indent=indent, sort_keys=True)
        file.write("\n")
    return output_path


def load_solution_json(path: str | Path) -> Solution:
    """Load a Solution from a JSON file."""

    input_path = Path(path)
    with input_path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, dict):
        raise ValueError(f"Solution JSON root must be an object: {input_path}")
    return solution_from_dict(data)


def save_metrics_csv(rows: Iterable[Mapping[str, Any]], path: str | Path) -> Path:
    """Write experiment metric rows to CSV and return the output path."""

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    materialized_rows = [dict(row) for row in rows]
    fieldnames = _collect_fieldnames(materialized_rows)

    with output_path.open("w", encoding="utf-8", newline="") as file:
        if not fieldnames:
            return output_path
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(materialized_rows)
    return output_path


def _route_from_dict(data: Mapping[str, Any]) -> Route:
    stops = tuple(_stop_from_dict(stop_data) for stop_data in data["stops"])
    return Route(
        vehicle_id=int(data["vehicle_id"]),
        stops=stops,
        distance=float(data["distance"]),
        duration=float(data["duration"]),
        load=int(data["load"]),
    )


def _stop_from_dict(data: Mapping[str, Any]) -> RouteStop:
    return RouteStop(
        customer_id=int(data["customer_id"]),
        arrival_time=float(data["arrival_time"]),
        start_service_time=float(data["start_service_time"]),
        departure_time=float(data["departure_time"]),
        load_after=int(data["load_after"]),
    )


def _collect_fieldnames(rows: list[dict[str, Any]]) -> list[str]:
    fieldnames: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row:
            if key not in seen:
                seen.add(key)
                fieldnames.append(key)
    return fieldnames
