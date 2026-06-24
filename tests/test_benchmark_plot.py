from pathlib import Path

from vrptw_hybrid.core.solution_io import save_solution_json
from vrptw_hybrid.data.solomon import parse_solomon
from vrptw_hybrid.solvers.greedy import solve_greedy
from vrptw_hybrid.visualization.benchmark_plot import (
    plot_benchmark_routes_matplotlib,
    plot_benchmark_routes_plotly,
)
from vrptw_hybrid.visualization.route_artifacts import build_benchmark_route_artifact

FIXTURE = Path("tests/fixtures/mini_solomon.txt")


def test_plot_benchmark_routes_writes_nonempty_png_and_html(tmp_path: Path) -> None:
    instance = parse_solomon(FIXTURE, limit_customers=8)
    solution = solve_greedy(instance, seed=42)
    solution_path = tmp_path / "solution.json"
    save_solution_json(solution, solution_path)
    artifact = build_benchmark_route_artifact(
        FIXTURE,
        solution_path,
        {
            "instance": "mini_solomon",
            "solver": "greedy",
            "seed": 42,
            "status": "FEASIBLE",
            "pipeline_status": "ok",
            "feasible": True,
            "has_solution": True,
            "vehicles": solution.vehicles_used,
            "distance": solution.total_distance,
            "objective": solution.objective,
            "runtime_sec": solution.runtime_sec,
        },
    )

    png_path = plot_benchmark_routes_matplotlib(artifact, tmp_path / "route.png")
    html_path = plot_benchmark_routes_plotly(artifact, tmp_path / "route.html")

    assert png_path.exists()
    assert png_path.stat().st_size > 0
    assert html_path.exists()
    assert html_path.stat().st_size > 0


def test_curated_demo_artifact_can_be_plotted_if_present(tmp_path: Path) -> None:
    artifact_path = Path("reports/demo/artifacts/r101_100_ortools_routing_seed0.json")
    if not artifact_path.exists():
        return

    import json

    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    output_path = plot_benchmark_routes_matplotlib(artifact, tmp_path / "no_solution.png")

    assert artifact["status"] == "NO_SOLUTION"
    assert artifact["routes"] == []
    assert output_path.exists()
    assert output_path.stat().st_size > 0
