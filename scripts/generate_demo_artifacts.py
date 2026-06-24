"""Generate curated VIS-01A benchmark route demo artifacts."""

from __future__ import annotations

from pathlib import Path
from shutil import copy2

from vrptw_hybrid.visualization.benchmark_plot import (
    plot_benchmark_routes_matplotlib,
    plot_benchmark_routes_plotly,
)
from vrptw_hybrid.visualization.route_artifacts import (
    build_benchmark_route_artifact,
    save_route_artifact,
    select_run_row,
)

RUNS_CSV = Path("reports/results/runs_medium.csv")
ARTIFACT_DIR = Path("reports/demo/artifacts")
PNG_DIR = Path("reports/demo/png")
HTML_DIR = Path("reports/demo/html")
SOLUTION_DIR = Path("reports/demo/solutions")

SELECTED_RUNS = (
    ("c101_100", "alns_roulette", 0),
    ("r101_100", "alns_roulette", 0),
    ("rc101_100", "alns_roulette", 0),
    ("gh_c1_2_1_200", "alns_uniform", 0),
    ("gh_r1_2_1_200", "alns_roulette", 0),
    ("gh_rc1_2_1_200", "alns_roulette", 0),
    ("gh_rc1_2_1_200", "ortools_routing", 0),
    ("r101_100", "ortools_routing", 0),
)


def main() -> None:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    PNG_DIR.mkdir(parents=True, exist_ok=True)
    HTML_DIR.mkdir(parents=True, exist_ok=True)
    SOLUTION_DIR.mkdir(parents=True, exist_ok=True)

    for instance, solver, seed in SELECTED_RUNS:
        row = select_run_row(RUNS_CSV, instance=instance, solver=solver, seed=seed)
        source_solution = Path(str(row["solution_json"]))
        curated_solution = SOLUTION_DIR / source_solution.name
        copy2(source_solution, curated_solution)

        artifact = build_benchmark_route_artifact(
            row["source_file"],
            source_solution,
            row,
        )
        stem = f"{instance}_{solver}_seed{seed}"
        artifact["solution_json"] = str(curated_solution)
        artifact["curated_demo"] = True
        artifact_path = save_route_artifact(artifact, ARTIFACT_DIR / f"{stem}.json")
        png_path = plot_benchmark_routes_matplotlib(artifact, PNG_DIR / f"{stem}.png")
        html_path = plot_benchmark_routes_plotly(artifact, HTML_DIR / f"{stem}.html")
        print(
            f"{instance} {solver} seed={seed} "
            f"status={artifact['status']} artifact={artifact_path} png={png_path} html={html_path}"
        )


if __name__ == "__main__":
    main()
