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


def test_todo_command_echoes_parameter_values() -> None:
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
    assert "TODO solve" in result.output
    assert "solver: greedy" in result.output
    assert "seed: 123" in result.output
