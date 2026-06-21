"""Run synthetic or template-based VRPTW scaling experiments."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

from vrptw_hybrid.experiments.scaling import run_scaling_experiment


def main() -> None:
    parser = argparse.ArgumentParser(description="Run VRPTW scaling smoke experiments.")
    parser.add_argument("--sizes", default="50,100,200,500,1000")
    parser.add_argument("--solvers", default="greedy,ortools_routing,alns_mosade")
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-iterations", type=int, default=20)
    parser.add_argument("--small-time-limit", type=float, default=30.0)
    parser.add_argument("--large-time-limit", type=float, default=120.0)
    parser.add_argument("--large-threshold", type=int, default=500)
    parser.add_argument(
        "--instance-template",
        default=None,
        help="Optional Solomon path template, e.g. data/solomon/C{size}.txt.",
    )
    args = parser.parse_args()

    output = args.output or Path("data/results") / f"scaling_{_timestamp()}.csv"
    result = run_scaling_experiment(
        sizes=_parse_int_tuple(args.sizes),
        solvers=_parse_str_tuple(args.solvers),
        output_csv=output,
        seed=args.seed,
        max_iterations=args.max_iterations,
        small_time_limit_sec=args.small_time_limit,
        large_time_limit_sec=args.large_time_limit,
        large_threshold=args.large_threshold,
        instance_template=args.instance_template,
    )
    print(result.csv_path)
    print(f"rows: {len(result.rows)}")


def _parse_int_tuple(value: str) -> tuple[int, ...]:
    return tuple(int(part.strip()) for part in value.split(",") if part.strip())


def _parse_str_tuple(value: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in value.split(",") if part.strip())


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


if __name__ == "__main__":
    main()
