"""Command-line interface for the VRPTW hybrid solver project."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any

import typer

from vrptw_hybrid import __version__
from vrptw_hybrid.core.models import Solution, VRPTWInstance
from vrptw_hybrid.core.solution_io import save_solution_json
from vrptw_hybrid.data.solomon import parse_solomon
from vrptw_hybrid.solvers import (
    ALNSSolver,
    CPSATRuntimeError,
    CPSATVRPTWSolver,
    GreedySolver,
    ORToolsRoutingSolver,
)
from vrptw_hybrid.utils.config import load_config
from vrptw_hybrid.utils.logging import setup_logging

app = typer.Typer(
    help="Run VRPTW validation, solvers, experiments, and reporting tools.",
    no_args_is_help=True,
)

ConfigOption = Annotated[
    Path,
    typer.Option("--config", "-c", help="Path to a YAML configuration file."),
]
InstanceOption = Annotated[
    Path,
    typer.Option("--instance", "-i", help="Path to a VRPTW instance file."),
]
OutputOption = Annotated[
    Path | None,
    typer.Option("--output", "-o", help="Optional output file or directory."),
]


@app.callback()
def main(
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Enable debug-level logging."),
    ] = False,
) -> None:
    """Configure shared CLI behavior."""

    setup_logging("DEBUG" if verbose else "INFO")


@app.command()
def info(
    config: ConfigOption = Path("configs/default.yaml"),
) -> None:
    """Print package and default configuration information."""

    typer.echo(f"vrptw-hybrid {__version__}")
    typer.echo(f"config: {config}")
    if config.exists():
        loaded = load_config(config)
        typer.echo(f"seed: {loaded.get('seed')}")
        typer.echo(f"vehicle_weight: {loaded.get('objective', {}).get('vehicle_weight')}")
    else:
        typer.echo("config_status: missing")


@app.command()
def validate_instance(
    instance: InstanceOption,
    config: ConfigOption = Path("configs/default.yaml"),
) -> None:
    """Validate an instance file once parsers and checkers are implemented."""

    _echo_todo(
        "validate-instance",
        instance=instance,
        config=config,
        detail="will parse a VRPTW instance and run feasibility/data checks",
    )


@app.command()
def solve(
    instance: InstanceOption,
    solver: Annotated[
        str,
        typer.Option("--solver", "-s", help="Solver name, e.g. greedy, cp_sat, alns."),
    ] = "greedy",
    config: ConfigOption = Path("configs/default.yaml"),
    seed: Annotated[int | None, typer.Option("--seed", help="Random seed.")] = None,
    time_limit: Annotated[
        float | None,
        typer.Option("--time-limit", help="Solver time limit in seconds."),
    ] = None,
    max_iterations: Annotated[
        int | None,
        typer.Option("--max-iterations", help="Maximum heuristic iterations."),
    ] = None,
    output: OutputOption = None,
) -> None:
    """Solve a Solomon-format instance with an implemented solver."""

    loaded_config = load_config(config)
    instance_obj = parse_solomon(instance)
    solution = _run_solver(
        solver_name=solver,
        instance=instance_obj,
        config=loaded_config,
        seed=seed,
        time_limit=time_limit,
        max_iterations=max_iterations,
    )
    typer.echo(
        f"solver={solution.solver_name} feasible={solution.feasible} "
        f"vehicles={solution.vehicles_used} distance={solution.total_distance:.3f} "
        f"runtime_sec={solution.runtime_sec:.3f}"
    )
    if output is not None:
        save_solution_json(solution, output)
        typer.echo(f"solution_json: {output}")


@app.command()
def batch(
    config: ConfigOption,
    output: OutputOption = Path("data/results"),
) -> None:
    """Run a batch experiment once experiment orchestration is implemented."""

    _echo_todo(
        "batch",
        config=config,
        output=output,
        detail="will execute configured experiment runs and save metrics",
    )


@app.command()
def plot(
    results: Annotated[
        Path,
        typer.Option("--results", "-r", help="Path to experiment CSV/JSON results."),
    ],
    output: OutputOption = None,
) -> None:
    """Generate plots once experiment reporting is implemented."""

    _echo_todo(
        "plot",
        results=results,
        output=output,
        detail="will generate convergence and comparison figures",
    )


def _echo_todo(command: str, **fields: object) -> None:
    detail = fields.pop("detail", "implementation pending")
    typer.echo(f"TODO {command}: {detail}.")
    for key, value in fields.items():
        typer.echo(f"{key}: {value}")


def _run_solver(
    *,
    solver_name: str,
    instance: VRPTWInstance,
    config: dict[str, Any],
    seed: int | None,
    time_limit: float | None,
    max_iterations: int | None,
) -> Solution:
    solver_key = solver_name.lower()
    solver_config = config.get("solver", {})
    objective_config = config.get("objective", {})
    if not isinstance(solver_config, dict):
        solver_config = {}
    if not isinstance(objective_config, dict):
        objective_config = {}

    vehicle_weight = float(objective_config.get("vehicle_weight", 100000.0))
    default_time_limit = float(solver_config.get("time_limit_sec", 60.0))
    effective_time_limit = default_time_limit if time_limit is None else time_limit
    effective_max_iterations = int(solver_config.get("max_iterations", 1000))
    if max_iterations is not None:
        effective_max_iterations = max_iterations

    if solver_key == "greedy":
        return GreedySolver(vehicle_weight=vehicle_weight, seed=seed).solve(instance, seed=seed)
    if solver_key in {"alns", "alns_uniform"}:
        return ALNSSolver(
            max_iterations=effective_max_iterations,
            time_limit_sec=effective_time_limit,
            vehicle_weight=vehicle_weight,
            seed=seed,
        ).solve(instance, seed=seed)
    if solver_key in {"ortools", "ortools_routing"}:
        return ORToolsRoutingSolver(
            time_limit_sec=effective_time_limit,
            vehicle_weight=vehicle_weight,
        ).solve(instance, seed=seed)
    if solver_key in {"cp_sat", "exact_cp_sat"}:
        try:
            return CPSATVRPTWSolver(
                time_limit_sec=effective_time_limit,
                vehicle_weight=vehicle_weight,
            ).solve(instance, seed=seed)
        except CPSATRuntimeError as exc:
            raise typer.BadParameter(str(exc), param_hint="--solver") from exc
    raise typer.BadParameter(f"Unknown solver: {solver_name}", param_hint="--solver")


if __name__ == "__main__":
    app()
