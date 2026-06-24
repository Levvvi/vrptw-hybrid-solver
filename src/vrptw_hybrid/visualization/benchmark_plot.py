"""Matplotlib and Plotly plots for benchmark x-y route artifacts."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

ROUTE_COLORS = (
    "#2563eb",
    "#dc2626",
    "#16a34a",
    "#9333ea",
    "#ea580c",
    "#0891b2",
    "#be123c",
    "#4d7c0f",
    "#0f766e",
    "#7c2d12",
)

BENCHMARK_CAPTION = "Benchmark x-y coordinates, not real latitude/longitude or road routes."


def plot_benchmark_routes_matplotlib(
    artifact: Mapping[str, Any],
    output_png: str | Path,
) -> Path:
    """Plot a benchmark route artifact to a PNG without map tiles."""

    plt = _pyplot()
    path = Path(output_png)
    path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(9, 7))
    _plot_customers(ax, artifact)
    if _truthy(artifact.get("feasible")) and _truthy(artifact.get("has_solution")):
        _plot_routes(ax, artifact)
    else:
        ax.text(
            0.5,
            0.5,
            f"No route available\nstatus={artifact.get('status', '')}",
            transform=ax.transAxes,
            ha="center",
            va="center",
            fontsize=14,
            bbox={"boxstyle": "round,pad=0.5", "fc": "#fee2e2", "ec": "#dc2626"},
        )

    ax.set_title(_title(artifact))
    ax.set_xlabel("Benchmark x")
    ax.set_ylabel("Benchmark y")
    ax.grid(True, alpha=0.25)
    ax.set_aspect("equal", adjustable="box")
    ax.text(
        0.5,
        -0.12,
        BENCHMARK_CAPTION,
        transform=ax.transAxes,
        ha="center",
        va="top",
        fontsize=9,
        color="#374151",
    )
    if _truthy(artifact.get("has_solution")):
        ax.legend(loc="best", fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)
    return path


def plot_benchmark_routes_plotly(
    artifact: Mapping[str, Any],
    output_html: str | Path,
) -> Path:
    """Plot a benchmark route artifact to standalone Plotly HTML."""

    import plotly.graph_objects as go

    path = Path(output_html)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig = go.Figure()

    customers = _list_of_mappings(artifact.get("customers"))
    fig.add_trace(
        go.Scatter(
            x=[customer.get("x") for customer in customers],
            y=[customer.get("y") for customer in customers],
            mode="markers",
            name="customers",
            marker={"size": 6, "color": "#f59e0b", "line": {"width": 1, "color": "#111827"}},
            text=[f"Customer {customer.get('id')}" for customer in customers],
        )
    )
    depot = artifact.get("depot")
    if isinstance(depot, Mapping):
        fig.add_trace(
            go.Scatter(
                x=[depot.get("x")],
                y=[depot.get("y")],
                mode="markers",
                name="depot",
                marker={"size": 14, "color": "#dc2626", "symbol": "star"},
                text=["Depot"],
            )
        )

    if _truthy(artifact.get("feasible")) and _truthy(artifact.get("has_solution")):
        for index, route in enumerate(_list_of_mappings(artifact.get("routes"))):
            points = _list_of_mappings(route.get("points"))
            fig.add_trace(
                go.Scatter(
                    x=[point.get("x") for point in points],
                    y=[point.get("y") for point in points],
                    mode="lines+markers",
                    name=f"vehicle {route.get('vehicle_id')}",
                    line={"color": ROUTE_COLORS[index % len(ROUTE_COLORS)], "width": 2},
                )
            )
    else:
        fig.add_annotation(
            text=f"No route available. status={artifact.get('status', '')}",
            x=0.5,
            y=0.5,
            xref="paper",
            yref="paper",
            showarrow=False,
        )

    fig.update_layout(
        title=f"{_title(artifact)}<br><sup>{BENCHMARK_CAPTION}</sup>",
        xaxis_title="Benchmark x",
        yaxis_title="Benchmark y",
        yaxis={"scaleanchor": "x", "scaleratio": 1},
        template="plotly_white",
    )
    fig.write_html(path, include_plotlyjs="cdn", full_html=True)
    return path


def _plot_customers(ax: Any, artifact: Mapping[str, Any]) -> None:
    customers = _list_of_mappings(artifact.get("customers"))
    if customers:
        ax.scatter(
            [customer.get("x") for customer in customers],
            [customer.get("y") for customer in customers],
            s=18,
            c="#f59e0b",
            edgecolors="#111827",
            linewidths=0.4,
            label="customers",
            zorder=3,
        )
    depot = artifact.get("depot")
    if isinstance(depot, Mapping):
        ax.scatter(
            [depot.get("x")],
            [depot.get("y")],
            s=160,
            c="#dc2626",
            marker="*",
            edgecolors="#111827",
            linewidths=0.7,
            label="depot",
            zorder=5,
        )


def _plot_routes(ax: Any, artifact: Mapping[str, Any]) -> None:
    for index, route in enumerate(_list_of_mappings(artifact.get("routes"))):
        points = _list_of_mappings(route.get("points"))
        if len(points) < 2:
            continue
        xs = [point.get("x") for point in points]
        ys = [point.get("y") for point in points]
        ax.plot(
            xs,
            ys,
            color=ROUTE_COLORS[index % len(ROUTE_COLORS)],
            linewidth=1.6,
            alpha=0.78,
            marker="o",
            markersize=2.5,
            label=f"vehicle {route.get('vehicle_id')}",
            zorder=4,
        )


def _title(artifact: Mapping[str, Any]) -> str:
    return (
        f"{artifact.get('instance', '')} / {artifact.get('solver', '')} / seed "
        f"{artifact.get('seed', '')} | vehicles={_fmt(artifact.get('vehicles'))} "
        f"distance={_fmt(artifact.get('distance'))} runtime={_fmt(artifact.get('runtime_sec'))}s"
    )


def _fmt(value: Any) -> str:
    if value is None or value == "":
        return "NA"
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return str(value)


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _list_of_mappings(value: Any) -> list[Mapping[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, Mapping)]


def _pyplot() -> Any:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    return plt
