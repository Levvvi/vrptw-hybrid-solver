import csv
from pathlib import Path

import pytest

from vrptw_hybrid.experiments.statistics import analyze_runs_csv, pairwise_comparisons


def run_row(
    instance: str,
    solver: str,
    seed: int | str,
    cost: int | str,
    *,
    feasible: bool | str = True,
    status: str = "ok",
    runtime_sec: int | str = 1,
) -> dict[str, object]:
    return {
        "instance": instance,
        "solver": solver,
        "seed": seed,
        "cost": cost,
        "runtime_sec": runtime_sec,
        "feasible": feasible,
        "status": status,
    }


def write_runs_csv(path: Path) -> None:
    rows = [
        run_row("i1", "A", 1, 90),
        run_row("i1", "B", 1, 100),
        run_row("i1", "C", 1, "", feasible=False, status="error", runtime_sec=""),
        run_row("i1", "A", 2, 91),
        run_row("i1", "B", 2, 101),
        run_row("i1", "C", 2, 105),
        run_row("i2", "A", 1, 80, runtime_sec=2),
        run_row("i2", "B", 1, 95, runtime_sec=2),
        run_row("i2", "C", 1, 98, runtime_sec=2),
    ]
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def test_analyze_runs_csv_writes_summary_and_pairwise_outputs(tmp_path: Path) -> None:
    runs_csv = tmp_path / "runs.csv"
    output_dir = tmp_path / "stats"
    write_runs_csv(runs_csv)

    result = analyze_runs_csv(runs_csv, output_dir=output_dir)
    summary_by_solver = {row["solver"]: row for row in result.summary_rows}
    pair_ab = next(
        row for row in result.pairwise_rows if row["solver_a"] == "A" and row["solver_b"] == "B"
    )

    assert result.summary_csv is not None and result.summary_csv.exists()
    assert result.pairwise_csv is not None and result.pairwise_csv.exists()
    assert summary_by_solver["A"]["valid_runs"] == 3
    assert summary_by_solver["C"]["failed_runs"] == 1
    assert summary_by_solver["C"]["feasible_rate"] == pytest.approx(2 / 3)
    assert pair_ab["paired_n"] == 3
    assert pair_ab["mean_diff_a_minus_b"] < 0
    assert pair_ab["effect_size_rank_biserial"] < 0
    assert pair_ab["better_solver"] == "A"
    assert "p_value_holm" in pair_ab
    assert "reject_0_05" in pair_ab


def test_pairwise_comparisons_handles_missing_or_failed_runs() -> None:
    rows = [
        run_row("i1", "A", "1", "10", feasible="True"),
        run_row("i1", "B", "1", "", feasible="False", status="error"),
        run_row("i2", "A", "1", "11", feasible="True"),
        run_row("i2", "B", "1", "12", feasible="True"),
    ]

    comparisons = pairwise_comparisons(rows)

    assert comparisons[0]["paired_n"] == 1
    assert comparisons[0]["p_value"] == 1.0
    assert comparisons[0]["better_solver"] == "A"
