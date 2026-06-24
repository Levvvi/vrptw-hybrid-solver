"""Generate EXP-02 medium-scale summaries, statistics, figures, and curated CSVs."""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path
from statistics import fmean, median
from typing import Any

from vrptw_hybrid.core.solution_io import save_metrics_csv
from vrptw_hybrid.experiments.statistics import pairwise_comparisons

RUNS_CSV = Path("data/results/experiments/runs_medium.csv")
SUMMARY_CSV = Path("data/results/experiments/summary_medium.csv")
STAT_TESTS_CSV = Path("data/results/experiments/stat_tests_medium.csv")
CURATED_DIR = Path("reports/results")
FIGURES_DIR = Path("reports/figures")


def main() -> None:
    rows = _read_csv(RUNS_CSV)
    rows = _with_best_observed_gap(rows)
    _write_csv(rows, RUNS_CSV)

    summary_rows = _summary(rows)
    stat_rows = pairwise_comparisons(rows, metric="distance")

    save_metrics_csv(summary_rows, SUMMARY_CSV)
    save_metrics_csv(stat_rows, STAT_TESTS_CSV)

    CURATED_DIR.mkdir(parents=True, exist_ok=True)
    _write_csv(rows, CURATED_DIR / "runs_medium.csv")
    save_metrics_csv(summary_rows, CURATED_DIR / "summary_medium.csv")
    save_metrics_csv(stat_rows, CURATED_DIR / "stat_tests_medium.csv")

    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    _plot_bar(
        FIGURES_DIR / "medium_solver_cost.png",
        title="EXP-02 Mean Objective",
        y_label="Mean objective",
        values=_metric_by_solver(rows, "cost"),
    )
    _plot_bar(
        FIGURES_DIR / "medium_solver_runtime.png",
        title="EXP-02 Mean Runtime",
        y_label="Mean runtime (sec)",
        values=_metric_by_solver(rows, "runtime_sec", require_feasible=False),
    )
    _plot_bar(
        FIGURES_DIR / "medium_feasible_rate.png",
        title="EXP-02 Feasible Rate",
        y_label="Feasible rate",
        values=_feasible_rate_by_solver(rows),
    )
    _plot_convergence(
        rows,
        FIGURES_DIR / "medium_convergence.png",
    )
    _update_figure_sources()
    print(f"wrote {SUMMARY_CSV}")
    print(f"wrote {STAT_TESTS_CSV}")
    print(f"wrote {CURATED_DIR / 'runs_medium.csv'}")
    print(f"wrote {FIGURES_DIR / 'medium_solver_cost.png'}")
    print(f"wrote {FIGURES_DIR / 'medium_solver_runtime.png'}")
    print(f"wrote {FIGURES_DIR / 'medium_feasible_rate.png'}")
    print(f"wrote {FIGURES_DIR / 'medium_convergence.png'}")


def _read_csv(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8", newline="") as file:
        return [dict(row) for row in csv.DictReader(file)]


def _write_csv(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _with_best_observed_gap(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    best_by_instance: dict[str, dict[str, float]] = {}
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get("instance", ""))].append(row)

    for instance, instance_rows in grouped.items():
        valid_rows = [row for row in instance_rows if _valid_solution(row)]
        if not valid_rows:
            continue
        best_vehicles = min(_float(row["vehicles"]) for row in valid_rows)
        vehicle_matched = [
            row for row in valid_rows if _float(row["vehicles"]) == best_vehicles
        ]
        best_distance = min(_float(row["distance"]) for row in vehicle_matched)
        best_objective = min(_float(row["cost"]) for row in valid_rows)
        best_by_instance[instance] = {
            "vehicles": best_vehicles,
            "distance": best_distance,
            "objective": best_objective,
        }

    for row in rows:
        best = best_by_instance.get(str(row.get("instance", "")))
        row["best_observed_vehicles"] = ""
        row["best_observed_distance"] = ""
        row["best_observed_objective"] = ""
        row["vehicle_gap_to_best_observed"] = ""
        row["distance_gap_to_best_observed_pct"] = ""
        row["objective_gap_to_best_observed_pct"] = ""
        if best is None or not _valid_solution(row):
            continue
        vehicles = _float(row["vehicles"])
        distance = _float(row["distance"])
        objective = _float(row["cost"])
        row["best_observed_vehicles"] = best["vehicles"]
        row["best_observed_distance"] = best["distance"]
        row["best_observed_objective"] = best["objective"]
        row["vehicle_gap_to_best_observed"] = vehicles - best["vehicles"]
        if vehicles == best["vehicles"]:
            row["distance_gap_to_best_observed_pct"] = (
                (distance - best["distance"]) / best["distance"] * 100.0
            )
        row["objective_gap_to_best_observed_pct"] = (
            (objective - best["objective"]) / best["objective"] * 100.0
        )
    return rows


def _summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get("solver", ""))].append(row)

    summary_rows: list[dict[str, Any]] = []
    for solver in sorted(grouped):
        solver_rows = grouped[solver]
        valid_rows = [row for row in solver_rows if _valid_solution(row)]
        runtime_values = [
            _float(row["runtime_sec"])
            for row in solver_rows
            if _float_or_none(row.get("runtime_sec")) is not None
        ]
        summary_rows.append(
            {
                "solver": solver,
                "runs": len(solver_rows),
                "valid_runs": len(valid_rows),
                "pipeline_error_runs": sum(
                    1 for row in solver_rows if row.get("pipeline_status") == "error"
                ),
                "has_solution_runs": sum(
                    1 for row in solver_rows if _truthy(row.get("has_solution"))
                ),
                "feasible_rate": len(valid_rows) / len(solver_rows) if solver_rows else None,
                "vehicles_mean": _mean_field(valid_rows, "vehicles"),
                "vehicles_median": _median_field(valid_rows, "vehicles"),
                "distance_mean": _mean_field(valid_rows, "distance"),
                "distance_median": _median_field(valid_rows, "distance"),
                "objective_mean": _mean_field(valid_rows, "cost"),
                "objective_median": _median_field(valid_rows, "cost"),
                "runtime_mean": fmean(runtime_values) if runtime_values else None,
                "runtime_median": median(runtime_values) if runtime_values else None,
                "objective_gap_to_best_observed_pct_mean": _mean_field(
                    valid_rows,
                    "objective_gap_to_best_observed_pct",
                ),
                "distance_gap_to_best_observed_pct_mean": _mean_field(
                    valid_rows,
                    "distance_gap_to_best_observed_pct",
                ),
            }
        )
    return summary_rows


def _metric_by_solver(
    rows: list[dict[str, Any]],
    metric: str,
    *,
    require_feasible: bool = True,
) -> dict[str, float]:
    grouped: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        if require_feasible and not _valid_solution(row):
            continue
        value = _float_or_none(row.get(metric))
        if value is None:
            continue
        grouped[str(row.get("solver", ""))].append(value)
    return {solver: fmean(values) for solver, values in grouped.items() if values}


def _feasible_rate_by_solver(rows: list[dict[str, Any]]) -> dict[str, float]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get("solver", ""))].append(row)
    return {
        solver: sum(1 for row in solver_rows if _valid_solution(row)) / len(solver_rows)
        for solver, solver_rows in grouped.items()
        if solver_rows
    }


def _plot_bar(path: Path, *, title: str, y_label: str, values: dict[str, float]) -> None:
    plt = _pyplot()
    labels = sorted(values)
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(labels, [values[label] for label in labels], color="#2563eb")
    ax.set_title(title)
    ax.set_ylabel(y_label)
    ax.tick_params(axis="x", rotation=20)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def _plot_convergence(rows: list[dict[str, Any]], path: Path) -> None:
    series: dict[str, dict[int, list[float]]] = defaultdict(lambda: defaultdict(list))
    for row in rows:
        solver = str(row.get("solver", ""))
        if not solver.startswith("alns"):
            continue
        convergence_path = Path(str(row.get("convergence_csv", "")))
        if not convergence_path.exists():
            continue
        for history_row in _read_csv(convergence_path):
            iteration = _int_or_none(history_row.get("iteration"))
            best_objective = _float_or_none(history_row.get("best_objective"))
            if iteration is None or best_objective is None:
                continue
            series[solver][iteration].append(best_objective)

    plt = _pyplot()
    fig, ax = plt.subplots(figsize=(9, 5))
    for solver in sorted(series):
        points = sorted(
            (iteration, fmean(values))
            for iteration, values in series[solver].items()
            if values
        )
        if not points:
            continue
        ax.plot(
            [point[0] for point in points],
            [point[1] for point in points],
            label=solver,
        )
    ax.set_title("EXP-02 ALNS Convergence")
    ax.set_xlabel("Iteration")
    ax.set_ylabel("Mean best objective")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def _update_figure_sources() -> None:
    manifest = FIGURES_DIR / "figure_sources.md"
    existing = manifest.read_text(encoding="utf-8") if manifest.exists() else "# Figure Sources\n"
    section = """

## P2-EXP-02 Medium Heuristic Comparison

- Command: `python scripts/generate_medium_assets.py`
- Primary input CSV: `data/results/experiments/runs_medium.csv`
- Summary CSV: `data/results/experiments/summary_medium.csv`
- Statistical tests CSV: `data/results/experiments/stat_tests_medium.csv`
- Convergence source: `data/results/experiments/convergence/medium/*.csv`
- Generated figures:
  - `reports/figures/medium_solver_cost.png`
  - `reports/figures/medium_solver_runtime.png`
  - `reports/figures/medium_feasible_rate.png`
  - `reports/figures/medium_convergence.png`
"""
    marker = "## P2-EXP-02 Medium Heuristic Comparison"
    if marker in existing:
        existing = existing.split(marker, 1)[0].rstrip() + "\n"
    manifest.write_text(existing.rstrip() + section, encoding="utf-8")


def _valid_solution(row: dict[str, Any]) -> bool:
    return (
        row.get("pipeline_status") == "ok"
        and _truthy(row.get("feasible"))
        and _truthy(row.get("has_solution"))
        and _float_or_none(row.get("distance")) is not None
    )


def _mean_field(rows: list[dict[str, Any]], field: str) -> float | None:
    values = [_float(row[field]) for row in rows if _float_or_none(row.get(field)) is not None]
    return fmean(values) if values else None


def _median_field(rows: list[dict[str, Any]], field: str) -> float | None:
    values = [_float(row[field]) for row in rows if _float_or_none(row.get(field)) is not None]
    return median(values) if values else None


def _truthy(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _float(value: Any) -> float:
    converted = _float_or_none(value)
    if converted is None:
        raise ValueError(f"expected numeric value, got {value!r}")
    return converted


def _float_or_none(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _int_or_none(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _pyplot() -> Any:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    return plt


if __name__ == "__main__":
    main()
