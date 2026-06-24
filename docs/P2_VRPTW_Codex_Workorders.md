# P2：城配 VRPTW 混合求解器 Codex 工单计划

版本：2026-06-21  
适用项目：P2 城配 VRPTW 混合求解器  
建议仓库名：`city-vrptw-hybrid-solver`  
建议 Python 包名：`vrptw_hybrid`  
目标用户：用 Codex 逐工单实现项目的人，而不是一次性让 Codex 生成完整系统。

---

## 0. 项目定位

本项目的核心不是“又写一个 VRPTW 求解器”，而是构建一条可以在面试中完整讲清楚的链路：

业务问题 → 数学建模 → 精确法校验 → 启发式求解 → 自适应机制 → 基准对比 → 统计评估 → 地图可视化 → 简历量化结果。

最终面试叙事应是：

> 我把博士阶段 MOSADE/自适应策略选择的思想迁移到 VRPTW 的 ALNS 算子选择中；小规模问题用 CP-SAT/MILP 精确解校验，中等规模问题用自适应 ALNS 求解，并与 OR-Tools 基线比较成本、车辆数、求解时间和收敛曲线；最后用 Streamlit + Folium 做可交互地图演示。

项目的技术价值在于“精确法与启发式的工程权衡”。项目的个人差异化价值在于“自适应策略选择从进化算法迁移到工业运筹场景”。

---

## 1. Codex 使用原则

不要把整份文件一次性丢给 Codex 让它“实现全部项目”。正确用法是：一次只执行一个工单，最多一个小里程碑。每次给 Codex 的提示词应包括：当前工单、已完成工单、约束、验收标准。每张工单完成后必须运行测试并提交。

固定执行流程：

1. 新建或切换分支：`feat/p2-xx-short-name`。
2. 把对应工单正文复制给 Codex。
3. 要求 Codex 先检查项目结构，再实现。
4. 要求 Codex 补充或更新测试。
5. 本地执行 `pytest -q`、`ruff check .`。
6. 手动检查结果，不接受“看起来能跑”。
7. 合并后再进入下一工单。

Codex 总提示词模板：

```text
你正在实现 P2 城配 VRPTW 混合求解器项目中的一个工单。请先阅读仓库结构，不要重写已有模块，不要破坏公开 API。优先写小而可测的代码。每个 solver 必须返回统一的 Solution 对象。每个随机过程必须支持 seed。完成后补充 pytest，并说明如何运行。

当前工单：<粘贴工单内容>
已完成工单：<列出已完成 ID>
约束：不要伪造实验结果；不要硬编码 benchmark 数字；不要把核心逻辑写进 notebook；不要使用外部 alns 包替代自研 ALNS 核心。
验收：<粘贴验收标准>
```

---

## 2. 最终交付物

项目结束时，仓库必须具备以下东西：

1. 可安装 Python 包：`pip install -e .`。
2. CLI：可用命令运行 Solomon 实例、城市路网实例、实验批处理。
3. 精确/基线求解器：小规模 CP-SAT arc-flow 模型；可选 COPT MILP；OR-Tools Routing baseline。
4. 自研 ALNS：包括初始解、destroy/repair 算子、接受准则、停止条件、算子自适应选择。
5. MOSADE-inspired 自适应选择器：不是直接复用 MOSADE，而是迁移“策略选择概率随历史成功贡献调整”的思想。
6. 评估模块：车辆数、距离、成本、可行性、运行时间、gap、收敛曲线、消融实验、统计检验。
7. Streamlit + Folium demo：地图上展示仓库、客户、车辆路线、时间窗、距离和求解指标。
8. README：包含业务背景、模型、算法、实验结果、复现实验命令、截图、面试讲法。
9. `docs/interview_notes.md`：准备面试讲法和简历 bullet。
10. `data/results/*.csv|json`：真实实验结果，不允许手填。

---

## 3. 建议最终仓库结构

```text
city-vrptw-hybrid-solver/
  README.md
  pyproject.toml
  LICENSE
  .gitignore
  .pre-commit-config.yaml
  configs/
    default.yaml
    solomon_small.yaml
    solomon_large.yaml
    city_demo.yaml
  data/
    raw/
      solomon/.gitkeep
      osm/.gitkeep
    processed/.gitkeep
    results/.gitkeep
    examples/
      mini_vrptw_8.json
      mini_city_20.json
  docs/
    modeling.md
    algorithm_alns.md
    adaptive_selector.md
    experiment_protocol.md
    interview_notes.md
    codex_workorders.md
  notebooks/
    00_data_sanity_check.ipynb
  scripts/
    download_solomon.py
    run_solomon_batch.py
    run_ablation.py
    run_scaling.py
    make_report_figures.py
  apps/
    streamlit_app.py
  src/
    vrptw_hybrid/
      __init__.py
      cli.py
      core/
        models.py
        objective.py
        checker.py
        solution_io.py
        metrics.py
      data/
        solomon.py
        synthetic.py
        osm_network.py
        distance_matrix.py
      solvers/
        base.py
        greedy.py
        exact_cp_sat.py
        copt_milp.py
        ortools_routing.py
        alns/
          __init__.py
          state.py
          operators.py
          repair.py
          destroy.py
          acceptance.py
          selectors.py
          solver.py
      experiments/
        runner.py
        protocol.py
        statistics.py
        plots.py
      visualization/
        folium_map.py
        geojson.py
        streamlit_components.py
      utils/
        random.py
        logging.py
        timing.py
        config.py
  tests/
    fixtures/
      mini_solomon.txt
      mini_vrptw_8.json
    test_solomon_parser.py
    test_checker.py
    test_objective.py
    test_greedy.py
    test_exact_cp_sat.py
    test_alns_operators.py
    test_selectors.py
    test_solution_io.py
    test_experiment_runner.py
```

---

## 4. 统一数据模型

Codex 实现任何模块前，必须遵守以下抽象。

### 4.1 VRPTWInstance

字段建议：

```python
@dataclass(frozen=True)
class Customer:
    id: int
    x: float
    y: float
    demand: int
    ready_time: float
    due_time: float
    service_time: float
    lat: float | None = None
    lon: float | None = None

@dataclass(frozen=True)
class VehicleSpec:
    capacity: int
    count: int
    fixed_cost: float = 0.0

@dataclass(frozen=True)
class VRPTWInstance:
    name: str
    depot: Customer
    customers: tuple[Customer, ...]
    vehicle: VehicleSpec
    distance_matrix: np.ndarray
    time_matrix: np.ndarray
    metadata: dict[str, Any]
```

### 4.2 Solution

```python
@dataclass(frozen=True)
class RouteStop:
    customer_id: int
    arrival_time: float
    start_service_time: float
    departure_time: float
    load_after: int

@dataclass(frozen=True)
class Route:
    vehicle_id: int
    stops: tuple[RouteStop, ...]
    distance: float
    duration: float
    load: int

@dataclass(frozen=True)
class Solution:
    instance_name: str
    solver_name: str
    routes: tuple[Route, ...]
    objective: float
    vehicles_used: int
    total_distance: float
    total_duration: float
    feasible: bool
    runtime_sec: float
    metadata: dict[str, Any]
```

### 4.3 目标函数

Solomon 基准建议报告两个层次：

1. `vehicles_used`：车辆数。
2. `total_distance`：总距离。

内部可以用组合目标方便计算：

```text
composite_cost = vehicle_weight * vehicles_used + total_distance
```

其中 `vehicle_weight` 必须足够大，保证车辆数优先。报告时不要只报 composite cost，必须同时报车辆数和距离。

---

## 5. 里程碑总览

| 里程碑 | 目标 | 工单 | 建议时间 |
|---|---|---:|---:|
| M0 | 仓库与工程骨架 | P2-00 ~ P2-03 | 2 天 |
| M1 | 数据层与可行性校验 | P2-04 ~ P2-08 | 4 天 |
| M2 | 精确解与基线 | P2-09 ~ P2-12 | 5 天 |
| M3 | ALNS 基础版 | P2-13 ~ P2-18 | 7 天 |
| M4 | 自适应机制与消融 | P2-19 ~ P2-23 | 7 天 |
| M5 | 实验评估与统计 | P2-24 ~ P2-28 | 5 天 |
| M6 | 城市路网与地图 | P2-29 ~ P2-33 | 6 天 |
| M7 | Demo、文档、简历包装 | P2-34 ~ P2-39 | 5 天 |

最短可用版本：完成 P2-00 到 P2-24。  
面试可展示版本：完成 P2-00 到 P2-36。  
完整作品集版本：完成 P2-00 到 P2-39。

---

# 6. 工单明细

## M0：仓库与工程骨架

### P2-00：初始化仓库与 Python 工程结构

目标：创建一个可安装、可测试、可持续迭代的 Python 项目骨架。

Codex 任务：

1. 创建 `pyproject.toml`。
2. 使用 `src/` layout。
3. 配置 `pytest`、`ruff`、`mypy` 的基础规则。
4. 创建 `README.md` 初稿。
5. 创建 `src/vrptw_hybrid/__init__.py`。
6. 创建最小测试 `tests/test_import.py`。
7. 添加 `.gitignore`，排除 `.venv/`、`data/raw/` 大文件、`data/processed/` 缓存、`__pycache__`。

建议依赖：

```toml
python = ">=3.11"
numpy
pandas
scipy
ortools
networkx
pyyaml
typer
rich
matplotlib
plotly
pytest
pytest-cov
ruff
mypy
```

可选依赖组：

```toml
vis = ["streamlit", "folium", "streamlit-folium", "osmnx", "geopandas"]
copt = ["coptpy"]
dev = ["pre-commit", "ipykernel"]
```

验收标准：

```bash
pip install -e ".[dev,vis]"
pytest -q
python -c "import vrptw_hybrid; print(vrptw_hybrid.__version__)"
```

Codex 提示词：

```text
实现 P2-00：初始化 city-vrptw-hybrid-solver 仓库。使用 src layout，创建 pyproject.toml、README、基础包、tests/test_import.py、ruff/pytest 配置。不要实现业务逻辑。完成后给出安装和测试命令。
```

---

### P2-01：建立统一配置与日志工具

目标：让后续 solver、实验、demo 都读取统一配置，避免参数散落在代码里。

Codex 任务：

1. 创建 `src/vrptw_hybrid/utils/config.py`。
2. 支持从 YAML 读取配置。
3. 支持 CLI 参数覆盖配置。
4. 创建 `src/vrptw_hybrid/utils/logging.py`。
5. 日志包含时间、模块名、level、message。
6. 添加 `configs/default.yaml`。

配置最少包含：

```yaml
seed: 42
objective:
  vehicle_weight: 100000.0
solver:
  time_limit_sec: 60
  max_iterations: 5000
  neighborhood_size: 25
alns:
  destroy_fraction_min: 0.05
  destroy_fraction_max: 0.25
  segment_length: 100
  reaction_factor: 0.2
  exploration_floor: 0.05
experiment:
  seeds: [1, 2, 3, 4, 5]
  output_dir: data/results
```

验收标准：

1. `load_config("configs/default.yaml")` 返回 dict 或 dataclass。
2. 缺失文件时给出清晰错误。
3. 有单元测试覆盖默认读取和覆盖逻辑。

Codex 提示词：

```text
实现 P2-01：添加 YAML 配置读取与日志工具。要求小而稳定，不引入复杂框架。补充单元测试，确保默认配置可读取、CLI 风格 override 可合并。
```

---

### P2-02：实现 CLI 入口骨架

目标：建立统一命令行入口，后续每个模块都能从 CLI 调用。

Codex 任务：

1. 使用 Typer 创建 `src/vrptw_hybrid/cli.py`。
2. 添加命令：
   - `vrptw info`
   - `vrptw validate-instance`
   - `vrptw solve`
   - `vrptw batch`
   - `vrptw plot`
3. 当前只实现 `info`，其他命令可以先打印 TODO，但参数结构要预留。
4. 在 `pyproject.toml` 中配置 console script：`vrptw = "vrptw_hybrid.cli:app"`。

验收标准：

```bash
vrptw info
vrptw --help
vrptw solve --help
```

Codex 提示词：

```text
实现 P2-02：添加 Typer CLI 骨架。只需要 info 命令真实可用，其他命令先保留参数和 TODO 输出。确保安装后可用 vrptw 命令。补测试或至少用 CliRunner 测 info。
```

---

### P2-03：建立核心类型模型

目标：定义统一数据结构，所有 solver 只认这些对象。

Codex 任务：

1. 创建 `core/models.py`。
2. 实现 `Customer`、`VehicleSpec`、`VRPTWInstance`、`RouteStop`、`Route`、`Solution`。
3. 使用 dataclass，保持不可变优先。
4. 增加基础校验函数，例如矩阵维度是否等于 `n+1`。
5. 添加 JSON 序列化辅助方法，或在 P2-08 实现。

验收标准：

1. 可构造 1 depot + 3 customers 的实例。
2. 距离矩阵维度错误时抛出清晰异常。
3. 类型模型无 solver 依赖。

Codex 提示词：

```text
实现 P2-03：在 core/models.py 中定义 VRPTW 的统一数据模型。要求 dataclass、类型注解、基础校验、测试。不要实现求解器。
```

---

## M1：数据层与可行性校验

### P2-04：实现 Solomon 实例解析器

目标：读取 Solomon VRPTW benchmark 文本，转为 `VRPTWInstance`。

Codex 任务：

1. 创建 `data/solomon.py`。
2. 支持 Solomon 标准文本格式。
3. 解析字段：customer id、x、y、demand、ready time、due date、service time。
4. 第一行客户 0 作为 depot。
5. 生成 Euclidean distance matrix 和 travel time matrix。
6. 支持 `limit_customers`，用于从 C101 截取前 10、25、50 个客户做小规模测试。
7. 添加 fixture：`tests/fixtures/mini_solomon.txt`。

实现注意：

- Solomon 数据的距离和时间常用欧氏距离，注意 double precision。
- 实验汇报时车辆数和距离分开报。
- 不要把外部 Solomon 数据文件提交到仓库；提供下载脚本或说明。

验收标准：

1. `parse_solomon(path)` 返回 `VRPTWInstance`。
2. `limit_customers=8` 时得到 8 个 customers + 1 depot。
3. 距离矩阵对称，对角线为 0。
4. 单元测试覆盖解析成功、字段数量异常、limit 行为。

Codex 提示词：

```text
实现 P2-04：写 Solomon VRPTW 文本解析器。请用 tests/fixtures/mini_solomon.txt 做测试，不要依赖网络下载。解析后生成 VRPTWInstance、distance_matrix、time_matrix。支持 limit_customers。
```

---

### P2-05：实现距离/时间矩阵工具

目标：把矩阵生成逻辑从 parser 中抽出来，后续城市路网也复用同一接口。

Codex 任务：

1. 创建 `data/distance_matrix.py`。
2. 实现：
   - `euclidean_distance_matrix(points)`
   - `round_matrix(matrix, decimals=None)`
   - `scale_to_int(matrix, factor)`，供 CP-SAT 使用。
3. 支持 NumPy 输入。
4. 添加数值容忍测试。

验收标准：

1. 3-4-5 三角形测试通过。
2. scaling 后矩阵为整数。
3. 原 Solomon parser 改为调用该模块。

Codex 提示词：

```text
实现 P2-05：抽象距离/时间矩阵工具，并重构 Solomon parser 使用它。要求数值测试清晰，不破坏 P2-04 测试。
```

---

### P2-06：实现可行性检查器

目标：任何 solver 返回的 Solution 都必须经过统一检查，避免“结果看起来有路线但实际违约”。

Codex 任务：

1. 创建 `core/checker.py`。
2. 检查以下约束：
   - 每个客户恰好访问一次。
   - depot 不作为普通客户重复访问。
   - 每条路线容量不超过车辆容量。
   - arrival/start/departure 满足服务时间。
   - start service 在 time window 内。
   - 相邻节点时间满足 travel time。
   - 车辆数不超过可用车辆数。
3. 返回 `FeasibilityReport`，包含 `feasible: bool` 和 violations 列表。
4. 添加严格/宽松容忍参数 `tol=1e-6`。

验收标准：

1. 正确解 feasible。
2. 漏客户、重复客户、超容量、超时间窗均能检测。
3. 所有 solver 后续必须调用 checker。

Codex 提示词：

```text
实现 P2-06：写 VRPTW Solution 可行性检查器。请设计 FeasibilityReport，详细列出 violations。补充多个负例单元测试：重复访问、漏访问、超容量、时间窗违约。
```

---

### P2-07：实现目标函数与指标计算

目标：统一计算车辆数、距离、duration、组合目标、gap。

Codex 任务：

1. 创建 `core/objective.py` 和 `core/metrics.py`。
2. 实现：
   - `compute_route_distance(route, instance)`
   - `compute_solution_metrics(solution, instance)`
   - `composite_objective(vehicles_used, total_distance, vehicle_weight)`
   - `gap_percent(value, reference)`
3. 明确处理 reference 为 0 或 None 的情况。
4. gap 对 BKS/精确解都可用。

验收标准：

1. 简单路线距离计算正确。
2. composite objective 可配置。
3. gap 计算有测试。

Codex 提示词：

```text
实现 P2-07：添加 objective 与 metrics 模块。统一计算车辆数、总距离、组合目标和 gap。要求有单元测试，并让 checker/后续 solver 可以复用。
```

---

### P2-08：实现 Solution 序列化与结果落盘

目标：后续实验结果可复现、可画图、可放进 README。

Codex 任务：

1. 创建 `core/solution_io.py`。
2. 支持 Solution 保存为 JSON。
3. 支持从 JSON 读取 Solution。
4. 支持实验指标保存为 CSV。
5. JSON 中必须包含：instance name、solver name、seed、runtime、routes、objective、feasible、git commit 可选。

验收标准：

1. Solution round-trip 后字段不丢。
2. JSON 文件人类可读，带缩进。
3. `data/results/` 不提交真实大结果，只提交 `.gitkeep`。

Codex 提示词：

```text
实现 P2-08：添加 Solution JSON 序列化与结果 CSV 写入工具。要求 round-trip 测试通过。不要写 solver。
```

---

## M2：精确解与基线

### P2-09：实现 Greedy 初始解

目标：获得一个简单、可行、可解释的初始解，供 ALNS 起点和 baseline 使用。

Codex 任务：

1. 创建 `solvers/greedy.py`。
2. 实现最近邻或 earliest-due-date 插入式构造。
3. 每次尝试把客户插入已有路线中可行位置；不可插入时开新车。
4. 支持 seed，但 deterministic 模式下结果固定。
5. 输出统一 `Solution`。

验收标准：

1. 对 mini instance 生成 feasible solution。
2. 结果经过 checker。
3. 若车辆不足，返回 infeasible solution 或抛出受控异常，不允许静默失败。

Codex 提示词：

```text
实现 P2-09：添加 greedy 初始解 solver。使用统一 Solution 对象，必须调用 checker。支持 deterministic 行为和 seed。补充 mini instance 测试。
```

---

### P2-10：实现小规模 CP-SAT arc-flow 精确模型

目标：用 OR-Tools CP-SAT 建显式 VRPTW 整数模型，为小实例提供精确解/下界/可行性校验。

数学模型建议：

集合：

- `N = {0, 1, ..., n}`，0 是 depot。
- `K = {0, ..., m-1}`，车辆集合。

变量：

- `x[i,j,k] ∈ {0,1}`：车辆 k 是否从 i 到 j。
- `u[i,k] ∈ {0,1}`：客户 i 是否由车辆 k 服务。
- `t[i,k] ∈ Z`：车辆 k 到达 i 的时间。
- `load[i,k] ∈ Z`：车辆 k 到达 i 后载重，可选。
- `used[k] ∈ {0,1}`：车辆 k 是否使用。

约束：

1. 每个客户恰好服务一次。
2. 每辆车从 depot 出发至多一次，回 depot 至多一次。
3. flow conservation。
4. 容量约束。
5. 时间窗约束。
6. Big-M 时间递推：`t[j,k] >= t[i,k] + service_i + travel_ij - M*(1-x[i,j,k])`。
7. 禁止自环 `x[i,i,k]=0`。

目标：

```text
min vehicle_weight * sum(used[k]) + sum(distance[i,j] * x[i,j,k])
```

实现注意：

- CP-SAT 只能处理整数，距离/时间要 scale。
- 该模型只用于 n<=25 的小实例，不要承诺超出证据范围的精确求解。
- time limit 到达时可返回 FEASIBLE + bound 信息。

Codex 任务：

1. 创建 `solvers/exact_cp_sat.py`。
2. 实现 `CPSATVRPTWSolver`。
3. 支持参数：time limit、scale factor、vehicle_weight。
4. 解析 solver status：OPTIMAL、FEASIBLE、INFEASIBLE、UNKNOWN。
5. 返回 Solution，并在 metadata 中记录 status、best_bound、objective。
6. 添加 mini instance 测试。

验收标准：

1. mini 8 客户实例能求出 feasible solution。
2. 客户访问不重复、不遗漏。
3. status 与 runtime 写入 metadata。
4. `pytest -q tests/test_exact_cp_sat.py` 通过。

Codex 提示词：

```text
实现 P2-10：用 OR-Tools CP-SAT 写小规模 VRPTW arc-flow 精确模型。注意 CP-SAT 只能用整数，矩阵要 scale。返回统一 Solution，并把 status/bound/runtime 写入 metadata。只要求 mini instance 测试通过，不追求中等及以上规模性能。
```

---

### P2-11：实现可选 COPT MILP 适配器

目标：为国产求解器/运筹岗位增加关键词，但不让许可证问题阻塞主线。

Codex 任务：

1. 创建 `solvers/copt_milp.py`。
2. 如果 `coptpy` 未安装，给出清晰错误：`COPT is optional; install with pip install -e .[copt] and configure license`。
3. 建模逻辑与 CP-SAT 类似。
4. 不强制 CI 跑 COPT 测试；测试只覆盖 import fallback。
5. README 标注“可选”。

验收标准：

1. 未安装 coptpy 时不会导致整个包 import 失败。
2. 有 `pytest.mark.optional` 或 skip 逻辑。
3. 不影响 CP-SAT 和 ALNS 主线。

Codex 提示词：

```text
实现 P2-11：添加可选 COPT MILP 适配器骨架。重点是优雅处理 coptpy 未安装/无许可证，不要让 CI 失败。模型接口与 BaseSolver 统一。COPT 真实求解可先最小实现。
```

---

### P2-12：实现 OR-Tools Routing baseline

目标：提供工业界常用基线，便于与自研 ALNS 比较。

说明：OR-Tools Routing Model 是 VRP/VRPTW 高层接口，适合做强基线；它不等同于 P2-10 中的显式 CP-SAT arc-flow 精确模型。README 里必须说清楚这点，避免面试时被追问露馅。

Codex 任务：

1. 创建 `solvers/ortools_routing.py`。
2. 使用 OR-Tools RoutingIndexManager / RoutingModel。
3. 添加 capacity dimension。
4. 添加 time dimension。
5. 支持 first solution strategy 和 local search metaheuristic 参数。
6. 输出统一 Solution。
7. 在 metadata 中记录 OR-Tools 参数。

验收标准：

1. mini instance 可解。
2. 结果经过 checker。
3. 与 greedy、CP-SAT 的 Solution 结构一致。

Codex 提示词：

```text
实现 P2-12：添加 OR-Tools Routing baseline，用 RoutingModel 建 VRPTW，包括 capacity/time dimension。输出统一 Solution。README 中明确它是 routing baseline，不是 P2-10 的 CP-SAT 精确模型。
```

---

## M3：ALNS 基础版

### P2-13：定义 Solver 基类与 ALNS State

目标：让所有 solver 具有统一接口，让 ALNS 状态可增量修改。

Codex 任务：

1. 创建 `solvers/base.py`。
2. 定义 `BaseSolver.solve(instance, config, seed) -> Solution`。
3. 创建 `solvers/alns/state.py`。
4. 实现 `ALNSState`：routes、unassigned、cost、feasibility metadata。
5. 支持从 Solution 转 State、从 State 转 Solution。
6. 支持 deep copy 或安全 copy。

验收标准：

1. Greedy/CP-SAT/OR-Tools 继承或兼容 BaseSolver。
2. Solution ↔ State round-trip 测试通过。
3. State 修改不污染原对象。

Codex 提示词：

```text
实现 P2-13：添加 BaseSolver 接口和 ALNSState。重构已有 solver 使其兼容 BaseSolver。实现 Solution 与 ALNSState 的双向转换和测试。
```

---

### P2-14：实现插入可行性与路线增量评估

目标：ALNS 的性能瓶颈在插入评估，必须集中实现。

Codex 任务：

1. 在 `solvers/alns/state.py` 或新文件 `route_eval.py` 中实现：
   - `evaluate_route(route_customer_ids, instance)`
   - `is_feasible_insertion(route, customer, position, instance)`
   - `insertion_delta_cost(route, customer, position, instance)`
2. 返回 arrival/start/departure/load。
3. 使用清晰的 `InsertionResult`。
4. 初版可 O(route length) 计算，后续再优化。

验收标准：

1. 对已有可行路线插入客户，能判断可行/不可行。
2. 时间窗和容量都被考虑。
3. 单元测试覆盖中间插入、末尾插入、不可插入。

Codex 提示词：

```text
实现 P2-14：为 ALNS 写 route evaluation 和 insertion feasibility。要求正确性优先，不做过早优化。补充时间窗、容量、插入位置测试。
```

---

### P2-15：实现 Destroy 算子集合

目标：提供 ALNS 的破坏算子组合，为后续自适应选择提供候选策略。

算子最少包括：

1. `random_removal`：随机移除 q 个客户。
2. `worst_distance_removal`：移除对距离贡献最大的客户。
3. `shaw_related_removal`：按地理距离、时间窗、需求相似性移除相关客户。
4. `route_removal`：移除一整条短路线或随机路线。
5. `time_window_tight_removal`：优先移除时间窗紧/难服务客户。

Codex 任务：

1. 创建 `solvers/alns/destroy.py`。
2. 每个 operator 接口统一：`operator(state, instance, rng, q) -> ALNSState`。
3. 每个 operator 有 `name`。
4. 移除客户进入 `state.unassigned`。
5. 不直接修改原 state。

验收标准：

1. 每个算子至少有一个单元测试。
2. 移除后客户总集合不丢失。
3. unassigned 数量符合 q 或可解释。

Codex 提示词：

```text
实现 P2-15：添加 ALNS destroy operators：random、worst-distance、shaw-related、route-removal、time-window-tight-removal。统一接口，不修改原 state。补测试验证客户不丢失。
```

---

### P2-16：实现 Repair 算子集合

目标：把未分配客户插回路线，形成可行候选解。

算子最少包括：

1. `greedy_cheapest_insertion`。
2. `regret_2_insertion`。
3. `regret_3_insertion`。
4. `time_window_priority_insertion`。
5. `noise_insertion`。

Codex 任务：

1. 创建 `solvers/alns/repair.py`。
2. 每个 operator 接口统一：`operator(state, instance, rng) -> ALNSState`。
3. 若无法插入已有路线，可以开新路线；若车辆不足，记录 infeasible。
4. 所有插入必须调用 P2-14 的 insertion evaluator。
5. 支持 deterministic seed。

验收标准：

1. 对 destroy 后的 mini state 能修复为 feasible。
2. 不重复插入客户。
3. regret 算子有测试。

Codex 提示词：

```text
实现 P2-16：添加 ALNS repair operators：cheapest insertion、regret-2、regret-3、time-window-priority、noise insertion。必须复用 insertion evaluator，输出客户集合完整的 state。补测试。
```

---

### P2-17：实现接受准则与停止条件

目标：让 ALNS 能探索，不只接受更优解。

Codex 任务：

1. 创建 `solvers/alns/acceptance.py`。
2. 实现：
   - `AlwaysBetterAcceptance`
   - `SimulatedAnnealingAcceptance`
3. 创建 stopping criteria：
   - max iterations
   - time limit
   - no improvement iterations
4. SA 参数：initial temperature、cooling rate、minimum temperature。
5. 所有随机接受必须支持 rng。

验收标准：

1. 更优解必接受。
2. 更差解按概率接受。
3. temperature 随迭代下降。
4. 单元测试不依赖随机偶然，可通过固定 seed 或概率边界测试。

Codex 提示词：

```text
实现 P2-17：添加 ALNS acceptance 和 stopping criteria。包括 better-only 和 simulated annealing。测试要稳定，不要写随机脆弱测试。
```

---

### P2-18：实现基础 ALNS Solver

目标：把 initial solution、destroy、repair、acceptance 串成可运行 solver。

Codex 任务：

1. 创建 `solvers/alns/solver.py`。
2. 流程：
   - 用 greedy 生成初始解。
   - 循环选择 destroy + repair。
   - 生成 candidate。
   - checker 校验。
   - acceptance 决定是否替换 current。
   - 维护 best。
   - 记录 convergence history。
3. 初版 operator selection 使用 uniform random。
4. metadata 记录：iterations、best_iteration、history、seed。
5. CLI 中接入 `--solver alns`。

验收标准：

1. mini instance 能运行并返回 feasible solution。
2. ALNS 不劣于 greedy，至少在同一 objective 下通常不劣；测试中可只要求 feasible。
3. history 长度与迭代数一致或可解释。
4. CLI 可运行：

```bash
vrptw solve --instance tests/fixtures/mini_solomon.txt --solver alns --max-iterations 200 --seed 42
```

Codex 提示词：

```text
实现 P2-18：把 greedy initial solution、destroy、repair、acceptance 串成基础 ALNS solver。初版 operator selection 用 uniform random。返回 Solution，metadata 包含 convergence history。接入 CLI。
```

---

## M4：自适应机制与消融

### P2-19：实现 OperatorSelector 接口与 UniformSelector

目标：把算子选择从 ALNS 主循环中抽象出来，方便替换为自适应版本。

Codex 任务：

1. 创建 `solvers/alns/selectors.py`。
2. 定义 `OperatorSelector`：
   - `select_destroy(rng)`
   - `select_repair(rng)`
   - `update(event)`
   - `snapshot()`
3. 实现 `UniformSelector`。
4. ALNS Solver 改为依赖 selector。
5. `event` 记录：destroy name、repair name、accepted、new_best、delta_cost、feasible。

验收标准：

1. UniformSelector 选择分布近似均匀，测试只做基本合法性。
2. ALNS 行为不被破坏。
3. selector snapshot 写入 history。

Codex 提示词：

```text
实现 P2-19：抽象 ALNS operator selection 接口，并实现 UniformSelector。ALNS 主循环改为通过 selector 选择 destroy/repair，并在每次迭代后 update event。
```

---

### P2-20：实现经典 RouletteWheelSelector

目标：建立一个标准 ALNS 自适应基线，与 MOSADE-inspired 版本对比。

机制建议：

- 每个算子有 weight。
- 每个 segment 汇总 score。
- 奖励：
  - new global best：5
  - improved current：3
  - accepted but not improved：1
  - feasible but rejected：0.2
  - infeasible：0
- 每 `segment_length` 次更新：

```text
w_i = (1 - reaction_factor) * w_i + reaction_factor * avg_score_i
```

- 选择概率来自 weight 归一化。
- 设置 exploration floor，防止某个算子永久为 0。

Codex 任务：

1. 在 `selectors.py` 中实现 `RouletteWheelSelector`。
2. 分别维护 destroy 和 repair 权重。
3. 支持 snapshot 输出 weights/probabilities。
4. ALNS 配置支持 `selector=roulette`。

验收标准：

1. 奖励事件能提高对应算子权重。
2. 概率和为 1。
3. 有 exploration floor。
4. history 中能看到权重变化。

Codex 提示词：

```text
实现 P2-20：添加经典 ALNS RouletteWheelSelector。按 segment 汇总奖励并更新 destroy/repair 权重。支持 exploration floor 和 snapshot。补充权重更新测试。
```

---

### P2-21：实现 MOSADE-inspired AdaptiveSelector

目标：实现本项目的独特故事线：把 MOSADE 的“自适应策略选择”思想迁移到 ALNS 算子选择。

注意：这里不是把 MOSADE 代码粘进来，而是迁移机制思想。README 中表述应为：

> Inspired by self-adaptive strategy selection in MOSADE, we treat each destroy-repair pair as a search strategy. Its probability is updated from recent success, improvement magnitude, feasibility contribution, and diversity contribution.

机制建议：

1. 把 `(destroy_operator, repair_operator)` 作为 strategy pair，而不是分别独立选择。
2. 维护 pair-level credit matrix：`credit[d, r]`。
3. 每次迭代生成 reward：

```text
reward = 5.0 * is_new_best
       + 3.0 * is_improved_current
       + 1.0 * is_accepted
       + 0.2 * is_feasible
       + diversity_bonus
       + normalized_improvement
```

4. 近期记忆窗口 `memory_size`，只用最近若干 segment 更新。
5. 用 softmax 生成概率：

```text
p[d,r] = softmax(credit[d,r] / temperature)
```

6. 加 exploration floor：

```text
p = (1 - epsilon) * p + epsilon / num_pairs
```

7. credit 衰减：

```text
credit = decay * credit + (1 - decay) * recent_reward
```

8. 记录每个 pair 的选择次数、接受次数、新 best 次数、平均 improvement。

Codex 任务：

1. 在 `selectors.py` 中实现 `MOSADEInspiredSelector`。
2. 支持 pair-level selection。
3. 支持参数：temperature、decay、memory_size、exploration_floor。
4. 在 ALNS solver 中兼容 pair selector。
5. history 中输出 pair probability heatmap 数据。
6. docs 中添加 `docs/adaptive_selector.md` 初稿。

验收标准：

1. 某 pair 连续获得高 reward 后概率上升。
2. 所有 pair 概率和为 1。
3. exploration floor 生效。
4. seed 固定时可复现。
5. 文档能讲清“为什么这是 MOSADE 思想迁移，而不是硬蹭名字”。

Codex 提示词：

```text
实现 P2-21：添加 MOSADEInspiredSelector。把 destroy-repair pair 当作策略，使用 recent reward、credit decay、softmax、exploration floor 更新选择概率。更新 ALNS solver 兼容 pair selector，并写 docs/adaptive_selector.md 初稿。补充概率更新和可复现测试。
```

---

### P2-22：实现可配置消融开关

目标：让实验能回答“自适应机制到底有没有用”。

消融组建议：

1. `greedy`。
2. `ortools_routing`。
3. `alns_uniform`。
4. `alns_roulette`。
5. `alns_mosade_adaptive`。
6. `alns_mosade_no_pair_memory`。
7. `alns_mosade_no_diversity_bonus`。
8. `alns_mosade_no_shaw_destroy`。
9. `alns_mosade_no_regret_repair`。

Codex 任务：

1. 在配置中支持启用/禁用某类 operator。
2. 支持 selector 类型选择。
3. 支持 ablation name 写入结果。
4. 添加 `configs/ablation.yaml`。

验收标准：

1. 不同 ablation 可以通过 CLI 跑。
2. 结果 CSV 中有 `ablation` 字段。
3. 禁用算子后 selector 不会选到该算子。

Codex 提示词：

```text
实现 P2-22：添加 ALNS 消融实验配置机制。支持 selector 类型、启用/禁用 destroy/repair operators、ablation name。结果 metadata/CSV 必须记录 ablation。
```

---

### P2-23：实现 ALNS 性能优化第一轮

目标：让 100 客户 Solomon 实例稳定运行，为后续 1000 点 scaling 打基础。

优化方向：

1. 预计算每个客户的 nearest neighbors。
2. Shaw removal 使用候选邻域，不全量扫描。
3. repair 插入只评估候选路线或候选位置。
4. 路线 evaluation 做缓存，state 修改后局部失效。
5. 添加 profiler 输出。

Codex 任务：

1. 添加 nearest neighbor cache。
2. 添加可配置 `candidate_neighbor_size`。
3. 保持 correctness test 不变。
4. 添加基准脚本 `scripts/profile_alns.py`。

验收标准：

1. 100 customer instance 在合理时间内完成 smoke run。
2. mini tests 全部通过。
3. README 说明“优化不改变目标函数，只改变候选评估范围”。

Codex 提示词：

```text
实现 P2-23：为 ALNS 添加第一轮性能优化，包括 nearest neighbor cache、候选插入限制和简单 profiler。不要牺牲 correctness，mini tests 必须保持通过。
```

---

## M5：实验评估与统计

### P2-24：实现实验 Runner

目标：统一批量运行多个 instance、solver、seed、time budget。

Codex 任务：

1. 创建 `experiments/runner.py`。
2. 输入：配置文件、instances 列表、solvers 列表、seeds、time limits。
3. 输出：
   - `data/results/runs_<timestamp>.csv`
   - 每个 solution 的 JSON。
4. 失败时记录 error，不中断整个 batch。
5. CLI 接入：`vrptw batch --config configs/solomon_small.yaml`。

验收标准：

1. mini batch 能跑 greedy + alns_uniform + alns_mosade。
2. CSV 字段完整：instance、solver、selector、seed、vehicles、distance、cost、runtime、feasible、status、error。
3. batch 可重复。

Codex 提示词：

```text
实现 P2-24：添加实验 Runner，能批量运行多个 solver/seed/instance 并输出 CSV + solution JSON。失败要记录 error 而不是中断。接入 vrptw batch。
```

---

### P2-25：接入 Solomon BKS/参考结果表

目标：用已知最优或最佳已知解计算 gap，提升评估可信度。

Codex 任务：

1. 创建 `data/solomon_bks.py` 或 `data/reference/solomon_bks.csv`。
2. 初期只手动维护常用 C101/R101/RC101 的小表；后续再扩展。
3. BKS 字段：instance、best_vehicles、best_distance、source。
4. gap 报告分两类：
   - vehicle gap/是否同车辆数。
   - distance gap when vehicles equal。
5. 不要把未核实数字当作 BKS。

验收标准：

1. 找不到 BKS 时 gap 留空，不报错。
2. 找到 BKS 时结果 CSV 有 gap 字段。
3. README 说明 BKS 来源。

Codex 提示词：

```text
实现 P2-25：添加 Solomon BKS/参考结果表支持。不要硬编码未知数字；找不到 BKS 时 gap 为空。结果 CSV 输出车辆数差异和距离 gap。
```

---

### P2-26：实现统计检验模块

目标：把你的消融和统计检验能力变成项目亮点。

建议方法：

1. 对同一 instance、同一 seed budget 下不同 solver 的 distance/cost 做配对比较。
2. 使用 Wilcoxon signed-rank test 或 Mann-Whitney U，视实验设计而定。
3. 多重比较用 Holm 校正。
4. 报告 effect size，例如 Cliff's delta 或 rank-biserial correlation。

Codex 任务：

1. 创建 `experiments/statistics.py`。
2. 输入 runs CSV。
3. 输出：
   - summary table。
   - pairwise comparison table。
   - Holm-adjusted p-values。
4. 添加测试：用小型人工数据验证方向和字段。

验收标准：

1. 函数能处理缺失/失败 run。
2. 输出 CSV 可读。
3. docs 中解释统计检验不是“证明最优”，而是评估稳定收益。

Codex 提示词：

```text
实现 P2-26：添加实验统计检验模块。读取 runs CSV，输出 solver summary、pairwise comparison、Holm corrected p-values、effect size。补充小数据测试。
```

---

### P2-27：实现收敛曲线与对比图

目标：生成 README 和面试展示用图。

图表至少包括：

1. 每个 solver 的 best cost over time/iteration。
2. solver cost vs runtime scatter。
3. gap boxplot。
4. operator probability over iterations。
5. MOSADE pair probability heatmap。

Codex 任务：

1. 创建 `experiments/plots.py`。
2. 创建 `scripts/make_report_figures.py`。
3. 从 results CSV 和 solution metadata 读取 history。
4. 输出到 `data/results/figures/`。
5. README 预留图片链接。

验收标准：

1. 用 mini results 可以生成至少 2 张图。
2. 图像文件不为空。
3. 不要求固定颜色。

Codex 提示词：

```text
实现 P2-27：添加实验图表模块，生成 convergence、cost-runtime、gap boxplot、operator probability、pair heatmap。用 mini result 做 smoke test。不要硬编码真实实验数值。
```

---

### P2-28：实现 Scaling 实验脚本

目标：准备更大规模实验的简历指标，但只有真实跑通后才能填写量化百分比。

Codex 任务：

1. 创建 `scripts/run_scaling.py`。
2. 支持生成或读取规模：50、100、200、500、1000。
3. 每个规模运行 greedy、ortools_routing、alns_mosade。
4. 输出 scaling CSV。
5. 对 1000 点设置更短/更实际的 time budget，如 60/120/300 秒可配。

验收标准：

1. 至少 synthetic 50/100 可跑通。
2. 1000 点脚本可以启动并记录失败/timeout。
3. README 明确：只有 `data/results/scaling_*.csv` 存在后才能写更大规模下的量化结论。

Codex 提示词：

```text
实现 P2-28：添加 scaling 实验脚本，支持 50/100/200/500/1000 规模。结果写 CSV，timeout/失败也要记录。不要在代码或 README 中编造 X%。
```

---

## M6：城市路网与地图

### P2-29：实现城市路网数据获取与缓存

目标：接入开源城市路网数据，为“城配”场景提供地图真实性。

建议工具：OSMnx + NetworkX。

Codex 任务：

1. 创建 `data/osm_network.py`。
2. 支持通过 place name 或 bbox 下载 driving network。
3. 支持缓存为 GraphML：`data/raw/osm/<city>.graphml`。
4. 如果缓存存在，优先读取缓存。
5. 给 edge 添加 travel_time：
   - 若有 speed_kph，用 length / speed。
   - 若无 speed_kph，按 highway type 设置默认速度。
6. 添加网络下载失败时的清晰错误。

验收标准：

1. 不联网情况下，如果有缓存可以继续运行。
2. 函数接口不直接依赖 Streamlit。
3. 有单元测试覆盖“缓存路径选择”和“travel_time 计算”，不强依赖真实 OSM 下载。

Codex 提示词：

```text
实现 P2-29：添加 OSMnx 城市路网获取与缓存模块。支持 place/bbox，缓存 GraphML，补 travel_time。测试不要依赖真实网络，重点测缓存逻辑和 travel_time 计算。
```

---

### P2-30：实现城市订单/客户生成器

目标：在真实城市路网上生成可控 VRPTW demo 实例。

Codex 任务：

1. 创建 `data/synthetic.py`。
2. 从 OSM graph 节点中抽样 depot 和 customers。
3. 支持参数：客户数、车辆数、容量、时间窗宽度、需求分布、服务时间。
4. 生成 lat/lon/x/y。
5. 输出 `VRPTWInstance`。
6. 支持保存为 JSON。

验收标准：

1. 固定 seed 时生成结果一致。
2. 客户 time windows 合法。
3. demand 不超过容量。
4. 生成 mini city 20 demo JSON。

Codex 提示词：

```text
实现 P2-30：添加城市 VRPTW synthetic instance generator。基于 OSM graph 节点抽样 depot/customers，生成需求、服务时间、时间窗。固定 seed 可复现，输出 VRPTWInstance 和 JSON。
```

---

### P2-31：实现路网最短路距离/时间矩阵

目标：把城市节点之间的欧氏距离替换为路网距离/时间。

Codex 任务：

1. 在 `data/osm_network.py` 或 `distance_matrix.py` 中添加：
   - `nearest_graph_nodes(graph, lat_lon_points)`
   - `network_distance_time_matrix(graph, node_ids)`
2. 使用 NetworkX shortest path length。
3. 支持 weight：`length`、`travel_time`。
4. 对不可达节点对给出清晰处理策略：报错或大 M，不要静默设 0。
5. 缓存矩阵到 `data/processed/`。

验收标准：

1. 小图人工测试最短路径正确。
2. 矩阵维度正确。
3. 不可达处理有测试。

Codex 提示词：

```text
实现 P2-31：添加基于 NetworkX/OSMnx 的路网距离和时间矩阵计算。支持 length/travel_time weight，缓存矩阵。用小型人工 graph 写单元测试。
```

---

### P2-32：实现 route geometry 与 GeoJSON 导出

目标：让 Folium 地图显示真实道路路径，而不是客户点之间的直线。

Codex 任务：

1. 创建 `visualization/geojson.py`。
2. 根据 solution 的客户顺序，找到对应 graph node。
3. 对相邻节点计算 shortest path。
4. 从 graph nodes/edges 提取 geometry 或 lat/lon。
5. 输出 GeoJSON FeatureCollection。
6. 每条 route 一个 Feature，包含 vehicle_id、distance、load、stops。

验收标准：

1. 人工小图可导出 valid GeoJSON。
2. 无 geometry edge 时用 node 坐标 fallback。
3. GeoJSON 可被 Folium 读取。

Codex 提示词：

```text
实现 P2-32：添加 Solution route geometry 到 GeoJSON 的导出。基于 graph shortest path，支持 edge geometry 缺失时用 node 坐标 fallback。补小图测试。
```

---

### P2-33：实现 Folium 地图渲染模块

目标：把路线、仓库、客户点、时间窗指标可视化。

Codex 任务：

1. 创建 `visualization/folium_map.py`。
2. 输入：instance、solution、可选 graph/geojson。
3. 输出：Folium Map 或 HTML 文件。
4. 地图元素：
   - depot marker。
   - customer marker。
   - route polyline。
   - popup：customer id、demand、time window、arrival time。
   - layer control。
5. 路线颜色自动分配，不要求指定品牌色。

验收标准：

1. mini city solution 可生成 HTML。
2. HTML 文件存在且非空。
3. 没有 graph 时也能画客户间直线。

Codex 提示词：

```text
实现 P2-33：添加 Folium 地图渲染模块。输入 VRPTWInstance 和 Solution，画 depot、customer、route、popup、layer control。支持无 graph 时画直线。输出 HTML。
```

---

## M7：Demo、文档、简历包装

### P2-34：实现 Streamlit Demo 页面

目标：让面试官 30 秒看懂项目。

页面结构建议：

1. Sidebar：选择实例、solver、seed、time limit、max iterations。
2. 主区域顶部：关键指标卡片。
3. 中部：Folium 地图。
4. 下部：路线表、收敛曲线、operator probability 曲线。
5. 底部：下载 solution JSON 和 experiment CSV。

Codex 任务：

1. 创建 `apps/streamlit_app.py`。
2. 接入 solvers：greedy、ortools_routing、alns_uniform、alns_mosade。
3. 使用 `streamlit-folium` 嵌入地图。
4. 对长时间求解显示 spinner/progress。
5. 支持读取预计算 result，避免 demo 现场卡住。

验收标准：

```bash
streamlit run apps/streamlit_app.py
```

1. 页面能启动。
2. 能加载 mini demo。
3. 能运行 greedy/ALNS small。
4. 能显示地图和指标。

Codex 提示词：

```text
实现 P2-34：创建 Streamlit demo。支持选择 demo instance、solver、seed、time limit，运行后显示指标卡片、Folium 地图、路线表、收敛曲线，并支持下载 solution JSON。注意 demo 要能读取预计算结果。
```

---

### P2-35：完善 README 项目说明

目标：把 GitHub 首页变成简历证明材料。

README 必须包含：

1. 项目一句话。
2. 背景：VRPTW 是什么，城配为什么需要。
3. 数学模型摘要。
4. 求解策略：CP-SAT exact small、OR-Tools baseline、ALNS large。
5. MOSADE-inspired 自适应机制图示或说明。
6. 实验协议：instances、seeds、time budget、metrics。
7. 真实结果表：没有结果前用 TODO，不许编造。
8. Demo 截图/GIF。
9. 快速开始命令。
10. 项目结构。
11. 局限性：非实时派单、路况简化、COPT 可选。
12. 面试讲法：约束如何数学化、为什么不全用精确法、自适应算子如何设计、如何验证解质量。

验收标准：

1. 新读者 5 分钟能跑 mini demo。
2. README 中所有命令真实可执行。
3. 没有伪造 X%。

Codex 提示词：

```text
实现 P2-35：重写 README，使其成为作品集首页。必须包括背景、模型、算法、实验协议、快速开始、demo、局限性和面试讲法。所有结果数字如果没有真实 CSV 支撑，就保留 TODO。
```

---

### P2-36：撰写算法文档

目标：把技术细节沉淀成面试可讲材料。

Codex 任务：

1. 创建/完善：
   - `docs/modeling.md`
   - `docs/algorithm_alns.md`
   - `docs/adaptive_selector.md`
   - `docs/experiment_protocol.md`
2. 每个文档都要有图或伪代码。
3. `adaptive_selector.md` 重点讲：
   - 为什么算子选择类似策略选择。
   - reward 如何定义。
   - 为什么 pair-level 比独立 destroy/repair 更合理。
   - 与 uniform/roulette 的区别。

验收标准：

1. 文档能独立阅读。
2. 没有大段堆公式但不解释业务含义。
3. 包含面试问答要点。

Codex 提示词：

```text
实现 P2-36：完善 docs 下的 modeling、ALNS、adaptive selector、experiment protocol 文档。要求公式 + 业务解释 + 伪代码 + 面试问答要点。不要编造实验结论。
```

---

### P2-37：CI、pre-commit 与质量门禁

目标：让项目看起来像工程项目，不是脚本堆。

Codex 任务：

1. 添加 `.github/workflows/ci.yml`。
2. CI 执行：install、ruff、pytest。
3. 添加 `.pre-commit-config.yaml`。
4. 测试不依赖 COPT license、不依赖真实 OSM 网络。
5. README 添加 badge。

验收标准：

1. GitHub Actions 通过。
2. 本地 `pre-commit run --all-files` 通过。
3. 网络不可用时测试仍可跑。

Codex 提示词：

```text
实现 P2-37：添加 GitHub Actions CI 和 pre-commit。CI 只跑不依赖外部网络/许可证的测试。添加 README badge。确保 ruff 和 pytest 通过。
```

---

### P2-38：Docker 与部署说明

目标：给 Streamlit demo 一个可复现部署路径。

Codex 任务：

1. 添加 `Dockerfile`。
2. 添加 `.dockerignore`。
3. 添加 `docker-compose.yml` 可选。
4. README 添加：

```bash
docker build -t vrptw-hybrid .
docker run -p 8501:8501 vrptw-hybrid
```

5. 如果 OSMnx/geopandas 依赖导致镜像复杂，提供 slim demo 模式，只用预计算 demo JSON + Folium HTML。

验收标准：

1. Docker 能启动 Streamlit。
2. 不把 data/raw 大文件复制进镜像。
3. README 部署命令有效。

Codex 提示词：

```text
实现 P2-38：添加 Dockerfile 和部署说明。目标是能启动 Streamlit demo。注意不要把 data/raw 大文件复制进镜像；如果 OSMnx 依赖重，提供 slim demo 模式。
```

---

### P2-39：生成简历 bullet 与面试讲稿

目标：把项目成果转化为求职语言。

Codex 任务：

1. 创建 `docs/interview_notes.md`。
2. 包含：
   - 30 秒项目介绍。
   - 2 分钟技术介绍。
   - 数学模型讲法。
   - 为什么不全用精确法。
   - 自适应算子选择讲法。
   - gap/收敛曲线/消融/统计检验讲法。
   - 面试官可能追问与回答。
3. 创建 `docs/resume_bullets.md`。
4. 所有数字用占位符，除非能从 results CSV 自动读取。

简历 bullet 模板：

```text
实现城配 VRPTW 混合求解器：基于 Solomon benchmark 与 OSM 城市路网构建配送实例，小规模采用 OR-Tools CP-SAT/COPT MILP 校验，中等规模实现自适应 ALNS；所有百分比结论必须来自已落盘实验结果，并提供 Streamlit+Folium 地图演示。
```

短版：

```text
将博士阶段自适应策略选择思想迁移到 ALNS 算子选择，实现 VRPTW 混合求解器；支持 CP-SAT 精确校验、OR-Tools 基线、消融实验与地图可视化 demo。
```

验收标准：

1. 没有伪造数字。
2. 面试稿能按“约束数学化→算法取舍→自适应机制→验证方法”展开。
3. README 链接到这两个文档。

Codex 提示词：

```text
实现 P2-39：创建 docs/interview_notes.md 和 docs/resume_bullets.md。把项目转化为面试讲法和简历 bullet。所有未由 results CSV 支撑的数字必须保留占位符，不得编造。
```

---

# 7. 推荐执行顺序

严格顺序：

```text
P2-00 → P2-01 → P2-02 → P2-03
→ P2-04 → P2-05 → P2-06 → P2-07 → P2-08
→ P2-09 → P2-10 → P2-12
→ P2-13 → P2-14 → P2-15 → P2-16 → P2-17 → P2-18
→ P2-19 → P2-20 → P2-21 → P2-22 → P2-23
→ P2-24 → P2-25 → P2-26 → P2-27 → P2-28
→ P2-29 → P2-30 → P2-31 → P2-32 → P2-33 → P2-34
→ P2-35 → P2-36 → P2-37 → P2-38 → P2-39
```

P2-11 是可选项，建议在 P2-10 后做，但不要阻塞主线。

最低可展示路线：

```text
P2-00 ~ P2-10, P2-12, P2-18, P2-21, P2-24, P2-27, P2-33, P2-34, P2-35, P2-39
```

这条路线可以先跳过 COPT、复杂统计、更大规模 scaling 和完整 OSM 路网，先形成可演示闭环。

---

# 8. 每周计划

## 第 1 周：可运行骨架 + Solomon 小实例

完成：P2-00 ~ P2-08。  
周末产物：

```bash
vrptw info
vrptw validate-instance --instance tests/fixtures/mini_solomon.txt
pytest -q
```

你应能讲清：数据格式、目标函数、可行性检查。

## 第 2 周：精确解/基线/初始解

完成：P2-09、P2-10、P2-12，P2-11 可选。  
周末产物：

```bash
vrptw solve --instance tests/fixtures/mini_solomon.txt --solver cp_sat --time-limit 30
vrptw solve --instance tests/fixtures/mini_solomon.txt --solver ortools_routing --time-limit 30
vrptw solve --instance tests/fixtures/mini_solomon.txt --solver greedy
```

你应能讲清：为什么精确法只做小规模，为什么基线和精确模型不同。

## 第 3 周：基础 ALNS

完成：P2-13 ~ P2-18。  
周末产物：

```bash
vrptw solve --instance tests/fixtures/mini_solomon.txt --solver alns --selector uniform --max-iterations 1000
```

你应能讲清：destroy/repair/acceptance 的作用。

## 第 4 周：自适应机制

完成：P2-19 ~ P2-23。  
周末产物：

```bash
vrptw solve --instance data/raw/solomon/C101.txt --solver alns --selector mosade --max-iterations 5000 --seed 42
```

你应能讲清：MOSADE 思想如何迁移到算子选择、reward 如何定义、为什么要做消融。

## 第 5 周：实验与统计

完成：P2-24 ~ P2-28。  
周末产物：

```bash
vrptw batch --config configs/solomon_small.yaml
python scripts/make_report_figures.py --runs data/results/runs_xxx.csv
python scripts/run_ablation.py --config configs/ablation.yaml
```

你应能讲清：gap、收敛曲线、统计检验、稳定性。

## 第 6 周：城市路网、地图、包装

完成：P2-29 ~ P2-39。  
周末产物：

```bash
streamlit run apps/streamlit_app.py
```

你应能讲清：业务 demo、地图数据、项目局限性、简历 bullet。

---

# 9. 实验协议建议

## 9.1 Solomon 协议

实例组：

- 小规模：C101/R101/RC101 截取 10、25 客户。
- 标准规模：C101/R101/RC101 100 客户。
- 扩展规模：synthetic 200、500、1000 客户。

求解器：

- greedy。
- cp_sat，小规模。
- ortools_routing。
- alns_uniform。
- alns_roulette。
- alns_mosade。

随机种子：至少 5 个，建议 `[1, 2, 3, 4, 5]`；最终报告建议 10 个。

时间预算：

- 小规模：10s、30s。
- 100 客户：60s。
- 500/1000 客户：120s 或 300s。

指标：

- feasible rate。
- vehicles used。
- total distance。
- composite cost。
- runtime_sec。
- best iteration。
- gap to BKS 或 gap to best observed。
- mean/std over seeds。
- statistical test vs baseline。

## 9.2 城市路网协议

城市 demo 不要宣称代表真实生产订单。正确表述：

> 使用 OpenStreetMap 路网生成合成配送订单，用于展示算法在真实道路距离/时间矩阵上的可视化能力。

指标同 Solomon，但主要用于 demo，不作为严肃 benchmark 结论。

---

# 10. 关键工程风险与处理

## 风险 1：CP-SAT 模型跑不动

处理：限制为 10/25 客户；设置 time limit；返回 feasible + bound；README 中明确其用途是小规模校验，不是中等及以上规模求解。

## 风险 2：ALNS 很难稳定优于 OR-Tools

处理：不要只比 OR-Tools；同时比 greedy、uniform ALNS、roulette ALNS。重点展示自适应机制在若干实例和消融中的收益。如果 OR-Tools 更强，诚实写：OR-Tools 是强工业基线，自研 ALNS 的价值在可扩展定制和可解释消融。

## 风险 3：地图/OSM 依赖复杂

处理：Solomon 闭环优先；OSM 只做 demo 增强。提供 cached mini city JSON，保证 Streamlit 不依赖现场下载。

## 风险 4：实验数字不可复现

处理：所有随机过程必须 seed；结果落 CSV/JSON；README 数字必须从结果文件来。

## 风险 5：Codex 生成大而乱的代码

处理：一次一工单；每工单先测试；禁止把 solver 逻辑写进 Streamlit 或 notebook。

---

# 11. README 中可以使用的项目标题

中文标题：

```text
城配 VRPTW 混合求解器：CP-SAT 精确校验 + MOSADE-inspired 自适应 ALNS + 地图可视化
```

英文标题：

```text
Hybrid VRPTW Solver for Urban Delivery: CP-SAT Validation, MOSADE-inspired Adaptive ALNS, and Map Visualization
```

一句话简介：

```text
A portfolio-grade operations research project that solves Vehicle Routing Problems with Time Windows using exact validation for small instances, adaptive ALNS for large instances, and Streamlit/Folium visualization for urban delivery scenarios.
```

---

# 12. 面试讲法骨架

## 12.1 约束怎么数学化

我把每个客户看成节点，仓库是 depot。决策变量包括车辆是否走 arc、客户由哪辆车服务、到达时间和载重。核心约束是每个客户恰好访问一次、车辆容量、时间窗、服务时间和路径流守恒。小规模时我用 CP-SAT 的 arc-flow 模型验证可行性和最优/近优解。

## 12.2 为什么不全用精确法

VRPTW 是组合优化问题，变量规模大约随客户数和车辆数的乘积二次增长。精确法在 10/25 客户上适合做校验，但到 100/1000 点时求解时间和内存迅速不可接受。因此我采用混合策略：小规模精确法做 correctness anchor，大规模启发式做工程可用解。

## 12.3 算子自适应怎么设计

ALNS 每轮要选择一个 destroy 算子和一个 repair 算子。传统做法可以 uniform random 或 roulette wheel。我借鉴 MOSADE 中自适应策略选择的思想，把 destroy-repair pair 看成一个搜索策略，根据最近窗口中的新 best、改进幅度、可行性和接受情况给 reward，再通过 decay + softmax 更新选择概率，同时保留 exploration floor，避免早熟。

## 12.4 怎么验证解质量

我从四层验证：第一，checker 保证解满足容量和时间窗；第二，小实例与 CP-SAT 解比较 gap；第三，Solomon benchmark 与 BKS 或 best observed 比较；第四，消融实验比较 uniform、roulette、MOSADE-inspired selector，并用收敛曲线、均值方差、Holm 校正后的统计检验评估收益稳定性。

---

# 13. 参考资料

这些资料用于确认技术方向和接口，不要求在 README 中全部引用。

1. OR-Tools VRPTW 文档：`https://developers.google.com/optimization/routing/vrptw`
2. OR-Tools CP-SAT 文档：`https://developers.google.com/optimization/cp/cp_solver`
3. OR-Tools Python reference：`https://or-tools.github.io/docs/python/index.html`
4. Solomon benchmark / SINTEF：`https://www.sintef.no/projectweb/top/vrptw/solomon-benchmark/`
5. SINTEF 100-customer BKS 说明：`https://www.sintef.no/projectweb/top/vrptw/100-customers/`
6. ALNS Python package docs，可作机制参考但不要替代自研实现：`https://alns.readthedocs.io/`
7. OSMnx user reference：`https://osmnx.readthedocs.io/en/stable/user-reference.html`
8. NetworkX shortest paths：`https://networkx.org/documentation/stable/reference/algorithms/shortest_paths.html`
9. Streamlit docs：`https://docs.streamlit.io/`
10. Folium docs：`https://python-visualization.github.io/folium/`
11. streamlit-folium：`https://folium.streamlit.app/`
12. COPT Python interface：`https://guide.coap.online/copt/en-doc/pythoninterface.html`
13. coptpy PyPI：`https://pypi.org/project/coptpy/`

---

# 14. 完成判定

项目不能以“代码写完”为完成。必须满足以下判定：

1. 新环境能安装。
2. Mini instance 能从 CLI 求解。
3. 至少 3 个 solver 输出统一 Solution。
4. ALNS 有 uniform、roulette、MOSADE-inspired 三种 selector。
5. 至少一个 Solomon 小实例有 CP-SAT 对比。
6. 至少一个 Solomon 100 客户实例有 batch 结果。
7. 至少一个城市 demo 能在 Streamlit 地图显示。
8. README 有真实命令、真实截图、真实结果表。
9. `docs/interview_notes.md` 能支持 10 分钟技术面试讲解。
10. 简历 bullet 中的每个数字都能在 `data/results/` 中找到来源。
