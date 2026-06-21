# Hybrid VRPTW Solver for Urban Delivery

A portfolio-grade operations research project for Vehicle Routing Problems with
Time Windows (VRPTW): exact validation on small instances, adaptive ALNS on
larger instances, OR-Tools baselines, experiment reporting, and map
visualization.

## Project Positioning

This repository is not meant to be "just another VRPTW solver." Its purpose is
to build an interview-ready engineering chain:

```text
business problem -> mathematical model -> exact validation -> heuristic solver
-> adaptive mechanism -> baseline comparison -> statistical evaluation
-> map visualization -> resume-ready evidence
```

The differentiating idea is to migrate MOSADE-style adaptive strategy selection
into ALNS operator selection for industrial routing scenarios. Small instances
will be checked with exact CP-SAT/MILP-style models, while larger instances will
be solved with adaptive ALNS and compared against OR-Tools baselines.

## Current Status

This repository is at the `P2-00` project skeleton stage.

Implemented:

- Installable Python package using a `src/` layout.
- Basic `pytest`, `ruff`, and `mypy` configuration.
- Minimal import test.

Not implemented yet:

- VRPTW data models.
- Solomon parser.
- Solvers and feasibility checker.
- Experiment runner.
- Streamlit/Folium demo.

## Quick Start

```bash
python -m pip install -e ".[dev]"
pytest -q
python -c "import vrptw_hybrid; print(vrptw_hybrid.__version__)"
```

Optional visualization dependencies will be used in later milestones:

```bash
python -m pip install -e ".[dev,vis]"
```

## Planned Milestones

1. `P2-00` to `P2-03`: project skeleton, config, CLI, core data models.
2. `P2-04` to `P2-08`: Solomon data layer, feasibility checking, metrics, I/O.
3. `P2-09` to `P2-12`: greedy solver, CP-SAT validation, OR-Tools baseline.
4. `P2-13` to `P2-23`: ALNS, adaptive operator selection, ablation support.
5. `P2-24` to `P2-28`: experiment runner, statistics, reporting.
6. `P2-29` to `P2-34`: city network data and Streamlit/Folium demo.
7. `P2-35` to `P2-39`: documentation, CI, deployment, interview notes.

## Notes On Results

No benchmark or performance numbers are reported yet. Any future README table
must be backed by files under `data/results/`; otherwise the value should remain
as a TODO placeholder.

## ALNS Performance Notes

The first ALNS optimization pass adds nearest-neighbor candidate filtering,
route-evaluation caching, and profiler counters. These changes do not alter the
VRPTW objective function or feasibility rules; they only reduce which insertion
candidates are evaluated first. If restricted candidate evaluation finds no
feasible insertion, repair falls back to the full candidate set.
