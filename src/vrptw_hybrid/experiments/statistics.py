"""Statistical summaries and paired comparisons for experiment runs."""

from __future__ import annotations

import csv
from collections import defaultdict
from dataclasses import dataclass
from itertools import combinations
from math import erfc, sqrt
from pathlib import Path
from statistics import fmean, median, stdev
from typing import Any

from vrptw_hybrid.core.solution_io import save_metrics_csv


@dataclass(frozen=True, slots=True)
class StatisticsResult:
    summary_rows: tuple[dict[str, Any], ...]
    pairwise_rows: tuple[dict[str, Any], ...]
    summary_csv: Path | None = None
    pairwise_csv: Path | None = None


def analyze_runs_csv(
    runs_csv: str | Path,
    *,
    metric: str = "cost",
    output_dir: str | Path | None = None,
) -> StatisticsResult:
    """Read a runs CSV and optionally write summary and pairwise statistics CSVs."""

    input_path = Path(runs_csv)
    rows = _read_csv(input_path)
    summary_rows = summarize_runs(rows, metric=metric)
    pairwise_rows = pairwise_comparisons(rows, metric=metric)
    summary_csv: Path | None = None
    pairwise_csv: Path | None = None
    if output_dir is not None:
        output_path = Path(output_dir)
        summary_csv = output_path / f"summary_{input_path.stem}.csv"
        pairwise_csv = output_path / f"pairwise_{input_path.stem}.csv"
        save_metrics_csv(summary_rows, summary_csv)
        save_metrics_csv(pairwise_rows, pairwise_csv)
    return StatisticsResult(
        summary_rows=tuple(summary_rows),
        pairwise_rows=tuple(pairwise_rows),
        summary_csv=summary_csv,
        pairwise_csv=pairwise_csv,
    )


def summarize_runs(rows: list[dict[str, Any]], *, metric: str = "cost") -> list[dict[str, Any]]:
    """Return one summary row per solver, tolerating failed or missing runs."""

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get("solver", ""))].append(row)

    summary_rows: list[dict[str, Any]] = []
    for solver in sorted(grouped):
        solver_rows = grouped[solver]
        valid_rows = [row for row in solver_rows if _is_valid_metric_row(row, metric)]
        values = [_float(row[metric]) for row in valid_rows]
        runtime_values = [
            _float(row["runtime_sec"])
            for row in solver_rows
            if _float_or_none(row.get("runtime_sec")) is not None
        ]
        feasible_count = sum(1 for row in solver_rows if _bool(row.get("feasible")))
        summary_rows.append(
            {
                "solver": solver,
                "metric": metric,
                "runs": len(solver_rows),
                "valid_runs": len(valid_rows),
                "failed_runs": sum(1 for row in solver_rows if row.get("status") == "error"),
                "feasible_rate": feasible_count / len(solver_rows) if solver_rows else None,
                "metric_mean": fmean(values) if values else None,
                "metric_std": stdev(values) if len(values) > 1 else 0.0 if values else None,
                "metric_median": median(values) if values else None,
                "metric_best": min(values) if values else None,
                "runtime_mean": fmean(runtime_values) if runtime_values else None,
            }
        )
    return summary_rows


def pairwise_comparisons(
    rows: list[dict[str, Any]],
    *,
    metric: str = "cost",
) -> list[dict[str, Any]]:
    """Return paired solver comparisons over common instance/seed keys."""

    valid_rows = [row for row in rows if _is_valid_metric_row(row, metric)]
    by_solver: dict[str, dict[tuple[str, str], float]] = defaultdict(dict)
    for row in valid_rows:
        solver = str(row["solver"])
        key = (str(row.get("instance", "")), str(row.get("seed", "")))
        by_solver[solver][key] = _float(row[metric])

    comparison_rows: list[dict[str, Any]] = []
    for solver_a, solver_b in combinations(sorted(by_solver), 2):
        common_keys = sorted(set(by_solver[solver_a]) & set(by_solver[solver_b]))
        values_a = [by_solver[solver_a][key] for key in common_keys]
        values_b = [by_solver[solver_b][key] for key in common_keys]
        diffs = [
            value_a - value_b for value_a, value_b in zip(values_a, values_b, strict=True)
        ]
        p_value = _wilcoxon_p_value(diffs)
        mean_a = fmean(values_a) if values_a else None
        mean_b = fmean(values_b) if values_b else None
        comparison_rows.append(
            {
                "solver_a": solver_a,
                "solver_b": solver_b,
                "metric": metric,
                "paired_n": len(common_keys),
                "mean_a": mean_a,
                "mean_b": mean_b,
                "mean_diff_a_minus_b": fmean(diffs) if diffs else None,
                "median_diff_a_minus_b": median(diffs) if diffs else None,
                "p_value": p_value,
                "p_value_holm": None,
                "reject_0_05": None,
                "effect_size_rank_biserial": _rank_biserial_effect(diffs),
                "better_solver": _better_solver(solver_a, solver_b, mean_a, mean_b),
            }
        )
    _apply_holm_correction(comparison_rows)
    return comparison_rows


def _read_csv(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8", newline="") as file:
        return [dict(row) for row in csv.DictReader(file)]


def _is_valid_metric_row(row: dict[str, Any], metric: str) -> bool:
    if row.get("status", "ok") != "ok":
        return False
    if not _bool(row.get("feasible")):
        return False
    return _float_or_none(row.get(metric)) is not None


def _wilcoxon_p_value(diffs: list[float]) -> float | None:
    nonzero_diffs = [diff for diff in diffs if diff != 0.0]
    if len(nonzero_diffs) < 2:
        return 1.0 if diffs else None
    ranks = _average_ranks([abs(diff) for diff in nonzero_diffs])
    positive_rank_sum = sum(
        rank for rank, diff in zip(ranks, nonzero_diffs, strict=True) if diff > 0
    )
    negative_rank_sum = sum(
        rank for rank, diff in zip(ranks, nonzero_diffs, strict=True) if diff < 0
    )
    statistic = min(positive_rank_sum, negative_rank_sum)
    count = len(nonzero_diffs)
    mean = count * (count + 1) / 4.0
    variance = count * (count + 1) * (2 * count + 1) / 24.0
    if variance == 0:
        return 1.0
    z_score = (statistic - mean) / sqrt(variance)
    return erfc(abs(z_score) / sqrt(2.0))


def _rank_biserial_effect(diffs: list[float]) -> float | None:
    nonzero_diffs = [diff for diff in diffs if diff != 0.0]
    if not nonzero_diffs:
        return 0.0 if diffs else None
    ranks = _average_ranks([abs(diff) for diff in nonzero_diffs])
    positive_rank_sum = sum(
        rank for rank, diff in zip(ranks, nonzero_diffs, strict=True) if diff > 0
    )
    negative_rank_sum = sum(
        rank for rank, diff in zip(ranks, nonzero_diffs, strict=True) if diff < 0
    )
    total_rank_sum = sum(ranks)
    if total_rank_sum == 0:
        return 0.0
    return float((positive_rank_sum - negative_rank_sum) / total_rank_sum)


def _apply_holm_correction(rows: list[dict[str, Any]]) -> None:
    indexed_p_values = [
        (index, float(row["p_value"]))
        for index, row in enumerate(rows)
        if row.get("p_value") is not None
    ]
    total = len(indexed_p_values)
    previous_adjusted = 0.0
    for rank, (index, p_value) in enumerate(
        sorted(indexed_p_values, key=lambda item: item[1]),
        start=1,
    ):
        adjusted = min(1.0, (total - rank + 1) * p_value)
        adjusted = max(adjusted, previous_adjusted)
        previous_adjusted = adjusted
        rows[index]["p_value_holm"] = adjusted
        rows[index]["reject_0_05"] = adjusted < 0.05


def _average_ranks(values: list[float]) -> list[float]:
    indexed_values = sorted((value, index) for index, value in enumerate(values))
    ranks = [0.0] * len(values)
    position = 0
    while position < len(indexed_values):
        tie_end = position + 1
        while (
            tie_end < len(indexed_values)
            and indexed_values[tie_end][0] == indexed_values[position][0]
        ):
            tie_end += 1
        average_rank = (position + 1 + tie_end) / 2.0
        for _value, original_index in indexed_values[position:tie_end]:
            ranks[original_index] = average_rank
        position = tie_end
    return ranks


def _better_solver(
    solver_a: str,
    solver_b: str,
    mean_a: float | None,
    mean_b: float | None,
) -> str:
    if mean_a is None or mean_b is None:
        return ""
    if mean_a == mean_b:
        return "tie"
    return solver_a if mean_a < mean_b else solver_b


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


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    normalized = str(value).strip().lower()
    return normalized in {"1", "true", "yes", "y"}
