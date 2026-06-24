# P2_INSTALL_AUDIT.md

审计时间：2026-06-22  
审计目录：`<repo-root>`  
审计类型：安装环境与依赖缺口审计，只读检查。  
写入范围：仅新增本报告文件；未修改源码、配置、README、pyproject、CI、Dockerfile。

## A. 总体结论

当前环境状态：**Blocked**。

核心 Python 依赖已基本补齐，`python -m pip check` 已通过，Streamlit/Folium/OSMnx 也可 import；但 **OR-Tools CP-SAT 在当前 Python 环境中 solve 时发生 native 崩溃**，项目 `cp_sat` solver 仍不可运行。因此最高优先级安装/运行时缺口是：

1. **P0：OR-Tools CP-SAT runtime 崩溃**，阻塞“小规模精确法校验”链路。
2. **P1：Docker 命令不在 PATH**，但 Docker Desktop/daemon 可通过绝对路径访问，不阻塞 Python 主线。
3. **P2：COPT/coptpy 未安装**，当前为可选增强，不是主线阻塞。

## B. P0/P1/P2 安装缺口表

| 优先级 | 项目 | 当前状态 | 证据命令 | 错误摘要 | 建议修复命令 | 是否必须 |
| --- | --- | --- | --- | --- | --- | --- |
| P0 | OR-Tools CP-SAT runtime | `ortools` 可 import，但 CP-SAT solve 崩溃 | `python` CP-SAT minimal model；subprocess smoke | 子进程 `returncode=3221225477`，stdout/stderr 为空；项目 CLI 报 CP-SAT smoke failed | `python -m pip install --upgrade --force-reinstall ortools`；如仍失败，修复 VC++ runtime 或更换 Python/OR-Tools 兼容组合 | 是，若要完成 CP-SAT 精确校验 |
| P1 | Docker CLI PATH | Docker Desktop 存在且 daemon 可用，但 `docker` 不在 PATH | `where.exe docker`; `& '<Docker Desktop>\resources\bin\docker.exe' version` | PATH 中找不到 docker；绝对路径可显示 Client/Server | 将 `<Docker Desktop>\resources\bin` 加入 PATH，或重启终端/Docker Desktop | 展示/交付验证需要 |
| P2 | COPT/coptpy | 未安装 | `python -c "import coptpy"`; `where.exe copt_cmd` | `ModuleNotFoundError: No module named 'coptpy'`; `copt_cmd` not found | 暂缓；需要商业求解器时再安装 `coptpy` 和 license | 否，当前主线可选 |
| P2 | GitHub remote / badge | Git remote 缺失，README badge 仍为占位 | `git remote -v`; placeholder scan | remote 输出为空；README 含历史 owner/repo 占位 | `git remote add origin <repo-url>` 后替换 badge | 否，不是安装问题 |

## C. Python 依赖完整性

### pip check

命令：

```powershell
python -m pip check
```

结果：

```text
No broken requirements found.
```

结论：上次审计中缺失的 `matplotlib`, `networkx`, `plotly`, `scipy` 已安装，当前 `pip check` 通过。

### Python 解释器与 pip 对应关系

| 项目 | 结果 |
| --- | --- |
| 当前 Python | `<python-install>\python.exe` |
| Python 版本 | `Python 3.13.7` |
| pip | `D:\Python\Lib\site-packages\pip (python 3.13)` |
| `where.exe python` | `<python-install>\python.exe`; `<WindowsApps>\python.exe` |
| `where.exe pip` | `D:\Python\Scripts\pip.exe` |
| `py -0p` | 仅列出 `-V:3.13 * <python-install>\python.exe` |

判断：`python -m pip` 与当前 `python` 对应，均指向 `D:\Python`。存在 WindowsApps python alias，但 `py -0p` 只发现一个实际 Python 解释器，当前环境混用风险较低。

### pyproject 声明摘要

| 项目 | 结果 |
| --- | --- |
| Python 版本约束 | `>=3.11` |
| console script | `vrptw = "vrptw_hybrid.cli:app"` |
| project.dependencies | `matplotlib`, `networkx`, `numpy`, `ortools`, `pandas`, `plotly`, `pyyaml`, `rich`, `scipy`, `typer` |
| dev extra | `ipykernel`, `mypy`, `pre-commit`, `pytest`, `pytest-cov`, `ruff` |
| vis extra | `folium`, `geopandas`, `osmnx`, `streamlit`, `streamlit-folium` |
| copt extra | `coptpy` |

### 指定依赖检查表

| 依赖包 | 所属分组 | pyproject 是否声明 | 当前是否安装 | 当前版本 | 是否可 import | 问题 |
| --- | --- | --- | --- | --- | --- | --- |
| numpy | core | 是 | 是 | 2.5.0 | 是 | 无 |
| pandas | core / app | 是 | 是 | 3.0.3 | 是 | 无 |
| pydantic | 未使用 | 否 | 否 | N/A | 否 | 项目未声明/未直接使用 |
| pydantic-settings | 未使用 | 否 | 否 | N/A | 否 | 项目未声明/未直接使用 |
| typer | core CLI | 是 | 是 | 0.26.7 | 是 | 无 |
| click | typer transitive | 否 | 是 | 8.4.1 | 是 | transitive 依赖，不需直接声明 |
| rich | core CLI/logging | 是 | 是 | 15.0.0 | 是 | 无 |
| PyYAML / yaml | config | 是 | 是 | 6.0.3 | 是 | 无 |
| ortools | solver | 是 | 是 | 9.15.6755 | 是 | CP-SAT solve 崩溃 |
| scipy | experiment | 是 | 是 | 1.18.0 | 是 | 无 |
| matplotlib | experiment/plots | 是 | 是 | 3.11.0 | 是 | 无 |
| plotly | experiment/demo | 是 | 是 | 6.8.0 | 是 | 无 |
| networkx | OSM graph | 是 | 是 | 3.6.1 | 是 | 无 |
| osmnx | vis | 是，vis extra | 是 | 2.1.0 | 是 | 无 |
| geopandas | vis | 是，vis extra | 是 | 1.1.3 | 是 | 无 |
| shapely | transitive geospatial | 否 | 是 | 2.1.2 | 是 | transitive 依赖 |
| pyproj | transitive geospatial | 否 | 是 | 3.7.2 | 是 | transitive 依赖 |
| streamlit | vis/app | 是，vis extra | 是 | 1.58.0 | 是 | 无 |
| folium | vis/app | 是，vis extra | 是 | 0.20.0 | 是 | 无 |
| streamlit-folium | vis/app | 是，vis extra | 是 | 0.27.2 | 是 | 无 |
| pytest | dev/test | 是，dev extra | 是 | 9.1.1 | 是 | 无 |
| pytest-cov | dev/test | 是，dev extra | 是 | 7.1.0 | 是 | 无 |
| ruff | dev/lint | 是，dev extra | 是 | 0.15.18 | 是 | 无 |
| mypy | dev/type | 是，dev extra | 是 | 2.1.0 | 是 | 无 |
| coptpy | copt optional | 是，copt extra | 否 | N/A | 否 | P2 optional，不阻塞主线 |

### 源码 import 静态扫描

扫描范围：`src/**/*.py`, `tests/**/*.py`, `apps/**/*.py`, `scripts/**/*.py`。  
排除：标准库、本项目内部包。

| import 名称 | 可能对应 pip 包 | 出现文件示例 | 是否安装 | 是否可 import | 优先级 |
| --- | --- | --- | --- | --- | --- |
| numpy | numpy | `core/models.py`, `data/distance_matrix.py`, tests | 是 | 是 | P0 |
| pandas | pandas | `apps/streamlit_app.py` | 是 | 是 | P1 |
| typer | typer | `cli.py`, `tests/test_cli.py` | 是 | 是 | P0 |
| yaml | PyYAML | `utils/config.py` | 是 | 是 | P0 |
| ortools | ortools | `exact_cp_sat.py`, `ortools_routing.py` | 是 | 是 | P0，CP-SAT solve 仍失败 |
| networkx | networkx | `data/osm_network.py` | 是 | 是 | P1 |
| osmnx | osmnx | `data/osm_network.py` | 是 | 是 | P1 |
| folium | folium | `visualization/folium_map.py` | 是 | 是 | P1 |
| streamlit | streamlit | `apps/streamlit_app.py` | 是 | 是 | P1 |
| streamlit_folium | streamlit-folium | `apps/streamlit_app.py` | 是 | 是 | P1 |
| pytest | pytest | tests | 是 | 是 | P0 for dev/test |

源码 direct import 未发现必须声明但未安装的 P0 包。`shapely/pyproj/click` 当前为 transitive/import smoke 可用，不是 direct project import。

## D. OR-Tools CP-SAT 诊断

| 检查项 | 结果 |
| --- | --- |
| `ortools` 版本 | 9.15.6755 |
| `from ortools.sat.python import cp_model` | 成功 |
| in-process CP-SAT solve | 失败，Python 进程非零退出，无 stdout/stderr |
| subprocess CP-SAT solve | 失败，`returncode=3221225477`, stdout/stderr 为空 |
| 项目 `cp_sat` solver CLI | 失败 |

项目命令：

```powershell
vrptw solve --instance tests\fixtures\mini_solomon.txt --solver cp_sat --config configs\solomon_small.yaml --seed 42 --time-limit 3 --max-iterations 10
```

错误摘要：

```text
Invalid value for --solver: OR-Tools CP-SAT is installed but failed a subprocess smoke test.
Use a supported Python/OR-Tools combination before running exact_cp_sat.
```

判断：更可能是 **环境 / native runtime / wheel 兼容性问题**，不是项目参数问题。证据是最小 CP-SAT 模型在项目外也崩溃，且返回码 `3221225477` 通常对应 Windows access violation。

建议修复动作，不执行：

```powershell
python -m pip install --upgrade --force-reinstall ortools
```

如仍失败：

```powershell
winget install -e --id Microsoft.VCRedist.2015+.x64
```

并检查 Python 3.13 与当前 OR-Tools wheel 的兼容性。若 OR-Tools 对 Python 3.13 支持不稳定，建议建立 Python 3.11/3.12 虚拟环境重新安装项目。

## E. Docker / WSL 诊断

| 检查项 | 结果 |
| --- | --- |
| `where.exe docker` | 失败，PATH 中找不到 |
| `docker --version` | 失败，PowerShell 找不到命令 |
| Docker Desktop 文件 | 存在：`<Docker Desktop>\Docker Desktop.exe` |
| Docker CLI 文件 | 存在：`<Docker Desktop>\resources\bin\docker.exe` |
| 绝对路径 Docker CLI | 成功：Docker 29.5.3 |
| Docker daemon | 成功：`docker.exe version` 显示 Server Docker Desktop 4.78.0 |
| Docker Compose | 成功：绝对路径 `docker.exe compose version` 返回 v5.1.4 |
| WSL | 可用 |
| WSL 发行版 | `Ubuntu` version 2 stopped；`docker-desktop` version 2 running |
| 默认 WSL 版本 | `wsl --status` 显示默认版本为 2（输出有编码噪声，但可读字段显示 Version 2） |

判断：Docker Desktop/daemon/Compose 实际存在并运行，但 Docker CLI 未加入当前 PowerShell PATH。无需安装 Docker Desktop；优先修 PATH 或重启终端。

建议动作，不执行：

```powershell
$env:Path += ';<Docker Desktop>\resources\bin'
docker --version
docker compose version
docker run hello-world
```

若新终端仍找不到 docker，则在系统环境变量 PATH 中添加：

```text
<Docker Desktop>\resources\bin
```

## F. Windows runtime 诊断

检测命令：

```powershell
Get-ItemProperty "HKLM:\SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64" -ErrorAction SilentlyContinue | Select-Object Version, Installed
Get-ItemProperty "HKLM:\SOFTWARE\WOW6432Node\Microsoft\VisualStudio\14.0\VC\Runtimes\x64" -ErrorAction SilentlyContinue | Select-Object Version, Installed
```

结果：

| Registry path | Version | Installed |
| --- | --- | --- |
| `HKLM:\SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64` | `v14.22.27821.00` | 1 |
| `HKLM:\SOFTWARE\WOW6432Node\Microsoft\VisualStudio\14.0\VC\Runtimes\x64` | `v14.22.27821.00` | 1 |

判断：检测到 x64 VC++ Redistributable，但版本较旧。由于 CP-SAT 仍发生 native 崩溃，建议在重装 OR-Tools 后仍失败时修复/升级 VC++ runtime。

建议命令，不执行：

```powershell
winget install -e --id Microsoft.VCRedist.2015+.x64
```

## G. GitHub 发布相关但非安装问题

| 项目 | 结果 |
| --- | --- |
| Git | 已安装：`git version 2.54.0.windows.1` |
| 当前分支 | `codexpro-test` |
| Git remote | 缺失，`git remote -v` 无输出 |
| README badge | 审计时仍含历史 owner/repo 占位 |
| README TODO | 仍含实验结果 TODO、TODO% 和 `<X>` 占位 |

判断：这不是安装问题，不列为 P0。但在公开仓库前需要处理。

建议命令，不执行：

```powershell
git remote add origin https://github.com/<YOUR_GITHUB_USERNAME>/VRPTW.git
git branch -M main
git push -u origin main
```

然后替换 README：

```text
historical owner/repo placeholder -> <YOUR_GITHUB_USERNAME>/<REPO>
```

## H. 最短修复顺序

1. 先确认 P0 Python 依赖完整性：

   ```powershell
   python -m pip check
   python -m pytest -q
   python -m ruff check .
   python -m mypy src
   ```

2. 修复 OR-Tools CP-SAT：

   ```powershell
   python -m pip install --upgrade --force-reinstall ortools
   python -c "from ortools.sat.python import cp_model; m=cp_model.CpModel(); x=m.NewBoolVar('x'); m.Maximize(x); s=cp_model.CpSolver(); status=s.Solve(m); print(status, s.Value(x))"
   ```

3. 如果 CP-SAT/DLL/native crash 仍失败，修复 Windows VC++ runtime：

   ```powershell
   winget install -e --id Microsoft.VCRedist.2015+.x64
   ```

4. 如果 Python 3.13 + OR-Tools 仍不稳定，创建 Python 3.11/3.12 虚拟环境：

   ```powershell
   py -3.11 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install -e ".[dev,vis]"
   ```

5. 修复 Docker PATH：

   ```powershell
   $env:Path += ';<Docker Desktop>\resources\bin'
   docker --version
   docker compose version
   docker run hello-world
   ```

6. 最后处理 GitHub remote、README badge、COPT 可选项：

   ```powershell
   git remote add origin https://github.com/<YOUR_GITHUB_USERNAME>/VRPTW.git
   ```

   COPT 只有需要商业求解器增强时再处理：

   ```powershell
   python -m pip install -e ".[copt]"
   ```

## I. 不确定项

| 项目 | 状态 | 原因 |
| --- | --- | --- |
| CP-SAT native crash 精确根因 | Unknown | 最小模型崩溃但 stderr 为空；需要重装 OR-Tools、升级 VC++ runtime 或换 Python 版本后复测 |
| Docker CLI 为何未进 PATH | Unknown | Docker Desktop 和 CLI 文件存在，daemon 可用；当前终端 PATH 不含 Docker bin |
| COPT license | Unknown | `COPT_HOME`、`COPT_LICENSE_DIR` 为空；`coptpy` 未安装；当前不影响主线 |

## 审计结束 8 问自检

1. **现在还缺哪些必须安装的 Python 包？**  
   当前没有 P0 Python 包缺失；`pip check` 通过。`coptpy` 缺失但为 P2 optional。

2. **`python -m pip check` 是否通过？**  
   是，通过：`No broken requirements found.`

3. **OR-Tools CP-SAT 是否能在当前 Python 环境中运行？**  
   否。`cp_model` 可 import，但最小 solve 发生 native crash；subprocess return code 为 `3221225477`。

4. **是否存在多个 Python 解释器导致的环境混用风险？**  
   风险较低。`where python` 有 `<python-install>\python.exe` 和 WindowsApps alias；`py -0p` 只列出 `<python-install>\python.exe`；`python -m pip` 对应该解释器。

5. **Docker Desktop / Docker CLI / Docker Compose 是否可用？**  
   Docker Desktop 和 daemon 可用；Docker CLI/Compose 通过绝对路径可用，但 `docker` 不在当前 PATH。

6. **WSL2 是否可用？**  
   是。`wsl` 存在；`Ubuntu` 和 `docker-desktop` 均为 version 2；`docker-desktop` 正在运行。

7. **VC++ Redistributable x64 是否检测到？**  
   是。检测到 `v14.22.27821.00`，Installed=1。由于 CP-SAT 崩溃，仍建议必要时修复/升级。

8. **COPT 是否只是可选项，而不是当前主线阻塞项？**  
   是。项目没有 `copt_milp.py`，主线精确校验目标使用 OR-Tools CP-SAT；`coptpy` 属于 `copt` extra，可选，不列为 P0。
