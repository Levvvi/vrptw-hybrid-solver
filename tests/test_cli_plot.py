import csv
from pathlib import Path

from typer.testing import CliRunner

from vrptw_hybrid.cli import app
from vrptw_hybrid.core.solution_io import save_solution_json
from vrptw_hybrid.data.solomon import parse_solomon
from vrptw_hybrid.solvers.greedy import solve_greedy

runner = CliRunner()
FIXTURE = Path("tests/fixtures/mini_solomon.txt")


def test_plot_benchmark_command_writes_artifact_and_png(tmp_path: Path) -> None:
    runs_csv = _write_run_csv(tmp_path, instance="mini", solver="greedy", seed=42)
    artifact_path = tmp_path / "artifact.json"
    png_path = tmp_path / "route.png"

    result = runner.invoke(
        app,
        [
            "plot",
            "--benchmark",
            "--run-csv",
            str(runs_csv),
            "--instance",
            "mini",
            "--solver",
            "greedy",
            "--seed",
            "42",
            "--output-png",
            str(png_path),
            "--output-artifact",
            str(artifact_path),
        ],
    )

    assert result.exit_code == 0
    assert "artifact:" in result.output
    assert "png:" in result.output
    assert "has_solution=True" in result.output
    assert artifact_path.exists()
    assert png_path.exists()
    assert png_path.stat().st_size > 0


def test_plot_benchmark_command_reports_missing_row(tmp_path: Path) -> None:
    runs_csv = _write_run_csv(tmp_path, instance="mini", solver="greedy", seed=42)

    result = runner.invoke(
        app,
        [
            "plot",
            "--benchmark",
            "--run-csv",
            str(runs_csv),
            "--instance",
            "missing",
            "--solver",
            "greedy",
            "--seed",
            "42",
            "--output-png",
            str(tmp_path / "route.png"),
            "--output-artifact",
            str(tmp_path / "artifact.json"),
        ],
    )

    assert result.exit_code != 0
    assert "no run row found" in result.output


def _write_run_csv(tmp_path: Path, *, instance: str, solver: str, seed: int) -> Path:
    instance_obj = parse_solomon(FIXTURE, limit_customers=8)
    solution = solve_greedy(instance_obj, seed=seed)
    solution_path = tmp_path / "solution.json"
    save_solution_json(solution, solution_path)
    runs_csv = tmp_path / "runs.csv"
    with runs_csv.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "instance",
                "solver",
                "seed",
                "source_file",
                "solution_json",
                "status",
                "pipeline_status",
                "feasible",
                "has_solution",
                "vehicles",
                "distance",
                "objective",
                "runtime_sec",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "instance": instance,
                "solver": solver,
                "seed": seed,
                "source_file": str(FIXTURE),
                "solution_json": str(solution_path),
                "status": "FEASIBLE",
                "pipeline_status": "ok",
                "feasible": True,
                "has_solution": True,
                "vehicles": solution.vehicles_used,
                "distance": solution.total_distance,
                "objective": solution.objective,
                "runtime_sec": solution.runtime_sec,
            }
        )
    return runs_csv
