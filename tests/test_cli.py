import json
from pathlib import Path

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


def test_solve_command_records_ablation_and_filters_alns_operators(tmp_path: Path) -> None:
    config_path = tmp_path / "ablation.yaml"
    output_path = tmp_path / "solution.json"
    config_path.write_text(
        """
seed: 42
ablation:
  name: alns_mosade_no_shaw_destroy
objective:
  vehicle_weight: 100000.0
solver:
  time_limit_sec: 3
  max_iterations: 8
alns:
  selector: mosade
  disabled_destroy_operators: [shaw_related_removal]
  disabled_repair_operators: [regret_2_insertion, regret_3_insertion]
""",
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        [
            "solve",
            "--instance",
            "tests/fixtures/mini_solomon.txt",
            "--solver",
            "alns_mosade",
            "--config",
            str(config_path),
            "--seed",
            "42",
            "--output",
            str(output_path),
        ],
    )

    assert result.exit_code == 0
    data = json.loads(output_path.read_text(encoding="utf-8"))
    metadata = data["metadata"]
    selected_destroy = {entry["destroy"] for entry in metadata["history"]}
    selected_repair = {entry["repair"] for entry in metadata["history"]}

    assert metadata["ablation"] == "alns_mosade_no_shaw_destroy"
    assert metadata["selector"]["name"] == "mosade_inspired"
    assert "shaw_related_removal" not in metadata["destroy_operators"]
    assert "shaw_related_removal" not in selected_destroy
    assert "regret_2_insertion" not in metadata["repair_operators"]
    assert "regret_3_insertion" not in selected_repair
