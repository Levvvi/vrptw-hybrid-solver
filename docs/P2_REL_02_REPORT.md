# P2-REL-02 Final Release Cleanup

## Status

The project is ready for the `v0.1.0` release checkpoint after the final CI run
on `main` passes.

## CI Scope

The GitHub Actions workflow uses:

- `actions/checkout@v6`
- `actions/setup-python@v6`
- Python `3.11`
- `python -m pip install -e ".[dev,vis]"`
- `python -m pip check`
- `python -m ruff check .`
- `python -m mypy src tests`
- `python -m pytest -q`
- `vrptw info`
- `python -c "import apps.streamlit_app; print('streamlit import ok')"`

## Historical CI Failures

Old failed GitHub Actions runs are intentionally left in the run history.

- The selector test typing failure was fixed by typing the mixed selector list
  as `OperatorSelector`.
- The CLI help test failure was fixed by checking Typer option metadata instead
  of asserting on ANSI-rich terminal help text.

## Release Caveats

- The MOSADE-inspired selector is not claimed to outperform uniform or roulette
  selection.
- The release does not claim very-large-scale benchmark results.
- The city demo uses an OSM road-network shortest-path proxy, not measured
  traffic time.
- Raw benchmark data, generated experiment outputs, OSM cache files, virtual
  environments, and local caches remain ignored.

## Release Tag

Create `v0.1.0` only after the latest `main` CI run is green.
