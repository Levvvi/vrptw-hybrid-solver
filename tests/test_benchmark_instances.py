from pathlib import Path

import pytest

from vrptw_hybrid.core.checker import check_solution
from vrptw_hybrid.data.solomon import parse_solomon
from vrptw_hybrid.data.solomon_bks import get_solomon_bks
from vrptw_hybrid.solvers.greedy import solve_greedy

ROOT = Path(__file__).resolve().parents[1]

SOLOMON_100 = ROOT / "data" / "raw" / "benchmark" / "solomon_100" / "In"
HOMBERGER_200 = ROOT / "data" / "raw" / "benchmark" / "homberger_200"

BENCHMARK_CASES = (
    pytest.param(SOLOMON_100 / "c101.txt", "C101", 100, id="solomon-c101-100"),
    pytest.param(SOLOMON_100 / "r101.txt", "R101", 100, id="solomon-r101-100"),
    pytest.param(SOLOMON_100 / "rc101.txt", "RC101", 100, id="solomon-rc101-100"),
    pytest.param(HOMBERGER_200 / "C1_2_1.TXT", "c1_2_1", 200, id="gh-c1-200"),
    pytest.param(HOMBERGER_200 / "R1_2_1.TXT", "r1_2_1", 200, id="gh-r1-200"),
    pytest.param(HOMBERGER_200 / "RC1_2_1.TXT", "rc1_2_1", 200, id="gh-rc1-200"),
)


def _require_benchmark_file(path: Path) -> None:
    if not path.exists():
        pytest.skip(f"benchmark data file not present: {path}")


@pytest.mark.parametrize(("path", "expected_name", "expected_customers"), BENCHMARK_CASES)
def test_downloaded_benchmark_instances_parse(
    path: Path,
    expected_name: str,
    expected_customers: int,
) -> None:
    _require_benchmark_file(path)

    instance = parse_solomon(path)

    assert instance.name == expected_name
    assert len(instance.customers) == expected_customers
    assert instance.distance_matrix.shape == (expected_customers + 1, expected_customers + 1)
    assert instance.time_matrix.shape == instance.distance_matrix.shape
    assert instance.vehicle.capacity > 0
    assert instance.vehicle.count > 0


@pytest.mark.parametrize("path", [case.values[0] for case in BENCHMARK_CASES])
def test_checker_accepts_greedy_solution_on_benchmark_slice(path: Path) -> None:
    _require_benchmark_file(path)
    instance = parse_solomon(path, limit_customers=20)

    solution = solve_greedy(instance, seed=0)
    report = check_solution(solution, instance)

    assert solution.feasible
    assert report.feasible


def test_solomon_bks_table_contains_selected_100_customer_references() -> None:
    assert get_solomon_bks("C101") is not None
    assert get_solomon_bks("R101") is not None
    assert get_solomon_bks("RC101") is not None
    assert get_solomon_bks("C1_2_1") is None
