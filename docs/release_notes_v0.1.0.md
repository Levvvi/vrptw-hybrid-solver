# v0.1.0 - Portfolio Release

This is the first portfolio release of `vrptw-hybrid-solver`, a VRPTW project
focused on the full engineering chain from modeling and validation to
heuristic search, benchmark evaluation, and route visualization.

## Highlights

- Hybrid solver stack: Greedy, OR-Tools Routing, CP-SAT small validation, and
  ALNS variants.
- Reproducible Solomon/GH benchmark experiment pipeline with curated results.
- Selector ablation documenting the current boundary of the MOSADE-inspired
  selector.
- Streamlit benchmark route viewer for Solomon/GH x-y coordinates.
- Berlin Mitte OSM/Folium city road demo using a road-network shortest-path
  proxy.
- Evidence registry, demo guide, interview notes, and release documentation.

## Validation

- GitHub Actions CI runs lint, type checks, tests, CLI smoke, and Streamlit
  import smoke on Python 3.11.
- Local release checks passed before tagging.
- Curated result artifacts are committed under `reports/`; raw benchmark data,
  generated experiment outputs, OSM cache files, and virtual environments remain
  ignored.

## Caveats

- No very-large-scale result is claimed.
- The MOSADE-inspired selector is instrumented and evaluated, but this release
  does not claim it outperforms uniform or roulette selection.
- The city demo uses a shortest-path proxy over OSM road geometry, not
  measured traffic time.
- CP-SAT is scoped to small validation and is not presented as a medium-scale
  or large-scale baseline.
