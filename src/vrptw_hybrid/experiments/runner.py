"""Batch experiment runner for VRPTW solver comparisons."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from vrptw_hybrid.core.checker import FeasibilityReport, check_solution
from vrptw_hybrid.core.models import Solution
from vrptw_hybrid.core.solution_io import (
    save_convergence_csv,
    save_metrics_csv,
    save_solution_json,
    solution_to_metrics_row,
)
from vrptw_hybrid.data.solomon import parse_solomon
from vrptw_hybrid.data.solomon_bks import bks_gap_fields
from vrptw_hybrid.solvers.dispatch import run_solver_from_config
from vrptw_hybrid.utils.config import load_config


@dataclass(frozen=True, slots=True)
class InstanceSpec:
    name: str
    path: Path
    limit_customers: int | None = None


@dataclass(frozen=True, slots=True)
class SolverSpec:
    name: str
    solver: str
    ablation: str
    alns_overrides: dict[str, Any]


@dataclass(frozen=True, slots=True)
class BatchRunResult:
    csv_path: Path
    solution_dir: Path
    convergence_dir: Path
    rows: tuple[dict[str, Any], ...]


def plan_batch(config_path: str | Path) -> tuple[dict[str, Any], ...]:
    """Return the configured batch run matrix without executing solvers."""

    config_file = Path(config_path)
    config = load_config(config_file)
    experiment_config = _mapping(config.get("experiment", {}))
    instances = _instance_specs(experiment_config, config_file.parent)
    solvers = _solver_specs(experiment_config)
    seeds = _int_list(experiment_config.get("seeds", config.get("seed", 42)), "experiment.seeds")

    rows: list[dict[str, Any]] = []
    for instance_spec in instances:
        for solver_spec in solvers:
            for seed in seeds:
                rows.append(
                    {
                        "instance": instance_spec.name,
                        "instance_path": str(instance_spec.path),
                        "solver": solver_spec.name,
                        "solver_alias": solver_spec.solver,
                        "seed": seed,
                        "ablation": solver_spec.ablation,
                    }
                )
    return tuple(rows)


def run_batch(
    config_path: str | Path,
    *,
    output_dir: str | Path | None = None,
    output_csv: str | Path | None = None,
    timestamp: str | None = None,
) -> BatchRunResult:
    """Run a configured solver batch and write metrics CSV plus solution JSON."""

    config_file = Path(config_path)
    config = load_config(config_file)
    experiment_config = _mapping(config.get("experiment", {}))
    run_timestamp = timestamp or datetime.now().strftime("%Y%m%d_%H%M%S")
    created_at = datetime.now().isoformat(timespec="seconds")
    resolved_output_dir = Path(output_dir or experiment_config.get("output_dir", "data/results"))
    csv_path = _configured_path(
        output_csv or experiment_config.get("runs_csv"),
        default=resolved_output_dir / f"runs_{run_timestamp}.csv",
    )
    solution_dir = _configured_path(
        experiment_config.get("solution_dir"),
        default=resolved_output_dir / "solutions" / run_timestamp,
    )
    convergence_dir = _configured_path(
        experiment_config.get("convergence_dir"),
        default=resolved_output_dir / "convergence" / run_timestamp,
    )
    instances = _instance_specs(experiment_config, config_file.parent)
    solvers = _solver_specs(experiment_config)
    seeds = _int_list(experiment_config.get("seeds", config.get("seed", 42)), "experiment.seeds")
    default_time_limit = _optional_float(experiment_config.get("time_limit_sec"))
    max_iterations = _optional_int(experiment_config.get("max_iterations"))

    rows: list[dict[str, Any]] = []
    for instance_spec in instances:
        for solver_spec in solvers:
            time_limit = _time_limit_for_solver(
                experiment_config,
                solver_spec,
                default=default_time_limit,
            )
            for seed in seeds:
                rows.append(
                    _run_one(
                        base_config=config,
                        instance_spec=instance_spec,
                        solver_spec=solver_spec,
                        seed=seed,
                        time_limit=time_limit,
                        max_iterations=max_iterations,
                        solution_dir=solution_dir,
                        convergence_dir=convergence_dir,
                        config_file=config_file,
                        created_at=created_at,
                    )
                )

    save_metrics_csv(rows, csv_path)
    return BatchRunResult(
        csv_path=csv_path,
        solution_dir=solution_dir,
        convergence_dir=convergence_dir,
        rows=tuple(rows),
    )


def _run_one(
    *,
    base_config: dict[str, Any],
    instance_spec: InstanceSpec,
    solver_spec: SolverSpec,
    seed: int,
    time_limit: float | None,
    max_iterations: int | None,
    solution_dir: Path,
    convergence_dir: Path,
    config_file: Path,
    created_at: str,
) -> dict[str, Any]:
    row_base = {
        "instance": instance_spec.name,
        "instance_path": str(instance_spec.path),
        "source_file": str(instance_spec.path),
        "solver": solver_spec.name,
        "seed": seed,
        "ablation": solver_spec.ablation,
        "time_limit_sec": time_limit,
        "max_iterations": max_iterations,
        "config_file": str(config_file),
        "created_at": created_at,
    }
    try:
        instance = parse_solomon(instance_spec.path, limit_customers=instance_spec.limit_customers)
        run_config = _config_for_solver(base_config, solver_spec)
        solution = run_solver_from_config(
            solver_name=solver_spec.solver,
            instance=instance,
            config=run_config,
            seed=seed,
            time_limit=time_limit,
            max_iterations=max_iterations,
        )
        report = check_solution(solution, instance)
        solution = _with_feasibility_report(solution, report)
        solution_json = _solution_json_path(solution_dir, instance_spec, solver_spec, seed)
        save_solution_json(solution, solution_json)
        convergence_csv = _save_convergence_if_available(
            solution=solution,
            convergence_dir=convergence_dir,
            instance_spec=instance_spec,
            solver_spec=solver_spec,
            seed=seed,
        )
        row = {
            **solution_to_metrics_row(solution),
            **row_base,
            **bks_gap_fields(
                solution.instance_name,
                vehicles_used=solution.vehicles_used,
                total_distance=solution.total_distance,
            ),
            "selector": _selector_name(solution.metadata),
            "vehicles": solution.vehicles_used,
            "distance": solution.total_distance,
            "cost": solution.objective,
            "solver_status": _solver_status(solution),
            "gap": "",
            "lower_bound": "",
            "best_bound": _best_bound(solution.metadata),
            "gap_or_bound_if_available": _gap_or_bound_if_available(solution.metadata),
            "has_solution": bool(solution.routes),
            "route_count": len(solution.routes),
            "customer_count": len(instance.customer_ids),
            "status": _solver_status(solution),
            "pipeline_status": "ok",
            "error": "",
            "solution_json": str(solution_json),
            "convergence_csv": str(convergence_csv) if convergence_csv is not None else "",
        }
    except Exception as exc:
        row = {
            **row_base,
            "selector": "",
            "vehicles_used": "",
            "total_distance": "",
            "total_duration": "",
            "objective": "",
            "iterations": "",
            "best_iteration": "",
            "vehicles": "",
            "distance": "",
            "cost": "",
            "runtime_sec": "",
            "feasible": False,
            **bks_gap_fields("", vehicles_used=0, total_distance=0.0),
            "solver_status": "error",
            "gap": "",
            "lower_bound": "",
            "best_bound": "",
            "gap_or_bound_if_available": "",
            "has_solution": False,
            "route_count": "",
            "customer_count": "",
            "status": "error",
            "pipeline_status": "error",
            "error": str(exc),
            "solution_json": "",
            "convergence_csv": "",
        }
    return row


def _config_for_solver(base_config: dict[str, Any], solver_spec: SolverSpec) -> dict[str, Any]:
    config = deepcopy(base_config)
    ablation_config = _mapping(config.get("ablation", {}))
    ablation_config["name"] = solver_spec.ablation
    config["ablation"] = ablation_config
    if solver_spec.alns_overrides:
        alns_config = _mapping(config.get("alns", {}))
        alns_config.update(solver_spec.alns_overrides)
        config["alns"] = alns_config
    return config


def _instance_specs(
    experiment_config: dict[str, Any],
    config_dir: Path,
) -> tuple[InstanceSpec, ...]:
    raw_instances = experiment_config.get("instances")
    if raw_instances is None:
        raise ValueError("experiment.instances is required")
    if not isinstance(raw_instances, list):
        raise ValueError("experiment.instances must be a list")

    specs: list[InstanceSpec] = []
    for item in raw_instances:
        if isinstance(item, str):
            path = _resolve_path(item, config_dir)
            specs.append(InstanceSpec(name=path.stem, path=path))
        elif isinstance(item, dict):
            raw_path = item.get("path")
            if raw_path is None:
                raise ValueError("experiment.instances entries require path")
            path = _resolve_path(str(raw_path), config_dir)
            specs.append(
                InstanceSpec(
                    name=str(item.get("name", path.stem)),
                    path=path,
                    limit_customers=_optional_int(item.get("limit_customers")),
                )
            )
        else:
            raise ValueError("experiment.instances entries must be strings or mappings")
    return tuple(specs)


def _solver_specs(experiment_config: dict[str, Any]) -> tuple[SolverSpec, ...]:
    raw_solvers = experiment_config.get("solvers")
    if raw_solvers is None:
        raise ValueError("experiment.solvers is required")
    if not isinstance(raw_solvers, list):
        raise ValueError("experiment.solvers must be a list")

    specs: list[SolverSpec] = []
    for item in raw_solvers:
        if isinstance(item, str):
            specs.append(SolverSpec(name=item, solver=item, ablation=item, alns_overrides={}))
        elif isinstance(item, dict):
            solver = str(item.get("solver", item.get("name", "")))
            if not solver:
                raise ValueError("experiment.solvers mapping entries require solver or name")
            name = str(item.get("name", solver))
            specs.append(
                SolverSpec(
                    name=name,
                    solver=solver,
                    ablation=str(item.get("ablation", name)),
                    alns_overrides=_mapping(item.get("alns", {})),
                )
            )
        else:
            raise ValueError("experiment.solvers entries must be strings or mappings")
    return tuple(specs)


def _solution_json_path(
    solution_dir: Path,
    instance_spec: InstanceSpec,
    solver_spec: SolverSpec,
    seed: int,
) -> Path:
    filename = f"{instance_spec.name}__{solver_spec.name}__seed{seed}.json"
    return solution_dir / filename.replace(" ", "_")


def _convergence_csv_path(
    convergence_dir: Path,
    instance_spec: InstanceSpec,
    solver_spec: SolverSpec,
    seed: int,
) -> Path:
    filename = f"{instance_spec.name}__{solver_spec.name}__seed{seed}.csv"
    return convergence_dir / filename.replace(" ", "_")


def _save_convergence_if_available(
    *,
    solution: Solution,
    convergence_dir: Path,
    instance_spec: InstanceSpec,
    solver_spec: SolverSpec,
    seed: int,
) -> Path | None:
    history = solution.metadata.get("history", [])
    if not isinstance(history, list) or not history:
        return None
    path = _convergence_csv_path(convergence_dir, instance_spec, solver_spec, seed)
    return save_convergence_csv(solution, path)


def _with_feasibility_report(
    solution: Solution,
    report: FeasibilityReport,
) -> Solution:
    return Solution(
        instance_name=solution.instance_name,
        solver_name=solution.solver_name,
        routes=solution.routes,
        objective=solution.objective,
        vehicles_used=solution.vehicles_used,
        total_distance=solution.total_distance,
        total_duration=solution.total_duration,
        feasible=report.feasible,
        runtime_sec=solution.runtime_sec,
        metadata={
            **solution.metadata,
            "feasibility_violations": list(report.violations),
        },
    )


def _selector_name(metadata: dict[str, Any]) -> str:
    selector = metadata.get("selector")
    if isinstance(selector, dict):
        return str(selector.get("name", ""))
    return ""


def _solver_status(solution: Solution) -> str:
    status = solution.metadata.get("status")
    if status is not None:
        return str(status)
    return "FEASIBLE" if solution.feasible else "INFEASIBLE"


def _gap_or_bound_if_available(metadata: dict[str, Any]) -> Any:
    best_bound = _best_bound(metadata)
    if best_bound != "":
        return best_bound
    return ""


def _best_bound(metadata: dict[str, Any]) -> Any:
    best_bound = metadata.get("best_bound")
    if best_bound is not None:
        return best_bound
    return ""


def _configured_path(value: object, *, default: Path) -> Path:
    if value is None or value == "":
        return default
    return Path(str(value))


def _time_limit_for_solver(
    experiment_config: dict[str, Any],
    solver_spec: SolverSpec,
    *,
    default: float | None,
) -> float | None:
    time_limits = _mapping(experiment_config.get("time_limits", {}))
    aliases = [solver_spec.name, solver_spec.solver]
    solver_key = solver_spec.solver.lower()
    if solver_key.startswith("alns"):
        aliases.append("alns")
    if solver_key in {"cp_sat", "exact_cp_sat"}:
        aliases.append("cp_sat")
    if solver_key in {"ortools", "ortools_routing"}:
        aliases.extend(["ortools", "ortools_routing"])

    for alias in aliases:
        if alias in time_limits:
            return _optional_float(time_limits[alias])
    return default


def _resolve_path(raw_path: str, config_dir: Path) -> Path:
    path = Path(raw_path)
    if path.is_absolute() or path.exists():
        return path
    return config_dir / path


def _mapping(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _int_list(value: object, field_name: str) -> tuple[int, ...]:
    if isinstance(value, int):
        return (value,)
    if isinstance(value, list | tuple):
        return tuple(int(item) for item in value)
    raise ValueError(f"{field_name} must be an integer or list of integers")


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, str | int | float):
        return int(value)
    raise ValueError("expected an integer-compatible value")


def _optional_float(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, str | int | float):
        return float(value)
    raise ValueError("expected a float-compatible value")
