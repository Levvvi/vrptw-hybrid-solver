import csv
from pathlib import Path

from vrptw_hybrid.experiments.runner import plan_batch, run_batch


def write_batch_config(tmp_path: Path, solvers: str) -> Path:
    config_path = tmp_path / "batch.yaml"
    output_dir = (tmp_path / "results").as_posix()
    config_path.write_text(
        f"""
seed: 42
objective:
  vehicle_weight: 100000.0
solver:
  time_limit_sec: 3
  max_iterations: 5
alns:
  selector: uniform
  segment_length: 2
  reaction_factor: 0.5
  exploration_floor: 0.05
  temperature: 1.0
  decay: 0.8
  memory_size: 10
  candidate_neighbor_size: 4
experiment:
  output_dir: {output_dir}
  instances:
    - name: mini_c101_8
      path: tests/fixtures/mini_solomon.txt
      limit_customers: 8
  solvers:
{solvers}
  seeds: [42]
  time_limit_sec: 3
  max_iterations: 5
""",
        encoding="utf-8",
    )
    return config_path


def test_run_batch_writes_csv_and_solution_jsons(tmp_path: Path) -> None:
    config_path = write_batch_config(
        tmp_path,
        """
    - name: greedy
      solver: greedy
      ablation: greedy
    - name: alns_uniform
      solver: alns_uniform
      ablation: alns_uniform
    - name: alns_mosade
      solver: alns_mosade
      ablation: alns_mosade_adaptive
      alns:
        selector: mosade
""",
    )

    result = run_batch(config_path, timestamp="unit")

    assert result.csv_path.exists()
    assert result.solution_dir.exists()
    assert result.convergence_dir.exists()
    assert len(result.rows) == 3
    assert {row["solver"] for row in result.rows} == {"greedy", "alns_uniform", "alns_mosade"}
    assert {row["pipeline_status"] for row in result.rows} == {"ok"}
    assert all(Path(row["solution_json"]).exists() for row in result.rows)
    assert all("solver_status" in row for row in result.rows)
    assert all("gap_or_bound_if_available" in row for row in result.rows)
    assert all("time_limit_sec" in row for row in result.rows)
    assert all("has_solution" in row for row in result.rows)
    assert all("customer_count" in row for row in result.rows)
    assert all("config_file" in row for row in result.rows)
    assert all("created_at" in row for row in result.rows)
    assert all(
        Path(row["convergence_csv"]).exists()
        for row in result.rows
        if row["solver"].startswith("alns")
    )

    with result.csv_path.open("r", encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))

    assert len(rows) == 3
    assert {"instance", "solver", "selector", "seed", "vehicles", "distance"}.issubset(
        rows[0]
    )
    assert {"cost", "runtime_sec", "feasible", "status", "pipeline_status", "error"}.issubset(
        rows[0]
    )
    assert {"solver_status", "gap_or_bound_if_available", "convergence_csv"}.issubset(rows[0])
    assert {"time_limit_sec", "has_solution", "customer_count", "config_file"}.issubset(rows[0])
    assert {"bks_vehicles", "vehicle_gap", "distance_gap_pct"}.issubset(rows[0])
    assert rows[0]["bks_vehicles"] == ""


def test_run_batch_can_write_fixed_output_csv(tmp_path: Path) -> None:
    config_path = write_batch_config(
        tmp_path,
        """
    - name: greedy
      solver: greedy
      ablation: greedy
""",
    )
    output_csv = tmp_path / "fixed_runs.csv"

    result = run_batch(config_path, output_csv=output_csv, timestamp="ignored")

    assert result.csv_path == output_csv
    assert output_csv.exists()


def test_plan_batch_returns_configured_matrix(tmp_path: Path) -> None:
    config_path = write_batch_config(
        tmp_path,
        """
    - name: greedy
      solver: greedy
      ablation: greedy
    - name: alns_uniform
      solver: alns_uniform
      ablation: alns_uniform
""",
    )

    planned = plan_batch(config_path)

    assert len(planned) == 2
    assert {row["solver"] for row in planned} == {"greedy", "alns_uniform"}


def test_run_batch_records_solver_errors_without_stopping(tmp_path: Path) -> None:
    config_path = write_batch_config(
        tmp_path,
        """
    - name: bad_solver
      solver: does_not_exist
      ablation: bad_solver
    - name: greedy
      solver: greedy
      ablation: greedy
""",
    )

    result = run_batch(config_path, timestamp="errors")
    rows_by_solver = {row["solver"]: row for row in result.rows}

    assert rows_by_solver["bad_solver"]["pipeline_status"] == "error"
    assert rows_by_solver["bad_solver"]["status"] == "error"
    assert "Unknown solver" in rows_by_solver["bad_solver"]["error"]
    assert rows_by_solver["greedy"]["pipeline_status"] == "ok"


def test_run_batch_populates_bks_fields_when_reference_exists(tmp_path: Path) -> None:
    source_fixture = Path("tests/fixtures/mini_solomon.txt")
    c101_fixture = tmp_path / "c101_smoke.txt"
    c101_fixture.write_text(
        source_fixture.read_text(encoding="utf-8").replace("MINI_C101", "C101", 1),
        encoding="utf-8",
    )
    config_path = tmp_path / "bks_batch.yaml"
    output_dir = (tmp_path / "results").as_posix()
    config_path.write_text(
        f"""
seed: 42
objective:
  vehicle_weight: 100000.0
solver:
  time_limit_sec: 3
  max_iterations: 1
experiment:
  output_dir: {output_dir}
  instances:
    - name: c101_smoke
      path: {c101_fixture.as_posix()}
  solvers:
    - name: greedy
      solver: greedy
      ablation: greedy
  seeds: [42]
""",
        encoding="utf-8",
    )

    result = run_batch(config_path, timestamp="bks")
    row = result.rows[0]

    assert row["pipeline_status"] == "ok"
    assert row["bks_vehicles"] == 10
    assert row["bks_distance"] == 828.94
    assert row["vehicle_gap"] == row["vehicles"] - 10
    assert row["distance_gap"] is None
