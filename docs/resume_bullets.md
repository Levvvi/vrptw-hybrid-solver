# Resume Bullets

This document contains resume-ready wording. Any numeric placeholder must remain
unfilled until it can be traced to a real result CSV under `data/results/`.

## Evidence Rule

Before replacing `<X>`, `<Y>`, `<Z>`, or `<instances>`, collect:

- the exact `runs_*.csv` path;
- solver names and baselines;
- seed list;
- time budget;
- metric definition;
- failed/infeasible run counts;
- summary or pairwise statistics, if used.

If those files do not exist, keep the placeholder.

## Full Chinese Bullet

```text
实现城配 VRPTW 混合求解器：基于 Solomon benchmark 与 OSM 城市路网构建配送实例，小规模采用 OR-Tools CP-SAT 精确校验，大规模实现自适应 ALNS；在 <instances> 上较 <baseline> 车辆数减少 <X>、距离成本降低 <Y>%、求解时间缩短 <Z>%，并提供 Streamlit+Folium 地图演示。
```

## Short Chinese Bullet

```text
将博士阶段自适应策略选择思想迁移到 ALNS 算子选择，实现 VRPTW 混合求解器；支持 CP-SAT 精确校验、OR-Tools 基线、消融实验与地图可视化 demo。
```

## English Bullet With Placeholders

```text
Built a hybrid VRPTW solver for urban delivery using CP-SAT validation, OR-Tools baselines, and MOSADE-inspired adaptive ALNS; on <instance set>, reduced <metric> by <X> versus <baseline> under <time budget>, with Streamlit/Folium route visualization.
```

## Safe English Bullet Before Results

```text
Built a portfolio-grade VRPTW optimization project with exact small-instance validation, greedy and OR-Tools baselines, adaptive ALNS operator selection, reproducible experiment runners, statistical reporting, and Streamlit/Folium map visualization.
```

## Technical Depth Bullet

```text
Implemented ALNS destroy/repair operators, route-evaluation caching, nearest-neighbor insertion filtering, and a MOSADE-inspired pair-level selector that logs operator probabilities, convergence history, and profiler counters for ablation analysis.
```

## Demo/Engineering Bullet

```text
Packaged the VRPTW workflow into a reproducible Python project with Typer CLI, pytest/ruff/mypy quality gates, GitHub Actions CI, Dockerized Streamlit demo, solution JSON export, experiment CSVs, and Folium route maps.
```

## How To Fill The Numbers

Use this checklist before editing a bullet:

1. Run the batch protocol with fixed seeds and budgets.
2. Generate summary and pairwise statistics.
3. Confirm the baseline solver and metric direction.
4. Compute the percentage from the CSV, not from memory.
5. Link or cite the CSV path in README or interview notes.

Example template for a supported claim:

```text
Evidence: data/results/<experiment>/runs_<timestamp>.csv
Instances: <instances>
Seeds: <seed list>
Budget: <seconds> seconds, <iterations> ALNS iterations
Baseline: <baseline>
Metric: <vehicles/distance/cost/runtime>
Claim: <X>
```

## LinkedIn/GitHub Summary

```text
Hybrid VRPTW solver for urban delivery: exact validation for small cases, adaptive ALNS for scalable search, OR-Tools baselines, statistical experiment reporting, and Streamlit/Folium map visualization. The key design idea is transferring MOSADE-style adaptive strategy selection into ALNS destroy/repair operator selection.
```
