from pathlib import Path

from vrptw_hybrid.core.checker import check_solution
from vrptw_hybrid.core.models import Solution
from vrptw_hybrid.data.solomon import parse_solomon
from vrptw_hybrid.solvers.alns.solver import ALNSSolver, solve_alns
from vrptw_hybrid.solvers.greedy import solve_greedy

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "mini_solomon.txt"


def route_signature(solution: Solution) -> tuple[tuple[int, ...], ...]:
    return tuple(tuple(stop.customer_id for stop in route.stops) for route in solution.routes)


def test_alns_solves_mini_instance_and_keeps_history() -> None:
    instance = parse_solomon(FIXTURE, limit_customers=8)
    greedy = solve_greedy(instance, seed=42)

    solution = solve_alns(instance, max_iterations=20, seed=42)
    report = check_solution(solution, instance)

    assert solution.feasible
    assert report.feasible
    assert solution.objective <= greedy.objective
    assert solution.metadata["iterations"] == len(solution.metadata["history"])
    assert solution.metadata["iterations"] <= 20
    assert solution.metadata["selector"]["name"] == "uniform"
    assert solution.metadata["selector"]["events_seen"] == solution.metadata["iterations"]
    assert "selector_snapshot" in solution.metadata["history"][0]
    assert "delta_cost" in solution.metadata["history"][0]


def test_alns_seed_reproducibility_for_solution_routes() -> None:
    instance = parse_solomon(FIXTURE, limit_customers=8)

    first = ALNSSolver(max_iterations=10, seed=7).solve(instance)
    second = ALNSSolver(max_iterations=10, seed=7).solve(instance)

    assert route_signature(first) == route_signature(second)
    assert first.objective == second.objective


def test_alns_can_use_roulette_selector() -> None:
    instance = parse_solomon(FIXTURE, limit_customers=8)

    solution = ALNSSolver(
        max_iterations=5,
        seed=11,
        selector_name="roulette",
        segment_length=1,
        reaction_factor=1.0,
    ).solve(instance)

    assert solution.feasible
    assert solution.metadata["selector"]["name"] == "roulette"
    assert solution.metadata["history"][0]["selector_snapshot"]["name"] == "roulette"


def test_alns_can_use_mosade_inspired_selector() -> None:
    instance = parse_solomon(FIXTURE, limit_customers=8)

    solution = ALNSSolver(
        max_iterations=5,
        seed=11,
        selector_name="mosade",
        memory_size=10,
        ablation_name="unit_mosade",
    ).solve(instance)

    assert solution.feasible
    assert solution.metadata["ablation"] == "unit_mosade"
    assert solution.metadata["selector"]["name"] == "mosade_inspired"
    assert "pair_heatmap" in solution.metadata["selector"]
    assert "pair_heatmap" in solution.metadata["history"][0]["selector_snapshot"]


def test_alns_records_candidate_context_profiler() -> None:
    instance = parse_solomon(FIXTURE, limit_customers=8)

    solution = ALNSSolver(
        max_iterations=5,
        seed=12,
        candidate_neighbor_size=2,
    ).solve(instance)

    assert solution.feasible
    assert solution.metadata["candidate_neighbor_size"] == 2
    assert solution.metadata["profiler"]["route_cache"]["entries"] > 0
    assert "repair_candidate_positions_evaluated" in solution.metadata["profiler"]["counters"]


def test_alns_rejects_invalid_parameters() -> None:
    try:
        ALNSSolver(max_iterations=-1)
    except ValueError as exc:
        assert "max_iterations must be non-negative" in str(exc)
    else:
        raise AssertionError("expected invalid max_iterations to fail")
