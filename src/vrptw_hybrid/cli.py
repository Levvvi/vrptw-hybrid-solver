"""Command-line interface for the VRPTW hybrid solver project."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any

import typer

from vrptw_hybrid import __version__
from vrptw_hybrid.core.models import Solution, VRPTWInstance
from vrptw_hybrid.core.solution_io import save_solution_json
from vrptw_hybrid.data.solomon import parse_solomon
from vrptw_hybrid.experiments.plots import generate_report_figures
from vrptw_hybrid.experiments.runner import plan_batch, run_batch
from vrptw_hybrid.solvers.dispatch import SolverDispatchError, run_solver_from_config
from vrptw_hybrid.utils.config import load_config
from vrptw_hybrid.utils.logging import setup_logging
from vrptw_hybrid.visualization.benchmark_plot import (
    plot_benchmark_routes_matplotlib,
    plot_benchmark_routes_plotly,
)
from vrptw_hybrid.visualization.route_artifacts import (
    RouteArtifactError,
    build_benchmark_route_artifact,
    save_route_artifact,
    select_run_row,
)

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
    output_json: Annotated[
        Path | None,
        typer.Option("--output-json", help="Write solution JSON to this path."),
    ] = None,
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
    output_path = output_json or output
    if output_path is not None:
        save_solution_json(solution, output_path)
        typer.echo(f"solution_json: {output_path}")


@app.command()
def batch(
    config: ConfigOption,
    output: OutputOption = None,
    output_csv: Annotated[
        Path | None,
        typer.Option("--output-csv", help="Write run metrics CSV to this exact path."),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Print the planned run matrix without executing solvers."),
    ] = False,
) -> None:
    """Run a configured batch experiment and save metrics."""

    try:
        if dry_run:
            planned = plan_batch(config)
            typer.echo(f"planned_runs: {len(planned)}")
            for row in planned:
                typer.echo(
                    f"instance={row['instance']} solver={row['solver']} seed={row['seed']}"
                )
            return
        result = run_batch(config, output_dir=output, output_csv=output_csv)
    except Exception as exc:
        raise typer.BadParameter(str(exc), param_hint="--config") from exc
    typer.echo(f"runs_csv: {result.csv_path}")
    typer.echo(f"solution_dir: {result.solution_dir}")
    typer.echo(f"convergence_dir: {result.convergence_dir}")
    typer.echo(f"runs: {len(result.rows)}")


@app.command()
def plot(
    results: Annotated[
        Path | None,
        typer.Option("--results", "-r", help="Path to experiment CSV/JSON results."),
    ] = None,
    output: OutputOption = None,
    benchmark: Annotated[
        bool,
        typer.Option("--benchmark", help="Plot one benchmark x-y route from a run CSV."),
    ] = False,
    run_csv: Annotated[
        Path | None,
        typer.Option("--run-csv", help="Run CSV for benchmark route selection."),
    ] = None,
    instance: Annotated[
        str | None,
        typer.Option("--instance", help="Instance alias in the run CSV."),
    ] = None,
    solver: Annotated[
        str | None,
        typer.Option("--solver", help="Solver alias in the run CSV."),
    ] = None,
    seed: Annotated[
        int | None,
        typer.Option("--seed", help="Seed in the run CSV."),
    ] = None,
    output_png: Annotated[
        Path | None,
        typer.Option("--output-png", help="Benchmark route PNG output path."),
    ] = None,
    output_artifact: Annotated[
        Path | None,
        typer.Option("--output-artifact", help="Benchmark route artifact JSON output path."),
    ] = None,
    output_html: Annotated[
        Path | None,
        typer.Option("--output-html", help="Optional benchmark route Plotly HTML output path."),
    ] = None,
) -> None:
    """Generate report figures or a benchmark x-y route plot."""

    if benchmark:
        _plot_benchmark_route(
            run_csv=run_csv,
            instance=instance,
            solver=solver,
            seed=seed,
            output_png=output_png,
            output_artifact=output_artifact,
            output_html=output_html,
        )
        return

    if results is None:
        raise typer.BadParameter("--results is required unless --benchmark is set")
    output_dir = output or Path("reports/figures")
    outputs = generate_report_figures(results, output_dir)
    for path in outputs.paths:
        typer.echo(f"figure: {path}")


def _plot_benchmark_route(
    *,
    run_csv: Path | None,
    instance: str | None,
    solver: str | None,
    seed: int | None,
    output_png: Path | None,
    output_artifact: Path | None,
    output_html: Path | None,
) -> None:
    missing = [
        name
        for name, value in {
            "--run-csv": run_csv,
            "--instance": instance,
            "--solver": solver,
            "--seed": seed,
            "--output-png": output_png,
            "--output-artifact": output_artifact,
        }.items()
        if value is None
    ]
    if missing:
        raise typer.BadParameter(f"missing required benchmark options: {', '.join(missing)}")

    assert run_csv is not None
    assert instance is not None
    assert solver is not None
    assert seed is not None
    assert output_png is not None
    assert output_artifact is not None

    try:
        row = select_run_row(run_csv, instance=instance, solver=solver, seed=seed)
        artifact = build_benchmark_route_artifact(
            row["source_file"],
            row["solution_json"],
            row,
        )
        artifact_path = save_route_artifact(artifact, output_artifact)
        png_path = plot_benchmark_routes_matplotlib(artifact, output_png)
        typer.echo(f"artifact: {artifact_path}")
        typer.echo(f"png: {png_path}")
        if output_html is not None:
            html_path = plot_benchmark_routes_plotly(artifact, output_html)
            typer.echo(f"html: {html_path}")
        typer.echo(
            "status="
            f"{artifact.get('status')} feasible={artifact.get('feasible')} "
            f"has_solution={artifact.get('has_solution')}"
        )
        if not artifact.get("has_solution"):
            typer.echo("No route available for this run under the configured time budget.")
    except (FileNotFoundError, KeyError, RouteArtifactError) as exc:
        raise typer.BadParameter(str(exc), param_hint="--run-csv") from exc


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
    try:
        return run_solver_from_config(
            solver_name=solver_name,
            instance=instance,
            config=config,
            seed=seed,
            time_limit=time_limit,
            max_iterations=max_iterations,
        )
    except SolverDispatchError as exc:
        raise typer.BadParameter(str(exc), param_hint="--solver") from exc


if __name__ == "__main__":
    app()
