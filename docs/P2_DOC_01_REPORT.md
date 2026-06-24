# P2_DOC_01_REPORT.md

Date: 2026-06-23

## A. README Update Summary

`README.md` was rewritten as a portfolio landing page. It now covers:

- project purpose and architecture;
- solver stack and scope;
- evidence-backed RUN-01/RUN-02/ABL-01/EXP-02/VIS-01A/VIS-01B results;
- Streamlit and CLI demo usage;
- reproducibility and data/cache policy;
- limitations and interview positioning.

The README no longer contains local absolute paths, TODO improvement claims, or
the placeholder GitHub CI badge.

## B. New Or Updated Documents

| File | Purpose |
| --- | --- |
| `README.md` | Portfolio landing page |
| `docs/claim_registry.md` | Public claim to evidence mapping |
| `docs/demo_guide.md` | Streamlit, benchmark viewer, city demo, CLI guide |
| `docs/resume_bullets.md` | Evidence-backed resume wording |
| `docs/interview_notes.md` | 30-second and 2-minute interview narrative |
| `docs/P2_DOC_01_REPORT.md` | DOC-01 summary |

Previously generated reports remain the detailed evidence base:

- `docs/P2_RUN_01_REPORT.md`
- `docs/P2_RUN_02_AUDIT.md`
- `docs/P2_ABL_01_REPORT.md`
- `docs/P2_EXP_02_REPORT.md`
- `docs/P2_VIS_00_AUDIT.md`
- `docs/P2_VIS_01A_REPORT.md`
- `docs/P2_VIS_01B_00_AUDIT.md`
- `docs/P2_VIS_01B_REPORT.md`

## C. Public Claims And Evidence

| Claim | Evidence file | Metric / fact | Safe for README |
| --- | --- | --- | --- |
| RUN-01 produced real small-scale artifacts | `docs/P2_RUN_01_REPORT.md`, `reports/results/summary_small.csv` | Small runs, summaries, stats, figures | Yes, with exploratory caveat |
| RUN-02 audited UNKNOWN and provenance | `docs/P2_RUN_02_AUDIT.md` | UNKNOWN not counted as feasible/optimal | Yes |
| MOSADE-inspired selector did not beat uniform/roulette | `docs/P2_ABL_01_REPORT.md` | Holm p-values 1.000; mean objective worse | Yes |
| EXP-02 completed 90 rows | `docs/P2_EXP_02_REPORT.md`, `reports/results/runs_medium.csv` | 6 instances x 5 solvers x 3 seeds | Yes |
| EXP-02 OR-Tools feasible rate was 0.5 | `reports/results/summary_medium.csv` | fixed 60s budget | Yes |
| EXP-02 ALNS variants feasible rate was 1.0 | `reports/results/summary_medium.csv` | selected medium suite | Yes |
| VIS-01A is benchmark x-y visualization | `docs/P2_VIS_01A_REPORT.md` | not a real map | Yes |
| VIS-01B uses Berlin Mitte OSM road geometry | `docs/P2_VIS_01B_REPORT.md`, `reports/demo/city/city_summary.csv` | 30-order city demo | Yes |
| VIS-01B travel time is a shortest-path proxy | `docs/P2_VIS_01B_REPORT.md` | not measured travel-time data | Yes |

Detailed claim mapping is in `docs/claim_registry.md`.

## D. Resume-Safe Conclusions

Safe to write:

- Implemented a VRPTW hybrid solver with OR-Tools Routing, CP-SAT small-instance
  validation, greedy construction, and ALNS variants.
- Ran a 90-row medium benchmark across selected Solomon 100 and
  Gehring-Homberger 200 instances.
- Built Streamlit demos for benchmark x-y route viewing and Berlin Mitte OSM
  route visualization.
- Instrumented ALNS selector behavior with convergence and operator probability
  logs.
- Found that OR-Tools Routing is strong when feasible but had fixed-budget
  feasibility gaps in EXP-02.
- Found that MOSADE-inspired selection is implemented but current evidence does
  not support a better-than-baseline claim.

## E. Conclusions Not To Write

Do not write:

- cost reduction percentages;
- large-scale scaling results;
- MOSADE dominance over baselines;
- CP-SAT as a medium benchmark baseline;
- city demo as measured travel-time routing;
- benchmark x-y viewer as a real map;
- production dispatch claims.

## F. Demo Startup

From the repository root:

```powershell
python -m pip install -e ".[dev,vis]"
streamlit run apps/streamlit_app.py
```

Demo modes:

- `Benchmark curated demo`
- `Benchmark full local experiment`
- `City road demo`

More detail: `docs/demo_guide.md`.

## G. REL-01 Items Still Open

REL-01 should handle release hygiene:

- configure GitHub remote;
- replace or add CI badge after the remote is known;
- verify Docker build/run if Docker is part of release scope;
- capture screenshots or a short demo GIF if desired;
- decide final commit split and stage only curated artifacts;
- confirm README links after repository publication.

## H. Suggested Commit Scope

Suggested source/config/docs/results to include:

- `README.md`
- `configs/experiment_small.yaml`
- `configs/experiment_medium.yaml`
- `configs/ablation_selectors.yaml`
- `configs/city_demo_berlin_mitte.yaml`
- `src/vrptw_hybrid/**`
- `tests/**`
- `scripts/generate_demo_artifacts.py`
- `scripts/generate_medium_assets.py`
- `scripts/generate_city_demo.py`
- `docs/*.md`
- `reports/results/*`
- `reports/figures/*`
- `reports/demo/**`

## I. Must Stay Ignored

- `.venv311/`
- `.ai-bridge/`
- `cache/`
- `data/raw/`
- `data/results/`
- Python and test caches

Current `.gitignore` already covers these categories.

## J. DOC-01 Status

DOC-01 is complete. Final quality gates and the markdown link/artifact check
passed.
