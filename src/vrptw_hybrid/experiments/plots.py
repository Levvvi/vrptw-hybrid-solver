"""Dependency-light SVG report figure generation for experiment outputs."""

from __future__ import annotations

import csv
from collections import defaultdict
from dataclasses import dataclass
from html import escape
from pathlib import Path
from statistics import fmean, median
from typing import Any

from vrptw_hybrid.core.solution_io import load_solution_json

WIDTH = 900
HEIGHT = 560
LEFT = 90
RIGHT = 30
TOP = 60
BOTTOM = 80
PLOT_WIDTH = WIDTH - LEFT - RIGHT
PLOT_HEIGHT = HEIGHT - TOP - BOTTOM
PALETTE = ("#2563eb", "#dc2626", "#16a34a", "#9333ea", "#ea580c", "#0891b2")


@dataclass(frozen=True, slots=True)
class FigureOutputs:
    paths: tuple[Path, ...]


def generate_report_figures(
    runs_csv: str | Path,
    output_dir: str | Path,
) -> FigureOutputs:
    """Generate standard report SVG figures from a runs CSV and solution metadata."""

    rows = _read_rows(Path(runs_csv))
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    solutions = _load_solutions(rows)
    figure_paths = (
        _plot_convergence(solutions, output_path / "convergence.svg"),
        _plot_cost_runtime(rows, output_path / "cost_runtime.svg"),
        _plot_gap_boxplot(rows, output_path / "gap_boxplot.svg"),
        _plot_operator_probabilities(solutions, output_path / "operator_probabilities.svg"),
        _plot_pair_heatmap(solutions, output_path / "pair_heatmap.svg"),
        _plot_solver_cost_png(rows, output_path / "solver_cost_comparison.png"),
        _plot_solver_runtime_png(rows, output_path / "solver_runtime_comparison.png"),
        _plot_alns_convergence_png(solutions, output_path / "alns_convergence.png"),
        _plot_selector_ablation_png(rows, output_path / "selector_ablation.png"),
    )
    manifest = _write_figure_sources(Path(runs_csv), output_path, figure_paths)
    return FigureOutputs(paths=(*figure_paths, manifest))


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as file:
        return [dict(row) for row in csv.DictReader(file)]


def _load_solutions(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    solutions: list[dict[str, Any]] = []
    for row in rows:
        solution_path = row.get("solution_json", "")
        if not solution_path:
            continue
        path = Path(solution_path)
        if not path.exists():
            continue
        solution = load_solution_json(path)
        solutions.append(
            {
                "solver": row.get("solver", solution.solver_name),
                "seed": row.get("seed", solution.metadata.get("seed", "")),
                "solution": solution,
            }
        )
    return solutions


def _write_figure_sources(
    runs_csv: Path,
    output_dir: Path,
    paths: tuple[Path, ...],
) -> Path:
    manifest = output_dir / "figure_sources.md"
    lines = [
        "# Figure Sources",
        "",
        f"- Command: `vrptw plot --results {runs_csv} --output {output_dir}`",
        f"- Primary input CSV: `{runs_csv}`",
        "- Solution JSON paths are read from the `solution_json` column.",
        "- ALNS convergence data is read from solution metadata and convergence-capable runs.",
        "",
        "## Outputs",
        "",
    ]
    lines.extend(f"- `{path}`" for path in paths)
    manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return manifest


def _plot_convergence(solutions: list[dict[str, Any]], path: Path) -> Path:
    series: list[tuple[str, list[tuple[float, float]]]] = []
    for item in solutions:
        history = item["solution"].metadata.get("history", [])
        points = [
            (float(entry["iteration"]), float(entry["best_cost"]))
            for entry in history
            if "iteration" in entry and "best_cost" in entry
        ]
        if points:
            series.append((f"{item['solver']} seed={item['seed']}", points))
    return _write_line_chart(path, "Best Cost Over Iteration", "Iteration", "Best cost", series)


def _plot_cost_runtime(rows: list[dict[str, str]], path: Path) -> Path:
    points: list[tuple[str, float, float]] = []
    for row in rows:
        if not _pipeline_ok(row):
            continue
        cost = _float_or_none(row.get("cost"))
        runtime = _float_or_none(row.get("runtime_sec"))
        if cost is not None and runtime is not None:
            points.append((row.get("solver", "solver"), runtime, cost))
    return _write_scatter(path, "Cost vs Runtime", "Runtime (sec)", "Cost", points)


def _plot_gap_boxplot(rows: list[dict[str, str]], path: Path) -> Path:
    values_by_solver: dict[str, list[float]] = {}
    for row in rows:
        if not _pipeline_ok(row):
            continue
        gap = _float_or_none(row.get("distance_gap_pct"))
        if gap is not None:
            values_by_solver.setdefault(row.get("solver", "solver"), []).append(gap)
    return _write_boxplot(
        path,
        "Distance Gap to BKS",
        "Solver",
        "Distance gap (%)",
        values_by_solver,
    )


def _plot_operator_probabilities(solutions: list[dict[str, Any]], path: Path) -> Path:
    for item in solutions:
        history = item["solution"].metadata.get("history", [])
        if not history:
            continue
        first_snapshot = history[0].get("selector_snapshot", {})
        probability_key = _operator_probability_key(first_snapshot)
        if probability_key is None:
            continue
        series: list[tuple[str, list[tuple[float, float]]]] = []
        for operator_name in sorted(first_snapshot[probability_key]):
            points = _probability_points(history, probability_key, operator_name)
            if points:
                series.append((f"{item['solver']}:{operator_name}", points))
        if series:
            return _write_line_chart(
                path,
                "Operator Probability Over Iteration",
                "Iteration",
                "Probability",
                series,
            )
    return _write_placeholder(path, "Operator Probability Over Iteration")


def _plot_pair_heatmap(solutions: list[dict[str, Any]], path: Path) -> Path:
    heatmap_rows = _first_pair_heatmap(solutions)
    if not heatmap_rows:
        return _write_placeholder(path, "MOSADE Pair Probability Heatmap")

    destroy_names = sorted({str(row["destroy"]) for row in heatmap_rows})
    repair_names = sorted({str(row["repair"]) for row in heatmap_rows})
    max_probability = max(float(row["probability"]) for row in heatmap_rows)
    cell_width = PLOT_WIDTH / max(1, len(repair_names))
    cell_height = PLOT_HEIGHT / max(1, len(destroy_names))
    elements = [_axes("MOSADE Pair Probability Heatmap", "Repair", "Destroy")]
    for row in heatmap_rows:
        destroy_index = destroy_names.index(str(row["destroy"]))
        repair_index = repair_names.index(str(row["repair"]))
        probability = float(row["probability"])
        x = LEFT + repair_index * cell_width
        y = TOP + destroy_index * cell_height
        elements.append(
            f'<rect x="{x:.2f}" y="{y:.2f}" width="{cell_width:.2f}" '
            f'height="{cell_height:.2f}" fill="{_heat_color(probability, max_probability)}" />'
        )
    for index, name in enumerate(repair_names):
        x = LEFT + index * cell_width + cell_width / 2
        elements.append(_text(x, HEIGHT - 40, name, size=10, anchor="middle", rotate=-25))
    for index, name in enumerate(destroy_names):
        y = TOP + index * cell_height + cell_height / 2
        elements.append(_text(LEFT - 10, y, name, size=10, anchor="end"))
    return _write_svg(path, elements)


def _plot_solver_cost_png(rows: list[dict[str, str]], path: Path) -> Path:
    return _write_bar_png(
        path,
        title="Solver Objective Comparison",
        y_label="Mean objective",
        values_by_label=_group_metric_by_solver(rows, "cost"),
    )


def _plot_solver_runtime_png(rows: list[dict[str, str]], path: Path) -> Path:
    return _write_bar_png(
        path,
        title="Solver Runtime Comparison",
        y_label="Mean runtime (sec)",
        values_by_label=_group_metric_by_solver(rows, "runtime_sec"),
    )


def _plot_alns_convergence_png(solutions: list[dict[str, Any]], path: Path) -> Path:
    series: list[tuple[str, list[tuple[float, float]]]] = []
    for item in solutions:
        solver = str(item["solver"])
        if not solver.startswith("alns"):
            continue
        history = item["solution"].metadata.get("history", [])
        if not isinstance(history, list):
            continue
        points = [
            (float(entry["iteration"]), float(entry["best_cost"]))
            for entry in history
            if isinstance(entry, dict) and "iteration" in entry and "best_cost" in entry
        ]
        if points:
            series.append((f"{solver} seed={item['seed']}", points))

    if not series:
        return _write_placeholder_png(path, "ALNS Convergence")

    plt = _pyplot()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(9, 5))
    for label, points in series:
        xs = [point[0] for point in points]
        ys = [point[1] for point in points]
        ax.plot(xs, ys, label=label)
    ax.set_title("ALNS Convergence")
    ax.set_xlabel("Iteration")
    ax.set_ylabel("Best objective")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)
    return path


def _plot_selector_ablation_png(rows: list[dict[str, str]], path: Path) -> Path:
    values = {
        solver: metric_values
        for solver, metric_values in _group_metric_by_solver(rows, "cost").items()
        if solver in {"alns_uniform", "alns_mosade"}
    }
    return _write_bar_png(
        path,
        title="ALNS Selector Ablation",
        y_label="Mean objective",
        values_by_label=values,
    )


def _group_metric_by_solver(
    rows: list[dict[str, str]],
    metric: str,
) -> dict[str, list[float]]:
    values_by_solver: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        if not _pipeline_ok(row):
            continue
        if str(row.get("feasible", "")).lower() not in {"1", "true", "yes"}:
            continue
        value = _float_or_none(row.get(metric))
        if value is not None:
            values_by_solver[row.get("solver", "solver")].append(value)
    return dict(values_by_solver)


def _write_bar_png(
    path: Path,
    *,
    title: str,
    y_label: str,
    values_by_label: dict[str, list[float]],
) -> Path:
    if not values_by_label:
        return _write_placeholder_png(path, title)

    labels = sorted(values_by_label)
    values = [fmean(values_by_label[label]) for label in labels]
    plt = _pyplot()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(labels, values, color="#2563eb")
    ax.set_title(title)
    ax.set_ylabel(y_label)
    ax.tick_params(axis="x", rotation=20)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)
    return path


def _write_placeholder_png(path: Path, title: str) -> Path:
    plt = _pyplot()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.set_title(title)
    ax.text(0.5, 0.5, "No data available yet", ha="center", va="center")
    ax.set_axis_off()
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)
    return path


def _pyplot() -> Any:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    return plt


def _write_line_chart(
    path: Path,
    title: str,
    x_label: str,
    y_label: str,
    series: list[tuple[str, list[tuple[float, float]]]],
) -> Path:
    if not series:
        return _write_placeholder(path, title)
    all_points = [point for _label, points in series for point in points]
    x_min, x_max = _range([point[0] for point in all_points])
    y_min, y_max = _range([point[1] for point in all_points])
    elements = [_axes(title, x_label, y_label)]
    for index, (label, points) in enumerate(series):
        color = PALETTE[index % len(PALETTE)]
        svg_points = " ".join(
            f"{_scale_x(x, x_min, x_max):.2f},{_scale_y(y, y_min, y_max):.2f}"
            for x, y in points
        )
        elements.append(
            f'<polyline points="{svg_points}" fill="none" stroke="{color}" stroke-width="2" />'
        )
        legend_y = TOP + 18 * index
        elements.append(_legend_swatch(WIDTH - 250, legend_y - 10, color))
        elements.append(_text(WIDTH - 235, legend_y, label, size=11, anchor="start"))
    return _write_svg(path, elements)


def _write_scatter(
    path: Path,
    title: str,
    x_label: str,
    y_label: str,
    points: list[tuple[str, float, float]],
) -> Path:
    if not points:
        return _write_placeholder(path, title)
    x_min, x_max = _range([point[1] for point in points])
    y_min, y_max = _range([point[2] for point in points])
    solver_colors = {
        solver: PALETTE[index % len(PALETTE)]
        for index, solver in enumerate(sorted({point[0] for point in points}))
    }
    elements = [_axes(title, x_label, y_label)]
    for solver, x, y in points:
        elements.append(
            f'<circle cx="{_scale_x(x, x_min, x_max):.2f}" cy="{_scale_y(y, y_min, y_max):.2f}" '
            f'r="5" fill="{solver_colors[solver]}" />'
        )
    for index, (solver, color) in enumerate(solver_colors.items()):
        legend_y = TOP + 18 * index
        elements.append(_legend_swatch(WIDTH - 180, legend_y - 10, color))
        elements.append(_text(WIDTH - 165, legend_y, solver, size=11, anchor="start"))
    return _write_svg(path, elements)


def _write_boxplot(
    path: Path,
    title: str,
    x_label: str,
    y_label: str,
    values_by_solver: dict[str, list[float]],
) -> Path:
    if not values_by_solver:
        return _write_placeholder(path, title)
    labels = sorted(values_by_solver)
    all_values = [value for values in values_by_solver.values() for value in values]
    y_min, y_max = _range(all_values)
    elements = [_axes(title, x_label, y_label)]
    slot_width = PLOT_WIDTH / max(1, len(labels))
    for index, label in enumerate(labels):
        values = sorted(values_by_solver[label])
        q1 = _quantile(values, 0.25)
        q2 = median(values)
        q3 = _quantile(values, 0.75)
        low = min(values)
        high = max(values)
        x_center = LEFT + slot_width * index + slot_width / 2
        box_width = min(60, slot_width * 0.5)
        elements.append(
            f'<line x1="{x_center:.2f}" x2="{x_center:.2f}" '
            f'y1="{_scale_y(low, y_min, y_max):.2f}" y2="{_scale_y(high, y_min, y_max):.2f}" '
            'stroke="#334155" stroke-width="2" />'
        )
        elements.append(
            _box_rect(
                x_center=x_center,
                box_width=box_width,
                q1_y=_scale_y(q1, y_min, y_max),
                q3_y=_scale_y(q3, y_min, y_max),
            )
        )
        elements.append(
            f'<line x1="{x_center - box_width / 2:.2f}" x2="{x_center + box_width / 2:.2f}" '
            f'y1="{_scale_y(q2, y_min, y_max):.2f}" y2="{_scale_y(q2, y_min, y_max):.2f}" '
            'stroke="#1e3a8a" stroke-width="2" />'
        )
        elements.append(_text(x_center, HEIGHT - 40, label, size=11, anchor="middle"))
    return _write_svg(path, elements)


def _box_rect(*, x_center: float, box_width: float, q1_y: float, q3_y: float) -> str:
    return (
        f'<rect x="{x_center - box_width / 2:.2f}" y="{q3_y:.2f}" '
        f'width="{box_width:.2f}" height="{abs(q1_y - q3_y):.2f}" '
        'fill="#bfdbfe" stroke="#1e3a8a" />'
    )


def _write_placeholder(path: Path, title: str) -> Path:
    elements = [
        _axes(title, "", ""),
        _text(WIDTH / 2, HEIGHT / 2, "No data available yet", size=18),
    ]
    return _write_svg(path, elements)


def _write_svg(path: Path, elements: list[str]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = "\n".join(
        [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" '
            f'height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}">',
            '<rect width="100%" height="100%" fill="white" />',
            *elements,
            "</svg>",
        ]
    )
    path.write_text(content + "\n", encoding="utf-8")
    return path


def _axes(title: str, x_label: str, y_label: str) -> str:
    return "\n".join(
        [
            _text(WIDTH / 2, 30, title, size=20),
            _line(LEFT, TOP + PLOT_HEIGHT, LEFT + PLOT_WIDTH, TOP + PLOT_HEIGHT),
            _line(LEFT, TOP, LEFT, TOP + PLOT_HEIGHT),
            _text(LEFT + PLOT_WIDTH / 2, HEIGHT - 15, x_label, size=13),
            _text(25, TOP + PLOT_HEIGHT / 2, y_label, size=13, rotate=-90),
        ]
    )


def _text(
    x: float,
    y: float,
    value: object,
    *,
    size: int = 12,
    anchor: str = "middle",
    rotate: int | None = None,
) -> str:
    transform = f' transform="rotate({rotate} {x:.2f} {y:.2f})"' if rotate is not None else ""
    return (
        f'<text x="{x:.2f}" y="{y:.2f}" font-family="Arial, sans-serif" '
        f'font-size="{size}" text-anchor="{anchor}" fill="#0f172a"{transform}>'
        f"{escape(str(value))}</text>"
    )


def _line(x1: float, y1: float, x2: float, y2: float) -> str:
    return (
        f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" '
        'stroke="#475569" />'
    )


def _legend_swatch(x: float, y: float, color: str) -> str:
    return (
        f'<rect x="{x:.2f}" y="{y:.2f}" width="10" height="10" '
        f'fill="{color}" />'
    )


def _operator_probability_key(snapshot: dict[str, Any]) -> str | None:
    if "destroy_probabilities" in snapshot:
        return "destroy_probabilities"
    if "pair_probabilities" in snapshot:
        return "pair_probabilities"
    return None


def _probability_points(
    history: list[dict[str, Any]],
    probability_key: str,
    operator_name: str,
) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    for entry in history:
        snapshot = entry.get("selector_snapshot", {})
        probabilities_by_operator = snapshot.get(probability_key, {})
        if operator_name in probabilities_by_operator:
            points.append(
                (
                    float(entry["iteration"]),
                    float(probabilities_by_operator[operator_name]),
                )
            )
    return points


def _first_pair_heatmap(solutions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for item in solutions:
        selector = item["solution"].metadata.get("selector", {})
        heatmap = selector.get("pair_heatmap") if isinstance(selector, dict) else None
        if isinstance(heatmap, list) and heatmap:
            return [dict(row) for row in heatmap]
    return []


def _pair_probability(
    rows: list[dict[str, Any]],
    destroy_name: str,
    repair_name: str,
) -> float:
    for row in rows:
        if row["destroy"] == destroy_name and row["repair"] == repair_name:
            return float(row["probability"])
    return 0.0


def _range(values: list[float]) -> tuple[float, float]:
    low = min(values)
    high = max(values)
    if low == high:
        return low - 1.0, high + 1.0
    padding = (high - low) * 0.05
    return low - padding, high + padding


def _scale_x(value: float, low: float, high: float) -> float:
    return LEFT + (value - low) / (high - low) * PLOT_WIDTH


def _scale_y(value: float, low: float, high: float) -> float:
    return TOP + PLOT_HEIGHT - (value - low) / (high - low) * PLOT_HEIGHT


def _quantile(values: list[float], q: float) -> float:
    if len(values) == 1:
        return values[0]
    position = (len(values) - 1) * q
    lower = int(position)
    upper = min(lower + 1, len(values) - 1)
    fraction = position - lower
    return values[lower] * (1.0 - fraction) + values[upper] * fraction


def _heat_color(value: float, maximum: float) -> str:
    ratio = 0.0 if maximum <= 0 else value / maximum
    blue = 255
    red_green = int(245 - 170 * ratio)
    return f"#{red_green:02x}{red_green:02x}{blue:02x}"


def _float_or_none(value: object) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, str | int | float):
        return float(value)
    return None


def _pipeline_ok(row: dict[str, str]) -> bool:
    status = row.get("pipeline_status")
    if status:
        return status == "ok"
    legacy_status = row.get("status", "ok")
    return legacy_status == "ok" or legacy_status not in {"ok", "error"}
