import random
from pathlib import Path

from vrptw_hybrid.core.checker import check_solution
from vrptw_hybrid.data.solomon import parse_solomon
from vrptw_hybrid.solvers.alns.context import ALNSContext, RouteEvaluationCache
from vrptw_hybrid.solvers.alns.destroy import random_removal, shaw_related_removal
from vrptw_hybrid.solvers.alns.repair import greedy_cheapest_insertion
from vrptw_hybrid.solvers.alns.state import ALNSState
from vrptw_hybrid.solvers.greedy import solve_greedy

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "mini_solomon.txt"


def test_nearest_neighbor_cache_returns_limited_neighbors() -> None:
    instance = parse_solomon(FIXTURE, limit_customers=8)
    context = ALNSContext.from_instance(instance, candidate_neighbor_size=2)

    neighbors = context.nearest_neighbors.nearest(instance.customers[0].id, limit=2)

    assert len(neighbors) == 2
    assert instance.customers[0].id not in neighbors


def test_route_evaluation_cache_records_hits_and_misses() -> None:
    instance = parse_solomon(FIXTURE, limit_customers=8)
    context = ALNSContext.from_instance(instance, candidate_neighbor_size=2)
    cache = RouteEvaluationCache()

    first = cache.evaluate((1, 2), instance, profiler=context.profiler)
    second = cache.evaluate((1, 2), instance, profiler=context.profiler)
    snapshot = context.snapshot()

    assert first == second
    assert snapshot["counters"]["route_eval_cache_misses"] == 1
    assert snapshot["counters"]["route_eval_cache_hits"] == 1
    assert cache.snapshot()["entries"] == 1


def test_repair_with_candidate_context_restores_feasible_solution() -> None:
    instance = parse_solomon(FIXTURE, limit_customers=8)
    initial = solve_greedy(instance, seed=42)
    state = ALNSState.from_solution(initial)
    context = ALNSContext.from_instance(instance, candidate_neighbor_size=2)
    destroyed = random_removal(state, instance, random.Random(2), q=3, context=context)

    repaired = greedy_cheapest_insertion(
        destroyed,
        instance,
        random.Random(1),
        context=context,
    )
    solution = repaired.to_solution(instance)
    report = check_solution(solution, instance)

    assert repaired.feasible
    assert report.feasible
    assert context.snapshot()["route_cache"]["entries"] > 0


def test_shaw_removal_counts_restricted_candidates() -> None:
    instance = parse_solomon(FIXTURE, limit_customers=8)
    initial = solve_greedy(instance, seed=42)
    state = ALNSState.from_solution(initial)
    context = ALNSContext.from_instance(instance, candidate_neighbor_size=2)

    destroyed = shaw_related_removal(
        state,
        instance,
        random.Random(3),
        q=2,
        context=context,
    )

    assert len(destroyed.unassigned) == 2
    assert context.snapshot()["counters"]["shaw_related_candidates_considered"] <= 2
