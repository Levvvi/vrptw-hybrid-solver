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


def solution_to_metrics_row(solution: Solution) -> dict[str, Any]:
    """Flatten a Solution into one experiment metrics row."""

    return {
        "instance": solution.instance_name,
        "solver": solution.solver_name,
        "ablation": solution.metadata.get("ablation", "default"),
        "seed": solution.metadata.get("seed"),
        "feasible": solution.feasible,
        "objective": solution.objective,
        "vehicles_used": solution.vehicles_used,
        "total_distance": solution.total_distance,
        "total_duration": solution.total_duration,
        "runtime_sec": solution.runtime_sec,
        "iterations": solution.metadata.get("iterations"),
        "best_iteration": solution.metadata.get("best_iteration"),
    }


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


def save_convergence_csv(solution: Solution, path: str | Path) -> Path:
    """Write ALNS convergence history from a Solution metadata block to CSV."""

    history = solution.metadata.get("history", [])
    rows: list[dict[str, Any]] = []
    if isinstance(history, list):
        for entry in history:
            if not isinstance(entry, Mapping):
                continue
            snapshot = entry.get("selector_snapshot")
            snapshot_mapping = snapshot if isinstance(snapshot, Mapping) else {}
            destroy_name = _string_value(entry.get("destroy_operator") or entry.get("destroy"))
            repair_name = _string_value(entry.get("repair_operator") or entry.get("repair"))
            rows.append(
                {
                    "instance": solution.instance_name,
                    "solver": solution.solver_name,
                    "seed": solution.metadata.get("seed"),
                    "iteration": entry.get("iteration"),
                    "current_cost": entry.get("current_cost"),
                    "current_objective": entry.get("current_objective", entry.get("current_cost")),
                    "candidate_cost": entry.get("candidate_cost"),
                    "candidate_objective": entry.get(
                        "candidate_objective",
                        entry.get("candidate_cost"),
                    ),
                    "best_cost": entry.get("best_cost"),
                    "best_objective": entry.get("best_objective", entry.get("best_cost")),
                    "delta_cost": entry.get("delta_cost"),
                    "reward": entry.get("reward"),
                    "accepted": entry.get("accepted"),
                    "new_best": entry.get("new_best"),
                    "destroy": destroy_name,
                    "destroy_operator": destroy_name,
                    "repair": repair_name,
                    "repair_operator": repair_name,
                    "selector": snapshot_mapping.get("name", ""),
                    "selected_destroy_probability": _operator_probability(
                        snapshot_mapping,
                        "destroy_probabilities",
                        destroy_name,
                    ),
                    "selected_repair_probability": _operator_probability(
                        snapshot_mapping,
                        "repair_probabilities",
                        repair_name,
                    ),
                    "selected_pair_probability": _pair_value(
                        snapshot_mapping,
                        "pair_probabilities",
                        destroy_name,
                        repair_name,
                    ),
                    "selected_destroy_weight": _operator_probability(
                        snapshot_mapping,
                        "destroy_weights",
                        destroy_name,
                    ),
                    "selected_repair_weight": _operator_probability(
                        snapshot_mapping,
                        "repair_weights",
                        repair_name,
                    ),
                    "selected_pair_credit": _pair_value(
                        snapshot_mapping,
                        "pair_credit",
                        destroy_name,
                        repair_name,
                    ),
                    "selector_snapshot": json.dumps(snapshot, sort_keys=True)
                    if snapshot is not None
                    else "",
                }
            )
    return save_metrics_csv(rows, path)


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


def _operator_probability(
    snapshot: Mapping[str, Any],
    field_name: str,
    operator_name: str,
) -> Any:
    values = snapshot.get(field_name)
    if isinstance(values, Mapping):
        return values.get(operator_name, "")
    return ""


def _pair_value(
    snapshot: Mapping[str, Any],
    field_name: str,
    destroy_name: str,
    repair_name: str,
) -> Any:
    values = snapshot.get(field_name)
    if isinstance(values, Mapping):
        return values.get(f"{destroy_name}|{repair_name}", "")
    return ""


def _string_value(value: object) -> str:
    return "" if value is None else str(value)
