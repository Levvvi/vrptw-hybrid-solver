# Environment

Date: 2026-06-22

## Python

- Python version: 3.11.9
- Python executable: `<repo-root>\.venv311\Scripts\python.exe`
- `pip check`: `No broken requirements found.`

## Optimization Runtime

- OR-Tools version: 9.15.6755
- CP-SAT smoke: `status= CpSolverStatus.OPTIMAL x= 1`

## Windows Runtime

- VC++ Runtime x64 registry path: `HKLM:\SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64`
  - Version: `v14.51.36247.00`
  - Installed: `1`
- VC++ Runtime x64 registry path: `HKLM:\SOFTWARE\WOW6432Node\Microsoft\VisualStudio\14.0\VC\Runtimes\x64`
  - Version: `v14.51.36247.00`
  - Installed: `1`

## Quality Gates

- `python -m pytest -q`: `150 passed, 1 skipped, 3 warnings`
- `python -m ruff check .`: `All checks passed!`
- `python -m mypy src`: `Success: no issues found in 41 source files`
