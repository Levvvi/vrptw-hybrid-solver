"""Generate report figures from a VRPTW runs CSV."""

from __future__ import annotations

import argparse
from pathlib import Path

from vrptw_hybrid.experiments.plots import generate_report_figures


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate VRPTW report figures.")
    parser.add_argument("--runs-csv", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("data/results/figures"))
    args = parser.parse_args()

    outputs = generate_report_figures(args.runs_csv, args.output_dir)
    for path in outputs.paths:
        print(path)


if __name__ == "__main__":
    main()
