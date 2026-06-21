"""Command-line interface for the VRPTW hybrid solver project."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from vrptw_hybrid import __version__
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
    """Solve an instance once solver implementations are available."""

    _echo_todo(
        "solve",
        instance=instance,
        solver=solver,
        config=config,
        seed=seed,
        time_limit=time_limit,
        max_iterations=max_iterations,
        output=output,
        detail="will run a solver and write a unified Solution object",
    )


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


if __name__ == "__main__":
    app()
