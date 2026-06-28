# Changelog

## v0.1.0 - 2026-06-28

Initial portfolio release.

Highlights:

- Hybrid VRPTW solver with Greedy, OR-Tools Routing, CP-SAT small validation,
  and ALNS variants.
- Solomon/GH benchmark experiment pipeline with curated results.
- Selector ablation with honest MOSADE-inspired selector boundary.
- Streamlit benchmark route viewer.
- Berlin Mitte OSM/Folium city road demo.
- Reproducible documentation and evidence registry.

Limitations:

- No very-large-scale claim.
- MOSADE-inspired selector is instrumented, but this release does not claim it
  outperforms the other selector baselines.
- City demo uses shortest-path proxy, not measured traffic time.
- CP-SAT is scoped to small validation.
