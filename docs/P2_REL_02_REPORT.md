# P2-REL-02 Final Release Cleanup

## A. CI Run Interpretation

- CI run #1 and #2 are historical failed runs and should remain in the GitHub
  Actions history.
- The first failure was caused by a brittle CLI help test that asserted directly
  on Rich/Typer terminal output.
- The second failure was caused by test typing where mypy inferred a mixed
  selector list as `object`.
- The latest checked run before this cleanup was green. Any new cleanup commit
  must pass CI before release actions proceed.

## B. Confirmed Fixes

- GitHub Actions uses `actions/checkout@v6` and `actions/setup-python@v6`.
- The workflow explicitly uses Python `3.11` and installs `.[dev,vis]`.
- CI runs `pip check`, `ruff`, `mypy src tests`, `pytest`, `vrptw info`, and
  `apps.streamlit_app` import smoke.
- `tests/test_cli.py` now invokes help with `color=False`, strips ANSI escape
  codes, and checks option tokens rather than matching full rendered lines.
- `tests/test_selectors.py` keeps the mixed selector serialization test typed
  through the shared `OperatorSelector` protocol, while MOSADE-specific
  `update`/`snapshot` behavior is covered on a concrete `MOSADEInspiredSelector`
  instance.

## C. Local Quality Gates

Run before push:

- `python -m pip check`
- `python -m ruff check .`
- `python -m mypy src tests`
- `python -m pytest -q`
- `vrptw info`
- `python -c "import apps.streamlit_app; print('streamlit import ok')"`

All must pass before pushing.

## D. Public Content Scan

The release scan checks for:

- local absolute paths, local file URLs, and sandbox-only paths;
- overclaims such as very-large-scale results, MOSADE superiority, top-tier
  performance language, measured traffic-time claims, or CP-SAT as a large-scale
  baseline.

README/docs/reports should have no matches before release.

## E. Release Metadata

Added or confirmed:

- `CHANGELOG.md`
- `CITATION.cff`
- `docs/release_notes_v0.1.0.md`
- README CI badge pointing at `.github/workflows/ci.yml` on `main`.

## F. Commit Scope

Expected release cleanup files:

- `.github/workflows/ci.yml`
- `README.md`
- `CHANGELOG.md`
- `CITATION.cff`
- `docs/P2_REL_02_REPORT.md`
- `docs/release_notes_v0.1.0.md`
- `tests/test_cli.py`
- `tests/test_selectors.py` if further selector typing edits are needed.

Ignored files must remain untracked:

- `.venv311/`
- `.ai-bridge/`
- `cache/`
- `data/raw/`
- `data/results/`
- Python and test caches.

## G. GitHub Actions Confirmation

After push, confirm the newest `main` run at:

`https://github.com/Levvvi/vrptw-hybrid-solver/actions/workflows/ci.yml`

Only the newest run matters for release readiness. Old failed runs are normal
history and should not be deleted.

## H. Tag and Release Strategy

- Create `v0.1.0` only after the latest `main` CI run is green.
- If `v0.1.0` already exists, do not overwrite or force-push it.
- If GitHub CLI is unavailable, create the GitHub Release manually from
  `docs/release_notes_v0.1.0.md`.
