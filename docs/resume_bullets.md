# Resume Bullets

Use only evidence-backed wording. Do not add percentage improvements, large-scale
scaling claims, or MOSADE superiority claims unless a later report supports
them.

## A. Conservative Version

Implemented a VRPTW hybrid solver and visualization demo integrating OR-Tools
Routing, CP-SAT small-instance validation, greedy construction, and ALNS
variants; ran a 90-row Solomon 100 / Gehring-Homberger 200 experiment and built
a Streamlit demo for benchmark route inspection and Berlin Mitte OSM road-map
visualization.

## B. Technical Detail Version

Built a reproducible VRPTW experiment pipeline with solution feasibility
checking, CSV/JSON result persistence, convergence logging, selector ablation,
statistical comparison tables, and report figures; instrumented ALNS operator
selection with uniform, roulette, and MOSADE-inspired pair-level selector logs.

## C. Interview Finding Version

Compared OR-Tools Routing and ALNS variants under fixed time budgets: OR-Tools
Routing produced strong solutions when feasible but reached only 0.5 feasible
rate in the EXP-02 medium suite, while ALNS variants reached 1.0 feasible rate;
the MOSADE-inspired selector was implemented and audited but did not outperform
uniform or roulette in the current ablation.

## D. Short Project Line

VRPTW hybrid solver with exact validation, ALNS variants, OR-Tools baselines,
medium benchmark reports, and Streamlit/Folium route demos.

## Do Not Write

- Reduced cost by X%.
- Proved MOSADE is better.
- Solved production-scale routing.
- Used live traffic or measured travel-time data.
- Used CP-SAT as the medium benchmark baseline.
