from typer.testing import CliRunner

from vrptw_hybrid.cli import app

runner = CliRunner()


def test_info_command_prints_version_and_config() -> None:
    result = runner.invoke(app, ["info"])

    assert result.exit_code == 0
    assert "vrptw-hybrid 0.1.0" in result.output
    assert "seed: 42" in result.output
    assert "vehicle_weight: 100000.0" in result.output


def test_solve_help_exposes_reserved_parameters() -> None:
    result = runner.invoke(app, ["solve", "--help"])

    assert result.exit_code == 0
    assert "--instance" in result.output
    assert "--solver" in result.output
    assert "--time-limit" in result.output
    assert "--max-iterations" in result.output


def test_solve_command_runs_greedy_solver() -> None:
    result = runner.invoke(
        app,
        [
            "solve",
            "--instance",
            "tests/fixtures/mini_solomon.txt",
            "--solver",
            "greedy",
            "--seed",
            "123",
        ],
    )

    assert result.exit_code == 0
    assert "solver=greedy" in result.output
    assert "feasible=True" in result.output


def test_solve_command_runs_alns_solver() -> None:
    result = runner.invoke(
        app,
        [
            "solve",
            "--instance",
            "tests/fixtures/mini_solomon.txt",
            "--solver",
            "alns",
            "--seed",
            "42",
            "--max-iterations",
            "5",
        ],
    )

    assert result.exit_code == 0
    assert "solver=alns" in result.output
    assert "feasible=True" in result.output
