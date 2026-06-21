import csv
from pathlib import Path

from vrptw_hybrid.experiments.scaling import (
    generate_synthetic_instance,
    run_scaling_experiment,
)


def test_generate_synthetic_instance_is_reproducible() -> None:
    first = generate_synthetic_instance(10, seed=7)
    second = generate_synthetic_instance(10, seed=7)

    assert first.name == "SYNTHETIC_10"
    assert first.customer_ids == second.customer_ids
    assert first.vehicle.count == second.vehicle.count
    assert first.distance_matrix.tolist() == second.distance_matrix.tolist()


def test_run_scaling_experiment_writes_rows_and_errors(tmp_path: Path) -> None:
    output_csv = tmp_path / "scaling.csv"

    result = run_scaling_experiment(
        sizes=(5,),
        solvers=("greedy", "does_not_exist"),
        output_csv=output_csv,
        seed=3,
        max_iterations=1,
        small_time_limit_sec=2.0,
    )

    with output_csv.open("r", encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))
    rows_by_solver = {row["solver"]: row for row in rows}

    assert result.csv_path == output_csv
    assert len(result.rows) == 2
    assert rows_by_solver["greedy"]["status"] in {"ok", "timeout"}
    assert rows_by_solver["does_not_exist"]["status"] == "error"
    assert "Unknown solver" in rows_by_solver["does_not_exist"]["error"]
