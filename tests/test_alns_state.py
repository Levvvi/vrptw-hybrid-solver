from pathlib import Path

from vrptw_hybrid.core.checker import check_solution
from vrptw_hybrid.core.models import Solution
from vrptw_hybrid.data.solomon import parse_solomon
from vrptw_hybrid.solvers.alns import ALNSState
from vrptw_hybrid.solvers.greedy import solve_greedy

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "mini_solomon.txt"


def route_signature_from_solution(solution: Solution) -> tuple[tuple[int, ...], ...]:
    return tuple(tuple(stop.customer_id for stop in route.stops) for route in solution.routes)


def test_solution_state_solution_round_trip() -> None:
    instance = parse_solomon(FIXTURE, limit_customers=8)
    solution = solve_greedy(instance, seed=42)

    state = ALNSState.from_solution(solution)
    restored = state.to_solution(instance, solver_name="state_roundtrip")
    report = check_solution(restored, instance)

    assert state.unassigned == frozenset()
    assert restored.feasible
    assert report.feasible
    assert route_signature_from_solution(restored) == route_signature_from_solution(solution)
    assert restored.metadata["source_solver"] == "greedy"
    assert restored.metadata["feasibility_violations"] == []


def test_state_copy_with_does_not_pollute_original() -> None:
    state = ALNSState(
        routes=((1, 2),),
        unassigned=frozenset(),
        cost=123.0,
        feasible=True,
        metadata={"history": ["initial"]},
    )

    copied = state.copy_with(routes=((2,),), unassigned={1}, metadata={"history": ["changed"]})
    copied.metadata["history"].append("mutated")

    assert state.routes == ((1, 2),)
    assert state.unassigned == frozenset()
    assert state.metadata == {"history": ["initial"]}
    assert copied.routes == ((2,),)
    assert copied.unassigned == frozenset({1})
    assert copied.metadata == {"history": ["changed", "mutated"]}


def test_partial_state_to_solution_is_marked_infeasible() -> None:
    instance = parse_solomon(FIXTURE, limit_customers=2)
    state = ALNSState(
        routes=((1,),),
        unassigned=frozenset({2}),
        cost=0.0,
        feasible=False,
        metadata={},
    )

    solution = state.to_solution(instance)

    assert not solution.feasible
    assert solution.metadata["unassigned"] == [2]
