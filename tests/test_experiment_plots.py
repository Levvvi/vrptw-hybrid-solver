from pathlib import Path

from vrptw_hybrid.experiments.plots import generate_report_figures
from vrptw_hybrid.experiments.runner import run_batch


def test_generate_report_figures_from_mini_batch(tmp_path: Path) -> None:
    batch_result = run_batch(
        "configs/solomon_small.yaml",
        output_dir=tmp_path / "results",
        timestamp="figures",
    )
    figure_dir = tmp_path / "figures"

    outputs = generate_report_figures(batch_result.csv_path, figure_dir)

    assert len(outputs.paths) >= 2
    assert {path.name for path in outputs.paths} >= {
        "convergence.svg",
        "cost_runtime.svg",
    }
    assert all(path.exists() and path.stat().st_size > 0 for path in outputs.paths)
