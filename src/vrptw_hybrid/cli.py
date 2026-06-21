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
from vrptw_hybrid.solvers.alns.operator_filters import (
    filter_destroy_operators,
    filter_repair_operators,
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
    alns_config = config.get("alns", {})
    if not isinstance(alns_config, dict):
        alns_config = {}
    ablation_config = config.get("ablation", {})
    if not isinstance(ablation_config, dict):
        ablation_config = {}
    ablation_name = str(ablation_config.get("name", "default"))
    selector_name = str(alns_config.get("selector", "uniform"))
    segment_length = int(alns_config.get("segment_length", 100))
    reaction_factor = float(alns_config.get("reaction_factor", 0.2))
    exploration_floor = float(alns_config.get("exploration_floor", 0.05))
    temperature = float(alns_config.get("temperature", 1.0))
    decay = float(alns_config.get("decay", 0.8))
    memory_size = int(alns_config.get("memory_size", 50))
    use_pair_memory = _bool_config(
        alns_config.get("use_pair_memory", True),
        "alns.use_pair_memory",
    )
    use_diversity_bonus = _bool_config(
        alns_config.get("use_diversity_bonus", True),
        "alns.use_diversity_bonus",
    )

    if solver_key == "greedy":
        return _with_ablation(
            GreedySolver(vehicle_weight=vehicle_weight, seed=seed).solve(instance, seed=seed),
            ablation_name,
        )
    if solver_key in {
        "alns",
        "alns_uniform",
        "alns_roulette",
        "alns_mosade",
        "alns_mosade_adaptive",
    }:
        try:
            destroy_operators = filter_destroy_operators(
                enabled_names=_optional_name_list(
                    alns_config.get("enabled_destroy_operators"),
                    "alns.enabled_destroy_operators",
                ),
                disabled_names=_optional_name_list(
                    alns_config.get("disabled_destroy_operators"),
                    "alns.disabled_destroy_operators",
                ),
            )
            repair_operators = filter_repair_operators(
                enabled_names=_optional_name_list(
                    alns_config.get("enabled_repair_operators"),
                    "alns.enabled_repair_operators",
                ),
                disabled_names=_optional_name_list(
                    alns_config.get("disabled_repair_operators"),
                    "alns.disabled_repair_operators",
                ),
            )
        except ValueError as exc:
            raise typer.BadParameter(str(exc), param_hint="--config") from exc

        effective_selector_name = _selector_name_from_solver_alias(solver_key, selector_name)
        return _with_ablation(
            ALNSSolver(
                max_iterations=effective_max_iterations,
                time_limit_sec=effective_time_limit,
                vehicle_weight=vehicle_weight,
                seed=seed,
                destroy_operators=destroy_operators,
                repair_operators=repair_operators,
                selector_name=effective_selector_name,
                segment_length=segment_length,
                reaction_factor=reaction_factor,
                exploration_floor=exploration_floor,
                temperature=temperature,
                decay=decay,
                memory_size=memory_size,
                use_pair_memory=use_pair_memory,
                use_diversity_bonus=use_diversity_bonus,
                ablation_name=ablation_name,
            ).solve(instance, seed=seed),
            ablation_name,
        )
    if solver_key in {"ortools", "ortools_routing"}:
        return _with_ablation(
            ORToolsRoutingSolver(
                time_limit_sec=effective_time_limit,
                vehicle_weight=vehicle_weight,
            ).solve(instance, seed=seed),
            ablation_name,
        )
    if solver_key in {"cp_sat", "exact_cp_sat"}:
        try:
            return _with_ablation(
                CPSATVRPTWSolver(
                    time_limit_sec=effective_time_limit,
                    vehicle_weight=vehicle_weight,
                ).solve(instance, seed=seed),
                ablation_name,
            )
        except CPSATRuntimeError as exc:
            raise typer.BadParameter(str(exc), param_hint="--solver") from exc
    raise typer.BadParameter(f"Unknown solver: {solver_name}", param_hint="--solver")


def _optional_name_list(value: object, field_name: str) -> tuple[str, ...] | None:
    if value is None:
        return None
    if isinstance(value, str):
        return (value,)
    if isinstance(value, list | tuple):
        return tuple(str(item) for item in value)
    raise typer.BadParameter(
        f"{field_name} must be a string or list of strings",
        param_hint="--config",
    )


def _bool_config(value: object, field_name: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    raise typer.BadParameter(f"{field_name} must be a boolean", param_hint="--config")


def _selector_name_from_solver_alias(solver_key: str, configured_selector: str) -> str:
    if solver_key == "alns_uniform":
        return "uniform"
    if solver_key == "alns_roulette":
        return "roulette"
    if solver_key in {"alns_mosade", "alns_mosade_adaptive"}:
        return "mosade"
    return configured_selector


def _with_ablation(solution: Solution, ablation_name: str) -> Solution:
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
        metadata={**solution.metadata, "ablation": ablation_name},
    )


if __name__ == "__main__":
    app()
